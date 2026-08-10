"""Tests for the rotation (换仓) opportunity ledger (2026-08-07).

Pins: record only when book is full, held codes excluded from candidates,
idempotent per (date, slot), forward-return math on the code's own sessions,
and spread direction (positive = missed alpha).
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import rotation_ledger as rl


def _positions(n):
    return [{"code": f"60{i:04d}", "name": f"P{i}", "entryPrice": 10.0,
             "entryDate": "2026-07-01", "pnl_pct": float(i)} for i in range(n)]


def _data(pool_codes, positions):
    return {
        "slot": "noon",
        "positions": positions,
        "position_prices": {},
        "strategy_pool": {"stocks": [
            {"code": c, "name": f"C{c}", "rps60": 95, "rps120": 96, "rps250": 97}
            for c in pool_codes]},
        "entry_regime": {"allow_new_positions": True},
    }


def test_no_record_when_book_not_full(tmp_path):
    ledger = tmp_path / "ledger.json"
    pos = _positions(9)
    out = rl.record_if_full("2026-08-07", _data(["000001"], pos),
                            ledger_path=ledger, max_positions=10, positions=pos)
    assert out is None
    assert not ledger.exists()


def test_record_when_full_excludes_held_and_dedupes(tmp_path):
    ledger = tmp_path / "ledger.json"
    pos = _positions(10)
    held_code = pos[0]["code"]  # 600000 also present in the pool
    data = _data([held_code, "000001", "000002", "000003", "000004"], pos)
    out = rl.record_if_full("2026-08-07", data, ledger_path=ledger,
                            max_positions=10, positions=pos)
    assert out is not None
    codes = [c["code"] for c in out["candidates"]]
    assert held_code not in codes
    assert codes == ["000001", "000002", "000003"]  # TOP_N=3, pool order kept
    assert out["weakest"]["code"] == pos[0]["code"]  # lowest pnl_pct
    # same date+slot again → no duplicate
    assert rl.record_if_full("2026-08-07", data, ledger_path=ledger,
                             max_positions=10, positions=pos) is None
    assert len(json.loads(ledger.read_text())) == 1


def _db_with(prices: dict) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE daily_prices (code TEXT, date TEXT, close REAL)")
    for code, series in prices.items():
        for d, c in series:
            conn.execute("INSERT INTO daily_prices VALUES (?,?,?)", (code, d, c))
    return conn


def test_backtest_spread_math(tmp_path):
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps([{
        "date": "2026-07-01", "slot": "noon",
        "weakest": {"code": "600000", "name": "弱者"},
        "candidates": [{"code": "000001", "name": "强者"}],
    }]))
    days = [f"2026-07-{d:02d}" for d in range(1, 6)]
    conn = _db_with({
        "600000": list(zip(days, [10.0, 10.0, 10.0, 10.0, 10.0])),   # flat
        "000001": list(zip(days, [10.0, 11.0, 12.0, 12.5, 13.0])),   # +30%
    })
    out = rl.backtest(horizon=4, conn=conn, ledger_path=ledger)
    s = out["summary"]
    assert s["n_resolved"] == 1
    r = out["entries"][0]
    assert r["weakest"]["fwd_ret"] == 0.0
    assert r["candidates"][0]["ret"] == 30.0
    assert r["spread"] == 30.0            # positive = missed alpha
    assert s["positive_spread_days"] == 1


def test_backtest_skips_incomplete_windows(tmp_path):
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps([{
        "date": "2026-07-01", "slot": "noon",
        "weakest": {"code": "600000", "name": "弱"},
        "candidates": [{"code": "000001", "name": "强"}],
    }]))
    conn = _db_with({"600000": [("2026-07-01", 10.0)],
                     "000001": [("2026-07-01", 10.0)]})
    out = rl.backtest(horizon=4, conn=conn, ledger_path=ledger)
    assert out["summary"]["n_resolved"] == 0
