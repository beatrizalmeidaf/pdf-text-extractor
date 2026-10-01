"""Structured extraction on a synthetic PDF (layout engine only: no Tika needed)."""

import pytest

from fixtures import unicode_font
from papero_extract import extract
from papero_extract.render import md_table, tables_csv
from papero_extract.symbols import latex_escape, normalize_char


@pytest.fixture(scope="module")
def doc(structured_pdf):
    return extract(structured_pdf, tika=False, images=True)


def types(page):
    return [b.type for b in page.blocks]


def test_headings_with_levels(doc):
    heads = [(b.level, b.text) for b in doc.blocks("heading")]
    assert heads[0] == (1, "Extração Estruturada")
    assert (2, "1 Introdução") in heads and (2, "3 Método") in heads


def test_running_header_and_page_numbers_are_furniture(doc):
    for page in doc.pages:
        assert "header" in types(page) and "page_number" in types(page)
    assert "Relatório Técnico" not in doc.text
    assert "Relatório Técnico" not in doc.to_markdown()


def test_numbered_list(doc):
    items = list(doc.blocks("list_item"))
    assert [i.marker for i in items] == ["1.", "2.", "3."]
    assert items[0].text == "Primeiro item da lista"


def test_ruled_table(doc):
    table = doc.tables[0]
    assert table.rows == [
        ["Modelo", "Precisão", "Latência (ms)"],
        ["Base", "0,81", "120"],
        ["Proposto", "0,93", "14"],
        ["Ablação", "0,88", "22"],
    ]
    assert table.caption == "Tabela 1: Comparação entre modelos."
    assert table.image is not None and table.image.data[:8] == b"\x89PNG\r\n\x1a\n"


def test_unruled_table_under_two_columns(doc):
    table = doc.tables[1]
    assert table.rows[0] == ["País", "Capital", "População"]
    assert table.rows[-1] == ["Peru", "Lima", "34 mi"]


def test_two_column_reading_order(doc):
    page = doc.pages[2]
    paras = [b for b in page.blocks if b.type == "paragraph"]
    assert paras[0].text.startswith("Coluna esquerda")
    assert paras[1].text.startswith("Coluna direita")
    assert "Coluna direita" not in paras[0].text
    assert page.blocks.index(paras[1]) < page.blocks.index(doc.tables[1])


@pytest.mark.skipif(unicode_font() is None, reason="needs a Unicode TTF for math glyphs")
def test_formulas_with_superscript_and_symbols(doc):
    formulas = doc.formulas
    assert formulas[0].text == "E = mc²"
    assert formulas[0].latex == "E = mc^{2}" and formulas[0].number == "(1)"
    assert r"\sum" in formulas[1].latex and r"\leq" in formulas[1].latex
    assert "$$\nE = mc^{2} \\tag{1}\n$$" in doc.to_markdown()


def test_figure_with_caption_and_crop(doc):
    fig = doc.figures[0]
    assert fig.caption == "Figura 1: Curva de desempenho."
    assert fig.image.width > 100 and fig.image.name == "p2-figure-1.png"
    x0, y0, x1, y1 = fig.bbox
    assert 140 < x0 < 170 and 240 < y0 < 270 and x1 > x0 and y1 > y0


def test_bboxes_are_top_left_points(doc):
    heading = next(doc.blocks("heading"))
    assert heading.bbox[1] < 100  # near the top of an A4 page (842 pt tall)
    assert all(0 <= b.bbox[0] <= b.bbox[2] <= 596 for b in doc.blocks() if b.bbox)


def test_json_shape(doc):
    d = doc.to_dict(embed_images=False)
    assert d["schema"] == "pdf-text-api/document@1"
    block = d["pages"][0]["blocks"][0]
    assert {"id", "type", "bbox", "text", "order"} <= block.keys()
    table = next(b for p in d["pages"] for b in p["blocks"] if b["type"] == "table")
    assert table["image"]["name"].endswith(".png") and "data" not in table["image"]


def test_exports(doc):
    md = doc.to_markdown()
    assert "| Modelo | Precisão | Latência (ms) |" in md and "![" in md
    html = doc.to_html()
    assert "<table" in html and 'data-bbox="' in html and "data:image/png;base64," in html
    csv = tables_csv(doc)
    assert 'Proposto,"0,93",14' in csv


def test_page_selection(structured_pdf):
    d = extract(structured_pdf, tika=False, pages="2")
    assert [p.number for p in d.pages] == [2] and d.page_count == 3


