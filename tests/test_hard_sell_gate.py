"""
Tests for the mechanical hard-sell gate (enforce_hard_sells).

Selling is otherwise LLM discretion; these rules from ANALYST.md Rule 5 are
enforced in code so a stop actually means something:
  1. price <= position stop        -> forced SELL, reason "stop_hit"
  2. unrealized PnL <= -5%          -> forced SELL, reason "hard_stop_loss"

Run: python -m pytest tests/test_hard_sell_gate.py -v
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from run_daily import enforce_hard_sells, HARD_SELL_LOSS_PCT


def _apply(positions, prices, position_decisions):
    """Run the gate and return (mutated decisions list, log actions)."""
    decisions = {"position_decisions": list(position_decisions)}
    data = {"positions": positions, "position_prices": prices}
    log = {"actions": []}
    enforce_hard_sells(decisions, data, log)
    return decisions["position_decisions"], log["actions"]


def _pos(code, entry, stop, name="X"):
    return {"code": code, "name": name, "entryPrice": entry, "currentStop": stop}


def test_stop_touch_overrides_hold():
    """Price at/below stop overrides an LLM HOLD to a forced SELL."""
    d, _ = _apply([_pos("000001", 100, 95)],
                  {"000001": {"price": 94}},
                  [{"code": "000001", "action": "HOLD"}])
    assert d[0]["action"] == "SELL"
    assert d[0]["reason"] == "forced:stop_hit"


def test_hard_loss_injected_when_llm_silent():
    """A -5%+ loser the LLM never mentioned gets a SELL injected."""
    # price 94 vs entry 100 = -6%, still above stop 80 so it's the loss rule
    d, _ = _apply([_pos("000002", 100, 80)],
                  {"000002": {"price": 94}},
                  [])
    assert len(d) == 1
    assert d[0]["action"] == "SELL"
    assert d[0]["reason"] == "forced:hard_stop_loss"
    assert d[0]["pnl_pct"] == -6.0


def test_healthy_position_untouched():
    """A profitable position within stop is left exactly as the LLM decided."""
    d, _ = _apply([_pos("000003", 100, 90)],
                  {"000003": {"price": 103}},
                  [{"code": "000003", "action": "HOLD"}])
    assert d[0]["action"] == "HOLD"


def test_existing_llm_sell_is_respected():
    """If the LLM already sells, keep its reason (don't clobber to 'forced:')."""
    d, _ = _apply([_pos("000004", 100, 95)],
                  {"000004": {"price": 94}},
                  [{"code": "000004", "action": "SELL", "reason": "thesis broke"}])
    assert d[0]["action"] == "SELL"
    assert d[0]["reason"] == "thesis broke"


def test_no_price_never_blind_sells():
    """Missing live price -> skip and log, never force-sell blind."""
    d, logs = _apply([_pos("000005", 100, 95)],
                     {},
                     [{"code": "000005", "action": "HOLD"}])
    assert d[0]["action"] == "HOLD"
    assert any("HARD-SELL SKIP" in x for x in logs)


def test_exact_loss_boundary_sells():
    """PnL exactly at -5% triggers (comparison is <=)."""
    assert HARD_SELL_LOSS_PCT == -5.0
    d, _ = _apply([_pos("000006", 100, 80)],
                  {"000006": {"price": 95}},  # exactly -5%
                  [])
    assert d and d[0]["action"] == "SELL"


def test_stop_takes_priority_over_loss_reason():
    """When both conditions hold, stop_hit is reported (checked first)."""
    # price 90 <= stop 96, and also -10% loss
    d, _ = _apply([_pos("000007", 100, 96)],
                  {"000007": {"price": 90}},
                  [])
    assert d[0]["reason"] == "forced:stop_hit"
