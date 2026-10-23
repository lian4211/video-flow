#!/usr/bin/env python3
"""Build SRT subtitles from script.timed.json (proportional to character count)."""
import argparse
import json
import re
from pathlib import Path


def split_text(text, max_chars=22):
    parts = re.split(r"(?<=[。；！？])", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        subs = re.split(r"(?<=[，、：])", p)
        buf = ""
        for s in subs:
            if len(buf) + len(s) <= max_chars:
                buf += s
            else:
                if buf:
                    out.append(buf)
                buf = s
        if buf:
            out.append(buf)
    capped = []
    for s in out:
        while len(s) > max_chars + 4:
            capped.append(s[:max_chars + 4])
            s = s[max_chars + 4:]
        if s:
            capped.append(s)
    return capped


def fmt(sec):
    ms = max(0, int(round(sec * 1000)))
    h = ms // 3600000; ms %= 3600000
    m = ms // 60000; ms %= 60000
    s = ms // 1000; ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--max-chars", type=int, default=22)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.project).resolve()
    data = json.loads((root / "script.timed.json").read_text(encoding="utf-8"))
    cues = []
    for sc in data["scenes"]:
        vo = (sc.get("vo") or "").strip()
        if not vo or not sc.get("voStart"):
            continue
        t0 = float(sc["voStart"]); dur = float(sc["voDur"])
        chunks = split_text(vo, args.max_chars)
        total = sum(len(c) for c in chunks) or 1
        t = t0
        for c in chunks:
            d = dur * len(c) / total
            cues.append((t, min(t0 + dur, t + d), c))
            t += d
    lines = []
    for i, (a, b, s) in enumerate(cues, 1):
        if b - a < 0.6:
            b = a + 0.6
        lines += [str(i), f"{fmt(a)} --> {fmt(b)}", s, ""]
    out = Path(args.out) if args.out else root / "out" / "final.srt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(cues)} cues -> {out}")


if __name__ == "__main__":
    main()
