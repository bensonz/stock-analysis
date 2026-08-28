"""The four things called "the MA rule" must stop contradicting each other.

Investigation on 2026-08-28 (docs/audits/CANDIDATE_ALPHA.md) found four separate
rules sharing that name:

  1. rps>=80 AND MA20>MA120>MA250  — data_collector.fetch_strategy_pool_local(),
     which CLAUDE.md called "the real tradeable filter" and which nothing called.
  2. rps60/120/250 > 85, no MA     — run_daily._build_strategy_intersection(),
     the gate that actually runs.
  3. abs(dist_ma) > band -> ❌      — report_generator, a display label only.
  4. dist_ma5 > +6% -> SKIP        — ANALYST.md Rule 2b, one-sided, LLM-enforced.

(3) and (4) disagree about sign: a stock 25% BELOW its MA5 was marked ❌ under a
rule written to catch stocks far ABOVE. The label filters nothing, so the LLM —
which reads raw distances — obeyed Rule 2b perfectly (0 violations in 52 matched
entries) while 13 entries came off rows the label had condemned. Those 13 did
badly (20d −9.67%, beat-index 22.2%, n=9), so the below-band signal is worth
keeping; it just is not what Rule 2b means.

These tests pin the reconciliation, not the numbers behind it:
❌ keeps its Rule 2b meaning, 🔻 carries the distinct below-band warning, the set
of names treated as actionable does not move, and the over-extension the spec
already mandates becomes visible in the prompt instead of being re-derived from
a bare RPS number every run.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import data_collector
import llm_client
import report_generator
import run_daily


def _pool(**over):
    stock = {"code": "000001", "name": "试验", "rps120": 88, "rps60": 85,
             "dist_ma5_pct": 0.5, "dist_ma10_pct": 0.5, "dist_ma20_pct": 0.5}
    stock.update(over)
    return {"strategy_pool": {"stocks": [stock]}, "ma_data": {}, "enriched": [],
            "entry_regime": {}}


def status_for(tmp_path, **over):
    """The Status cell report_generator assigns to a single pool row."""
    p = report_generator.generate_candidates_md("2026-08-28", _pool(**over),
                                                output_dir=tmp_path)
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("| 000001 "):
            return [c.strip() for c in line.strip().strip("|").split("|")][-1]
    raise AssertionError("row not rendered")


# --- Change 3: the label splits by side -------------------------------------

def test_far_above_the_band_is_the_rule_2b_violation(tmp_path):
    """Rule 2b's actual subject: 'a stock that just spiked far above its MAs'."""
    assert status_for(tmp_path, dist_ma5_pct=25.0).startswith("❌")


def test_far_below_the_band_gets_its_own_marker(tmp_path):
    """Not chasing — a broken trend. Conflating the two is what made the label
    contradict the spec."""
    st = status_for(tmp_path, dist_ma5_pct=-25.0)
    assert st.startswith("🔻"), st


def test_inside_the_band_still_passes(tmp_path):
    assert status_for(tmp_path, dist_ma5_pct=1.0).startswith("✅")


def test_chasing_wins_when_a_stock_is_above_on_one_ma_and_below_another(tmp_path):
    """Rule 2b is the one the spec marks NON-NEGOTIABLE, so it takes precedence."""
    st = status_for(tmp_path, dist_ma5_pct=25.0, dist_ma20_pct=-30.0)
    assert st.startswith("❌"), st


def test_the_marker_names_which_mas_were_breached(tmp_path):
    """'🔻 BELOW MA5,MA20' has to stay diagnosable, like '❌ MA5,MA10'."""
    st = status_for(tmp_path, dist_ma5_pct=-25.0, dist_ma20_pct=-30.0)
    assert "MA5" in st and "MA20" in st and "MA10" not in st


def test_missing_ma_data_is_still_its_own_state(tmp_path):
    """⚠️ no MA predates this split and must not be swallowed by 🔻."""
    st = status_for(tmp_path, dist_ma5_pct=None, dist_ma10_pct=None,
                    dist_ma20_pct=None)
    assert st.startswith("⚠️"), st


# --- Change 3: what counts as actionable must NOT move ----------------------

def test_below_band_names_stay_out_of_sweet_spot_and_wait_list(tmp_path):
    """The label changes; the set of tradeable names does not. Before the split
    these rows were ❌ and excluded from both summaries — that must hold."""
    p = report_generator.generate_candidates_md(
        "2026-08-28", _pool(dist_ma5_pct=-25.0), output_dir=tmp_path)
    body = p.read_text(encoding="utf-8")
    assert "## Sweet Spot" not in body
    assert "## Wait List" not in body


def test_an_over_95_name_inside_the_band_is_still_the_wait_list(tmp_path):
    p = report_generator.generate_candidates_md(
        "2026-08-28", _pool(rps120=99, dist_ma5_pct=1.0), output_dir=tmp_path)
    body = p.read_text(encoding="utf-8")
    assert "## Wait List" in body and "## Sweet Spot" not in body


# --- Change 1: over-extension is visible in the prompt ----------------------

def _prompt_pool_rows(rps120):
    text = llm_client.build_summary({
        "strategy_pool": {"stocks": [{"code": "000001", "name": "试验",
                                      "rps120": rps120, "rps20": 50}]}})
    return [ln for ln in text.splitlines() if ln.startswith("| 000001 ")]


