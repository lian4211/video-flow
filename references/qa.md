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

## 3. 自动命令

```bash
# 黑帧（>=0.25s）
ffmpeg -hide_banner -i out/final.mp4 -vf "blackdetect=d=0.25:pix_th=0.04" -an -f null NUL

# 响度/真峰值
ffmpeg -hide_banner -i out/final.mp4 -af ebur128=peak=true -f null NUL

# 流信息
ffprobe -v error -show_entries format=duration,size:stream=index,codec_type,codec_name,width,height,sample_rate,channels -of default=nw=1 out/final.mp4

# 抽帧拼图
ffmpeg -i out/final.mp4 -vf "fps=1/5,scale=480:-1,tile=4x3" -frames:v 1 qa/sheet.png
```

## 4. 质量门槛

| 项 | 目标 |
|---|---|
| 时长误差 | ±0.2 s（相对 timeline） |
| 黑帧 | 0 个 ≥0.25 s |
| 响度 | −14.2 ±1 LUFS |
| 真峰值 | ≤ −1.5 dBFS（AAC 解码后） |
| 视频码率 | ≥1.5 Mbps（1080p 文字多时 2–3 Mbps） |
| 音频码率 | 256 kbps |
| 字幕覆盖率 | 旁白 100% |

## 5. 返工策略

- 只改某镜：改 `script.json` → `timeline.py` → 只重渲该段（`render.py --start/--duration`）→ 重新混音/编码；
- 改文案：重跑 `tts.py` + `timeline.py`（时长会变）；
- 改风格：换 `project.style` 重新 init 模板（场景代码通常不用动）；
- 改画幅：`project.format` 重渲；检查竖屏排版；
- 不要“整片重来”除非结构错了。
