// Browser layout engine — a port of src/pdf_text_api/layout.py on top of pdf.js.
// Emits the same JSON as the Python library (schema "pdf-text-api/document@1"),
// so the viewer and the exporters work the same with either engine.
// Thresholds share their names with layout.py: keep both files in sync.

import * as pdfjsLib from "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc =
  "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.worker.min.mjs";
export { pdfjsLib };

export const SCHEMA = "pdf-text-api/document@1";

// ---------------------------------------------------------------- tunables (see layout.py)
const SPAN_GAP_EM = 0.9;
const JUSTIFIED_GAP_EM = 2.6;
const WORD_GAP_EM = 0.18;
const PARA_GAP_EM = 0.55;
const GUTTER_MIN = 5;
const RULE_MAX = 2.5;
const EDGE_ZONE = 0.09;
const TEXT_LIKE_CHARS = 15;
const SCANNED_CHARS_PER_PAGE = 25;
const HYPHEN_MARK = String.fromCharCode(2); // PDFium/pdf.js mark for an end-of-line hyphenation

// ---------------------------------------------------------------- symbols (see symbols.py)
const LIGATURES = { "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st" };
const SYMBOL_FONT = {};
"abcdefghijklmnopqrstuvwxyzADFGLPQSWXY".split("").forEach((k, i) => {
  SYMBOL_FONT[k.charCodeAt(0)] = "αβχδεφγηιϕκλμνοπθρστυϖωξψζΑΔΦΓΛΠΘΣΩΞΨ"[i];
});
Object.assign(SYMBOL_FONT, {
  0xb7: "•", 0xb1: "±", 0xa3: "≤", 0xb3: "≥", 0xb9: "≠", 0xbb: "≈", 0xa5: "∞", 0xe5: "∑", 0xf2: "∫",
  0xd6: "√", 0xb4: "×", 0xb8: "÷", 0xae: "→", 0xac: "←", 0xab: "↔", 0xde: "⇒", 0xdb: "⇔", 0xb6: "∂",
  0xd1: "∇", 0xce: "∈", 0xcf: "∉", 0xc7: "∩", 0xc8: "∪", 0xc6: "∅", 0xcc: "⊂", 0xc9: "⊃", 0xcd: "⊆",
  0xca: "⊇", 0xd8: "¬", 0xd9: "∧", 0xda: "∨", 0x22: "∀", 0x24: "∃", 0x2d: "−", 0xbc: "…", 0xa2: "′",
  0xb2: "″", 0xb0: "°", 0xba: "≡", 0xb5: "∝", 0x40: "≅", 0x7e: "∼", 0xc5: "⊕", 0xc4: "⊗", 0xd5: "∏",
});
const WINGDINGS = {
  0x6c: "●", 0x6d: "○", 0x6e: "■", 0x6f: "□", 0x71: "❑", 0x75: "◆", 0x76: "❖", 0x77: "⬥", 0xa7: "▪",
  0xa8: "◻", 0x9f: "•", 0xd8: "➢", 0xfc: "✓", 0xfb: "✗", 0xe0: "→", 0xe8: "➔", 0xf0: "⇨",
};
const BULLETS = new Set("•◦▪▫‣⁃●○■□–—-*✓✔➢➤►▶·".split(""));
const GREEK = {
  "α": "\\alpha", "β": "\\beta", "γ": "\\gamma", "δ": "\\delta", "ε": "\\epsilon", "ϵ": "\\epsilon",
  "ζ": "\\zeta", "η": "\\eta", "θ": "\\theta", "ϑ": "\\vartheta", "ι": "\\iota", "κ": "\\kappa",
  "λ": "\\lambda", "μ": "\\mu", "ν": "\\nu", "ξ": "\\xi", "π": "\\pi", "ϖ": "\\varpi", "ρ": "\\rho",
  "σ": "\\sigma", "ς": "\\varsigma", "τ": "\\tau", "υ": "\\upsilon", "φ": "\\phi", "ϕ": "\\phi",
  "χ": "\\chi", "ψ": "\\psi", "ω": "\\omega", "Γ": "\\Gamma", "Δ": "\\Delta", "Θ": "\\Theta",
  "Λ": "\\Lambda", "Ξ": "\\Xi", "Π": "\\Pi", "Σ": "\\Sigma", "Υ": "\\Upsilon", "Φ": "\\Phi",
  "Ψ": "\\Psi", "Ω": "\\Omega",
};
const OPERATORS = {
  "∑": "\\sum", "∏": "\\prod", "∐": "\\coprod", "∫": "\\int", "∬": "\\iint", "∭": "\\iiint",
  "∮": "\\oint", "√": "\\sqrt", "∂": "\\partial", "∇": "\\nabla", "∞": "\\infty", "±": "\\pm",
  "∓": "\\mp", "×": "\\times", "÷": "\\div", "·": "\\cdot", "⋅": "\\cdot", "∘": "\\circ",
  "≤": "\\leq", "≥": "\\geq", "≠": "\\neq", "≈": "\\approx", "≡": "\\equiv", "≅": "\\cong",
  "∼": "\\sim", "∝": "\\propto", "≪": "\\ll", "≫": "\\gg", "∈": "\\in", "∉": "\\notin", "∋": "\\ni",
  "⊂": "\\subset", "⊃": "\\supset", "⊆": "\\subseteq", "⊇": "\\supseteq", "∪": "\\cup", "∩": "\\cap",
  "∅": "\\emptyset", "∀": "\\forall", "∃": "\\exists", "∄": "\\nexists", "¬": "\\neg", "∧": "\\wedge",
  "∨": "\\vee", "⊕": "\\oplus", "⊗": "\\otimes", "→": "\\to", "←": "\\leftarrow",
  "↔": "\\leftrightarrow", "⇒": "\\Rightarrow", "⇐": "\\Leftarrow", "⇔": "\\Leftrightarrow",
  "↦": "\\mapsto", "ℝ": "\\mathbb{R}", "ℕ": "\\mathbb{N}", "ℤ": "\\mathbb{Z}", "ℚ": "\\mathbb{Q}",
  "ℂ": "\\mathbb{C}", "ℓ": "\\ell", "ℏ": "\\hbar", "′": "'", "″": "''", "−": "-", "∗": "*",
  "…": "\\ldots", "⋯": "\\cdots", "⌊": "\\lfloor", "⌋": "\\rfloor", "⌈": "\\lceil", "⌉": "\\rceil",
  "⟨": "\\langle", "⟩": "\\rangle", "‖": "\\|", "°": "^{\\circ}",
};
const LATEX = { ...GREEK, ...OPERATORS };
const MATH_CHARS = new Set([...Object.keys(OPERATORS), ...Object.keys(GREEK), "=", "+", "<", ">"]);
const MATH_FONT_HINTS = ["cmmi", "cmsy", "cmex", "msbm", "msam", "math", "stix", "symbol", "mtmi", "mtsy", "rsfs", "esint"];
const SUP_FROM = "0123456789+-=()niabcdehijklmoprstuvwxyz";
const SUP_TO = "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱᵃᵇᶜᵈᵉʰⁱʲᵏˡᵐᵒᵖʳˢᵗᵘᵛʷˣʸᶻ";
const SUB_FROM = "0123456789+-=()aehijklmnoprstuvx";
const SUB_TO = "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ";
const SPACES = new Set([0xa0, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200a, 0x202f, 0x205f, 0x3000]);
const INVISIBLE = new Set([0xad, 0x200b, 0x200c, 0x200d, 0xfeff]);

function normalizeChar(ch, font = "") {
  if (LIGATURES[ch]) return LIGATURES[ch];
  const cp = ch.codePointAt(0);
  if (cp >= 0xf000 && cp <= 0xf0ff) {
    const code = cp - 0xf000;
    const [a, b] = font.toLowerCase().includes("wingding") ? [WINGDINGS, SYMBOL_FONT] : [SYMBOL_FONT, WINGDINGS];
    return a[code] || b[code] || ch;
  }
  if (SPACES.has(cp)) return " ";
  if (INVISIBLE.has(cp)) return "";
  return ch;
}
const isMathFont = (name) => MATH_FONT_HINTS.some((h) => name.toLowerCase().includes(h));
function mathScore(text) {
  const chars = [...text].filter((c) => !/\s/.test(c));
  return chars.length ? chars.filter((c) => MATH_CHARS.has(c)).length / chars.length : 0;
}
function mapChars(text, from, to) {
  const t = text.trim();
  if (!t || [...t].some((c) => !from.includes(c))) return null;
  const toArr = [...to];
  return [...t].map((c) => toArr[from.indexOf(c)]).join("");
}
function latexEscape(text) {
  let out = "";
  for (const ch of text) {
    if (LATEX[ch]) out += LATEX[ch] + (/[a-zA-Z]$/.test(LATEX[ch]) ? " " : "");
    else if ("{}%#&$".includes(ch)) out += "\\" + ch;
    else out += ch;
  }
  return out.replace(/ {2}/g, " ");
}
const stripAccentsLower = (t) => t.toLowerCase().normalize("NFKD").replace(/\p{M}/gu, "");
const signature = (t) => stripAccentsLower(t).split(/\s+/).filter(Boolean).join(" ").replace(/\d+/g, "#");

// ---------------------------------------------------------------- regexes (see layout.py)
const ENUM = /^(\(?(\d{1,3}(\.\d{1,3})*|[a-zA-Z]|[ivxlcdmIVXLCDM]{1,5})[.)]|\(\d{1,3}\)|\([a-z]\))(?=\s|$)/;
const NUMBERED_HEADING = /^(\d{1,2}(\.\d{1,2}){0,4})\.?\s+\S/;
const CAPTION_WORDS = "(fig(ura|ure)?|tab(ela|le)?|quadro|gr[aá]fico|chart|imagem|image|equa[cç][aã]o|equation|listing|algoritmo|algorithm|esquema|diagrama|diagram)";
const CAPTION = new RegExp(`^${CAPTION_WORDS}\\.?\\s*(\\d+(\\.\\d+)?|[ivxlc]+)\\s*([.:\\-–—|]|\\s|$)`, "i");
const STRICT_CAPTION = new RegExp(`^${CAPTION_WORDS}\\.?\\s*(\\d+(\\.\\d+)?|[ivxlc]+)\\s*[.:\\-–—|]`, "i");
const KEY_VALUE = /^[^:]{2,40}:\s+\S/;
const EQ_NUMBER = /^\(\s*\d{1,3}(\.\d{1,3})?[a-z]?\s*\)$/;
const PAGE_NUMBER = /^\s*(?:(?:p[áa]g(?:ina)?|page|p)\.?\s*)?[-–—(\[]?\s*(\d{1,4}|[ivxlcdm]{1,6})\s*[-–—)\]]?(?:\s*(?:\/|de|of)\s*\d{1,4})?\s*$/i;

