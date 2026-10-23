#!/usr/bin/env python3
"""Generate narration WAVs for script.json scenes.

Engines:
  edge   : Microsoft Edge neural TTS (needs network, 24 kHz source)
  sapi   : Windows offline voice (lower quality)
  from-dir: use human recordings in audio/vo_human/<id>.wav

Output: audio/vo/<id>.wav  (48 kHz mono, lightly processed)
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

PROCESS = (
    "aresample=resampler=soxr:osr=48000,"
    "highpass=f=75,"
    "equalizer=f=180:t=q:w=1:g=1.2,"
    "equalizer=f=3200:t=q:w=1.2:g=0.8,"
    "acompressor=threshold=-20dB:ratio=1.8:attack=8:release=140"
)
PROCESS_WITH_ROOM = PROCESS + ",aecho=0.8:0.7:22:0.05"


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        ch, sw, sr = w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        raise ValueError(f"only 16-bit wav supported: {path}")
    d = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        d = d.reshape(-1, ch).mean(axis=1)
    return d, sr


def write_wav(path, data, sr=48000):
    d = np.clip(data, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((d * 32767).astype(np.int16).tobytes())


def split_text(text, limit=180):
    parts = re.split(r"(?<=[。！？；\n])", text)
    chunks, buf = [], ""
    for p in parts:
        if not p.strip():
            continue
        if len(buf) + len(p) <= limit:
            buf += p
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks


def process_wav(src, dst, clean=True, room=False):
    af = PROCESS_WITH_ROOM if (clean and room) else (PROCESS if clean else "aresample=resampler=soxr:osr=48000")
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(src),
        "-af", af, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(dst)
    ], check=True)


async def edge_tts_one(text, voice, rate, pitch, out_mp3):
    import edge_tts
    com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await com.save(str(out_mp3))


def synth_edge(text, voice, rate, pitch, tmpdir):
    import edge_tts  # noqa: F401
    chunks = split_text(text)
    wavs = []
    for i, chunk in enumerate(chunks):
        mp3 = Path(tmpdir) / f"c{i}.mp3"
        asyncio.run(edge_tts_one(chunk, voice, rate, pitch, mp3))
        wav = Path(tmpdir) / f"c{i}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-ar", "48000",
                        "-ac", "1", "-c:a", "pcm_s16le", str(wav)], check=True)
        wavs.append(wav)
    if len(wavs) == 1:
        return wavs[0]
    # concatenate with 120 ms silence
    data = []
    for i, w in enumerate(wavs):
        d, sr = read_wav(w)
        data.append(d)
        if i != len(wavs) - 1:
            data.append(np.zeros(int(0.12 * sr), dtype=np.float32))
    out = Path(tmpdir) / "joined.wav"
    write_wav(out, np.concatenate(data), 48000)
    return out


def synth_sapi(text, out_wav):
    if sys.platform != "win32":
        sys.exit("sapi engine is Windows-only")
    ps = Path(tempfile.gettempdir()) / "video_flow_tts.ps1"
    payload = text.replace('"', '`"')
    script = (
        "Add-Type -AssemblyName System.Speech\n"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
        "$s.Rate = 1\n"
        f'$s.SetOutputToWaveFile("{out_wav}")\n'
        f'$s.Speak("{payload}")\n'
        "$s.Dispose()\n"
    )
    ps.write_text(script, encoding="utf-8-sig")
    subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--engine", default="edge", choices=["edge", "sapi", "from-dir"])
    ap.add_argument("--voice", default=None)
    ap.add_argument("--rate", default=None)
    ap.add_argument("--pitch", default=None)
    ap.add_argument("--from-dir", default=None, help="folder with <id>.wav human recordings")
    ap.add_argument("--clean", dest="clean", action="store_true", default=True)
    ap.add_argument("--no-clean", dest="clean", action="store_false")
    ap.add_argument("--room", action="store_true", help="add very short room reflection")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    root = Path(args.project).resolve()
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    script = json.loads((root / "script.json").read_text(encoding="utf-8"))
    v = project.get("voice", {})
    voice = args.voice or v.get("name", "zh-CN-XiaoxiaoNeural")
    rate = args.rate or v.get("rate", "+3%")
    pitch = args.pitch or v.get("pitch", "+0Hz")

    outdir = root / "audio" / "vo"
    outdir.mkdir(parents=True, exist_ok=True)
    fromdir = Path(args.from_dir) if args.from_dir else root / "audio" / "vo_human"

    scenes = [s for s in script.get("scenes", []) if (s.get("vo") or "").strip()]
    if not scenes:
        print("no scenes with 'vo'; nothing to synthesize")
        return

    for sc in scenes:
        sid = sc["id"]
        dst = outdir / f"{sid}.wav"
        if dst.exists() and not args.force:
            print(f"skip {sid} (exists)")
            continue
        with tempfile.TemporaryDirectory() as td:
            if args.engine == "from-dir":
                src = fromdir / f"{sid}.wav"
                if not src.exists():
                    sys.exit(f"missing human recording: {src}")
                process_wav(src, dst, clean=args.clean, room=args.room)
            elif args.engine == "sapi":
                raw = Path(td) / "sapi.wav"
                synth_sapi(sc["vo"], raw)
                process_wav(raw, dst, clean=args.clean, room=args.room)
            else:
                raw = synth_edge(sc["vo"], voice, rate, pitch, td)
                process_wav(raw, dst, clean=args.clean, room=args.room)
        print(f"wrote {dst}")
    print("done")


if __name__ == "__main__":
    main()
