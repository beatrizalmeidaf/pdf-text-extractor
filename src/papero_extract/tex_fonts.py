"""TeX math fonts without a ToUnicode map.

pdfTeX and dvips write Computer Modern glyphs with their TeX font encoding as the character
code, and many papers ship no ToUnicode table. A reader then sees the raw code: "ϵ" comes out
as control character 0x0F, "≠" as "6=", "⟨x, y⟩" as "hx, yi", "∫" as "Z". These tables are the
encodings (OML, OMS, OMX, OT1), so the code can be turned back into the symbol.

Only valid when the PDF was written by TeX itself (see `is_tex_producer`): other producers
(IEEE Xplore's, for one) renumber the glyphs of a subset font.

PDFium already resolves the glyphs whose PostScript name it knows ("minus", "alpha",
"braceleft"…) and hands over the raw code only for the others ("epsilon1", "negationslash",
"parenleftbigg"…). So a code is mapped only where the font has no glyph that could
legitimately produce that character: "{" from cmsy is a real brace, "h" is "⟨".
"""

from __future__ import annotations

import re

NOT = chr(0x338)  # combining slash: TeX draws "≠" as a slash followed by "="
NEGATED = dict(zip("=∈∋≡∼≃≈⊂⊃⊆⊇<>≤≥∃|‖→←⇒⇔≺≻", "≠∉∌≢≁≄≉⊄⊅⊈⊉≮≯≰≱∄∤∦↛↚⇏⇎⊀⊁", strict=True))

_TEX_PRODUCER = re.compile(r"pdftex|luatex|xetex|dvips|dvipdfm", re.IGNORECASE)


def is_tex_producer(producer: str) -> bool:
    return bool(_TEX_PRODUCER.search(producer or ""))


def _table(*rows: tuple[int, list[str] | str]) -> dict[int, str]:
    out: dict[int, str] = {}
    for start, glyphs in rows:
        for k, g in enumerate(glyphs):
            out[start + k] = g
    return out


_GREEK_CAPS = "ΓΔΘΛΞΠΣΥΦΨΩ"

# Math italic (cmmi): Greek, then a few symbols where ASCII punctuation would be.
OML = _table(
    (0x00, _GREEK_CAPS + "αβγδϵζηθικλμνξπρστυϕχψωεϑϖϱςφ"),
    (0x28, ["↼", "↽", "⇀", "⇁", "", "", "▷", "◁"]),
    (0x3A, [".", ",", "<", "/", ">", "⋆", "∂"]),
    (0x5B, ["♭", "♮", "♯", "⌣", "⌢", "ℓ"]),
    (0x7B, ["ı", "ȷ", "℘", "", ""]),
)

# Math symbols (cmsy). 0x41-0x5A are the calligraphic capitals: left alone.
OMS = _table(
    (0x00, "−·×∗÷⋄±∓⊕⊖⊗⊘⊙○∘•"),
    (0x10, "≍≡⊆⊇≤≥⪯⪰∼≈⊂⊃≪≫≺≻"),
    (0x20, "←→↑↓↔↗↘≃⇐⇒⇑⇓⇔↖↙∝"),
    (0x30, ["′", "∞", "∈", "∋", "△", "▽", NOT, "", "∀", "∃", "¬", "∅", "ℜ", "ℑ", "⊤", "⊥", "ℵ"]),
    (0x5B, "∪∩⊎∧∨"),
    (0x60, "⊢⊣⌊⌋⌈⌉{}⟨⟩|‖↕⇕\\≀"),
    (0x70, "√⨿∇∫⊔⊓⊑⊒§†‡¶♣♢♡♠"),
)

# Math extension (cmex): big delimiters and operators. Wide accents and the pieces of
# horizontal braces carry no text.
OMX = _table(
    (0x00, "()[]⌊⌋⌈⌉{}⟨⟩|‖/\\"),
    (0x10, "()()[]⌊⌋⌈⌉{}⟨⟩/\\"),
    (0x20, "()[]⌊⌋⌈⌉{}⟨⟩/\\/\\"),
    (0x30, ["⎛", "⎞", "⎡", "⎤", "⎣", "⎦", "⎢", "⎥", "⎧", "⎫", "⎩", "⎭", "⎨", "⎬", "⎪", ""]),
    (0x40, "⎝⎠⎜⎟⟨⟩⊔⊔∮∮⊙⊙⊕⊕⊗⊗"),
    (0x50, "∑∏∫⋃⋂⊎⋀⋁∑∏∫⋃⋂⊎⋀⋁"),
    (0x60, ["∐", "∐", "", "", "", "", "", "", "[", "]", "⌊", "⌋", "⌈", "⌉", "{", "}"]),
    (0x70, ["√", "√", "√", "√", "√", "", "", "", "", "", "", "", "", "", "", ""]),
)

ENCODINGS = {"oml": OML, "oms": OMS, "omx": OMX}
_FAMILY = (
    (re.compile(r"^(cmmi|cmmib|lmmi|lmmathitalic)"), "oml"),
    (re.compile(r"^(cmsy|cmbsy|lmsy|lmmathsymbols)"), "oms"),
    (re.compile(r"^(cmex|lmex|lmmathextension)"), "omx"),
)
# Codes that can only be raw: no glyph of the font maps to these characters by name.
_OML_RAW = frozenset({*range(0x20), 0x24, 0x25, 0x28, 0x29, 0x2A, 0x2B, 0x60, 0x7C, 0x7E, 0x7F})
_OMS_RAW = frozenset({*range(0x20), *range(0x21, 0x41), *range(0x61, 0x7B)})


def tex_encoding(font_name: str) -> str:
    """'ABCDEF+CMSY10' -> 'oms'; '' for a font that is not one of TeX's."""
    base = font_name.split("+")[-1].lower()
    for pattern, enc in _FAMILY:
        if pattern.match(base):
            return enc
    return ""


def tex_char(code: int, encoding: str) -> str | None:
    """The symbol behind a raw character code, '' for a glyph that carries no text, or None
    when the code already is what it looks like."""
    if (encoding == "oml" and code not in _OML_RAW) or (encoding == "oms" and code not in _OMS_RAW):
        return None
    return ENCODINGS[encoding].get(code)
