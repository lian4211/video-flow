#!/usr/bin/env python3
"""Ingest a source into source/source.md + source/meta.json (+ page images when needed)."""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent


def has(mod):
    import importlib.util
    return importlib.util.find_spec(mod) is not None


def clean_text(s):
    return (s or "").encode("utf-8", "replace").decode("utf-8")


def text_ok(s):
    if not s or len(s.strip()) < 20:
        return False
    bad = s.count("\ufffd") + s.count("\\ud")
    return bad / max(1, len(s)) < 0.02


def pdf_extract(path, out):
    if not has("pypdf"):
        sys.exit("pip install pypdf")
    from pypdf import PdfReader
    r = PdfReader(str(path))
    pages = []
    for i, p in enumerate(r.pages, 1):
        try:
            t = clean_text(p.extract_text() or "")
        except Exception as e:
            t = f"[extract error: {e}]"
        pages.append((i, t))
    good = sum(1 for _, t in pages if text_ok(t))
    meta = {"type": "pdf", "pages": len(pages), "text_pages": good, "ocr_needed": good < len(pages) * 0.6}
    body = []
    for i, t in pages:
        body.append(f"\n\n--- page {i} ---\n{t}")
    (out / "source.md").write_text("".join(body).strip(), encoding="utf-8")
    if meta["ocr_needed"]:
        render_pdf_pages(path, out)
    return meta


def render_pdf_pages(path, out):
    pages = out / "pages"; pages.mkdir(exist_ok=True)
    if has("fitz"):
        import fitz
        doc = fitz.open(str(path))
        for i, page in enumerate(doc, 1):
            pix = page.get_pixmap(dpi=150)
            pix.save(str(pages / f"page-{i:02d}.png"))
        return
    if sys.platform == "win32":
        ps = SKILL / "scripts" / "pdf_to_png.ps1"
        if ps.exists():
            subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", str(ps), "-PdfPath", str(path), "-OutDir", str(pages)], check=False)
            return
    print("WARN: cannot rasterize PDF. Install pymupdf or poppler (`pdftoppm`) and rerun.")


def pptx_extract(path, out):
    if not has("pptx"):
        sys.exit("pip install python-pptx")
    from pptx import Presentation
    prs = Presentation(str(path))
    lines = []
    for i, slide in enumerate(prs.slides, 1):
        lines.append(f"\n\n--- slide {i} ---")
        for shape in slide.shapes:
            if shape.has_text_frame:
                t = shape.text_frame.text.strip()
                if t:
                    lines.append(t)
            if shape.has_table:
                for row in shape.table.rows:
                    lines.append(" | ".join(c.text.strip() for c in row.cells))
        try:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                lines.append(f"[notes] {notes}")
        except Exception:
            pass
    (out / "source.md").write_text("\n".join(lines).strip(), encoding="utf-8")
    return {"type": "pptx", "slides": len(prs.slides)}


def docx_extract(path, out):
    if not has("docx"):
        sys.exit("pip install python-docx")
    import docx
    d = docx.Document(str(path))
    lines = []
    for p in d.paragraphs:
        if p.text.strip():
            lines.append(p.text.strip())
    for t in d.tables:
        for row in t.rows:
            lines.append(" | ".join(c.text.strip() for c in row.cells))
    (out / "source.md").write_text("\n".join(lines), encoding="utf-8")
    return {"type": "docx", "paragraphs": len(d.paragraphs)}


def url_extract(url, out):
    if not has("requests") or not has("lxml"):
        sys.exit("pip install requests lxml")
    import requests
    from lxml import html
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 video-flow"})
    r.raise_for_status()
    doc = html.fromstring(r.text)
    for bad in doc.xpath("//script|//style|//nav|//footer|//header"):
        bad.getparent().remove(bad)
    title = (doc.xpath("//title/text()") or [""])[0].strip()
    chunks = []
    for el in doc.xpath("//h1|//h2|//h3|//p|//li|//table//tr"):
        t = " ".join(el.text_content().split())
        if t:
            chunks.append(t)
    (out / "source.md").write_text(f"# {title}\n\n" + "\n\n".join(chunks), encoding="utf-8")
    return {"type": "url", "url": url, "title": title, "fetched": True}


def video_extract(path, out, frames):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=width,height,r_frame_rate,codec_name",
                        "-of", "json", str(path)], capture_output=True, text=True)
    info = json.loads(p.stdout or "{}")
    dur = float(info.get("format", {}).get("duration", 0))
    pages = out / "pages"; pages.mkdir(exist_ok=True)
    step = max(1.0, dur / max(1, frames))
    for i in range(frames):
        t = i * step
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(path),
                        "-frames:v", "1", str(pages / f"frame-{i:03d}.png")], check=False)
    (out / "source.md").write_text(f"[video] {path.name}\nduration: {dur:.1f}s\n", encoding="utf-8")
    return {"type": "video", "duration": dur, **info.get("format", {})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None)
    ap.add_argument("--text", default=None)
    ap.add_argument("--out", default="source")
    ap.add_argument("--frames", type=int, default=12)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    if args.text:
        (out / "source.md").write_text(args.text, encoding="utf-8")
        meta = {"type": "text"}
    elif not args.input:
        sys.exit("provide --input or --text")
    else:
        p = args.input
        if p.startswith("http://") or p.startswith("https://"):
            meta = url_extract(p, out)
        else:
            path = Path(p)
            if not path.exists():
                sys.exit(f"not found: {p}")
            ext = path.suffix.lower()
            if ext == ".pdf":
                meta = pdf_extract(path, out)
            elif ext == ".pptx":
                meta = pptx_extract(path, out)
            elif ext == ".docx":
                meta = docx_extract(path, out)
            elif ext in (".md", ".txt", ".markdown"):
                shutil.copy2(path, out / "source.md")
                meta = {"type": "text", "file": path.name}
            elif ext in (".mp4", ".mov", ".mkv", ".webm", ".avi"):
                meta = video_extract(path, out, args.frames)
            else:
                sys.exit(f"unsupported: {ext}")
    meta["source_md"] = str((out / "source.md").relative_to(out.parent)).replace("\\", "/")
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print("wrote", out / "source.md")


if __name__ == "__main__":
    main()
