---
name: video-flow
description: >-
  把任意内容（PDF / PPT / DOCX / Markdown / 网页 / 视频 / 一个主题）制作成“代码渲染”的可视化讲解视频：
  先做教学结构，再写分镜与旁白，然后用 Canvas/HTML 的 render(t) 画每一帧，headless Chrome 逐帧截图，
  FFmpeg 编码，可选 TTS 旁白、合成配乐、软字幕、质检报告。
  支持 16:9 / 9:16 / 1:1 / 4:5，内置 5 套视觉风格与 8 类通用镜头，也支持自定义镜头与品牌。
  当用户说“把这个 PDF/PPT/文章做成讲解视频”“做一个科普/产品/教程短片”“可视化教学”“代码做视频”
  “explainer video”“video as code”时使用。
  不用于：直接调用 Sora/Veo 等视频生成模型、剪辑已有实拍素材、或只写文案不做视频。
---

# video-flow：代码渲染的通用讲解视频工作流

> 一句话：**先想清楚“教会什么”，再把这件事变成一条可计算的时间轴，最后让浏览器逐帧画出来。**
> 成片 = Canvas/HTML 的 `render(t)` + headless Chrome 逐帧截图 + FFmpeg + 可选 TTS/配乐/字幕。

本 Skill 把“一条视频”拆成 8 个可检查的阶段。每个阶段都有产物和验收点；任何一步不合格，不要进入下一步。

---

## 0. 什么时候用 / 不用

**用**：
- 把一份 PDF / PPT / DOCX / 文章 / 网页 / 视频 / 一个主题，做成 1–5 分钟讲解视频；
- 需要“文字清晰、数据准确、可改一帧、可复现”的视频（代码渲染相对视频生成模型的结构性优势）；
- 要竖屏/方形/横屏多版本，或多语言版本；
- 需要旁白、字幕、配乐，且希望整套流程可重复。

**不用**：
- 需要真人/实拍/写实镜头 → 用视频生成模型或实拍，本 Skill 只负责“代码这一层”；
- 只是剪已有素材 → 用剪辑工具/Agent；
- 只想生成一段 MP4 却不愿意定分镜和文案 → 成片会像模板，建议先做第 1–2 步。

---

## 1. 硬规则（违反任何一条，返工）

1. **画面是时间的纯函数**：页面暴露 `window.render(t)`；给定 `t`，画面唯一确定。
   - 禁止 `Date.now()`、无种子随机、`requestAnimationFrame` 驱动的状态、CSS `transition/animation`、跨帧缓存。
   - 累积型动画（粒子/水面）用固定步长从 0 推到 `t`，或改解析公式。
2. **时间轴是唯一事实来源**：分镜、旁白、配乐、音效、字幕都从同一张 `timeline.json` 派生。
3. **先分镜后代码**：没有 `storyboard.md` 和 `script.json`，不要写场景代码。
4. **原文事实不编造**：数字、年份、人名、公式必须来自源材料；不确定的标 `[待核实]` 并在交付时单列。
5. **默认不带任何品牌/水印**：除非用户提供 logo/品牌名；默认页脚只写课程/主题信息。
6. **一次编码**：音频在 WAV 阶段完成混音与响度，最终只做一次 AAC 编码；不要反复转码。
7. **交付前必须过 QA**：抽帧、黑帧、响度、时长、字幕、音画同步，见第 8 步。

---

## 2. 输入与产物

### 输入（任选，可混合）
| 类型 | 处理方式 |
|---|---|
| PDF | `scripts/ingest.py` 抽文字；扫描件/乱码时自动栅格化为 PNG，让模型“看页” |
| PPTX | 逐页抽标题、正文、备注；可选把关键页导出为图片 |
| DOCX / Markdown / TXT | 直接抽取为 `source/source.md` |
| 网页 URL | 抓正文；保留来源链接 |
| 视频 | ffprobe 元数据 + 定点抽帧；无 ASR 时由人补充内容 |
| 纯主题 | 用户给的一句话/大纲；先让用户确认“必须出现的事实” |

