"""Symbol handling: ligatures, private-use bullets, math detection and Unicode→LaTeX.

The same tables are mirrored in `docs/assets/engine.js` (browser engine) — keep
them in sync.
"""

from __future__ import annotations

import unicodedata

LIGATURES = {
    chr(0xFB00): "ff",
    chr(0xFB01): "fi",
    chr(0xFB02): "fl",
    chr(0xFB03): "ffi",
    chr(0xFB04): "ffl",
    chr(0xFB05): "st",
    chr(0xFB06): "st",
}

# Symbol and Wingdings fonts put their glyphs in the Private Use Area (U+F000 + code).
# The same code means different glyphs in each font, so the mapping depends on it.
_SYMBOL_FONT = dict(
    zip(
        map(ord, "abcdefghijklmnopqrstuvwxyzADFGLPQSWXY"),
        "αβχδεφγηιϕκλμνοπθρστυϖωξψζΑΔΦΓΛΠΘΣΩΞΨ",
        strict=True,
    )
)
_SYMBOL_FONT.update({
    0xB7: "•", 0xB1: "±", 0xA3: "≤", 0xB3: "≥", 0xB9: "≠", 0xBB: "≈", 0xA5: "∞",
    0xE5: "∑", 0xF2: "∫", 0xD6: "√", 0xB4: "×", 0xB8: "÷", 0xAE: "→", 0xAC: "←",
    0xAB: "↔", 0xDE: "⇒", 0xDB: "⇔", 0xB6: "∂", 0xD1: "∇", 0xCE: "∈", 0xCF: "∉",
    0xC7: "∩", 0xC8: "∪", 0xC6: "∅", 0xCC: "⊂", 0xC9: "⊃", 0xCD: "⊆", 0xCA: "⊇",
    0xD8: "¬", 0xD9: "∧", 0xDA: "∨", 0x22: "∀", 0x24: "∃", 0x2D: "−", 0xBC: "…",
    0xA2: "′", 0xB2: "″", 0xB0: "°", 0xBA: "≡", 0xB5: "∝", 0x40: "≅", 0x7E: "∼",
    0xC5: "⊕", 0xC4: "⊗", 0xE1: "⟨", 0xF1: "⟩", 0xD5: "∏",
})  # fmt: skip
_WINGDINGS = {
    0x6C: "●", 0x6D: "○", 0x6E: "■", 0x6F: "□", 0x71: "❑", 0x75: "◆", 0x76: "❖",
    0x77: "⬥", 0xA7: "▪", 0xA8: "◻", 0x9F: "•", 0xD8: "➢", 0xFC: "✓", 0xFB: "✗",
    0xE0: "→", 0xE8: "➔", 0xF0: "⇨",
}  # fmt: skip
PUA_SYMBOL = {chr(0xF000 + k): v for k, v in _SYMBOL_FONT.items()}
PUA_WINGDINGS = {chr(0xF000 + k): v for k, v in _WINGDINGS.items()}

BULLETS = set("•◦▪▫‣⁃●○■□–—-*✓✔➢➤►▶·")

GREEK = {
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta", "ε": r"\epsilon",
    "ϵ": r"\epsilon", "ζ": r"\zeta", "η": r"\eta", "θ": r"\theta", "ϑ": r"\vartheta",
    "ι": r"\iota", "κ": r"\kappa", "λ": r"\lambda", "μ": r"\mu", "ν": r"\nu", "ξ": r"\xi",
    "π": r"\pi", "ϖ": r"\varpi", "ρ": r"\rho", "σ": r"\sigma", "ς": r"\varsigma",
    "τ": r"\tau", "υ": r"\upsilon", "φ": r"\phi", "ϕ": r"\phi", "χ": r"\chi", "ψ": r"\psi",
    "ω": r"\omega", "Γ": r"\Gamma", "Δ": r"\Delta", "Θ": r"\Theta", "Λ": r"\Lambda",
    "Ξ": r"\Xi", "Π": r"\Pi", "Σ": r"\Sigma", "Υ": r"\Upsilon", "Φ": r"\Phi",
    "Ψ": r"\Psi", "Ω": r"\Omega",
}  # fmt: skip

OPERATORS = {
    "∑": r"\sum", "∏": r"\prod", "∐": r"\coprod", "∫": r"\int", "∬": r"\iint",
    "∭": r"\iiint", "∮": r"\oint", "√": r"\sqrt", "∂": r"\partial", "∇": r"\nabla",
    "∞": r"\infty", "±": r"\pm", "∓": r"\mp", "×": r"\times", "÷": r"\div", "·": r"\cdot",
    "⋅": r"\cdot", "∘": r"\circ", "≤": r"\leq", "≥": r"\geq", "≠": r"\neq", "≈": r"\approx",
    "≡": r"\equiv", "≅": r"\cong", "∼": r"\sim", "∝": r"\propto", "≪": r"\ll", "≫": r"\gg",
    "∈": r"\in", "∉": r"\notin", "∋": r"\ni", "⊂": r"\subset", "⊃": r"\supset",
    "⊆": r"\subseteq", "⊇": r"\supseteq", "∪": r"\cup", "∩": r"\cap", "∅": r"\emptyset",
    "∀": r"\forall", "∃": r"\exists", "∄": r"\nexists", "¬": r"\neg", "∧": r"\wedge",
    "∨": r"\vee", "⊕": r"\oplus", "⊗": r"\otimes", "→": r"\to", "←": r"\leftarrow",
    "↔": r"\leftrightarrow", "⇒": r"\Rightarrow", "⇐": r"\Leftarrow", "⇔": r"\Leftrightarrow",
    "↦": r"\mapsto", "ℝ": r"\mathbb{R}", "ℕ": r"\mathbb{N}", "ℤ": r"\mathbb{Z}",
    "ℚ": r"\mathbb{Q}", "ℂ": r"\mathbb{C}", "ℓ": r"\ell", "ℏ": r"\hbar", "′": "'",
    "″": "''", "−": "-", "∗": "*", "…": r"\ldots", "⋯": r"\cdots", "⌊": r"\lfloor",
    "⌋": r"\rfloor", "⌈": r"\lceil", "⌉": r"\rceil", "⟨": r"\langle", "⟩": r"\rangle",
    "‖": r"\|", "°": r"^{\circ}",
}  # fmt: skip