def test_markdown_table_escaping():
    assert md_table([["a|b", "c"], ["1\n2", "3"]]).splitlines()[0] == "| a\\|b | c |"
    assert "1<br>2" in md_table([["h", "i"], ["1\n2", "3"]])


def test_symbol_normalization():
    assert normalize_char(chr(0xF0B7)) == "•"  # Symbol-font bullet
    assert normalize_char(chr(0xF06C), "Wingdings") == "●"
    assert normalize_char(chr(0xF06C), "Symbol") == "λ"
    assert normalize_char(chr(0xF044), "Symbol") == "Δ"  # uppercase letters line up too
    assert normalize_char(chr(0xF057), "Symbol") == "Ω"
    assert normalize_char(chr(0xFB01)) == "fi"
    assert latex_escape("∑ α ≤ x") == r"\sum \alpha \leq x"


# ----------------------------------------------------------------------------- regressions
@pytest.fixture(scope="module")
def hard(tmp_path_factory):
    from fixtures import hard_cases_pdf

    return extract(hard_cases_pdf(tmp_path_factory.mktemp("hard") / "hard.pdf"), tika=False)


def test_booktabs_table_keeps_every_column(hard):
    rows = hard.pages[0].blocks[1].rows
    assert rows[1] == [
        "Repr.",
        "Escore",
        "B2W",
        "Intent",
        "Ruling",
        "TuPy",
        "B2W",
        "Intent",
        "Ruling",
    ]
    assert rows[2][:4] == ["Congelado", "MSP", "0,014", "0,217"]  # numbers never cut in two
    assert all(len(r) == 9 for r in rows)


def test_chart_is_one_figure_with_its_labels(hard):
    page = hard.pages[1]
    assert [b.type for b in page.blocks] == ["paragraph", "figure", "caption", "paragraph"]
    fig = page.blocks[1]
    assert "baseline + MSP" in fig.text and "coverage" in fig.text and "0.175" in fig.text
    assert fig.caption.startswith("Figura 1")
    assert not hard.tables[1:] or all("baseline" not in t.text for t in hard.tables)


def test_page_header_rule_does_not_swallow_paragraphs(hard):
    page = hard.pages[2]
    table = next(b for b in page.blocks if b.type == "table")
    assert table.rows[0] == ["Tarefa", "Duração", "Início", "Responsável"]
    assert table.rows[3][0] == "Definição, etapas e\ndocumentação do projeto"  # multi-line cell
    assert len(table.rows) == 5
    assert not any("estruturada" in c for r in table.rows for c in r)


@pytest.mark.skipif(unicode_font() is None, reason="needs a Unicode TTF for accent glyphs")
def test_tex_accents_are_composed(hard):
    assert "Teoria da Computação e Máquinas" in hard.text


def test_repeated_logo_is_page_furniture(hard):
    logos = [b for p in hard.pages[2:] for b in p.blocks if b.bbox and b.bbox[1] < 40]
    assert logos and all(b.type == "header" for b in logos)
    assert (
        hard.to_markdown().split("Teoria")[1].count("<!-- figura") == 2
    )  # Gantt + scatter plot, no logos


def test_wrapped_list_item_without_hanging_indent(hard):
    item = next(b for b in hard.pages[2].blocks if b.type == "list_item")
    assert "que melhora a qualidade" in item.text


def test_two_tables_of_same_width_stay_apart(hard):
    page = hard.pages[3]
    types = [b.type for b in page.blocks if b.type not in ("header", "footer", "page_number")]
    assert types[-5:] == ["table", "paragraph", "figure", "paragraph", "table"]
    assert page.blocks[-1].rows[0] == ["Risco", "Probabilidade", "Impacto", "Mitigação"]


# ----------------------------------------------------------------------------- letters & forms
@pytest.fixture(scope="module")
def letter(tmp_path_factory):
    from fixtures import declaration_pdf

    return extract(declaration_pdf(tmp_path_factory.mktemp("decl") / "decl.pdf"), tika=False)


def test_white_alignment_text_is_dropped(letter):
    texts = [b.text for b in letter.pages[0].blocks]
    lines = [ln for t in texts for ln in t.splitlines()]  # one block or two: font metrics
    assert "( ) Matrícula trancada" in lines and "( ) Participante de mobilidade" in lines
    assert sum("Situação do vínculo" in t for t in texts) == 1


