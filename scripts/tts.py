#!/usr/bin/env python3
"""Generate narration WAVs for script.json scenes.

Engines:
  edge   : Microsoft Edge neural TTS (needs network, 24 kHz source)
  sapi   : Windows offline voice (lower quality)
  from-dir: use human recordings in audio/vo_human/<id>.wav
  voxcpm : local VoxCPM2 2B (48 kHz, CUDA, Apache-2.0; optional 4.7 GB download)

Output: audio/vo/<id>.wav  (48 kHz mono, lightly processed)
"""
import argparse
import asyncio
import json
import os
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

# Local 48 kHz neural TTS (VoxCPM2) is already clean; use lighter processing.
PROCESS_LOCAL = (
    "aresample=resampler=soxr:osr=48000,"
    "highpass=f=60,"
    "equalizer=f=180:t=q:w=1:g=0.8,"
    "equalizer=f=3200:t=q:w=1.2:g=0.6,"
    "acompressor=threshold=-20dB:ratio=1.4:attack=8:release=150"
)
PROCESS_LOCAL_WITH_ROOM = PROCESS_LOCAL + ",aecho=0.85:0.7:25:0.04"



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


def process_wav(src, dst, clean=True, room=False, local=False):
    if local:
        af = PROCESS_LOCAL_WITH_ROOM if (clean and room) else (PROCESS_LOCAL if clean else "aresample=resampler=soxr:osr=48000")
    else:
        af = PROCESS_WITH_ROOM if (clean and room) else (PROCESS if clean else "aresample=resampler=soxr:osr=48000")
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(src),
        "-af", af, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(dst)
    ], check=True)


