"""Math inside running text, as LaTeX: "Se tg x − cotg x = 1, então…" ->
"Se $\\operatorname{tg} x - \\operatorname{cotg} x = 1$, então…".

Many documents set their math in the text font (a Word exam in Times New Roman), so the
font says nothing: a stretch of text is math by what it is made of — an operator between
operands, a function name and its argument, an exponent, a root, a Greek letter. Numbers
and lone letters only join a stretch that has one of those.

Mirrored in `web/assets/mathtext.js` — keep both in sync (tests/js/parity.mjs compares them).
"""

from __future__ import annotations

import re

from .symbols import LATEX, SUBSCRIPT, SUPERSCRIPT, latex_escape, to_subscript, to_superscript

_SUP = {chr(v): chr(k) for k, v in SUPERSCRIPT.items()}  # "²" -> "2"
_SUB = {chr(v): chr(k) for k, v in SUBSCRIPT.items()}
_STRONG_OPS = frozenset("=+−<>≤≥≠≈±×÷·⋅→⇒⇔∈∉⊂⊆∪∩∝≡∼")
_FUNCS = frozenset({
    "sen", "sin", "cos", "tg", "tan", "cotg", "cot", "cossec", "csc", "arcsen", "arcsin",
    "arccos", "arctg", "arctan", "log", "ln", "lim", "mdc", "mmc",
})  # fmt: skip
_LATEX_FUNCS = frozenset({
    "sin", "cos", "tan", "cot", "csc", "arcsin", "arccos", "arctan", "log", "ln", "lim",
})  # fmt: skip
_STOP = frozenset("aeoAEOI")  # one-letter words: a variable only next to an operator
_ASCII_ALNUM = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
_SCRIPTS = frozenset(_SUP) | frozenset(_SUB)
_SYMBOLS = (
    frozenset(LATEX) | _STRONG_OPS | frozenset("^")
)  # operators, Greek, "√"…: math whatever is around
_EXPR_CHARS = _ASCII_ALNUM | _SYMBOLS | _SCRIPTS | frozenset("-()[]|,.'%_/")

_TOKEN = re.compile(r"[^ \n]+")
_NUM = re.compile(r"^[+\-−]?[0-9]+(?:[.,][0-9]+)*%?$")
_COEF = re.compile(r"^[+\-−]?[0-9]+(?:[.,][0-9]+)*[A-Za-z]$")  # "2x"
_IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9]{1,2}$")  # "Mn", "pH": math only beside an operator
_CALL = re.compile(r"^[A-Za-z]\([^()]*\)$")  # "f(x)"
_GROUP = re.compile(r"^\([A-Za-z0-9]+\)$")  # "(x)", "(2)": an argument when math is around it
# Lower-case names set upright; other lower-case letters together are a product: "ax", "mc".
_UNITS = frozenset({
    "mol", "cm", "mm", "km", "dm", "nm", "kg", "mg", "ml", "cal", "atm", "rad", "min", "seg",
})  # fmt: skip
_LETTERS = re.compile(r"[A-Za-z]+")
# A name inside the math ("tg", "mol") — not the letters of an index: "a_(ij)".
_WORD = re.compile(r"(?<![\\A-Za-z])(?<![\^_]\()[A-Za-z]{2,}")
_ROOT = re.compile(r"\\sqrt\s*(\([^()]*\)|[0-9]+|[A-Za-z0-9])")
_SUP_RUN = re.compile("[" + "".join(_SUP) + "]+")
_SUB_RUN = re.compile("[" + "".join(_SUB) + "]+")
_SCRIPT_GROUP = re.compile(r"([\^_])\(([^()]*)\)")
_DECIMAL = re.compile(r"(?<=[0-9]),(?=[0-9])")
_STATE = re.compile(r"\((s|l|ℓ|g|aq|v|c)\)$")  # state of matter, set in the index: "CO2(g)"


def script_text(core: str, up: bool) -> str:
    """A raised or lowered run as text: "2" -> "²" when every character has that form, else
    "^(…)". In an index, the state of matter is written plainly: "2(g)" -> "₂(g)"."""
    state = None if up else _STATE.search(core)
    if state:
        head = core[: state.start()]
        lowered = to_subscript(head) if head else ""
        if lowered is not None:
            return lowered + state.group(0)
    script = to_superscript(core) if up else to_subscript(core)
    if script is not None:
        return script
    return ("^" if up else "_") + (core if len(core) == 1 else f"({core})")


def _balance(piece: str) -> int:
    return sum(piece.count(c) for c in "([") - sum(piece.count(c) for c in ")]")


def _inner(core: str) -> str:
    """A token without the brackets it does not close itself: "(x" -> "x", "f(x)" stays."""
    while core[:1] and core[0] in "([" and _balance(core) > 0:
        core = core[1:]
    while core[-1:] and core[-1] in ")]" and _balance(core) < 0:
        core = core[:-1]
    return core


