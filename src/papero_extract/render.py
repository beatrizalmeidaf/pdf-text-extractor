"""Document -> Markdown / plain text / HTML / CSV."""

from __future__ import annotations

import base64
import csv
import html
import io
import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal

from .columns import bands
from .mathtext import inline_latex, latexify, math_spans, script_text
from .model import FURNITURE, Block

if TYPE_CHECKING:
    from .model import Document

ImageMode = Literal["ref", "embed", "none"]
# How math in running text is written: as it reads ("x² + 1 = 0") or as LaTeX ("$x^{2} + 1 = 0$").
MathMode = Literal["unicode", "latex"]


# ----------------------------------------------------------------------------- text
def blocks_to_text(blocks: Iterable[Block], math: MathMode = "unicode") -> str:
    latex = math == "latex"
    parts = []
    for b in blocks:
        text = inline_latex(b.text) if latex and b.type not in ("formula", "code") else b.text
        if b.type == "table" and b.rows:
            parts.append("\n".join("\t".join(c.replace("\n", " ") for c in r) for r in b.rows))
        elif b.type == "list_item":
            parts.append("  " * (b.level or 0) + f"{b.marker or '-'} {text}")
        elif b.type == "formula":
            body = f"$${b.latex or b.text}$$" if latex else b.text
            parts.append(body + (f"  {b.number}" if b.number else ""))
        elif text:
            parts.append(text)
    return "\n\n".join(p for p in parts if p.strip())


def to_text(doc: Document, *, math: MathMode = "unicode") -> str:
    """Plain text in reading order. `math="latex"` writes formulas as `$$…$$` and the math
    inside paragraphs as `$…$`."""
    pages = (blocks_to_text(p.content, math) for p in doc.pages)
    return "\n\n".join(t for t in pages if t.strip())


# ----------------------------------------------------------------------------- markdown
def _md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", "<br>").strip()


