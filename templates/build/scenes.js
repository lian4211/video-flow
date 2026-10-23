"use strict";
/* video-flow generic scenes. Each: (u, D, cs, ctx) => void, using lib.js globals. */

const L = layout();
const CONTENT = window.CONTENT || { meta: {}, scenes: [] };
const SCENE_BY_ID = {};
(CONTENT.scenes || []).forEach(s => { SCENE_BY_ID[s.id] = s; });

function kicker(cs, u, y) {
  const a = smooth(seg(u, .1, .8));
  if (a <= 0) return;
  const yy = y === undefined ? L.top - 34 : y;
  ctx.save(); ctx.globalAlpha *= a;
  ctx.fillStyle = C.accent; ctx.fillRect(L.pad, yy - 15, 5, 30);
  txt(cs.kicker || "", L.pad + 22, yy, { size: L.smallSize, color: C.accent, weight: 700, alpha: .95, spacing: 1 });
  ctx.restore();
}

function headline(cs, u, y, opts = {}) {
  const a = smooth(seg(u, .2, 1.0));
  const size = opts.size || L.h2Size;
  txt(cs.headline || "", opts.x || L.pad, y, {
    size, weight: 800, color: C.text, alpha: a, spacing: .5,
    blur: (BG === "circuit" || BG === "nebula") ? 14 : 0, glow: rgba(C.accent, .25)
  });
}

function marker(x, y, n, color, alpha = 1) {
  ctx.save(); ctx.globalAlpha *= alpha;
  ctx.fillStyle = rgba(color, .16);
  ctx.beginPath(); ctx.arc(x, y, 22, 0, Math.PI * 2); ctx.fill();
  ring(x, y, 22, { color: rgba(color, .7), alpha: .9, width: 1.5 });
  txt(String(n), x, y + 1, { size: 18, weight: 800, color, align: "center", family: MONO });
  ctx.restore();
}

/* ---------------- title ---------------- */
function titleScene(u, D, cs) {
  const a = fadeInOut(u, D, .6, .5);
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a;
  const portrait = PORTRAIT;
  const cx = portrait ? W / 2 : L.pad + L.contentW * .34;
  const cy = portrait ? H * .34 : H * .40;
  const glow = (BG === "circuit" || BG === "nebula") ? 26 : 0;

  // decorative rings / lines
  ctx.save();
  const ringA = 1 - smooth(seg(u, 0, D));
  if (portrait) {
    ring(W / 2, H * .34, 220 + u * 8, { color: rgba(C.accent, .12), width: 1.2 });
    ring(W / 2, H * .34, 300 + u * 5, { color: rgba(C.accent, .08), width: 1 });
  } else {
    ring(cx + 300, cy - 40, 260 + u * 8, { color: rgba(C.accent, .10), width: 1.2 });
    ring(cx + 300, cy - 40, 340 + u * 5, { color: rgba(C.accent, .07), width: 1 });
    line(L.pad, cy + 90, L.pad + 460, cy + 90, { color: rgba(C.accent, .35), width: 2, alpha: .8 });
  }
  ctx.restore();

  txt(cs.kicker || "", portrait ? W / 2 : L.pad, portrait ? H * .18 : cy - 180, {
    size: portrait ? 24 : 24, color: C.accent, align: portrait ? "center" : "left", alpha: .9, spacing: 2
  });
  para(cs.title || "", portrait ? W / 2 : L.pad, portrait ? H * .30 : cy - 50, portrait ? W - L.pad * 2 : L.contentW * .55,
    { size: portrait ? 84 : 112, weight: 800, color: C.text, lineH: 1.15, align: portrait ? "center" : "left", alpha: 1 });
  const subY = portrait ? H * .47 : cy + 110;
  para(cs.subtitle || "", portrait ? W / 2 : L.pad, subY, portrait ? W - L.pad * 2 : L.contentW * .5,
    { size: portrait ? 34 : 32, weight: 500, color: C.muted, lineH: 1.45, align: portrait ? "center" : "left", alpha: .95 });

  // motif: small index / pulse
  const m = smooth(seg(u, 1.2, 2.4));
  if (m > 0) {
    if (portrait) {
      line(W / 2 - 80, H * .56, W / 2 + 80, H * .56, { color: rgba(C.accent, .5), width: 2, alpha: m });
    } else {
      for (let i = 0; i < 5; i++) dot(L.pad + 30 + i * 26, cy + 190, 3.2, rgba(C.accent, .8), m * (.4 + i * .1));
    }
  }
  ctx.restore();
}

