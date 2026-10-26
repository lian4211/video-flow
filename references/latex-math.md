# LaTeX 数学排版：从 Unicode 到 MathJax SVG

> 适用：讲义/竞赛/工程类视频，公式多、上下标多、要求手机上也清楚。
> 结论：**构建期用 MathJax 把 TeX 渲染成透明 SVG data URI，Canvas 直接 `drawImage`**。不要在 Canvas 里手写上下标解析器。

---

## 1. 为什么不用 Unicode / 手写 parser

常见做法是把 `e^(x+1/x)`、`x²`、`1/2` 用 Unicode 字符和 `fillText` 拼出来。问题：

- `^` 后只取一个字符 → `e^(x+1/x)` 只把 `(` 当上标，后面的 `x+1/x)` 掉回基线，整体错位；
- Unicode 上标字符（`²³ⁿ`）字体覆盖不全，和中文混排时基线/字重不一致；
- 分式、根号、积分号、极限、矩阵无法可靠手绘；
- 同一公式在横屏/竖屏/不同字号下要重复调坐标。

真 LaTeX 的收益：公式结构由 MathJax 排版，Canvas 只负责按目标宽高缩放，不再关心上下标。

---

## 2. 数据契约

在 `script.json` 里给公式字段加 `_tex` 版本：

```json
{
  "id": "s04_05",
  "type": "example",
  "title": "例4 精讲：换元后两次分部",
  "problem": "I = ∫ x arctan x ln(1+x²) dx",
  "problem_tex": "I=\\int x\\arctan x\\,\\ln(1+x^2)\\,dx",
  "answer": "…",
  "answer_tex": "\\frac12\\left[(x^2+1)\\ln(1+x^2)-x^2-3\\right]\\arctan x-\\frac12x\\ln(1+x^2)+\\frac{3x}{2}+C",
  "steps": [
    "换元：$t=\\arctan x,\\ x=\\tan t,\\ dx=\\sec^2 t\\,dt$",
    "合并：$e^{x+1/x}(1+x-1/x)$"
  ]
}
```

规则：

1. **展示公式**（题面/答案/公式卡）用 `formula_tex`、`problem_tex`、`answer_tex`；渲染时优先用 `_tex`，没有才回退纯文本。
2. **行内公式**在普通字符串里用 `$...$` 包裹；中文留在 `$` 外。
3. `steps`/`bullets`/`signals` 里的数学都要包成 `$...$`，不要只包一半。
4. `vo`（旁白）不加 `$`，TTS 不读 TeX。
5. 旧字段保留（`problem`/`answer`/`formula`），用于没有 MathJax 时的兜底和无障碍文本。

### 2.1 行内公式的写法

- 行内分式用 `1/x`、`(1+x)/x`，不要用 `\frac{}{}`：分式会把行高撑开，和中文基线错位。
- 展示公式才用 `\frac{}{}`、`\int`、`\sum`。
- 中文和公式之间留一个空格或 `\,`：
  - ✅ `观察：指数是 $x+1/x$`
  - ❌ `观察：指数是$x+1/x$`（贴太紧）
- 避免把中文标点包进 `$...$`：
  - ✅ `$t \to \sin x$，再看定义域`
  - ❌ `$t \to \sin x，$`
- 单独的 `=`、`+C` 可以写成 `$=$`、`$+C$`；但更推荐把整个表达式包起来。

---

## 3. 构建 MathJax SVG

### 3.1 安装

```bash
cd <project>
npm init -y
npm install mathjax-full@3
```

`mathjax-full` 只用于构建，不进最终页面；`node_modules/` 加进 `.gitignore`。

### 3.2 生成

技能自带：

```bash
node scripts/build_math_svgs.js --project .
```

默认输出：

- `build/math_svgs.js`：`window.MATH_SVG = { "<tex>|<color>": "data:image/svg+xml;base64,..." }`
- `build/math_tex.json`：去重后的 TeX 清单，便于检查

常用参数：

```bash
node scripts/build_math_svgs.js --project . \
  --script script.json \
  --colors "#E8F1FA,#FFD166" \
  --out build/math_svgs.js
```

颜色为什么要有多个变体：Canvas `drawImage` 不会应用 CSS `currentColor`，所以构建期就要把 `currentColor` 替换成目标色，正文色/强调色各一份。

### 3.3 页面加载顺序

```html
<script src="math_svgs.js"></script>
<script src="lib.js"></script>
<script src="app.js"></script>
```

