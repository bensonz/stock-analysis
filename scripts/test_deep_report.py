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


_CARD = ('```scorecard\n{"F": 7.5, "F_anchor": "8: 利润加速——净利+35%", '
         '"V": 5.0, "V_anchor": "4: 分位 70–85%——分位77%", '
         '"M": 6.5, "M_anchor": "6: 三线过闸——RPS20=23", '
         '"R": 6.0, "R_anchor": "6: 单一风险点——现金流待验证"}\n```\n')
# 0.35·7.5 + 0.25·5 + 0.25·6.5 + 0.15·6 = 6.4 → 3/5, F≥6 and M≥5 → 看多
_CARD_STAMP = "看多 ｜ 评级 3/5（W=6.4）"


def _ok_draft(body: str = "", card: str = _CARD) -> str:
    """Writer-mock draft that clears the 2026-08-07 degenerate-draft floor,
    in the scoring-equation shape: rating placeholders + a scorecard block."""
    return ("# 测试（000703）深度研究报告 · {{评级}}\n**结论：{{评级}}（测试）**\n"
            + body + "正文。" * 1500 + "\n" + card)


@pytest.fixture(autouse=True)
def _scorecard_log_to_tmp(tmp_path, monkeypatch):
    """main() appends to reports/scorecards.jsonl — never the real one in tests."""
    monkeypatch.setattr(deep_report, "SCORECARD_LOG", tmp_path / "scorecards.jsonl")


def test_generate_openai_orchestration(monkeypatch):
    import llm_client
    monkeypatch.setattr(llm_client, "normalize_llm_provider", lambda p: "openai")
    monkeypatch.setattr(llm_client, "_build_openai_client", lambda: object())
    monkeypatch.setattr(llm_client, "OPENAI_MODEL", "fake-model")
    monkeypatch.setattr(llm_client, "_run_openai_tool_loop",
                        lambda *a, **k: (_ok_draft("结论：中性"), 1000, 2000, 3))
    res = deep_report.generate("000703", provider="openai", data={"code": "000703.SZ"},
                               verify=False, bear=False)
    assert res["text"].startswith("# 测试")
    assert res["provider"] == "openai" and res["model"] == "fake-model"
    assert res["input_tokens"] == 1000 and res["output_tokens"] == 2000 and res["rounds"] == 3
    assert res["verify_audit"] is None and res["verify_rounds"] == 0


def test_generate_anthropic_branch(monkeypatch):
    import llm_client
    monkeypatch.setattr(llm_client, "normalize_llm_provider", lambda p: "anthropic")
    monkeypatch.setattr(llm_client, "_build_anthropic_client", lambda: object())
    monkeypatch.setenv("ANTHROPIC_MODEL", "fake-claude")  # _provider_model reads env, not DEFAULT_MODEL
    monkeypatch.setattr(llm_client, "_run_tool_loop",
                        lambda *a, **k: (_ok_draft("结论：看空"), 5, 6, 1))
    res = deep_report.generate("000703", provider="anthropic", data={"code": "000703.SZ"},
                               verify=False, bear=False)
    assert res["model"] == "fake-claude" and "结论：看空" in res["text"]


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
                        lambda *a, **k: (_ok_draft("草稿标记X7Y。"), 1000, 2000, 3))
    canned_audit = {"rounds": [{"round": 1}], "final": {"total": 0}}
    seen = {}

    def fake_pipeline(draft, data, **kw):
        seen["draft"] = draft
        seen["max_rounds"] = kw["max_rounds"]
        return "# 已核验报告\n\n---\n数据核验：0处数字。", canned_audit

    monkeypatch.setattr(deep_verify, "run_pipeline", fake_pipeline)
    res = deep_report.generate("000703", provider="openai", data={"code": "000703.SZ"},
                               verify=True, max_verify_rounds=3, bear=False)
    assert "草稿标记X7Y" in seen["draft"] and seen["max_rounds"] == 3
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
                        lambda *a, **k: (_ok_draft("站上MA20约2.3%〖内部数据〗。"), 10, 20, 1))

    res = deep_report.generate("000703", provider="anthropic",
                               data={"code": "000703.SZ"},
                               verify=True, verify_provider="openai", bear=False)
    # every verify-side LLM call (judge round 1 + cleanup) ran on the verify provider
    assert judge_calls and all(m == "deepseek-fast" for m in judge_calls)
    assert res["provider"] == "anthropic" and res["model"] == "kimi-k3"
    assert res["verify_audit"]["final"]["unverified_remaining"] == 0