// ---------------------------------------------------------------- small helpers
const median = (arr) => {
  if (!arr.length) return 0;
  const s = [...arr].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const sum = (arr) => arr.reduce((a, b) => a + b, 0);
const area = (b) => Math.max(0, b[2] - b[0]) * Math.max(0, b[3] - b[1]);
const inside = (inner, outer, tol = 0) =>
  inner[0] >= outer[0] - tol && inner[1] >= outer[1] - tol && inner[2] <= outer[2] + tol && inner[3] <= outer[3] + tol;
const charSize = (c) => c.y1 - c.y0;
function modeSize(chars) {
  const counts = new Map();
  for (const c of chars) {
    const k = Math.round(charSize(c) * 2) / 2;
    counts.set(k, (counts.get(k) || 0) + 1);
  }
  let best = 0, bestN = -1;
  for (const [k, n] of counts) if (n > bestN) [best, bestN] = [k, n];
  return best;
}

// ---------------------------------------------------------------- spans
function segmentsOf(chars, main) {
  const normal = chars.filter((c) => Math.abs(charSize(c) - main) <= main * 0.12).map((c) => c.y1);
  const base = median(normal.length ? normal : chars.map((c) => c.y1));
  const gaps = [];
  for (let i = 1; i < chars.length; i++) if (chars[i].space < 2) gaps.push(chars[i].x0 - chars[i - 1].x1);
  const tracking = gaps.length >= 3 ? Math.max(0, median(gaps)) : 0;
  const wordGap = tracking + Math.max(main, 1) * WORD_GAP_EM;
  const out = [];
  let prev = null;
  for (const ch of chars) {
    let kind = "n";
    if (charSize(ch) < main * 0.86) {
      if (base - ch.y1 > main * 0.2) kind = "sup";
      else if (ch.y1 - base > main * 0.08) kind = "sub";
    }
    const gap = prev ? ch.x0 - prev.x1 : 0;
    const space = prev !== null && (ch.space === 2 || gap > wordGap || (ch.space && gap > wordGap * 0.6));
    if (out.length && out[out.length - 1][0] === kind) out[out.length - 1][1] += (space ? " " : "") + ch.c;
    else {
      if (space && out.length) out[out.length - 1][1] += " ";
      out.push([kind, ch.c]);
    }
    prev = ch;
  }
  return out;
}

export function segmentsText(segs) {
  return segs
    .map(([kind, text]) => {
      if (kind === "n") return text;
      const conv = kind === "sup" ? mapChars(text, SUP_FROM, SUP_TO) : mapChars(text, SUB_FROM, SUB_TO);
      if (conv !== null) return conv;
      const t = text.trim();
      const mark = kind === "sup" ? "^" : "_";
      return t.length === 1 ? mark + t : `${mark}(${t})`;
    })
    .join("");
}
function segmentsLatex(segs) {
  return segs
    .map(([kind, text]) => {
      const body = latexEscape(kind === "n" ? text : text.trim());
      return kind === "n" ? body : (kind === "sup" ? "^{" : "_{") + body + "}";
    })
    .join("")
    .replace(/\s+/g, " ")
    .trim();
}

class Span {
  constructor(chars, fonts, rotated = false) {
    this.chars = chars;
    this.fonts = fonts;
    this.x0 = Math.min(...chars.map((c) => c.x0));
    this.x1 = Math.max(...chars.map((c) => c.x1));
    this.y0 = Math.min(...chars.map((c) => c.y0));
    this.y1 = Math.max(...chars.map((c) => c.y1));
    this.size = modeSize(chars);
    const f = chars.map((c) => fonts[c.font]);
    const n = f.length;
    this.bold = f.filter((x) => x.bold).length > n * 0.6;
    this.italic = f.filter((x) => x.italic).length > n * 0.6;
    this.mono = f.filter((x) => x.mono).length > n * 0.8;
    this.math = f.filter((x) => x.math).length / n;
    // Rotated text (side stamps, axis titles): stream order, no baseline logic.
    this.segments = rotated
      ? [["n", chars.map((c, i) => (c.space && i ? " " : "") + c.c).join("")]]
      : segmentsOf(chars, this.size);
    this.text = segmentsText(this.segments);
  }
  get width() { return this.x1 - this.x0; }
  get height() { return this.y1 - this.y0; }
}

function buildSpans(chars, fonts) {
  const raw = [];
  let cur = [];
  for (const ch of chars) {
    if (cur.length) {
      const last = cur[cur.length - 1];
      const overlap = Math.min(last.y1, ch.y1) - Math.max(last.y0, ch.y0);
      const small = Math.min(charSize(last), charSize(ch));
      const sameLine = overlap >= small * 0.35 && ch.x0 >= last.x0 - small * 0.5;
      if (!sameLine || (ch.newline && !(overlap >= small * 0.8))) {
        raw.push(cur);
        cur = [];
      }
    }
    cur.push(ch);
  }
  if (cur.length) raw.push(cur);

  const lines = mergeFragments(raw);
  const spans = [];
  for (let line of lines) {
    line.sort((a, b) => a.x0 - b.x0);
    line = composeAccents(line);
    const size = Math.max(median(line.map(charSize)), 4);
    const wordGaps = [];
    for (let i = 1; i < line.length; i++) {
      const g = line[i].x0 - line[i - 1].x1;
      if (line[i].space || g > size * WORD_GAP_EM) wordGaps.push(g);
    }
    const typical = wordGaps.length >= 3 ? median(wordGaps) : 0;
    let piece = [line[0]];
    for (let i = 1; i < line.length; i++) {
      const prev = line[i - 1], ch = line[i];
      const gap = ch.x0 - prev.x1;
      let wide = gap > size * SPAN_GAP_EM && (gap > typical * 2.2 || gap > size * JUSTIFIED_GAP_EM);
      if (ch.space === 2 && gap < size * JUSTIFIED_GAP_EM) wide = false;
      if (wide) {
        spans.push(new Span(piece, fonts));
        piece = [];
      }
      piece.push(ch);
    }
    spans.push(new Span(piece, fonts));
  }
  return joinMarkers(spans);
}

// Accents drawn as their own glyph (TeX OT1 fonts): "Computa¸ca˜o" -> "Computação".
const SPACING_ACCENTS = {
  "´": "́", "ˊ": "́", "ˋ": "̀", "˜": "̃", "ˆ": "̂",
  "¨": "̈", "¸": "̧", "˚": "̊", "ˇ": "̌", "˘": "̆",
  "˙": "̇", "¯": "̄", "ˉ": "̄", "˝": "̋", "˛": "̨",
};
for (let c = 0x300; c < 0x370; c++) SPACING_ACCENTS[String.fromCharCode(c)] = String.fromCharCode(c);
const BELOW_ACCENTS = new Set(["̧", "̨"]);
function composeAccent(base, accent) {
  const mark = SPACING_ACCENTS[accent];
  if (!mark || !base || !/\p{L}$/u.test(base)) return null;
  const composed = (base.slice(-1) + mark).normalize("NFC");
  return [...composed].length === 1 ? base.slice(0, -1) + composed : null;
}
// The letter is the neighbour the accent overlaps; on a tie, accents above attach to the
// previous letter and cedillas/ogoneks to the next one (TeX's drawing order).
function composeAccents(line) {
  if (!line.some((c) => SPACING_ACCENTS[c.c])) return line;
  const out = [...line];
  for (let i = 0; i < out.length; ) {
    const acc = out[i];
    if (!SPACING_ACCENTS[acc.c]) { i++; continue; }
    let best = null, bestScore = 0;
    for (const j of [i - 1, i + 1]) {
      if (j < 0 || j >= out.length || composeAccent(out[j].c, acc.c) === null) continue;
      const base = out[j];
      const overlap = Math.min(base.x1, acc.x1 + 0.5) - Math.max(base.x0, acc.x0 - 0.5);
      const near = Math.max(base.x0 - acc.x1, acc.x0 - base.x1) < Math.max(charSize(acc), 4) * 0.3;
      const prefer = (j > i) === BELOW_ACCENTS.has(SPACING_ACCENTS[acc.c]);
      const score = (overlap > 0 ? overlap : near ? 0.5 : 0) + (prefer ? 0.01 : 0);
      if ((overlap > 0 || near) && score > bestScore) { best = j; bestScore = score; }
    }
    if (best === null) { i++; continue; }
    out[best].c = composeAccent(out[best].c, acc.c);
    out.splice(i, 1);
    // Drawing the accent moves the pen back, so a fake space shows up before the next letter.
    const nxt = out[best + 1];
    if (nxt && nxt.x0 - out[best].x1 < Math.max(charSize(nxt), 4) * 0.15) nxt.space = 0;
  }
  return out;
}

function mergeFragments(lines) {
  if (lines.length < 2) return lines;
  const boxes = lines.map((ln) => [
    Math.min(...ln.map((c) => c.x0)), Math.min(...ln.map((c) => c.y0)),
    Math.max(...ln.map((c) => c.x1)), Math.max(...ln.map((c) => c.y1)),
  ]);
  const order = lines.map((_, i) => i).sort((a, b) => boxes[a][1] - boxes[b][1] || boxes[a][0] - boxes[b][0]);
  const merged = [];
  const out = new Map();
  for (const i of order) {
    const bi = boxes[i];
    let target = null;
    for (const j of merged.slice(-6)) {
      const bj = boxes[j];
      const hi = bi[3] - bi[1], hj = bj[3] - bj[1];
      const h = Math.min(hi, hj);
      const overlap = Math.min(bi[3], bj[3]) - Math.max(bi[1], bj[1]);
      const touching = bi[0] <= bj[2] + h * SPAN_GAP_EM && bj[0] <= bi[2] + h * SPAN_GAP_EM;
      if (overlap >= h * 0.7 && touching) { target = j; break; }
      const glued = bi[0] <= bj[2] + h * 0.4 && bj[0] <= bi[2] + h * 0.4;
      if (h <= Math.max(hi, hj) * 0.8 && overlap >= h * 0.2 && glued) { target = j; break; }
    }
    if (target === null) {
      merged.push(i);
      out.set(i, [...lines[i]]);
    } else {
      out.get(target).push(...lines[i]);
      const bj = boxes[target];
      boxes[target] = [Math.min(bj[0], bi[0]), Math.min(bj[1], bi[1]), Math.max(bj[2], bi[2]), Math.max(bj[3], bi[3])];
    }
  }
  return merged.map((i) => out.get(i));
}

const isMarker = (text) => {
  const t = text.trim();
  return (t.length === 1 && BULLETS.has(t)) || new RegExp(ENUM.source + "$").test(t);
};

function joinMarkers(spans) {
  const out = [];
  for (let i = 0; i < spans.length; i++) {
    const s = spans[i];
    if (i + 1 < spans.length && isMarker(s.text)) {
      const nxt = spans[i + 1];
      const sameRow = Math.min(s.y1, nxt.y1) - Math.max(s.y0, nxt.y0) > Math.min(s.height, nxt.height) * 0.4;
      if (sameRow && nxt.x0 - s.x1 >= 0 && nxt.x0 - s.x1 < Math.max(s.size, 6) * 4) {
        nxt.chars[0].space = 2;
        out.push(new Span([...s.chars, ...nxt.chars], s.fonts));
        i++;
        continue;
      }
    }
    out.push(s);
  }
  return out;
}

// ---------------------------------------------------------------- reading order (column-aware XY-cut)
function atom(kind, x0, y0, x1, y1, extra = {}) {
  return { kind, x0, y0, x1, y1, ...extra };
}
function core(a) {
  if (a.kind !== "span") return [a.y0, a.y1];
  const pad = (a.y1 - a.y0) * 0.22;
  return [a.y0 + pad, a.y1 - pad];
}
function bandsOf(items) {
  const sorted = [...items].sort((a, b) => core(a)[0] - core(b)[0]);
  const bands = [];
  let bottom = -Infinity;
  for (const a of sorted) {
    const [top, bot] = core(a);
    if (bands.length && top < bottom) {
      bands[bands.length - 1].push(a);
      bottom = Math.max(bottom, bot);
    } else {
      bands.push([a]);
      bottom = bot;
    }
  }
  return bands;
}
function gutters(items, minGap) {
  const ivs = items.map((a) => [a.x0, a.x1]).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const gaps = [];
  let end = ivs[0][1];
  for (const [x0, x1] of ivs.slice(1)) {
    if (x0 - end >= minGap) gaps.push([end, x0]);
    end = Math.max(end, x1);
  }
  return gaps;
}
function textLike(side) {
  if (side.some((a) => a.kind !== "span")) return true;
  const lengths = side.map((a) => a.span.text.length);
  return lengths.length > 0 && median(lengths) >= TEXT_LIKE_CHARS;
}
function tableRow(band) {
  const spans = band.filter((a) => a.kind === "span").map((a) => a.span);
  return spans.length >= 3 && spans.length === band.length && spans.every((s) => s.text.length < TEXT_LIKE_CHARS);
}
function splitColumns(items, minGap) {
  if (items.length < 2) return null;
  const cols = [];
  let rest = items;
  const gs = gutters(items, minGap);
  const rows = gs.length ? bandsOf(items).filter(tableRow) : [];
  for (const [g0, g1] of gs) {
    const left = rest.filter((a) => a.x1 <= g0 + 0.01);
    const right = rest.filter((a) => a.x0 >= g1 - 0.01);
    const cutsTable = rows.some((row) => row.some((a) => a.x1 <= g0 + 0.01) && row.some((a) => a.x0 >= g1 - 0.01));
    if (left.length && right.length && !cutsTable && textLike(left) && textLike(right)) {
      cols.push(left);
      rest = right;
    }
  }
  if (!cols.length) return null;
  cols.push(rest);
  return cols;
}
function readingOrder(items, minGap) {
  if (!items.length) return [];
  if (items.length === 1) return [items];
  const cols = splitColumns(items, minGap);
  if (cols) return cols.flatMap((c) => readingOrder(c, minGap));
  const bands = bandsOf(items);
  if (bands.length === 1) return [[...items].sort((a, b) => a.x0 - b.x0)];
  const groups = [bands[0]];
  for (let k = 1; k < bands.length; k++) {
    const band = bands[k];
    const last = groups[groups.length - 1];
    const union = [...last, ...band];
    // Look two bands ahead: a short heading on a column ("Abstract") proves itself with the lines below.
    const ahead = bands.slice(k + 1, k + 3).flat();
    if (tableRow(band) && !tableRow(last.slice(-1))) groups.push(band);
    else if (splitColumns(union, minGap) || (ahead.length && splitColumns([...union, ...ahead], minGap))) groups[groups.length - 1] = union;
    else groups.push(band);
  }
  const out = [];
  for (const g of groups) {
    if (g.length === items.length) out.push(...bandsOf(g).map((b) => b.sort((a, c) => a.x0 - c.x0)));
    else out.push(...readingOrder(g, minGap));
  }
  return out;
}

// ---------------------------------------------------------------- tables
function cluster(values, tol) {
  const out = [];
  for (const v of [...values].sort((a, b) => a - b)) {
    if (out.length && v - out[out.length - 1][out[out.length - 1].length - 1] <= tol) out[out.length - 1].push(v);
    else out.push([v]);
  }
  return out.map((c) => sum(c) / c.length);
}
function mergeRules(rules) {
  const sorted = [...rules].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const out = [];
  for (const [pos, a, b] of sorted) {
    const r = out.slice(-8).find((r) => Math.abs(r[0] - pos) <= 1.5 && a <= r[2] + 2 && b >= r[1] - 2);
    if (r) { r[1] = Math.min(r[1], a); r[2] = Math.max(r[2], b); }
    else out.push([pos, a, b]);
  }
  return out;
}
function proseBetween(spans, x0, x1, ya, yb) {
  return spans.some((s) => {
    const cx = (s.x0 + s.x1) / 2, cy = (s.y0 + s.y1) / 2;
    if (!(x0 <= cx && cx <= x1 && ya < cy && cy < yb)) return false;
    return s.text.split(/\s+/).filter((w) => w.length >= 2 && /^\p{L}/u.test(w)).length >= 7;
  });
}
function ruledRegions(g, spans = []) {
  const H = mergeRules(g.hrules), V = mergeRules(g.vrules);
  if (H.length < 2) return [];
  const n = H.length + V.length;
  const parent = [...Array(n).keys()];
  const find = (i) => { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; };
  const tol = 2.5;
  H.forEach(([hy, hx0, hx1], i) => V.forEach(([vx, vy0, vy1], j) => {
    if (hx0 - tol <= vx && vx <= hx1 + tol && vy0 - tol <= hy && hy <= vy1 + tol) parent[find(i)] = find(H.length + j);
  }));
  // Stacked rules of similar extent (booktabs) — unless running text sits between them:
  // a page-header rule and a table further down are not one table.
  // Rules tied to vertical rules are a full grid: two Word tables of equal width stay apart.
  const gridded = new Set(V.map((_, j) => find(H.length + j)));
  for (let i = 0; i < H.length; i++)
    for (let j = i + 1; j < H.length; j++) {
      const a = H[i], b = H[j];
      if (gridded.has(find(i)) || gridded.has(find(j))) continue;
      const lo = Math.min(a[0], b[0]), hi = Math.max(a[0], b[0]);
      const imageBetween = g.images.some((im) => im[1] < hi && im[3] > lo);
      if (Math.abs(a[1] - b[1]) <= 4 && Math.abs(a[2] - b[2]) <= 4 && a[2] - a[1] > 30 &&
          !imageBetween && !proseBetween(spans, a[1], a[2], lo, hi)) parent[find(i)] = find(j);
    }
  const comps = new Map();
  for (let i = 0; i < n; i++) {
    const r = find(i);
    if (!comps.has(r)) comps.set(r, []);
    comps.get(r).push(i);
  }
  const out = [];
  for (const members of comps.values()) {
    const hs = members.filter((i) => i < H.length).map((i) => H[i]);
    const vs = members.filter((i) => i >= H.length).map((i) => V[i - H.length]);
    if (hs.length < 2) continue;
    const x0 = Math.min(...hs.map((h) => h[1]), ...vs.map((v) => v[0]));
    const x1 = Math.max(...hs.map((h) => h[2]), ...vs.map((v) => v[0]));
    const y0 = Math.min(...hs.map((h) => h[0]), ...vs.map((v) => v[1]));
    const y1 = Math.max(...hs.map((h) => h[0]), ...vs.map((v) => v[2]));
    if (x1 - x0 < 30 || y1 - y0 < 8) continue;
    const xs = cluster([...vs.map((v) => v[0]), x0, x1], 3);
    out.push({ bbox: [x0, y0, x1, y1], xs, ys: cluster([...hs.map((h) => h[0]), y0, y1], 2), realV: xs.length >= 3 });
  }
  return out;
}
function charsText(chars) {
  if (!chars.length) return "";
  const cy = (c) => (c.y0 + c.y1) / 2;
  const sorted = [...chars].sort((a, b) => cy(a) - cy(b) || a.x0 - b.x0);
  const lines = [[sorted[0]]];
  for (const ch of sorted.slice(1)) {
    const last = lines[lines.length - 1];
    const ref = median(last.map(cy));
    if (Math.abs(cy(ch) - ref) <= Math.max(charSize(ch), charSize(last[0])) * 0.45) last.push(ch);
    else lines.push([ch]);
  }
  return lines
    .map((ln) => { ln.sort((a, b) => a.x0 - b.x0); return segmentsText(segmentsOf(ln, modeSize(ln))).trim(); })
    .filter(Boolean)
    .join("\n");
}
// A run of glyphs without a space: the unit placed in a table cell, so a column boundary
// never cuts "0,014" or "Brasília" in two.
function wordsOf(span) {
  const size = Math.max(span.size, 4);
  const words = [];
  let cur = [span.chars[0]];
  for (let i = 1; i < span.chars.length; i++) {
    const prev = span.chars[i - 1], ch = span.chars[i];
    const gap = ch.x0 - prev.x1;
    if (ch.space === 2 || gap > size * 0.25 || (ch.space && gap > size * 0.1)) { words.push(cur); cur = []; }
    cur.push(ch);
  }
  words.push(cur);
  return words.map((chars) => ({
    chars, x0: chars[0].x0, x1: Math.max(...chars.map((c) => c.x1)),
    cy: median(chars.map((c) => (c.y0 + c.y1) / 2)),
  }));
}
// Column boundaries: vertical whitespace channels no word crosses. Rows with far fewer words
// than usual (a title spanning columns, a "Fase 1" divider) stay out of the projection.
function projectionColumns(spans, x0, x1) {
  const bands = bandsOf(spans.map((s) => atom("span", s.x0, s.y0, s.x1, s.y1, { span: s })))
    .map((band) => band.flatMap((a) => wordsOf(a.span)));
  const typical = median(bands.map((b) => b.length));
  const body = bands.filter((b) => b.length >= typical * 0.5 && b.length >= 2);
  const words = (body.length >= 2 ? body : bands).flat();
  const minGap = Math.max(3, median(spans.map((s) => s.size)) * 0.55);
  const ivs = words.map((w) => [w.x0, w.x1]).sort((a, b) => a[0] - b[0]);
  const bounds = [x0];
  let end = ivs[0][1];
  for (const [a, b] of ivs.slice(1)) {
    if (a - end >= minGap) bounds.push((a + end) / 2);
    end = Math.max(end, b);
  }
  bounds.push(x1);
  return bounds;
}
function bucket(v, edges) {
  if (v < edges[0] - 1 || v > edges[edges.length - 1] + 1) return null;
  for (let i = 0; i < edges.length - 1; i++) if (v <= edges[i + 1]) return i;
  return edges.length - 2;
}
function gridRows(words, xs, ys) {
  const ncol = xs.length - 1, nrow = ys.length - 1;
  const cells = Array.from({ length: nrow }, () => Array.from({ length: ncol }, () => []));
  for (const w of words) {
    const r = bucket(w.cy, ys), c = bucket((w.x0 + w.x1) / 2, xs);
    if (r !== null && c !== null) cells[r][c].push(...w.chars);
  }
  let rows = cells.map((row) => row.map(charsText)).filter((row) => row.some(Boolean));
  if (rows.length) {
    const keep = [...Array(ncol).keys()].filter((j) => rows.some((r) => r[j]));
    rows = rows.map((r) => keep.map((j) => r[j]));
  }
  return rows;
}
function tableBlock(bbox, rows) {
  if (rows.length < 2 || Math.max(...rows.map((r) => r.length)) < 2) return null;
  if (sum(rows.map((r) => r.filter(Boolean).length)) < 3) return null;
  return newBlock("table", bbox, { text: rows.map((r) => r.map((c) => c.replace(/\n/g, " ")).join(" | ")).join("\n"), rows });
}
function bandRows(spans) {
  const bands = bandsOf(spans.map((s) => atom("span", s.x0, s.y0, s.x1, s.y1, { span: s })));
  const edges = [Math.min(...bands[0].map((a) => a.y0))];
  for (let i = 1; i < bands.length; i++)
    edges.push((Math.max(...bands[i - 1].map((a) => a.y1)) + Math.min(...bands[i].map((a) => a.y0))) / 2);
  edges.push(Math.max(...bands[bands.length - 1].map((a) => a.y1)));
  return edges;
}
// A rule row holding 3+ text lines that each have 2+ cells is really several rows.
function looksUnruledRows(spans, ys) {
  for (let k = 0; k < ys.length - 1; k++) {
    const ins = spans.filter((s) => ys[k] <= (s.y0 + s.y1) / 2 && (s.y0 + s.y1) / 2 <= ys[k + 1]);
    const bands = bandsOf(ins.map((s) => atom("span", s.x0, s.y0, s.x1, s.y1, { span: s })));
    if (bands.length >= 3 && bands.filter((b) => b.length >= 2).length >= 3) return true;
  }
  return false;
}
// Row edges when rules don't separate every row (booktabs): decided inside each interval
// between rules — gaps of two sizes: only the big ones split rows; a line filling far fewer
// columns than the one above, set tight under it, continues its cells.
function logicalRows(spans, ys, xs) {
  const edges = [...ys];
  for (let k = 0; k < ys.length - 1; k++) {
    const ins = spans.filter((s) => ys[k] <= (s.y0 + s.y1) / 2 && (s.y0 + s.y1) / 2 <= ys[k + 1]);
    if (ins.length < 2) continue;
    const bands = bandsOf(ins.map((s) => atom("span", s.x0, s.y0, s.x1, s.y1, { span: s })));
    if (bands.length < 2) continue;
    const tops = bands.map((b) => Math.min(...b.map((a) => a.y0)));
    const bottoms = bands.map((b) => Math.max(...b.map((a) => a.y1)));
    const gaps = tops.slice(1).map((t, i) => t - bottoms[i]);
    const h = median(bottoms.map((b, i) => b - tops[i]));
    const threshold = Math.min(...gaps) + Math.max(1.5, h * 0.3);
    const bimodal = gaps.length >= 2 && Math.max(...gaps) > threshold;
    const cols = bands.map((b) => new Set(b.map((a) => bucket((a.x0 + a.x1) / 2, xs))).size);
    gaps.forEach((gap, i) => {
      const split = bimodal ? gap > threshold : !(cols[i + 1] < cols[i] * 0.6 && gap < h * 0.6);
      if (split) edges.push((bottoms[i] + tops[i + 1]) / 2);
    });
  }
  return [...new Set(cluster(edges, 2))];
}
function detectRuledTables(spans, g) {
  const tables = [];
  const used = new Set();
  for (const region of ruledRegions(g, spans)) {
    let { bbox, xs, ys, realV } = region;
    const [x0, y0, x1, y1] = bbox;
    const idx = spans
      .map((s, i) => i)
      .filter((i) => !used.has(i) && x0 - 2 <= (spans[i].x0 + spans[i].x1) / 2 && (spans[i].x0 + spans[i].x1) / 2 <= x1 + 2 &&
        y0 - 2 <= (spans[i].y0 + spans[i].y1) / 2 && (spans[i].y0 + spans[i].y1) / 2 <= y1 + 2);
    if (!idx.length) continue;
    const ins = idx.map((i) => spans[i]);
    if (!realV) xs = projectionColumns(ins, x0, x1);
    // Trust the rules of a full grid (cells may wrap); split by text bands only when rules
    // just frame the table (booktabs) or a rule row clearly holds several rows.
    if (!realV) ys = logicalRows(ins, ys, xs);
    const block = tableBlock(bbox, gridRows(ins.flatMap(wordsOf), xs, ys));
    if (!block) continue;
    tables.push(block);
    idx.forEach((i) => used.add(i));
  }
  return [tables, spans.filter((_, i) => !used.has(i))];
}

function distinctColumns(band, cols) {
  const seen = new Set();
  for (const a of band) {
    const c = bucket((a.x0 + a.x1) / 2, cols);
    if (seen.has(c)) return false;
    seen.add(c);
  }
  return true;
}
function unruledTable(bands, start, body) {
  const first = bands[start];
  if (first.length < 2 || first.some((a) => a.kind !== "span")) return [null, start];
  const run = [first];
  let singles = 0;
  let j = start + 1;
  for (; j < bands.length; j++) {
    const band = bands[j];
    if (band.some((a) => a.kind !== "span")) break;
    const prevBottom = Math.max(...run[run.length - 1].map((a) => a.y1));
    if (Math.min(...band.map((a) => a.y0)) - prevBottom > body * 1.6) break;
    const spans = [...run, band].flat().map((a) => a.span);
    const rx0 = Math.min(...spans.map((s) => s.x0)), rx1 = Math.max(...spans.map((s) => s.x1));
    const cols = projectionColumns(spans, rx0, rx1);
    if (cols.length < 3) break;
    if (band.length === 1) {
      if (band[0].span.width > (rx1 - rx0) * 0.6 || singles >= 1) break;
      singles++;
    } else {
      if (!distinctColumns(band, cols)) break;
      singles = 0;
    }
    run.push(band);
  }
  while (run.length && run[run.length - 1].length === 1) { run.pop(); j--; }
  const multi = run.filter((b) => b.length >= 2);
  const spans = run.flat().map((a) => a.span);
  if (!spans.length) return [null, start];
  const rx0 = Math.min(...spans.map((s) => s.x0)), rx1 = Math.max(...spans.map((s) => s.x1));
  const cols = projectionColumns(spans, rx0, rx1);
  const ncols = cols.length - 1;
  if (multi.length < 3 && !(multi.length >= 2 && ncols >= 3)) return [null, start];
  if (median(spans.map((s) => s.text.length)) > 38 || (ncols <= 3 && median(spans.map((s) => s.text.split(/\s+/).length)) >= 6))
    return [null, start];
  const edges = [Math.min(...run[0].map((a) => a.y0))];
  for (let k = 1; k < run.length; k++)
    if (run[k].length >= 2) edges.push((Math.max(...run[k - 1].map((a) => a.y1)) + Math.min(...run[k].map((a) => a.y0))) / 2);
  edges.push(Math.max(...run[run.length - 1].map((a) => a.y1)));
  const rows = gridRows(spans.flatMap(wordsOf), cols, edges);
  const bbox = [rx0, Math.min(...spans.map((s) => s.y0)), rx1, Math.max(...spans.map((s) => s.y1))];
  return [tableBlock(bbox, rows), j];
}

// ---------------------------------------------------------------- figures
function clusterBoxes(boxes, gap) {
  let bs = boxes.map((b) => [...b]);
  let changed = true;
  while (changed) {
    changed = false;
    const out = [];
    for (const b of bs) {
      const o = out.find((o) => b[0] <= o[2] + gap && o[0] <= b[2] + gap && b[1] <= o[3] + gap && o[1] <= b[3] + gap);
      if (o) {
        o[0] = Math.min(o[0], b[0]); o[1] = Math.min(o[1], b[1]); o[2] = Math.max(o[2], b[2]); o[3] = Math.max(o[3], b[3]);
        changed = true;
      } else out.push(b);
    }
    bs = out;
  }
  return bs;
}
// Vector charts: clusters of non-rule ink grown to take in their axes, ticks and legend frame.
// Rectangles of rules holding many vector marks and little text: the axes of a plot whose
// marks are too sparse to cluster (scatter plots). A table is the opposite.
function plotFrames(g, spans) {
  const H = mergeRules(g.hrules), V = mergeRules(g.vrules);
  if (V.length > 200 || g.ink.length < 8) return [];
  const frames = [];
  for (let i = 0; i < V.length; i++)
    for (const right of V.slice(i + 1)) {
      const left = V[i];
      if (right[0] - left[0] < 30 || Math.abs(left[1] - right[1]) > 3 || Math.abs(left[2] - right[2]) > 3) continue;
      const x0 = left[0], x1 = right[0], y0 = Math.max(left[1], right[1]), y1 = Math.min(left[2], right[2]);
      const edge = (y) => H.some((h) => Math.abs(h[0] - y) <= 3 && h[1] <= x0 + 3 && h[2] >= x1 - 3);
      if (!edge(y0) || !edge(y1) || y1 - y0 < 30) continue;
      const box = [x0, y0, x1, y1];
      const marks = g.ink.filter((b) => inside(b, box, 1)).length;
      const texts = spans.filter((s) => inside([s.x0, s.y0, s.x1, s.y1], box, 1)).length;
      if (marks >= 8 && marks >= texts * 3) frames.push(box);
    }
  return frames;
}
function chartRegions(g, width, height, spans = []) {
  let boxes = clusterBoxes(g.ink, 6).filter((b) => area(b) > width * height * 0.01);
  const frames = plotFrames(g, spans);
  if (frames.length) boxes = clusterBoxes([...boxes, ...frames], 2);
  const rules = [...g.hrules.map(([y, x0, x1]) => [x0, y, x1, y]), ...g.vrules.map(([x, y0, y1]) => [x, y0, x, y1])];
  for (const box of boxes) {
    for (let it = 0; it < 4; it++) {
      const w = box[2] - box[0], h = box[3] - box[1];
      const grow = [box[0] - w * 0.25, box[1] - h * 0.25, box[2] + w * 0.25, box[3] + h * 0.25];
      const near = [box[0] - 6, box[1] - 6, box[2] + 6, box[3] + 6];
      let changed = false;
      for (const r of rules) {
        const touches = r[0] <= near[2] && r[2] >= near[0] && r[1] <= near[3] && r[3] >= near[1];
        if (touches && inside(r, grow) && !inside(r, box)) {
          box[0] = Math.min(box[0], r[0]); box[1] = Math.min(box[1], r[1]);
          box[2] = Math.max(box[2], r[2]); box[3] = Math.max(box[3], r[3]);
          changed = true;
        }
      }
      if (!changed) break;
    }
  }
  return boxes;
}
function withoutRulesIn(g, boxes) {
  if (!boxes.length) return g;
  const free = (r) => !boxes.some((b) => inside(r, b, 3));
  return {
    ...g,
    hrules: g.hrules.filter((h) => free([h[1], h[0], h[2], h[0]])),
    vrules: g.vrules.filter((v) => free([v[0], v[1], v[0], v[2]])),
  };
}
// Labels of a chart (tick values, axis titles, legend rows): no bigger than the body text and
// not bold; beside the plot only short texts (never a line of the neighbouring column).
function labelOf(s, box, body) {
  const t = s.text.trim();
  if (!t || s.bold || s.size > body * 1.05 || CAPTION.test(t) || listStart(t)) return false;
  if (t.endsWith(".") && !/^[\d.,]+$/.test(t.slice(0, -1))) return false;
  const m = Math.max(s.size * 3.5, 18);
  if (!inside([s.x0, s.y0, s.x1, s.y1], [box[0] - m, box[1] - m, box[2] + m, box[3] + m])) return false;
  const beside = s.x1 <= box[0] + 2 || s.x0 >= box[2] - 2;
  if (beside) return t.length <= 12 || s.height > s.width;
  return t.length <= 60 && t.split(/\s+/).length <= 8 && s.width <= (box[2] - box[0]) * 1.1;
}
function detectFigures(g, spans, tables, width, height, charts, body = 10) {
  const raster = g.images.map((b) => [...b]);
  charts = charts || chartRegions(g, width, height);
  const boxes = clusterBoxes([...raster, ...charts.map((b) => [...b])], 2);
  const figures = [];
  let remaining = [...spans];
  for (let box of boxes) {
    box = [Math.max(0, box[0]), Math.max(0, box[1]), Math.min(width, box[2]), Math.min(height, box[3])];
    if (box[2] - box[0] < 12 || box[3] - box[1] < 12) continue;
    if (tables.some((t) => inside(box, t.bbox, 3))) continue;
    const isRaster = raster.some((r) => inside(r, box, 2) && inside(box, r, 2));
    let ins = remaining.filter((s) => inside([s.x0, s.y0, s.x1, s.y1], box, 2));
    const words = sum(ins.map((s) => s.text.split(/\s+/).length));
    const textArea = sum(ins.map((s) => s.width * s.height));
    const prose = words > 40 || textArea > area(box) * 0.35;
    const fullPage = area(box) > width * height * 0.85;
    if (prose && !fullPage) {
      if (!isRaster) continue;
      ins = [];
    } else if (!isRaster) {
      // Tick values and axis titles sit just outside the plot area: take them in.
      for (let pass = 0; pass < 3; pass++) // axis title, then the legend rows under it
        for (const s of remaining) {
          if (ins.includes(s) || !labelOf(s, box, body)) continue;
          {
            ins.push(s);
            box = [Math.min(box[0], s.x0), Math.min(box[1], s.y0), Math.max(box[2], s.x1), Math.max(box[3], s.y1)];
          }
        }
    }
    figures.push(newBlock("figure", box, { text: charsText(ins.flatMap((s) => s.chars)) }));
    const ids = new Set(ins);
    remaining = remaining.filter((s) => !ids.has(s));
  }
  return [figures, remaining];
}

// ---------------------------------------------------------------- lines & paragraphs
class Line {
  constructor(spans) {
    this.spans = spans;
    this.x0 = Math.min(...spans.map((s) => s.x0));
    this.y0 = Math.min(...spans.map((s) => s.y0));
    this.x1 = Math.max(...spans.map((s) => s.x1));
    this.y1 = Math.max(...spans.map((s) => s.y1));
    this.text = spans.map((s) => s.text.trim()).filter(Boolean).join(" ");
    this.size = spans.reduce((a, b) => (b.chars.length > a.chars.length ? b : a)).size;
    // By glyph: a line with a few words in bold is not a bold line.
    const all = spans.flatMap((s) => s.chars.map((c) => s.fonts[c.font].bold));
    this.bold = all.filter(Boolean).length >= all.length * 0.9;
    this.mono = spans.every((s) => s.mono);
    const n = sum(spans.map((s) => s.chars.length));
    this.math = sum(spans.map((s) => s.math * s.chars.length)) / Math.max(n, 1);
    this.hasScripts = spans.some((s) => s.segments.some(([k]) => k !== "n"));
  }
  get segments() {
    const out = [];
    this.spans.forEach((s, i) => { if (i) out.push(["n", " "]); out.push(...s.segments); });
    return out;
  }
  firstWordWidth() {
    const chars = this.spans.flatMap((s) => s.chars);
    let end = chars.findIndex((c, i) => i > 0 && c.space);
    if (end < 0) end = chars.length;
    return chars[end - 1].x1 - chars[0].x0;
  }
}
function listStart(text) {
  const t = text.trimStart();
  if (BULLETS.has(t[0]) && (t.length === 1 || t[1] === " ")) return t[0];
  const m = ENUM.exec(t);
  return m ? m[0] : null;
}
function formulaLike(line) {
  const text = line.text;
  const compact = text.replace(/ /g, "");
  if (!compact || compact.length > 160 || !/[\p{L}\p{N}]/u.test(compact)) return false;
  const words = text.split(/\s+/).filter((w) => w.length > 3 && /^\p{L}+$/u.test(w));
  if (words.length >= 5) return false;
  const score = mathScore(text);
  return line.math >= 0.4 || score >= 0.22 || (line.hasScripts && score >= 0.1) ||
    (text.includes("=") && words.length <= 1 && /[\p{L}\p{N}]/u.test(compact));
}
const NEWLINE = "\n"; // a line break the author made on purpose, kept inside a paragraph
// A break is intentional when the next line's first word would have fitted on this one.
const hardBreak = (prev, nxt, edges) =>
  (edges.get(prev) ?? prev.x1) - prev.x1 > nxt.firstWordWidth() + Math.max(prev.size, 4) * 0.6;
// Right edge of each line's text column: the furthest any line reaching over it goes.
function rightEdges(lines) {
  const out = new Map();
  for (const a of lines) {
    let edge = a.x1;
    for (const b of lines) if (Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0) > (a.x1 - a.x0) * 0.5) edge = Math.max(edge, b.x1);
    out.set(a, edge);
  }
  return out;
}
function joinLines(lines, edges = new Map()) {
  let text = "";
  let prev = null;
  for (const ln of lines) {
    const t = ln.text.trim();
    if (!text) text = t;
    else if (text.endsWith("-") && text.length > 1 && /\p{L}/u.test(text[text.length - 2]) && /^\p{Ll}/u.test(t)) text = text.slice(0, -1) + t;
    else if (prev && edges.size && hardBreak(prev, ln, edges)) text += NEWLINE + t;
    else text += " " + t;
    prev = ln;
  }
  return text;
}
// Gap between two lines of the same text (overlapping, same size), else null.
function lineGap(a, b) {
  const size = Math.max(a.size, 4);
  const gap = b.y0 - a.y1;
  const overlap = Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0);
  return overlap > 0 && Math.abs(a.size - b.size) <= size * 0.15 && gap > -size * 0.5 && gap < size * 2.5 ? gap : null;
}
// A line break inside a paragraph: a small gap, or one equal to the neighbouring lines'
// spacing (1.5- and double-spaced documents).
function sameLeading(gap, size, group, lines, idx) {
  if (gap <= -size * 0.5) return false;
  if (gap <= size * PARA_GAP_EM) return true;
  if (gap > size * 1.6) return false;
  const near = [];
  if (group.length >= 2) near.push(lineGap(group[group.length - 2], group[group.length - 1]));
  if (idx + 1 < lines.length) near.push(lineGap(lines[idx], lines[idx + 1]));
  return near.some((g) => g !== null && Math.abs(g - gap) <= Math.max(1.5, gap * 0.2));
}
// Inline formatting (bold / italic / super- and subscript runs), joined like joinLines.
function runsOf(group, edges) {
  const runs = [];
  const add = (text, bold, italic, script) => {
    const last = runs[runs.length - 1];
    if (last && ((last.bold === bold && last.italic === italic && last.script === script) || !text.trim())) last.text += text;
    else runs.push({ text, bold, italic, script });
  };
  let prev = null;
  for (const ln of group) {
    if (prev && runs.length) {
      const last = runs[runs.length - 1];
      const first = ln.text.trim()[0] || "";
      if (last.text.endsWith("-") && last.text.length > 1 && /\p{L}/u.test(last.text[last.text.length - 2]) && /\p{Ll}/u.test(first)) last.text = last.text.slice(0, -1);
      else last.text += hardBreak(prev, ln, edges) ? NEWLINE : " ";
    }
    ln.spans.forEach((span, k) => {
      if (k && runs.length) runs[runs.length - 1].text += " ";
      const fonts = span.fonts;
      let piece = [];
      const flushPiece = () => {
        if (!piece.length) return;
        const f = fonts[piece[0].font];
        const last = runs[runs.length - 1];
        const lead = piece[0].space && last && !/[ \n]$/.test(last.text) ? " " : "";
        segmentsOf(piece, span.size).forEach(([kind, text], i) =>
          add((i === 0 ? lead : "") + text, !!f.bold, !!f.italic, kind === "n" ? null : kind === "sup" ? "super" : "sub"));
        piece = [];
      };
      for (const ch of span.chars) {
        if (piece.length) {
          const a = fonts[piece[0].font], b = fonts[ch.font];
          if (!!a.bold !== !!b.bold || !!a.italic !== !!b.italic) flushPiece();
        }
        piece.push(ch);
      }
      flushPiece();
    });
    prev = ln;
  }
  const out = runs.filter((r) => r.text);
  if (out.length) {
    out[0].text = out[0].text.trimStart();
    out[out.length - 1].text = out[out.length - 1].text.trimEnd();
  }
  return out;
}
function stripPrefix(runs, prefix) {
  let n = prefix.length;
  for (const r of runs) {
    if (n <= 0) break;
    const cut = Math.min(n, r.text.length);
    r.text = r.text.slice(cut);
    n -= cut;
  }
  const out = runs.filter((r) => r.text);
  if (out.length) out[0].text = out[0].text.trimStart();
  return out;
}
// "ABCDEF+TimesNewRomanPS-BoldMT" -> "Times New Roman": what Word calls the font.
function family(name) {
  let base = name.split("+").pop().split(/[-,]/)[0].replace(/(PSMT|PS|MT)$/, "");
  base = base.replace(/(Bold|Italic|Oblique|Regular|Semibold|SemiBold|Black|Light|Medium|Book)+$/, "");
  return base.replace(/([a-z])([A-Z])/g, "$1 $2").trim() || name;
}
function linesToBlocks(lines) {
  const blocks = [];
  let group = [];
  let kind = "paragraph";
  const edges = lines.length > 1 ? rightEdges(lines) : new Map();
  const flush = () => {
    if (!group.length) return;
    const x0 = Math.min(...group.map((l) => l.x0)), y0 = Math.min(...group.map((l) => l.y0));
    const x1 = Math.max(...group.map((l) => l.x1)), y1 = Math.max(...group.map((l) => l.y1));
    const size = median(group.map((l) => l.size));
    let b;
    if (kind === "code") {
      const indent = (l) => " ".repeat(Math.max(0, Math.round((l.x0 - x0) / Math.max(size * 0.6, 1))));
      b = newBlock("code", [x0, y0, x1, y1], { text: group.map((l) => indent(l) + l.text).join("\n") });
    } else if (kind === "formula") {
      let segs = [], number = null;
      for (const ln of group) {
        const spans = [...ln.spans];
        if (spans.length > 1 && EQ_NUMBER.test(spans[spans.length - 1].text.trim())) number = spans.pop().text.trim();
        if (segs.length) segs.push(["n", " "]);
        segs = segs.concat(new Line(spans).segments);
      }
      b = newBlock("formula", [x0, y0, x1, y1], { text: segmentsText(segs).trim(), latex: segmentsLatex(segs), number });
    } else {
      const text = joinLines(group, edges);
      b = newBlock(kind, [x0, y0, x1, y1], { text });
      let runs = runsOf(group, edges);
      if (kind === "list_item") {
        b.marker = listStart(text);
        if (b.marker) {
          b.text = text.trimStart().slice(b.marker.length).trim();
          runs = stripPrefix(runs, b.marker);
        }
      }
      if (runs.length > 1 || (runs.length && (runs[0].bold || runs[0].italic || runs[0].script))) b.runs = runs;
      b.line_boxes = group.map((l) => [l.x0, l.y0, l.x1, l.y1]);
    }
    const glyphFonts = group.flatMap((l) => l.spans.flatMap((s) => s.chars.map((c) => [s.fonts[c.font], c.pt])));
    const pts = glyphFonts.map(([, pt]) => pt).filter(Boolean);
    if (pts.length) b.pt = Math.round(median(pts) * 10) / 10;
    // Letter spacing of a "T Í T U L O": the usual gap between letters of the same word.
    const gaps = group.flatMap((l) => l.spans.flatMap((s) => s.chars.slice(1).filter((c) => !c.space).map((c) => c.x0 - s.chars[s.chars.indexOf(c) - 1].x1)));
    if (gaps.length >= 4 && median(gaps) > size * 0.08) b.tracking = Math.round(median(gaps) * 10) / 10;
    const names = new Map();
    for (const [f] of glyphFonts) if (f.name) names.set(f.name, (names.get(f.name) || 0) + 1);
    if (names.size) b.font = family([...names.entries()].sort((a, c) => c[1] - a[1])[0][0]);
    b.font_size = size;
    b.bold = group.every((l) => l.bold);
    b.lines = group.length;
    blocks.push(b);
    group = [];
    kind = "paragraph";
  };
  lines.forEach((ln, idx) => {
    const text = ln.text;
    if (!text.trim()) return;
    let thisKind = "paragraph";
    if (ln.mono && text.length > 1) thisKind = "code";
    else if (formulaLike(ln)) thisKind = "formula";
    else if (listStart(text)) thisKind = "list_item";
    if (group.length) {
      const prev = group[group.length - 1];
      const size = Math.max(prev.size, 4);
      const gap = ln.y0 - prev.y1;
      const overlap = Math.min(prev.x1, ln.x1) - Math.max(prev.x0, ln.x0);
      const sameStyle = Math.abs(ln.size - prev.size) <= size * 0.15 && ln.bold === prev.bold;
      let cont = sameLeading(gap, size, group, lines, idx) && overlap > 0 && sameStyle;
      if (kind === "code") cont = thisKind === "code" && gap <= size * 1.2 && overlap > -size;
      else if (kind === "formula") cont = thisKind === "formula" && gap <= size * 0.9;
      else if (["list_item", "formula", "code"].includes(thisKind)) cont = false;
      else if (kind === "list_item") {
        // Wrapped item text: indented under the text, or flush with the marker right after a full line.
        const wrapped = ln.x0 >= group[0].x0 - 2 && prev.x1 >= Math.max(...group.map((g) => g.x1)) - size * 2;
        cont = cont && (ln.x0 >= group[0].x0 + size * 0.3 || wrapped);
      }
      else {
        const shortPrev = prev.x1 < Math.max(...group.map((g) => g.x1)) - size * 2.5;
        if (shortPrev && /[.:!?]$/.test(prev.text.trimEnd())) cont = false;
        if (ln.x0 > prev.x0 + size * 0.9 && !shortPrev) cont = false;
      }
      if (!cont) flush();
    }
    if (!group.length) kind = thisKind;
    group.push(ln);
  });
  flush();
  return blocks;
}
// Alignment, indents and line spacing of each text block against the page's text area.
function layoutFormat(page) {
  const text = page.blocks.filter((b) => b.line_boxes && !FURNITURE.has(b.type));
  if (!text.length) return;
  const left = Math.min(...text.map((b) => b.bbox[0])), right = Math.max(...text.map((b) => b.bbox[2]));
  const width = Math.max(right - left, 1), mid = (left + right) / 2, tol = Math.max(3, width * 0.012);
  for (const b of text) {
    const boxes = b.line_boxes;
    const x0s = boxes.map((l) => l[0]), x1s = boxes.map((l) => l[2]);
    const centred = x0s.every((a, i) => Math.abs((a + x1s[i]) / 2 - mid) <= tol * 1.5);
    let align = "left";
    if (boxes.length >= 2 && x1s.slice(0, -1).every((e) => Math.abs(e - right) <= tol) && Math.min(...x0s) <= left + tol) align = "justify";
    else if (centred && Math.min(...x0s) > left + width * 0.05) align = "center";
    else if (x1s.every((e) => Math.abs(e - right) <= tol) && Math.min(...x0s) > left + width * 0.3) align = "right";
    const fmt = { align };
    if (align === "left" || align === "justify") {
      const base = boxes.length > 1 ? Math.min(...x0s.slice(1)) : x0s[0];
      if (base - left > tol) fmt.indent = Math.round((base - left) * 10) / 10;
      if (boxes.length > 1 && Math.abs(x0s[0] - base) > tol) fmt.first_line = Math.round((x0s[0] - base) * 10) / 10;
    }
    if (boxes.length >= 2 && b.pt) {
      const pitch = median(boxes.slice(1).map((l, k) => l[3] - boxes[k][3]));
      const multiple = pitch / (b.pt * 1.15);
      if (multiple > 1.2) fmt.line_spacing = Math.round(multiple * 100) / 100;
    }
    b.format = fmt;
  }
}

