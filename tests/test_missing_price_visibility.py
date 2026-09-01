"""A missing price must stay VISIBLE — never become 0, −100%, or 'flat'.

Audit A2 / top-10 #5. Three faces of one defect, and the same rule closes all
three (the null-visibility rule: data→null regressions must surface as
explicit markers, never as plausible numbers):

1. run_daily's HOLD/RAISE_STOP path did `price_data.get("price", 0)` — a
   failed fetch (which emits {"code":..., "error":...} with NO price key)
   became price 0 → pnl −100.0 written into permanent history and read back
   into later prompts as a real crash.
2. close_position accepted exit_price 0 while open_position hard-rejects it —
   a failed fetch on a SELL day would book a total loss into realized P&L.
3. (documented, fixed here at the history layer) position_manager's display
   default rendered a missing mark as exactly flat, hiding real drawdowns
   from all six sell rules.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import position_manager as pm
import run_daily


# --- the history-entry builder (extracted seam) ------------------------------

def test_a_present_price_computes_real_pnl():
    e = run_daily.build_mark_entry("2026-09-01", "noon", {"price": 19.2},
                                   entry_price=15.6, action="HOLD", note="x")
    assert e["price"] == 19.2
    assert e["change_pct"] == pytest.approx(23.08, abs=0.01)


def test_a_missing_price_yields_no_fabricated_numbers():
    """The exact failure shape: fetch error dict, no 'price' key. The entry
    must say so — not claim price 0 / pnl −100."""
    e = run_daily.build_mark_entry("2026-09-01", "noon",
                                   {"code": "000703", "error": "all 3 sources failed"},
                                   entry_price=15.6, action="HOLD", note="x")
    assert e["price"] is None
    assert e["change_pct"] is None
    assert "PRICE UNAVAILABLE" in e["note"]


def test_a_zero_price_is_treated_as_missing_not_a_crash():
    e = run_daily.build_mark_entry("2026-09-01", "noon", {"price": 0},
                                   entry_price=15.6, action="HOLD", note="x")
    assert e["price"] is None and e["change_pct"] is None


def test_missing_entry_price_still_records_the_mark_without_pnl():
    e = run_daily.build_mark_entry("2026-09-01", "noon", {"price": 19.2},
                                   entry_price=0, action="HOLD", note="x")
    assert e["price"] == 19.2
    assert e["change_pct"] is None


# --- close_position symmetry with open_position ------------------------------

def test_close_rejects_a_zero_exit_price(tmp_path, monkeypatch):
    """open_position hard-fails on invalid prices; close must too — booking a
    SELL at price 0 writes a fake total loss into realized P&L forever."""
    with pytest.raises(ValueError, match="exit_price"):
        pm.close_position("600000", "stop_hit", exit_price=0)


def test_close_rejects_a_negative_exit_price():
    with pytest.raises(ValueError, match="exit_price"):
        pm.close_position("600000", "stop_hit", exit_price=-1.5)


def test_close_rejects_a_none_exit_price():
    with pytest.raises(ValueError, match="exit_price"):
        pm.close_position("600000", "stop_hit", exit_price=None)
