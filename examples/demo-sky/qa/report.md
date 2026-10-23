# QA report

file: `out/final.mp4`
duration: 45.13s / timeline 45.12s

| check | result | detail |
|---|---|---|
| video stream | PASS | h264 |
| audio stream | PASS | aac |
| subtitle stream | PASS | optional |
| duration vs timeline | PASS | 45.13s vs 45.12s |
| no black >=0.25s | PASS |  |
| loudness | PASS | -15.5 LUFS |
| true peak | PASS | -2.1 dBFS |

overall: **PASS**

## streams
```json
[
 {
  "index": 0,
  "codec_name": "h264",
  "codec_type": "video",
  "width": 1080,
  "height": 1920,
  "r_frame_rate": "30/1"
 },
 {
  "index": 1,
  "codec_name": "aac",
  "codec_type": "audio",
  "sample_rate": "48000",
  "channels": 1
 },
 {
  "index": 2,
  "codec_name": "mov_text",
  "codec_type": "subtitle"
 }
]
```

## files
- `qa/contact.png`
- `qa/frames/*.png`
