"""Draws benchmarks/latency.svg: average time per PDF, as a dot plot on a log scale.

A dot plot, not bars: on a log axis a bar's length starts from an arbitrary floor and
misleads; the dot's position is the value. The SVG follows the reader's light/dark theme.

    python benchmarks/plot_latency.py
"""

import math
from pathlib import Path

ROWS = [  # (name, what it returns, mean ms per PDF, is papero) — run_massive_benchmark.py
    ("PyMuPDF", "raw text", 97.2, False),
    ("papero · fast", "clean text (Tika)", 135.6, True),
    ("papero · structured", "order, tables, formulas, figures", 542.6, True),
    ("pypdf", "raw text", 1520.2, False),
    ("pdfplumber", "text + tables", 3555.9, False),
    ("Docling", "ML layout models", 82880.4, False),
]


def fmt(ms: float) -> str:
    if ms < 1000:
        return f"{ms:.0f} ms"
    return f"{ms / 1000:.2f} s" if ms < 10_000 else f"{ms / 1000:.1f} s"


def main() -> None:
    w, left, right, top, row_h = 760, 250, 110, 74, 40
    h = top + row_h * len(ROWS) + 46
    lo, hi = math.log10(50), math.log10(150_000)

    def x(ms: float) -> float:
        return left + (math.log10(ms) - lo) / (hi - lo) * (w - left - right)

    style = (
        ".bg{fill:#ffffff}.ink,.val{fill:#1f2328}.sub{fill:#656d76}.grid{stroke:#d8dee4}"
        ".dot{fill:#6b7280}.dot.p{fill:#c2410c}.stem{stroke:#d0d7de}.stem.p{stroke:#f6c7a8}"
        ".ring{stroke:#ffffff}"
        "@media (prefers-color-scheme: dark){.bg{fill:#0d1117}.ink,.val{fill:#e6edf3}"
        ".sub{fill:#8d96a0}.grid{stroke:#262c33}.dot{fill:#9ca3af}.dot.p{fill:#fb923c}"
        ".stem{stroke:#30363d}.stem.p{stroke:#7c3a12}.ring{stroke:#0d1117}}"
    )
    desc = "; ".join(f"{n}: {fmt(v)}" for n, _, v, _ in ROWS)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        'role="img" aria-labelledby="t d" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
        '<title id="t">Average extraction time per PDF</title>',
        f'<desc id="d">{desc}. Dense arXiv papers, CPU only, log scale.</desc>',
        f"<style>{style}</style>",
        f'<rect class="bg" width="{w}" height="{h}" rx="12"/>',
        '<text class="ink" x="24" y="34" font-size="18" font-weight="650">'
        "Average extraction time per PDF</text>",
        '<text class="sub" x="24" y="56" font-size="13">'
        "50+ dense arXiv papers · CPU only · no GPU · lower is better · log scale</text>",
    ]
    for ms, label in ((100, "100 ms"), (1000, "1 s"), (10_000, "10 s"), (100_000, "100 s")):
        out.append(
            f'<line class="grid" x1="{x(ms):.1f}" y1="{top - 10}" x2="{x(ms):.1f}" '
            f'y2="{top + row_h * len(ROWS) - 6}" stroke-width="1"/>'
        )
        out.append(
            f'<text class="sub" x="{x(ms):.1f}" y="{top + row_h * len(ROWS) + 12}" '
            f'font-size="12" text-anchor="middle">{label}</text>'
        )
    for i, (name, detail, ms, mine) in enumerate(ROWS):
        y = top + row_h * i + 14
        c, weight = (" p", 650) if mine else ("", 500)
        out += [
            f'<text class="ink" x="24" y="{y - 2}" font-size="14" font-weight="{weight}">{name}</text>',
            f'<text class="sub" x="24" y="{y + 14}" font-size="12">{detail}</text>',
            f'<line class="stem{c}" x1="{x(50):.1f}" y1="{y + 4}" x2="{x(ms):.1f}" y2="{y + 4}" '
            'stroke-width="2" stroke-linecap="round"/>',
            f'<circle class="dot{c} ring" cx="{x(ms):.1f}" cy="{y + 4}" r="7" stroke-width="2"/>',
            f'<text class="val" x="{x(ms) + 14:.1f}" y="{y + 9}" font-size="13" '
            f'font-weight="{weight}">{fmt(ms)}</text>',
        ]
    out.append(
        f'<text class="sub" x="24" y="{h - 12}" font-size="11">Docling: ~83 s per paper on CPU. '
        "papero · structured analyses the layout of every page (54 papers, same machine).</text>"
    )
    out.append("</svg>")
    path = Path(__file__).with_name("latency.svg")
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
