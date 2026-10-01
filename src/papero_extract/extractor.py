"""Extraction entry points.

Two modes, both built on Apache Tika:

* `extract()` — **structured** (default). Tika and a PDFium layout engine run *at the
  same time*: PDFium gives geometry (reading order across columns, tables, figures,
  formulas, bounding boxes); Tika gives metadata, tagged-PDF headings, OCR for
  scanned pages (Tesseract) and every non-PDF format (DOCX, PPTX, XLSX, HTML, EPUB…).
* `extract_text()` — **fast**. Tika only, plain text per page (the v2 behaviour).
"""

from __future__ import annotations

import logging
import math
import os
import time
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from pathlib import Path

import pypdfium2 as pdfium

from .cleaning import RAW, CleanOptions, clean_pages
from .layout import LayoutOptions, PageResult, analyze_page, analyze_pages, finalize
from .model import Block, Document
from .tika_client import TikaUnavailableError, get_client
from .tika_xhtml import TikaDoc, page_texts, parse_xhtml, to_pages

log = logging.getLogger("papero_extract")

Source = str | os.PathLike | bytes

SCANNED_CHARS_PER_PAGE = 25
TIKA_WAIT_S = 30.0  # how long structured mode waits for Tika's enrichment


# --------------------------------------------------------------------------- errors
class ExtractionError(Exception):
    code = "extraction_failed"
    status = 422


class InvalidPDFError(ExtractionError):
    code = "invalid_pdf"


class EncryptedPDFError(ExtractionError):
    code = "encrypted_pdf"


class PageRangeError(ExtractionError):
    code = "invalid_page_range"


class TooManyPagesError(ExtractionError):
    code = "too_many_pages"
    status = 413


class EngineUnavailableError(ExtractionError):
    code = "tika_unavailable"
    status = 503


# --------------------------------------------------------------------------- fast-mode results
@dataclass
class PageText:
    number: int  # 1-based
    text: str


@dataclass
class ExtractionResult:
    text: str
    pages: list[PageText]
    page_count: int
    metadata: dict[str, str] = field(default_factory=dict)
    likely_scanned: bool = False
    elapsed_ms: float = 0.0

    def to_dict(self, include_pages: bool = True) -> dict:
        data = {
            "text": self.text,
            "page_count": self.page_count,
            "pages_extracted": len(self.pages),
            "likely_scanned": self.likely_scanned,
            "metadata": self.metadata,
            "elapsed_ms": round(self.elapsed_ms, 1),
        }
        if include_pages:
            data["pages"] = [{"number": p.number, "text": p.text} for p in self.pages]
        return data


# --------------------------------------------------------------------------- helpers
def parse_page_spec(spec: str | None, page_count: int) -> list[int]:
    """'1-3,5,9-' -> [0,1,2,4,8,...] (0-based, sorted, unique). None/'' = all pages."""
    if not spec or not spec.strip():
        return list(range(page_count))
    selected: set[int] = set()
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        try:
            if "-" in part:
                a, b = part.split("-", 1)
                start = int(a) if a else 1
                end = int(b) if b else page_count
            else:
                start = end = int(part)
        except ValueError:
            raise PageRangeError(f"Intervalo de páginas inválido: '{part}'") from None
        if start < 1 or end < start:
            raise PageRangeError(f"Intervalo de páginas inválido: '{part}'")
        if start > page_count:
            raise PageRangeError(
                f"Página {start} não existe (o documento tem {page_count} páginas)"
            )
        selected.update(range(start - 1, min(end, page_count)))
    if not selected:
        raise PageRangeError("Nenhuma página selecionada")
    return sorted(selected)


def build_result(
    raw_pages: list[str],
    indices: list[int],
    page_count: int,
    metadata: dict[str, str],
    clean: CleanOptions,
    started: float,
) -> ExtractionResult:
    texts = clean_pages(raw_pages, clean)
    chars = sum(len(t.strip()) for t in texts)
    return ExtractionResult(
        text="\n\n".join(t for t in texts if t.strip()),
        pages=[PageText(i + 1, t) for i, t in zip(indices, texts, strict=True)],
        page_count=page_count,
        metadata=metadata,
        likely_scanned=bool(indices) and chars / len(indices) < SCANNED_CHARS_PER_PAGE,
        elapsed_ms=(time.perf_counter() - started) * 1000,
    )


