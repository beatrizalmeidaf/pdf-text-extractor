"""Synthetic PDFs that exercise the layout engine (generated with fpdf2)."""

from __future__ import annotations

import os
from pathlib import Path

from fpdf import FPDF

LOREM = (
    "A extração estruturada de documentos preserva a ordem de leitura, as tabelas e as "
    "fórmulas, o que melhora a qualidade das respostas de sistemas de busca semântica."
)

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]


def unicode_font() -> str | None:
    for path in [os.environ.get("PTE_TEST_FONT", ""), *_FONT_CANDIDATES]:
        if path and os.path.isfile(path):
            return path
    return None


def _pdf() -> tuple[FPDF, str]:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(False)
    font = unicode_font()
    if font:
        pdf.add_font("U", "", font)
        bold = font.replace("arial.ttf", "arialbd.ttf").replace(
            "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"
        )
        pdf.add_font("U", "B", bold if os.path.isfile(bold) else font)
        return pdf, "U"
    return pdf, "Helvetica"


def structured_pdf(path: Path) -> Path:
    """Title, headings, a list, a ruled table, a formula with sub/superscripts, a figure."""
    pdf, F = _pdf()
    for n in (1, 2, 3):
        pdf.add_page()
        pdf.set_font(F, size=8)
        pdf.set_xy(20, 8)
        pdf.cell(0, 5, "Relatório Técnico 2026 — Laboratório Exemplo")
        pdf.set_xy(0, 285)
        pdf.cell(210, 5, str(n), align="C")
        if n == 1:
            pdf.set_font(F, "B", 22)
            pdf.set_xy(20, 22)
            pdf.cell(0, 10, "Extração Estruturada")
            pdf.set_font(F, "B", 15)
            pdf.set_xy(20, 38)
            pdf.cell(0, 8, "1 Introdução")
            pdf.set_font(F, size=11)
            pdf.set_xy(20, 48)
            pdf.multi_cell(170, 5.5, LOREM + " " + LOREM)
            pdf.set_xy(20, 68)
            for k, item in enumerate(
                ["Primeiro item da lista", "Segundo item da lista", "Terceiro item"]
            ):
                pdf.set_xy(25, 68 + k * 6)
                pdf.cell(0, 5.5, f"{k + 1}. {item}")
            pdf.set_font(F, "B", 15)
            pdf.set_xy(20, 92)
            pdf.cell(0, 8, "2 Resultados")
            # Ruled table
            pdf.set_font(F, size=10)
            data = [
                ["Modelo", "Precisão", "Latência (ms)"],
                ["Base", "0,81", "120"],
                ["Proposto", "0,93", "14"],
                ["Ablação", "0,88", "22"],
            ]
            pdf.set_xy(20, 104)
            for row in data:
                for cell in row:
                    pdf.cell(50, 7, cell, border=1)
                pdf.ln(7)
                pdf.set_x(20)
            pdf.set_font(F, size=10)
            pdf.set_xy(20, 134)
            pdf.cell(0, 5, "Tabela 1: Comparação entre modelos.")
        if n == 2:
            pdf.set_font(F, "B", 15)
            pdf.set_xy(20, 22)
            pdf.cell(0, 8, "3 Método")
            pdf.set_font(F, size=11)
            pdf.set_xy(20, 34)
            pdf.multi_cell(170, 5.5, LOREM)
            # Formula: E = mc² with a real superscript, and a sum with a subscript.
            y = 56
            if F == "U":
                pdf.set_font(F, size=13)
                pdf.set_xy(80, y)
                width = pdf.get_string_width("E = mc")
                pdf.cell(width, 7, "E = mc")
                pdf.set_font(F, size=8)
                pdf.set_xy(80 + width - pdf.c_margin + 0.3, y - 1.8)
                pdf.cell(4, 5, "2")
                pdf.set_font(F, size=13)
                pdf.set_xy(170, y)
                pdf.cell(12, 7, "(1)")
                pdf.set_xy(80, y + 12)
                pdf.cell(40, 7, "S = ∑ α · x ≤ β")
            # Figure: an embedded raster image.
            from PIL import Image, ImageDraw

            img = Image.new("RGB", (240, 140), "white")
            draw = ImageDraw.Draw(img)
            draw.rectangle([20, 20, 220, 120], outline="black", width=3)
            draw.line([20, 120, 220, 20], fill="blue", width=4)
            pdf.image(img, x=55, y=90, w=100)
            pdf.set_font(F, size=10)
            pdf.set_xy(55, 152)
            pdf.cell(0, 5, "Figura 1: Curva de desempenho.")
        if n == 3:
            # Two columns of prose
            pdf.set_font(F, size=10)
            for col, x in enumerate((20, 110)):
                pdf.set_xy(x, 25)
                text = (
                    f"Coluna {'esquerda' if col == 0 else 'direita'} começa aqui. " + LOREM + " "
                ) * 2
                pdf.multi_cell(80, 5, text)
            # Unruled table (aligned columns, no borders)
            pdf.set_font(F, size=10)
            rows = [
                ["País", "Capital", "População"],
                ["Brasil", "Brasília", "203 mi"],
                ["Chile", "Santiago", "19 mi"],
                ["Peru", "Lima", "34 mi"],
            ]
            for r, row in enumerate(rows):
                for c, cell in enumerate(row):
                    pdf.set_xy(30 + c * 45, 120 + r * 6)
                    pdf.cell(40, 5, cell)
    pdf.output(str(path))
    return path