LATEX = {**GREEK, **OPERATORS}
# Characters that, on their own, strongly suggest mathematical content.
MATH_CHARS = set(OPERATORS) | set(GREEK) | set("=+<>")
# Math fonts: TeX Computer Modern math/symbol/extension, STIX, Cambria Math, Symbol…
MATH_FONT_HINTS = (
    "cmmi",
    "cmsy",
    "cmex",
    "msbm",
    "msam",
    "math",
    "stix",
    "symbol",
    "mtmi",
    "mtsy",
    "rsfs",
    "esint",
)

SUPERSCRIPT = str.maketrans(
    "0123456789+-=()niabcdehijklmoprstuvwxyz", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱᵃᵇᶜᵈᵉʰⁱʲᵏˡᵐᵒᵖʳˢᵗᵘᵛʷˣʸᶻ"
)
SUBSCRIPT = str.maketrans("0123456789+-=()aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ")
_SUP_OK = set("0123456789+-=()niabcdehijklmoprstuvwxyz")
_SUB_OK = set("0123456789+-=()aehijklmnoprstuvx")


# Written as code points on purpose: these characters are invisible in an editor.
_SPACES = frozenset(map(chr, (0xA0, *range(0x2000, 0x200B), 0x202F, 0x205F, 0x3000)))
_INVISIBLE = frozenset(map(chr, (0xAD, 0x200B, 0x200C, 0x200D, 0xFEFF)))  # soft hyphen, ZW*
_PUA_FONT_START, _PUA_FONT_END = chr(0xF000), chr(0xF0FF)


def normalize_char(ch: str, font: str = "") -> str:
    """Ligatures -> letters, Symbol/Wingdings glyphs -> real symbols, odd spaces -> space."""
    if ch in LIGATURES:
        return LIGATURES[ch]
    if _PUA_FONT_START <= ch <= _PUA_FONT_END:
        first, second = (PUA_SYMBOL, PUA_WINGDINGS)
        if "wingding" in font.lower():
            first, second = second, first
        return first.get(ch) or second.get(ch) or ch
    if ch in _SPACES:
        return " "
    if ch in _INVISIBLE:
        return ""
    return ch


def is_math_font(name: str) -> bool:
    low = name.lower()
    return any(h in low for h in MATH_FONT_HINTS)


def math_score(text: str) -> float:
    """Share of non-space chars that are math symbols (0..1)."""
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    return sum(c in MATH_CHARS for c in chars) / len(chars)


def to_superscript(text: str) -> str | None:
    t = text.strip()
    return t.translate(SUPERSCRIPT) if t and all(c in _SUP_OK for c in t) else None


def to_subscript(text: str) -> str | None:
    t = text.strip()
    return t.translate(SUBSCRIPT) if t and all(c in _SUB_OK for c in t) else None


def latex_escape(text: str) -> str:
    out = []
    for ch in text:
        if ch in LATEX:
            cmd = LATEX[ch]
            out.append(cmd + (" " if cmd[-1].isalpha() else ""))
        elif ch in "{}" or ch in "%#&$":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out).replace("  ", " ")


def strip_accents_lower(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c)
    )


# Accents drawn as their own glyph (TeX OT1 fonts, some Word exports): "Computa¸ca˜o".
# Spacing accent -> combining mark. ASCII ^ ` ~ are left alone: in code and math they
# are real characters.
SPACING_ACCENTS = {
    chr(0x00B4): chr(0x0301), chr(0x02CA): chr(0x0301), chr(0x02CB): chr(0x0300),
    chr(0x02DC): chr(0x0303), chr(0x02C6): chr(0x0302), chr(0x00A8): chr(0x0308),
    chr(0x00B8): chr(0x0327), chr(0x02DA): chr(0x030A), chr(0x02C7): chr(0x030C),
    chr(0x02D8): chr(0x0306), chr(0x02D9): chr(0x0307), chr(0x00AF): chr(0x0304),
    chr(0x02C9): chr(0x0304), chr(0x02DD): chr(0x030B), chr(0x02DB): chr(0x0328),
}  # fmt: skip
SPACING_ACCENTS.update({chr(c): chr(c) for c in range(0x0300, 0x0370)})  # lone combining marks
BELOW_ACCENTS = frozenset({chr(0x0327), chr(0x0328)})  # cedilla, ogonek: drawn under the letter


def compose_accent(base: str, accent: str) -> str | None:
    """'c' + '¸' -> 'ç'. None when there is no single precomposed character."""
    mark = SPACING_ACCENTS.get(accent)
    if mark is None or not base or not base[-1].isalpha():
        return None
    composed = unicodedata.normalize("NFC", base[-1] + mark)
    return base[:-1] + composed if len(composed) == 1 else None
