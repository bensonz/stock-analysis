#!/usr/bin/env python3
"""Render a markdown report (e.g. reports/*/…-deep.md) to a print-ready PDF.

    python3 scripts/research/md_to_pdf.py reports/000002-万科Ａ/000002-2026-10-01-deep.md
    python3 scripts/research/md_to_pdf.py a.md b.md          # several at once
    python3 scripts/research/md_to_pdf.py a.md -o /tmp/a.pdf

Pipeline: pandoc (gfm → standalone HTML with the CSS below) → weasyprint.
Chosen over pandoc+xelatex because weasyprint picks up the macOS CJK system
fonts (PingFang SC) with no LaTeX font setup. Both are external CLIs
(`brew install pandoc weasyprint`), not pip deps — the pipeline never runs this.

Output defaults to the .md path with a .pdf suffix. reports/ is git-ignored,
so the PDF stays local.
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CSS = """
@page { size: A4; margin: 18mm 16mm;
  @bottom-center { content: counter(page) " / " counter(pages); font-size: 9pt; color: #888; } }
body { font-family: "PingFang SC", "Hiragino Sans GB", "Songti SC", sans-serif;
  font-size: 10.5pt; line-height: 1.6; color: #222; }
h1 { font-size: 18pt; border-bottom: 2px solid #333; padding-bottom: 4px; }
h2 { font-size: 14pt; border-bottom: 1px solid #ccc; padding-bottom: 2px; margin-top: 1.4em; }
h3 { font-size: 12pt; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: .8em 0; page-break-inside: auto; }
th, td { border: 1px solid #bbb; padding: 4px 6px; vertical-align: top; }
th { background: #f0f0f0; }
tr { page-break-inside: avoid; }
td:first-child, th:first-child { white-space: nowrap; }
code { font-family: Menlo, monospace; font-size: 9pt; background: #f5f5f5; padding: 0 2px; }
pre { background: #f5f5f5; padding: 8px; white-space: pre-wrap; font-size: 8.5pt; }
blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 10px; color: #555; }
a { color: #1a5fb4; text-decoration: none; word-break: break-all; }
"""

_H1 = re.compile(r"^#\s+(.*\S)\s*$")


def strip_placeholder_title(md: str) -> str:
    """Drop a leading generic `# 报告` heading when the real H1 follows it.

    Some deep reports open with `# 报告` and then the actual title H1, which
    renders as two stacked titles. Only removed when the next non-blank line
    is itself an H1 — a lone `# 报告` is the only title and stays.
    """
    lines = md.splitlines(keepends=True)
    if not lines or _H1.match(lines[0]) is None or _H1.match(lines[0]).group(1) != "报告":
        return md
    rest = lines[1:]
    nxt = next((ln for ln in rest if ln.strip()), "")
    if _H1.match(nxt) is None:
        return md
    return "".join(rest).lstrip("\n")


def first_h1(md: str) -> str | None:
    for ln in md.splitlines():
        m = _H1.match(ln)
        if m:
            return m.group(1)
    return None


def render(md_path: Path, pdf_path: Path) -> None:
    md = strip_placeholder_title(md_path.read_text(encoding="utf-8"))
    title = first_h1(md) or md_path.stem
    with tempfile.TemporaryDirectory() as tmp:
        css = Path(tmp) / "report.css"
        css.write_text(CSS, encoding="utf-8")
        html = Path(tmp) / "report.html"
        subprocess.run(
            ["pandoc", "-f", "gfm", "-t", "html5", "-s",
             "--metadata", f"pagetitle={title}",
             "--css", str(css), "--embed-resources", "-o", str(html)],
            input=md, text=True, check=True,
        )
        # weasyprint's stderr is mostly harmless font-subsetting chatter
        # ("CFF FDArray keys ignored"); real failures surface via check=True.
        subprocess.run(["weasyprint", str(html), str(pdf_path)],
                       check=True, stderr=subprocess.DEVNULL)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("inputs", nargs="+", type=Path, help="markdown file(s)")
    ap.add_argument("-o", "--output", type=Path,
                    help="output PDF path (single input only; default: <input>.pdf)")
    args = ap.parse_args()

    missing = [t for t in ("pandoc", "weasyprint") if shutil.which(t) is None]
    if missing:
        sys.exit(f"missing tool(s): {', '.join(missing)} — brew install {' '.join(missing)}")
    if args.output and len(args.inputs) > 1:
        sys.exit("--output only works with a single input")

    for md_path in args.inputs:
        if not md_path.is_file():
            sys.exit(f"not a file: {md_path}")
        pdf_path = args.output or md_path.with_suffix(".pdf")
        render(md_path, pdf_path)
        print(pdf_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
