"""Text columns of a page, from block boxes alone.

A gutter is a vertical strip that (almost) no text crosses, with text on both sides; a
title or figure spanning the columns may cross it. Both the layout pass (alignment and
indents are measured against the block's own column) and the exporters (two columns on
the page become two columns in HTML and Word) use this, so it only needs bboxes.
"""

from __future__ import annotations

from collections.abc import Sequence

Box = Sequence[float]
STEP = 2.0  # pt per coverage bin
MIN_GUTTER = 6.0  # pt


def gutters(boxes: Sequence[Box]) -> list[tuple[float, float]]:
    if len(boxes) < 3:
        return []
    left = min(b[0] for b in boxes)
    right = max(b[2] for b in boxes)
    n = int((right - left) / STEP) + 1
    if n < 20:
        return []
    # How much text height crosses each strip. Blocks as wide as the page (a table and a
    # figure over two short columns of text) say nothing about a gutter: they are counted
    # apart, only to tell how much of the page the columns are.
    cover = [0.0] * n
    everything = [0.0] * n
    for x0, y0, x1, y1 in boxes:
        wide = x1 - x0 > (right - left) * 0.6
        for k in range(max(0, int((x0 - left) / STEP) + 1), min(n, int((x1 - left) / STEP))):
            everything[k] += y1 - y0
            if not wide:
                cover[k] += y1 - y0
    peak = max(cover)
    if peak <= 0:
        return []
    whole = max(everything)
    out = []
    k = 0
    while k < n:
        if cover[k] > peak * 0.4:
            k += 1
            continue
        j = k
        while j < n and cover[j] <= peak * 0.4:
            j += 1
        # The valley floor: what crosses it is only titles, figures… spanning the columns.
        floor = min(cover[k:j])
        a = k
        while a < j:
            if cover[a] > floor + peak * 0.02:
                a += 1
                continue
            b = a
            while b < j and cover[b] <= floor + peak * 0.02:
                b += 1
            if (
                a > 0
                and b < n
                and (b - a) * STEP >= MIN_GUTTER
                and min(max(cover[:a]), max(cover[b:])) >= max(peak, whole * 0.6) * 0.15
                and floor <= min(max(cover[:a]), max(cover[b:])) * 0.4
            ):
                out.append((left + a * STEP, left + b * STEP))
            a = b
        k = j
    return out


def columns(boxes: Sequence[Box]) -> list[tuple[float, float]]:
    """Left/right edge of each column (one column when there is no gutter)."""
    if not boxes:
        return []
    cuts = gutters(boxes)
    left = min(b[0] for b in boxes)
    right = max(b[2] for b in boxes)
    mids = [(g[0] + g[1]) / 2 for g in cuts]
    out = []
    for lo, hi in zip([left - 1] + mids, mids + [right + 1], strict=True):
        inside = [b for b in boxes if b[0] >= lo and b[2] <= hi]
        out.append((min(b[0] for b in inside), max(b[2] for b in inside)) if inside else (lo, hi))
    return out


def column_of(box: Box, cols: Sequence[tuple[float, float]]) -> int | None:
    """Index of the column the box sits in; None when it spans more than one."""
    hits = [i for i, (lo, hi) in enumerate(cols) if min(box[2], hi) - max(box[0], lo) > 1]
    if len(hits) == 1:
        return hits[0]
    if not hits:  # in a gutter: the nearest column
        mid = (box[0] + box[2]) / 2
        return min(range(len(cols)), key=lambda i: abs((cols[i][0] + cols[i][1]) / 2 - mid))
    return None


def area_of(box: Box, cols: Sequence[tuple[float, float]]) -> tuple[float, float]:
    """The text area a block lays out against: its column, or the columns it spans."""
    i = column_of(box, cols)
    if i is not None:
        return cols[i]
    hits = [c for c in cols if min(box[2], c[1]) - max(box[0], c[0]) > 1]
    return hits[0][0], hits[-1][1]


def bands(blocks: list, bbox=lambda b: b.bbox, kind=lambda b: b.type) -> list[dict]:
    """Split a page's blocks (in reading order) into horizontal bands: full-width runs and
    multi-column runs, each column keeping its blocks in reading order.

    -> [{"columns": [(x0, x1), ...], "blocks": [[...], [...]]}]
    """
    # Figures don't count: a grid of pictures has gaps that are not gutters.
    cols = columns([bbox(b) for b in blocks if bbox(b) and kind(b) != "figure"])
    if len(cols) < 2:
        return [{"columns": cols, "blocks": [list(blocks)]}] if blocks else []
    out: list[dict] = []
    for b in blocks:
        box = bbox(b)
        i = column_of(box, cols) if box else (0 if out and len(out[-1]["blocks"]) > 1 else None)
        if i is None:
            if not out or len(out[-1]["blocks"]) > 1:
                out.append({"columns": [(cols[0][0], cols[-1][1])], "blocks": [[]]})
            out[-1]["blocks"][0].append(b)
        else:
            if not out or len(out[-1]["blocks"]) == 1:
                out.append({"columns": list(cols), "blocks": [[] for _ in cols]})
            out[-1]["blocks"][i].append(b)
    return out
