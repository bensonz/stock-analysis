#!/usr/bin/env python3
"""
fetch_iv_sentiment.py — Fetch IV rank/percentile from the options-learn backend
to provide market sentiment context for stock analysis.

Requires the options-learn backend running on localhost:8000.

Usage:
    python scripts/fetch_iv_sentiment.py           # JSON output
    python scripts/fetch_iv_sentiment.py --human   # Human-readable summary

Primary endpoints:
    GET /api/history/iv-rank?underlying=510050&lookback_days=252
    GET /api/history/iv-history?underlying=510050&days=30
"""

import json
import sys
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

API_BASE = "http://localhost:8000/api/history"

UNDERLYINGS = [
    {"code": "510050", "name": "50ETF", "desc": "大盘蓝筹"},
    {"code": "510300", "name": "300ETF", "desc": "沪深300"},
    {"code": "510500", "name": "500ETF", "desc": "中证500"},
    {"code": "588000", "name": "科创50", "desc": "科创板"},
    {"code": "159915", "name": "创业板ETF", "desc": "创业板"},
    {"code": "159922", "name": "500ETF深", "desc": "深市中盘"},
    {"code": "159919", "name": "300ETF深", "desc": "深市宽基"},
    {"code": "159901", "name": "深100ETF", "desc": "深市蓝筹"},
    {"code": "588080", "name": "科创板50", "desc": "科创板（备用代理）"},
]

CORE_UNDERLYINGS = ["510050", "510300", "510500", "588000", "159915"]


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
    if iv_rank < 0.25:
        return "低 (市场偏乐观，波动率便宜)"
    if iv_rank < 0.50:
        return "中性"
    if iv_rank < 0.75:
        return "偏高 (市场谨慎，波动率偏贵)"
    return "极高 (市场恐慌，可能是超卖反弹机会)"


def _normalize_stock_code(code: str) -> str:
    return str(code or "").split(".")[0].strip()


def _to_float(value) -> float | None:
    try:
        if value in (None, "", "?"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def iv_sizing_bucket(iv_rank: float | None) -> str:
    """Translate IV rank into the sizing throttle bucket used by ANALYST.md."""
    if iv_rank is None:
        return "unknown"
    if iv_rank < 0.15:
        return "half"
    if iv_rank < 0.50:
        return "normal"
    if iv_rank < 0.75:
        return "selective"
    return "tight"


def iv_sizing_guidance(iv_rank: float | None, proxy_name: str) -> str:
    if iv_rank is None:
        return f"{proxy_name} IV proxy unavailable; fall back to overall market IV."
    pct = iv_rank * 100
    if iv_rank < 0.15:
        return f"{proxy_name} IV Rank {pct:.1f}% < 15%; reduce new position sizing by 50%."
    if iv_rank < 0.50:
        return f"{proxy_name} IV Rank {pct:.1f}% is in the normal sizing range."
    if iv_rank < 0.75:
        return f"{proxy_name} IV Rank {pct:.1f}% is elevated; be selective with new entries."
    return f"{proxy_name} IV Rank {pct:.1f}% is very high; only take the strongest setups with wider stops."


def build_iv_lookup(results: list[dict]) -> dict[str, dict]:
    return {
        str(item.get("underlying")): item
        for item in results
        if isinstance(item, dict) and item.get("underlying")
    }


def proxy_candidates_for_stock(stock_code: str, market_cap: float | None = None) -> tuple[str, list[str]]:
    """Pick the best available IV proxy candidates for a stock.

    This is intentionally a board/size heuristic, not a claim of exact index
    membership. It gives the LLM a much better proxy than one global average.
    """
    code = _normalize_stock_code(stock_code)
    market_cap = _to_float(market_cap)

    if code.startswith("688"):
        return "board_prefix:688 (科创板)", ["588000", "588080"]
    if code.startswith(("300", "301")):
        return "board_prefix:300/301 (创业板)", ["159915", "159922", "159919"]
    if code.startswith(("000", "001")):
        return "board_prefix:000/001 (深主板)", ["159901", "159919", "159922"]
    if code.startswith(("002", "003")):
        return "board_prefix:002/003 (深市中小盘)", ["159922", "159919", "159901"]
    if code.startswith(("600", "601", "603", "605")):
        if market_cap is not None and market_cap < 150:
            return "board_prefix:60x + market_cap<150 (沪市中小盘)", ["510500", "510300", "510050"]
        if market_cap is not None and market_cap >= 1200:
            return "board_prefix:60x + market_cap>=1200 (沪市超大盘)", ["510050", "510300", "510500"]
        return "board_prefix:60x (沪市主板)", ["510300", "510500", "510050"]
    return "fallback:broad_market", ["510300", "159919", "510500"]


def stock_iv_proxy(stock_code: str, iv_data: dict, market_cap: float | None = None) -> dict:
    """Resolve a stock-specific IV proxy context from the fetched ETF universe."""
    results = iv_data.get("etf_iv_data", []) if isinstance(iv_data, dict) else []
    lookup = build_iv_lookup(results)
    basis, candidates = proxy_candidates_for_stock(stock_code, market_cap=market_cap)

    primary_code = next((code for code in candidates if code in lookup and lookup[code].get("iv_rank") is not None), None)
    alternates = []
    for code in candidates:
        if code == primary_code or code not in lookup:
            continue
        item = lookup[code]
        if item.get("iv_rank") is None:
            continue
        alternates.append({
            "underlying": code,
            "name": item.get("name", code),
            "iv_rank": round(item.get("iv_rank"), 4),
            "iv_percentile": round(item.get("iv_percentile"), 4),
        })

    if primary_code is None:
        overall = (iv_data or {}).get("overall_sentiment", {}) if isinstance(iv_data, dict) else {}
        rank = _to_float(overall.get("avg_iv_rank"))
        return {
            "basis": "fallback:overall_market",
            "primary_underlying": None,
            "primary_name": "overall_market",
            "iv_rank": round(rank, 4) if rank is not None else None,
            "iv_percentile": _to_float(overall.get("avg_iv_percentile")),
            "interpretation": overall.get("signal"),
            "sizing": iv_sizing_bucket(rank),
            "guidance": iv_sizing_guidance(rank, "Overall market"),
            "alternates": [],
        }

    primary = lookup[primary_code]
    rank = _to_float(primary.get("iv_rank"))
    percentile = _to_float(primary.get("iv_percentile"))
    current_iv = _to_float(primary.get("current_iv"))
    return {
        "basis": basis,
        "primary_underlying": primary_code,
        "primary_name": primary.get("name", primary_code),
        "iv_rank": round(rank, 4) if rank is not None else None,
        "iv_percentile": round(percentile, 4) if percentile is not None else None,
        "current_iv": round(current_iv, 4) if current_iv is not None else None,
        "interpretation": primary.get("interpretation"),
        "sizing": iv_sizing_bucket(rank),
        "guidance": iv_sizing_guidance(rank, primary.get("name", primary_code)),
        "alternates": alternates,
    }


def overall_sentiment(results: list[dict], codes: list[str] | None = None) -> dict:
    """Compute aggregate sentiment from multiple ETF IV readings."""
    code_filter = set(codes or [])
    valid = [
        r for r in results
        if r.get("iv_rank") is not None and (not code_filter or r.get("underlying") in code_filter)
    ]
    if not valid:
        return {"signal": "无数据", "detail": "无法获取IV数据", "based_on": []}

    avg_rank = sum(r["iv_rank"] for r in valid) / len(valid)
    avg_percentile = sum(r["iv_percentile"] for r in valid) / len(valid)

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
        "based_on": [r.get("underlying") for r in valid],
    }


