// Interface strings in Portuguese and English. Language: ?lang= in the URL, else the last
// choice, else the browser's language. Static text is tagged in index.html with
// data-i18n="key" (text), data-i18n-html="key" (markup) or data-i18n-attr="attr:key;…".

const STRINGS = {
  pt: {
    "page.title": "papero — PDF para Markdown, JSON, Word e Excel, com estrutura",
    "page.description": "Converta PDF em Markdown, JSON, HTML, Word, Excel e CSV direto no navegador, sem enviar o arquivo. Mantém a ordem de leitura, tabelas, fórmulas em LaTeX, imagens e a posição de cada bloco.",
    "brand.tagline": "estrutura de documentos, sem a stack pesada",
    "brand.home": "papero — início",
    "nav.docs": "Documentação",
    "nav.theme": "Alternar tema claro/escuro",
    "nav.lang": "Switch to English",
    "aside.label": "Arquivo e opções",
    "intro.title": "PDF para Markdown, tabelas e fórmulas",
    "intro.text": "Ordem de leitura em colunas, tabelas estruturadas, LaTeX, imagens e a posição de cada bloco. Exporte no formato que precisar.",
    "drop.pdf": "Arraste um PDF aqui",
    "drop.doc": "Arraste um documento aqui",
    "drop.hint": "ou clique para escolher",
    "sample.before": "Sem um PDF à mão?",
    "sample.link": "Use o exemplo",
    "engine.legend": "Motor",
    "engine.label": "Motor de extração",
    "engine.browser": "No navegador",
    "engine.server": "Servidor (Tika)",
    "engine.hint.browser": "Nada sai do seu computador: o PDF é lido aqui mesmo, com pdf.js.",
    "engine.hint.server": "O arquivo vai para a sua API: Tika + PDFium, OCR e outros formatos.",
    "server.url": "URL da API",
    "server.hint": "Suba a sua com <code>docker compose up</code>. Aceita também DOCX, PPTX, XLSX, HTML e EPUB, e faz OCR de escaneados.",
    "options.legend": "Opções",
    "options.pages": "Páginas",
    "options.pages.ph": "todas",
    "options.password": "Senha",
    "options.password.ph": "se houver",
    "options.pages.hint": "Ex.: <code>1-3,5,10-</code>",
    "options.tables": "Tabelas estruturadas<small>com e sem bordas</small>",
    "options.formulas": "Fórmulas em LaTeX<small>sobrescrito, subscrito e símbolos</small>",
    "options.images": "Recortar imagens<small>figuras, tabelas e fórmulas em PNG</small>",
    "run": "Extrair",
    "privacy.browser": "No modo navegador o arquivo não é enviado a lugar nenhum.",
    "privacy.server": "No modo servidor o arquivo é enviado à URL acima e apagado ao fim da requisição.",
    "result.label": "Resultado",
    "tabs.label": "Visualizações",
    "tabs.pages": "Páginas",
    "tabs.tables": "Tabelas",
    "tabs.images": "Imagens",
    "tabs.text": "Texto",
    "copy.md": "Copiar Markdown",
    "export": "Exportar",
    "empty.title": "Escolha um PDF para ver a estrutura",
    "empty.text": "Cada bloco aparece destacado na página, no lugar exato onde está.",
    "empty.list": "<li>Ordem de leitura correta em documentos de duas ou três colunas</li><li>Tabelas com e sem bordas viram linhas e colunas (CSV, Excel)</li><li>Fórmulas com sobrescrito, subscrito e símbolos viram LaTeX</li><li>Figuras, tabelas e fórmulas também saem como imagem recortada</li><li>Cabeçalhos, rodapés e números de página são separados do conteúdo</li>",
    "inspector.title": "Clique num bloco",
    "inspector.hint": "Para ver o tipo, a posição (bbox em pontos, origem no topo) e o conteúdo extraído.",
    "md.mode": "Modo do Markdown",
    "md.rendered": "Visualizar",
    "md.source": "Código",
    "footer.summary": "Como funciona e como usar em código",
    "footer.browser.title": "No navegador",
    "footer.browser.text": "O motor de layout roda em JavaScript sobre o pdf.js: lê a posição exata de cada letra, detecta colunas com um XY-cut que não confunde coluna de texto com coluna de tabela, reconstrói tabelas pelas réguas ou pelo alinhamento e transforma sobrescritos em LaTeX.",
    "footer.server.title": "No servidor",
    "footer.server.text": "O mesmo algoritmo roda em Python sobre o PDFium, em paralelo com o Apache Tika, que adiciona metadados, títulos marcados do PDF, OCR com Tesseract e mais de mil formatos (DOCX, PPTX, XLSX, EPUB…).",
    "footer.python.title": "Em Python",
    "footer.api.title": "Via API",
    "type.heading": "Título", "type.paragraph": "Parágrafo", "type.list_item": "Item de lista",
    "type.table": "Tabela", "type.figure": "Figura", "type.formula": "Fórmula", "type.caption": "Legenda",
    "type.code": "Código", "type.header": "Cabeçalho", "type.footer": "Rodapé", "type.page_number": "Nº de página",
    "stats.pages": "páginas", "stats.headings": "títulos", "stats.tables": "tabelas", "stats.figures": "figuras",
    "stats.formulas": "fórmulas", "stats.engine": "motor", "stats.scanned": "parece escaneado — use o modo servidor com OCR",
    "no.positions": "Este formato não tem páginas com posição (o Tika lê o conteúdo, não o layout). Veja as abas Markdown e Tabelas.",
    "insp.level": "nível", "insp.marker": "marcador", "insp.number": "número", "insp.caption": "legenda",
    "insp.font": "fonte", "insp.bold": "negrito", "insp.empty": "(sem texto)", "insp.crop": "Recorte do bloco",
    "tables.none": "Nenhuma tabela encontrada", "tables.off": " (a detecção está desligada)",
    "tables.title": "Tabela", "tables.copy": "Copiar CSV", "tables.show": "Ver na página", "tables.crop": "Recorte da tabela",
    "images.none": "Nenhuma imagem", "images.off": " — ative “Recortar imagens” nas opções",
    "toast.onlyPdf": "No navegador só PDFs. Para DOCX, PPTX, XLSX ou HTML, use o modo Servidor (Tika).",
    "toast.sample": "Não consegui carregar o exemplo.",
    "toast.failed": "Falha na extração.",
    "toast.server": "Não consegui falar com {url}. A API está no ar e com CORS liberado?",
    "toast.apiError": "Erro {status} na API.",
    "toast.csv": "CSV copiado", "toast.md": "Markdown copiado",
    "toast.noTables": "Nenhuma tabela neste documento — o arquivo sairá vazio.",
    "toast.zip": "Biblioteca de ZIP não carregou; verifique a conexão.",
    "err.encrypted_pdf": "PDF protegido por senha ou senha incorreta.",
    "err.invalid_pdf": "Arquivo não é um PDF válido ou está corrompido.",
    "fmt.md": "Markdown", "fmt.md.hint": "RAG / LLM, com imagens embutidas",
    "fmt.txt": "Texto puro", "fmt.txt.hint": "só o texto, em ordem de leitura",
    "fmt.html": "HTML", "fmt.html.hint": "página única, com alinhamento e posições",
    "fmt.json": "JSON estruturado", "fmt.json.hint": "blocos, bbox, tabelas, LaTeX",
    "fmt.csv": "CSV das tabelas", "fmt.csv.hint": "todas as tabelas",
    "fmt.xlsx": "Excel", "fmt.xlsx.hint": "uma planilha por tabela",
    "fmt.docx": "Word", "fmt.docx.hint": "mantém o layout da página",
    "fmt.zip": "Pacote ZIP", "fmt.zip.hint": "tudo + pasta images/",
  },
  en: {
    "page.title": "papero — PDF to Markdown, JSON, Word and Excel, with structure",
    "page.description": "Convert PDF to Markdown, JSON, HTML, Word, Excel and CSV right in your browser, without uploading the file. Keeps reading order, tables, LaTeX formulas, images and the position of every block.",
    "brand.tagline": "document structure, without the heavyweight stack",
    "brand.home": "papero — home",
    "nav.docs": "Docs",
    "nav.theme": "Toggle light/dark theme",
    "nav.lang": "Mudar para português",
    "aside.label": "File and options",
    "intro.title": "PDF to Markdown, tables and formulas",
    "intro.text": "Reading order across columns, structured tables, LaTeX, images and the position of every block. Export to the format you need.",
    "drop.pdf": "Drop a PDF here",
    "drop.doc": "Drop a document here",
    "drop.hint": "or click to choose",
    "sample.before": "No PDF at hand?",
    "sample.link": "Use the sample",
    "engine.legend": "Engine",
    "engine.label": "Extraction engine",
    "engine.browser": "In the browser",
    "engine.server": "Server (Tika)",
    "engine.hint.browser": "Nothing leaves your computer: the PDF is read right here, with pdf.js.",
    "engine.hint.server": "The file goes to your API: Tika + PDFium, OCR and other formats.",
    "server.url": "API URL",
    "server.hint": "Run yours with <code>docker compose up</code>. It also reads DOCX, PPTX, XLSX, HTML and EPUB, and OCRs scanned pages.",
    "options.legend": "Options",
    "options.pages": "Pages",
    "options.pages.ph": "all",
    "options.password": "Password",
    "options.password.ph": "if any",
    "options.pages.hint": "E.g. <code>1-3,5,10-</code>",
    "options.tables": "Structured tables<small>ruled and borderless</small>",
    "options.formulas": "LaTeX formulas<small>superscripts, subscripts and symbols</small>",
    "options.images": "Crop images<small>figures, tables and formulas as PNG</small>",
    "run": "Extract",
    "privacy.browser": "In browser mode the file is not sent anywhere.",
    "privacy.server": "In server mode the file is sent to the URL above and deleted when the request ends.",
    "result.label": "Result",
    "tabs.label": "Views",
    "tabs.pages": "Pages",
    "tabs.tables": "Tables",
    "tabs.images": "Images",
    "tabs.text": "Text",
    "copy.md": "Copy Markdown",
    "export": "Export",
    "empty.title": "Pick a PDF to see its structure",
    "empty.text": "Every block is outlined on the page, exactly where it sits.",
    "empty.list": "<li>Correct reading order in two- and three-column documents</li><li>Ruled and borderless tables become rows and columns (CSV, Excel)</li><li>Formulas with superscripts, subscripts and symbols become LaTeX</li><li>Figures, tables and formulas also come out as cropped images</li><li>Headers, footers and page numbers are kept apart from the content</li>",
    "inspector.title": "Click a block",
    "inspector.hint": "To see its type, position (bbox in points, origin at the top) and extracted content.",
    "md.mode": "Markdown mode",
    "md.rendered": "Preview",
    "md.source": "Source",
    "footer.summary": "How it works and how to use it from code",
    "footer.browser.title": "In the browser",
    "footer.browser.text": "The layout engine runs in JavaScript on pdf.js: it reads the exact position of every glyph, finds columns with an XY-cut that never mistakes a table column for a text column, rebuilds tables from rules or alignment, and turns superscripts into LaTeX.",
    "footer.server.title": "On the server",
    "footer.server.text": "The same algorithm runs in Python on PDFium, alongside Apache Tika, which adds metadata, tagged-PDF headings, OCR with Tesseract and over a thousand formats (DOCX, PPTX, XLSX, EPUB…).",
    "footer.python.title": "In Python",
    "footer.api.title": "Through the API",
    "type.heading": "Heading", "type.paragraph": "Paragraph", "type.list_item": "List item",
    "type.table": "Table", "type.figure": "Figure", "type.formula": "Formula", "type.caption": "Caption",
    "type.code": "Code", "type.header": "Header", "type.footer": "Footer", "type.page_number": "Page number",
    "stats.pages": "pages", "stats.headings": "headings", "stats.tables": "tables", "stats.figures": "figures",
    "stats.formulas": "formulas", "stats.engine": "engine", "stats.scanned": "looks scanned — use server mode with OCR",
    "no.positions": "This format has no positioned pages (Tika reads the content, not the layout). See the Markdown and Tables tabs.",
    "insp.level": "level", "insp.marker": "marker", "insp.number": "number", "insp.caption": "caption",
    "insp.font": "font", "insp.bold": "bold", "insp.empty": "(no text)", "insp.crop": "Block crop",
    "tables.none": "No tables found", "tables.off": " (detection is off)",
    "tables.title": "Table", "tables.copy": "Copy CSV", "tables.show": "Show on page", "tables.crop": "Crop of table",
    "images.none": "No images", "images.off": " — turn on “Crop images” in the options",
    "toast.onlyPdf": "The browser reads PDFs only. For DOCX, PPTX, XLSX or HTML, use Server (Tika) mode.",
    "toast.sample": "Couldn't load the sample.",
    "toast.failed": "Extraction failed.",
    "toast.server": "Couldn't reach {url}. Is the API up, with CORS allowed?",
    "toast.apiError": "API error {status}.",
    "toast.csv": "CSV copied", "toast.md": "Markdown copied",
    "toast.noTables": "No tables in this document — the file will be empty.",
    "toast.zip": "The ZIP library didn't load; check your connection.",
    "err.encrypted_pdf": "Password-protected PDF, or wrong password.",
    "err.invalid_pdf": "Not a valid PDF, or the file is damaged.",
    "fmt.md": "Markdown", "fmt.md.hint": "RAG / LLM, images embedded",
    "fmt.txt": "Plain text", "fmt.txt.hint": "just the text, in reading order",
    "fmt.html": "HTML", "fmt.html.hint": "single page, with alignment and positions",
    "fmt.json": "Structured JSON", "fmt.json.hint": "blocks, bbox, tables, LaTeX",
    "fmt.csv": "Tables as CSV", "fmt.csv.hint": "every table",
    "fmt.xlsx": "Excel", "fmt.xlsx.hint": "one sheet per table",
    "fmt.docx": "Word", "fmt.docx.hint": "keeps the page's layout",
    "fmt.zip": "ZIP bundle", "fmt.zip.hint": "everything + images/ folder",
  },
};