/* ---------------- concept ---------------- */
function conceptScene(u, D, cs) {
  const a = fadeInOut(u, D, .5, .4);
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a;
  kicker(cs, u);
  headline(cs, u, L.top + L.h2Size * .55);

  const lead = cs.lead || "";
  const leadSize = PORTRAIT ? L.bodySize * .92 : L.bodySize;
  const leadW = PORTRAIT ? L.contentW : L.contentW * .52;
  let y = L.top + L.h2Size * (PORTRAIT ? 1.9 : 1.45);
  if (lead) {
    const lines = wrapLines(lead, leadW, leadSize, 500);
    para(lead, L.pad, y, leadW, { size: leadSize, color: C.muted, lineH: 1.5, alpha: .95 });
    y += lines.length * leadSize * 1.5 + L.bodySize * .65;
  }

  const points = cs.points || [];
  const pointW = PORTRAIT ? L.contentW - 64 : L.contentW * .46;
  let py = y;
  points.slice(0, 3).forEach((p, i) => {
    const pa = smooth(seg(u, 1.2 + i * .7, 1.8 + i * .7));
    const lines = wrapLines(p, pointW, L.bodySize * .95, 500);
    const h = lines.length * L.bodySize * .95 * 1.4;
    marker(L.pad + 14, py + L.bodySize * .38, i + 1, C.accent, pa);
    para(p, L.pad + 54, py, pointW, { size: L.bodySize * .95, color: C.text, lineH: 1.4, alpha: pa });
    py += h + L.bodySize * .85;
  });

  // visual
  const vx = PORTRAIT ? L.pad : W * .56;
  const vw = PORTRAIT ? L.contentW : W - vx - L.pad;
  let vy, vh;
  if (PORTRAIT) {
    vy = Math.max(py + 20, H * .44);
    vh = H - vy - L.bottom;
  } else {
    vy = L.top + L.h2Size * 1.2;
    vh = H - vy - L.bottom - 10;
  }
  const va = smooth(seg(u, .8, 1.8));
  if (va <= 0 || vh < 120) { ctx.restore(); return; }
  const kind = (cs.visual && cs.visual.kind) || "nodes";

  if (kind === "number") {
    const val = (cs.visual && cs.visual.value) || "1";
    txt(val, vx + vw / 2, vy + vh * .42, { size: Math.min(vh * .8, 220), weight: 800, color: C.accent,
      align: "center", alpha: va, blur: 24, glow: rgba(C.accent, .4), family: MONO });
    txt((cs.visual && cs.visual.unit) || "", vx + vw / 2, vy + vh * .82, { size: 26, color: C.muted, align: "center", alpha: va });
  } else if (kind === "spectrum") {
    const items = (cs.visual && cs.visual.items) || [];
    const n = Math.max(1, items.length);
    const bw = vw / n - 8;
    items.forEach((it, i) => {
      const h = vh * (.25 + .65 * (it.value || (i + 1) / n));
      const x = vx + i * (bw + 8);
      const y = vy + vh - h;
      const ia = smooth(seg(u, 1.0 + i * .12, 1.6 + i * .12)) * va;
      ctx.save(); ctx.globalAlpha *= ia;
      ctx.fillStyle = rgba(it.color || C.accent, .75);
      ctx.fillRect(x, y, bw, h);
      txt(it.label || "", x + bw / 2, vy + vh + 22, { size: 18, color: C.muted, align: "center" });
      ctx.restore();
    });
  } else {
    // nodes
    const cx = vx + vw / 2, cy = vy + vh / 2;
    ring(cx, cy, Math.min(vw, vh) * .34, { color: rgba(C.accent, .18), width: 1.4, dash: [6, 10], alpha: va });
    const labels = (cs.visual && cs.visual.labels) || points.map(p => String(p).slice(0, 6));
    labels.slice(0, 4).forEach((label, i) => {
      const ang = -Math.PI / 2 + i * (Math.PI * 2 / Math.max(1, labels.length));
      const r = Math.min(vw, vh) * .38;
      const x = cx + Math.cos(ang) * r, y = cy + Math.sin(ang) * r;
      const na = smooth(seg(u, 1.1 + i * .3, 1.7 + i * .3)) * va;
      line(cx, cy, x, y, { color: rgba(C.accent, .25), width: 1.2, dash: [4, 8], alpha: na });
      dot(x, y, 6, rgba(C.accent, .9), na, 10);
      txt(label, x, y + (Math.sin(ang) > 0 ? 28 : -28), { size: 18, color: C.muted, align: "center", alpha: na });
    });
    txt((cs.visual && cs.visual.center) || "", cx, cy, { size: 22, color: C.accent, align: "center", alpha: va, family: MONO });
  }
  ctx.restore();
}

