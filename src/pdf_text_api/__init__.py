"""Structured PDF & document extraction on Apache Tika — Python library, CLI and HTTP API.

>>> from pdf_text_api import extract, extract_text
>>> doc = extract("artigo.pdf", images=True)   # structure: order, tables, figures, formulas
>>> doc.to_markdown()
>>> extract_text("contrato.pdf").text           # fastest: plain text via Tika
"""

__version__ = "3.0.0"

from .cleaning import CleanOptions, clean_pages  # noqa: E402
from .extractor import (  # noqa: E402
    EncryptedPDFError,
    EngineUnavailableError,
    ExtractionError,
    ExtractionResult,
    InvalidPDFError,
    PageRangeError,
    PageText,
    TooManyPagesError,
    extract,
    extract_text,
)
from .model import Block, Document, ImageData, Page  # noqa: E402

__all__ = [
    "__version__",
    "extract",
    "extract_text",
    "Document",
    "Page",
    "Block",
    "ImageData",
    "ExtractionResult",
    "PageText",
    "CleanOptions",
    "clean_pages",
    "ExtractionError",
    "InvalidPDFError",
    "EncryptedPDFError",
    "EngineUnavailableError",
    "PageRangeError",
    "TooManyPagesError",
]
