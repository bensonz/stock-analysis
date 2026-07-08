"""
Tests for pipeline contracts and gates.

Run: python -m pytest tests/test_contracts.py -v
Or:  python tests/test_contracts.py
"""

import json
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest
from contracts import (
    PipelineGate,
    PipelineStatus,
    RunManifest,
    validate_phase1_gate,
    validate_llm_output_gate,
    validate_phase3_gate,
    _is_trading_day_recent,
    _is_today,
)
from datetime import datetime, timedelta


# ─── Helpers ───

def make_position_prices(*codes, source="sina", error=None):
    """Build a position_prices dict for testing."""
    prices = {}
    today = datetime.now().strftime("%Y-%m-%d")
    for code in codes:
        if error:
            prices[code] = {"code": code, "error": error}
        else:
            prices[code] = {
                "code": code,
                "name": f"Test_{code}",
                "date": today,
                "price": 100.0,
                "open": 99.0,
                "high": 101.0,
                "low": 98.0,
                "prev_close": 99.5,
                "change_pct": 0.5,
                "volume": 50000,
                "mavol30": 60000.0,
                "source": source,
            }
    return prices


def make_positions(*codes):
    """Build a positions list for testing."""
    return [{"code": code, "name": f"Test_{code}"} for code in codes]


def make_market(indices_ok=True, breadth_ok=True, breadth_total=5000):
    """Build a market dict for testing."""
    today = datetime.now().strftime("%Y-%m-%d")
    market = {}
    if indices_ok:
        market["indices"] = {
            "上证指数": {"code": "sh000001", "close": 3200.0, "change_pct": -0.5, "date": today},
            "深证成指": {"code": "sz399001", "close": 11000.0, "change_pct": 0.3, "date": today},
            "创业板指": {"code": "sz399006", "close": 2300.0, "change_pct": -0.2, "date": today},
        }
    else:
        market["indices"] = {
            "上证指数": {"error": "fetch failed"},
        }
    if breadth_ok:
        market["breadth"] = {"up": 2000, "down": 2500, "flat": 100, "total": breadth_total}
    else:
        market["breadth"] = {}
    return market


