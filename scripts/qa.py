#!/usr/bin/env python3
"""QA: probe streams, black frames, loudness, contact sheet; write qa/report.md."""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="ignore")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--file", default=None)
    args = ap.parse_args()
    root = Path(args.project).resolve()
    video = Path(args.file) if args.file else root / "out" / "final.mp4"
    qa = root / "qa"; qa.mkdir(exist_ok=True)
    if not video.exists():
        raise SystemExit(f"missing {video}")
    tl = json.loads((root / "timeline.json").read_text(encoding="utf-8"))
    total = float(tl["total"])

    _, probe = run(["ffprobe", "-v", "error", "-show_entries",
                    "format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
                    "-of", "json", str(video)])
    info = json.loads(probe)
    dur = float(info["format"]["duration"])
    streams = info.get("streams", [])
    has_v = any(s["codec_type"] == "video" for s in streams)
    has_a = any(s["codec_type"] == "audio" for s in streams)
    has_s = any(s["codec_type"] == "subtitle" for s in streams)
    v = next((s for s in streams if s["codec_type"] == "video"), {})

    _, black = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
                    "-vf", "blackdetect=d=0.25:pix_th=0.04", "-an", "-f", "null", os.devnull])
    black_hits = re.findall(r"black_start:([0-9.]+)", black)

    _, loud = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
                   "-af", "ebur128=peak=true", "-f", "null", os.devnull])
    li = re.findall(r"I:\s+(-?\d+\.\d+) LUFS", loud)
    tp = re.findall(r"Peak:\s+(-?\d+\.\d+) dBFS", loud)
    I = float(li[-1]) if li else None
    TP = float(tp[-1]) if tp else None

    # contact sheet + stills
    step = max(1.0, total / 12)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf",
         f"fps=1/{step:.3f},scale=480:-1,tile=4x3", "-frames:v", "1", str(qa / "contact.png")])
    frames_dir = qa / "frames"; frames_dir.mkdir(exist_ok=True)
    for pct in (0.02, 0.18, 0.36, 0.54, 0.72, 0.9):
        t = total * pct
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
             str(frames_dir / f"at_{pct:.2f}.png")])

    checks = []
    def chk(name, ok, detail):
        checks.append((name, ok, detail))
    chk("video stream", has_v, v.get("codec_name", ""))
    chk("audio stream", has_a, "aac" if has_a else "MISSING")
    chk("subtitle stream", has_s, "optional" if has_s else "none")
    chk("duration vs timeline", abs(dur - total) <= 0.5, f"{dur:.2f}s vs {total:.2f}s")
    chk("no black >=0.25s", len(black_hits) == 0, ",".join(black_hits[:5]))
    chk("loudness", I is not None and abs(I - (-14.2)) <= 1.5, f"{I} LUFS")
    chk("true peak", TP is not None and TP <= -1.0, f"{TP} dBFS")

    ok_all = all(x[1] for x in checks)
    try:
        shown = video.relative_to(root).as_posix()
    except ValueError:
        shown = str(video)
    lines = ["# QA report", "", f"file: `{shown}`", f"duration: {dur:.2f}s / timeline {total:.2f}s", ""]
    lines += ["| check | result | detail |", "|---|---|---|"]
    for name, ok, detail in checks:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    lines += ["", f"overall: **{'PASS' if ok_all else 'CHECK' }**", ""]
    lines += ["## streams", "```json", json.dumps(streams, ensure_ascii=False, indent=1), "```", ""]
    lines += ["## files", "- `qa/contact.png`", "- `qa/frames/*.png`", ""]
    (qa / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:16]))
    print("report ->", qa / "report.md")


if __name__ == "__main__":
    main()
