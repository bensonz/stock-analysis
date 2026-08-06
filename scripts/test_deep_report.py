"""Tests for deep_report — CheeseForTune-style deep-research article generator.

Pure logic is unit-tested; all network/LLM is monkeypatched. One live integration
smoke test behind the `integration` marker.
"""

import json

import pytest

import deep_report


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #
def test_downsample_thins_long_series():
    series = [{"x": i} for i in range(240)]
    out = deep_report._downsample(series, keep=24)
    assert len(out) <= 24 + 1
    assert deep_report._downsample([1, 2, 3], keep=24) == [1, 2, 3]  # short passthrough
    assert deep_report._downsample(None) is None


def test_trim_peers_keeps_target_row_drops_market_list():
    peers = {
        "total": 5796,
        "catalog": [{"optname": "总市值"}, {"optname": "ROE"}],
        "list": [
            {"code": "600000.SH", "name": "银行", "rank": 1},
            {"code": "000703.SZ", "name": "恒逸石化", "rank": 378},
        ],
    }
    out = deep_report._trim_peers(peers, "000703")
    assert out["industry_total"] == 5796
    assert out["metrics"] == ["总市值", "ROE"]
    assert out["target_row"]["name"] == "恒逸石化"
    assert "top_peers" not in out  # misleading market-cap list dropped
    assert deep_report._trim_peers(None, "000703") is None


# --------------------------------------------------------------------------- #
# gather_data (all data sources monkeypatched)
# --------------------------------------------------------------------------- #
class _FakeClient:
    def __init__(self, *a, **k):
        pass

    def get_stock_summary(self, code):
        return {"name": "恒逸石化", "pe": 24.2, "highlights": [], "risks": []}

    def get_intro(self, code):
        return {"basic": {"briefing": "炼化一体化"}}

    def get_industry_compare(self, code):
        return {"total": 5796, "catalog": [{"optname": "ROE"}],
                "list": [{"code": "000703.SZ", "name": "恒逸石化", "rank": 378}]}

    def get_pepb_history(self, code, years="5Y"):
        return {"msg": "估值中位", "newest": {"pe": 24.2}, "datas": [{"x": "d", "y": 1}] * 300}


def _patch_sources(monkeypatch, client=_FakeClient):
    import cheesefortune_client
    import margin_flow
    import rps_calculator
    monkeypatch.setattr(cheesefortune_client, "CheeseFortuneClient", client)
    monkeypatch.setattr(cheesefortune_client, "normalize_code", lambda c: f"{c}.SZ")
    monkeypatch.setattr(rps_calculator, "get_ma_rps_for_stocks",
                        lambda db, codes, date=None: {codes[0]: {"rps60": 85.9, "rps120": 94.5, "rps250": 90.2, "ma10_today": 7.5}})
    monkeypatch.setattr(margin_flow, "fetch_margin_flow",
                        lambda code: {"rzye_yi": 10.5, "signal": "deleveraging"})
    monkeypatch.setattr(deep_report, "_recent_klines", lambda code6, limit=20: [{"date": "2026-07-14", "close": 20.5}])


def test_gather_data_assembles_expected_keys(monkeypatch):
    _patch_sources(monkeypatch)
    d = deep_report.gather_data("000703")
    for key in ("code", "code6", "summary", "intro", "peers", "valuation_history",
                "technicals", "rps_gate", "margin"):
        assert key in d, f"missing {key}"
    assert d["code6"] == "000703"
    assert d["rps_gate"]["passes_all_ge_80"] is True  # 85.9/94.5/90.2 all >= 80
    assert d["technicals"]["klines"][0]["close"] == 20.5
    assert len(d["valuation_history"]["series"]) <= 25  # downsampled from 300
    assert "_gather_errors" not in d


def test_gather_data_tolerates_a_failing_source(monkeypatch):
    class _Flaky(_FakeClient):
        def get_stock_summary(self, code):
            raise RuntimeError("cheesefortune down")

    _patch_sources(monkeypatch, client=_Flaky)
    d = deep_report.gather_data("000703")
    assert d["summary"] is None            # failed source -> None, not a crash
    assert d["intro"] is not None          # other sources still populated
    assert any("summary" in e for e in d["_gather_errors"])


