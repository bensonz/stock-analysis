"""fundamentals.py + the stock_fundamentals tool: exact peer numbers for deep reports.

The whole point: peer/valuation figures come from disclosure tables and enter the
DATA corpus, so 〖内部数据〗 claims about them verify mechanically — instead of
dying as unverifiable web claims (the 002245 report lost its whole peer table
to that failure mode).
"""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import deep_report
import deep_verify
import fundamentals
import llm_client


@pytest.fixture(autouse=True)
def _clear_cache():
    fundamentals._TABLE_CACHE.clear()
    yield
    fundamentals._TABLE_CACHE.clear()


def _yjbb_df(code="300014", revenue=2.067986e10, rev_yoy=61.61, profit=1.446303e9,
             profit_yoy=31.35):
    return pd.DataFrame([{
        "股票代码": code, "股票简称": "亿纬锂能", "每股收益": 0.71,
        "营业总收入-营业总收入": revenue, "营业总收入-同比增长": rev_yoy,
        "净利润-净利润": profit, "净利润-同比增长": profit_yoy,
        "每股净资产": 16.4, "净资产收益率": 4.32, "每股经营现金流量": -0.5,
        "销售毛利率": 17.2, "所处行业": "电池", "最新公告日期": "2026-04-30",
    }])


def test_report_periods_include_upcoming_quarter():
    # 预告 for a period publishes weeks early — the walk must probe 20260630 in July.
    ps = fundamentals.report_periods(date(2026, 7, 24))
    assert ps[:3] == ["20260930", "20260630", "20260331"]
    assert "20251231" in ps
    # 亿纬's 2026H1 预告 landed 6/15 — two weeks BEFORE the period end, so the
    # upcoming period must already be probed in June.
    assert fundamentals.report_periods(date(2026, 6, 15))[0] == "20260630"


def test_snapshot_walks_back_and_converts_units(monkeypatch):
    def fake_load(kind, period):
        if kind == "yjbb" and period == "20260331":
            return _yjbb_df()
        if kind == "yjbb" and period == "20251231":
            return _yjbb_df(revenue=6.5e10, rev_yoy=40.0, profit=5.1e9, profit_yoy=25.0)
        return None  # 20260630 not yet published; yjyg/yjkb empty

    monkeypatch.setattr(fundamentals, "_load_table", fake_load)
    snap = fundamentals.stock_snapshot(
        "300014.SZ", today=date(2026, 7, 24),
        include_valuation=False, include_rps=False)

    assert snap["code"] == "300014"
    assert snap["name"] == "亿纬锂能"
    # 亿元 2dp — the exact form a writer cites, so mechanical verify matches
    assert snap["latest_report"]["period"] == "2026一季报"
    assert snap["latest_report"]["revenue_亿元"] == 206.8
    assert snap["latest_report"]["net_profit_亿元"] == 14.46
    assert snap["annual_report"]["period"] == "2025年报"
    assert snap["annual_report"]["revenue_亿元"] == 650.0


def test_snapshot_no_disclosures_notes_it(monkeypatch):
    monkeypatch.setattr(fundamentals, "_load_table", lambda k, p: None)
    snap = fundamentals.stock_snapshot("999999", today=date(2026, 7, 24),
                                       include_valuation=False, include_rps=False)
    assert "note" in snap


def test_tool_executor_stores_into_data_corpus(monkeypatch):
    monkeypatch.setattr(
        fundamentals, "stock_snapshot",
        lambda code, **kw: {"code": code, "latest_report": {"revenue_亿元": 47.68}})
    data = {"code6": "002245"}
    tools, executor = deep_report._make_report_tools(data)

    assert tools[0]["name"] == "stock_fundamentals"
    out = executor("stock_fundamentals", {"code": "300438.SZ"})
    assert json.loads(out)["latest_report"]["revenue_亿元"] == 47.68
    # stored → part of the verify corpus
    assert data["peer_fundamentals"]["300438"]["latest_report"]["revenue_亿元"] == 47.68
    # a 〖内部数据〗 claim citing the fetched number now matches mechanically
    nums = deep_verify.flatten_data_numbers(data)
    assert deep_verify.internal_numbers_match(["47.68亿元"], nums)
    # other tools fall through to the global dispatch
    assert executor("web_search", {"query": "x"}) is None


def test_tool_executor_caches_per_code(monkeypatch):
    calls = []
    monkeypatch.setattr(fundamentals, "stock_snapshot",
                        lambda code, **kw: calls.append(code) or {"code": code})
    data = {}
    _, executor = deep_report._make_report_tools(data)
    executor("stock_fundamentals", {"code": "300014"})
    executor("stock_fundamentals", {"code": "300014.SZ"})  # revise-round repeat
    assert calls == ["300014"]


def test_anthropic_tool_converts_to_openai_schema():
    t = llm_client.anthropic_tool_to_openai(deep_report.STOCK_FUNDAMENTALS_TOOL)
    assert t["type"] == "function"
    assert t["function"]["name"] == "stock_fundamentals"
    assert t["function"]["parameters"]["required"] == ["code"]


def test_verify_pipeline_grown_corpus_rescues_internal_claim():
    """A 〖内部数据〗 claim failing round 1 verifies in round 2 after the revise
    pass fetches the peer via the tool (data grows mid-pipeline) — the stale
    cached failure must not pin it."""
    data = {"technicals": {"rps60": 90.0}}
    draft = "# R\n\n同业营收47.68亿元〖内部数据〗，RPS60=90.0〖内部数据〗\n"

    def judge_runner(prompt):
        # unmatched internal claims get judged not_found (number not in DATA yet)
        req = json.loads(prompt.split("# 待核验条目 (JSON)\n```json\n")[1].split("```")[0])
        verdicts = [{"id": c["id"], "verdict": "not_found", "reason": "无",
                     "fallback_text": "（略）"} for c in req]
        return json.dumps({"verdicts": verdicts}), 10, 10

    def revise_runner(prompt):
        # the revise pass calls stock_fundamentals → corpus grows; text unchanged
        data["peer_fundamentals"] = {"300438": {"latest_report": {"revenue_亿元": 47.68}}}
        return draft, 10, 10, 1

    text, audit = deep_verify.run_pipeline(
        draft, data, spec_writer="SPEC", spec_verify="VSPEC", max_rounds=2,
        judge_runner=judge_runner, revise_runner=revise_runner,
        cleanup_runner=lambda p: (p, 0, 0), fetch=lambda url: "")

    assert audit["final"]["unverified_remaining"] == 0
    assert audit["final"]["verified_internal"] == 2
    assert "47.68亿元" in text  # survived, not scrubbed
    assert not audit["cleanup"]["used"]