function newBlock(type, bbox, extra = {}) {
  return { id: "", type, order: 0, bbox: bbox ? bbox.map((v) => Math.round(v * 100) / 100) : null, text: "", ...extra };
}

// ---------------------------------------------------------------- pdf.js readers
const IDENTITY = [1, 0, 0, 1, 0, 0];
const mul = (m, n) => pdfjsLib.Util.transform(m, n);
const apply = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];

async function fontInfo(page, fontName, style) {
  let name = style?.fontFamily || "";
  try {
    if (page.commonObjs.has(fontName)) {
      const f = page.commonObjs.get(fontName);
      name = f?.name || f?.loadedName || name;
    }
  } catch { /* font not resolved: use the family */ }
  const low = name.toLowerCase().split("+").pop();
  return {
    name,
    bold: /bold|black|heavy|semibold|demi/.test(low),
    italic: /italic|oblique/.test(low),
    math: isMathFont(low),
    mono: /mono|courier|consol|menlo|inconsolata/.test(low) || style?.fontFamily === "monospace",
  };
}

// Every glyph from the operator list, run through the PDF text state machine: exact
// position (not spread evenly over a text item), real font size, and fill colour — so white
// text on white paper can be told apart from what the reader sees. Mirrors read_chars() in
// layout.py, which gets the same from PDFium.
function readGlyphs(page, viewport, ops) {
  const O = pdfjsLib.OPS;
  const fonts = [];
  const fontIndex = new Map();
  const chars = [], rotated = [];
  let ctm = viewport.transform.slice();
  let st = { key: null, size: 0, cs: 0, ws: 0, hs: 1, lead: 0, rise: 0, mode: 0, fill: [0, 0, 0] };
  const stack = [];
  let tm = IDENTITY.slice(), tlm = IDENTITY.slice();
  let space = 0, newline = false;

  const font = () => {
    let fi = fontIndex.get(st.key);
    if (fi === undefined) {
      let f = null;
      try { if (page.commonObjs.has(st.key)) f = page.commonObjs.get(st.key); } catch { /* unresolved */ }
      const name = f?.name || st.key || "";
      const low = name.toLowerCase().split("+").pop();
      fi = fonts.length;
      fontIndex.set(st.key, fi);
      fonts.push({
        name, obj: f,
        bold: !!f?.bold || !!f?.black || /bold|black|heavy|semibold|demi/.test(low),
        italic: !!f?.italic || /italic|oblique/.test(low),
        math: isMathFont(low),
        mono: /mono|courier|consol|menlo|inconsolata/.test(low),
      });
    }
    return fi;
  };
  const moveText = (tx, ty) => {
    tlm = mul(tlm, [1, 0, 0, 1, tx, ty]);
    tm = tlm.slice();
    if (ty) newline = true;
  };
  const show = (items) => {
    const fi = font();
    const f = fonts[fi].obj;
    const fm = f?.fontMatrix || [0.001, 0, 0, 0.001, 0, 0];
    const asc = f?.ascent || 0.8, desc = f?.descent || -0.2;
    const white = Math.min(...st.fill) >= 250 && (st.mode === 0 || st.mode === 4);
    for (const it of items) {
      if (typeof it === "number") { // TJ spacing, thousandths of an em
        tm = mul(tm, [1, 0, 0, 1, (-it / 1000) * st.size * st.hs, 0]);
        continue;
      }
      if (!it) continue;
      if (Array.isArray(it)) { show(it); continue; }
      const w0 = (it.width || 0) * fm[0];
      const trm = mul(ctm, mul(tm, [st.size * st.hs, 0, 0, st.size, 0, st.rise]));
      const uni = it.unicode || "";
      if (it.isSpace || !uni.trim()) {
        space = 2;
      } else {
        const parts = [...uni].map((g) => normalizeChar(g, fonts[fi].name)).join("");
        const glyphs = [...parts].filter((g) => g && !/\s/.test(g));
        glyphs.forEach((g, k) => {
          const a = (w0 * k) / glyphs.length, b = (w0 * (k + 1)) / glyphs.length;
          const pts = [apply(trm, a, desc), apply(trm, b, desc), apply(trm, a, asc), apply(trm, b, asc)];
          const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
          const ch = {
            c: g === HYPHEN_MARK ? "-" : g, x0: Math.min(...xs), x1: Math.max(...xs),
            y0: Math.min(...ys), y1: Math.max(...ys), font: fi, space, newline, white,
            pt: st.size * Math.sqrt(Math.abs(trm[0] * trm[3] - trm[1] * trm[2])) / Math.max(st.size, 1e-6),
          };
          if (ch.y1 - ch.y0 > 0.1) (Math.abs(trm[1]) > Math.abs(trm[0]) * 0.2 ? rotated : chars).push(ch);
          space = 0;
          newline = false;
        });
      }
      const tx = (w0 * st.size + st.cs + (it.isSpace ? st.ws : 0)) * st.hs;
      tm = mul(tm, [1, 0, 0, 1, tx, 0]);
    }
  };
  const color = (fn, args) => {
    if (fn === O.setFillRGBColor) {
      const c = args[0];
      st.fill = typeof c === "string" ? [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16)) : [...args].map((v) => (v <= 1 ? v * 255 : v));
    } else if (fn === O.setFillGray) st.fill = [args[0] * 255, args[0] * 255, args[0] * 255];
    else if (fn === O.setFillCMYKColor) {
      const [c, m, y, k] = args;
      st.fill = [255 * (1 - c) * (1 - k), 255 * (1 - m) * (1 - k), 255 * (1 - y) * (1 - k)];
    }
  };
  for (let i = 0; i < ops.fnArray.length; i++) {
    const fn = ops.fnArray[i], args = ops.argsArray[i];
    switch (fn) {
      case O.save: stack.push({ ctm: ctm.slice(), st: { ...st, fill: [...st.fill] } }); break;
      case O.restore: if (stack.length) ({ ctm, st } = stack.pop()); break;
      case O.transform: ctm = mul(ctm, args); break;
      case O.paintFormXObjectBegin: stack.push({ ctm: ctm.slice(), st: { ...st, fill: [...st.fill] } }); if (args[0]) ctm = mul(ctm, args[0]); break;
      case O.paintFormXObjectEnd: if (stack.length) ({ ctm, st } = stack.pop()); break;
      case O.beginText: tm = IDENTITY.slice(); tlm = IDENTITY.slice(); break;
      case O.setFont: st.key = args[0]; st.size = args[1]; break;
      case O.setTextMatrix: tlm = (args.length === 6 ? args : args[0]).slice(0, 6); tm = tlm.slice(); newline = true; break;
      case O.moveText: moveText(args[0], args[1]); break;
      case O.setLeadingMoveText: st.lead = -args[1]; moveText(args[0], args[1]); break;
      case O.nextLine: moveText(0, -st.lead); break;
      case O.setLeading: st.lead = args[0]; break;
      case O.setCharSpacing: st.cs = args[0]; break;
      case O.setWordSpacing: st.ws = args[0]; break;
      case O.setHScale: st.hs = args[0] / 100; break;
      case O.setTextRise: st.rise = args[0]; break;
      case O.setTextRenderingMode: st.mode = args[0]; break;
      case O.showText: case O.showSpacedText: show(args[0]); break;
      case O.nextLineShowText: moveText(0, -st.lead); show(args[0]); break;
      case O.nextLineSetSpacingShowText: st.ws = args[0]; st.cs = args[1]; moveText(0, -st.lead); show(args[2]); break;
      default: color(fn, args);
    }
  }
  return { chars, rotated, fonts };
}

