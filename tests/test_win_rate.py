"""Win-rate methodology — pins the three views apart.

The pooled `16/54 = 29.6%` reported by the first weekly audit is censored: the
book holds winners and cuts losers, so at any moment open positions skew winner
and closed positions skew loser. These tests build a book with that exact shape
and assert the three views disagree in the predicted direction.
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import win_rate as wr


def _book(tmp, closed, active):
    (tmp / "tracking" / "closed").mkdir(parents=True)
    for i, c in enumerate(closed):
        (tmp / "tracking" / "closed" / f"{i}.json").write_text(
            json.dumps(c), encoding="utf-8")
    (tmp / "tracking" / "positions.json").write_text(
        json.dumps({"activePositions": active}), encoding="utf-8")
    return tmp


def _pricedb(tmp, bars):
    """bars: {code: [(date, close), ...]}"""
    p = tmp / "prices.db"
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE daily_prices (code TEXT, date TEXT, close REAL)")
    for code, series in bars.items():
        conn.executemany("INSERT INTO daily_prices VALUES (?,?,?)",
                         [(code, d, c) for d, c in series])
    conn.commit()
    conn.close()
    return p


def test_era_attribution_uses_entry_not_exit():
    # entered under 入场护栏 (03-24+), closed months later under a later ruleset
    assert wr.era_of("2026-07-01")[1] == "入场护栏"
    assert wr.era_of("2026-07-22")[1] == "RPS 上限取消 (已证伪)"
    assert wr.era_of("2026-02-03")[1] == "v1 3-agent 架构"
    # a date before the first era still lands somewhere rather than crashing
    assert wr.era_of("2020-01-01") == wr.ERAS[0]


def test_open_positions_are_censored_out_of_the_realized_view(tmp_path):
    """The failure mode that made 07-31 read 0%: its winners were all still open."""
    root = _book(
        tmp_path,
        closed=[{"code": "600000", "name": "L", "entryDate": "2026-07-31",
                 "entryPrice": 10.0, "returnPct": -4.0}],
        active=[{"code": "600001", "name": "W", "entryDate": "2026-07-31",
                 "entryPrice": 10.0, "currentPrice": 13.0}],
    )
    d = wr.build(horizon=2, root=root, db_path=root / "nonexistent.db")
    era = [e for e in d["eras"] if e["start"] == "2026-07-31"][0]
    assert era["open"] == 1
    assert era["realized"]["n"] == 1 and era["realized"]["win_rate"] == 0.0
    assert era["marked"]["n"] == 2 and era["marked"]["win_rate"] == 50.0
    assert d["pooled_realized"]["n"] == 1        # pooled realized ignores the winner


def test_fixed_horizon_counts_open_and_closed_alike(tmp_path):
    root = _book(
        tmp_path,
        closed=[{"code": "600000", "name": "L", "entryDate": "2026-07-31",
                 "entryPrice": 10.0, "returnPct": -4.0}],
        active=[{"code": "600001", "name": "W", "entryDate": "2026-07-31",
                 "entryPrice": 10.0, "currentPrice": 13.0}],
    )
    db = _pricedb(tmp_path, {
        # stopped out at -4%, but by day 2 it had recovered to +5%
        "600000": [("2026-08-01", 10.2), ("2026-08-02", 10.5)],
        "600001": [("2026-08-01", 11.0), ("2026-08-02", 13.0)],
    })
    d = wr.build(horizon=2, root=root, db_path=db)
    era = [e for e in d["eras"] if e["start"] == "2026-07-31"][0]
    assert era["fixed"]["n"] == 2                 # both, regardless of exit
    assert era["fixed"]["win_rate"] == 100.0      # the stop, not the pick, lost
    assert era["realized"]["win_rate"] == 0.0     # ...which realized cannot see


def test_trades_younger_than_horizon_are_dropped_not_zeroed(tmp_path):
    root = _book(tmp_path, closed=[], active=[
        {"code": "600001", "name": "新", "entryDate": "2026-08-13",
         "entryPrice": 10.0, "currentPrice": 10.1}])
    db = _pricedb(tmp_path, {"600001": [("2026-08-14", 10.1)]})   # only 1 session
    d = wr.build(horizon=10, root=root, db_path=db)
    assert d["pooled_fixed"] is None              # small n, not a diluted number
    assert d["pooled_realized"] is None           # still open


def test_weekly_buckets_are_reported_for_the_noise_argument(tmp_path):
    root = _book(tmp_path, closed=[
        {"code": "600000", "name": "A", "entryDate": "2026-07-27",
         "entryPrice": 10.0, "returnPct": -4.0},
        {"code": "600002", "name": "B", "entryDate": "2026-07-28",
         "entryPrice": 10.0, "returnPct": +4.0},
    ], active=[])
    d = wr.build(horizon=2, root=root, db_path=root / "nonexistent.db")
    assert list(d["weekly"]) == ["2026-W31"]      # same ISO week
    assert d["weekly"]["2026-W31"]["n"] == 2
