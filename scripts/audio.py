#!/usr/bin/env python3
"""Build BGM + SFX + narration mix, duck music, master to target loudness."""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000


def read_wav(path, stereo=False):
    with wave.open(str(path), "rb") as w:
        ch, sw, sr = w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        raise ValueError(f"16-bit wav required: {path}")
    d = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        d = d.reshape(-1, ch)
        d = d if stereo else d.mean(axis=1)
    elif stereo:
        d = np.stack([d, d], axis=1)
    return d, sr


def write_wav(path, data, sr=SR):
    d = np.clip(data, -1, 1)
    ch = 1 if d.ndim == 1 else d.shape[1]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((d * 32767).astype(np.int16).tobytes())


def measure(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
                        "-af", "ebur128=peak=true", "-f", "null", os.devnull],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    i = re.findall(r"I:\s+(-?\d+\.\d+) LUFS", p.stderr)
    tp = re.findall(r"Peak:\s+(-?\d+\.\d+) dBFS", p.stderr)
    return (float(i[-1]) if i else -23.0, float(tp[-1]) if tp else 0.0)


def env_adsr(n, a, d, s, r):
    a = max(1, int(a * SR)); d = max(1, int(d * SR)); r = max(1, int(r * SR))
    e = np.ones(n)
    aa = min(a, n); e[:aa] = np.linspace(0, 1, aa)
    if n > a:
        k = min(d, n - a); e[a:a + k] = np.linspace(1, s, k)
        e[a + k:] = s
    if n > r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def pluck(f, dur, amp=0.1, bright=0.4):
    n = int(dur * SR); tt = np.arange(n) / SR
    y = sum(g * np.sin(2 * np.pi * f * (i + 1) * tt + i) for i, g in enumerate([1, 0.5 * bright, 0.25 * bright]))
    y *= np.exp(-tt * 4.5) * env_adsr(n, 0.004, 0.02, 0.7, 0.1)
    return y * amp / 1.8


