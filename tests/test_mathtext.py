import pytest

from papero_extract import extract
from papero_extract.cli import main
from papero_extract.mathtext import inline_latex, latexify, math_spans


@pytest.fixture(scope="module")
def exam(tmp_path_factory):
    from fixtures import exam_pdf

    return extract(exam_pdf(tmp_path_factory.mktemp("exam") / "exam.pdf"), tika=False)


# ----------------------------------------------------------------- finding the math
def test_math_set_in_the_text_font_is_found():
    assert inline_latex("Se tg x − cotg x = 1, então o valor de tg 2x é") == (
        r"Se $\operatorname{tg} x - \operatorname{cotg} x = 1$, "
        r"então o valor de $\operatorname{tg} 2x$ é"
    )


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1,035·10⁹ e 5,5·10⁷", r"$1{,}035\cdot 10^{9}$ e $5{,}5\cdot 10^{7}$"),
        ("y = −2√2x + 6", r"$y = -2\sqrt{2}x + 6$"),
        ("√(h² − d²)", r"$\sqrt{h^{2} - d^{2}}$"),
        ("CO₂(g) + H₂O(l)", r"$\operatorname{CO}_{2}(g) + H_{2}O(l)$"),
        ("f(x) = log x + 2, com x ∈ ℝ", r"$f(x) = \log x + 2$, com $x \in \mathbb{R}$"),
        # Letters together are a product, unless they are a name: a function, a unit, an element.
        (
            "Se f (x) = ax² + bx + c é tal que f (2) = 8 e f (3) = 15, então",
            "Se $f (x) = ax^{2} + bx + c$ é tal que $f (2) = 8$ e $f (3) = 15$, então",
        ),
        ("E = mc² para 2 mol de Mn", r"$E = mc^{2}$ para 2 mol de Mn"),
        # Each value on its own: the comma between them is prose.
        ("H = 1, C = 12 e Ar = 40", r"$H = 1$, $C = 12$ e $\operatorname{Ar} = 40$"),
        # A bracket that opens before the math stays out of it.
        ("(veja x = 2)", "(veja $x = 2$)"),
        ("(g·mol⁻¹) Mn = 55", r"$(g\cdot \operatorname{mol}^{-1})$ $\operatorname{Mn} = 55$"),
    ],
)
def test_stretches_of_math(text, expected):
    assert inline_latex(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "O Art. 5 da Constituição de 1988 garante direitos. Em 2023 foram 42 casos.",
        "A tabela (a) e o item 2 - veja a página 10.",  # a dash, a letter in brackets
        "x e y são os lados, a e b os ângulos.",  # letters, but nothing done with them
        "the method¹ uses a log file and max 3 items",  # a note mark, a word that is a function
        "custa R$ 50,00 ou 20% do total",
    ],
)
def test_prose_is_left_alone(text):
    assert math_spans(text) == [] and inline_latex(text) == text


def test_one_letter_words_are_variables_only_beside_an_operator():
    assert inline_latex("x = 1 e y = 2") == "$x = 1$ e $y = 2$"
    assert inline_latex("a = 2 e o valor") == "$a = 2$ e o valor"


def test_latexify():
    assert latexify("x^(n+1) + a_(ij)") == "x^{n+1} + a_{ij}"
    assert latexify("sen 30° ≤ α") == r"\operatorname{sen} 30^{\circ} \leq \alpha"


# ----------------------------------------------------------------- in the outputs
def test_markdown_and_text_with_latex_math(exam):
    md = exam.to_markdown(math="latex")
    assert r"igual a $64 \operatorname{cm}^{3}$ e a circunferência $x^{2} + y^{2} = 4$ corta" in md
    assert r"d) $1{,}035\cdot 10^{9}$ e $5{,}5\cdot 10^{7}$" in md
    assert r"c) $\operatorname{CO}_{2}(g) + H_{2}O(l)$" in md
    assert "<sup>" not in md
    text = exam.to_text(math="latex")
    assert r"e) $5{,}000\cdot 10^{3}$ e $1{,}0\cdot 10^{6}$" in text
    assert r"Dados: massas molares $(g\cdot \operatorname{mol}^{-1})$ $H = 1$, $C = 12$" in md


def test_bold_stays_on_the_words_around_the_math():
    from papero_extract.model import Block
    from papero_extract.render import block_markdown

    plain = {"bold": False, "italic": False, "script": None}
    runs = [
        {**plain, "text": "Dados:", "bold": True},
        {**plain, "text": " área de 10 m"},
        {**plain, "text": "2 ", "script": "super"},
        {**plain, "text": "e custo de R$ 5 *"},
    ]
    block = Block("paragraph", None, text="Dados: área de 10 m² e custo de R$ 5 *", runs=runs)
    assert block_markdown(block, math="latex") == (
        r"**Dados:** área de $10 m^{2}$ e custo de R\$ 5 \*"
    )


def test_default_output_is_unchanged(exam):
    assert "operatorname" not in exam.to_markdown() and "64 cm<sup>3</sup>" in exam.to_markdown()
    assert exam.to_text() == exam.text and "x² + y² = 4" in exam.text


def test_sentence_of_values_is_not_a_formula(exam):
    block = next(b for b in exam.pages[0].blocks if b.text.startswith("Dados:"))
    assert block.type == "paragraph"
    assert block.text == "Dados: massas molares (g·mol⁻¹) H = 1, C = 12, N = 14, O = 16"


def test_cli_math_option(tmp_path, capsys):
    from fixtures import exam_pdf

    pdf = exam_pdf(tmp_path / "exam.pdf")
    assert main(["extract", str(pdf), "--no-tika", "-q", "-f", "text", "--math", "latex"]) == 0
    assert r"$x^{2} + y^{2} = 4$" in capsys.readouterr().out
