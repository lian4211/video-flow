# 本地高质量 TTS：VoxCPM2（48 kHz）

> 适用：Edge TTS 的 24 kHz / 48 kbps 已经不够用，需要“抖音级/商业配音”质感，且不想把旁白发给云端。
> 结论：**VoxCPM2 2B + 一段 10–30 秒参考音色克隆**，是当前开源里“48 kHz + 可商用 + 可本地跑”的最优解之一。

---

## 1. 为什么需要这一层

| 方案 | 采样率 | 自然度 | 情绪/音色 | 许可 | 结论 |
|---|---|---|---|---|---|
| Edge TTS | 24 kHz / 48 kbps | 好，但偏“播音腔” | 不可控 | 免费接口 | 快速草稿 |
| 系统 SAPI | 16 kHz | 机械 | 不可控 | 系统 | 仅离线兜底 |
| **VoxCPM2** | **48 kHz** | **接近商业配音** | **Voice Design + 参考克隆** | **Apache-2.0** | **成片首选** |
| 真人录音 | 取决于录音 | 最好 | 完全可控 | 需授权 | 品牌片/指定声线 |

VoxCPM2 的关键不是“参数大”，而是：原生 48 kHz、tokenizer-free、可用一段参考音频把音色/节奏/情绪一起带过来。

---

## 2. 安装（Windows 示例，Linux 同理）

### 2.1 硬件

- NVIDIA GPU，**≥ 8 GB 显存**（RTX 4060 Laptop 8 GB 实测可跑；加载后约 5.3 GB）；
- 磁盘 ≈ 8 GB（CUDA PyTorch 2.7 GB + 模型 4.7 GB）；
- 没有 GPU 也能 CPU 跑，但 2B 模型会很慢，不建议做 2 分钟以上的片子。

### 2.2 隔离环境

```bash
python -m venv .venv-voxcpm
# Windows
.venv-voxcpm\Scripts\activate
# Linux/macOS
source .venv-voxcpm/bin/activate

python -m pip install -U pip
```

### 2.3 CUDA 版 PyTorch

PyPI 的 Windows `torch` 默认是 CPU 版；必须从 PyTorch 官方 index 装 CUDA 版：

```bash
# 以 cu128 / torch 2.11 为例；驱动需支持对应 CUDA
pip install torch==2.11.0+cu128 torchaudio==2.11.0+cu128 \
  --index-url https://download.pytorch.org/whl/cu128
```

验证：

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# 期望：2.11.0+cu128 True NVIDIA GeForce RTX ...
```

> 如果 `torch.cuda.is_available()` 为 False，先查显卡驱动；不要继续装模型，否则只能 CPU 跑。

### 2.4 VoxCPM 包与模型

```bash
pip install voxcpm
# 可选：只装运行所需，避免 gradio/funasr 等大依赖
# pip install transformers einops addict safetensors soundfile librosa huggingface_hub
```

模型下载（HuggingFace 不可达时用 ModelScope）：

```bash
pip install modelscope
modelscope download --model OpenBMB/VoxCPM2 --local_dir models/VoxCPM2
```

目录应包含：

```text
models/VoxCPM2/
  config.json
  model.safetensors      # ~4.37 GB
  audiovae.pth           # ~360 MB
  tokenizer.json
  tokenizer_config.json
  special_tokens_map.json
  tokenization_voxcpm2.py
```

离线运行前可设：

```bash
set HF_HUB_OFFLINE=1        # Windows
export HF_HUB_OFFLINE=1     # Linux/macOS
```

### 2.5 快速自检

```bash
python -c "from voxcpm import VoxCPM; m=VoxCPM.from_pretrained('models/VoxCPM2', load_denoiser=False, optimize=False, device='cuda'); print(m.tts_model.sample_rate)"
# 期望：48000
```

首次加载约 25 s；之后每 10 s 音频约 20–30 s（RTF ≈ 2–2.5，RTX 4060 Laptop）。

---

## 3. 在 video-flow 里使用

### 3.1 准备参考音色（推荐）

准备一段 **10–30 秒、干净、单人、无音乐/混响** 的参考音频，最好 48 kHz；同时在 `audio/voice_ref.txt` 写下**逐字 transcript**（必须和音频完全一致）。

```text
<project>/
  audio/
    voice_ref.wav        # 参考音色
    voice_ref.txt        # 参考音频的逐字文本
```

> 参考音频越干净、情绪越接近目标，克隆越自然。
> 不要用带 BGM、多人、电话音质的片段；不要克隆未授权的声音。

### 3.2 project.json

```json
{
  "voice": {
    "engine": "voxcpm",
    "model_dir": "models/VoxCPM2",
    "ref_audio": "audio/voice_ref.wav",
    "ref_text": "",
    "control": "",
    "atempo": 0.95,
    "device": "cuda"
  }
}
```

- `ref_text` 留空时，`tts.py` 会读取 `audio/voice_ref.txt`；
- 没有参考音频时，可只用 `control` 做 Voice Design（音色一致性弱一些）；
- `atempo: 0.95` = 放慢 5%，不改音高，教学片更稳。

### 3.3 生成

```bash
# 用 project.json 里的配置
python scripts/tts.py --project . --engine voxcpm --model-dir models/VoxCPM2

