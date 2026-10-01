"""Batch extraction: a folder of documents -> a dataset ready for retrieval, plus a
fidelity report that says which documents need a human look.

    dataset/
    ├── documents/            one .md and one .json per source file (same sub-folders)
    ├── chunks.jsonl          every chunk of every document, one JSON per line
    ├── manifest.json         one entry per document: counts, outputs, fidelity scores
    └── fidelity/
        ├── report.json       totals, signals and every document's issues
        ├── summary.html      the same, to open in a browser
        └── problematic/      one .json per document with warnings or errors

>>> from papero_extract.batch import run_batch
>>> summary = run_batch("./documents", "./dataset", workers=8)
>>> summary["totals"]
{'documents': 10000, 'ok': 9721, 'warning': 214, 'error': 65, ...}

The fidelity figures are heuristic signals, not accuracy (see `fidelity.py`).
"""

from __future__ import annotations

import html
import json
import sys
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .chunks import chunk_document
from .extractor import ExtractionError, extract, is_pdf
from .fidelity import SIGNALS, Signal, assess, reference_text
from .tika_client import TikaUnavailableError, get_client

SCHEMA = "papero-extract/batch@1"
FORMATS = ("markdown", "json")
_SUFFIX = {"markdown": ".md", "json": ".json"}
_HTML_LIMIT = 500  # problematic documents listed in summary.html (all are in report.json)


@dataclass(frozen=True)
class BatchOptions:
    formats: tuple[str, ...] = FORMATS
    chunk_chars: int = 1500
    tables: bool = True
    formulas: bool = True
    ocr: str = "auto"
    ocr_language: str = "por+eng"
    tika: bool = True
    password: str | None = None


def _long(path: Path) -> Path:
    """Windows refuses a path over 260 characters unless it is spelled with this prefix —
    and a paper's title as a file name inside a few folders gets there."""
    if sys.platform == "win32":
        full = str(path.resolve())
        if not full.startswith("\\\\"):
            return Path("\\\\?\\" + full)
    return path


# ----------------------------------------------------------------------------- one document
def _failed(name: str, source: str, code: str, message: str) -> dict:
    issue = {"code": code, "severity": "error", "count": 1, "pages": [], "message": message}
    return {
        "document": name,
        "source": source,
        "status": "error",
        "fidelity": {"status": "error", "score": None, "signals": {}, "issues": [issue]},
        "chunk_rows": [],
    }


def process_document(source: str, name: str, stem: str, out: str, opts: BatchOptions) -> dict:
    """Extract one file, write its outputs under `out`/documents and return its manifest
    entry (with the chunks in "chunk_rows"). Top-level so a worker process can run it."""
    try:
        data = Path(source).read_bytes()
        doc = extract(
            data,
            password=opts.password,
            tables=opts.tables,
            formulas=opts.formulas,
            ocr=opts.ocr,
            ocr_language=opts.ocr_language,
            tika=opts.tika,
        )
        reference = reference_text(data, opts.password) if is_pdf(data) else None
        fidelity = assess(doc, reference)
    except ExtractionError as exc:
        return _failed(name, source, exc.code, str(exc))
    except Exception as exc:  # noqa: BLE001 - one broken file must not stop the batch
        return _failed(name, source, "internal_error", f"{type(exc).__name__}: {exc}")

    outputs = {}
    try:
        for fmt in opts.formats:
            path = Path(out, "documents", stem + _SUFFIX[fmt])
            _long(path.parent).mkdir(parents=True, exist_ok=True)
            if fmt == "markdown":
                text = doc.to_markdown(images="none")
            else:
                body = doc.to_dict(embed_images=False, include_markdown=False)
                text = json.dumps(body, ensure_ascii=False)
            _long(path).write_text(text, encoding="utf-8")
            outputs[fmt] = path.relative_to(out).as_posix()
    except OSError as exc:
        return _failed(name, source, "write_failed", f"{type(exc).__name__}: {exc}")
    chunks = chunk_document(doc, document=name, max_chars=opts.chunk_chars)
    return {
        "document": name,
        "source": source,
        "status": fidelity.status,
        "pages": doc.page_count,
        "chars": len(doc.text),
        "tables": len(doc.tables),
        "figures": len(doc.figures),
        "formulas": len(doc.formulas),
        "chunks": len(chunks),
        "elapsed_ms": round(doc.elapsed_ms, 1),
        "outputs": outputs,
        "fidelity": fidelity.to_dict(),
        "chunk_rows": chunks,
    }