def _capturing_openai(calls, finish_reason="stop"):
    class _Usage:
        prompt_tokens, completion_tokens = 7, 3

    class _Choice:
        def __init__(self):
            self.message = type("M", (), {"content": '{"verdicts": {}}'})()
            self.finish_reason = finish_reason

    class _Resp:
        usage, choices = _Usage(), [_Choice()]

    class _Client:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    calls.append(kw)
                    return _Resp()
    return _Client()


def test_deepseek_judge_runs_with_thinking_disabled():
    """deepseek-v4-pro thinking spent the judge's whole 8192-token budget on
    reasoning and returned "" (000002, 2026-10-01). A verdict check needs no
    chain of thought — the judge call turns it off; cleanup is left alone."""
    calls = []
    _rev, judge, cleanup = deep_report._make_runners(
        "openai", _capturing_openai(calls), "deepseek-v4-pro", [],
        {"in": 0, "out": 0, "rounds": 0})
    text, _i, _o, finish = judge("p")
    cleanup("p")
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "extra_body" not in calls[1]
    assert finish == "stop"


def test_non_deepseek_judge_gets_no_thinking_param():
    calls = []
    _rev, judge, _cl = deep_report._make_runners(
        "openai", _capturing_openai(calls), "gpt-5.4", [],
        {"in": 0, "out": 0, "rounds": 0})
    judge("p")
    assert "extra_body" not in calls[0]


def test_judge_runner_reports_length_finish():
    calls = []
    _rev, judge, _cl = deep_report._make_runners(
        "openai", _capturing_openai(calls, finish_reason="length"), "gpt-5.4", [],
        {"in": 0, "out": 0, "rounds": 0})
    assert judge("p")[3] == "length"


def test_write_verify_audit_path(tmp_path):
    audit = {"final": {"total": 1}}
    out = deep_report.write_verify_audit("000703.SZ", audit, output_dir=tmp_path)
    assert out.parent == tmp_path
    assert out.name.startswith("000703-") and out.name.endswith("-deep-verify.json")
    import json
    assert json.loads(out.read_text(encoding="utf-8")) == audit


def test_ensure_full_draft_retries_then_accepts():
    good = "# 测试（000001）深度研究报告 · 评级 3/5\n" + "正文" * 2000
    calls = []

    def rerun(attempt):
        calls.append(attempt)
        return good, [{"event": "x"}]

    text, bets = deep_report._ensure_full_draft("太短", [], rerun)
    assert text == good
    assert bets == [{"event": "x"}]
    assert calls == [0]  # accepted after first retry


def test_ensure_full_draft_raises_on_persistent_stub():
    import pytest
    with pytest.raises(RuntimeError, match="degenerate draft"):
        deep_report._ensure_full_draft("", [], lambda a: ("still short", []))


def test_ensure_full_draft_passes_good_draft_through():
    good = "# 测试（000001）深度研究报告 · 评级 4/5\n" + "x" * 4000
    text, bets = deep_report._ensure_full_draft(
        good, [{"event": "keep"}],
        lambda a: (_ for _ in ()).throw(AssertionError("must not rerun")))
    assert text == good
    assert bets == [{"event": "keep"}]


def test_cli_verify_flags(monkeypatch, tmp_path, capsys):
    import sys as _sys
    seen = {}

    def fake_generate(code, provider=None, verify=True, max_verify_rounds=2,
                      verify_provider=None, focus=None, bear=True):
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


# --------------------------------------------------------------------------- #
# Bear-research pass (2026-10-03: 600150 report missed the port-fee expiry)
# --------------------------------------------------------------------------- #
_BRIEF = ("# 反方研究简报\n"
          "BRIEF-SENTINEL 港口费暂停将于11月9日到期。" + "风险线索。" * 200 + "\n"
          "```events\n"
          '[{"event": "USTR 301港口费暂停到期", "date": "2026-11-09", "url": "https://x.gov/a"}]\n'
          "```\n")


def test_build_prompt_puts_bear_brief_in_own_block_not_data():
    prompt = deep_report.build_prompt("SPEC", "600150", {"code": "600150.SH", "pe": 24},
                                      bear_brief=_BRIEF)
    before_data, after_data = prompt.split("# DATA", 1)
    assert "# 反方研究简报（独立空头研究员预先检索，非DATA）" in before_data
    assert "BRIEF-SENTINEL" in before_data
    assert "BRIEF-SENTINEL" not in after_data  # D1: never in the verifier's corpus


def test_build_prompt_bear_block_follows_focus_block():
    prompt = deep_report.build_prompt("SPEC", "600150", {"code": "600150.SH"},
                                      focus="FOCUS-Q", bear_brief=_BRIEF)
    assert prompt.index("FOCUS-Q") < prompt.index("# 反方研究简报") < prompt.index("# DATA")