def _as_options(clean: bool | CleanOptions) -> CleanOptions:
    if isinstance(clean, CleanOptions):
        return clean
    return CleanOptions() if clean else RAW


def _read(source: Source) -> bytes:
    if isinstance(source, bytes):
        return source
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(source)
    return path.read_bytes()


def is_pdf(data: bytes) -> bool:
    return b"%PDF-" in data[:1024]


def _tika_parse(data: bytes, password: str | None, **kwargs) -> TikaDoc:
    resp = get_client().parse(data, password=password, **kwargs)
    body = resp.xhtml
    if resp.status in (401, 403) or "EncryptedDocumentException" in body[:2000]:
        raise EncryptedPDFError("PDF protegido por senha ou senha incorreta.")
    if resp.status == 415:
        raise InvalidPDFError("Formato de arquivo não suportado pelo Tika.")
    if resp.status == 422 and is_pdf(data):
        # Tika answers 422 with an empty body for encrypted *and* broken PDFs: PDFium tells which.
        _open_pdf(data, password).close()
    if resp.status >= 400:
        raise InvalidPDFError(f"O Tika não conseguiu ler o arquivo (HTTP {resp.status}).")
    return parse_xhtml(body)


def _open_pdf(data: bytes, password: str | None) -> pdfium.PdfDocument:
    try:
        return pdfium.PdfDocument(data, password=password)
    except pdfium.PdfiumError as exc:
        msg = str(exc).lower()
        if "password" in msg:
            raise EncryptedPDFError("PDF protegido por senha ou senha incorreta.") from None
        raise InvalidPDFError(f"Arquivo não é um PDF válido ou está corrompido ({exc})") from None


def _check_pages(indices: list[int], max_pages: int) -> None:
    if max_pages and len(indices) > max_pages:
        raise TooManyPagesError(
            f"{len(indices)} páginas selecionadas; o limite é {max_pages}. "
            "Use o parâmetro 'pages' para extrair um intervalo."
        )


# --------------------------------------------------------------------------- fast mode (Tika)
def worker_warmup(delay: float = 0.0) -> int:
    """Load PDFium and run the layout once, so a worker's first real request isn't cold."""
    from .tika_client import _WARMUP_PDF

    analyze_pages(_WARMUP_PDF, None, [0], LayoutOptions())
    time.sleep(delay)  # keeps the task busy so the pool spawns every worker
    return os.getpid()


def extract_text(
    source: Source,
    *,
    pages: str | None = None,
    password: str | None = None,
    clean: bool | CleanOptions = True,
    max_pages: int = 0,
    **_ignored,
) -> ExtractionResult:
    """Fast plain-text extraction with Apache Tika (any format Tika reads).

    >>> from papero_extract import extract_text
    >>> extract_text("relatorio.pdf", pages="1-3").text
    """
    started = time.perf_counter()
    options = _as_options(clean)
    data = _read(source)
    try:
        tdoc = _tika_parse(data, password)
    except TikaUnavailableError as exc:
        raise EngineUnavailableError(str(exc)) from None
    if is_pdf(data) and not any(tdoc.pages) and tdoc.metadata.get("encrypted") == "true":
        raise EncryptedPDFError("PDF protegido por senha ou senha incorreta.")
    if is_pdf(data) and not tdoc.metadata:
        raise InvalidPDFError("Arquivo não é um PDF válido ou está corrompido")
    texts = page_texts(tdoc)
    page_count = len(texts)
    indices = parse_page_spec(pages, page_count)
    _check_pages(indices, max_pages)
    return build_result(
        [texts[i] for i in indices], indices, page_count, tdoc.metadata, options, started
    )


