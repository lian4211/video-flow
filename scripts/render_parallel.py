#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a project in N parallel chunks, each chunk with its own Chrome.

Why: headless Canvas rendering is CPU-bound and single-process Chrome often
tops out at 9-15 fps for 1080p. Four chunks typically give ~3-4x throughput.

Examples:
  python scripts/render_parallel.py --project . --chunks 4
  python scripts/render_parallel.py --project . --chunks 4 --cdp http://127.0.0.1:9333
  python scripts/render_parallel.py --project . --chunks 4 --dry-run
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RENDER = HERE / "render.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--chunks", type=int, default=4)
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--quality", type=int, default=92)
    ap.add_argument("--out", default="frames")
    ap.add_argument("--cdp", default=None)
    ap.add_argument("--no-launch-chrome", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.project).resolve()
    tl_path = root / "timeline.json"
    if not tl_path.exists():
        sys.exit(f"missing {tl_path}; run timeline.py first")
    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    total = float(tl["total"])
    fps = int(args.fps or tl.get("fps") or 30)
    frames = int(round(total * fps))
    n = max(1, int(args.chunks))
    print(f"total={total:.2f}s fps={fps} frames={frames} chunks={n}")

    procs = []
    for i in range(n):
        lo = round(i * frames / n)
        hi = round((i + 1) * frames / n)
        start = lo / fps
        dur = (hi - lo) / fps
        cmd = [
            sys.executable, str(RENDER),
            "--project", str(root),
            "--out", args.out,
            "--fps", str(fps),
            "--start", f"{start:.6f}",
            "--duration", f"{dur:.6f}",
            "--quality", str(args.quality),
        ]
        if args.cdp:
            cmd += ["--cdp", args.cdp]
        elif not args.no_launch_chrome:
            cmd += ["--launch-chrome"]

        if args.dry_run:
            print("chunk", i, "frames", lo, "..", hi, "|", " ".join(cmd))
            continue

        log_path = root / "qa" / f"render_part{i}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log = open(log_path, "w", encoding="utf-8")
        print(f"chunk {i}: frames {lo}..{hi - 1} ({dur:.1f}s) -> {log_path.name}")
        procs.append((i, subprocess.Popen(cmd, cwd=str(root), stdout=log, stderr=subprocess.STDOUT), log))

    if args.dry_run:
        return

    t0 = time.time()
    bad = []
    for i, p, log in procs:
        rc = p.wait()
        log.close()
        print(f"chunk {i}: exit {rc}")
        if rc != 0:
            bad.append((i, rc))

    elapsed = time.time() - t0
    print(f"done in {elapsed/60:.1f} min; logs in {root / 'qa'}")
    if bad:
        sys.exit(f"failed chunks: {bad}")


if __name__ == "__main__":
    main()
