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
    "Specific, actionable insight from today's analysis"
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
  "date": "2026-08-03",
  "portfolio": {
    "startingCapital": 1000000,
    "totalEquity": 937659.0,
    "cash": 743396.0,
    "investedValue": 194263.0,
    "unrealizedPnl": -3564.0,
    "realizedPnl": -58777.0,
    "totalPnl": -62341.0,
    "totalReturnPct": -6.23,
    "positionsUsed": 5,
    "positionsMax": 10,
    "cashPct": 79.28,
    "dayPnl": -1386.0,
    "minCashPct": 0,
    "minCashValue": 0.0,
    "deployableCash": 743396.0
  },
  "market": {
    "timestamp": "2026-08-03T11:35:52.509500",
    "indices": {
      "上证指数": {
        "code": "sh000001",
        "close": 3809.645,
        "change_pct": -0.59,
        "date": "2026-08-03"
      },
      "深证成指": {
        "code": "sz399001",
        "close": 13517.62,
        "change_pct": -0.45,
        "date": "2026-08-03"
      },
      "创业板指": {
        "code": "sz399006",
        "close": 3329.13,
        "change_pct": -0.44,
        "date": "2026-08-03"
      },
      "科创50": {
        "code": "sh000688",
        "close": 1575.008,
        "change_pct": -3.73,
        "date": "2026-08-03"
      }
    },
    "breadth": {
      "up": 3717,
      "down": 1690,
      "flat": 122,
      "total": 5529,
      "distribution": {
        "f10": 3,
        "f7_10": 63,
        "f4_7": 204,
        "f2_4": 397,
        "f0_2": 1023,
        "f0": 122,
        "r0_2": 2394,
        "r2_4": 962,
        "r4_7": 231,
        "r7_10": 64,
        "r10": 66
      }
    },
    "sectors": {
      "top5": [
        {
          "板块名称": "电机Ⅱ",
          "涨跌幅": 4.11
        },
        {
          "板块名称": "航天装备Ⅱ",
          "涨跌幅": 3.24
        },
        {
          "板块名称": "风电设备",
          "涨跌幅": 3.04
        },
        {
          "板块名称": "环保设备Ⅱ",
          "涨跌幅": 2.74
        },
        {
          "板块名称": "林业Ⅱ",
          "涨跌幅": 2.69
        }
      ],
      "bottom5": [
        {
          "板块名称": "玻璃玻纤",
          "涨跌幅": -6.22
        },
        {
          "板块名称": "半导体",
          "涨跌幅": -4.48
        },
        {
          "板块名称": "电子化学品Ⅱ",
          "涨跌幅": -4.12
        },
        {
          "板块名称": "医疗美容",
          "涨跌幅": -2.34
        },
        {
          "板块名称": "非金属材料Ⅱ",
          "涨跌幅": -2.12
        }
      ]
    }
  },
  "strategy_pool": {
    "source": "cheesefortune_intersection",
    "total_stocks": 68,
    "stocks": [
      {
        "code": "688146",
        "code_full": "688146.SH",
        "name": "中船特气",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1408.2353,
        "pe": 3.2,
        "risks_count": 3,
        "rps20": null,
        "rps60": 99.98,
        "rps120": 100.0,
        "rps250": 99.96,
        "ma10": 249.6,
        "vcp_quality": null,
        "ma5": 282.51,
        "ma20": 268.76,
        "dist_ma5_pct": -5.8,
        "dist_ma10_pct": 6.6,
        "dist_ma20_pct": -1.0
      },
      {
        "code": "002980",
        "code_full": "002980.SZ",
        "name": "华盛昌",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 125.4972,
        "pe": 6.3,
        "risks_count": 2,
        "rps20": 13.38,
        "rps60": 87.01,
        "rps120": 99.88,
        "rps250": 99.04,
        "ma10": 79.43,
        "vcp_quality": null,
        "ma5": 72.19,
        "ma20": 89.93,
        "dist_ma5_pct": -8.2,
        "dist_ma10_pct": -16.6,
        "dist_ma20_pct": -26.3
      },
      {
        "code": "002384",
        "code_full": "002384.SZ",
        "name": "东山精密",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 3140.8406,
        "pe": 16.3,
        "risks_count": 2,
        "rps20": 25.31,
        "rps60": 91.84,
        "rps120": 99.65,
        "rps250": 98.98,
        "ma10": 198.77,
        "vcp_quality": null,
        "ma5": 183.13,
        "ma20": 222.66,
        "dist_ma5_pct": -6.4,
        "dist_ma10_pct": -13.7,
        "dist_ma20_pct": -23.0
      },
      {
        "code": "002281",
        "code_full": "002281.SZ",
        "name": "光迅科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1338.2176,
        "pe": 16.9,
        "risks_count": 1,
        "rps20": 16.11,
        "rps60": 97.15,
        "rps120": 99.53,
        "rps250": 98.86,
        "ma10": 177.63,
        "vcp_quality": null,
        "ma5": 169.93,
        "ma20": 199.22,
        "dist_ma5_pct": -4.9,
        "dist_ma10_pct": -9.0,
        "dist_ma20_pct": -18.9
      },
      {
        "code": "688498",
        "code_full": "688498.SH",
        "name": "源杰科技",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 1359.6686,
        "pe": 3.6,
        "risks_count": 1,
        "rps20": 18.05,
        "rps60": 97.33,
        "rps120": 99.44,
        "rps250": 100.0,
        "ma10": 1319.93,
        "vcp_quality": null,
        "ma5": 1207.18,
        "ma20": 1516.31,
        "dist_ma5_pct": -9.5,
        "dist_ma10_pct": -17.3,
        "dist_ma20_pct": -28.0
      },
      {
        "code": "000811",
        "code_full": "000811.SZ",
        "name": "冰轮环境",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 350.3447,
        "pe": 28.2,
        "risks_count": 2,
        "rps20": 24.53,
        "rps60": 99.47,
        "rps120": 99.42,
        "rps250": 98.53,
        "ma10": 40.18,
        "vcp_quality": null,
        "ma5": 37.69,
        "ma20": 45.76,
        "dist_ma5_pct": -6.3,
        "dist_ma10_pct": -12.1,
        "dist_ma20_pct": -22.9
      },
      {
        "code": "301377",
        "code_full": "301377.SZ",
        "name": "鼎泰高科",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1484.5813,
        "pe": 3.6,
        "risks_count": 1,
        "rps20": 9.86,
        "rps60": 99.49,
        "rps120": 99.26,
        "rps250": 99.98,
        "ma10": 382.01,
        "vcp_quality": null,
        "ma5": 366.31,
        "ma20": 428.25,
        "dist_ma5_pct": -4.4,
        "dist_ma10_pct": -8.4,
        "dist_ma20_pct": -18.2
      },
      {
        "code": "300604",
        "code_full": "300604.SZ",
        "name": "长川科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1647.2045,
        "pe": 9.3,
        "risks_count": 1,
        "rps20": 48.55,
        "rps60": 99.43,
        "rps120": 99.11,
        "rps250": 99.9,
        "ma10": 284.4,
        "vcp_quality": null,
        "ma5": 271.45,
        "ma20": 303.6,
        "dist_ma5_pct": -4.4,
        "dist_ma10_pct": -8.7,
        "dist_ma20_pct": -14.5
      },
      {
        "code": "688347",
        "code_full": "688347.SH",
        "name": "华虹宏力",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 4134.0511,
        "pe": 2.9,
        "risks_count": 1,
        "rps20": 70.73,
        "rps60": 99.9,
        "rps120": 99.05,
        "rps250": 99.76,
        "ma10": 311.77,
        "vcp_quality": null,
        "ma5": 265.5,
        "ma20": 329.78,
        "dist_ma5_pct": -10.4,
        "dist_ma10_pct": -23.7,
        "dist_ma20_pct": -27.9
      },
      {
        "code": "301165",
        "code_full": "301165.SZ",
        "name": "锐捷网络",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1314.0909,
        "pe": 3.7,
        "risks_count": 1,
        "rps20": 99.92,
        "rps60": 99.62,
        "rps120": 98.99,
        "rps250": 97.06,
        "ma10": 116.96,
        "vcp_quality": null,
        "ma5": 114.21,
        "ma20": 109.96,
        "dist_ma5_pct": 3.3,
        "dist_ma10_pct": 0.9,
        "dist_ma20_pct": 7.3
      },
      {
        "code": "688630",
        "code_full": "688630.SH",
        "name": "芯碁微装",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 476.4786,
        "pe": 5.3,
        "risks_count": 0,
        "rps20": 17.2,
        "rps60": 98.73,
        "rps120": 98.97,
        "rps250": 99.29,
        "ma10": 371.52,
        "vcp_quality": null,
        "ma5": 354.79,
        "ma20": 411.34,
        "dist_ma5_pct": -8.3,
        "dist_ma10_pct": -12.5,
        "dist_ma20_pct": -20.9
      },
      {
        "code": "300408",
        "code_full": "300408.SZ",
        "name": "三环集团",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 2220.0439,
        "pe": 11.6,
        "risks_count": 0,
        "rps20": 10.64,
        "rps60": 97.56,
        "rps120": 98.95,
        "rps250": 98.16,
        "ma10": 104.62,
        "vcp_quality": null,
        "ma5": 107.65,
        "ma20": 114.68,
        "dist_ma5_pct": 3.7,
        "dist_ma10_pct": 6.7,
        "dist_ma20_pct": -2.6
      },
      {
        "code": "688200",
        "code_full": "688200.SH",
        "name": "华峰测控",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 718.0268,
        "pe": 6.4,
        "risks_count": 0,
        "rps20": 24.06,
        "rps60": 99.29,
        "rps120": 98.89,
        "rps250": 99.08,
        "ma10": 365.27,
        "vcp_quality": null,
        "ma5": 359.19,
        "ma20": 420.34,
        "dist_ma5_pct": -0.4,
        "dist_ma10_pct": -2.1,
        "dist_ma20_pct": -14.9
      },
      {
        "code": "688072",
        "code_full": "688072.SH",
        "name": "拓荆科技",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 1932.928,
        "pe": 4.2,
        "risks_count": 1,
        "rps20": null,
        "rps60": 99.5,
        "rps120": 98.87,
        "rps250": 99.35,
        "ma10": 723.63,
        "vcp_quality": null,
        "ma5": 701.95,
        "ma20": 756.52,
        "dist_ma5_pct": -5.3,
        "dist_ma10_pct": -8.1,
        "dist_ma20_pct": -12.1
      },
      {
        "code": "688120",
        "code_full": "688120.SH",
        "name": "华海清科",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1275.344,
        "pe": 4.1,
        "risks_count": 2,
        "rps20": 61.64,
        "rps60": 99.84,
        "rps120": 98.74,
        "rps250": 98.3,
        "ma10": 262.04,
        "vcp_quality": null,
        "ma5": 264.69,
        "ma20": 278.91,
        "dist_ma5_pct": -2.9,
        "dist_ma10_pct": -1.9,
        "dist_ma20_pct": -7.9
      },
      {
        "code": "600176",
        "code_full": "600176.SH",
        "name": "中国巨石",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 1514.7869,
        "pe": 27.3,
        "risks_count": 1,
        "rps20": 3.01,
        "rps60": 94.61,
        "rps120": 98.66,
        "rps250": 98.0,
        "ma10": 38.84,
        "vcp_quality": null,
        "ma5": 38.3,
        "ma20": 46.8,
        "dist_ma5_pct": -1.2,
        "dist_ma10_pct": -2.6,
        "dist_ma20_pct": -19.1
      },
      {
        "code": "300285",
        "code_full": "300285.SZ",
        "name": "国瓷材料",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 618.5688,
        "pe": 14.5,
        "risks_count": 2,
        "rps20": 5.0,
        "rps60": 99.35,
        "rps120": 98.6,
        "rps250": 98.26,
        "ma10": 58.94,
        "vcp_quality": null,
        "ma5": 60.26,
        "ma20": 66.63,
        "dist_ma5_pct": 3.0,
        "dist_ma10_pct": 5.3,
        "dist_ma20_pct": -6.9
      },
      {
        "code": "688361",
        "code_full": "688361.SH",
        "name": "中科飞测",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1220.2111,
        "pe": 3.2,
        "risks_count": 3,
        "rps20": 75.12,
        "rps60": 99.8,
        "rps120": 98.47,
        "rps250": 99.27,
        "ma10": 350.95,
        "vcp_quality": null,
        "ma5": 357.78,
        "ma20": 367.14,
        "dist_ma5_pct": -3.1,
        "dist_ma10_pct": -1.2,
        "dist_ma20_pct": -5.6
      },
      {
        "code": "688300",
        "code_full": "688300.SH",
        "name": "联瑞新材",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 259.1447,
        "pe": 6.7,
        "risks_count": 0,
        "rps20": 0.37,
        "rps60": 98.47,
        "rps120": 98.39,
        "rps250": 96.47,
        "ma10": 121.48,
        "vcp_quality": null,
        "ma5": 115.7,
        "ma20": 149.58,
        "dist_ma5_pct": -7.2,
        "dist_ma10_pct": -11.7,
        "dist_ma20_pct": -28.3
      },
      {
        "code": "301536",
        "code_full": "301536.SZ",
        "name": "星宸科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 476.8334,
        "pe": 2.3,
        "risks_count": 2,
        "rps20": 75.34,
        "rps60": 98.91,
        "rps120": 98.29,
        "rps250": 94.75,
        "ma10": 122.08,
        "vcp_quality": null,
        "ma5": 118.34,
        "ma20": 117.51,
        "dist_ma5_pct": -4.5,
        "dist_ma10_pct": -7.4,
        "dist_ma20_pct": -3.8
      },
      {
        "code": "605376",
        "code_full": "605376.SH",
        "name": "博迁新材",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 356.4823,
        "pe": 5.6,
        "risks_count": 1,
        "rps20": 2.43,
        "rps60": 95.05,
        "rps120": 98.15,
        "rps250": 98.79,
        "ma10": 141.38,
        "vcp_quality": null,
        "ma5": 140.42,
        "ma20": 167.9,
        "dist_ma5_pct": -3.0,
        "dist_ma10_pct": -3.6,
        "dist_ma20_pct": -18.8
      },
      {
        "code": "300308",
        "code_full": "300308.SZ",
        "name": "中际旭创",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 10551.1234,
        "pe": 14.3,
        "risks_count": 2,
        "rps20": 26.05,
        "rps60": 95.88,
        "rps120": 97.9,
        "rps250": 99.8,
        "ma10": 1002.23,
        "vcp_quality": null,
        "ma5": 940.39,
        "ma20": 1065.87,
        "dist_ma5_pct": -4.1,
        "dist_ma10_pct": -10.0,
        "dist_ma20_pct": -15.4
      },
      {
        "code": "601991",
        "code_full": "601991.SH",
        "name": "大唐发电",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1093.7466,
        "pe": 19.6,
        "risks_count": 3,
        "rps20": 31.16,
        "rps60": 98.97,
        "rps120": 97.84,
        "rps250": 93.06,
        "ma10": 6.33,
        "vcp_quality": null,
        "ma5": 6.01,
        "ma20": 6.38,
        "dist_ma5_pct": -1.7,
        "dist_ma10_pct": -6.6,
        "dist_ma20_pct": -7.3
      },
      {
        "code": "300502",
        "code_full": "300502.SZ",
        "name": "新易盛",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 5521.3959,
        "pe": 10.4,
        "risks_count": 0,
        "rps20": 30.31,
        "rps60": 96.4,
        "rps120": 97.8,
        "rps250": 99.06,
        "ma10": 463.01,
        "vcp_quality": null,
        "ma5": 417.24,
        "ma20": 497.2,
        "dist_ma5_pct": -5.1,
        "dist_ma10_pct": -14.5,
        "dist_ma20_pct": -20.4
      },
      {
        "code": "002832",
        "code_full": "002832.SZ",
        "name": "比音勒芬",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 148.3268,
        "pe": 9.6,
        "risks_count": 1,
        "rps20": 96.75,
        "rps60": 97.41,
        "rps120": 97.75,
        "rps250": 89.05,
        "ma10": 23.61,
        "vcp_quality": null,
        "ma5": 25.08,
        "ma20": 22.29,
        "dist_ma5_pct": 3.6,
        "dist_ma10_pct": 10.1,
        "dist_ma20_pct": 16.6
      },
      {
        "code": "002821",
        "code_full": "002821.SZ",
        "name": "凯莱英",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 550.7322,
        "pe": 9.7,
        "risks_count": 1,
        "rps20": 87.78,
        "rps60": 97.66,
        "rps120": 97.65,
        "rps250": 90.5,
        "ma10": 159.2,
        "vcp_quality": null,
        "ma5": 154.78,
        "ma20": 164.07,
        "dist_ma5_pct": -1.4,
        "dist_ma10_pct": -4.1,
        "dist_ma20_pct": -7.0
      },
      {
        "code": "002787",
        "code_full": "002787.SZ",
        "name": "华源控股",
        "source_date": "2026/07/31",
        "highlights_count": 4,
        "market_cap": 64.718,
        "pe": 10.5,
        "risks_count": 1,
        "rps20": 10.78,
        "rps60": 89.42,
        "rps120": 97.36,
        "rps250": 96.24,
        "ma10": 20.35,
        "vcp_quality": null,
        "ma5": 19.74,
        "ma20": 23.5,
        "dist_ma5_pct": -1.4,
        "dist_ma10_pct": -4.3,
        "dist_ma20_pct": -17.2
      },
      {
        "code": "002463",
        "code_full": "002463.SZ",
        "name": "沪电股份",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 1996.5272,
        "pe": 15.9,
        "risks_count": 1,
        "rps20": 22.35,
        "rps60": 93.29,
        "rps120": 97.34,
        "rps250": 95.51,
        "ma10": 110.86,
        "vcp_quality": null,
        "ma5": 105.76,
        "ma20": 121.42,
        "dist_ma5_pct": -1.9,
        "dist_ma10_pct": -6.4,
        "dist_ma20_pct": -14.6
      },
      {
        "code": "000938",
        "code_full": "000938.SZ",
        "name": "紫光股份",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 997.8819,
        "pe": 26.7,
        "risks_count": 4,
        "rps20": 99.79,
        "rps60": 97.03,
        "rps120": 97.16,
        "rps250": 89.93,
        "ma10": 39.67,
        "vcp_quality": null,
        "ma5": 37.75,
        "ma20": 37.67,
        "dist_ma5_pct": -7.6,
        "dist_ma10_pct": -12.1,
        "dist_ma20_pct": -7.4
      },
      {
        "code": "002938",
        "code_full": "002938.SZ",
        "name": "鹏鼎控股",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1888.7924,
        "pe": 7.8,
        "risks_count": 1,
        "rps20": 31.06,
        "rps60": 96.42,
        "rps120": 97.12,
        "rps250": 94.12,
        "ma10": 87.32,
        "vcp_quality": null,
        "ma5": 83.86,
        "ma20": 92.67,
        "dist_ma5_pct": -2.8,
        "dist_ma10_pct": -6.7,
        "dist_ma20_pct": -12.0
      },
      {
        "code": "002353",
        "code_full": "002353.SZ",
        "name": "杰瑞股份",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 1379.1338,
        "pe": 16.5,
        "risks_count": 2,
        "rps20": 31.03,
        "rps60": 86.37,
        "rps120": 96.89,
        "rps250": 98.65,
        "ma10": 132.31,
        "vcp_quality": null,
        "ma5": 137.41,
        "ma20": 141.18,
        "dist_ma5_pct": -2.0,
        "dist_ma10_pct": 1.8,
        "dist_ma20_pct": -4.6
      },
      {
        "code": "002422",
        "code_full": "002422.SZ",
        "name": "科伦药业",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 691.0354,
        "pe": 16.1,
        "risks_count": 0,
        "rps20": 98.54,
        "rps60": 98.55,
        "rps120": 96.66,
        "rps250": 85.17,
        "ma10": 46.44,
        "vcp_quality": null,
        "ma5": 44.4,
        "ma20": 46.2,
        "dist_ma5_pct": -2.2,
        "dist_ma10_pct": -6.5,
        "dist_ma20_pct": -6.0
      },
      {
        "code": "688629",
        "code_full": "688629.SH",
        "name": "华丰科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 645.7236,
        "pe": 3.1,
        "risks_count": 1,
        "rps20": 43.01,
        "rps60": 93.62,
        "rps120": 96.52,
        "rps250": 97.22,
        "ma10": 146.58,
        "vcp_quality": null,
        "ma5": 136.65,
        "ma20": 168.55,
        "dist_ma5_pct": 0.9,
        "dist_ma10_pct": -5.9,
        "dist_ma20_pct": -18.2
      },
      {
        "code": "002371",
        "code_full": "002371.SZ",
        "name": "北方华创",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 4985.4848,
        "pe": 16.3,
        "risks_count": 1,
        "rps20": 40.96,
        "rps60": 98.53,
        "rps120": 96.29,
        "rps250": 95.55,
        "ma10": 722.9,
        "vcp_quality": null,
        "ma5": 709.29,
        "ma20": 753.23,
        "dist_ma5_pct": -3.1,
        "dist_ma10_pct": -5.0,
        "dist_ma20_pct": -8.8
      },
      {
        "code": "600428",
        "code_full": "600428.SH",
        "name": "中远海特",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 310.3374,
        "pe": 24.3,
        "risks_count": 0,
        "rps20": 99.67,
        "rps60": 97.45,
        "rps120": 96.19,
        "rps250": 91.65,
        "ma10": 10.79,
        "vcp_quality": null,
        "ma5": 10.91,
        "ma20": 9.97,
        "dist_ma5_pct": 3.6,
        "dist_ma10_pct": 4.8,
        "dist_ma20_pct": 13.4
      },
      {
        "code": "601918",
        "code_full": "601918.SH",
        "name": "新集能源",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 253.614,
        "pe": 18.6,
        "risks_count": 1,
        "rps20": 95.49,
        "rps60": 95.48,
        "rps120": 95.88,
        "rps250": 88.89,
        "ma10": 9.95,
        "vcp_quality": null,
        "ma5": 9.8,
        "ma20": 9.81,
        "dist_ma5_pct": -0.1,
        "dist_ma10_pct": -1.6,
        "dist_ma20_pct": -0.2
      },
      {
        "code": "688017",
        "code_full": "688017.SH",
        "name": "绿的谐波",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 556.6819,
        "pe": 5.9,
        "risks_count": 1,
        "rps20": 20.29,
        "rps60": 98.44,
        "rps120": 95.75,
        "rps250": 96.14,
        "ma10": 300.07,
        "vcp_quality": null,
        "ma5": 290.57,
        "ma20": 351.98,
        "dist_ma5_pct": 4.5,
        "dist_ma10_pct": 1.2,
        "dist_ma20_pct": -13.7
      },
      {
        "code": "688256",
        "code_full": "688256.SH",
        "name": "寒武纪",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 6948.9202,
        "pe": 6.0,
        "risks_count": 0,
        "rps20": 29.64,
        "rps60": 95.23,
        "rps120": 95.63,
        "rps250": 97.98,
        "ma10": 1200.74,
        "vcp_quality": null,
        "ma5": 1132.87,
        "ma20": 1294.6,
        "dist_ma5_pct": -2.4,
        "dist_ma10_pct": -7.9,
        "dist_ma20_pct": -14.6
      },
      {
        "code": "600236",
        "code_full": "600236.SH",
        "name": "桂冠电力",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 852.8733,
        "pe": 26.3,
        "risks_count": 2,
        "rps20": 98.97,
        "rps60": 94.63,
        "rps120": 95.57,
        "rps250": 91.4,
        "ma10": 11.02,
        "vcp_quality": null,
        "ma5": 10.59,
        "ma20": 10.35,
        "dist_ma5_pct": 2.2,
        "dist_ma10_pct": -1.8,
        "dist_ma20_pct": 4.6
      },
      {
        "code": "002831",
        "code_full": "002831.SZ",
        "name": "裕同科技",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 338.7022,
        "pe": 9.6,
        "risks_count": 2,
        "rps20": 20.64,
        "rps60": 88.14,
        "rps120": 95.51,
        "rps250": 89.54,
        "ma10": 26.47,
        "vcp_quality": null,
        "ma5": 26.23,
        "ma20": 27.53,
        "dist_ma5_pct": 0.2,
        "dist_ma10_pct": -0.7,
        "dist_ma20_pct": -4.5
      },
      {
        "code": "002916",
        "code_full": "002916.SZ",
        "name": "深南电路",
        "source_date": "2026/07/29",
        "highlights_count": 9,
        "market_cap": 2097.9931,
        "pe": 8.6,
        "risks_count": 1,
        "rps20": 17.74,
        "rps60": 91.62,
        "rps120": 95.22,
        "rps250": 96.73,
        "ma10": 326.27,
        "vcp_quality": null,
        "ma5": 316.01,
        "ma20": 366.12,
        "dist_ma5_pct": -2.5,
        "dist_ma10_pct": -5.6,
        "dist_ma20_pct": -15.9
      },
      {
        "code": "603203",
        "code_full": "603203.SH",
        "name": "快克智能",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 122.3683,
        "pe": 9.7,
        "risks_count": 1,
        "rps20": 2.55,
        "rps60": 93.92,
        "rps120": 95.12,
        "rps250": 94.36,
        "ma10": 39.56,
        "vcp_quality": null,
        "ma5": 38.34,
        "ma20": 48.71,
        "dist_ma5_pct": -3.3,
        "dist_ma10_pct": -6.3,
        "dist_ma20_pct": -23.9
      },
      {
        "code": "002245",
        "code_full": "002245.SZ",
        "name": "蔚蓝锂芯",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 271.1732,
        "pe": 18.1,
        "risks_count": 2,
        "rps20": 28.19,
        "rps60": 95.46,
        "rps120": 95.1,
        "rps250": 91.67,
        "ma10": 16.32,
        "vcp_quality": null,
        "ma5": 16.03,
        "ma20": 18.13,
        "dist_ma5_pct": -0.9,
        "dist_ma10_pct": -2.7,
        "dist_ma20_pct": -12.4
      },
      {
        "code": "300661",
        "code_full": "300661.SZ",
        "name": "圣邦股份",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 656.2034,
        "pe": 9.1,
        "risks_count": 0,
        "rps20": 16.96,
        "rps60": 94.43,
        "rps120": 95.01,
        "rps250": 86.77,
        "ma10": 99.84,
        "vcp_quality": null,
        "ma5": 95.99,
        "ma20": 111.05,
        "dist_ma5_pct": -0.3,
        "dist_ma10_pct": -4.1,
        "dist_ma20_pct": -13.8
      },
      {
        "code": "000725",
        "code_full": "000725.SZ",
        "name": "京东方A",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 2041.1425,
        "pe": 25.5,
        "risks_count": 2,
        "rps20": 18.44,
        "rps60": 98.65,
        "rps120": 94.81,
        "rps250": 87.18,
        "ma10": 5.81,
        "vcp_quality": null,
        "ma5": 5.63,
        "ma20": 6.49,
        "dist_ma5_pct": -2.1,
        "dist_ma10_pct": -5.2,
        "dist_ma20_pct": -15.1
      },
      {
        "code": "603259",
        "code_full": "603259.SH",
        "name": "药明康德",
        "source_date": "2026/07/29",
        "highlights_count": 9,
        "market_cap": 3832.0393,
        "pe": 8.2,
        "risks_count": 0,
        "rps20": 88.1,
        "rps60": 96.32,
        "rps120": 94.79,
        "rps250": 89.73,
        "ma10": 125.71,
        "vcp_score": 41,
        "vcp_contraction_ratio": 0.82,
        "vcp_last_depth": 13.4,
        "vcp_dist_peak_pct": 5.0,
        "vcp_nearest_ma": "MA10",
        "vcp_nearest_ma_dist": 2.2,
        "vcp_vol_declining": false,
        "vcp_num_contractions": 8,
        "vcp_depths": "16%→8%→10%→22%→21%→15%→11%→13%",
        "vcp_quality": "SETUP",
        "ma5": 125.62,
        "ma20": 124.41,
        "dist_ma5_pct": 2.2,
        "dist_ma10_pct": 2.2,
        "dist_ma20_pct": 3.2
      },
      {
        "code": "688008",
        "code_full": "688008.SH",
        "name": "澜起科技",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 2500.8824,
        "pe": 7.0,
        "risks_count": 1,
        "rps20": 21.42,
        "rps60": 96.45,
        "rps120": 94.39,
        "rps250": 96.77,
        "ma10": 213.15,
        "vcp_quality": null,
        "ma5": 208.37,
        "ma20": 232.24,
        "dist_ma5_pct": -1.7,
        "dist_ma10_pct": -3.9,
        "dist_ma20_pct": -11.8
      },
      {
        "code": "688002",
        "code_full": "688002.SH",
        "name": "睿创微纳",
        "source_date": "2026/08/01",
        "highlights_count": 6,
        "market_cap": 666.482,
        "pe": 7.0,
        "risks_count": 1,
        "rps20": 65.75,
        "rps60": 89.36,
        "rps120": 94.19,
        "rps250": 95.28,
        "ma10": 144.89,
        "vcp_quality": null,
        "ma5": 143.81,
        "ma20": 146.06,
        "dist_ma5_pct": -1.5,
        "dist_ma10_pct": -2.2,
        "dist_ma20_pct": -3.0
      },
      {
        "code": "000977",
        "code_full": "000977.SZ",
        "name": "浪潮信息",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 1054.5131,
        "pe": 26.1,
        "risks_count": 1,
        "rps20": 99.16,
        "rps60": 94.93,
        "rps120": 94.0,
        "rps250": 88.38,
        "ma10": 81.44,
        "vcp_quality": null,
        "ma5": 76.14,
        "ma20": 81.39,
        "dist_ma5_pct": -5.7,
        "dist_ma10_pct": -11.8,
        "dist_ma20_pct": -11.8
      },
      {
        "code": "002440",
        "code_full": "002440.SZ",
        "name": "闰土股份",
        "source_date": "2026/07/30",
        "highlights_count": 4,
        "market_cap": 154.1004,
        "pe": 16.0,
        "risks_count": 2,
        "rps20": 97.72,
        "rps60": 95.27,
        "rps120": 93.74,
        "rps250": 90.14,
        "ma10": 12.69,
        "vcp_quality": null,
        "ma5": 13.06,
        "ma20": 11.51,
        "dist_ma5_pct": 5.0,
        "dist_ma10_pct": 8.0,
        "dist_ma20_pct": 19.1
      },
      {
        "code": "300001",
        "code_full": "300001.SZ",
        "name": "特锐德",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 370.42,
        "pe": 16.7,
        "risks_count": 1,
        "rps20": 52.27,
        "rps60": 95.6,
        "rps120": 93.37,
        "rps250": 87.67,
        "ma10": 34.81,
        "vcp_quality": null,
        "ma5": 34.26,
        "ma20": 33.72,
        "dist_ma5_pct": 2.4,
        "dist_ma10_pct": 0.8,
        "dist_ma20_pct": 4.1
      },
      {
        "code": "688536",
        "code_full": "688536.SH",
        "name": "思瑞浦",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 307.9083,
        "pe": 5.8,
        "risks_count": 2,
        "rps20": 13.07,
        "rps60": 86.85,
        "rps120": 93.32,
        "rps250": 92.51,
        "ma10": 240.9,
        "vcp_quality": null,
        "ma5": 232.55,
        "ma20": 273.24,
        "dist_ma5_pct": -4.1,
        "dist_ma10_pct": -7.4,
        "dist_ma20_pct": -18.4
      },
      {
        "code": "603162",
        "code_full": "603162.SH",
        "name": "海通发展",
        "source_date": "2026/07/30",
        "highlights_count": 5,
        "market_cap": 149.7113,
        "pe": 3.3,
        "risks_count": 1,
        "rps20": 97.61,
        "rps60": 92.95,
        "rps120": 93.1,
        "rps250": 93.26,
        "ma10": 10.84,
        "vcp_quality": null,
        "ma5": 10.81,
        "ma20": 10.45,
        "dist_ma5_pct": 0.6,
        "dist_ma10_pct": 0.4,
        "dist_ma20_pct": 4.2
      },
      {
        "code": "002203",
        "code_full": "002203.SZ",
        "name": "海亮股份",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 420.9954,
        "pe": 18.5,
        "risks_count": 5,
        "rps20": 22.54,
        "rps60": 87.15,
        "rps120": 92.03,
        "rps250": 91.22,
        "ma10": 17.82,
        "vcp_quality": null,
        "ma5": 17.65,
        "ma20": 18.63,
        "dist_ma5_pct": 4.1,
        "dist_ma10_pct": 3.1,
        "dist_ma20_pct": -1.4
      },
      {
        "code": "603127",
        "code_full": "603127.SH",
        "name": "昭衍新药",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 311.2793,
        "pe": 8.9,
        "risks_count": 3,
        "rps20": 98.62,
        "rps60": 96.34,
        "rps120": 91.72,
        "rps250": 91.89,
        "ma10": 45.87,
        "vcp_quality": null,
        "ma5": 44.16,
        "ma20": 45.05,
        "dist_ma5_pct": -5.9,
        "dist_ma10_pct": -9.4,
        "dist_ma20_pct": -7.8
      },
      {
        "code": "688652",
        "code_full": "688652.SH",
        "name": "京仪装备",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 215.6784,
        "pe": 2.6,
        "risks_count": 0,
        "rps20": 26.42,
        "rps60": 96.99,
        "rps120": 91.65,
        "rps250": 96.9,
        "ma10": 144.19,
        "vcp_quality": null,
        "ma5": 137.41,
        "ma20": 170.94,
        "dist_ma5_pct": -6.6,
        "dist_ma10_pct": -11.0,
        "dist_ma20_pct": -24.9
      },
      {
        "code": "603156",
        "code_full": "603156.SH",
        "name": "养元饮品",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 488.1055,
        "pe": 8.4,
        "risks_count": 2,
        "rps20": 24.66,
        "rps60": 89.88,
        "rps120": 90.99,
        "rps250": 92.0,
        "ma10": 36.41,
        "vcp_quality": null,
        "ma5": 37.58,
        "ma20": 39.96,
        "dist_ma5_pct": 3.1,
        "dist_ma10_pct": 6.4,
        "dist_ma20_pct": -3.1
      },
      {
        "code": "688401",
        "code_full": "688401.SH",
        "name": "路维光电",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 124.1049,
        "pe": 3.9,
        "risks_count": 0,
        "rps20": 16.51,
        "rps60": 86.55,
        "rps120": 90.65,
        "rps250": 93.44,
        "ma10": 63.95,
        "vcp_quality": null,
        "ma5": 62.45,
        "ma20": 73.21,
        "dist_ma5_pct": -3.2,
        "dist_ma10_pct": -5.5,
        "dist_ma20_pct": -17.5
      },
      {
        "code": "688041",
        "code_full": "688041.SH",
        "name": "海光信息",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 6438.4165,
        "pe": 3.9,
        "risks_count": 0,
        "rps20": 43.28,
        "rps60": 90.31,
        "rps120": 90.44,
        "rps250": 95.67,
        "ma10": 306.88,
        "vcp_quality": null,
        "ma5": 289.26,
        "ma20": 324.17,
        "dist_ma5_pct": -4.2,
        "dist_ma10_pct": -9.7,
        "dist_ma20_pct": -14.6
      },
      {
        "code": "688981",
        "code_full": "688981.SH",
        "name": "中芯国际",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 10614.5434,
        "pe": 6.0,
        "risks_count": 0,
        "rps20": 54.11,
        "rps60": 96.51,
        "rps120": 90.38,
        "rps250": 89.56,
        "ma10": 140.68,
        "vcp_quality": null,
        "ma5": 131.67,
        "ma20": 148.35,
        "dist_ma5_pct": -5.8,
        "dist_ma10_pct": -11.9,
        "dist_ma20_pct": -16.4
      },
      {
        "code": "300373",
        "code_full": "300373.SZ",
        "name": "扬杰科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 455.9775,
        "pe": 12.5,
        "risks_count": 0,
        "rps20": 8.62,
        "rps60": 95.44,
        "rps120": 90.13,
        "rps250": 91.95,
        "ma10": 89.69,
        "vcp_quality": null,
        "ma5": 86.29,
        "ma20": 104.49,
        "dist_ma5_pct": -2.8,
        "dist_ma10_pct": -6.4,
        "dist_ma20_pct": -19.7
      },
      {
        "code": "002138",
        "code_full": "002138.SZ",
        "name": "顺络电子",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 345.1043,
        "pe": 19.1,
        "risks_count": 1,
        "rps20": 4.65,
        "rps60": 96.63,
        "rps120": 89.06,
        "rps250": 88.18,
        "ma10": 42.23,
        "vcp_quality": null,
        "ma5": 42.58,
        "ma20": 47.58,
        "dist_ma5_pct": 0.5,
        "dist_ma10_pct": 1.4,
        "dist_ma20_pct": -10.0
      },
      {
        "code": "000739",
        "code_full": "000739.SZ",
        "name": "普洛药业",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 234.2373,
        "pe": 29.2,
        "risks_count": 1,
        "rps20": 98.74,
        "rps60": 94.26,
        "rps120": 88.96,
        "rps250": 85.75,
        "ma10": 20.21,
        "vcp_score": 60,
        "vcp_contraction_ratio": 0.54,
        "vcp_last_depth": 8.0,
        "vcp_dist_peak_pct": 6.0,
        "vcp_nearest_ma": "MA10",
        "vcp_nearest_ma_dist": 0.0,
        "vcp_vol_declining": true,
        "vcp_num_contractions": 6,
        "vcp_depths": "15%→8%→10%→17%→13%→8%",
        "vcp_quality": "SETUP",
        "ma5": 20.17,
        "ma20": 19.57,
        "dist_ma5_pct": 0.2,
        "dist_ma10_pct": 0.0,
        "dist_ma20_pct": 3.3
      },
      {
        "code": "600885",
        "code_full": "600885.SH",
        "name": "宏发股份",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 549.5507,
        "pe": 13.7,
        "risks_count": 0,
        "rps20": 61.27,
        "rps60": 94.99,
        "rps120": 88.87,
        "rps250": 87.81,
        "ma10": 33.95,
        "vcp_quality": null,
        "ma5": 34.42,
        "ma20": 34.45,
        "dist_ma5_pct": 3.2,
        "dist_ma10_pct": 4.6,
        "dist_ma20_pct": 3.1
      },
      {
        "code": "688777",
        "code_full": "688777.SH",
        "name": "中控技术",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 736.7557,
        "pe": 5.6,
        "risks_count": 2,
        "rps20": 17.41,
        "rps60": 94.59,
        "rps120": 88.73,
        "rps250": 92.71,
        "ma10": 85.48,
        "vcp_quality": null,
        "ma5": 83.6,
        "ma20": 93.0,
        "dist_ma5_pct": 11.4,
        "dist_ma10_pct": 8.9,
        "dist_ma20_pct": 0.1
      },
      {
        "code": "601168",
        "code_full": "601168.SH",
        "name": "西部矿业",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 916.0252,
        "pe": 19.0,
        "risks_count": 0,
        "rps20": 99.42,
        "rps60": 96.87,
        "rps120": 87.95,
        "rps250": 95.3,
        "ma10": 36.3,
        "vcp_quality": null,
        "ma5": 37.32,
        "ma20": 33.59,
        "dist_ma5_pct": 3.0,
        "dist_ma10_pct": 5.9,
        "dist_ma20_pct": 14.4
      },
      {
        "code": "601233",
        "code_full": "601233.SH",
        "name": "桐昆股份",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 532.8963,
        "pe": 15.2,
        "risks_count": 2,
        "rps20": 55.92,
        "rps60": 85.94,
        "rps120": 86.89,
        "rps250": 93.53,
        "ma10": 21.77,
        "vcp_quality": null,
        "ma5": 21.87,
        "ma20": 21.46,
        "dist_ma5_pct": 2.4,
        "dist_ma10_pct": 2.9,
        "dist_ma20_pct": 4.4
      },
      {
        "code": "002056",
        "code_full": "002056.SZ",
        "name": "横店东磁",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 338.1934,
        "pe": 20.0,
        "risks_count": 1,
        "rps20": 15.95,
        "rps60": 95.42,
        "rps120": 86.26,
        "rps250": 86.83,
        "ma10": 21.4,
        "vcp_quality": null,
        "ma5": 20.98,
        "ma20": 24.32,
        "dist_ma5_pct": -0.9,
        "dist_ma10_pct": -2.9,
        "dist_ma20_pct": -14.5
      }
    ]
  },
  "enriched_candidates": [
    {
      "code": "000725.SZ",
      "fetch_time": "2026-08-03T11:35:52+0800",
      "name": "京东方A",
      "pe": 33.8681,
      "pb": 1.5036,
      "ps_ttm": 0.9831,
      "pcf_ttm": 4.2533,
      "valuation_percentile": 54.78,
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
        "数字经济指数"
      ],
      "score_company": 8.4,
      "score_trend": 7.3,
      "score_value": 5.1,
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
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 1.9% ，现金分红较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 13% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 15家 机构给出评级，其中 60% 为“买入”，距目标价的上涨空间为 29% 。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 6.5% ，很受外资机构青睐。"
        },
        {
          "tag": "回购",
          "text": "近6月，公司累计回购 10亿股 ，占总股本比例 2.7% ，金额合计 43亿元 。"
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
      "valuation_history_from": "20210803",
      "current_price": 5.51,
      "price": 5.51,
      "ma5": 5.63,
      "ma10": 5.81,
      "ma20": 6.49,
      "dist_ma5_pct": -2.1,
      "dist_ma10_pct": -5.2,
      "dist_ma20_pct": -15.1,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.8337,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 117.75,
        "pct_float": 6.04,
        "chg5_pct": -2.03,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "603259.SH",
      "fetch_time": "2026-08-03T11:35:52+0800",
      "name": "药明康德",
      "pe": 18.8688,
      "pb": 4.7772,
      "ps_ttm": 7.8742,
      "pcf_ttm": 21.577,
      "valuation_percentile": 36.48,
      "total_shares": 2983757155,
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
        "A50指数",
        "双循环指数",
        "茅指数",
        "出海贸易指数",
        "人工智能+指数",
        "自主可控指数",
        "贷款回购指数",
        "RCEP指数",
        "大消费指数",
        "股权激励指数",
        "中概股回归指数",
        "宁组合",
        "高瓴资本指数"
      ],
      "score_company": 9.7,
      "score_trend": 8.9,
      "score_value": 6.6,
      "highlights": [
        {
          "tag": "A/H",
          "text": "A/H溢价率仅为 -7% ，从流动性而言，A股吸引力较高。"
        },
        {
          "tag": "龙头",
          "text": "公司为 医疗研发外包 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年04月28日，业绩超预期引发股价跳空高开，但目前股价缺口已回补。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 27% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 19% ，投入资本回报率为 20% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 6.2% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 11% ，很受外资机构青睐；公募基金持股 15% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 97% 的股票，收盘价接近 一年新高 ，走势很强。"
        },
        {
          "tag": "回购",
          "text": "近2月，公司累计回购 970万股 ，占总股本比例 0.33% ，金额合计 10亿元 。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/04发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-04"
        },
        {
          "content": "20:48 7月31日，平安理财、杭银理财披露上半年理财业务报告，加上此前已披露业绩的浦银理财、苏银理财、青银理财、浙银理财，首批理财公司上半年业绩答卷出炉。其中，苏银理财、浦银理财、浙银理财的管理规模较年初分别增长8.46%、5.31%、1.24%，增速跑赢行业。银行业理财登记托管中心数据显示，截至6月末，存续理财产品规模33.66万亿元，较年初增加1.11%。开源证券分析指出，今年二季度理财产品规模增长1.75万亿元，扭转了一季度增长较弱态势，股债行情带动“固收+”产品吸引力增强。含权类产品成为规模增长重要来源，上半年苏银理财混合类产品规模增长59%，浦银理财权益类产品规模增长484%，浙银理财混合类产品规模增长346%。苏银理财上半年新发3只混合类产品，募集67.53亿元，6月末持有药明康德、生益科技、恒瑞医药及创业板人工智能ETF等资产。浦银理财新发2只权益类产品，募集60.17亿元。浙银理财旗下混合类产品规模从2025年末的9559.17万元增至今年上半年末的4.26亿元，增持了农行优2、易方达创业板ETF、华泰柏瑞沪深300ETF、摩根标普港股通低波红利ETF等资产。\n邮储银行研究员娄飞鹏认为，上半年含权理财产品规模增长主要受客户需求驱动及机构资产配置策略调整影响。在“资产荒”背景下，传统固收资产收益率下行，客户为追求更高回报增加含权产品配置。含权类产品有助于理财公司开辟长期增长曲线，但理财公司投研能力仍需提升，且需关注市场波动导致的净值回撤对规模稳定性的影响。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "02:11 江苏汉邦科技股份有限公司（证券简称：汉邦科技，代码：688755）发布回购报告书。公司拟以集中竞价交易方式回购股份，回购金额不低于3,000万元且不超过5,000万元，回购价格不超过39.41元/股，期限为董事会审议通过之日起3个月内。回购资金来源为自有资金或自筹资金（含专项贷款，已取得兴业银行淮安分行贷款承诺函）。回购用途为维护公司价值及股东权益。公司持股5%以上股东上海药明康德新药开发有限公司、杭州清科致盛投资合伙企业及其一致行动人存在减持计划。\n本次回购方案已于2026年7月23日经公司第二届董事会第五次会议审议通过。截至2026年7月22日，公司股票收盘价为22.15元/股，符合相关回购规定。回购期限内，若触及资金上限、董事会决议终止或资金下限等条件，回购期限可提前届满。\n公司已取得兴业银行淮安分行出具的《贷款承诺函》，承诺贷款金额不超过4,500万元，专项用于回购股票。具体回购数量及比例以实施结果为准，若遇除权除息事项将进行相应调整。\n截至2026年3月31日，公司总资产194,447.87万元，归属于上市公司股东的净资产126,593.90万元。本次回购资金上限占上述财务数据比例较小，预计不会对公司经营、财务及未来发展产生重大影响。公司董事、高管、控股股东及实控人在回购决议前6个月内无买卖公司股份行为，且回购期间暂无增减持计划。\n本次回购股份拟在披露回购结果暨股份变动公告12个月后采用集中竞价方式出售；若3年内未实施，将依法注销。董事会授权管理层办理回购相关事宜，包括设立专用账户、择机回购及调整方案等。\n公司已在中国证券登记结算有限责任公司上海分公司开立回购专用证券账户（号码：B888681859）。公司提示，回购方案存在价格超出上限、重大事项导致终止、监管政策变化等不确定性风险。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "药明康德：H股公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 32856716508.86,
      "revenue_yoy": 0.186077,
      "operating_profit": 15066061792.99,
      "operating_profit_yoy": 0.909303,
      "net_profit": 12206193461.26,
      "net_profit_yoy": 0.848972,
      "gross_profit": 15318617871.07,
      "gross_profit_yoy": 0.360235,
      "cogs": 17538098637.79,
      "gross_margin": 46.62,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210803",
      "current_price": 128.43,
      "price": 128.43,
      "ma5": 125.62,
      "ma10": 125.71,
      "ma20": 124.41,
      "dist_ma5_pct": 2.2,
      "dist_ma10_pct": 2.2,
      "dist_ma20_pct": 3.2,
      "iv_proxy": {
        "primary_name": "50ETF",
        "iv_rank": 0.6318,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 51.52,
        "pct_float": 1.62,
        "chg5_pct": -4.6,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688008.SH",
      "fetch_time": "2026-08-03T11:35:52+0800",
      "name": "澜起科技",
      "pe": 91.9344,
      "pb": 11.667,
      "ps_ttm": 41.2889,
      "pcf_ttm": 95.5665,
      "valuation_percentile": 78.02,
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
        "5G指数"
      ],
      "score_company": 9.4,
      "score_trend": 7.6,
      "score_value": 4.4,
      "highlights": [
        {
          "tag": "A/H",
          "text": "A/H溢价率仅为 -12% ，从流动性而言，A股吸引力较高。"
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
          "text": "近90天， 5家 机构给出评级，其中 60% 为“买入”，距目标价的上涨空间为 89% 。"
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
          "text": "近1月，公司累计回购 216万股 ，占总股本比例 0.18% ，金额合计 3.2亿元 。"
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
          "content": "17:00 存储元器件价格波动直接影响存储芯片相关上市公司的业绩，同时需关注晶圆成本及企业产销情况。本周电子存储市场价格变动如下：Flash（MLC 64Gb）价格为32.57美元，周涨幅3.74%，月涨幅15.55%；Flash（SLC 2Gb）价格为4.09美元，周涨幅1.19%，月涨幅4.60%；eMMC/128G价格为31.00美元；UFS/128GB价格为33.00美元；DDR4/16Gb价格为50.00美元；SSD/256GB（SATA3）价格为71.00美元，月涨幅7.58%。存储价格指数方面，DRAM指数周涨幅0.04%，报4061.45点；NAND指数报2988.98点。上游晶圆价格方面，Wafer（256Gb）价格为10.46美元，周涨幅2.79%；Wafer（128Gb）价格为6.65美元，周涨幅2.56%；Wafer（512Gb）价格为18.93美元，周跌幅1.28%。相关上市公司财务数据如下：兆易创新存储芯片产品收入占比64.05%，毛利率39.71%；北京君正存储芯片产品收入占比68.15%，毛利率30.40%；紫光国微集成电路产品收入占比94.13%，毛利率61.97%；上海贝岭集成电路产品收入占比70.34%，毛利率40.58%；普冉股份集成电路产品收入占比100%，毛利率36.23%。\n国科微固态存储系列芯片产品收入占比55.11%，毛利率12.98%；澜起科技集成电路产品收入占比100%，毛利率48.08%；德明利储存产品收入占比99.75%，毛利率21.23%；东芯股份集成电路产品收入占比99.93%，毛利率42.09%。存储芯片作为半导体产业重要分支，约占全球半导体市场的三分之一。产业链上游包括硅片、光刻胶、抛光液等原材料及制造设备；中游为存储芯片制造及封装，涵盖DRAM、NAND及NOR闪存芯片；下游应用包括消费电子和汽车电子。成本结构中，设计、制造、封测环节分别占比30%、40%和30%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "16:36 中证指数有限公司与恒生指数公司今天宣布，截至2026年6月30日之中证恒生沪港通AH股精明指数的半年度指数检讨结果。中证恒生沪港通AH股精明指数成份股公司将有以下的变动，成份股公司数目仍维持50只。加入兆易创新、澜起科技，剔除中国南方航空股份、中国铁建。",
          "tags": [
            "快讯"
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
      "valuation_history_from": "20210803",
      "current_price": 204.9,
      "price": 204.9,
      "ma5": 208.37,
      "ma10": 213.15,
      "ma20": 232.24,
      "dist_ma5_pct": -1.7,
      "dist_ma10_pct": -3.9,
      "dist_ma20_pct": -11.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.942,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 151.39,
        "pct_float": 6.45,
        "chg5_pct": -3.99,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688002.SH",
      "fetch_time": "2026-08-03T11:35:52+0800",
      "name": "睿创微纳",
      "pe": 44.2035,
      "pb": 9.0315,
      "ps_ttm": 9.0586,
      "pcf_ttm": 25.2285,
      "valuation_percentile": 58.06,
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
        "可转债正股指数",
        "ASIC芯片指数",
        "半导体分立器件指数",
        "传感器指数"
      ],
      "score_company": 8.7,
      "score_trend": 8.5,
      "score_value": 5.4,
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
      "valuation_history_from": "20210803",
      "current_price": 141.65,
      "price": 141.65,
      "ma5": 143.81,
      "ma10": 144.89,
      "ma20": 146.06,
      "dist_ma5_pct": -1.5,
      "dist_ma10_pct": -2.2,
      "dist_ma20_pct": -3.0,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.942,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 13.68,
        "pct_float": 2.05,
        "chg5_pct": -10.83,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "000977.SZ",
      "fetch_time": "2026-08-03T11:35:52+0800",
      "name": "浪潮信息",
      "pe": 41.23,
      "pb": 4.736,
      "ps_ttm": 0.6868,
      "pcf_ttm": null,
      "valuation_percentile": 68.31,
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
        "国企改革指数",
        "贷款回购指数",
        "新基建指数",
        "信创产业指数",
        "AI备案指数",
        "元宇宙指数",
        "设备更新指数",
        "AI应用指数",
        "AI算力指数"
      ],
      "score_company": 8.7,
      "score_trend": 7.7,
      "score_value": 4.6,
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
          "text": "近90天， 14家 机构给出评级，其中 71% 为“买入”，距目标价的上涨空间为 28% 。"
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
          "text": "近6月，股价涨幅超过A股市场 91% 的股票，走势较强。"
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
          "content": "12:37 美国当地时间7月30日，亚马逊公布2026年第二季度财报，其中，最受市场关注的亚马逊云服务（AWS）业务在本季度营收422.32亿美元，同比增长36.7%，高于市场预期的31%，创2021年以来最快增速，已连续第五个季度实现加速增长。AWS贡献了公司约五分之一的营收和大部分营业利润。在业绩利好的刺激下，亚马逊股价大幅上涨。美国当地时间周五，亚马逊（AMZN.O）股价收盘上涨15.32%，截至最新收盘，公司总市值达到2.93万亿美元。在AI技术与算力网络深度融合的大趋势下，叠加国内企业“智改数转”进程持续提速，市场用云需求不断下沉、深化。从业绩数据来看，今年上半年净利润同比增长（含扭亏为盈）的云计算概念股有11只，其中浪潮信息、金山办公、紫光股份净利润规模靠前。资金维度方面，数据宝统计，截至7月31日收盘，18只云计算概念股7月以来获得机构资金净买入超1亿元。紫光股份、星网锐捷、浪潮信息分别获得机构资金净买入28.71亿元、22.2亿元、21.42亿元，排在前三位。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "19:51 2026年7月30日，中共中央政治局会议将“扎实推进六张网规划建设”列为下半年经济工作要点。国家发展改革委政策研究室主任、新闻发言人蒋毅在7月31日新闻发布会上指出，据有关机构测算，“十五五”时期算力网建设将新增直接投资4万亿元。算力网正式与水网、新型电网、新一代通信网等并列，成为国家顶层基础设施统筹布局的重要组成部分。算力产业正从硬件投资时代，逐步进入网络化、平台化、运营化的新阶段。\n算力网的政策定位已从区域工程演进为国家基础设施。2026年，算力网被正式纳入国家“六张网”建设，并列入“十五五”重大工程项目谋划范围。国家数据局等部门已部署国家数据基础设施建设路径，并明确加大中央财政投入，利用超长期特别国债资金支持建设。目前，“全国一体化算力网监测调度试验验证平台”已初步建成，实现对“东数西算”八大枢纽十大集群、三大运营商、超算互联网及部分非枢纽地区算力资源的统一监测，覆盖全国超过900个算力基础设施。\n2026年3月，“算电协同”首次写入政府工作报告，旨在形成“以电强算、以算促电”的良性循环。国家发改委明确多网协同逻辑：新型电网提供电力供应，算力网指挥电网智能化调度，通信网支撑算力跨区域调度。当前算力产业面临利用率低、东西部资源失衡及定价体系不统一等痛点，算力网建设旨在通过“算力池化”实现按需取用，并推动计量标准统一。\n算力产业竞争焦点正从硬件囤积转向资源组织能力。运营商方面，中国移动、中国电信、中国联通正加速向“云网算力服务商”转型。2025年，中国移动算力服务收入898亿元，智算服务收入增速达279%；中国电信天翼云收入1207亿元，AIDC收入345亿元；中国联通人工智能业务收入增长超140%。2026年，三大运营商在算力基础设施投入上持续加码，算力相关资本开支占比显著提升。\n云服务商正从算力资源提供者向AI生产力平台转型。腾讯2026年一季度资本开支319.36亿元，同比增加16%；阿里2026财年四季度资本支出269亿元，AI相关产品收入占比首破30%；字节跳动2026年AI资本开支预算增至2000亿元。此外，围绕算力资源流通的新型服务商出现，如贵州“大衍”算力调度平台，截至2026年6月累计交易额超258亿元。\n算力产业链中，AI芯片、AI服务器及光模块等环节已进入业绩兑现期。国产AI芯片方面，华为、阿里平头哥、寒武纪等厂商市场份额提升。寒武纪2026年一季度净利10.13亿元，同比增加185%；海光信息上半年预计归母净利17亿至18.3亿元。AI服务器领域，工业富联预计上半年归母净利234亿至244亿元，浪潮信息预计上半年归母净利26亿至31亿元，紫光股份预计上半年净利19.1亿至23.2亿元。\n光模块环节，中际旭创2026年一季度归母净利57.35亿元，同比增加262%；新易盛预计上半年归母净利70亿至80亿元；光迅科技预计上半年归母净利5.59亿至6.15亿元。此外，存储环节受AI服务器需求拉动，佰维存储预计2026年上半年净利70亿至75亿元，实现扭亏。\n算力租赁与液冷技术领域表现分化。算力租赁方面，利通电子一季度归母净利2.71亿元，同比增加821%；协创数据一季度归母净利7.50亿元，同比增加343.45%；中科曙光一季度归母净利2.28亿元，同比增加22.19%；润泽科技一季度扣非归母净利5.82亿元，同比增加35.92%。液冷技术方面，英维克一季度归母净利同比下降81.97%，显示赛道竞争加剧。\n算力交易平台与算电协同仍处于商业模式探索期。云赛智联、中科曙光等参与算力交易平台建设。算电协同方面，全国已形成3个算电协同发展区域，如中国移动中卫云基地已实现绿电直供。随着政策支持力度加大，这些领域有望成为算力经济的新增长极。\n本文内容基于公开信息整理，涉及公司业绩均为2026年半年度预告或估算数据，最终以正式公告为准。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:30股价达到 83.8 元，创历史新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价开盘上涨 10.01% ，股价收盘涨幅 10.01%",
          "tags": [
            "股价上涨"
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
      "valuation_history_from": "20210803",
      "current_price": 71.81,
      "price": 71.81,
      "ma5": 76.14,
      "ma10": 81.44,
      "ma20": 81.39,
      "dist_ma5_pct": -5.7,
      "dist_ma10_pct": -11.8,
      "dist_ma20_pct": -11.8,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.8337,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 36.23,
        "pct_float": 3.44,
        "chg5_pct": -20.5,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002440.SZ",
      "fetch_time": "2026-08-03T11:35:52+0800",
      "name": "闰土股份",
      "pe": 18.4241,
      "pb": 1.4982,
      "ps_ttm": 2.4188,
      "pcf_ttm": 21.543,
      "valuation_percentile": 75.8,
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
      "score_company": 8.1,
      "score_trend": 8.9,
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
      "valuation_history_from": "20210803",
      "current_price": 13.71,
      "price": 13.71,
      "ma5": 13.06,
      "ma10": 12.69,
      "ma20": 11.51,
      "dist_ma5_pct": 5.0,
      "dist_ma10_pct": 8.0,
      "dist_ma20_pct": 19.1,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 2.94,
        "pct_float": 2.26,
        "chg5_pct": -16.86,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300001.SZ",
      "fetch_time": "2026-08-03T11:35:52+0800",
      "name": "特锐德",
      "pe": 30.5913,
      "pb": 4.5347,
      "ps_ttm": 2.4054,
      "pcf_ttm": 18.3501,
      "valuation_percentile": 42.9,
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
        "高铁指数",
        "智能电网指数",
        "高低压设备精选指数",
        "电气自动化设备精选指数"
      ],
      "score_company": 8.5,
      "score_trend": 8.6,
      "score_value": 5.8,
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
          "text": "近3月，股价涨幅超过A股市场 97% 的股票，走势很强。"
        },
        {
          "tag": "回购",
          "text": "公司公告自2026年07月30日起，拟回购不超过 6.0亿元 ，回购价格不超过 50元/股 。"
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
          "content": "02:27 在7月30日举行的新闻发布会上，国家能源局表示，受新能源汽车、人工智能等高新技术产业带动，今年上半年充换电服务业、互联网数据服务业用电量增长强劲，同比分别增长56.9%和44%，合计拉高全社会用电量0.9个百分点。截至2026年6月底，我国电动汽车充电基础设施总数达到2305.7万个，同比增长43.2%。其中，公共充电设施500.9万个，同比增长22.3%，额定总功率2.47亿千瓦；私人充电设施1804.8万个，同比增长50.4%。在大功率充电设施方面，全国已建成大功率充电枪超过18万个。县域充电设施覆盖率提升至98.61%。根据《电动汽车充电设施服务能力“三年倍增”行动方案（2025—2027）》，到2027年底全国城市将新增160万个直流充电枪，其中包括10万个大功率充电枪。《新型能源体系建设“十五五”规划》提出，2030年充电基础设施达到4000万个，车网互动聚合可调充电规模将达到5000万千瓦左右，预计到2030年车能融合将创造万亿级综合经济效益。\n在充电桩概念股中，银河电子、ST长园、京泉华、特锐德、思源电气今年上半年净利润同比增长。其中，银河电子、ST长园预计扭亏为盈。特锐德预计上半年净利润为3.92亿元至4.58亿元，同比增长20%至40%；截至6月底，公司运营公共充电终端约96万台，上半年充电量约126亿度，同比增长约47%。截至7月30日，协鑫能科、特锐德、中恒电气等年内涨幅均超20%，其中协鑫能科年内累计上涨38.52%。此外，金杯电工、大洋电机、双杰电气、盛弘股份、许继电气、国电南自、众业达等个股滚动市盈率相对较低。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "20:03 特锐德公告，拟使用自有资金以集中竞价交易方式回购公司股份，回购资金总额不低于人民币3亿元（含）且不超过人民币6亿元（含），回购价格不超过50元/股，回购期限自董事会审议通过之日起12个月内。回购股份将用于股权激励或员工持股计划。",
          "tags": [
            "快讯"
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
      "valuation_history_from": "20210803",
      "current_price": 35.1,
      "price": 35.1,
      "ma5": 34.26,
      "ma10": 34.81,
      "ma20": 33.72,
      "dist_ma5_pct": 2.4,
      "dist_ma10_pct": 0.8,
      "dist_ma20_pct": 4.1,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9577,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.96,
        "pct_float": 3.03,
        "chg5_pct": -0.11,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "688536.SH",
      "fetch_time": "2026-08-03T11:35:52+0800",
      "name": "思瑞浦",
      "pe": 115.8744,
      "pb": 4.8037,
      "ps_ttm": 12.5713,
      "pcf_ttm": 95.5618,
      "valuation_percentile": 34.03,
      "total_shares": 138075483,
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
        "5G应用指数",
        "半导体产业指数",
        "5G指数",
        "专精特新小巨人主题指数",
        "股权激励指数",
        "芯片指数",
        "半导体精选指数",
        "专精特新小巨人指数",
        "AIPC指数",
        "智能家居指数",
        "预期提升指数",
        "模拟芯片指数",
        "苏州工业园区指数"
      ],
      "score_company": 8.2,
      "score_trend": 6.9,
      "score_value": 7.3,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 577% ，利润成长性强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 153% ，净利润现金含量较高。"
        },
        {
          "tag": "订单",
          "text": "合同负债 2459万元 ，较上期增长 43% ，占2025年营收 1.1% ，在手订单充足。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 11% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年07月01日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "商誉",
          "text": "商誉占净资产 11% ，商誉减值风险较高。"
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
          "content": "05:59 思瑞浦发布关于2026年限制性股票激励计划内幕信息知情人买卖公司股票情况的自查报告。经核查，在自查期间（2026年1月14日至2026年7月13日），有5名核查对象存在买卖公司股票行为，系基于个人判断，不存在利用内幕信息交易的情形。\n公司董事会确认未发现内幕信息泄露及内幕交易行为。此外，公司第四届董事会第十三次会议审议通过了向激励对象授予限制性股票的议案，确定2026年7月29日为授予日，以201元/股的价格向113名激励对象授予1,338,500股限制性股票。\n公司2026年第三次临时股东会审议通过了《关于公司2026年限制性股票激励计划（草案）》及其摘要、考核管理办法及授权董事会办理相关事宜的议案。会议表决程序及结果合法有效。\n公司披露限制性股票授予公告，授予日为2026年7月29日，授予数量1,338,500股，占总股本的0.9694%，授予价格为201元/股。\n董事会经核查，公司及激励对象均未出现法律法规规定的不得实施或参与股权激励的情形，授予条件已成就。\n董事会薪酬与考核委员会同意本次激励计划的授予日及授予价格。限制性股票有效期最长不超过48个月，并设置了相应的归属限制。\n本次激励对象不包括独立董事及持股5%以上股东或实际控制人。董事会薪酬与考核委员会确认激励对象名单符合相关法律法规及公司激励计划规定。\n参与本次激励计划的董事及高级管理人员在授予前6个月内无卖出公司股票行为。公司采用Black-Scholes模型测算限制性股票公允价值，相关股份支付费用将在有效期内摊销，具体影响以年度审计报告为准。\n上海兰迪律师事务所出具法律意见书，认为公司本次限制性股票授予事项已取得必要批准，授予条件已成就，相关程序及信息披露符合法律法规规定。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "思瑞浦：国浩律师（上海）事务所关于思瑞浦微电子科技（苏州）股份有限公司2026年第三次临时股东会之法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "思瑞浦：上海兰迪律师事务所关于思瑞浦微电子科技（苏州）股份有限公司2026年限制性股票激励计划授予限制性股票的法律意见书",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1530764511,
      "revenue_yoy": 0.804682,
      "operating_profit": 130208206.38,
      "operating_profit_yoy": 2.347147,
      "net_profit": 126009880.99,
      "net_profit_yoy": 2.276357,
      "gross_profit": 711263254.49,
      "gross_profit_yoy": 0.695221,
      "cogs": 819501256.51,
      "gross_margin": 46.46,
      "pe_forward": null,
      "valuation_history_days": 305,
      "valuation_history_from": "20220922",
      "current_price": 223.0,
      "price": 223.0,
      "ma5": 232.55,
      "ma10": 240.9,
      "ma20": 273.24,
      "dist_ma5_pct": -4.1,
      "dist_ma10_pct": -7.4,
      "dist_ma20_pct": -18.4,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.942,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.96,
        "pct_float": 3.62,
        "chg5_pct": -2.36,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "603162.SH",
      "fetch_time": "2026-08-03T11:35:54+0800",
      "name": "海通发展",
      "pe": 16.3312,
      "pb": 3.0217,
      "ps_ttm": 2.4086,
      "pcf_ttm": 8.9701,
      "valuation_percentile": 40.21,
      "total_shares": 1376022580,
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
      "score_trend": 8.6,
      "score_value": 7.1,
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
          "tag": "股东",
          "text": "北向资金持股 7.7% ，很受外资机构青睐；公募基金持股 12% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 94% 的股票，走势较强。"
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
          "content": "2026/09/29解禁9.33亿股，占总股本67.80%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-29"
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
        },
        {
          "content": "2026/05/23至2026/07/31，公司累计回购 123万股(股权激励注销)，占总股本比例为 0.09% ，最高成交价为 3.73元/股 ，最低成交价为 2.71元/股 ，耗资 388万元  （已完成）",
          "tags": [
            "公司回购限售股"
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
      "valuation_history_days": 323,
      "valuation_history_from": "20250331",
      "current_price": 10.88,
      "price": 10.88,
      "ma5": 10.81,
      "ma10": 10.84,
      "ma20": 10.45,
      "dist_ma5_pct": 0.6,
      "dist_ma10_pct": 0.4,
      "dist_ma20_pct": 4.2,
      "iv_proxy": {
        "primary_name": "500ETF",
        "iv_rank": 0.9365,
        "sizing": "tight"
      }
    },
    {
      "code": "002203.SZ",
      "fetch_time": "2026-08-03T11:35:54+0800",
      "name": "海亮股份",
      "pe": 40.9247,
      "pb": 2.5232,
      "ps_ttm": 0.4881,
      "pcf_ttm": null,
      "valuation_percentile": 77.39,
      "total_shares": 2291755274,
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
        "有色金属指数",
        "工业金属精选指数",
        "铜产业指数",
        "铜冶炼指数",
        "再生金属指数",
        "涉矿指数"
      ],
      "score_company": 7.8,
      "score_trend": 7.6,
      "score_value": 4.1,
      "highlights": [
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.3% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 6家 机构给出评级，其中 83% 为“买入”，距目标价的上涨空间为 28% 。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 4.0% ，很受外资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近6月，股价涨幅超过A股市场 93% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月23日大跌 -7.22% ，且成交额为近20日均值的 1.6倍 ，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月23日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "毛利",
          "text": "毛利率为 4.0% ，行业处于衰退期，或企业缺乏竞争力。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比为 -177% ，净利润现金含量较低。"
        },
        {
          "tag": "偿债",
          "text": "现金短债比为 0.22 ，带息债务占全部投入资本 57% ，现金保障很弱，偿债压力很大。"
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
          "content": "15:00 今天大涨的原因可能是控股股东海亮集团拟增持6亿至10亿元公司股份，且已获建设银行8.6亿元专项贷款支持，增持计划彰显大股东信心并带来资金面利好。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "09:46 7月30日，A股三大指数集体低开，沪指跌0.43%，深成指跌0.93%，创业板指跌1.40%，科创50跌1.51%。盘面上，黄金、油气、有色金属、煤炭板块涨幅居前；电子、电力设备、计算机、机械设备、商贸零售板块跌幅居前。受隔夜美股半导体板块下挫影响，科技板块表现较弱。全市场上涨家数不足两成。隔夜美联储维持利率不变，美股三大股指显著下跌。国内方面，央行预告合计投放2.1万亿元隔夜逆回购，九部门联合印发科技金融数据开发利用通知。此外，中际旭创、京东方A、海亮股份、兆易创新等公司披露回购增持方案。\n今日A股三大指数集体低开，科创50与创业板指跌幅居前。受美股半导体板块重挫及美债收益率上升影响，电子、电力设备板块领跌。央行预告合计2.1万亿元逆回购护航流动性，多家龙头公司披露大额回购增持方案。机构认为短期市场或维持震荡再平衡，科技主线受外部扰动，低位板块轮动修复有望延续。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "海亮股份：天健审〔2026〕17336号",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "海亮股份：甘肃海亮_评估报告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 65017794738.56,
      "revenue_yoy": -0.045557,
      "operating_profit": 1087241929.18,
      "operating_profit_yoy": 0.438629,
      "net_profit": 915882617.63,
      "net_profit_yoy": 0.168721,
      "gross_profit": 2475752883.86,
      "gross_profit_yoy": 0.128395,
      "cogs": 62542041854.7,
      "gross_margin": 3.81,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210803",
      "current_price": 18.37,
      "price": 18.37,
      "ma5": 17.65,
      "ma10": 17.82,
      "ma20": 18.63,
      "dist_ma5_pct": 4.1,
      "dist_ma10_pct": 3.1,
      "dist_ma20_pct": -1.4,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.11,
        "pct_float": 2.49,
        "chg5_pct": 2.91,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "603127.SH",
      "fetch_time": "2026-08-03T11:35:54+0800",
      "name": "昭衍新药",
      "pe": 61.7368,
      "pb": 3.6098,
      "ps_ttm": 18.1239,
      "pcf_ttm": 60.2816,
      "valuation_percentile": 41.78,
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
        "CRO指数"
      ],
      "score_company": 8.2,
      "score_trend": 8.5,
      "score_value": 6.3,
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
          "content": "20:00 7月27日，A股医疗板块反弹，医疗ETF（512170）收涨2.54%，港股通医疗ETF华宝（159137）收涨1.06%。个股方面，脑机接口及CXO概念表现活跃，三博脑科涨12.71%，昭衍新药、美好医疗涨超9%，泰格医药涨4.35%；港股微创机器人-B收涨6.23%，微创脑科学涨4.24%。消息面上，美国Science Corp.视网膜芯片获批在欧盟销售。国内方面，科研团队实现跨地域千人同步脑电信号采集，政策层面《国民健康“十五五”规划》提出加强脑机接口科技攻关。光大证券认为，随着政策发布、临床推进及技术迭代，今年有望成为脑机接口商业化落地元年，建议关注创新药产业链及创新医疗器械。\n风险提示：文中指数成份股仅作展示，不构成投资建议。基金管理人评估的港股通医疗ETF华宝、医疗ETF华宝联接基金风险等级为R4，医疗ETF华宝风险等级为R3。投资人须对自主决定的投资行为负责，基金过往业绩不代表未来表现。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "17:33 7月27日，A股医疗板块反弹，医疗ETF（512170）收涨2.54%，港股通医疗ETF（159137）收涨1.06%。个股方面，三博脑科涨12.71%，昭衍新药、美好医疗涨超9%，泰格医药涨4.35%；港股微创机器人-B收涨6.23%，微创脑科学涨4.24%。消息面上，美国ScienceCorp.获批在欧盟销售视网膜芯片，为脑机接口设备商业化进展。国内方面，科研团队实现跨地域脑电信号采集，政策层面《国民健康“十五五”规划》提出加强脑机接口科技攻关。光大证券认为，随着政策发布、临床推进及技术迭代，今年有望成为脑机接口商业化落地元年，建议关注创新药产业链及创新医疗器械。\n风险提示：文中指数成份股仅作展示，不构成投资建议。基金管理人评估的港股通医疗ETF华宝、医疗ETF华宝联接基金风险等级为R4，医疗ETF华宝风险等级为R3。投资人须对自主决定的投资行为负责，基金过往业绩不代表未来表现。",
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
      "valuation_history_from": "20210803",
      "current_price": 41.54,
      "price": 41.54,
      "ma5": 44.16,
      "ma10": 45.87,
      "ma20": 45.05,
      "dist_ma5_pct": -5.9,
      "dist_ma10_pct": -9.4,
      "dist_ma20_pct": -7.8,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7766,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.08,
        "pct_float": 2.33,
        "chg5_pct": -12.09,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688652.SH",
      "fetch_time": "2026-08-03T11:35:54+0800",
      "name": "京仪装备",
      "pe": 124.651,
      "pb": 8.8733,
      "ps_ttm": 13.3422,
      "pcf_ttm": 37.4441,
      "valuation_percentile": 88.86,
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
      "score_company": 7.3,
      "score_trend": 7.2,
      "score_value": 3.9,
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
          "content": "13:10 半导体设备午后持续走高，至纯科技涨停，托伦斯逼近20CM涨停，中科飞测、芯源微、拓荆科技、强一股份、京仪装备跟涨。",
          "tags": [
            "快讯"
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
      "valuation_history_days": 161,
      "valuation_history_from": "20251201",
      "current_price": 128.38,
      "price": 128.38,
      "ma5": 137.41,
      "ma10": 144.19,
      "ma20": 170.94,
      "dist_ma5_pct": -6.6,
      "dist_ma10_pct": -11.0,
      "dist_ma20_pct": -24.9,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.942,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 1.85,
        "pct_float": 1.19,
        "chg5_pct": -21.02,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "603156.SH",
      "fetch_time": "2026-08-03T11:35:54+0800",
      "name": "养元饮品",
      "pe": 37.6623,
      "pb": 6.2062,
      "ps_ttm": 8.8983,
      "pcf_ttm": 29.7948,
      "valuation_percentile": 97.62,
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
      "score_company": 7.6,
      "score_trend": 8.1,
      "score_value": 3.4,
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
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月19日 至今陷入调整，资金有出逃可能。"
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
          "content": "16:06 汤臣倍健发布公告，出资1.3亿元间接持有DeepSeek 0.04%股权。开润股份亦披露出资4000万元持有DeepSeek 0.0114%股权。根据公告测算，DeepSeek本轮估值在3250亿至3509亿元区间。\n汤臣倍健通过投资天津砺思星灵创业投资合伙企业间接参与DeepSeek融资。该基金由砺思资本管理，合伙人包括多家国资及金融机构。汤臣倍健通过多层持股结构，最终持有DeepSeek约0.04%股权。\n汤臣倍健通过关联交易认购月之暗面母公司Moonshot AI Ltd股权，并追加投资。此外，公司今年4月起通过基金间接投资阶跃星辰、XG TECH及原粒半导体，合计投入约4.5亿元。截至2025年末，公司货币资金为24.49亿元，资产负债率为19.95%。\n除汤臣倍健外，莲花味精、养元饮品、国投中鲁、金字火腿、千味央厨等消费企业近期亦通过投资或收购方式布局AI、算力及半导体领域。部分企业因跨界投资面临主业协同不足及现金流压力。\n一级市场估值回归背景下，传统企业跨界AI投资的最终回报仍存在不确定性。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "16:06 汤臣倍健发布公告，出资1.3亿元间接持有DeepSeek 0.04%股权。此前，开润股份亦披露出资4000万元持有DeepSeek 0.0114%股权。根据公告数据测算，DeepSeek本轮估值在3250亿至3509亿元区间。自今年4月起，汤臣倍健已累计投入约4.5亿元，布局包括Kimi、DeepSeek、阶跃星辰在内的多家大模型企业及硬科技芯片公司。\n汤臣倍健通过投资天津砺思星灵创业投资合伙企业间接参与DeepSeek融资。该基金由砺思资本管理，汤臣倍健出资1.3亿元，占基金总规模的19.12%。通过多层穿透，汤臣倍健最终持有DeepSeek约0.04%股权。\n汤臣倍健通过自有资金认购月之暗面母公司Moonshot AI Ltd发行的认股权证，持股0.11%。此外，其全资子公司香港佰瑞通过认购投资基金份额，间接追加投资月之暗面，两笔合计持有月之暗面0.12%股权。公告显示，因公司实控人梁允超亲属孙晋瑜间接持有标的公司股权，上述交易构成关联交易。此外，汤臣倍健今年还通过基金投资了阶跃星辰、XG TECH及原粒半导体。\n汤臣倍健AI领域投资总额约4.5亿元，占公司2025年末货币资金比例不到14%。除汤臣倍健外，莲花味精、养元饮品、国投中鲁、金字火腿、千味央厨等消费企业近期也通过投资或收购方式布局AI、算力及半导体等领域。\n传统行业企业跨界布局AI，反映了在主业增长压力下，企业寻求新增长点的诉求。然而，跨界投资面临技术资源匮乏及重资产投入等风险，部分企业已出现投资项目进展不及预期或资金周转压力等情况。",
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
      "valuation_history_from": "20210803",
      "current_price": 38.73,
      "price": 38.73,
      "ma5": 37.58,
      "ma10": 36.41,
      "ma20": 39.96,
      "dist_ma5_pct": 3.1,
      "dist_ma10_pct": 6.4,
      "dist_ma20_pct": -3.1,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7766,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.72,
        "pct_float": 0.97,
        "chg5_pct": 8.32,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "688401.SH",
      "fetch_time": "2026-08-03T11:35:54+0800",
      "name": "路维光电",
      "pe": 45.2635,
      "pb": 4.7403,
      "ps_ttm": 10.0424,
      "pcf_ttm": 41.5971,
      "valuation_percentile": 71.51,
      "total_shares": 205369700,
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
          "name": "半导体材料",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "专精特新小巨人主题指数",
        "半导体精选指数",
        "专精特新小巨人指数",
        "可转债正股指数",
        "IPO现场检查指数"
      ],
      "score_company": 7.6,
      "score_trend": 7.0,
      "score_value": 5.0,
      "highlights": [
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 25% ，最新季度归母净利润同比增长 39% ，成长能力很强。"
        },
        {
          "tag": "ROE",
          "text": "近5年，净资产收益率为 12% ，获取收益的能力较强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 150% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 4.6% ，未来产能扩张后，营收有望进一步增长。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "2027/01/15解禁1202.02万股，占总股本5.85%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2027-01-15"
        },
        {
          "content": "预计2026/08/26发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-26"
        },
        {
          "content": "路维光电：国信证券股份有限公司关于深圳市路维光电股份有限公司调整2026年度向特定对象发行股票募投项目拟投入募集资金金额的核查意见",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "路维光电：国信证券股份有限公司关于深圳市路维光电股份有限公司使用2026年度向特定对象发行股票募集资金向全资子公司提供无息借款以实施募投项目的核查意见",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "路维光电：国信证券股份有限公司关于深圳市路维光电股份有限公司使用自有资金方式支付募投项目所需资金并以募集资金等额置换的核查意见",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 827000185.91,
      "revenue_yoy": 0.372465,
      "operating_profit": 198550012.1,
      "operating_profit_yoy": 0.435106,
      "net_profit": 171750546.26,
      "net_profit_yoy": 0.413717,
      "gross_profit": 286227171.54,
      "gross_profit_yoy": 0.377143,
      "cogs": 540773014.37,
      "gross_margin": 34.61,
      "pe_forward": null,
      "valuation_history_days": 470,
      "valuation_history_from": "20240819",
      "current_price": 60.43,
      "price": 60.43,
      "ma5": 62.45,
      "ma10": 63.95,
      "ma20": 73.21,
      "dist_ma5_pct": -3.2,
      "dist_ma10_pct": -5.5,
      "dist_ma20_pct": -17.5,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.942,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.26,
        "pct_float": 4.5,
        "chg5_pct": -11.3,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688041.SH",
      "fetch_time": "2026-08-03T11:35:54+0800",
      "name": "海光信息",
      "pe": 228.5963,
      "pb": 26.9196,
      "ps_ttm": 38.9232,
      "pcf_ttm": null,
      "valuation_percentile": 85.86,
      "total_shares": 2324338091,
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
        "科技龙头指数",
        "双创100指数",
        "茅指数",
        "人工智能+指数",
        "半导体产业指数",
        "专精特新小巨人主题指数",
        "信创产业指数",
        "新质生产力指数",
        "股权激励指数",
        "芯片指数",
        "半导体精选指数"
      ],
      "score_company": 8.8,
      "score_trend": 7.7,
      "score_value": 4.1,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 数字芯片设计 行业龙头企业。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 51% ，最新季度归母净利润同比增长 55% ，成长能力很强。"
        },
        {
          "tag": "评级",
          "text": "近90天， 13家 机构给出评级，其中 77% 为“买入”，距目标价的上涨空间为 62% 。"
        },
        {
          "tag": "预测",
          "text": " 7家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 9.1% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 95% 的股票，走势较强。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/20发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-20"
        },
        {
          "content": "19:51 2026年7月30日，中共中央政治局会议将“扎实推进六张网规划建设”列为下半年经济工作要点。国家发展改革委政策研究室主任、新闻发言人蒋毅在7月31日新闻发布会上指出，据有关机构测算，“十五五”时期算力网建设将新增直接投资4万亿元。算力网正式与水网、新型电网、新一代通信网等并列，成为国家顶层基础设施统筹布局的重要组成部分。算力产业正从硬件投资时代，逐步进入网络化、平台化、运营化的新阶段。\n算力网的政策定位已从区域工程演进为国家基础设施。2026年，算力网被正式纳入国家“六张网”建设，并列入“十五五”重大工程项目谋划范围。国家数据局等部门已部署国家数据基础设施建设路径，并明确加大中央财政投入，利用超长期特别国债资金支持建设。目前，“全国一体化算力网监测调度试验验证平台”已初步建成，实现对“东数西算”八大枢纽十大集群、三大运营商、超算互联网及部分非枢纽地区算力资源的统一监测，覆盖全国超过900个算力基础设施。\n2026年3月，“算电协同”首次写入政府工作报告，旨在形成“以电强算、以算促电”的良性循环。国家发改委明确多网协同逻辑：新型电网提供电力供应，算力网指挥电网智能化调度，通信网支撑算力跨区域调度。当前算力产业面临利用率低、东西部资源失衡及定价体系不统一等痛点，算力网建设旨在通过“算力池化”实现按需取用，并推动计量标准统一。\n算力产业竞争焦点正从硬件囤积转向资源组织能力。运营商方面，中国移动、中国电信、中国联通正加速向“云网算力服务商”转型。2025年，中国移动算力服务收入898亿元，智算服务收入增速达279%；中国电信天翼云收入1207亿元，AIDC收入345亿元；中国联通人工智能业务收入增长超140%。2026年，三大运营商在算力基础设施投入上持续加码，算力相关资本开支占比显著提升。\n云服务商正从算力资源提供者向AI生产力平台转型。腾讯2026年一季度资本开支319.36亿元，同比增加16%；阿里2026财年四季度资本支出269亿元，AI相关产品收入占比首破30%；字节跳动2026年AI资本开支预算增至2000亿元。此外，围绕算力资源流通的新型服务商出现，如贵州“大衍”算力调度平台，截至2026年6月累计交易额超258亿元。\n算力产业链中，AI芯片、AI服务器及光模块等环节已进入业绩兑现期。国产AI芯片方面，华为、阿里平头哥、寒武纪等厂商市场份额提升。寒武纪2026年一季度净利10.13亿元，同比增加185%；海光信息上半年预计归母净利17亿至18.3亿元。AI服务器领域，工业富联预计上半年归母净利234亿至244亿元，浪潮信息预计上半年归母净利26亿至31亿元，紫光股份预计上半年净利19.1亿至23.2亿元。\n光模块环节，中际旭创2026年一季度归母净利57.35亿元，同比增加262%；新易盛预计上半年归母净利70亿至80亿元；光迅科技预计上半年归母净利5.59亿至6.15亿元。此外，存储环节受AI服务器需求拉动，佰维存储预计2026年上半年净利70亿至75亿元，实现扭亏。\n算力租赁与液冷技术领域表现分化。算力租赁方面，利通电子一季度归母净利2.71亿元，同比增加821%；协创数据一季度归母净利7.50亿元，同比增加343.45%；中科曙光一季度归母净利2.28亿元，同比增加22.19%；润泽科技一季度扣非归母净利5.82亿元，同比增加35.92%。液冷技术方面，英维克一季度归母净利同比下降81.97%，显示赛道竞争加剧。\n算力交易平台与算电协同仍处于商业模式探索期。云赛智联、中科曙光等参与算力交易平台建设。算电协同方面，全国已形成3个算电协同发展区域，如中国移动中卫云基地已实现绿电直供。随着政策支持力度加大，这些领域有望成为算力经济的新增长极。\n本文内容基于公开信息整理，涉及公司业绩均为2026年半年度预告或估算数据，最终以正式公告为准。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "19:30 7月28日，达梦数据与海光信息正式签署战略合作协议。双方将联合创新研发，持续推进处理器芯片与数据库深度联调适配、性能迭代优化，联合攻坚前沿底层技术，打造软硬协同一体化基础软件算力方案；深耕重点行业，聚力金融、能源、电力、医疗等关键领域，加快软硬件一体化方案在核心业务场景规模化落地；协同拓展市场，联合打造标准化联合产品，提升国产一体化方案市场竞争力，健全自主信息技术产业生态。（人民财讯）",
          "tags": [
            "快讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 9489974831.12,
      "revenue_yoy": 0.54647,
      "operating_profit": 2839090510.78,
      "operating_profit_yoy": 0.31509,
      "net_profit": 2840528700.64,
      "net_profit_yoy": 0.348254,
      "gross_profit": 5703213623.21,
      "gross_profit_yoy": 0.416017,
      "cogs": 3786761207.91,
      "gross_margin": 60.1,
      "pe_forward": null,
      "valuation_history_days": 464,
      "valuation_history_from": "20240812",
      "current_price": 277.0,
      "price": 277.0,
      "ma5": 289.26,
      "ma10": 306.88,
      "ma20": 324.17,
      "dist_ma5_pct": -4.2,
      "dist_ma10_pct": -9.7,
      "dist_ma20_pct": -14.6,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.942,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 86.4,
        "pct_float": 1.34,
        "chg5_pct": 1.64,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "688981.SH",
      "fetch_time": "2026-08-03T11:35:54+0800",
      "name": "中芯国际",
      "pe": 200.3809,
      "pb": 5.3099,
      "ps_ttm": 14.7297,
      "pcf_ttm": 38.3196,
      "valuation_percentile": 82.48,
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
        "HALO指数",
        "TMT指数",
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
      "score_trend": 7.8,
      "score_value": 3.9,
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
          "text": "近90天， 9家 机构给出评级，其中 67% 为“买入”，距目标价的上涨空间为 38% 。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 18% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 89% 的股票，走势较强。"
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
          "content": "中芯国际：中芯国际关于召开2026年第二季度业绩说明会的预告公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "17:31 南向资金今日净卖出55.89亿港元。中芯国际、小米集团-W分别遭净卖出20.08亿港元、19.47亿港元；阿里巴巴-W、腾讯控股分别获净买入约13.26亿港元、8.32亿港元。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "中芯国际：上海兰迪律师事务所关于中芯国际集成电路制造有限公司2021年科创板限制性股票激励计划预留授予部分第四个归属期归属条件成就暨作废部分限制性股票的法律意见书",
          "tags": [
            "重要公告"
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
      "valuation_history_days": 326,
      "valuation_history_from": "20220718",
      "current_price": 123.99,
      "price": 123.99,
      "ma5": 131.67,
      "ma10": 140.68,
      "ma20": 148.35,
      "dist_ma5_pct": -5.8,
      "dist_ma10_pct": -11.9,
      "dist_ma20_pct": -16.4,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.942,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 109.75,
        "pct_float": 4.43,
        "chg5_pct": -3.39,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300373.SZ",
      "fetch_time": "2026-08-03T11:35:57+0800",
      "name": "扬杰科技",
      "pe": 32.3452,
      "pb": 4.5996,
      "ps_ttm": 5.7716,
      "pcf_ttm": 27.4306,
      "valuation_percentile": 49.4,
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
        "集成电路指数",
        "半导体精选指数",
        "GDR指数",
        "中小创蓝筹指数",
        "晶圆产业指数",
        "华为合作半导体企业指数",
        "IGBT指数",
        "汽车芯片指数"
      ],
      "score_company": 8.2,
      "score_trend": 6.8,
      "score_value": 5.7,
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
      "risks": [],
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
      "valuation_history_from": "20210803",
      "current_price": 83.92,
      "price": 83.92,
      "ma5": 86.29,
      "ma10": 89.69,
      "ma20": 104.49,
      "dist_ma5_pct": -2.8,
      "dist_ma10_pct": -6.4,
      "dist_ma20_pct": -19.7,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9577,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 15.77,
        "pct_float": 3.47,
        "chg5_pct": 2.84,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "002138.SZ",
      "fetch_time": "2026-08-03T11:35:57+0800",
      "name": "顺络电子",
      "pe": 35.4047,
      "pb": 5.2973,
      "ps_ttm": 4.7125,
      "pcf_ttm": 22.757,
      "valuation_percentile": 56.95,
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
        "珠三角指数",
        "新基建指数",
        "5G指数",
        "员工持股指数",
        "元宇宙指数",
        "AI手机指数",
        "养老金指数",
        "元宇宙主题指数",
        "基站指数",
        "智能手表指数",
        "小米产业链指数",
        "元件精选指数"
      ],
      "score_company": 8.4,
      "score_trend": 5.6,
      "score_value": 5.4,
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
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 6.9% ，很受外资机构青睐；公募基金持股 5.5% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "偿债",
          "text": "现金短债比为 0.25 ，货币资金对短期债务的保障较弱。"
        }
      ],
      "events": [
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
        },
        {
          "content": "18:35 顺络电子公告，2026年上半年营业收入38.59亿元，同比增长19.67%。归属于上市公司股东的净利润4.47亿元，同比下降7.98%。归属于上市公司股东的扣除非经常性损益的净利润4.34亿元，同比下降6.21%。公司计划不派发现金红利，不送红股，不以公积金转增股本。",
          "tags": [
            "快讯"
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
      "valuation_history_from": "20210803",
      "current_price": 42.8,
      "price": 42.8,
      "ma5": 42.58,
      "ma10": 42.23,
      "ma20": 47.58,
      "dist_ma5_pct": 0.5,
      "dist_ma10_pct": 1.4,
      "dist_ma20_pct": -10.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 14.27,
        "pct_float": 4.35,
        "chg5_pct": 2.87,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "000739.SZ",
      "fetch_time": "2026-08-03T11:35:57+0800",
      "name": "普洛药业",
      "pe": 25.9326,
      "pb": 3.6723,
      "ps_ttm": 2.4324,
      "pcf_ttm": 16.9904,
      "valuation_percentile": 57.92,
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
      "score_trend": 8.1,
      "score_value": 5.6,
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
          "text": "近3月，股价涨幅超过A股市场 97% 的股票，走势很强。"
        },
        {
          "tag": "增持",
          "text": "近3月，控股股东累计实际增持 606万股 ，占总股本比例 0.52% ，金额合计 1.0亿元 。"
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
          "content": "15:00 今天大涨的原因可能是普洛药业子公司与药明生物、多宁生物签署战略合作协议，将推动生物大分子药物管线开发及CDMO能力建设，有望带来新业务增长。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "17:03 普洛药业公告，公司控股子公司浙江普洛康裕制药有限公司近日收到国家药品监督管理局签发的左卡尼汀口服溶液《药品注册证书》，规格为10ml：1g和10ml：2g。左卡尼汀口服溶液用于治疗原发性系统性卡尼汀缺乏症，也用于先天性代谢异常导致的继发性卡尼汀缺乏症的短期和长期治疗。根据相关数据显示，左卡尼汀2025年度国内市场规模约为4067万支，销售金额约为2.98亿元。该产品按照化学药品4类获批上市，视同通过仿制药一致性评价。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "普洛药业：关于获得化学原料药欧洲CEP证书的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "09:34股价达到 19.58 元，创近24个月新高",
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
      "valuation_history_from": "20210803",
      "current_price": 20.22,
      "price": 20.22,
      "ma5": 20.17,
      "ma10": 20.21,
      "ma20": 19.57,
      "dist_ma5_pct": 0.2,
      "dist_ma10_pct": 0.0,
      "dist_ma20_pct": 3.3,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.8337,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 1.74,
        "pct_float": 0.74,
        "chg5_pct": 3.25,
        "net5_repay_days": 4,
        "signal": "adding"
      }
    },
    {
      "code": "600885.SH",
      "fetch_time": "2026-08-03T11:35:57+0800",
      "name": "宏发股份",
      "pe": 28.3188,
      "pb": 4.1781,
      "ps_ttm": 2.7771,
      "pcf_ttm": 24.5615,
      "valuation_percentile": 37.0,
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
        "新能源汽车指数",
        "养老金指数",
        "预期提升指数",
        "特斯拉指数",
        "数字能源指数",
        "借壳上市指数",
        "宁德时代产业链指数",
        "智能交通指数",
        "电动物流车指数",
        "共享汽车指数",
        "特高压指数",
        "智能电网指数"
      ],
      "score_company": 9.4,
      "score_trend": 9.0,
      "score_value": 6.7,
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
          "tag": "预测",
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 20% ，很受外资机构青睐；公募基金持股 8.6% ，很受内资机构青睐；2026年03月31日至2026年06月30日期间，股东户数减少 39% ，大资金买入。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 95% 的股票，走势较强。"
        }
      ],
      "risks": [],
      "events": [
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
          "content": "18:02 宏发股份(600885)发布2026年半年报，上半年营业收入110.22亿元，同比增长32.05%；归母净利润11.56亿元，同比增长19.9%；扣非归母净利润11.02亿元，同比增长18.97%；经营现金流净额1.14亿元，同比下降86.3%；EPS为0.7469元。其中第二季度营业收入59.1亿元，同比增长35.5%；归母净利润6.72亿元，同比增长21.4%；扣非归母净利润6.53亿元，同比增长19.5%；EPS为0.434元。截至二季度末，公司总资产256.8亿元，归母净资产132.12亿元。报告期内，公司继电器产品在消费电子、工业装备、电力能源及新能源汽车领域业务规模实现增长，并推进低压电器、薄膜电容器等新产品发展，上半年完成566项新品研发。",
          "tags": [
            "资讯"
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
      "valuation_history_from": "20210803",
      "current_price": 35.51,
      "price": 35.51,
      "ma5": 34.42,
      "ma10": 33.95,
      "ma20": 34.45,
      "dist_ma5_pct": 3.2,
      "dist_ma10_pct": 4.6,
      "dist_ma20_pct": 3.1,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7766,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.36,
        "pct_float": 0.79,
        "chg5_pct": -19.61,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688777.SH",
      "fetch_time": "2026-08-03T11:35:57+0800",
      "name": "中控技术",
      "pe": 188.3794,
      "pb": 7.6016,
      "ps_ttm": 9.3598,
      "pcf_ttm": 276.726,
      "valuation_percentile": 75.25,
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
        "人工智能指数",
        "工业4.0指数",
        "机器人指数",
        "DeepSeek指数",
        "新型工业化指数",
        "工业软件指数",
        "触板指数"
      ],
      "score_company": 8.2,
      "score_trend": 8.2,
      "score_value": 4.6,
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
      "valuation_history_days": 297,
      "valuation_history_from": "20221125",
      "current_price": 93.12,
      "price": 93.12,
      "ma5": 83.6,
      "ma10": 85.48,
      "ma20": 93.0,
      "dist_ma5_pct": 11.4,
      "dist_ma10_pct": 8.9,
      "dist_ma20_pct": 0.1,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.942,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 25.95,
        "pct_float": 3.54,
        "chg5_pct": -8.54,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "601168.SH",
      "fetch_time": "2026-08-03T11:35:57+0800",
      "name": "西部矿业",
      "pe": 15.1215,
      "pb": 4.0082,
      "ps_ttm": 1.2928,
      "pcf_ttm": 6.6318,
      "valuation_percentile": 87.65,
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
        "锂电池指数",
        "有色金属指数",
        "预期提升指数",
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
      "score_trend": 9.8,
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
          "text": "北向资金持股 5.5% ，很受外资机构青睐；公募基金持股 6.4% ，很受内资机构青睐；2026年05月08日至2026年07月20日期间，股东户数减少 30% ，大资金买入。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 98% 的股票，走势很强。"
        },
        {
          "tag": "增持",
          "text": "近6月，控股股东累计实际增持 2544万股 ，占总股本比例 1.1% ，金额合计 7.4亿元 。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "06:00 西部矿业发布2026年半年度报告，上半年实现营业收入394.43亿元，同比增长25%；利润总额71.06亿元，同比增长83%；归属于上市公司股东的净利润41.69亿元，同比增长123%。公司表示，业绩增长主要受益于有色金属市场价格上移及主营产品产量稳定，同时硫酸、硫磺等副产品价格上涨也增厚了利润。上半年公司矿产铜8.97万吨、矿产锌6.39万吨、矿产铅2.95万吨、矿产钼0.24万吨、铁精粉70.66万吨。公司正推进玉龙铜矿扩建及茶亭铜矿等项目建设。玉龙铜业作为核心支撑，目前正推进4500万吨/年生产规模扩建工程预可研及配套基础设施建设。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "02:11 西部矿业发布2026年半年度报告摘要，报告未经审计。董事会审议通过了2026年半年度报告。\n董事会审议通过了修订《公司章程》、《股东会议事规则》、《董事会议事规则》、《信息披露管理办法》、《关联交易管理办法》、《董事和高级管理人员薪酬管理制度》以及相关工作细则的议案，并将提请2026年第三次临时股东会审议。\n董事会审议通过了修订董事会各专门委员会工作细则的议案，并批准了《关于公司控股子公司西部矿业集团财务有限公司的风险持续评估报告》。此外，董事会提名王海丰、赵福康、周华荣、王伟为第九届董事会非独立董事候选人。\n董事会提名秦嘉龙、李计发、王正文、周科平为第九届董事会独立董事候选人，并决定于2026年8月14日召开2026年第三次临时股东会。\n第九届董事会非独立董事候选人简历：王海丰现任公司董事长；赵福康现任公司副董事长；周华荣现任公司总裁；王伟现任公司董事、财务负责人、董事会秘书。\n第九届董事会独立董事候选人简历：秦嘉龙、李计发、王正文、周科平均为现任公司独立董事。\n公司发布关于修订《公司章程》的公告，并通知将于2026年8月14日召开2026年第三次临时股东会，审议相关议案。\n股东会采取现场投票与网络投票相结合的方式，股权登记日为2026年8月14日，审议事项包括董事会换届选举等。\n股东会相关登记方法及累积投票制说明已披露，股东可按规定行使表决权。\n以上为本次公告相关事项。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "西部矿业：独立董事候选人声明与承诺（李计发）",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "西部矿业：独立董事候选人声明与承诺（周科平)",
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
      "valuation_history_from": "20210803",
      "current_price": 38.44,
      "price": 38.44,
      "ma5": 37.32,
      "ma10": 36.3,
      "ma20": 33.59,
      "dist_ma5_pct": 3.0,
      "dist_ma10_pct": 5.9,
      "dist_ma20_pct": 14.4,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7766,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 20.32,
        "pct_float": 2.22,
        "chg5_pct": 5.49,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "601233.SH",
      "fetch_time": "2026-08-03T11:35:57+0800",
      "name": "桐昆股份",
      "pe": 16.2109,
      "pb": 1.3475,
      "ps_ttm": 0.55,
      "pcf_ttm": 6.7697,
      "valuation_percentile": 46.53,
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
        "养老金指数",
        "预期提升指数",
        "石化精选指数",
        "涤纶指数",
        "PTA指数"
      ],
      "score_company": 8.8,
      "score_trend": 8.6,
      "score_value": 5.9,
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
          "text": "近90天， 14家 机构给出评级，其中 86% 为“买入”，距目标价的上涨空间为 45% 。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.0% ，较受外资机构青睐；公募基金持股 6.6% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 95% 的股票，走势较强。"
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
        },
        {
          "content": "回购总金额不超过3453万元，回购最高价不超过7.98元/股 （预案）",
          "tags": [
            "公司回购限售股"
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
      "valuation_history_from": "20210803",
      "current_price": 22.4,
      "price": 22.4,
      "ma5": 21.87,
      "ma10": 21.77,
      "ma20": 21.46,
      "dist_ma5_pct": 2.4,
      "dist_ma10_pct": 2.9,
      "dist_ma20_pct": 4.4,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7766,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.18,
        "pct_float": 1.73,
        "chg5_pct": -4.31,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002056.SZ",
      "fetch_time": "2026-08-03T11:35:57+0800",
      "name": "横店东磁",
      "pe": 18.5064,
      "pb": 3.2731,
      "ps_ttm": 1.4413,
      "pcf_ttm": 9.6243,
      "valuation_percentile": 46.23,
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
        "新能源汽车指数",
        "新材料指数",
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
        "磁悬浮列车指数",
        "钙钛矿电池指数",
        "触板指数"
      ],
      "score_company": 8.5,
      "score_trend": 6.0,
      "score_value": 6.3,
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
      "valuation_history_from": "20210803",
      "current_price": 20.79,
      "price": 20.79,
      "ma5": 20.98,
      "ma10": 21.4,
      "ma20": 24.32,
      "dist_ma5_pct": -0.9,
      "dist_ma10_pct": -2.9,
      "dist_ma20_pct": -14.5,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.81,
        "pct_float": 2.02,
        "chg5_pct": 1.41,
        "net5_repay_days": 3,
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
        "iv_rank": 0.8337,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.03,
        "pct_float": 1.48,
        "chg5_pct": -0.4,
        "net5_repay_days": 2,
        "signal": "neutral"
      },
      "history": [
        {
          "date": "2026-07-29",
          "price": 15.6,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 恒逸石化"
        },
        {
          "date": "2026-07-30",
          "price": 16.05,
          "change_pct": 2.88,
          "action": "HOLD",
          "note": "Thesis intact: H1净利+2326-2547%, 10亿回购支撑. PnL +2.88% in 2 days confirms catalyst traction. Sector 石油石化 neutral — benefiting from rotation out of tech. Stop at ¥14.82 not threatened (8.3% cushion). Margin signal neutral. Only 2 days held — far from time-stop risk."
        },
        {
          "date": "2026-07-31",
          "price": 16.09,
          "change_pct": 3.14,
          "action": "HOLD",
          "note": "+3.14% in 3 days, thesis intact (H1净利+2326-2547%, 文莱炼化, 10亿回购). Sector 石油石化 neutral. Stop at 14.82 safe (7.9% cushion). Days held 3 — far from 10-day time stop."
        }
      ]
    },
    {
      "code": "002916",
      "name": "深南电路",
      "entryDate": "2026-07-31",
      "entryPrice": 308.35,
      "targetPrice": 380.0,
      "stopLoss": 300.21,
      "currentStop": 300.21,
      "thesis": "PCB龙头，100%机构买入评级，目标价+92% upside。AI算力需求驱动高多层板放量，Vera Rubin量产拉动PCB价值量提升。H1业绩Q2环比增长。元件sector #3今日+7.66%。股价在MA5下方-4.7%形成pullback入场机会。",
      "sector": "元件",
      "rps120": 95.23,
      "catalysts": [],
      "shares": 100,
      "allocation_pct": 6.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 16.32,
        "pct_float": 0.8,
        "chg5_pct": -21.55,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      },
      "history": [
        {
          "date": "2026-07-31",
          "price": 308.35,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 深南电路"
        },
        {
          "date": "2026-07-31",
          "price": 308.0,
          "change_pct": -0.11,
          "action": "HOLD",
          "note": "Day 1 entry. -0.11% from entry but +8.26% from prev close — gapped up, entry just poorly timed intraday. WARNING: only 2.53% above stop at 300.21. Prepare sell order. PCB/AI thesis intact."
        }
      ]
    },
    {
      "code": "300373",
      "name": "扬杰科技",
      "entryDate": "2026-07-31",
      "entryPrice": 87.6,
      "targetPrice": 105.0,
      "stopLoss": 83.22,
      "currentStop": 83.22,
      "thesis": "功率半导体龙头，H1预增20-40%，SiC碳化硅收入翻倍。AI服务器+新能源车双驱动。0风险标签。RPS 92.42% sweet spot。股价在MA下方形成pullback入场机会。",
      "sector": "半导体",
      "rps120": 92.42,
      "catalysts": [],
      "shares": 400,
      "allocation_pct": 5.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9577,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 15.77,
        "pct_float": 3.47,
        "chg5_pct": 2.84,
        "net5_repay_days": 2,
        "signal": "adding"
      },
      "history": [
        {
          "date": "2026-07-31",
          "price": 87.6,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 扬杰科技"
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
      "currentStop": 103.45,
      "thesis": "MLCC行业景气爆发：三星电机8/1起全系列MLCC涨价30%，太阳诱电9/1跟进涨价。AI服务器MLCC用量为普通服务器数倍，高端产品供需紧至2027H1。公司7月21日完成8.9亿回购+7月30日再推5-10亿二期回购。上半年业绩预增45-65%。零风险标签。元件sector #3今日+7.66%。",
      "sector": "元件",
      "rps120": 98.09,
      "catalysts": [],
      "shares": 600,
      "allocation_pct": 8.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9577,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 37.43,
        "pct_float": 1.79,
        "chg5_pct": 7.22,
        "net5_repay_days": 2,
        "signal": "adding"
      },
      "history": [
        {
          "date": "2026-07-31",
          "price": 115.07,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 三环集团"
        },
        {
          "date": "2026-07-31",
          "price": 111.68,
          "change_pct": -2.95,
          "action": "HOLD",
          "note": "Day 1 entry. -2.95% from entry — entered at intraday high after gap-up open. MLCC catalyst (三星8/1涨价30%) is fresh. 回购5-10亿 floor. Monitor: if -5% (109.32) fires, sell immediately."
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
      "currentStop": 120.18,
      "thesis": "CXO龙头，A/H溢价-8%(A股折价)。近3月涨幅超98%个股，强势动量。10亿回购+11%北向+15%公募。VCP SETUP：价格在MA5/MA10/MA20的1.5%范围内极致收敛，突破在即。8月4日中报发布（催化剂即将兑现）。零风险。唯一风险：医疗服务sector未进入今日top5，但大概率在top30%。",
      "sector": "医疗服务",
      "rps120": 90.81,
      "catalysts": [],
      "shares": 300,
      "allocation_pct": 5.0,
      "iv_proxy": {
        "primary_name": "50ETF",
        "iv_rank": 0.6318,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 51.52,
        "pct_float": 1.62,
        "chg5_pct": -4.6,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      },
      "history": [
        {
          "date": "2026-07-31",
          "price": 126.5,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 药明康德"
        },
        {
          "date": "2026-07-31",
          "price": 128.43,
          "change_pct": 1.53,
          "action": "HOLD",
          "note": "+1.53% day 1. Strongest position: RPS 90.81% sweet spot, VCP SETUP (within 1.5% of all MAs), 0 risks, 8/4中报 catalyst. A/H折价-7%. 10亿回购+11%北向+15%公募."
        }
      ]
    }
  ],
  "position_prices": {
    "000703": {
      "code": "000703",
      "name": "恒逸石化",
      "date": "2026-08-03",
      "price": 16.23,
      "open": 15.74,
      "high": 16.57,
      "low": 15.3,
      "prev_close": 16.09,
      "change_pct": 0.87,
      "volume": 515194,
      "amount": 823987966.46,
      "source": "sina",
      "mavol30": 8623.93,
      "volume_below_mavol30": false
    },
    "002916": {
      "code": "002916",
      "name": "深南电路",
      "date": "2026-08-03",
      "price": 304.31,
      "open": 303.13,
      "high": 308.0,
      "low": 293.88,
      "prev_close": 308.0,
      "change_pct": -1.2,
      "volume": 61892,
      "amount": 1870425831.73,
      "source": "sina",
      "mavol30": 1213.17,
      "volume_below_mavol30": false
    },
    "300373": {
      "code": "300373",
      "name": "扬杰科技",
      "date": "2026-08-03",
      "price": 81.59,
      "open": 83.0,
      "high": 84.4,
      "low": 80.5,
      "prev_close": 83.92,
      "change_pct": -2.78,
      "volume": 88597,
      "amount": 722587554.54,
      "source": "sina",
      "mavol30": 2277.63,
      "volume_below_mavol30": false
    },
    "300408": {
      "code": "300408",
      "name": "三环集团",
      "date": "2026-08-03",
      "price": 111.73,
      "open": 111.8,
      "high": 116.1,
      "low": 110.0,
      "prev_close": 111.68,
      "change_pct": 0.04,
      "volume": 462666,
      "amount": 5224878436.72,
      "source": "sina",
      "mavol30": 6785.97,
      "volume_below_mavol30": false
    },
    "603259": {
      "code": "603259",
      "name": "药明康德",
      "date": "2026-08-03",
      "price": 127.3,
      "open": 129.2,
      "high": 132.38,
      "low": 126.15,
      "prev_close": 128.43,
      "change_pct": -0.88,
      "volume": 408129,
      "amount": 5259648655.0,
      "source": "sina",
      "mavol30": 6002.5,
      "volume_below_mavol30": false
    }
  },
  "missed_opportunity_prices": [
    {
      "code": "002975",
      "name": "博杰股份",
      "recommended_date": "2026-07-31",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 70.5,
      "return_pct": null
    },
    {
      "code": "000938",
      "name": "紫光股份",
      "recommended_date": "2026-07-31",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 33.3,
      "return_pct": null
    },
    {
      "code": "600428",
      "name": "中远海特",
      "recommended_date": "2026-07-31",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 11.29,
      "return_pct": null
    },
    {
      "code": "601168",
      "name": "西部矿业",
      "recommended_date": "2026-07-31",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 37.71,
      "return_pct": null
    },
    {
      "code": "688256",
      "name": "寒武纪",
      "recommended_date": "2026-07-31",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 1046.17,
      "return_pct": null
    },
    {
      "code": "000988",
      "name": "华工科技",
      "recommended_date": "2026-07-31",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 94.11,
      "return_pct": null
    },
    {
      "code": "688146",
      "name": "中船特气",
      "recommended_date": "2026-07-31",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 268.9,
      "return_pct": null
    },
    {
      "code": "002384",
      "name": "东山精密",
      "recommended_date": "2026-07-31",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 166.9,
      "return_pct": null
    },
    {
      "code": "300502",
      "name": "新易盛",
      "recommended_date": "2026-07-31",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 398.5,
      "return_pct": null
    },
    {
      "code": "688200",
      "name": "华峰测控",
      "recommended_date": "2026-07-30",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 326.66,
      "return_pct": null
    },
    {
      "code": "688361",
      "name": "中科飞测",
      "recommended_date": "2026-07-30",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 310.72,
      "return_pct": null
    },
    {
      "code": "300285",
      "name": "国瓷材料",
      "recommended_date": "2026-07-30",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 59.4,
      "return_pct": null
    },
    {
      "code": "300408",
      "name": "三环集团",
      "recommended_date": "2026-07-30",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 111.73,
      "return_pct": null
    },
    {
      "code": "603259",
      "name": "药明康德",
      "recommended_date": "2026-07-30",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 127.3,
      "return_pct": null
    },
    {
      "code": "688498",
      "name": "源杰科技",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 1153.0,
      "return_pct": null
    },
    {
      "code": "300604",
      "name": "长川科技",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 235.42,
      "return_pct": null
    },
    {
      "code": "002353",
      "name": "杰瑞股份",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 131.99,
      "return_pct": null
    }
  ],
  "iv_sentiment": {
    "date": "2026-08-03",
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
        "data_points": 224,
        "data_points_filtered": 216,
        "current_iv": 0.1854,
        "is_live": false,
        "iv_high": 0.2272,
        "iv_low": 0.1137,
        "iv_high_raw": 0.2625,
        "iv_low_raw": 0.1137,
        "iv_rank": 0.6318,
        "iv_rank_raw": 0.4818,
        "iv_percentile": 0.7593,
        "iv_percentile_raw": 0.7321,
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
          0.2283
        ],
        "name": "50ETF",
        "desc": "大盘蓝筹",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "510300",
        "lookback_days": 252,
        "data_points": 224,
        "data_points_filtered": 217,
        "current_iv": 0.2191,
        "is_live": false,
        "iv_high": 0.2476,
        "iv_low": 0.1201,
        "iv_high_raw": 0.3137,
        "iv_low_raw": 0.069,
        "iv_rank": 0.7766,
        "iv_rank_raw": 0.6134,
        "iv_percentile": 0.894,
        "iv_percentile_raw": 0.875,
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
          0.1092,
          0.2492
        ],
        "name": "300ETF",
        "desc": "沪深300",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "510500",
        "lookback_days": 252,
        "data_points": 224,
        "data_points_filtered": 215,
        "current_iv": 0.3471,
        "is_live": false,
        "iv_high": 0.3575,
        "iv_low": 0.194,
        "iv_high_raw": 0.4544,
        "iv_low_raw": 0.107,
        "iv_rank": 0.9365,
        "iv_rank_raw": 0.6911,
        "iv_percentile": 0.9721,
        "iv_percentile_raw": 0.942,
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
          0.1736,
          0.3597
        ],
        "name": "500ETF",
        "desc": "中证500",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "588000",
        "lookback_days": 252,
        "data_points": 224,
        "data_points_filtered": 216,
        "current_iv": 0.612,
        "is_live": false,
        "iv_high": 0.6345,
        "iv_low": 0.2467,
        "iv_high_raw": 0.7788,
        "iv_low_raw": 0.126,
        "iv_rank": 0.942,
        "iv_rank_raw": 0.7445,
        "iv_percentile": 0.9722,
        "iv_percentile_raw": 0.9464,
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
          0.158,
          0.6386
        ],
        "name": "科创50",
        "desc": "科创板",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159915",
        "lookback_days": 252,
        "data_points": 221,
        "data_points_filtered": 217,
        "current_iv": 0.4793,
        "is_live": false,
        "iv_high": 0.4913,
        "iv_low": 0.2082,
        "iv_high_raw": 0.6363,
        "iv_low_raw": 0.2082,
        "iv_rank": 0.9577,
        "iv_rank_raw": 0.6333,
        "iv_percentile": 0.9908,
        "iv_percentile_raw": 0.9729,
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
          0.1748,
          0.4927
        ],
        "name": "创业板ETF",
        "desc": "创业板",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159922",
        "lookback_days": 252,
        "data_points": 221,
        "data_points_filtered": 211,
        "current_iv": 0.3529,
        "is_live": false,
        "iv_high": 0.352,
        "iv_low": 0.1804,
        "iv_high_raw": 0.468,
        "iv_low_raw": 0.1804,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.5998,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9548,
        "outliers_removed": 10,
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
          },
          {
            "date": "2026-08-03",
            "iv": 0.3529
          }
        ],
        "sigma_range": [
          0.1778,
          0.3526
        ],
        "name": "500ETF深",
        "desc": "深市中盘",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159919",
        "lookback_days": 252,
        "data_points": 221,
        "data_points_filtered": 215,
        "current_iv": 0.2225,
        "is_live": false,
        "iv_high": 0.258,
        "iv_low": 0.1298,
        "iv_high_raw": 0.3431,
        "iv_low_raw": 0.1298,
        "iv_rank": 0.7231,
        "iv_rank_raw": 0.4346,
        "iv_percentile": 0.8744,
        "iv_percentile_raw": 0.8507,
        "outliers_removed": 6,
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
          0.1117,
          0.2585
        ],
        "name": "300ETF深",
        "desc": "深市宽基",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "159901",
        "lookback_days": 252,
        "data_points": 221,
        "data_points_filtered": 216,
        "current_iv": 0.3119,
        "is_live": false,
        "iv_high": 0.3406,
        "iv_low": 0.1682,
        "iv_high_raw": 0.4504,
        "iv_low_raw": 0.1682,
        "iv_rank": 0.8337,
        "iv_rank_raw": 0.5092,
        "iv_percentile": 0.9213,
        "iv_percentile_raw": 0.9005,
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
          0.1457,
          0.3425
        ],
        "name": "深100ETF",
        "desc": "深市蓝筹",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "588080",
        "lookback_days": 252,
        "data_points": 223,
        "data_points_filtered": 216,
        "current_iv": 0.6208,
        "is_live": false,
        "iv_high": 0.6208,
        "iv_low": 0.184,
        "iv_high_raw": 0.756,
        "iv_low_raw": 0.184,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.7636,
        "iv_percentile": 0.9954,
        "iv_percentile_raw": 0.9641,
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
          0.1613,
          0.6342
        ],
        "name": "科创板50",
        "desc": "科创板（备用代理）",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      }
    ],
    "overall_sentiment": {
      "signal": "极度恐慌",
      "avg_iv_rank": 0.8489,
      "avg_iv_percentile": 0.9177,
      "implication": "波动率处于高位，市场恐慌。历史上往往是中期买入机会，但短期可能继续剧烈波动。",
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
    "regime": "balanced",
    "breadth_ratio": 2.1994,
    "up": 3717,
    "down": 1690,
    "positive_indices": [],
    "negative_indices": [
      "上证指数",
      "深证成指",
      "创业板指"
    ],
    "limit_ups": 66,
    "limit_downs": 3,
    "sizing_multiplier": 1.0,
    "hard_block": false,
    "reason": "Entry regime balanced: breadth 2.20:1, 0/3 major indices green, 66 limit-ups / 3 limit-downs. Allow normal sizing."
  },
  "rule_violations": {
    "status": "violations",
    "total_rules": 6,
    "total_violations": 4,
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
        "status": "violations",
        "exit_code": 1,
        "violations": [
          {
            "code": "300373",
            "name": "扬杰科技",
            "rule": "iv_filter",
            "days_held": 3,
            "pnl_pct": -6.86,
            "suggestion": "Down -6.9% after only 3 days. Possible entry during low-IV complacent market. Review: was IVRank<15% at entry? Was 5-day cum gain >6%? Consider tighter stop or faster exit for entries during low-IV regimes."
          }
        ],
        "error": null
      },
      {
        "rule": "check_overextended_entry",
        "file": "scripts/rules/check_overextended_entry.py",
        "status": "violations",
        "exit_code": 1,
        "violations": [
          {
            "code": "300373",
            "name": "扬杰科技",
            "rule": "overextended_entry",
            "days_held": 3,
            "pnl_pct": -6.86,
            "suggestion": "Down -6.9% after only 3 days — likely overextended entry. Check: (1) Was 5-day cum gain >12% at entry? (LEARNINGS#13) (2) Was IV Rank <15% at entry? (LEARNINGS auto-update 03-03) (3) Was the stock up >8% on entry day? (LEARNINGS#10) Consider tighter stop or accelerated exit."
          }
        ],
        "error": null
      },
      {
        "rule": "check_stop_proximity",
        "file": "scripts/rules/check_stop_proximity.py",
        "status": "violations",
        "exit_code": 1,
        "violations": [
          {
            "code": "002916",
            "name": "深南电路",
            "rule": "stop_proximity",
            "severity": "CRITICAL",
            "currentPrice": 304.31,
            "stopLoss": 300.21,
            "distance_pct": 1.35,
            "suggestion": "🔴 CRITICAL — only 1.3% above stop! Gap risk is real (03-03 lesson: 扬杰科技 gapped to -8.37%). Strongly recommend proactive stop-loss NOW. Don't wait for exact trigger."
          },
          {
            "code": "300373",
            "name": "扬杰科技",
            "rule": "stop_proximity",
            "severity": "CRITICAL",
            "currentPrice": 81.59,
            "stopLoss": 83.22,
            "distance_pct": -2.0,
            "suggestion": "🔴 CRITICAL — only -2.0% above stop! Gap risk is real (03-03 lesson: 扬杰科技 gapped to -8.37%). Strongly recommend proactive stop-loss NOW. Don't wait for exact trigger."
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
  "active_learnings": "## Active Rules (proven, hitRate ≥ 75%)\n- [h013] Strong breadth alone is not enough to force entries; without candidate RPS and MA-distance data, the correct momentum decision is to keep cash. (hitRate: 99%, n=130, confidence: 98%)\n- [h019] Bottom-list sectors should be treated as hard no-buy zones even when individual names still carry acceptable RPS readings. (hitRate: 100%, n=51, confidence: 98%)\n- [h028] Today’s relative leaders are concentrated in communication equipment and adjacent tech hardware, while cyclicals/agri/resource laggards are being de-risked aggressively. (hitRate: 100%, n=50, confidence: 98%)\n- [h027] MA-distance discipline remains critical inside hot sectors: a hot sector does not override chase risk when dist_ma5_pct exceeds 6% or dist_ma10_pct exceeds 8%. (hitRate: 100%, n=42, confidence: 98%)\n- [h023] Raising stops mechanically after +10% works well in weak tapes because it converts a fast winner into a low-risk hold without needing a fresh market call. (hitRate: 100%, n=36, confidence: 97%)\n- [h021] The MA-distance anti-chase rule is doing real work: several visually strong names fail because they are too far above short-term support. (hitRate: 98%, n=104, confidence: 97%)\n- [h077] The hard block is preventing FOMO entries. 新宙邦 (宁德时代协议 catalyst, VCP SETUP) and 奥来德 (dist_ma5 0.3%) would have been tempting buys in V1. V2 correctly forces cash preservation in panic regime. (hitRate: 100%, n=17, confidence: 95%)\n- [h017] Low-IV conditions around 16-22% IV rank do not justify freezing risk when breadth is 5.6:1; they argue for normal sizing but tighter discipline on chasing. (hitRate: 97%, n=29, confidence: 94%)\n- [h024] Stop-proximity violations deserve proactive action before the hard stop is hit, especially in 科创板 names where gap risk can erase the remaining cushion quickly. (hitRate: 91%, n=11, confidence: 85%)\n",
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
