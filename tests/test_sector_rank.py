"""sector_rank: every 申万二级 sector ranked by 5-day return, with bands and
consecutive cold sessions — what ANALYST.md Rule 1 and the overlay read."""
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sector_rank as sr


def test_bands_are_top_and_bottom_30_percent():
    n = 10                                    # ceil(0.3*10) = 3
    assert [sr._band(r, n) for r in range(1, 11)] == (
        ["hot"] * 3 + ["mid"] * 4 + ["cold"] * 3)


# --- membership cache ------------------------------------------------------

def _cache(tmp_path, fetched, sectors=None):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"fetched": fetched, "sectors": sectors or {"801": {"codes": []}}}))
    return p


def _never(*_a):
    raise AssertionError("refresh called")


def test_fresh_cache_is_used_without_refreshing(tmp_path):
    p = _cache(tmp_path, "2026-11-01")
    sectors, note = sr.load_members("2026-11-21", cache=p, refresh=_never)
    assert sectors == {"801": {"codes": []}} and note is None


def test_stale_cache_is_refreshed_and_rewritten(tmp_path):
    p = _cache(tmp_path, "2026-09-01")
    fresh = {str(i): {"name": f"s{i}", "codes": []} for i in range(120)}
    sectors, note = sr.load_members("2026-11-21", cache=p, refresh=lambda: fresh)
    assert sectors == fresh and note is None
    assert json.loads(p.read_text())["fetched"] == "2026-11-21"


def test_failed_refresh_keeps_old_cache_and_says_so(tmp_path):
    p = _cache(tmp_path, "2026-09-01")

    def boom():
        raise OSError("akshare down")
    sectors, note = sr.load_members("2026-11-21", cache=p, refresh=boom)
    assert sectors == {"801": {"codes": []}}
    assert "2026-09-01" in note and "akshare down" in note


def test_a_short_refresh_counts_as_a_failure(tmp_path):
    p = _cache(tmp_path, "2026-09-01")
    _, note = sr.load_members("2026-11-21", cache=p, refresh=lambda: {"1": {}})
    assert "only 1 sectors" in note
    assert json.loads(p.read_text())["fetched"] == "2026-09-01"   # not overwritten


def test_no_cache_and_no_refresh_raises(tmp_path):
    def boom():
        raise OSError("down")
    with pytest.raises(OSError):
        sr.load_members("2026-11-21", cache=tmp_path / "none.json", refresh=boom)


# --- ranking ---------------------------------------------------------------

def _db(paths: dict) -> sqlite3.Connection:
    """paths: {code: [close per session]} over consecutive weekdays."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE daily_prices (code TEXT, date TEXT, open REAL, high REAL, "
                 "low REAL, close REAL, volume REAL, amount REAL)")
    conn.execute("CREATE TABLE adj_factors (code TEXT, date TEXT, factor REAL)")
    d, days = date(2026, 1, 5), []
    while len(days) < len(next(iter(paths.values()))):
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += timedelta(days=1)
    for code, closes in paths.items():
        conn.executemany("INSERT INTO daily_prices VALUES (?,?,0,0,0,?,0,0)",
                         [(code, day, c) for day, c in zip(days, closes)])
    return conn


def _sectors(k):
    return {f"80{i}": {"name": f"S{i}", "codes": [f"{i}0000{j}" for j in range(3)]}
            for i in range(k)}


def test_ranks_by_equal_weighted_5_day_return_and_counts_cold_days():
    """10 sectors, 25 sessions. Sector i rises i% a session, so S9 is #1 and
    S0..S2 are the cold band every day: S0 (flat) is last and has been cold
    for the whole lookback."""
    n_days, paths = 25, {}
    for i in range(10):
        for j in range(3):
            paths[f"{i}0000{j}"] = [100 * (1 + i / 100) ** t for t in range(n_days)]
    conn = _db(paths)
    out = sr.rank_sectors(conn, _sectors(10))
    assert out["n"] == 10 and out["hot_max_rank"] == 3 and out["cold_min_rank"] == 8
    s = out["sectors"]
    assert s["809"]["rank5"] == 1 and s["809"]["band"] == "hot"
    assert s["800"]["rank5"] == 10 and s["800"]["band"] == "cold"
    assert s["800"]["cold_days"] == sr.COLD_LOOKBACK
    assert s["805"]["band"] == "mid" and s["805"]["cold_days"] == 0
    assert s["809"]["ret5"] == pytest.approx((1.09 ** 5 - 1) * 100, abs=0.01)
    assert s["809"]["ret20"] == pytest.approx((1.09 ** 20 - 1) * 100, abs=0.01)


def test_a_sector_that_just_turned_cold_counts_one_day():
    """S5 matches S0's flat path until the last session, then crashes: before
    that it ranked mid, so its streak is exactly 1."""
    n_days, paths = 25, {}
    for i in range(10):
        for j in range(3):
            path = [100 * (1 + i / 100) ** t for t in range(n_days)]
            if i == 5:
                path[-1] = path[-2] * 0.5
            paths[f"{i}0000{j}"] = path
    out = sr.rank_sectors(_db(paths), _sectors(10))
    assert out["sectors"]["805"]["rank5"] == 10 and out["sectors"]["805"]["cold_days"] == 1


def test_too_little_history_returns_none():
    paths = {f"{i}0000{j}": [100.0] * 8 for i in range(4) for j in range(3)}
    assert sr.rank_sectors(_db(paths), _sectors(4)) is None


def test_prompt_block_maps_codes_to_their_sector():
    ranking = {"asof": "2026-11-20", "n": 2, "hot_max_rank": 1, "cold_min_rank": 2,
               "sectors": {"801": {"name": "电力", "rank5": 1, "band": "hot", "ret5": 1.0,
                                   "ret20": 3.0, "cold_days": 0},
                           "802": {"name": "出版", "rank5": 2, "band": "cold", "ret5": -9.0,
                                   "ret20": -2.0, "cold_days": 4}}}
    sectors = {"801": {"name": "电力", "codes": ["000690"]},
               "802": {"name": "出版", "codes": ["000719"]},
               "803": {"name": "新板块", "codes": ["600001"]}}
    out = sr.for_prompt(ranking, sectors, ["000690", "000719", "600001", "999999"])
    assert out["stocks"]["000719"] == {"sector": "出版", "rank5": 2, "band": "cold",
                                       "ret5": -9.0, "cold_days": 4}
    assert out["stocks"]["600001"] == {"sector": "新板块", "band": "unranked"}
    assert out["stocks"]["999999"] == {"sector": None, "band": "unranked"}
    assert [x["name"] for x in out["top"]] == ["电力", "出版"]
    assert [x["name"] for x in out["bottom"]] == ["出版", "电力"]


def test_collect_reports_failure_instead_of_raising(monkeypatch):
    def boom(today):
        raise OSError("no cache, akshare down")
    monkeypatch.setattr(sr, "load_members", boom)
    assert sr.collect(["000690"], "2026-11-21") == {"error": "OSError: no cache, akshare down"}