def test_rps_gate_none_when_metrics_missing(monkeypatch):
    _patch_sources(monkeypatch)
    import rps_calculator
    monkeypatch.setattr(rps_calculator, "get_ma_rps_for_stocks", lambda db, codes, date=None: {})
    d = deep_report.gather_data("000703")
    assert d["rps_gate"]["passes_all_ge_80"] is None  # can't evaluate without RPS


# --------------------------------------------------------------------------- #
# build_prompt / write_report / generate
# --------------------------------------------------------------------------- #
def test_build_prompt_contains_spec_code_and_data():
    prompt = deep_report.build_prompt("SPEC-SENTINEL", "000703", {"code": "000703.SZ", "pe": 24})
    assert "SPEC-SENTINEL" in prompt
    assert "000703.SZ" in prompt
    assert '"pe": 24' in prompt
    assert "# DATA" in prompt


def test_write_report_path_and_content(tmp_path):
    # explicit output_dir bypasses grouping — flat write, exactly where asked
    out = deep_report.write_report("000703.SZ", "# 报告\n结论：看多", output_dir=tmp_path)
    assert out.parent == tmp_path
    assert out.name.startswith("000703-") and out.name.endswith("-deep.md")
    assert "看多" in out.read_text(encoding="utf-8")


def test_write_report_groups_by_code_and_chinese_name(tmp_path, monkeypatch):
    import report_generator
    monkeypatch.setattr(report_generator, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(deep_report, "_stock_name", lambda c: "*ST 奥来德")
    out = deep_report.write_report("688378", "# 报告")
    # name sanitized (no *, no spaces) and grouped: <code>-<name>/<code>-<date>-deep.md
    assert out.parent == tmp_path / "688378-ST奥来德"
    assert out.name.startswith("688378-") and out.name.endswith("-deep.md")
    # audit JSON lands in the same group folder
    audit = deep_report.write_verify_audit("688378", {"final": {}})
    assert audit.parent == out.parent
    # no name available -> plain code folder
    monkeypatch.setattr(deep_report, "_stock_name", lambda c: None)
    out2 = deep_report.write_report("999999", "# 报告")
    assert out2.parent == tmp_path / "999999"


def test_generate_openai_orchestration(monkeypatch):
    import llm_client
    monkeypatch.setattr(llm_client, "normalize_llm_provider", lambda p: "openai")
    monkeypatch.setattr(llm_client, "_build_openai_client", lambda: object())
    monkeypatch.setattr(llm_client, "OPENAI_MODEL", "fake-model")
    monkeypatch.setattr(llm_client, "_run_openai_tool_loop",
                        lambda *a, **k: ("# 报告\n结论：中性", 1000, 2000, 3))
    res = deep_report.generate("000703", provider="openai", data={"code": "000703.SZ"},
                               verify=False)
    assert res["text"].startswith("# 报告")
    assert res["provider"] == "openai" and res["model"] == "fake-model"
    assert res["input_tokens"] == 1000 and res["output_tokens"] == 2000 and res["rounds"] == 3
    assert res["verify_audit"] is None and res["verify_rounds"] == 0


def test_generate_anthropic_branch(monkeypatch):
    import llm_client
    monkeypatch.setattr(llm_client, "normalize_llm_provider", lambda p: "anthropic")
    monkeypatch.setattr(llm_client, "_build_anthropic_client", lambda: object())
    monkeypatch.setenv("ANTHROPIC_MODEL", "fake-claude")  # _provider_model reads env, not DEFAULT_MODEL
    monkeypatch.setattr(llm_client, "_run_tool_loop",
                        lambda *a, **k: ("结论：看空", 5, 6, 1))
    res = deep_report.generate("000703", provider="anthropic", data={"code": "000703.SZ"},
                               verify=False)
    assert res["model"] == "fake-claude" and res["text"] == "结论：看空"


# --------------------------------------------------------------------------- #
# Citation-verify orchestration
# --------------------------------------------------------------------------- #
def test_generate_verify_orchestration(monkeypatch):
    import deep_verify
    import llm_client
    monkeypatch.setattr(llm_client, "normalize_llm_provider", lambda p: "openai")
    monkeypatch.setattr(llm_client, "_build_openai_client", lambda: object())
    monkeypatch.setattr(llm_client, "OPENAI_MODEL", "fake-model")
    monkeypatch.setattr(llm_client, "_run_openai_tool_loop",
                        lambda *a, **k: ("# 草稿", 1000, 2000, 3))
    canned_audit = {"rounds": [{"round": 1}], "final": {"total": 0}}
    seen = {}

    def fake_pipeline(draft, data, **kw):
        seen["draft"] = draft
        seen["max_rounds"] = kw["max_rounds"]
        return "# 已核验报告\n\n---\n数据核验：0处数字。", canned_audit

    monkeypatch.setattr(deep_verify, "run_pipeline", fake_pipeline)
    res = deep_report.generate("000703", provider="openai", data={"code": "000703.SZ"},
                               verify=True, max_verify_rounds=3)
    assert seen["draft"] == "# 草稿" and seen["max_rounds"] == 3
    assert res["text"].startswith("# 已核验报告")
    assert res["verify_audit"] is canned_audit and res["verify_rounds"] == 1


def test_split_provider_judge_runs_on_verify_provider(monkeypatch):
    """Writer on anthropic (the brain), judge/cleanup on openai (fast agent)."""
    import llm_client

    class _FakeUsage:
        prompt_tokens, completion_tokens = 7, 3

    class _FakeMsg:
        content = '{"verdicts": {}}'

    class _FakeChoice:
        message = _FakeMsg()

    class _FakeResp:
        usage, choices = _FakeUsage(), [_FakeChoice()]

    judge_calls = []

    class _FakeOpenAI:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    judge_calls.append(kw["model"])
                    return _FakeResp()

    monkeypatch.setattr(llm_client, "normalize_llm_provider",
                        lambda p: p or "anthropic")
    monkeypatch.setattr(llm_client, "_build_anthropic_client", lambda: object())
    monkeypatch.setattr(llm_client, "_build_openai_client", lambda: _FakeOpenAI())
    monkeypatch.setenv("ANTHROPIC_MODEL", "kimi-k3")  # _provider_model reads env, not DEFAULT_MODEL
    monkeypatch.setattr(llm_client, "OPENAI_MODEL", "deepseek-fast")
    # writer draft: contains one internal claim so the pipeline runs but needs
    # no web fetch; judge gets exercised via the unmatched-internal batch
    monkeypatch.setattr(llm_client, "_run_tool_loop",
                        lambda *a, **k: ("# 报告\n站上MA20约2.3%〖内部数据〗。", 10, 20, 1))

    res = deep_report.generate("000703", provider="anthropic",
                               data={"code": "000703.SZ"},
                               verify=True, verify_provider="openai")
    # every verify-side LLM call (judge round 1 + cleanup) ran on the verify provider
    assert judge_calls and all(m == "deepseek-fast" for m in judge_calls)
    assert res["provider"] == "anthropic" and res["model"] == "kimi-k3"
    assert res["verify_audit"]["final"]["unverified_remaining"] == 0


def test_write_verify_audit_path(tmp_path):
    audit = {"final": {"total": 1}}
    out = deep_report.write_verify_audit("000703.SZ", audit, output_dir=tmp_path)
    assert out.parent == tmp_path
    assert out.name.startswith("000703-") and out.name.endswith("-deep-verify.json")
    import json
    assert json.loads(out.read_text(encoding="utf-8")) == audit


def test_cli_verify_flags(monkeypatch, tmp_path, capsys):
    import sys as _sys
    seen = {}

    def fake_generate(code, provider=None, verify=True, max_verify_rounds=2,
                      verify_provider=None, focus=None):
        seen["verify"] = verify
        seen["max_verify_rounds"] = max_verify_rounds
        seen["verify_provider"] = verify_provider
        return {"text": "# R", "tool_calls": [], "input_tokens": 1, "output_tokens": 1,
                "rounds": 1, "provider": "openai", "model": "m", "data": {},
                "verify_audit": None, "verify_rounds": 0}

    monkeypatch.setattr(deep_report, "generate", fake_generate)
    monkeypatch.setattr(_sys, "argv",
                        ["deep_report.py", "000703", "--no-verify",
                         "--max-verify-rounds", "1", "--output-dir", str(tmp_path)])
    deep_report.main()
    assert seen["verify"] is False and seen["max_verify_rounds"] == 1


@pytest.mark.integration
def test_generate_live():
    res = deep_report.generate("000703")
    assert isinstance(res["text"], str) and len(res["text"]) > 500
    assert "核心观点" in res["text"]
    # verified output must contain zero naked numbers
    import deep_verify
    body = res["text"].split("数据核验")[0]
    naked = [c for c in deep_verify.extract_claims(body) if c["kind"] == "naked"]
    assert naked == []
