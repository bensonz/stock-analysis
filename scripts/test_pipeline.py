#!/usr/bin/env python3
"""
Pipeline Tests — Basic tests for each module.

Tests:
- position_manager: state transitions (open, close, update)
- validator: catches common issues
- report_generator: outputs valid files
- data_collector: basic function signatures
- run_daily: LLM response parsing

Run: python scripts/test_pipeline.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# Ensure scripts/ is on the path
sys.path.insert(0, str(Path(__file__).parent))


class TestPositionManager(unittest.TestCase):
    """Test position state machine."""

    def setUp(self):
        """Create a temp tracking directory."""
        self.tmpdir = Path(tempfile.mkdtemp())
        self.tracking = self.tmpdir / "tracking"
        self.tracking.mkdir()
        (self.tracking / "closed").mkdir()
        (self.tracking / "daily").mkdir()

        # Patch module-level paths
        import position_manager as pm
        self._orig_tracking = pm.TRACKING_DIR
        self._orig_closed = pm.CLOSED_DIR
        self._orig_daily = pm.DAILY_DIR
        self._orig_positions = pm.POSITIONS_FILE
        self._orig_config = pm.PORTFOLIO_CONFIG_FILE
        pm.TRACKING_DIR = self.tracking
        pm.CLOSED_DIR = self.tracking / "closed"
        pm.DAILY_DIR = self.tracking / "daily"
        pm.POSITIONS_FILE = self.tracking / "positions.json"
        pm.PORTFOLIO_CONFIG_FILE = self.tracking / "portfolio_config.json"
        pm.PORTFOLIO_CONFIG_FILE.write_text(json.dumps({
            "starting_capital": 1000000,
            "max_position_pct": 10,
            "max_positions": 10,
            "min_cash_pct": 20,
        }, ensure_ascii=False, indent=2))
        self.pm = pm

    def tearDown(self):
        """Restore paths and clean up."""
        self.pm.TRACKING_DIR = self._orig_tracking
        self.pm.CLOSED_DIR = self._orig_closed
        self.pm.DAILY_DIR = self._orig_daily
        self.pm.POSITIONS_FILE = self._orig_positions
        self.pm.PORTFOLIO_CONFIG_FILE = self._orig_config
        shutil.rmtree(self.tmpdir)

    def _write_position(self, code: str, **overrides) -> Path:
        """Helper to write a test position file."""
        pos = {
            "code": code,
            "name": f"Test {code}",
            "status": "active",
            "thesis": "Test thesis",
            "entryDate": "2026-01-01",
            "entryPrice": 100.0,
            "targetPrice": 120.0,
            "stopLoss": 90.0,
            "currentStop": 90.0,
            "history": [],
            **overrides,
        }
        path = self.tracking / f"{code}.json"
        path.write_text(json.dumps(pos, ensure_ascii=False, indent=2))
        return path

    def test_load_active_positions(self):
        self._write_position("000001")
        self._write_position("000002")
        self._write_position("000003", status="closed")

        active = self.pm.load_active_positions()
        self.assertEqual(len(active), 2)
        codes = {p["code"] for p in active}
        self.assertEqual(codes, {"000001", "000002"})

    def test_open_position(self):
        pos = self.pm.open_position({
            "code": "688001",
            "name": "测试股",
            "entryPrice": 50.0,
            "targetPrice": 60.0,
            "stopLoss": 45.0,
            "thesis": "Test thesis",
        })

        self.assertEqual(pos["code"], "688001")
        self.assertEqual(pos["status"], "active")
        self.assertEqual(pos["entryPrice"], 50.0)
        self.assertTrue((self.tracking / "688001.json").exists())

        # Check positions.json was regenerated
        self.assertTrue((self.tracking / "positions.json").exists())
        pj = json.loads((self.tracking / "positions.json").read_text())
        self.assertEqual(len(pj["activePositions"]), 1)
        self.assertEqual(pj["activePositions"][0]["code"], "688001")

    def test_open_position_sizes_from_available_cash(self):
        (self.tracking / "portfolio_config.json").write_text(json.dumps({
            "starting_capital": 100000,
            "max_position_pct": 10,
            "max_positions": 10,
            "min_cash_pct": 20,
        }, ensure_ascii=False, indent=2))
        self._write_position("600001", entryPrice=10.0, shares=6000, allocation_pct=60)
        self.pm.regenerate_positions_json()

        pos = self.pm.open_position({
            "code": "600002",
            "name": "现金约束测试",
            "entryPrice": 10.0,
            "targetPrice": 12.0,
            "stopLoss": 9.0,
            "allocation_pct": 50,
            "thesis": "Size from deployable cash",
        })

        self.assertEqual(pos["shares"], 1000)
        self.assertEqual(pos["allocatedCapital"], 10000.0)

    def test_open_position_respects_min_cash_reserve(self):
        (self.tracking / "portfolio_config.json").write_text(json.dumps({
            "starting_capital": 100000,
            "max_position_pct": 10,
            "max_positions": 10,
            "min_cash_pct": 20,
        }, ensure_ascii=False, indent=2))
        self._write_position("600001", entryPrice=10.0, shares=7900, allocation_pct=79)
        self.pm.regenerate_positions_json()

        with self.assertRaises(ValueError):
            self.pm.open_position({
                "code": "600002",
                "name": "保留现金测试",
                "entryPrice": 20.0,
                "targetPrice": 24.0,
                "stopLoss": 19.0,
                "allocation_pct": 50,
                "thesis": "Should fail on reserve",
            })

    def test_close_position(self):
        self._write_position("600001")
        # Regenerate so positions.json exists
        self.pm.regenerate_positions_json()

        pos = self.pm.close_position(
            code="600001",
            reason="target_hit",
            exit_price=120.0,
            lesson="Good trade",
            date="2026-02-01",
        )

        self.assertEqual(pos["status"], "closed")
        self.assertEqual(pos["exitPrice"], 120.0)
        self.assertEqual(pos["returnPct"], 20.0)
        self.assertEqual(pos["holdingDays"], 31)
        self.assertFalse((self.tracking / "600001.json").exists())
        self.assertTrue((self.tracking / "closed" / "600001.json").exists())

        # positions.json should be empty now
        pj = json.loads((self.tracking / "positions.json").read_text())
        self.assertEqual(len(pj["activePositions"]), 0)

    def test_update_position_raise_stop(self):
        self._write_position("300001", currentStop=90.0)
        self.pm.regenerate_positions_json()

        # Raise stop
        pos = self.pm.update_position("300001", {"new_stop": 95.0})
        self.assertEqual(pos["currentStop"], 95.0)

        # Try to lower stop (should not work)
        pos = self.pm.update_position("300001", {"new_stop": 92.0})
        self.assertEqual(pos["currentStop"], 95.0)

    def test_update_position_history(self):
        self._write_position("300002")
        self.pm.regenerate_positions_json()

        pos = self.pm.update_position("300002", {
            "history_entry": {
                "date": "2026-01-02",
                "price": 105.0,
                "change_pct": 5.0,
                "action": "HOLD",
                "note": "Holding steady",
            }
        })

        self.assertEqual(len(pos["history"]), 1)
        self.assertEqual(pos["history"][0]["action"], "HOLD")

    def test_regenerate_positions_json(self):
        self._write_position("000001")
        self._write_position("000002")

        result = self.pm.regenerate_positions_json()
        self.assertEqual(len(result["activePositions"]), 2)
        self.assertIn("lastUpdated", result)

    def test_save_daily_summary(self):
        path = self.pm.save_daily_summary(
            "2026-01-01",
            [{"code": "000001", "action": "HOLD", "price": 100}],
            portfolioStats={"totalPositions": 1},
        )
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["date"], "2026-01-01")
        self.assertEqual(len(data["actions"]), 1)


class TestValidator(unittest.TestCase):
    """Test consistency checks."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.tracking = self.tmpdir / "tracking"
        self.tracking.mkdir()
        (self.tracking / "closed").mkdir()
        (self.tracking / "daily").mkdir()
        self.watchlist = self.tmpdir / "watchlist"
        self.watchlist.mkdir()
        self.reports = self.tmpdir / "reports"
        self.reports.mkdir()

        import validator as v
        self._orig = {
            "TRACKING_DIR": v.TRACKING_DIR,
            "WATCHLIST_DIR": v.WATCHLIST_DIR,
            "REPORTS_DIR": v.REPORTS_DIR,
            "DAILY_DIR": v.DAILY_DIR,
            "POSITIONS_FILE": v.POSITIONS_FILE,
        }
        v.TRACKING_DIR = self.tracking
        v.WATCHLIST_DIR = self.watchlist
        v.REPORTS_DIR = self.reports
        v.DAILY_DIR = self.tracking / "daily"
        v.POSITIONS_FILE = self.tracking / "positions.json"
        self.v = v

    def tearDown(self):
        for k, val in self._orig.items():
            setattr(self.v, k, val)
        shutil.rmtree(self.tmpdir)

    def test_validate_data_complete(self):
        data = {
            "strategy_pool": {"total_stocks": 10, "stocks": [{}]},
            "market": {"indices": {"上证指数": {}}, "breadth": {}},
            "position_prices": {},
            "positions_count": 0,
            "learnings": "some text",
        }
        errors = self.v.validate_data(data)
        self.assertEqual(len(errors), 0)

    def test_validate_data_missing_pool(self):
        data = {"market": {"indices": {}}, "position_prices": {}}
        errors = self.v.validate_data(data)
        self.assertTrue(any("strategy_pool" in e for e in errors))

    def test_validate_data_market_error(self):
        data = {
            "strategy_pool": {"total_stocks": 5, "stocks": [{}]},
            "market": {"indices_error": "timeout"},
            "position_prices": {},
        }
        errors = self.v.validate_data(data)
        self.assertTrue(any("indices" in e for e in errors))

    def test_validate_output_all_good(self):
        # Create consistent state
        pos = {"code": "000001", "name": "Test", "status": "active", "entryPrice": 100,
               "entryDate": "2026-01-01", "targetPrice": 120, "stopLoss": 90}
        (self.tracking / "000001.json").write_text(json.dumps(pos))
        positions = {
            "lastUpdated": "2026-01-01",
            "activePositions": [{"code": "000001", "name": "Test"}],
        }
        (self.tracking / "positions.json").write_text(json.dumps(positions))

        wl = {"date": "2026-01-01", "recommendations": []}
        (self.watchlist / "2026-01-01.json").write_text(json.dumps(wl))
        (self.reports / "2026-01-01.md").write_text("# Report")
        (self.tracking / "daily" / "2026-01-01.json").write_text(json.dumps({"date": "2026-01-01"}))

        errors = self.v.validate_output("2026-01-01")
        self.assertEqual(len(errors), 0)

    def test_validate_output_position_mismatch(self):
        # positions.json says 000001 but tracking has 000002
        pos = {"code": "000002", "name": "Wrong", "status": "active"}
        (self.tracking / "000002.json").write_text(json.dumps(pos))
        positions = {
            "lastUpdated": "2026-01-01",
            "activePositions": [{"code": "000001", "name": "Missing"}],
        }
        (self.tracking / "positions.json").write_text(json.dumps(positions))

        errors = self.v.validate_output("2026-01-01")
        self.assertTrue(any("mismatch" in e for e in errors))

    def test_validate_output_closed_in_root(self):
        pos = {"code": "000001", "name": "Closed", "status": "closed"}
        (self.tracking / "000001.json").write_text(json.dumps(pos))
        positions = {"lastUpdated": "2026-01-01", "activePositions": []}
        (self.tracking / "positions.json").write_text(json.dumps(positions))

        errors = self.v.validate_output("2026-01-01")
        self.assertTrue(any("closed" in e.lower() for e in errors))

    def test_validate_output_missing_files(self):
        positions = {"lastUpdated": "2026-01-01", "activePositions": []}
        (self.tracking / "positions.json").write_text(json.dumps(positions))

        errors = self.v.validate_output("2026-01-01")
        self.assertTrue(any("watchlist" in e for e in errors))
        self.assertTrue(any("report" in e.lower() for e in errors))


