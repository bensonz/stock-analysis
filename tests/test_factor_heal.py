"""Unit tests for the multi-session adjustment-factor gap heal (2026-08-01).

Context: the eastmoney clist endpoint (same-day f18 event detector) went
unreachable on 2026-07-30/31, leaving adj_factors two sessions behind
daily_prices with 39 real ex-div events inside the gap. These tests lock in:

1. sync_adj_factors_for_today REFUSES to run across a gap (it would reset
   every cumulative chain to base 1.0);
2. heal_adj_factor_gap re-derives only calendar-named event codes, anchor-
   rescaled so pre-gap rows are unchanged, and forward-fills the rest;
3. _sync_or_heal_factors routes to heal whenever the lag exceeds one session.

Pure-logic tests — all network fetchers are monkeypatched.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pricedb
import pricedb_factors

D1, D2, D3 = "2026-07-29", "2026-07-30", "2026-07-31"


def _seed(codes_factors: dict, dates=(D1, D2, D3), factor_dates=(D1,)):
    """In-memory DB: every code has price rows for `dates`, factor rows
    (at the given per-code factor) only for `factor_dates`."""
    conn = sqlite3.connect(":memory:")
    pricedb.ensure_schema(conn)
    for code, factor in codes_factors.items():
        conn.execute("INSERT INTO stocks(code, name, exchange) VALUES (?,?,?)",
                     (code, code, "SZ"))
        for d in dates:
            conn.execute(
                "INSERT INTO daily_prices VALUES (?,?,?,?,?,?,?,?)",
                (code, d, 10.0, 10.5, 9.5, 10.0, 1000, 10000.0))
        for d in factor_dates:
            conn.execute("INSERT INTO adj_factors VALUES (?,?,?)", (code, d, factor))
    conn.commit()
    return conn


def test_sync_refuses_chain_reset_on_gap(monkeypatch):
    conn = _seed({"000001": 2.0})  # factors stop at D1, prices through D3
    monkeypatch.setattr(pricedb, "_fetch_clist_prev_close_map",
                        lambda: {"000001": 10.0})
    with pytest.raises(RuntimeError, match="heal"):
        pricedb.sync_adj_factors_for_today(conn, D3)
    # and nothing was written for the gap
    assert conn.execute(
        "SELECT COUNT(*) FROM adj_factors WHERE date > ?", (D1,)
    ).fetchone()[0] == 0


def test_heal_rederives_event_code_and_ffills_the_rest(monkeypatch):
    conn = _seed({"000001": 2.0, "000002": 1.5})
    monkeypatch.setattr(pricedb, "ADJ_BACKFILL_SLEEP_SEC", 0.0)
    monkeypatch.setattr(pricedb, "_fetch_ex_div_codes_datacenter",
                        lambda d: {"000001"} if d == D2 else set())
    # sina absolute scale: 4.0 before the gap, 4.4 from the D2 ex-div on.
    # Anchor at D1 (stored 2.0) → scale 0.5 → D1 stays 2.0, D2/D3 become 2.2.
    monkeypatch.setattr(pricedb, "fetch_adj_factor_events_sina",
                        lambda code, ex: [("2026-01-05", 4.0), (D2, 4.4)])

    earliest = pricedb.heal_adj_factor_gap(conn, D2, D3)

    factors = dict(
        ((r[0], r[1]), r[2]) for r in
        conn.execute("SELECT code, date, factor FROM adj_factors"))
    assert factors[("000001", D1)] == pytest.approx(2.0)   # pre-gap untouched
    assert factors[("000001", D2)] == pytest.approx(2.2)   # event applied
    assert factors[("000001", D3)] == pytest.approx(2.2)
    assert factors[("000002", D2)] == pytest.approx(1.5)   # plain forward-fill
    assert factors[("000002", D3)] == pytest.approx(1.5)
    assert earliest == D2                                   # shallow invalidation


def test_heal_calendar_unreachable_degrades_to_ffill(monkeypatch):
    conn = _seed({"000001": 2.0})
    monkeypatch.setattr(pricedb, "ADJ_BACKFILL_SLEEP_SEC", 0.0)
    monkeypatch.setattr(pricedb, "_fetch_ex_div_codes_datacenter", lambda d: None)

    earliest = pricedb.heal_adj_factor_gap(conn, D2, D3)

    assert earliest is None
    factors = dict(
        (r[0], r[1]) for r in
        conn.execute("SELECT date, factor FROM adj_factors WHERE code='000001'"))
    assert factors[D2] == pytest.approx(2.0)  # dense again, status-quo values
    assert factors[D3] == pytest.approx(2.0)


def test_heal_skips_codes_already_event_derived(monkeypatch):
    # 000001's stored factors already jump on D2 (2.0 → 2.2): the event was
    # derived event-aware, so heal must not waste a re-derivation on it.
    conn = _seed({"000001": 2.0}, factor_dates=(D1,))
    conn.execute("INSERT INTO adj_factors VALUES ('000001', ?, 2.2)", (D2,))
    conn.execute("INSERT INTO adj_factors VALUES ('000001', ?, 2.2)", (D3,))
    conn.commit()
    monkeypatch.setattr(pricedb, "ADJ_BACKFILL_SLEEP_SEC", 0.0)
    monkeypatch.setattr(pricedb, "_fetch_ex_div_codes_datacenter",
                        lambda d: {"000001"} if d == D2 else set())

    def _must_not_call(code, ex):
        raise AssertionError("re-derivation fetched for an already-derived code")
    monkeypatch.setattr(pricedb, "fetch_adj_factor_events_sina", _must_not_call)

    assert pricedb.heal_adj_factor_gap(conn, D2, D3) is None


def test_fetch_klines_sina_parses_and_converts(monkeypatch):
    body = ('x=([{"day":"2026-07-30","open":"11.280","high":"11.620",'
            '"low":"11.180","close":"11.610","volume":"277770773"},'
            '{"day":"2026-07-31","open":"11.500","high":"11.630",'
            '"low":"11.280","close":"11.630","volume":"202497895"}])')

    class _Resp:
        status_code = 200
        text = body

    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp())

    rows = pricedb._fetch_klines_sina(
        {"code": "000001", "exchange": "SZ"}, datalen=5)

    assert rows == [
        ("000001", "2026-07-30", 11.28, 11.62, 11.18, 11.61, 2777707, None),
        ("000001", "2026-07-31", 11.50, 11.63, 11.28, 11.63, 2024978, None),
    ]


def test_sync_or_heal_routes_multiday_gap_to_heal(monkeypatch):
    conn = _seed({"000001": 2.0})  # lag = 2 sessions, mpd is in the past
    calls = []
    # Patch on pricedb_factors, not pricedb. Both functions moved there on
    # 2026-08-30, so the caller resolves this name in that module's globals;
    # patching the pricedb re-export leaves the fake inert and the REAL heal
    # runs — which is exactly what happened when this was retargeted, and only
    # the assertion below caught it.
    monkeypatch.setattr(pricedb_factors, "heal_adj_factor_gap",
                        lambda c, beg, end: calls.append((beg, end)) or D2)

    changed = pricedb._sync_or_heal_factors(conn)

    assert calls == [(D2, D3)]
    assert changed == D2
