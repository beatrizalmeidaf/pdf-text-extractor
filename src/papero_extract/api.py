"""HTTP API: `POST /v1/extract` + the web app at `/`.

Run with:  uvicorn papero_extract.api:app  (or `papero-extract serve`)

Latency plan for one request:
  * Tika is called from long-lived threads of this process (keep-alive connections);
  * at the same time, PDFium layout runs in the worker processes, pages split across
    them for long documents;
  * identical requests are answered from an in-memory LRU cache (content hash).
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import math
import multiprocessing
import os
import sys
import tempfile
import time
import zipfile
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from . import __version__
from .cleaning import CleanOptions
from .config import Settings
from .extractor import (
    ExtractionError,
    _open_pdf,
    _tika_threads,
    _timed_tika,
    assemble,
    extract,
    extract_text,
    is_pdf,
    parse_page_spec,
    worker_warmup,
)
from .layout import LayoutOptions, analyze_pages
from .render import tables_csv
from .tika_client import TikaUnavailableError, get_client

log = logging.getLogger("papero_extract")

REPO_URL = "https://github.com/beatrizalmeidaf/papero-pdf-text-extractor"
PAGES_URL = "https://beatrizalmeidaf.github.io/papero-pdf-text-extractor/"

MEDIA = {
    "json": "application/json",
    "markdown": "text/markdown; charset=utf-8",
    "text": "text/plain; charset=utf-8",
    "html": "text/html; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "zip": "application/zip",
}


# --------------------------------------------------------------------------- errors
class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.headers = status, code, message, headers


def _error(status: int, code: str, message: str, headers: dict | None = None, **extra):
    body = {"error": {"code": code, "message": message, **extra}}
    return JSONResponse(body, status_code=status, headers=headers)


# --------------------------------------------------------------------------- worker pool
class WorkerPool:
    """Process pool for PDFium work that survives a worker crash (a PDF segfaulting PDFium)."""

    def __init__(self, workers: int):
        self.workers = workers
        self._pool: ProcessPoolExecutor | None = None

    def start(self) -> None:
        self._pool = ProcessPoolExecutor(
            max_workers=self.workers,
            mp_context=multiprocessing.get_context("spawn"),
            # Recycle workers now and then (PDFium leaks a little); Python 3.11+ only.
            **({"max_tasks_per_child": 1000} if sys.version_info >= (3, 11) else {}),
        )
        # Spawn every worker and import PDFium now, so the first request isn't slow.
        futures = [self._pool.submit(worker_warmup, 0.2) for _ in range(self.workers)]
        pids = {f.result() for f in futures}
        log.info("worker pool ready: %d processes", len(pids))

    def stop(self) -> None:
        if self._pool:
            self._pool.shutdown(wait=False, cancel_futures=True)

    async def run(self, fn, *args):
        pool = self._pool
        try:
            return await asyncio.get_running_loop().run_in_executor(pool, partial(fn, *args))
        except BrokenProcessPool:
            if self._pool is pool:
                log.error("worker crashed; restarting pool")
                self.stop()
                await run_in_threadpool(self.start)
            raise ApiError(
                422,
                "parser_crashed",
                "O PDF derrubou o processo de extração. O arquivo pode estar corrompido.",
            ) from None


# --------------------------------------------------------------------------- rate limiting & cache
class RateLimiter:
    """Fixed-window limiter per client IP. In-memory: fine for a single instance."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, tuple[int, int]] = {}

    def check(self, key: str) -> int | None:
        """Return seconds to wait if limited, else None."""
        window = int(time.time() // 60)
        start, count = self._hits.get(key, (window, 0))
        if start != window:
            start, count = window, 0
        if count >= self.per_minute:
            return 60 - int(time.time() % 60)
        self._hits[key] = (start, count + 1)
        if len(self._hits) > 10_000:  # drop stale windows
            self._hits = {k: v for k, v in self._hits.items() if v[0] == window}
        return None


class ResponseCache:
    """LRU of rendered responses, bounded by entry count and total bytes."""

    def __init__(self, entries: int, max_bytes: int):
        self.entries, self.max_bytes = entries, max_bytes
        self._data: OrderedDict[str, tuple[bytes, str, dict]] = OrderedDict()
        self._bytes = 0

    def get(self, key: str):
        item = self._data.get(key)
        if item is not None:
            self._data.move_to_end(key)
        return item

    def put(self, key: str, body: bytes, media: str, headers: dict) -> None:
        if not self.entries or len(body) > self.max_bytes // 4:
            return
        if key in self._data:
            self._bytes -= len(self._data.pop(key)[0])
        self._data[key] = (body, media, headers)
        self._bytes += len(body)
        while len(self._data) > self.entries or self._bytes > self.max_bytes:
            _, (old, _, _) = self._data.popitem(last=False)
            self._bytes -= len(old)


# --------------------------------------------------------------------------- schemas
class ErrorOut(BaseModel):
    error: dict


# --------------------------------------------------------------------------- helpers
def _save_upload(src, limit: int) -> tuple[str, str]:
    """Stream the upload to a temp file; returns (path, sha256)."""
    fd, path = tempfile.mkstemp(prefix="pte-")
    digest = hashlib.sha256()
    try:
        with os.fdopen(fd, "wb") as out:
            size = 0
            while chunk := src.read(1 << 20):
                size += len(chunk)
                if size > limit:
                    raise ApiError(
                        413,
                        "file_too_large",
                        f"Arquivo maior que o limite de {limit // (1024 * 1024)} MB.",
                    )
                digest.update(chunk)
                out.write(chunk)
            if size == 0:
                raise ApiError(400, "empty_file", "O arquivo enviado está vazio.")
        return path, digest.hexdigest()
    except BaseException:
        os.unlink(path)
        raise


def worker_page_count(path: str, password: str | None) -> int:
    pdf = _open_pdf(Path(path).read_bytes(), password)
    try:
        return len(pdf)
    finally:
        pdf.close()


def web_dir() -> Path | None:
    """The web app: packaged copy (wheel) or the repo's web/ folder (dev checkout)."""
    here = Path(__file__).resolve().parent
    for candidate in (here / "web", here.parents[1] / "web"):
        if (candidate / "index.html").is_file():
            return candidate
    return None


def _zip_bundle(doc, stem: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{stem}.md", doc.to_markdown(images="ref"))
        z.writestr(f"{stem}.txt", doc.text)
        z.writestr(f"{stem}.html", doc.to_html(images="ref"))
        z.writestr(
            f"{stem}.json",
            json.dumps(doc.to_dict(embed_images=False), ensure_ascii=False, indent=2),
        )
        if doc.tables:
            z.writestr(f"{stem}-tabelas.csv", tables_csv(doc))
        for block in doc.blocks():
            if block.image is not None:
                z.writestr(f"images/{block.image.name}", block.image.data)
    return buf.getvalue()


# --------------------------------------------------------------------------- app
def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if not log.handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s %(message)s")
    pool = WorkerPool(settings.workers)
    limiter = (
        RateLimiter(settings.rate_limit_per_minute) if settings.rate_limit_per_minute else None
    )
    cache = ResponseCache(settings.cache_entries, settings.cache_mb * 1024 * 1024)
    state = {"inflight": 0, "tika": "starting"}

    def start_tika() -> None:
        try:
            get_client().ensure_started()
            state["tika"] = "ok"
        except TikaUnavailableError as exc:
            state["tika"] = "unavailable"
            log.warning("Tika indisponível (modo estruturado segue sem ele): %s", exc)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await asyncio.gather(run_in_threadpool(pool.start), run_in_threadpool(start_tika))
        yield
        pool.stop()

    app = FastAPI(
        title="papero API",
        version=__version__,
        summary="papero — extração estruturada de PDFs e documentos (Apache Tika + PDFium).",
        description=(
            "Envie um PDF (ou DOCX, PPTX, XLSX, HTML, EPUB…) e receba Markdown, JSON com "
            "posições, tabelas estruturadas, fórmulas em LaTeX e imagens recortadas. "
            "Nenhum arquivo é armazenado: tudo é apagado ao fim da requisição.\n\n"
            f"Código-fonte: [{REPO_URL}]({REPO_URL}) · App web: [{PAGES_URL}]({PAGES_URL})"
        ),
        license_info={"name": "MIT", "url": f"{REPO_URL}/blob/main/LICENSE"},
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["Server-Timing", "X-Page-Count", "X-Cache", "Content-Disposition"],
    )

    @app.middleware("http")
    async def reject_huge_bodies(request: Request, call_next):
        # Fail fast, before the body is uploaded and parsed.
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_file_bytes + 64 * 1024:
            return _error(
                413, "file_too_large", f"Arquivo maior que o limite de {settings.max_file_mb} MB."
            )
        return await call_next(request)

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return _error(exc.status, exc.code, exc.message, exc.headers)

    @app.exception_handler(ExtractionError)
    async def _extraction_error(_: Request, exc: ExtractionError):
        return _error(exc.status, exc.code, str(exc))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        return _error(
            422,
            "validation_error",
            "Parâmetros inválidos.",
            details=[{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()],
        )

    async def guard(request: Request) -> None:
        if settings.api_keys:
            auth = request.headers.get("authorization", "")
            key = request.headers.get("x-api-key") or auth.removeprefix("Bearer ").strip()
            if key not in settings.api_keys:
                raise ApiError(401, "unauthorized", "Envie uma chave válida no header X-API-Key.")
        if limiter:
            client = request.client.host if request.client else "unknown"
            wait = limiter.check(client)
            if wait is not None:
                raise ApiError(
                    429,
                    "rate_limited",
                    f"Limite de requisições atingido. Tente de novo em {wait}s.",
                    {"Retry-After": str(wait)},
                )

    # ----------------------------------------------------------------------- routes
    @app.get("/health", tags=["meta"])
    async def health():
        return {
            "status": "ok",
            "version": __version__,
            "tika": state["tika"],
            "workers": settings.workers,
            "inflight": state["inflight"],
            "max_file_mb": settings.max_file_mb,
        }

    @app.post(
        "/v1/extract",
        tags=["extract"],
        dependencies=[Depends(guard)],
        responses={
            200: {
                "content": {m: {} for m in MEDIA.values()},
                "description": "JSON (padrão), Markdown, texto, HTML, CSV das tabelas ou ZIP.",
            },
            401: {"model": ErrorOut},
            413: {"model": ErrorOut},
            415: {"model": ErrorOut},
            422: {"model": ErrorOut},
            429: {"model": ErrorOut},
            503: {"model": ErrorOut},
            504: {"model": ErrorOut},
        },
        summary="Extrair texto e estrutura de um PDF ou documento",
    )
    async def extract_route(
        file: UploadFile = File(..., description="PDF, DOCX, PPTX, XLSX, ODT, RTF, EPUB, HTML…"),
        password: str | None = Form(None, description="Senha, se o PDF for protegido"),
        mode: Literal["structured", "fast"] = Query(
            "structured",
            description="`structured`: ordem de leitura, tabelas, fórmulas, posições "
            "(Tika + PDFium). "
            "`fast`: só texto, via Tika.",
        ),
        format: Literal["json", "markdown", "text", "html", "csv", "zip"] = Query(
            "json", description="Formato da resposta. `csv` = tabelas; `zip` = tudo + imagens."
        ),
        pages: str | None = Query(
            None, description="Páginas, ex.: `1-3,5,10-`", examples=["1-3,5"]
        ),
        per_page: bool = Query(
            False, description="JSON: incluir as páginas (e os blocos com posição)"
        ),
        images: bool = Query(False, description="Recortar figuras, tabelas e fórmulas em PNG"),
        image_scale: float = Query(
            2.0, ge=0.5, le=4.0, description="Resolução dos recortes (2 = 144 dpi)"
        ),
        tables: bool = Query(True, description="Detectar tabelas"),
        formulas: bool = Query(True, description="Detectar fórmulas (LaTeX aproximado)"),
        ocr: Literal["auto", "off", "force"] = Query(
            "auto", description="OCR (Tika + Tesseract) em páginas escaneadas"
        ),
        ocr_language: str = Query("por+eng", pattern=r"^[a-z_]{3,8}(\+[a-z_]{3,8})*$"),
        clean: bool = Query(True, description="fast: remover números de página"),
        remove_headers: bool = Query(
            True, description="fast: remover cabeçalhos/rodapés repetidos"
        ),
        dehyphenate: bool = Query(False, description="fast: juntar palavras hifenizadas"),
        math_mode: Literal["unicode", "latex"] = Query(
            "unicode",
            alias="math",
            description="markdown/text: 'latex' escreve a matemática do texto como $…$",
        ),
    ):
        if state["inflight"] >= settings.job_limit:
            raise ApiError(
                503, "busy", "Servidor ocupado. Tente novamente em instantes.", {"Retry-After": "2"}
            )
        state["inflight"] += 1
        path = None
        try:
            path, digest = await run_in_threadpool(_save_upload, file.file, settings.max_file_bytes)
            params = {
                "mode": mode, "format": format, "pages": pages, "per_page": per_page,
                "images": images, "image_scale": image_scale, "tables": tables,
                "formulas": formulas, "ocr": ocr, "ocr_language": ocr_language, "clean": clean,
                "remove_headers": remove_headers, "dehyphenate": dehyphenate, "math": math_mode,
            }  # fmt: skip
            secret = hashlib.sha256((password or "").encode()).hexdigest()
            key = f"{digest}:{secret}:{json.dumps(params, sort_keys=True)}"
            hit = cache.get(key)
            if hit is not None:
                body, media, headers = hit
                return Response(body, media_type=media, headers={**headers, "X-Cache": "hit"})
            stem = Path(file.filename or "documento").stem or "documento"
            try:
                body, media, headers = await asyncio.wait_for(
                    _handle(path, stem, password, params), timeout=settings.request_timeout_s
                )
            except asyncio.TimeoutError:
                raise ApiError(
                    504,
                    "timeout",
                    f"A extração passou de {settings.request_timeout_s}s. Tente um intervalo "
                    "menor de páginas com o parâmetro 'pages'.",
                ) from None
        finally:
            state["inflight"] -= 1
            if path:
                os.unlink(path)
        cache.put(key, body, media, headers)
        return Response(body, media_type=media, headers={**headers, "X-Cache": "miss"})

    async def _handle(path: str, stem: str, password: str | None, p: dict):
        data = await run_in_threadpool(Path(path).read_bytes)
        if p["mode"] == "fast":
            options = CleanOptions(
                remove_page_numbers=p["clean"],
                remove_headers_footers=p["clean"] and p["remove_headers"],
                dehyphenate=p["dehyphenate"],
            )
            result = await run_in_threadpool(
                partial(extract_text, data, pages=p["pages"], password=password, clean=options,
                        max_pages=settings.max_pages)
            )  # fmt: skip
            headers = _timing_headers(result.elapsed_ms, result.page_count)
            if p["format"] == "json":
                return _json(result.to_dict(include_pages=p["per_page"])), MEDIA["json"], headers
            return (
                result.text.encode(),
                MEDIA["text" if p["format"] != "markdown" else "markdown"],
                headers,
            )

        doc = await _structured(path, data, password, p)
        headers = _timing_headers(doc.elapsed_ms, doc.page_count, doc.timings)
        fmt = p["format"]
        if fmt == "json":
            out = doc.to_dict(embed_images=p["images"])
            if not p["per_page"]:
                out.pop("pages")
            return _json(out), MEDIA["json"], headers
        if fmt == "markdown":
            return (
                doc.to_markdown(images="embed" if p["images"] else "none", math=p["math"]).encode(),
                MEDIA[fmt],
                headers,
            )
        if fmt == "text":
            return doc.to_text(math=p["math"]).encode(), MEDIA[fmt], headers
        if fmt == "html":
            return doc.to_html(images="embed").encode(), MEDIA[fmt], headers
        if fmt == "csv":
            headers["Content-Disposition"] = f'attachment; filename="{stem}-tabelas.csv"'
            return tables_csv(doc).encode("utf-8-sig"), MEDIA[fmt], headers
        body = await run_in_threadpool(_zip_bundle, doc, stem)
        headers["Content-Disposition"] = f'attachment; filename="{stem}.zip"'
        return body, MEDIA["zip"], headers

    async def _structured(path: str, data: bytes, password: str | None, p: dict):
        started = time.perf_counter()
        if not is_pdf(data):
            return await run_in_threadpool(
                partial(
                    extract, data, pages=p["pages"], password=password, max_pages=settings.max_pages
                )
            )
        loop = asyncio.get_running_loop()
        tika_on = state["tika"] != "unavailable"
        tika_future = None
        if tika_on:
            tika_future = asyncio.wrap_future(
                _tika_threads().submit(
                    _timed_tika, data, password, p["ocr"] == "force", p["ocr_language"]
                )
            )
        t0 = time.perf_counter()
        try:
            page_count = await pool.run(worker_page_count, path, password)
            indices = parse_page_spec(p["pages"], page_count)
            if settings.max_pages and len(indices) > settings.max_pages:
                from .extractor import TooManyPagesError

                raise TooManyPagesError(
                    f"{len(indices)} páginas selecionadas; o limite é {settings.max_pages}. "
                    "Use o parâmetro 'pages' para extrair um intervalo."
                )
            opts = LayoutOptions(
                images=p["images"], image_scale=p["image_scale"],
                detect_tables=p["tables"], detect_formulas=p["formulas"],
            )  # fmt: skip
            n = settings.workers if len(indices) >= settings.parallel_threshold else 1
            size = math.ceil(len(indices) / n)
            chunks = [indices[k : k + size] for k in range(0, len(indices), size)]
            parts = await asyncio.gather(
                *(pool.run(analyze_pages, path, password, c, opts) for c in chunks)
            )
        except BaseException:
            if tika_future is not None:
                tika_future.cancel()
            raise
        results = [r for part in parts for r in part]
        timings = {"layout_ms": (time.perf_counter() - t0) * 1000}
        warnings: list[str] = []
        tdoc = None
        if tika_future is not None:
            try:
                tdoc, timings["tika_ms"] = await asyncio.wait_for(tika_future, timeout=30)
            except (TikaUnavailableError, asyncio.TimeoutError, ExtractionError, OSError) as exc:
                warnings.append(f"tika_unavailable: {exc}")
        else:
            warnings.append("tika_unavailable: servidor Tika fora do ar")
        return await loop.run_in_executor(
            None,
            partial(
                assemble, results, tdoc, page_count=page_count, data=data, password=password,
                ocr=p["ocr"] if tika_on else "off", ocr_language=p["ocr_language"],
                timings=timings, warnings=warnings, started=started,
            ),
        )  # fmt: skip

    web = web_dir() if settings.enable_ui else None
    if web is not None:
        # Tell the page it is served by the API, so it defaults to this server (Tika).
        page = (
            (web / "index.html")
            .read_text("utf-8")
            .replace("<html ", '<html data-api="same-origin" ', 1)
        )
        if (web / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=web / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        async def ui():
            return HTMLResponse(page, headers={"Cache-Control": "public, max-age=300"})

    return app


def _json(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()


def _timing_headers(elapsed_ms: float, page_count: int, timings: dict | None = None) -> dict:
    parts = [f"extract;dur={elapsed_ms:.1f}"]
    for k, v in (timings or {}).items():
        if k != "total_ms":
            parts.append(f"{k.removesuffix('_ms')};dur={v:.1f}")
    return {"Server-Timing": ", ".join(parts), "X-Page-Count": str(page_count)}


app = create_app()
