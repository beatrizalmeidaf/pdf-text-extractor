"""Write the Python engine's view of the test PDFs, for parity.mjs to compare against."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fixtures import declaration_pdf, exam_pdf, hard_cases_pdf, structured_pdf  # noqa: E402
from papero_extract import extract  # noqa: E402

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
print(f"fixtures + expected JSON in {out}")