// White text on white paper is invisible: generators use it to align things. White on a
// coloured cell or an image is real text. (Unlike PDFium, pdf.js keeps glyphs that overlap,
// so dropping the white ones never removes a visible one.)
function visibleOnly(list, g) {
  const under = [...g.fills, ...g.images];
  return list.filter((c) => !c.white || under.some((b) => b[0] <= (c.x0 + c.x1) / 2 && (c.x0 + c.x1) / 2 <= b[2] && b[1] <= (c.y0 + c.y1) / 2 && (c.y0 + c.y1) / 2 <= b[3]));
}


async function readChars(page, viewport, textContent) {
  const fonts = [];
  const fontIndex = new Map();
  const chars = [], rotated = [];
  let newline = false;
  let space = 0; // 0 none, 1 inserted by pdf.js (whitespace-only item), 2 inside the PDF's own text
  for (const it of textContent.items) {
    if (!("str" in it)) continue;
    if (!it.str.trim()) {
      if (it.str) space = Math.max(space, 1);
      if (it.hasEOL) newline = true;
      continue;
    }
    let fi = fontIndex.get(it.fontName);
    if (fi === undefined) {
      fi = fonts.length;
      fontIndex.set(it.fontName, fi);
      fonts.push(await fontInfo(page, it.fontName, textContent.styles[it.fontName]));
    }
    const tx = mul(viewport.transform, it.transform);
    const fh = Math.hypot(tx[2], tx[3]);
    if (fh <= 0.1) continue;
    const isRotated = Math.abs(tx[1]) > Math.abs(tx[0]) * 0.2;
    const st = textContent.styles[it.fontName] || {};
    const asc = st.ascent || 0.8, desc = st.descent || -0.2;
    // Glyph boxes follow the text's own axes, so rotated text (the arXiv side stamp, axis
    // titles) gets a tall narrow box instead of a horizontal one across the page.
    const along = Math.hypot(tx[0], tx[1]) || 1;
    const ux = tx[0] / along, uy = tx[1] / along; // reading direction (device space)
    const vx = tx[2] / fh, vy = tx[3] / fh; // "up" for the glyphs
    const glyphs = [...it.str];
    // TeX accents: pdf.js turns the pen's step back after "˜" into a fake space ("˜ o e").
    if (glyphs.length > 2 && SPACING_ACCENTS[glyphs[0]] && glyphs[1] === " ") glyphs.splice(1, 1);
    const w = it.width * viewport.scale;
    const n = glyphs.length;
    glyphs.forEach((g, k) => {
      const c = normalizeChar(g, fonts[fi].name);
      if (!c || /\s/.test(c)) { space = 2; return; }
      const sx = tx[4] + ux * (w * k) / n, sy = tx[5] + uy * (w * k) / n;
      const ex = sx + ux * w / n, ey = sy + uy * w / n;
      const xs = [sx + vx * fh * desc, sx + vx * fh * asc, ex + vx * fh * desc, ex + vx * fh * asc];
      const ys = [sy + vy * fh * desc, sy + vy * fh * asc, ey + vy * fh * desc, ey + vy * fh * asc];
      const ch = {
        c: c === HYPHEN_MARK ? "-" : c, x0: Math.min(...xs), x1: Math.max(...xs),
        y0: Math.min(...ys), y1: Math.max(...ys), font: fi, space, newline,
      };
      (isRotated ? rotated : chars).push(ch);
      space = 0;
      newline = false;
    });
    if (it.hasEOL) newline = true;
  }
  return { chars, rotated, fonts };
}

