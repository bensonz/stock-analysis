"""Adjustment factors sourced from iFinD's ths_af_stock.

Two invariants carry the risk here:

1. **Never splice bases mid-series.** Our chains anchor at 1.0 on each code's
   first date; iFinD anchors at listing. Writing their absolute factor into the
   middle of one of our series would fabricate a return on the splice date. So
   the daily sync imports a RATIO, and `rebuild` replaces a code's whole series.

2. **The noise threshold belongs to the source.** clist f18 INFERS the event
   from prev_close/f18, so sub-0.5% ratios are indistinguishable from rounding
   noise. ths_af_stock is exact — the same 0.5% floor would have discarded 4 of
   the 6 real dividends on 2026-08-25 (steps of 1.0021–1.0039).
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pricedb

PREV, TODAY = "2026-08-24", "2026-08-25"


def _conn(codes=("000001",), with_factors=True):
    conn = sqlite3.connect(":memory:")
    pricedb.ensure_schema(conn)
    for c in codes:
        conn.execute("INSERT INTO stocks(code,name,exchange) VALUES (?,?,'SZ')", (c, c))
        for d, close in ((PREV, 10.0), (TODAY, 10.0)):
            conn.execute("INSERT INTO daily_prices(code,date,open,high,low,close,volume) "
                         "VALUES (?,?,?,?,?,?,100)", (c, d, close, close, close, close))
        if with_factors:
            conn.execute("INSERT INTO adj_factors(code,date,factor) VALUES (?,?,?)",
                         (c, PREV, 2.0))   # a non-1.0 base, so splices are visible
    conn.commit()
    return conn


def _fake_af(monkeypatch, series):
    """series = {code: {date: af}}"""
    monkeypatch.setattr(pricedb, "_ifind_af_series",
                        lambda codes, ex_map, beg, end: series)
    monkeypatch.setattr(pricedb.ifind_client, "is_available", lambda: True)


# ---------------------------------------------------------------------------
# Daily sync
# ---------------------------------------------------------------------------


def test_multipliers_are_ratios_not_absolutes(monkeypatch):
    """iFinD's base differs from ours; only the ratio may cross over."""
    conn = _conn()
    _fake_af(monkeypatch, {"000001": {PREV: 5.0392585, TODAY: 5.15772974}})

    m = pricedb._ifind_event_multipliers(conn, ["000001"], PREV, TODAY)

    assert m["000001"] == pytest.approx(5.15772974 / 5.0392585)


def test_sync_preserves_our_base_across_an_event(monkeypatch):
    """New factor = OUR prior factor × iFinD's ratio — never iFinD's absolute."""
    conn = _conn()
    _fake_af(monkeypatch, {"000001": {PREV: 5.0, TODAY: 5.5}})   # ratio 1.10

    pricedb.sync_adj_factors_for_today(conn, TODAY)

    factor = conn.execute("SELECT factor FROM adj_factors WHERE date=?",
                          (TODAY,)).fetchone()[0]
    assert factor == pytest.approx(2.0 * 1.10), \
        "must be prior-factor × ratio, not iFinD's 5.5"


def test_small_dividend_is_not_snapped_away(monkeypatch):
    """A 0.21% step is a real dividend; the clist noise floor would eat it."""
    conn = _conn()
    _fake_af(monkeypatch, {"000001": {PREV: 1.0, TODAY: 1.002067}})

    pricedb.sync_adj_factors_for_today(conn, TODAY)

    factor = conn.execute("SELECT factor FROM adj_factors WHERE date=?",
                          (TODAY,)).fetchone()[0]
    assert factor == pytest.approx(2.0 * 1.002067), \
        "sub-0.5% events must survive when the source is exact"
    assert 1.002067 - 1.0 < pricedb.ADJ_EVENT_THRESHOLD, \
        "guard: this step really is below the inferred-source floor"


def test_float_noise_still_snaps_to_one(monkeypatch):
    conn = _conn()
    _fake_af(monkeypatch, {"000001": {PREV: 1.0, TODAY: 1.0 + 1e-12}})

    pricedb.sync_adj_factors_for_today(conn, TODAY)

    assert conn.execute("SELECT factor FROM adj_factors WHERE date=?",
                        (TODAY,)).fetchone()[0] == pytest.approx(2.0)