def test_build_prompt_without_bear_brief_has_no_bear_header():
    prompt = deep_report.build_prompt("SPEC", "600150", {"code": "600150.SH"})
    assert "反方研究简报" not in prompt


def test_build_bear_prompt_is_slim():
    data = {"code": "600150.SH", "summary": {"name": "中国船舶"}, "intro": {"basic": "造船"},
            "technicals": {"klines": ["KLINE-SENTINEL"]}}
    prompt = deep_report.build_bear_prompt("BEAR-SPEC", "600150", data, "2026-10-03")
    assert "BEAR-SPEC" in prompt and "600150.SH" in prompt and "中国船舶" in prompt
    assert "2026-10-03" in prompt and "造船" in prompt
    assert "KLINE-SENTINEL" not in prompt  # full data package stays out


def test_build_bear_prompt_tolerates_failed_summary():
    prompt = deep_report.build_bear_prompt("BEAR-SPEC", "600150",
                                           {"code": "600150.SH", "summary": None}, "2026-10-03")
    assert "600150.SH" in prompt


def test_extract_bear_events_valid_block():
    events = deep_report.extract_bear_events(_BRIEF)
    assert events == [{"event": "USTR 301港口费暂停到期", "date": "2026-11-09",
                       "url": "https://x.gov/a"}]


def test_extract_bear_events_bad_json_is_empty():
    assert deep_report.extract_bear_events("x\n```events\n[{not json\n```\n") == []


def test_extract_bear_events_missing_block_is_empty():
    assert deep_report.extract_bear_events("# 简报\n没有事件块") == []


def test_extract_bear_events_drops_undated_entries():
    brief = ('```events\n[{"event": "A", "date": "2026-11-09"}, {"event": "B"}, "junk"]\n```\n')
    assert deep_report.extract_bear_events(brief) == [{"event": "A", "date": "2026-11-09"}]


def test_extract_bear_events_last_block_wins():
    brief = ('```events\n[{"event": "OLD", "date": "2026-01-01"}]\n```\n正文\n'
             '```events\n[{"event": "NEW", "date": "2026-11-09"}]\n```\n')
    assert deep_report.extract_bear_events(brief) == [{"event": "NEW", "date": "2026-11-09"}]


