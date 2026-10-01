<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="web/assets/logo-dark.png">
    <img src="web/assets/logo-light.png" alt="papero" width="460">
  </picture>
</p>

<p align="center">
  <strong>Document structure extraction without the heavyweight stack.</strong>
</p>

<p align="center">
  PDF → Markdown · JSON · Excel · Word
  <br>
  Reading order · Tables · Formulas · Figures · Bounding boxes
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#python">Python</a> ·
  <a href="#cli">CLI</a> ·
  <a href="#rest-api">REST API</a> ·
  <a href="#benchmarks">Benchmarks</a>
</p>

<p align="center">
  <a href="https://github.com/beatrizalmeidaf/pdf-text-extractor/actions/workflows/ci.yml">
    <img src="https://github.com/beatrizalmeidaf/pdf-text-extractor/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-orange.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/runs%20on-CPU-2ea44f.svg" alt="Runs on CPU">
  <img src="https://img.shields.io/badge/ML%20models-none-8A2BE2.svg" alt="No ML models">
  <img src="https://img.shields.io/badge/engine-Apache%20Tika%20%2B%20PDFium-D22128.svg" alt="Apache Tika + PDFium">
</p>

<p align="center">
  <a href="https://beatrizalmeidaf.github.io/pdf-text-extractor/">
    <strong>▶ Try Papero in your browser</strong>
  </a>
</p>

---

## Why Papero?

Extracting text from a document is easy.

Extracting its **structure** is not.

Papero reconstructs documents into structured, machine-readable data while preserving:

- reading order across columns
- paragraphs and headings
- tables, including multi-line cells
- formulas and LaTeX
- figures and images
- block coordinates
- headers, footers and page numbers
- document metadata

It runs on **CPU**, requires **no ML models**, and can be used as a Python library, CLI, REST API, Docker service, or directly in the browser.

---

## Quick Start

### Install

```bash
pip install pdf-text-api   # the package keeps its name; papero is the project's name
```

### Extract a document

```python
from pdf_text_api import extract

doc = extract("paper.pdf")

print(doc.to_markdown())
```

That's it.

Papero returns a structured document that you can feed into RAG pipelines, search systems, LLM workflows, data processing pipelines, or your own applications.

---

## Python

```python
from pdf_text_api import extract

doc = extract("paper.pdf", images=True)

print(doc.to_markdown())

print(doc.tables[0].rows)

print(doc.formulas[0].latex)

for block in doc.pages[0].blocks:
    print(block.type, block.bbox, block.text)
```

You can also extract only text:

```python
from pdf_text_api import extract_text

text = extract_text("paper.pdf").text
```

### Supported options

```python
extract(
    "paper.pdf",
    pages="1-3,5",
    images=True,
    image_scale=2.0,
    tables=True,
    formulas=True,
    ocr="auto",
    ocr_language="por+eng",
    tika=False,
    workers=4,
)
```

---

## What Papero extracts

| Feature              | Output                        |
| -------------------- | ----------------------------- |
| Reading order        | Structured blocks             |
| Headings             | Heading + level               |
| Paragraphs           | Clean text                    |
| Lists                | Items + markers               |
| Tables               | Rows, columns, multi-line cells (ruled, borderless, booktabs) |
| Formulas             | LaTeX + cropped image         |
| Figures              | Cropped PNG                   |
| Bounding boxes       | `[x0, y0, x1, y1]` in points, origin at the top-left |
| Metadata             | Title, author, language, etc. |
| Headers / footers    | Detected and marked           |
| Page numbers         | Detected separately           |
| OCR                  | Tesseract                     |
| Multi-column layouts | Column-aware reading order    |
| Inline formatting    | Bold, italic, super/subscript runs |
| Layout               | Alignment, indents, line spacing, letter spacing |
| Hidden text          | White-on-white text dropped (forms, templates) |

---

## Supported formats

Papero's structured PDF engine works alongside Apache Tika for broader document support.

### Documents

* PDF
* DOCX
* PPTX
* XLSX
* ODT
* RTF
* EPUB
* HTML
* email formats

### Output