### 每个项目的目录契约
```
<project>/
  project.json          # 元信息：标题/受众/目标/画幅/风格/声音/音乐/品牌
  source/               # 源材料（source.md、pages/*.png、meta.json）
  storyboard.md         # 分镜表：每镜讲什么、画面、时长、旁白、考点
  script.json           # 机器可读：scenes[]（type/文案/视觉/vo/时长）
  build/                # index.html + lib.js + theme.js + scenes.js + timeline.js
  audio/                # vo/*.wav、bgm、mix.wav
  frames/               # 逐帧 JPEG
  out/                  # final.mp4 / final.srt / poster.png
  qa/                   # report.md + contact sheets + 抽帧
```
用 `scripts/init_project.py` 一次生成骨架。

---

## 3. 工作流（8 步）

### 第 0 步：环境检查
```bash
python scripts/check_env.py
```
必须：Python 3.10+、FFmpeg/ffprobe、一个 Chromium 内核浏览器、`numpy/scipy`。
建议：`edge-tts`（在线神经语音）、`pypdf`、`python-pptx`、`python-docx`、`Pillow`。
要做 48 kHz / 商业配音感：CUDA 版 PyTorch + `voxcpm` + VoxCPM2 权重（可选，见 `references/local-tts.md`）。
缺什么按输出的提示装；装不了就降级（无旁白 / 系统语音 / 手写音频）。

### 第 1 步：读源材料，提炼“教学结构”
先回答 5 个问题（写进 `project.json` 的 `brief`）：
1. 受众是谁？他们**已经会什么**？
2. 看完后要能**说出/做出**什么？（1–3 条可检验目标）
3. 最容易误解/最难的 1 个点是什么？
4. 必须出现的事实/公式/数据有哪些？来源分别是什么？
5. 时长与画幅？平台（课堂/手机/社媒）？

**不要**直接按原文页序讲。用 `references/storytelling.md` 里的 4 种结构之一重组：
- 因果链（推荐给理科/工程）；
- 问题→解法→验证；
- 误区→纠正→迁移；
- 时间线/流程。

### 第 2 步：定风格与画幅
按 `references/styles.md` 选 1 套（silicon / paper / blueprint / neon / swiss），按 `references/formats.md` 定画幅。
规则：
- 内容偏“芯片/工程/数据”→ silicon / blueprint；
- 偏“人文/生物/历史”→ paper；
- 偏“发布/营销/年轻化”→ neon / swiss；
- 一屏只讲一件事；竖屏必须重排版，不要把横屏裁成竖屏。

### 第 3 步：写分镜与脚本
产出 `storyboard.md`（人看）和 `script.json`（机器用）。每个镜头必须写：
- `type`（title/concept/process/compare/formula/bars/quote/recap/custom）
- `kicker`（小标题）、`headline`（一句话结论）、`points`（≤3 条）
- `vo`（旁白，1–2 句；没有配音就留空）
- `visual`（图/表/流程/公式的具体数据）
- `duration`（可空，由旁白时长自动定）

写文案的 5 条硬约束：
1. 屏幕字 ≠ 旁白稿：屏幕只留关键词/结论，旁白负责解释。
2. 一屏最多 1 个结论 + 3 个支撑点；标题 ≤ 18 字，正文每行 ≤ 22 字。
3. 每 2–4 秒要有变化（元素/镜头/强调），但不要粒子爆炸。
4. 先写“禁用清单”：渐变背景+居中大字、所有元素淡入、满屏小字、无意义光晕。
5. 事实句单独标来源；不确定的加 `[待核实]`。