def test_one_and_a_half_spaced_paragraph_is_one_block(letter):
    para = next(b for b in letter.pages[0].blocks if b.text.startswith("Atestamos"))
    assert para.text.endswith("turno INTEGRAL.") and para.lines == 3
    assert para.align == "justify" and para.first_line and para.line_spacing > 1.4
    assert {"text": "FULANA DE TAL", "bold": True} in [
        {"text": r["text"].strip(), "bold": r["bold"]} for r in para.runs
    ]


def test_intended_line_breaks_and_layout(letter):
    blocks = letter.pages[0].blocks
    head = next(b for b in blocks if b.text.startswith("UNIVERSIDADE"))
    assert head.text.split("\n") == [
        "UNIVERSIDADE EXEMPLO",
        "PRÓ-REITORIA DE GRADUAÇÃO",
        "CENTRO ACADÊMICO",
    ]
    title = next(b for b in blocks if "VÍNCULO" in b.text)
    assert title.text == "DECLARAÇÃO DE VÍNCULO" and title.align == "center" and title.tracking
    option = next(b for b in blocks if b.text.startswith("( ) Matr"))
    assert option.indent and option.indent > 90
    assert blocks[-1].align == "center" and blocks[-1].pt == 8.0


# ----------------------------------------------------------------- drawn mathematics
@pytest.fixture(scope="module")
def exam(tmp_path_factory):
    from fixtures import exam_pdf

    doc = extract(exam_pdf(tmp_path_factory.mktemp("exam") / "exam.pdf"), tika=False)
    return [b for b in doc.pages[0].blocks]


def _text_of(blocks, start: str) -> str:
    block = next(
        b for b in blocks if (b.marker or "").startswith(start) or b.text.startswith(start)
    )
    return block.text


def test_exponent_barely_smaller_than_the_text(exam):
    question = _text_of(exam, "Um cone")
    assert "64 cm³" in question
    assert "x² + y² = 4" in question


def test_stacked_fraction_is_read_as_a_fraction(exam):
    assert _text_of(exam, "a)").endswith("5/12")


def test_root_sign_drawn_with_strokes(exam):
    assert _text_of(exam, "b)").endswith("10√2")
    assert not any(b.type in ("table", "figure") for b in exam)  # its strokes are not a grid


def test_chemical_indices_and_state_of_matter(exam):
    assert _text_of(exam, "c)").endswith("CO₂(g) + H₂O(l)")


def test_options_with_exponents_stay_one_per_line(exam):
    # (As formulas, the two lines would run together into one block.)
    items = {b.marker: b.text for b in exam if b.type == "list_item"}
    assert items["d)"] == "1,035·10⁹ e 5,5·10⁷"  # and the word gap after the exponent is kept
    assert items["e)"] == "5,000·10³ e 1,0·10⁶"
    assert not any(b.type == "formula" for b in exam)


# ----------------------------------------------------------------- columns, TeX fonts
def test_gutter_between_two_columns_despite_a_spanning_title():
    from papero_extract.columns import area_of, bands, columns

    title = (120, 60, 480, 80)
    left = [(50, 100 + 60 * k, 295, 150 + 60 * k) for k in range(8)]
    right = [(310, 100 + 60 * k, 560, 150 + 60 * k) for k in range(8)]
    boxes = [title, *left, *right]
    cols = columns(boxes)
    assert [(round(a), round(b)) for a, b in cols] == [(50, 295), (310, 560)]
    assert area_of(left[0], cols) == cols[0] and area_of(title, cols) == (50, 560)
    grouped = bands(boxes, bbox=lambda b: b, kind=lambda b: "paragraph")
    assert [len(band["blocks"]) for band in grouped] == [1, 2]
    assert [len(col) for col in grouped[1]["blocks"]] == [8, 8]


def test_single_column_has_no_gutter():
    from papero_extract.columns import columns

    assert len(columns([(50, 100 + 30 * k, 560, 125 + 30 * k) for k in range(10)])) == 1


def test_tex_font_codes_without_tounicode():
    from papero_extract.tex_fonts import NOT, is_tex_producer, tex_char, tex_encoding

    assert is_tex_producer("pdfTeX-1.40.21") and not is_tex_producer("Acrobat Distiller 11.0")
    assert tex_encoding("ABCDEF+CMMI10") == "oml" and tex_encoding("TimesNewRomanPSMT") == ""
    assert tex_char(0x0F, "oml") == "ϵ"  # epsilon1: no Unicode name, comes as a control code
    assert tex_char(ord("h"), "oms") == "⟨" and tex_char(ord("6"), "oms") == NOT
    assert tex_char(ord("{"), "oms") is None  # a real brace, already resolved by name
    assert tex_char(0x58, "omx") == "∑"
