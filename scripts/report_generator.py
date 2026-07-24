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


def generate_watchlist_json(date: str, data: dict, decisions: dict, output_dir: Path | None = None) -> Path:
    """Write watchlist JSON from collected data and LLM decisions.

    Args:
        date: Date string "YYYY-MM-DD"
        data: Collected data from Phase 1 (strategy_pool, market, enriched, etc.)
        decisions: LLM analysis decisions
        output_dir: If provided, write to output_dir/watchlist.json instead of watchlist/YYYY-MM-DD.json

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

    # Recommendations from LLM decisions (V1: "watchlist", V2: "skip_list")
    recommendations = []
    for item in (decisions.get("watchlist", []) or decisions.get("skip_list", [])):
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

    if output_dir:
        out = output_dir / "watchlist.json"
    else:
        out = WATCHLIST_DIR / f"{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(watchlist, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out


def generate_report_md(date: str, data: dict, decisions: dict, output_dir: Path | None = None) -> Path:
    """Write report markdown from structured data.

    Report includes market overview + stock recommendations ONLY.
    No position status (that's the tracker's domain).

    Args:
        date: Date string "YYYY-MM-DD"
        data: Collected data from Phase 1
        decisions: LLM analysis decisions
        output_dir: If provided, write to output_dir/report.md instead of reports/YYYY-MM-DD.md

    Returns:
        Path to written file.
    """
    lines = [f"# 每日研究报告 {date}\n"]

    # Which model made these decisions (from the run dir's llm_meta.json,
    # written by phase 2 — self-discovered so --apply replays work too)
    if output_dir is not None:
        meta_path = Path(output_dir).parent / "llm_meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {}
            model = meta.get("primary_model") or meta.get("provider")
            if model:
                src = meta.get("decision_source") or ""
                suffix = f"（{src}）" if src and src != model else ""
                lines.append(f"> 模型: {model}{suffix} · "
                             f"{meta.get('input_tokens', '?')}+{meta.get('output_tokens', '?')} tokens\n")

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

    # 3. Recommendations (V1: "watchlist", V2: "skip_list" + "new_positions")
    watchlist = decisions.get("watchlist", [])

    # V2: new_positions are the BUY recommendations
    new_positions = decisions.get("new_positions", [])

    # V2: skip_list replaces WATCH — stocks considered but not bought
    skip_list = decisions.get("skip_list", [])

    # V2: positions closed today (SELL) — executed via position_decisions.
    # Rendered as its own section so exits aren't invisible in the report.
    sells = [
        d for d in decisions.get("position_decisions", [])
        if str(d.get("action", "")).upper() == "SELL"
    ]

    has_recs = watchlist or new_positions or skip_list or sells

    if has_recs:
        # V1-style watchlist (has recommendation field)
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

        # V2: new positions opened today
        if new_positions:
            lines.append("## 今日开仓\n")
            for i, item in enumerate(new_positions, 1):
                name = item.get("name", "")
                code = item.get("code", "")
                conviction = item.get("conviction", "")
                lines.append(f"### {i}. {name} ({code}) — BUY/{conviction}\n")
                if item.get("entry_price"):
                    lines.append(f"- **入场价**: ¥{item['entry_price']}")
                if item.get("stop"):
                    lines.append(f"- **止损**: ¥{item['stop']}")
                if item.get("target"):
                    lines.append(f"- **目标**: ¥{item['target']}")
                if item.get("rps120"):
                    lines.append(f"- **RPS120**: {item['rps120']}%")
                if item.get("sector"):
                    lines.append(f"- **板块**: {item['sector']} ({item.get('sector_rank', '')})")
                thesis = item.get("thesis", "")
                if thesis:
                    lines.append(f"\n{thesis}\n")

        # V2: positions closed today (SELL)
        if sells:
            lines.append("## 今日平仓\n")
            for i, item in enumerate(sells, 1):
                name = item.get("name", "")
                code = item.get("code", "")
                pnl = item.get("pnl_pct")
                pnl_str = f" — {pnl:+.2f}%" if isinstance(pnl, (int, float)) else ""
                lines.append(f"### {i}. {name} ({code}) — SELL{pnl_str}\n")
                if item.get("exit_price") is not None:
                    lines.append(f"- **出场价**: ¥{item['exit_price']}")
                if item.get("days_held") is not None:
                    lines.append(f"- **持有天数**: {item['days_held']}天")
                if item.get("sector_rank"):
                    lines.append(f"- **板块排名**: {item['sector_rank']}")
                reason = item.get("reason", "")
                if reason:
                    lines.append(f"\n{reason}\n")

        # V2: skip list (considered but not bought)
        if skip_list:
            lines.append("## 跳过标的\n")
            for i, item in enumerate(skip_list, 1):
                name = item.get("name", "")
                code = item.get("code", "")
                reason = item.get("reason", "")
                rps = item.get("rps120")
                rps_str = f" (RPS {rps}%)" if rps else ""
                lines.append(f"{i}. **{name}** ({code}){rps_str} — {reason}")
            lines.append("")

    # 4. Summary
    lines.append("## 今日研究结论\n")
    buy_recs = [w for w in watchlist if w.get("recommendation") == "BUY"]
    watch_recs = [w for w in watchlist if w.get("recommendation") == "WATCH"]
    avoid_recs = [w for w in watchlist if w.get("recommendation") == "AVOID"]

    if watchlist:
        # V1 summary
        lines.append(f"- BUY推荐: {len(buy_recs)}只")
        lines.append(f"- WATCH推荐: {len(watch_recs)}只")
        lines.append(f"- AVOID推荐: {len(avoid_recs)}只")
    else:
        # V2 summary
        lines.append(f"- 新开仓: {len(new_positions)}只")
        lines.append(f"- 平仓: {len(sells)}只")
        lines.append(f"- 跳过: {len(skip_list)}只")

    if decisions.get("new_learnings"):
        lines.append("\n### 新教训")
        for lesson in decisions["new_learnings"]:
            lines.append(f"- {lesson}")

    lines.append("")

    if output_dir:
        out = output_dir / "report.md"
    else:
        out = REPORTS_DIR / f"{date}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
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


def generate_candidates_md(date: str, data: dict, output_dir: Path | None = None) -> Path:
    """Write a candidates summary table from Phase 1 data.

    Shows all strategy pool stocks with RPS, MA distances, and pass/fail status.
    This runs after Phase 1 (before LLM), so it's always available even if the
    LLM step fails or the entry regime blocks all buys.

    Args:
        date: Date string "YYYY-MM-DD"
        data: Collected data from Phase 1 (strategy_pool, ma_data, enriched, entry_regime)
        output_dir: If provided, write there; otherwise writes to reports/

    Returns:
        Path to written file.
    """
    pool = data.get("strategy_pool", {}).get("stocks", [])
    ma_data = data.get("ma_data", {})
    enriched_map = {
        str(c.get("code", "")).split(".")[0]: c
        for c in data.get("enriched", [])
    }
    regime = data.get("entry_regime", {})

    lines = [f"# 候选股票 {date}\n"]

    # Entry regime status
    if regime:
        allow = regime.get("allow_new_positions", False)
        breadth = regime.get("breadth_ratio", 0)
        pos_idx = regime.get("positive_indices", [])
        neg_idx = regime.get("negative_indices", [])
        sizing_multiplier = float(regime.get("sizing_multiplier", 1.0) or 1.0)
        if not allow:
            status = "🚫 BLOCKED"
        elif sizing_multiplier < 1.0:
            status = "⚠ THROTTLED"
        else:
            status = "✅ OPEN"
        lines.append(f"## 入场条件: {status}")
        lines.append(f"- 涨跌比: {breadth:.2f}:1")
        if pos_idx:
            lines.append(f"- 上涨指数: {', '.join(pos_idx)}")
        if neg_idx:
            lines.append(f"- 下跌指数: {', '.join(neg_idx)}")
        lines.append(f"- 新仓位尺寸系数: {sizing_multiplier:.2f}x")
        lines.append(f"- 原因: {regime.get('reason', '')}")
        lines.append("")

    # Table header
    lines.append(f"## 策略池 ({len(pool)} stocks)\n")
    lines.append("| Code | Name | RPS120 | RPS60 | Trend | Co | MA5% | MA10% | MA20% | Status |")
    lines.append("|------|------|--------|-------|-------|-----|------|-------|-------|--------|")

    sweet_spot = []

    for s in pool:
        code = str(s.get("code", "")).split(".")[0]
        name = s.get("name", code)
        rps120 = s.get("rps120", 0)
        rps60 = s.get("rps60", 0)
        trend = s.get("score_trend", "-")
        co = s.get("score_company", "-")

        # Get MA data: first from the stock itself (merged), then from ma_data dict
        ma5 = s.get("dist_ma5_pct")
        ma10 = s.get("dist_ma10_pct")
        ma20 = s.get("dist_ma20_pct")
        if ma5 is None:
            e = enriched_map.get(code) or {}
            ma5 = e.get("dist_ma5_pct")
            ma10 = e.get("dist_ma10_pct")
            ma20 = e.get("dist_ma20_pct")
        if ma5 is None:
            m = ma_data.get(code, {})
            ma5 = m.get("dist_ma5_pct")
            ma10 = m.get("dist_ma10_pct")
            ma20 = m.get("dist_ma20_pct")

        # MA check
        fails = []
        if ma5 is not None and abs(ma5) > 6:
            fails.append("MA5")
        if ma10 is not None and abs(ma10) > 8:
            fails.append("MA10")
        if ma20 is not None and abs(ma20) > 12:
            fails.append("MA20")

        if fails:
            status = f"❌ {','.join(fails)}"
        elif ma5 is not None:
            status = "✅ PASS"
        else:
            status = "⚠️ no MA"

        ma5_s = f"{ma5:+.1f}" if ma5 is not None else "-"
        ma10_s = f"{ma10:+.1f}" if ma10 is not None else "-"
        ma20_s = f"{ma20:+.1f}" if ma20 is not None else "-"
        rps120_s = f"{rps120:.0f}" if isinstance(rps120, (int, float)) else str(rps120)
        rps60_s = f"{rps60:.0f}" if isinstance(rps60, (int, float)) else str(rps60)

        lines.append(
            f"| {code} | {name} | {rps120_s} | {rps60_s} | {trend} | {co} "
            f"| {ma5_s} | {ma10_s} | {ma20_s} | {status} |"
        )

        if not fails and ma5 is not None:
            entry = {"code": code, "name": name, "rps120": rps120, "rps60": rps60,
                     "trend": trend, "co": co, "ma5": ma5, "ma10": ma10, "ma20": ma20}
            sweet_spot.append(entry)

    lines.append("")

    # Sweet spot summary
    if sweet_spot:
        lines.append(f"## Sweet Spot ({len(sweet_spot)})\n")
        lines.append("RPS ≥75%, MA check pass — actionable when regime opens.\n")
        for s in sweet_spot:
            lines.append(
                f"- **{s['name']}** ({s['code']}) RPS120={s['rps120']:.0f} "
                f"Trend={s['trend']} Co={s['co']} "
                f"MA5={s['ma5']:+.1f}% MA10={s['ma10']:+.1f}% MA20={s['ma20']:+.1f}%"
            )
        lines.append("")

    if not sweet_spot:
        lines.append("## No candidates pass all filters today.\n")

    content = "\n".join(lines)
    if output_dir:
        out = output_dir / "candidates.md"
    else:
        out = REPORTS_DIR / f"{date}-candidates.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return out


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
