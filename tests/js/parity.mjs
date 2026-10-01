// Runs web/assets/engine.js under Node and compares it with the Python engine's output
// (written by expected.py). Usage: python expected.py out && node parity.mjs out
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dir = process.argv[2] || join(here, "out");
const src = readFileSync(join(here, "../../web/assets/engine.js"), "utf8")
  .replace(/https:\/\/cdn\.jsdelivr\.net\/npm\/pdfjs-dist@[\d.]+\/build\/pdf\.min\.mjs/, "pdfjs-dist/legacy/build/pdf.mjs")
  .replace(/pdfjsLib\.GlobalWorkerOptions\.workerSrc =\s*"[^"]+";/, "")
  .replace(/"\.\/(\w+\.js)"/g, (_, f) => JSON.stringify(pathToFileURL(join(here, "../../web/assets", f)).href));
const enginePath = join(here, ".engine.node.mjs");
writeFileSync(enginePath, src);
const { extractDocument, captionText } = await import(pathToFileURL(enginePath).href);
const { assess, referenceItems } = await import(pathToFileURL(join(here, "../../web/assets/fidelity.js")).href);

// The fidelity report (web/assets/fidelity.js against fidelity.py): same verdict, same issues,
// same counts. The text signal reads the page with another library, so only its score is compared.
const verdict = (f) => ({
  status: f.status,
  issues: f.issues.map((i) => [i.code, i.severity, i.count, i.pages]),
  signals: Object.fromEntries(Object.entries(f.signals).map(([n, s]) => [n, n === "text" ? Math.round(s.score * 100) : [s.ok, s.total]])),
});

const view = (doc) =>
  doc.pages.map((p) =>
    p.blocks.map((b) => {
      const v = { type: b.type };
      if (b.rows) v.rows = b.rows;
      else if (b.type === "formula") v.latex = b.latex;
      else if (b.type !== "figure") v.text = b.text;
      if (b.level != null && b.type === "heading") v.level = b.level;
      return v;
    }));

let failures = 0;
for (const name of ["structured", "hard", "declaration", "exam"]) {
  const data = readFileSync(join(dir, `${name}.pdf`));
  const { doc, pdf } = await extractDocument(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength));
  const js = view(doc);
  const py = view(JSON.parse(readFileSync(join(dir, `${name}.json`), "utf8")));
  py.forEach((pyPage, i) => {
    const a = JSON.stringify(pyPage), b = JSON.stringify(js[i]);
    if (a !== b) {
      failures++;
      console.error(`✗ ${name} p${i + 1}\n  python: ${a}\n  js:     ${b}`);
    } else console.log(`✓ ${name} p${i + 1}: ${pyPage.length} blocks`);
  });
  const jsFid = JSON.stringify(verdict(assess(doc, await referenceItems(pdf, doc.pages.map((p) => p.number)), captionText)));
  const pyFid = JSON.stringify(verdict(JSON.parse(readFileSync(join(dir, `${name}.fidelity.json`), "utf8"))));
  if (jsFid !== pyFid) {
    failures++;
    console.error(`✗ ${name} fidelity
  python: ${pyFid}
  js:     ${jsFid}`);
  } else console.log(`✓ ${name} fidelity: ${JSON.parse(jsFid).status}`);
  if (name === "structured") {
    // Take a paragraph out: the report must say so, and say where on the page it was.
    const first = doc.pages[0];
    const cut = { ...doc, pages: [{ ...first, blocks: first.blocks.filter((b) => b.type !== "paragraph") }, ...doc.pages.slice(1)] };
    const lost = assess(cut, await referenceItems(pdf, doc.pages.map((p) => p.number)), captionText);
    const where = lost.pages.get(1).missing.length;
    if (lost.issues[0]?.code !== "text_loss" || !where || lost.pages.get(2).missing.length) {
      failures++;
      console.error(`✗ ${name} text loss not located: ${JSON.stringify(lost.issues)} (${where} spans)`);
    } else console.log(`✓ ${name} text loss located: ${where} spans on p1`);
  }
}
process.exit(failures ? 1 : 0);
