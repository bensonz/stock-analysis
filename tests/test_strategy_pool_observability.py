import json
import sqlite3
import sys
import types
from datetime import datetime
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import data_collector
import run_daily
import run_paths


def _make_temp_pricedb(path: Path, codes: list[str], date_str: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.execute("CREATE TABLE daily_prices (date TEXT, code TEXT, volume INTEGER)")
        conn.execute("CREATE TABLE stocks (code TEXT, name TEXT, exchange TEXT)")
        for code in codes:
            conn.execute("INSERT INTO daily_prices(date, code, volume) VALUES (?, ?, ?)", (date_str, code, 100000))
            conn.execute("INSERT INTO stocks(code, name, exchange) VALUES (?, ?, ?)", (code, f"Test{code}", "SH"))
        conn.commit()


def test_fetch_strategy_pool_local_uses_relaxed_local_fallback_when_strict_filters_zero_pool(tmp_path, monkeypatch):
    today = datetime.now().strftime("%Y-%m-%d")
    db_path = tmp_path / "pricedb" / "ashare_prices.db"
    _make_temp_pricedb(db_path, ["600001"], today)

    fake_rps = types.ModuleType("rps_calculator")
    fake_rps.compute_ma_rps = lambda db, date=None: {
        "600001": {"rps20": 80.0, "rps60": 90.0, "rps120": 95.0, "rps250": 96.0, "ma10_today": 10.5}
    }
    fake_rps.compute_ma_alignment = lambda db, date=None: {
        "600001": {"aligned": True, "ma20": 10.0, "ma120": 9.5, "ma250": 9.0}
    }
    monkeypatch.setitem(sys.modules, "rps_calculator", fake_rps)

    monkeypatch.setattr(
        data_collector,
        "batch_enrich",
        lambda rows: [{
            "code": "600001.SH",
            "name": "FallbackTest",
            "highlights": [{"tag": "one", "text": "only one"}],
            "risks": [],
            "total_shares": 100_000_000,
        }],
    )
    monkeypatch.setattr(
        data_collector,
        "_load_price_snapshots",
        lambda db, codes, date: {"600001": {"price": 12.5, "change_pct": 1.2}},
    )
    monkeypatch.setattr(
        data_collector,
        "fetch_strategy_pool",
        lambda strategy_id=data_collector.DEFAULT_STRATEGY_ID: {
            "source": "api",
            "strategy_id": strategy_id,
            "date": today,
            "total_stocks": 2,
            "stocks": [
                {"code": "600111", "name": "Remote A", "rps120": 88.0},
                {"code": "600222", "name": "Remote B", "rps120": 91.0},
            ],
            "error": None,
        },
    )

    result = data_collector.fetch_strategy_pool_local(str(db_path))

    assert result["source"] == "local_pricedb_relaxed"
    assert result["total_stocks"] == 1
    assert [s["code"] for s in result["stocks"]] == ["600001"]
    assert result["debug"]["stage_counts"]["after_rps_alignment"] == 1
    assert result["debug"]["stage_counts"]["after_local_filters"] == 0
    assert result["debug"]["stage_counts"]["after_relaxed_fallback"] == 1
    assert result["debug"]["fallback"]["used"] is True
    assert result["debug"]["fallback"]["reason"] == "strict_local_filters_yielded_zero_candidates"
    assert result["stocks"][0]["strict_filter_reasons"] == ["weak_highlights_or_risks(highlights=1,risks=0)"]


def test_phase1_collect_writes_crawl_intersect_rps_and_vcp_artifacts(tmp_path, monkeypatch):
    date_str = datetime.now().strftime("%Y-%m-%d")
    project_root = tmp_path
    runs_dir = project_root / "runs"
    pricedb_path = project_root / "data" / "pricedb" / "ashare_prices.db"
    pricedb_path.parent.mkdir(parents=True, exist_ok=True)
    pricedb_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("PRICEDB_SKIP_UPDATE", "1")

    original_paths = {
        "PROJECT_ROOT": run_daily.PROJECT_ROOT,
        "RUNS_DIR": run_daily.RUNS_DIR,
        "LEARNINGS_FILE": run_daily.LEARNINGS_FILE,
        "HYPOTHESES_FILE": run_daily.HYPOTHESES_FILE,
    }
    run_daily.PROJECT_ROOT = project_root
    run_daily.RUNS_DIR = runs_dir
    run_daily.LEARNINGS_FILE = project_root / "LEARNINGS.md"
    run_daily.HYPOTHESES_FILE = project_root / "tracking" / "hypotheses.json"
    # get_run_dir lives in run_paths and builds paths from run_paths.RUNS_DIR.
    monkeypatch.setattr(run_paths, "RUNS_DIR", runs_dir)

    fake_rps = types.ModuleType("rps_calculator")
    fake_rps.compute_ma_rps = lambda db, date=None: {
        "600001": {"rps20": 81.0, "rps60": 88.0, "rps120": 92.0, "rps250": 95.0, "ma10_today": 10.2},
        "600999": {"rps20": 70.0, "rps60": 80.0, "rps120": 91.0, "rps250": 95.0, "ma10_today": 9.8},
    }
    monkeypatch.setitem(sys.modules, "rps_calculator", fake_rps)

    fake_vcp = types.ModuleType("vcp_scanner")
    fake_vcp.scan_vcp = lambda db, rps_data=None, min_rps120=0, base_days=120, top_n=500: [{
        "code": "600001",
        "score": 80,
        "contraction_ratio": 0.3,
        "last_depth": 0.12,
        "dist_from_peak_pct": 1.8,
        "nearest_ma": "MA20",
        "nearest_ma_dist": 1.4,
        "vol_declining": True,
        "num_contractions": 3,
        "depth_strs": ["10%", "7%", "4%"],
    }]
    monkeypatch.setitem(sys.modules, "vcp_scanner", fake_vcp)

    fake_iv = types.ModuleType("fetch_iv_sentiment")
    fake_iv.fetch_all = lambda: {
        "overall_sentiment": {"signal": "中性", "avg_iv_rank": 0.12, "based_on": ["510300"]},
    }
    fake_iv.stock_iv_proxy = lambda code, iv_data, market_cap=None: None
    monkeypatch.setitem(sys.modules, "fetch_iv_sentiment", fake_iv)

    monkeypatch.setattr(run_daily, "fetch_strategy_pool", lambda: {
        "source": "api",
        "strategy_id": "407228",
        "date": date_str,
        "total_stocks": 2,
        "stocks": [
            {"code": "600001", "code_full": "600001.SH", "name": "Remote Match"},
            {"code": "600999", "code_full": "600999.SH", "name": "Remote Only"},
        ],
        "error": None,
    })
    monkeypatch.setattr(run_daily, "load_active_positions", lambda: [])
    monkeypatch.setattr(run_daily, "load_recent_watchlists", lambda days=5: [])
    monkeypatch.setattr(run_daily, "fetch_market_overview", lambda: {
        "indices": {
            "上证指数": {"close": 4000.0, "change_pct": 1.0, "date": date_str},
            "深证成指": {"close": 12000.0, "change_pct": 1.2, "date": date_str},
            "创业板指": {"close": 2500.0, "change_pct": 1.4, "date": date_str},
        },
        "breadth": {"up": 3000, "down": 1000, "flat": 200, "total": 4200, "distribution": {"r10": 50, "f10": 8}},
        "sectors": {"top5": [], "bottom5": []},
    })
    monkeypatch.setattr(run_daily, "fetch_position_prices", lambda positions: {})
    monkeypatch.setattr(run_daily, "fetch_missed_opportunity_prices", lambda watchlists: [])
    monkeypatch.setattr(run_daily, "fetch_ma_data", lambda pool_stocks: {})
    monkeypatch.setattr(run_daily, "batch_enrich", lambda candidates: [])
    monkeypatch.setattr(run_daily, "snapshot_positions", lambda snapshot_type, date: {})
    monkeypatch.setattr(run_daily, "check_snapshot_consistency", lambda date, snap: [])
    monkeypatch.setattr(run_daily, "load_hypotheses", lambda: {})
    monkeypatch.setattr(run_daily, "hypothesis_prompt", lambda hyp_data: "")
    monkeypatch.setattr(run_daily, "run_all_rules", lambda: {"total_violations": 0, "rules": []})
    monkeypatch.setattr(run_daily, "regenerate_positions_json", lambda price_data=None: {})
    monkeypatch.setattr(run_daily, "validate_data", lambda data: [])

    try:
        run_daily.phase1_collect(date_str, "afternoon")
    finally:
        for name, value in original_paths.items():
            setattr(run_daily, name, value)

    input_dir = runs_dir / date_str / "afternoon" / "input"
    crawl_file = input_dir / "crawl.json"
    intersect_file = input_dir / "intersect.json"
    debug_file = input_dir / "strategy_pool_debug.json"
    rps_file = input_dir / "rps.json"
    vcp_file = input_dir / "vcp.json"

    assert crawl_file.exists()
    assert intersect_file.exists()
    assert debug_file.exists()
    assert rps_file.exists()
    assert vcp_file.exists()

    crawl_data = json.loads(crawl_file.read_text(encoding="utf-8"))
    intersect_data = json.loads(intersect_file.read_text(encoding="utf-8"))
    debug_data = json.loads(debug_file.read_text(encoding="utf-8"))
    rps_data = json.loads(rps_file.read_text(encoding="utf-8"))
    vcp_data = json.loads(vcp_file.read_text(encoding="utf-8"))

    assert crawl_data["strategy_id"] == "407228"
    assert [s["code"] for s in crawl_data["stocks"]] == ["600001", "600999"]
    assert intersect_data["source"] == "cheesefortune_intersection"
    assert [s["code"] for s in intersect_data["stocks"]] == ["600001"]
    assert debug_data["final_total_stocks"] == 1
    assert debug_data["stage_counts"]["remote_strategy_total"] == 2
    assert debug_data["stage_counts"]["rps_universe"] == 2
    assert debug_data["stage_counts"]["intersection_total"] == 1
    assert debug_data["drop_counts"]["remote_missing_rps"] == 0
    assert debug_data["drop_counts"]["remote_below_rps_threshold"] == 1
    assert debug_data["criteria"] == {"rps60_gt": 85.0, "rps120_gt": 85.0, "rps250_gt": 85.0}
    assert list(rps_data.keys()) == ["600001", "600999"]
    assert len(vcp_data) == 1