def apply_atempo(src, dst, tempo):
    """Slow/speed up without changing pitch (0.5–2.0 per atempo stage)."""
    if abs(tempo - 1.0) < 1e-6:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ar", "48000",
                        "-ac", "1", "-c:a", "pcm_s16le", str(dst)], check=True)
        return
    filters, t = [], float(tempo)
    while t < 0.5:
        filters.append("atempo=0.5"); t /= 0.5
    while t > 2.0:
        filters.append("atempo=2.0"); t /= 2.0
    filters.append(f"atempo={t:.6f}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", ",".join(filters),
                    "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(dst)], check=True)


def load_voxcpm(model_dir, device="cuda"):
    """Load VoxCPM2 once; call from the main process, not per scene."""
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from voxcpm import VoxCPM
    if not model_dir:
        sys.exit("voxcpm engine needs --model-dir (or project.json voice.model_dir)")
    model_dir = Path(model_dir)
    if not model_dir.is_dir():
        sys.exit(f"VoxCPM2 model dir not found: {model_dir}\n"
                 "Download: modelscope download --model OpenBMB/VoxCPM2 --local_dir models/VoxCPM2")
    print(f"loading VoxCPM2 from {model_dir} ...", flush=True)
    model = VoxCPM.from_pretrained(str(model_dir), load_denoiser=False, optimize=False, device=device)
    print(f"VoxCPM2 ready, sample_rate={model.tts_model.sample_rate}", flush=True)
    return model


def synth_voxcpm(model, text, ref_audio, ref_text, control, timesteps, cfg, out_wav):
    """Synthesize one scene with VoxCPM2 (voice design or reference cloning)."""
    import soundfile as sf
    if control and not ref_audio:
        text = f"({control}){text}"
    kwargs = dict(text=text, inference_timesteps=int(timesteps), cfg_value=float(cfg),
                  normalize=False, retry_badcase=True)
    if ref_audio:
        kwargs["reference_wav_path"] = str(ref_audio)
        if ref_text:
            kwargs["prompt_wav_path"] = str(ref_audio)
            kwargs["prompt_text"] = ref_text
    wav = model.generate(**kwargs)
    sf.write(str(out_wav), wav, model.tts_model.sample_rate)
    return out_wav



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
    ap.add_argument("--engine", default=None, choices=["edge", "sapi", "from-dir", "voxcpm"],
                    help="voxcpm = local VoxCPM2, 48 kHz, needs --model-dir")
    ap.add_argument("--voice", default=None)
    ap.add_argument("--rate", default=None)
    ap.add_argument("--pitch", default=None)
    ap.add_argument("--from-dir", default=None, help="folder with <id>.wav human recordings")
    ap.add_argument("--model-dir", default=None, help="local VoxCPM2 model directory")
    ap.add_argument("--ref-audio", default=None, help="10–30 s clean reference voice for cloning")
    ap.add_argument("--ref-text", default=None, help="exact transcript of --ref-audio")
    ap.add_argument("--control", default=None,
                    help="voice-design instruction in natural language (optional)")
    ap.add_argument("--device", default="cuda", help="voxcpm device: cuda / cpu / auto")
    ap.add_argument("--timesteps", type=int, default=10, help="VoxCPM2 diffusion steps (default 10)")
    ap.add_argument("--cfg", type=float, default=2.0, help="VoxCPM2 CFG value (default 2.0)")
    ap.add_argument("--atempo", type=float, default=1.0,
                    help="tempo factor; 0.95 = 5%% slower without pitch shift")
    ap.add_argument("--clean", dest="clean", action="store_true", default=True)
    ap.add_argument("--no-clean", dest="clean", action="store_false")
    ap.add_argument("--room", action="store_true", help="add very short room reflection")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    root = Path(args.project).resolve()
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    script = json.loads((root / "script.json").read_text(encoding="utf-8"))
    v = project.get("voice", {})
    engine = args.engine or v.get("engine", "edge")
    if args.from_dir and not args.engine:
        engine = "from-dir"
    voice = args.voice or v.get("name", "zh-CN-XiaoxiaoNeural")
    rate = args.rate or v.get("rate", "+3%")
    pitch = args.pitch or v.get("pitch", "+0Hz")
    model_dir = args.model_dir or v.get("model_dir") or os.environ.get("VOXCPM_MODEL_DIR", "")
    ref_audio = args.ref_audio or v.get("ref_audio")
    ref_text = args.ref_text or v.get("ref_text")
    control = args.control or v.get("control")
    atempo = float(args.atempo if args.atempo != 1.0 else v.get("atempo", 1.0))
    device = args.device or v.get("device", "cuda")

    outdir = root / "audio" / "vo"
    outdir.mkdir(parents=True, exist_ok=True)
    fromdir = Path(args.from_dir) if args.from_dir else root / "audio" / "vo_human"

    if ref_audio:
        ref_audio = Path(ref_audio)
        if not ref_audio.is_absolute():
            ref_audio = (root / ref_audio).resolve()
        if not ref_audio.exists():
            sys.exit(f"reference audio not found: {ref_audio}")
        if not ref_text:
            txt = root / "audio" / "voice_ref.txt"
            if txt.exists():
                ref_text = txt.read_text(encoding="utf-8").strip()
        if not ref_text:
            print("warn: no --ref-text; cloning will use reference audio only (lower similarity)", flush=True)

    scenes = [s for s in script.get("scenes", []) if (s.get("vo") or "").strip()]
    if not scenes:
        print("no scenes with 'vo'; nothing to synthesize")
        return

    model = None
    if engine == "voxcpm":
        if not model_dir:
            sys.exit("voxcpm engine needs --model-dir (or project.json voice.model_dir / VOXCPM_MODEL_DIR)")
        model = load_voxcpm(model_dir, device=device)

    for sc in scenes:
        sid = sc["id"]
        dst = outdir / f"{sid}.wav"
        if dst.exists() and not args.force:
            print(f"skip {sid} (exists)")
            continue
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / "raw.wav"
            if engine == "from-dir":
                src = fromdir / f"{sid}.wav"
                if not src.exists():
                    sys.exit(f"missing human recording: {src}")
                process_wav(src, dst, clean=args.clean, room=args.room)
            elif engine == "sapi":
                synth_sapi(sc["vo"], raw)
                process_wav(raw, dst, clean=args.clean, room=args.room)
            elif engine == "voxcpm":
                synth_voxcpm(model, sc["vo"], ref_audio, ref_text, control,
                             args.timesteps, args.cfg, raw)
                if abs(atempo - 1.0) > 1e-6:
                    paced = Path(td) / "paced.wav"
                    apply_atempo(raw, paced, atempo)
                    raw = paced
                process_wav(raw, dst, clean=args.clean, room=args.room, local=True)
            else:
                raw = synth_edge(sc["vo"], voice, rate, pitch, td)
                process_wav(raw, dst, clean=args.clean, room=args.room)
        print(f"wrote {dst}")
    print("done")


if __name__ == "__main__":
    main()