async function readGraphics(page, viewport, width, height, ops) {
  const g = { hrules: [], vrules: [], ink: [], images: [], fills: [] };
  ops = ops || (await page.getOperatorList());
  const O = pdfjsLib.OPS;
  const pageArea = width * height;
  let ctm = viewport.transform.slice();
  const stack = [];
  let pending = null;

  const toPage = (m, x0, y0, x1, y1) => {
    const pts = [apply(m, x0, y0), apply(m, x1, y0), apply(m, x0, y1), apply(m, x1, y1)];
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  };
  const addBoxRules = (b) => {
    const [x0, y0, x1, y1] = b;
    const w = x1 - x0, h = y1 - y0;
    // Thick rules (Word borders, a 0.5 mm booktabs toprule) are flat bars, not boxes.
    if ((w <= RULE_MAX && h > 3) || (w <= 4.5 && h > w * 6)) g.vrules.push([(x0 + x1) / 2, y0, y1]);
    else if ((h <= RULE_MAX && w > 3) || (h <= 4.5 && w > h * 6)) g.hrules.push([(y0 + y1) / 2, x0, x1]);
    else if (w * h < pageArea * 0.6) {
      g.hrules.push([y0, x0, x1], [y1, x0, x1]);
      g.vrules.push([x0, y0, y1], [x1, y0, y1]);
    }
  };
  const paint = (path, fill, stroke) => {
    if (!path || (!fill && !stroke)) return;
    if (fill && !stroke && path.white) return;
    if (fill && !path.white) g.fills.push(path.box); // coloured area: white text on it is real
    const { box, segs, curves, rects } = path;
    if (box[2] < -5 || box[3] < -5 || box[0] > width + 5 || box[1] > height + 5) return;
    const w = box[2] - box[0], h = box[3] - box[1];
    if (curves === 0 && (rects.length || segs.length)) {
      rects.forEach(addBoxRules);
      const straight = segs.filter((s) => s);
      if (straight.length) {
        straight.forEach(([k, pos, a, b]) => (k === "h" ? g.hrules : g.vrules).push([pos, a, b]));
        return;
      }
      if (rects.length) return;
    }
    if (w * h < pageArea * 0.9) g.ink.push(box);
  };

  let fillColor = [0, 0, 0];
  for (let i = 0; i < ops.fnArray.length; i++) {
    const fn = ops.fnArray[i], args = ops.argsArray[i];
    switch (fn) {
      case O.save: stack.push(ctm.slice()); break;
      case O.restore: if (stack.length) ctm = stack.pop(); break;
      case O.transform: ctm = mul(ctm, args); break;
      case O.paintFormXObjectBegin: stack.push(ctm.slice()); if (args[0]) ctm = mul(ctm, args[0]); break;
      case O.paintFormXObjectEnd: if (stack.length) ctm = stack.pop(); break;
      case O.setFillRGBColor: {
        const c = args[0];
        fillColor = typeof c === "string" ? [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)] : [...args];
        break;
      }
      case O.setFillGray: fillColor = [args[0] * 255, args[0] * 255, args[0] * 255]; break;
      case O.constructPath: {
        const [pathOps, coords] = args;
        let k = 0, cx = 0, cy = 0;
        const segs = [], rects = [];
        let curves = 0;
        const pts = [];
        for (const op of pathOps) {
          if (op === O.rectangle) {
            const [x, y, w, h] = coords.slice(k, k + 4); k += 4;
            rects.push(toPage(ctm, x, y, x + w, y + h));
            pts.push(apply(ctm, x, y), apply(ctm, x + w, y + h));
          } else if (op === O.moveTo) {
            [cx, cy] = [coords[k], coords[k + 1]]; k += 2;
            pts.push(apply(ctm, cx, cy));
          } else if (op === O.lineTo) {
            const [nx, ny] = [coords[k], coords[k + 1]]; k += 2;
            const [ax, ay] = apply(ctm, cx, cy), [bx, by] = apply(ctm, nx, ny);
            if (Math.abs(ay - by) <= 0.5 && Math.abs(ax - bx) > 3) segs.push(["h", (ay + by) / 2, Math.min(ax, bx), Math.max(ax, bx)]);
            else if (Math.abs(ax - bx) <= 0.5 && Math.abs(ay - by) > 3) segs.push(["v", (ax + bx) / 2, Math.min(ay, by), Math.max(ay, by)]);
            else curves++; // diagonal: vector art
            pts.push([bx, by]);
            [cx, cy] = [nx, ny];
          } else if (op === O.curveTo) {
            curves++; [cx, cy] = [coords[k + 4], coords[k + 5]]; k += 6; pts.push(apply(ctm, cx, cy));
          } else if (op === O.curveTo2 || op === O.curveTo3) {
            curves++; [cx, cy] = [coords[k + 2], coords[k + 3]]; k += 4; pts.push(apply(ctm, cx, cy));
          }
        }
        if (!pts.length) { pending = null; break; }
        const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
        const box = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
        pending = { box, segs, curves, rects, white: Math.min(...fillColor) >= 250 };
        break;
      }
      case O.fill: case O.eoFill: paint(pending, true, false); pending = null; break;
      case O.stroke: case O.closeStroke: paint(pending, false, true); pending = null; break;
      case O.fillStroke: case O.eoFillStroke: case O.closeFillStroke: case O.closeEOFillStroke:
        paint(pending, true, true); pending = null; break;
      case O.endPath: pending = null; break;
      case O.paintImageXObject: case O.paintInlineImageXObject: case O.paintImageMaskXObject:
      case O.paintImageXObjectRepeat: case O.paintSolidColorImageMask: {
        const b = toPage(ctm, 0, 0, 1, 1);
        if (b[2] - b[0] >= 8 && b[3] - b[1] >= 8) g.images.push(b);
        break;
      }
      default: break;
    }
  }
  return g;
}