# --------------------------------------------------------------------------- structured mode
def extract(
    source: Source,
    *,
    pages: str | None = None,
    password: str | None = None,
    images: bool = False,
    image_scale: float = 2.0,
    tables: bool = True,
    formulas: bool = True,
    ocr: str = "auto",
    ocr_language: str = "por+eng",
    tika: bool = True,
    workers: int = 1,
    parallel_threshold: int = 48,
    max_pages: int = 0,
    executor: Executor | None = None,
) -> Document:
    """Structured extraction: reading order, tables, figures, formulas, positions.

    `images=True` crops every figure, table and formula to PNG (`block.image`).
    `ocr`: "auto" OCRs pages without a text layer through Tika + Tesseract,
    "force" OCRs everything, "off" never does.
    `tika=False` skips Tika entirely (no metadata/OCR; PDFs only).

    >>> from papero_extract import extract
    >>> doc = extract("artigo.pdf", images=True)
    >>> print(doc.to_markdown())
    >>> doc.tables[0].rows
    """
    started = time.perf_counter()
    data = _read(source)
    timings: dict[str, float] = {}
    warnings: list[str] = []

    if not is_pdf(data):
        return _extract_other(data, password, pages, max_pages, started, tika)

    # Tika runs in a thread (it's an HTTP call) while PDFium works in this one.
    tika_future = (
        _tika_threads().submit(_timed_tika, data, password, ocr == "force", ocr_language)
        if tika
        else None
    )

    try:
        t0 = time.perf_counter()
        pdf = _open_pdf(data, password)
        try:
            page_count = len(pdf)
            indices = parse_page_spec(pages, page_count)
            _check_pages(indices, max_pages)
            opts = LayoutOptions(
                images=images,
                image_scale=image_scale,
                detect_tables=tables,
                detect_formulas=formulas,
            )
            results = _run_layout(
                pdf, data, password, indices, opts, workers, parallel_threshold, executor
            )
        finally:
            pdf.close()
    except BaseException:
        if tika_future is not None:
            tika_future.cancel()
        raise
    timings["layout_ms"] = (time.perf_counter() - t0) * 1000

    tdoc: TikaDoc | None = None
    if tika_future is not None:
        try:
            tdoc, timings["tika_ms"] = tika_future.result(timeout=TIKA_WAIT_S)
        except (TikaUnavailableError, FutureTimeout, ExtractionError, OSError) as exc:
            warnings.append(f"tika_unavailable: {exc}")
            log.warning("Tika enrichment skipped: %s", exc)

    return assemble(
        results,
        tdoc,
        page_count=page_count,
        data=data,
        password=password,
        ocr=ocr if tika else "off",
        ocr_language=ocr_language,
        timings=timings,
        warnings=warnings,
        started=started,
    )


def assemble(
    results: list[PageResult],
    tdoc: TikaDoc | None,
    *,
    page_count: int,
    data: bytes | None,
    password: str | None,
    ocr: str,
    ocr_language: str,
    timings: dict[str, float],
    warnings: list[str],
    started: float,
) -> Document:
    """Merge PDFium pages with Tika's enrichment into the final Document."""
    hints = _heading_hints(tdoc) if tdoc else {}
    doc_pages = finalize(results, hints)
    chars = sum(r.chars for r in results)
    map_errors = sum(r.map_errors for r in results)
    if map_errors > max(20, chars * 0.05):
        warnings.append(
            "unmapped_glyphs: fontes sem mapa Unicode; parte do texto pode estar ilegível"
        )

    # Only pages with no text layer and a page-sized image: blank pages don't trigger OCR.
    scanned = [p for p in doc_pages if p.scanned]
    low_text = sum(1 for r in results if r.chars < SCANNED_CHARS_PER_PAGE)
    likely_scanned = bool(results) and low_text >= max(1, math.ceil(len(results) * 0.5))
    if scanned and ocr != "off" and data is not None:
        t0 = time.perf_counter()
        try:
            _apply_ocr(data, password, scanned, ocr_language, tdoc if ocr == "force" else None)
            timings["ocr_ms"] = (time.perf_counter() - t0) * 1000
        except (TikaUnavailableError, ExtractionError) as exc:
            warnings.append(f"ocr_failed: {exc}")

    metadata = dict(tdoc.metadata) if tdoc else {}
    metadata.pop("content_type", None)
    elapsed = (time.perf_counter() - started) * 1000
    timings["total_ms"] = elapsed
    return Document(
        pages=doc_pages,
        page_count=page_count,
        metadata=metadata,
        likely_scanned=likely_scanned,
        elapsed_ms=elapsed,
        timings=timings,
        engine="tika+pdfium" if tdoc else "pdfium",
        source_type="application/pdf",
        warnings=warnings,
    )