def test_over_extended_names_are_flagged_in_the_prompt():
    """ANALYST.md Rule 2 already says 'Above 95%: Skip' and calls the cap
    empirically load-bearing. The prompt showed a bare number and left the model
    to re-derive that every run."""
    row = _prompt_pool_rows(99)[0]
    assert "OVER-EXTENDED" in row


def test_ninety_five_exactly_is_not_flagged():
    """Rule 2 says 'Above 95%', so 95.0 is inside the band. An off-by-one here
    would silently move a documented threshold."""
    assert "OVER-EXTENDED" not in _prompt_pool_rows(95.0)[0]


def test_a_normal_name_carries_no_flag_text():
    assert "OVER-EXTENDED" not in _prompt_pool_rows(88)[0]


# The table above is build_summary(), which only the HYBRID provider's Pass 2
# uses. The live `openai` path builds prompt.md in run_daily.phase2_build_prompt
# as ANALYST.md + json.dumps(payload), where pool stocks are raw dicts — so the
# flag has to ride as a FIELD there. Flagging only the table would have shipped
# a change that never reached the running provider (caught 2026-08-28, after the
# first live run showed no `## Strategy Pool` section in prompt.md at all).
#
# phase2_build_prompt writes to the live run dir and rewrites positions.json, so
# it must never be called with synthetic data; the flagging is a pure helper.

def test_the_live_payload_flags_over_extended_stocks():
    got = run_daily.flag_over_extended([
        {"code": "000001", "rps120": 99.0},
        {"code": "000002", "rps120": 88.0},
    ])
    assert got[0]["rule2_over_extended"] is True
    assert got[1]["rule2_over_extended"] is False


def test_the_live_payload_uses_the_same_boundary_as_rule_2():
    """'Above 95%' — 95.0 exactly is inside the band, in both renderings."""
    got = run_daily.flag_over_extended([{"code": "000001", "rps120": 95.0}])
    assert got[0]["rule2_over_extended"] is False


def test_a_missing_rps_is_not_silently_called_safe():
    """Absent RPS must not read as 'fine' — that is how a data gap becomes an
    unflagged buy. It gets None, which is visibly not False."""
    got = run_daily.flag_over_extended([{"code": "000001"}])
    assert got[0]["rule2_over_extended"] is None


def test_flagging_does_not_mutate_the_caller_s_stocks():
    """The same dicts feed candidates.md and the run artifacts; stamping a
    prompt-only field onto them in place would leak into both."""
    original = [{"code": "000001", "rps120": 99.0}]
    run_daily.flag_over_extended(original)
    assert "rule2_over_extended" not in original[0]


# --- Change 2: the local pool becomes an outage fallback --------------------

def test_an_empty_crawl_falls_back_to_the_local_pool(monkeypatch):
    """2026-08-25: the crawl failed outright and the run died at Gate 1 with an
    empty pool while a usable local price DB sat right there."""
    monkeypatch.setattr(run_daily, "fetch_strategy_pool",
                        lambda *a, **k: {"stocks": [], "error": "API down"})
    monkeypatch.setattr(data_collector, "fetch_strategy_pool_local",
                        lambda *a, **k: {"stocks": [{"code": "000001"}],
                                         "source": "local_pricedb"})
    debug = {"fallback": {"used": False}}
    got = run_daily.fetch_strategy_pool_with_fallback(debug)
    assert [s["code"] for s in got["stocks"]] == ["000001"]
    assert debug["fallback"]["used"] is True
    assert "API down" in str(debug["fallback"].get("reason", ""))


def test_a_healthy_crawl_never_touches_the_local_path(monkeypatch):
    """The fallback is an outage measure, not a second opinion. The two paths
    use different gates (local >=80 + MA alignment vs live >85), so firing it on
    a normal day would silently change what gets admitted."""
    called = []
    monkeypatch.setattr(run_daily, "fetch_strategy_pool",
                        lambda *a, **k: {"stocks": [{"code": "600000"}]})
    monkeypatch.setattr(data_collector, "fetch_strategy_pool_local",
                        lambda *a, **k: called.append(1) or {"stocks": []})
    debug = {"fallback": {"used": False}}
    got = run_daily.fetch_strategy_pool_with_fallback(debug)
    assert [s["code"] for s in got["stocks"]] == ["600000"]
    assert called == []
    assert debug["fallback"]["used"] is False


def test_a_fallback_that_also_fails_preserves_the_original_cause(monkeypatch):
    """A stale pricedb must not overwrite 'the crawl was down' — the first
    failure is the one worth debugging."""
    def boom(*a, **k):
        raise RuntimeError("local pricedb is stale: latest=2026-08-20")

    monkeypatch.setattr(run_daily, "fetch_strategy_pool",
                        lambda *a, **k: {"stocks": [], "error": "API down"})
    monkeypatch.setattr(data_collector, "fetch_strategy_pool_local", boom)
    debug = {"fallback": {"used": False}}
    got = run_daily.fetch_strategy_pool_with_fallback(debug)
    assert got["stocks"] == []
    assert "API down" in got["error"]
    assert debug["fallback"]["used"] is False
    assert "stale" in str(debug["fallback"].get("error", ""))
