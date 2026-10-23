#!/usr/bin/env python3
"""Scaffold a video-flow project from templates."""
import argparse
import json
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TPL = SKILL / "templates"

FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def main():
    ap = argparse.ArgumentParser(description="Create a new video-flow project")
    ap.add_argument("--dir", required=True, help="project directory")
    ap.add_argument("--title", default="未命名视频")
    ap.add_argument("--format", default="16:9", choices=list(FORMATS))
    ap.add_argument("--style", default="silicon")
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    ap.add_argument("--music", default="ambient", choices=["ambient", "tech", "paper", "uplift", "none"])
    ap.add_argument("--language", default="zh")
    ap.add_argument("--script", default=None, help="optional script.json to copy")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    root = Path(args.dir).resolve()
    if root.exists() and any(root.iterdir()) and not args.force:
        sys.exit(f"directory not empty: {root} (use --force)")
    for sub in ["source", "audio/vo", "audio/vo_human", "build/scenes", "frames", "out", "qa"]:
        (root / sub).mkdir(parents=True, exist_ok=True)

    # style
    style_file = TPL / "styles" / f"{args.style}.json"
    if not style_file.exists():
        sys.exit(f"unknown style: {args.style}; available: {[p.stem for p in (TPL/'styles').glob('*.json')]}")
    style = json.loads(style_file.read_text(encoding="utf-8"))
    (root / "build" / "theme.js").write_text(
        "window.STYLE = " + json.dumps(style, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8"
    )
    w, h = FORMATS[args.format]
    (root / "build" / "format.js").write_text(
        "window.FORMAT = " + json.dumps({"name": args.format, "w": w, "h": h, "portrait": h > w},
                                        ensure_ascii=False) + ";\n", encoding="utf-8"
    )
    brand = {"enabled": False, "name": "", "footer": ""}
    (root / "build" / "brand.js").write_text("window.BRAND = " + json.dumps(brand, ensure_ascii=False) + ";\n",
                                             encoding="utf-8")

    # build template
    for name in ["index.html", "lib.js", "scenes.js"]:
        src = TPL / "build" / name
        if src.exists():
            shutil.copy2(src, root / "build" / name)
    custom = TPL / "build" / "custom.js"
    (root / "build" / "custom.js").write_text(
        custom.read_text(encoding="utf-8") if custom.exists() else "window.CUSTOM = window.CUSTOM || {};\n",
        encoding="utf-8",
    )

    # script
    if args.script:
        shutil.copy2(args.script, root / "script.json")
    else:
        shutil.copy2(TPL / "script.example.json", root / "script.json")

    w, h = FORMATS[args.format]
    project = {
        "title": args.title,
        "subtitle": "",
        "language": args.language,
        "format": args.format,
        "width": w,
        "height": h,
        "fps": 30,
        "style": args.style,
        "voice": {"engine": "edge", "name": args.voice, "rate": "+3%", "pitch": "+0Hz"},
        "music": args.music,
        "target_lufs": -14.2,
        "brand": {"enabled": False, "name": "", "footer": ""},
        "brief": {"audience": "", "goals": [], "misconception": "", "facts_source": []},
    }
    (root / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "storyboard.md").write_text(
        "# Storyboard\n\n> 先填这张表，再写场景代码。\n\n"
        "| # | 时间 | 镜头类型 | 讲什么（一句话） | 画面/视觉 | 旁白 | 考点/目标 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| 0 |  | title |  |  |  |  |\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        f"# {args.title}\n\n"
        f"- format: {args.format} ({w}x{h})\n- style: {args.style}\n- voice: {args.voice}\n\n"
        "```bash\n"
        "python ../../scripts/tts.py --project .\n"
        "python ../../scripts/timeline.py --project .\n"
        "python ../../scripts/render.py --project . --launch-chrome\n"
        "python ../../scripts/audio.py --project .\n"
        "python ../../scripts/srt.py --project .\n"
        "python ../../scripts/encode.py --project .\n"
        "python ../../scripts/qa.py --project .\n"
        "```\n",
        encoding="utf-8",
    )
    print(f"created {root}")
    print("next: edit script.json, then run scripts/tts.py, timeline.py, render.py")


if __name__ == "__main__":
    main()