// ---------------------------------------------------------------- page & document
async function analyzePage(pdf, number, opts) {
  const page = await pdf.getPage(number);
  const viewport = page.getViewport({ scale: 1, rotation: 0 });
  const width = viewport.width, height = viewport.height;
  const ops = await page.getOperatorList(); // also resolves the fonts
  const g = await readGraphics(page, viewport, width, height, ops);
  let { chars, rotated, fonts } = readGlyphs(page, viewport, ops);
  if (!chars.length && !rotated.length) {
    // No glyphs in the operator list (unusual fonts): fall back to pdf.js text items.
    ({ chars, rotated, fonts } = await readChars(page, viewport, await page.getTextContent()));
  }
  chars = visibleOnly(chars, g);
  rotated = visibleOnly(rotated, g);
  let spans = chars.length ? buildSpans(chars, fonts) : [];
  const rotSpans = groupRotated(rotated).map((grp) => new Span(grp, fonts, true));
  const sizes = new Map();
  for (const c of chars) { const k = Math.round(charSize(c) * 2) / 2; sizes.set(k, (sizes.get(k) || 0) + 1); }
  let body = 10, bestN = 0;
  for (const [k, n] of sizes) if (n > bestN) [body, bestN] = [k, n];

  // Charts first: their axes, ticks and legend frame are rules that must not form a table.
  const charts = chartRegions(g, width, height, spans);
  let tables = [];
  if (opts.tables) [tables, spans] = detectRuledTables(spans, withoutRulesIn(g, charts));
  let figures;
  [figures, spans] = detectFigures(g, [...spans, ...rotSpans], tables, width, height, charts, body);

  const atoms = spans.map((s) => atom("span", s.x0, s.y0, s.x1, s.y1, { span: s }));
  for (const b of [...tables, ...figures]) atoms.push(atom(b.type, ...b.bbox, { block: b }));
  const bands = readingOrder(atoms, Math.max(GUTTER_MIN, body * 0.8));

  const blocks = [];
  let pendingLines = [];
  const flushLines = () => { blocks.push(...linesToBlocks(pendingLines)); pendingLines = []; };
  for (let i = 0; i < bands.length; ) {
    const band = bands[i];
    if (band.length === 1 && band[0].kind !== "span") { flushLines(); blocks.push(band[0].block); i++; continue; }
    if (opts.tables && band.length >= 2) {
      const [table, j] = unruledTable(bands, i, body);
      if (table) { flushLines(); blocks.push(table); i = j; continue; }
    }
    const inBand = band.filter((a) => a.span).map((a) => a.span);
    for (const a of band) if (a.kind !== "span") { flushLines(); blocks.push(a.block); }
    if (inBand.length) pendingLines.push(new Line(inBand));
    i++;
  }
  flushLines();
  if (!opts.formulas) blocks.forEach((b) => { if (b.type === "formula") b.type = "paragraph"; });

  const scanned = !chars.length && g.images.some((b) => area(b) > width * height * 0.5);
  const result = { number, width, height, blocks, scanned };
  return { page: result, pdfPage: page, sizes, chars: chars.length };
}