/* ---------------- process ---------------- */
function processScene(u, D, cs) {
  const a = fadeInOut(u, D, .5, .4);
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a;
  kicker(cs, u);
  headline(cs, u, L.top + L.h2Size * .55, { size: L.h2Size * .85 });
  const steps = (cs.steps || []).slice(0, 5);
  if (!steps.length) { ctx.restore(); return; }

  if (PORTRAIT) {
    const y0 = L.top + L.h2Size * 1.5;
    const rowH = Math.min(180, (H - y0 - L.bottom) / steps.length - 16);
    steps.forEach((st, i) => {
      const sa = smooth(seg(u, .8 + i * .55, 1.4 + i * .55));
      const y = y0 + i * (rowH + 18);
      panel(L.pad, y, L.contentW, rowH, { alpha: sa, fill: true });
      marker(L.pad + 46, y + rowH / 2, i + 1, C.accent, sa);
      txt(st.title || "", L.pad + 86, y + rowH * .38, { size: 32, weight: 700, color: C.text, alpha: sa });
      if (st.detail) txt(st.detail, L.pad + 86, y + rowH * .68, { size: 22, color: C.muted, alpha: sa });
      if (i < steps.length - 1) arrow(L.pad + L.contentW / 2, y + rowH + 2, L.pad + L.contentW / 2, y + rowH + 16,
        { color: rgba(C.accent, .55), width: 2, head: 9, alpha: sa });
    });
  } else {
    const gap = 26;
    const cw = (L.contentW - gap * (steps.length - 1)) / steps.length;
    const y = L.top + L.h2Size * 2.0;
    const ch = Math.min(300, L.contentH * .52);
    steps.forEach((st, i) => {
      const sa = smooth(seg(u, .8 + i * .5, 1.5 + i * .5));
      const x = L.pad + i * (cw + gap);
      panel(x, y, cw, ch, { alpha: sa });
      txt(String(i + 1).padStart(2, "0"), x + 26, y + 42, { size: 20, color: C.accent, family: MONO, alpha: sa });
      txt(st.title || "", x + 26, y + 92, { size: 28, weight: 700, color: C.text, alpha: sa });
      if (st.detail) para(st.detail, x + 26, y + 140, cw - 52, { size: 20, color: C.muted, lineH: 1.4, alpha: sa });
      if (i < steps.length - 1) arrow(x + cw + 2, y + ch / 2, x + cw + gap - 4, y + ch / 2,
        { color: rgba(C.accent, .55), width: 2.4, head: 10, alpha: sa });
    });
  }
  ctx.restore();
}