def test_run_bear_pass_degrades_on_exception(monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("search API down")

    monkeypatch.setattr(deep_report, "_run_writer_pass", boom)
    assert deep_report.run_bear_pass(None, "m", "openai", [], "p") == (None, 0, 0, 0)
    assert "bear pass FAILED" in capsys.readouterr().err


def test_run_bear_pass_thin_text_keeps_tokens(monkeypatch, capsys):
    monkeypatch.setattr(deep_report, "_run_writer_pass", lambda *a, **k: ("太短", 11, 22, 2))
    assert deep_report.run_bear_pass(None, "m", "openai", [], "p") == (None, 11, 22, 2)
    assert "thin brief" in capsys.readouterr().err


def test_run_bear_pass_returns_brief_web_tools_only(monkeypatch):
    seen = {}

    def fake(client, model, resolved, messages, tool_log, label, **kw):
        seen.update(kw, label=label, prompt=messages[0]["content"])
        return "好的，我来检索。\n" + _BRIEF, 11, 22, 2

    monkeypatch.setattr(deep_report, "_run_writer_pass", fake)
    brief, i, o, r = deep_report.run_bear_pass(None, "m", "openai", [], "BEAR-P")
    assert brief.startswith("# 反方研究简报")  # leading chatter stripped
    assert (i, o, r) == (11, 22, 2)
    assert seen["prompt"] == "BEAR-P" and seen["label"] == "deep_report-bear "
    assert not seen.get("extra_tools") and not seen.get("tool_executor")


def _openai_fakes(monkeypatch, responses):
    """Stateful writer-loop fake: returns `responses` in order, records prompts."""
    import llm_client
    monkeypatch.setattr(llm_client, "normalize_llm_provider", lambda p: "openai")
    monkeypatch.setattr(llm_client, "_build_openai_client", lambda: object())
    monkeypatch.setattr(llm_client, "OPENAI_MODEL", "fake-model")
    prompts = []

    def loop(client, messages, *a, **k):
        prompts.append(messages[0]["content"])
        return responses[len(prompts) - 1]

    monkeypatch.setattr(llm_client, "_run_openai_tool_loop", loop)
    return prompts


def test_generate_bear_pass_feeds_brief_into_draft(monkeypatch, tmp_path):
    spec = tmp_path / "DEEP_BEAR.md"
    spec.write_text("BEAR-SPEC-SENTINEL", encoding="utf-8")
    monkeypatch.setattr(deep_report, "BEAR_SPEC_FILE", spec)
    prompts = _openai_fakes(monkeypatch, [(_BRIEF, 100, 200, 2),
                                          (_ok_draft("结论：中性"), 1000, 2000, 3)])
    data = {"code": "600150.SH"}
    res = deep_report.generate("600150", provider="openai", data=data, verify=False)
    assert len(prompts) == 2
    assert "BEAR-SPEC-SENTINEL" in prompts[0] and "# DATA" not in prompts[0]
    assert "BRIEF-SENTINEL" in prompts[1]
    assert "# 反方研究简报（独立空头研究员预先检索，非DATA）" in prompts[1]
    assert res["bear_brief"].startswith("# 反方研究简报")
    assert res["bear_events"][0]["date"] == "2026-11-09"
    assert (res["input_tokens"], res["output_tokens"], res["rounds"]) == (1100, 2200, 5)
    assert "BRIEF-SENTINEL" not in json.dumps(data, ensure_ascii=False)  # D1


def test_generate_bear_off_makes_no_bear_call(monkeypatch):
    prompts = _openai_fakes(monkeypatch, [(_ok_draft(), 1, 2, 1)])
    res = deep_report.generate("600150", provider="openai", data={"code": "600150.SH"},
                               verify=False, bear=False)
    # compare to the brief-less prompt: the spec itself mentions the block name
    spec = deep_report.SPEC_FILE.read_text(encoding="utf-8")
    assert prompts == [deep_report.build_prompt(spec, "600150", {"code": "600150.SH"})]
    assert res["bear_brief"] is None and res["bear_events"] == []


def test_generate_missing_bear_spec_degrades(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(deep_report, "BEAR_SPEC_FILE", tmp_path / "nope.md")
    prompts = _openai_fakes(monkeypatch, [(_ok_draft(), 1, 2, 1)])
    res = deep_report.generate("600150", provider="openai", data={"code": "600150.SH"},
                               verify=False)
    assert len(prompts) == 1  # straight to the draft
    assert res["bear_brief"] is None and res["bear_events"] == []
    assert "bear pass FAILED" in capsys.readouterr().err


def test_write_bear_brief_path(tmp_path):
    out = deep_report.write_bear_brief("600150.SH", _BRIEF, output_dir=tmp_path)
    assert out.parent == tmp_path
    assert out.name.startswith("600150-") and out.name.endswith("-deep-bear.md")
    assert "BRIEF-SENTINEL" in out.read_text(encoding="utf-8")


def _cli_fake_generate(seen, bear_brief=None):
    def fake(code, provider=None, verify=True, max_verify_rounds=2,
             verify_provider=None, focus=None, bear=True):
        seen["bear"] = bear
        return {"text": "# R", "tool_calls": [], "input_tokens": 1, "output_tokens": 1,
                "rounds": 1, "provider": "openai", "model": "m", "data": {},
                "verify_audit": None, "verify_rounds": 0,
                "bear_brief": bear_brief,
                "bear_events": deep_report.extract_bear_events(bear_brief or "")}
    return fake


def test_cli_no_bear_flag(monkeypatch, tmp_path, capsys):
    import sys as _sys
    seen = {}
    monkeypatch.setattr(deep_report, "generate", _cli_fake_generate(seen))
    monkeypatch.setattr(_sys, "argv", ["deep_report.py", "600150", "--no-verify",
                                       "--no-bear", "--output-dir", str(tmp_path)])
    deep_report.main()
    assert seen["bear"] is False
    assert "bear   : OFF" in capsys.readouterr().err
    assert not list(tmp_path.glob("*-deep-bear.md"))


def test_cli_writes_bear_brief(monkeypatch, tmp_path, capsys):
    import sys as _sys
    seen = {}
    monkeypatch.setattr(deep_report, "generate", _cli_fake_generate(seen, _BRIEF))
    monkeypatch.setattr(_sys, "argv", ["deep_report.py", "600150", "--no-verify",
                                       "--output-dir", str(tmp_path)])
    deep_report.main()
    assert seen["bear"] is True
    assert len(list(tmp_path.glob("600150-*-deep-bear.md"))) == 1
    assert "bear brief: 1 dated events" in capsys.readouterr().err


def test_cli_warns_when_bear_on_but_no_brief(monkeypatch, tmp_path, capsys):
    import sys as _sys
    monkeypatch.setattr(deep_report, "generate", _cli_fake_generate({}))
    monkeypatch.setattr(_sys, "argv", ["deep_report.py", "600150", "--no-verify",
                                       "--output-dir", str(tmp_path)])
    deep_report.main()
    assert "drafted WITHOUT bear research" in capsys.readouterr().err


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


# --------------------------------------------------------------------------- #
# Truncation feedback (2026-10-13, 688018: a revision cut off at max_tokens was
# published as the report — nothing passed the stop reason along)
# --------------------------------------------------------------------------- #
_GOOD_DRAFT = "# 测试（000001）深度研究报告 · 评级 3/5\n" + "正文" * 2000


def test_ensure_full_draft_re_asks_when_the_draft_was_cut_off():
    calls = []

    def rerun(attempt):
        calls.append(attempt)
        return _GOOD_DRAFT, [], False

    text, _ = deep_report._ensure_full_draft(_GOOD_DRAFT + "截断", [], rerun, truncated=True)
    assert calls == [0]
    assert text == _GOOD_DRAFT


def test_ensure_full_draft_refuses_a_draft_cut_off_every_time():
    import pytest
    with pytest.raises(RuntimeError, match="cut off"):
        deep_report._ensure_full_draft(_GOOD_DRAFT, [], lambda a: (_GOOD_DRAFT, [], True),
                                       truncated=True)


def test_ensure_full_draft_takes_a_complete_retry_over_a_longer_cut_off_one():
    retries = [(_GOOD_DRAFT * 2, [], True), (_GOOD_DRAFT, [], False)]
    text, _ = deep_report._ensure_full_draft(
        _GOOD_DRAFT, [], lambda a: retries[a], truncated=True)
    assert text == _GOOD_DRAFT


def test_revise_runner_passes_the_stop_reason(monkeypatch):
    def fake(*a, meta=None, **k):
        meta.update(stop_reason="length", truncated=True)
        return "修订稿", 1, 1, 1

    monkeypatch.setattr(deep_report, "_run_writer_pass", fake)
    rev, _judge, _cl = deep_report._make_runners(
        "openai", object(), "m", [], {"in": 0, "out": 0, "rounds": 0})
    assert rev("p")[4] == "length"


def test_cleanup_runner_reports_length_finish():
    calls = []
    _rev, _judge, cleanup = deep_report._make_runners(
        "openai", _capturing_openai(calls, finish_reason="length"), "gpt-5.4", [],
        {"in": 0, "out": 0, "rounds": 0})
    assert cleanup("p")[3] == "length"


def test_cleanup_gets_a_long_timeout_and_the_judge_keeps_the_short_one():
    """At MAX_TOKENS the non-streaming cleanup can write a whole report; 120s
    would time it out three times and crash verify into the UNVERIFIED path."""
    import llm_client
    calls = []
    _rev, judge, cleanup = deep_report._make_runners(
        "openai", _capturing_openai(calls), "deepseek-v4-pro", [],
        {"in": 0, "out": 0, "rounds": 0})
    judge("p")
    cleanup("p")
    assert calls[0]["timeout"] == llm_client.GPT_TIMEOUT
    assert calls[1]["timeout"] == deep_report.CLEANUP_TIMEOUT
    assert calls[1]["max_tokens"] == deep_report.MAX_TOKENS


# --------------------------------------------------------------------------- #
# Scoring equation (docs/deep_report_scoring/): the writer scores F/V/M/R in a
# ```scorecard block; code computes W, band, direction and stamps the report.
# --------------------------------------------------------------------------- #
def _flat(x):
    """All four sub-scores equal → W == x (the weights sum to 1)."""
    return {"F": x, "V": x, "M": x, "R": x}


@pytest.mark.parametrize("x, W, band", [
    (8.5, 8.5, 5), (8.45, 8.5, 5), (8.44, 8.4, 4),
    (7.0, 7.0, 4), (6.95, 7.0, 4), (6.94, 6.9, 3),
    (5.5, 5.5, 3), (5.45, 5.5, 3), (5.44, 5.4, 2),
    (4.0, 4.0, 2), (3.95, 4.0, 2), (3.94, 3.9, 1),
    (10, 10.0, 5), (0, 0.0, 1),
])
def test_compute_rating_band_edges_use_rounded_W(x, W, band):
    got_W, got_band, _ = deep_report.compute_rating(_flat(x))
    assert (got_W, got_band) == (W, band)


def test_compute_rating_weights_through_the_equation():
    # 0.35·7.5 + 0.25·5 + 0.25·6.5 + 0.15·6 = 6.4
    assert deep_report.compute_rating(
        {"F": 7.5, "V": 5.0, "M": 6.5, "R": 6.0}) == (6.4, 3, "看多")
    # 0.35·8 + 0.25·7 + 0.25·7 + 0.15·6 = 7.2 → 4/5
    assert deep_report.compute_rating({"F": 8, "V": 7, "M": 7, "R": 6}) == (7.2, 4, "看多")


@pytest.mark.parametrize("F, M, direction", [
    (6, 5, "看多"), (9, 9, "看多"),
    (6, 4.9, "中性"), (5.9, 9, "中性"), (4.1, 2, "中性"),
    (4, 9, "看空"), (0, 0, "看空"),
])
def test_compute_rating_direction_rules(F, M, direction):
    assert deep_report.compute_rating({"F": F, "V": 5, "M": M, "R": 5})[2] == direction


def test_compute_rating_bearish_can_pair_with_band_4():
    """Documented, flagged to owner (DECISIONS D4): F<=4 means 看空 even when
    high V/M/R lift W into band 4. Assert what the equation gives."""
    W, band, direction = deep_report.compute_rating({"F": 4, "V": 10, "M": 10, "R": 10})
    assert (W, band, direction) == (7.9, 4, "看空")


_CARD_JSON = {"F": 7.5, "F_anchor": "8: 利润加速——净利+35%", "V": 5, "V_anchor": "4: 分位77%",
              "M": 6.5, "M_anchor": "6: RPS20=23", "R": 6.0, "R_anchor": "6: 现金流待验证"}


def _block(obj) -> str:
    body = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return f"```scorecard\n{body}\n```\n"


def test_extract_scorecard_valid_block_is_stripped():
    text = "# 报告\n正文。\n\n" + _block(_CARD_JSON) + "```predictions\n[]\n```\n"
    card, err, rest = deep_report.extract_scorecard_block(text)
    assert err is None
    assert card["F"] == 7.5 and card["V"] == 5.0 and isinstance(card["V"], float)
    assert card["M_anchor"] == "6: RPS20=23"
    assert "scorecard" not in rest and "```predictions" in rest and "正文。" in rest


@pytest.mark.parametrize("block, err", [
    ("", "missing"),
    (_block("{not json"), "bad json"),
    (_block("[1, 2]"), "bad json"),
    (_block({k: v for k, v in _CARD_JSON.items() if k != "M"}), "missing key M"),
    (_block({**_CARD_JSON, "V": 10.5}), "V not a number in [0,10]"),
    (_block({**_CARD_JSON, "R": -1}), "R not a number in [0,10]"),
    (_block({**_CARD_JSON, "F": "7"}), "F not a number in [0,10]"),
    (_block({**_CARD_JSON, "F": True}), "F not a number in [0,10]"),
    (_block('{"F": NaN, "F_anchor": "x", "V": 5, "V_anchor": "x", "M": 5, '
            '"M_anchor": "x", "R": 5, "R_anchor": "x"}'), "F not a number in [0,10]"),
    (_block({**_CARD_JSON, "R_anchor": "  "}), "R_anchor empty"),
    (_block({k: v for k, v in _CARD_JSON.items() if k != "V_anchor"}), "V_anchor empty"),
])
def test_extract_scorecard_errors(block, err):
    card, got, rest = deep_report.extract_scorecard_block("# 报告\n正文。\n" + block)
    assert card is None and got == err
    assert "```scorecard" not in rest


def test_extract_scorecard_two_blocks_last_wins_all_stripped():
    text = ("# 报告\n" + _block({**_CARD_JSON, "F": 1}) + "正文。\n"
            + _block({**_CARD_JSON, "F": 9}))
    card, err, rest = deep_report.extract_scorecard_block(text)
    assert err is None and card["F"] == 9.0
    assert "scorecard" not in rest and "正文。" in rest


def test_extract_scorecard_strip_keeps_a_blank_line_before_the_footer():
    """A block glued to the line above must not turn that line into a setext
    H2 over the verify footer's ---."""
    _c, _e, rest = deep_report.extract_scorecard_block(
        "末行。\n" + _block(_CARD_JSON) + "\n---\n数据核验：0处数字。")
    assert "末行。\n\n---" in rest


_RATING = (7.2, 4, "看多")


def test_stamp_rating_fills_tokens():
    text = "# 甲（000001）深度研究报告 · {{评级}}\n**结论：{{评级}}（龙头）**\n正文\n"
    out = deep_report.stamp_rating(text, _RATING)
    assert out.splitlines()[0] == "# 甲（000001）深度研究报告 · 评级 4/5（W=7.2）"
    assert out.splitlines()[1] == "**结论：看多 ｜ 评级 4/5（W=7.2）（龙头）**"
    assert "{{评级}}" not in out and out.count("结论") == 1


def test_stamp_rating_formats_whole_W_with_one_decimal():
    out = deep_report.stamp_rating("# 甲 · {{评级}}\n**结论：{{评级}}**\n", (7.0, 4, "中性"))
    assert "评级 4/5（W=7.0）" in out.splitlines()[0]


def test_stamp_rating_inserts_verdict_when_token_lost():
    # a revision dropped the 结论 token; the H1 still has its own
    text = "# 甲深度研究报告 · {{评级}}\n## 1. 核心观点\n结论：看多，理由如下。\n"
    out = deep_report.stamp_rating(text, _RATING)
    lines = out.splitlines()
    assert lines[0] == "# 甲深度研究报告 · 评级 4/5（W=7.2）"
    assert lines[1] == "**结论：看多 ｜ 评级 4/5（W=7.2）**"
    assert lines[2] == "" and lines[3] == "## 1. 核心观点"


def test_stamp_rating_finds_h1_under_a_banner_and_appends_when_no_suffix():
    text = "> ⚠️ **数据核验中断**\n\n# 甲深度研究报告\n正文\n"
    out = deep_report.stamp_rating(text, _RATING)
    lines = out.splitlines()
    assert lines[0].startswith("> ⚠️")
    assert lines[2] == "# 甲深度研究报告 · 评级 4/5（W=7.2）"
    assert lines[3] == "**结论：看多 ｜ 评级 4/5（W=7.2）**"


def test_stamp_rating_replaces_model_written_ratings(capsys):
    # legacy-shaped draft: the writer wrote its own 3/5 in the H1, 结论 and prose
    text = ("# 甲深度研究报告 · 评级 3/5\n**结论：看多 ｜ 评级 3/5（龙头）**\n"
            "我们给予评级 3／5。\n")
    out = deep_report.stamp_rating(text, _RATING)
    lines = out.splitlines()
    assert lines[0] == "# 甲深度研究报告 · 评级 4/5（W=7.2）"
    assert lines[1] == "**结论：看多 ｜ 评级 4/5（W=7.2）**"   # no 结论 carried the stamp
    assert lines[3] == "**结论：看多 ｜ 评级 4/5（龙头）**"     # leftover → computed band
    assert "评级 3" not in out and "我们给予评级 4/5。" in out
    assert "writer wrote its own 评级 N/5 3×" in capsys.readouterr().err


def test_stamp_rating_does_not_warn_on_its_own_stamp(capsys):
    deep_report.stamp_rating("# 甲 · {{评级}}\n**结论：{{评级}}**\n", _RATING)
    assert "writer wrote" not in capsys.readouterr().err


def test_stamp_rating_none_is_visible_never_a_number(capsys):
    import re
    text = "# 甲深度研究报告 · {{评级}}\n**结论：{{评级}}（龙头）**\n给予评级 4/5。\n"
    out = deep_report.stamp_rating(text, None, "missing")
    lines = out.splitlines()
    assert lines[0] == "# 甲深度研究报告 · 评级 无法计算（scorecard missing）"
    assert lines[1] == "**结论：方向 无法计算 ｜ 评级 无法计算（scorecard missing）（龙头）**"
    assert "给予评级 无法计算。" in out
    assert not re.search(r"[1-5]\s*/\s*5", out)
    assert "writer wrote" in capsys.readouterr().err


def test_stamp_rating_none_inserts_verdict_when_token_lost():
    out = deep_report.stamp_rating("# 甲深度研究报告\n正文\n", None, "bad json")
    assert out.splitlines()[1] == "**结论：方向 无法计算 ｜ 评级 无法计算（scorecard bad json）**"


def test_generate_stamps_rating_from_the_scorecard(monkeypatch):
    _openai_fakes(monkeypatch, [(_ok_draft(), 1, 2, 1)])
    res = deep_report.generate("000703", provider="openai", data={"code": "000703.SZ"},
                               verify=False, bear=False)
    assert res["text"].splitlines()[0] == "# 测试（000703）深度研究报告 · 评级 3/5（W=6.4）"
    assert f"**结论：{_CARD_STAMP}（测试）**" in res["text"]
    assert "```scorecard" not in res["text"] and "{{评级}}" not in res["text"]
    assert res["rating"] == {"W": 6.4, "band": 3, "direction": "看多"}
    assert res["scorecard"]["F"] == 7.5 and res["scorecard_error"] is None


def test_generate_without_scorecard_publishes_visible_unrated(monkeypatch):
    _openai_fakes(monkeypatch, [(_ok_draft(card=""), 1, 2, 1)])
    res = deep_report.generate("000703", provider="openai", data={"code": "000703.SZ"},
                               verify=False, bear=False)
    assert "评级 无法计算（scorecard missing）" in res["text"].splitlines()[0]
    assert res["rating"] is None and res["scorecard"] is None
    assert res["scorecard_error"] == "missing"


def test_generate_retry_scorecard_replaces_a_missing_one(monkeypatch):
    _openai_fakes(monkeypatch, [("太短", 1, 1, 1), (_ok_draft(), 1, 2, 1)])
    res = deep_report.generate("000703", provider="openai", data={"code": "000703.SZ"},
                               verify=False, bear=False)
    assert res["rating"]["band"] == 3 and res["scorecard_error"] is None


def test_generate_draft_scorecard_stands_over_a_revise_re_emission(monkeypatch):
    import deep_verify
    _openai_fakes(monkeypatch, [(_ok_draft(), 1, 2, 1)])
    seen = {}

    def fake_pipeline(draft, data, **kw):
        seen["draft"] = draft
        # a revise pass re-emitted a different scorecard (F=1 → 看空)
        return ("# 测试（000703）深度研究报告 · {{评级}}\n**结论：{{评级}}（测试）**\n正文。\n"
                + _block({**_CARD_JSON, "F": 1}) + "\n---\n数据核验：0处数字。\n", {"rounds": []})

    monkeypatch.setattr(deep_verify, "run_pipeline", fake_pipeline)
    res = deep_report.generate("000703", provider="openai", data={"code": "000703.SZ"},
                               verify=True, bear=False)
    # the verifier saw the placeholder, never the stamped W or the scorecard
    assert "{{评级}}" in seen["draft"] and "W=" not in seen["draft"]
    assert "```scorecard" not in seen["draft"]
    assert res["rating"] == {"W": 6.4, "band": 3, "direction": "看多"}
    assert f"**结论：{_CARD_STAMP}（测试）**" in res["text"]
    assert "```scorecard" not in res["text"] and "正文。\n\n---" in res["text"]


def test_log_scorecard_writes_a_row(tmp_path):
    path = tmp_path / "sub" / "scorecards.jsonl"
    result = {"scorecard": {"F": 7.5, "V": 5.0, "M": 6.5, "R": 6.0, "F_anchor": "a"},
              "rating": {"W": 6.5, "band": 3, "direction": "看多"},
              "provider": "anthropic", "model": "claude-fable-5"}
    deep_report.log_scorecard("002293.SZ", result, "/r/002293-deep.md", path=path)
    deep_report.log_scorecard("002293", {"scorecard_error": "bad json",
                                         "provider": "openai", "model": "m"}, "/r/x.md", path=path)
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()]
    assert rows[0] == {"date": rows[0]["date"], "code": "002293", "F": 7.5, "V": 5.0,
                       "M": 6.5, "R": 6.0, "W": 6.5, "band": 3, "direction": "看多",
                       "provider": "anthropic", "model": "claude-fable-5",
                       "report": "/r/002293-deep.md"}
    assert rows[1]["error"] == "bad json"
    assert all(rows[1][k] is None for k in ("F", "V", "M", "R", "W", "band", "direction"))


def test_cli_logs_scorecard_and_prints_rating(monkeypatch, tmp_path, capsys):
    import sys as _sys

    def fake(code, **kw):
        return {"text": "# R", "tool_calls": [], "input_tokens": 1, "output_tokens": 1,
                "rounds": 1, "provider": "openai", "model": "m", "data": {},
                "verify_audit": None, "verify_rounds": 0,
                "scorecard": {"F": 8, "V": 7, "M": 7, "R": 6},
                "scorecard_error": None,
                "rating": {"W": 7.2, "band": 4, "direction": "看多"}}

    monkeypatch.setattr(deep_report, "generate", fake)
    monkeypatch.setattr(_sys, "argv", ["deep_report.py", "600150", "--no-verify",
                                       "--no-bear", "--output-dir", str(tmp_path)])
    deep_report.main()
    assert "[deep_report] rating: 4/5 W=7.2 看多" in capsys.readouterr().err
    row = json.loads(deep_report.SCORECARD_LOG.read_text(encoding="utf-8"))
    assert row["code"] == "600150" and row["band"] == 4
    assert row["report"].endswith("-deep.md")


def test_cli_warns_and_logs_when_rating_missing(monkeypatch, tmp_path, capsys):
    import sys as _sys
    monkeypatch.setattr(deep_report, "generate", _cli_fake_generate({}))
    monkeypatch.setattr(_sys, "argv", ["deep_report.py", "600150", "--no-verify",
                                       "--no-bear", "--output-dir", str(tmp_path)])
    deep_report.main()
    assert "⚠️ rating: 无法计算 (missing)" in capsys.readouterr().err
    row = json.loads(deep_report.SCORECARD_LOG.read_text(encoding="utf-8"))
    assert row["error"] == "missing" and row["W"] is None
