#!/usr/bin/env python3
"""Run the video-flow pipeline steps in order."""
import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def run(cmd):
    print("\n$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--steps", default="tts,timeline,render,audio,srt,encode,qa")
    ap.add_argument("--cdp", default=None)
    ap.add_argument("--launch-chrome", action="store_true")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--no-tts", action="store_true", help="skip tts when VO already exists")
    args = ap.parse_args()
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    py = sys.executable
    proj = str(Path(args.project).resolve())

    for step in steps:
        if step == "tts":
            if args.no_tts:
                print("skip tts"); continue
            run([py, str(SCRIPTS / "tts.py"), "--project", proj])
        elif step == "timeline":
            cmd = [py, str(SCRIPTS / "timeline.py"), "--project", proj]
            if args.fps: cmd += ["--fps", str(args.fps)]
            run(cmd)
        elif step == "render":
            cmd = [py, str(SCRIPTS / "render.py"), "--project", proj]
            if args.cdp: cmd += ["--cdp", args.cdp]
            elif args.launch_chrome: cmd += ["--launch-chrome"]
            if args.fps: cmd += ["--fps", str(args.fps)]
            run(cmd)
        elif step == "audio":
            run([py, str(SCRIPTS / "audio.py"), "--project", proj])
        elif step == "srt":
            run([py, str(SCRIPTS / "srt.py"), "--project", proj])
        elif step == "encode":
            run([py, str(SCRIPTS / "encode.py"), "--project", proj])
        elif step == "qa":
            run([py, str(SCRIPTS / "qa.py"), "--project", proj])
        else:
            sys.exit(f"unknown step: {step}")


if __name__ == "__main__":
    main()
