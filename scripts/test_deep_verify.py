"""Unit tests for deep_verify — extraction, verification, pipeline (no network)."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import deep_verify as dv


def _kinds(claims):
    return [c["kind"] for c in claims]


def _naked_texts(claims):
    return [c["numbers"][0] for c in claims if c["kind"] == "naked"]


# --------------------------------------------------------------------------- #
# Linked / internal extraction
# --------------------------------------------------------------------------- #
def test_extract_linked_claim_with_numbers():
    md = "归母净利润[43–47.7亿元（+62%–80%）](https://finance.example.com/a1)创新高。"
    claims = dv.extract_claims(md)
    linked = [c for c in claims if c["kind"] == "linked"]
    assert len(linked) == 1
    assert linked[0]["url"] == "https://finance.example.com/a1"
    assert any("43" in n for n in linked[0]["numbers"])
    assert not [c for c in claims if c["kind"] == "naked"]


def test_digit_free_link_creates_no_claim_but_covers_url():
    md = "详见[公司公告](https://static.example.com/2026/07/doc99.pdf)。"
    claims = dv.extract_claims(md)
    assert claims == []  # URL digits must not be flagged naked


def test_extract_internal_tag():
    md = "技术面上，RPS60=91.82〖内部数据〗，动量强劲。"
    claims = dv.extract_claims(md)
    internal = [c for c in claims if c["kind"] == "internal"]
    assert len(internal) == 1
    assert any("91.82" in n for n in internal[0]["numbers"])
    assert not [c for c in claims if c["kind"] == "naked"]


# --------------------------------------------------------------------------- #
# Allowlist: what needs NO citation
# --------------------------------------------------------------------------- #
def test_allowlist_passes():
    md = (
        "# 比音勒芬（002832.SZ）深度研究报告 · 评级 4/5\n"
        "2025年、2026Q1、2011–2025年，8月29日中报。\n"
        "### 3. 风险提示\n"
        "1. 第一条\n"
        "近1月、5个交易日，MA250与RPS60的定义，RPS≥80动量门槛。\n"
    )
    claims = dv.extract_claims(md)
    assert claims == [], f"false positives: {[(c['kind'], c['numbers']) for c in claims]}"


def test_real_figures_are_flagged():
    md = (
        "从5000元/件降级至1000元/件。营收43.14亿元，同比+108%。"
        "连续15年增长，净增117家门店。"
    )
    claims = dv.extract_claims(md)
    naked = _naked_texts(claims)
    assert any("5000" in t for t in naked)
    assert any("1000" in t for t in naked)
    assert any("43.14" in t for t in naked)
    assert any("108" in t for t in naked)
    assert any("15" in t for t in naked)
    assert any("117" in t for t in naked)


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
def test_table_row_with_link_is_one_linked_claim():
    md = (
        "| 指标 | 数值 |\n"
        "|------|------|\n"
        "| 净利润 | [43.14亿（+89.3%）](https://ex.com/p1) |\n"
    )
    claims = dv.extract_claims(md)
    assert _kinds(claims) == ["linked"]
    assert any("89.3" in n for n in claims[0]["numbers"])


def test_table_row_without_link_or_tag_is_naked():
    md = "| 毛利率 | 75.09% |\n|------|------|\n"
    claims = dv.extract_claims(md)
    assert "naked" in _kinds(claims)


def test_table_caption_tag_covers_rows():
    md = (
        "核心技术指标〖内部数据〗\n"
        "| RPS60 | 91.82 |\n"
        "|------|------|\n"
        "| RPS250 | 67.48 |\n"
    )
    claims = dv.extract_claims(md)
    assert set(_kinds(claims)) == {"internal"}
    assert not [c for c in claims if c["kind"] == "naked"]


# --------------------------------------------------------------------------- #
# Structural exemptions
# --------------------------------------------------------------------------- #
def test_code_fence_and_footer_exempt():
    md = (
        "```\nx = 12345\n```\n"
        "数据核验：45处数字，43处已核验（37外链/6内部），2处已改写。\n"
    )
    assert dv.extract_claims(md) == []


# --------------------------------------------------------------------------- #
# Internal-data mechanical matching
# --------------------------------------------------------------------------- #
def test_flatten_and_match():
    data = {"technicals": {"rps60": 91.82, "rps250": 67.484, "klines": [{"close": 20.5}]},
            "rps_gate": {"threshold": 80},
            "summary": {"note": "净利预告55~60亿元"}}
    nums = dv.flatten_data_numbers(data)
    assert dv.internal_numbers_match(["91.82"], nums)
    assert dv.internal_numbers_match(["67.48"], nums)      # rounded variant
    assert dv.internal_numbers_match(["20.5", "80"], nums)
    assert dv.internal_numbers_match(["55"], nums)         # from string leaf
    assert not dv.internal_numbers_match(["999.9"], nums)


def test_normalize_number():
    assert dv.normalize_number("４３.１４％") == "43.14%"
    assert dv.normalize_number("1,234") == "1234"


# --------------------------------------------------------------------------- #
# Verification round
# --------------------------------------------------------------------------- #
def _auto_judge(verdict_for=None, calls=None):
    """Judge stub: supports everything except ids in verdict_for."""
    verdict_for = verdict_for or {}

    def judge(prompt):
        if calls is not None:
            calls.append(prompt)
        ids = re.findall(r'"id": "(c\d+)"', prompt)
        v = {i: verdict_for.get(i, {"verdict": "supported"}) for i in ids}
        return json.dumps({"verdicts": v}), 10, 5
    return judge


PAGE = "本页显示公司2026年半年度业绩预告，归母净利润43.14亿元，同比+89.3%。" * 10


def test_verify_linked_batches_per_url_and_unreachable():
    md = (
        "营收[43.14亿](https://a.com/1)与净利[5.51亿](https://a.com/1)，"
        "毛利率[75.09%](https://b.com/2)。"
    )
    claims = dv.extract_claims(md)
    fetched, judged = [], []

    def fetch(url):
        fetched.append(url)
        return "HTTP 403: Forbidden" if "b.com" in url else PAGE

    rec = dv.verify_claims(claims, set(), {}, spec_verify="SPEC",
                           judge_runner=_auto_judge(calls=judged), fetch=fetch, cache={})
    assert sorted(set(fetched)) == ["https://a.com/1", "https://b.com/2"]
    assert len(fetched) == 2                      # one fetch per unique URL
    assert len(judged) == 1                       # b.com unreachable → no judge call
    by_url = {c["url"]: c["status"] for c in claims}
    assert by_url["https://a.com/1"] == "verified"
    assert by_url["https://b.com/2"] == "unreachable"
    assert rec["counts"]["verified"] == 2


def test_parse_verdicts_retry_then_unreachable():
    md = "营收[43.14亿](https://a.com/1)。"
    claims = dv.extract_claims(md)
    calls = []

    def bad_judge(prompt):
        calls.append(prompt)
        return "not json at all", 1, 1

    dv.verify_claims(claims, set(), {}, spec_verify="S",
                     judge_runner=bad_judge, fetch=lambda u: PAGE, cache={})
    assert len(calls) == 2                        # one retry
    assert claims[0]["status"] == "unreachable"


def test_verified_cache_skips_refetch():
    md = "营收[43.14亿](https://a.com/1)。"
    cache = {}
    fetched = []
    claims1 = dv.extract_claims(md)
    dv.verify_claims(claims1, set(), {}, spec_verify="S",
                     judge_runner=_auto_judge(), fetch=lambda u: (fetched.append(u), PAGE)[1],
                     cache=cache)
    claims2 = dv.extract_claims(md)
    dv.verify_claims(claims2, set(), {}, spec_verify="S",
                     judge_runner=_auto_judge(), fetch=lambda u: (fetched.append(u), PAGE)[1],
                     cache=cache)
    assert len(fetched) == 1                      # round 2: cache hit, no fetch
    assert claims2[0]["status"] == "verified"


def test_internal_mechanical_and_llm_fallback():
    md = "RPS60=91.82〖内部数据〗，且股价站上MA20约2.3%〖内部数据〗。"
    claims = dv.extract_claims(md)
    data = {"technicals": {"rps60": 91.82}}
    judged = []
    dv.verify_claims(claims, dv.flatten_data_numbers(data), data, spec_verify="S",
                     judge_runner=_auto_judge(calls=judged), fetch=lambda u: PAGE, cache={})
    assert all(c["status"] == "verified" for c in claims)
    assert len(judged) == 1                       # only the derived claim hit the LLM
    assert "内部DATA核验" in judged[0]


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def _boom(*a, **k):
    raise AssertionError("runner must not be called")


def test_run_pipeline_clean_first_round():
    draft = "RPS60=91.82〖内部数据〗。"
    data = {"technicals": {"rps60": 91.82}}
    text, audit = dv.run_pipeline(
        draft, data, spec_writer="W", spec_verify="V", max_rounds=2,
        judge_runner=_boom, revise_runner=_boom, cleanup_runner=_boom,
        fetch=_boom)
    assert "数据核验" in text
    assert audit["final"]["verified_internal"] == 1
    assert audit["final"]["unverified_remaining"] == 0
    assert len(audit["rounds"]) == 1
    assert audit["cleanup"]["used"] is False


def test_run_pipeline_revise_then_pass():
    draft = "营收43.14亿元创新高。"                       # naked → fails round 1
    fixed = "营收[43.14亿元](https://a.com/1)创新高。"   # revise adds the link
    revises = []

    def revise(prompt):
        revises.append(prompt)
        return fixed, 100, 50, 2

    text, audit = dv.run_pipeline(
        draft, {}, spec_writer="W", spec_verify="V", max_rounds=2,
        judge_runner=_auto_judge(), revise_runner=revise, cleanup_runner=_boom,
        fetch=lambda u: PAGE)
    assert len(revises) == 1
    assert "核验失败清单" in revises[0] and "43.14亿元" in revises[0]
    assert "https://a.com/1" in text
    assert audit["final"]["unverified_remaining"] == 0
    assert audit["cleanup"]["used"] is False
    assert len(audit["rounds"]) == 2


def test_run_pipeline_exhausted_uses_cleanup_and_mechanical_guard():
    draft = "从5000元/件降级。"                            # naked, never fixed

    def stubborn(prompt):                                  # revise returns same text
        return draft, 1, 1, 1

    def lazy_cleanup(prompt):                              # cleanup also fails to fix
        return draft, 1, 1

    text, audit = dv.run_pipeline(
        draft, {}, spec_writer="W", spec_verify="V", max_rounds=2,
        judge_runner=_auto_judge(), revise_runner=stubborn, cleanup_runner=lazy_cleanup,
        fetch=lambda u: PAGE)
    assert audit["cleanup"]["used"] is True
    assert audit["cleanup"]["mechanical_fallbacks"] >= 1
    assert "5000" not in text.split("数据核验")[0]          # the number is GONE
    body = text.split("数据核验")[0]
    assert not [c for c in dv.extract_claims(body) if c["kind"] == "naked"]
    assert dv.GENERIC_FALLBACK in text


def test_strip_preamble():
    chatty = "Now I have all the verified data. Let me write.\n\n---\n\n# 报告标题\n正文"
    assert dv.strip_preamble(chatty).startswith("# 报告标题")
    clean = "# 报告标题\n正文"
    assert dv.strip_preamble(clean) == clean
    no_h1 = "只是普通文本，没有标题"
    assert dv.strip_preamble(no_h1) == no_h1


def test_pipeline_strips_revise_preamble():
    draft = "营收43.14亿元创新高。"
    fixed = "好的，我来修订。\n\n# 报告\n营收[43.14亿元](https://a.com/1)创新高。"

    text, audit = dv.run_pipeline(
        draft, {}, spec_writer="W", spec_verify="V", max_rounds=2,
        judge_runner=_auto_judge(), revise_runner=lambda p: (fixed, 1, 1, 1),
        cleanup_runner=_boom, fetch=lambda u: PAGE)
    assert text.startswith("# 报告")
    assert "好的，我来修订" not in text


def test_verification_footer_counts():
    f = dv.verification_footer({"total": 45, "verified_linked": 37,
                                "verified_internal": 6, "rewritten_qualitative": 2,
                                "unverified_remaining": 0})
    assert "45处数字" in f and "43处已核验" in f and "37外链/6内部" in f and "2处已改写" in f


# --------------------------------------------------------------------------- #
# Fixture sweep: the real 002832 report (allowlist tuning harness)
# --------------------------------------------------------------------------- #
def test_fixture_002832_report_sweep():
    # Frozen copy of the ORIGINAL (unverified) 002832 report — the one with the
    # fabricated ¥5000/件 — used as the allowlist tuning harness. The live
    # reports/ copy is now the verified version and would trivially pass.
    fixture = (Path(__file__).resolve().parent.parent / "tests" / "fixtures"
               / "002832-2026-07-22-deep-unverified.md")
    if not fixture.exists():
        import pytest
        pytest.skip("fixture report not present")
    text = fixture.read_text(encoding="utf-8")
    claims = dv.extract_claims(text)
    naked = [c for c in claims if c["kind"] == "naked"]
    # The old report has no links/tags: nearly every real figure should be
    # flagged, including the fabricated 5000元/件 — while dates/codes/rating
    # stay exempt. Sanity bounds, not exact counts.
    assert len(naked) > 40
    assert any("5000" in c["numbers"][0] for c in naked), "the fabricated price must be caught"
    joined = " ".join(c["numbers"][0] for c in naked)
    assert "2025年" not in joined
    assert "002832" not in joined
