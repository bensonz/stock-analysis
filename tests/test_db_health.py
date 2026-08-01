"""Tests for the data-quality health block + phase-1 freshness contract
(2026-08-01, post-outage loudness layer).

The 07-30 outage stayed silent for two days because every degradation path
worked-but-whispered. These tests pin the new behavior: staleness, partial
days, and cross-source mismatches must flip ok=False and hard-fail the
phase-1 gate.
"""
import sqlite3
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import contracts
import pricedb

D1, D2, D3 = "2026-07-29", "2026-07-30", "2026-07-31"


def _db(dates_counts: dict, factors_through: str | None = None):
    """DB where date -> N synthetic codes have rows (and factors)."""
    conn = sqlite3.connect(":memory:")
    pricedb.ensure_schema(conn)
    for d, n in dates_counts.items():
        for i in range(n):
            code = f"{600000 + i:06d}"
            conn.execute(
                "INSERT OR IGNORE INTO stocks(code, name, exchange) VALUES (?,?,?)",
                (code, code, "SH"))
            conn.execute(
                "INSERT INTO daily_prices VALUES (?,?,?,?,?,?,?,?)",
                (code, d, 10.0, 10.5, 9.5, 10.0, 1000, 10000.0))
            if factors_through and d <= factors_through:
                conn.execute("INSERT INTO adj_factors VALUES (?,?,1.0)", (code, d))
    conn.commit()
    return conn


def _pin_calendar(monkeypatch, expected_iso: str, cal_iso: list):
    monkeypatch.setattr(
        pricedb, "last_settled_trading_day",
        lambda now=None: _date.fromisoformat(expected_iso))
    monkeypatch.setattr(
        pricedb, "_get_trade_calendar_cached",
        lambda: [d.replace("-", "") for d in cal_iso])


def test_health_ok_when_fresh(monkeypatch):
    conn = _db({D1: 10, D2: 10, D3: 10}, factors_through=D3)
    _pin_calendar(monkeypatch, D3, [D1, D2, D3])
    h = pricedb.db_health(conn)
    assert h["ok"] is True
    assert h["lag_sessions"] == 0
    assert h["warnings"] == []


def test_health_flags_two_session_staleness(monkeypatch):
    conn = _db({D1: 10}, factors_through=D1)
    _pin_calendar(monkeypatch, D3, [D1, D2, D3])
    h = pricedb.db_health(conn)
    assert h["lag_sessions"] == 2
    assert h["ok"] is False
    assert any("stale" in w for w in h["warnings"])


def test_health_flags_partial_latest_day(monkeypatch):
    conn = _db({D1: 10, D2: 10, D3: 3}, factors_through=D3)
    _pin_calendar(monkeypatch, D3, [D1, D2, D3])
    h = pricedb.db_health(conn)
    assert h["latest_partial"] is True
    assert h["ok"] is False


def test_health_spot_audit_catches_mismatch(monkeypatch):
    conn = _db({D1: 10, D2: 10, D3: 10}, factors_through=D3)
    _pin_calendar(monkeypatch, D3, [D1, D2, D3])
    # sina disagrees: says close was 12.0 while DB stores 10.0
    monkeypatch.setattr(pricedb, "_fetch_klines_sina", lambda stock, datalen: [
        (stock["code"], D3, 11.9, 12.1, 11.8, 12.0, 1000, None)])
    h = pricedb.db_health(conn, spot_check=True)
    assert h["spot_check"]["mismatches"]
    assert h["ok"] is False


def _gate_data(health: dict) -> dict:
    """Minimal phase-1 data dict that passes every other check."""
    return {
        "positions": [],
        "position_prices": {},
        "market": {
            "indices": {
                "上证指数": {"close": 3500.0},
                "深证成指": {"close": 11000.0},
                "创业板指": {"close": 2300.0},
            },
            "breadth": {"total": 5200, "up": 2600, "down": 2600},
        },
        "strategy_pool": {},
        "db_health": health,
    }


def test_phase1_gate_hard_fails_on_two_session_staleness():
    result = contracts.validate_phase1_gate(_gate_data(
        {"lag_sessions": 2, "latest_price_date": D1, "expected_latest": D3}))
    assert not result.passed
    assert any("antique" in f for f in result.hard_fails)


def test_phase1_gate_tolerates_one_session_lag():
    result = contracts.validate_phase1_gate(_gate_data(
        {"lag_sessions": 1, "latest_price_date": D2, "expected_latest": D3}))
    assert result.passed  # soft warning only — the coverage floor's domain


def test_phase1_gate_hard_fails_on_spot_mismatch():
    result = contracts.validate_phase1_gate(_gate_data({
        "lag_sessions": 0,
        "spot_check": {"mismatches": [{"code": "600000", "stored": 10.0, "sina": 12.0}]},
    }))
    assert not result.passed


def test_phase1_gate_skips_when_health_absent():
    result = contracts.validate_phase1_gate(_gate_data({}) | {"db_health": None})
    assert result.passed