def hard_cases_pdf(path: Path) -> Path:
    """Regressions from real documents (LaTeX papers, matplotlib charts, Word reports).

    p1: booktabs table (only horizontal rules, uniform narrow gaps, numbers) under a paragraph
    p2: vector chart (axes, ticks, data polylines, framed legend, tick labels) + caption
    p3-4: logo + rule repeated at the top of every page, text, then a bordered table with
        multi-line cells and a shaded full-width row; TeX-style accents drawn as separate glyphs
    """
    from PIL import Image, ImageDraw

    pdf, F = _pdf()
    # p1 ---------------------------------------------------------------- booktabs
    pdf.add_page()
    pdf.set_font(F, size=10)
    pdf.set_xy(20, 20)
    pdf.multi_cell(170, 5, LOREM)
    cols = [20, 44, 62, 80, 98, 116, 134, 152, 170]
    head = ["Repr.", "Escore", "B2W", "Intent", "Ruling", "TuPy", "B2W", "Intent", "Ruling"]
    rows = [
        ["Congelado", "MSP", "0,014", "0,217", "0,498", "0,229", "0,848", "0,829", "0,688"],
        ["Congelado", "cos", "0,017", "0,260", "0,566", "0,322", "0,787", "0,739", "0,561"],
        ["CE", "MSP", "0,048", "0,283", "0,450", "0,167", "0,811", "0,806", "0,704"],
        ["proto", "MSP", "0,004", "0,115", "0,072", "0,068", "0,898", "0,876", "0,936"],
    ]
    pdf.set_font(F, size=9)
    pdf.set_line_width(0.5)
    pdf.line(20, 45, 190, 45)
    pdf.set_xy(62, 46)
    pdf.cell(36, 4, "AURC")
    pdf.set_xy(134, 46)
    pdf.cell(36, 4, "AUROC")
    pdf.set_line_width(0.2)
    pdf.line(62, 50.5, 114, 50.5)
    pdf.line(134, 50.5, 186, 50.5)
    for c, text in zip(cols, head, strict=True):
        pdf.set_xy(c, 51)
        pdf.cell(16, 4, text)
    pdf.line(20, 56, 190, 56)
    for r, row in enumerate(rows):
        for c, text in zip(cols, row, strict=True):
            pdf.set_xy(c, 57 + r * 4.5)
            pdf.cell(16, 4, text)
    pdf.set_line_width(0.5)
    pdf.line(20, 76, 190, 76)
    pdf.set_font(F, size=10)
    pdf.set_xy(20, 82)
    pdf.multi_cell(170, 5, LOREM)

    # p2 ---------------------------------------------------------------- chart
    pdf.add_page()
    pdf.set_font(F, size=10)
    pdf.set_xy(20, 20)
    pdf.multi_cell(170, 5, "O gráfico abaixo compara o risco seletivo dos dois métodos.")
    x0, y0, w, h = 50, 50, 110, 70
    pdf.set_line_width(0.3)
    pdf.rect(x0, y0, w, h)
    pdf.set_font(F, size=7)
    for k in range(6):
        tx = x0 + k * w / 5
        pdf.line(tx, y0 + h, tx, y0 + h + 1.5)
        pdf.set_xy(tx - 4, y0 + h + 2)
        pdf.cell(8, 3, f"{k / 5:.1f}", align="C")
        ty = y0 + h - k * h / 5
        pdf.line(x0 - 1.5, ty, x0, ty)
        pdf.set_xy(x0 - 11, ty - 1.5)
        pdf.cell(9, 3, f"{k * 0.035:.3f}", align="R")
    pdf.set_xy(x0 + w / 2 - 10, y0 + h + 6)
    pdf.cell(20, 3, "coverage", align="C")
    pdf.set_draw_color(30, 90, 200)
    pts = [(x0 + i * w / 20, y0 + h - (i / 20) ** 2 * h * 0.9) for i in range(21)]
    pdf.polyline(pts)
    pdf.set_draw_color(200, 60, 30)
    pdf.polyline([(x, y + 6) for x, y in pts[:-1]])
    pdf.set_draw_color(0, 0, 0)
    pdf.rect(x0 + 5, y0 + 4, 40, 12)  # legend frame
    pdf.line(x0 + 7, y0 + 8, x0 + 13, y0 + 8)
    pdf.set_xy(x0 + 14, y0 + 6.5)
    pdf.cell(30, 3, "baseline + MSP")
    pdf.line(x0 + 7, y0 + 13, x0 + 13, y0 + 13)
    pdf.set_xy(x0 + 14, y0 + 11.5)
    pdf.cell(30, 3, "prototypical + cosine")
    pdf.set_font(F, size=10)
    pdf.set_xy(20, 135)
    pdf.cell(0, 5, "Figura 1. Risco-cobertura a 5-shot.")
    pdf.set_xy(20, 145)
    pdf.multi_cell(170, 5, LOREM)

    # p3-4 -------------------------------------------------------------- report
    logo = Image.new("RGB", (120, 60), "white")
    ImageDraw.Draw(logo).ellipse([5, 5, 55, 55], fill=(20, 80, 180))
    for page in (3, 4):
        pdf.add_page()
        pdf.image(logo, x=20, y=10, w=30)
        pdf.set_line_width(0.3)
        pdf.line(20, 28, 190, 28)  # rule under the header, same width as the tables
        pdf.set_font(F, size=11)
        y = 34
        if page == 3 and F == "U":
            # TeX (OT1) draws accents as separate glyphs over/under the letter.
            base = y + 5
            x = 20.0
            for piece in ("Teoria da Computa", "c", "a", "o e M", "a", "quinas"):
                pdf.text(x, base, piece)
                wd = pdf.get_string_width(piece)
                if piece == "c":
                    pdf.text(x + wd * 0.25, base + 0.3, "¸")  # cedilla under the c
                elif piece == "a" and x < 60:
                    pdf.text(x + wd * 0.15, base - 0.6, "˜")  # tilde over the a
                elif piece == "a":
                    pdf.text(x + wd * 0.3, base - 0.5, "´")  # acute over the a
                x += wd
            y += 10
        pdf.set_xy(20, y)
        pdf.multi_cell(170, 5.5, ("• " + LOREM + " ") * 2)
        rows = [
            ["Tarefa", "Duração", "Início", "Responsável"],
            ["Fase 1 - Iniciação", "", "", ""],
            ["Objetivo, finalidade e equipe", "7 dias", "24/08/2026", "Equipe"],
            ["Definição, etapas e documentação do projeto", "3 dias", "08/09/2026", "Gustavo"],
            ["Cronograma e riscos", "3 dias", "08/09/2026", "Gustavo"],
        ]
        widths = [80, 25, 35, 30]
        ty = 110
        pdf.set_font(F, size=10)
        for r, row in enumerate(rows):
            lines = 2 if r == 3 else 1
            hgt = 6 * lines
            if r == 1:
                pdf.set_fill_color(205, 220, 245)
                pdf.rect(20, ty, sum(widths), hgt, style="DF")
                pdf.set_xy(21, ty)
                pdf.cell(60, 6, row[0])
            else:
                x = 20
                for c, (text, wd) in enumerate(zip(row, widths, strict=True)):
                    pdf.rect(x, ty, wd, hgt)
                    pdf.set_xy(x, ty)
                    if c == 0 and lines == 2:
                        pdf.multi_cell(wd - 30, 6, text)
                    else:
                        pdf.cell(wd, 6, text)
                    x += wd
            ty += hgt
        if page == 4:
            # A second table of the same width further down, with a heading and a chart image
            # between them (Word report: "9 - Gráfico de Gantt"): two tables, not one.
            pdf.set_xy(20, ty + 6)
            pdf.cell(0, 6, "9 - Gráfico de Gantt")
            gantt = Image.new("RGB", (300, 80), "white")
            ImageDraw.Draw(gantt).rectangle([40, 20, 200, 40], fill=(30, 120, 230))
            pdf.image(gantt, x=20, y=ty + 14, w=120)
            ty += 52
            pdf.set_xy(20, ty - 8)
            pdf.cell(0, 6, "10 - Plano de Riscos")
            for row in [
                ["Risco", "Probabilidade", "Impacto", "Mitigação"],
                ["Baixa adesão", "Média", "Alta", "Divulgação"],
                ["Custos de APIs", "Baixa", "Médio", "Alternativas"],
            ]:
                x = 20
                for text, wd in zip(row, (55, 40, 30, 45), strict=True):  # text fits any font
                    pdf.rect(x, ty, wd, 6)
                    pdf.set_xy(x, ty)
                    pdf.cell(wd, 6, text)
                    x += wd
                ty += 6

    # p5 ---------------------------------------------------------------- paper page
    # booktabs table whose cells wrap over several lines (rows set apart by extra space),
    # then a scatter plot with a long axis title and a legend of markers under it.
    pdf.add_page()
    pdf.set_font(F, size=9)
    pdf.set_line_width(0.5)
    pdf.line(20, 20, 190, 20)
    heads = ["study", "statistics", "methods", "divergence"]
    xs = [20, 60, 100, 145]
    for x, h in zip(xs, heads, strict=True):
        pdf.text(x, 25, h)
    pdf.set_line_width(0.2)
    pdf.line(20, 27, 190, 27)
    body = [
        (
            ["Dutta et al.", "(2024)"],
            ["flips, KL"],
            ["6 quant.", "schemes, layer", "drop, Wanda"],
            ["correlation;", "margin account"],
        ),
        (
            ["Qamar et al.", "(2026)"],
            ["TV, JS,", "accuracy"],
            ["llama.cpp", "formats"],
            ["only evaluates", "endpoint"],
        ),
        (["this work"], ["flips, KL, TV"], ["9 families,", "MoE, QAT"], ["ratio = 1 (TV)"]),
    ]
    y = 32.0
    for row in body:
        for x, lines in zip(xs, row, strict=True):
            for k, ln in enumerate(lines):
                pdf.text(x, y + k * 3.6, ln)
        y += max(len(c) for c in row) * 3.6 + 2.6  # extra space between logical rows
    pdf.set_line_width(0.5)
    pdf.line(20, y - 1.5, 190, y - 1.5)

    import random

    rnd = random.Random(7)
    px, py, pw, ph = 60, 110, 90, 60
    pdf.set_line_width(0.3)
    pdf.rect(px, py, pw, ph)
    colors = [(220, 60, 60), (40, 110, 220), (240, 150, 30)]
    for _ in range(120):
        t = rnd.random()
        pdf.set_fill_color(*rnd.choice(colors))
        pdf.ellipse(
            px + 3 + t * (pw - 8),
            py + ph - 5 - t * (ph - 10) + rnd.uniform(-4, 4),
            1.4,
            1.4,
            style="F",
        )
    pdf.set_font(F, size=7)
    for k, lab in enumerate(["10^-1", "10^0"]):
        pdf.text(px + 20 + k * 45, py + ph + 4, lab)
    pdf.text(px + 15, py + ph + 9, "KL (per-token KL averaged, then rooted)")
    for k, lab in enumerate(["GSM8K", "MMLU-en", "WikiText (natural)"]):
        pdf.set_fill_color(*colors[k])
        pdf.ellipse(px + 2 + k * 30, py + ph + 12, 1.6, 1.6, style="F")
        pdf.text(px + 5 + k * 30, py + ph + 13.4, lab)
    pdf.set_font(F, size=10)
    pdf.text(20, py + ph + 24, "Figure 1: The same configurations, measured two ways.")
    pdf.output(str(path))
    return path


