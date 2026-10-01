"""Tests for scripts/research/md_to_pdf.py — markdown preprocessing only.

Rendering itself shells out to pandoc/weasyprint and is not exercised here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "research"))

from md_to_pdf import first_h1, strip_placeholder_title


def test_placeholder_dropped_when_real_title_follows_directly():
    md = "# 报告\n# 万科A 深度研究报告\n\n正文\n"
    assert strip_placeholder_title(md) == "# 万科A 深度研究报告\n\n正文\n"


def test_placeholder_dropped_when_real_title_follows_after_blank_line():
    md = "# 报告\n\n# 中熔电气 深度研究报告\n正文\n"
    assert strip_placeholder_title(md) == "# 中熔电气 深度研究报告\n正文\n"


def test_lone_placeholder_kept_when_no_real_title_follows():
    md = "# 报告\n\n正文\n"
    assert strip_placeholder_title(md) == md


def test_real_title_first_is_untouched():
    md = "# 恒逸石化 深度研究报告\n\n# 报告\n"
    assert strip_placeholder_title(md) == md


def test_first_h1_skips_body_text():
    assert first_h1("intro\n## sub\n# Title here\n") == "Title here"
