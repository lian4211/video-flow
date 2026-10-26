# 并行渲染：把 30 分钟压到 8–10 分钟

> 逐帧渲染是 CPU 密集，单进程 headless Chrome 在 1080p Canvas 上通常只有 **9–15 fps**。
> 一条 36 分钟、66,450 帧的片子，单进程要 1.5–2 小时；4 进程可到 ~30 分钟。

---

## 1. 先算清楚成本

```text
帧数 = round(总时长 × fps)
单进程耗时 ≈ 帧数 / 单进程 fps
并行耗时 ≈ 帧数 / (单进程 fps × 进程数) + 启动/合并开销
```

实测（1920×1080、Canvas 2D、复杂公式/卡片）：

| 进程数 | 每进程 fps | 总 fps | 66,450 帧耗时 |
|---|---|---|---|
| 1 | 12 | 12 | ~92 min |
| 4 | 9 | 36 | ~31 min |
| 6 | 7–8 | 42–48 | ~23–26 min |

不是越多越好：Chrome 每个实例都吃内存/CPU，超过 6–8 个进程后总吞吐不再线性增长。

---

## 2. 用 `render_parallel.py`

```bash
# 4 进程，自动按 timeline.json 的 total 切分
python scripts/render_parallel.py --project . --chunks 4

# 连接一个已启动的 Chrome（所有 chunk 共用）
python scripts/render_parallel.py --project . --chunks 4 --cdp http://127.0.0.1:9333

# 只看切分，不启动进程
python scripts/render_parallel.py --project . --chunks 4 --dry-run
```

脚本会：

1. 读 `timeline.json.total` 与 `fps`；
2. 把 `round(total*fps)` 帧切成 N 段；
3. 每段起一个 `render.py --start/--duration` 子进程，各自 `--launch-chrome`；
4. 日志写到 `qa/render_part0..N.log`；
5. 全部结束后检查退出码。

`render.py` 已支持断点续渲：已存在且 >2KB 的帧会跳过。重跑只会补缺失帧。

---

## 3. 切分原则

- **按帧切，不按秒切**：用 `lo=round(i*frames/N)`，避免每段多/少一帧；
- 每段 `duration = (hi-lo)/fps`；
- 最后一段可能略短，正常；
- 每段独立 Chrome，互不共享 cookie/profile，避免锁；
- 不要把同一帧分给两个进程；
- 输出仍写同一个 `frames/`，文件名全局唯一，不会冲突。

---

## 4. 增量重渲

改一个场景时，不要全片重来：

```bash
# 先查该场景在 timeline.json 的 start/dur
python - <<'PY'
import json
tl=json.load(open('timeline.json'))
for s in tl['scenes']:
    if s['id']=='s04_05': print(s['start'], s['dur'])
PY

# 只渲该段（前后各留 0.5s 边界）
python scripts/render.py --project . --start 930 --duration 40 --launch-chrome
```

然后只重编码（帧序列缺的仍从旧帧补），音频/字幕不变。

**注意**：如果改文案导致 TTS 时长变化，`timeline.py` 会改变后续所有 `start`，这时不能只渲单段，必须全量重渲。

---

## 5. 编码瓶颈

渲染完成后，编码也可能 5–10 分钟：

- `libx264 -preset slow -crf 18`：画质优先，36 分钟 1080p 约 6–8 分钟；
- `-preset medium`：快约 30–40%，体积略大；
- `NVENC`（`h264_nvenc`）：快 2–3 倍，但文字/线条可能有轻微涂抹，交付前对比一帧；
- 硬字幕（ASS）会多一层滤镜，时间再 +10–20%；
- 不要为了快而把 `crf` 提到 23：小字会糊。

---

## 6. 何时用 GPU 渲染

Canvas 2D 在 headless Chrome 里默认走软件光栅（CPU）。如果场景是大量 WebGL/滤镜，可尝试：

```bash
chrome --use-gl=angle --use-angle=swiftshader ...
```

但大多数“卡片+文字+公式”的讲解片，CPU 并行比折腾 GPU 更稳。