/* ---------------- compare ---------------- */
function compareScene(u, D, cs) {
  const a = fadeInOut(u, D, .5, .4);
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a;
  kicker(cs, u);
  headline(cs, u, L.top + L.h2Size * .55, { size: L.h2Size * .85 });
  const left = cs.left || { title: "A", points: [] };
  const right = cs.right || { title: "B", points: [] };
  const y0 = L.top + L.h2Size * 1.6;
  const h = H - y0 - L.bottom;

  function block(x, w, data, color, delay) {
    const ba = smooth(seg(u, delay, delay + .7));
    panel(x, y0, w, h, { alpha: ba, accent: color });
    txt(data.title || "", x + w / 2, y0 + 46, { size: 30, weight: 800, color, align: "center", alpha: ba });
    (data.points || []).slice(0, 3).forEach((p, i) => {
      const pa = smooth(seg(u, delay + .4 + i * .35, delay + 1 + i * .35));
      para(p, x + 26, y0 + 100 + i * 78, w - 52, { size: 22, color: C.text, lineH: 1.35, alpha: pa });
    });
  }

  if (PORTRAIT) {
    const bh = (h - 30) / 2;
    block(L.pad, L.contentW, left, C.accent, .9);
    block(L.pad, L.contentW, right, C.accent2, 1.4);
    txt("VS", W / 2, y0 + h / 2, { size: 26, weight: 800, color: C.muted, align: "center", alpha: .6 });
  } else {
    const gap = 70;
    const bw = (L.contentW - gap) / 2;
    block(L.pad, bw, left, C.accent, .9);
    block(L.pad + bw + gap, bw, right, C.accent2, 1.3);
    const va = smooth(seg(u, 1.8, 2.4));
    txt("VS", W / 2, y0 + h / 2, { size: 34, weight: 800, color: C.muted, align: "center", alpha: va * .7 });
  }
  ctx.restore();
}

/* ---------------- formula ---------------- */
function formulaScene(u, D, cs) {
  const a = fadeInOut(u, D, .5, .4);
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a;
  kicker(cs, u);
  if (cs.headline) txt(cs.headline, W / 2, L.top + 40, { size: 34, weight: 700, color: C.muted, align: "center", alpha: .95 });
  const fa = smooth(seg(u, .8, 1.7));
  const fs = PORTRAIT ? 76 : 110;
  txt(cs.formula || "", W / 2, H * .43, { size: fs, weight: 700, color: C.text, align: "center",
    alpha: fa, family: F.mono, blur: 14, glow: rgba(C.accent, .25) });
  line(W / 2 - 220, H * .43 + fs * .55, W / 2 + 220, H * .43 + fs * .55,
    { color: rgba(C.accent, .5), width: 2, alpha: fa });
  const notes = (cs.notes || []).slice(0, 3);
  notes.forEach((n, i) => {
    const na = smooth(seg(u, 1.6 + i * .4, 2.2 + i * .4));
    const y = H * .43 + fs * .95 + i * (PORTRAIT ? 52 : 42);
    txt("· " + n, W / 2, y, { size: PORTRAIT ? 26 : 22, color: C.muted, align: "center", alpha: na });
  });
  ctx.restore();
}

