"""Tests for build_summary() — ensures it handles the actual Phase 1 schema."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def _make_phase1_fixture():
    """Minimal fixture matching actual Phase 1 schema."""
    return {
        "date": "2026-03-10",
        "market": {
            "indices": {
                "上证指数": {"code": "sh000001", "close": 4120.29, "change_pct": 0.58},
                "深证成指": {"code": "sz399001", "close": 14342.73, "change_pct": 1.96},
            },
            "breadth": {"up": 4412, "down": 969, "flat": 100, "total": 5481},
            "sectors": {
                "top5": [
                    {"板块名称": "非金属材料Ⅱ", "涨跌幅": 6.43},
                    {"板块名称": "元件", "涨跌幅": 5.54},
                ],
                "bottom5": [
                    {"板块名称": "油服工程", "涨跌幅": -7.28},
                    {"板块名称": "煤炭开采", "涨跌幅": -3.22},
                ],
            },
        },
        "strategy_pool": {
            "total_stocks": 2,
            "stocks": [
                {"code": "002121", "name": "科陆电子", "rps120": 88.7, "rps20": 82.5, "pe": 19.0, "market_cap": 164.4},
            ],
        },
        "enriched": [
            {
                "code": "002121.SZ", "name": "科陆电子", "pe": 19.0,
                "dist_ma5_pct": 2.1, "dist_ma10_pct": 4.3, "dist_ma20_pct": 7.8,
                "industries": [{"name": "电力设备", "level": 1}],
                "iv_proxy": {
                    "primary_name": "500ETF深",
                    "iv_rank": 0.3089,
                    "sizing": "normal",
                },
            },
        ],
        "positions": [
            {
                "code": "002046", "name": "国机精工", "entryDate": "2026-03-10",
                "entryPrice": 52.3, "stopLoss": 49.69, "targetPrice": 65.0, "sector": "通用设备",
                "iv_proxy": {
                    "primary_name": "500ETF深",
                    "iv_rank": 0.3089,
                    "sizing": "normal",
                },
            },
        ],
        "position_prices": {
            "002046": {"code": "002046", "name": "国机精工", "price": 52.49, "change_pct": 4.04},
        },
        "iv_sentiment": {
            "date": "2026-03-10",
            "source": "akshare",
            "etf_iv_data": [
                {"underlying": "510050", "name": "50ETF", "current_iv": 0.15, "iv_rank": 0.19, "interpretation": "低"},
            ],
            "overall_sentiment": {"signal": "极度乐观", "avg_iv_rank": 0.088, "avg_iv_percentile": 0.062, "implication": "市场自满"},
        },
    }


class TestBuildSummary:
    def test_no_crash_on_real_schema(self):
        from llm_client import build_summary
        data = _make_phase1_fixture()
        result = build_summary(data)
        assert isinstance(result, str)
        assert len(result) > 100

    def test_indices_dict_rendered(self):
        from llm_client import build_summary
        data = _make_phase1_fixture()
        result = build_summary(data)
        assert "上证指数" in result
        assert "4120.29" in result

    def test_sectors_top_bottom(self):
        from llm_client import build_summary
        data = _make_phase1_fixture()
        result = build_summary(data)
        assert "非金属材料Ⅱ" in result
        assert "油服工程" in result

    def test_positions_key(self):
        from llm_client import build_summary
        data = _make_phase1_fixture()
        result = build_summary(data)
        assert "国机精工" in result
        assert "52.3" in result

    def test_position_prices_price_key(self):
        from llm_client import build_summary
        data = _make_phase1_fixture()
        result = build_summary(data)
        assert "52.49" in result
        assert "4.04" in result

    def test_iv_sentiment_structured(self):
        from llm_client import build_summary
        data = _make_phase1_fixture()
        result = build_summary(data)
        assert "极度乐观" in result
        assert "50ETF" in result

    def test_stock_iv_proxy_rendered(self):
        from llm_client import build_summary
        data = _make_phase1_fixture()
        result = build_summary(data)
        assert "500ETF深" in result
        assert "30.9%" in result

    def test_enriched_key(self):
        from llm_client import build_summary
        data = _make_phase1_fixture()
        result = build_summary(data)
        assert "科陆电子" in result
        assert "电力设备" in result

    def test_empty_data_no_crash(self):
        from llm_client import build_summary
        result = build_summary({})
        assert isinstance(result, str)

    def test_none_fields_no_crash(self):
        from llm_client import build_summary
        data = {"market": None, "positions": None, "iv_sentiment": None, "portfolio": None}
        result = build_summary(data)
        assert isinstance(result, str)

    def test_real_phase1_file(self):
        """Load actual phase1.json if available (legacy or slot-aware layout)."""
        from llm_client import build_summary
        runs = Path(__file__).resolve().parent.parent / "runs"
        # Legacy: runs/<date>/phase1.json ; slot-aware: runs/<date>/<slot>/phase1.json
        candidates = sorted(runs.glob("*/phase1.json")) + sorted(runs.glob("*/*/phase1.json"))
        if not candidates:
            return  # skip if no real data
        data = json.load(open(candidates[-1]))
        result = build_summary(data)
        assert isinstance(result, str)
        assert len(result) > 500