def md_table(rows: list[list[str]]) -> str:
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(_md_cell(c) for c in rows[0]) + " |"]
    lines.append("|" + "|".join(["---"] * width) + "|")
    lines += ["| " + " | ".join(_md_cell(c) for c in r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def _image_md(b: Block, images: ImageMode, alt: str) -> str | None:
    if b.image is None or images == "none":
        return None
    if images == "embed":
        data = base64.b64encode(b.image.data).decode("ascii")
        return f"![{alt}](data:{b.image.mime};base64,{data})"
    return f"![{alt}](images/{b.image.name})"


_MD_LIST = re.compile(r"\s*(-|\d+[.)]) ")  # what Markdown reads as a list item
_NUMBER = re.compile(r"^[-+−]?[\d.,%]+$")


def figure_words(text: str) -> list[str]:
    """Words printed inside a figure (legend, axis titles) without the bare tick values:
    useful for search, unlike "0.0 0.2 0.4"."""
    out = []
    for line in text.splitlines():
        kept = " ".join(t for t in line.split() if not _NUMBER.match(t))
        if any(c.isalpha() for c in kept):
            out.append(kept)
    return out


def _emphasis(text: str, bold: bool, italic: bool) -> str:
    """**bold** / *italic* around the words, the spaces at either end left outside."""
    core = text.strip()
    if not core:
        return text
    lead, trail = text[: len(text) - len(text.lstrip())], text[len(text.rstrip()) :]
    if italic:
        core = f"*{core}*"
    if bold:
        core = f"**{core}**"
    return lead + core + trail


def md_inline(b: Block, math: MathMode = "unicode") -> str:
    """Inline formatting as Markdown: **bold**, *italic*, <sup>/<sub>; kept line breaks."""
    if math == "latex":
        return _md_inline_latex(b)
    if not b.runs:
        return b.text.replace("\n", "  \n")
    out = []
    for r in b.runs:
        text = r["text"]
        core = text.strip()
        if not core:
            out.append(text)
            continue
        lead, trail = text[: len(text) - len(text.lstrip())], text[len(text.rstrip()) :]
        t = core.replace("*", "\\*")
        if r.get("script"):
            tag = "sup" if r["script"] == "super" else "sub"
            t = f"<{tag}>{t}</{tag}>"
        out.append(lead + _emphasis(t, bool(r.get("bold")), bool(r.get("italic"))) + trail)
    return "".join(out).replace("\n", "  \n")


def _md_inline_latex(b: Block) -> str:
    """The block with its math as `$…$` (exponents and indices inside it), bold and italic
    kept on the words around."""
    text = ""
    looks: list[tuple[bool, bool]] = []  # (bold, italic) of each character
    for r in b.runs or [{"text": b.text}]:
        t = r["text"]
        if r.get("script"):
            script = script_text(t.strip(), r["script"] == "super")
            t = script + (" " if t[-1:].isspace() else "")
        text += t
        looks += [(bool(r.get("bold")), bool(r.get("italic")))] * len(t)

    def plain(start: int, end: int) -> str:
        out, at = [], start
        for k in range(start, end + 1):
            if k == end or looks[k] != looks[at]:
                piece = text[at:k].replace("*", "\\*").replace("$", "\\$")
                out.append(_emphasis(piece, *looks[at]) if at < k else "")
                at = k
        return "".join(out)

    out, at = [], 0
    for start, end in math_spans(text):
        out.append(plain(at, start) + "$" + latexify(text[start:end]) + "$")
        at = end
    return ("".join(out) + plain(at, len(text))).replace("\n", "  \n")


def html_inline(b: Block) -> str:
    def br(t: str) -> str:
        return html.escape(t).replace("\n", "<br>")

    if not b.runs:
        return br(b.text)
    out = []
    for r in b.runs:
        t = br(r["text"])
        if r.get("script"):
            tag = "sup" if r["script"] == "super" else "sub"
            t = f"<{tag}>{t}</{tag}>"
        if r.get("italic"):
            t = f"<em>{t}</em>"
        if r.get("bold"):
            t = f"<strong>{t}</strong>"
        out.append(t)
    return "".join(out)


def html_style(b: Block) -> str:
    css = []
    if b.align and b.align != "left":
        css.append(f"text-align:{b.align}")
    if b.indent:
        css.append(f"margin-left:{b.indent}pt")
    if b.first_line:
        css.append(f"text-indent:{b.first_line}pt")
    if b.line_spacing:
        css.append(f"line-height:{round(b.line_spacing * 1.15, 2)}")
    if b.tracking:
        css.append(f"letter-spacing:{b.tracking}pt")
    return f' style="{";".join(css)}"' if css else ""


def block_markdown(b: Block, images: ImageMode = "ref", math: MathMode = "unicode") -> str:
    t = b.type
    text = inline_latex(b.text) if math == "latex" else b.text
    if t == "heading":
        return "#" * min(6, max(1, b.level or 2)) + " " + text.replace("\n", " ")
    if t == "list_item":
        marker = b.marker or "-"
        if marker[:1] in "•◦▪▫‣⁃●○■□–—*✓✔➢➤►▶·-":
            marker = "-"
        return "  " * (b.level or 0) + f"{marker} {md_inline(b, math)}"
    if t == "table" and b.rows:
        # The crop of the table stays in JSON/ZIP: repeating it here would duplicate the table.
        return md_table(b.rows)
    if t == "formula":
        latex = b.latex or b.text
        tag = f" \\tag{{{b.number.strip('()')}}}" if b.number else ""
        return f"$$\n{latex}{tag}\n$$"
    if t == "figure":
        alt = (b.caption or "figura").replace("]", ")").replace("\n", " ")[:120]
        img = _image_md(b, images, alt)
        out = img or f"<!-- figura: {alt} -->"
        words = figure_words(b.text)
        if words:
            out += "\n\n" + "\n".join(f"> {ln}" for ln in words)
        return out
    if t == "caption":
        return f"*{text}*"
    if t == "code":
        return f"```\n{b.text}\n```"
    return md_inline(b, math)


def to_markdown(
    doc: Document,
    *,
    images: ImageMode = "ref",
    page_breaks: bool = False,
    furniture: bool = False,
    math: MathMode = "unicode",
) -> str:
    """Markdown in reading order. `images`: "ref" -> images/<name>, "embed" -> data URI.
    `math="latex"` writes the math inside paragraphs as `$…$` instead of <sup>/<sub>."""
    out: list[str] = []
    for page in doc.pages:
        if page_breaks and out:
            out.append(f"<!-- página {page.number} -->")
        blocks = page.blocks if furniture else page.content
        prev: Block | None = None
        for b in blocks:
            md = block_markdown(b, images, math)
            if not md.strip():
                continue
            # Consecutive list items stay tight. "a) …" is not a list to Markdown, which would
            # run such lines together: they end in a hard break.
            if prev is not None and prev.type == "list_item" and b.type == "list_item" and out:
                out[-1] += ("\n" if _MD_LIST.match(md) else "  \n") + md
            else:
                out.append(md)
            prev = b
    return "\n\n".join(out).strip() + "\n"


# ----------------------------------------------------------------------------- html
_HTML_STYLE = """
body{font:16px/1.6 system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem;
color:#1f2328}
section.page{border-top:1px solid #d0d7de;padding-top:1rem;margin-top:2rem}
section.page>h6.page-label{color:#656d76;font-weight:500;margin:0 0 1rem}
table{border-collapse:collapse;margin:1rem 0}
td,th{border:1px solid #d0d7de;padding:.3rem .6rem;vertical-align:top}th{background:#f6f8fa}
figure{margin:1rem 0}figure img{max-width:100%}figcaption{color:#656d76;font-size:.9em}
.formula{overflow-x:auto;padding:.5rem 1rem;background:#f6f8fa;border-radius:6px;
font-family:ui-monospace,monospace}
pre{background:#f6f8fa;padding:1rem;border-radius:6px;overflow-x:auto}
.cols{display:grid;column-gap:1.75rem;align-items:start}.cols>div{min-width:0}
@media(max-width:640px){.cols{display:block}}
"""


def _attrs(b: Block) -> str:
    bbox = ",".join(f"{v:.1f}" for v in b.bbox) if b.bbox else ""
    return f' id="{b.id}" data-type="{b.type}" data-bbox="{bbox}"'


def block_html(b: Block, images: ImageMode = "embed", own_caption: bool = True) -> str:
    """`own_caption`: False when the caption is also a block of its own on the page."""
    e = html.escape
    a = _attrs(b)
    if b.type == "heading":
        lvl = min(6, max(1, b.level or 2))
        return f"<h{lvl}{a}{html_style(b)}>{e(b.text.replace(chr(10), ' '))}</h{lvl}>"
    if b.type == "list_item":
        pad = (b.level or 0) * 1.5
        return f'<p{a} style="margin-left:{pad}rem">{e(b.marker or "•")} {html_inline(b)}</p>'
    if b.type == "table" and b.rows:
        head = "".join(f"<th>{e(c)}</th>" for c in b.rows[0])
        body = "".join(
            "<tr>" + "".join(f"<td>{e(c)}</td>" for c in r) + "</tr>" for r in b.rows[1:]
        )
        cap = f"<caption>{e(b.caption)}</caption>" if b.caption and own_caption else ""
        return f"<table{a}>{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    if b.type == "formula":
        num = f" <span>{e(b.number)}</span>" if b.number else ""
        latex = e(b.latex or "")
        return f'<div class="formula"{a} data-latex="{latex}">\\[{latex or e(b.text)}\\]{num}</div>'
    if b.type == "figure":
        src = ""
        if b.image is not None and images != "none":
            if images == "embed":
                src = f"data:{b.image.mime};base64,{base64.b64encode(b.image.data).decode('ascii')}"
            else:
                src = f"images/{b.image.name}"
        img = f'<img src="{src}" alt="{e(b.caption or "figura")}">' if src else ""
        cap = f"<figcaption>{e(b.caption)}</figcaption>" if b.caption and own_caption else ""
        return f"<figure{a}>{img}{cap}</figure>"
    if b.type == "caption":
        return f"<p{a}{html_style(b)}><em>{html_inline(b)}</em></p>"
    if b.type == "code":
        return f"<pre{a}><code>{e(b.text)}</code></pre>"
    return f"<p{a}{html_style(b)}>{html_inline(b)}</p>"


def to_html(doc: Document, *, images: ImageMode = "embed", title: str | None = None) -> str:
    title = title or doc.metadata.get("title") or "Documento"
    parts = [
        "<!doctype html>",
        '<html lang="pt-BR"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>{html.escape(title)}</title><style>{_HTML_STYLE}</style>",
        "</head><body>",
    ]
    for page in doc.pages:
        parts.append(
            f'<section class="page" data-page="{page.number}" '
            f'data-width="{page.width:.1f}" data-height="{page.height:.1f}">'
            f'<h6 class="page-label">Página {page.number}</h6>'
        )
        blocks = [b for b in page.blocks if b.type not in FURNITURE]
        captions = {b.text for b in blocks if b.type == "caption"}
        # Two columns on the page stay two columns: each multi-column band is a grid.
        for band in bands(blocks):
            cols = [
                [block_html(b, images, b.caption not in captions) for b in c]
                for c in band["blocks"]
            ]
            if len(cols) == 1:
                parts += cols[0]
                continue
            tracks = " ".join(f"{max(1, round(x1 - x0))}fr" for x0, x1 in band["columns"])
            parts.append(f'<div class="cols" style="grid-template-columns:{tracks}">')
            for col in cols:
                parts += ["<div>", *col, "</div>"]
            parts.append("</div>")
        parts.append("</section>")
    parts.append("</body></html>")
    return "\n".join(parts)


# ----------------------------------------------------------------------------- csv
def tables_csv(doc: Document) -> str:
    """Every table, separated by a blank line and a `# página N, tabela K` comment row."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    for k, t in enumerate(doc.tables, 1):
        if k > 1:
            writer.writerow([])
        page = t.id.split("-")[0][1:] if t.id else "?"
        writer.writerow([f"# página {page}, tabela {k}" + (f": {t.caption}" if t.caption else "")])
        writer.writerows(t.rows or [])
    return buf.getvalue()