### 第 4 步：生成旁白与时间轴
```bash
# 默认：Edge 神经语音（24 kHz 源，快速草稿）
python scripts/tts.py --project . --voice zh-CN-XiaoxiaoNeural --rate +3%

# 要 48 kHz / “抖音级”质感：VoxCPM2 本地 + 参考音色克隆
python scripts/tts.py --project . --engine voxcpm \
  --model-dir models/VoxCPM2 \
  --ref-audio audio/voice_ref.wav \
  --atempo 0.95

python scripts/timeline.py --project .
```
- `tts.py` 输出 `audio/vo/<id>.wav`（48 kHz），自动做轻 EQ/压缩；支持 `--from-dir` 用真人录音、`--engine voxcpm` 用本地 48 kHz 模型。
- VoxCPM2 需要单独装 CUDA 版 PyTorch 与 4.7 GB 权重；完整步骤、参考音色、OOM 处理见 `references/local-tts.md`。
- **专有名词口播规则**：屏幕保留 `ALU/CF/OF` 缩写，旁白写“算术逻辑单元/进位标志/溢出标志”；不要写 `A L U`（字母间会有停顿）；`74181` 写成“七四一八一”。
- `timeline.py` 用实测旁白时长生成 `build/timeline.js` 与 `timeline.json`：
  `scene.duration = head + voDuration + tail`，没有旁白的镜头用显式 `duration`。
- 之后**只改 script.json 再重跑这两步**，不要手改 timeline。

### 第 5 步：搭页面与实现镜头
用模板：
```bash
python scripts/init_project.py --dir my-video --title "..." --format 16:9 --style silicon
# 编辑 build/content 由 timeline.py 生成；通用镜头已实现，直接改 script.json
```
- 通用镜头（8 类）在 `build/scenes.js`，读 `CONTENT` 渲染；大多数讲解片足够。
- 需要专业图（芯片/电路/解剖/地图/分子）时，写 `build/custom.js`：
  ```js
  window.CUSTOM['s3'] = function(u, D, sc, ctx){ /* 用 lib.js 的 helpers 画 */ };
  ```
  在 `script.json` 里把该镜 `type` 设为 `custom`。
- 每次只做一个镜头：先渲 3 张静帧（`scripts/render.py --still 1.2,2.4,3.6`），检查文字溢出/重叠/主体大小，再继续。

### 第 6 步：渲染
```bash
python scripts/render.py --project . --fps 30
# 只渲某段：--start 8 --duration 4
# 复用已有 Chrome：--cdp http://127.0.0.1:9333
# 让脚本自己起 Chrome：--launch-chrome
```
输出 `frames/f00000.jpg...`，可断点续渲（已存在且 >2KB 的帧跳过）。
> 无头 Chrome 与 sandbox：如果运行环境禁止 Chrome 的 IPC/管道，需在允许的环境运行，或用 `--cdp` 连接一个已启动的 Chrome。

### 第 7 步：配乐、音效、混音、字幕
```bash
python scripts/audio.py --project .            # 合成 BGM + 放旁白 + duck + 母带
python scripts/srt.py --project .              # 生成 out/final.srt
```
- 没有旁白：`audio.py --no-bgm` 或只用用户提供的音乐。
- 用户提供音乐：放到 `audio/music.*`，`audio.py` 会自动循环/裁切并 duck。
- 目标响度默认 −14.2 LUFS、真峰值 ≤ −1.5 dBFS；音频只编码一次。

### 第 8 步：编码 + QA + 交付
```bash
python scripts/encode.py --project .           # frames+mix+srt → out/final.mp4
python scripts/qa.py --project .               # qa/report.md + 抽帧拼图
```
QA 必须全部通过（见 `references/qa.md`）：
- 时长/画幅/帧率/音轨/字幕流正确；
- 无 ≥0.25 s 黑帧；抽帧无空白、无叠字、无溢出；
- 响度在目标 ±1 LU，真峰值 ≤ −1.5 dBFS；
- 首帧不是纯黑；最后一个镜头有收束；
- 事实清单与源材料一致；`[待核实]` 已单列。

交付：`out/final.mp4`、`out/final.srt`、`poster.png`、`storyboard.md`、`script.json`、`qa/report.md`、渲染用时与已知不足。

---

## 4. 通用镜头类型（模板已实现）

| type | 用途 | 关键字段 |
|---|---|---|
| `title` | 开场/章节 | `title/subtitle/kicker` |
| `concept` | 一个概念 + 3 个要点 | `headline/points/visual` |
| `process` | 流程/步骤（3–5 步） | `steps[]` |
| `compare` | 两方对比 | `left/right` |
| `formula` | 公式 + 解释 | `formula/notes[]` |
| `bars` | 数据对比 | `items[{label,value}]` |
| `quote` | 金句/结论 | `quote/author` |
| `recap` | 总结地图 | `nodes[]/takeaway` |
| `custom` | 专业图 | 自己写 `custom.js` |

