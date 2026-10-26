/* Optional Canvas helpers for MathJax SVG + mixed Chinese/LaTeX lines.
 *
 * Usage:
 *   <script src="math_svgs.js"></script>
 *   <script src="rich.js"></script>
 *   await RICH.ready();                    // after document.fonts.ready
 *   RICH.drawTex(ctx, "\\int f(x)dx", x, y, {size: 34, maxW: 800});
 *   RICH.drawRich(ctx, "合并：$e^{x+1/x}(1+x-1/x)$", x, y, {size: 26, maxW: 900});
 *
 * This file is intentionally dependency-free; it reads window.MATH_SVG.
 */
(function () {
  const INK = "#E8F1FA";
  const GOLD = "#FFD166";

  function key(tex, color) { return tex + "|" + color; }

  const readyPromise = Promise.all(
    Object.entries(window.MATH_SVG || {}).map(([k, uri]) => new Promise((resolve) => {
      const img = new Image();
      img.onload = img.onerror = () => { window.__mathImages[k] = img; resolve(); };
      img.src = uri;
    }))
  );

  function image(tex, color) {
    const img = (window.__mathImages || {})[key(tex, color)];
    return img && img.naturalWidth ? img : null;
  }

  function drawTex(ctx, tex, x, y, opts) {
    const o = Object.assign({ size: 32, color: INK, maxW: 0, align: "left", hFactor: 1.55 }, opts || {});
    const img = image(tex, o.color);
    if (!img) return 0;
    let h = o.size * o.hFactor;
    let w = h * (img.naturalWidth / img.naturalHeight);
    if (o.maxW && w > o.maxW) { w = o.maxW; h = w * (img.naturalHeight / img.naturalWidth); }
    let dx = x;
    if (o.align === "center") dx = x - w / 2;
    if (o.align === "right") dx = x - w;
    ctx.drawImage(img, dx, y, w, h);
    return w;
  }

  function drawInline(ctx, tex, x, y, opts) {
    const o = Object.assign({ size: 26, color: INK, hFactor: 1.7 }, opts || {});
    const img = image(tex, o.color);
    if (!img) return 0;
    const h = o.size * o.hFactor;
    const w = h * (img.naturalWidth / img.naturalHeight);
    ctx.drawImage(img, x, y - h * 0.72, w, h);
    return w;
  }

  function tokens(text) {
    return text.split(/(\$[^$]+\$)/g).filter(Boolean).map((s) => (
      s.startsWith("$") && s.endsWith("$") && s.length > 2
        ? { type: "tex", value: s.slice(1, -1) }
        : { type: "text", value: s }
    ));
  }

  function measure(ctx, text, size, color) {
    let w = 0;
    ctx.save();
    ctx.font = `${size}px "Microsoft YaHei","PingFang SC","Noto Sans SC",sans-serif`;
    for (const t of tokens(text)) {
      if (t.type === "tex") {
        const img = image(t.value, color);
        if (!img) { w += ctx.measureText(t.value).width; continue; }
        const h = size * 1.7;
        w += h * (img.naturalWidth / img.naturalHeight);
      } else {
        w += ctx.measureText(t.value).width;
      }
    }
    ctx.restore();
    return w;
  }

  function drawRich(ctx, text, x, y, opts) {
    const o = Object.assign({ size: 26, color: INK, maxW: 0, lineH: 0, align: "left" }, opts || {});
    const lineH = o.lineH || o.size * 1.45;
    const lines = String(text).split("\n");
    let cy = y;
    for (const line of lines) {
      let cx = x;
      const total = measure(ctx, line, o.size, o.color);
      if (o.align === "center") cx = x - total / 2;
      if (o.align === "right") cx = x - total;
      for (const t of tokens(line)) {
        if (t.type === "tex") {
          cx += drawInline(ctx, t.value, cx, cy, { size: o.size, color: o.color });
        } else {
          ctx.save();
          ctx.font = `${o.size}px "Microsoft YaHei","PingFang SC","Noto Sans SC",sans-serif`;
          ctx.fillStyle = o.color;
          ctx.textBaseline = "alphabetic";
          ctx.fillText(t.value, cx, cy);
          ctx.restore();
          cx += ctx.measureText(t.value).width;
        }
      }
      cy += lineH;
    }
  }

  window.RICH = {
    INK, GOLD, ready: () => readyPromise,
    drawTex, drawInline, drawRich, measure,
  };
})();
