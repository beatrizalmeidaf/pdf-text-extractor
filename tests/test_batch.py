import json
import shutil

import pytest

from papero_extract import extract
from papero_extract.batch import BatchOptions, run_batch
from papero_extract.chunks import chunk_document
from papero_extract.cli import main
from papero_extract.fidelity import assess, reference_text

NO_TIKA = BatchOptions(tika=False)


@pytest.fixture
def folder(tmp_path, structured_pdf, sample_pdf):
    src = tmp_path / "in"
    (src / "sub").mkdir(parents=True)
    shutil.copy(structured_pdf, src / "structured.pdf")
    shutil.copy(sample_pdf, src / "sub" / "sample.pdf")
    (src / "broken.pdf").write_bytes(b"%PDF-1.4 isto nao e um pdf")
    return src


@pytest.fixture(scope="module")
def doc(structured_pdf):
    return extract(structured_pdf, tika=False)


# ----------------------------------------------------------------------------- batch
def test_batch_writes_dataset(folder, tmp_path):
    out = tmp_path / "dataset"
    summary = run_batch(folder, out, options=NO_TIKA)

    assert summary["totals"]["documents"] == 3
    assert (summary["totals"]["ok"], summary["totals"]["error"]) == (2, 1)
    assert (out / "documents" / "structured.md").read_text("utf-8").startswith("# Extração")
    page = json.loads((out / "documents" / "sub" / "sample.json").read_text("utf-8"))
    assert page["page_count"] == 5 and "markdown" not in page

    chunks = [json.loads(ln) for ln in (out / "chunks.jsonl").read_text("utf-8").splitlines()]
    assert {c["document"] for c in chunks} == {"structured.pdf", "sub/sample.pdf"}
    assert len({c["id"] for c in chunks}) == len(chunks)

    manifest = json.loads((out / "manifest.json").read_text("utf-8"))
    rows = {d["document"]: d for d in manifest["documents"]}
    assert rows["structured.pdf"]["tables"] == 2 and rows["structured.pdf"]["fidelity"]["text"] == 1
    assert rows["structured.pdf"]["outputs"]["markdown"] == "documents/structured.md"
    assert rows["broken.pdf"]["status"] == "error" and rows["broken.pdf"]["issues"] == [
        "invalid_pdf"
    ]
    assert sum(d["chunks"] for d in manifest["documents"] if "chunks" in d) == len(chunks)

    report = json.loads((out / "fidelity" / "report.json").read_text("utf-8"))
    assert report["problems"]["invalid_pdf"]["documents"] == 1
    assert report["signals"]["tables"]["score"] == 1
    flagged = [p.name for p in (out / "fidelity" / "problematic").iterdir()]
    assert flagged == ["broken.pdf.json"]
    page = (out / "fidelity" / "summary.html").read_text("utf-8")
    assert "broken.pdf" in page and "invalid_pdf" in page and "structured.pdf" not in page


def test_batch_in_parallel_matches_sequential(folder, tmp_path):
    run_batch(folder, tmp_path / "one", options=NO_TIKA)
    summary = run_batch(folder, tmp_path / "two", workers=2, options=NO_TIKA)
    assert summary["totals"]["documents"] == 3
    one = (tmp_path / "one" / "chunks.jsonl").read_text("utf-8")
    assert (tmp_path / "two" / "chunks.jsonl").read_text("utf-8") == one


def test_batch_cli(folder, tmp_path, capsys):
    out = tmp_path / "dataset"
    assert main(["batch", str(folder), "-o", str(out), "--no-tika", "-w", "1"]) == 0
    err = capsys.readouterr().err
    assert "[3/3]" in err and "✗ broken.pdf  invalid_pdf" in err and "3 documentos" in err
    assert (out / "fidelity" / "summary.html").exists()
    assert main(["batch", str(tmp_path / "nada"), "-o", str(out)]) == 2
    (tmp_path / "vazia").mkdir()
    assert main(["batch", str(tmp_path / "vazia"), "-o", str(out)]) == 2


# ----------------------------------------------------------------------------- chunks
def test_chunks_follow_the_structure(doc):
    chunks = chunk_document(doc, document="a.pdf", max_chars=400)
    assert [c["id"] for c in chunks] == [f"a.pdf#{n}" for n in range(len(chunks))]
    tables = [c for c in chunks if c["type"] == "table"]
    assert len(tables) == 2
    # The table carries its caption, and the caption is not repeated as text.
    assert tables[0]["text"].startswith("Tabela 1: Comparação entre modelos.\n\n| Modelo |")
    assert sum("Tabela 1:" in c["text"] for c in chunks) == 1
    assert tables[0]["headings"] == ["Extração Estruturada", "2 Resultados"]
    # A chunk never crosses a heading: at most one, and at its top.
    for c in chunks:
        assert c["text"].count("\n## ") == 0 and c["chars"] == len(c["text"])
    intro = chunks[0]
    assert intro["text"].startswith("## 1 Introdução") and intro["pages"] == [1, 1]
    assert all(b.startswith("p1-") for b in intro["blocks"])


def test_chunk_size_is_respected(doc):
    small = chunk_document(doc, max_chars=300)
    large = chunk_document(doc, max_chars=5000)
    assert len(small) > len(large)
    text = "".join(c["text"] for c in large)
    assert "E = mc" in text and "Coluna direita começa aqui" in text


# ----------------------------------------------------------------------------- fidelity
def test_clean_document_passes(doc, structured_pdf):
    report = assess(doc, reference_text(structured_pdf))
    assert report.status == "ok" and report.score == 1 and not report.issues
    assert {n: s.total > 0 for n, s in report.signals.items()} == dict.fromkeys(
        report.signals, True
    )


def test_fidelity_finds_what_is_wrong(structured_pdf):
    doc = extract(structured_pdf, tika=False)
    reference = reference_text(structured_pdf)
    first, second, third = doc.pages

    first.blocks = [b for b in first.blocks if b.type != "paragraph"]  # text gone
    two = [b for b in second.blocks if b.type in ("heading", "paragraph")]
    i, j = second.blocks.index(two[0]), second.blocks.index(two[1])
    second.blocks[i], second.blocks[j] = second.blocks[j], second.blocks[i]  # read upwards
    for b in second.blocks:
        if b.type == "formula":
            b.latex = None
    third.blocks = [b for b in third.blocks if b.type != "table"]
    first.blocks = [b for b in first.blocks if b.type != "table"]  # its caption stays

    report = assess(doc, reference)
    found = {i.code: i for i in report.issues}
    assert report.status == "error" and report.score < 0.9
    assert found["text_loss"].pages == [1, 3]
    assert found["reading_order"].pages == [2]
    assert found["formula_uncertain"].count == 2
    assert found["table_not_detected"].severity == "error"
    assert found["table_not_detected"].pages == [1]
    assert report.signals["tables"].score == 0


def test_fidelity_without_reference(doc):
    report = assess(doc)
    assert report.signals["text"].score is None and report.status == "ok"
