<p align="center">
  <img src="https://github.com/user-attachments/assets/4795977c-7651-4969-bb32-374fbf3fc7d2" alt="PDF Text Extractor" width="220"/>
</p>

<h1 align="center">PDF Text Extractor</h1>

<p align="center">
  <strong>PDF para Markdown, JSON, Excel e Word — com ordem de leitura, tabelas, fórmulas, imagens e a posição de cada bloco.</strong><br>
  Open source, roda na CPU, sem modelos de IA. Biblioteca Python, CLI, API REST (Apache Tika) e um app web que funciona 100% no navegador.
</p>

<p align="center">
  <a href="https://beatrizalmeidaf.github.io/pdf-text-extractor/"><b>▶ Usar no navegador</b></a> ·
  <a href="#biblioteca-python">Python</a> ·
  <a href="#api-rest">API</a> ·
  <a href="#cli">CLI</a> ·
  <a href="#english">English</a>
</p>

<p align="center">
  <a href="https://github.com/beatrizalmeidaf/pdf-text-extractor/actions/workflows/ci.yml"><img src="https://github.com/beatrizalmeidaf/pdf-text-extractor/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/beatrizalmeidaf/pdf-text-extractor/pkgs/container/pdf-text-extractor"><img src="https://img.shields.io/badge/docker-ghcr.io-2496ED.svg" alt="Docker"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/licen%C3%A7a-MIT-green.svg" alt="MIT"></a>
  <img src="https://img.shields.io/badge/Apache-Tika-D22128.svg" alt="Apache Tika">
  <img src="https://img.shields.io/badge/RAG-ready-8A2BE2.svg" alt="RAG ready">
</p>

---

## O que ele faz

| | |
|---|---|
| **Ordem de leitura** | Documentos de 2 ou 3 colunas lidos coluna a coluna (XY-cut que não confunde coluna de texto com coluna de tabela). |
| **Tabelas estruturadas** | Com bordas (grade do Word), sem bordas (alinhamento) e *booktabs* do LaTeX (só réguas horizontais). Células de várias linhas e linhas mescladas preservadas. Saem como linhas e colunas: Markdown, CSV, Excel. |
| **Fórmulas** | Sobrescrito, subscrito e símbolos viram LaTeX (`E = mc^{2}`, `\sum \alpha \leq \beta`), com o número da equação, mais o recorte da fórmula em PNG. |
| **Imagens** | Figuras, gráficos vetoriais (com eixos, legenda e rótulos), tabelas e fórmulas recortados em PNG — a imagem fica junto da posição de onde veio. |
| **Posição de tudo** | Cada bloco tem `bbox` em pontos (origem no topo da página): dá para desenhar por cima do PDF, citar a origem num RAG ou recortar. |
| **Símbolos e acentos** | Ligaduras (`ﬁ`→`fi`), bullets das fontes Symbol/Wingdings, letras gregas e acentos do LaTeX desenhados à parte (`Computa¸ca˜o` → `Computação`). |
| **Limpeza** | Cabeçalhos, rodapés, números de página e logos repetidos ficam fora do texto (mas continuam no JSON, marcados). Palavras hifenizadas na quebra de linha são unidas. |
| **Qualquer formato** | Pelo Apache Tika: DOCX, PPTX, XLSX, ODT, RTF, EPUB, HTML, e-mails — e **OCR** (Tesseract) em PDFs escaneados. |
| **Exporta para** | Markdown, texto, HTML (com `data-bbox`), JSON, CSV, Excel (.xlsx), Word (.docx) ou um ZIP com tudo + pasta `images/`. |

### Como funciona

Dois motores rodam **ao mesmo tempo** sobre o mesmo arquivo:

- **Apache Tika** (Java) — metadados, títulos marcados do PDF (*tagged PDF*), OCR e todos os formatos que não são PDF. Falamos direto com o Tika Server por conexões persistentes, sem o `tika-python` no caminho: metade da latência.
- **Motor de layout sobre o PDFium** — lê cada glifo com posição, fonte e tamanho, e cada traço e imagem da página, e reconstrói colunas, tabelas, fórmulas, listas e figuras.

O app web usa **o mesmo algoritmo portado para JavaScript sobre o pdf.js** e devolve o mesmo JSON. O CI compara os dois motores bloco a bloco em cada commit.

## Usar no navegador