def make_pool(total=10, date=None, error=None):
    """Build a strategy_pool dict for testing."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    stocks = [{"code": f"{600000+i}", "name": f"Stock_{i}", "rps120": 85.0, "price": 50.0}
              for i in range(total)]
    return {
        "source": "test",
        "strategy_id": "test",
        "date": date,
        "total_stocks": total,
        "stocks": stocks,
        "error": error,
    }


def make_phase1_data(
    position_codes=None,
    price_error=None,
    indices_ok=True,
    breadth_ok=True,
    breadth_total=5000,
    pool_total=10,
    pool_date=None,
    pool_error=None,
    iv_error=None,
):
    """Build a complete Phase 1 data dict for testing."""
    codes = position_codes or []
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "positions": make_positions(*codes),
        "position_prices": make_position_prices(*codes, error=price_error) if codes else {},
        "market": make_market(indices_ok=indices_ok, breadth_ok=breadth_ok, breadth_total=breadth_total),
        "strategy_pool": make_pool(total=pool_total, date=pool_date, error=pool_error),
        "enriched": [],
        "iv_sentiment": {"error": iv_error} if iv_error else {"overall_sentiment": {"signal": "中性"}},
    }
    return data


# ━━━ PipelineGate unit tests ━━━

class TestPipelineGate:
    def test_empty_gate_passes(self):
        gate = PipelineGate("test")
        result = gate.check()
        assert result.passed is True
        assert result.hard_fails == []
        assert result.soft_warns == []

    def test_soft_warn_still_passes(self):
        gate = PipelineGate("test")
        gate.soft(False, "this is a warning")
        result = gate.check()
        assert result.passed is True
        assert len(result.soft_warns) == 1

    def test_hard_fail_blocks(self):
        gate = PipelineGate("test")
        gate.hard(False, "critical failure")
        result = gate.check()
        assert result.passed is False
        assert len(result.hard_fails) == 1

    def test_hard_pass_when_true(self):
        gate = PipelineGate("test")
        gate.hard(True, "should not appear")
        result = gate.check()
        assert result.passed is True
        assert result.hard_fails == []

    def test_multiple_failures(self):
        gate = PipelineGate("test")
        gate.hard(False, "fail 1")
        gate.hard(False, "fail 2")
        gate.soft(False, "warn 1")
        result = gate.check()
        assert result.passed is False
        assert len(result.hard_fails) == 2
        assert len(result.soft_warns) == 1


# ━━━ Date freshness tests ━━━

class TestDateFreshness:
    def test_today_is_fresh(self):
        today = datetime.now().strftime("%Y-%m-%d")
        assert _is_trading_day_recent(today) is True

    def test_yesterday_is_fresh(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        assert _is_trading_day_recent(yesterday) is True

    def test_4_days_ago_is_fresh(self):
        """Long weekends can cause 3-4 day gaps."""
        four_ago = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")
        assert _is_trading_day_recent(four_ago) is True

    def test_5_days_ago_is_stale(self):
        five_ago = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        assert _is_trading_day_recent(five_ago) is False

    def test_empty_string_is_not_fresh(self):
        assert _is_trading_day_recent("") is False

    def test_none_is_not_fresh(self):
        assert _is_trading_day_recent(None) is False

    def test_slash_format(self):
        today = datetime.now().strftime("%Y/%m/%d")
        assert _is_trading_day_recent(today) is True

    def test_is_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        assert _is_today(today) is True

    def test_yesterday_is_not_today(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        assert _is_today(yesterday) is False


# ━━━ Gate 1: Phase 1 → Phase 2 ━━━

class TestPhase1Gate:
    """Gate 1 validates Phase 1 data collection output."""

    def test_clean_data_passes(self):
        """Perfect data -> gate passes with no warnings."""
        data = make_phase1_data(position_codes=["605167", "688037"])
        result = validate_phase1_gate(data)
        assert result.passed is True
        assert result.hard_fails == []

    def test_no_positions_passes(self):
        """No active positions -> gate passes (nothing to price)."""
        data = make_phase1_data(position_codes=[])
        result = validate_phase1_gate(data)
        assert result.passed is True

    def test_position_price_error_hard_fails(self):
        """Position with price error -> hard failure."""
        data = make_phase1_data(position_codes=["605167"], price_error="No kline data")
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert any("605167" in f and "No kline data" in f for f in result.hard_fails)

    def test_position_price_zero_hard_fails(self):
        """Position with price=0 -> hard failure."""
        data = make_phase1_data(position_codes=["605167"])
        data["position_prices"]["605167"]["price"] = 0
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert any("invalid price=0" in f for f in result.hard_fails)

    def test_position_price_none_hard_fails(self):
        """Position with price=None -> hard failure."""
        data = make_phase1_data(position_codes=["605167"])
        data["position_prices"]["605167"]["price"] = None
        result = validate_phase1_gate(data)
        assert result.passed is False

    def test_position_prices_empty_with_positions_hard_fails(self):
        """Active positions but empty price dict -> hard failure."""
        data = make_phase1_data(position_codes=["605167"])
        data["position_prices"] = {}
        result = validate_phase1_gate(data)
        assert result.passed is False

    def test_two_of_three_indices_ok(self):
        """2/3 indices valid -> passes."""
        data = make_phase1_data()
        del data["market"]["indices"]["创业板指"]
        result = validate_phase1_gate(data)
        assert result.passed is True

    def test_one_of_three_indices_hard_fails(self):
        """Only 1/3 indices valid -> hard failure."""
        data = make_phase1_data(indices_ok=False)
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert any("indices" in f.lower() for f in result.hard_fails)

    def test_breadth_too_low_hard_fails(self):
        """Breadth total < 1000 -> hard failure (broken data)."""
        data = make_phase1_data(breadth_total=500)
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert any("breadth" in f.lower() for f in result.hard_fails)

    def test_breadth_missing_hard_fails(self):
        """No breadth data -> hard failure."""
        data = make_phase1_data(breadth_ok=False)
        result = validate_phase1_gate(data)
        assert result.passed is False

    def test_pool_stale_date_hard_fails(self):
        """Pool has stocks but date is 10 days old -> hard failure."""
        stale = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        data = make_phase1_data(pool_date=stale, pool_total=5)
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert any("stale" in f.lower() for f in result.hard_fails)

    def test_pool_yesterday_soft_warns(self):
        """Pool date is yesterday (not today) -> soft warning, not hard fail.
        This is common when pricedb hasn't updated yet."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        data = make_phase1_data(pool_date=yesterday, pool_total=5)
        result = validate_phase1_gate(data)
        assert result.passed is True  # Soft warn, not hard fail
        assert any("not today" in w.lower() for w in result.soft_warns)

    def test_pool_empty_soft_warns(self):
        """Empty pool -> soft warning (can be legitimate on weak days)."""
        data = make_phase1_data(pool_total=0)
        result = validate_phase1_gate(data)
        assert result.passed is True
        assert any("empty" in w.lower() for w in result.soft_warns)

    def test_pool_error_soft_warns(self):
        """Pool with error -> soft warning."""
        data = make_phase1_data(pool_error="API timeout")
        result = validate_phase1_gate(data)
        assert result.passed is True
        assert any("API timeout" in w for w in result.soft_warns)

    def test_iv_error_soft_warns(self):
        """IV sentiment failure -> soft warning (supplementary data)."""
        data = make_phase1_data(iv_error="timeout")
        result = validate_phase1_gate(data)
        assert result.passed is True
        assert any("IV" in w for w in result.soft_warns)

    def test_multiple_position_failures(self):
        """Multiple positions failing -> all reported."""
        data = make_phase1_data(position_codes=["605167", "688037"], price_error="No kline data")
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert len(result.hard_fails) >= 2

    def test_real_failure_scenario_20260409(self):
        """Reproduce today's actual failure: both prices missing, pool stale."""
        data = make_phase1_data(position_codes=["605167", "688037"])
        # Simulate real failure
        data["position_prices"]["605167"] = {"code": "605167", "error": "No kline data"}
        data["position_prices"]["688037"] = {"code": "688037", "error": "No kline data"}
        data["strategy_pool"]["date"] = "2026-04-08"
        data["strategy_pool"]["total_stocks"] = 0
        data["strategy_pool"]["stocks"] = []
        data["date"] = "2026-04-09"

        result = validate_phase1_gate(data)
        assert result.passed is False
        assert len(result.hard_fails) >= 2  # Both prices
        # Pool is empty (0 stocks) -> soft warn about empty, NOT hard fail about stale
        # (stale date check only applies when pool has stocks)