function initialLang() {
  const fromUrl = new URLSearchParams(location.search).get("lang");
  if (fromUrl && STRINGS[fromUrl]) return fromUrl;
  try {
    const saved = localStorage.getItem("pte-lang");
    if (saved && STRINGS[saved]) return saved;
  } catch { /* private mode */ }
  return (navigator.language || "pt").toLowerCase().startsWith("pt") ? "pt" : "en";
}

export let lang = initialLang();

export function t(key, vars = {}) {
  const s = STRINGS[lang][key] ?? STRINGS.pt[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
}

export function applyStatic(root = document) {
  document.documentElement.lang = lang === "pt" ? "pt-BR" : "en";
  document.title = t("page.title");
  document.querySelector('meta[name="description"]')?.setAttribute("content", t("page.description"));
  root.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  root.querySelectorAll("[data-i18n-html]").forEach((el) => (el.innerHTML = t(el.dataset.i18nHtml)));
  root.querySelectorAll("[data-i18n-attr]").forEach((el) => {
    for (const pair of el.dataset.i18nAttr.split(";")) {
      const [attr, key] = pair.split(":");
      el.setAttribute(attr, t(key));
    }
  });
}

export function setLang(next) {
  lang = STRINGS[next] ? next : "pt";
  try { localStorage.setItem("pte-lang", lang); } catch { /* private mode */ }
  const url = new URL(location.href);
  url.searchParams.set("lang", lang);
  history.replaceState(null, "", url);
  applyStatic();
}
