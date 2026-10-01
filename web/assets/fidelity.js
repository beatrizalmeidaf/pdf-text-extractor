// Fidelity signals — the browser side of src/papero_extract/fidelity.py, on the document
// JSON (so it works with either engine). Heuristic checks, not accuracy: there is no ground
// truth for an arbitrary PDF. Thresholds share their names with fidelity.py: keep in sync.
//
// Besides the report, `assess()` says *where* each problem is — the words of the PDF that
// are not in the output and the blocks that failed a check — for the compare view to draw.

export const SIGNALS = ["text", "reading_order", "tables", "figures", "formulas"];
const WEIGHTS = { text: 0.4, reading_order: 0.2, tables: 0.15, figures: 0.1, formulas: 0.15 };
const TEXT_ERROR = 0.8, TEXT_WARNING = 0.95; // share of the page's words found in the output
const TEXT_MIN = 200; // characters of text on a page before its share means anything
const ORDER_ERROR = 0.1; // share of block-to-block steps that go backwards
const GARBLED_ERROR = 0.05, GARBLED_WARNING = 0.005; // share of characters with no Unicode value
const FURNITURE = new Set(["header", "footer", "page_number"]);
const TOKEN = /[\p{L}\p{N}]+/gu;
const TABLE_CAPTION = /^(tab(ela|le)?|quadro)(?![\p{L}\p{N}_])/iu;
const FIGURE_CAPTION = /^(fig(ura|ure)?|gr[aá]fico|chart)(?![\p{L}\p{N}_])/iu;

// ---------------------------------------------------------------- reference text
// What pdf.js reads on each page, with no layout analysis: Map(page number -> [{ str, box }]),
// boxes in points with the origin at the top-left, like the blocks' bbox.
export async function referenceItems(pdf, numbers) {
  const out = new Map();
  for (const number of numbers) {
    const page = await pdf.getPage(number);
    const m = page.getViewport({ scale: 1, rotation: 0 }).transform;
    const content = await page.getTextContent();
    const items = [];
    for (const it of content.items) {
      if (!it.str || !it.str.trim()) continue;
      const t = it.transform;
      const a = m[0] * t[0] + m[2] * t[1], b = m[1] * t[0] + m[3] * t[1];
      const c = m[0] * t[2] + m[2] * t[3], d = m[1] * t[2] + m[3] * t[3];
      const x = m[0] * t[4] + m[2] * t[5] + m[4], y = m[1] * t[4] + m[3] * t[5] + m[5];
      const h = Math.hypot(c, d) || it.height || 1;
      const upright = Math.abs(a) >= Math.abs(b);
      items.push({ str: it.str, box: upright ? [x, y - h, x + it.width, y + h * 0.25] : [x - h, y - it.width, x + h * 0.25, y] });
    }
    out.set(number, items);
  }
  return out;
}

// Case, accents and ligatures out of the way: "ﬁ" = "fi", "´e" = "é" = "e".
// An exponent is a number of its own: "10⁹" is "10" and "9", as the PDF has them.
const SCRIPTS = /([\u00b2\u00b3\u00b9\u2070-\u209f]+)/g;
const fold = (text) => text.replace(SCRIPTS, " $1 ").normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase();
const tokens = (text) => fold(text).match(TOKEN) || [];

function pageOutput(page) {
  const parts = [];
  for (const b of page.blocks) {
    parts.push(b.text || "", b.caption || "", b.number || "", b.marker || "");
    for (const row of b.rows || []) parts.push(...row);
  }
  return parts.join("\n");
}

// Words of the reference found in the output, item by item: { matched, total, missing: [box] }.
function coverage(items, output) {
  const have = new Map();
  const out = tokens(output);
  for (const t of out) have.set(t, (have.get(t) || 0) + 1);
  // Without separators: a word hyphenated at a line end, or split by an accent drawn as its
  // own glyph, is still there — and so is "10⁹" read as "109". Not for short numbers: "30" is
  // inside too many other things, and the cells of a lost table would all be "found".
  const stream = out.join("");
  let matched = 0, total = 0;
  const missing = [];
  for (const item of items) {
    let own = 0, found = 0;
    for (const token of tokens(item.str)) {
      if (token.length < 2) continue;
      own += token.length;
      if (have.get(token) > 0) { have.set(token, have.get(token) - 1); found += token.length; }
      else if (!/^\p{Nd}{1,2}$/u.test(token) && stream.includes(token)) found += token.length;
    }
    total += own;
    matched += found;
    if (own && found < own * 0.5) missing.push(item.box);
  }
  return { matched, total, missing };
}

