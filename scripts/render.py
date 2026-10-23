#!/usr/bin/env python3
"""Render a render(t) page frame-by-frame via Chrome DevTools Protocol.

Examples:
  python render.py --project . --launch-chrome
  python render.py --project . --cdp http://127.0.0.1:9333
  python render.py --project . --still 1.2,2.4,3.6
  python render.py --project . --start 8 --duration 4
"""
import argparse
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

try:
    import requests
    import websocket
except ImportError as e:
    sys.exit("pip install requests websocket-client pillow numpy  (" + str(e) + ")")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def find_chrome():
    cands = []
    if sys.platform == "win32":
        cands = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
    elif sys.platform == "darwin":
        cands = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    else:
        cands = ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"]
    for c in cands:
        if os.path.exists(c):
            return c
    for n in ("chrome", "chromium", "chromium-browser", "msedge"):
        p = shutil.which(n)
        if p:
            return p
    return None


class Chrome:
    def __init__(self, cdp=None, chrome=None, width=1920, height=1080):
        self.proc = None
        self.port = None
        if cdp:
            self.base = cdp.rstrip("/")
        else:
            chrome = chrome or find_chrome()
            if not chrome:
                sys.exit("no Chrome found; install Chrome or pass --chrome")
            self.port = free_port()
            prof = tempfile.mkdtemp(prefix="video-flow-chrome-")
            self.profile = prof
            args = [
                chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                "--no-first-run", "--disable-extensions", "--hide-scrollbars",
                f"--remote-debugging-port={self.port}",
                "--remote-allow-origins=*", f"--user-data-dir={prof}",
                f"--window-size={width},{height}", "about:blank",
            ]
            self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.base = f"http://127.0.0.1:{self.port}"
            for _ in range(80):
                try:
                    urllib.request.urlopen(self.base + "/json/version", timeout=1)
                    break
                except Exception:
                    time.sleep(0.25)
            else:
                self.close()
                sys.exit("Chrome did not start (CDP not reachable)")
        self.ws = None
        self.tid = None

    def open(self, url, width, height):
        r = requests.put(self.base + "/json/new?" + requests.utils.quote(url, safe=":/"), timeout=10)
        if r.status_code >= 400:
            r = requests.get(self.base + "/json/new?" + requests.utils.quote(url, safe=":/"), timeout=10)
        info = r.json()
        self.tid = info["id"]
        self.ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60, max_size=100 * 1024 * 1024)
        self.mid = 0
        self.send("Runtime.enable")
        self.send("Emulation.setDeviceMetricsOverride",
                  width=width, height=height, deviceScaleFactor=1, mobile=False)
        time.sleep(0.3)
        self.send("Runtime.evaluate",
                  expression="(async()=>{ if(document.fonts) await document.fonts.ready; return true })()",
                  awaitPromise=True)

    def send(self, method, **params):
        self.mid += 1
        self.ws.send(json.dumps({"id": self.mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.mid:
                return msg

    def eval(self, expr, await_promise=False):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=await_promise)
        return r

    def close(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        if self.tid:
            try:
                requests.get(f"{self.base}/json/close/{self.tid}", timeout=5)
            except Exception:
                pass
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except Exception:
                self.proc.kill()
            shutil.rmtree(getattr(self, "profile", ""), ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--html", default=None)
    ap.add_argument("--timeline", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--size", default=None, help="WxH")
    ap.add_argument("--quality", type=int, default=92)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--still", default=None, help="comma separated seconds; saves PNG")
    ap.add_argument("--motion-blur", type=int, default=1)
    ap.add_argument("--cdp", default=os.environ.get("VIDEO_FLOW_CDP"))
    ap.add_argument("--launch-chrome", action="store_true")
    ap.add_argument("--chrome", default=None)
    args = ap.parse_args()

    root = Path(args.project).resolve() if args.project else Path.cwd()
    html = Path(args.html) if args.html else root / "build" / "index.html"
    tl_path = Path(args.timeline) if args.timeline else root / "timeline.json"
    outdir = Path(args.out) if args.out else root / "frames"
    outdir.mkdir(parents=True, exist_ok=True)
    if not html.exists():
        sys.exit(f"missing html: {html}")
    tl = json.loads(tl_path.read_text(encoding="utf-8")) if tl_path.exists() else {}
    project = json.loads((root / "project.json").read_text(encoding="utf-8")) if (root / "project.json").exists() else {}
    fps = args.fps or int(tl.get("fps") or project.get("fps", 30))
    if args.size:
        w, h = [int(x) for x in args.size.lower().split("x")]
    else:
        w = int(project.get("width", 1920)); h = int(project.get("height", 1080))
    total = float(tl.get("total") or project.get("duration") or 0)

    if args.cdp and not args.launch_chrome:
        ch = Chrome(cdp=args.cdp, width=w, height=h)
    elif args.launch_chrome or not args.cdp:
        ch = Chrome(chrome=args.chrome, width=w, height=h)
    else:
        ch = Chrome(cdp=args.cdp, width=w, height=h)

    try:
        ch.open(html.resolve().as_uri(), w, h)
        # wait for render + READY
        for _ in range(120):
            r = ch.eval("typeof window.render==='function' && (window.READY===undefined || window.READY===true)")
            if r.get("result", {}).get("result", {}).get("value"):
                break
            time.sleep(0.25)
        else:
            diag = ch.eval("JSON.stringify({err:window.__err||null, render:typeof window.render, lib:typeof window.LIB, ready:window.READY, state:document.readyState, html:document.body?document.body.innerHTML.length:0})")
            print("diagnostics:", diag.get("result", {}).get("result", {}).get("value"))
            sys.exit("page did not expose window.render / READY")

        if args.still:
            for s in args.still.split(","):
                t = float(s)
                ch.eval(f"window.render({t})")
                r = ch.eval("document.getElementById('c').toDataURL('image/png')")
                val = r.get("result", {}).get("result", {}).get("value", "")
                p = outdir if outdir.suffix else outdir / f"still_{t:06.2f}.png"
                Path(p).write_bytes(base64.b64decode(val.split(",", 1)[1]))
                print("still", p)
            return

        end = total if args.duration is None else min(total, args.start + args.duration)
        first = int(round(args.start * fps)); last = int(round(end * fps))
        blur = max(1, args.motion_blur)
        t0 = time.time(); done = 0
        for i in range(first, last):
            p = outdir / f"f{i:05d}.jpg"
            if p.exists() and p.stat().st_size > 2000:
                continue
            if blur == 1:
                ch.eval(f"window.render({i / fps})")
                r = ch.eval(f"document.getElementById('c').toDataURL('image/jpeg',{args.quality / 100})")
                val = r.get("result", {}).get("result", {}).get("value", "")
                p.write_bytes(base64.b64decode(val.split(",", 1)[1]))
            else:
                acc = None
                for k in range(blur):
                    tt = i / fps + (k / (blur * fps))
                    ch.eval(f"window.render({tt})")
                    r = ch.eval("document.getElementById('c').toDataURL('image/png')")
                    val = r.get("result", {}).get("result", {}).get("value", "")
                    im = Image.open(__import__("io").BytesIO(base64.b64decode(val.split(",", 1)[1]))).convert("RGB")
                    a = np.asarray(im, dtype=np.float32)
                    acc = a if acc is None else acc + a
                Image.fromarray((acc / blur).astype(np.uint8)).save(p, quality=args.quality)
            done += 1
            if done % 300 == 0:
                el = time.time() - t0
                print(f"{done}/{last - first} frames, {el:.0f}s, {done / max(el, 1e-9):.1f} fps", flush=True)
        print(f"done {done} frames -> {outdir}")
    finally:
        ch.close()


if __name__ == "__main__":
    main()
