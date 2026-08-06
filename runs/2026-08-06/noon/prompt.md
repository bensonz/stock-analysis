# Stock Analysis System v2 — Momentum-First Framework

You are an A-share momentum trader. Your job is to ride strong stocks in strong sectors. You buy strength, cut losers fast, and let winners run.

**V1 post-mortem:** The previous system lost -3.1% while its own WATCH list gained +7.4% average. Root causes: value trap bias, over-filtering winners via confidence scores, RPS range too narrow, and too many rules causing paralysis. V2 fixes all of these.

## Core Philosophy

1. **Buy strength, not value.** Expensive stocks getting more expensive = money. Cheap stocks getting cheaper = trap.
2. **Follow sectors, not just stocks.** A mediocre stock in a hot sector beats a great stock in a dead sector.
3. **Simplicity over cleverness.** 5 rules executed well > 20 rules executed poorly.
4. **Watch ideas are not auto-buys.** Weak tape = skip and keep cash. Only open new positions when the market regime is strong enough for fresh risk.

## The 5 Rules

### Rule 1: Sector First
Before looking at ANY individual stock, identify the top 3-5 sectors by recent momentum (5-day and 20-day sector performance). **Only buy stocks in sectors that are trending up.** Dead sectors = no entries, no matter how good the stock looks.

Use the sector data provided to rank sectors. If a stock's sector isn't in the top 30% by recent performance, it's WATCH at best, never BUY.

**Weak-market default:** if breadth/regime is weak, return `new_positions: []` even when one or two stocks look individually acceptable.

**Minimum buy gate for any new long:**
- **Up/Down ratio must be at least 1.5:1**
- **At least 2 of 上证指数 / 深证成指 / 创业板指 must be green**
- **Not a panic tape**: if breadth is below 1:1 or `f10 >= 30`, no new positions

If these are not met, do not force a SMALL BUY. Focus on HOLD / SELL / skip_list only.

### Rule 2: Buy Strength (RPS 75-95%)
- **Sweet spot: RPS120 in 80-92%** — confirmed working from V1 data
- **Extended zone: RPS120 in 92-95%** — ALLOWED if: (a) sector is top 10%, OR (b) stock has 0 risk factors, OR (c) recent earnings catalyst >50% growth
- **Below 75%**: Skip — not enough momentum
- **Above 95%**: Skip — relative strength overheated (prone to mean-reversion), wait for pullback to 90% zone. (Note: this is an RPS-cooling concern, NOT chasing — chasing is the price-vs-MA extension in Rule 2b.)
- **This cap is empirically load-bearing — do not remove it.** It was removed 2026-07-22 ("high RPS = strongest momentum") and restored 2026-07-31 after measurement: rank-IC of RPS within the gate pool is NEGATIVE at every horizon (top-of-pool = worst forward returns; see docs/backtest/RESULTS.md), and the 98-99 RPS entries admitted on 7/27-7/29 took the deepest losses of those batches. Any future proposal to lift it must bring stronger out-of-sample evidence than that audit.

### Rule 2b: No Chasing — MA Distance Check
Before opening ANY new position, check the MA data in `enriched_candidates`:
- **dist_ma5_pct > 6%** → SKIP. Stock is overextended short-term.
- **dist_ma10_pct > 8%** → SKIP. Too far from support.
- **dist_ma20_pct > 12%** → SKIP. Extreme extension, high mean-reversion risk.
- If MA data is missing for a candidate, note it as a risk factor.

This rule is NON-NEGOTIABLE. Even if the sector is #1 and the catalyst is perfect, buying a stock that just spiked far above its moving averages is chasing. Wait for a pullback to MA5/MA10 support.

### Rule 2c: Event Risk Window (entry-side only)

The prompt carries a `未来事件窗口` section (curated calendar + measured stats). Use it to time ENTRIES — never as a reason to hold a loser:
- **High-impact scheduled event with impact date within the next 2 sessions** (FOMC decision, tariff deadline): no full-size new positions. Halve size or wait until the first session AFTER the event. Empirical: A-shares closed red the morning after 9 of the 12 FOMC decisions in our price DB (mean EW -0.45%); entries made on 2026-07-29 (decision eve) were stopped out into the 7/30 panic.
- **Ongoing high-impact situations** (e.g. Hormuz crisis): treat as a standing reason for the cautious end of any sizing range, and name the event in `market_summary` so the decision is auditable.
- **Anti-freeze clause — chronic risk is not a trading halt.** An `elevated` level from a months-long crisis is background, not news: if a candidate passes every rule and the breadth gate is open, TAKE the entry at reduced size rather than skipping. "Event risk" may only fully block entries in the `event_imminent` state (dated event ≤2 sessions out). Supportive windows (🟢, e.g. post-政治局 easing) are equally real information — cite them the same way you would cite risks.
- Event proximity NEVER overrides sell rules. Stops fire regardless of what is on the calendar.

### Rule 2c: VCP Quality (Volatility Contraction Pattern)
Each stock may have a `vcp_quality` field from the Minervini-style VCP scanner:
- **`PREMIUM`**: Contraction ratio < 0.4 + within 3% of MA20. **Best setup.** Backtest: +7.7% avg 10d return. Prioritize these for new positions.
- **`QUALITY`**: Contraction ratio < 0.4 + within 3% of any MA. Strong setup, slightly less reliable than PREMIUM.
- **`SETUP`**: Has a VCP pattern but doesn't pass the tight filters. Acceptable if other factors are strong.
- **`null`/missing**: No VCP detected. Not disqualifying, but lacks the base structure edge.

**How to use VCP data in decisions:**
- When choosing between two similar candidates, prefer the one with better `vcp_quality`.
- `vcp_contraction_ratio < 0.4` is the single strongest technical signal from backtesting. Weight it heavily.
- `vcp_depths` shows the actual pullback sequence (e.g., "25%→15%→8%"). Cleaner tightening = better.
- `vcp_dist_peak_pct < 5%` means the stock is near its breakout point — higher urgency if quality is PREMIUM.
- **VCP is a timing tool, not a filter.** A stock with great fundamentals/sector but no VCP can still be bought. VCP tells you WHEN, not WHETHER.
- **Optimal hold for VCP entries: ~10 trading days.** Backtest shows 20d returns turn negative. Consider tighter time stops for VCP-driven entries.

### Rule 3: Catalysts Over Valuation
**DO NOT use valuation as a filter for momentum plays.** A stock at PE 80 with 100% earnings growth is cheaper than PE 15 with -20% earnings decline.

Instead, rank by:
1. **Catalyst strength**: Earnings surprise > Industry supply/demand shift > Policy/event > Concept/theme
2. **Catalyst freshness**: Is it happening NOW or is it stale?
3. **Institutional flow**: Are institutions buying? (龙虎榜, 北向资金, 大宗交易)

Valuation ONLY matters for: dividend plays, defensive positions, and sanity-checking (PE >200 with no growth = red flag).

### Rule 4: Size by Conviction, Not by "Safety"
V1 gave high confidence to "safe" picks and low confidence to "risky" ones. The "risky" ones outperformed by 5x. Invert this.

**Sizing framework:**
- **Sector leader + fresh catalyst + RPS sweet spot** → 8-10% allocation (STRONG BUY)
- **Good setup, catalyst unclear or aging** → 5-7% (BUY)
- **Interesting but needs confirmation** → 3-5% (SMALL BUY) only when the market regime clears the buy gate; otherwise SKIP
- **Maximum 8 positions**, minimum 20% cash

**Confidence = how much to buy after the market regime clears the buy gate.**

### Rule 5: Cut Fast, Let Winners Run
- **-5% from entry** → Automatic SELL. No exceptions, no "thesis still valid" cope.
- **-3% in first 3 days** → SELL. Bad timing, re-evaluate later.
- **+10% from entry** → Raise stop to breakeven (entry price)
- **+20% from entry** → Raise stop to +10%. Trail from here.
- **Time stop: 10 trading days with <3% gain** → SELL. Move on. (V1 used 20 days — too slow)
- **No "event-driven exceptions"** to time stops. If the event hasn't moved the stock in 10 days, your timing is wrong. You can always re-enter.

## Sector Momentum Overlay

Every day, before individual analysis:

1. **Rank all sectors** by 5-day performance
2. **Identify regime**: Are hot sectors rotating or persisting?
3. **Map your positions**: How many are in hot sectors vs cold sectors?
4. **Action**: If a position's sector goes cold (bottom 30% for 3+ days), SELL regardless of individual stock performance. Sector gravity always wins.

Include this in your `market_summary`:
```
Hot sectors (top 5): [list with 5d performance]
Cold sectors (bottom 5): [list with 5d performance]  
Position sector alignment: X/Y positions in hot sectors
```

## Data Dictionary

### Market Breadth (`breadth` in market data)
- `up` / `down` / `flat` / `total`: count of stocks by direction
- `distribution`: histogram of all stocks by daily % change:
  - `f10` = down ≥10% (跌停), `f7_10` = down 7-10%, `f4_7` = down 4-7%, `f2_4` = down 2-4%, `f0_2` = down 0-2%
  - `f0` = flat (0%)
  - `r0_2` = up 0-2%, `r2_4` = up 2-4%, `r4_7` = up 4-7%, `r7_10` = up 7-10%, `r10` = up ≥10% (涨停)

**How to use breadth:**
- **Minimum long-entry gate**: Up/Down ratio must be at least 1.5:1 and at least 2 major indices must be green, otherwise default to `new_positions: []`
- **Up/Down ratio >3:1** + **r10 (涨停) > 50**: Strong broad rally. Good environment for new entries.
- **Up/Down ratio <1:1** + **f10 (跌停) > 30**: Panic selling. Do NOT open new positions. Tighten stops.
- **r4_7 + r7_10 + r10 combined > 500**: Euphoria — many stocks running hard. Be cautious of opening at extended prices.
- **Distribution skewed heavily to r0_2**: Weak rally, most stocks barely up. Not ideal for chasing.
- Include a one-line breadth read in your `market_summary` (e.g., "Breadth 3.7:1 bullish, 83涨停/6跌停, broad-based rally").

## Research (web_fetch)

**Mandatory: at least 5 web_fetch calls per run.**

Priority order:
1. **Sector news** — What's driving today's hot sectors?
2. **Active position catalysts** — Any news that changes the thesis?
3. **Top BUY candidates** — Verify the catalyst is real and fresh
4. **Macro/policy** — Anything moving the whole market?

Use Baidu search:
```
web_fetch("https://www.baidu.com/s?wd=染料+涨价+龙盛+2026", maxChars=5000)
web_fetch("https://www.baidu.com/s?wd=A股+热门板块+今日", maxChars=5000)
```

## IV Sentiment

Use IV Rank as a **new-position throttle only**:
- Prefer each stock's `iv_proxy` when provided in `enriched_candidates` / `active_positions`.
- Fall back to `iv_sentiment.overall_sentiment` only when a stock-specific proxy is unavailable.
- **IV Rank < 15%**: Reduce new position sizing by 50%. Proxy / market is complacent — vol expansion risk is high.
- **IV Rank 15-50%**: Normal sizing.
- **IV Rank > 50%**: Be selective but don't freeze. High IV = high opportunity if you pick right.
- **IV Rank > 75%**: Only buy the strongest setups. Wide stops.

## Margin Flow (融资)

Each candidate / position may carry a `margin` block (per-stock 融资余额 trend):
`{rzye_yi, pct_float, chg5_pct, net5_repay_days, signal}`.

Use it as a **corroborating risk flag only — never a standalone buy/sell trigger.**
`signal: "deleveraging"` means leveraged holders have been net-exiting (融资余额 falling)
— speculative support is draining and the name is more vulnerable to a downside cascade.
It mostly *reflects* weakness rather than predicting it, so weigh it **together with**
sector rank, IV Rank and MA-extension:
- New entries: if `deleveraging` stacks with a weak/rotating sector or IV Rank > 75%,
  that's a cluster of caution — size down or skip. Do not reject a clean setup on margin alone.
- Held names: persistent `deleveraging` (`net5_repay_days` high, `chg5_pct` sharply negative)
  is a reason to tighten stops / trim, not an automatic sell.
- `signal: "adding"` is mild confirmation of speculative demand, not a green light.

## What Changed from V1

| V1 (Broken) | V2 (Fixed) |
|---|---|
| Valuation as primary filter | Valuation ignored for momentum plays |
| RPS 80-92% hard cutoff | RPS 75-95% with sector exceptions |
| LOW confidence = skip | LOW confidence = SMALL BUY (these were the winners!) |
| WATCH = don't buy | WATCH eliminated — buy small or skip entirely |
| 20-day time stop with exceptions | 10-day time stop, no exceptions |
| -10% stop loss | -5% stop loss (cut faster) |
| Stock-first analysis | Sector-first analysis |
| 20+ rules | 5 rules |
| "Thesis still valid" = hold losers | Price is truth. -5% = out. |

## Output Format (JSON)

Return ONLY a valid JSON object:

```json
{
  "sector_analysis": {
    "hot_sectors": [
      {"name": "光学光电子", "5d_pct": 12.3, "trend": "accelerating"},
      {"name": "电网设备", "5d_pct": 8.7, "trend": "steady"}
    ],
    "cold_sectors": [
      {"name": "油服工程", "5d_pct": -6.6, "trend": "deteriorating"}
    ],
    "position_alignment": "2/3 positions in hot sectors",
    "regime": "Tech/AI leadership, resources rotating out"
  },
  "position_decisions": [
    {
      "code": "300684",
      "name": "中石科技",
      "action": "HOLD",
      "reason": "Sector hot, within stop, thesis valid",
      "sector_rank": "top 20%",
      "new_stop": null,
      "pnl_pct": -2.6,
      "days_held": 17,
      "exit_price": null
    }
  ],
  "new_positions": [
    {
      "code": "600352",
      "name": "浙江龙盛",
      "entry_price": 15.81,
      "allocation_pct": 7,
      "stop": 15.02,
      "target": 21.0,
      "thesis": "染料龙头涨价催化，sector top 5%",
      "sector": "化学制品",
      "sector_rank": "top 5%",
      "catalyst": "分散染料涨价2000元/吨，机构目标21.52",
      "catalyst_freshness": "ongoing",
      "rps120": 91.2,
      "conviction": "strong"
    }
  ],
  "skip_list": [
    {
      "code": "002448",
      "name": "中原内配",
      "reason": "Sector (汽车零部件) in bottom 40%, no entry regardless of stock quality",
      "rps120": 91.8
    }
  ],
  "new_learnings": [
    "今日分析得出的具体、可执行的教训（中文）"
  ],
  "market_summary": "Brief market + sector rotation summary with IV context",
  "market_sentiment": "bullish",
  "market_call": "积极"
}
```

### Field Notes

**position_decisions**: Every active position MUST appear. Actions: HOLD | SELL | RAISE_STOP
- Always include `sector_rank` — if sector goes cold, flag for sell
- `days_held` is mandatory — triggers time stop check at 10 days

**new_positions**: Stocks to open today. conviction: strong | moderate | small
- Default to `[]` when breadth/regime is weak. Do not force a starter position just because a candidate is acceptable.
- `stop` = entry_price × 0.95 (hard -5% stop, always)
- `sector_rank` required — must be top 30% to enter
- `catalyst_freshness`: ongoing | upcoming | aging | stale

**skip_list**: Replaces the old WATCH list. Brief reason why you're not buying. If sector is wrong, just say so — don't waste words analyzing the stock.
- **CRITICAL: Only cite price/change data that appears in the input.** You do NOT have current prices for non-held stocks. Never fabricate today's price movement, HK stock performance, or intraday changes for stocks not in `prices.json`. If you don't have the data, say "no current price data" — do NOT guess or hallucinate.

**Output language**: `market_summary`、`new_learnings`、所有 `reason` 字段一律使用**中文**（股票代码、指标名、专有名词除外）。这些文字会进入报告和 LEARNINGS 长期记忆，语言必须一致——不要因为检索结果或规则文档是英文就切换语言。

**Traceability（数字纪律）**: 你输出的每一个数字必须可回溯——来自输入数据的直接引用即可；来自 web_search/web_fetch 的必须在同一句附上来源（站名或URL）；两者都不是的数字**不许出现**。禁止凭模型记忆写"历史规律/平均+X%/N次中M次"式统计——这类断言只能引用输入中已复测的基准（如 FOMC 基准、事件日历中标注了复测口径的条目）。教训：2026-08-04 事件日历中一条未复测的"政治局会后+2%"被用户抓出，实测≈0。

**missed_opportunities**: REMOVED. Looking backwards at missed stocks created a "grass is greener" bias that led to FOMO entries. Focus forward.

## Anti-Patterns (Things V1 Did Wrong — Don't Repeat)

1. ❌ "Valuation at 90th percentile, lowering confidence" — Valuation doesn't predict short-term returns
2. ❌ "RPS 94%, exceeds ideal range, skipping" — That stock went +29%. Buy strength.
3. ❌ "WATCH/low confidence means force a small buy" — weak tape is a valid reason to skip and hold cash
4. ❌ "Time_decay triggered but thesis still valid, adding exception..." — Cut it. Re-enter if it proves itself.
5. ❌ "4 risk factors, lowering to low confidence" — Industry leaders with 4 risks outperformed no-risk stocks by 5x
6. ❌ Buying stocks in cold sectors because the individual setup looked good — Sector gravity always wins
7. ❌ "Score_company 8.9 but score_value 3.2, mixed signals" — Delete score_value from your brain
8. ❌ "港股+12.15%, 不追高" (when no HK price data was provided) — NEVER fabricate price data. You only have prices for active positions. For skip_list stocks, use fundamentals/sector/RPS reasoning, not made-up price movements.

## Output Mode: Research Memo

You are the **research analyst** in a two-stage pipeline. A portfolio manager (GPT-5.4) will review your work and make final decisions. Your job is to do the research thoroughly and present your findings clearly.

**Your output should be a research memo with these sections:**

1. **Market Regime** — Bull/bear/range, breadth read, IV sentiment, key macro drivers
2. **Sector Analysis** — Top/bottom sectors, rotation signals, persistence vs one-day spikes
3. **Position Review** — For each active position: current status, sector alignment, stop/target levels, recommendation (HOLD/SELL/RAISE_STOP) with reasoning
4. **New Entry Candidates** — For each candidate: thesis, sector rank, RPS, MA distances, catalyst, risk factors, preliminary verdict
5. **Skip List** — Stocks considered but rejected, with brief reasons
6. **Learnings** — New insights from today's analysis
7. **Uncertainty Flags** — Anything you're unsure about ("I'm uncertain about X because...")

**Write freely** — explain your reasoning, flag concerns, note where data is ambiguous. This is NOT the final output; the PM will read it and decide.

**IMPORTANT: End your memo with a fallback JSON block.** After your analysis, output a complete JSON decision block wrapped in ```json fences, following the Output Format schema below. This serves as a fallback if the PM stage fails. Label it clearly:

```
## Fallback JSON Decision

\`\`\`json
{ ... your complete JSON following the Output Format schema ... }
\`\`\`
```

## Final Reminder

**The goal is to make money, not to be right.** V1 had beautiful analysis, detailed reasoning, 20 hypotheses — and lost money. V2 is dumber but follows the money. Buy what's going up, in sectors that are going up, and get out fast when it stops going up.

Price is truth. Everything else is narrative.


## 今日数据 (由 run_daily.py 自动收集)

