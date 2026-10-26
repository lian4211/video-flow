# Pipeline：从 script.json 到 MP4

本文是实现层的“接口文档”。所有脚本都遵循这里的字段约定。

---

## 1. 数据模型

### project.json
```json
{
  "title": "天空为什么是蓝的",
  "subtitle": "瑞利散射",
  "language": "zh",
  "format": "9:16",
  "fps": 30,
  "style": "paper",
  "voice": { "engine": "edge", "name": "zh-CN-XiaoxiaoNeural", "rate": "+3%", "pitch": "+0Hz" },
  "music": "ambient",
  "target_lufs": -14.2,
  "brand": { "enabled": false, "name": "", "footer": "" },
  "brief": {
    "audience": "高中/大一学生",
    "goals": ["能用 1/λ⁴ 解释蓝光为什么更易被散射"],
    "misconception": "以为天空的蓝色是海面反射",
    "facts_source": ["source/source.md#p3"]
  }
}
```

**本地 48 kHz 旁白**（可选，不改变 timeline 契约）：

```json
"voice": {
  "engine": "voxcpm",
  "model_dir": "models/VoxCPM2",
  "ref_audio": "audio/voice_ref.wav",
  "ref_text": "参考音频的逐字文本",
  "control": "",
  "atempo": 0.91,
  "device": "cuda"
}
```

`tts.py` 读取 `voice.engine` 决定引擎；`voxcpm` 路径输出同样是 `audio/vo/<id>.wav`（48 kHz 单声道），后续步骤不变。**`ref_text` 必须给**：只给 `ref_audio` 会退化为弱克隆，段间 f0 漂移；`ref_text` 为空时脚本会尝试 `audio/voice_ref.txt`，再没有就警告。安装/参考音色/排错见 `references/local-tts.md`。

### script.json
```json
{
  "scenes": [
    {
      "id": "s0", "type": "title",
      "kicker": "光与大气 · 01",
      "title": "天空为什么是蓝的？",
      "subtitle": "不是海的颜色，是光的散射",
      "vo": "抬头看天，你有没有想过，天空为什么是蓝的？"
    },
    {
      "id": "s1", "type": "process",
      "kicker": "01 / 三步",
      "headline": "阳光进入大气后，发生了什么",
      "steps": [
        { "title": "白光包含所有颜色", "detail": "波长 400–700 nm" },
        { "title": "遇到空气分子", "detail": "分子比波长还小" },
        { "title": "短波被散射得更强", "detail": "强度 ∝ 1/λ⁴" }
      ],
      "vo": "太阳光看起来是白的，其实混着所有颜色。进入大气后，它会撞上比波长还小的空气分子。波长越短，被散射得越厉害。",
      "visual": { "kind": "steps" }
    },
    {
      "id": "s2", "type": "formula",
      "kicker": "02 / 一条公式",
      "headline": "瑞利散射",
      "formula": "I ∝ 1 / λ⁴",
      "notes": ["λ 是波长", "蓝光 450 nm，红光 650 nm", "散射强度相差约 4.4 倍"],
      "vo": "瑞利散射的强度，和波长的四次方成反比。"
    },
    {
      "id": "s3", "type": "recap",
      "kicker": "03 / 带走",
      "headline": "抬头看到的蓝，是被散射的蓝",
      "nodes": ["白光", "空气分子", "短波散射", "天空呈蓝"],
      "takeaway": "波长越短，散射越强",
      "vo": "所以，天空的蓝，是蓝光被空气分子散射后，进入你眼睛的结果。"
    }
  ]
}
```

- `duration`：可省略；省略时由 `tts.py` 实测旁白长度 + `head/tail` 计算。
- `visual`：给通用镜头的可选参数（`kind`、`items`、`left/right`…）。
- `type: "custom"`：由 `build/custom.js` 中同 id 的函数实现。

---

## 2. 时间轴生成

`scripts/timeline.py`：
1. 读 `script.json` 与 `project.json`；
2. 读 `audio/vo/<id>.wav` 的实际时长（无旁白则用 `duration`）；
3. `start` 累加，`dur = head + vo + tail`（默认 head 0.5、tail 0.9；title 可 0.8/1.4）；
4. 写 `build/timeline.js`：
```js
window.SCENES = [
  {id:'s0', type:'title', start:0.0, dur:12.6, voStart:0.8},
  ...
];
window.TOTAL = 42.3;
```
5. 写 `timeline.json` 供音频/字幕/QA 使用。

**不要手改 timeline**。改 `script.json` 后重跑 `tts.py` 与 `timeline.py`。

---

## 3. 页面契约

`build/index.html` 必须：
- 有一个固定尺寸的 `<canvas id="c">`（尺寸来自 project.format）；
- 暴露 `window.render(t)`：画出 `t` 秒；
- 暴露 `window.READY`：字体/资源就绪后置 `true`；
- 从 `timeline.js` 读取 `SCENES` 与 `TOTAL`；
- 按 `SCENES[i].type` 分派到 `window.SCENES_IMPL[type]`，再回落到 `window.CUSTOM[id]`。

推荐骨架：
```js
function render(t){
  drawBackground(t);
  for (const sc of SCENES){
    if (t >= sc.start && t < sc.start + sc.dur){
      const u = t - sc.start;
      ctx.save(); ctx.globalAlpha = sceneAlpha(t, sc);
      const fn = window.CUSTOM[sc.id] || window.SCENES_IMPL[sc.type] || SCENES_IMPL.concept;
      fn(u, sc.dur, sc, ctx);
      ctx.restore();
    }
  }
  drawCut(t);
  drawHUD(t);
}
```

