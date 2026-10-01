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
const { extractDocument } = await import(pathToFileURL(enginePath).href);

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
  const { doc } = await extractDocument(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength));
  const js = view(doc);
  const py = view(JSON.parse(readFileSync(join(dir, `${name}.json`), "utf8")));
  py.forEach((pyPage, i) => {
    const a = JSON.stringify(pyPage), b = JSON.stringify(js[i]);
    if (a !== b) {
      failures++;
      console.error(`✗ ${name} p${i + 1}\n  python: ${a}\n  js:     ${b}`);
    } else console.log(`✓ ${name} p${i + 1}: ${pyPage.length} blocks`);
  });
}
process.exit(failures ? 1 : 0);
