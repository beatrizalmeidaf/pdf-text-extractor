import pytest

from papero_extract import (
    EncryptedPDFError,
    InvalidPDFError,
    PageRangeError,
    TooManyPagesError,
    extract_text,
)
from papero_extract.extractor import parse_page_spec


def test_extracts_and_cleans(sample_pdf):
    r = extract_text(sample_pdf)
    assert r.page_count == 5 and len(r.pages) == 5
    assert "Art. 5 da Constituição de 1988" in r.text
    assert "Linha final do conteudo 35." in r.text  # number inside text kept
    assert "Relatorio Anual" not in r.text  # repeated header removed
    assert not any(p.text.strip().endswith("\n1") for p in r.pages)
    assert r.pages[0].text.splitlines()[-1] == "Linha final do conteudo 7."
    assert not r.likely_scanned


def test_raw_mode_keeps_header(sample_pdf):
    assert "Relatorio Anual" in extract_text(sample_pdf, clean=False).text


def test_bytes_input(sample_pdf):
    assert extract_text(sample_pdf.read_bytes()).page_count == 5


def test_page_selection(sample_pdf):
    r = extract_text(sample_pdf, pages="2,4-")
    assert [p.number for p in r.pages] == [2, 4, 5]


def test_parallel_matches_sequential(big_pdf):
    seq = extract_text(big_pdf, workers=1)
    par = extract_text(big_pdf, workers=4, parallel_threshold=16)
    assert par.text == seq.text and len(par.pages) == 120


def test_scanned_detection(blank_pdf):
    assert extract_text(blank_pdf).likely_scanned


def test_encrypted(encrypted_pdf):
    with pytest.raises(EncryptedPDFError):
        extract_text(encrypted_pdf)
    assert extract_text(encrypted_pdf, password="1234").page_count == 2


def test_invalid_pdf():
    with pytest.raises(InvalidPDFError):
        extract_text(b"%PDF-1.4 isto nao e um pdf")


def test_max_pages(sample_pdf):
    with pytest.raises(TooManyPagesError):
        extract_text(sample_pdf, max_pages=3)


@pytest.mark.parametrize(
    "spec,expected",
    [
        (None, [0, 1, 2, 3, 4]),
        ("1-3", [0, 1, 2]),
        ("5,1", [0, 4]),
        ("4-", [3, 4]),
        ("-2", [0, 1]),
        ("2-99", [1, 2, 3, 4]),
    ],
)
def test_parse_page_spec(spec, expected):
    assert parse_page_spec(spec, 5) == expected


@pytest.mark.parametrize("spec", ["0", "abc", "3-1", "9"])
def test_parse_page_spec_errors(spec):
    with pytest.raises(PageRangeError):
        parse_page_spec(spec, 5)