def declaration_pdf(path: Path) -> Path:
    """A one-page institutional letter (no real data): logo + 3-line header beside it, a
    letter-spaced centred bold title, a justified 1.5-spaced paragraph with bold runs and a
    first-line indent, option lines aligned with *white* (invisible) text, centred footer."""
    from PIL import Image, ImageDraw

    pdf, F = _pdf()
    pdf.add_page()
    logo = Image.new("RGB", (80, 80), "white")
    ImageDraw.Draw(logo).ellipse([5, 5, 75, 75], fill=(20, 80, 180))
    pdf.image(logo, x=25, y=12, w=20)
    pdf.set_font(F, "B", 11)
    for k, line in enumerate(
        ["UNIVERSIDADE EXEMPLO", "PRÓ-REITORIA DE GRADUAÇÃO", "CENTRO ACADÊMICO"]
    ):
        pdf.text(50, 18 + k * 5, line)
    pdf.set_font(F, "B", 13)
    pdf.set_char_spacing(3)
    title = "DECLARAÇÃO DE VÍNCULO"
    pdf.text(105 - pdf.get_string_width(title) / 2, 60, title)
    pdf.set_char_spacing(0)
    pdf.set_font(F, size=11)
    pdf.set_xy(25, 75)
    text = (
        "            Atestamos que a estudante **FULANA DE TAL**, matrícula Nº **000000000** "
        "ingressou nesta Universidade em **2023.1** e encontra-se regularmente vinculada ao "
        "curso de graduação de **CIÊNCIA DA COMPUTAÇÃO**, turno **INTEGRAL**."
    )
    pdf.multi_cell(160, 8, text, align="J", markdown=True)  # 1.5 line spacing
    y = pdf.get_y() + 2
    pdf.text(25, y, "Situação do vínculo: (X) Matriculada em disciplinas")
    for k, option in enumerate(["( ) Matrícula trancada", "( ) Participante de mobilidade"]):
        yy = y + 7 * (k + 1)
        pdf.set_text_color(255, 255, 255)  # invisible prefix used only to align the option
        pdf.text(25, yy, "Situação do vínculo: (X)")
        pdf.set_text_color(0, 0, 0)
        pdf.text(25 + pdf.get_string_width("Situação do vínculo: "), yy, option)
    pdf.set_font(F, "B", 12)
    for k, line in enumerate(["Código de verificação:", "abc123"]):
        pdf.text(105 - pdf.get_string_width(line) / 2, 200 + k * 6, line)
    pdf.set_font(F, size=8)
    foot = "Documento válido por 30 dias a partir da data de sua emissão."
    pdf.text(105 - pdf.get_string_width(foot) / 2, 220, foot)
    pdf.output(str(path))
    return path
