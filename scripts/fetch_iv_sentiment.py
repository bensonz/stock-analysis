#!/usr/bin/env python3
"""
fetch_iv_sentiment.py — Fetch IV rank/percentile from the options-learn backend
to provide market sentiment context for stock analysis.

Requires the options-learn backend running on localhost:8000.

Usage:
    python scripts/fetch_iv_sentiment.py           # JSON output
    python scripts/fetch_iv_sentiment.py --human    # Human-readable summary

Key ETF underlyings:
    510050 = 50ETF (large-cap, closest to "A-share VIX")
    510300 = 300ETF (CSI 300, broad market)
    510500 = 500ETF (mid-cap)
    588000 = 科创50 (tech/growth)
"""

import json
import sys
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

API_BASE = "http://localhost:8000/api/history"

UNDERLYINGS = [
    {"code": "510050", "name": "50ETF", "desc": "大盘蓝筹"},
    {"code": "510300", "name": "300ETF", "desc": "沪深300"},
    {"code": "510500", "name": "500ETF", "desc": "中证500"},
    {"code": "588000", "name": "科创50", "desc": "科创板"},
]


def fetch_iv_rank(code: str, lookback: int = 252) -> dict | None:
    """Fetch IV rank data for one underlying."""
    url = f"{API_BASE}/iv-rank?underlying={code}&lookback_days={lookback}"
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except (URLError, OSError, json.JSONDecodeError) as e:
        print(f"  Warning: Failed to fetch IV for {code}: {e}", file=sys.stderr)
        return None


def interpret_iv_rank(iv_rank: float) -> str:
    """Interpret IV rank as sentiment signal."""
    if iv_rank < 0.10:
        return "极低 (市场极度乐观/自满，适合买入保护)"
    elif iv_rank < 0.25:
        return "低 (市场偏乐观，波动率便宜)"
    elif iv_rank < 0.50:
        return "中性"
    elif iv_rank < 0.75:
        return "偏高 (市场谨慎，波动率偏贵)"
    else:
        return "极高 (市场恐慌，可能是超卖反弹机会)"


def overall_sentiment(results: list[dict]) -> dict:
    """Compute aggregate sentiment from multiple ETF IV readings."""
    valid = [r for r in results if r.get("iv_rank") is not None]
    if not valid:
        return {"signal": "无数据", "detail": "无法获取IV数据"}

    avg_rank = sum(r["iv_rank"] for r in valid) / len(valid)
    avg_percentile = sum(r["iv_percentile"] for r in valid) / len(valid)

    # Sentiment signal
    if avg_rank < 0.15:
        signal = "极度乐观"
        implication = "市场自满，波动率处于低位。短期可能继续上涨但缺乏安全边际。适合：(1)买入便宜的看跌保护 (2)谨慎追高 (3)注意可能的波动率突然飙升"
    elif avg_rank < 0.30:
        signal = "偏乐观"
        implication = "波动率偏低，市场情绪稳定。中期趋势可能延续，但关注IV拐点。"
    elif avg_rank < 0.50:
        signal = "中性"
        implication = "波动率适中，无明显方向性信号。"
    elif avg_rank < 0.70:
        signal = "偏悲观"
        implication = "波动率偏高，市场存在恐慌情绪。可能临近底部区域，但不排除继续下跌。"
    else:
        signal = "极度恐慌"
        implication = "波动率处于高位，市场恐慌。历史上往往是中期买入机会，但短期可能继续剧烈波动。"

    return {
        "signal": signal,
        "avg_iv_rank": round(avg_rank, 4),
        "avg_iv_percentile": round(avg_percentile, 4),
        "implication": implication,
    }


def fetch_all() -> dict:
    """Fetch IV sentiment for all key ETFs."""
    results = []
    for u in UNDERLYINGS:
        data = fetch_iv_rank(u["code"])
        if data:
            data["name"] = u["name"]
            data["desc"] = u["desc"]
            data["interpretation"] = interpret_iv_rank(data.get("iv_rank", 0.5))
            results.append(data)

    sentiment = overall_sentiment(results)

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": "options-learn backend (OpenVlab IV history)",
        "etf_iv_data": results,
        "overall_sentiment": sentiment,
    }


def main():
    human_mode = "--human" in sys.argv

    data = fetch_all()

    if human_mode:
        print(f"📊 A股期权隐含波动率情绪 ({data['date']})")
        print(f"{'='*50}")
        for r in data["etf_iv_data"]:
            print(f"\n{r['name']} ({r['desc']}):")
            print(f"  当前IV: {r['current_iv']*100:.1f}%  |  52周: {r['iv_low']*100:.1f}% - {r['iv_high']*100:.1f}%")
            print(f"  IV Rank: {r['iv_rank']*100:.1f}%  |  IV Percentile: {r['iv_percentile']*100:.1f}%")
            print(f"  解读: {r['interpretation']}")
        s = data["overall_sentiment"]
        print(f"\n{'='*50}")
        print(f"综合信号: {s['signal']}")
        print(f"均IV Rank: {s['avg_iv_rank']*100:.1f}%  |  均IV Percentile: {s['avg_iv_percentile']*100:.1f}%")
        print(f"含义: {s['implication']}")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