function garbled(text) {
  let n = 0;
  for (const ch of text) {
    const c = ch.codePointAt(0);
    if (c === 0xfffd || (c >= 0xe000 && c <= 0xf8ff) || (c < 0x20 && c !== 10 && c !== 9)) n++;
  }
  return n;
}

// ---------------------------------------------------------------- geometry
// `b` is read after `a` but sits wholly above it in the same column.
function backwards(a, b) {
  if (b.bbox[3] > a.bbox[1] + 2) return false;
  const overlap = Math.min(a.bbox[2], b.bbox[2]) - Math.max(a.bbox[0], b.bbox[0]);
  const narrow = Math.min(a.bbox[2] - a.bbox[0], b.bbox[2] - b.bbox[0]);
  return narrow > 0 && overlap > narrow * 0.5;
}

const area = (b) => (b.bbox[2] - b.bbox[0]) * (b.bbox[3] - b.bbox[1]);
// The JSON has no line count: a block taller than a line and a half of its own type is several.
const multiLine = (b) => b.bbox[3] - b.bbox[1] > (b.format?.leading || (b.style?.size || 10) * 1.2) * 1.6;

// Two blocks on the same spot. A one-line block inside another is how a run-in heading or
// the tail of a reference looks, so only tables and multi-line blocks count.
function overlaps(a, b) {
  const small = area(a) <= area(b) ? a : b;
  if (a.type !== "table" && b.type !== "table" && !multiLine(small)) return false;
  const w = Math.min(a.bbox[2], b.bbox[2]) - Math.max(a.bbox[0], b.bbox[0]);
  const h = Math.min(a.bbox[3], b.bbox[3]) - Math.max(a.bbox[1], b.bbox[1]);
  if (w <= 0 || h <= 0) return false;
  return area(small) > 0 && w * h > area(small) * 0.5;
}

function tableProblem(rows) {
  if (!rows || rows.length < 2 || Math.max(...rows.map((r) => r.length)) < 2) return true;
  if (new Set(rows.map((r) => r.length)).size > 1) return true;
  const cells = rows.flat();
  return cells.filter((c) => !c.trim()).length > cells.length * 0.5;
}

