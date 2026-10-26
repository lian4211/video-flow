# Audio：旁白、配乐、混音与响度

## 1. 四种声音来源

| 来源 | 何时用 | 质量 | 命令 |
|---|---|---|---|
| Edge 神经语音 | 默认，有网络 | 24 kHz / 48 kbps，自然度好 | `tts.py --engine edge --voice zh-CN-XiaoxiaoNeural` |
| **VoxCPM2 本地** | 要 48 kHz、要“抖音级”/商业配音感 | **48 kHz，可克隆音色/情绪，Apache-2.0** | `tts.py --engine voxcpm --model-dir models/VoxCPM2 --ref-audio audio/voice_ref.wav` |
| 系统离线语音 | 无网络/必须离线 | 一般，偏机械 | `tts.py --engine sapi`（Windows） |
| 真人录音 | 要求“像真人”/品牌片 | 最好 | 把 `<id>.wav` 放 `audio/vo_human/`，`tts.py --from-dir` |

**边界**：Edge 免费接口的源是 24 kHz；要 48 kHz 录音棚级，优先用 **VoxCPM2 本地 48 kHz**（Apache-2.0，8 GB 显存可跑），其次才是真人录音或付费 API。不要用“升采样 + 重低音”假装高音质。

> 本地 48 kHz 的完整安装、参考音色、中文技术名词改写、OOM/下载/音色问题，见 [`local-tts.md`](local-tts.md)。

### 1.1 本地 VoxCPM2 的最小用法

```bash
# 1) 参考音色：10–30 s 干净人声；transcript 放 audio/voice_ref.txt
# 2) project.json 的 voice.engine 设为 voxcpm，ref_text 填逐字文本
python scripts/tts.py --project . --engine voxcpm --model-dir models/VoxCPM2 --atempo 0.91
```

- **必须 both 模式**：`ref_audio` + `ref_text` 同时给。只给 `ref_audio` 时克隆相似度低，段间 median f0 可从 130 Hz 漂到 230 Hz，听感像换人。
- 全片固定同一 `ref_audio`/`ref_text`/`atempo`，不要逐段换声线；
- 口播把 `ALU/CPU/CF/OF` 改成中文全称，屏幕保留缩写；
- 数字写成中文读法（74181 → 七四一八一）；
- 生成后先抽查 3 段 f0（中位数），再批量。

### 1.2 音色一致性自检

```bash
python - <<'PY'
import numpy as np, soundfile as sf, glob
for p in sorted(glob.glob("audio/vo/*.wav"))[:5]:
    x, sr = sf.read(p)
    x = x[:,0] if x.ndim>1 else x
    # 简易自相关 f0（只用于相对比较）
    x = x - x.mean()
    ac = np.correlate(x, x, "full")[len(x)-1:]
    lo, hi = sr//400, sr//70
    print(p, sr, round(sr/(lo+np.argmax(ac[lo:hi])),1), "Hz")
PY
```

段间中位数差 >20 Hz 就要查参考音/文本是否一致。

### 1.3 停顿：不要一直连读

- 句号/问号后至少 0.25–0.40 s；逗号 0.12–0.20 s；
- VoxCPM2 本身可能连读，可在音频静音段补 0.10–0.18 s；
- 不要用整体 `atempo 0.85` 代替停顿：会拖慢所有字，反而不自然；
- 每个场景的 `vo` 保持 1–2 句，长句拆场景；这比后期硬插静音更自然。

## 2. TTS 参数

- 中文女声：`zh-CN-XiaoxiaoNeural`（温暖）、`zh-CN-XiaoyiNeural`（活泼）；
- 中文男声：`zh-CN-YunxiNeural`（年轻）、`zh-CN-YunyangNeural`（新闻）、`zh-CN-YunjianNeural`（激情）；
- 语速：`+0% ~ +6%`；教学片推荐 `+3%`；不要用 `+10%` 以上，辅音会糊。
- 音高：默认 `+0Hz`；不要为了“低沉”降太多，会失真。
- 旁白按场景整段合成，不要一句一句拼接；句间留 0.3–0.6 s。

## 3. 人声处理链（tts.py 内置，可关）

```text
48 kHz 单声道
→ highpass 75 Hz
→ EQ: 180 Hz +1.2 dB（厚度）, 3.2 kHz +0.8 dB（清晰度）
→ 轻压缩: threshold -20 dB, ratio 1.8, attack 8 ms, release 140 ms
→ 极短房间反射: aecho 0.8:0.7:22:0.05（可关）
→ 峰值归一化（不削顶）
```

真人录音额外：降噪（`afftdn`）、去齿音（`deesser`）、静音裁剪（`silenceremove`）。

**VoxCPM2 本地音源**用更轻的链（`tts.py --engine voxcpm` 内置）：

```text
48 kHz 单声道
→ atempo 0.91（可选，不改音高）
→ highpass 60 Hz
→ EQ: 180 Hz +0.8 dB, 3.2 kHz +0.6 dB
→ 轻压缩: -20 dB, ratio 1.4, 8 ms / 150 ms
→ 峰值归一化
```

本地模型本身已经干净，不要再叠重低音/空间插件；需要时只加极短 room。

## 4. 配乐

`audio.py` 内置 4 种程序化 BGM（numpy 合成，无版权问题）：

| preset | 氛围 | 速度 | 适合 |
|---|---|---|---|
| `ambient` | 温暖 pad + 稀疏琶音 | 慢 | 人文、科普 |
| `tech` | 脉冲低音 + 电子 tick | 96–110 BPM | 工程、芯片、产品 |
| `paper` | 钢琴/拨弦 + 轻噪 | 慢 | 讲义、历史 |
| `uplift` | 明亮和弦 + 推进鼓点 | 110–120 BPM | 发布、营销 |

用户提供音乐：`audio/music.mp3|wav`，脚本会循环/裁切到总时长，并做 ducking。

## 5. Ducking 与混音

- 旁白出现时，BGM 增益降到 **0.25–0.35**（约 −10 dB），释放 300 ms；
- BGM 在无旁白间隙保持在 **−32 ~ −36 dBFS**（能听到但不抢）；
- 旁白 RMS 约 **−16 dBFS**；
- 音效（whoosh/tick/ding）峰值 −18 ~ −12 dBFS，放在动作帧。

## 6. 响度与编码

- 目标：**−14.2 LUFS**（可配 −14 ~ −16）；真峰值 **≤ −1.5 dBFS**；
- 在 WAV 阶段用**静态增益 + 轻限幅**达到目标；不要用多次 `loudnorm`；
- 最终 **只做一次 AAC 256 kbps / 48 kHz** 编码；
- 若真峰值超标，从同一份 WAV 重新以 −1 dB 编码一次，不要从已编码文件再转。

## 7. 常见问题

| 现象 | 原因 | 修 |
|---|---|---|
| 声音发闷 | 源 24 kHz + 过度低通/压缩 | 减压缩；加 3 kHz presence；不要加低通 |
| 声音发尖/齿音 | TTS 本身 + 高音增强 | 加 deesser，降 6–8 kHz |
| 音量忽大忽小 | 动态 loudnorm | 静态增益；WAV 阶段轻压缩 |
| 音画不同步 | 音频从 0 开始 vs 视频从 start | timeline 统一；`-ss` 放在 `-i` 前 |
| 旁白被音乐盖住 | duck 不够/音乐太响 | BGM 降 6 dB；duck 深度 0.3；旁白 +2 dB |
| TTS 读错专业词 | 文本缩写/符号 | 改写为口语（“74181”→“七四一八一”）；先试听关键段 |
