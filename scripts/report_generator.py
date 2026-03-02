#!/usr/bin/env python3
"""
Report Generator — Generate reports and watchlists from structured data.

Reports focus on market overview + stock recommendations only.
Position status is handled by the tracker, not here.
"""

import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WATCHLIST_DIR = PROJECT_ROOT / "watchlist"
REPORTS_DIR = PROJECT_ROOT / "reports"

WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_watchlist_json(date: str, data: dict, decisions: dict) -> Path:
    """Write watchlist/YYYY-MM-DD.json from collected data and LLM decisions.

    Args:
        date: Date string "YYYY-MM-DD"
        data: Collected data from Phase 1 (strategy_pool, market, enriched, etc.)
        decisions: LLM analysis decisions

    Returns:
        Path to written file.
    """
    market = data.get("market", {})
    indices = market.get("indices", {})

    # Build market overview
    market_overview = {
        "shanghai_composite": _index_summary(indices.get("上证指数", {})),
        "shenzhen_component": _index_summary(indices.get("深证成指", {})),
        "chinext": _index_summary(indices.get("创业板指", {})),
        "sentiment": decisions.get("market_sentiment", "neutral"),
        "hot_sectors": _extract_sector_names(market.get("sectors", {}).get("top5", [])),
        "cold_sectors": _extract_sector_names(market.get("sectors", {}).get("bottom5", [])),
        "notes": decisions.get("market_summary", ""),
    }

    # Strategy scan info
    pool = data.get("strategy_pool", {})
    strategy_scan = {
        "total_stocks_scanned": pool.get("total_stocks", 0),
        "strategy_name": "小市值-无 20RP",
        "scan_time": datetime.now().astimezone().isoformat(),
    }

    # Recommendations from LLM decisions
    recommendations = []
    for item in decisions.get("watchlist", []):
        rec = {
            "code": _format_code(item.get("code", "")),
            "name": item.get("name", ""),
            "price": item.get("price"),
            "rps120": item.get("rps120"),
            "recommendation": item.get("recommendation", "WATCH"),
            "confidence": item.get("confidence", "medium"),
            "reasoning": item.get("reasoning", ""),
        }
        # Add enrichment data if available
        for key in [
            "score_company", "score_trend", "score_value",
            "pe", "valuation_percentile", "revenue_yoy",
            "net_profit_yoy", "gross_margin",
            "highlights", "risks", "events", "catalyst",
        ]:
            if key in item:
                rec[key] = item[key]
        recommendations.append(rec)

    # Summary
    buy_count = sum(1 for r in recommendations if r["recommendation"] == "BUY")
    watch_count = sum(1 for r in recommendations if r["recommendation"] == "WATCH")
    avoid_count = sum(1 for r in recommendations if r["recommendation"] == "AVOID")

    summary = {
        "total_scanned": pool.get("total_stocks", 0),
        "buy_recommendations": buy_count,
        "watch_recommendations": watch_count,
        "avoid_recommendations": avoid_count,
        "market_call": decisions.get("market_call", "谨慎"),
        "reasoning": decisions.get("market_summary", ""),
    }

    watchlist = {
        "date": date,
        "market_overview": market_overview,
        "strategy_scan": strategy_scan,
        "recommendations": recommendations,
        "summary": summary,
    }

    out = WATCHLIST_DIR / f"{date}.json"
    out.write_text(
        json.dumps(watchlist, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out


def generate_report_md(date: str, data: dict, decisions: dict) -> Path:
    """Write reports/YYYY-MM-DD.md from structured data.

    Report includes market overview + stock recommendations ONLY.
    No position status (that's the tracker's domain).

    Args:
        date: Date string "YYYY-MM-DD"
        data: Collected data from Phase 1
        decisions: LLM analysis decisions

    Returns:
        Path to written file.
    """
    lines = [f"# 每日研究报告 {date}\n"]

    # 1. Market Overview
    lines.append("## 市场概览\n")
    market = data.get("market", {})
    indices = market.get("indices", {})

    lines.append("| 指数 | 收盘 | 涨跌幅 |")
    lines.append("|------|------|--------|")
    for name in ["上证指数", "深证成指", "创业板指", "科创50"]:
        idx = indices.get(name, {})
        if "error" not in idx and "close" in idx:
            lines.append(f"| {name} | {idx['close']:.2f} | {idx.get('change_pct', 0):+.2f}% |")
        else:
            lines.append(f"| {name} | N/A | N/A |")
    lines.append("")

    # Breadth
    breadth = market.get("breadth", {})
    if breadth:
        up = breadth.get("up", 0)
        down = breadth.get("down", 0)
        total = breadth.get("total", 0)
        lines.append(f"涨跌比: {up}涨 / {down}跌 / {total}总\n")

    # Sectors
    sectors = market.get("sectors", {})
    if sectors:
        top5 = sectors.get("top5", [])
        bot5 = sectors.get("bottom5", [])
        if top5:
            top_str = ", ".join(f"{s['板块名称']}({s['涨跌幅']:+.2f}%)" for s in top5)
            lines.append(f"**热门板块**: {top_str}\n")
        if bot5:
            bot_str = ", ".join(f"{s['板块名称']}({s['涨跌幅']:+.2f}%)" for s in bot5)
            lines.append(f"**冷门板块**: {bot_str}\n")

    # Market summary from LLM
    if decisions.get("market_summary"):
        lines.append(f"{decisions['market_summary']}\n")

    # 2. Strategy Pool Scan
    lines.append("## 策略池扫描\n")
    pool = data.get("strategy_pool", {})
    lines.append(f"扫描 **{pool.get('total_stocks', 0)}** 只策略池股票")
    lines.append(f"(来源: {pool.get('source', 'unknown')})\n")

    # 3. Recommendations
    watchlist = decisions.get("watchlist", [])
    if watchlist:
        lines.append("## 个股推荐\n")
        for i, item in enumerate(watchlist, 1):
            action = item.get("recommendation", "WATCH")
            confidence = item.get("confidence", "medium")
            name = item.get("name", "")
            code = item.get("code", "")

            lines.append(f"### {i}. {name} ({code}) — {action}/{confidence}\n")

            if item.get("price"):
                lines.append(f"- **价格**: ¥{item['price']}")
            if item.get("rps120"):
                lines.append(f"- **RPS120**: {item['rps120']}%")
            if item.get("pe"):
                lines.append(f"- **PE**: {item['pe']}")

            reasoning = item.get("reasoning", "")
            if reasoning:
                lines.append(f"\n{reasoning}\n")

    # 4. Summary
    lines.append("## 今日研究结论\n")
    buy_recs = [w for w in watchlist if w.get("recommendation") == "BUY"]
    watch_recs = [w for w in watchlist if w.get("recommendation") == "WATCH"]
    avoid_recs = [w for w in watchlist if w.get("recommendation") == "AVOID"]

    lines.append(f"- BUY推荐: {len(buy_recs)}只")
    lines.append(f"- WATCH推荐: {len(watch_recs)}只")
    lines.append(f"- AVOID推荐: {len(avoid_recs)}只")

    if decisions.get("new_learnings"):
        lines.append("\n### 新教训")
        for lesson in decisions["new_learnings"]:
            lines.append(f"- {lesson}")

    lines.append("")

    out = REPORTS_DIR / f"{date}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _index_summary(idx: dict) -> dict:
    """Extract value/change_pct from an index dict."""
    if "error" in idx or "close" not in idx:
        return {"value": None, "change_pct": None}
    return {
        "value": idx["close"],
        "change_pct": idx.get("change_pct", 0),
    }


def _extract_sector_names(sectors: list) -> list[str]:
    """Extract sector names from AkShare board data."""
    return [s.get("板块名称", "") for s in sectors if s.get("板块名称")]


def _format_code(code: str) -> str:
    """Ensure code has exchange suffix."""
    code = str(code).strip()
    if "." in code:
        return code.upper()
    if code.startswith("6"):
        return f"{code}.SH"
    elif code.startswith("0") or code.startswith("3"):
        return f"{code}.SZ"
    return f"{code}.SH"
