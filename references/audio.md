# Audio：旁白、配乐、混音与响度

## 1. 三种声音来源

| 来源 | 何时用 | 质量 | 命令 |
|---|---|---|---|
| Edge 神经语音 | 默认，有网络 | 24 kHz / 48 kbps，自然度好 | `tts.py --engine edge --voice zh-CN-XiaoxiaoNeural` |
| 系统离线语音 | 无网络/必须离线 | 一般，偏机械 | `tts.py --engine sapi`（Windows） |
| 真人录音 | 要求“像真人”/品牌片 | 最好 | 把 `<id>.wav` 放 `audio/vo_human/`，`tts.py --from-dir` |

**必须承认的边界**：Edge 免费接口的源是 24 kHz；要 48 kHz 录音棚级，只有真人录音或付费 API（Azure/ElevenLabs）两条路。不要用“升采样 + 重低音”假装高音质。

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
