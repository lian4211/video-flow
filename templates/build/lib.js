"use strict";
/* video-flow shared library: layout, text, shapes, background, transitions, HUD. */

const W = window.FORMAT.w, H = window.FORMAT.h;
const PORTRAIT = window.FORMAT.portrait;
const C = window.STYLE.colors;
const F = window.STYLE.font;
const PANEL = window.STYLE.panel;
const BG = window.STYLE.background;
const FONT = F.body;
const MONO = F.mono;

const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const c01 = x => clamp(x, 0, 1);
const seg = (t, a, b) => c01((t - a) / (b - a));
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = x => { x = c01(x); return x * x * (3 - 2 * x); };
const eOut = x => 1 - Math.pow(1 - c01(x), 3);
const eInOut = x => { x = c01(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const ease = eOut;
const hash = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const rgba = (hex, a) => {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
};

function layout() {
  const pad = PORTRAIT ? 64 : 96;
  const top = PORTRAIT ? 150 : 92;
  const bottom = PORTRAIT ? 240 : 92;
  return {
    portrait: PORTRAIT,
    pad, top, bottom,
    contentW: W - pad * 2,
    contentH: H - top - bottom,
    titleSize: PORTRAIT ? 74 : 104,
    h2Size: PORTRAIT ? 52 : 64,
    bodySize: PORTRAIT ? 34 : 30,
    smallSize: PORTRAIT ? 26 : 20,
    lineH: PORTRAIT ? 1.55 : 1.45,
    cols: PORTRAIT ? 1 : 2
  };
}

function font(size, weight = 700, family = FONT) {
  return `${weight} ${size}px ${family}`;
}

function txt(s, x, y, o = {}) {
  const { size = 32, weight = 700, color = C.text, align = "left", base = "middle",
    alpha = 1, blur = 0, glow = null, spacing = 0, family = FONT } = o;
  if (alpha <= 0 || s === undefined || s === null || s === "") return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.fillStyle = color;
  ctx.textAlign = align;
  ctx.textBaseline = base;
  ctx.font = font(size, weight, family);
  if (spacing) ctx.letterSpacing = spacing + "px";
  if (blur) { ctx.shadowColor = glow || color; ctx.shadowBlur = blur; }
  ctx.fillText(String(s), x, y);
  ctx.restore();
}

function wrapLines(s, maxW, size, weight = 500, family = FONT) {
  ctx.save();
  ctx.font = font(size, weight, family);
  const chars = String(s).split("");
  const lines = [];
  let line = "";
  for (const ch of chars) {
    const test = line + ch;
    if (ctx.measureText(test).width > maxW && line) {
      lines.push(line);
      line = ch;
    } else line = test;
  }
  if (line) lines.push(line);
  ctx.restore();
  return lines;
}

function para(s, x, y, maxW, o = {}) {
  const { size = 30, weight = 500, color = C.text, lineH = 1.5, alpha = 1, family = FONT, align = "left" } = o;
  const lines = wrapLines(s, maxW, size, weight, family);
  const lh = size * lineH;
  lines.forEach((line, i) => txt(line, x, y + i * lh, { size, weight, color, alpha, family, align }));
  return lines.length * lh;
}

function rr(x, y, w, h, r = PANEL.radius) {
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, r);
  else ctx.rect(x, y, w, h);
}

function panel(x, y, w, h, o = {}) {
  const { radius = PANEL.radius, fill = true, stroke = true, alpha = 1, accent = C.accent,
    fillAlpha = PANEL.fillAlpha, strokeAlpha = PANEL.strokeAlpha, glow = PANEL.glow, lw = 1.6 } = o;
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  rr(x, y, w, h, radius);
  if (fill) { ctx.fillStyle = rgba(C.panel, fillAlpha); ctx.fill(); }
  if (stroke) {
    ctx.strokeStyle = rgba(accent, strokeAlpha);
    ctx.lineWidth = lw;
    if (glow) { ctx.shadowColor = rgba(accent, .5); ctx.shadowBlur = glow; }
    ctx.stroke();
  }
  ctx.restore();
}

function line(x1, y1, x2, y2, o = {}) {
  const { color = C.accent, alpha = 1, width = 2, dash = null, glow = 0 } = o;
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  if (dash) ctx.setLineDash(dash);
  if (glow) { ctx.shadowColor = color; ctx.shadowBlur = glow; }
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  ctx.restore();
}

function arrow(x1, y1, x2, y2, o = {}) {
  const { color = C.accent, alpha = 1, width = 3, head = 12, glow = 0 } = o;
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = width;
  if (glow) { ctx.shadowColor = color; ctx.shadowBlur = glow; }
  const a = Math.atan2(y2 - y1, x2 - x1);
  const bx = x2 - Math.cos(a) * head * .9, by = y2 - Math.sin(a) * head * .9;
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(bx, by); ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - Math.cos(a - .42) * head, y2 - Math.sin(a - .42) * head);
  ctx.lineTo(x2 - Math.cos(a + .42) * head, y2 - Math.sin(a + .42) * head);
  ctx.closePath(); ctx.fill();
  ctx.restore();
}

