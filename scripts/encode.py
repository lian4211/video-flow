#!/usr/bin/env python3
"""Encode frames + audio (+ optional soft SRT or burned-in ASS) in a single video/audio encode."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--frames", default=None)
    ap.add_argument("--audio", default=None)
    ap.add_argument("--srt", default=None)
    ap.add_argument("--ass", default=None, help="burn this ASS file into the picture")
    ap.add_argument("--no-soft-subs", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--aac-kbps", type=int, default=256)
    ap.add_argument("--ac", type=int, default=None, help="audio channels: 1 mono / 2 stereo")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.project).resolve()
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    tl = json.loads((root / "timeline.json").read_text(encoding="utf-8"))
    fps = args.fps or int(tl.get("fps") or project.get("fps", 30))
    frames = Path(args.frames) if args.frames else root / "frames"
    audio = Path(args.audio) if args.audio else root / "audio" / "mix.wav"
    srt = Path(args.srt) if args.srt else (root / "out" / "final.srt")
    out = Path(args.out) if args.out else root / "out" / "final.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    if not (frames / "f00000.jpg").exists():
        sys.exit(f"no frames in {frames}")
    if not audio.exists():
        sys.exit(f"missing audio: {audio}")

    ass = None
    if args.ass:
        ass = Path(args.ass)
        if not ass.is_absolute():
            ass = root / ass
        if not ass.exists():
            sys.exit(f"missing ASS: {ass}")

    cmd = [
        "ffmpeg", "-hide_banner", "-v", "error", "-y",
        "-framerate", str(fps), "-i", str(frames / "f%05d.jpg"),
        "-i", str(audio),
    ]
    if ass:
        # Relative path avoids Windows drive-colon escaping inside -vf.
        rel = os.path.relpath(ass, root).replace("\\", "/")
        cmd += ["-vf", f"ass={rel}"]
    cmd += [
        "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", f"{args.aac_kbps}k",
        "-ar", "48000", "-movflags", "+faststart", "-shortest",
        "-metadata", f"title={project.get('title', '')}",
    ]
    if args.ac:
        cmd += ["-ac", str(args.ac)]
    cmd += [str(out)]
    if args.dry_run:
        print(" ".join(cmd)); return
    subprocess.run(cmd, cwd=str(root), check=True)
    print("encoded", out, out.stat().st_size)

    if srt.exists() and not args.ass and not args.no_soft_subs:
        sub = out.with_name(out.stem + "_subbed.mp4")
        cmd2 = ["ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", str(out), "-i", str(srt),
                "-map", "0", "-map", "1", "-c", "copy", "-c:s", "mov_text",
                "-metadata:s:s:0", "language=zho", "-movflags", "+faststart", str(sub)]
        subprocess.run(cmd2, check=True)
        sub.replace(out)
        print("muxed subtitles")


if __name__ == "__main__":
    main()