需要新类型时：在 `scenes.js` 里加一个 `window.SCENES_IMPL['type']`，并在 `references/pipeline.md` 记录数据契约。

---

## 5. 画幅与安全区

| 画幅 | 尺寸 | 安全区 | 标题字号 | 正文字号 |
|---|---|---|---|---|
| 16:9 | 1920×1080 | 左右 96 / 上下 64 | 72–120 | 28–40 |
| 9:16 | 1080×1920 | 左右 64 / 上下 160 | 64–96 | 32–44 |
| 1:1 | 1080×1080 | 四周 72 | 56–88 | 28–40 |
| 4:5 | 1080×1350 | 四周 80 | 60–92 | 30–42 |

竖屏要重排：标题在上、图在中、结论在下；不要横向压缩。模板用 `layout()` 根据画幅切换，参考 `references/formats.md`。

---

## 6. 常见失败 → 修法

| 现象 | 根因 | 修法 |
|---|---|---|
| 黑屏/白屏 | JS 报错、`render` 未定义、canvas 尺寸 0 | `render.py --still`，看控制台；显式给 canvas 宽高 |
| 字体不对/首帧回退字体 | 字体未加载 | 等 `document.fonts.ready` 再置 `READY=true`；CJK 用系统兜底串 |
| 同一 t 两次不一样 / 并行闪 | 用了 rAF/计时器/随机/跨帧状态 | 改纯函数；`hash(seed)`；闭式弹簧 |
| 文字重叠/溢出 | 没有逐镜静帧检查 | 每镜 3 张静帧 + 竖屏 360px 宽抽帧 |
| 音画不同步 | 音频从 0 开始 vs 视频从 start；TTS 逐句拼 | 同一 timeline；整段 TTS；`-ss` 放 `-i` 前 |
| 响度忽大忽小 | 多次 loudnorm/转码 | 只在 WAV 阶段静态增益；一次 AAC |
| 渲染太慢 | 4K/子帧/笔刷/WebGL | 先 960×540 小样；子帧只给快动作；并行 worker |
| Chrome 起不来 | sandbox 限制 IPC/管道 | 在允许环境运行，或 `--cdp` 连已启动 Chrome |

---

## 7. 扩展点

- **新风格**：复制 `templates/styles/*.json`，改色板/字体/背景类型；在 `styles.md` 补一格。
- **新镜头**：`build/scenes.js` 注册；或 `build/custom.js` 写专业图。
- **真人配音**：把录音按 `<scene-id>.wav` 放进 `audio/vo_human/`，`tts.py --from-dir` 只做重采样/轻处理。
- **本地 48 kHz TTS**：`tts.py --engine voxcpm` + 参考音色克隆；安装/调参/排错见 `references/local-tts.md`。
- **多语言**：一个 `script.<lang>.json` + 对应 TTS 声线；时间轴可复用同一套画面（注意文本长度差异）。
- **多画幅**：同一 `script.json` 用不同 `project.format` 重新 init/render；布局由 `layout()` 适配。
- **品牌**：`project.json.brand` 提供 logo 文字/颜色/页脚；默认关闭。

---

## 8. 参考文档

- `references/pipeline.md`：完整技术管线、`render(t)` 契约、CDP 渲染、FFmpeg 参数、时间轴数据模型。
- `references/inputs.md`：PDF/PPT/DOCX/URL/视频的抽取与 OCR 兜底。
- `references/storytelling.md`：4 种教学结构、节奏表、文案规则。
- `references/styles.md`：5 套风格的色板/字体/动效/适用题材。
- `references/formats.md`：画幅、安全区、竖屏重排规则。
- `references/audio.md`：TTS 选项、真人录音、配乐合成、ducking、响度、单次编码。
- `references/local-tts.md`：VoxCPM2 本地 48 kHz 安装、参考音色克隆、中文技术名词改写、OOM/下载排错。
- `references/qa.md`：验收清单与自动检查命令。