**[beatrizalmeidaf.github.io/pdf-text-extractor](https://beatrizalmeidaf.github.io/pdf-text-extractor/)** — arraste um PDF e veja cada bloco destacado na página, com abas de Markdown, tabelas, imagens, texto e JSON, e exportação para o formato que quiser. O arquivo **não sai do seu computador**.

Para DOCX/PPTX, OCR de escaneados e o motor completo com Tika, escolha "Servidor (Tika)" e aponte para a sua API (`docker compose up`). A mesma página é servida pela API em `/`.

## Biblioteca Python

```bash
pip install pdf-text-api            # biblioteca + CLI (Java 11+ para o Tika)
pip install "pdf-text-api[api]"     # + servidor HTTP
```

```python
from pdf_text_api import extract, extract_text

doc = extract("artigo.pdf", images=True)       # estruturado (padrão)
print(doc.to_markdown())                        # Markdown pronto para RAG/LLM
doc.tables[0].rows                              # [["Modelo", "Precisão"], ["Base", "0,81"], ...]
doc.formulas[0].latex                           # "E = mc^{2}"
doc.figures[0].image.data                       # PNG da figura
for block in doc.pages[0].blocks:               # tudo, em ordem de leitura, com posição
    print(block.type, block.bbox, block.text[:60])

doc.to_html(); doc.to_dict()                    # HTML com data-bbox, JSON
extract("relatorio.docx").to_markdown()         # qualquer formato que o Tika lê
extract_text("contrato.pdf").text               # só texto, o mais rápido (Tika)
```

Opções de `extract()`: `pages="1-3,5"`, `password=`, `images=True`, `image_scale=2.0`, `tables=`, `formulas=`, `ocr="auto"|"force"|"off"`, `ocr_language="por+eng"`, `tika=False` (só o motor de layout, sem Java), `workers=` (processos para PDFs longos).

O Tika Server é iniciado e aquecido sozinho na primeira chamada (o jar é baixado uma vez). Para usar um servidor já rodando: `PTE_TIKA_URL=http://localhost:9998`.

## CLI

```bash
pdf-text-api extract artigo.pdf -o artigo.md --images   # Markdown + pasta images/
pdf-text-api extract artigo.pdf -o artigo.json           # formato pela extensão
pdf-text-api extract artigo.pdf -f csv -o tabelas.csv    # só as tabelas
pdf-text-api extract artigo.pdf -p 1-5 -f html           # páginas 1 a 5, em HTML
pdf-text-api extract apresentacao.pptx                   # qualquer formato do Tika
pdf-text-api extract contrato.pdf --fast                 # só texto, via Tika
pdf-text-api serve --port 8000                           # API + app web
```

## API REST

```bash
docker compose up        # API + Tika + Tesseract + app web em http://localhost:8000
```

```bash
curl -F "file=@artigo.pdf" "localhost:8000/v1/extract?format=markdown"
curl -F "file=@artigo.pdf" "localhost:8000/v1/extract?format=zip&images=true" -o artigo.zip
curl -F "file=@artigo.pdf" "localhost:8000/v1/extract?per_page=true"          # JSON com blocos e bbox
```

Um endpoint: `POST /v1/extract`, arquivo no campo `file` (multipart). Documentação interativa em `/docs`.

| Parâmetro | Padrão | O que faz |
|---|---|---|
| `mode` | `structured` | `structured` (layout + Tika) ou `fast` (só texto, Tika) |
| `format` | `json` | `json`, `markdown`, `text`, `html`, `csv` (tabelas), `zip` (tudo + imagens) |
| `pages` | todas | `1-3,5,10-` |
| `per_page` | `false` | JSON: incluir as páginas com os blocos e suas posições |
| `images` | `false` | Recortar figuras, tabelas e fórmulas em PNG |
| `tables` / `formulas` | `true` | Detectar tabelas / fórmulas |
| `ocr` | `auto` | `auto` (só páginas escaneadas), `force`, `off` |
| `ocr_language` | `por+eng` | Idiomas do Tesseract |
| `password` (form) | — | Senha do PDF |

Formato do JSON (o mesmo da biblioteca e do app web):

```json
{
  "schema": "pdf-text-api/document@1",
  "engine": "tika+pdfium",
  "page_count": 12,
  "metadata": { "title": "…", "author": "…", "language": "pt" },
  "timings": { "layout_ms": 120.4, "tika_ms": 48.1, "total_ms": 122.9 },
  "markdown": "# Título\n\n…",
  "pages": [{
    "number": 1, "width": 595.3, "height": 841.9,
    "blocks": [
      { "id": "p1-b3", "type": "table", "bbox": [56.7, 294.8, 481.9, 374.2],
        "rows": [["Modelo", "Precisão"], ["Base", "0,81"]],
        "caption": "Tabela 1: Comparação entre modelos.",
        "image": { "name": "p1-table-1.png", "mime": "image/png", "data": "iVBOR…" } },
      { "id": "p1-b4", "type": "formula", "bbox": […], "text": "E = mc²",
        "latex": "E = mc^{2}", "number": "(1)" }
    ]
  }]
}
```

Tipos de bloco: `heading` (com `level`), `paragraph`, `list_item` (com `marker`), `table`, `figure`, `formula`, `caption`, `code`, e os que ficam fora do texto: `header`, `footer`, `page_number`.

Erros sempre como `{"error": {"code", "message"}}`: `empty_file` (400), `unauthorized` (401), `file_too_large`/`too_many_pages` (413), `invalid_pdf`/`encrypted_pdf`/`invalid_page_range`/`parser_crashed` (422), `rate_limited` (429), `busy`/`tika_unavailable` (503), `timeout` (504).

### Latência

- O Tika e o layout rodam **em paralelo**: o tempo é o maior dos dois, não a soma.
- Conexões *keep-alive* com o Tika Server e JVM aquecida na inicialização.
- Páginas de documentos longos são divididas entre processos (`PTE_WORKERS`).
- Uploads repetidos com as mesmas opções saem do cache em memória (header `X-Cache: hit`).
- `Server-Timing` traz o tempo de cada etapa.

Configuração por variáveis de ambiente — veja [`.env.example`](.env.example) (limites, chaves de API, rate limit, CORS, cache, Tika externo).

## Desempenho (Massive Benchmark)

Testado com um dataset real de **50 PDFs acadêmicos** baixados do **arXiv** (papers densos de Inteligência Artificial, média de 15 páginas, em múltiplas colunas e com equações matemáticas). 

> **Metodologia Importante:** Todos os testes abaixo foram executados estritamente em **CPU local**, sem uso de nenhuma aceleração por placa de vídeo (GPU), simulando ambientes de servidores comuns e lambdas.

O motor TikaClient otimizado roda na JVM com `keep-alive` habilitado e anti-kerning acionado.

| Ferramenta | Tempo Total (Estimado 50 Papers) | Tempo Médio/PDF | Características |
|:---|---:|---:|:---|
| **PyMuPDF** (C++) | 4.86s | 97.23 ms | Apenas texto bruto e caótico; perde parágrafos e tabelas |
| **PDF Text Extractor** (modo `fast`) | **6.78s** | **135.65 ms** | **Retorna Markdown limpo estruturado; roda em qualquer OS** |
| **PyPDF** (Python) | 1m 16s | 1520.24 ms | Engine padrão, quebra linhas no meio e é lenta |
| **pdfplumber** (Python) | 2m 57s | 3555.92 ms | Extração focada em visual/tabelas, mas pesada na CPU |
| **Docling (IBM)** (PyTorch/C++) | ~1h 09m | 82880.45 ms | Extremamente lento em CPU (~83s/paper). Possui bugs com acentuação no Windows (necessita bypass) |

![Gráfico de Desempenho](benchmarks/benchmark_results.png)

> **Nota:** Estes são **PDFs densos do arXiv** (dataset DocBank). Nosso extrator usando Tika processa a impressionante marca de **~9ms por página**, enquanto as ferramentas hypadas baseadas em IA (Docling) gastam literalmente mais de 1 minuto inteiro por PDF rodando na CPU, além de serem difíceis de configurar localmente.

Rode você mesmo testando com seus PDFs ou baixando os papers:
```bash
python benchmarks/download_arxiv_pdfs.py
python benchmarks/run_massive_benchmark.py
```

### Como nos comparamos com outras ferramentas?

Se você está construindo pipelines de **RAG** ou alimentando **LLMs**, o mercado geralmente força uma escolha entre **Velocidade Bruta** ou **Fidelidade de Estrutura**. O `pdf-text-extractor` foi desenhado para ser o meio-termo perfeito:

1. **Ferramentas de IA (Docling / Marker):** Lentas (chegam a mais de 1.5s por página) e dão crash em pastas locais do Windows sem placa de vídeo (dependem do PyTorch). São excelentes para layouts caóticos se você tiver GPUs caras.
2. **Bibliotecas de Baixo Nível (PyMuPDF):** Rápido (6ms) mas perde a semântica do Markdown e junta colunas desordenadas.
3. **Nosso Extrator (TikaClient):** Roda em **~134 ms por paper acadêmico (~9 ms por página)** em processadores comuns e utiliza heurísticas na engine do Tika para devolver o texto já formatado em **Markdown Estruturado**. É o *sweet spot* ideal para produção.

### Modo estruturado no mesmo dataset

Medido com o modo estruturado (`extract(..., tika=False)`, um processo, CPU de notebook) nos **54 PDFs do arXiv** de `benchmarks/dataset`:

| | |
|---|---|
| Falhas | **0 de 54** |
| Tempo por página (mediana / p90) | **34 ms / 57 ms** |
| Blocos encontrados | 9.259 parágrafos, 762 títulos, 1.412 itens de lista, 286 tabelas, 499 figuras, 738 fórmulas, 385 legendas |

Com o Tika ligado, o tempo total quase não muda: ele roda em paralelo ao layout. No modo `fast` (só texto via Tika), o cliente próprio responde em ~10–17 ms um PDF de 1–3 páginas, contra ~31–37 ms do `tika-python` (mesmo servidor, aquecido).

### Comparação de recursos

| | Este projeto | PyMuPDF | pdfplumber | pypdf | Docling | Marker |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Licença | MIT | AGPL | MIT | BSD | MIT | GPL |
| Precisa de modelos de IA / PyTorch | não | não | não | não | sim | sim |
| Ordem de leitura em colunas | ✓ | parcial | — | — | ✓ | ✓ |
| Tabelas estruturadas | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Fórmulas em LaTeX | aproximado (glifos) | — | — | — | ✓ (modelo) | ✓ (modelo) |
| Posição (bbox) de cada bloco | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| DOCX/PPTX/XLSX/EPUB/HTML | ✓ (Tika) | parcial | — | — | ✓ | parcial |
| OCR de escaneados | ✓ (Tika + Tesseract) | ✓ | — | — | ✓ | ✓ |
| Roda inteiro no navegador | ✓ | — | — | — | — | — |
| API REST pronta (Docker) | ✓ | — | — | — | — | — |

Onde as ferramentas com modelos de IA ganham: layouts muito irregulares, fórmulas complexas (frações empilhadas, matrizes) e tabelas sem nenhuma pista visual. Aqui a fórmula sai em LaTeX montado a partir dos glifos **e** como imagem recortada, para você escolher.

## Limitações conhecidas

- **Fórmulas**: o LaTeX é montado a partir dos glifos (símbolos, sobrescrito, subscrito). Frações empilhadas, matrizes e raízes grandes saem lineares — use o recorte PNG da fórmula.
- **Tabelas sem bordas com colunas muito próximas** (vão menor que ~1 em entre colunas) podem ser lidas como texto corrido.
- **Motor do navegador**: o pdf.js não informa a posição de cada glifo, então textos com espaçamento entre letras (`T Í T U L O`) podem sair com espaços a mais; o modo servidor não tem esse problema. OCR só no modo servidor.
- **PDFs escaneados** precisam do Tesseract (já incluso na imagem Docker); a resposta sinaliza com `likely_scanned`.
- Cabeçalhos e rodapés repetidos são detectados a partir de 2 páginas.

## Desenvolvimento

```bash
pip install -e ".[dev]"
pytest -q                       # Python (inclui casos reais: booktabs, gráficos, acentos do LaTeX…)
ruff check . && ruff format --check .
npm install --prefix tests/js && python tests/js/expected.py tests/js/out && node tests/js/parity.mjs tests/js/out
python -m http.server -d web    # app web em http://localhost:8000
```

O app web é estático (HTML + JS, sem build) e é publicado no GitHub Pages pelo workflow `pages.yml` — ative em *Settings → Pages → Source: GitHub Actions*.

## Palavras-chave

PDF para Markdown · PDF to Markdown · PDF to JSON · PDF para Excel · PDF para Word · extrair tabelas de PDF · PDF table extraction · extrair texto de PDF · PDF text extraction · PDF parser Python · document parsing · layout analysis · reading order · multi-column PDF · extrair fórmulas LaTeX de PDF · PDF math extraction · extrair imagens de PDF · bounding boxes · OCR PDF · Apache Tika · PDFium · pdf.js · RAG preprocessing · LLM document loader · chunking · conversor de PDF online sem upload · open source · self-hosted · FastAPI · Docker · alternativa ao Docling · alternativa ao Marker · alternativa ao PyMuPDF (MIT)

Tópicos sugeridos para o repositório (*About → Topics*): `pdf` `pdf-to-markdown` `pdf-to-json` `pdf-parser` `pdf-extraction` `table-extraction` `layout-analysis` `document-parsing` `ocr` `apache-tika` `pdfium` `pdfjs` `rag` `llm` `markdown` `latex` `fastapi` `python` `open-source`

## English

**PDF Text Extractor** turns PDFs into Markdown, JSON, Excel and Word while keeping the structure: reading order across columns, ruled/unruled/booktabs tables, formulas as LaTeX, cropped images of figures/tables/formulas and the bounding box of every block. It runs Apache Tika (metadata, tagged-PDF headings, OCR, DOCX/PPTX/XLSX/EPUB/HTML) in parallel with a PDFium layout engine, with no ML models and on CPU only. The same engine, ported to JavaScript on pdf.js, powers a [browser app](https://beatrizalmeidaf.github.io/pdf-text-extractor/) where files never leave your machine. Available as a Python library (`pip install pdf-text-api`), a CLI, a REST API (`docker compose up`) and a web app. MIT licensed.

## Licença

[MIT](LICENSE) © Beatriz Almeida