function groupRotated(chars) {
  const groups = [];
  for (const ch of chars) {
    const last = groups.length ? groups[groups.length - 1][groups[groups.length - 1].length - 1] : null;
    const d = Math.max(charSize(ch), ch.x1 - ch.x0) * 3; // rotated glyph: its box is turned too
    if (last && Math.abs((ch.x0 + ch.x1) / 2 - (last.x0 + last.x1) / 2) < d &&
        Math.abs((ch.y0 + ch.y1) / 2 - (last.y0 + last.y1) / 2) < d) groups[groups.length - 1].push(ch);
    else groups.push([ch]);
  }
  return groups;
}

const FURNITURE = new Set(["header", "footer", "page_number"]);

function markFurniture(pages) {
  const key = (b) => b.type === "figure"
    ? `fig:${b.bbox.map((v, i) => Math.round((i < 2 ? v : v - b.bbox[i - 2]) / 6)).join(",")}`
    : signature(b.text);
  const zone = (b, p) => {
    if (!b.bbox || !["paragraph", "heading", "list_item", "figure"].includes(b.type)) return null;
    const [x0, y0, x1, y1] = b.bbox;
    if (b.type !== "figure" && x1 - x0 < p.width * 0.06 && y1 - y0 > p.height * 0.1 &&
        (x1 <= p.width * 0.1 || x0 >= p.width * 0.9)) return "margin"; // side stamp (arXiv id…)
    if (b.bbox[3] <= p.height * EDGE_ZONE + 20 || (b.type === "figure" && b.bbox[1] <= p.height * EDGE_ZONE)) return "header";
    if (b.bbox[1] >= p.height * (1 - EDGE_ZONE) - 20) return "footer";
    return null;
  };
  const counts = new Map();
  for (const p of pages) {
    const seen = new Set();
    for (const b of p.blocks) { const z = zone(b, p); if (z) seen.add(z + "|" + key(b)); }
    for (const k of seen) counts.set(k, (counts.get(k) || 0) + 1);
  }
  const need = Math.max(2, Math.ceil(pages.length * 0.5));
  for (const p of pages)
    for (const b of p.blocks) {
      const z = zone(b, p);
      if (!z) continue;
      const k = key(b);
      if (z === "margin") b.type = "header";
      else if (b.type !== "figure" && PAGE_NUMBER.test(b.text.trim())) b.type = "page_number";
      else if (pages.length >= 2 && (counts.get(z + "|" + k) || 0) >= (b.type === "figure" ? 2 : need) && k.length >= 3) b.type = z;
    }
}

