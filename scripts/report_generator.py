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

    # Data-quality banner: the 2026-07-30 outage ran two days silent because
    # degradation only showed in stderr. If the DB is stale/partial/corrupt,
    # say it HERE, first thing the reader sees.
    health = data.get("db_health") or {}
    if health.get("warnings"):
        mark = "🔴" if not health.get("ok", True) else "🔶"
        lines.append(f"> {mark} **数据质量警报**")
        for w in health["warnings"]:
            lines.append(f"> - {w}")
        lines.append("")

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

    # 1b. Foreseeable-event window (from event_calendar via phase-1 `events`)
    events = data.get("events") or {}
    if events.get("dated") or events.get("ongoing"):
        rw = events.get("risk_window", {})
        _dir_mark = {"supportive": "🟢", "two_sided": "🔶", "risk": "🔴"}
        _impact_zh = {"high": "冲击:高", "medium": "冲击:中", "low": "冲击:低"}

        def _impact(e):
            return _impact_zh.get(e.get("impact"), f"冲击:{e.get('impact')}")

        def _src(e):
            s = (e.get("source") or "").strip()
            if not s:
                return " 〔来源: 未标注〕"
            if s.startswith("http"):
                return f" 〔[来源]({s})〕"
            return f" 〔来源: {s}〕"

        lines.append("## 未来事件窗口\n")
        lines.append("_图例: 加粗日期=**A股影响日**（海外盘后公布的事件，影响日为下一A股交易日，"
                     "公布日另行标注）；图标=方向（🔴利空风险 / 🔶双向不确定 / 🟢利好支撑），"
                     "[冲击:高/中/低]=预估冲击强度——两者独立：🔴[冲击:低]=偏利空但幅度小_\n")
        lines.append(f"**风险档: {rw.get('level', '?')}** — {rw.get('advice', '')}\n")
        for e in events.get("dated", [])[:10]:
            mark = _dir_mark.get(e.get("direction", "risk"), "🔴")
            est = "（日期待确认）" if e.get("certainty") == "estimated" else ""
            rel = "📊**结果已出·影响待落地** " if e.get("released") else ""
            pub = (f"（公布日 {e.get('date')}）"
                   if e.get("date") and e.get("date") != e.get("a_share_impact_date") else "")
            lines.append(f"- {mark} **{e.get('a_share_impact_date')}** "
                         f"(T-{e.get('days_until_impact')}) [{_impact(e)}] "
                         f"{rel}{e.get('name')}{pub}{est} — {e.get('notes', '')}{_src(e)}")
        for e in events.get("ongoing", []):
            mark = _dir_mark.get(e.get("direction", "risk"), "🔴")
            lines.append(f"- {mark} **持续中** [{_impact(e)}] "
                         f"{e.get('name')} — {e.get('notes', '')}{_src(e)}")
        recent = events.get("recent", [])
        if recent:
            lines.append("\n**已落地事件（近几日）** — 结果与市场反应见市场概览段"
                         "（模型每次运行检索实际值）：\n")
            for e in recent[:5]:
                mark = _dir_mark.get(e.get("direction", "risk"), "🔴")
                lines.append(f"- {mark} {e.get('date')} {e.get('name')}"
                             f"（A股影响日 {e.get('a_share_impact_date')}）{_src(e)}")
        st = events.get("fomc_next_session_stats")
        if st:
            lines.append(f"\n> 实测基准: FOMC决议次日A股 — 过去{st.get('n')}次中"
                         f"{st.get('sessions_negative')}次收跌，平均EW "
                         f"{st.get('mean_ew_ret_pct')}%（{st.get('note', '')}）"
                         f"〔来源: 内部复测 scripts/base_rates.py:fomc_next_session_stats，"
                         f"本地价格库可重算〕")
        lines.append("")

    regime = data.get("regime") or {}
    if regime.get("label"):
        lines.append("## 市场机制读数（只读实验）\n")
        lines.append(
            f"**{regime.get('label')}** — RPS60滚动rank-IC(20日) "
            f"{regime.get('rolling_ic20')}（为正 {regime.get('ic_positive_days')}，"
            f"最近已结算 {regime.get('ic_last_resolved')}）· "
            f"池内3日止损率(10日均) {regime.get('pool_stop_rate10')}\n")
        lines.append("> 说明: 此读数不接任何规则、不进入模型提示——先只读观察一段时间；"
                     "两项输入均为滞后指标，转折点处会晚翻。"
                     f"〔来源: {regime.get('source', '未标注')}〕\n")

    gex = data.get("gex") or {}
    if gex.get("etf_gex_data"):
        o = gex.get("overall", {})
        lines.append("## Gamma敞口 (GEX)\n")
        lines.append(f"**{o.get('signal', '?')}**（净负gamma: "
                     f"{o.get('net_negative', '?')}；现价处剖面零轴下方: "
                     f"{o.get('below_flip', '?')}）— {o.get('implication', '')}\n")
        lines.append("| 标的 | 净GEX | 状态 | 现价 | 剖面零轴 | 距离 | put墙/call墙 |")
        lines.append("|------|-------|------|------|----------|------|--------------|")
        for s in gex["etf_gex_data"]:
            lines.append(f"| {s.get('name')} | {s.get('total_net_gex'):.3g} "
                         f"| {s.get('regime')} | {s.get('spot')} "
                         f"| {s.get('flip_point')} "
                         f"| {s.get('dist_to_flip_pct'):+.2f}% "
                         f"| {s.get('put_wall')}/{s.get('call_wall')} |")
        lines.append(f"\n〔来源: {gex.get('source', '未标注')}〕\n")

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

        # V2: new positions opened today.
        # `_not_opened` is stamped by phase3_apply when the intent did not become
        # a position. Before 2026-08-17 this section rendered intent as fact:
        # 688019 was printed under 今日开仓 with entry/stop/target/thesis while
        # nothing was bought, and "新开仓: 1只" below it. A skip is fine; a skip
        # that reads as a fill is not.
        opened = [p for p in new_positions if not p.get("_not_opened")]
        not_opened = [p for p in new_positions if p.get("_not_opened")]

        if opened:
            lines.append("## 今日开仓\n")
            for i, item in enumerate(opened, 1):
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

        if not_opened:
            lines.append("## ⚠️ 想开但没开成\n")
            lines.append("模型决定买入, 但执行阶段被拦下 —— 这些**不是持仓**。\n")
            for i, item in enumerate(not_opened, 1):
                lines.append(
                    f"{i}. **{item.get('name', '')}** ({item.get('code', '')})"
                    f"{' 拟入场 ¥' + str(item['entry_price']) if item.get('entry_price') else ''}"
                    f" — {item['_not_opened']}")
            lines.append("")

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
        # V2 summary. Count what was actually opened, never the intent —
        # `新开仓: 1只` alongside an unchanged 8-position book is how the
        # 2026-08-17 sizing bug stayed invisible.
        blocked = [p for p in new_positions if p.get("_not_opened")]
        lines.append(f"- 新开仓: {len(new_positions) - len(blocked)}只")
        if blocked:
            lines.append(f"- ⚠️ 想开但被执行阶段拦下: {len(blocked)}只")
        lines.append(f"- 平仓: {len(sells)}只")
        lines.append(f"- 跳过: {len(skip_list)}只")

    if decisions.get("new_learnings"):
        lines.append("\n### 新教训")
        for lesson in decisions["new_learnings"]:
            # Hypothesis-system lessons arrive as dicts; render the text, not
            # the raw Python repr (bug seen in the 2026-08-03 reports).
            if isinstance(lesson, dict):
                text = lesson.get("text") or json.dumps(lesson, ensure_ascii=False)
                meta = "、".join(
                    x for x in [lesson.get("type", "")] + list(lesson.get("tags", []) or []) if x)
                lines.append(f"- {text}" + (f"（{meta}）" if meta else ""))
            else:
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
    lines.append("| Code | Name | RPS120 | RPS60 | MA5% | MA10% | MA20% | Status |")
    lines.append("|------|------|--------|-------|------|-------|-------|--------|")

    sweet_spot = []
    wait_list = []

    for s in pool:
        code = str(s.get("code", "")).split(".")[0]
        name = s.get("name", code)
        rps120 = s.get("rps120", 0)
        rps60 = s.get("rps60", 0)

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

        # MA check — split by SIDE, because the two sides mean different things.
        #
        # ANALYST.md Rule 2b is one-sided: "dist_ma5_pct > 6% → SKIP. Stock is
        # overextended short-term … buying a stock that just spiked far ABOVE
        # its moving averages is chasing." This label used abs() and so also
        # condemned deeply-oversold names, which Rule 2b never mentions — a
        # stock 25% BELOW its MA5 was marked ❌ under a no-chasing rule.
        #
        # Both signals are worth having; conflating them is what made the label
        # contradict the spec (2026-08-28 audit). ❌ keeps Rule 2b's meaning,
        # 🔻 carries the below-band warning. Distinct leading glyphs matter:
        # candidate_alpha.parse_candidates() classifies rows by first character
        # and ⚠️ is already taken by "no MA".
        BANDS = (("MA5", ma5, 6), ("MA10", ma10, 8), ("MA20", ma20, 12))
        above = [n for n, v, b in BANDS if v is not None and v > b]
        below = [n for n, v, b in BANDS if v is not None and v < -b]
        fails = above + below

        if above:
            # Chasing takes precedence: Rule 2b is the one the spec marks
            # NON-NEGOTIABLE, so a stock breaching on both sides reads as ❌.
            status = f"❌ {','.join(above)}"
        elif below:
            status = f"🔻 BELOW {','.join(below)}"
        elif ma5 is not None:
            if rps120 and rps120 > 95:
                status = "⏳ >95"
            else:
                status = "✅ PASS"
        else:
            status = "⚠️ no MA"

        ma5_s = f"{ma5:+.1f}" if ma5 is not None else "-"
        ma10_s = f"{ma10:+.1f}" if ma10 is not None else "-"
        ma20_s = f"{ma20:+.1f}" if ma20 is not None else "-"
        rps120_s = f"{rps120:.0f}" if isinstance(rps120, (int, float)) else str(rps120)
        rps60_s = f"{rps60:.0f}" if isinstance(rps60, (int, float)) else str(rps60)

        lines.append(
            f"| {code} | {name} | {rps120_s} | {rps60_s} "
            f"| {ma5_s} | {ma10_s} | {ma20_s} | {status} |"
        )

        if not fails and ma5 is not None:
            entry = {"code": code, "name": name, "rps120": rps120, "rps60": rps60,
                     "ma5": ma5, "ma10": ma10, "ma20": ma20}
            if rps120 and rps120 > 95:
                wait_list.append(entry)
            else:
                sweet_spot.append(entry)

    lines.append("")

    # Sweet spot summary
    if sweet_spot:
        lines.append(f"## Sweet Spot ({len(sweet_spot)})\n")
        lines.append("RPS 75-95%, MA check pass — actionable when regime opens.\n")
        for s in sweet_spot:
            lines.append(
                f"- **{s['name']}** ({s['code']}) RPS120={s['rps120']:.0f} "
                f"MA5={s['ma5']:+.1f}% MA10={s['ma10']:+.1f}% MA20={s['ma20']:+.1f}%"
            )
        lines.append("")

    # Wait list
    if wait_list:
        lines.append(f"## Wait List ({len(wait_list)})\n")
        lines.append("RPS >95% (relative-strength overheated, mean-reversion risk), MA pass — watch for pullback into 85-95 zone.\n")
        for s in wait_list:
            lines.append(
                f"- **{s['name']}** ({s['code']}) RPS120={s['rps120']:.0f} "
                f"MA5={s['ma5']:+.1f}% MA10={s['ma10']:+.1f}% MA20={s['ma20']:+.1f}%"
            )
        lines.append("")

    if not sweet_spot and not wait_list:
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
