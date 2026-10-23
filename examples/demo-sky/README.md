# demo-sky：45 秒竖屏示例

这是用 video-flow 从**一个主题**（不是现成 PDF）生成的完整示例，用来验证“换主题/换画幅/换风格”不需要改代码。

- 画幅：9:16（1080×1920）
- 风格：paper
- 声音：Edge TTS `zh-CN-XiaoxiaoNeural` + 程序化 ambient BGM
- 时长：45.1 秒
- 成片：`out/final.mp4`（含软字幕）
- 海报：`out/poster.png`
- 质检：`qa/report.md`

## 怎么复现

```bash
cd examples/demo-sky
python ../../scripts/tts.py --project .
python ../../scripts/timeline.py --project .
python ../../scripts/render.py --project . --launch-chrome
python ../../scripts/audio.py --project .
python ../../scripts/srt.py --project .
python ../../scripts/encode.py --project .
python ../../scripts/qa.py --project .
```

或者一键：

```bash
python ../../scripts/run_pipeline.py --project . --launch-chrome
```

## 文件说明

- `script.json`：5 个镜头（title / concept / process / formula / recap）
- `build/`：由 `init_project.py` 生成的模板，`timeline.py` 生成 `timeline.js/content.js`
- `audio/vo/`：旁白 WAV（48 kHz）；删除后可重新生成
- `out/final.mp4`：成片；`out/final.srt`：字幕
- `qa/report.md`：自动质检结果（全 PASS）