function classifyHeadings(pages, body) {
  const candidates = [];
  for (const p of pages) {
    p.blocks.forEach((b, i) => {
      // A one-line "list item" set bold or bigger than the body is a numbered section heading.
      const neighbours = [p.blocks[i - 1], p.blocks[i + 1]].filter(Boolean).map((x) => x.type);
      if (b.type === "list_item" && !neighbours.includes("list_item") && b.lines === 1 && b.marker &&
          /^\d/.test(b.marker) && b.text.length <= 80 &&
          ((b.font_size || body) >= body * 1.25 || (b.bold && !/\.$/.test(b.text.trimEnd())))) {
        b.text = `${b.marker} ${b.text}`;
        b.type = "paragraph";
        delete b.marker;
      }
      if (b.type !== "paragraph" || !b.text) return;
      const text = b.text.trim();
      if (b.lines > 3 || text.length > 200 || /[,;]$/.test(text) || CAPTION.test(text)) return;
      const size = b.font_size || body;
      const nxt = p.blocks.slice(i + 1).find((x) => !FURNITURE.has(x.type));
      const letters = [...text].filter((c) => /\p{L}/u.test(c));
      const caps = letters.length >= 4 && letters.every((c) => c === c.toUpperCase() && c !== c.toLowerCase()) && text.length <= 90;
      const kv = KEY_VALUE.test(text);
      if (size >= body * 1.18 && !kv) candidates.push([b, "size"]);
      else if (kv) return;
      else if (b.bold && text.length <= 140 && b.lines <= 2 && !text.endsWith(".") && (!nxt || !nxt.bold || nxt.type !== "paragraph")) candidates.push([b, "bold"]);
      else if (caps && b.lines === 1 && !text.endsWith(".")) candidates.push([b, "caps"]);
    });
  }
  const levels = [...new Set(candidates.filter(([, w]) => w === "size").map(([b]) => Math.round((b.font_size || body) * 2) / 2))]
    .sort((a, b) => b - a).slice(0, 3);
  const top = levels.length;
  for (const [b, why] of candidates) {
    b.type = "heading";
    if (why === "size") {
      const key = Math.round((b.font_size || body) * 2) / 2;
      b.level = levels.includes(key) ? levels.indexOf(key) + 1 : top;
    } else b.level = Math.min(6, top + 1);
    const m = NUMBERED_HEADING.exec(b.text);
    if (m && why !== "size") b.level = Math.min(6, Math.max(b.level, (m[1].match(/\./g) || []).length + 1 + (top ? 1 : 0)));
  }
}

function linkCaptions(page) {
  const targets = page.blocks.filter((b) => (b.type === "figure" || b.type === "table") && b.bbox);
  for (const b of page.blocks) {
    if (!["paragraph", "heading"].includes(b.type) || !b.bbox || !CAPTION.test(b.text.trim()) || b.text.length > 400) continue;
    let best = null, dist = Infinity;
    for (const t of targets) {
      if (Math.min(b.bbox[2], t.bbox[2]) - Math.max(b.bbox[0], t.bbox[0]) <= 0) continue;
      const d = Math.min(Math.abs(b.bbox[1] - t.bbox[3]), Math.abs(t.bbox[1] - b.bbox[3]));
      if (d < dist) [best, dist] = [t, d];
    }
    if (best && dist <= 60) {
      b.type = "caption"; delete b.level;
      if (!best.caption) best.caption = b.text;
    } else if (b.lines <= 3 && STRICT_CAPTION.test(b.text.trim())) {
      b.type = "caption"; delete b.level;
    }
  }
}

async function cropImages(pdfPage, page, opts) {
  const wanted = new Set(["figure", "table", "formula"]);
  const targets = page.blocks.filter((b) => wanted.has(b.type) && b.bbox);
  if (!targets.length) return;
  const scale = opts.imageScale || 2;
  const viewport = pdfPage.getViewport({ scale, rotation: 0 });
  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil(viewport.width);
  canvas.height = Math.ceil(viewport.height);
  await pdfPage.render({ canvasContext: canvas.getContext("2d"), viewport, background: "white" }).promise;
  const counters = {};
  for (const b of targets) {
    const pad = 3;
    const x0 = Math.max(0, (b.bbox[0] - pad) * scale), y0 = Math.max(0, (b.bbox[1] - pad) * scale);
    const x1 = Math.min(canvas.width, (b.bbox[2] + pad) * scale), y1 = Math.min(canvas.height, (b.bbox[3] + pad) * scale);
    const w = Math.round(x1 - x0), h = Math.round(y1 - y0);
    if (w < 4 || h < 4) continue;
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    c.getContext("2d").drawImage(canvas, x0, y0, w, h, 0, 0, w, h);
    counters[b.type] = (counters[b.type] || 0) + 1;
    const data = c.toDataURL("image/png").split(",")[1];
    b.image = { name: `p${page.number}-${b.type}-${counters[b.type]}.png`, mime: "image/png", width: w, height: h, data };
  }
  canvas.width = canvas.height = 0; // free memory early
}

export function parsePageSpec(spec, count) {
  if (!spec || !spec.trim()) return [...Array(count).keys()];
  const sel = new Set();
  for (const part of spec.replace(/\s/g, "").split(",")) {
    if (!part) continue;
    let a, b;
    if (part.includes("-")) {
      const [s, e] = part.split("-");
      a = s ? parseInt(s, 10) : 1;
      b = e ? parseInt(e, 10) : count;
    } else a = b = parseInt(part, 10);
    if (!Number.isFinite(a) || !Number.isFinite(b) || a < 1 || b < a) throw new Error(`Intervalo de páginas inválido: '${part}'`);
    if (a > count) throw new Error(`Página ${a} não existe (o documento tem ${count} páginas)`);
    for (let i = a; i <= Math.min(b, count); i++) sel.add(i - 1);
  }
  if (!sel.size) throw new Error("Nenhuma página selecionada");
  return [...sel].sort((x, y) => x - y);
}

async function readMetadata(pdf) {
  try {
    const { info } = await pdf.getMetadata();
    const map = { Title: "title", Author: "author", Subject: "subject", Keywords: "keywords", Producer: "producer", Creator: "creator_tool", CreationDate: "created", ModDate: "modified", PDFFormatVersion: "pdf_version" };
    const out = {};
    for (const [k, v] of Object.entries(map)) if (info?.[k]) out[v] = String(info[k]);
    return out;
  } catch { return {}; }
}

/**
 * Extract a structured document in the browser.
 * @param {ArrayBuffer} data
 * @param {{pages?: string, password?: string, tables?: boolean, formulas?: boolean, images?: boolean,
 *          imageScale?: number, onProgress?: (done:number, total:number) => void}} opts
 * @returns {Promise<{doc: object, pdf: any}>}
 */
export async function extractDocument(data, opts = {}) {
  const started = performance.now();
  const o = { tables: true, formulas: true, images: false, imageScale: 2, ...opts };
  const task = pdfjsLib.getDocument({ data: new Uint8Array(data), password: o.password || undefined, isEvalSupported: false });
  let pdf;
  try {
    pdf = await task.promise;
  } catch (e) {
    if (e?.name === "PasswordException") throw Object.assign(new Error("PDF protegido por senha ou senha incorreta."), { code: "encrypted_pdf" });
    throw Object.assign(new Error("Arquivo não é um PDF válido ou está corrompido."), { code: "invalid_pdf" });
  }
  const indices = parsePageSpec(o.pages, pdf.numPages);
  const results = [];
  for (const [k, i] of indices.entries()) {
    results.push(await analyzePage(pdf, i + 1, o));
    o.onProgress?.(k + 1, indices.length);
  }
  const layoutMs = performance.now() - started;
  const total = new Map();
  for (const r of results) for (const [k, n] of r.sizes) total.set(k, (total.get(k) || 0) + n);
  let body = 10, bestN = 0;
  for (const [k, n] of total) if (n > bestN) [body, bestN] = [k, n];

  const pages = results.map((r) => r.page);
  markFurniture(pages);
  classifyHeadings(pages, body);
  for (const p of pages) {
    linkCaptions(p);
    layoutFormat(p);
    p.blocks.forEach((b, n) => {
      b.order = n; b.id = `p${p.number}-b${n}`;
      if (b.font_size) {
        b.style = { size: Math.round(b.font_size * 10) / 10, bold: !!b.bold };
        if (b.pt) b.style.pt = b.pt;
        if (b.font) b.style.font = b.font;
        if (b.tracking) b.style.tracking = b.tracking;
      }
      delete b.font_size; delete b.bold; delete b.lines; delete b.line_boxes; delete b.pt; delete b.font; delete b.tracking;
      if (b.number === null) delete b.number;
    });
  }
  if (o.images) for (const r of results) await cropImages(r.pdfPage, r.page, o);

  const lowText = results.filter((r) => r.chars < SCANNED_CHARS_PER_PAGE).length;
  const elapsed = performance.now() - started;
  const doc = {
    schema: SCHEMA,
    engine: "pdf.js",
    source_type: "application/pdf",
    page_count: pdf.numPages,
    pages_extracted: pages.length,
    likely_scanned: results.length > 0 && lowText >= Math.max(1, Math.ceil(results.length * 0.5)),
    metadata: await readMetadata(pdf),
    elapsed_ms: Math.round(elapsed * 10) / 10,
    timings: { layout_ms: Math.round(layoutMs * 10) / 10, total_ms: Math.round(elapsed * 10) / 10 },
    warnings: [],
    pages,
  };
  return { doc, pdf };
}

export async function openPdf(data, password) {
  return pdfjsLib.getDocument({ data: new Uint8Array(data), password: password || undefined, isEvalSupported: false }).promise;
}