function dot(x, y, r, color, alpha = 1, glow = 0) {
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.fillStyle = color;
  if (glow) { ctx.shadowColor = color; ctx.shadowBlur = glow; }
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

function ring(x, y, r, o = {}) {
  const { color = C.accent, alpha = 1, width = 1.5, dash = null } = o;
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.strokeStyle = color; ctx.lineWidth = width;
  if (dash) ctx.setLineDash(dash);
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
  ctx.restore();
}

function chip(x, y, w, h, o = {}) {
  const { label = "", color = C.accent, alpha = 1, glow = 12, sub = "" } = o;
  if (alpha <= 0) return;
  panel(x, y, w, h, { accent: color, glow, alpha });
  if (label) txt(label, x + w / 2, y + h / 2 - (sub ? 8 : 0), {
    size: Math.min(44, h * .28), weight: 800, color: C.text, align: "center", blur: 10, glow: rgba(color, .45)
  });
  if (sub) txt(sub, x + w / 2, y + h / 2 + 26, { size: 16, color: C.muted, align: "center" });
}

function fadeInOut(u, D, inT = .4, outT = .35) {
  return smooth(seg(u, 0, inT)) * (1 - smooth(seg(u, D - outT, D)));
}

/* ---------------- background ---------------- */
const PARTICLES = [];
for (let i = 0; i < 60; i++) {
  PARTICLES.push({ x: hash(i * 2.3) * W, y: hash(i * 5.1) * H, r: .6 + hash(i * 9.4) * 1.8,
    sp: .4 + hash(i * 4.2) * 1.5, a: .05 + hash(i * 8.8) * .13, ph: hash(i * 3.3) * 6.28 });
}

function gradient(a, b) {
  const g = ctx.createLinearGradient(0, 0, W, H);
  g.addColorStop(0, a); g.addColorStop(1, b);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}

function vignette(strength = .55) {
  const g = ctx.createRadialGradient(W / 2, H / 2, H * .25, W / 2, H / 2, H * .95);
  g.addColorStop(0, "rgba(0,0,0,0)"); g.addColorStop(1, `rgba(0,0,0,${strength})`);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}

function drawBackground(t) {
  if (BG === "circuit") {
    gradient(window.STYLE.bg[0], window.STYLE.bg[1]);
    const g = ctx.createRadialGradient(W * .7, H * .3, 0, W * .7, H * .3, W * .5);
    g.addColorStop(0, rgba(C.accent, .06)); g.addColorStop(1, rgba(C.accent, 0));
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.save();
    ctx.strokeStyle = rgba(C.accent, .045); ctx.lineWidth = 1;
    const off = (t * 6) % 80;
    for (let x = -80 + off; x < W + 80; x += 80) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = -80 + off; y < H + 80; y += 80) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    ctx.restore();
    for (const p of PARTICLES) {
      const y = (p.y - t * 6 * p.sp) % (H + 120);
      dot(p.x + Math.sin(t * .25 + p.ph) * 16, y < 0 ? y + H + 120 : y, p.r, rgba(C.accent, .8), p.a);
    }
    vignette(.6);
  } else if (BG === "paper") {
    gradient(window.STYLE.bg[0], window.STYLE.bg[1]);
    ctx.save();
    for (let y = 0; y < H; y += 46) line(0, y, W, y, { color: rgba(C.line, .05), width: 1 });
    for (let i = 0; i < 40; i++) {
      const x = hash(i * 3.7) * W, y = hash(i * 7.7) * H, l = 1 + hash(i * 5.3) * 2.2;
      dot(x, y, l, rgba(C.line, .10), .6);
    }
    ctx.restore();
    const g = ctx.createRadialGradient(W * .3, H * .25, 0, W * .3, H * .25, W * .7);
    g.addColorStop(0, rgba("#ffffff", .35)); g.addColorStop(1, rgba("#ffffff", 0));
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  } else if (BG === "grid") {
    gradient(window.STYLE.bg[0], window.STYLE.bg[1]);
    ctx.save();
    ctx.strokeStyle = rgba(C.accent, .18); ctx.lineWidth = 1;
    for (let x = 0; x <= W; x += 48) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y <= H; y += 48) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    ctx.strokeStyle = rgba(C.accent, .35); ctx.lineWidth = 1.6;
    ctx.strokeRect(48, 48, W - 96, H - 96);
    ctx.restore();
    vignette(.35);
  } else if (BG === "nebula") {
    gradient(window.STYLE.bg[0], window.STYLE.bg[1]);
    const g1 = ctx.createRadialGradient(W * .2, H * .8, 0, W * .2, H * .8, W * .55);
    g1.addColorStop(0, rgba(C.accent, .18)); g1.addColorStop(1, rgba(C.accent, 0));
    ctx.fillStyle = g1; ctx.fillRect(0, 0, W, H);
    const g2 = ctx.createRadialGradient(W * .85, H * .2, 0, W * .85, H * .2, W * .5);
    g2.addColorStop(0, rgba(C.accent2, .16)); g2.addColorStop(1, rgba(C.accent2, 0));
    ctx.fillStyle = g2; ctx.fillRect(0, 0, W, H);
    for (const p of PARTICLES) {
      const y = (p.y - t * 10 * p.sp) % (H + 120);
      dot(p.x, y < 0 ? y + H + 120 : y, p.r, rgba(C.accent2, .9), p.a * 1.2, 6);
    }
    vignette(.65);
  } else { // swiss
    ctx.fillStyle = window.STYLE.bg[0]; ctx.fillRect(0, 0, W, H);
    ctx.save();
    ctx.strokeStyle = rgba(C.text, .06); ctx.lineWidth = 1;
    for (let i = 0; i <= 12; i++) { const x = (W / 12) * i; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    ctx.restore();
  }
}

