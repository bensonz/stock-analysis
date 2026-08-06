"""Tests for the static portfolio site generator (2026-08-06).

Pins the equity-series extraction rules: legacy + slotted run layouts,
latest-snapshot-of-the-day wins, broken/empty snapshots skipped.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_site as bs


def _snap(tmp, rel, time, equity, ret=None):
    path = tmp / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "snapshot_time": time,
        "positions_json": {
            "portfolio": {
                "startingCapital": 1000000,
                "totalEquity": equity,
                "totalReturnPct": ret,
                "positionsUsed": 2,
            }
        },
    }), encoding="utf-8")


def test_series_legacy_and_slotted_latest_wins(tmp_path):
    runs = tmp_path / "runs"
    # legacy layout day
    _snap(runs, "2026-03-05/input/positions_snapshot.json",
          "2026-03-05T15:35:00+08:00", 968982.0, -3.1)
    # slotted day: afternoon must beat noon
    _snap(runs, "2026-08-06/noon/input/positions_snapshot.json",
          "2026-08-06T11:35:00+08:00", 960000.0)
    _snap(runs, "2026-08-06/afternoon/input/positions_snapshot.json",
          "2026-08-06T15:35:00+08:00", 964319.0)
    series = bs.collect_equity_series(runs)
    assert [p["date"] for p in series] == ["2026-03-05", "2026-08-06"]
    assert series[1]["equity"] == 964319.0  # afternoon snapshot won


def test_series_skips_broken_and_empty_snapshots(tmp_path):
    runs = tmp_path / "runs"
    bad = runs / "2026-04-01/input/positions_snapshot.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not json", encoding="utf-8")
    empty = runs / "2026-04-02/input/positions_snapshot.json"
    empty.parent.mkdir(parents=True)
    empty.write_text(json.dumps({"snapshot_time": "t", "positions_json": {}}),
                     encoding="utf-8")
    _snap(runs, "2026-04-03/input/positions_snapshot.json",
          "2026-04-03T15:35:00+08:00", 1000500.0)
    series = bs.collect_equity_series(runs)
    assert [p["date"] for p in series] == ["2026-04-03"]


def test_inception_anchor_from_config(tmp_path):
    (tmp_path / "portfolio_config.json").write_text(json.dumps({
        "starting_capital": 1000000, "created": "2026-02-03"}), encoding="utf-8")
    p = bs.inception_point(tmp_path)
    assert p == {"date": "2026-02-03", "time": "", "equity": 1000000.0,
                 "ret_pct": 0.0, "positions": 0, "starting": 1000000,
                 "synthetic": True}
    assert bs.inception_point(tmp_path / "nope") is None


def test_max_drawdown():
    series = [{"equity": e} for e in [100.0, 110.0, 99.0, 105.0]]
    stats = bs.compute_stats(series, [])
    assert stats["max_drawdown_pct"] == 10.0  # 110 → 99


def test_render_html_contains_data_and_no_external_refs(tmp_path):
    series = [{"date": "2026-08-06", "equity": 964319.0, "ret_pct": -3.57,
               "positions": 9, "starting": 1000000}]
    trades = [{"code": "600988", "name": "赤峰黄金", "entryDate": "2026-07-01",
               "exitDate": "2026-07-10", "holdingDays": 9, "returnPct": 5.5,
               "exitReason": "target_hit"}]
    html_out = bs.render_html(series, {"portfolio": {"totalEquity": 964319.0},
                                       "activePositions": []},
                              trades, bs.compute_stats(series, trades))
    assert "964319" in html_out
    assert "赤峰黄金" in html_out
    assert "http" not in html_out.split("<script>")[1]  # no CDN in the JS
    assert "胜率 100.0%" in html_out
