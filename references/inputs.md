# Inputs：把源材料变成可讲的内容

## 1. 支持的类型与命令

```bash
python scripts/ingest.py --input source.pdf --out source/
python scripts/ingest.py --input slides.pptx --out source/
python scripts/ingest.py --input notes.docx --out source/
python scripts/ingest.py --input article.md --out source/
python scripts/ingest.py --input https://example.com/post --out source/
python scripts/ingest.py --input clip.mp4 --out source/ --frames 12
python scripts/ingest.py --text "一句话主题或大纲" --out source/
```

输出：
```
source/
  source.md        # 纯文本（保留标题层级/页码标记）
  meta.json        # 类型、页数、时长、来源 URL、抽取方式
  pages/page-*.png # PDF 扫描件/PPT 关键页/视频抽帧（可选）
```

## 2. PDF

1. 先用 `pypdf` 抽文字；
2. 如果出现大量 `�`、孤立代理字符（`\ud83d`）或空文本 → 判定为**字体无 ToUnicode / 扫描件**；
3. 兜底：
   - 有 `pymupdf`：`fitz` 直接渲染每页 PNG；
   - Windows 无 pymupdf：调用 `scripts/pdf_to_png.ps1`（WinRT）渲染；
   - 其他系统：`pdftoppm`（poppler）或提示用户安装 poppler；
4. 把 `pages/*.png` 交给模型“看页”，不要硬猜乱码文字；
5. 在 `source/meta.json` 标注 `"ocr_needed": true`，交付时说明哪些页是看图整理的。

> 经验：WPS 导出的中文 PDF 常见“文字层损坏、画面正常”，直接 OCR/看图比修字体快。

## 3. PPTX

- 逐页抽 `slide.shapes.text`（标题/正文/表格）+ `slide.notes_slide.notes_text`；
- 图片型幻灯片（整页截图）单独导出为 `pages/slide-XX.png`；
- 保留页码，方便 `script.json` 的 `sources` 引用。

## 4. DOCX / Markdown / TXT

- DOCX：段落 + 表格 + 标题样式；图片导出到 `source/images/`；
- Markdown/TXT：复制并解析标题层级；
- 注意去掉页眉页脚/目录/重复水印。

## 5. 网页

- `requests` 抓 HTML，`lxml` 去脚本/样式，保留 `<h1-h3>/<p>/<li>/<table>`；
- 保留 canonical URL 与抓取时间；
- 登录墙/JS 渲染页 → 让用户保存为 PDF/MHTML 再喂。

## 6. 视频

- `ffprobe` 拿时长/分辨率/帧率/音轨；
- 每 N 秒抽 1 帧到 `pages/`，让模型判断结构/风格；
- 没有 ASR 时不要假装听懂了内容：只提取“画面结构/字幕截图”，内容让用户补文字稿。

## 7. 内容提炼（给模型的任务）

读 `source/source.md` 后输出：
1. 一句话主旨；
2. 3–6 个必须保留的事实/公式/数字（带来源页码）；
3. 最容易被误解的 1 个点；
4. 建议的教学结构（因果链/问题-解法/误区-纠正/时间线）；
5. 建议删掉的冗余（目录、致谢、重复例子）。

写进 `storyboard.md` 顶部，再开始分镜。

## 8. 事实核查

- 每个数字/公式/年份在 `script.json` 的 `sources` 里写来源；
- 源材料没有的，不要补；必须补的标 `[待核实]`；
- 交付时输出“事实清单 + 来源 + 待核实项”。
