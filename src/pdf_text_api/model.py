"""Structured document model shared by every engine (Python and the browser engine).

Coordinates are PDF points with the origin at the TOP-LEFT of the page
(y grows downwards), so a block's `bbox` can be drawn on a rendered page as is.
The JSON produced by `Document.to_dict()` follows `SCHEMA` — the browser engine in
`docs/assets/engine.js` emits the same shape.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field

SCHEMA = "pdf-text-api/document@1"

# Block types, in the order a reader usually cares about them.
BLOCK_TYPES = (
    "heading",
    "paragraph",
    "list_item",
    "table",
    "figure",
    "formula",
    "caption",
    "code",
    "header",
    "footer",
    "page_number",
)
# Page furniture: kept in the JSON (with its position) but left out of text/markdown.
FURNITURE = frozenset({"header", "footer", "page_number"})

BBox = tuple[float, float, float, float]


@dataclass
class ImageData:
    name: str  # e.g. "p3-table-2.png"
    mime: str
    width: int  # pixels
    height: int
    data: bytes = field(repr=False)

    def to_dict(self, embed: bool) -> dict:
        out = {"name": self.name, "mime": self.mime, "width": self.width, "height": self.height}
        if embed:
            out["data"] = base64.b64encode(self.data).decode("ascii")
        return out


@dataclass
class Block:
    type: str
    bbox: BBox | None
    text: str = ""
    level: int | None = None  # heading level (1-6) or list indent level (0-based)
    rows: list[list[str]] | None = None  # table cells, first row is the header
    latex: str | None = None  # formula (approximate, from glyphs; see README)
    number: str | None = None  # formula / figure / table number, e.g. "(3)"
    marker: str | None = None  # list marker ("•", "1.", "a)")
    image: ImageData | None = None  # crop of the region (figures, tables, formulas)
    caption: str | None = None
    font_size: float | None = None
    bold: bool = False
    lines: int = 1
    column: int = 0
    order: int = 0
    id: str = ""

    def to_dict(self, embed_images: bool = True) -> dict:
        out: dict = {"id": self.id, "type": self.type, "order": self.order}
        out["bbox"] = [round(v, 2) for v in self.bbox] if self.bbox else None
        out["text"] = self.text
        for key in ("level", "rows", "latex", "number", "marker", "caption"):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        if self.font_size:
            out["style"] = {"size": round(self.font_size, 1), "bold": self.bold}
        if self.image is not None:
            out["image"] = self.image.to_dict(embed_images)
        return out


@dataclass
class Page:
    number: int  # 1-based
    width: float
    height: float
    blocks: list[Block] = field(default_factory=list)
    scanned: bool = False

    @property
    def content(self) -> list[Block]:
        return [b for b in self.blocks if b.type not in FURNITURE]

    @property
    def text(self) -> str:
        from .render import blocks_to_text

        return blocks_to_text(self.content)

    def to_dict(self, embed_images: bool = True) -> dict:
        return {
            "number": self.number,
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "scanned": self.scanned,
            "blocks": [b.to_dict(embed_images) for b in self.blocks],
        }


@dataclass
class Document:
    pages: list[Page]
    page_count: int
    metadata: dict[str, str] = field(default_factory=dict)
    likely_scanned: bool = False
    elapsed_ms: float = 0.0
    timings: dict[str, float] = field(default_factory=dict)
    engine: str = "tika+pdfium"
    source_type: str = "application/pdf"
    warnings: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ views
    def blocks(self, *types: str):
        for page in self.pages:
            for block in page.blocks:
                if not types or block.type in types:
                    yield block

    @property
    def tables(self) -> list[Block]:
        return list(self.blocks("table"))

    @property
    def figures(self) -> list[Block]:
        return list(self.blocks("figure"))

    @property
    def formulas(self) -> list[Block]:
        return list(self.blocks("formula"))

    @property
    def text(self) -> str:
        from .render import to_text

        return to_text(self)

    def to_markdown(self, **kwargs) -> str:
        from .render import to_markdown

        return to_markdown(self, **kwargs)

    def to_html(self, **kwargs) -> str:
        from .render import to_html

        return to_html(self, **kwargs)

    def to_dict(self, embed_images: bool = True, include_markdown: bool = True) -> dict:
        out = {
            "schema": SCHEMA,
            "engine": self.engine,
            "source_type": self.source_type,
            "page_count": self.page_count,
            "pages_extracted": len(self.pages),
            "likely_scanned": self.likely_scanned,
            "metadata": self.metadata,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "timings": {k: round(v, 1) for k, v in self.timings.items()},
            "warnings": self.warnings,
            "text": self.text,
        }
        if include_markdown:
            # Images are referenced by name (images/<name>); the bytes live in the blocks.
            out["markdown"] = self.to_markdown(images="ref")
        out["pages"] = [p.to_dict(embed_images) for p in self.pages]
        return out
