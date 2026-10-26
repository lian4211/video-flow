#!/usr/bin/env node
// Build transparent MathJax SVG data URIs for every *_tex field and every
// inline $...$ fragment in script.json. Canvas can then drawImage() them.
//
// Install (once per project):
//   npm init -y && npm install mathjax-full@3
//
// Usage:
//   node scripts/build_math_svgs.js --project .
//   node scripts/build_math_svgs.js --project . --colors "#E8F1FA,#FFD166"
//   node scripts/build_math_svgs.js --project . --script script.json --out build/math_svgs.js
//
// Outputs:
//   build/math_svgs.js   window.MATH_SVG = { "<tex>|<color>": "data:image/svg+xml;base64,..." }
//   build/math_tex.json  unique TeX list (debug / preflight)
const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

function arg(name, def) {
  const i = process.argv.indexOf(name);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : def;
}

const ROOT = path.resolve(arg("--project", "."));
const SCRIPT = path.resolve(ROOT, arg("--script", "script.json"));
const OUT = path.resolve(ROOT, arg("--out", "build/math_svgs.js"));
const COLORS = (arg("--colors", "#E8F1FA,#FFD166")).split(",").map(s => s.trim()).filter(Boolean);

function loadMathJax() {
  const candidates = [
    path.join(ROOT, "package.json"),
    path.join(ROOT, "tools", "package.json"),
    path.join(__dirname, "..", "package.json"),
    __filename,
  ];
  for (const p of candidates) {
    try {
      const req = createRequire(p);
      return {
        mathjax: req("mathjax-full/js/mathjax.js").mathjax,
        TeX: req("mathjax-full/js/input/tex.js").TeX,
        SVG: req("mathjax-full/js/output/svg.js").SVG,
        liteAdaptor: req("mathjax-full/js/adaptors/liteAdaptor.js").liteAdaptor,
        RegisterHTMLHandler: req("mathjax-full/js/handlers/html.js").RegisterHTMLHandler,
        AllPackages: req("mathjax-full/js/input/tex/AllPackages.js").AllPackages,
      };
    } catch (e) { /* try next */ }
  }
  console.error("Cannot resolve mathjax-full. Run: npm install mathjax-full@3 (in project root or skill root).");
  process.exit(2);
}

const { mathjax, TeX, SVG, liteAdaptor, RegisterHTMLHandler, AllPackages } = loadMathJax();
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const tex = new TeX({ packages: AllPackages });
const svg = new SVG({ fontCache: "none" });
const doc = mathjax.document("", { InputJax: tex, OutputJax: svg });

function render(texString, color) {
  const node = doc.convert(texString, { display: true });
  let out = adaptor.innerHTML(node);
  // data-URI SVG has no CSS context, so resolve currentColor at build time.
  out = out.split("currentColor").join(color);
  return "data:image/svg+xml;base64," + Buffer.from(out, "utf8").toString("base64");
}

function walk(obj, out) {
  if (typeof obj === "string") {
    for (const m of obj.matchAll(/\$([^$]+)\$/g)) out.add(m[1].trim());
    return;
  }
  if (Array.isArray(obj)) { obj.forEach(v => walk(v, out)); return; }
  if (!obj || typeof obj !== "object") return;
  for (const [k, v] of Object.entries(obj)) {
    if (typeof v === "string") {
      if (k.endsWith("_tex") && v.trim()) out.add(v.trim());
      for (const m of v.matchAll(/\$([^$]+)\$/g)) out.add(m[1].trim());
    } else {
      walk(v, out);
    }
  }
}

if (!fs.existsSync(SCRIPT)) {
  console.error("missing script:", SCRIPT);
  process.exit(2);
}
const texSet = new Set();
walk(JSON.parse(fs.readFileSync(SCRIPT, "utf8")), texSet);

const map = {};
for (const t of [...texSet].sort()) {
  for (const c of COLORS) map[`${t}|${c}`] = render(t, c);
}

const out = `window.MATH_SVG = ${JSON.stringify(map, null, 0)};\n`;
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, out, "utf8");
fs.writeFileSync(path.join(path.dirname(OUT), "math_tex.json"), JSON.stringify([...texSet].sort(), null, 2), "utf8");
console.log("formulas:", texSet.size, "entries:", Object.keys(map).length, "->", OUT);