`app.js` 必须等图片解码完成再 `READY`：

```js
window.MATH_READY = Promise.all(
  Object.entries(window.MATH_SVG || {}).map(([k, uri]) => new Promise((res) => {
    const img = new Image();
    img.onload = img.onerror = () => { window.__mathImages[k] = img; res(); };
    img.src = uri;
  }))
).then(() => true);

Promise.all([document.fonts.ready, window.MATH_READY]).then(() => { window.READY = true; });
```

---

## 4. Canvas 绘制

### 4.1 展示公式

```js
function drawTex(ctx, tex, x, y, maxW, size, color, align = "left") {
  const key = tex + "|" + color;
  const img = window.__mathImages[key];
  if (!img || !img.naturalWidth) return 0;
  const h = size * 1.55;                 // 展示公式高度
  let w = h * (img.naturalWidth / img.naturalHeight);
  if (maxW && w > maxW) { w = maxW; }    // 超宽时等比缩小
  const hh = w * (img.naturalHeight / img.naturalWidth);
  let dx = x;
  if (align === "center") dx = x - w / 2;
  if (align === "right") dx = x - w;
  ctx.drawImage(img, dx, y, w, hh);
  return w;
}
```

### 4.2 行内公式

行内图要按 **字号倍数** 放大，不能直接用正文字号：

```js
function drawInlineTex(ctx, tex, x, y, size, color) {
  const key = tex + "|" + color;
  const img = window.__mathImages[key];
  if (!img || !img.naturalWidth) return 0;
  const h = size * 1.7;                  // 关键：1.5–1.8，太小看不清，太大压行
  const w = h * (img.naturalWidth / img.naturalHeight);
  ctx.drawImage(img, x, y - h * 0.72, w, h);
  return w;
}
```

基线经验：`top = baselineY - h*0.72`；不同字体/字号可微调 0.68–0.76。

### 4.3 混合文本行

按 `$...$` 拆 token：普通文本 `fillText`，公式 `drawInlineTex`，逐段前进：

```js
function richTokens(text) {
  return text.split(/(\$[^$]+\$)/g).filter(Boolean).map(s =>
    s.startsWith("$") ? { type: "tex", value: s.slice(1, -1) } : { type: "text", value: s }
  );
}
```

不要用正则一次性测量整行宽度；逐 token 累加 `measureText`/`inlineTexW`，超宽时换行。超过 2 行就拆场景或缩短文案。

---

## 5. 常见坑

| 现象 | 根因 | 修 |
|---|---|---|
| 上标只包住一个括号 | 手写 parser 的 `^` 只取一个字符 | 用 MathJax；若保留 parser，`^(` 要匹配到对应 `)` |
| 行内公式太小/悬浮 | 高度系数 1.25 偏小 | 改 1.6–1.8；基线 `y - h*0.72` |
| 公式颜色不对 | SVG 里是 `currentColor` | 构建期替换成具体色，按颜色生成多份 |
| 公式显示为空白 | `math_svgs.js` 未加载/图片未解码 | 先加载 `math_svgs.js`；等 `MATH_READY` |
| 改了 script 但公式没变 | `content.js`/`math_svgs.js` 没重建 | 先 `build_math_svgs.js`，再 `timeline.py` 重建 `content.js` |
| 中文和公式贴太紧 | 没有排版空格 | 文本里留空格；或 `drawInlineTex` 前后加 4–6 px |
| 长公式超出卡片 | 只按字号不按宽度 | `drawTex` 传 `maxW`，超宽等比缩 |
| 分式把行高撑开 | 行内用了 `\frac` | 行内改 `1/x`；展示公式才用 `\frac` |

---

## 6. 验收

```bash
# 1) 生成资产
node scripts/build_math_svgs.js --project .

# 2) 重建 content/timeline
python scripts/timeline.py --project .

# 3) 抽关键帧：题面、步骤中段、答案
python scripts/render.py --project . --still 18,28,47,52 --launch-chrome
```

逐张检查：

- [ ] 题面公式完整，没有半截上标；
- [ ] 中文与公式基线一致，不贴边、不悬空；
- [ ] 长答案没有超出卡片；
- [ ] 手机 1080×1920 上仍可读；
- [ ] 所有 `_tex` 字段都能在 `build/math_tex.json` 中找到。

完整实现参考 `templates/build/rich.js`（可选 helper）和 `references/mobile-video.md`。