/* ---------------- bars ---------------- */
function barsScene(u, D, cs) {
  const a = fadeInOut(u, D, .5, .4);
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a;
  kicker(cs, u);
  headline(cs, u, L.top + L.h2Size * .55, { size: L.h2Size * .85 });
  const items = (cs.items || []).slice(0, 6);
  if (!items.length) { ctx.restore(); return; }
  const max = Math.max(...items.map(i => Number(i.value) || 0), 1);
  const areaTop = L.top + L.h2Size * 1.6;
  const avail = H - areaTop - L.bottom;
  const rowH = Math.min(130, avail / items.length);
  const y0 = areaTop + Math.max(0, (avail - rowH * items.length) / 2);
  const labelW = PORTRAIT ? 150 : 220;
  const barX = L.pad + labelW;
  const barW = W - barX - L.pad - 90;
  items.forEach((it, i) => {
    const ba = smooth(seg(u, .9 + i * .25, 1.5 + i * .25));
    const y = y0 + i * rowH;
    txt(it.label || "", L.pad, y + rowH * .45, { size: PORTRAIT ? 22 : 20, color: C.text, alpha: ba });
    const w = barW * (Number(it.value) || 0) / max * eOut(seg(u, 1.1 + i * .25, 2.0 + i * .25));
    ctx.save(); ctx.globalAlpha *= ba;
    ctx.fillStyle = rgba(it.color || C.accent, .75);
    ctx.fillRect(barX, y + rowH * .22, w, rowH * .5);
    ctx.restore();
    txt(String(it.value ?? ""), barX + w + 12, y + rowH * .47, { size: 20, color: C.muted, alpha: ba, family: MONO });
  });
  ctx.restore();
}

/* ---------------- quote ---------------- */
function quoteScene(u, D, cs) {
  const a = fadeInOut(u, D, .5, .4);
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a;
  const q = cs.quote || cs.headline || "";
  para(q, W / 2, H * .40, W - L.pad * 2, { size: PORTRAIT ? 54 : 64, weight: 700, color: C.text,
    lineH: 1.35, align: "center", alpha: smooth(seg(u, .4, 1.4)) });
  if (cs.author) txt("— " + cs.author, W / 2, H * .62, { size: 26, color: C.muted, align: "center", alpha: smooth(seg(u, 1.2, 2)) });
  ctx.restore();
}

/* ---------------- recap ---------------- */
function recapScene(u, D, cs) {
  const a = fadeInOut(u, D, .5, .4);
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a;
  kicker(cs, u);
  const nodes = (cs.nodes || []).slice(0, 5);
  const cy = PORTRAIT ? H * .36 : H * .42;
  const cx = W / 2;
  const ca = smooth(seg(u, .7, 1.5));
  ring(cx, cy, PORTRAIT ? 74 : 88, { color: rgba(C.accent, .6), width: 2, alpha: ca });
  dot(cx, cy, PORTRAIT ? 74 : 88, rgba(C.accent, .08), ca);
  txt("总结", cx, cy, { size: PORTRAIT ? 26 : 24, weight: 800, color: C.accent, align: "center", alpha: ca });

  const R = PORTRAIT ? Math.min(W * .34, 220) : Math.min(W * .30, 330);
  nodes.forEach((n, i) => {
    const ang = -Math.PI / 2 + i * (Math.PI * 2 / Math.max(1, nodes.length));
    const x = cx + Math.cos(ang) * R, y = cy + Math.sin(ang) * R;
    const na = smooth(seg(u, 1.2 + i * .35, 1.9 + i * .35));
    line(cx, cy, x, y, { color: rgba(C.accent, .28), width: 1.4, dash: [5, 8], alpha: na });
    panel(x - 90, y - 26, 180, 52, { alpha: na, radius: 26 });
    txt(n, x, y, { size: PORTRAIT ? 20 : 18, color: C.text, align: "center", alpha: na });
  });
  const ta = smooth(seg(u, 3.2, 4.2));
  if (cs.takeaway) txt(cs.takeaway, W / 2, H - L.bottom + 20, { size: PORTRAIT ? 30 : 26, color: C.accent, align: "center", alpha: ta });
  ctx.restore();
}

/* dispatch */
window.SCENES_IMPL = {
  title: titleScene,
  concept: conceptScene,
  process: processScene,
  compare: compareScene,
  formula: formulaScene,
  bars: barsScene,
  quote: quoteScene,
  recap: recapScene
};
