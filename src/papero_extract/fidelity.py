"""Fidelity signals: how much an extraction can be trusted, without a ground truth.

Nothing here is an accuracy figure — an arbitrary PDF has no reference to score against.
These are checks a correct extraction passes and a broken one usually fails:

* **text** — the words PDFium reads on each page (in whatever order) are all in the output;
* **reading_order** — a block never jumps back up inside its own column;
* **tables** / **figures** — every "Table N" / "Figure N" caption has its table or figure, and
  each table is a real grid;
* **formulas** — each formula has LaTeX and no unmapped glyphs.

>>> from papero_extract import extract
>>> from papero_extract.fidelity import assess, reference_text
>>> doc = extract("artigo.pdf")
>>> report = assess(doc, reference_text("artigo.pdf"))
>>> report.status, report.score, [i.code for i in report.issues]
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

import pypdfium2 as pdfium

from .layout import _caption_text
from .model import Block, Document, Page

SIGNALS = ("text", "reading_order", "tables", "figures", "formulas")
# How much each signal weighs in the document score (renormalised over the ones that apply).
_WEIGHTS = {"text": 0.4, "reading_order": 0.2, "tables": 0.15, "figures": 0.1, "formulas": 0.15}

TEXT_ERROR, TEXT_WARNING = 0.80, 0.95  # share of the page's words found in the output
TEXT_MIN = 200  # characters of text on a page before its share means anything
ORDER_ERROR = 0.10  # share of block-to-block steps that go backwards
GARBLED_ERROR, GARBLED_WARNING = 0.05, 0.005  # share of characters with no Unicode value

_TOKEN = re.compile(r"[^\W_]+")
_SCRIPTS = re.compile("([\u00b2\u00b3\u00b9\u2070-\u209f]+)")  # super- and subscript characters
_TABLE_CAPTION = re.compile(r"^(tab(ela|le)?|quadro)\b", re.IGNORECASE)
_FIGURE_CAPTION = re.compile(r"^(fig(ura|ure)?|gr[aá]fico|chart)\b", re.IGNORECASE)


@dataclass
class Signal:
    ok: float = 0.0
    total: float = 0.0

    @property
    def score(self) -> float | None:
        return None if not self.total else self.ok / self.total

    def to_dict(self) -> dict:
        score = self.score
        return {
            "score": None if score is None else round(score, 4),
            "ok": round(self.ok, 1),
            "total": round(self.total, 1),
        }


@dataclass
class Issue:
    code: str
    severity: str  # "warning" | "error"
    message: str
    count: int = 0
    pages: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "count": self.count,
            "pages": self.pages,
            "message": self.message,
        }


@dataclass
class Fidelity:
    status: str  # "ok" | "warning" | "error"
    score: float | None
    signals: dict[str, Signal]
    issues: list[Issue]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "score": None if self.score is None else round(self.score, 4),
            "signals": {name: s.to_dict() for name, s in self.signals.items()},
            "issues": [i.to_dict() for i in self.issues],
        }


class _Issues:
    def __init__(self) -> None:
        self.found: dict[str, Issue] = {}

    def add(self, code: str, severity: str, message: str, page: int | None = None, count: int = 1):
        issue = self.found.setdefault(code, Issue(code, severity, message))
        issue.count += count
        if severity == "error":
            issue.severity = "error"
        if page is not None and page not in issue.pages:
            issue.pages.append(page)


# ----------------------------------------------------------------------------- reference text
def reference_text(
    source, password: str | None = None, pages: list[int] | None = None
) -> dict[int, str]:
    """Text of each page (1-based) as PDFium reads it, with no layout analysis."""
    pdf = pdfium.PdfDocument(source, password=password)
    try:
        out = {}
        for number in pages or range(1, len(pdf) + 1):
            page = pdf[number - 1]
            textpage = page.get_textpage()
            try:
                out[number] = textpage.get_text_bounded()
            finally:
                textpage.close()
                page.close()
        return out
    finally:
        pdf.close()


def _fold(text: str) -> str:
    """Case, accents and ligatures out of the way: "ﬁ" = "fi", "´e" = "é" = "e"."""
    # An exponent is a number of its own: "10⁹" is "10" and "9", as the PDF has them.
    text = unicodedata.normalize("NFKD", _SCRIPTS.sub(r" \1 ", text))
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


def _page_output(page: Page) -> str:
    parts = []
    for b in page.blocks:
        parts += [b.text or "", b.caption or "", b.number or "", b.marker or ""]
        for row in b.rows or []:
            parts += row
    return "\n".join(parts)


def _coverage(reference: str, output: str) -> tuple[int, int]:
    """(characters of the reference's words found in the output, characters in those words)."""
    out = _fold(output)
    have = Counter(_TOKEN.findall(out))
    # Without separators: a word hyphenated at a line end, or split by an accent drawn as
    # its own glyph, is still there — and so is "10⁹" read as "109". Not for short numbers:
    # "30" is inside too many other things, and the cells of a lost table would all be "found".
    stream = "".join(_TOKEN.findall(out))
    matched = total = 0
    for token in _TOKEN.findall(_fold(reference)):
        if len(token) < 2:
            continue
        total += len(token)
        if have[token] > 0:
            have[token] -= 1
            matched += len(token)
        elif not (token.isdigit() and len(token) < 3) and token in stream:
            matched += len(token)
    return matched, total


def _garbled(text: str) -> int:
    return sum(1 for c in text if c == "�" or "" <= c <= "" or (c < " " and c not in "\n\t"))


# ----------------------------------------------------------------------------- geometry
def _backwards(a: Block, b: Block) -> bool:
    """`b` is read after `a` but sits wholly above it in the same column."""
    if b.bbox[3] > a.bbox[1] + 2:
        return False
    overlap = min(a.bbox[2], b.bbox[2]) - max(a.bbox[0], b.bbox[0])
    narrow = min(a.bbox[2] - a.bbox[0], b.bbox[2] - b.bbox[0])
    return narrow > 0 and overlap > narrow * 0.5


def _overlap(a: Block, b: Block) -> bool:
    """Two blocks on the same spot. A one-line block inside another is how a run-in heading
    or the tail of a reference looks, so only tables and multi-line blocks count."""
    small = min(a, b, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
    if "table" not in (a.type, b.type) and small.lines < 2:
        return False
    w = min(a.bbox[2], b.bbox[2]) - max(a.bbox[0], b.bbox[0])
    h = min(a.bbox[3], b.bbox[3]) - max(a.bbox[1], b.bbox[1])
    if w <= 0 or h <= 0:
        return False
    smaller = min(
        (a.bbox[2] - a.bbox[0]) * (a.bbox[3] - a.bbox[1]),
        (b.bbox[2] - b.bbox[0]) * (b.bbox[3] - b.bbox[1]),
    )
    return smaller > 0 and w * h > smaller * 0.5


def _captions(page: Page, pattern: re.Pattern) -> int:
    return sum(
        1
        for b in page.content
        if b.type in ("caption", "paragraph", "heading")
        and pattern.match(b.text.strip())
        and _caption_text(b.text.strip())
    )


def _table_problem(rows: list[list[str]] | None) -> bool:
    if not rows or len(rows) < 2 or max(len(r) for r in rows) < 2:
        return True
    if len({len(r) for r in rows}) > 1:
        return True
    cells = [c for r in rows for c in r]
    return sum(1 for c in cells if not c.strip()) > len(cells) * 0.5


# ----------------------------------------------------------------------------- assessment
def assess(doc: Document, reference: dict[int, str] | None = None) -> Fidelity:
    """Check `doc` against itself and, when given, against the source's raw page text
    (`reference_text()`; PDFs only)."""
    signals = {name: Signal() for name in SIGNALS}
    issues = _Issues()
    chars = garbled = 0

    for page in doc.pages:
        output = _page_output(page)
        chars += len(output)
        bad = _garbled(output)
        garbled += bad

        if reference is not None and not page.scanned:
            matched, total = _coverage(reference.get(page.number, ""), output)
            signals["text"].ok += matched
            signals["text"].total += total
            if total >= TEXT_MIN and matched < total * TEXT_WARNING:
                severity = "error" if matched < total * TEXT_ERROR else "warning"
                issues.add(
                    "text_loss",
                    severity,
                    "words on the page are missing from the output",
                    page.number,
                )
        if page.scanned and not any(b.text.strip() for b in page.content):
            issues.add("scanned_no_text", "warning", "scanned page with no OCR text", page.number)

        placed = [b for b in page.content if b.bbox] if not page.scanned else []
        for a, b in zip(placed, placed[1:], strict=False):
            signals["reading_order"].total += 1
            if _backwards(a, b):
                issues.add(
                    "reading_order",
                    "warning",
                    "a block is read after one that sits below it in the same column",
                    page.number,
                )
            else:
                signals["reading_order"].ok += 1
        solid = [b for b in placed if b.type != "figure"]
        for i, a in enumerate(solid):
            for b in solid[i + 1 :]:
                if _overlap(a, b):
                    issues.add(
                        "block_overlap", "warning", "two blocks cover the same area", page.number
                    )

        tables = [b for b in page.content if b.type == "table"]
        for t in tables:
            signals["tables"].total += 1
            if _table_problem(t.rows):
                issues.add(
                    "table_malformed",
                    "warning",
                    "table with a single row/column, ragged rows or mostly empty cells",
                    page.number,
                )
            else:
                signals["tables"].ok += 1
        missing = _captions(page, _TABLE_CAPTION) - len(tables)
        if missing > 0:
            signals["tables"].total += missing
            issues.add(
                "table_not_detected",
                "error",
                "a table caption with no table extracted on the page (it may be an image)",
                page.number,
                missing,
            )

        figures = [b for b in page.content if b.type == "figure"]
        signals["figures"].ok += len(figures)
        signals["figures"].total += len(figures)
        missing = _captions(page, _FIGURE_CAPTION) - len(figures)
        if missing > 0:
            signals["figures"].total += missing
            issues.add(
                "figure_not_detected",
                "warning",
                "a figure caption with no figure extracted on the page",
                page.number,
                missing,
            )

        for f in (b for b in page.content if b.type == "formula"):
            signals["formulas"].total += 1
            if not f.latex or _garbled(f.text + f.latex):
                issues.add(
                    "formula_uncertain",
                    "warning",
                    "formula without LaTeX or with unmapped glyphs",
                    page.number,
                )
            else:
                signals["formulas"].ok += 1

    order = signals["reading_order"]
    if order.total and order.total - order.ok > order.total * ORDER_ERROR:
        issues.found["reading_order"].severity = "error"
    if chars and garbled > chars * GARBLED_WARNING:
        severity = "error" if garbled > chars * GARBLED_ERROR else "warning"
        issues.add(
            "garbled_text",
            severity,
            "characters with no Unicode value in the output",
            count=garbled,
        )
    if doc.pages and not chars:
        issues.add("no_text", "error", "nothing was extracted from the document")
    for warning in doc.warnings:
        code = warning.split(":", 1)[0]
        issues.add(code, "warning", warning.split(":", 1)[-1].strip())

    found = sorted(issues.found.values(), key=lambda i: (i.severity != "error", i.code))
    for issue in found:
        issue.pages.sort()
    weight = sum(_WEIGHTS[n] for n, s in signals.items() if s.total)
    score = (
        sum(_WEIGHTS[n] * s.score for n, s in signals.items() if s.total) / weight
        if weight
        else None
    )
    failed = any(i.severity == "error" for i in found)
    status = "error" if failed else "warning" if found else "ok"
    return Fidelity(status, score, signals, found)
