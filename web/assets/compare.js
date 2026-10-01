// Compare view: each page of the PDF next to what was extracted from it, drawn
// block by block in the same place — so a table that came out as text, a formula that came
// out empty or a paragraph that is missing is seen at a glance. On the PDF side, the text
// that is not in the output is marked; on the output side, the blocks that failed a check.

import { esc } from "./export.js";
import { SIGNALS } from "./fidelity.js";

const FURNITURE = new Set(["header", "footer", "page_number"]);
const ERRORS = new Set(["table_not_detected", "text_loss", "no_text"]);
const pct = (score) => (score == null ? "—" : `${(score * 100).toFixed(1)}%`);
const typeColor = (t) => `var(--t-${FURNITURE.has(t) ? "furniture" : t})`;

// ---------------------------------------------------------------- fidelity panel
export function renderFidelity(box, fidelity, { tr, hasReference, onPage }) {
  const code = (c) => (tr(`fid.code.${c}`) === `fid.code.${c}` ? c : tr(`fid.code.${c}`));
  const signals = SIGNALS.map((name) => {
    const s = fidelity.signals[name];
    const detail = s.total ? `${Math.round(s.ok).toLocaleString()} / ${Math.round(s.total).toLocaleString()}` : tr("fid.sig.none");
    return `<div class="fid-signal"><span>${tr(`fid.sig.${name}`)}</span>
      <div class="meter"><i style="width:${s.score == null ? 0 : (s.score * 100).toFixed(1)}%"></i></div>
      <b>${pct(s.score)}</b><small>${detail}</small></div>`;
  }).join("");
  const issues = fidelity.issues.map((i) => `<li class="${i.severity}"><span class="badge">${tr(`fid.sev.${i.severity}`)}</span>
      <span>${esc(code(i.code))} <span class="times">×${i.count}</span></span>
      <span class="fid-pages">${i.pages.map((p) => `<button type="button" data-page="${p}">p. ${p}</button>`).join("")}</span></li>`).join("");
  box.className = `fidelity ${fidelity.status}`;
  box.innerHTML = `
    <div class="fid-head"><b>${pct(fidelity.score)}</b>
      <div><strong>${tr("fid.title")}</strong> <span class="badge">${tr(`fid.status.${fidelity.status}`)}</span>
      <p class="hint">${tr("fid.note")}${hasReference ? "" : " " + tr("fid.nopdf")}</p></div></div>
    <div class="fid-signals">${signals}</div>
    ${issues ? `<ul class="fid-issues">${issues}</ul>` : `<p class="hint">${tr("fid.none")}</p>`}`;
  box.querySelectorAll("button[data-page]").forEach((b) => b.addEventListener("click", () => onPage(+b.dataset.page)));
}

// ---------------------------------------------------------------- one block of the output
// Shrinks the type until the content fits its box: the page was set in another font.
function fit(el) {
  let size = parseFloat(el.style.fontSize);
  for (let k = 0; k < 16 && size > 3 && (el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1); k++) {
    size *= 0.92;
    el.style.fontSize = `${size}px`;
    if (el.style.lineHeight.endsWith("px")) el.style.lineHeight = `${parseFloat(el.style.lineHeight) * 0.92}px`;
  }
}

function blockEl(b, scale, codes, { tr, typeLabel, onSelect }) {
  const [x0, y0, x1, y1] = b.bbox;
  const el = document.createElement("div");
  el.className = "rb" + (FURNITURE.has(b.type) ? " furniture" : "");
  el.dataset.type = b.type;
  el.dataset.id = b.id;
  const size = (b.style?.pt || b.style?.size || 9) * scale;
  el.style.cssText = `--c:${typeColor(b.type)};left:${x0 * scale}px;top:${y0 * scale}px;width:${(x1 - x0) * scale}px;height:${(y1 - y0) * scale}px;font-size:${size}px;`
    + `line-height:${b.format?.leading ? `${b.format.leading * scale}px` : "1.2"};`
    + (b.format?.align ? `text-align:${b.format.align};` : "")
    + (b.style?.font ? `font-family:"${b.style.font.replace(/[^\p{L}\p{N} -]/gu, "")}",Georgia,serif;` : "")
    + (b.style?.bold || b.type === "heading" ? "font-weight:650;" : "");
  let title = typeLabel(b.type);
  if (b.type === "table" && b.rows) {
    el.innerHTML = `<table>${b.rows.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</table>`;
  } else if (b.type === "formula") {
    if (b.latex && window.katex) {
      try { window.katex.render(b.latex, el, { displayMode: false, throwOnError: false }); } catch { el.textContent = b.text; }
    } else el.textContent = b.text || "";
    el.classList.add("center");
  } else if (b.type === "figure") {
    if (b.image?.data) el.innerHTML = `<img alt="" src="data:${b.image.mime};base64,${b.image.data}">`;
    else { el.classList.add("placeholder", "center"); el.textContent = typeLabel("figure"); }
  } else {
    el.textContent = (b.type === "list_item" && b.marker ? `${b.marker} ` : "") + (b.text || "");
  }
  if (codes?.length) {
    const error = codes.some((c) => ERRORS.has(c));
    el.classList.add("flagged", error ? "error" : "warning");
    title += " — " + codes.map((c) => tr(`fid.code.${c}`)).join("; ");
    const tag = document.createElement("span");
    tag.className = "rtag";
    tag.textContent = codes.map((c) => tr(`fid.tag.${c}`)).join(" · ");
    el.append(tag);
  }
  el.title = title;
  el.addEventListener("click", () => onSelect(b));
  return el;
}

