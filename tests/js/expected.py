"""Write the Python engine's view of the test PDFs, for parity.mjs to compare against."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fixtures import declaration_pdf, exam_pdf, hard_cases_pdf, structured_pdf  # noqa: E402
from papero_extract import extract  # noqa: E402
from papero_extract.fidelity import assess, reference_text  # noqa: E402
from papero_extract.mathtext import inline_latex  # noqa: E402

# Text for the inline-math writer: what it must find, and what it must leave alone.
MATH_SAMPLES = [
    "Se tg x − cotg x = 1, então o valor de tg 2x é",
    "Considerando o volume total de 1·10⁶ m³, as quantidades em mols são da ordem de",
    "Dados: massas molares (g·mol⁻¹) H = 1, C = 12, N = 14, O = 16, Ar = 40",
    "1,035·10⁹ e 5,5·10⁷",
    "Se f (x) = ax² + bx + c é tal que f (2) = 8, f (3) = 15 e f (4) = 26, então a + b + c é",
    "E = mc² e a massa de 2 mol de Mn em 5 cm³ (veja a tabela (a) e a nota (2))",
    "y = −2√2x + 6",
    "√(h² − d²) e 2√(h² + d²)",
    "CO₂(g) + H₂O(l) → H₂CO₃(aq)",
    "constante universal dos gases ideais (mmHg·L·mol⁻¹·K⁻¹) = 62,3",
    "a função f(x) = log x + 2 é crescente, x ∈ ℝ e α > 0 (veja x = 2)",
    "sen 53º = 0,80; cos 53º = 0,60 e x^(n+1) + a_(ij) ≤ 3",
    "O Art. 5 da Constituição de 1988 garante direitos. Em 2023 foram 42 casos - veja (a) e o 2.",
    "O custo é R$ 50,00, a nota é 7 e o método¹ usa um log de 3 linhas; e a = b.",
    "the method¹ uses a log file, max 3 items and p < 0.05\nnew line with x² + y² = 4",
]

out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
out.mkdir(exist_ok=True)
for name, build in (
    ("structured", structured_pdf),
    ("hard", hard_cases_pdf),
    ("declaration", declaration_pdf),
    ("exam", exam_pdf),
):
    pdf = build(out / f"{name}.pdf")
    doc = extract(pdf, tika=False)
    (out / f"{name}.json").write_text(
        json.dumps(doc.to_dict(embed_images=False), ensure_ascii=False), encoding="utf-8"
    )
    fidelity = assess(doc, reference_text(pdf)).to_dict()
    (out / f"{name}.fidelity.json").write_text(json.dumps(fidelity), encoding="utf-8")
    for suffix, text in (
        ("md", doc.to_markdown(images="none", math="latex")),
        ("txt", doc.to_text(math="latex")),
    ):
        (out / f"{name}.latex.{suffix}").write_text(text, encoding="utf-8", newline="\n")
(out / "inline_math.json").write_text(
    json.dumps({s: inline_latex(s) for s in MATH_SAMPLES}, ensure_ascii=False), encoding="utf-8"
)
print(f"fixtures + expected JSON in {out}")