_tika_pool: ThreadPoolExecutor | None = None


def _tika_threads() -> ThreadPoolExecutor:
    """Long-lived threads: each keeps its own keep-alive connection to Tika Server.

    (A fresh thread per call means a fresh TCP connection — measured at +20 ms.)
    """
    global _tika_pool
    if _tika_pool is None:
        _tika_pool = ThreadPoolExecutor(
            max_workers=int(os.environ.get("PTE_TIKA_THREADS", 4)), thread_name_prefix="tika"
        )
    return _tika_pool


def _timed_tika(data: bytes, password: str | None, force_ocr: bool, lang: str):
    t0 = time.perf_counter()
    tdoc = _tika_parse(
        data,
        password,
        marked_content=not force_ocr,
        ocr="ocr_and_text" if force_ocr else "no_ocr",
        ocr_language=lang,
    )
    return tdoc, (time.perf_counter() - t0) * 1000


def _run_layout(
    pdf, data, password, indices, opts, workers, threshold, executor
) -> list[PageResult]:
    if workers <= 1 or len(indices) < threshold:
        return [analyze_page(pdf, i, opts) for i in indices]
    size = math.ceil(len(indices) / workers)
    chunks = [indices[k : k + size] for k in range(0, len(indices), size)]
    own = executor is None
    pool = executor or ProcessPoolExecutor(max_workers=min(workers, len(chunks)))
    try:
        parts = pool.map(
            analyze_pages,
            [data] * len(chunks),
            [password] * len(chunks),
            chunks,
            [opts] * len(chunks),
        )
        return [r for part in parts for r in part]
    finally:
        if own:
            pool.shutdown()


def _heading_hints(tdoc: TikaDoc) -> dict[str, int]:
    """Headings the PDF author tagged (<H1>…<H6>) — authoritative when present."""
    from .layout import _signature

    return {
        _signature(b.text): b.level or 2
        for blocks in tdoc.pages
        for b in blocks
        if b.type == "heading" and b.text and len(b.text) <= 200
    }


def _apply_ocr(data, password, scanned_pages, lang, tdoc: TikaDoc | None) -> None:
    """Fill pages that have no text layer with Tika+Tesseract OCR text."""
    if tdoc is None:
        tdoc = _tika_parse(data, password, ocr="auto", ocr_language=lang)
    texts = page_texts(tdoc)
    for page in scanned_pages:
        i = page.number - 1
        if i >= len(texts) or not texts[i].strip():
            continue
        keep = [b for b in page.blocks if b.type == "figure"]
        page.blocks = keep + [
            Block("paragraph", (0.0, 0.0, page.width, page.height), text=para.strip())
            for para in texts[i].split("\n\n")
            if para.strip()
        ]
        for n, b in enumerate(page.blocks):
            b.order, b.id = n, f"p{page.number}-b{n}"


def _extract_other(data, password, pages, max_pages, started, tika) -> Document:
    """Anything that isn't a PDF: DOCX, PPTX, XLSX, ODT, RTF, EPUB, HTML, e-mail, images…"""
    if not tika:
        raise InvalidPDFError("Sem o Tika, só PDFs são suportados.")
    t0 = time.perf_counter()
    try:
        tdoc = _tika_parse(data, password, ocr="auto")
    except TikaUnavailableError as exc:
        raise EngineUnavailableError(str(exc)) from None
    tika_ms = (time.perf_counter() - t0) * 1000
    doc_pages = to_pages(tdoc)
    indices = parse_page_spec(pages, len(doc_pages))
    _check_pages(indices, max_pages)
    selected = [doc_pages[i] for i in indices]
    metadata = dict(tdoc.metadata)
    source_type = metadata.pop("content_type", "application/octet-stream").split(";")[0]
    elapsed = (time.perf_counter() - started) * 1000
    return Document(
        pages=selected,
        page_count=len(doc_pages),
        metadata=metadata,
        elapsed_ms=elapsed,
        timings={"tika_ms": tika_ms, "total_ms": elapsed},
        engine="tika",
        source_type=source_type,
    )
