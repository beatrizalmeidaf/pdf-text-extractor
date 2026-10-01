"""Heuristic cleanup of text extracted from PDFs.

Design rule: only touch lines at the *edges* of a page (where page numbers,
running headers and footers live). Numbers in the body of the text are never
removed, so "Art. 5", "em 2023" or a table column survive intact.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

EDGE_LINES = 2  # how many non-empty lines at the top/bottom of a page count as "edge"

_ROMAN = r"m{0,3}(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})"
_PAGE_NUMBER = re.compile(
    rf"""^\s*
    (?:(?:p[áa]g(?:ina)?|page|p)\.?\s*)?      # "Página", "pág.", "Page", "p."
    [-–—(\[]?\s*
    (?:\d{{1,4}}|(?=[ivxlcdm])(?:{_ROMAN}))   # 12  or  xii
    \s*[-–—)\]]?
    (?:\s*(?:/|de|of)\s*\d{{1,4}})?           # "3/10", "3 de 10", "3 of 10"
    \s*$""",
    re.IGNORECASE | re.VERBOSE,
)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\uffff]")
# PDFium replaces an end-of-line hyphenation ("exem-\nplo") with a marker char
# and joins the word: "exem\x02plo" (or U+FFFE, depending on the call).
_PDFIUM_HYPHEN = re.compile(r"[\x02\ufffe]")
_HYPHEN_BREAK = re.compile(r"(\w)[-\u00ad]\n(?=[a-zà-ÿ])")
_MANY_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class CleanOptions:
    remove_page_numbers: bool = True
    remove_headers_footers: bool = True
    dehyphenate: bool = False
    normalize_whitespace: bool = True


RAW = CleanOptions(
    remove_page_numbers=False,
    remove_headers_footers=False,
    dehyphenate=False,
    normalize_whitespace=False,
)


def is_page_number(line: str) -> bool:
    return bool(line.strip()) and bool(_PAGE_NUMBER.match(line))


def _signature(line: str) -> str:
    """Line fingerprint that ignores digits, so 'Relatório 2024 - pág 3' == '... pág 7'."""
    return re.sub(r"\d+", "#", " ".join(line.lower().split()))


def _edges(lines: list[str]) -> dict[int, int]:
    """Map line index -> edge position (0, 1 from the top; -1, -2 from the bottom).

    Short pages get fewer edge lines so their body text is never treated as a
    header/footer.
    """
    non_empty = [i for i, line in enumerate(lines) if line.strip()]
    k = max(1, min(EDGE_LINES, len(non_empty) // 3))
    edges: dict[int, int] = {}
    for pos, i in enumerate(non_empty[:k]):
        edges[i] = pos
    for pos, i in enumerate(reversed(non_empty[-k:])):
        edges.setdefault(i, -pos - 1)
    return edges


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub("", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return _MANY_BLANK_LINES.sub("\n\n", text).strip("\n")


def clean_pages(pages: list[str], options: CleanOptions = CleanOptions()) -> list[str]:
    """Clean a list of page texts. Returns a list of the same length."""
    marker = "" if options.dehyphenate else "-\n"
    pages = [_PDFIUM_HYPHEN.sub(marker, p) for p in pages]
    if options.normalize_whitespace:
        pages = [_normalize(p) for p in pages]
    split = [p.split("\n") for p in pages]

    repeated: set[tuple[int, str]] = set()
    if options.remove_headers_footers and len(split) >= 3:
        counts: Counter[tuple[int, str]] = Counter()
        for lines in split:
            counts.update({(pos, _signature(lines[i])) for i, pos in _edges(lines).items()})
        threshold = max(3, math.ceil(len(split) * 0.5))
        repeated = {key for key, n in counts.items() if n >= threshold and len(key[1]) >= 3}

    cleaned: list[str] = []
    for lines in split:
        drop: set[int] = set()
        for i, pos in _edges(lines).items():
            page_number = options.remove_page_numbers and is_page_number(lines[i])
            header_footer = bool(repeated) and (pos, _signature(lines[i])) in repeated
            if page_number or header_footer:
                drop.add(i)
        text = "\n".join(line for i, line in enumerate(lines) if i not in drop)
        if options.dehyphenate:
            text = _HYPHEN_BREAK.sub(r"\1", text)
        if options.normalize_whitespace:
            text = _MANY_BLANK_LINES.sub("\n\n", text).strip("\n")
        cleaned.append(text)
    return cleaned
