// Renderers and file exporters for the document JSON — a port of src/pdf_text_api/render.py
// plus XLSX/DOCX writers (plain OOXML zipped with JSZip, no heavy dependencies).

const FURNITURE = new Set(["header", "footer", "page_number"]);
const BOM = String.fromCharCode(0xfeff); // lets Notepad/Excel detect UTF-8 (accents)
const BULLET_CHARS = "•◦▪▫‣⁃●○■□–—*✓✔➢➤►▶·-";

export const contentBlocks = (page) => page.blocks.filter((b) => !FURNITURE.has(b.type));
export const allBlocks = (doc) => doc.pages.flatMap((p) => p.blocks);
export const tablesOf = (doc) => allBlocks(doc).filter((b) => b.type === "table" && b.rows);
export const imagesOf = (doc) => allBlocks(doc).filter((b) => b.image && b.image.data);

// ---------------------------------------------------------------- text
export function blocksToText(blocks) {
  return blocks
    .map((b) => {
      if (b.type === "table" && b.rows) return b.rows.map((r) => r.map((c) => c.replace(/\n/g, " ")).join("\t")).join("\n");
      if (b.type === "list_item") return "  ".repeat(b.level || 0) + `${b.marker || "-"} ${b.text}`;
      if (b.type === "formula") return b.text + (b.number ? `  ${b.number}` : "");
      return b.text || "";
    })
    .filter((t) => t.trim())
    .join("\n\n");
}
export const toText = (doc) => doc.pages.map((p) => blocksToText(contentBlocks(p))).filter((t) => t.trim()).join("\n\n");

// ---------------------------------------------------------------- markdown
const mdCell = (t) => String(t).replace(/\|/g, "\\|").replace(/\n/g, "<br>").trim();
export function mdTable(rows) {
  const width = Math.max(...rows.map((r) => r.length));
  const full = rows.map((r) => [...r, ...Array(width - r.length).fill("")]);
  return [
    "| " + full[0].map(mdCell).join(" | ") + " |",
    "|" + Array(width).fill("---").join("|") + "|",
    ...full.slice(1).map((r) => "| " + r.map(mdCell).join(" | ") + " |"),
  ].join("\n");
}
function imageMd(b, images, alt) {
  if (!b.image || images === "none") return null;
  if (images === "embed" && b.image.data) return `![${alt}](data:${b.image.mime};base64,${b.image.data})`;
  return `![${alt}](images/${b.image.name})`;
}
// Words printed inside a figure (legend, axis titles) help search; bare tick values don't.
export function figureWords(text) {
  return text
    .split("\n")
    .map((ln) => ln.split(/\s+/).filter((t) => t && !/^[-+−]?[\d.,%]+$/.test(t)).join(" "))
    .filter((ln) => /\p{L}/u.test(ln));
}
export function blockMarkdown(b, images = "ref") {
  switch (b.type) {
    case "heading":
      return "#".repeat(Math.min(6, Math.max(1, b.level || 2))) + " " + b.text;
    case "list_item": {
      let marker = b.marker || "-";
      if (BULLET_CHARS.includes(marker[0])) marker = "-";
      return "  ".repeat(b.level || 0) + `${marker} ${b.text}`;
    }
    case "table":
      return b.rows ? mdTable(b.rows) : b.text;
    case "formula": {
      const tag = b.number ? ` \\tag{${b.number.replace(/[()]/g, "")}}` : "";
      return `$$\n${b.latex || b.text}${tag}\n$$`;
    }
    case "figure": {
      const alt = (b.caption || "figura").replace(/]/g, ")").replace(/\n/g, " ").slice(0, 120);
      let out = imageMd(b, images, alt) || `<!-- figura: ${alt} -->`;
      const words = figureWords(b.text || "");
      if (words.length) out += "\n\n" + words.map((l) => `> ${l}`).join("\n");
      return out;
    }
    case "caption":
      return `*${b.text}*`;
    case "code":
      return "```\n" + b.text + "\n```";
    default:
      return b.text || "";
  }
}
export function toMarkdown(doc, { images = "ref", pageBreaks = false } = {}) {
  const out = [];
  doc.pages.forEach((page) => {
    if (pageBreaks && out.length) out.push(`<!-- página ${page.number} -->`);
    let prev = null;
    for (const b of contentBlocks(page)) {
      const md = blockMarkdown(b, images);
      if (!md.trim()) continue;
      if (prev && prev.type === "list_item" && b.type === "list_item" && out.length) out[out.length - 1] += "\n" + md;
      else out.push(md);
      prev = b;
    }
  });
  return out.join("\n\n").trim() + "\n";
}

