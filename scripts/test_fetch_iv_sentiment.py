import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from fetch_iv_sentiment import CORE_UNDERLYINGS, overall_sentiment, stock_iv_proxy


IV_ROWS = [
    {"underlying": "510050", "name": "50ETF", "iv_rank": 0.1156, "iv_percentile": 0.1097, "current_iv": 0.1384, "interpretation": "低"},
    {"underlying": "510300", "name": "300ETF", "iv_rank": 0.0140, "iv_percentile": 0.0084, "current_iv": 0.1315, "interpretation": "极低"},
    {"underlying": "510500", "name": "500ETF", "iv_rank": 0.0000, "iv_percentile": 0.0000, "current_iv": 0.2031, "interpretation": "极低"},
    {"underlying": "588000", "name": "科创50", "iv_rank": 0.0362, "iv_percentile": 0.0127, "current_iv": 0.2538, "interpretation": "极低"},
    {"underlying": "159915", "name": "创业板ETF", "iv_rank": 0.1709, "iv_percentile": 0.1857, "current_iv": 0.2613, "interpretation": "低"},
    {"underlying": "159922", "name": "500ETF深", "iv_rank": 0.3089, "iv_percentile": 0.5574, "current_iv": 0.2385, "interpretation": "中性"},
    {"underlying": "159919", "name": "300ETF深", "iv_rank": 0.0402, "iv_percentile": 0.0681, "current_iv": 0.1691, "interpretation": "极低"},
    {"underlying": "159901", "name": "深100ETF", "iv_rank": 0.0598, "iv_percentile": 0.0468, "current_iv": 0.1758, "interpretation": "极低"},
    {"underlying": "588080", "name": "科创板50", "iv_rank": 0.0000, "iv_percentile": 0.0000, "current_iv": 0.2538, "interpretation": "极低"},
]

IV_DATA = {"etf_iv_data": IV_ROWS, "overall_sentiment": overall_sentiment(IV_ROWS, codes=CORE_UNDERLYINGS)}


def test_overall_sentiment_uses_core_basket():
    sentiment = overall_sentiment(IV_ROWS, codes=CORE_UNDERLYINGS)
    assert sentiment["based_on"] == CORE_UNDERLYINGS
    assert sentiment["signal"] == "极度乐观"
    assert sentiment["avg_iv_rank"] == 0.0673


def test_stock_iv_proxy_for_kechuang_stock_prefers_kechuang_proxy():
    proxy = stock_iv_proxy("688125.SH", IV_DATA)
    assert proxy["primary_underlying"] == "588000"
    assert proxy["primary_name"] == "科创50"
    assert proxy["sizing"] == "half"
    assert proxy["alternates"][0]["underlying"] == "588080"


def test_stock_iv_proxy_for_chinext_stock_prefers_chinext_proxy():
    proxy = stock_iv_proxy("300750", IV_DATA)
    assert proxy["primary_underlying"] == "159915"
    assert proxy["primary_name"] == "创业板ETF"
    assert proxy["sizing"] == "normal"
