"""Tests for scripts/research/entry_drift.py — the pure measurement pieces.

Everything runs on an in-memory sqlite DB with synthetic prices/factors, so no
test touches data/pricedb, runs/ or tracking/.
"""
import json
import math
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "research"))

import entry_drift as ed

DATES = ["2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06"]


def make_db(bars, factors=()):
    """bars: [(code, date, close, volume)]; factors: [(code, date, factor)]."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE daily_prices (code TEXT, date TEXT, open REAL, "
                 "high REAL, low REAL, close REAL, volume INTEGER, amount REAL, "
                 "PRIMARY KEY (code, date))")
    conn.execute("CREATE TABLE adj_factors (code TEXT, date TEXT, factor REAL, "
                 "PRIMARY KEY (code, date))")
    conn.executemany(
        "INSERT INTO daily_prices (code, date, close, volume) VALUES (?, ?, ?, ?)",
        bars)
    conn.executemany("INSERT INTO adj_factors VALUES (?, ?, ?)", factors)
    return conn


def panel(conn):
    closes = ed.load_closes(conn, DATES[0])
    return closes, ed.build_calendar(closes, ed.phantom_dates(conn))


def test_ex_dividend_gap_is_not_a_loss():
    # Raw close drops 10 -> 9 on the ex-date; the hfq factor steps up by 10/9,
    # so the adjusted series is flat and the forward return must be ~0.
    conn = make_db(
        [("600000", DATES[0], 10.0, 100), ("600000", DATES[1], 9.0, 110)],
        [("600000", DATES[0], 1.0), ("600000", DATES[1], 10 / 9)])
    closes, cal = panel(conn)
    assert ed.forward_return(closes, cal, "600000", DATES[0], 1) == pytest.approx(0.0)


def test_missing_forward_bar_is_skipped_not_zero_filled():
    # 000002 is suspended on the target date; 000001 rises 10%. The universe
    # mean must be 10% (000002 dropped), not 5% (000002 counted as flat).
    conn = make_db([("000001", DATES[0], 10.0, 1), ("000001", DATES[1], 11.0, 2),
                    ("000002", DATES[0], 20.0, 1)])
    closes, cal = panel(conn)
    assert ed.forward_return(closes, cal, "000002", DATES[0], 1) is None
    assert ed.universe_mean(closes, cal, DATES[0], 1) == pytest.approx(10.0)


def test_horizon_past_last_session_is_none():
    conn = make_db([("000001", DATES[0], 10.0, 1), ("000001", DATES[1], 11.0, 2)])
    closes, cal = panel(conn)
    assert ed.forward_return(closes, cal, "000001", DATES[0], 5) is None


def test_excess_is_cohort_minus_universe():
    # Returns: A +10%, B 0%, C -4%. Universe mean = +2%. Cohort {A} -> +8.
    conn = make_db([("A", DATES[0], 10.0, 1), ("A", DATES[1], 11.0, 2),
                    ("B", DATES[0], 10.0, 1), ("B", DATES[1], 10.0, 2),
                    ("C", DATES[0], 10.0, 1), ("C", DATES[1], 9.6, 2)])
    closes, cal = panel(conn)
    series = ed.excess_series(closes, cal, {DATES[0]: ["A"]}, 1)
    assert series == {DATES[0]: pytest.approx(8.0)}


def test_t_stat_on_known_series():
    # mean 3, sd sqrt(2.5), n 5 -> t = 3 / (sqrt(2.5)/sqrt(5)) = 3*sqrt(2)
    assert ed.t_stat([1, 2, 3, 4, 5]) == pytest.approx(3 * math.sqrt(2))


def test_t_stat_undefined_cases():
    assert ed.t_stat([1.0]) is None
    assert ed.t_stat([2.0, 2.0, 2.0]) is None


def test_phantom_copy_day_is_dropped_from_calendar():
    # DATES[2] repeats DATES[1] byte-for-byte for every code: a copy, not a
    # session. Horizon 1 from DATES[1] must then land on DATES[3].
    bars = []
    for code in ("A", "B"):
        bars += [(code, DATES[0], 10.0, 1), (code, DATES[1], 11.0, 2),
                 (code, DATES[2], 11.0, 2), (code, DATES[3], 12.1, 3)]
    conn = make_db(bars)
    closes, cal = panel(conn)
    assert DATES[2] not in cal
    assert ed.forward_return(closes, cal, "A", DATES[1], 1) == pytest.approx(10.0)


def test_non_overlapping_keeps_windows_apart():
    cal = [f"d{i:02d}" for i in range(20)]
    picked = ed.non_overlapping(["d00", "d01", "d05", "d09", "d10"], cal, 5)
    assert picked == ["d00", "d05", "d10"]


def _write_intersect(run_dir, stocks):
    (run_dir / "input").mkdir(parents=True)
    (run_dir / "output").mkdir()
    (run_dir / "input" / "intersect.json").write_text(
        json.dumps({"stocks": stocks}), encoding="utf-8")


def test_gate_cohorts_prefer_afternoon_and_split_by_rps(tmp_path):
    _write_intersect(tmp_path / DATES[0] / "noon", [{"code": "999999", "rps120": 90}])
    _write_intersect(tmp_path / DATES[0] / "afternoon", [
        {"code": "600000", "rps120": 90.0},
        {"code": "600001.SH", "rps120": 97.5},
        {"code": "600002", "rps120": None},
    ])
    got = ed.load_gate_cohorts(tmp_path)[DATES[0]]
    assert got == {"gate": ["600000", "600001", "600002"],
                   "in_band": ["600000"], "over_extended": ["600001"]}
