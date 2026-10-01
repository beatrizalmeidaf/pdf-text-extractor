import sys
from pathlib import Path

import pytest
from fpdf import FPDF

sys.path.insert(0, str(Path(__file__).parent))  # tests/fixtures.py

BODY = (
    "O Art. 5 da Constituição de 1988 garante direitos fundamentais. "
    "Em 2023 foram registrados 42 casos."
)


def make_pdf(
    path: Path,
    pages: int = 5,
    *,
    header: bool = True,
    numbers: bool = True,
    body: bool = True,
    password: str | None = None,
) -> Path:
    pdf = FPDF()
    pdf.set_auto_page_break(False)
    if password:
        pdf.set_encryption(owner_password="owner", user_password=password)
    pdf.set_font("Helvetica", size=11)
    for n in range(1, pages + 1):
        pdf.add_page()
        if header:
            pdf.set_y(10)
            pdf.cell(0, 8, "Relatorio Anual 2024 - Empresa Exemplo")
        if body:
            pdf.set_y(30)
            pdf.multi_cell(0, 6, f"Capitulo {n}\n{BODY}\nLinha final do conteudo {n * 7}.")
        if numbers:
            pdf.set_y(-20)
            pdf.cell(0, 8, str(n), align="C")
    pdf.output(str(path))
    return path


@pytest.fixture
def sample_pdf(tmp_path):
    return make_pdf(tmp_path / "sample.pdf")


@pytest.fixture
def big_pdf(tmp_path):
    return make_pdf(tmp_path / "big.pdf", pages=120)


@pytest.fixture
def blank_pdf(tmp_path):
    return make_pdf(tmp_path / "blank.pdf", pages=3, header=False, numbers=False, body=False)


@pytest.fixture
def encrypted_pdf(tmp_path):
    return make_pdf(tmp_path / "secret.pdf", pages=2, password="1234")


@pytest.fixture(scope="session")
def structured_pdf(tmp_path_factory):
    from fixtures import structured_pdf as build

    return build(tmp_path_factory.mktemp("structured") / "structured.pdf")