// ---------------------------------------------------------------- pages
let observer;

async function paintOriginal(pane, pdf, number, scale, missing) {
  if (pdf) {
    const page = await pdf.getPage(number);
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const viewport = page.getViewport({ scale: scale * dpr, rotation: 0 });
    const canvas = document.createElement("canvas");
    canvas.width = Math.floor(viewport.width);
    canvas.height = Math.floor(viewport.height);
    canvas.style.width = `${viewport.width / dpr}px`;
    canvas.style.height = `${viewport.height / dpr}px`;
    pane.prepend(canvas);
    await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
  }
  for (const [x0, y0, x1, y1] of missing) {
    const m = document.createElement("i");
    m.className = "miss";
    m.style.cssText = `left:${x0 * scale - 1}px;top:${y0 * scale - 1}px;width:${(x1 - x0) * scale + 2}px;height:${(y1 - y0) * scale + 2}px`;
    pane.append(m);
  }
}

function paintOutput(pane, page, scale, flags, ctx) {
  const els = page.blocks.filter((b) => b.bbox).map((b) => blockEl(b, scale, flags.get(b.id), ctx));
  pane.append(...els);
  for (const el of els) if (!el.querySelector("img")) fit(el);
}

export function renderCompare(list, { doc, pdf, fidelity, onlyProblems, tr, typeLabel, onSelect }) {
  observer?.disconnect();
  list.innerHTML = "";
  const avail = (list.clientWidth || 800) - 18; // room for the scrollbar the pages bring in
  const side = avail >= 640; // narrower than that, the output goes under its page
  const paneWidth = side ? (avail - 16) / 2 : Math.min(avail, 900);
  const ctx = { tr, typeLabel, onSelect };
  const jobs = new Map();
  observer = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { observer.unobserve(e.target); jobs.get(e.target)?.(); }
  }, { rootMargin: "400px" });

  let shown = 0;
  for (const page of doc.pages) {
    if (!page.width) continue;
    const mark = fidelity.pages.get(page.number) || { missing: [], flags: new Map() };
    const problems = mark.missing.length + mark.flags.size;
    if (onlyProblems && !problems) continue;
    shown++;
    const scale = paneWidth / page.width;
    const size = `width:${paneWidth}px;height:${page.height * scale}px`;
    const row = document.createElement("section");
    row.className = "diff-row";
    row.dataset.page = page.number;
    const notes = [
      mark.missing.length ? `<span class="error">${tr("diff.missing", { n: mark.missing.length })}</span>` : "",
      mark.flags.size ? `<span class="warning">${tr("diff.flags", { n: mark.flags.size })}</span>` : "",
    ].join("");
    row.innerHTML = `<header><b>p. ${page.number}</b>${notes}</header>
      <div class="diff-panes${side ? " two" : ""}">
        <figure><figcaption>${tr("diff.original")}</figcaption><div class="diff-pane original" style="${size}"></div></figure>
        <figure><figcaption>${tr("diff.output")}</figcaption><div class="diff-pane output" style="${size}"></div></figure>
      </div>`;
    const [original, output] = row.querySelectorAll(".diff-pane");
    jobs.set(row, () => {
      paintOutput(output, page, scale, mark.flags, ctx);
      paintOriginal(original, pdf, page.number, scale, mark.missing);
    });
    list.append(row);
    observer.observe(row);
  }
  if (!shown) list.innerHTML = `<p class="hint">${tr(onlyProblems ? "diff.empty" : "no.positions")}</p>`;
}
