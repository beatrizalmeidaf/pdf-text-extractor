import pytest
from fastapi.testclient import TestClient

from pdf_text_api.api import create_app
from pdf_text_api.config import Settings


@pytest.fixture(scope="module")
def client():
    app = create_app(Settings(workers=2, parallel_threshold=16, max_file_mb=1, max_pages=500))
    with TestClient(app) as c:
        yield c


def post(client, path, **params):
    with open(path, "rb") as f:
        return client.post(
            "/v1/extract", params=params, files={"file": ("doc.pdf", f, "application/pdf")}
        )


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_ui_and_docs(client):
    page = client.get("/")
    assert page.status_code == 200 and "<html" in page.text
    assert client.get("/openapi.json").json()["paths"]["/v1/extract"]


def test_extract_json(client, sample_pdf):
    r = post(client, sample_pdf)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["page_count"] == 5 and "Constituição" in body["text"]
    assert "pages" not in body
    assert r.headers["server-timing"].startswith("extract;dur=")


def test_extract_text_format_and_pages(client, sample_pdf):
    r = post(client, sample_pdf, format="text", pages="2")
    assert r.headers["content-type"].startswith("text/plain")
    assert "Capitulo 2" in r.text and "Capitulo 1\n" not in r.text


def test_per_page(client, sample_pdf):
    body = post(client, sample_pdf, per_page="true").json()
    assert [p["number"] for p in body["pages"]] == [1, 2, 3, 4, 5]


def test_parallel_path(client, big_pdf):
    body = post(client, big_pdf).json()
    assert body["pages_extracted"] == 120


def test_other_formats_go_through_tika(client, tmp_path):
    p = tmp_path / "nota.html"
    p.write_text("<html><body><h1>Título</h1><p>olá mundo</p></body></html>", encoding="utf-8")
    with open(p, "rb") as f:
        r = client.post("/v1/extract", files={"file": ("nota.html", f, "text/html")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_type"] == "text/html" and "olá mundo" in body["text"]
    assert body["markdown"].startswith("# Título")


def test_empty_file(client, tmp_path):
    p = tmp_path / "vazio.pdf"
    p.write_bytes(b"")
    r = post(client, p)
    assert r.status_code == 400 and r.json()["error"]["code"] == "empty_file"


def test_too_large(client, tmp_path):
    p = tmp_path / "big.pdf"
    p.write_bytes(b"%PDF-1.4\n" + b"0" * (2 * 1024 * 1024))
    r = post(client, p)
    assert r.status_code == 413


def test_encrypted_needs_password(client, encrypted_pdf):
    r = post(client, encrypted_pdf)
    assert r.status_code == 422 and r.json()["error"]["code"] == "encrypted_pdf"
    with open(encrypted_pdf, "rb") as f:
        ok = client.post("/v1/extract", files={"file": f}, data={"password": "1234"})
    assert ok.status_code == 200


def test_bad_page_range(client, sample_pdf):
    r = post(client, sample_pdf, pages="9")
    assert r.json()["error"]["code"] == "invalid_page_range"


def test_api_key_and_rate_limit(sample_pdf):
    app = create_app(Settings(workers=1, api_keys=frozenset({"k1"}), rate_limit_per_minute=2))
    with TestClient(app) as c:
        assert post(c, sample_pdf).status_code == 401
        with open(sample_pdf, "rb") as f:
            data = f.read()
        codes = [
            c.post(
                "/v1/extract", headers={"X-API-Key": "k1"}, files={"file": ("a.pdf", data)}
            ).status_code
            for _ in range(3)
        ]
        assert codes[:1] == [200] and codes[-1] == 429


def test_worker_crash_recovers():
    import asyncio
    import os

    from pdf_text_api.api import ApiError, WorkerPool
    from pdf_text_api.extractor import worker_warmup

    async def scenario():
        pool = WorkerPool(1)
        pool.start()
        try:
            with pytest.raises(ApiError) as exc:
                await pool.run(os._exit, 1)  # simulate PDFium segfault
            assert exc.value.code == "parser_crashed"
            assert await pool.run(worker_warmup, 0) > 0  # pool was rebuilt
        finally:
            pool.stop()

    asyncio.run(scenario())


def test_structured_blocks_and_formats(client, structured_pdf):
    body = post(client, structured_pdf, per_page="true", images="true").json()
    assert body["schema"] == "pdf-text-api/document@1"
    blocks = [b for p in body["pages"] for b in p["blocks"]]
    table = next(b for b in blocks if b["type"] == "table")
    assert table["rows"][0] == ["Modelo", "Precisão", "Latência (ms)"]
    assert len(table["bbox"]) == 4 and table["image"]["data"]
    assert "| Modelo |" in body["markdown"]

    md = post(client, structured_pdf, format="markdown")
    assert md.headers["content-type"].startswith("text/markdown") and "## 2 Resultados" in md.text
    csv = post(client, structured_pdf, format="csv")
    assert "Proposto" in csv.text and "attachment" in csv.headers["content-disposition"]
    html = post(client, structured_pdf, format="html")
    assert "<table" in html.text


def test_zip_bundle(client, structured_pdf):
    import io
    import zipfile

    r = post(client, structured_pdf, format="zip", images="true")
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert "doc.md" in names and "doc.json" in names and "doc-tabelas.csv" in names
    assert any(n.startswith("images/") and n.endswith(".png") for n in names)


def test_cache_hit(client, structured_pdf):
    first = post(client, structured_pdf, pages="1")
    second = post(client, structured_pdf, pages="1")
    assert first.headers["x-cache"] == "miss" and second.headers["x-cache"] == "hit"
    assert first.content == second.content


def test_fast_mode(client, sample_pdf):
    body = post(client, sample_pdf, mode="fast").json()
    assert body["page_count"] == 5 and "Constituição" in body["text"]
    assert "schema" not in body