def synth_bgm(preset, dur, seed=7):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n)
    rng = np.random.RandomState(seed)

    if preset == "paper":
        bpm, chords = 76, [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63],
                           [196.0, 246.94, 293.66], [164.81, 207.65, 246.94]]
        beat = 60 / bpm
        for ci in range(int(np.ceil(dur / (beat * 8))) + 1):
            st = ci * beat * 8; ln = beat * 8 + 0.5; nn = int(ln * SR); tt = np.arange(nn) / SR
            e = env_adsr(nn, 0.6, 0.4, 0.8, 1.6)
            seg = np.zeros(nn)
            for k, f in enumerate(chords[ci % 4]):
                seg += 0.5 * np.sin(2 * np.pi * f * 0.5 * tt) + 0.25 * np.sin(2 * np.pi * f * tt + k)
            seg *= e * 0.055
            i = int(st * SR); j = min(n, i + nn)
            if j > i: out[i:j] += seg[:j - i]
        for i in range(int(12 / (beat / 2)), int((dur - 6) / (beat / 2))):
            at = i * beat / 2
            ci = int(at / (beat * 8)) % 4
            f = chords[ci][rng.randint(0, 3)] * 2
            if rng.rand() < 0.4:
                s = pluck(f, 0.7, 0.04, 0.25); k = int(at * SR); out[k:k + len(s)] += s[:max(0, n - k)]
        noise = rng.randn(n)
        noise = signal.sosfilt(signal.butter(2, [120, 1800], "band", fs=SR, output="sos"), noise)
        out += noise * 0.004
    else:
        bpm = {"ambient": 72, "tech": 100, "uplift": 112}.get(preset, 92)
        beat = 60 / bpm; bar = beat * 4
        chords = [[110.0, 220.0, 261.63, 329.63], [87.31, 174.61, 220.0, 261.63],
                  [130.81, 261.63, 329.63, 392.0], [98.0, 196.0, 246.94, 293.66]]
        # pad
        for ci in range(int(np.ceil(dur / (bar * 2))) + 1):
            st = ci * bar * 2; ln = bar * 2 + 0.5; nn = int(ln * SR); tt = np.arange(nn) / SR
            e = env_adsr(nn, 1.0, 0.4, 0.75, 1.2)
            seg = np.zeros(nn)
            for k, f in enumerate(chords[ci % 4]):
                det = 1.0 + (k - 1.5) * 0.001
                seg += 0.5 * np.sin(2 * np.pi * f * 0.5 * det * tt) + 0.22 * np.sin(2 * np.pi * f * det * tt + k)
            seg *= e * 0.05
            i = int(st * SR); j = min(n, i + nn)
            if j > i: out[i:j] += seg[:j - i]
        out = signal.sosfilt(signal.butter(2, 1000, "low", fs=SR, output="sos"), out)
        # bass
        for i in range(int(dur / (beat / 2))):
            at = i * beat / 2; ci = int(at / (bar * 2)) % 4
            f = chords[ci][0]
            nn = int(0.4 * SR); tt = np.arange(nn) / SR
            y = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 7) * 0.09
            k = int(at * SR); j = min(n, k + nn)
            if j > k: out[k:j] += y[:j - k]
        # drums
        if preset in ("tech", "uplift"):
            for b in range(int(dur / bar) + 1):
                for q in ((0, 1, 2, 3) if preset == "uplift" else (0, 2)):
                    at = b * bar + q * beat
                    nn = int(0.18 * SR); tt = np.arange(nn) / SR
                    fr = 75 * np.exp(-tt * 20) + 38
                    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt * 16) * 0.12
                    k = int(at * SR); j = min(n, k + nn)
                    if j > k:
                        out[k:j] += y[:j - k]
        for i in range(int(dur / (beat / 2))):
            at = i * beat / 2 + beat / 4
            nn = int(0.05 * SR)
            noise = rng.randn(nn)
            noise = signal.sosfilt(signal.butter(2, 6500, "high", fs=SR, output="sos"), noise)
            noise *= np.exp(-np.arange(nn) / SR * 90) * 0.02
            k = int(at * SR); j = min(n, k + nn)
            if j > k: out[k:j] += noise[:j - k]
        # arp
        for i in range(int(10 / (beat / 2)), int((dur - 6) / (beat / 2))):
            at = i * beat / 2; ci = int(at / (bar * 2)) % 4
            f = chords[ci][1 + rng.randint(0, 3)] * 2
            if rng.rand() < 0.5:
                s = pluck(f, 0.5, 0.035, 0.35)
                k = int(at * SR); j = min(n, k + len(s))
                if j > k:
                    out[k:j] += s[:j - k]

    fade_in = np.clip(t / 4.0, 0, 1)
    fade_out = np.clip((dur - t) / 5.0, 0, 1)
    return out * fade_in * fade_out


def load_music(path, dur):
    tmp = Path(tempfile.gettempdir()) / "video_flow_music.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-ar", str(SR),
                    "-ac", "2", "-c:a", "pcm_s16le", str(tmp)], check=True)
    d, sr = read_wav(tmp, stereo=True)
    n = int(dur * SR)
    if len(d) < n:
        reps = int(np.ceil(n / len(d)))
        d = np.tile(d, (reps, 1))
    return d[:n]


def whoosh(seed=0, dur=0.8):
    n = int(dur * SR); tt = np.arange(n) / SR
    noise = np.random.RandomState(seed).randn(n)
    noise = signal.sosfilt(signal.butter(2, [300, 5000], "band", fs=SR, output="sos"), noise)
    e = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 2
    return noise * e * 0.05