// ---------------------------------------------------------------- html
export const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

export function blockHtml(b, images = "embed") {
  const bbox = b.bbox ? b.bbox.map((v) => v.toFixed(1)).join(",") : "";
  const a = ` id="${esc(b.id)}" data-type="${b.type}" data-bbox="${bbox}"`;
  switch (b.type) {
    case "heading": {
      const l = Math.min(6, Math.max(1, b.level || 2));
      return `<h${l}${a}>${esc(b.text)}</h${l}>`;
    }
    case "list_item":
      return `<p${a} style="margin-left:${(b.level || 0) * 1.5}rem">${esc(b.marker || "•")} ${esc(b.text)}</p>`;
    case "table": {
      if (!b.rows) return `<p${a}>${esc(b.text)}</p>`;
      const head = b.rows[0].map((c) => `<th>${esc(c)}</th>`).join("");
      const body = b.rows.slice(1).map((r) => "<tr>" + r.map((c) => `<td>${esc(c)}</td>`).join("") + "</tr>").join("");
      const cap = b.caption ? `<caption>${esc(b.caption)}</caption>` : "";
      return `<table${a}>${cap}<thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
    }
    case "formula":
      return `<div class="formula"${a} data-latex="${esc(b.latex || "")}">\\[${esc(b.latex || b.text)}\\]${b.number ? ` <span>${esc(b.number)}</span>` : ""}</div>`;
    case "figure": {
      let src = "";
      if (b.image && images !== "none") src = images === "embed" && b.image.data ? `data:${b.image.mime};base64,${b.image.data}` : `images/${b.image.name}`;
      return `<figure${a}>${src ? `<img src="${src}" alt="${esc(b.caption || "figura")}">` : ""}${b.caption ? `<figcaption>${esc(b.caption)}</figcaption>` : ""}</figure>`;
    }
    case "caption":
      return `<p${a}><em>${esc(b.text)}</em></p>`;
    case "code":
      return `<pre${a}><code>${esc(b.text)}</code></pre>`;
    default:
      return `<p${a}>${esc(b.text)}</p>`;
  }
}
const HTML_STYLE = `body{font:16px/1.6 system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem;color:#1f2328}
section.page{border-top:1px solid #d0d7de;padding-top:1rem;margin-top:2rem}section.page>h6{color:#656d76;font-weight:500;margin:0 0 1rem}
table{border-collapse:collapse;margin:1rem 0}td,th{border:1px solid #d0d7de;padding:.3rem .6rem;vertical-align:top}th{background:#f6f8fa}
figure{margin:1rem 0}figure img{max-width:100%}figcaption{color:#656d76;font-size:.9em}
.formula{overflow-x:auto;padding:.5rem 1rem;background:#f6f8fa;border-radius:6px;font-family:ui-monospace,monospace}
pre{background:#f6f8fa;padding:1rem;border-radius:6px;overflow-x:auto}`;
export function toHtml(doc, { images = "embed", title } = {}) {
  const t = title || doc.metadata?.title || "Documento";
  const pages = doc.pages
    .map((p) => `<section class="page" data-page="${p.number}" data-width="${p.width}" data-height="${p.height}"><h6>Página ${p.number}</h6>\n${contentBlocks(p).map((b) => blockHtml(b, images)).join("\n")}\n</section>`)
    .join("\n");
  return `<!doctype html>\n<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(t)}</title><style>${HTML_STYLE}</style></head><body>\n${pages}\n</body></html>\n`;
}

// ---------------------------------------------------------------- csv
const csvCell = (v) => (/[",\n\r;]/.test(v) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
export function tablesCsv(doc) {
  return tablesOf(doc)
    .map((t, k) => {
      const page = t.id ? t.id.split("-")[0].slice(1) : "?";
      const head = csvCell(`# página ${page}, tabela ${k + 1}${t.caption ? ": " + t.caption : ""}`);
      return [head, ...t.rows.map((r) => r.map(csvCell).join(","))].join("\r\n");
    })
    .join("\r\n\r\n");
}

// ---------------------------------------------------------------- json
export function toJson(doc, { embedImages = true } = {}) {
  const copy = structuredClone(doc);
  copy.text = toText(doc);
  copy.markdown = toMarkdown(doc, { images: "ref" });
  if (!embedImages) for (const b of allBlocks(copy)) if (b.image) delete b.image.data;
  return JSON.stringify(copy, null, 2);
}

// ---------------------------------------------------------------- xlsx (one sheet per table)
const xmlEsc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "");
const colName = (i) => { let s = ""; for (i++; i; i = Math.floor((i - 1) / 26)) s = String.fromCharCode(65 + ((i - 1) % 26)) + s; return s; };
export async function toXlsx(doc) {
  const tables = tablesOf(doc);
  const zip = new JSZip();
  const sheets = tables.length ? tables : [{ rows: [["Nenhuma tabela encontrada"]] }];
  const numeric = /^-?\d{1,15}([.,]\d+)?$/;
  sheets.forEach((t, k) => {
    const rows = t.rows.map((r, ri) =>
      `<row r="${ri + 1}">` + r.map((c, ci) => {
        const ref = `${colName(ci)}${ri + 1}`;
        const v = String(c ?? "");
        if (ri > 0 && numeric.test(v.trim())) return `<c r="${ref}"><v>${v.trim().replace(",", ".")}</v></c>`;
        return `<c r="${ref}" t="inlineStr"${ri === 0 ? ' s="1"' : ""}><is><t xml:space="preserve">${xmlEsc(v)}</t></is></c>`;
      }).join("") + "</row>").join("");
    zip.file(`xl/worksheets/sheet${k + 1}.xml`,
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${rows}</sheetData></worksheet>`);
  });
  const names = sheets.map((t, k) => {
    const page = t.id ? t.id.split("-")[0].slice(1) : "";
    return xmlEsc(`Tabela ${k + 1}${page ? " (p" + page + ")" : ""}`.slice(0, 31));
  });
  zip.file("[Content_Types].xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>${sheets.map((_, k) => `<Override PartName="/xl/worksheets/sheet${k + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join("")}</Types>`);
  zip.file("_rels/.rels", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`);
  zip.file("xl/workbook.xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>${names.map((n, k) => `<sheet name="${n}" sheetId="${k + 1}" r:id="rId${k + 1}"/>`).join("")}</sheets></workbook>`);
  zip.file("xl/_rels/workbook.xml.rels", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${sheets.map((_, k) => `<Relationship Id="rId${k + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${k + 1}.xml"/>`).join("")}<Relationship Id="rId${sheets.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`);
  zip.file("xl/styles.xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf fontId="0"/><xf fontId="1" applyFont="1"/></cellXfs></styleSheet>`);
  return zip.generateAsync({ type: "blob", mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

// ---------------------------------------------------------------- docx
export async function toDocx(doc) {
  const zip = new JSZip();
  const media = [];
  const run = (t, props = "") => `<w:r>${props ? `<w:rPr>${props}</w:rPr>` : ""}<w:t xml:space="preserve">${xmlEsc(t)}</w:t></w:r>`;
  const para = (inner, style) => `<w:p>${style ? `<w:pPr><w:pStyle w:val="${style}"/></w:pPr>` : ""}${inner}</w:p>`;
  const EMU = 9525; // per pixel at 96 dpi
  const imageXml = (img, id) => {
    const maxW = 600;
    const w = Math.min(maxW, img.width / 2), h = (img.height / 2) * (w / (img.width / 2));
    const cx = Math.round(w * EMU), cy = Math.round(h * EMU);
    return `<w:r><w:drawing><wp:inline><wp:extent cx="${cx}" cy="${cy}"/><wp:docPr id="${id}" name="${xmlEsc(img.name)}"/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="${id}" name="${xmlEsc(img.name)}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rImg${id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="${cx}" cy="${cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>`;
  };
  const body = [];
  for (const page of doc.pages) {
    for (const b of contentBlocks(page)) {
      switch (b.type) {
        case "heading": body.push(para(run(b.text), `Heading${Math.min(6, Math.max(1, b.level || 2))}`)); break;
        case "list_item": body.push(para(run(`${"   ".repeat(b.level || 0)}${b.marker || "•"} ${b.text}`), "ListParagraph")); break;
        case "table": {
          if (!b.rows) break;
          const width = Math.max(...b.rows.map((r) => r.length));
          const rows = b.rows.map((r, ri) => `<w:tr>${[...r, ...Array(width - r.length).fill("")].map((c) =>
            `<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr>${String(c).split("\n").map((ln) => para(run(ln, ri === 0 ? "<w:b/>" : ""))).join("")}</w:tc>`).join("")}</w:tr>`).join("");
          body.push(`<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/><w:tblBorders>${["top", "left", "bottom", "right", "insideH", "insideV"].map((s) => `<w:${s} w:val="single" w:sz="4" w:space="0" w:color="999999"/>`).join("")}</w:tblBorders></w:tblPr>${rows}</w:tbl>`);
          if (b.caption) body.push(para(run(b.caption, "<w:i/>"), "Caption"));
          break;
        }
        case "formula": body.push(para(run(b.latex || b.text, '<w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/>') + (b.number ? run("  " + b.number) : ""))); break;
        case "figure":
          if (b.image?.data) {
            media.push(b.image);
            body.push(para(imageXml(b.image, media.length)));
          }
          if (b.caption) body.push(para(run(b.caption, "<w:i/>"), "Caption"));
          break;
        case "caption": body.push(para(run(b.text, "<w:i/>"), "Caption")); break;
        case "code": for (const ln of b.text.split("\n")) body.push(para(run(ln, '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>'))); break;
        default: if (b.text) body.push(para(run(b.text)));
      }
    }
  }
  media.forEach((img, k) => zip.file(`word/media/image${k + 1}.png`, img.data, { base64: true }));
  const W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"';
  zip.file("word/document.xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document ${W}><w:body>${body.join("")}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>`);
  const headingStyles = [1, 2, 3, 4, 5, 6].map((l) => `<w:style w:type="paragraph" w:styleId="Heading${l}"><w:name w:val="heading ${l}"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="80"/><w:outlineLvl w:val="${l - 1}"/></w:pPr><w:rPr><w:b/><w:sz w:val="${[40, 32, 28, 26, 24, 22][l - 1]}"/></w:rPr></w:style>`).join("");
  zip.file("word/styles.xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles ${W}><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="22"/><w:lang w:val="pt-BR"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>${headingStyles}<w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360"/><w:spacing w:after="40"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="caption"/><w:basedOn w:val="Normal"/><w:rPr><w:i/><w:color w:val="555555"/><w:sz w:val="20"/></w:rPr></w:style><w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblCellMar><w:left w:w="108" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style></w:styles>`);
  zip.file("word/_rels/document.xml.rels", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>${media.map((_, k) => `<Relationship Id="rImg${k + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image${k + 1}.png"/>`).join("")}</Relationships>`);
  zip.file("_rels/.rels", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>`);
  zip.file("[Content_Types].xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>`);
  return zip.generateAsync({ type: "blob", mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
}

// ---------------------------------------------------------------- zip bundle
export async function toZip(doc, stem) {
  const zip = new JSZip();
  zip.file(`${stem}.md`, toMarkdown(doc, { images: "ref" }));
  zip.file(`${stem}.txt`, toText(doc));
  zip.file(`${stem}.html`, toHtml(doc, { images: "ref" }));
  zip.file(`${stem}.json`, toJson(doc, { embedImages: false }));
  if (tablesOf(doc).length) zip.file(`${stem}-tabelas.csv`, "\uFEFF" + tablesCsv(doc));
  for (const b of imagesOf(doc)) zip.file(`images/${b.image.name}`, b.image.data, { base64: true });
  return zip.generateAsync({ type: "blob", mimeType: "application/zip" });
}

// ---------------------------------------------------------------- formats registry
export const FORMATS = [
  { id: "md", label: "Markdown", ext: "md", hint: "RAG / LLM, com imagens embutidas" },
  { id: "txt", label: "Texto puro", ext: "txt", hint: "só o texto, em ordem de leitura" },
  { id: "html", label: "HTML", ext: "html", hint: "página única, com posições (data-bbox)" },
  { id: "json", label: "JSON estruturado", ext: "json", hint: "blocos, bbox, tabelas, LaTeX" },
  { id: "csv", label: "CSV das tabelas", ext: "csv", hint: "todas as tabelas" },
  { id: "xlsx", label: "Excel", ext: "xlsx", hint: "uma planilha por tabela" },
  { id: "docx", label: "Word", ext: "docx", hint: "títulos, listas, tabelas e figuras" },
  { id: "zip", label: "Pacote ZIP", ext: "zip", hint: "tudo + pasta images/" },
];

export async function exportAs(doc, format, stem) {
  const text = (s, type) => new Blob([s], { type: `${type};charset=utf-8` });
  switch (format) {
    case "md": return text(toMarkdown(doc, { images: "embed" }), "text/markdown");
    case "txt": return text(BOM + toText(doc), "text/plain"); // BOM: Notepad/Excel read UTF-8
    case "html": return text(toHtml(doc, { images: "embed" }), "text/html");
    case "json": return text(toJson(doc, { embedImages: true }), "application/json");
    case "csv": return text("\uFEFF" + tablesCsv(doc), "text/csv");
    case "xlsx": return toXlsx(doc);
    case "docx": return toDocx(doc);
    case "zip": return toZip(doc, stem);
    default: throw new Error(`Formato desconhecido: ${format}`);
  }
}