def test_sync_falls_back_to_clist_when_ifind_fails(monkeypatch):
    """A vendor hiccup must not stop the factor chain."""
    conn = _conn()
    monkeypatch.setattr(pricedb.ifind_client, "is_available", lambda: True)

    def _boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(pricedb, "_ifind_af_series", _boom)
    # f18 = prev_close / multiplier → 10.0/1.10
    monkeypatch.setattr(pricedb, "_fetch_clist_prev_close_map",
                        lambda: {"000001": 10.0 / 1.10})

    pricedb.sync_adj_factors_for_today(conn, TODAY)

    assert conn.execute("SELECT factor FROM adj_factors WHERE date=?",
                        (TODAY,)).fetchone()[0] == pytest.approx(2.0 * 1.10, rel=1e-6)


def test_multi_day_gap_still_refuses(monkeypatch):
    """Pre-existing guard must survive the iFinD rewiring."""
    conn = _conn(with_factors=False)
    _fake_af(monkeypatch, {"000001": {PREV: 1.0, TODAY: 1.0}})

    with pytest.raises(RuntimeError, match="multi-day gap"):
        pricedb.sync_adj_factors_for_today(conn, TODAY)


# ---------------------------------------------------------------------------
# Whole-series rebuild
# ---------------------------------------------------------------------------


def test_rebuild_anchors_each_series_at_one(monkeypatch):
    conn = _conn()
    _fake_af(monkeypatch, {"000001": {PREV: 5.0, TODAY: 5.5}})

    stats = pricedb.rebuild_factors_from_ifind(conn, ["000001"])

    rows = dict(conn.execute("SELECT date, factor FROM adj_factors WHERE code='000001'"))
    assert rows[PREV] == 1.0, "first date of the series must be the 1.0 anchor"
    assert rows[TODAY] == pytest.approx(1.10)
    assert stats["rebuilt"] == 1


def test_rebuild_replaces_the_whole_series(monkeypatch):
    """Leftover rows from the old chain would be a base splice."""
    conn = _conn()
    conn.execute("INSERT INTO adj_factors(code,date,factor) VALUES "
                 "('000001','2026-01-05',9.99)")
    conn.commit()
    _fake_af(monkeypatch, {"000001": {PREV: 5.0, TODAY: 5.5}})

    pricedb.rebuild_factors_from_ifind(conn, ["000001"])

    stale = conn.execute("SELECT COUNT(*) FROM adj_factors "
                         "WHERE code='000001' AND factor=9.99").fetchone()[0]
    assert stale == 0, "old rows must be deleted, not merged"


def test_rebuild_dry_run_writes_nothing(monkeypatch):
    conn = _conn()
    _fake_af(monkeypatch, {"000001": {PREV: 5.0, TODAY: 5.5}})

    pricedb.rebuild_factors_from_ifind(conn, ["000001"], dry_run=True)

    assert conn.execute("SELECT factor FROM adj_factors WHERE date=?",
                        (PREV,)).fetchone()[0] == 2.0, "original base untouched"


def test_rebuild_skips_codes_without_ifind_data(monkeypatch):
    """No data must leave the existing chain alone, not blank it."""
    conn = _conn()
    _fake_af(monkeypatch, {})

    stats = pricedb.rebuild_factors_from_ifind(conn, ["000001"])

    assert stats["no_data"] == 1 and stats["rebuilt"] == 0
    # The original chain survives untouched. (A TODAY row may also appear —
    # rebuild ends with _forward_fill_factors, which keeps the table dense and
    # carries the existing 2.0 forward. That is the pre-existing convention,
    # not a rebuild artifact, so it must carry the SAME factor.)
    factors = dict(conn.execute("SELECT date, factor FROM adj_factors "
                                "WHERE code='000001'"))
    assert factors[PREV] == 2.0
    assert set(factors.values()) == {2.0}, "no rebuilt value may have landed"