| Format | Python / CLI / API | Browser app |
| --- | :---: | :---: |
| Markdown | ✓ | ✓ |
| JSON (blocks, bbox, runs, layout) | ✓ | ✓ |
| Plain text | ✓ | ✓ |
| HTML (keeps alignment and indents) | ✓ | ✓ |
| CSV (tables) | ✓ | ✓ |
| ZIP + extracted images | ✓ | ✓ |
| Word `.docx` (keeps the page's layout) | — | ✓ |
| Excel `.xlsx` (one sheet per table) | — | ✓ |

---

## Built for RAG and LLM pipelines

Papero is designed for the step that usually happens **before** embeddings, chunking and retrieval:

```text
Document
   │
   ▼
┌──────────────┐
│    Papero    │
└──────┬───────┘
       │
       ▼
Structured document
       │
       ├── Markdown
       ├── JSON
       ├── Tables
       ├── Formulas
       ├── Figures
       └── Bounding boxes
       │
       ▼
Chunking / Embeddings / RAG / LLM
```

Because every block retains its position, the output can also be mapped back to the original document.

For example:

```json
{
  "type": "table",
  "bbox": [56.7, 294.8, 481.9, 374.2],
  "rows": [
    ["Model", "Accuracy"],
    ["Base", "0.81"]
  ]
}
```

This makes it possible to preserve both **content and provenance**.

---

## Browser

Papero also runs in the browser.

**Your PDF stays on your machine.**

<a href="https://beatrizalmeidaf.github.io/pdf-text-extractor/">
  <strong>▶ Open the browser app</strong>
</a>

The web application lets you inspect:

* extracted text
* Markdown
* tables
* images
* JSON
* document blocks
* block coordinates

The browser implementation uses the same structural concepts as the Python engine, ported to JavaScript with pdf.js.

---

## CLI

Install the package and use the command line:

```bash
pdf-text-api extract paper.pdf -o paper.md --images
```

JSON:

```bash
pdf-text-api extract paper.pdf -o paper.json
```

Tables:

```bash
pdf-text-api extract paper.pdf -f csv -o tables.csv
```

Specific pages:

```bash
pdf-text-api extract paper.pdf -p 1-5 -f html
```

Fast text extraction:

```bash
pdf-text-api extract paper.pdf --fast
```

Run the web/API server:

```bash
pdf-text-api serve --port 8000
```

---

## REST API

Run the complete stack:

```bash
docker compose up
```

The API will be available at:

```text
http://localhost:8000
```

Extract Markdown:

```bash
curl \
  -F "file=@paper.pdf" \
  "localhost:8000/v1/extract?format=markdown"
```

Extract everything as a ZIP:

```bash
curl \
  -F "file=@paper.pdf" \
  "localhost:8000/v1/extract?format=zip&images=true" \
  -o paper.zip
```

Get page-level blocks and coordinates:

```bash
curl \
  -F "file=@paper.pdf" \
  "localhost:8000/v1/extract?per_page=true"
```

Interactive API documentation:

```text
/docs
```

---

## How it works

Papero combines two complementary processing paths.

### PDF layout engine

The PDF engine operates on PDF-level geometry:

* glyph positions
* fonts
* font sizes
* lines
* images
* page coordinates

It uses this information to reconstruct:

* columns
* paragraphs
* tables
* lists
* formulas
* figures
* reading order

### Apache Tika

Apache Tika provides:

* document metadata
* tagged-PDF information
* OCR integration
* support for additional document formats

The two paths can run in parallel.

For the browser, the structural engine is implemented with JavaScript and pdf.js.

---

## Benchmarks

Papero includes reproducible benchmark scripts and a dataset of academic PDFs.

The benchmark uses dense academic papers with:

* multiple columns
* mathematical formulas
* tables
* figures
* long documents

Tests were performed locally on CPU.

### 50-paper benchmark

| Tool              |      Total | Average / PDF |
| ----------------- | ---------: | ------------: |
| PyMuPDF           |     4.86 s |      97.23 ms |
| **Papero — fast** | **6.78 s** | **135.65 ms** |
| PyPDF             |   1 m 16 s |    1520.24 ms |
| pdfplumber        |   2 m 57 s |    3555.92 ms |
| Docling           |  ~1 h 09 m |       ~82.9 s |

<p align="center">
  <img src="benchmarks/latency.svg" alt="Average extraction time per PDF on a log scale: PyMuPDF 97 ms, papero fast 136 ms, papero structured 902 ms, pypdf 1.52 s, pdfplumber 3.56 s, Docling 82.9 s" width="760">
</p>

These numbers describe this benchmark configuration (one laptop CPU, no GPU) and should not be read as universal performance figures. `papero · fast` returns clean text; `papero · structured` also reconstructs reading order, tables, formulas and figures for every page.

### Structured mode

On 54 academic PDFs:

| Metric        |     Result |
| ------------- | ---------: |
| Failures      | **0 / 54** |
| Median / page |  **34 ms** |
| P90 / page    |  **57 ms** |
| Paragraphs    |      9,259 |
| Headings      |        762 |
| List items    |      1,412 |
| Tables        |        286 |
| Figures       |        499 |
| Formulas      |        738 |
| Captions      |        385 |

Run the benchmark yourself:

```bash
python benchmarks/download_arxiv_pdfs.py
python benchmarks/run_massive_benchmark.py
```

---

## Feature comparison

| Feature                    | Papero | PyMuPDF | pdfplumber | pypdf | Docling |  Marker |
| -------------------------- | :----: | :-----: | :--------: | :---: | :-----: | :-----: |
| License                    |  MIT   |   AGPL  |     MIT    |  BSD  |   MIT   |   GPL   |
| No ML models               |    ✓   |    ✓    |      ✓     |   ✓   |    —    |    —    |
| Multi-column reading order |    ✓   | partial |      —     |   —   |    ✓    |    ✓    |
| Structured tables          |    ✓   |    ✓    |      ✓     |   —   |    ✓    |    ✓    |
| Formula extraction         | LaTeX (from glyphs) + image | — | — | — | ✓ (model) | ✓ (model) |
| Bounding boxes             |    ✓   |    ✓    |      ✓     |   —   |    ✓    |    ✓    |
| DOCX/PPTX/XLSX/EPUB/HTML   |    ✓   | partial |      —     |   —   |    ✓    | partial |
| OCR                        |    ✓   |    ✓    |      —     |   —   |    ✓    |    ✓    |
| Runs fully in the browser  |    ✓   |    —    |      —     |   —   |    —    |    —    |
| Word export keeping layout |    ✓   |    —    |      —     |   —   |    —    |    —    |
| REST API                   |    ✓   |    —    |      —     |   —   |    —    |    —    |

---

## JSON schema

Papero exposes a structured representation of the document:

```json
{
  "schema": "pdf-text-api/document@1",
  "engine": "tika+pdfium",
  "page_count": 12,
  "metadata": {
    "title": "...",
    "author": "...",
    "language": "en"
  },
  "pages": [
    {
      "number": 1,
      "width": 595.3,
      "height": 841.9,
      "blocks": [
        {
          "id": "p1-b3",
          "type": "table",
          "bbox": [56.7, 294.8, 481.9, 374.2],
          "rows": [
            ["Model", "Accuracy"],
            ["Base", "0.81"]
          ]
        }
      ]
    }
  ]
}
```

Block types include:

```text
heading
paragraph
list_item
table
figure
formula
caption
code
header
footer
page_number
```

---

## OCR

Scanned PDFs can be processed through Tesseract:

```bash
docker compose up
```

Or configure OCR through Python:

```python
doc = extract(
    "scanned.pdf",
    ocr="auto",
    ocr_language="por+eng",
)
```

Available modes:

```text
auto
force
off
```

---

## Limitations

Papero is intentionally transparent about where its current approach has limitations.

### Complex mathematical notation

Formula reconstruction is based on PDF glyph geometry.

Very complex structures such as:

* large matrices
* stacked fractions
* complex radicals

may not produce perfect LaTeX.

The original formula crop is also available as an image.

### Borderless tables

Tables with very small spacing between columns can sometimes be interpreted as continuous text.

### Browser positioning

The browser implementation depends on the positioning information exposed by pdf.js. Some PDFs with unusual character spacing can therefore behave differently from the server engine.

### Scanned documents

OCR requires the server/Tesseract path.

---

## Development

Clone the repository:

```bash
git clone https://github.com/beatrizalmeidaf/pdf-text-extractor.git
cd pdf-text-extractor
```

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest -q
```

Check formatting:

```bash
ruff check src tests
ruff format --check src tests
```

Run the JavaScript parity tests:

```bash
npm install --prefix tests/js
python tests/js/expected.py tests/js/out
node tests/js/parity.mjs tests/js/out
```

Run the browser locally:

```bash
python -m http.server -d web
```

---

## Project structure

```text
pdf-text-extractor/
├── src/pdf_text_api/     Python engine: layout (PDFium), Tika client, API, CLI
├── web/                  Browser app (GitHub Pages) — engine.js is the JS port
├── tests/                pytest + JS/Python parity test (tests/js)
├── benchmarks/           dataset download + benchmark scripts
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## Contributing

Contributions are welcome.

If you find a PDF that Papero parses incorrectly, a reproducible example is especially useful.

Good issues include:

* incorrect reading order
* table detection failures
* formula reconstruction problems
* character encoding issues
* OCR edge cases
* browser/server parity differences
* performance regressions

---

## Keywords

PDF to Markdown · PDF to JSON · PDF to Word · PDF to Excel · PDF table extraction · PDF parser · document parsing · layout analysis · reading order · multi-column PDF · formula extraction · LaTeX · bounding boxes · OCR · Apache Tika · PDFium · pdf.js · RAG preprocessing · LLM document loader · Docling alternative · Marker alternative · PyMuPDF alternative (MIT)

**Português:** converter PDF para Markdown, Word e Excel · extrair tabelas de PDF · extrair texto de PDF mantendo a formatação · extrair fórmulas de PDF · leitura de PDF em duas colunas · OCR de PDF escaneado · conversor de PDF no navegador sem upload · open source

---

## License

MIT © Beatriz Almeida

---

<p align="center">
  <strong>If Papero is useful to you, consider giving it a star.</strong>
  <br>
  <sub>It helps other developers discover the project.</sub>
</p>

<p align="center">
  <a href="https://github.com/beatrizalmeidaf/pdf-text-extractor">
    GitHub
  </a>
  ·
  <a href="https://beatrizalmeidaf.github.io/pdf-text-extractor/">
    Browser Demo
  </a>
</p>

