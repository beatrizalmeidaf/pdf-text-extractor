"""Tika XHTML -> blocks.

Tika emits the same XHTML vocabulary for every format it parses (PDF, DOCX, PPTX,
XLSX, ODT, EPUB, HTML, e-mails…): `<h1-6>`, `<p>`, `<ul>/<ol>/<li>`, `<table>`,
`<div class="page">` (PDF pages), `<div class="slide-content">` (PPTX)… so one small
event parser turns any of them into our block model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from .model import Block, Page

_META_KEYS = {
    "dc:title": "title",
    "title": "title",
    "dc:creator": "author",
    "meta:author": "author",
    "dc:subject": "subject",
    "dc:description": "description",
    "meta:keyword": "keywords",
    "pdf:docinfo:keywords": "keywords",
    "dcterms:created": "created",
    "dcterms:modified": "modified",
    "dc:language": "language",
    "pdf:producer": "producer",
    "xmp:creatortool": "creator_tool",
    "pdf:pdfversion": "pdf_version",
    "pdf:encrypted": "encrypted",
    "xmptpg:npages": "pages",
    "meta:page-count": "pages",
    "content-type": "content_type",
}
_WS = re.compile(r"[ \t\r\n ]+")


@dataclass
class TikaDoc:
    metadata: dict[str, str] = field(default_factory=dict)
    pages: list[list[Block]] = field(default_factory=list)  # one list per page (or 1 for non-PDF)
    tagged: bool = False  # headings came from the PDF's tag tree


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.pages: list[list[Block]] = [[]]
        self.saw_page = False
        self.stack: list[str] = []
        self.buf: list[str] = []
        self.block: str | None = None  # "p" | "h3" | "li" | "td" …
        self.list_depth = 0
        self.ol_counters: list[int] = []
        self.label: str | None = None
        self.in_label = False
        self.table: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.skip = 0  # inside <head>/<script>/<style>/<title>

    # ------------------------------------------------------------------ helpers
    def _text(self) -> str:
        return _WS.sub(" ", "".join(self.buf)).strip()

    def _emit(self, block: Block) -> None:
        if block.text or block.rows:
            self.pages[-1].append(block)

    def _close_block(self) -> None:
        if self.block is None:
            return
        tag, text = self.block, self._text()
        self.buf = []
        self.block = None
        if tag in ("td", "th"):
            if self.row is not None:
                self.row.append(text)
            return
        if not text:
            return
        if tag[0] == "h" and tag[1:].isdigit():
            self._emit(Block("heading", None, text=text, level=int(tag[1:])))
        elif tag == "li":
            marker = self.label
            if marker is None and self.ol_counters and self.ol_counters[-1] > 0:
                marker = f"{self.ol_counters[-1]}."
            self._emit(
                Block(
                    "list_item",
                    None,
                    text=text,
                    level=max(0, self.list_depth - 1),
                    marker=marker or "-",
                )
            )
            self.label = None
        elif tag == "pre":
            self._emit(Block("code", None, text=text))
        else:
            self._emit(Block("paragraph", None, text=text))

    # ------------------------------------------------------------------ events
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("head", "script", "style", "title"):
            self.skip += 1
            return
        if tag == "meta":
            name = (a.get("name") or "").lower()
            key = _META_KEYS.get(name)
            if key and a.get("content") and key not in self.meta:
                self.meta[key] = a["content"].strip()
            return
        if self.skip:
            return
        cls = a.get("class", "")
        if tag == "div" and cls in ("page", "slide-content"):
            self._close_block()
            if self.saw_page or self.pages[-1]:
                self.pages.append([])
            self.saw_page = True
            return
        if tag == "div" and cls == "lbl":
            self.in_label = True
            self.label_buf: list[str] = []
            return
        if tag in ("ul", "ol"):
            self._close_block()
            self.list_depth += 1
            self.ol_counters.append(0 if tag == "ul" else 1)
            return
        if tag == "table":
            self._close_block()
            self.table = []
            return
        if tag == "tr" and self.table is not None:
            self.row = []
            return
        if tag in ("td", "th"):
            self._close_block()
            self.block = tag
            return
        if tag in ("p", "li", "pre", "h1", "h2", "h3", "h4", "h5", "h6"):
            if self.block in ("td", "th"):
                return  # paragraphs inside a table cell stay in the cell
            self._close_block()
            self.block = tag
            return
        if tag == "br":
            self.buf.append(" ")

    def handle_endtag(self, tag):
        if tag in ("head", "script", "style", "title"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag == "div" and self.in_label:
            self.in_label = False
            self.label = _WS.sub(" ", "".join(self.label_buf)).strip() or None
            return
        if tag in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "pre"):
            if self.block == tag:
                self._close_block()
            return
        if tag == "li":
            if self.block == "li":
                self._close_block()
            if self.ol_counters and self.ol_counters[-1] > 0:
                self.ol_counters[-1] += 1
            return
        if tag in ("ul", "ol"):
            self._close_block()
            self.list_depth = max(0, self.list_depth - 1)
            if self.ol_counters:
                self.ol_counters.pop()
            return
        if tag in ("td", "th"):
            self._close_block()
            return
        if tag == "tr" and self.table is not None and self.row is not None:
            if any(self.row):
                self.table.append(self.row)
            self.row = None
            return
        if tag == "table" and self.table is not None:
            rows = self.table
            self.table = None
            if rows:
                width = max(len(r) for r in rows)
                rows = [r + [""] * (width - len(r)) for r in rows]
                text = "\n".join(" | ".join(r) for r in rows)
                self._emit(Block("table", None, text=text, rows=rows))

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_label:
            self.label_buf.append(data)
            return
        if self.block is None:
            if data.strip():  # loose text directly in <body>/<div>
                self.block = "p"
            else:
                return
        self.buf.append(data)


def parse_xhtml(xhtml: str) -> TikaDoc:
    p = _Parser()
    p.feed(xhtml)
    p.close()
    p._close_block()
    pages = p.pages if p.saw_page else [p.pages[0]] if p.pages else [[]]
    tagged = "extractmarkedcontent" in xhtml[:4000].lower() or any(
        b.type == "heading" for page in pages for b in page
    )
    return TikaDoc(metadata=p.meta, pages=pages, tagged=tagged)


def to_pages(tdoc: TikaDoc) -> list[Page]:
    """Blocks without geometry (Tika has none) — for non-PDF input and OCR text."""
    pages = []
    for n, blocks in enumerate(tdoc.pages, 1):
        for k, b in enumerate(blocks):
            b.order, b.id = k, f"p{n}-b{k}"
        pages.append(Page(n, 0.0, 0.0, blocks))
    return pages


def page_texts(tdoc: TikaDoc) -> list[str]:
    from .render import blocks_to_text

    return [blocks_to_text(blocks) for blocks in tdoc.pages]