def _kind(inner: str) -> str:
    if not inner:
        return "word"
    if all(c in _STRONG_OPS for c in inner):
        return "op"
    if inner == "-":
        return "wop"
    if _NUM.match(inner) or _COEF.match(inner):
        return "num"
    if len(inner) == 1:
        if inner in _SYMBOLS:
            return "expr"
        return "var" if inner in _ASCII_ALNUM else "word"
    if inner.lower() in _FUNCS:
        return "func"
    if _GROUP.match(inner):
        return "num"
    if all(c in _EXPR_CHARS for c in inner) and any(c in _ASCII_ALNUM for c in inner):
        if any(c in _SYMBOLS for c in inner) or _CALL.match(inner):
            return "expr"
        # Only an exponent or an index says so: "cm³", "H₂O" — but not "method¹" (a note).
        short = all(len(w) <= 3 for w in _LETTERS.findall(inner))
        if short and any(c in _SCRIPTS for c in inner):
            return "expr"
    return "ident" if _IDENT.match(inner) else "word"


def math_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) of each stretch of math in `text`, in order."""
    tokens = []  # (start, end without the punctuation that follows, kind, the token bare)
    for m in _TOKEN.finditer(text):
        core = m.group().rstrip(",.;:!?")
        inner = _inner(core)
        tokens.append((m.start(), m.start() + len(core), _kind(inner), inner))

    def beside(i: int, j: int) -> str:
        """Kind of token `j` when only spaces separate it from token `i`."""
        if not 0 <= j < len(tokens):
            return ""
        gap = text[tokens[min(i, j)][1] : tokens[max(i, j)][0]]
        return tokens[j][2] if gap and not gap.strip(" ") else ""

    spans = []
    run: list[int] = []

    def close() -> None:
        nonlocal run
        while run and tokens[run[0]][2] == "wop":
            run = run[1:]
        while run and tokens[run[-1]][2] == "wop":
            run = run[:-1]
        kinds = [tokens[i][2] for i in run]
        strong = any(k in ("op", "expr") for k in kinds) or ("func" in kinds and len(kinds) > 1)
        if strong and any(k != "op" for k in kinds):
            start, end = tokens[run[0]][0], tokens[run[-1]][1]
            # A bracket opened or closed outside the stretch stays outside.
            while text[start] in "([" and _balance(text[start:end]) > 0:
                start += 1
            while text[end - 1] in ")]" and _balance(text[start:end]) < 0:
                end -= 1
            spans.append((start, end))
        run = []

    for i, (_start, _end, kind, inner) in enumerate(tokens):
        near = (beside(i, i - 1), beside(i, i + 1))
        if kind == "var" and inner in _STOP:
            mathy = "op" in near or "wop" in near
        elif kind == "ident":
            mathy = "op" in near
        else:
            mathy = kind != "word"
        if run and not near[0]:
            close()  # punctuation or a line break before this token
        if mathy:
            run.append(i)
        else:
            close()
        # "(g·mol⁻¹) Mn = 55": what follows a bracketed group is another matter, unless an
        # operator joins them.
        if run and inner[:1] == "(" and inner[-1:] == ")" and near[1] not in ("op", "wop"):
            close()
    close()
    return spans


def _unbracket(group: str) -> str:
    return group[1:-1] if group.startswith("(") and group.endswith(")") else group


def _name(match: re.Match) -> str:
    word = match.group()
    low = word.lower()
    if low in _LATEX_FUNCS:
        return "\\" + low + " "
    if low in _FUNCS or word in _UNITS or word != low:  # "tg", "mol", "Mn", "mmHg"
        return "\\operatorname{" + word + "}"
    return word


def latexify(piece: str) -> str:
    """A stretch of math, as text, to LaTeX: "10⁶" -> "10^{6}", "tg x" -> "\\operatorname{tg} x"."""
    out = _WORD.sub(_name, latex_escape(piece))
    out = _ROOT.sub(lambda m: "\\sqrt{" + _unbracket(m.group(1)) + "}", out)
    out = _SUP_RUN.sub(lambda m: "^{" + "".join(_SUP[c] for c in m.group()) + "}", out)
    out = _SUB_RUN.sub(lambda m: "_{" + "".join(_SUB[c] for c in m.group()) + "}", out)
    out = _SCRIPT_GROUP.sub(lambda m: m.group(1) + "{" + m.group(2) + "}", out)
    out = _DECIMAL.sub("{,}", out)
    return re.sub(r" +", " ", out).strip()


def inline_latex(text: str) -> str:
    """`text` with each stretch of math written as `$…$`."""
    out = []
    at = 0
    for start, end in math_spans(text):
        out.append(text[at:start] + "$" + latexify(text[start:end]) + "$")
        at = end
    return "".join(out) + text[at:]