# ━━━ Gate 2: Phase 2 → Phase 3 ━━━

class TestLLMOutputGate:
    """Gate 2 validates LLM response before applying decisions."""

    def _make_decisions(self, position_codes=None, new_positions=None, extra=None):
        """Build a valid decisions dict."""
        decisions = {
            "market_summary": "Test summary",
            "position_decisions": [
                {"code": code, "action": "HOLD", "reason": "Above stop"}
                for code in (position_codes or [])
            ],
            "new_positions": new_positions or [],
            "skip_list": [],
            "watchlist": [],
            "new_learnings": [],
            **(extra or {}),
        }
        return decisions

    def test_valid_decisions_pass(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions(position_codes=["605167"])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True

    def test_empty_decisions_hard_fails(self):
        data = make_phase1_data(position_codes=["605167"])
        result = validate_llm_output_gate({}, data)
        assert result.passed is False

    def test_missing_position_decision_hard_fails(self):
        """Active position not in decisions -> hard fail."""
        data = make_phase1_data(position_codes=["605167", "688037"])
        decisions = self._make_decisions(position_codes=["605167"])  # Missing 688037
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("688037" in f for f in result.hard_fails)

    def test_invalid_action_hard_fails(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions()
        decisions["position_decisions"] = [
            {"code": "605167", "action": "BUY_MORE", "reason": "YOLO"}
        ]
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("BUY_MORE" in f for f in result.hard_fails)

    def test_sell_without_exit_price_hard_fails(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions()
        decisions["position_decisions"] = [
            {"code": "605167", "action": "SELL", "reason": "Stop hit"}
        ]
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("exit_price" in f for f in result.hard_fails)

    def test_sell_with_exit_price_passes(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions()
        decisions["position_decisions"] = [
            {"code": "605167", "action": "SELL", "reason": "Stop hit", "exit_price": 15.5}
        ]
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True

    def test_raise_stop_without_new_stop_hard_fails(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions()
        decisions["position_decisions"] = [
            {"code": "605167", "action": "RAISE_STOP", "reason": "Trailing"}
        ]
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("new_stop" in f for f in result.hard_fails)

    def test_raise_stop_with_valid_stop_passes(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions()
        decisions["position_decisions"] = [
            {"code": "605167", "action": "RAISE_STOP", "reason": "Trailing", "new_stop": 16.0}
        ]
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True

    def test_new_position_missing_fields_hard_fails(self):
        data = make_phase1_data()
        decisions = self._make_decisions(new_positions=[
            {"code": "600000", "name": "Test"}  # Missing entry_price, stop, target, thesis
        ])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert len(result.hard_fails) >= 3  # At least entry_price, stop, target

    def test_new_position_stop_above_entry_hard_fails(self):
        data = make_phase1_data()
        decisions = self._make_decisions(new_positions=[
            {"code": "600000", "name": "Test", "entry_price": 50.0,
             "stop": 55.0, "target": 60.0, "thesis": "Breakout"}
        ])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("stop" in f and "entry_price" in f for f in result.hard_fails)

    def test_valid_new_position_passes(self):
        data = make_phase1_data()
        decisions = self._make_decisions(new_positions=[
            {"code": "600000", "name": "Test", "entry_price": 50.0,
             "stop": 45.0, "target": 60.0, "thesis": "Breakout"}
        ])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True

    def test_missing_market_summary_soft_warns(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions(position_codes=["605167"])
        decisions["market_summary"] = ""
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True
        assert any("market_summary" in w for w in result.soft_warns)

    def test_no_positions_empty_decisions_passes(self):
        """No active positions + empty position_decisions -> passes."""
        data = make_phase1_data(position_codes=[])
        decisions = self._make_decisions(position_codes=[])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True

    def test_duplicate_decisions_hard_fails(self):
        """Two decisions for the same position -> hard fail."""
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions()
        decisions["position_decisions"] = [
            {"code": "605167", "action": "SELL", "reason": "Stop hit", "exit_price": 15.5},
            {"code": "605167", "action": "HOLD", "reason": "Changed mind"},
        ]
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("duplicate" in f.lower() for f in result.hard_fails)

    def test_duplicate_decisions_sell_hold_conflict(self):
        """SELL then HOLD for same code — must not pass Gate 2."""
        data = make_phase1_data(position_codes=["605167", "688037"])
        decisions = self._make_decisions(position_codes=["688037"])
        decisions["position_decisions"].extend([
            {"code": "605167", "action": "SELL", "reason": "Stop", "exit_price": 15.0},
            {"code": "605167", "action": "RAISE_STOP", "reason": "Oops", "new_stop": 16.0},
        ])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("605167" in f and "duplicate" in f.lower() for f in result.hard_fails)

    def test_string_typed_entry_price_hard_fails(self):
        """entry_price as string "50.0" -> hard fail (must be numeric)."""
        data = make_phase1_data()
        decisions = self._make_decisions(new_positions=[
            {"code": "600000", "name": "Test", "entry_price": "50.0",
             "stop": "45.0", "target": "60.0", "thesis": "Breakout"}
        ])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("numeric" in f.lower() and "entry_price" in f for f in result.hard_fails)

    def test_string_typed_stop_hard_fails(self):
        """stop as string -> hard fail."""
        data = make_phase1_data()
        decisions = self._make_decisions(new_positions=[
            {"code": "600000", "name": "Test", "entry_price": 50.0,
             "stop": "45.0", "target": 60.0, "thesis": "Breakout"}
        ])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("numeric" in f.lower() and "stop" in f for f in result.hard_fails)

    def test_mixed_numeric_and_string_fields(self):
        """entry_price numeric but target as string -> hard fail on target only."""
        data = make_phase1_data()
        decisions = self._make_decisions(new_positions=[
            {"code": "600000", "name": "Test", "entry_price": 50.0,
             "stop": 45.0, "target": "60.0", "thesis": "Breakout"}
        ])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("target" in f for f in result.hard_fails)
        # entry_price and stop should NOT appear in hard_fails
        assert not any("entry_price" in f for f in result.hard_fails)


# ━━━ Gate 3: Phase 3 → Phase 4 ━━━

class TestPhase3Gate:
    def test_clean_apply_passes(self):
        log = {"actions": ["HOLD 605167", "Generated report"]}
        result = validate_phase3_gate("2026-04-09", log, {})
        assert result.passed is True

    def test_error_action_hard_fails(self):
        log = {"actions": ["ERROR SELL 605167: file not found"]}
        result = validate_phase3_gate("2026-04-09", log, {})
        assert result.passed is False

    def test_price_correction_soft_warns(self):
        log = {"actions": ["PRICE_CORRECTED 605167: LLM=29.79 outside [28,31], using market=30.5"]}
        result = validate_phase3_gate("2026-04-09", log, {})
        assert result.passed is True
        assert len(result.soft_warns) == 1

    def test_volume_rule_violation_soft_warns(self):
        log = {
            "actions": ["HOLD 605167"],
            "post_apply_rule_violations": {
                "status": "violations",
                "rules": [{
                    "rule": "check_volume_below_mavol30",
                    "status": "violations",
                    "violations": [{"code": "605167", "suggestion": "Volume 21K below MAVOL30 67K"}],
                }],
            },
        }
        result = validate_phase3_gate("2026-04-09", log, {})
        assert result.passed is True
        assert len(result.soft_warns) >= 1


# ━━━ RunManifest tests ━━━

class TestRunManifest:
    def test_successful_run(self):
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        m.add_phase("collect", "ok", 13.5)
        g = PipelineGate("test")
        m.add_gate(g.check())
        m.finalize()
        assert m.status == PipelineStatus.SUCCESS
        assert m.exit_code == 0

    def test_degraded_run(self):
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        g = PipelineGate("test")
        g.soft(False, "IV failed")
        m.add_gate(g.check())
        m.finalize()
        assert m.status == PipelineStatus.DEGRADED
        assert m.exit_code == 0

    def test_failed_run(self):
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        g = PipelineGate("test")
        g.hard(False, "no prices")
        m.add_gate(g.check())
        m.finalize()
        assert m.status == PipelineStatus.FAILED
        assert m.exit_code == 1

    def test_critical_validation_error_fails_manifest(self):
        """CRITICAL errors in phase details must cause FAILED status even with passing gates."""
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        g = PipelineGate("test")
        m.add_gate(g.check())  # Gate passes
        m.add_phase("validate", "warnings", details={
            "errors": ["CRITICAL: positions.json mismatch with tracking files. Diff: {'605167'}"]
        })
        m.finalize()
        assert m.status == PipelineStatus.FAILED
        assert m.exit_code == 1

    def test_non_critical_validation_does_not_fail_manifest(self):
        """Non-CRITICAL validation warnings should not cause FAILED status."""
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        g = PipelineGate("test")
        m.add_gate(g.check())
        m.add_phase("validate", "warnings", details={
            "errors": ["WARNING: no watchlist found for 2026-04-09"]
        })
        m.finalize()
        assert m.status == PipelineStatus.SUCCESS
        assert m.exit_code == 0

    def test_to_dict_serializable(self):
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        m.finalize()
        d = m.to_dict()
        # Must be JSON-serializable
        json_str = json.dumps(d)
        assert '"success"' in json_str

    def test_slot_and_run_started_at_stamped(self):
        m = RunManifest(
            date="2026-07-08",
            status=PipelineStatus.SUCCESS,
            slot="noon",
            run_started_at="2026-07-08T11:35:00+08:00",
        )
        m.finalize()
        d = m.to_dict()
        assert d["slot"] == "noon"
        assert d["run_started_at"] == "2026-07-08T11:35:00+08:00"

    def test_slot_defaults_to_afternoon(self):
        # Legacy/back-compat: an unspecified slot self-identifies as afternoon.
        m = RunManifest(date="2026-07-08", status=PipelineStatus.SUCCESS)
        assert m.to_dict()["slot"] == "afternoon"


# ━━━ Sina price fetch tests (integration) ━━━

class TestSinaPriceFetch:
    """Integration tests for Sina price fetching.

    These tests hit the real Sina API. Skip with -m "not integration" if needed.
    They verify the Sina fallback chain actually works on this machine.
    """

    @pytest.mark.integration
    def test_fetch_shanghai_stock(self):
        """Fetch a Shanghai stock (6xxxxx) via Sina."""
        from data_collector import _fetch_position_prices_sina
        positions = [{"code": "601398", "name": "工商银行"}]  # ICBC — always available
        result = _fetch_position_prices_sina(positions)
        assert "601398" in result
        p = result["601398"]
        assert p["source"] == "sina"
        assert p["price"] > 0
        assert p["open"] > 0
        assert p["high"] >= p["low"]
        assert p["volume"] >= 0

    @pytest.mark.integration
    def test_fetch_shenzhen_stock(self):
        """Fetch a Shenzhen stock (0xxxxx) via Sina."""
        from data_collector import _fetch_position_prices_sina
        positions = [{"code": "000001", "name": "平安银行"}]
        result = _fetch_position_prices_sina(positions)
        assert "000001" in result
        assert result["000001"]["price"] > 0

    @pytest.mark.integration
    def test_fetch_star_market_stock(self):
        """Fetch a 科创板 stock (688xxx) via Sina."""
        from data_collector import _fetch_position_prices_sina
        positions = [{"code": "688037", "name": "芯源微"}]
        result = _fetch_position_prices_sina(positions)
        assert "688037" in result
        assert result["688037"]["price"] > 0

    @pytest.mark.integration
    def test_fetch_multiple_stocks(self):
        """Fetch multiple stocks in one call."""
        from data_collector import _fetch_position_prices_sina
        positions = [
            {"code": "605167", "name": "利柏特"},
            {"code": "688037", "name": "芯源微"},
        ]
        result = _fetch_position_prices_sina(positions)
        assert len(result) == 2
        for code in ["605167", "688037"]:
            assert code in result
            assert result[code]["price"] > 0

    @pytest.mark.integration
    def test_full_fallback_chain(self):
        """Test full fetch_position_prices with Sina as primary."""
        from data_collector import fetch_position_prices
        positions = [
            {"code": "601398", "name": "工商银行"},
            {"code": "605167", "name": "利柏特"},
        ]
        result = fetch_position_prices(positions)
        for code in ["601398", "605167"]:
            assert code in result
            p = result[code]
            assert not p.get("error"), f"{code} has error: {p.get('error')}"
            assert p["price"] > 0
            # Should come from Sina (primary) unless something is wrong
            # Don't assert source=sina because AkShare might succeed too


# ━━━ End-to-end pipeline gate tests ━━━

class TestEndToEnd:
    """Tests that simulate real pipeline scenarios."""

    def test_20260409_scenario_would_fail(self):
        """Today's real scenario: both positions have no prices.
        With gates, the pipeline would have stopped at Gate 1."""
        data = {
            "date": "2026-04-09",
            "positions": [
                {"code": "605167", "name": "利柏特"},
                {"code": "688037", "name": "芯源微"},
            ],
            "position_prices": {
                "605167": {"code": "605167", "error": "No kline data"},
                "688037": {"code": "688037", "error": "No kline data"},
            },
            "market": make_market(),
            "strategy_pool": {
                "source": "local_pricedb+cf_cross",
                "strategy_id": "407228-local-ma-rps",
                "date": "2026-04-08",
                "total_stocks": 0,
                "stocks": [],
                "error": None,
            },
            "enriched": [],
            "iv_sentiment": {"overall_sentiment": {"signal": "偏乐观"}},
        }
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert len(result.hard_fails) >= 2
        # Verify the actual error messages are useful
        for fail in result.hard_fails:
            assert "605167" in fail or "688037" in fail

    def test_clean_run_all_gates_pass(self):
        """A perfectly clean run passes all gates."""
        # Phase 1 gate
        data = make_phase1_data(position_codes=["605167"])
        g1 = validate_phase1_gate(data)
        assert g1.passed is True

        # Phase 2 gate
        decisions = {
            "market_summary": "Weak day",
            "position_decisions": [
                {"code": "605167", "action": "HOLD", "reason": "Above stop"}
            ],
            "new_positions": [],
            "skip_list": [],
            "watchlist": [{"code": "600000", "name": "Test"}],
            "new_learnings": [],
        }
        g2 = validate_llm_output_gate(decisions, data)
        assert g2.passed is True

        # Phase 3 gate
        apply_log = {"actions": ["HOLD 605167", "Generated report"]}
        g3 = validate_phase3_gate("2026-04-09", apply_log, data)
        assert g3.passed is True

        # Manifest
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        m.add_gate(g1)
        m.add_gate(g2)
        m.add_gate(g3)
        m.finalize()
        assert m.status == PipelineStatus.SUCCESS


# ━━━ Runner ━━━

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