def ding(f=880, dur=0.9):
    n = int(dur * SR); tt = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 2 * tt)
    return y * np.exp(-tt * 4.5) * 0.045


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--no-bgm", action="store_true")
    ap.add_argument("--target-lufs", type=float, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    root = Path(args.project).resolve()
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    tl = json.loads((root / "timeline.json").read_text(encoding="utf-8"))
    total = float(tl["total"])
    dur = total + 0.4
    n = int(dur * SR)

    vo = np.zeros(n)
    env = np.zeros(n)
    for sc in tl["scenes"]:
        if not sc.get("vo"):
            continue
        d, sr = read_wav(root / sc["vo"])
        if sr != SR:
            idx = np.linspace(0, len(d) - 1, int(len(d) * SR / sr))
            d = np.interp(idx, np.arange(len(d)), d)
        d = d / (np.max(np.abs(d)) + 1e-9) * 0.74
        i = int(sc["voStart"] * SR); j = min(n, i + len(d))
        vo[i:j] += d[:j - i]
        env[i:j] = 1.0

    music = np.zeros(n)
    if not args.no_bgm:
        music_file = next((root / "audio" / f for f in ("music.mp3", "music.wav", "music.m4a")
                           if (root / "audio" / f).exists()), None)
        if music_file:
            st = load_music(music_file, dur)
            music = st.mean(axis=1)
        else:
            preset = project.get("music", "ambient")
            if preset != "none":
                music = synth_bgm(preset, dur)

    sfx = np.zeros(n)
    scenes = tl["scenes"]
    script_timed = {}
    st_path = root / "script.timed.json"
    if st_path.exists():
        try:
            stj = json.loads(st_path.read_text(encoding="utf-8"))
            script_timed = {s.get("id"): s.get("sfx") for s in stj.get("scenes", [])}
        except Exception:
            script_timed = {}
    for i, sc in enumerate(scenes):
        if i > 0:
            s = whoosh(seed=i)
            k = max(0, int((sc["start"] - 0.18) * SR)); j = min(n, k + len(s))
            if j > k:
                sfx[k:j] += s[:j - k]
        for ev in (script_timed.get(sc["id"]) or []):
            at = sc["start"] + float(ev.get("at", 0))
            kind = ev.get("kind", "tick")
            seed = sum(ord(c) for c in str(sc["id"])) % 997
            s = ding(ev.get("freq", 880)) if kind == "ding" else whoosh(seed=seed, dur=0.2) if kind == "whoosh" else ding(1500, 0.05)
            k = int(at * SR); j = min(n, k + len(s))
            if j > k:
                sfx[k:j] += s[:j - k]
    sfx *= 0.7

    # smooth duck
    a = 1 - np.exp(-1 / (SR * 0.08))
    y = signal.lfilter([a], [1, -(1 - a)], env)
    b = 1 - np.exp(-1 / (SR * 0.30))
    duck = signal.lfilter([b], [1, -(1 - b)], y[::-1])[::-1]
    duck = np.clip(1.0 - 0.72 * duck, 0.26, 1.0)

    mix = vo + music * duck + sfx
    pk = float(np.max(np.abs(mix)))
    if pk > 0.95:
        mix /= pk * 1.02

    tmp = root / "audio" / "_mix_raw.wav"
    write_wav(tmp, mix, SR)
    I0, TP0 = measure(tmp)
    target = args.target_lufs if args.target_lufs is not None else float(project.get("target_lufs", -14.2))
    gain = 10 ** ((target - I0) / 20)
    mix = mix * gain

    def soft_limit(x, ceil=0.80):
        a = np.abs(x)
        over = a > ceil
        x[over] = np.sign(x[over]) * (ceil + (0.995 - ceil) * np.tanh((a[over] - ceil) / (0.995 - ceil)))
        return x

    mix = soft_limit(mix)
    tmp2 = root / "audio" / "_mix_norm.wav"
    write_wav(tmp2, mix, SR)
    I1, TP1 = measure(tmp2)
    # leave ~1.5 dB headroom for AAC intersample overshoot
    if TP1 > -2.0:
        mix *= 10 ** ((-2.0 - TP1) / 20)

    out = Path(args.out) if args.out else root / "audio" / "mix.wav"
    write_wav(out, mix, SR)
    I2, TP2 = measure(out)
    print(f"raw I={I0:.2f} TP={TP0:.2f}  ->  master I={I2:.2f} TP={TP2:.2f}  gain={20*np.log10(gain):+.2f} dB")
    print("wrote", out)


if __name__ == "__main__":
    main()