/* ---------------- transitions & HUD ---------------- */
function drawCut(t) {
  for (const sc of SCENES) {
    if (sc.start <= 0) continue;
    const b = sc.start;
    if (t > b - .36 && t < b + .08) {
      const p = seg(t, b - .36, b + .08);
      if (BG === "paper" || BG === "swiss") {
        const x = lerp(-W * .4, W * 1.2, p);
        ctx.save();
        ctx.fillStyle = BG === "paper" ? rgba("#efe7d6", .92) : rgba("#ffffff", .92);
        ctx.fillRect(x - W * .2, 0, W * .4, H);
        ctx.restore();
      } else {
        ctx.save();
        ctx.globalCompositeOperation = "lighter";
        const x = lerp(-300, W + 300, p);
        const g = ctx.createLinearGradient(x - 260, 0, x + 260, 0);
        g.addColorStop(0, rgba(C.accent, 0)); g.addColorStop(.5, rgba(C.accent, .45)); g.addColorStop(1, rgba(C.accent, 0));
        ctx.fillStyle = g; ctx.fillRect(x - 260, 0, 520, H);
        ctx.restore();
      }
    }
  }
}

function drawHUD(t) {
  const meta = (window.CONTENT && window.CONTENT.meta) || {};
  txt(meta.title || "", PORTRAIT ? 40 : 56, 28, { size: 18, weight: 600, color: C.muted, alpha: .65 });
  if (meta.format) txt(meta.format, W - (PORTRAIT ? 40 : 56), 28, { size: 16, color: C.muted, alpha: .45, align: "right" });
  // progress
  const pad = PORTRAIT ? 40 : 56;
  ctx.save();
  ctx.fillStyle = rgba(C.text, .10); ctx.fillRect(pad, H - 34, W - pad * 2, 2);
  ctx.fillStyle = rgba(C.accent, .8); ctx.fillRect(pad, H - 34, (W - pad * 2) * (t / (window.TOTAL || 1)), 2);
  ctx.restore();
  const idx = SCENES.findIndex(s => t >= s.start && t < s.start + s.dur);
  if (idx >= 0) txt(`${String(idx).padStart(2, "0")} / ${String(SCENES.length - 1).padStart(2, "0")}`,
    W - pad, H - 58, { size: 15, color: C.muted, alpha: .5, align: "right", family: MONO });
  const brand = window.BRAND || {};
  if (brand.enabled && brand.footer) txt(brand.footer, pad, H - 58, { size: 15, color: C.muted, alpha: .5 });
}

function sceneAlpha(t, sc) {
  return smooth(seg(t - sc.start, 0, .32)) * (1 - smooth(seg(t - sc.start, sc.dur - .3, sc.dur)));
}

window.LIB = { W, H, PORTRAIT, C, F, layout, txt, para, wrapLines, panel, rr, line, arrow, dot, ring, chip,
  fadeInOut, clamp, c01, seg, lerp, smooth, eOut, eInOut, ease, hash, rgba, drawBackground, drawCut, drawHUD,
  sceneAlpha, font };