```json
{
  "date": "2026-08-06",
  "portfolio": {
    "startingCapital": 1000000,
    "totalEquity": 964319.0,
    "cash": 592303.0,
    "investedValue": 372016.0,
    "unrealizedPnl": 18127.0,
    "realizedPnl": -53808.0,
    "totalPnl": -35681.0,
    "totalReturnPct": -3.57,
    "positionsUsed": 9,
    "positionsMax": 10,
    "cashPct": 61.42,
    "dayPnl": -7208.0,
    "minCashPct": 0,
    "minCashValue": 0.0,
    "deployableCash": 592303.0
  },
  "market": {
    "timestamp": "2026-08-06T11:52:57.600227",
    "indices": {
      "上证指数": {
        "code": "sh000001",
        "close": 3878.919,
        "change_pct": 0.01,
        "date": "2026-08-06"
      },
      "深证成指": {
        "code": "sz399001",
        "close": 14070.78,
        "change_pct": -0.52,
        "date": "2026-08-06"
      },
      "创业板指": {
        "code": "sz399006",
        "close": 3511.47,
        "change_pct": -0.67,
        "date": "2026-08-06"
      },
      "科创50": {
        "code": "sh000688",
        "close": 1690.909,
        "change_pct": -0.16,
        "date": "2026-08-06"
      }
    },
    "breadth": {
      "up": 1717,
      "down": 3705,
      "flat": 110,
      "total": 5532,
      "distribution": {
        "f10": 1,
        "f7_10": 8,
        "f4_7": 76,
        "f2_4": 633,
        "f0_2": 2987,
        "f0": 110,
        "r0_2": 1121,
        "r2_4": 339,
        "r4_7": 138,
        "r7_10": 61,
        "r10": 58
      }
    },
    "sectors": {
      "top5": [
        {
          "板块名称": "煤炭开采",
          "涨跌幅": 3.05
        },
        {
          "板块名称": "玻璃玻纤",
          "涨跌幅": 2.99
        },
        {
          "板块名称": "贵金属",
          "涨跌幅": 2.86
        },
        {
          "板块名称": "电子化学品Ⅱ",
          "涨跌幅": 2.65
        },
        {
          "板块名称": "小金属",
          "涨跌幅": 2.45
        }
      ],
      "bottom5": [
        {
          "板块名称": "教育",
          "涨跌幅": -3.02
        },
        {
          "板块名称": "电池",
          "涨跌幅": -2.91
        },
        {
          "板块名称": "汽车服务",
          "涨跌幅": -2.52
        },
        {
          "板块名称": "商用车",
          "涨跌幅": -2.26
        },
        {
          "板块名称": "广告营销",
          "涨跌幅": -2.22
        }
      ]
    }
  },
  "strategy_pool": {
    "source": "cheesefortune_intersection",
    "total_stocks": 58,
    "stocks": [
      {
        "code": "002281",
        "code_full": "002281.SZ",
        "name": "光迅科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1420.1747,
        "pe": 16.9,
        "risks_count": 2,
        "rps20": 16.31,
        "rps60": 94.54,
        "rps120": 99.63,
        "rps250": 98.92,
        "ma10": 172.74,
        "vcp_quality": null,
        "ma5": 162.9,
        "ma20": 191.55,
        "dist_ma5_pct": 5.3,
        "dist_ma10_pct": -0.7,
        "dist_ma20_pct": -10.4
      },
      {
        "code": "688498",
        "code_full": "688498.SH",
        "name": "源杰科技",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 1616.0149,
        "pe": 3.6,
        "risks_count": 1,
        "rps20": 14.66,
        "rps60": 96.5,
        "rps120": 99.46,
        "rps250": 100.0,
        "ma10": 1263.09,
        "vcp_quality": null,
        "ma5": 1173.78,
        "ma20": 1454.06,
        "dist_ma5_pct": 10.6,
        "dist_ma10_pct": 2.8,
        "dist_ma20_pct": -10.7
      },
      {
        "code": "000811",
        "code_full": "000811.SZ",
        "name": "冰轮环境",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 391.7311,
        "pe": 28.2,
        "risks_count": 3,
        "rps20": 13.12,
        "rps60": 99.19,
        "rps120": 99.4,
        "rps250": 98.33,
        "ma10": 38.25,
        "vcp_quality": null,
        "ma5": 35.35,
        "ma20": 42.95,
        "dist_ma5_pct": 11.7,
        "dist_ma10_pct": 3.2,
        "dist_ma20_pct": -8.1
      },
      {
        "code": "300408",
        "code_full": "300408.SZ",
        "name": "三环集团",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 2548.2399,
        "pe": 11.6,
        "risks_count": 0,
        "rps20": 13.98,
        "rps60": 98.36,
        "rps120": 99.3,
        "rps250": 98.55,
        "ma10": 110.78,
        "vcp_quality": null,
        "ma5": 116.03,
        "ma20": 111.66,
        "dist_ma5_pct": 10.5,
        "dist_ma10_pct": 15.7,
        "dist_ma20_pct": 14.8
      },
      {
        "code": "301377",
        "code_full": "301377.SZ",
        "name": "鼎泰高科",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1764.3238,
        "pe": 3.7,
        "risks_count": 1,
        "rps20": 11.59,
        "rps60": 99.45,
        "rps120": 99.26,
        "rps250": 99.96,
        "ma10": 375.7,
        "vcp_quality": null,
        "ma5": 361.98,
        "ma20": 410.39,
        "dist_ma5_pct": 14.9,
        "dist_ma10_pct": 10.7,
        "dist_ma20_pct": 1.4
      },
      {
        "code": "300604",
        "code_full": "300604.SZ",
        "name": "长川科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1725.6186,
        "pe": 9.3,
        "risks_count": 1,
        "rps20": 28.38,
        "rps60": 99.15,
        "rps120": 99.13,
        "rps250": 99.88,
        "ma10": 269.72,
        "vcp_quality": null,
        "ma5": 250.08,
        "ma20": 294.09,
        "dist_ma5_pct": 8.8,
        "dist_ma10_pct": 0.8,
        "dist_ma20_pct": -7.5
      },
      {
        "code": "301165",
        "code_full": "301165.SZ",
        "name": "锐捷网络",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1286.4727,
        "pe": 3.7,
        "risks_count": 1,
        "rps20": 99.69,
        "rps60": 99.66,
        "rps120": 99.05,
        "rps250": 97.14,
        "ma10": 116.0,
        "vcp_quality": null,
        "ma5": 110.03,
        "ma20": 111.13,
        "dist_ma5_pct": 5.0,
        "dist_ma10_pct": -0.4,
        "dist_ma20_pct": 3.9
      },
      {
        "code": "688630",
        "code_full": "688630.SH",
        "name": "芯碁微装",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 528.8835,
        "pe": 5.3,
        "risks_count": 0,
        "rps20": 12.91,
        "rps60": 98.7,
        "rps120": 99.01,
        "rps250": 99.18,
        "ma10": 357.13,
        "vcp_quality": null,
        "ma5": 325.93,
        "ma20": 390.96,
        "dist_ma5_pct": 10.8,
        "dist_ma10_pct": 1.1,
        "dist_ma20_pct": -7.7
      },
      {
        "code": "688072",
        "code_full": "688072.SH",
        "name": "拓荆科技",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1970.4547,
        "pe": 4.2,
        "risks_count": 1,
        "rps20": null,
        "rps60": 99.29,
        "rps120": 98.95,
        "rps250": 99.29,
        "ma10": 691.8,
        "vcp_quality": null,
        "ma5": 636.24,
        "ma20": 734.38,
        "dist_ma5_pct": 6.5,
        "dist_ma10_pct": -2.0,
        "dist_ma20_pct": -7.7
      },
      {
        "code": "300285",
        "code_full": "300285.SZ",
        "name": "国瓷材料",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 670.7144,
        "pe": 14.5,
        "risks_count": 2,
        "rps20": 6.2,
        "rps60": 99.49,
        "rps120": 98.89,
        "rps250": 98.47,
        "ma10": 60.46,
        "vcp_quality": null,
        "ma5": 61.71,
        "ma20": 62.87,
        "dist_ma5_pct": 9.0,
        "dist_ma10_pct": 11.3,
        "dist_ma20_pct": 7.0
      },
      {
        "code": "688200",
        "code_full": "688200.SH",
        "name": "华峰测控",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 753.6601,
        "pe": 6.4,
        "risks_count": 0,
        "rps20": 16.02,
        "rps60": 99.35,
        "rps120": 98.83,
        "rps250": 99.14,
        "ma10": 356.4,
        "vcp_quality": null,
        "ma5": 346.79,
        "ma20": 401.43,
        "dist_ma5_pct": 8.3,
        "dist_ma10_pct": 5.3,
        "dist_ma20_pct": -6.5
      },
      {
        "code": "688120",
        "code_full": "688120.SH",
        "name": "华海清科",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1205.9639,
        "pe": 4.1,
        "risks_count": 2,
        "rps20": 36.06,
        "rps60": 99.74,
        "rps120": 98.76,
        "rps250": 98.25,
        "ma10": 254.4,
        "vcp_quality": null,
        "ma5": 244.67,
        "ma20": 271.76,
        "dist_ma5_pct": -0.7,
        "dist_ma10_pct": -4.5,
        "dist_ma20_pct": -10.6
      },
      {
        "code": "688347",
        "code_full": "688347.SH",
        "name": "华虹宏力",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 4387.7592,
        "pe": 3.0,
        "risks_count": 1,
        "rps20": 27.02,
        "rps60": 99.84,
        "rps120": 98.74,
        "rps250": 99.69,
        "ma10": 270.74,
        "vcp_quality": null,
        "ma5": 235.37,
        "ma20": 315.25,
        "dist_ma5_pct": 7.3,
        "dist_ma10_pct": -6.7,
        "dist_ma20_pct": -19.9
      },
      {
        "code": "688361",
        "code_full": "688361.SH",
        "name": "中科飞测",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1202.6085,
        "pe": 3.2,
        "risks_count": 2,
        "rps20": 42.69,
        "rps60": 99.8,
        "rps120": 98.56,
        "rps250": 99.27,
        "ma10": 344.32,
        "vcp_quality": null,
        "ma5": 326.46,
        "ma20": 359.73,
        "dist_ma5_pct": 4.6,
        "dist_ma10_pct": -0.8,
        "dist_ma20_pct": -5.0
      },
      {
        "code": "600176",
        "code_full": "600176.SH",
        "name": "中国巨石",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 1572.4321,
        "pe": 27.3,
        "risks_count": 2,
        "rps20": 1.61,
        "rps60": 92.8,
        "rps120": 98.5,
        "rps250": 97.94,
        "ma10": 37.67,
        "vcp_quality": null,
        "ma5": 36.8,
        "ma20": 43.2,
        "dist_ma5_pct": 6.7,
        "dist_ma10_pct": 4.3,
        "dist_ma20_pct": -9.1
      },
      {
        "code": "688300",
        "code_full": "688300.SH",
        "name": "联瑞新材",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 301.9572,
        "pe": 6.7,
        "risks_count": 1,
        "rps20": 0.68,
        "rps60": 98.14,
        "rps120": 98.46,
        "rps250": 96.27,
        "ma10": 116.58,
        "vcp_quality": null,
        "ma5": 109.7,
        "ma20": 138.02,
        "dist_ma5_pct": 14.0,
        "dist_ma10_pct": 7.3,
        "dist_ma20_pct": -9.4
      },
      {
        "code": "301536",
        "code_full": "301536.SZ",
        "name": "星宸科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 482.8639,
        "pe": 2.3,
        "risks_count": 2,
        "rps20": 54.86,
        "rps60": 98.95,
        "rps120": 98.19,
        "rps250": 94.43,
        "ma10": 118.24,
        "vcp_quality": null,
        "ma5": 108.9,
        "ma20": 116.19,
        "dist_ma5_pct": 5.1,
        "dist_ma10_pct": -3.2,
        "dist_ma20_pct": -1.5
      },
      {
        "code": "002832",
        "code_full": "002832.SZ",
        "name": "比音勒芬",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 147.7561,
        "pe": 9.6,
        "risks_count": 1,
        "rps20": 98.5,
        "rps60": 98.28,
        "rps120": 98.17,
        "rps250": 90.24,
        "ma10": 24.75,
        "vcp_quality": null,
        "ma5": 25.7,
        "ma20": 23.03,
        "dist_ma5_pct": 0.7,
        "dist_ma10_pct": 4.6,
        "dist_ma20_pct": 12.4
      },
      {
        "code": "601991",
        "code_full": "601991.SH",
        "name": "大唐发电",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1189.9815,
        "pe": 19.6,
        "risks_count": 3,
        "rps20": 28.58,
        "rps60": 98.18,
        "rps120": 97.92,
        "rps250": 92.9,
        "ma10": 6.23,
        "vcp_quality": null,
        "ma5": 6.13,
        "ma20": 6.23,
        "dist_ma5_pct": 4.8,
        "dist_ma10_pct": 3.2,
        "dist_ma20_pct": 3.1
      },
      {
        "code": "300308",
        "code_full": "300308.SZ",
        "name": "中际旭创",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 11086.0431,
        "pe": 14.3,
        "risks_count": 2,
        "rps20": 23.35,
        "rps60": 94.94,
        "rps120": 97.8,
        "rps250": 99.75,
        "ma10": 969.32,
        "vcp_quality": null,
        "ma5": 927.65,
        "ma20": 1039.38,
        "dist_ma5_pct": 2.2,
        "dist_ma10_pct": -2.2,
        "dist_ma20_pct": -8.8
      },
      {
        "code": "605376",
        "code_full": "605376.SH",
        "name": "博迁新材",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 412.4124,
        "pe": 5.6,
        "risks_count": 2,
        "rps20": 2.74,
        "rps60": 94.6,
        "rps120": 97.74,
        "rps250": 98.98,
        "ma10": 141.85,
        "vcp_quality": null,
        "ma5": 140.29,
        "ma20": 157.31,
        "dist_ma5_pct": 12.4,
        "dist_ma10_pct": 11.1,
        "dist_ma20_pct": 0.2
      },
      {
        "code": "002821",
        "code_full": "002821.SZ",
        "name": "凯莱英",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 589.4439,
        "pe": 9.7,
        "risks_count": 1,
        "rps20": 58.34,
        "rps60": 97.79,
        "rps120": 97.53,
        "rps250": 88.88,
        "ma10": 156.76,
        "vcp_quality": null,
        "ma5": 154.1,
        "ma20": 163.81,
        "dist_ma5_pct": 6.0,
        "dist_ma10_pct": 4.2,
        "dist_ma20_pct": -0.3
      },
      {
        "code": "002463",
        "code_full": "002463.SZ",
        "name": "沪电股份",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 2224.5642,
        "pe": 15.9,
        "risks_count": 2,
        "rps20": 19.71,
        "rps60": 92.27,
        "rps120": 97.47,
        "rps250": 95.27,
        "ma10": 108.57,
        "vcp_quality": null,
        "ma5": 105.86,
        "ma20": 118.42,
        "dist_ma5_pct": 9.2,
        "dist_ma10_pct": 6.5,
        "dist_ma20_pct": -2.4
      },
      {
        "code": "002353",
        "code_full": "002353.SZ",
        "name": "杰瑞股份",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 1525.4428,
        "pe": 16.5,
        "risks_count": 1,
        "rps20": 30.33,
        "rps60": 88.75,
        "rps120": 97.34,
        "rps250": 98.94,
        "ma10": 138.1,
        "vcp_quality": null,
        "ma5": 136.4,
        "ma20": 136.94,
        "dist_ma5_pct": 9.2,
        "dist_ma10_pct": 7.9,
        "dist_ma20_pct": 8.8
      },
      {
        "code": "300502",
        "code_full": "300502.SZ",
        "name": "新易盛",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 5915.8311,
        "pe": 10.4,
        "risks_count": 1,
        "rps20": 20.94,
        "rps60": 95.35,
        "rps120": 97.03,
        "rps250": 98.78,
        "ma10": 432.59,
        "vcp_quality": null,
        "ma5": 406.7,
        "ma20": 482.81,
        "dist_ma5_pct": 4.3,
        "dist_ma10_pct": -1.9,
        "dist_ma20_pct": -12.1
      },
      {
        "code": "000938",
        "code_full": "000938.SZ",
        "name": "紫光股份",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 1056.5135,
        "pe": 26.7,
        "risks_count": 4,
        "rps20": 99.36,
        "rps60": 96.74,
        "rps120": 96.97,
        "rps250": 88.76,
        "ma10": 37.7,
        "vcp_quality": null,
        "ma5": 34.57,
        "ma20": 38.0,
        "dist_ma5_pct": 6.9,
        "dist_ma10_pct": -2.0,
        "dist_ma20_pct": -2.8
      },
      {
        "code": "600428",
        "code_full": "600428.SH",
        "name": "中远海特",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 321.8619,
        "pe": 24.3,
        "risks_count": 0,
        "rps20": 99.71,
        "rps60": 98.56,
        "rps120": 96.91,
        "rps250": 91.84,
        "ma10": 11.03,
        "vcp_quality": null,
        "ma5": 11.39,
        "ma20": 10.49,
        "dist_ma5_pct": 3.0,
        "dist_ma10_pct": 6.3,
        "dist_ma20_pct": 11.9
      },
      {
        "code": "002371",
        "code_full": "002371.SZ",
        "name": "北方华创",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 5328.0101,
        "pe": 16.4,
        "risks_count": 1,
        "rps20": 28.4,
        "rps60": 98.44,
        "rps120": 96.83,
        "rps250": 95.37,
        "ma10": 710.6,
        "vcp_quality": null,
        "ma5": 683.51,
        "ma20": 733.85,
        "dist_ma5_pct": 7.4,
        "dist_ma10_pct": 3.3,
        "dist_ma20_pct": 0.0
      },
      {
        "code": "002938",
        "code_full": "002938.SZ",
        "name": "鹏鼎控股",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 2111.9712,
        "pe": 7.8,
        "risks_count": 2,
        "rps20": 28.11,
        "rps60": 96.48,
        "rps120": 96.71,
        "rps250": 93.43,
        "ma10": 85.63,
        "vcp_quality": null,
        "ma5": 83.72,
        "ma20": 91.61,
        "dist_ma5_pct": 8.9,
        "dist_ma10_pct": 6.4,
        "dist_ma20_pct": -0.5
      },
      {
        "code": "688629",
        "code_full": "688629.SH",
        "name": "华丰科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 671.6649,
        "pe": 3.1,
        "risks_count": 1,
        "rps20": 19.48,
        "rps60": 91.82,
        "rps120": 96.56,
        "rps250": 97.24,
        "ma10": 140.17,
        "vcp_quality": null,
        "ma5": 133.47,
        "ma20": 158.36,
        "dist_ma5_pct": 7.5,
        "dist_ma10_pct": 2.3,
        "dist_ma20_pct": -9.4
      },
      {
        "code": "688017",
        "code_full": "688017.SH",
        "name": "绿的谐波",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 624.3124,
        "pe": 5.9,
        "risks_count": 3,
        "rps20": 15.16,
        "rps60": 98.26,
        "rps120": 95.98,
        "rps250": 96.35,
        "ma10": 303.49,
        "vcp_quality": null,
        "ma5": 308.63,
        "ma20": 334.04,
        "dist_ma5_pct": 10.3,
        "dist_ma10_pct": 12.2,
        "dist_ma20_pct": 1.9
      },
      {
        "code": "688256",
        "code_full": "688256.SH",
        "name": "寒武纪",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 7143.0628,
        "pe": 6.0,
        "risks_count": 1,
        "rps20": 20.51,
        "rps60": 88.32,
        "rps120": 95.76,
        "rps250": 97.69,
        "ma10": 1138.15,
        "vcp_quality": null,
        "ma5": 1078.31,
        "ma20": 1247.68,
        "dist_ma5_pct": 5.4,
        "dist_ma10_pct": -0.1,
        "dist_ma20_pct": -8.9
      },
      {
        "code": "603259",
        "code_full": "603259.SH",
        "name": "药明康德",
        "source_date": "2026/07/29",
        "highlights_count": 11,
        "market_cap": 4401.0418,
        "pe": 8.2,
        "risks_count": 0,
        "rps20": 84.12,
        "rps60": 97.21,
        "rps120": 95.65,
        "rps250": 89.61,
        "ma10": 129.79,
        "vcp_quality": null,
        "ma5": 134.25,
        "ma20": 127.28,
        "dist_ma5_pct": 9.9,
        "dist_ma10_pct": 13.6,
        "dist_ma20_pct": 15.9
      },
      {
        "code": "002245",
        "code_full": "002245.SZ",
        "name": "蔚蓝锂芯",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 286.7127,
        "pe": 18.1,
        "risks_count": 3,
        "rps20": 23.31,
        "rps60": 95.53,
        "rps120": 95.63,
        "rps250": 91.49,
        "ma10": 16.24,
        "vcp_quality": null,
        "ma5": 15.99,
        "ma20": 17.36,
        "dist_ma5_pct": 5.0,
        "dist_ma10_pct": 3.4,
        "dist_ma20_pct": -3.3
      },
      {
        "code": "002916",
        "code_full": "002916.SZ",
        "name": "深南电路",
        "source_date": "2026/07/29",
        "highlights_count": 9,
        "market_cap": 2378.4975,
        "pe": 8.6,
        "risks_count": 1,
        "rps20": 15.61,
        "rps60": 90.69,
        "rps120": 95.57,
        "rps250": 96.55,
        "ma10": 323.44,
        "vcp_quality": null,
        "ma5": 315.31,
        "ma20": 351.98,
        "dist_ma5_pct": 10.7,
        "dist_ma10_pct": 8.0,
        "dist_ma20_pct": -0.8
      },
      {
        "code": "600236",
        "code_full": "600236.SH",
        "name": "桂冠电力",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 877.3086,
        "pe": 26.3,
        "risks_count": 2,
        "rps20": 98.27,
        "rps60": 92.79,
        "rps120": 95.16,
        "rps250": 91.61,
        "ma10": 10.82,
        "vcp_score": 34,
        "vcp_contraction_ratio": 0.8,
        "vcp_last_depth": 20.0,
        "vcp_dist_peak_pct": 10.1,
        "vcp_nearest_ma": "MA10",
        "vcp_nearest_ma_dist": 2.8,
        "vcp_vol_declining": true,
        "vcp_num_contractions": 6,
        "vcp_depths": "25%→8%→12%→19%→26%→20%",
        "vcp_quality": "SETUP",
        "ma5": 10.96,
        "ma20": 10.61,
        "dist_ma5_pct": 1.6,
        "dist_ma10_pct": 2.8,
        "dist_ma20_pct": 4.9
      },
      {
        "code": "300661",
        "code_full": "300661.SZ",
        "name": "圣邦股份",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 713.0292,
        "pe": 9.1,
        "risks_count": 1,
        "rps20": 14.74,
        "rps60": 93.83,
        "rps120": 95.0,
        "rps250": 86.1,
        "ma10": 98.42,
        "vcp_quality": null,
        "ma5": 97.06,
        "ma20": 106.12,
        "dist_ma5_pct": 7.2,
        "dist_ma10_pct": 5.7,
        "dist_ma20_pct": -2.0
      },
      {
        "code": "000725",
        "code_full": "000725.SZ",
        "name": "京东方A",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 2211.5464,
        "pe": 25.5,
        "risks_count": 2,
        "rps20": 12.09,
        "rps60": 98.93,
        "rps120": 94.63,
        "rps250": 86.31,
        "ma10": 5.7,
        "vcp_quality": null,
        "ma5": 5.58,
        "ma20": 6.17,
        "dist_ma5_pct": 7.0,
        "dist_ma10_pct": 4.7,
        "dist_ma20_pct": -3.2
      },
      {
        "code": "603156",
        "code_full": "603156.SH",
        "name": "养元饮品",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 568.0071,
        "pe": 8.4,
        "risks_count": 1,
        "rps20": 29.67,
        "rps60": 91.54,
        "rps120": 94.3,
        "rps250": 93.35,
        "ma10": 39.24,
        "vcp_quality": null,
        "ma5": 41.71,
        "ma20": 39.94,
        "dist_ma5_pct": 8.1,
        "dist_ma10_pct": 14.9,
        "dist_ma20_pct": 12.8
      },
      {
        "code": "300001",
        "code_full": "300001.SZ",
        "name": "特锐德",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 378.0184,
        "pe": 16.7,
        "risks_count": 1,
        "rps20": 58.3,
        "rps60": 96.66,
        "rps120": 94.21,
        "rps250": 88.31,
        "ma10": 35.28,
        "vcp_quality": null,
        "ma5": 35.31,
        "ma20": 33.96,
        "dist_ma5_pct": 1.5,
        "dist_ma10_pct": 1.5,
        "dist_ma20_pct": 5.5
      },
      {
        "code": "688002",
        "code_full": "688002.SH",
        "name": "睿创微纳",
        "source_date": "2026/08/01",
        "highlights_count": 6,
        "market_cap": 714.4273,
        "pe": 7.0,
        "risks_count": 1,
        "rps20": 52.51,
        "rps60": 89.13,
        "rps120": 93.55,
        "rps250": 95.51,
        "ma10": 145.42,
        "vcp_quality": null,
        "ma5": 141.66,
        "ma20": 144.67,
        "dist_ma5_pct": 7.2,
        "dist_ma10_pct": 4.4,
        "dist_ma20_pct": 5.0
      },
      {
        "code": "000977",
        "code_full": "000977.SZ",
        "name": "浪潮信息",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 1133.664,
        "pe": 26.1,
        "risks_count": 1,
        "rps20": 95.86,
        "rps60": 93.93,
        "rps120": 93.49,
        "rps250": 86.37,
        "ma10": 77.7,
        "vcp_quality": null,
        "ma5": 72.78,
        "ma20": 81.72,
        "dist_ma5_pct": 6.1,
        "dist_ma10_pct": -0.6,
        "dist_ma20_pct": -5.5
      },
      {
        "code": "688008",
        "code_full": "688008.SH",
        "name": "澜起科技",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 2587.5406,
        "pe": 7.0,
        "risks_count": 1,
        "rps20": 18.49,
        "rps60": 93.73,
        "rps120": 93.31,
        "rps250": 96.76,
        "ma10": 210.53,
        "vcp_quality": null,
        "ma5": 201.37,
        "ma20": 224.04,
        "dist_ma5_pct": 5.3,
        "dist_ma10_pct": 0.7,
        "dist_ma20_pct": -5.4
      },
      {
        "code": "603162",
        "code_full": "603162.SH",
        "name": "海通发展",
        "source_date": "2026/07/30",
        "highlights_count": 6,
        "market_cap": 153.8395,
        "pe": 3.3,
        "risks_count": 1,
        "rps20": 97.67,
        "rps60": 89.41,
        "rps120": 91.95,
        "rps250": 93.49,
        "ma10": 10.92,
        "vcp_quality": null,
        "ma5": 10.81,
        "ma20": 10.64,
        "dist_ma5_pct": 3.5,
        "dist_ma10_pct": 2.5,
        "dist_ma20_pct": 5.1
      },
      {
        "code": "603127",
        "code_full": "603127.SH",
        "name": "昭衍新药",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 346.9482,
        "pe": 8.9,
        "risks_count": 3,
        "rps20": 95.94,
        "rps60": 96.22,
        "rps120": 91.56,
        "rps250": 90.51,
        "ma10": 44.62,
        "vcp_quality": null,
        "ma5": 42.66,
        "ma20": 45.71,
        "dist_ma5_pct": 8.5,
        "dist_ma10_pct": 3.8,
        "dist_ma20_pct": 1.3
      },
      {
        "code": "600885",
        "code_full": "600885.SH",
        "name": "宏发股份",
        "source_date": "2026/07/29",
        "highlights_count": 9,
        "market_cap": 561.7767,
        "pe": 13.7,
        "risks_count": 0,
        "rps20": 52.92,
        "rps60": 95.83,
        "rps120": 91.45,
        "rps250": 88.47,
        "ma10": 35.0,
        "vcp_quality": null,
        "ma5": 35.67,
        "ma20": 34.26,
        "dist_ma5_pct": 1.8,
        "dist_ma10_pct": 3.7,
        "dist_ma20_pct": 6.0
      },
      {
        "code": "002440",
        "code_full": "002440.SZ",
        "name": "闰土股份",
        "source_date": "2026/07/30",
        "highlights_count": 4,
        "market_cap": 146.682,
        "pe": 16.0,
        "risks_count": 2,
        "rps20": 98.78,
        "rps60": 97.33,
        "rps120": 91.31,
        "rps250": 90.96,
        "ma10": 12.91,
        "vcp_quality": null,
        "ma5": 13.23,
        "ma20": 11.91,
        "dist_ma5_pct": -1.3,
        "dist_ma10_pct": 1.1,
        "dist_ma20_pct": 9.6
      },
      {
        "code": "002138",
        "code_full": "002138.SZ",
        "name": "顺络电子",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 399.9339,
        "pe": 19.1,
        "risks_count": 2,
        "rps20": 7.19,
        "rps60": 97.69,
        "rps120": 91.06,
        "rps250": 89.35,
        "ma10": 43.88,
        "vcp_quality": null,
        "ma5": 44.65,
        "ma20": 45.51,
        "dist_ma5_pct": 11.1,
        "dist_ma10_pct": 13.0,
        "dist_ma20_pct": 9.0
      },
      {
        "code": "688652",
        "code_full": "688652.SH",
        "name": "京仪装备",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 234.36,
        "pe": 2.6,
        "risks_count": 0,
        "rps20": 10.98,
        "rps60": 94.82,
        "rps120": 90.32,
        "rps250": 96.59,
        "ma10": 136.59,
        "vcp_quality": null,
        "ma5": 127.0,
        "ma20": 157.97,
        "dist_ma5_pct": 9.8,
        "dist_ma10_pct": 2.1,
        "dist_ma20_pct": -11.7
      },
      {
        "code": "000739",
        "code_full": "000739.SZ",
        "name": "普洛药业",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 253.4675,
        "pe": 29.2,
        "risks_count": 1,
        "rps20": 98.15,
        "rps60": 95.69,
        "rps120": 89.33,
        "rps250": 85.51,
        "ma10": 20.52,
        "vcp_quality": null,
        "ma5": 20.87,
        "ma20": 20.04,
        "dist_ma5_pct": 4.8,
        "dist_ma10_pct": 6.6,
        "dist_ma20_pct": 9.2
      },
      {
        "code": "300503",
        "code_full": "300503.SZ",
        "name": "昊志机电",
        "source_date": "2026/08/05",
        "highlights_count": 5,
        "market_cap": 219.4266,
        "pe": 10.4,
        "risks_count": 3,
        "rps20": 11.82,
        "rps60": 87.21,
        "rps120": 88.98,
        "rps250": 97.63,
        "ma10": 64.88,
        "vcp_quality": null,
        "ma5": 64.8,
        "ma20": 72.12,
        "dist_ma5_pct": 9.9,
        "dist_ma10_pct": 9.7,
        "dist_ma20_pct": -1.3
      },
      {
        "code": "601168",
        "code_full": "601168.SH",
        "name": "西部矿业",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 977.5066,
        "pe": 19.0,
        "risks_count": 0,
        "rps20": 99.67,
        "rps60": 97.67,
        "rps120": 88.65,
        "rps250": 95.8,
        "ma10": 37.74,
        "vcp_quality": null,
        "ma5": 38.36,
        "ma20": 35.11,
        "dist_ma5_pct": 6.9,
        "dist_ma10_pct": 8.7,
        "dist_ma20_pct": 16.8
      },
      {
        "code": "688981",
        "code_full": "688981.SH",
        "name": "中芯国际",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 10739.8492,
        "pe": 6.0,
        "risks_count": 0,
        "rps20": 31.73,
        "rps60": 94.7,
        "rps120": 88.22,
        "rps250": 87.45,
        "ma10": 131.02,
        "vcp_quality": null,
        "ma5": 122.01,
        "ma20": 144.27,
        "dist_ma5_pct": 2.8,
        "dist_ma10_pct": -4.3,
        "dist_ma20_pct": -13.0
      },
      {
        "code": "300373",
        "code_full": "300373.SZ",
        "name": "扬杰科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 494.5008,
        "pe": 12.5,
        "risks_count": 1,
        "rps20": 6.12,
        "rps60": 96.05,
        "rps120": 87.46,
        "rps250": 91.37,
        "ma10": 87.3,
        "vcp_quality": null,
        "ma5": 84.73,
        "ma20": 97.57,
        "dist_ma5_pct": 7.4,
        "dist_ma10_pct": 4.2,
        "dist_ma20_pct": -6.7
      },
      {
        "code": "601233",
        "code_full": "601233.SH",
        "name": "桐昆股份",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 546.9324,
        "pe": 15.2,
        "risks_count": 2,
        "rps20": 52.02,
        "rps60": 85.73,
        "rps120": 86.8,
        "rps250": 93.51,
        "ma10": 22.07,
        "vcp_quality": null,
        "ma5": 22.41,
        "ma20": 21.44,
        "dist_ma5_pct": 2.6,
        "dist_ma10_pct": 4.2,
        "dist_ma20_pct": 7.2
      },
      {
        "code": "600160",
        "code_full": "600160.SH",
        "name": "巨化股份",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 1163.3206,
        "pe": 28.1,
        "risks_count": 1,
        "rps20": 21.19,
        "rps60": 95.61,
        "rps120": 85.5,
        "rps250": 88.39,
        "ma10": 40.17,
        "vcp_quality": null,
        "ma5": 40.69,
        "ma20": 40.77,
        "dist_ma5_pct": 5.9,
        "dist_ma10_pct": 7.3,
        "dist_ma20_pct": 5.7
      },
      {
        "code": "002056",
        "code_full": "002056.SZ",
        "name": "横店东磁",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 356.9006,
        "pe": 20.0,
        "risks_count": 2,
        "rps20": 11.2,
        "rps60": 95.49,
        "rps120": 85.38,
        "rps250": 85.22,
        "ma10": 21.06,
        "vcp_quality": null,
        "ma5": 20.74,
        "ma20": 22.81,
        "dist_ma5_pct": 5.8,
        "dist_ma10_pct": 4.2,
        "dist_ma20_pct": -3.8
      },
      {
        "code": "688777",
        "code_full": "688777.SH",
        "name": "中控技术",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 843.3289,
        "pe": 5.7,
        "risks_count": 2,
        "rps20": 21.58,
        "rps60": 95.14,
        "rps120": 85.15,
        "rps250": 93.29,
        "ma10": 88.25,
        "vcp_quality": null,
        "ma5": 94.64,
        "ma20": 92.39,
        "dist_ma5_pct": 12.6,
        "dist_ma10_pct": 20.8,
        "dist_ma20_pct": 15.4
      }
    ]
  },
  "enriched_candidates": [
    {
      "code": "300661.SZ",
      "fetch_time": "2026-08-06T11:52:57+0800",
      "name": "圣邦股份",
      "pe": 117.2383,
      "pb": 7.2722,
      "ps_ttm": 17.0281,
      "pcf_ttm": 169.618,
      "valuation_percentile": 33.48,
      "total_shares": 685473137,
      "industries": [
        {
          "name": "电子",
          "level": 1
        },
        {
          "name": "半导体",
          "level": 2
        },
        {
          "name": "模拟芯片设计",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "三新指数",
        "科技龙头指数",
        "双循环指数",
        "双创100指数",
        "出海贸易指数",
        "5G应用指数",
        "先进制造指数",
        "消费电子产业指数",
        "华为平台指数",
        "半导体产业指数",
        "专精特新小巨人主题指数",
        "数字经济指数",
        "信创产业指数"
      ],
      "score_company": 9.2,
      "score_trend": 7.6,
      "score_value": 7.6,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 模拟芯片设计 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 107% ，利润成长性强。"
        },
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 15% ，创造价值的能力很强。"
        },
        {
          "tag": "评级",
          "text": "近90天， 6家 机构给出评级，其中 67% 为“买入”，距目标价的上涨空间为 23% 。"
        },
        {
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 7.4% ，很受外资机构青睐；公募基金持股 13% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年07月01日 至今陷入调整，资金有出逃可能。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "16:24 7月29日，A股存储芯片概念板块部分个股上涨。截至收盘，上市第三天的长鑫科技涨幅达12.66%，成交额为448.14亿元。正帆科技、托伦斯涨幅超10%，红板科技、圣邦股份涨幅超6%。前海开源基金首席经济学家杨德龙表示，看好长鑫科技承接AI算力存储增量需求的能力。中关村物联网产业联盟副秘书长袁帅认为，存储赛道结构性机会或成为主线，具备自主制造能力和高端存储研发落地的龙头有望获得资金青睐。TrendForce数据显示，预计存储器产业产值2026年达5516亿美元，2027年达8427亿美元。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "12:01 港股午间收盘，恒生指数跌1.27%，恒生科技指数跌1.69%。恒指港股通ETF银华（159318）跌1.3%，港股通科技ETF鹏华（159751）跌1.47%。板块方面，电气设备、个人护理用品板块跌幅靠前。个股方面，现代牧业涨8.13%，智谱涨7.6%，中国再保险涨7.03%，大新金融涨6.95%，威华达控股涨6.8%；圣邦股份跌10.38%，旺山旺水-B跌9.55%，建滔积层板跌9.14%，海致科技集团跌8.9%，思格新能跌8.64%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "圣邦股份：H股公告（截至2026年6月30日止股份发行人的证券变动月报表）",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 2800608107.32,
      "revenue_yoy": 0.14552,
      "operating_profit": 338345201.64,
      "operating_profit_yoy": 0.018742,
      "net_profit": 332423931.2,
      "net_profit_yoy": 0.198787,
      "gross_profit": 1411941118.14,
      "gross_profit_yoy": 0.107058,
      "cogs": 1388666989.18,
      "gross_margin": 50.42,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 104.02,
      "price": 104.02,
      "ma5": 97.06,
      "ma10": 98.42,
      "ma20": 106.12,
      "dist_ma5_pct": 7.2,
      "dist_ma10_pct": 5.7,
      "dist_ma20_pct": -2.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.685,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 5.06,
        "pct_float": 0.81,
        "chg5_pct": -10.12,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "000725.SZ",
      "fetch_time": "2026-08-06T11:52:57+0800",
      "name": "京东方A",
      "pe": 36.8555,
      "pb": 1.6362,
      "ps_ttm": 1.0697,
      "pcf_ttm": 4.6285,
      "valuation_percentile": 61.23,
      "total_shares": 37044328064,
      "industries": [
        {
          "name": "电子",
          "level": 1
        },
        {
          "name": "光学光电子",
          "level": 2
        },
        {
          "name": "面板",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "三新指数",
        "科技龙头指数",
        "双循环指数",
        "出海贸易指数",
        "自主可控指数",
        "5G应用指数",
        "先进制造指数",
        "消费电子产业指数",
        "华为平台指数",
        "贷款回购指数",
        "QFII重仓指数",
        "成交额TOP20指数"
      ],
      "score_company": 8.4,
      "score_trend": 7.3,
      "score_value": 4.7,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 面板 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年07月09日，业绩超预期引发股价大幅上涨，当日收涨 6.82% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 117% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 13% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 12家 机构给出评级，其中 67% 为“买入”，距目标价的上涨空间为 30% 。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 6.5% ，很受外资机构青睐。"
        },
        {
          "tag": "回购",
          "text": "近6月，公司累计回购 11亿股 ，占总股本比例 2.9% ，金额合计 47亿元 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月13日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 33% ，收益质量较低。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "09:46 7月30日，A股三大指数集体低开，沪指跌0.43%，深成指跌0.93%，创业板指跌1.40%，科创50跌1.51%。盘面上，黄金、油气、有色金属、煤炭板块涨幅居前；电子、电力设备、计算机、机械设备、商贸零售板块跌幅居前。受隔夜美股半导体板块下挫影响，科技板块表现较弱。全市场上涨家数不足两成。隔夜美联储维持利率不变，美股三大股指显著下跌。国内方面，央行预告合计投放2.1万亿元隔夜逆回购，九部门联合印发科技金融数据开发利用通知。此外，中际旭创、京东方A、海亮股份、兆易创新等公司披露回购增持方案。\n今日A股三大指数集体低开，科创50与创业板指跌幅居前。受美股半导体板块重挫及美债收益率上升影响，电子、电力设备板块领跌。央行预告合计2.1万亿元逆回购护航流动性，多家龙头公司披露大额回购增持方案。机构认为短期市场或维持震荡再平衡，科技主线受外部扰动，低位板块轮动修复有望延续。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "23:23 国仪公司披露IPO发行安排，确定发行价为21.22元/股，预计募集资金8.49亿元，上市估值为84.88亿元。战略配售投资者包括华泰创新投资有限公司、公司高管与核心员工专项资管计划，以及深圳外滩科技开发有限公司、天津京东方创投、皖能资本及季丰电子。其中，深圳外滩为兆易创新全资子公司，双方将围绕设备选型、技术交流及芯片供应开展合作；京东方及天津京东方创投将与国仪公司在关键部品技术攻关及半导体显示领域展开合作。\n本次发行初始战略配售数量为800.2万股，占发行总量的20%，获配金额为1.7亿元。国仪公司专注于高端科学仪器研发，2025年主营业务收入6.63亿元，目前尚未盈利，预计最早于2026年转盈。公司将于7月31日开启网下申购，8月4日公布配售结果。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/28～2027/07/27 北京电子控股有限责任公司(控股股东，实际控制人)计划增持，变动价格说明：本次增持不设置固定价格，拟增持金额不超过 10.0亿元  ，拟增持金额不低于 5.00亿元",
          "tags": [
            "控股股东增持"
          ]
        },
        {
          "content": "2026/07/23解禁544.65万股，占总股本0.01%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-07-23"
        }
      ],
      "report_period": "20250930",
      "revenue": 154547999525,
      "revenue_yoy": 0.075255,
      "operating_profit": 5550695257,
      "operating_profit_yoy": 1.08087,
      "net_profit": 4404678299,
      "net_profit_yoy": 1.273634,
      "gross_profit": 22281107839,
      "gross_profit_yoy": 0.020915,
      "cogs": 132266891686,
      "gross_margin": 14.42,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 5.97,
      "price": 5.97,
      "ma5": 5.58,
      "ma10": 5.7,
      "ma20": 6.17,
      "dist_ma5_pct": 7.0,
      "dist_ma10_pct": 4.7,
      "dist_ma20_pct": -3.2,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.6921,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 117.64,
        "pct_float": 5.57,
        "chg5_pct": -0.44,
        "net5_repay_days": 4,
        "signal": "neutral"
      }
    },
    {
      "code": "603156.SH",
      "fetch_time": "2026-08-06T11:52:57+0800",
      "name": "养元饮品",
      "pe": 40.6677,
      "pb": 6.7015,
      "ps_ttm": 9.6083,
      "pcf_ttm": 32.1723,
      "valuation_percentile": 99.2,
      "total_shares": 1260277566,
      "industries": [
        {
          "name": "食品饮料",
          "level": 1
        },
        {
          "name": "饮料乳品",
          "level": 2
        },
        {
          "name": "软饮料",
          "level": 3
        }
      ],
      "concepts": [
        "长江存储指数"
      ],
      "score_company": 7.7,
      "score_trend": 8.6,
      "score_value": 3.3,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 软饮料 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年04月27日，业绩超预期引发股价大幅上涨，当日收涨 6.74% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 26% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 15% ，投入资本回报率为 18% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 113% ，净利润现金含量较高。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 110% ，销售收入现金含量较强。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 6.3% ，现金分红极高。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月01日大跌 -3.81% ，且成交额为近20日均值的 1.53倍 ，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/22发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-22"
        },
        {
          "content": "17:00 本周软饮料市场价格与产量变动情况如下：产业链相关材料价格追踪显示，PET现货价格周涨幅2.73%，月涨幅10.03%，2026年8月4日报7627.50元/吨；6种重点监测水果批发价周涨幅2.21%，月跌幅4.14%，8月5日报6.94元/公斤；玻璃周跌幅1.86%，月跌幅4.93%，8月5日报12.15元/平方米；包装纸（瓦楞纸）周跌幅0.87%，月涨幅2.10%，7月31日报3400.00元/吨；白糖周跌幅0.71%，月跌幅2.65%，8月5日报5150.00元/吨；包装纸（箱板纸）周涨幅0.00%，月涨幅1.27%，7月31日报5960.00元/吨；生鲜乳（原奶）周涨幅0.00%，月涨幅0.99%，7月31日报3.06元/公斤。受软饮料市场价格与产量变化影响的公司包括：安德利净利润0.73亿元，机构预测年度净利润3.51亿元，截至2026年3月31日，产品为果汁、香精，收入占比98.74%，库存量112500；维维股份净利润0.84亿元，机构预测年度净利润未披露，截至2026年3月31日，产品为饮料类，收入占比48.22%，库存量1656.23；泉阳泉净利润0.18亿元，机构预测年度净利润0.78亿元，截至2026年3月31日，产品为矿泉水，收入占比45.88%，库存量29600；香飘飘净利润0.93亿元，机构预测年度净利润2.15亿元，截至2026年3月31日，产品为冲泡类、即饮类，收入占比98.25%，库存量378400；承德露露净利润2.48亿元，机构预测年度净利润6.88亿元，截至2026年3月31日，产品为植物蛋白饮料，收入占比99.95%，库存量3400；养元饮品净利润8.08亿元，机构预测年度净利润14.26亿元，截至2026年3月31日，产品为饮料，收入占比未披露；欢乐家净利润0.37亿元，机构预测年度净利润0.45亿元，截至2026年3月31日，产品为饮料，收入占比63.84%，库存量922.7；东鹏饮料净利润28.67亿元，机构预测年度净利润58.90亿元，截至2026年6月30日，产品为东鹏特饮，收入占比95.02%；国投中鲁净利润0.06亿元，机构预测年度净利润未披露，截至2026年3月31日，产品为果汁、香料及果糖等，收入占比96.02%，库存量121600；李子园净利润0.53亿元，机构预测年度净利润2.02亿元，截至2026年3月31日，产品为含乳饮料，收入占比96.18%，库存量7278.78；均瑶健康净利润0.10亿元，机构预测年度净利润未披露，截至2026年3月31日，产品为饮品，收入占比91.44%。软饮料属于包材敏感型行业，包材成本占比远高于原材料，产品包装主要为PET瓶，在直接原材料成本中约占18%，纸箱、外帽、瓶盖使用量也较大。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "17:00 本周软饮料市场价格与产量变动如下：产业链相关材料价格追踪（按周涨跌幅排序）：PET现货周涨2.49%，月涨9.77%，2026年8月3日报价7610元/吨；玻璃周跌2.38%，月跌3.14%，2026年8月4日报价12.33元/平方米；白糖周跌1.28%，月跌2.86%，2026年8月4日报价5143.33元/吨；包装纸（瓦楞纸）周跌0.87%，月涨2.10%，2026年7月31日报价3400元/吨；6种重点监测水果批发周跌0.14%，月跌5.74%，2026年8月4日报价6.90元/公斤；包装纸（箱板纸）周涨0.00%，月涨1.27%，2026年7月31日报价5960元/吨；生鲜乳（原奶）周涨0.00%，月涨0.99%，2026年7月31日报价3.06元/公斤。受软饮料市场价格/产量变化影响的公司有：安德利（净利润0.73亿元，机构预测年度净利润3.51亿元，截止2026-03-31，果汁、香精占比98.74%，库存量112500）；维维股份（净利润0.84亿元，截止2026-03-31，饮料类占比48.22%，库存量1656.23）；泉阳泉（净利润0.18亿元，机构预测0.36亿元，截止2026-03-31，矿泉水占比45.88%，库存量29600）；香飘飘（净利润0.93亿元，机构预测2.03亿元，截止2026-03-31，冲泡类、即饮类占比98.25%，库存量378400）；承德露露（净利润2.48亿元，机构预测7.02亿元，截止2026-03-31，植物蛋白饮料占比99.95%，库存量3400）；养元饮品（净利润8.08亿元，机构预测14.18亿元，截止2026-03-31，饮料占比未披露）；欢乐家（净利润0.37亿元，机构预测0.45亿元，截止2026-03-31，饮料占比63.84%，库存量922.7）；东鹏饮料（净利润28.67亿元，机构预测55.44亿元，截止2026-06-30，东鹏特饮占比95.02%）；国投中鲁（净利润0.06亿元，截止2026-03-31，果汁、香料及果糖等占比96.02%，库存量121600）；李子园（净利润0.53亿元，机构预测1.93亿元，截止2026-03-31，含乳饮料占比96.18%，库存量7278.78）；均瑶健康（净利润0.10亿元，截止2026-03-31，饮品占比91.44%）。注：财务数据截止到各公司最新披露的财务报告日期。软饮料属于包材敏感型行业，包材成本占比远高于原材料，产品包装主要是PET瓶，在直接原材料成本中约占18%，此外纸箱、外帽、瓶盖使用量较大。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 3905326394.37,
      "revenue_yoy": -0.076436,
      "operating_profit": 1418722265.57,
      "operating_profit_yoy": -0.095856,
      "net_profit": 1119043029.7,
      "net_profit_yoy": -0.089482,
      "gross_profit": 1740516577.9,
      "gross_profit_yoy": -0.115416,
      "cogs": 2164809816.47,
      "gross_margin": 44.57,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 45.07,
      "price": 45.07,
      "ma5": 41.71,
      "ma10": 39.24,
      "ma20": 39.94,
      "dist_ma5_pct": 8.1,
      "dist_ma10_pct": 14.9,
      "dist_ma20_pct": 12.8,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.5113,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 4.79,
        "pct_float": 0.84,
        "chg5_pct": -0.22,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "300001.SZ",
      "fetch_time": "2026-08-06T11:52:57+0800",
      "name": "特锐德",
      "pe": 29.6616,
      "pb": 4.3968,
      "ps_ttm": 2.3323,
      "pcf_ttm": 17.7925,
      "valuation_percentile": 44.28,
      "total_shares": 1055327713,
      "industries": [
        {
          "name": "电力设备",
          "level": 1
        },
        {
          "name": "电网设备",
          "level": 2
        },
        {
          "name": "输变电设备",
          "level": 3
        }
      ],
      "concepts": [
        "QFII重仓指数",
        "新基建指数",
        "员工持股指数",
        "分拆上市指数",
        "RCEP指数",
        "一带一路指数",
        "新能源汽车指数",
        "数字能源指数",
        "轨道交通指数",
        "仪电仪表指数",
        "融资租赁指数",
        "智能电网指数",
        "高铁指数",
        "高低压设备精选指数",
        "电气自动化设备精选指数"
      ],
      "score_company": 8.5,
      "score_trend": 8.5,
      "score_value": 5.7,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月20日，业绩超预期引发股价跳空高开，当日收涨 8.31% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 35% ，利润成长性强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 8.5亿元 ，较上期增长 31% ，占2025年营收 5.4% ，在手订单充足。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 8.2% ，很受外资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 95% 的股票，走势较强。"
        },
        {
          "tag": "回购",
          "text": "近1月公司发布1条回购公告，拟回购不超过 6.0亿元 ，回购价格不超过 50元/股 。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月05日 至今陷入调整，资金有出逃可能。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/25发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-25"
        },
        {
          "content": "17:16 2026年8月1日，中国充电桩行业正式实施强制性产品认证（3C认证）。未获认证的电动汽车供电设备不得出厂、销售、进口或使用。此前，市场监管总局于2024年12月发布公告，给予一年半过渡期，2025年3月1日起受理认证申请。截至2026年6月底，全国充电基础设施总量达2305.7万个，同比增长43.2%，现存充电桩相关企业超51万家。市场监管总局2025年抽查显示，充电桩不合格率高达49.1%。3C认证的强制实施旨在提升行业质量门槛。\n3C认证覆盖交流供电设备和直流供电设备，家用私桩、公共商用桩均纳入管理。认证包括型式试验和工厂检查，安全指标从旧标准的42项提升至178项，依据《电动汽车供电设备安全要求》《电动汽车传导充电系统安全要求》两项强制性国家标准。认证遵循“管新不管旧”原则：8月1日前已投运的存量充电桩可继续使用，新出厂、销售、投运的产品必须持证。关键零部件实行备案制，不得随意更换规格及供应商。行业长期存在技术门槛低、标准不统一、以次充好等问题，2024年底抽查不合格率接近30%，僵尸桩问题突出。业内预计30%至50%的中小厂商将被淘汰，头部企业市场份额有望从45%提升至65%以上。部分小厂已无单可接，转向委外加工或第三方维护。\n认证费用方面，单款产品交流桩费用5万至10万元，直流桩10万至15万元；头部厂商单台分摊成本50至150元，小厂单台分摊成本200至500元。隐性投入包括产线改造、质量管理体系完善，单型号额外投入5万至10万元。2026年11月1日将执行能效标准《电动汽车供电设备能效限定值及能效等级》（GB46519-2025），三级能效（充电效率94.5%）以下设备禁止生产、进口和销售，存量设备需在2027年11月1日前升级。直流桩升级至一级能效（96.5%以上）需更换碳化硅模块并采用液冷散热，单台硬件成本增加800至1500元。终端价格预计家用7kW交流桩上涨5%至10%，商用120kW直流桩上涨10%至15%。\n头部企业已提前完成认证：特来电2025年5月获得首批3C认证；盛弘股份（300693）全系列产品完成认证，覆盖7kW至2500kW；香山股份（002870）旗下均悦充的7kW产品在受理后28天获证；星云股份（300648）完成多品类认证。3C认证要求备案零部件不得更换，大型供应商与厂商有望形成强绑定。特锐德（300001）旗下特来电以约23%市场份额居全国充电运营第一，截至2026年6月底运营公共充电终端约96万台，累计充电量突破700亿度，上半年充电量126亿度，同比增长约47%。盛弘股份2025年充电桩业务收入14.96亿元，占营收逾四成。道通科技（688208）2025年智能充电网络收入12.42亿元，超半数收入来自北美市场。上半年净利润增长的充电桩概念股还包括银河电子（002519）、京泉华（002885）、思源电气（002028）等，17只概念股市盈率低于40倍。\n3C认证将重塑竞争规则，从低价竞争转向技术、运营与服务。合规设备降低故障率、适配智能充电、车网互动等新业态。《新型能源体系建设“十五五”规划》提出2030年充电基础设施达4000万个，车网互动聚合可调充电规模5000万千瓦左右，车能融合预计创造超万亿级综合经济效益。行业正经历从“有桩可用”到“桩桩可信”的规范化历程。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "02:27 在7月30日举行的新闻发布会上，国家能源局表示，受新能源汽车、人工智能等高新技术产业带动，今年上半年充换电服务业、互联网数据服务业用电量增长强劲，同比分别增长56.9%和44%，合计拉高全社会用电量0.9个百分点。截至2026年6月底，我国电动汽车充电基础设施总数达到2305.7万个，同比增长43.2%。其中，公共充电设施500.9万个，同比增长22.3%，额定总功率2.47亿千瓦；私人充电设施1804.8万个，同比增长50.4%。在大功率充电设施方面，全国已建成大功率充电枪超过18万个。县域充电设施覆盖率提升至98.61%。根据《电动汽车充电设施服务能力“三年倍增”行动方案（2025—2027）》，到2027年底全国城市将新增160万个直流充电枪，其中包括10万个大功率充电枪。《新型能源体系建设“十五五”规划》提出，2030年充电基础设施达到4000万个，车网互动聚合可调充电规模将达到5000万千瓦左右，预计到2030年车能融合将创造万亿级综合经济效益。\n在充电桩概念股中，银河电子、ST长园、京泉华、特锐德、思源电气今年上半年净利润同比增长。其中，银河电子、ST长园预计扭亏为盈。特锐德预计上半年净利润为3.92亿元至4.58亿元，同比增长20%至40%；截至6月底，公司运营公共充电终端约96万台，上半年充电量约126亿度，同比增长约47%。截至7月30日，协鑫能科、特锐德、中恒电气等年内涨幅均超20%，其中协鑫能科年内累计上涨38.52%。此外，金杯电工、大洋电机、双杰电气、盛弘股份、许继电气、国电南自、众业达等个股滚动市盈率相对较低。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "回购总金额不超过6.00亿元，回购最高价不超过50.0元/股 （预案）",
          "tags": [
            "公司回购流通股"
          ]
        },
        {
          "content": "特锐德：关于公司及子公司预中标国网项目的提示性公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 9834300812.09,
      "revenue_yoy": 0.105253,
      "operating_profit": 825623808.61,
      "operating_profit_yoy": 0.776371,
      "net_profit": 689560541.66,
      "net_profit_yoy": 0.589903,
      "gross_profit": 2597118628.76,
      "gross_profit_yoy": 0.206299,
      "cogs": 7237182183.33,
      "gross_margin": 26.41,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 35.82,
      "price": 35.82,
      "ma5": 35.31,
      "ma10": 35.28,
      "ma20": 33.96,
      "dist_ma5_pct": 1.5,
      "dist_ma10_pct": 1.5,
      "dist_ma20_pct": 5.5,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.685,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 11.21,
        "pct_float": 3.04,
        "chg5_pct": 0.07,
        "net5_repay_days": 4,
        "signal": "neutral"
      }
    },
    {
      "code": "688002.SH",
      "fetch_time": "2026-08-06T11:52:57+0800",
      "name": "睿创微纳",
      "pe": 50.2411,
      "pb": 10.2651,
      "ps_ttm": 10.2958,
      "pcf_ttm": 28.6743,
      "valuation_percentile": 63.78,
      "total_shares": 470513245,
      "industries": [
        {
          "name": "国防军工",
          "level": 1
        },
        {
          "name": "军工电子Ⅱ",
          "level": 2
        },
        {
          "name": "军工电子Ⅲ",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "双创100指数",
        "贷款回购指数",
        "半导体产业指数",
        "5G指数",
        "RCEP指数",
        "股权激励指数",
        "芯片指数",
        "元宇宙指数",
        "AI应用指数",
        "预期提升指数",
        "可转债正股指数",
        "ASIC芯片指数",
        "半导体分立器件指数",
        "传感器指数"
      ],
      "score_company": 8.8,
      "score_trend": 9.1,
      "score_value": 5.0,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 军工电子Ⅲ 行业龙头企业。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 33% ，最新季度归母净利润同比增长 276% ，成长能力很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 13% ，投入资本回报率为 11% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 132% ，净利润现金含量很高。"
        },
        {
          "tag": "订单",
          "text": "合同负债 4.4亿元 ，较上期增长 33% ，占2025年营收 6.9% ，在手订单充足。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 10% ，很受外资机构青睐；公募基金持股 16% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月10日大跌 -9.32% ，且成交额为近20日均值的 2.36倍 ，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/18发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-18"
        },
        {
          "content": "睿创微纳：关于本次限制性股票归属登记完成后调整可转债转股价格暨转股停牌的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "2026/07/29解禁56.15万股，占总股本0.12%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-07-29"
        },
        {
          "content": "15:02 7月23日，通用航空板块表现活跃，通用航空指数盘中上涨1.155%。跟踪该指数的航空ETF富国(159392)盘中涨幅达1.356%，成交额256万元。成分股中，航天彩虹上涨3.09%，中无人机涨2.12%，睿创微纳涨1.77%，中直股份涨1.70%，万丰奥威涨1.59%。资金面上，航空ETF富国近期主力资金呈现流出态势，近5个交易日累计净流出263万元。该ETF综合费率为0.60%/年，近1年超基准年化收益为+1.13%。根据2026年2季度基金季报，该ETF前十大权重股合计占比31.65%，其中万丰奥威、中无人机、航天彩虹位列前三。持仓变动方面，南网科技、芯动联科、睿创微纳、宗申动力新进前十大重仓股。截至7月17日，通用航空指数市盈率为88.34倍。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "02:11 随着公募基金二季报披露，贝莱德、富达、路博迈、安联、联博等外商独资公募基金的持仓情况披露。外资机构在二季度保持较高权益仓位，重点布局光模块、半导体、AI算力硬件等细分领域。贝莱德中国新视野混合二季度末重仓中际旭创、华润微、新易盛和东山精密；联博智选混合重仓中际旭创、寒武纪、澜起科技、芯原股份和睿创微纳；安联中国精选混合重仓华虹宏力、中芯国际、卓易信息和北方华创。路博迈中国机遇混合基金经理魏晓雪表示，基金持仓结构均衡偏成长，布局能源革命、高端制造、AI基础设施及半导体等领域。富达传承6个月持有期股票基金经理周文群和张笑牧表示，二季度增加了半导体板块配置。\n展望后市，贝莱德先进制造一年持有混合基金经理单秀丽和陈之渊表示，A股大、中盘股票具备估值扩张潜力，看好AI科技浪潮及产业链自主发展。联博智远混合基金经理朱良认为，AI资本开支将持续为存储、服务器等硬件赛道贡献盈利增长。安联中国精选混合基金经理程彧认为，当前A股相对于人民币债券吸引力突出，将维持股票超配，未来将重点配置优质科技资产，并根据市场变化配置红利资产及盈利预期超标的。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 4085976026.2,
      "revenue_yoy": 0.297199,
      "operating_profit": 733534421.56,
      "operating_profit_yoy": 0.796213,
      "net_profit": 619035839.84,
      "net_profit_yoy": 0.604014,
      "gross_profit": 2123668757.56,
      "gross_profit_yoy": 0.318704,
      "cogs": 1962307268.64,
      "gross_margin": 51.97,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 151.84,
      "price": 151.84,
      "ma5": 141.66,
      "ma10": 145.42,
      "ma20": 144.67,
      "dist_ma5_pct": 7.2,
      "dist_ma10_pct": 4.4,
      "dist_ma20_pct": 5.0,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.6829,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 14.2,
        "pct_float": 1.99,
        "chg5_pct": -0.93,
        "net5_repay_days": 3,
        "signal": "neutral"
      }
    },
    {
      "code": "000977.SZ",
      "fetch_time": "2026-08-06T11:52:57+0800",
      "name": "浪潮信息",
      "pe": 43.6503,
      "pb": 5.0139,
      "ps_ttm": 0.7271,
      "pcf_ttm": null,
      "valuation_percentile": 77.31,
      "total_shares": 1468476655,
      "industries": [
        {
          "name": "计算机",
          "level": 1
        },
        {
          "name": "计算机设备",
          "level": 2
        },
        {
          "name": "其他计算机设备",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "三新指数",
        "科技龙头指数",
        "人工智能+指数",
        "5G应用指数",
        "贷款回购指数",
        "国企改革指数",
        "新基建指数",
        "信创产业指数",
        "AI备案指数",
        "元宇宙指数",
        "AI应用指数",
        "设备更新指数",
        "AI算力指数"
      ],
      "score_company": 8.7,
      "score_trend": 7.2,
      "score_value": 4.1,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 其他计算机设备 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年07月08日，业绩超预期引发股价跳空高开，但目前股价缺口已回补。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 122% ，销售收入现金含量很强。"
        },
        {
          "tag": "评级",
          "text": "近90天， 11家 机构给出评级，其中 82% 为“买入”，距目标价的上涨空间为 24% 。"
        },
        {
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 2.5% ，较受外资机构青睐；公募基金持股 4.6% ，较受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 93% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "毛利",
          "text": "毛利率为 5.7% ，行业处于衰退期，或企业缺乏竞争力。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "13:34 截至8月5日13点15分，上证指数涨1.38%，深证成指涨1.98%，创业板指涨1.60%。云计算ETF易方达（516510）涨3.04%，成分股泛微网络（603039）、星网锐捷（002396）、紫光股份（000938）涨停，宏景科技（301396）涨超10%，云天励飞-U（688343）、深信服（300454）、万兴科技（300624）、浪潮信息（000977）、国投智能（300188）、鼎捷数智（300378）涨超5%。消息面上，美国大数据与人工智能软件公司Palantir Technologies公布的第二季度业绩大幅超出预期，其营收同比增长近一倍，其中商业收入增长一倍有余。这一强劲业绩验证了AI技术商业化应用的巨大潜力与市场空间，显著提振了全球市场对AI应用端企业盈利前景的信心，带动A股人工智能应用板块集体走强。中信证券表示，当下“AI吞噬软件”叙事正在逐步证伪：Salesforce、ServiceNow、Workday等龙头厂商收入与在手订单仍保持稳健增长，应用软件基本面尚未出现市场此前担忧的结构性失速；同时模型厂商通过嵌入CRM、ERP、ITSM和HCM等既有工作流推进企业级落地，传统软件厂商的数据、行业知识及客户服务能力仍构成核心壁垒。短期看，模型同质化属性提升、软件企业AI收入占比提升等有望推动美股软件板块估值持续向上修复。中期维度，板块能否由估值修复走向反转，仍取决于AI产品能否带动软件企业整体营收增速回升，未来1-2个季度可能是重要观察窗口。长城证券认为，随着算力需求的持续火热，各家科技巨头大幅提升资本开支的同时，AI背后的各类成本都在上涨，各个环节都面临需求驱动的产能瓶颈。持续看好PCB、液冷、光纤光缆等算力相关产业链，以及AI驱动云计算市场结构性变革下AI+云、AI+应用环节的投资机会。\n云计算ETF易方达（516510）跟踪中证云计算与大数据主题指数，产品覆盖云计算基础设施、光通信、数据中心运营和AI应用等产业链环节，成分股中包含多家在AI算力基础设施建设中具有核心竞争力的企业，前五大权重股包括科大讯飞（002230）、新易盛（300502）、润泽科技（300442）、中际旭创（300308）、浪潮信息（000977）。投资者可关注该产品在全球AI算力投资版图扩大背景下的中长期配置价值。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "10:39 今日上午，国产算力产业链整体走强，紫光股份（000938）、锐捷网络（301165）、菲菱科思（301191）、浪潮信息（000977）、裕太微等个股盘中大涨。其中，因7月持续走强被网友称为“紫色的光”的紫光股份，盘中一度涨停。紫光股份预计2026年上半年归母净利润19.1亿元至23.2亿元，同比增长83.50%至122.89%；扣非净利润16.1亿元至20.2亿元，同比增长44.02%至80.69%。据公开信息，银河证券表示，当前国产大模型Kimi K3已实现与多家国产算力平台的Day 0极速适配，拉动国产超节点需求，进而推动服务器、交换机、光模块、液冷、电源等国产算力产业链环节配套需求，建议关注国产超节点及产业链相关公司。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:30股价达到 83.8 元，创历史新高",
          "tags": [
            "股价新高"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 120669018861.99,
      "revenue_yoy": 0.448467,
      "operating_profit": 1518710819.6,
      "operating_profit_yoy": 0.182766,
      "net_profit": 1488864885.87,
      "net_profit_yoy": 0.173292,
      "gross_profit": 5919386979.21,
      "gross_profit_yoy": 0.054504,
      "cogs": 114749631882.78,
      "gross_margin": 4.91,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 77.2,
      "price": 77.2,
      "ma5": 72.78,
      "ma10": 77.7,
      "ma20": 81.72,
      "dist_ma5_pct": 6.1,
      "dist_ma10_pct": -0.6,
      "dist_ma20_pct": -5.5,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.6921,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 40.7,
        "pct_float": 3.59,
        "chg5_pct": -2.19,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688008.SH",
      "fetch_time": "2026-08-06T11:52:57+0800",
      "name": "澜起科技",
      "pe": 98.9543,
      "pb": 12.5578,
      "ps_ttm": 44.4416,
      "pcf_ttm": 102.8638,
      "valuation_percentile": 80.91,
      "total_shares": 1220538021,
      "industries": [
        {
          "name": "电子",
          "level": 1
        },
        {
          "name": "半导体",
          "level": 2
        },
        {
          "name": "数字芯片设计",
          "level": 3
        }
      ],
      "concepts": [
        "A50指数",
        "TMT指数",
        "三新指数",
        "科技龙头指数",
        "双循环指数",
        "双创100指数",
        "出海贸易指数",
        "人工智能+指数",
        "自主可控指数",
        "5G应用指数",
        "先进制造指数",
        "消费电子产业指数",
        "半导体产业指数",
        "成交额TOP20指数",
        "5G指数"
      ],
      "score_company": 9.4,
      "score_trend": 7.5,
      "score_value": 4.2,
      "highlights": [
        {
          "tag": "A/H",
          "text": "A/H溢价率仅为 -10% ，从流动性而言，A股吸引力较高。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 82% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 12% ，投入资本回报率为 11% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.2% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 5家 机构给出评级，其中 60% 为“买入”，距目标价的上涨空间为 82% 。"
        },
        {
          "tag": "预测",
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 13% ，很受外资机构青睐；公募基金持股 15% ，很受内资机构青睐。"
        },
        {
          "tag": "回购",
          "text": "近1月，公司累计回购 237万股 ，占总股本比例 0.19% ，金额合计 3.6亿元 。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年07月02日 至今陷入调整，资金有出逃可能。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "17:00 存储元器件价格上涨会对主营业务为存储芯片的上市公司产生正向业绩影响，反之亦然，此外，需同时关注成本端晶圆价格变动和各企业的产销情况。\n本周，电子存储市场价格变动情况如下：\n存储器价格追踪一览表（按周涨跌幅幅度排序）\n品种周涨跌幅（%）月涨跌幅（%）日期价格/数量单位\nFlash（SLC 2Gb）2.617.14202607274.20美元\nFlash（MLC 64Gb）1.0713.232026072732.91美元\neMMC/128G0.000.002026080431.00美元\nUFS/128GB0.000.002026080433.00美元\nDDR4/16Gb0.000.002026080450.00美元\nSSD/256GB（SATA3）0.000.002026080471.00美元\n价格指数一定程度上反映了该行业当前的景气指数。\n本周存储价格指数追踪异动情况如下：\n存储价格指数追踪一览表（按周涨跌幅幅度排序）\n品种周涨跌幅（%）月涨跌幅（%）日期价格/数量单位\nDRAM指数1.082.64202608044105.19--\nNAND指数-0.040.02202608042987.73--\n需要关注上游材料价格变化对相关公司的成本影响，上游晶圆价格涨幅过大时，下游终端厂商的成本压力将陡然增加。\n本周上游晶圆价格异动情况如下：\n上游晶圆价格一览表（按周涨跌幅幅度排序）\n品种周涨跌幅（%）月涨跌幅（%）日期价格/数量单位\nWafer（256Gb）3.095.962026072710.79美元\nWafer（128Gb）3.015.64202607276.85美元\nWafer（512Gb）1.69-4.082026072719.25美元\n受电子存储市场价格变化影响的公司一览表\n股票名净利润（亿元）机构预测年度净利润（亿元）截止日期产品名称产品收入占比（%）产品毛利率（%）\n兆易创新14.7362.722026-03-31存储芯片64.0539.71\n北京君正3.208.892026-03-31存储芯片68.1530.40\n紫光国微3.3318.512026-03-31集成电路94.1361.97\n上海贝岭0.22--2026-03-31集成电路产品70.3440.58\n普冉股份3.7310.742026-03-31集成电路10036.23\n国科微0.533.262026-03-31固态存储系列芯片产品55.1112.98\n澜起科技8.3031.232026-03-31集成电路产品10048.08\n德明利33.4688.832026-03-31储存产品99.7521.23\n东芯股份1.535.502026-03-31集成电路99.9342.09\n（注：财务数据截止到该公司最新披露的财务报告日期）\n存储产业链\n存储芯片是半导体产业的重要分支，约占全球半导体市场的四分之一至三分之一。行业上游主要为硅片、光刻胶、CMP抛光液等原材料以及光刻机、PVD、CVD、刻蚀等设备；中游为存储芯片制造及封装，常见的存储芯片包括DRAM、NAND闪存芯片和NOR闪存芯片等；下游为消费电子和汽车电子等应用领域。成本构成来看，设计环节占成本30%，制造环节占成本40%，封测环节占成本30%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "13:32 截至8月5日13点26分，上证指数涨1.57%，深证成指涨2.58%，创业板指涨2.71%。电子化学品、国家大基金持股、中芯国际概念等板块涨幅居前。科创创业人工智能ETF易方达（159140）涨3.32%，成分股北京君正、星环科技、奥普特、云天励飞、聚辰股份、星宸科技、寒武纪、合合信息、深信服、澜起科技涨超5%。美国Palantir Technologies公布的第二季度业绩大幅超出预期，其营收同比增长近一倍，其中商业收入增长一倍有余。这一强劲表现验证了AI技术商业化应用的巨大潜力，显著提振了全球市场对AI应用端企业盈利前景的信心，带动A股人工智能应用板块集体走强。国盛证券表示，此前头部视频模型以闭源为主，H3有望推动视频模型开源社区发展。开源模型中的阿里万相、腾讯混元视频等与Seedance、可灵等闭源模型存在差距，视频生成领域生态开放性明显落后于大语言模型领域。大语言模型在DeepSeek、Kimi、通义千问及MiniMax等开源模型带动下，已形成“模型开放—社区共建—快速迭代”的正循环。H3开源后，行业层面有利于降低AI使用门槛，推动视频模型开源社区发展并加速国产芯片适配；公司层面，模型开源能以生态优势和开发者规模助力H3迭代、能力快速提升。中信证券表示，2023年以来AI高速发展驱动光模块技术更新迭代，光芯片速率升级、硅光集成与CPO架构等新技术共同驱动光模块测试设备迭代升级，叠加AI算力基础设施快速扩张，驱动光模块测试设备“量价齐升”。目前国际厂商仍在1.6T高端市场相对领先，但国内企业加速追赶，差距不断缩小，看好国产光模块行业长期发展以及高端光模块测试设备国产替代趋势。\n科创创业人工智能ETF易方达（159140）跟踪中证科创创业人工智能指数，该指数聚焦双创板块人工智能相关标的，同时配置海外及国内算力，且海外算力敞口较高，前五大权重股包括新易盛、澜起科技、中际旭创、寒武纪、芯原股份。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "澜起科技：H股公告-翌日披露报表",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 4057688490.81,
      "revenue_yoy": 0.578333,
      "operating_profit": 1693766552.21,
      "operating_profit_yoy": 0.625811,
      "net_profit": 1576364498.29,
      "net_profit_yoy": 0.614501,
      "gross_profit": 2493802875.41,
      "gross_profit_yoy": 0.669139,
      "cogs": 1563885615.4,
      "gross_margin": 61.46,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 212.0,
      "price": 212.0,
      "ma5": 201.37,
      "ma10": 210.53,
      "ma20": 224.04,
      "dist_ma5_pct": 5.3,
      "dist_ma10_pct": 0.7,
      "dist_ma20_pct": -5.4,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.6829,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 150.82,
        "pct_float": 6.21,
        "chg5_pct": 2.5,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "603162.SH",
      "fetch_time": "2026-08-06T11:52:57+0800",
      "name": "海通发展",
      "pe": 17.5818,
      "pb": 3.2558,
      "ps_ttm": 2.593,
      "pcf_ttm": 9.657,
      "valuation_percentile": 44.08,
      "total_shares": 1374794890,
      "industries": [
        {
          "name": "交通运输",
          "level": 1
        },
        {
          "name": "航运港口",
          "level": 2
        },
        {
          "name": "航运",
          "level": 3
        }
      ],
      "concepts": [
        "股权激励指数",
        "预期提升指数",
        "万得预增指数",
        "航运精选指数",
        "港口精选指数",
        "两岸融合指数"
      ],
      "score_company": 8.2,
      "score_trend": 8.5,
      "score_value": 6.8,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 1528% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 23% ，投入资本回报率为 19% ，盈利能力很强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 1.8亿元 ，较上期增长 157% ，占2025年营收 3.9% ，在手订单充足。"
        },
        {
          "tag": "评级",
          "text": "近90天， 6家 机构给出评级，其中 83% 为“买入”，距目标价的上涨空间为 12% 。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 7.7% ，很受外资机构青睐；公募基金持股 12% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 93% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "解禁",
          "text": "2026年09月29日，解禁 9.33亿股 ，占总股本 68% ，若股东减持，股价或受影响。"
        }
      ],
      "events": [
        {
          "content": "2026/09/29解禁9.33亿股，占总股本67.86%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-29"
        },
        {
          "content": "16:36 华源证券发布交通运输行业周报（2026年7月27日-2026年8月2日）。航运方面，受胡塞武装威胁，沙特油轮绕航好望角，导致航距拉长，预计合规VLCC运力需求增加约100艘，推动运价上行；阿联酋Adnoc为增强出口韧性，溢价购入6艘二手VLCC。本周油轮运价上涨，BDTI指数环比上涨7.34%至2595点，VLCC运价环比上涨11.5%；BCTI指数环比上涨8.1%至1424点。航空方面，自2026年8月5日起，国内航线燃油附加费将迎来三连降，800公里（含）以下航线收取40元，800公里以上收取70元，较调整前分别下降10元和30元。\n航空暑运需求回升，截至7月31日，8月首周周末机票预订量环比增长62%，19-22岁群体预订量同比增长20%，需求向县域支线下沉。C919高原型首架机于7月29日完成首飞，标志着该机型走向系列化。公路铁路方面，截至7月31日，10年/30年国债收益率降至1.71%/2.19%，公铁港板块股息率优势凸显。7月20日至26日，国家铁路运输货物7744.7万吨，环比增长3.77%；全国高速公路货车通行5408万辆，环比增长0.08%。7月1日至31日，全国铁路累计发送旅客4.32亿人次。\n快递行业方面，电商需求坚韧，“反内卷”带动价格上涨，建议关注圆通速递、中通快递、顺丰控股、极兔速递、申通快递。航空方面，建议关注南方航空、华夏航空、中国东航、海航控股、中国国航、中国民航信息网络。航运方面，看好油运市场景气度提升，建议关注招商轮船、中远海能、招商南油；看好散运市场复苏，建议关注招商轮船、海通发展、海航科技、国航远洋；看好亚洲内集运需求，建议关注海丰国际、中谷物流、锦江航运；关注航运红利资产，如中远海特、中国船舶租赁、中远海控、东方海外国际。船舶方面，建议关注中国船舶、中船防务、中国动力、松发股份。\n供应链物流方面，建议关注深圳国际及化工物流龙头密尔克卫、兴通股份。港口方面，建议关注招商港口、唐山港、青岛港、北部湾港。行业",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "海通发展：福建海通发展股份有限公司关于2026年7月对外担保进展的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "海通发展：福建海通发展股份有限公司关于举办2026年半年度业绩说明会的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "01:58 截至7月30日，A股交通运输板块已有40多家上市公司披露上半年业绩预告，其中23家公司预喜，物流、航运港口相关公司分别有11家和8家。上半年交运细分赛道景气度呈现分化格局：快递板块稳步上行，航运港口高位稳健运行，高速公路平稳偏弱，航空缓慢磨底修复。专家指出，未来应抓住产业链重构机遇，推动交通物流由规模扩张转向高质量发展。快递行业方面，随着“反内卷”政策落地，无序价格战得到遏制，终端快递单价修复，单票利润改善。据中国物流与采购联合会数据，上半年我国快递业务量累计完成1003.8亿件，业务收入7714.1亿元，同比分别增长5%和7.3%。圆通速递预计上半年归母净利润31亿元至34亿元，同比增长69.34%至85.73%，主要得益于全链路运营效率提升及成本降低。申通快递预计上半年净利润9.5亿元至10.6亿元，同比增长109.59%至133.85%，受益于价格理性回升及经营策略调整。韵达股份预计上半年净利润9.05亿元至10.50亿元，同比增长71.15%至98.57%，6月快递服务单票收入同比增长10.47%。\n人工智能与数字技术成为快递企业提质增效的抓手，申通快递发布了智能体平台“SClaw”并明确物理AI战略方向。圆通速递展示了数字孪生、机器视觉、智能体、AI助手、数字员工及AI编程等六大AI全栈落地成果，通过统一智能中台与全网数据标准，推动AI技术适配快递垂直场景。航运方面，全球贸易供需维持紧平衡，航运周期红利释放，海通发展、招商轮船、中远海能等企业通过优化运力与航线布局实现业绩增长。海通发展上半年营收34.71亿元，同比增长92.78%；归母净利润5.23亿元，同比增长502.60%。招商轮船预计上半年归母净利润66亿元至73亿元，同比增长214%至248%，盈利规模已超2025年全年水平。中远海能预计上半年净利润约45亿元，同比增长约141%。不过，上海国际航运研究中心航运发展研究所所长周德全指出，受新一轮船舶运力增长、供应链扰动淡化及地缘政治影响，航运市场仍面临较大不确定性。\n专家认为，产业链综合化、绿色化、规模化集中是交运行业长期主线，其中远洋航运、外贸港口及头部快递企业增长确定性较高。航运市场正经历从“效率导向”向“韧性导向”的切换，供应链风险预警成为市场关注重点。政策层面，物流保通保畅、快递“反内卷”、绿色航运及多式联运等政策推动了行业生态重塑。未来政策红利预计集中在三大方向：一是全国统一大市场下的跨区域物流协同政策；二是绿色船舶、新能源货运车辆购置补贴与配套基建政策；三是针对跨境物流、国际航运的外贸配套扶持政策。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 3009119957.58,
      "revenue_yoy": 0.163191,
      "operating_profit": 262987994.63,
      "operating_profit_yoy": -0.356143,
      "net_profit": 252592481.32,
      "net_profit_yoy": -0.384661,
      "gross_profit": 416817316.64,
      "gross_profit_yoy": -0.106148,
      "cogs": 2592302640.94,
      "gross_margin": 13.85,
      "pe_forward": null,
      "valuation_history_days": 326,
      "valuation_history_from": "20250331",
      "current_price": 11.19,
      "price": 11.19,
      "ma5": 10.81,
      "ma10": 10.92,
      "ma20": 10.64,
      "dist_ma5_pct": 3.5,
      "dist_ma10_pct": 2.5,
      "dist_ma20_pct": 5.1,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.5113,
        "sizing": "selective"
      }
    },
    {
      "code": "603127.SH",
      "fetch_time": "2026-08-06T11:52:59+0800",
      "name": "昭衍新药",
      "pe": 70.0935,
      "pb": 4.0983,
      "ps_ttm": 20.5771,
      "pcf_ttm": 68.4414,
      "valuation_percentile": 48.02,
      "total_shares": 749348220,
      "industries": [
        {
          "name": "医药生物",
          "level": 1
        },
        {
          "name": "医疗服务",
          "level": 2
        },
        {
          "name": "医疗研发外包",
          "level": 3
        }
      ],
      "concepts": [
        "股权激励指数",
        "宁组合",
        "万得预增指数",
        "创新药指数",
        "反内卷指数",
        "医疗服务精选指数",
        "CRO指数",
        "触板指数"
      ],
      "score_company": 8.2,
      "score_trend": 8.6,
      "score_value": 5.9,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月15日，业绩超预期引发股价跳空高开，但目前股价缺口已回补。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 2483% ，利润成长性强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 124% ，净利润现金含量很高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 2.9% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 10亿元 ，较上期增长 22% ，占2025年营收 63% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 3.3% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月17日大跌 -9.99% ，股价跌停，抛压很重。"
        },
        {
          "tag": "毛利",
          "text": "近5年，毛利率从 49% 下滑至 19% ，企业缺乏竞争力。"
        },
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 -31% ，收益质量很低。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "13:30 截至8月5日13点23分，上证指数涨1.57%，深证成指涨2.40%，创业板指涨2.30%。电子化学品、国家大基金持股、中芯国际概念等板块涨幅居前。医疗ETF易方达（159847）涨1.00%，成分股迪安诊断、昭衍新药涨超5%，热景生物、九安医疗、华大智造、药明康德、奕瑞科技、凯莱英、华大基因、卫宁健康等上涨。消息方面，药明康德发布公告全面上调2026年业绩指引，全年收入从513亿元～530亿元上调至585亿元～605亿元，持续经营收入增速从18%～22%大幅上调至35%～39%。该消息作为行业龙头业绩的重大利好，提振了市场对生物医药板块，特别是CXO及创新药产业链的整体信心。渤海证券表示，7月，医药生物板块前期强势反弹，后期有所回调，持续看好行业底部修复机遇，从26Q2基金持仓情况来看，医药生物板块仓位仍较低，具备较大修复空间。展望8月，进入半年报业绩期，建议关注业绩催化板块，长期看好国产创新药发展趋势，行业景气度向上，出海持续演绎，后续学术会议陆续召开，临床数据有望读出，带来密集催化，建议关注创新药、CXO及生命科学上游产业链等的投资机遇，同时关注新兴技术如脑机接口、AI应用、手术机器人等，以及中药等高股息板块的防御性机会。医疗ETF易方达（159847）跟踪中证医疗指数，该指数从沪深市场中选取业务涉及医疗器械、医疗服务、医疗信息化等医疗主题的上市公司证券作为样本，前五大权重股包括药明康德、迈瑞医疗、联影医疗、爱尔眼科、康龙化成。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "19:14 8月4日收盘，A股创新药概念股集体走强，其中CXO（医药外包）板块成为领涨主力。药明康德（603259）封住涨停，报141.35元，总市值达4218亿元。凯莱英（002821）、百花医药（600721）、罗欣药业（002793）等多股涨停，博腾股份（300363）涨超13%，康龙化成（300759）涨超10%，泰格医药（300347）、美迪西、昭衍新药（603127）等跟涨。港股同步上涨，药明康德H股收涨11.6%，康龙化成涨8%，凯莱英涨6.6%，药明生物涨4.5%。行情的直接催化来自8月3日晚药明康德发布的中期业绩公告：上半年归母净利润110.8亿元，同比增长29.43%，首次在半年报中突破百亿元；公司同时大幅上调全年收入指引。但市场关注的已不只是板块上涨本身，而是经历近三年调整后的CXO，是否正在迎来基本面与估值的重新定价。2021年前后，CXO曾是医药行业最受资本市场关注的赛道之一。彼时，在全球创新药研发投入增长以及国内创新药产业快速发展的背景下，CXO企业迎来高速扩张。但随后，全球生物医药融资环境变化、行业估值回归以及海外政策不确定性等因素影响，CXO板块进入调整期。据申万宏源研究数据，申万医疗研发外包指数市盈率（TTM）从2021年6月最高的约124倍，下降至2024年4月最低的约15倍。以药明康德为例，公司A股总市值一度从近5000亿元的历史高点大幅回落，阶段内市值较高点蒸发超3000亿元。如今，随着企业业绩改善和市场预期变化，CXO板块重新受到关注。药明康德的中报，则为这轮重估提供了数据验证。这份财报释放的信号可以概括为“四个首次”：第一，上半年归母净利润110.8亿元，同比增长29.43%，首次在半年报中突破百亿；第二，第二季度单季营收164.62亿元，同比增长47.71%，创下单季度历史新高，增速较第一季度的28.8%明显加速；第三，全年收入指引上调约14%，持续经营业务收入增速预期从18%至22%大幅上调至35%至39%；第四，截至6月末在手订单664.3亿元，同比增长25.2%，创历史新高，已超过全年新指引收入中值。\n对CXO企业而言，订单储备比单季度利润更能反映行业景气变化。药明康德之外，康龙化成近期业绩预告显示，上半年新签订单同比增长超过30%；美迪西则预计实现扭亏为盈。多家CXO企业中报或业绩预告出现改善迹象。对于本轮CXO行情的性质，市场专家看法不尽相同。南开大学金融发展研究院教授田利辉认为，这一轮回暖是估值修复与产业趋势变化的共同作用，但估值修复因素仍占主导，此前市场因《生物安全法案》等不确定性给予了板块极端风险折价，随着相关担忧缓解，叠加药明康德中报超预期，市场开始重新定价。远东资信研究院研究员苗琳杉则认为，本轮行情并非单纯的超跌反弹，而是估值修复与基本面实质性改善的“共振”，且基本面改善的权重正在加大。2022至2024年间，CXO板块调整的核心压制因素包括新冠大订单高基数消化、美国生物安全法案地缘政治扰动以及创新药投融资寒冬导致的订单预期下修。随着这些因素边际缓和，叠加龙头公司业绩全面超预期，板块重估获得了基本面支撑。市场关注的另一个问题是，此轮CXO行情是否会复制2021年的上涨周期。田利辉认为，CXO行业竞争逻辑正在发生变化。他指出，上一轮行情更多受益于创新药投资快速增长带来的规模扩张，而当前市场关注点正从过去的规模扩张，转向企业的技术能力、客户粘性以及全球供应链能力。在他看来，市场关注重心正在发生转移：从关注产能规模转向关注技术深度，从关注订单金额转向关注客户粘性，从关注成本优势转向关注全球化运营能力。具备解决复杂工艺难题、能够深度嵌入全球供应链的企业，才更有可能在竞争中获取优势。远东资信研究副总监简奖平的分析进一步揭示了两轮周期的本质差异。从驱动因子来看，2020至2021年的高景气由新冠疫情催化的疫苗与特效药研发需求推动，药明康德、凯莱英等企业承接了跨国药企的新冠口服药大订单，带来阶段性业绩峰值。而本轮复苏的驱动力已发生根本变化：国内端，医保控费与集采常态化倒逼传统药企向创新药转型，研发外包需求结构性增加，国内创新药生态正从“Fast-follow”向“Best-in-class”升级；国际端，跨国药企正面临“专利悬崖”，无论自研还是通过BD交易引进管线，均需要CXO提供从药物发现到商业化生产的全链条服务。\n从竞争方式来看，上一轮是产能竞赛——谁能在最短时间内扩产、承接大订单。本轮则围绕更复杂的分子类型和全球化监管能力展开。以药明康德为例，其多肽和寡核苷酸业务（TIDES）上半年收入72.6亿元，同比增长44.3%，TIDES D&M服务客户数同比提升39%，服务分子数同比提升68%。公司同时将TIDES全年收入增长指引由30%至40%上调至约45%。这类分子对工艺开发、生产放大、质量控制的要求远高于传统小分子，CXO企业必须具备复杂分子的研究与制造能力。从行业格局来看，分化特征明显。药明康德、凯莱英等头部企业订单大幅增长，而部分扩产较快的中小企业仍面临产能利用率不足和价格竞争。行业回暖并非普惠，中小企业仍面临订单和产能压力。中信建投证券研报指出，受益于海外投融资回暖，2026年国内CRO/CDMO行业新签订单及业绩有望加速增长。不过，市场机构也认为，行业景气变化仍需进一步观察。从估值来看，药明康德当前市盈率约19.5倍（TTM），仍低于申万医药行业约32倍的平均水平。当前市场对CXO的重新定价，更多建立在业绩改善预期基础上。\n不过，行业回暖并不意味着所有问题已经解决。首先，增长持续性仍需观察。远东资信研究副总监简奖平提示，2025年药明康德归母净利润已达191.5亿元，同比增长102.65%，2026年下半年面临同比基数抬高的压力。药明康德净利润突破百亿元后，市场关注未来增长空间。在高基数背景下，订单质量、盈利能力以及商业化项目占比变化，将成为判断行业后续发展的重要指标。其次，行业集中趋势能否进一步延续仍需验证。经历此前扩张周期后，部分企业面临产能消化压力。龙头企业订单恢复，并不意味着整个行业已经全面回暖。需要观察的是，龙头份额提升究竟来自技术壁垒驱动的结构性集中，还是周期性的订单回流。第三，海外政策因素仍是CXO企业需要关注的重要变量。2024年初，美国BIOSECURE法案相关讨论曾引发市场担忧，成为压制CXO估值的重要因素。随着相关政策讨论持续推进，市场关注重点逐渐从政策本身，转向其对客户选择和供应链布局的实际影响。不过，部分跨国药企的合规部门可能因声誉考量调整合作策略，这一变化对CXO企业的影响仍需长期观察。田利辉表示，判断行业景气能否持续，需要观察三个层面的指标。需求端看全球生物医药投融资数据，目前已出现触底回升的积极信号。供给端看订单的客户结构与行业产能出清程度，行业分化正在加剧，中小型同质化企业是否真正触底仍需观察。此外，全球供应链多元化布局是否会实质影响中国CXO企业的市场份额，也需要持续关注。值得注意的是，积极信号正在显现。据国家药监局披露数据，2026年上半年我国创新药对外授权交易总额约1100亿美元，已达2025年全年总额的80%，反映中国创新药资产全球认可度提升，有望转化为CXO生产订单。多家机构近期上调对药明康德的盈利预测和目标价，认为公司订单恢复以及业绩改善成为重要支撑。但也有机构提示，医药板块后续表现仍取决于业绩兑现情况。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 984961529.76,
      "revenue_yoy": -0.262287,
      "operating_profit": 99452028.34,
      "operating_profit_yoy": 2.427657,
      "net_profit": 80706047.32,
      "net_profit_yoy": 2.087038,
      "gross_profit": 212280141.46,
      "gross_profit_yoy": -0.421429,
      "cogs": 772681388.3,
      "gross_margin": 21.55,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 46.3,
      "price": 46.3,
      "ma5": 42.66,
      "ma10": 44.62,
      "ma20": 45.71,
      "dist_ma5_pct": 8.5,
      "dist_ma10_pct": 3.8,
      "dist_ma20_pct": 1.3,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.5113,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 5.81,
        "pct_float": 2.0,
        "chg5_pct": -6.18,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "600885.SH",
      "fetch_time": "2026-08-06T11:52:59+0800",
      "name": "宏发股份",
      "pe": 27.7874,
      "pb": 4.0997,
      "ps_ttm": 2.725,
      "pcf_ttm": 24.1007,
      "valuation_percentile": 39.61,
      "total_shares": 1547594313,
      "industries": [
        {
          "name": "电力设备",
          "level": 1
        },
        {
          "name": "电网设备",
          "level": 2
        },
        {
          "name": "电网自动化设备",
          "level": 3
        }
      ],
      "concepts": [
        "三新指数",
        "5G应用指数",
        "QFII重仓指数",
        "RCEP指数",
        "碳中和指数",
        "预期提升指数",
        "新能源汽车指数",
        "养老金指数",
        "特斯拉指数",
        "数字能源指数",
        "借壳上市指数",
        "宁德时代产业链指数",
        "智能交通指数",
        "电动物流车指数",
        "特高压指数",
        "共享汽车指数",
        "智能电网指数"
      ],
      "score_company": 9.4,
      "score_trend": 9.6,
      "score_value": 6.5,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 电网自动化设备 行业龙头企业。"
        },
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 17% ，收入成长性较强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 16% ，投入资本回报率为 16% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 132% ，净利润现金含量很高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.2% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 11家 机构给出评级，其中 73% 为“买入”，距目标价的上涨空间为 18% 。"
        },
        {
          "tag": "预测",
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 20% ，很受外资机构青睐；公募基金持股 8.6% ，很受内资机构青睐；2026年03月31日至2026年06月30日期间，股东户数减少 39% ，大资金买入。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 96% 的股票，走势较强。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "08:04 随着半年报陆续披露，各类机构二季度持股动向逐渐曝光。据证券时报·数据宝统计，截至8月5日公开的数据，QFII持股二季度末持有44股，合计持有2.64亿股，期末持股市值173.62亿元。从单只个股持股市值来看，有17股期末持股市值超过1亿元，宁德时代、宏发股份2只个股获持股超20亿元。从新进角度看，有23股为QFII新进持有，合计持股134亿元，除宁德时代外，还包括多只热门科技股，其中包括年内第一大牛股中船特气，以及富满微、乐鑫科技等热门半导体个股。从业绩看，QFII新进股中，盛达资源、富满微、昊志机电、亚翔集成上半年归母净利润同比增长均超2倍。（人民财讯）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "10:46 2026年8月3日，中银证券发布电力设备与新能源行业研究报告，指出电池新技术正加速落地，光伏行业“反内卷”进程持续推进。\n报告观点如下：新能源汽车方面，预计2026年全球销量保持增长，带动电池及材料需求，固态电池与钠离子电池产业化进程值得关注。光伏方面，投资主线为“反内卷”与“太空光伏”，卫星互联网建设利好太空光伏产业链。电池片环节格局优化，高功率组件需求推动市场化出清，建议关注电池组件、钙钛矿及胶膜等辅材。风电方面，受欧洲能源独立需求驱动，海风市场前景向好。储能方面，建议关注储能电芯及大储集成厂。氢能方面，绿氢耦合煤化工及绿色甲醇处于导入期，建议关注氢能设备及绿色燃料运营。本周板块行情方面，电力设备和新能源板块整体上涨1.60%，其中风电、核电、新能源汽车、锂电池、发电设备及光伏板块均有不同程度上涨，工控自动化板块下跌。行业重点信息方面，新能源汽车领域，多家车企公布7月销量数据，小米发布“澎程”系列增程SUV；电池领域，韩国成立“K-钠联盟”，国轩控股集团启动年产2万吨固态电池关键材料项目；光伏领域，中国光伏行业协会发布《光伏行业成本核算模型通则》，监管部门在江苏盐城开展价格合规指导，推动行业从“拼价格”向“拼质量”转型。\n公司重点信息方面：宏发股份2026年上半年归母净利润11.56亿元，同比增长19.89%；诺德股份上半年归母净利润1.03亿元，实现扭亏为盈；东方精工上半年归母净利润38.46亿元，同比增长867.75%；寒锐钴业上半年营业收入39.07亿元，同比增长23.32%，归母净利润同比下降22.50%。容百科技拟投资47.23亿元建设年产30万吨钠电正极材料一体化项目，分三期建设，预计投资收益率19.75%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "宏发股份：宏发股份：关于2026年半年度业绩说明会预告公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "2026/03/31～2026/06/30股东户数减少 39%",
          "tags": [
            "股东户数减少"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 12914117640.41,
      "revenue_yoy": 0.188161,
      "operating_profit": 2258796551.18,
      "operating_profit_yoy": 0.17755,
      "net_profit": 1946818535.47,
      "net_profit_yoy": 0.161325,
      "gross_profit": 4472307806.27,
      "gross_profit_yoy": 0.173649,
      "cogs": 8441809834.14,
      "gross_margin": 34.63,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 36.3,
      "price": 36.3,
      "ma5": 35.67,
      "ma10": 35.0,
      "ma20": 34.26,
      "dist_ma5_pct": 1.8,
      "dist_ma10_pct": 3.7,
      "dist_ma20_pct": 6.0,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.5113,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 4.17,
        "pct_float": 0.74,
        "chg5_pct": -12.71,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002440.SZ",
      "fetch_time": "2026-08-06T11:52:59+0800",
      "name": "闰土股份",
      "pe": 18.284,
      "pb": 1.4868,
      "ps_ttm": 2.4004,
      "pcf_ttm": 21.3791,
      "valuation_percentile": 73.38,
      "total_shares": 1123999905,
      "industries": [
        {
          "name": "基础化工",
          "level": 1
        },
        {
          "name": "化学制品",
          "level": 2
        },
        {
          "name": "纺织化学制品",
          "level": 3
        }
      ],
      "concepts": [
        "添加剂指数",
        "氟化工指数",
        "染料指数",
        "印染指数"
      ],
      "score_company": 8.0,
      "score_trend": 8.7,
      "score_value": 4.2,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月14日，业绩超预期引发股价大幅上涨，当日收涨 8.08% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 299% ，利润成长性强。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 2.8% ，现金分红极高。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 3.5% ，较受外资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "收益",
          "text": "近12月，扣非净利润占净利润 58% ，收益质量较低。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比为 58% ，销售收入现金含量很低。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/28发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-28"
        },
        {
          "content": "15:00 今天大涨的原因可能是分散染料行业开启新一轮涨价周期，闰土股份作为主要分散染料生产商有望受益于产品价格提升。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "10:34 申万宏源研报指出，染料产业链库存处于低位，预计8月后开启补库，需求端短期拉动效应显著。染料行业供需格局虽仍显宽松，但压力测试下置信度提升，格局有望长期向好。具备核心中间体配套及规模品牌优势的企业有望受益。需求端方面，染料跟随纺服订单增长，下游对价格不敏感，涨价对产销量影响有限。供给端方面，行业集中度较高，分散染料主要由浙江龙盛、闰土股份、吉华集团主导，活性染料前五家产能占比约76%。核心中间体如还原物、间苯二胺等供给格局优异，由头部企业把控，随着头部企业协同性建立，中间体价格上行推动染料价格底部回升。\n研报认为，在纺服产业链需求承压背景下，还原物价格维持在10万元/吨，显示出头部企业涨价的协同性。中远期看，还原物新批产能受限，行业有望持续演绎价在量先的逻辑，支撑染料价格中枢上行。风险提示包括原材料价格波动、下游需求不及预期及中间体竞争加剧。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "闰土股份：关于聘任公司董事会秘书的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 4163303974.91,
      "revenue_yoy": 0.022502,
      "operating_profit": 326804261.74,
      "operating_profit_yoy": 0.11783,
      "net_profit": 229745372.33,
      "net_profit_yoy": 0.400887,
      "gross_profit": 790379522.1,
      "gross_profit_yoy": 0.178738,
      "cogs": 3372924452.81,
      "gross_margin": 18.98,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 13.05,
      "price": 13.05,
      "ma5": 13.23,
      "ma10": 12.91,
      "ma20": 11.91,
      "dist_ma5_pct": -1.3,
      "dist_ma10_pct": 1.1,
      "dist_ma20_pct": 9.6,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6005,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 2.89,
        "pct_float": 2.34,
        "chg5_pct": -12.7,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002138.SZ",
      "fetch_time": "2026-08-06T11:52:59+0800",
      "name": "顺络电子",
      "pe": 39.5681,
      "pb": 5.9202,
      "ps_ttm": 5.2667,
      "pcf_ttm": 25.4331,
      "valuation_percentile": 71.75,
      "total_shares": 806318354,
      "industries": [
        {
          "name": "电子",
          "level": 1
        },
        {
          "name": "元件",
          "level": 2
        },
        {
          "name": "被动元件",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "消费电子产业指数",
        "华为平台指数",
        "贷款回购指数",
        "新基建指数",
        "珠三角指数",
        "5G指数",
        "员工持股指数",
        "元宇宙指数",
        "AI手机指数",
        "养老金指数",
        "元宇宙主题指数",
        "基站指数",
        "小米产业链指数",
        "智能手表指数",
        "元件精选指数"
      ],
      "score_company": 8.4,
      "score_trend": 6.0,
      "score_value": 4.5,
      "highlights": [
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 19% ，收入成长性较强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 13% ，投入资本回报率为 11% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.5% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 6.9% ，很受外资机构青睐；公募基金持股 5.5% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月30日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "偿债",
          "text": "现金短债比为 0.25 ，货币资金对短期债务的保障较弱。"
        }
      ],
      "events": [
        {
          "content": "17:01 顺络电子公告，公司近日收到最高人民法院送达的《民事上诉状》，原告株式会社村田制作所不服上海知识产权法院此前作出的两案一审判决(均驳回其诉讼请求)，已向最高院提起上诉。一审判决认定公司不存在专利侵权行为，二审尚未开庭，对公司本期利润或期后利润的影响具有不确定性。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "13:32 截至8月5日13点16分，上证指数涨1.45%，深证成指涨2.11%，创业板指涨1.79%。电子化学品、国家大基金持股、中芯国际概念等板块涨幅居前。ETF方面，消费电子ETF易方达（562950）涨5.03%，成分股环旭电子（601231）、福晶科技（002222）、工业富联（601138）涨停，生益科技（600183）、北京君正（300223）、兆易创新（603986）、三环集团（300408）、信维通信（300136）、瑞芯微（603893）、顺络电子（002138）涨超5%。消息方面，进入8月，消费电子市场迎来新品发布季，以苹果新一代产品为核心驱动，整个“果链”上下游加快了“招兵买马”的节奏，为产能爬坡做足准备。据媒体报道，富士康等龙头代工厂在工程师岗位上也在不断扩充，资本市场与供应链上下游正密切关注苹果首款折叠屏手机的进展。平安证券表示，晶圆代工行业规模持续增长，大陆占比提升：受益于消费电子、汽车电子、人工智能技术等高科技需求的快速增长，全球半导体产业高速发展，全球晶圆代工市场规模从2021年的1002亿美元增至2025年的1747亿美元，复合年增长率为14.9%。预计到2030年，全球市场将达到2955亿美元，2026年至2030年年复合增长率为10.7%。中国大陆晶圆代工市场销售额从2021年的94亿美元增至2025年的172亿美元，复合年增长率为16.3%。中国大陆在全球的市场占比从2021年的9.4%提升至2025年的9.8%。预计未来随着供应链国产化的进一步加速，中国大陆晶圆代工市场将继续扩大，2026年至2030年的年复合增长率将增至15.1%，到2030年达到347亿美元，预计在全球的市场占比提升至11.8%。\n消费电子ETF易方达（562950）跟踪消费电子指数（931494），被市场定位为“全球算力硬件上游”指数产品。该指数覆盖了PCB、MLCC、光互联等算力硬件的核心领域，成分股中包含了多家在光通信硬件产业链中具有重要地位的企业，前五大权重股包括立讯精密（002475）、寒武纪、工业富联、中芯国际、兆易创新。投资者可关注该产品在光通信景气周期和AI算力硬件升级背景下的配置价值。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "公司发布2026半年报报告，股价开盘上涨 7.23% ，股价收盘涨幅 6.73%",
          "tags": [
            "股价上涨"
          ]
        },
        {
          "content": "顺络电子：半年度非经营性资金占用及其他关联资金往来情况汇总表",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 5032025812.67,
      "revenue_yoy": 0.199482,
      "operating_profit": 991233575.19,
      "operating_profit_yoy": 0.19198,
      "net_profit": 873315516.03,
      "net_profit_yoy": 0.241406,
      "gross_profit": 1848764304.79,
      "gross_profit_yoy": 0.181167,
      "cogs": 3183261507.88,
      "gross_margin": 36.74,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 49.6,
      "price": 49.6,
      "ma5": 44.65,
      "ma10": 43.88,
      "ma20": 45.51,
      "dist_ma5_pct": 11.1,
      "dist_ma10_pct": 13.0,
      "dist_ma20_pct": 9.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6005,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 14.29,
        "pct_float": 3.76,
        "chg5_pct": 7.0,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "688652.SH",
      "fetch_time": "2026-08-06T11:52:59+0800",
      "name": "京仪装备",
      "pe": 148.9189,
      "pb": 10.6007,
      "ps_ttm": 15.9398,
      "pcf_ttm": 44.734,
      "valuation_percentile": 92.96,
      "total_shares": 168000000,
      "industries": [
        {
          "name": "电子",
          "level": 1
        },
        {
          "name": "半导体",
          "level": 2
        },
        {
          "name": "半导体设备",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "专精特新小巨人主题指数",
        "半导体精选指数",
        "专精特新小巨人指数",
        "半导体设备指数"
      ],
      "score_company": 7.4,
      "score_trend": 7.2,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 29% ，收入成长性很强。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 148% ，销售收入现金含量较强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 6.7% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 15亿元 ，较上期增长 10% ，占2025年营收 104% ，在手订单充足。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 7.0% ，很受内资机构青睐。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "2026/11/30解禁4725.00万股，占总股本28.13%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-11-30"
        },
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "15:00 今天大涨的原因可能是《集成电路布图设计保护条例》修订显示政策对半导体知识产权保护升级，利好半导体产业整体发展，京仪装备作为半导体专用设备供应商有望受益，从而提振股价。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1103054838.06,
      "revenue_yoy": 0.428136,
      "operating_profit": 135953960.72,
      "operating_profit_yoy": -0.051938,
      "net_profit": 128510042.02,
      "net_profit_yoy": -0.009879,
      "gross_profit": 366984633.45,
      "gross_profit_yoy": 0.477792,
      "cogs": 736070204.61,
      "gross_margin": 33.27,
      "pe_forward": null,
      "valuation_history_days": 164,
      "valuation_history_from": "20251201",
      "current_price": 139.5,
      "price": 139.5,
      "ma5": 127.0,
      "ma10": 136.59,
      "ma20": 157.97,
      "dist_ma5_pct": 9.8,
      "dist_ma10_pct": 2.1,
      "dist_ma20_pct": -11.7,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.6829,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 2.09,
        "pct_float": 1.24,
        "chg5_pct": 8.14,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "000739.SZ",
      "fetch_time": "2026-08-06T11:52:59+0800",
      "name": "普洛药业",
      "pe": 28.2607,
      "pb": 4.0019,
      "ps_ttm": 2.6507,
      "pcf_ttm": 18.5157,
      "valuation_percentile": 64.45,
      "total_shares": 1158443576,
      "industries": [
        {
          "name": "医药生物",
          "level": 1
        },
        {
          "name": "化学制药",
          "level": 2
        },
        {
          "name": "原料药",
          "level": 3
        }
      ],
      "concepts": [
        "贷款回购指数",
        "RCEP指数",
        "股票回购指数",
        "肺炎主题指数",
        "医保指数",
        "化学制药精选指数",
        "抗癌指数",
        "医疗物资出口指数",
        "流感指数",
        "抗艾滋病指数",
        "抗生素指数",
        "达菲指数",
        "抗核辐射指数"
      ],
      "score_company": 8.7,
      "score_trend": 9.5,
      "score_value": 5.2,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 原料药 行业龙头企业。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 16% ，投入资本回报率为 15% ，盈利能力很强。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 2.0% ，现金分红较高。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 2.7% ，较受外资机构青睐；公募基金持股 6.1% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 97% 的股票，收盘价接近 一年新高 ，走势很强。"
        },
        {
          "tag": "增持",
          "text": "近3月，控股股东累计实际增持 606万股 ，占总股本比例 0.52% ，金额合计 1.0亿元 。"
        },
        {
          "tag": "回购",
          "text": "近2月，公司累计回购 346万股 ，占总股本比例 0.30% ，金额合计 6150万元 。"
        }
      ],
      "risks": [
        {
          "tag": "收现",
          "text": "近5年，收现比为 76% ，销售收入现金含量较低。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/20发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-20"
        },
        {
          "content": "普洛药业：关于获得化学原料药上市申请批准通知书的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "17:38 普洛药业公告，全资子公司浙江普洛家园药业有限公司近日收到国家药品监督管理局签发的氟泽雷塞原料药《化学原料药上市申请批准通知书》，规格为20kg/桶、40kg/桶。氟泽雷塞片是KRAS G12C抑制剂，用于治疗至少接受过一种系统性治疗的KRAS G12C突变型晚期非小细胞肺癌成人患者，该片剂已于2024年8月在中国大陆获批上市，并于2025年底纳入国家医保药品目录。公司称本次获批将对未来经营带来一定积极影响。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "16:25 药明康德发布超预期半年报后，8月4日股价直奔涨停，封单一度超10万手，总市值逼近4300亿元。其他医药股受到提振，凯莱英、普洛药业、罗欣药业、双成药业等直线拉升涨停，康龙化成、药石科技等跟涨。截至当日收盘，医药板块整体涨幅超过2%，CRO方向领涨，义翘神州20%涨停，药明康德、罗欣药业、珍宝岛、哈三联、双成药业、百花医药、凯莱英、普洛药业10%涨停，康龙化成、药石科技、博腾股份、药康生物、成都先导、百普赛斯等涨超10%。药明康德半年报显示，上半年实现营收288.97亿元，同比增长38.93%；归母净利润110.8亿元，同比增长29.43%。其中第二季度营收164.62亿元，同比增长47.71%，环比增长32.37%；归母净利润64.29亿元，同比增长31.49%，环比增长38.21%。截至2026年6月末，持续经营业务在手订单664.3亿元，同比增长25.2%。公司全面上调2026年全年业绩指引，预计整体收入由513亿—530亿元上调至585亿—605亿元，持续经营业务收入同比增速由18%—22%上调至35%—39%。药明康德是全球领先的一体化、端到端CXO龙头，通过CRDMO和CTDMO模式赋能新药研发项目。财报发布后，兴业证券上调盈利预测，预计2026—2028年营业收入分别为605.65亿元、730.90亿元、871.07亿元，归母净利润分别为226.48亿元、278.93亿元、338.58亿元，对应EPS分别为7.59元、9.35元、11.35元，维持“买入”评级。\n华泰证券表示，考虑到药明康德的CRO/CDMO业务业绩超预期，上调该公司2026—2028年归母净利润至222亿元、263亿元、308亿元（分别较前值+32%、+31%、+31%）。基于SOTP估值，给予公司A/H估值分别为6168亿元/7031亿港元，对应目标价为206.72元/235.64港元（前值138.84元/164.27港元）。今年1月—6月，我国创新药对外授权交易总额约1100亿美元，达2025年全年总额的八成，再创历史新高。招商证券认为，医药板块已从前期超跌修复，过渡至基本面与产业趋势驱动的行情，且市场风格和资金轮动的影响逐步削弱，随着中报季及创新药管线催化预期到来，持续看好医药板块后市，重点关注业绩兑现、订单增长、管线数据与出海验证等创新主线。兴业证券也表示，“创新+国际化”仍为2026年医药核心主线。创新药方面，中国创新药全球竞争力持续加强，政策支持、BD出海及商业化盈利兑现的产业逻辑不变。海外大药企面临专利悬崖及管线补充需求，中国企业研发效率和成本优势突出，Co-Co模式逐步增多，反映中国创新药企业合作话语权持续提升。当前，医药板块正由“估值驱动”向“业绩+全球化兑现驱动”转变，已达成BD的产品逐步进入海外关键临床、注册上市及商业化分成兑现阶段，2026年ESMO年会重要数据、重磅BD及新技术突破仍将构成催化。重点关注具备差异化创新能力、全球BIC潜质及商业化放量能力的企业，同时关注创新转型顺利、销售能力较强的综合药企。8月进入医药板块中报密集披露期，结合此前的宏观环境变动，中泰证券建议关注创新药企业经营兑现情况，一方面，部分具备成熟且合规的商业化能力、商业化管线创新程度高的创新药企业，在监管趋严的背景下抗扰动能力将得到阶段性凸显；另一方面，此前中国创新资产积累了诸多BD交易，首付款、里程碑等收入的确认既可以使表观业绩有明显改善，亦代表BD的顺利推进。\n中泰证券称，近年来，中国创新药企业在ADC、双抗、自免等领域持续突破，部分资产已进入全球关键临床阶段，诸多MNC在引进中国创新药资产后，会随着相关临床开发支持工作的完善、自身商业结构的变化，不断明确对中国创新药的后续研发定位，关注已BD品种的后续Ⅲ期临床开发进度及和MNC内部管线的联用机会，以及具备稀缺性和MNC管线契合度的尚未BD品种后续临床数据积累、海外临床研究申报进度。下半年进入国际肿瘤学会议密集期，ESMO、WCLC等重要会议有望成为创新药板块核心催化窗口，当下普通标题已陆续发布，摘要中的初步临床结果、LBA标题即将发布。中泰证券建议关注：ADC、二代IO针对NSCLC等大癌种的大样本临床研究结果；ADC领域围绕新靶点、新毒素及新型偶联技术有突破潜力的创新资产；契合MNC应对“专利悬崖”策略的ADC+二代IO在早期临床研究中的POC数据；兼具成药确定性和良好竞争格局的pan-RAS等。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:31股价达到 21.54 元，创近24个月新高",
          "tags": [
            "股价新高"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 7763882133.27,
      "revenue_yoy": -0.164295,
      "operating_profit": 842655816.16,
      "operating_profit_yoy": -0.176388,
      "net_profit": 700189009.91,
      "net_profit_yoy": -0.194619,
      "gross_profit": 1942694031.28,
      "gross_profit_yoy": -0.136973,
      "cogs": 5821188101.99,
      "gross_margin": 25.02,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 21.88,
      "price": 21.88,
      "ma5": 20.87,
      "ma10": 20.52,
      "ma20": 20.04,
      "dist_ma5_pct": 4.8,
      "dist_ma10_pct": 6.6,
      "dist_ma20_pct": 9.2,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.6921,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 1.9,
        "pct_float": 0.75,
        "chg5_pct": 8.89,
        "net5_repay_days": 4,
        "signal": "adding"
      }
    },
    {
      "code": "300503.SZ",
      "fetch_time": "2026-08-06T11:52:59+0800",
      "name": "昊志机电",
      "pe": 76.8719,
      "pb": 13.9662,
      "ps_ttm": 10.7663,
      "pcf_ttm": 144.2942,
      "valuation_percentile": 85.9,
      "total_shares": 308226785,
      "industries": [
        {
          "name": "机械设备",
          "level": 1
        },
        {
          "name": "通用设备",
          "level": 2
        },
        {
          "name": "其他通用设备",
          "level": 3
        }
      ],
      "concepts": [
        "QFII重仓指数",
        "具身智能指数",
        "股权激励指数",
        "人形机器人指数",
        "工业4.0指数",
        "富士康产业链指数",
        "新型工业化指数",
        "通用机械精选指数",
        "仪器仪表精选指数",
        "3D玻璃指数",
        "减速器指数",
        "工业母机指数"
      ],
      "score_company": 7.8,
      "score_trend": 7.6,
      "score_value": 4.1,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月21日，业绩超预期引发股价大幅上涨，当日收涨 13.3% 。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 30% ，最新季度归母净利润同比增长 196% ，成长能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 2.7% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 2227万元 ，较上期增长 7.4% ，占2025年营收 1.4% ，在手订单充足。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 8.5% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月07日大跌 -10.3% ，且成交额为近20日均值的 1.8倍 ，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年07月06日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "波动",
          "text": "2026年07月07日，换手率 20% ，短线资金追逐，波动风险较高。"
        }
      ],
      "events": [
        {
          "content": "08:04 随着半年报陆续披露，各类机构二季度持股动向逐渐曝光。据证券时报·数据宝统计，截至8月5日公开的数据，QFII持股二季度末持有44股，合计持有2.64亿股，期末持股市值173.62亿元。从单只个股持股市值来看，有17股期末持股市值超过1亿元，宁德时代、宏发股份2只个股获持股超20亿元。从新进角度看，有23股为QFII新进持有，合计持股134亿元，除宁德时代外，还包括多只热门科技股，其中包括年内第一大牛股中船特气，以及富满微、乐鑫科技等热门半导体个股。从业绩看，QFII新进股中，盛达资源、富满微、昊志机电、亚翔集成上半年归母净利润同比增长均超2倍。（人民财讯）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "19:53 8月3日，市场全天缩量调整，三大股指集体下挫，科创50午后跌超5%。核电板块逆市走强，中国核建、江苏神通、合锻智能等十余股涨停。光伏概念反弹，通威股份、国晟科技、福莱特涨停。半导体、存储芯片、光刻机、玻璃基板等板块跌幅居前。AI应用人气股传智教育（003032）再度“一”字涨停，迎来6连板。公司布局AI人才培训，率先推出“AI具身智能机器人开发”新学科，发布6款支持二次开发的教学机器人硬件，并深度联动华为鸿蒙等头部科技企业共建课程体系。国泰海通证券首次覆盖传智教育并给予“增持”评级，助推市场热度。业绩方面，公司上半年预计扭亏，持续深化“职业培训+学历教育”双轨发展战略，短训课程招生增长较快，职业培训业务呈现复苏态势。人形机器人板块表现活跃，中大力德（002896）2连板，福莱新材（605488）涨停，卧龙电驱、丰光精密、奥比中光、绿的谐波、丰立智能等跟涨。消息面上，宇树科技冲刺人形机器人第一股，确定于8月10日开放申购，最快8月底登陆科创板，拟募资42.02亿元，按10%公开发行比例推算，发行市值预计420亿元。特斯拉Optimus项目负责人Ashok Elluswamy于7月30日发文，将Optimus远期年产能目标修正为1000万台，为原100万台产能规划的十倍。东吴证券研报称，具身智能竞争重点由“能否实现运动”转向“能否稳定完成任务并实现规模制造”，预计全球人形机器人市场规模由2026年230亿元增长至2030年2776亿元，CAGR达86.4%。随着本体性能提升、核心零部件国产化及规模制造推动BOM成本下降，产业链商业化进程有望加快。\n据统计，今日50余只人形机器人概念股获得主力加仓，绿的谐波主力资金净流入额居首，达2.1亿元。昊志机电、中大力德、福莱新材、拓斯达的主力资金净流入额均超5000万元。福莱新材今日涨停，今年2月与灵心巧手签署全面战略合作协议，灵心巧手向福莱新材采购10万套触觉传感器；5月发布触觉数据采集终端，瞄准具身智能训练中“触觉数据”这一关键缺口。股价表现上，今日获主力加仓的概念股中，昊志机电、福莱新材、拓斯达、泰晶科技、金力永磁等最新股价较年内高点回撤超40%。业绩方面，目前17只人形机器人概念股发布相关数据，从预告下限和快报数据看，业绩预喜的有11股。江苏北人上半年业绩预计扭亏，拓斯达、宏英智能、东方锆业、锐科激光、神力股份上半年净利润均预计同比翻倍。拓斯达上半年业绩增幅最高，预计净利润9000万元至11500万元，同比增长213.24%至300.25%，公司表示工业机器人及自动化应用系统业务收入同比显著增加，毛利贡献大幅提升。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "昊志机电：关于控股股东、实际控制人部分股份解除质押的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "公司发布2026半年报报告，股价开盘上涨 6.55% ，股价收盘涨幅 13.32%",
          "tags": [
            "股价上涨"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1143200539.32,
      "revenue_yoy": 0.181012,
      "operating_profit": 124327503.16,
      "operating_profit_yoy": 0.388607,
      "net_profit": 121638269.18,
      "net_profit_yoy": 0.498441,
      "gross_profit": 428232861.02,
      "gross_profit_yoy": 0.257074,
      "cogs": 714967678.3,
      "gross_margin": 37.46,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20210806",
      "current_price": 71.19,
      "price": 71.19,
      "ma5": 64.8,
      "ma10": 64.88,
      "ma20": 72.12,
      "dist_ma5_pct": 9.9,
      "dist_ma10_pct": 9.7,
      "dist_ma20_pct": -1.3,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.685,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 8.14,
        "pct_float": 4.74,
        "chg5_pct": 6.88,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "601168.SH",
      "fetch_time": "2026-08-06T11:52:59+0800",
      "name": "西部矿业",
      "pe": 16.0246,
      "pb": 4.2475,
      "ps_ttm": 1.37,
      "pcf_ttm": 7.0279,
      "valuation_percentile": 88.9,
      "total_shares": 2383000000,
      "industries": [
        {
          "name": "有色金属",
          "level": 1
        },
        {
          "name": "工业金属",
          "level": 2
        },
        {
          "name": "铜",
          "level": 3
        }
      ],
      "concepts": [
        "贷款回购指数",
        "资源股",
        "西部大开发指数",
        "预期提升指数",
        "锂电池指数",
        "有色金属指数",
        "工业金属精选指数",
        "锌电池指数",
        "铜产业指数",
        "铅锌矿指数",
        "化债AMC指数",
        "铜冶炼指数",
        "锂矿指数",
        "再生金属指数",
        "镍矿指数",
        "青海省国资指数",
        "铁矿石指数"
      ],
      "score_company": 9.1,
      "score_trend": 9.9,
      "score_value": 3.7,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月10日，业绩超预期引发股价跳空高开，当日收涨 5.00% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 143% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 21% ，投入资本回报率为 15% ，盈利能力很强。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 117% ，销售收入现金含量很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.6% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 5.5% ，很受外资机构青睐；公募基金持股 6.4% ，很受内资机构青睐；2026年05月08日至2026年07月31日期间，股东户数减少 30% ，大资金买入。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 97% 的股票，收盘价接近 一年新高 ，走势很强。"
        },
        {
          "tag": "增持",
          "text": "近6月，控股股东累计实际增持 2544万股 ，占总股本比例 1.1% ，金额合计 7.4亿元 。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "09:30股价达到 42 元，创近24个月新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "13:28 按照已披露的半年报、业绩快报、预告净利润下限（若未披露下限则取公告数值）统计，今年上半年净利润同比增长30%以上（含扭亏为盈）的新型储能概念股有22只。恩捷股份、鹏辉能源、智光电气、钒钛股份净利润扭亏为盈。非扭亏股中，10股净利润将达到10亿元以上，包括宁德时代、电投能源、西部矿业、亿纬锂能、天赐材料等。上述22只业绩高增长的新型储能概念股中，截至8月3日收盘，11股滚动市盈率（PE）低于30倍。其中电投能源、西部矿业、海德股份、银龙股份、璞泰来滚动市盈率在20倍以下。电投能源滚动市盈率为14.24倍，排在最低位置。（人民财讯）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "06:00 西部矿业发布2026年半年度报告，上半年实现营业收入394.43亿元，同比增长25%；利润总额71.06亿元，同比增长83%；归属于上市公司股东的净利润41.69亿元，同比增长123%。公司表示，业绩增长主要受益于有色金属市场价格上移及主营产品产量稳定，同时硫酸、硫磺等副产品价格上涨也增厚了利润。上半年公司矿产铜8.97万吨、矿产锌6.39万吨、矿产铅2.95万吨、矿产钼0.24万吨、铁精粉70.66万吨。公司正推进玉龙铜矿扩建及茶亭铜矿等项目建设。玉龙铜业作为核心支撑，目前正推进4500万吨/年生产规模扩建工程预可研及配套基础设施建设。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "西部矿业：独立董事候选人声明与承诺（李计发）",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 48442386524,
      "revenue_yoy": 0.319048,
      "operating_profit": 5967030516,
      "operating_profit_yoy": 0.094865,
      "net_profit": 5182502641,
      "net_profit_yoy": 0.115209,
      "gross_profit": 9520267350,
      "gross_profit_yoy": 0.155746,
      "cogs": 38922119174,
      "gross_margin": 19.65,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 41.02,
      "price": 41.02,
      "ma5": 38.36,
      "ma10": 37.74,
      "ma20": 35.11,
      "dist_ma5_pct": 6.9,
      "dist_ma10_pct": 8.7,
      "dist_ma20_pct": 16.8,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.5113,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 19.46,
        "pct_float": 1.99,
        "chg5_pct": -4.2,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "688981.SH",
      "fetch_time": "2026-08-06T11:53:01+0800",
      "name": "中芯国际",
      "pe": 210.7009,
      "pb": 5.5833,
      "ps_ttm": 15.4883,
      "pcf_ttm": 40.2933,
      "valuation_percentile": 83.94,
      "total_shares": 8560805995,
      "industries": [
        {
          "name": "电子",
          "level": 1
        },
        {
          "name": "半导体",
          "level": 2
        },
        {
          "name": "集成电路制造",
          "level": 3
        }
      ],
      "concepts": [
        "A50指数",
        "TMT指数",
        "HALO指数",
        "三新指数",
        "科技龙头指数",
        "双循环指数",
        "双创100指数",
        "茅指数",
        "人工智能+指数",
        "自主可控指数",
        "5G应用指数",
        "先进制造指数",
        "消费电子产业指数",
        "半导体产业指数"
      ],
      "score_company": 7.0,
      "score_trend": 7.7,
      "score_value": 3.8,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 集成电路制造 行业龙头企业。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 20% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 9家 机构给出评级，其中 67% 为“买入”，距目标价的上涨空间为 36% 。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 18% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 91% 的股票，走势较强。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "2027/06/24解禁5.47亿股，占总股本6.39%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2027-06-24"
        },
        {
          "content": "预计2026/08/28发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-28"
        },
        {
          "content": "13:32 截至8月5日13点16分，上证指数涨1.45%，深证成指涨2.11%，创业板指涨1.79%。电子化学品、国家大基金持股、中芯国际概念等板块涨幅居前。ETF方面，消费电子ETF易方达（562950）涨5.03%，成分股环旭电子（601231）、福晶科技（002222）、工业富联（601138）涨停，生益科技（600183）、北京君正（300223）、兆易创新（603986）、三环集团（300408）、信维通信（300136）、瑞芯微（603893）、顺络电子（002138）涨超5%。消息方面，进入8月，消费电子市场迎来新品发布季，以苹果新一代产品为核心驱动，整个“果链”上下游加快了“招兵买马”的节奏，为产能爬坡做足准备。据媒体报道，富士康等龙头代工厂在工程师岗位上也在不断扩充，资本市场与供应链上下游正密切关注苹果首款折叠屏手机的进展。平安证券表示，晶圆代工行业规模持续增长，大陆占比提升：受益于消费电子、汽车电子、人工智能技术等高科技需求的快速增长，全球半导体产业高速发展，全球晶圆代工市场规模从2021年的1002亿美元增至2025年的1747亿美元，复合年增长率为14.9%。预计到2030年，全球市场将达到2955亿美元，2026年至2030年年复合增长率为10.7%。中国大陆晶圆代工市场销售额从2021年的94亿美元增至2025年的172亿美元，复合年增长率为16.3%。中国大陆在全球的市场占比从2021年的9.4%提升至2025年的9.8%。预计未来随着供应链国产化的进一步加速，中国大陆晶圆代工市场将继续扩大，2026年至2030年的年复合增长率将增至15.1%，到2030年达到347亿美元，预计在全球的市场占比提升至11.8%。\n消费电子ETF易方达（562950）跟踪消费电子指数（931494），被市场定位为“全球算力硬件上游”指数产品。该指数覆盖了PCB、MLCC、光互联等算力硬件的核心领域，成分股中包含了多家在光通信硬件产业链中具有重要地位的企业，前五大权重股包括立讯精密（002475）、寒武纪、工业富联、中芯国际、兆易创新。投资者可关注该产品在光通信景气周期和AI算力硬件升级背景下的配置价值。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 49510416000,
      "revenue_yoy": 0.182233,
      "operating_profit": 6189760000,
      "operating_profit_yoy": 0.742394,
      "net_profit": 5770359000,
      "net_profit_yoy": 0.785019,
      "gross_profit": 11462219000,
      "gross_profit_yoy": 0.551649,
      "cogs": 38048197000,
      "gross_margin": 23.15,
      "pe_forward": null,
      "valuation_history_days": 327,
      "valuation_history_from": "20220718",
      "current_price": 125.45,
      "price": 125.45,
      "ma5": 122.01,
      "ma10": 131.02,
      "ma20": 144.27,
      "dist_ma5_pct": 2.8,
      "dist_ma10_pct": -4.3,
      "dist_ma20_pct": -13.0,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.6829,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 110.21,
        "pct_float": 4.39,
        "chg5_pct": 1.58,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "300373.SZ",
      "fetch_time": "2026-08-06T11:53:01+0800",
      "name": "扬杰科技",
      "pe": 37.0804,
      "pb": 5.2729,
      "ps_ttm": 6.6164,
      "pcf_ttm": 31.4463,
      "valuation_percentile": 56.31,
      "total_shares": 543347787,
      "industries": [
        {
          "name": "电子",
          "level": 1
        },
        {
          "name": "半导体",
          "level": 2
        },
        {
          "name": "分立器件",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "双创100指数",
        "华为平台指数",
        "半导体产业指数",
        "5G指数",
        "半导体精选指数",
        "集成电路指数",
        "中小创蓝筹指数",
        "GDR指数",
        "晶圆产业指数",
        "华为合作半导体企业指数",
        "IGBT指数",
        "汽车芯片指数"
      ],
      "score_company": 8.2,
      "score_trend": 6.4,
      "score_value": 5.3,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 21% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 14% ，投入资本回报率为 12% ，盈利能力很强。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 1.2% ，现金分红较高。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 2.9% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年07月01日 至今陷入调整，资金有出逃可能。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/22发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-22"
        },
        {
          "content": "15:00 今天大涨的原因可能是扬杰科技发布2026年上半年业绩预告，预计净利同比增长20%-40%，表明公司半导体器件业务盈利能力和业绩预期显著改善。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "17:33 扬杰科技披露2026年半年度业绩预告，预计上半年归母净利润为7.22亿元至8.42亿元，同比增长20.00%至40.00%；扣非净利润为7.00亿元至8.20亿元，同比增长25.21%至46.72%。公司上半年营业收入同比增长约30%，主要受功率半导体行业景气度上行、AI服务器及新能源汽车等需求释放驱动。汽车电子业务上半年收入同比增幅超100%，SiC碳化硅业务收入同比接近翻倍。公司目前拥有扬州6英寸车规SiC晶圆产线，七号厂车规级功率模块封装项目预计下半年启动设备调试，越南6英寸SiC晶圆工厂计划2027年一季度量产。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价盘中下跌 -8.03%",
          "tags": [
            "股价下跌"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 5347737516.95,
      "revenue_yoy": 0.208906,
      "operating_profit": 1131627914.34,
      "operating_profit_yoy": 0.448632,
      "net_profit": 965260944.26,
      "net_profit_yoy": 0.442554,
      "gross_profit": 1873671359.97,
      "gross_profit_yoy": 0.365278,
      "cogs": 3474066156.98,
      "gross_margin": 35.04,
      "pe_forward": null,
      "valuation_history_days": 299,
      "valuation_history_from": "20210806",
      "current_price": 91.01,
      "price": 91.01,
      "ma5": 84.73,
      "ma10": 87.3,
      "ma20": 97.57,
      "dist_ma5_pct": 7.4,
      "dist_ma10_pct": 4.2,
      "dist_ma20_pct": -6.7,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.685,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 15.72,
        "pct_float": 3.19,
        "chg5_pct": 2.77,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "601233.SH",
      "fetch_time": "2026-08-06T11:53:01+0800",
      "name": "桐昆股份",
      "pe": 16.7565,
      "pb": 1.3928,
      "ps_ttm": 0.5685,
      "pcf_ttm": 6.9976,
      "valuation_percentile": 49.42,
      "total_shares": 2379001490,
      "industries": [
        {
          "name": "石油石化",
          "level": 1
        },
        {
          "name": "炼化及贸易",
          "level": 2
        },
        {
          "name": "其他石化",
          "level": 3
        }
      ],
      "concepts": [
        "三新指数",
        "贷款回购指数",
        "资源股",
        "股权激励指数",
        "预期提升指数",
        "养老金指数",
        "石化精选指数",
        "涤纶指数",
        "PTA指数"
      ],
      "score_company": 8.8,
      "score_trend": 8.5,
      "score_value": 5.6,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 其他石化 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 395% ，利润成长性强。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 110% ，销售收入现金含量较强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 4.6% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 11家 机构给出评级，其中 82% 为“买入”，距目标价的上涨空间为 41% 。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.0% ，较受外资机构青睐；公募基金持股 6.6% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 93% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 31% ，收益质量较低。"
        },
        {
          "tag": "偿债",
          "text": "带息债务占全部投入资本 60% ，偿债压力较大。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/26发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-26"
        },
        {
          "content": "回购总金额不超过3453万元，回购最高价不超过7.98元/股 （预案）",
          "tags": [
            "公司回购限售股"
          ]
        },
        {
          "content": "17:07 2026年8月4日，中银证券发布基础化工行业研究报告，指出国际原油、环氧丙烷价格下跌，有机硅价格上涨。报告提出8月份重点关注：中报行情；由中国断供稀土、下游需求旺盛等带来的涨价行情，尤其电子材料等领域；染料、长丝等子行业企稳修复涨价情况。本周（07.27-08.02）均价跟踪的100个化工品种中，共38个品种价格上涨，36个品种价格下跌，26个品种价格稳定。跟踪产品中38%的产品月均价环比上涨，51%的产品月均价环比下跌，11%的产品月均价环比持平。周均价涨幅居前品种为：丙烯腈、醋酸乙烯（华东）、液氨（河北新化）、煤焦油（山西）、甲基环硅氧烷；周均价跌幅居前的品种为：硝酸铵（陕西兴化）、石脑油（新加坡）、维生素A、NYMEX天然气、WTI原油。\n本周（07.27-08.02）国际油价下跌，WTI原油期货价格收于84.67美元/桶，收盘价周跌幅5.20%；布伦特原油期货价格收于90.12美元/桶，收盘价周跌幅6.88%。宏观方面，美国总统特朗普27日对媒体表示，决定暂停对伊朗的打击，同日，伊朗外交部长阿拉格齐与阿曼以及沙特阿拉伯外交大臣分别通话，讨论霍尔木兹海峡事宜。当地时间7月30日，美国总统特朗普表示，“和平委员会”当天达成一项“历史性协议”，哈马斯及加沙地带其他所有武装团体将全面解除武装。供应方面，根据EIA数据，截至7月24日当周，美国原油日均产量1,379.6万桶，较前一周减少了0.2万桶，较去年同期日均产量增加48.2万桶；需求方面，美国石油需求总量日均2,075.4万桶，较前一周增加23.5万桶，其中美国汽油日均需求量904.1万桶，较前一周增加9.4万桶；库存方面，包括战略储备在内的美国原油库存总量152,630.0万桶，较前一周增加750.0万桶。展望后市，短期地缘风险主导，需关注后续事态进展；中长期来看，待冲突缓和后，供应过剩压力或导致国际油价中枢下行，但地缘政治等仍可能对国际油价产生意外冲击，加剧国际油价波动幅度。本周NYMEX天然气期货收于2.75美元/mmbtu，收盘价周跌幅4.18%。EIA天然气库存周报显示，截至7月24日当周，美国天然气库存总量为30,840亿立方英尺，较前一周增加280亿立方英尺，较去年同期减少320亿立方英尺，跌幅为1.0%，同时较5年均值增加1,850亿立方英尺，涨幅为6.4%。展望后市，短期来看，尽管地缘局势释放积极信号，但欧洲储气进度不及预期及旺季需求有望推升天然气价格；中期来看，欧洲能源供应结构依然脆弱，地缘政治博弈以及季节性需求波动都有可能导致天然气价格剧烈宽幅震荡。\n本周（07.27-08.02）有机硅DMC价格止跌回升。根据百川盈孚，截至7月31日，有机硅DMC价格为1.23万元/吨，较上周末上涨6.72%，本周均价为1.20万元/吨。供应方面，本周国内有机硅单体厂周产量为4.29万吨，环比增加7.52%。云南能投（002053）、内蒙古恒星装置恢复生产，与浙江新安局部检修等相互对冲，山东金岭15万吨装置计划下月复产，后续供应仍存在增量预期。库存方面，主流单体厂依靠前期预售订单持续去库，工厂库存降至4.06万吨，环比下降8.35%，库存压力有所缓解。需求方面，根据百川盈孚，单体厂收紧低价货源、封盘挺价后，中下游询盘有所回暖，部分低库存企业开始小批量试探采购和前置备货，但终端仍处传统淡季，集中采购需求尚未有效释放。成本利润方面，目前国内有机硅综合成本约11878.13元/吨，环比下降0.83%，平均毛利润约778.13元/吨，环比回升33.15%。展望后市，短期市场具备温和修复条件，行情核心仍取决于行业协同减产及稳价方案的实际执行力度，预计近期有机硅市场以底部偏强震荡为主。本周（07.27-08.02）环氧丙烷价格下跌。根据百川盈孚，截至7月30日，国内环氧丙烷市场均价为0.90万元/吨，较上周同期下降6.25%。供应方面，本周行业开工率为50.84%，周产量为9.37万吨，环比增加1.18%。镇海二期、齐翔腾达（002408）、盛虹、瑞恒、联泓等装置仍处停车检修状态，滨华、广西石化降负运行，但航锦及中石化长岭装置周内提负至满产，供应整体仍处低位但边际有所恢复。库存方面，根据百川盈孚，截至7月30日，国内工厂库存为2.72万吨，环比增加0.96%。需求方面，终端仍处传统淡季，需求回暖的持续性有限。成本方面，根据百川盈孚，本周环氧丙烷生产成本为9633.52元/吨，环比下降1.27%，但自29日起丙烯、液氯价格走强，或支撑后续价格。利润方面，根据百川盈孚，本周行业平均毛利润为-253.8元/吨，毛利率为-2.71%，行业再度转入亏损。展望后市，下半年行业仍有90万吨/年新增产能计划释放，叠加检修装置重启预期及终端订单偏弱，预计近期环氧丙烷价格以低位震荡企稳为主。\n截至7月31日，SW基础化工市盈率（TTM剔除负值）为24.59倍，处在历史（2002年至今）71.18%分位数；市净率为2.20倍，处在历史50.88%分位数。SW石油石化市盈率（TTM剔除负值）为14.11倍，处在历史（2002年至今）41.98%分位数；市净率为1.33倍，处在历史43.77%分位数。展望2026年，本轮行业扩产已近尾声，“反内卷”等措施有望催化行业盈利底部修复，同时新材料受益于下游需求的快速发展，有望开启新一轮高成长。8月份重点关注：1、中报行情；2、由中国断供稀土、下游需求旺盛等带来的涨价行情，尤其电子材料等领域；3、染料、长丝等子行业企稳修复涨价情况。中长期推荐投资主线：1、地缘冲突持续背景下油价维持中高位，优质石化、煤化工资产有望迎来价值重估；2、化工产业全球市占率与竞争力持续提升，行业龙头经营韧性凸显，布局新材料等领域，竞争能力逆势提升，行业景气度好转背景下有望迎来业绩、估值双提升；3、“双碳”“反内卷”等持续催化，关注供需格局持续向好子行业，包括炼化、聚酯、染料、有机硅、农药、制冷剂、磷化工等；4、下游行业快速发展，新材料领域公司发展空间广阔。推荐：中国石油（601857）、中国海油（600938）、卫星化学（002648）、宝丰能源（600989）、万华化学（600309）、华鲁恒升（600426）、新和成（002001）、中国石化（600028）、恒力石化（600346）、东方盛虹（000301）、桐昆股份（601233）、新凤鸣（603225）、浙江龙盛（600352）、兴发集团（600141）、扬农化工（600486）、利尔化学（002258）、联化科技（002250）、巨化股份（600160）、云天化（600096）、赛轮轮胎（601058）、安集科技、雅克科技（002409）、鼎龙股份（300054）、江丰电子（300666）、彤程新材（603650）、圣泉集团（605589）、东材科技（601208）、中材科技（002080）、莱特光电、蓝晓科技（300487）、瑞联新材等。8月金股：安集科技，巨化股份。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "桐昆股份：桐昆集团股份有限公司章程202607",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "桐昆股份：桐昆集团股份有限公司关于变更注册资本并修订《公司章程》的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 67397282748.76,
      "revenue_yoy": -0.113763,
      "operating_profit": 1594418190.9,
      "operating_profit_yoy": 0.732289,
      "net_profit": 1561635856.95,
      "net_profit_yoy": 0.533433,
      "gross_profit": 3916995383.48,
      "gross_profit_yoy": 0.002129,
      "cogs": 63480287365.28,
      "gross_margin": 5.81,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20210806",
      "current_price": 22.99,
      "price": 22.99,
      "ma5": 22.41,
      "ma10": 22.07,
      "ma20": 21.44,
      "dist_ma5_pct": 2.6,
      "dist_ma10_pct": 4.2,
      "dist_ma20_pct": 7.2,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.5113,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 8.78,
        "pct_float": 1.61,
        "chg5_pct": -7.89,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "600160.SH",
      "fetch_time": "2026-08-06T11:53:01+0800",
      "name": "巨化股份",
      "pe": 27.9396,
      "pb": 5.6286,
      "ps_ttm": 4.2589,
      "pcf_ttm": 17.2603,
      "valuation_percentile": 93.55,
      "total_shares": 2699746081,
      "industries": [
        {
          "name": "基础化工",
          "level": 1
        },
        {
          "name": "化学制品",
          "level": 2
        },
        {
          "name": "氟化工",
          "level": 3
        }
      ],
      "concepts": [
        "HALO指数",
        "资源股",
        "半导体材料指数",
        "六氟磷酸锂指数",
        "化学制品精选指数",
        "CDM指数",
        "浙江省国资指数",
        "工业气体指数",
        "PVDF指数",
        "氟化工指数",
        "氢氟酸指数",
        "制冷剂指数",
        "萤石指数",
        "除尘指数",
        "锦纶指数"
      ],
      "score_company": 9.1,
      "score_trend": 7.9,
      "score_value": 3.5,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 氟化工 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 45% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 13% ，投入资本回报率为 12% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 145% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 23% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 4.0亿元 ，较上期增长 9.0% ，占2025年营收 1.5% ，在手订单充足。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 4.4% ，较受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 98% 的股票，走势很强。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月03日大跌 -9.99% ，股价跌停，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/26发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-26"
        },
        {
          "content": "17:00 本周氟化工市场，上游产品现货价格变动如下：液氯周跌20.00%，月跌166.67%，报100.00元/吨；甲醇MA周跌3.45%，月涨1.42%，报2565.00元/吨；电石周涨2.13%，月跌0.41%，报2400.00元/吨；硫酸周跌1.43%，月跌2.37%，报2062.50元/吨；萤石周涨0.73%，月涨2.04%，报3443.75元/吨；烧碱周跌0.31%，月跌2.58%，报641.00元/吨。氟化工产业链相关价格异动：二氯甲烷周跌2.25%，月涨11.14%，报2170.00元/吨；R134a周涨1.56%，月涨2.09%，报65000.00元/吨；聚四氟乙烯周持平，月跌6.25%，报30000.00元/吨；萤石(97湿粉)周持平，月涨2.94%，报3500.00元/吨；氢氟酸周持平，月涨5.39%，报16300.00元/吨；R22周持平，月涨2.19%，报23333.33元/吨。受氟化工市场价格变化影响的公司方面：永太科技净利润1.22亿元，机构预测年度净利润--，截止2026-03-31，工业产品收入占比63.63%；多氟多净利润4.32亿元，预测17.24亿元，新材料占比61.54%，产品产销/库存量53500吨；中欣氟材净利润-0.04亿元，精细化工占比59.28%，产品产销/库存量4797.22吨；联创股份净利润0.09亿元，含氟新材料产品占比79.86%，产品产销/库存量2499.89吨；巨化股份净利润13.01亿元，预测59.49亿元，氟化工原料占比21.44%；昊华科技净利润3.82亿元，预测21.80亿元，高端氟材料占比28.31%，产品产销/库存量2700.93吨；三美股份净利润5.00亿元，预测26.95亿元，氟产品占比96.00%。（注：财务数据截止到该公司最新披露的财务报告日期）\n氟化工产业链以萤石为起点，中上游主要为氢氟酸及氟化铝等，并延伸出氟制冷剂、含氟聚合物、含氟精细化学品和无机氟化物四大类，终端产品为空调及汽车用的制冷剂、工业含氟新材料、半导体领域中极其重要的电子级氢氟酸等。氟化工产业链中，随产品加工深度增加，产品的附加值和利润率成几何级数增长。目前四代氟制冷剂、含氟精细化学品、含氟聚合物等产品均处于起步及成长阶段。目前氟化工产业市场容量最大仍为传统的制冷剂行业，但氟橡塑及氟精细化工凭借其广泛的用途及优良的特性正加快在各领域的渗透。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "17:07 2026年8月4日，中银证券发布基础化工行业研究报告，指出国际原油、环氧丙烷价格下跌，有机硅价格上涨。报告提出8月份重点关注：中报行情；由中国断供稀土、下游需求旺盛等带来的涨价行情，尤其电子材料等领域；染料、长丝等子行业企稳修复涨价情况。本周（07.27-08.02）均价跟踪的100个化工品种中，共38个品种价格上涨，36个品种价格下跌，26个品种价格稳定。跟踪产品中38%的产品月均价环比上涨，51%的产品月均价环比下跌，11%的产品月均价环比持平。周均价涨幅居前品种为：丙烯腈、醋酸乙烯（华东）、液氨（河北新化）、煤焦油（山西）、甲基环硅氧烷；周均价跌幅居前的品种为：硝酸铵（陕西兴化）、石脑油（新加坡）、维生素A、NYMEX天然气、WTI原油。\n本周（07.27-08.02）国际油价下跌，WTI原油期货价格收于84.67美元/桶，收盘价周跌幅5.20%；布伦特原油期货价格收于90.12美元/桶，收盘价周跌幅6.88%。宏观方面，美国总统特朗普27日对媒体表示，决定暂停对伊朗的打击，同日，伊朗外交部长阿拉格齐与阿曼以及沙特阿拉伯外交大臣分别通话，讨论霍尔木兹海峡事宜。当地时间7月30日，美国总统特朗普表示，“和平委员会”当天达成一项“历史性协议”，哈马斯及加沙地带其他所有武装团体将全面解除武装。供应方面，根据EIA数据，截至7月24日当周，美国原油日均产量1,379.6万桶，较前一周减少了0.2万桶，较去年同期日均产量增加48.2万桶；需求方面，美国石油需求总量日均2,075.4万桶，较前一周增加23.5万桶，其中美国汽油日均需求量904.1万桶，较前一周增加9.4万桶；库存方面，包括战略储备在内的美国原油库存总量152,630.0万桶，较前一周增加750.0万桶。展望后市，短期地缘风险主导，需关注后续事态进展；中长期来看，待冲突缓和后，供应过剩压力或导致国际油价中枢下行，但地缘政治等仍可能对国际油价产生意外冲击，加剧国际油价波动幅度。本周NYMEX天然气期货收于2.75美元/mmbtu，收盘价周跌幅4.18%。EIA天然气库存周报显示，截至7月24日当周，美国天然气库存总量为30,840亿立方英尺，较前一周增加280亿立方英尺，较去年同期减少320亿立方英尺，跌幅为1.0%，同时较5年均值增加1,850亿立方英尺，涨幅为6.4%。展望后市，短期来看，尽管地缘局势释放积极信号，但欧洲储气进度不及预期及旺季需求有望推升天然气价格；中期来看，欧洲能源供应结构依然脆弱，地缘政治博弈以及季节性需求波动都有可能导致天然气价格剧烈宽幅震荡。\n本周（07.27-08.02）有机硅DMC价格止跌回升。根据百川盈孚，截至7月31日，有机硅DMC价格为1.23万元/吨，较上周末上涨6.72%，本周均价为1.20万元/吨。供应方面，本周国内有机硅单体厂周产量为4.29万吨，环比增加7.52%。云南能投（002053）、内蒙古恒星装置恢复生产，与浙江新安局部检修等相互对冲，山东金岭15万吨装置计划下月复产，后续供应仍存在增量预期。库存方面，主流单体厂依靠前期预售订单持续去库，工厂库存降至4.06万吨，环比下降8.35%，库存压力有所缓解。需求方面，根据百川盈孚，单体厂收紧低价货源、封盘挺价后，中下游询盘有所回暖，部分低库存企业开始小批量试探采购和前置备货，但终端仍处传统淡季，集中采购需求尚未有效释放。成本利润方面，目前国内有机硅综合成本约11878.13元/吨，环比下降0.83%，平均毛利润约778.13元/吨，环比回升33.15%。展望后市，短期市场具备温和修复条件，行情核心仍取决于行业协同减产及稳价方案的实际执行力度，预计近期有机硅市场以底部偏强震荡为主。本周（07.27-08.02）环氧丙烷价格下跌。根据百川盈孚，截至7月30日，国内环氧丙烷市场均价为0.90万元/吨，较上周同期下降6.25%。供应方面，本周行业开工率为50.84%，周产量为9.37万吨，环比增加1.18%。镇海二期、齐翔腾达（002408）、盛虹、瑞恒、联泓等装置仍处停车检修状态，滨华、广西石化降负运行，但航锦及中石化长岭装置周内提负至满产，供应整体仍处低位但边际有所恢复。库存方面，根据百川盈孚，截至7月30日，国内工厂库存为2.72万吨，环比增加0.96%。需求方面，终端仍处传统淡季，需求回暖的持续性有限。成本方面，根据百川盈孚，本周环氧丙烷生产成本为9633.52元/吨，环比下降1.27%，但自29日起丙烯、液氯价格走强，或支撑后续价格。利润方面，根据百川盈孚，本周行业平均毛利润为-253.8元/吨，毛利率为-2.71%，行业再度转入亏损。展望后市，下半年行业仍有90万吨/年新增产能计划释放，叠加检修装置重启预期及终端订单偏弱，预计近期环氧丙烷价格以低位震荡企稳为主。\n截至7月31日，SW基础化工市盈率（TTM剔除负值）为24.59倍，处在历史（2002年至今）71.18%分位数；市净率为2.20倍，处在历史50.88%分位数。SW石油石化市盈率（TTM剔除负值）为14.11倍，处在历史（2002年至今）41.98%分位数；市净率为1.33倍，处在历史43.77%分位数。展望2026年，本轮行业扩产已近尾声，“反内卷”等措施有望催化行业盈利底部修复，同时新材料受益于下游需求的快速发展，有望开启新一轮高成长。8月份重点关注：1、中报行情；2、由中国断供稀土、下游需求旺盛等带来的涨价行情，尤其电子材料等领域；3、染料、长丝等子行业企稳修复涨价情况。中长期推荐投资主线：1、地缘冲突持续背景下油价维持中高位，优质石化、煤化工资产有望迎来价值重估；2、化工产业全球市占率与竞争力持续提升，行业龙头经营韧性凸显，布局新材料等领域，竞争能力逆势提升，行业景气度好转背景下有望迎来业绩、估值双提升；3、“双碳”“反内卷”等持续催化，关注供需格局持续向好子行业，包括炼化、聚酯、染料、有机硅、农药、制冷剂、磷化工等；4、下游行业快速发展，新材料领域公司发展空间广阔。推荐：中国石油（601857）、中国海油（600938）、卫星化学（002648）、宝丰能源（600989）、万华化学（600309）、华鲁恒升（600426）、新和成（002001）、中国石化（600028）、恒力石化（600346）、东方盛虹（000301）、桐昆股份（601233）、新凤鸣（603225）、浙江龙盛（600352）、兴发集团（600141）、扬农化工（600486）、利尔化学（002258）、联化科技（002250）、巨化股份（600160）、云天化（600096）、赛轮轮胎（601058）、安集科技、雅克科技（002409）、鼎龙股份（300054）、江丰电子（300666）、彤程新材（603650）、圣泉集团（605589）、东材科技（601208）、中材科技（002080）、莱特光电、蓝晓科技（300487）、瑞联新材等。8月金股：安集科技，巨化股份。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "巨化股份：巨化股份2026年第一次临时股东会之法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "史建兵 任独立董事",
          "tags": [
            "管理层变更"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 20393824651.95,
      "revenue_yoy": 0.138911,
      "operating_profit": 4175030422.42,
      "operating_profit_yoy": 1.701978,
      "net_profit": 3623403550.23,
      "net_profit_yoy": 1.631417,
      "gross_profit": 5885263652.21,
      "gross_profit_yoy": 0.939402,
      "cogs": 14508560999.74,
      "gross_margin": 28.86,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 43.09,
      "price": 43.09,
      "ma5": 40.69,
      "ma10": 40.17,
      "ma20": 40.77,
      "dist_ma5_pct": 5.9,
      "dist_ma10_pct": 7.3,
      "dist_ma20_pct": 5.7,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.5113,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 40.11,
        "pct_float": 3.45,
        "chg5_pct": -1.43,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002056.SZ",
      "fetch_time": "2026-08-06T11:53:01+0800",
      "name": "横店东磁",
      "pe": 19.6504,
      "pb": 3.4755,
      "ps_ttm": 1.5304,
      "pcf_ttm": 10.2192,
      "valuation_percentile": 52.96,
      "total_shares": 1626712074,
      "industries": [
        {
          "name": "电力设备",
          "level": 1
        },
        {
          "name": "光伏设备",
          "level": 2
        },
        {
          "name": "光伏电池组件",
          "level": 3
        }
      ],
      "concepts": [
        "消费电子产业指数",
        "QFII重仓指数",
        "员工持股指数",
        "新材料指数",
        "新能源汽车指数",
        "锂电池指数",
        "苹果指数",
        "特斯拉指数",
        "磷酸铁锂电池指数",
        "新能源指数",
        "光伏指数",
        "能源出海指数",
        "电源设备精选指数",
        "无线充电指数",
        "三元锂电池指数",
        "稀土永磁指数",
        "触板指数",
        "磁悬浮列车指数",
        "钙钛矿电池指数"
      ],
      "score_company": 8.5,
      "score_trend": 6.4,
      "score_value": 5.8,
      "highlights": [
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 18% ，投入资本回报率为 16% ，盈利能力很强。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 2.8% ，现金分红极高。"
        },
        {
          "tag": "订单",
          "text": "合同负债 6.5亿元 ，较上期增长 36% ，占2025年营收 2.9% ，在手订单充足。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 6.1% ，很受外资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月13日大跌 -9.98% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年07月06日 至今陷入调整，资金有出逃可能。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/20发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-20"
        },
        {
          "content": "10:52 稀土永磁板块持续走低，争光股份跌超10%，中钢天源触及跌停，北方稀土、横店东磁、大地熊、中矿资源跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "16:07 横店东磁7月1日在互动平台表示，公司现有光伏产品面向地面应用，目前没有太空光伏产品。（界面新闻）",
          "tags": [
            "快讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 17561698935.87,
      "revenue_yoy": 0.293063,
      "operating_profit": 2180995490.65,
      "operating_profit_yoy": 1.153775,
      "net_profit": 1808006456.6,
      "net_profit_yoy": 0.971811,
      "gross_profit": 3146659428.33,
      "gross_profit_yoy": 0.522794,
      "cogs": 14415039507.54,
      "gross_margin": 17.92,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210806",
      "current_price": 21.94,
      "price": 21.94,
      "ma5": 20.74,
      "ma10": 21.06,
      "ma20": 22.81,
      "dist_ma5_pct": 5.8,
      "dist_ma10_pct": 4.2,
      "dist_ma20_pct": -3.8,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6005,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 7.05,
        "pct_float": 1.98,
        "chg5_pct": -0.9,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "688777.SH",
      "fetch_time": "2026-08-06T11:53:01+0800",
      "name": "中控技术",
      "pe": 206.1964,
      "pb": 8.3206,
      "ps_ttm": 10.245,
      "pcf_ttm": 302.8988,
      "valuation_percentile": 79.74,
      "total_shares": 791189527,
      "industries": [
        {
          "name": "机械设备",
          "level": 1
        },
        {
          "name": "自动化设备",
          "level": 2
        },
        {
          "name": "工控设备",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "双创100指数",
        "自主可控指数",
        "先进制造指数",
        "具身智能指数",
        "人形机器人指数",
        "GDR指数",
        "工业4.0指数",
        "人工智能指数",
        "机器人指数",
        "DeepSeek指数",
        "新型工业化指数",
        "工业软件指数"
      ],
      "score_company": 8.2,
      "score_trend": 8.6,
      "score_value": 4.2,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 工控设备 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年04月27日，业绩超预期引发股价大幅上涨，当日收涨 11.2% 。"
        },
        {
          "tag": "订单",
          "text": "合同负债 15亿元 ，较上期增长 7.6% ，占2025年营收 19% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 10家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 12% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 4.1% ，收益质量较低。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比为 75% ，销售收入现金含量较低。"
        }
      ],
      "events": [
        {
          "content": "2027/01/05解禁399.04万股，占总股本0.50%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2027-01-05"
        },
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "13:23 7月31日，午后人形机器人概念板块涨势扩大。奥比中光、福莱新材、永茂泰封涨停，中大力德、锋龙股份、日盈电子、卧龙电驱此前已涨停，中控技术、绿的谐波、昊志机电、沃尔德等多股涨幅超过10%。消息面上，宇树科技公告称，公司首次公开发行股票并在科创板上市，初步询价日为2026年8月5日，网下申购日为2026年8月10日。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "中控技术：中控技术股份有限公司关于调整暨聘任部分高级管理人员的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 5653987901.79,
      "revenue_yoy": -0.107777,
      "operating_profit": 466391868.46,
      "operating_profit_yoy": -0.388337,
      "net_profit": 438594253.77,
      "net_profit_yoy": -0.397293,
      "gross_profit": 1801796117.74,
      "gross_profit_yoy": -0.1345,
      "cogs": 3852191784.05,
      "gross_margin": 31.87,
      "pe_forward": null,
      "valuation_history_days": 298,
      "valuation_history_from": "20221125",
      "current_price": 106.59,
      "price": 106.59,
      "ma5": 94.64,
      "ma10": 88.25,
      "ma20": 92.39,
      "dist_ma5_pct": 12.6,
      "dist_ma10_pct": 20.8,
      "dist_ma20_pct": 15.4,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.6829,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 26.8,
        "pct_float": 3.19,
        "chg5_pct": 1.26,
        "net5_repay_days": 4,
        "signal": "adding"
      }
    }
  ],
  "active_positions": [
    {
      "code": "000703",
      "name": "恒逸石化",
      "entryDate": "2026-07-29",
      "entryPrice": 15.6,
      "targetPrice": 21.0,
      "stopLoss": 14.82,
      "currentStop": 14.82,
      "thesis": "H1净利暴增+2326-2547%，文莱炼化独特资产享受税收+市场化定价红利，PTA产能周期见底，10亿回购进行中",
      "sector": "石油石化",
      "rps120": 97.37,
      "catalysts": [],
      "shares": 1600,
      "allocation_pct": 3.0,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.6921,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 8.7,
        "pct_float": 1.4,
        "chg5_pct": -2.36,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      },
      "history": [
        {
          "date": "2026-08-03",
          "price": 16.2,
          "change_pct": 3.85,
          "action": "HOLD",
          "note": "+3.85% PnL, 5 days held. Thesis intact: H1净利+2326-2547%, 文莱炼化 tax+mkt pricing edge, 10亿回购. Sector 石油石化 mid-pack, no gravity. Stop at ¥14.82 (-5%) safe with 8.5% cushion. Far from 10-day time stop. Margin neutral."
        },
        {
          "date": "2026-08-04",
          "price": 15.77,
          "change_pct": 1.09,
          "action": "HOLD",
          "note": "PnL+1.09%持仓7天，thesis完整（H1净利暴增+2326-2547%，文莱炼化独特资产，10亿回购）。Sector石油石化中游无板块拖累。距10日时间止损仅剩3天——若8/7仍<+3%则触发SELL。今日-2.65%温和回调。"
        },
        {
          "date": "2026-08-05",
          "price": 16.43,
          "change_pct": 5.32,
          "action": "HOLD",
          "note": "PnL+5.32%持仓8天。距10日时间止损仅剩2天但远高于+3%门槛，不会触发。⚠️油气开采Ⅱ今日在Bottom5——Rule 1要求板块持续冷门3天以上才触发卖出，今日为第1天。密切关注。"
        }
      ]
    },
    {
      "code": "002138",
      "name": "顺络电子",
      "entryDate": "2026-08-04",
      "entryPrice": 43.51,
      "targetPrice": 52.0,
      "stopLoss": 41.33,
      "currentStop": 43.51,
      "thesis": "元件sector今日#2（+7.56%），RPS120=89.79%甜点位。被动元件龙头，H1营收+19.67%成长稳健。MA距离全部合规（dist_ma5+3.0%, dist_ma10+1.7%）。Margin adding（+7.19%）。北向6.9%+公募5.5%机构认可。净利微降-7.98%已被市场消化（今日+6.73%），利空出尽。",
      "sector": "元件",
      "rps120": 89.79,
      "catalysts": [],
      "shares": 1100,
      "allocation_pct": 6.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6005,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 14.29,
        "pct_float": 3.76,
        "chg5_pct": 7.0,
        "net5_repay_days": 3,
        "signal": "adding"
      },
      "history": [
        {
          "date": "2026-08-04",
          "price": 43.51,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 顺络电子"
        },
        {
          "date": "2026-08-04",
          "price": 47.23,
          "change_pct": 8.55,
          "action": "HOLD",
          "note": "PnL+8.55%今日开仓即大涨！Sector元件#2（+8.45%）极强势。被动元件龙头直接受益MLCC涨价潮。逼近+10%止盈阈值——若明日触及¥47.86立即提止损至成本价¥43.51。今日+8.55%后MA偏离加大但不影响持仓（Rule 2b仅约束新开仓）。"
        },
        {
          "date": "2026-08-05",
          "price": 50.28,
          "change_pct": 15.56,
          "action": "RAISE_STOP",
          "note": "PnL+15.56%持仓2天，Rule 5强制触发：+10%以上→止损提至盈亏平衡¥43.51。元件sector受益MLCC涨价潮，今日+6.46%继续强势。距+20%（¥52.21）仅差¥1.93——触及后止损提至+10%。"
        }
      ]
    },
    {
      "code": "300001",
      "name": "特锐德",
      "entryDate": "2026-08-04",
      "entryPrice": 35.66,
      "targetPrice": 43.0,
      "stopLoss": 33.88,
      "currentStop": 33.88,
      "thesis": "充电桩龙头，特来电23%市场份额全国第一。8/1 3C认证强制实施重塑行业格局，头部集中利好。H1净利预增+20-40%，上半年充电量+47%。拟回购≤6亿。MA距离全部合规（dist_ma5+3.6%, dist_ma10+1.8%）。北向8.2%。",
      "sector": "电网设备",
      "rps120": 93.89,
      "catalysts": [],
      "shares": 1200,
      "allocation_pct": 6.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.685,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 11.21,
        "pct_float": 3.04,
        "chg5_pct": 0.07,
        "net5_repay_days": 4,
        "signal": "neutral"
      },
      "history": [
        {
          "date": "2026-08-04",
          "price": 35.66,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 特锐德"
        },
        {
          "date": "2026-08-04",
          "price": 36.24,
          "change_pct": 1.63,
          "action": "HOLD",
          "note": "PnL+1.63%今日开仓。充电桩龙头，3C认证8/1强制实施利好头部集中（特来电23%市占率）。H1净利预增+20-40%，上半年充电量+47%。拟回购≤6亿。Margin deleveraging轻度警示。Sector电网设备中游。"
        },
        {
          "date": "2026-08-05",
          "price": 36.14,
          "change_pct": 1.35,
          "action": "HOLD",
          "note": "PnL+1.35%持仓2天。充电桩龙头3C认证利好逻辑完好，H1充电量+47%。今日微跌-0.28%正常波动。IV rank 80%偏高但非卖出信号。"
        }
      ]
    },
    {
      "code": "300408",
      "name": "三环集团",
      "entryDate": "2026-07-31",
      "entryPrice": 115.07,
      "targetPrice": 130.0,
      "stopLoss": 103.45,
      "currentStop": 115.07,
      "thesis": "MLCC行业景气爆发：三星电机8/1起全系列MLCC涨价30%，太阳诱电9/1跟进涨价。AI服务器MLCC用量为普通服务器数倍，高端产品供需紧至2027H1。公司7月21日完成8.9亿回购+7月30日再推5-10亿二期回购。上半年业绩预增45-65%。零风险标签。元件sector #3今日+7.66%。",
      "sector": "元件",
      "rps120": 98.09,
      "catalysts": [],
      "shares": 600,
      "allocation_pct": 8.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.685,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 37.42,
        "pct_float": 1.56,
        "chg5_pct": -3.16,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      },
      "history": [
        {
          "date": "2026-08-03",
          "price": 114.0,
          "change_pct": -0.93,
          "action": "HOLD",
          "note": "-0.93% in 3 days. MLCC catalyst (Samsung 8/1涨价30%, 太阳诱电9/1跟进) just activated. Bounced +2.08% today after testing ¥110. Stop tightened from ¥103.45 (-10.1%, incorrect) to ¥109.32 (-5% per V2 Rule 5). Monitor -3% trigger at ¥111.62 — only ¥2.38 away. Margin adding (+7.22% 5d) — leveraged buyers accumulating."
        },
        {
          "date": "2026-08-04",
          "price": 120.98,
          "change_pct": 5.14,
          "action": "HOLD",
          "note": "PnL+5.14%持仓5天。Sector元件#2（+8.45%）极强势。MLCC涨价核心受益标的（三星电机8/1+30%已生效，太阳诱电9/1跟进），今日+6.12%强势延续。止损修正：原¥103.45（-10.1%）违反Rule 5，新止损¥109.32（entry×0.95）。逼近+10%（¥126.58）→届时提至盈亏平衡¥115.07。"
        },
        {
          "date": "2026-08-05",
          "price": 129.99,
          "change_pct": 12.97,
          "action": "RAISE_STOP",
          "note": "PnL+12.97%持仓6天，Rule 5强制触发：+10%以上→止损提至盈亏平衡¥115.07。MLCC涨价核心受益标的（三星电机8/1+30%已生效），今日+7.45%强势。"
        }
      ]
    },
    {
      "code": "600885",
      "name": "宏发股份",
      "entryDate": "2026-08-04",
      "entryPrice": 35.75,
      "targetPrice": 42.0,
      "stopLoss": 33.96,
      "currentStop": 33.96,
      "thesis": "电网自动化设备龙头，0风险标签。今日发布H1半年报：营收+32.05%，净利11.56亿（+19.9%），业绩扎实。北向20%极高外资认可，股东户数-39%大资金吸筹。MA距离全部合规（dist_ma5+3.3%, dist_ma10+4.1%）。继电器+新能源+消费电子多线增长。",
      "sector": "电网设备",
      "rps120": 89.99,
      "catalysts": [],
      "shares": 1000,
      "allocation_pct": 5.0,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.5113,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 4.17,
        "pct_float": 0.74,
        "chg5_pct": -12.71,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      },
      "history": [
        {
          "date": "2026-08-04",
          "price": 35.75,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 宏发股份"
        },
        {
          "date": "2026-08-04",
          "price": 36.31,
          "change_pct": 1.57,
          "action": "HOLD",
          "note": "PnL+1.57%今日开仓。电网自动化龙头，0风险标签。H1半年报扎实：营收+32.05%，净利11.56亿（+19.9%）。北向20%极高外资认可，股东户数-39%大资金吸筹。Margin deleveraging（-16.3% 5d）需关注但不改持仓。"
        },
        {
          "date": "2026-08-05",
          "price": 36.85,
          "change_pct": 3.08,
          "action": "HOLD",
          "note": "PnL+3.08%持仓2天。H1半年报扎实（营收+32%净利+19.9%），0风险标签，北向20%+股东户数-39%。Margin deleveraging（-21.21% 5d）严重但公司基本面极强，不构成卖出。"
        }
      ]
    },
    {
      "code": "601168",
      "name": "西部矿业",
      "entryDate": "2026-08-05",
      "entryPrice": 40.64,
      "targetPrice": 46.0,
      "stopLoss": 38.61,
      "currentStop": 38.61,
      "thesis": "工业金属/铜龙头，0风险标签。H1净利+123%爆发力极强。Sector贵金属+6.21%/小金属+6.15%今日Top5共振，整个有色板块顺风。VCP SETUP形态（contraction=0.69, dist_peak=3.0%）。北向5.5%+公募6.4%+股东户数-30%+控股股东增持7.4亿。MA全部合规（dist_ma5=1.8%/ma10=2.5%/ma20=10.8%）。",
      "sector": "工业金属",
      "rps120": 88.43,
      "catalysts": [],
      "shares": 1100,
      "allocation_pct": 7.0,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.5113,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 19.46,
        "pct_float": 1.99,
        "chg5_pct": -4.2,
        "net5_repay_days": 2,
        "signal": "neutral"
      },
      "history": [
        {
          "date": "2026-08-05",
          "price": 40.64,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 西部矿业"
        }
      ]
    },
    {
      "code": "603127",
      "name": "昭衍新药",
      "entryDate": "2026-08-04",
      "entryPrice": 44.35,
      "targetPrice": 55.0,
      "stopLoss": 42.13,
      "currentStop": 42.13,
      "thesis": "CRO安评龙头，医疗服务sector#3（+7.51%），受益药明康德H1超预期带动板块情绪。实验猴供需持续紧张（猴价突破20万/只），公司拥有约2.5万只实验猴储备构成稀缺壁垒。H1预增归母净利6-9亿（+885~1377%）。RPS120=91.56%甜点位，MA距离全部合规。⚠️利润质量差（猴价重估驱动非经营改善）+毛利率49%→19%结构性下滑+margin deleveraging，故仅SMALL BUY 4%。",
      "sector": "医疗服务",
      "rps120": 91.56,
      "catalysts": [],
      "shares": 600,
      "allocation_pct": 4.0,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.5113,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 5.81,
        "pct_float": 2.0,
        "chg5_pct": -6.18,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      },
      "history": [
        {
          "date": "2026-08-04",
          "price": 44.35,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 昭衍新药"
        },
        {
          "date": "2026-08-05",
          "price": 46.0,
          "change_pct": 3.72,
          "action": "HOLD",
          "note": "PnL+3.72%持仓2天。CXO安评龙头，受益板块情绪扩散+实验猴稀缺。Margin deleveraging（-14.8% 5d）警示但不触发卖出。"
        }
      ]
    },
    {
      "code": "603259",
      "name": "药明康德",
      "entryDate": "2026-07-31",
      "entryPrice": 126.5,
      "targetPrice": 150.0,
      "stopLoss": 120.18,
      "currentStop": 126.5,
      "thesis": "CXO龙头，A/H溢价-8%(A股折价)。近3月涨幅超98%个股，强势动量。10亿回购+11%北向+15%公募。VCP SETUP：价格在MA5/MA10/MA20的1.5%范围内极致收敛，突破在即。8月4日中报发布（催化剂即将兑现）。零风险。唯一风险：医疗服务sector未进入今日top5，但大概率在top30%。",
      "sector": "医疗服务",
      "rps120": 90.81,
      "catalysts": [],
      "shares": 300,
      "allocation_pct": 5.0,
      "iv_proxy": {
        "primary_name": "50ETF",
        "iv_rank": 0.4441,
        "sizing": "normal"
      },
      "margin": {
        "rzye_yi": 50.96,
        "pct_float": 1.4,
        "chg5_pct": 1.47,
        "net5_repay_days": 3,
        "signal": "adding"
      },
      "history": [
        {
          "date": "2026-08-04",
          "price": 141.35,
          "change_pct": 11.74,
          "action": "RAISE_STOP",
          "note": "PnL+11.74%持仓4天，今日涨停+10.00%！中报催化兑现完美。Sector医疗服务#3（+6.89%）。按Rule 5：+10%以上→止损提至成本价。新止损¥126.50（盈亏平衡），确保此笔交易不再亏损。CXO龙头+A/H折价+10亿回购+0风险，继续持有让利润奔跑。"
        },
        {
          "date": "2026-08-04",
          "price": 141.35,
          "change_pct": 11.74,
          "action": "HOLD",
          "note": "PnL+11.74%持仓5天，今日涨停+10.00%！Sector医疗服务#3（+7.51%）。H1营收288.97亿（+38.93%），归母净利110.8亿（+29.43%），上调全年指引至585-605亿。止损已提至成本¥126.50（盈亏平衡），确保此笔不亏损。下一目标：+20%（¥151.80）→提止损至+10%（¥139.15）。"
        },
        {
          "date": "2026-08-05",
          "price": 146.94,
          "change_pct": 16.16,
          "action": "HOLD",
          "note": "PnL+16.16%持仓6天，中报催化完美兑现（H1营收+39%净利+29%，全年指引上调至585-605亿）。止损已提至成本¥126.50（盈亏平衡），确保此笔不亏损。下一目标+20%=¥151.80→届时提止损至+10%。Sector医疗服务受益CXO板块扩散。"
        }
      ]
    },
    {
      "code": "688981",
      "name": "中芯国际",
      "entryDate": "2026-08-05",
      "entryPrice": 121.1,
      "targetPrice": 145.0,
      "stopLoss": 115.04,
      "currentStop": 115.04,
      "thesis": "集成电路制造绝对龙头，0风险标签。科创50今日+5.18%极强势，半导体产业链全线上涨。在建工程20%产能大扩张周期，机构目标+41%。远低于各均线（dist_ma20=-16.8%）——非追涨而是抄回调。IV rank 75%偏紧但0风险+龙头地位满足仅选最强标的门槛。",
      "sector": "半导体",
      "rps120": 88.97,
      "catalysts": [],
      "shares": 200,
      "allocation_pct": 5.0,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.6829,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 110.21,
        "pct_float": 4.39,
        "chg5_pct": 1.58,
        "net5_repay_days": 3,
        "signal": "adding"
      },
      "history": [
        {
          "date": "2026-08-05",
          "price": 121.1,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 中芯国际"
        }
      ]
    }
  ],
  "position_prices": {
    "000703": {
      "code": "000703",
      "name": "恒逸石化",
      "date": "2026-08-06",
      "price": 17.12,
      "open": 16.3,
      "high": 17.29,
      "low": 16.24,
      "prev_close": 16.39,
      "change_pct": 4.45,
      "volume": 618380,
      "amount": 1045109018.74,
      "source": "sina",
      "mavol30": 8617.87,
      "volume_below_mavol30": false
    },
    "002138": {
      "code": "002138",
      "name": "顺络电子",
      "date": "2026-08-06",
      "price": 48.2,
      "open": 48.52,
      "high": 49.83,
      "low": 47.11,
      "prev_close": 49.6,
      "change_pct": -2.82,
      "volume": 250945,
      "amount": 1219120483.37,
      "source": "sina",
      "mavol30": 4228.47,
      "volume_below_mavol30": false
    },
    "300001": {
      "code": "300001",
      "name": "特锐德",
      "date": "2026-08-06",
      "price": 35.14,
      "open": 35.88,
      "high": 36.0,
      "low": 35.07,
      "prev_close": 35.82,
      "change_pct": -1.9,
      "volume": 110367,
      "amount": 389756537.6,
      "source": "sina",
      "mavol30": 2119.33,
      "volume_below_mavol30": false
    },
    "300408": {
      "code": "300408",
      "name": "三环集团",
      "date": "2026-08-06",
      "price": 124.15,
      "open": 124.0,
      "high": 129.65,
      "low": 120.8,
      "prev_close": 128.19,
      "change_pct": -3.15,
      "volume": 526169,
      "amount": 6592804137.79,
      "source": "sina",
      "mavol30": 6914.3,
      "volume_below_mavol30": false
    },
    "600885": {
      "code": "600885",
      "name": "宏发股份",
      "date": "2026-08-06",
      "price": 35.0,
      "open": 36.45,
      "high": 36.9,
      "low": 34.84,
      "prev_close": 36.3,
      "change_pct": -3.58,
      "volume": 154252,
      "amount": 551512270.0,
      "source": "sina",
      "mavol30": 1874.07,
      "volume_below_mavol30": false
    },
    "601168": {
      "code": "601168",
      "name": "西部矿业",
      "date": "2026-08-06",
      "price": 39.96,
      "open": 41.95,
      "high": 42.62,
      "low": 39.6,
      "prev_close": 41.02,
      "change_pct": -2.58,
      "volume": 778901,
      "amount": 3179885539.0,
      "source": "sina",
      "mavol30": 6101.43,
      "volume_below_mavol30": false
    },
    "603127": {
      "code": "603127",
      "name": "昭衍新药",
      "date": "2026-08-06",
      "price": 46.31,
      "open": 47.0,
      "high": 47.18,
      "low": 44.85,
      "prev_close": 46.3,
      "change_pct": 0.02,
      "volume": 299371,
      "amount": 1384018571.0,
      "source": "sina",
      "mavol30": 4898.03,
      "volume_below_mavol30": false
    },
    "603259": {
      "code": "603259",
      "name": "药明康德",
      "date": "2026-08-06",
      "price": 144.56,
      "open": 148.82,
      "high": 149.37,
      "low": 142.8,
      "prev_close": 147.5,
      "change_pct": -1.99,
      "volume": 466518,
      "amount": 6780418026.0,
      "source": "sina",
      "mavol30": 6269.17,
      "volume_below_mavol30": false
    },
    "688981": {
      "code": "688981",
      "name": "中芯国际",
      "date": "2026-08-06",
      "price": 124.18,
      "open": 122.0,
      "high": 126.99,
      "low": 121.88,
      "prev_close": 125.45,
      "change_pct": -1.01,
      "volume": 340079,
      "amount": 4226808707.0,
      "source": "sina",
      "mavol30": 7913.13,
      "volume_below_mavol30": false
    }
  },
  "missed_opportunity_prices": [
    {
      "code": "688777",
      "name": "中控技术",
      "recommended_date": "2026-08-05",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 103.22,
      "return_pct": null
    },
    {
      "code": "603156",
      "name": "养元饮品",
      "recommended_date": "2026-08-05",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 46.0,
      "return_pct": null
    },
    {
      "code": "000739",
      "name": "普洛药业",
      "recommended_date": "2026-08-05",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 21.74,
      "return_pct": null
    },
    {
      "code": "300503",
      "name": "昊志机电",
      "recommended_date": "2026-08-05",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 71.88,
      "return_pct": null
    },
    {
      "code": "002384",
      "name": "东山精密",
      "recommended_date": "2026-08-05",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 188.06,
      "return_pct": null
    },
    {
      "code": "688498",
      "name": "源杰科技",
      "recommended_date": "2026-08-05",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 1334.89,
      "return_pct": null
    },
    {
      "code": "603162",
      "name": "海通发展",
      "recommended_date": "2026-08-05",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 11.53,
      "return_pct": null
    },
    {
      "code": "002440",
      "name": "闰土股份",
      "recommended_date": "2026-08-05",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 13.1,
      "return_pct": null
    },
    {
      "code": "000977",
      "name": "浪潮信息",
      "recommended_date": "2026-08-05",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 75.95,
      "return_pct": null
    },
    {
      "code": "002056",
      "name": "横店东磁",
      "recommended_date": "2026-08-05",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 21.49,
      "return_pct": null
    },
    {
      "code": "601168",
      "name": "西部矿业",
      "recommended_date": "2026-08-04",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 39.96,
      "return_pct": null
    },
    {
      "code": "688008",
      "name": "澜起科技",
      "recommended_date": "2026-08-04",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 207.35,
      "return_pct": null
    },
    {
      "code": "000725",
      "name": "京东方A",
      "recommended_date": "2026-08-04",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 5.92,
      "return_pct": null
    },
    {
      "code": "002203",
      "name": "海亮股份",
      "recommended_date": "2026-08-04",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 18.97,
      "return_pct": null
    },
    {
      "code": "600885",
      "name": "宏发股份",
      "recommended_date": "2026-08-03",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 35.0,
      "return_pct": null
    },
    {
      "code": "688981",
      "name": "中芯国际",
      "recommended_date": "2026-08-03",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 124.18,
      "return_pct": null
    },
    {
      "code": "688041",
      "name": "海光信息",
      "recommended_date": "2026-08-03",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 288.65,
      "return_pct": null
    },
    {
      "code": "688146",
      "name": "中船特气",
      "recommended_date": "2026-08-03",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 307.36,
      "return_pct": null
    },
    {
      "code": "600428",
      "name": "中远海特",
      "recommended_date": "2026-08-03",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 11.93,
      "return_pct": null
    },
    {
      "code": "300001",
      "name": "特锐德",
      "recommended_date": "2026-08-03",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 35.14,
      "return_pct": null
    }
  ],
  "iv_sentiment": {
    "date": "2026-08-06",
    "source": "options-learn backend (/api/history/iv-rank)",
    "core_underlyings": [
      "510050",
      "510300",
      "510500",
      "588000",
      "159915"
    ],
    "etf_iv_data": [
      {
        "underlying": "510050",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 217,
        "current_iv": 0.1641,
        "is_live": false,
        "iv_high": 0.2272,
        "iv_low": 0.1137,
        "iv_high_raw": 0.2625,
        "iv_low_raw": 0.1137,
        "iv_rank": 0.4441,
        "iv_rank_raw": 0.3387,
        "iv_percentile": 0.5207,
        "iv_percentile_raw": 0.5022,
        "outliers_removed": 8,
        "outlier_details": [
          {
            "date": "2025-08-25",
            "iv": 0.2287
          },
          {
            "date": "2025-08-28",
            "iv": 0.2286
          },
          {
            "date": "2026-02-02",
            "iv": 0.2471
          },
          {
            "date": "2026-03-23",
            "iv": 0.2291
          },
          {
            "date": "2026-06-23",
            "iv": 0.2503
          },
          {
            "date": "2026-07-17",
            "iv": 0.2443
          },
          {
            "date": "2026-07-20",
            "iv": 0.2333
          },
          {
            "date": "2026-07-22",
            "iv": 0.2625
          }
        ],
        "sigma_range": [
          0.1047,
          0.2281
        ],
        "name": "50ETF",
        "desc": "大盘蓝筹",
        "interpretation": "中性"
      },
      {
        "underlying": "510300",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 218,
        "current_iv": 0.1853,
        "is_live": false,
        "iv_high": 0.2476,
        "iv_low": 0.1201,
        "iv_high_raw": 0.3137,
        "iv_low_raw": 0.069,
        "iv_rank": 0.5113,
        "iv_rank_raw": 0.4753,
        "iv_percentile": 0.5872,
        "iv_percentile_raw": 0.5778,
        "outliers_removed": 7,
        "outlier_details": [
          {
            "date": "2025-08-15",
            "iv": 0.2599
          },
          {
            "date": "2025-08-18",
            "iv": 0.2694
          },
          {
            "date": "2025-08-20",
            "iv": 0.255
          },
          {
            "date": "2026-04-16",
            "iv": 0.069
          },
          {
            "date": "2026-04-17",
            "iv": 0.099
          },
          {
            "date": "2026-07-17",
            "iv": 0.3137
          },
          {
            "date": "2026-07-20",
            "iv": 0.2708
          }
        ],
        "sigma_range": [
          0.1094,
          0.2487
        ],
        "name": "300ETF",
        "desc": "沪深300",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "510500",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 216,
        "current_iv": 0.2778,
        "is_live": false,
        "iv_high": 0.3575,
        "iv_low": 0.194,
        "iv_high_raw": 0.4544,
        "iv_low_raw": 0.107,
        "iv_rank": 0.5125,
        "iv_rank_raw": 0.4917,
        "iv_percentile": 0.7037,
        "iv_percentile_raw": 0.6844,
        "outliers_removed": 9,
        "outlier_details": [
          {
            "date": "2025-08-18",
            "iv": 0.3616
          },
          {
            "date": "2025-08-25",
            "iv": 0.3612
          },
          {
            "date": "2025-09-04",
            "iv": 0.3769
          },
          {
            "date": "2026-04-16",
            "iv": 0.128
          },
          {
            "date": "2026-04-17",
            "iv": 0.107
          },
          {
            "date": "2026-07-17",
            "iv": 0.3612
          },
          {
            "date": "2026-07-20",
            "iv": 0.4544
          },
          {
            "date": "2026-07-21",
            "iv": 0.3659
          },
          {
            "date": "2026-07-30",
            "iv": 0.3886
          }
        ],
        "sigma_range": [
          0.1741,
          0.3594
        ],
        "name": "500ETF",
        "desc": "中证500",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "588000",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 217,
        "current_iv": 0.5115,
        "is_live": false,
        "iv_high": 0.6345,
        "iv_low": 0.2467,
        "iv_high_raw": 0.7788,
        "iv_low_raw": 0.126,
        "iv_rank": 0.6829,
        "iv_rank_raw": 0.5905,
        "iv_percentile": 0.7742,
        "iv_percentile_raw": 0.7556,
        "outliers_removed": 8,
        "outlier_details": [
          {
            "date": "2026-04-16",
            "iv": 0.145
          },
          {
            "date": "2026-04-17",
            "iv": 0.126
          },
          {
            "date": "2026-07-16",
            "iv": 0.6732
          },
          {
            "date": "2026-07-17",
            "iv": 0.7362
          },
          {
            "date": "2026-07-20",
            "iv": 0.7293
          },
          {
            "date": "2026-07-21",
            "iv": 0.7006
          },
          {
            "date": "2026-07-22",
            "iv": 0.7788
          },
          {
            "date": "2026-07-30",
            "iv": 0.6685
          }
        ],
        "sigma_range": [
          0.1586,
          0.6417
        ],
        "name": "科创50",
        "desc": "科创板",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "159915",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 218,
        "current_iv": 0.4021,
        "is_live": false,
        "iv_high": 0.4913,
        "iv_low": 0.2082,
        "iv_high_raw": 0.6363,
        "iv_low_raw": 0.2082,
        "iv_rank": 0.685,
        "iv_rank_raw": 0.453,
        "iv_percentile": 0.7523,
        "iv_percentile_raw": 0.7387,
        "outliers_removed": 4,
        "outlier_details": [
          {
            "date": "2025-09-05",
            "iv": 0.5002
          },
          {
            "date": "2026-07-17",
            "iv": 0.5958
          },
          {
            "date": "2026-07-20",
            "iv": 0.6363
          },
          {
            "date": "2026-07-30",
            "iv": 0.5331
          }
        ],
        "sigma_range": [
          0.1764,
          0.494
        ],
        "name": "创业板ETF",
        "desc": "创业板",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "159922",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 213,
        "current_iv": 0.2834,
        "is_live": false,
        "iv_high": 0.352,
        "iv_low": 0.1804,
        "iv_high_raw": 0.468,
        "iv_low_raw": 0.1804,
        "iv_rank": 0.6005,
        "iv_rank_raw": 0.3582,
        "iv_percentile": 0.7324,
        "iv_percentile_raw": 0.7027,
        "outliers_removed": 9,
        "outlier_details": [
          {
            "date": "2025-09-04",
            "iv": 0.3669
          },
          {
            "date": "2025-09-18",
            "iv": 0.361
          },
          {
            "date": "2025-09-19",
            "iv": 0.3533
          },
          {
            "date": "2026-03-23",
            "iv": 0.361
          },
          {
            "date": "2026-07-17",
            "iv": 0.36
          },
          {
            "date": "2026-07-20",
            "iv": 0.468
          },
          {
            "date": "2026-07-21",
            "iv": 0.3716
          },
          {
            "date": "2026-07-22",
            "iv": 0.4068
          },
          {
            "date": "2026-07-30",
            "iv": 0.3904
          }
        ],
        "sigma_range": [
          0.1797,
          0.352
        ],
        "name": "500ETF深",
        "desc": "深市中盘",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "159919",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 215,
        "current_iv": 0.1887,
        "is_live": false,
        "iv_high": 0.2577,
        "iv_low": 0.1298,
        "iv_high_raw": 0.3431,
        "iv_low_raw": 0.1298,
        "iv_rank": 0.4607,
        "iv_rank_raw": 0.2762,
        "iv_percentile": 0.6186,
        "iv_percentile_raw": 0.5991,
        "outliers_removed": 7,
        "outlier_details": [
          {
            "date": "2025-08-18",
            "iv": 0.2642
          },
          {
            "date": "2025-08-20",
            "iv": 0.2681
          },
          {
            "date": "2025-08-25",
            "iv": 0.258
          },
          {
            "date": "2026-06-23",
            "iv": 0.2815
          },
          {
            "date": "2026-07-17",
            "iv": 0.3036
          },
          {
            "date": "2026-07-20",
            "iv": 0.2755
          },
          {
            "date": "2026-07-22",
            "iv": 0.3431
          }
        ],
        "sigma_range": [
          0.1119,
          0.2578
        ],
        "name": "300ETF深",
        "desc": "深市宽基",
        "interpretation": "中性"
      },
      {
        "underlying": "159901",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 217,
        "current_iv": 0.2875,
        "is_live": false,
        "iv_high": 0.3406,
        "iv_low": 0.1682,
        "iv_high_raw": 0.4504,
        "iv_low_raw": 0.1682,
        "iv_rank": 0.6921,
        "iv_rank_raw": 0.4227,
        "iv_percentile": 0.8065,
        "iv_percentile_raw": 0.7883,
        "outliers_removed": 5,
        "outlier_details": [
          {
            "date": "2025-08-20",
            "iv": 0.3484
          },
          {
            "date": "2026-07-17",
            "iv": 0.4504
          },
          {
            "date": "2026-07-20",
            "iv": 0.4064
          },
          {
            "date": "2026-07-21",
            "iv": 0.3723
          },
          {
            "date": "2026-07-22",
            "iv": 0.3521
          }
        ],
        "sigma_range": [
          0.1458,
          0.3432
        ],
        "name": "深100ETF",
        "desc": "深市蓝筹",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "588080",
        "lookback_days": 252,
        "data_points": 224,
        "data_points_filtered": 217,
        "current_iv": 0.5154,
        "is_live": false,
        "iv_high": 0.6248,
        "iv_low": 0.184,
        "iv_high_raw": 0.756,
        "iv_low_raw": 0.184,
        "iv_rank": 0.7518,
        "iv_rank_raw": 0.5794,
        "iv_percentile": 0.8249,
        "iv_percentile_raw": 0.7991,
        "outliers_removed": 7,
        "outlier_details": [
          {
            "date": "2026-07-15",
            "iv": 0.6485
          },
          {
            "date": "2026-07-16",
            "iv": 0.676
          },
          {
            "date": "2026-07-17",
            "iv": 0.7362
          },
          {
            "date": "2026-07-20",
            "iv": 0.7044
          },
          {
            "date": "2026-07-21",
            "iv": 0.6686
          },
          {
            "date": "2026-07-22",
            "iv": 0.756
          },
          {
            "date": "2026-07-30",
            "iv": 0.6632
          }
        ],
        "sigma_range": [
          0.1619,
          0.6373
        ],
        "name": "科创板50",
        "desc": "科创板（备用代理）",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      }
    ],
    "overall_sentiment": {
      "signal": "偏悲观",
      "avg_iv_rank": 0.5672,
      "avg_iv_percentile": 0.6676,
      "implication": "波动率偏高，市场存在恐慌情绪。可能临近底部区域，但不排除继续下跌。",
      "based_on": [
        "510050",
        "510300",
        "510500",
        "588000",
        "159915"
      ]
    }
  },
  "entry_regime": {
    "allow_new_positions": true,
    "regime": "weak",
    "breadth_ratio": 0.4634,
    "up": 1717,
    "down": 3705,
    "positive_indices": [
      "上证指数"
    ],
    "negative_indices": [
      "深证成指",
      "创业板指"
    ],
    "limit_ups": 58,
    "limit_downs": 1,
    "sizing_multiplier": 0.5,
    "hard_block": false,
    "reason": "Entry regime weak: breadth 0.46:1, 1/3 major indices green, 58 limit-ups / 1 limit-downs. Allow entries only with 50% sizing."
  },
  "rule_violations": {
    "status": "violations",
    "total_rules": 6,
    "total_violations": 3,
    "rules": [
      {
        "rule": "check_breakout_failure",
        "file": "scripts/rules/check_breakout_failure.py",
        "status": "ok",
        "exit_code": 0,
        "violations": [],
        "error": null
      },
      {
        "rule": "check_iv_filter",
        "file": "scripts/rules/check_iv_filter.py",
        "status": "ok",
        "exit_code": 0,
        "violations": [],
        "error": null
      },
      {
        "rule": "check_overextended_entry",
        "file": "scripts/rules/check_overextended_entry.py",
        "status": "ok",
        "exit_code": 0,
        "violations": [],
        "error": null
      },
      {
        "rule": "check_stop_proximity",
        "file": "scripts/rules/check_stop_proximity.py",
        "status": "violations",
        "exit_code": 1,
        "violations": [
          {
            "code": "300001",
            "name": "特锐德",
            "rule": "stop_proximity",
            "severity": "WATCH",
            "currentPrice": 35.14,
            "stopLoss": 33.88,
            "distance_pct": 3.59,
            "suggestion": "🟠 WATCH — 3.6% above stop. Monitor closely. No immediate action but be ready."
          },
          {
            "code": "600885",
            "name": "宏发股份",
            "rule": "stop_proximity",
            "severity": "WARNING",
            "currentPrice": 35.0,
            "stopLoss": 33.96,
            "distance_pct": 2.97,
            "suggestion": "🟡 WARNING — only 3.0% above stop. Prepare sell order. If market opens weak tomorrow, may gap through stop."
          },
          {
            "code": "601168",
            "name": "西部矿业",
            "rule": "stop_proximity",
            "severity": "WATCH",
            "currentPrice": 39.96,
            "stopLoss": 38.61,
            "distance_pct": 3.38,
            "suggestion": "🟠 WATCH — 3.4% above stop. Monitor closely. No immediate action but be ready."
          }
        ],
        "error": null
      },
      {
        "rule": "check_time_decay",
        "file": "scripts/rules/check_time_decay.py",
        "status": "ok",
        "exit_code": 0,
        "violations": [],
        "error": null
      },
      {
        "rule": "check_volume_below_mavol30",
        "file": "scripts/rules/check_volume_below_mavol30.py",
        "status": "ok",
        "exit_code": 0,
        "violations": [],
        "error": null
      }
    ]
  },
  "collection_errors": [],
  "active_learnings": "## Active Rules (proven, hitRate ≥ 75%)\n- [h013] Strong breadth alone is not enough to force entries; without candidate RPS and MA-distance data, the correct momentum decision is to keep cash. (hitRate: 99%, n=131, confidence: 98%)\n- [h019] Bottom-list sectors should be treated as hard no-buy zones even when individual names still carry acceptable RPS readings. (hitRate: 100%, n=56, confidence: 98%)\n- [h028] Today’s relative leaders are concentrated in communication equipment and adjacent tech hardware, while cyclicals/agri/resource laggards are being de-risked aggressively. (hitRate: 100%, n=51, confidence: 98%)\n- [h027] MA-distance discipline remains critical inside hot sectors: a hot sector does not override chase risk when dist_ma5_pct exceeds 6% or dist_ma10_pct exceeds 8%. (hitRate: 100%, n=44, confidence: 98%)\n- [h023] Raising stops mechanically after +10% works well in weak tapes because it converts a fast winner into a low-risk hold without needing a fresh market call. (hitRate: 100%, n=36, confidence: 97%)\n- [h021] The MA-distance anti-chase rule is doing real work: several visually strong names fail because they are too far above short-term support. (hitRate: 98%, n=104, confidence: 97%)\n- [h077] The hard block is preventing FOMO entries. 新宙邦 (宁德时代协议 catalyst, VCP SETUP) and 奥来德 (dist_ma5 0.3%) would have been tempting buys in V1. V2 correctly forces cash preservation in panic regime. (hitRate: 100%, n=17, confidence: 95%)\n- [h017] Low-IV conditions around 16-22% IV rank do not justify freezing risk when breadth is 5.6:1; they argue for normal sizing but tighter discipline on chasing. (hitRate: 97%, n=29, confidence: 94%)\n- [h024] Stop-proximity violations deserve proactive action before the hard stop is hit, especially in 科创板 names where gap risk can erase the remaining cushion quickly. (hitRate: 91%, n=11, confidence: 85%)\n",
  "learnings_excerpt": "# 📚 LEARNINGS.md - 自我改进记录\n\n*最后更新: 2026-03-06*\n\n## 🎯 使用说明\n\n每日报告前，阅读本文件回顾历史教训。\n每日报告后，更新预测记录。\n每周日，进行准确率回顾并更新策略。\n\n---\n\n## 📊 预测追踪\n\n预测记录保存在 `predictions/` 目录，格式为 `YYYY-MM-DD.json`\n\n### 追踪指标\n- **推荐股票3日涨跌幅** - 核心指标\n- **推荐股票7日涨跌幅** - 中期验证\n- **回避股票后续表现** - 验证风险判断\n- **市场判断准确性** - 观望/积极的择时\n\n### 评分标准\n| 结果 | 得分 | 说明 |\n|------|------|------|\n| ⭐⭐⭐推荐 3日涨>3% | +2 | 强推成功 |\n| ⭐⭐⭐推荐 3日涨0-3% | +1 | 强推一般 |\n| ⭐⭐⭐推荐 3日跌<-3% | -2 | 强推失败 |\n| 回避股票 3日跌>3% | +1 | 风险判断正确 |\n| 回避股票 3日涨>5% | -1 | 错过机会 |\n\n---\n\n## 📈 历史准确率\n\n| 周期 | 强推胜率 | 回避准确率 | 总分 | 备注 |\n|------|----------|------------|------|------|\n| 2026-W05 | - | - | - | 首周，暂无数据 |\n| 2026-W06 | 0/2 (0%) | 1/1 (100%) | - | 600988/688002开仓，首周均浮亏 |\n| 2026-W07 | 2/4 (50%) | 1/1 (100%) | - | 300684表现突出+3.61%，新开300373 |\n| 2026-W08 | - | - | - | 春节假期(02-14~02-23) |\n| 2026-W09 | 2/6 (33%) | 1/1 (100%) | - | 6持仓(全盈)均PnL+1.97%，新开科达/云天化，中石科技本周+9.52pp最佳，赤峰黄金18天接近时间止损 |\n| 2026-W10 | 0/2 (0%) | 1/1 (100%) | - | 灾难性一周：03-03系统性暴跌6持仓全亏，03-03平仓扬杰(-8.21%)+芯碁(-7.50%)，03-04平仓睿创(-4.76%)，组合从+2%跌至-2.72%。3只活跃持仓全部浮亏。规则进化：新增iv_filter+breakout_failure规则 |\n\n---\n\n## 🧠 策略教训\n\n### ✅ 有效策略\n\n1. **[W07验证] RPS 80-92%区间选股有效** — 4只持仓RPS均在88-91%区间，其中300684(RPS91.2%)本周+3.61%表现最佳。初步验证该区间选股逻辑成立。\n2. **[W07新发现] 业绩催化+高confidence信号质量高** — 300684中石科技(业绩预告+64-84%，8亮点0风险)连续3日获BUY/high推荐，开仓后4天即+3.61%，是组合最佳。决策质量高。\n3. **[W07新发现] 严格止损纪律保护资金** — 600988赤峰黄金在02-05跌至36.68(距止损36.00仅1.9%)但未触及，之后反弹至38.26(+4.02%)再回落。止损线设在合理位置，避免了提前止损的踏空。\n4. **[W07新发现] 跳过RPS>92%的股票是正确的** — 02-10跳过了大金重工(RPS=95.4%)，严格执行规则，避免追高风险。\n\n### ❌ 失败教训\n\n1. **[W06-W07] 黄金股持仓时间过长，回撤大** — 600988赤峰黄金持仓11天仍-6.06%，期间最大浮亏-7.79%。金价波动带来的回撤显著，且持仓期间watchlist评级已降为WATCH。教训：当watchlist评级从BUY降至WATCH时，应考虑减仓或收紧止损。\n   - ⚡ **W10更新**: 赤峰黄金最终因time_decay规则于02-27平仓@+0.50%，但03-02涨停+9.99%至¥43.91(如持有+10.39%)。**此教训需修正**：黄金股波动大不等于应该更早退出——相反，thesis有效时应更有耐心。真正的问题是time_decay规则对事件驱动型标的不够灵活。\n2. **[W06-W07] 688002睿创微纳横盘11天无方向** — 持仓11天PnL在-1.35%到+0.72%之间反复，无明显趋势。高RPS(89.2%)但缺乏短期催化剂的股票可能需要更长时间才能兑现。教训：无近期催化剂的标的应适当降低仓位预期。\n   - ⚡ **W10更新**: 睿创微纳持仓19天后终于突破¥120关口，PnL达+4.75%。耐心持有得到回报，验证了假设15(催化发酵期可能>10天)。\n3. **[W10] 赤峰黄金time_decay平仓错失涨停 — 最大\"卖早了\"错误** — 持仓24天PnL仅+0.50%触发time_decay，02-27平仓。3天后(03-02)中东冲突推高金价→涨停+9.99%。错失+9.89pp收益。**核心教训**: 机械性时间止损不适用于事件驱动型标的(黄金/大宗)，需增加催化剂例外条款。详见专项复盘。\n\n### 🔄 待验证假设\n1. ~~RPS120在80-92%区间的股票胜率更高~~ → **初步验证有效**(4/4持仓在此区间，2盈利1亏1持平)→ **持续验证**(5/5新持仓均在此区间,科达制造87.2%入场)\n2. 恐慌日(跌停>50家)次日反弹概率高 — 暂无数据\n3. 风险数≤1的股票回撤更小 — **初步验证**(300684 0风险→+3.61%→现+1.86%,300373 0风险→+4.65%)\n4. **[新假设] 有明确业绩催化的股票3-5日涨幅优于纯概念票** — 300684业绩预告催化 +1.86%(持仓中), 300373涨价催化+4.65%\n5. ~~**持仓超10天仍在成本附近(±2%)的标的应重新评估thesis**~~ → **部分验证**: 688002睿创微纳持仓22天仅+0.25%,赤峰黄金持仓22天-1.36%,均需重新评估\n6. **[W08假设] low confidence推荐中也有大牛股** — 中材科技(low)+34%，大族激光(low)+19.89%，华懋科技(low/02-13)+9.2%。**再次验证有效**，3/3 low confidence显著错过\n7. **[W08假设] 行业供需拐点催化>个股亮点数量** — 电子布缺货带动中材科技+34%，远超大多数高亮点个股\n8. **[W08假设] 大额回购(>5%股本)是2周内+10%的强信号** — 华懋科技8亿回购后+14%(截至02-25仍在高位¥85.38)\n9. **[W09新假设] 连续3期以上出现在watchlist的股票有更高胜率** — 科达制造(4期)终于入场,华懋科技(4期)持续上涨。假设：多次入选说明基本面持续达标，是强信号\n10. **[W09假设→验证中] 当日涨幅>8%的BUY推荐应跳过，等回调后再评估** — 云天化02-25 BUY但已+9.10%跳过→02-26入场(多付2.6%但安全) ✅ **已验证**。芯碁微装02-26 BUY +7.99%跳过→02-27 -1.65%回调至¥199(目标¥195距3.4%) **初步验证有效** — 不追高是对的\n11. **[W09新假设] 海外龙头财报日是A股硬件链的超级催化事件** — 英伟达02-26业绩后PCB/光纤/散热/光刻全链条爆发(5+只股涨停)，应提前布局受益标的\n12. **[W09假设→待验证] 超强业绩催化(净利增速>200%)可以覆盖\"追高\"风险** — 芯碁微装Q4净利+1522%，02-26 +7.99%→02-27 -1.65%回调中，尚未到目标¥195。两日累计+6.3%仍高于入场点。待继续跟踪\n13. **[W09教训] 单日涨幅规则不够，需检查多日累计涨幅和均线偏离** — 云天化02-26入场@¥44.05，但近3日累计涨幅~15%，远超MA10。单日+1.96%看似\"回归正常\"，但股价已严重超买。**新规则**: 入场前必须检查 (a) 近5日累计涨幅，>12%则等回调 (b) 与MA10偏离度，>10%则等回调。两者满足任一即跳过。不要被\"今天只涨了一点\"骗了，要看完整图形。\n14. **[W09新假设] 0风险标的的RPS容忍度可放宽至95%** — 常宝股份RPS=94.3%被降级跳过，但0风险+6亮点，结果+29.3%。华锐精密虽有风险但0风险标的特别：无风险=抗跌能力强，追高风险更低。待更多样本验证\n15. **[W09新假设] 催化发酵期可能>10个交易日** — 铂力特02-04 WATCH @¥105.13，前18个交易日回报-2.7%，但02-27已+8.4%。一些国产替代/军工标的需要更长的催化酝酿期，不应因短期无方向就放弃跟踪。⚡ **W10进一步验证**: 睿创微纳横盘19天后突破+4.75%；赤峰黄金如果多等3天就有+10.39%。**两个案例都说明耐心的价值远超time_decay的效率诉求**\n16. **[W10新假设] 标的应分类为\"趋势型\"和\"事件驱动型\"，适用不同退出规则** — 趋势型(如中石科技、扬杰科技)：RPS+业绩驱动，适合time_decay规则。事件驱动型(如赤峰黄金、大宗商品)：受地缘/供需事件脉冲驱动，PnL波动大但爆发力强。两者不应用同一套时间止损参数。黄金/石油/稀土等大宗商品标的建议归为\"事件驱动型\"\n17. **[W10验证] 03-03系统性暴跌验证了多条规则的失效和有效** — 6持仓同日全亏(-6%~-8%)，扬杰科技(-8.37%)和芯碁微装(-7.89%)被止损。stop_proximity规则03-03当日正确触发2次(扬杰1.8%+芯碁2.1%)，proactive止损避免了更大损失。✅ **已验证**: stop_proximity规则是组合最有价值的防御规则。\n18. **[W10核心教训] 突破失败是加速退出信号** — 睿创微纳03-02突破¥120(+4.75%)，03-04跌至¥109(-4.76%)，2天回撤9.5pp。**新规则(已实施)**: check_breakout_failure规则检测持仓>10天+PnL<-3%的\"曾经盈利现在亏损\"模式。突破失败比time_decay更紧急。\n19. **[W10核心教训] IV极低+短期涨幅已大=最差入场时机** — 芯碁微装03-02入场(IVRank~12%, 5日涨幅~8.2%)，次日-7.89%。**新规则(已实施)**: check_iv_filter规则标记开仓5天内即亏>4%的持仓，提示入场质量问题。**建议**: IVRank<15%且5日涨幅>6%时一律WATCH等回调。\n20. **[W10假设→验证失败] 超强业绩催化可以覆盖追高风险** — 芯碁微装Q4净利+1522%是历史级催化，03-02入场@¥201.72仍亏-7.5%止损。**结论**: 即使催化再强，市场环境(IV极低+系统性回调)才是决定短期走势的主导因素。催化剂决定方向，但市场环境决定时机。❌ **假设#12被否定**。\n\n---\n\n## 🔍 错过的机会 (截至 2026-03-02)\n\n### 📌 本次更新 (2026-03-02 周一 W10首日)\n\n**分析范围**: 全量未入场推荐价格更新(03-02收盘价) + 持仓状态更新\n\n#### 全量未入场推荐最新涨跌幅 (03-02收盘)\n\n| 股票 | 推荐日 | 推荐价 | 上次价(02-27) | 今日价(03-02) | 累计涨幅 | 周变化 |\n|------|--------|--------|--------------|--------------|---------|--------|\n| 002008 大族激光 | 02-05 | ¥49.18 | ¥72.30 | **¥74.62** | **+51.7%** 🔥🔥🔥 | +3.2%↑ |\n| 002080 中材科技 | 02-05 | ¥38.65 | ¥50.63 | **¥50.84** | **+31.5%** 🔥🔥🔥 | +0.4%↑ |\n| 002478 常宝股份 | 02-10 | ¥10.46 | ¥13.53 | **¥13.00** | **+24.3%** 🔥🔥 | -3.9%↓ 回调 |\n\n[... truncated, see hypothesis system for active rules ...]"
}
```

请根据以上数据进行分析，按照 Required Output JSON 格式返回你的决策。

重要提醒：请再次仔细阅读以上所有数据（特别是 enriched_candidates 中的详细指标、position_prices 中的实时价格、以及 iv_sentiment），严格按照 ANALYST.md 的5条规则和 Output Format 要求，返回完整的 JSON 决策。skip_list 中只能引用输入数据中实际存在的价格和指标，不要编造任何数据。

**new_learnings 格式更新**: 尽量使用结构化格式返回 new_learnings：
```json
"new_learnings": [
  {
    "text": "具体、可操作的洞察",
    "type": "heuristic|signal|rule|observation",
    "tags": ["sector", "entry-filter", "exit-rule", "timing", "position-sizing"],
    "evidence_type": "supporting|contradicting",
    "related_hypothesis": "h001 (如果是对已有假设的新证据)",
    "mechanism": "为什么这个规律成立的解释"
  }
]
```
也接受纯字符串格式(向后兼容)。如果 active_learnings 中有相关假设，请引用其 ID。