class TestReportGenerator(unittest.TestCase):
    """Test report generation."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        import report_generator as rg
        self._orig_wl = rg.WATCHLIST_DIR
        self._orig_rp = rg.REPORTS_DIR
        rg.WATCHLIST_DIR = self.tmpdir / "watchlist"
        rg.REPORTS_DIR = self.tmpdir / "reports"
        rg.WATCHLIST_DIR.mkdir()
        rg.REPORTS_DIR.mkdir()
        self.rg = rg

    def tearDown(self):
        self.rg.WATCHLIST_DIR = self._orig_wl
        self.rg.REPORTS_DIR = self._orig_rp
        shutil.rmtree(self.tmpdir)

    def test_generate_watchlist_json(self):
        data = {
            "market": {
                "indices": {
                    "上证指数": {"close": 4000, "change_pct": 0.5},
                },
                "sectors": {"top5": [], "bottom5": []},
            },
            "strategy_pool": {"total_stocks": 10},
        }
        decisions = {
            "watchlist": [
                {"code": "688001", "name": "Test", "recommendation": "BUY", "confidence": "high"},
                {"code": "300001", "name": "Watch", "recommendation": "WATCH", "confidence": "medium"},
            ],
            "market_summary": "Market is flat",
            "market_call": "谨慎",
        }

        path = self.rg.generate_watchlist_json("2026-01-01", data, decisions)
        self.assertTrue(path.exists())
        wl = json.loads(path.read_text())
        self.assertEqual(wl["date"], "2026-01-01")
        self.assertEqual(len(wl["recommendations"]), 2)
        self.assertEqual(wl["summary"]["buy_recommendations"], 1)
        self.assertEqual(wl["summary"]["watch_recommendations"], 1)

    def test_generate_report_md(self):
        data = {
            "market": {
                "indices": {"上证指数": {"close": 4000, "change_pct": 0.5}},
                "breadth": {"up": 2000, "down": 1500, "total": 4000},
                "sectors": {"top5": [], "bottom5": []},
            },
            "strategy_pool": {"total_stocks": 10, "source": "api"},
        }
        decisions = {
            "watchlist": [
                {"code": "688001", "name": "Test", "recommendation": "BUY",
                 "confidence": "high", "price": 50, "rps120": 85, "reasoning": "Good"},
            ],
            "market_summary": "Market note",
            "new_learnings": ["Lesson 1"],
        }

        path = self.rg.generate_report_md("2026-01-01", data, decisions)
        self.assertTrue(path.exists())
        content = path.read_text()
        self.assertIn("2026-01-01", content)
        self.assertIn("市场概览", content)
        self.assertIn("BUY", content)
        self.assertIn("Lesson 1", content)


class TestRunDailyParser(unittest.TestCase):
    """Test LLM response parsing."""

    def test_parse_direct_json(self):
        from run_daily import _parse_llm_response
        text = '{"position_decisions": [], "watchlist": []}'
        result = _parse_llm_response(text)
        self.assertIn("position_decisions", result)

    def test_parse_json_in_code_block(self):
        from run_daily import _parse_llm_response
        text = """Here is my analysis:
