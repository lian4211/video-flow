# 手机竖屏版（9:16）：大字、硬字幕与阶段进度条

> 竖屏不是把横屏裁一刀。它的核心是 **重排信息层级**：一屏只讲一件事，字号大，底部留给字幕和进度。
> 本文记录一套已交付 36 分钟手机版的实战参数，可直接复用。

---

## 1. 规格基线

| 项 | 值 |
|---|---|
| 画布 | 1080×1920，30fps |
| 左右安全边 | 54 px（`APAD=54`） |
| 顶部 | 标题从 y≈120 开始；顶部 HUD 40–80 |
| 底部字幕区 | y≈1560–1730 |
| 阶段进度条 | y≈1738–1888（10 段 + 当前章内进度） |
| 正文 | 30–36 px；手机观看仍偏大，不要低于 28 |
| 标题 | 52–64 px；长标题自动缩到 44 |
| 步骤 | 26–30 px；步骤多时行高压缩，但字不能小于 24 |
| 公式展示 | 30–36 px 基准，长公式按 `maxW` 等比缩 |

> 关键：**先按 1080×1920 设计，不要从 1920×1080 等比缩**。缩放会把 30 px 字变成 17 px，手机上不可读。

---

## 2. 版式重排

### 2.1 开场（open）

- 标题在上：两行大字（如“30 秒，还是 30 分钟？”），字号 56–72；
- 副标题一行，30 px，灰色；
- 两张纵向大卡：
  - 卡 1：y=620，h=340；
  - 卡 2：y=990，h=390；
  - 卡内主数字 84–96 px，说明 30–34 px；
- 结论句 y≈1470，字号 34，强调色。

### 2.2 技能卡（card）

- 左侧只有卡号（大水印数字）和标题；
- 右侧公式卡：宽 `CW`，高 230；
- 下方 signals 两列，每个高 64–72；
- 底部例题卡：高 410，题面 + 答案；
- 所有卡间距 ≥ 20 px。

### 2.3 例题/过程精讲（example）

- 题面卡高 180–220；
- 步骤区从题面下 24 px 开始；
- 步骤行高：`rowH = min(84, 500 / n)`，n 为步骤数；
- 5 步以内用 74–84；6–7 步用 56–64；
- 右侧 NOTE 卡动态下移：`noteY = min(1100, max(stepsBottom + 24, 820))`；
- VERIFY 小卡在 `noteY + 206`；
- 答案卡：`answerY = max(1250, min(1410, noteY + 230))`；
- 如果步骤超过 7 条：拆成两屏，或只保留关键节点，不要压到 16 px。

### 2.4 总结（recap）

- 中心圆/图在上半屏；
- 左右两栏分别放“工具”和“性质”；
- 结论句在 y≈1500，字号 36–42。

---

## 3. 底部三件套：字幕、进度、时间

### 3.1 字幕

硬字幕（burn-in）比软字幕更适合手机：平台转码/网页播放器不会把它关掉，也不会遮住画面。

流程：

```bash
python scripts/srt.py --project .              # 先生成 out/final.srt
python scripts/make_ass.py --project . \
  --srt out/final.srt --out out/final.ass \
  --width 1080 --height 1920 \
  --font-size 42 --margin-v 250
python scripts/encode.py --project . --ass out/final.ass
```

参数经验：

- 字号 42–46 px（微软雅黑/思源黑体）；
- 白色字 + 深色描边（`Outline=2.2`，`Shadow=1.2`）；
- 底部 MarginV 60–80，落在字幕安全区，不压答案卡；
- 每条最多 2 行；中文按可视宽度换行（中文 1.0、拉丁 0.55、空格 0.35）；
- 不要跨镜头；SRT 的 `voStart/voDur` 已经按场景切好。

### 3.2 阶段进度条

10 段对应 10 章，不是“全片进度百分比”：

