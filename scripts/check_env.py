#!/usr/bin/env python3
"""Environment check for video-flow.

Prints a checklist; exit code 1 if required tools are missing.
"""
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys

MODULES = [
    ("numpy", True, "音频/合成"),
    ("scipy", False, "滤波/重采样"),
    ("PIL", False, "抽帧/拼图"),
    ("pypdf", False, "PDF 文本抽取"),
    ("pptx", False, "PPTX 抽取"),
    ("docx", False, "DOCX 抽取"),
    ("requests", False, "URL 抽取"),
    ("edge_tts", False, "在线神经语音"),
]

CHROME_CANDIDATES = {
    "Windows": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ],
    "Linux": [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ],
}


def has(mod):
    return importlib.util.find_spec(mod) is not None


def which(cmd):
    return shutil.which(cmd)


def chrome_path():
    for p in CHROME_CANDIDATES.get(platform.system(), []):
        if os.path.exists(p):
            return p
    return which("chrome") or which("chromium") or which("chromium-browser") or which("msedge")


def check_cdp(url):
    try:
        import urllib.request
        with urllib.request.urlopen(url.rstrip("/") + "/json/version", timeout=3) as r:
            info = json.loads(r.read().decode("utf-8"))
        return True, info.get("Browser", "")
    except Exception as e:
        return False, str(e)


def main():
    ok = True
    print("=" * 62)
    print("video-flow environment check")
    print("=" * 62)
    print(f"OS       : {platform.system()} {platform.release()}")
    print(f"Python   : {sys.version.split()[0]}  ({sys.executable})")

    print("\n[Python modules]")
    for mod, required, why in MODULES:
        good = has(mod)
        mark = "OK " if good else ("MISS" if required else "warn")
        print(f"  [{mark}] {mod:<12} {why}")
        if required and not good:
            ok = False

    print("\n[CLI tools]")
    for cmd, required in (("ffmpeg", True), ("ffprobe", True)):
        p = which(cmd)
        print(f"  [{'OK ' if p else 'MISS'}] {cmd:<8} {p or ''}")
        if required and not p:
            ok = False

    cp = chrome_path()
    print(f"  [{'OK ' if cp else 'MISS'}] chrome   {cp or 'install Chrome/Chromium/Edge'}")

    print("\n[CDP]")
    url = os.environ.get("VIDEO_FLOW_CDP", "")
    if url:
        good, info = check_cdp(url)
        print(f"  [{'OK ' if good else 'warn'}] {url} {info}")
    else:
        print("  [info] no VIDEO_FLOW_CDP set; render.py --launch-chrome will start its own")

    print("\n[Suggested installs]")
    missing = [m for m, req, _ in MODULES if req and not has(m)]
    if missing:
        print("  python -m pip install " + " ".join(missing))
    if not which("ffmpeg"):
        print("  install FFmpeg and add it to PATH")
    if not cp:
        print("  install Google Chrome or Chromium")

    print("\n[Notes]")
    print("  - If Chrome cannot start due to sandbox IPC restrictions, run render.py in an")
    print("    environment that allows Chrome, or start Chrome yourself and pass --cdp.")
    print("  - edge-tts needs network; without it use --engine sapi or human recordings.")
    print("\n" + ("READY" if ok else "NOT READY"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