def fetch_all() -> dict:
    """Fetch IV sentiment for the full options dashboard proxy universe."""
    results = []
    for u in UNDERLYINGS:
        data = fetch_iv_rank(u["code"])
        if data:
            data["name"] = u["name"]
            data["desc"] = u["desc"]
            if data.get("iv_rank") is not None:
                data["interpretation"] = interpret_iv_rank(data.get("iv_rank", 0.5))
            else:
                data["interpretation"] = "无数据"
            results.append(data)

    sentiment = overall_sentiment(results, codes=CORE_UNDERLYINGS)

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": "options-learn backend (/api/history/iv-rank)",
        "core_underlyings": CORE_UNDERLYINGS,
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
            current_iv = r.get("current_iv")
            iv_low = r.get("iv_low")
            iv_high = r.get("iv_high")
            iv_rank = r.get("iv_rank")
            iv_pct = r.get("iv_percentile")
            print(f"\n{r['name']} ({r['desc']}):")
            print(
                f"  当前IV: {current_iv*100:.1f}%  |  52周: {iv_low*100:.1f}% - {iv_high*100:.1f}%"
                if None not in (current_iv, iv_low, iv_high)
                else "  当前IV: 无数据"
            )
            if None not in (iv_rank, iv_pct):
                print(f"  IV Rank: {iv_rank*100:.1f}%  |  IV Percentile: {iv_pct*100:.1f}%")
            else:
                print("  IV Rank: 无数据")
            print(f"  解读: {r.get('interpretation', '无数据')}")
        s = data["overall_sentiment"]
        print(f"\n{'='*50}")
        print(f"综合信号: {s['signal']}")
        print(f"核心篮子: {', '.join(s.get('based_on', []))}")
        print(f"均IV Rank: {s['avg_iv_rank']*100:.1f}%  |  均IV Percentile: {s['avg_iv_percentile']*100:.1f}%")
        print(f"含义: {s['implication']}")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