# 或显式指定参考音色
python scripts/tts.py --project . --engine voxcpm \
  --model-dir models/VoxCPM2 \
  --ref-audio audio/voice_ref.wav \
  --ref-text "参考音频的逐字文本" \
  --atempo 0.95

# 没有参考音频：纯 Voice Design
python scripts/tts.py --project . --engine voxcpm \
  --model-dir models/VoxCPM2 \
  --control "温暖自然的年轻女声，普通话标准，口语化，语速适中"
```

输出仍是 `audio/vo/<id>.wav`（48 kHz 单声道），后续 `timeline.py → render.py → audio.py → encode.py` 不变。

### 3.4 试听与重生成

- 先只生成 1 段试听，确认音色/语速/专有名词，再跑全片；
- 改 `script.json` 后加 `--force` 重生成；
- 8 段共用同一参考音色，保证段间一致；
- 如果某段读错，单独改该段 `vo` 文本，不要重生成全片。

---

## 4. 中文技术名词：避免“断着读”

这是实测最容易翻车的地方。TTS 对空格/缩写很敏感：

| 写法 | 实际听感 | 建议 |
|---|---|---|
| `A L U` | “A—L—U”，字母间有停顿 | ❌ 不要用空格拆字母 |
| `ALU` | 有的模型读字母，有的读“阿鲁” | 首次出现写全称 |
| `算术逻辑单元` | 连贯、像人话 | ✅ 推荐 |
| `CPU` | 可能读 “C P U” 或 “CPU” | 口播用“处理器” |
| `CF / OF` | 字母+停顿 | 口播用“进位标志/溢出标志” |
| `74181` | 可能读成“七万四千…” | 写成“七四一八一” |
| `S3~S0` | 符号/字母混读 | 写成“选择端 S 三到 S 零” |

原则：

1. **屏幕保留缩写，口播用中文全称**；字幕跟屏幕一致即可；
2. 数字按中文读法写（74181 → 七四一八一；16 → 十六）；
3. 标点就是停顿：逗号短停、句号长停；不要用大量省略号；
4. 每段旁白控制在 1–2 句；长句拆成两个 scene 或加句号；
5. 生成后**必听**关键段：开场、ALU 首次出现、74181/74182、CF/OF。

---

## 5. 后处理与混音

`scripts/tts.py --engine voxcpm` 默认使用轻处理链（与 Edge 链不同，避免过度染色）：

```text
48 kHz 单声道
→ atempo 0.95（可选，不改音高）
→ highpass 60 Hz
→ EQ: 180 Hz +0.8 dB, 3.2 kHz +0.6 dB
→ 轻压缩: -20 dB / 1.4 / 8 ms / 150 ms
→ 峰值归一化
```

建议：

- **不要**再叠加“重低音/空间感”插件；VoxCPM2 本身已经干净；
- 需要“录音棚感”时加极短 room（`--room`），但教学片默认不加；
- 母带仍按 `audio.py`：−14.2 LUFS、真峰值 ≤ −1.5 dBFS、只做一次 AAC；
- 24 kHz 的模型（如 Qwen3-TTS）不要靠升采样冒充 48 kHz；要 48 kHz 就用 VoxCPM2。

---

## 6. 常见问题

| 现象 | 原因 | 修 |
|---|---|---|
| 加载 OOM | 8 GB 显存被浏览器/桌面占用 | 关 Chrome/游戏；`optimize=False`；`load_denoiser=False`；仍不行换 0.6B 级模型 |
| `torch.cuda.is_available()=False` | 装了 CPU wheel | 卸掉 torch，按 CUDA index 重装 |
| 模型下载卡住/重置 | HF 不可达 | 用 ModelScope；断点续传脚本见 `scripts/` 或手动重试 |
| 声音“人机感” | 用 AI 设计音再克隆（二次合成） | 换成**真实/官方演示参考音**；放慢 5%；避免字母空格 |
| 专有名词断读 | 缩写/空格/符号 | 按第 4 节改写口播文本 |
| 语速太快 | 参考音本身快 | `--atempo 0.92~0.95`；或在参考音里放慢 |
| 段间音色漂移 | 每段独立 Voice Design | 固定同一 `ref_audio`，全片克隆 |
| 真峰值超标 | 多段叠加/母带过推 | WAV 阶段静态增益；重新母带，不从 MP4 转 |

---

## 7. 许可与合规

- **VoxCPM2 代码/权重：Apache-2.0**，可商用；仍需遵守其模型卡与当地法律。
- **参考音色**：必须拥有授权/肖像/声音权；不要克隆未授权的真人、主播、影视角色。
- 生成音频的版权归属因司法辖区而异；商用前自行确认。
- 本 Skill 不附带模型权重；`models/` 应加入 `.gitignore`。

---

## 8. 性能参考（RTX 4060 Laptop 8 GB）

| 阶段 | 耗时 |
|---|---|
| 模型加载 | ≈ 25 s |
| 10 s 旁白（10 steps） | ≈ 20–30 s |
| 2 分钟成片（8 段） | ≈ 4–5 min 生成 + 4–9 min 渲染 |

> 生成比渲染更值得等待；先用 1 段试音确认音色，再批量生成。
