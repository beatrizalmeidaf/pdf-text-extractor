import pytest

from papero_extract.cleaning import RAW, CleanOptions, clean_pages, is_page_number


@pytest.mark.parametrize(
    "line",
    ["3", " 12 ", "- 4 -", "Página 7", "pág. 2", "Page 3 of 10", "3/10", "5 de 20", "xii", "(9)"],
)
def test_detects_page_numbers(line):
    assert is_page_number(line)


@pytest.mark.parametrize("line", ["", "Art. 5", "em 2023", "Capítulo 3", "12345", "Total: 42"])
def test_does_not_flag_regular_lines(line):
    assert not is_page_number(line)


def test_keeps_numbers_inside_text():
    # Regression: v1 stripped every number at the end of any line.
    pages = ["Título\nO prazo é de 30\ndias corridos.\n1"]
    assert clean_pages(pages) == ["Título\nO prazo é de 30\ndias corridos."]


def test_removes_repeated_headers_and_footers():
    pages = [
        f"ACME S.A. - Relatório 2024\nConteúdo da página {n}\nmais texto\nConfidencial - pág {n}"
        for n in range(1, 6)
    ]
    out = clean_pages(pages)
    assert all(p.startswith("Conteúdo") for p in out)
    assert not any("Confidencial" in p for p in out)


def test_short_pages_body_is_not_treated_as_header():
    pages = ["Título\nMesmo corpo repetido\nFim"] * 4
    assert "Mesmo corpo repetido" in clean_pages(pages)[0]


def test_pdfium_hyphen_marker():
    assert clean_pages(["exem\x02plo"]) == ["exem-\nplo"]
    assert clean_pages(["exem\x02plo"], CleanOptions(dehyphenate=True)) == ["exemplo"]


def test_dehyphenate_plain_hyphen():
    out = clean_pages(["uma pala-\nvra quebrada"], CleanOptions(dehyphenate=True))
    assert out == ["uma palavra quebrada"]


def test_raw_keeps_everything():
    assert clean_pages(["x\r\n1"], RAW) == ["x\r\n1"]


def test_normalizes_whitespace():
    assert clean_pages(["a  \r\n\r\n\r\n\r\nb   "]) == ["a\n\nb"]
