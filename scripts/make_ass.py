#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a burn-in ASS subtitle file from SRT.

Why ASS: ffmpeg's `subtitles`/`ass` filter gives stable font/size/outline and
lets you control MarginV. SRT burn-in has almost no styling control.

Examples:
  python scripts/make_ass.py --project . --srt out/final.srt --out out/final.ass
  python scripts/make_ass.py --project . --width 1080 --height 1920 \
      --font-size 42 --margin-v 64
"""
import argparse
import re
import sys
from pathlib import Path

TS = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")
CUE = re.compile(r"(\d+)\s*\n([^\n]+)\s*\n(.*?)(?=\n\s*\n|\Z)", re.S)


def ass_time(h, m, s, ms):
    # ASS uses centiseconds, H:MM:SS.cc
    cc = int(round(int(ms.ljust(3, "0")[:3]) / 10.0))
    if cc >= 100:
        cc = 99
    return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cc:02d}"


def visual_units(s):
    u = 0.0
    for ch in s:
        if ch == " ":
            u += 0.35
        elif ord(ch) < 128:
            u += 0.55
        else:
            u += 1.0
    return u


def wrap_line(s, max_units):
    if not max_units or visual_units(s) <= max_units:
        return [s]
    out, cur, cur_u = [], "", 0.0
    for ch in s:
        cu = 0.35 if ch == " " else (0.55 if ord(ch) < 128 else 1.0)
        if cur and cur_u + cu > max_units:
            out.append(cur.rstrip())
            cur, cur_u = "", 0.0
        cur += ch
        cur_u += cu
    if cur.strip():
        out.append(cur.strip())
    return out or [s]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--srt", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--font", default="Microsoft YaHei")
    ap.add_argument("--font-size", type=int, default=42)
    ap.add_argument("--margin-v", type=int, default=64)
    ap.add_argument("--margin-h", type=int, default=80)
    ap.add_argument("--outline", type=float, default=2.2)
    ap.add_argument("--shadow", type=float, default=1.2)
    ap.add_argument("--wrap", type=float, default=0.0,
                    help="max visual units per line; 0 = keep SRT line breaks")
    args = ap.parse_args()

    root = Path(args.project).resolve()
    srt = Path(args.srt) if args.srt else root / "out" / "final.srt"
    if not srt.is_absolute():
        srt = root / srt
    out = Path(args.out) if args.out else root / "out" / "final.ass"
    if not out.is_absolute():
        out = root / out
    if not srt.exists():
        sys.exit(f"missing SRT: {srt}")

    text = srt.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    events = []
    for m in CUE.finditer(text):
        stamp = m.group(2)
        tm = TS.search(stamp)
        if not tm:
            continue
        start = ass_time(*tm.groups()[:4])
        end = ass_time(*tm.groups()[4:])
        body = m.group(3).strip()
        lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
        if not lines:
            continue
        wrapped = []
        for ln in lines:
            wrapped.extend(wrap_line(ln, args.wrap) if args.wrap else [ln])
        body = r"\N".join(wrapped)
        body = body.replace("{", r"\{").replace("}", r"\}")
        events.append((start, end, body))

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {args.width}
PlayResY: {args.height}
WrapStyle: 2
ScaledBorderAndShadow: yes
Collisions: Normal

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{args.font},{args.font_size},&H00FFFFFF,&H000000FF,&H00101820,&H64000000,-1,0,0,0,100,100,0,0,1,{args.outline},{args.shadow},2,{args.margin_h},{args.margin_h},{args.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "\n".join(f"Dialogue: 0,{a},{b},Default,,0,0,0,,{t}" for a, b, t in events)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(header + body + "\n", encoding="utf-8")
    print(f"{len(events)} cues -> {out} ({args.width}x{args.height}, {args.font_size}px, MarginV={args.margin_v})")


if __name__ == "__main__":
    main()