// ---------------------------------------------------------------- assessment
// `reference`: referenceItems() of the source, or null (not a PDF). `captionText`: the
// engine's test for "Table 1: …" against "Table 1 shows…".
// -> { status, score, signals: { name: { ok, total, score } }, issues: [{ code, severity,
//      count, pages }], pages: Map(number -> { missing: [box], flags: Map(block id -> [code]) }) }
export function assess(doc, reference = null, captionText = () => true) {
  const signals = Object.fromEntries(SIGNALS.map((n) => [n, { ok: 0, total: 0 }]));
  const found = new Map();
  const where = new Map();
  const add = (code, severity, page = null, count = 1) => {
    const issue = found.get(code) || { code, severity, count: 0, pages: [] };
    issue.count += count;
    if (severity === "error") issue.severity = "error";
    if (page != null && !issue.pages.includes(page)) issue.pages.push(page);
    found.set(code, issue);
  };
  let chars = 0, bad = 0;

  for (const page of doc.pages) {
    const mark = { missing: [], flags: new Map() };
    where.set(page.number, mark);
    const flag = (b, code) => mark.flags.set(b.id, [...new Set([...(mark.flags.get(b.id) || []), code])]);
    const content = page.blocks.filter((b) => !FURNITURE.has(b.type));
    const output = pageOutput(page);
    chars += output.length;
    bad += garbled(output);

    if (reference && !page.scanned) {
      const c = coverage(reference.get(page.number) || [], output);
      signals.text.ok += c.matched;
      signals.text.total += c.total;
      mark.missing = c.missing;
      if (c.total >= TEXT_MIN && c.matched < c.total * TEXT_WARNING) {
        add("text_loss", c.matched < c.total * TEXT_ERROR ? "error" : "warning", page.number);
      }
    }
    if (page.scanned && !content.some((b) => (b.text || "").trim())) add("scanned_no_text", "warning", page.number);

    const placed = page.scanned ? [] : content.filter((b) => b.bbox);
    for (let i = 0; i + 1 < placed.length; i++) {
      signals.reading_order.total++;
      if (backwards(placed[i], placed[i + 1])) { add("reading_order", "warning", page.number); flag(placed[i + 1], "reading_order"); }
      else signals.reading_order.ok++;
    }
    const solid = placed.filter((b) => b.type !== "figure");
    for (let i = 0; i < solid.length; i++) {
      for (let j = i + 1; j < solid.length; j++) {
        if (!overlaps(solid[i], solid[j])) continue;
        add("block_overlap", "warning", page.number);
        flag(solid[i], "block_overlap");
        flag(solid[j], "block_overlap");
      }
    }

    const captions = (pattern) => content.filter((b) =>
      ["caption", "paragraph", "heading"].includes(b.type) && pattern.test((b.text || "").trim()) && captionText((b.text || "").trim()));
    // The captions left without their table/figure: the ones no block claims.
    const orphans = (caps, blocks) => {
      const claimed = new Set(blocks.map((b) => b.caption).filter(Boolean));
      const free = caps.filter((c) => !claimed.has(c.text));
      return free.length ? free : caps;
    };

    const tables = content.filter((b) => b.type === "table");
    for (const t of tables) {
      signals.tables.total++;
      if (tableProblem(t.rows)) { add("table_malformed", "warning", page.number); flag(t, "table_malformed"); }
      else signals.tables.ok++;
    }
    const tableCaps = captions(TABLE_CAPTION);
    let lost = tableCaps.length - tables.length;
    if (lost > 0) {
      signals.tables.total += lost;
      add("table_not_detected", "error", page.number, lost);
      for (const c of orphans(tableCaps, tables)) flag(c, "table_not_detected");
    }

    const figures = content.filter((b) => b.type === "figure");
    signals.figures.ok += figures.length;
    signals.figures.total += figures.length;
    const figureCaps = captions(FIGURE_CAPTION);
    lost = figureCaps.length - figures.length;
    if (lost > 0) {
      signals.figures.total += lost;
      add("figure_not_detected", "warning", page.number, lost);
      for (const c of orphans(figureCaps, figures)) flag(c, "figure_not_detected");
    }

    for (const f of content.filter((b) => b.type === "formula")) {
      signals.formulas.total++;
      if (!f.latex || garbled((f.text || "") + f.latex)) { add("formula_uncertain", "warning", page.number); flag(f, "formula_uncertain"); }
      else signals.formulas.ok++;
    }
  }

  const order = signals.reading_order;
  if (order.total && order.total - order.ok > order.total * ORDER_ERROR) found.get("reading_order").severity = "error";
  if (chars && bad > chars * GARBLED_WARNING) add("garbled_text", bad > chars * GARBLED_ERROR ? "error" : "warning", null, bad);
  if (doc.pages.length && !chars) add("no_text", "error");
  for (const w of doc.warnings || []) add(w.split(":")[0], "warning");

  const issues = [...found.values()].sort((a, b) => (a.severity !== "error") - (b.severity !== "error") || a.code.localeCompare(b.code));
  for (const i of issues) i.pages.sort((a, b) => a - b);
  let weight = 0, sum = 0;
  for (const [name, s] of Object.entries(signals)) {
    s.score = s.total ? s.ok / s.total : null;
    if (s.total) { weight += WEIGHTS[name]; sum += WEIGHTS[name] * s.score; }
  }
  const failed = issues.some((i) => i.severity === "error");
  return {
    status: failed ? "error" : issues.length ? "warning" : "ok",
    score: weight ? sum / weight : null,
    signals,
    issues,
    pages: where,
  };
}
