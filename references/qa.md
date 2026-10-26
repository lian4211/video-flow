# QA：交付前必须通过的检查

## 1. 自动检查（`scripts/qa.py`）

```bash
python scripts/qa.py --project .
```

会输出 `qa/report.md` 与：
- `qa/contact.png`：每 10% 时长抽 1 帧，拼图；
- `qa/frames/`：6–10 张关键帧；
- 探测结果：时长、分辨率、帧率、音轨、字幕流、黑帧、响度、真峰值、平均码率。

## 2. 人工检查（必须做）

逐项打勾，不合格就回第 5/7 步：

- [ ] **开场 2 秒**有信息（不是黑屏/logo/“大家好”）
- [ ] 每屏只有 **1 个中心思想**；标题 ≤ 18 字
- [ ] 文字无溢出、无重叠、无被裁切；竖屏 360 px 宽仍可读
- [ ] 同一角色/元素跨镜头一致（颜色、字体、比例）
- [ ] 每 2–4 秒有变化；没有“空拍”超过 4 秒
- [ ] 数字/公式/年份与源材料一致；`[待核实]` 已单列
- [ ] 音画同步：旁白说到某个概念时，画面已出现（允许 ±0.3 s）
- [ ] 首帧不是纯黑；最后一镜有收束（结论/行动）
- [ ] 没有品牌/水印（除非用户要求）
- [ ] 字幕断句自然，不跨镜头、不超过 2 行
- [ ] **硬字幕**：抽 3 帧确认在安全区，不压答案卡/阶段条，左右不超界
- [ ] **阶段进度条**：10 段都在、当前章高亮、无 `NaN`、章节与实际内容一致
- [ ] **公式**：行内公式与中文基线齐平；上标完整（`e^{x+1/x}` 不是 `e^(x+1/x)`）
- [ ] **帧数**：`frames` 数量 = `round(timeline.total*fps)`，首尾帧都存在

## 2.1 音色一致性

```bash
# 抽查 5 段，median f0 差 >20 Hz 视为换人
python - <<'PY'
import numpy as np, soundfile as sf, glob
for p in sorted(glob.glob("audio/vo/*.wav"))[:5]:
    x, sr = sf.read(p); x = x[:,0] if x.ndim>1 else x
    x = x - x.mean()
    ac = np.correlate(x, x, "full")[len(x)-1:]
    lo, hi = sr//400, sr//70
    print(p, round(sr/(lo+np.argmax(ac[lo:hi])),1), "Hz")
PY
```

## 3. 自动命令

```bash
# 黑帧（>=0.25s）
ffmpeg -hide_banner -i out/final.mp4 -vf "blackdetect=d=0.25:pix_th=0.04" -an -f null NUL

# 响度/真峰值
ffmpeg -hide_banner -i out/final.mp4 -af ebur128=peak=true -f null NUL

# 流信息
ffprobe -v error -show_entries format=duration,size:stream=index,codec_type,codec_name,width,height,sample_rate,channels -of default=nw=1 out/final.mp4

# 硬字幕抽帧（改 t 到有字幕的位置）
ffmpeg -v error -y -ss 15:37 -i out/final.mp4 -frames:v 1 qa/hardsub_check.jpg

# 抽帧拼图
ffmpeg -i out/final.mp4 -vf "fps=1/5,scale=480:-1,tile=4x3" -frames:v 1 qa/sheet.png

# 并行渲染是否每段都完成
Get-ChildItem qa/render_part*.log | ForEach-Object { $_.Name; Get-Content $_ -Tail 1 }
```

## 4. 质量门槛

| 项 | 目标 |
|---|---|
| 时长误差 | ±0.2 s（相对 timeline） |
| 黑帧 | 0 个 ≥0.25 s |
| 响度 | −14.2 ±1 LUFS |
| 真峰值 | ≤ −1.5 dBFS（AAC 解码后） |
| 视频码率 | ≥1.5 Mbps（1080p 文字多时 2–3 Mbps） |
| 音频码率 | 192–256 kbps（手机版 192 立体声足够） |
| 字幕覆盖率 | 旁白 100% |
| 硬字幕 | 全片烧录；`ffprobe` 无独立字幕流 |
| 音色 | 段间 median f0 差 ≤20 Hz |
| 帧数 | 与 timeline 精确一致 |

## 5. 返工策略

- 只改某镜：改 `script.json` → `timeline.py` → 只重渲该段（`render.py --start/--duration`）→ 重新混音/编码；
- 改文案：重跑 `tts.py` + `timeline.py`（时长会变）；
- 改风格：换 `project.style` 重新 init 模板（场景代码通常不用动）；
- 改画幅：简单模板改 `project.format`；复杂讲解片建议复制工程单独写竖屏/横屏布局；
- 只改字幕：`make_ass.py` + `encode.py --ass` 重新烧录，不必重渲帧；
- 只改某几镜公式：重跑 `build_math_svgs.js` + `timeline.py`，只重渲受影响场景；
- 不要“整片重来”除非结构错了。
