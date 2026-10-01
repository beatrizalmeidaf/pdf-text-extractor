"""Document -> chunks for retrieval (RAG), cut where the document's own structure cuts.

A chunk never crosses a heading, a table is always a chunk of its own (with its caption),
and paragraphs are packed up to `max_chars`. Each chunk says where it came from: the
section path, the pages and the ids of its blocks (so a hit can be shown on the page).

>>> from papero_extract import extract
>>> from papero_extract.chunks import chunk_document
>>> chunk_document(extract("artigo.pdf"), document="artigo.pdf")[0]
{'id': 'artigo.pdf#0', 'type': 'text', 'headings': ['Introduction'], 'pages': [1, 1], ...}
"""

from __future__ import annotations

from .model import Document
from .render import block_markdown, figure_words


def chunk_document(doc: Document, *, document: str = "", max_chars: int = 1500) -> list[dict]:
    chunks: list[dict] = []
    headings: list[tuple[int, str]] = []  # (level, text) of the section we are in
    parts: list[str] = []
    blocks: list[str] = []
    pages: list[int] = []
    size = 0
    body = False  # something under the heading
    last = ""  # type of the previous block in `parts`

    def emit(kind: str, text: str, ids: list[str], on: list[int]) -> None:
        chunks.append(
            {
                "id": f"{document}#{len(chunks)}",
                "document": document,
                "index": len(chunks),
                "type": kind,
                "headings": [t for _, t in headings],
                "pages": [min(on), max(on)],
                "blocks": ids,
                "chars": len(text),
                "text": text,
            }
        )

    def flush() -> None:
        nonlocal parts, blocks, pages, size, body, last
        # A heading with nothing under it is not worth a chunk: it is in the next one's path.
        if body:
            emit("text", "\n\n".join(parts), blocks, pages)
        parts, blocks, pages, size, body, last = [], [], [], 0, False, ""

    for page in doc.pages:
        linked = {b.caption for b in page.content if b.type == "table" and b.caption}
        for b in page.content:
            if b.type == "heading":
                flush()
                level = b.level or 2
                headings[:] = [h for h in headings if h[0] < level]
                headings.append((level, b.text.replace("\n", " ")))
            elif b.type == "table" and b.rows:
                flush()
                text = block_markdown(b, "none")
                if b.caption:
                    text = f"{b.caption}\n\n{text}"
                emit("table", text, [b.id], [page.number])
                continue
            elif b.type == "caption" and b.text in linked:
                continue  # already at the top of its table's chunk
            if b.type == "figure":
                text = "\n".join(figure_words(b.text))  # legend and axis titles, for search
            else:
                text = block_markdown(b, "none")
            if not text.strip():
                continue
            if size and size + len(text) > max_chars:
                flush()
            # Consecutive list items stay tight, as in the Markdown export.
            if b.type == "list_item" and last == "list_item":
                parts[-1] += "\n" + text
            else:
                parts.append(text)
            body = body or b.type != "heading"
            last = b.type
            blocks.append(b.id)
            pages.append(page.number)
            size += len(text)
    flush()
    return chunks