```js
// 每段底槽 + 当前章高亮 + 章内进度
const sw = (AW - APAD*2 - 9*10) / 10;
for (let i=0;i<10;i++){
  const x = APAD + i*(sw+10);
  const on = i === chapter;
  ctx.fillStyle = on ? AC.accent : "rgba(120,150,180,.18)";
  ctx.fillRect(x, 1738, sw, 8);
  if (on) {
    const frac = Math.min(1, (t - chStart) / (chEnd - chStart));
    ctx.fillStyle = AC.accent;
    ctx.fillRect(x, 1738, sw*frac, 8);
  }
  LIB.txt(String(i+1).padStart(2,"0"), x, 1762, {size: 18, color: on ? AC.accent : AC.muted});
}
LIB.txt(fmtTime(t), APAD, 1880, {size: 16, color: AC.muted});
LIB.txt("TOTAL " + fmtTime(total), AW-APAD, 1880, {size: 16, align:"right"});
```

关键：`chapter` 从 `CONTENT.scenes` 里按当前 `scene.id` 查，不要假设 `SCENES` 项自带 `chapter`（常见 `NaN / 10` 来源）。

### 3.3 进度条与字幕不打架

- 字幕底边 ≤ 进度条顶边 − 16 px；
- 进度条高 8 px，章标签在条下 18 px；
- 时间码在最底部，字号 16；
- 如果字幕两行，先缩字号或拆句，不要往上压内容。

---

## 4. 从横屏改竖屏的路线

不要直接给横屏 app 加 `if (portrait)` 就完事；复杂讲解片建议 **复制一份工程，写竖屏布局**：

```bash
cp -r my-video my-video-mobile
# 修改 project.json：format=9:16, width=1080, height=1920
# 修改 build/format.js：{"name":"9:16","w":1080,"h":1920,"portrait":true}
# 保留：script.json、timeline.json、audio/、out/final.srt
# 重写：build/app.js 的 header + 各场景布局
```

可复用的部分：

- `lib.js` 的绘制 helpers、字体、颜色；
- `script.json`、`timeline.json`、旁白、`mix.wav`；
- MathJax SVG 资产（`math_svgs.js`）；
- `rich.js` 的 `drawTex/drawRich`（如果有）。

必须重写的部分：

- header/chrome 的坐标；
- 每个场景的卡片位置、字号、换行；
- 底部字幕安全区 + 阶段进度条；
- 竖屏的 `APAD`、`CW`、标题最大宽度。

---

## 5. 从竖屏回到横屏

如果用户先要竖屏、后要横屏：**复用竖屏的配音/时间轴/字幕，重写 16:9 布局**，不要让横屏从旧 16:9 音轨重新生成。

```text
video_mobile/  (1080×1920, 36:55)
  script.json / timeline.json / audio/mix.wav / out/final.srt / math_svgs.js
        ↓ 复制
video_landscape/ (1920×1080)
  build/app.js 换回横屏；chrome 加阶段条
  make_ass.py --width 1920 --height 1080 --font-size 42 --margin-v 64
```

注意：

- 时间轴不变，所以帧数 = `round(total*fps)` 不变；
- 字幕的 ASS `PlayRes` 必须跟画布一致，否则字号/边距全错；
- 横屏底部空间更紧，答案卡下沿和字幕之间要留 20 px；
- 阶段条放 y=1030 左右，标签在 1056，时间码 1070。

---

## 6. 验收清单

- [ ] 1080×1920 原生渲染，不是缩放；
- [ ] 正文字号 ≥ 28 px，步骤 ≥ 24 px；
- [ ] 字幕在安全区，最多 2 行，不压答案/进度条；
- [ ] 10 段阶段条正确高亮，无 `NaN`；
- [ ] 长公式没有超出卡片；
- [ ] 竖屏抽 3 帧：开场/技能卡/7 步例题；
- [ ] 手机实际播放一遍，确认字能看清。

参考实现：一个 36:55、59 场景的 `video_mobile` 工程；工程结构与横竖屏互转步骤见第 4、5 节。