# ----------------------------------------------------------------------------- the batch
def find_documents(source: Path, pattern: str = "*.pdf") -> list[Path]:
    if source.is_file():
        return [source]
    return sorted(p for p in source.rglob(pattern) if p.is_file())


def _tasks(source: Path, files: list[Path]) -> list[tuple[str, str, str]]:
    """(path, document name, output stem) per file. Two sources that would write the same
    output ("a.pdf" and "a.docx") keep their extension in the stem."""
    root = source if source.is_dir() else source.parent
    tasks, taken = [], set()
    for path in files:
        name = path.relative_to(root).as_posix()
        stem = path.relative_to(root).with_suffix("").as_posix()
        if stem.lower() in taken:
            stem = name
        taken.add(stem.lower())
        tasks.append((str(path), name, stem))
    return tasks


def run_batch(
    source: str | Path,
    output: str | Path,
    *,
    pattern: str = "*.pdf",
    workers: int = 1,
    options: BatchOptions | None = None,
    progress: Callable[[int, int, dict], None] | None = None,
) -> dict:
    """Extract every document under `source` into `output` and return the report summary.

    `progress(done, total, entry)` is called after each document.
    """
    started = time.perf_counter()
    source, out = Path(source), Path(output)
    if not source.exists():
        raise FileNotFoundError(source)
    opts = options or BatchOptions()
    tasks = _tasks(source, find_documents(source, pattern))
    notes: list[str] = []
    if opts.tika and tasks:
        # Started here once, so the worker processes find it already listening.
        try:
            get_client().ensure_started()
        except TikaUnavailableError as exc:
            opts = BatchOptions(**{**asdict(opts), "tika": False})
            notes.append(f"tika_unavailable: {exc}")

    problematic = out / "fidelity" / "problematic"
    problematic.mkdir(parents=True, exist_ok=True)
    (out / "documents").mkdir(exist_ok=True)
    for stale in problematic.glob("*.json"):  # from a previous run into the same folder
        stale.unlink()

    entries: list[dict] = []
    with (out / "chunks.jsonl").open("w", encoding="utf-8") as chunk_file:

        def done(entry: dict) -> None:
            for row in entry.pop("chunk_rows"):
                chunk_file.write(json.dumps(row, ensure_ascii=False) + "\n")
            if entry["status"] != "ok":
                target = problematic / (entry["document"].replace("/", "__") + ".json")
                try:
                    _long(target).write_text(
                        json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                except OSError as exc:  # the document is in report.json all the same
                    notes.append(f"write_failed: {target.name}: {exc}")
            entries.append(entry)
            if progress:
                progress(len(entries), len(tasks), entry)

        if workers <= 1 or len(tasks) <= 1:
            for path, name, stem in tasks:
                done(process_document(path, name, stem, str(out), opts))
        else:
            with ProcessPoolExecutor(max_workers=min(workers, len(tasks))) as pool:
                futures = [
                    pool.submit(process_document, path, name, stem, str(out), opts)
                    for path, name, stem in tasks
                ]
                for (path, name, _), future in zip(tasks, futures, strict=True):
                    try:
                        done(future.result())
                    except Exception as exc:  # noqa: BLE001 - a worker died on this file
                        done(_failed(name, path, "worker_crashed", f"{type(exc).__name__}: {exc}"))

    summary = summarize(entries)
    summary.update(
        schema=SCHEMA,
        version=__version__,
        created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        input=str(source.resolve()),
        options={**asdict(opts), "password": bool(opts.password), "pattern": pattern},
        notes=notes,
        elapsed_s=round(time.perf_counter() - started, 1),
    )
    report = {**summary, "documents": [_report_row(e) for e in entries]}
    manifest = {**summary, "documents": [_manifest_row(e) for e in entries]}
    _write_json(out / "manifest.json", manifest)
    _write_json(out / "fidelity" / "report.json", report)
    (out / "fidelity" / "summary.html").write_text(summary_html(summary, entries), encoding="utf-8")
    return summary


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _manifest_row(entry: dict) -> dict:
    fidelity = entry["fidelity"]
    row = {k: v for k, v in entry.items() if k not in ("fidelity", "status")}
    row["status"] = entry["status"]
    row["fidelity"] = {
        "score": fidelity["score"],
        **{name: s["score"] for name, s in fidelity["signals"].items()},
    }
    row["issues"] = [i["code"] for i in fidelity["issues"]]
    return row


def _report_row(entry: dict) -> dict:
    return {
        "document": entry["document"],
        "status": entry["status"],
        "pages": entry.get("pages"),
        **{k: entry["fidelity"][k] for k in ("score", "signals", "issues")},
    }


def summarize(entries: list[dict]) -> dict:
    """Totals, pooled signals and the tally of each problem over the whole batch."""
    totals = {"documents": len(entries), "ok": 0, "warning": 0, "error": 0}
    totals.update(dict.fromkeys(("pages", "chunks", "tables", "figures", "formulas"), 0))
    pooled = {name: Signal() for name in SIGNALS}
    problems: dict[str, dict] = {}
    for e in entries:
        totals[e["status"]] += 1
        for key in ("pages", "chunks", "tables", "figures", "formulas"):
            totals[key] += e.get(key, 0)
        for name, s in e["fidelity"]["signals"].items():
            pooled[name].ok += s["ok"]
            pooled[name].total += s["total"]
        for issue in e["fidelity"]["issues"]:
            p = problems.setdefault(
                issue["code"],
                {"severity": "warning", "documents": 0, "count": 0, "message": issue["message"]},
            )
            p["documents"] += 1
            p["count"] += issue["count"]
            if issue["severity"] == "error":
                p["severity"] = "error"
    ordered = sorted(
        problems.items(), key=lambda kv: (kv[1]["severity"] != "error", -kv[1]["documents"])
    )
    return {
        "totals": totals,
        "signals": {name: s.to_dict() for name, s in pooled.items()},
        "problems": dict(ordered),
    }


# ----------------------------------------------------------------------------- summary.html
_SIGNAL_LABEL = {
    "text": ("Text", "of the words on each page are in the output"),
    "reading_order": ("Reading order", "of the steps between blocks go forward"),
    "tables": ("Tables", "of the tables are a clean grid and none is missing"),
    "figures": ("Figures", "of the figure captions have their figure"),
    "formulas": ("Formulas", "of the formulas have LaTeX and no unmapped glyph"),
}
_STATUS_LABEL = {"ok": "High fidelity", "warning": "Warnings", "error": "Errors"}

_CSS = """
:root{--bg:#f7f7f4;--surface:#fff;--surface-2:#f0f0ec;--border:#e2e2dc;--text:#1c1c1a;
--muted:#6a6a64;--accent:#c2410c;--danger:#b42318;--warn:#a16207;--ok:#15803d;color-scheme:light}
@media(prefers-color-scheme:dark){:root{--bg:#121211;--surface:#1b1b19;--surface-2:#242421;
--border:#33332f;--text:#ecece6;--muted:#a2a29a;--accent:#fb923c;--danger:#f97066;--warn:#facc15;
--ok:#4ade80;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.5 Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:60rem;margin:0 auto;padding:2rem 1rem 4rem}
h1{font-size:1.4rem;margin:0}h2{font-size:1rem;margin:2.5rem 0 .75rem}
.sub,.note{color:var(--muted);font-size:.85rem;overflow-wrap:anywhere}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(7.5rem,1fr));gap:.75rem;
margin-top:1.5rem}
.tile,.card,details{background:var(--surface);border:1px solid var(--border);border-radius:12px}
.tile{padding:.9rem 1rem}.tile b{display:block;font-size:1.6rem;font-variant-numeric:tabular-nums}
.tile span{color:var(--muted);font-size:.85rem}
.ok b,.ok .badge{color:var(--ok)}.warning b,.warning .badge{color:var(--warn)}
.error b,.error .badge{color:var(--danger)}
.card{padding:.5rem 1rem}
.signal{display:grid;grid-template-columns:8rem 1fr 4.5rem;gap:.75rem;align-items:center;
padding:.55rem 0}
.signal+.signal{border-top:1px solid var(--border)}
.meter{height:.5rem;background:var(--surface-2);border-radius:99px;overflow:hidden}
.meter i{display:block;height:100%;background:var(--accent);border-radius:99px}
.signal strong{text-align:right;font-variant-numeric:tabular-nums}
.signal small{grid-column:2/4;color:var(--muted);margin-top:-.5rem}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:.5rem .5rem;border-top:1px solid var(--border);vertical-align:top}
th{border-top:0;color:var(--muted);font-weight:500;font-size:.85rem}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
code{font:.85em ui-monospace,SFMono-Regular,Consolas,monospace}
details{margin-top:.5rem;padding:.6rem 1rem}
summary{cursor:pointer;display:flex;gap:.75rem;align-items:baseline;flex-wrap:wrap}
summary .name{font-weight:600;overflow-wrap:anywhere;flex:1 1 14rem}
.badge{font-size:.8rem;font-weight:600;text-transform:uppercase;letter-spacing:.03em}
details ul{margin:.6rem 0;padding-left:1.1rem}details a{color:var(--accent)}
"""


def _pct(score: float | None) -> str:
    return "—" if score is None else f"{score * 100:.1f}%"


def _document_html(entry: dict) -> str:
    e = html.escape
    fidelity = entry["fidelity"]
    issues = "".join(
        f'<li class="{i["severity"]}"><span class="badge">{i["severity"]}</span> '
        f"<code>{e(i['code'])}</code> ×{i['count']} — {e(i['message'])}"
        + (
            f" <span class='sub'>(pages {', '.join(map(str, i['pages'][:20]))})</span>"
            if i["pages"]
            else ""
        )
        + "</li>"
        for i in fidelity["issues"]
    )
    links = " · ".join(
        f'<a href="../{e(path)}">{fmt}</a>' for fmt, path in entry.get("outputs", {}).items()
    )
    source = Path(entry["source"])
    links += (" · " if links else "") + f'<a href="{e(source.resolve().as_uri())}">source</a>'
    pages = f"{entry['pages']} pages" if "pages" in entry else ""
    return (
        f'<details class="{entry["status"]}"><summary><span class="name">{e(entry["document"])}'
        f'</span><span class="badge">{entry["status"]}</span>'
        f'<span class="sub">{_pct(fidelity["score"])} · {pages}</span></summary>'
        f'<ul>{issues}</ul><p class="sub">{links}</p></details>'
    )


def summary_html(summary: dict, entries: list[dict]) -> str:
    e = html.escape
    t = summary["totals"]
    tiles = [("", t["documents"], "Documents")]
    tiles += [(s, t[s], _STATUS_LABEL[s]) for s in ("ok", "warning", "error")]
    tiles += [("", t[k], k.capitalize()) for k in ("pages", "chunks", "tables")]
    tiles_html = "".join(
        f'<div class="tile {cls}"><b>{value:,}</b><span>{label}</span></div>'
        for cls, value, label in tiles
    )
    signals = ""
    for name, s in summary["signals"].items():
        label, meaning = _SIGNAL_LABEL[name]
        width = 0 if s["score"] is None else s["score"] * 100
        detail = f"{_pct(s['score'])} {meaning}" if s["total"] else "nothing to check"
        signals += (
            f'<div class="signal"><span>{label}</span><div class="meter">'
            f'<i style="width:{width:.1f}%"></i></div>'
            f"<strong>{_pct(s['score'])}</strong><small>{detail} "
            f"({s['ok']:,.0f} of {s['total']:,.0f})</small></div>"
        )
    problems = "".join(
        f'<tr class="{p["severity"]}"><td><span class="badge">{p["severity"]}</span></td>'
        f"<td><code>{e(code)}</code><br><span class='sub'>{e(p['message'])}</span></td>"
        f'<td class="n">{p["documents"]:,}</td><td class="n">{p["count"]:,}</td></tr>'
        for code, p in summary["problems"].items()
    )
    flagged = sorted(
        (x for x in entries if x["status"] != "ok"),
        key=lambda x: (x["status"] != "error", x["fidelity"]["score"] or 0),
    )
    listing = "".join(_document_html(x) for x in flagged[:_HTML_LIMIT])
    if len(flagged) > _HTML_LIMIT:
        shown = f"Showing {_HTML_LIMIT} of {len(flagged):,}; all are in report.json."
        listing += f'<p class="note">{shown}</p>'
    problems_html = (
        '<div class="card"><table><tr><th></th><th>Problem</th><th class="n">Documents</th>'
        f'<th class="n">Occurrences</th></tr>{problems}</table></div>'
        if problems
        else '<p class="note">No problems found.</p>'
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>papero · batch fidelity report</title><style>{_CSS}</style></head>
<body><main>
<h1>Batch fidelity report</h1>
<p class="sub">{e(summary.get("input", ""))} · {e(summary.get("created", ""))} ·
papero-extract {e(summary.get("version", ""))} · {summary.get("elapsed_s", 0):,} s</p>
<div class="tiles">{tiles_html}</div>
<h2>Fidelity signals</h2>
<div class="card">{signals}</div>
<p class="note">Heuristic checks against each PDF's own text and geometry, pooled over the batch.
There is no ground truth here: read them as "where to look", not as accuracy.</p>
<h2>Problems</h2>
{problems_html}
<h2>Documents to review ({len(flagged):,})</h2>
{listing or '<p class="note">Every document passed every check.</p>'}
</main></body></html>
"""
