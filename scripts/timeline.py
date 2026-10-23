#!/usr/bin/env python3
"""Build timeline.js / timeline.json / content.js from script.json + VO durations."""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def wav_dur(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path)
    ], text=True)
    return float(out.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--head", type=float, default=0.5, help="silence before VO")
    ap.add_argument("--tail", type=float, default=0.9, help="silence after VO")
    args = ap.parse_args()

    root = Path(args.project).resolve()
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    script = json.loads((root / "script.json").read_text(encoding="utf-8"))
    fps = args.fps or int(project.get("fps", 30))

    scenes = script.get("scenes", [])
    if not scenes:
        sys.exit("script.json has no scenes")

    timed = []
    t = 0.0
    for i, sc in enumerate(scenes):
        sid = sc.get("id") or f"s{i}"
        head = args.head
        tail = args.tail
        if sc.get("type") == "title":
            head = max(head, 0.8)
            tail = max(tail, 1.4)
        if sc.get("head") is not None:
            head = float(sc["head"])
        if sc.get("tail") is not None:
            tail = float(sc["tail"])

        vo = sc.get("vo") or ""
        vo_file = None
        vo_dur = 0.0
        if vo.strip():
            cand = root / "audio" / "vo" / f"{sid}.wav"
            alt = root / "audio" / "vo_human" / f"{sid}.wav"
            if cand.exists():
                vo_file = cand
            elif alt.exists():
                vo_file = alt
            else:
                sys.exit(f"missing VO for {sid}: {cand}")
            vo_dur = wav_dur(vo_file)

        dur = head + vo_dur + tail
        explicit = sc.get("duration")
        if explicit:
            dur = max(float(explicit), vo_dur + 0.6)
        dur = round(dur, 3)
        entry = {
            "id": sid,
            "type": sc.get("type", "concept"),
            "start": round(t, 3),
            "dur": dur,
            "voStart": round(t + head, 3) if vo_dur else None,
            "voDur": round(vo_dur, 3) if vo_dur else 0,
            "vo": str(vo_file.relative_to(root)).replace("\\", "/") if vo_file else None,
        }
        timed.append({"timeline": entry, "scene": sc})
        t = round(t + dur, 3)

    total = round(t, 3)
    (root / "build" / "timeline.js").write_text(
        "window.SCENES = " + json.dumps([x["timeline"] for x in timed], ensure_ascii=False, indent=1) + ";\n"
        "window.TOTAL = " + str(total) + ";\n",
        encoding="utf-8",
    )
    content = {"meta": {k: project.get(k) for k in ("title", "subtitle", "language", "format", "style")},
               "scenes": [x["scene"] for x in timed]}
    (root / "build" / "content.js").write_text(
        "window.CONTENT = " + json.dumps(content, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8"
    )
    (root / "timeline.json").write_text(json.dumps({"total": total, "fps": fps,
                                                   "scenes": [x["timeline"] for x in timed]},
                                                  ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "script.timed.json").write_text(json.dumps(
        {"meta": content["meta"], "scenes": [dict(x["scene"], **x["timeline"]) for x in timed]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"total {total:.2f}s / {round(total*fps)} frames @ {fps}fps")
    for x in timed:
        e = x["timeline"]
        print(f"  {e['id']:<6} {e['start']:>7.2f}s  dur {e['dur']:>6.2f}  vo {e['voDur']:>5.2f}")


if __name__ == "__main__":
    main()