```json
{"position_decisions": [{"code": "000001", "action": "HOLD"}]}
```
"""
        result = _parse_llm_response(text)
        self.assertIn("position_decisions", result)
        self.assertEqual(result["position_decisions"][0]["code"], "000001")

    def test_parse_json_in_text(self):
        from run_daily import _parse_llm_response
        text = 'Some text before {"watchlist": []} and after'
        result = _parse_llm_response(text)
        self.assertIn("watchlist", result)

    def test_parse_empty_returns_empty(self):
        from run_daily import _parse_llm_response
        result = _parse_llm_response("no json here at all")
        self.assertEqual(result, {})

    def test_entry_regime_blocks_weak_market(self):
        from run_daily import evaluate_new_entry_regime

        regime = evaluate_new_entry_regime({
            "breadth": {"up": 1500, "down": 3800, "distribution": {"f10": 24, "r10": 69}},
            "indices": {
                "上证指数": {"change_pct": -0.82},
                "深证成指": {"change_pct": -0.65},
                "创业板指": {"change_pct": -0.22},
            },
        })

        self.assertFalse(regime["allow_new_positions"])
        self.assertEqual(regime["regime"], "weak")

    def test_entry_regime_allows_strong_market(self):
        from run_daily import evaluate_new_entry_regime

        regime = evaluate_new_entry_regime({
            "breadth": {"up": 3600, "down": 1800, "distribution": {"f10": 8, "r10": 96}},
            "indices": {
                "上证指数": {"change_pct": 1.1},
                "深证成指": {"change_pct": 1.8},
                "创业板指": {"change_pct": -0.1},
            },
        })

        self.assertTrue(regime["allow_new_positions"])
        self.assertEqual(regime["regime"], "strong")


if __name__ == "__main__":
    unittest.main(verbosity=2)