### 3.1 公式（可选）：MathJax SVG

公式多时，不要手写上下标 parser：

```bash
npm install mathjax-full@3
node scripts/build_math_svgs.js --project .
```

- `script.json` 的展示字段加 `*_tex`，行内公式用 `$...$`；
- 构建期生成 `build/math_svgs.js`，页面直接 `drawImage`；
- `content.js` 要重跑 `timeline.py` 才会带上新字段；
- 完整契约/坑见 `references/latex-math.md`。

**三条禁令**（再强调一次）：不读系统时间、不用无种子随机、不在帧之间保存状态。需要随机用 `hash(seed)`，需要弹簧用闭式解：

```js
function spring(x, w=16, z=0.72){
  if (x <= 0) return 0;
  const wd = w*Math.sqrt(1-z*z);
  return 1 - Math.exp(-z*w*x)*(Math.cos(wd*x) + z*w/wd*Math.sin(wd*x));
}
```

---

## 4. 渲染器

`scripts/render.py` 通过 **CDP**（Chrome DevTools Protocol）逐帧截图：

1. 连接 Chrome（`--cdp`）或启动一个 headless 实例（`--launch-chrome`）；
2. `Emulation.setDeviceMetricsOverride(width, height, deviceScaleFactor=1)`；
3. 打开页面，等待 `typeof window.render === 'function'` 且 `window.READY !== false`，再等 `document.fonts.ready`；
4. 对 `i in [start*fps, end*fps)`：
   - `Runtime.evaluate("render(t)")`
   - `Runtime.evaluate("canvas.toDataURL('image/jpeg', q)")`
   - 解码写 `frames/f{i:05d}.jpg`；已存在且 >2KB 则跳过（可续渲）。
5. 进度每 300 帧打印一次。

为什么不用录屏：录屏会掉帧、帧率不稳，且受机器影响；逐帧 seek 保证恒定帧率与可复现。

性能参考：1080p Canvas 场景约 10–20 fps 渲染速度（受绘制复杂度/Chrome 状态影响）；30 秒 ≈ 900 帧 ≈ 1–2 分钟。

可选运动模糊：`--motion-blur 4` 在 1/4 帧间隔采样 4 次并在内存平均；只对快速运动镜头使用，成本 ×4。

长片并行：

```bash
python scripts/render_parallel.py --project . --chunks 4 --launch-chrome
```

按 `timeline.total` 切成 4 段，每段独立 Chrome，日志 `qa/render_part*.log`；1080p 单进程约 9–15 fps，4 进程约 3–4 倍吞吐。详见 `references/parallel-render.md`。

---

## 5. 编码

`scripts/encode.py` 只做一次编码：

```bash
ffmpeg -y -framerate 30 -i frames/f%05d.jpg -i audio/mix.wav \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 256k -ar 48000 \
  -movflags +faststart -shortest out/final.mp4
```

要软字幕：
```bash
ffmpeg -y -i out/final.mp4 -i out/final.srt \
  -map 0 -map 1 -c copy -c:s mov_text -metadata:s:s:0 language=zho \
  -movflags +faststart out/final_subbed.mp4
```

要硬字幕（手机平台/网页播放器不会关掉）：
```bash
python scripts/make_ass.py --project . --srt out/final.srt --out out/final.ass \
  --width 1920 --height 1080 --font-size 42 --margin-v 64
python scripts/encode.py --project . --ass out/final.ass
```

ASS 的 `PlayResX/Y` 必须等于画布；否则字号/边距按错误比例缩放。Windows 下 `encode.py` 用项目内相对路径喂 `-vf ass=...`，避免盘符冒号转义。

参数经验：
- `crf 18`（文字/线条多，别用 23）；
- `-pix_fmt yuv420p`（兼容性）；
- `-preset slow` 值得；
- 音频 256k、48 kHz，避免二次转码；
- `-shortest` 防止音轨比画面长。

---

## 6. 字体

- 中文兜底：`"PingFang SC","Microsoft YaHei","Noto Sans CJK SC","Noto Sans SC",sans-serif`；
- 要跨机器一致：把字体文件放进 `assets/fonts/`，用 `@font-face` 或 `FontFace` 加载，等 `document.fonts.ready`；
- Canvas 文字在缩放容器里容易糊：不要给会缩放的文字元素加 `will-change`，文字画在不受 transform 的层，或按目标分辨率重绘；
- 竖屏中文正文 ≥ 32 px，横屏 ≥ 28 px。

---

## 7. 数据契约（供自定义镜头）

`SCENES_IMPL[type](u, D, sc, ctx)`：
- `u`：场景内秒数（0..D）
- `D`：场景总时长
- `sc`：该镜对象（含 `headline/points/...`）
- `ctx`：2D context（模板已 setTransform 到 1920×1080 或当前画幅）

可用 helpers（`build/lib.js`）：`txt/panel/line/arrow/poly/dot/ring/bar/bitBox`、`ease/seg/smooth`、`drawBackground/drawCut`、`layout()`。

新增字段时，先写进 `script.json`，再在场景函数里读；不要散落魔法常量。
