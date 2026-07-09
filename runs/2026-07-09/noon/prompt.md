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
- **Above 95%**: Skip — chasing, wait for pullback to 90% zone

### Rule 2b: No Chasing — MA Distance Check
Before opening ANY new position, check the MA data in `enriched_candidates`:
- **dist_ma5_pct > 6%** → SKIP. Stock is overextended short-term.
- **dist_ma10_pct > 8%** → SKIP. Too far from support.
- **dist_ma20_pct > 12%** → SKIP. Extreme extension, high mean-reversion risk.
- If MA data is missing for a candidate, note it as a risk factor.

This rule is NON-NEGOTIABLE. Even if the sector is #1 and the catalyst is perfect, buying a stock that just spiked far above its moving averages is chasing. Wait for a pullback to MA5/MA10 support.

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
  "date": "2026-07-09",
  "portfolio": {
    "startingCapital": 1000000,
    "totalEquity": 985121.0,
    "cash": 985121.0,
    "investedValue": 0.0,
    "unrealizedPnl": 0.0,
    "realizedPnl": -14879.0,
    "totalPnl": -14879.0,
    "totalReturnPct": -1.49,
    "positionsUsed": 0,
    "positionsMax": 10,
    "cashPct": 100.0,
    "dayPnl": 0.0,
    "minCashPct": 0,
    "minCashValue": 0.0,
    "deployableCash": 985121.0
  },
  "market": {
    "timestamp": "2026-07-09T11:35:50.688836",
    "indices": {
      "上证指数": {
        "code": "sh000001",
        "close": 3952.492,
        "change_pct": -0.46,
        "date": "2026-07-09"
      },
      "深证成指": {
        "code": "sz399001",
        "close": 14887.99,
        "change_pct": -0.35,
        "date": "2026-07-09"
      },
      "创业板指": {
        "code": "sz399006",
        "close": 3850.21,
        "change_pct": 0.13,
        "date": "2026-07-09"
      },
      "科创50": {
        "code": "sh000688",
        "close": 2080.501,
        "change_pct": 3.19,
        "date": "2026-07-09"
      }
    },
    "breadth": {
      "up": 842,
      "down": 4616,
      "flat": 63,
      "total": 5521,
      "distribution": {
        "f10": 21,
        "f7_10": 85,
        "f4_7": 508,
        "f2_4": 2106,
        "f0_2": 1896,
        "f0": 63,
        "r0_2": 466,
        "r2_4": 179,
        "r4_7": 100,
        "r7_10": 61,
        "r10": 36
      }
    },
    "sectors": {
      "top5": [
        {
          "板块名称": "半导体",
          "涨跌幅": 3.05
        },
        {
          "板块名称": "油服工程",
          "涨跌幅": 2.6
        },
        {
          "板块名称": "综合Ⅱ",
          "涨跌幅": 1.38
        },
        {
          "板块名称": "非金属材料Ⅱ",
          "涨跌幅": 1.05
        },
        {
          "板块名称": "计算机设备",
          "涨跌幅": 0.92
        }
      ],
      "bottom5": [
        {
          "板块名称": "能源金属",
          "涨跌幅": -6.28
        },
        {
          "板块名称": "小金属",
          "涨跌幅": -5.11
        },
        {
          "板块名称": "工业金属",
          "涨跌幅": -3.66
        },
        {
          "板块名称": "特钢Ⅱ",
          "涨跌幅": -3.57
        },
        {
          "板块名称": "金属新材料",
          "涨跌幅": -3.5
        }
      ]
    }
  },
  "strategy_pool": {
    "source": "cheesefortune_intersection",
    "total_stocks": 58,
    "stocks": [
      {
        "code": "300489",
        "code_full": "300489.SZ",
        "name": "光智科技",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 372.776,
        "pe": 11.0,
        "risks_count": 3,
        "rps20": 100.0,
        "rps60": 100.0,
        "rps120": 99.9,
        "rps250": 98.77,
        "ma10": 284.64,
        "vcp_quality": null,
        "ma5": 279.68,
        "ma20": 224.26,
        "dist_ma5_pct": 0.9,
        "dist_ma10_pct": -0.9,
        "dist_ma20_pct": 25.8
      },
      {
        "code": "002980",
        "code_full": "002980.SZ",
        "name": "华盛昌",
        "source_date": "2026/04/30",
        "highlights_count": 5,
        "market_cap": 183.9085,
        "pe": 6.2,
        "risks_count": 2,
        "rps20": 97.45,
        "rps60": 99.88,
        "rps120": 99.63,
        "rps250": 97.62,
        "ma10": 111.72,
        "vcp_quality": null,
        "ma5": 106.63,
        "ma20": 114.34,
        "dist_ma5_pct": -5.6,
        "dist_ma10_pct": -9.9,
        "dist_ma20_pct": -12.0
      },
      {
        "code": "301362",
        "code_full": "301362.SZ",
        "name": "民爆光电",
        "source_date": "2026/06/16",
        "highlights_count": 4,
        "market_cap": 214.0425,
        "pe": 2.9,
        "risks_count": 1,
        "rps20": 92.63,
        "rps60": 99.69,
        "rps120": 99.43,
        "rps250": 98.24,
        "ma10": 176.35,
        "vcp_quality": null,
        "ma5": 160.17,
        "ma20": 186.13,
        "dist_ma5_pct": -5.9,
        "dist_ma10_pct": -14.5,
        "dist_ma20_pct": -19.0
      },
      {
        "code": "300285",
        "code_full": "300285.SZ",
        "name": "国瓷材料",
        "source_date": "2026/07/08",
        "highlights_count": 7,
        "market_cap": 782.5832,
        "pe": 14.4,
        "risks_count": 2,
        "rps20": 99.74,
        "rps60": 98.98,
        "rps120": 99.27,
        "rps250": 98.38,
        "ma10": 95.5,
        "vcp_quality": null,
        "ma5": 90.22,
        "ma20": 78.89,
        "dist_ma5_pct": -8.4,
        "dist_ma10_pct": -13.5,
        "dist_ma20_pct": 4.7
      },
      {
        "code": "600869",
        "code_full": "600869.SH",
        "name": "远东股份",
        "source_date": "2026/06/29",
        "highlights_count": 5,
        "market_cap": 512.6705,
        "pe": 31.4,
        "risks_count": 5,
        "rps20": 98.4,
        "rps60": 98.89,
        "rps120": 99.23,
        "rps250": 99.25,
        "ma10": 32.19,
        "vcp_quality": null,
        "ma5": 28.83,
        "ma20": 31.65,
        "dist_ma5_pct": -14.4,
        "dist_ma10_pct": -23.3,
        "dist_ma20_pct": -22.0
      },
      {
        "code": "301396",
        "code_full": "301396.SZ",
        "name": "宏景科技",
        "source_date": "2026/05/13",
        "highlights_count": 4,
        "market_cap": 552.3561,
        "pe": 3.6,
        "risks_count": 2,
        "rps20": 83.09,
        "rps60": 99.2,
        "rps120": 99.17,
        "rps250": 95.78,
        "ma10": 291.15,
        "vcp_quality": null,
        "ma5": 283.46,
        "ma20": 235.79,
        "dist_ma5_pct": -4.6,
        "dist_ma10_pct": -7.1,
        "dist_ma20_pct": 14.7
      },
      {
        "code": "688668",
        "code_full": "688668.SH",
        "name": "鼎通科技",
        "source_date": "2026/04/08",
        "highlights_count": 4,
        "market_cap": 451.8217,
        "pe": 5.5,
        "risks_count": 1,
        "rps20": 98.54,
        "rps60": 98.47,
        "rps120": 99.0,
        "rps250": 99.56,
        "ma10": 372.27,
        "vcp_quality": null,
        "ma5": 346.9,
        "ma20": 365.91,
        "dist_ma5_pct": -4.7,
        "dist_ma10_pct": -11.2,
        "dist_ma20_pct": -9.6
      },
      {
        "code": "300806",
        "code_full": "300806.SZ",
        "name": "斯迪克",
        "source_date": "2026/04/28",
        "highlights_count": 5,
        "market_cap": 382.087,
        "pe": 6.6,
        "risks_count": 2,
        "rps20": 96.41,
        "rps60": 97.91,
        "rps120": 98.96,
        "rps250": 98.97,
        "ma10": 101.5,
        "vcp_quality": null,
        "ma5": 94.75,
        "ma20": 92.66,
        "dist_ma5_pct": -6.0,
        "dist_ma10_pct": -12.3,
        "dist_ma20_pct": -3.9
      },
      {
        "code": "688630",
        "code_full": "688630.SH",
        "name": "芯碁微装",
        "source_date": "2026/03/12",
        "highlights_count": 6,
        "market_cap": 684.2363,
        "pe": 5.2,
        "risks_count": 1,
        "rps20": 98.91,
        "rps60": 98.71,
        "rps120": 98.94,
        "rps250": 99.05,
        "ma10": 502.01,
        "vcp_quality": null,
        "ma5": 505.47,
        "ma20": 435.11,
        "dist_ma5_pct": -5.7,
        "dist_ma10_pct": -5.0,
        "dist_ma20_pct": 9.6
      },
      {
        "code": "688300",
        "code_full": "688300.SH",
        "name": "联瑞新材",
        "source_date": "2026/05/06",
        "highlights_count": 6,
        "market_cap": 439.6188,
        "pe": 6.6,
        "risks_count": 1,
        "rps20": 99.6,
        "rps60": 99.43,
        "rps120": 98.92,
        "rps250": 96.89,
        "ma10": 233.57,
        "vcp_quality": null,
        "ma5": 209.05,
        "ma20": 204.44,
        "dist_ma5_pct": -10.1,
        "dist_ma10_pct": -19.5,
        "dist_ma20_pct": -8.0
      },
      {
        "code": "000811",
        "code_full": "000811.SZ",
        "name": "冰轮环境",
        "source_date": "2026/06/12",
        "highlights_count": 5,
        "market_cap": 497.2315,
        "pe": 28.1,
        "risks_count": 2,
        "rps20": 98.93,
        "rps60": 99.08,
        "rps120": 98.64,
        "rps250": 96.91,
        "ma10": 53.91,
        "vcp_quality": null,
        "ma5": 54.16,
        "ma20": 44.91,
        "dist_ma5_pct": -3.4,
        "dist_ma10_pct": -2.9,
        "dist_ma20_pct": 16.5
      },
      {
        "code": "603663",
        "code_full": "603663.SH",
        "name": "三祥新材",
        "source_date": "2026/06/02",
        "highlights_count": 5,
        "market_cap": 323.1913,
        "pe": 9.9,
        "risks_count": 2,
        "rps20": 98.72,
        "rps60": 97.73,
        "rps120": 98.53,
        "rps250": 95.88,
        "ma10": 91.15,
        "vcp_quality": null,
        "ma5": 88.42,
        "ma20": 79.95,
        "dist_ma5_pct": -8.1,
        "dist_ma10_pct": -10.9,
        "dist_ma20_pct": 1.6
      },
      {
        "code": "300201",
        "code_full": "300201.SZ",
        "name": "海伦哲",
        "source_date": "2026/05/06",
        "highlights_count": 6,
        "market_cap": 168.5103,
        "pe": 15.2,
        "risks_count": 2,
        "rps20": 95.04,
        "rps60": 97.79,
        "rps120": 98.43,
        "rps250": 95.52,
        "ma10": 18.71,
        "vcp_quality": null,
        "ma5": 18.31,
        "ma20": 18.8,
        "dist_ma5_pct": -5.5,
        "dist_ma10_pct": -7.5,
        "dist_ma20_pct": -8.0
      },
      {
        "code": "688627",
        "code_full": "688627.SH",
        "name": "精智达",
        "source_date": "2026/05/31",
        "highlights_count": 4,
        "market_cap": 553.4735,
        "pe": 2.9,
        "risks_count": 0,
        "rps20": 98.76,
        "rps60": 97.32,
        "rps120": 98.39,
        "rps250": 99.5,
        "ma10": 603.75,
        "vcp_quality": null,
        "ma5": 632.54,
        "ma20": 500.79,
        "dist_ma5_pct": -7.5,
        "dist_ma10_pct": -3.1,
        "dist_ma20_pct": 16.8
      },
      {
        "code": "300390",
        "code_full": "300390.SZ",
        "name": "天华新能",
        "source_date": "2026/06/25",
        "highlights_count": 4,
        "market_cap": 673.0743,
        "pe": 11.9,
        "risks_count": 2,
        "rps20": 81.99,
        "rps60": 95.52,
        "rps120": 97.99,
        "rps250": 97.56,
        "ma10": 91.86,
        "vcp_quality": null,
        "ma5": 92.36,
        "ma20": 89.47,
        "dist_ma5_pct": -7.0,
        "dist_ma10_pct": -6.5,
        "dist_ma20_pct": -4.0
      },
      {
        "code": "003031",
        "code_full": "003031.SZ",
        "name": "中瓷电子",
        "source_date": "2026/07/01",
        "highlights_count": 5,
        "market_cap": 640.2244,
        "pe": 5.5,
        "risks_count": 1,
        "rps20": 95.14,
        "rps60": 97.26,
        "rps120": 97.74,
        "rps250": 95.74,
        "ma10": 167.94,
        "vcp_quality": null,
        "ma5": 154.5,
        "ma20": 157.75,
        "dist_ma5_pct": -5.0,
        "dist_ma10_pct": -12.6,
        "dist_ma20_pct": -6.9
      },
      {
        "code": "002787",
        "code_full": "002787.SZ",
        "name": "华源控股",
        "source_date": "2026/07/06",
        "highlights_count": 4,
        "market_cap": 90.346,
        "pe": 10.5,
        "risks_count": 1,
        "rps20": 96.98,
        "rps60": 97.69,
        "rps120": 97.41,
        "rps250": 95.6,
        "ma10": 30.44,
        "vcp_quality": null,
        "ma5": 30.17,
        "ma20": 28.43,
        "dist_ma5_pct": -5.9,
        "dist_ma10_pct": -6.7,
        "dist_ma20_pct": -0.1
      },
      {
        "code": "688127",
        "code_full": "688127.SH",
        "name": "蓝特光学",
        "source_date": "2026/06/20",
        "highlights_count": 8,
        "market_cap": 318.8326,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 88.6,
        "rps60": 96.44,
        "rps120": 97.05,
        "rps250": 96.18,
        "ma10": 88.61,
        "vcp_quality": null,
        "ma5": 86.6,
        "ma20": 85.8,
        "dist_ma5_pct": -9.2,
        "dist_ma10_pct": -11.3,
        "dist_ma20_pct": -8.4
      },
      {
        "code": "300776",
        "code_full": "300776.SZ",
        "name": "帝尔激光",
        "source_date": "2026/06/29",
        "highlights_count": 4,
        "market_cap": 453.5228,
        "pe": 7.1,
        "risks_count": 0,
        "rps20": 98.16,
        "rps60": 97.46,
        "rps120": 96.97,
        "rps250": 94.06,
        "ma10": 184.58,
        "vcp_quality": null,
        "ma5": 176.47,
        "ma20": 170.22,
        "dist_ma5_pct": -5.4,
        "dist_ma10_pct": -9.5,
        "dist_ma20_pct": -1.9
      },
      {
        "code": "301182",
        "code_full": "301182.SZ",
        "name": "凯旺科技",
        "source_date": "2026/04/24",
        "highlights_count": 5,
        "market_cap": 84.6681,
        "pe": 4.5,
        "risks_count": 3,
        "rps20": 95.26,
        "rps60": 98.44,
        "rps120": 96.84,
        "rps250": 93.92,
        "ma10": 101.6,
        "vcp_quality": null,
        "ma5": 101.48,
        "ma20": 93.46,
        "dist_ma5_pct": -6.8,
        "dist_ma10_pct": -6.9,
        "dist_ma20_pct": 1.2
      },
      {
        "code": "688017",
        "code_full": "688017.SH",
        "name": "绿的谐波",
        "source_date": "2026/07/08",
        "highlights_count": 4,
        "market_cap": 716.8208,
        "pe": 5.8,
        "risks_count": 2,
        "rps20": 97.77,
        "rps60": 95.93,
        "rps120": 96.62,
        "rps250": 93.33,
        "ma10": 411.2,
        "vcp_quality": null,
        "ma5": 442.78,
        "ma20": 383.0,
        "dist_ma5_pct": 8.8,
        "dist_ma10_pct": 17.2,
        "dist_ma20_pct": 25.8
      },
      {
        "code": "688531",
        "code_full": "688531.SH",
        "name": "日联科技",
        "source_date": "2026/06/16",
        "highlights_count": 8,
        "market_cap": 292.1077,
        "pe": 3.2,
        "risks_count": 1,
        "rps20": 97.2,
        "rps60": 97.67,
        "rps120": 96.38,
        "rps250": 92.75,
        "ma10": 174.74,
        "vcp_quality": null,
        "ma5": 176.31,
        "ma20": 176.73,
        "dist_ma5_pct": 0.1,
        "dist_ma10_pct": 1.0,
        "dist_ma20_pct": -0.1
      },
      {
        "code": "688150",
        "code_full": "688150.SH",
        "name": "莱特光电",
        "source_date": "2026/04/16",
        "highlights_count": 6,
        "market_cap": 219.5699,
        "pe": 4.3,
        "risks_count": 1,
        "rps20": 89.14,
        "rps60": 97.07,
        "rps120": 96.32,
        "rps250": 93.11,
        "ma10": 61.57,
        "vcp_quality": null,
        "ma5": 64.94,
        "ma20": 57.15,
        "dist_ma5_pct": -8.8,
        "dist_ma10_pct": -3.8,
        "dist_ma20_pct": 3.6
      },
      {
        "code": "301183",
        "code_full": "301183.SZ",
        "name": "东田微",
        "source_date": "2026/04/29",
        "highlights_count": 4,
        "market_cap": 177.281,
        "pe": 4.1,
        "risks_count": 2,
        "rps20": 91.11,
        "rps60": 93.12,
        "rps120": 95.77,
        "rps250": 98.46,
        "ma10": 238.08,
        "vcp_quality": null,
        "ma5": 224.96,
        "ma20": 234.26,
        "dist_ma5_pct": 4.5,
        "dist_ma10_pct": -1.3,
        "dist_ma20_pct": 0.3
      },
      {
        "code": "300005",
        "code_full": "300005.SZ",
        "name": "探路者",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 182.7496,
        "pe": 16.7,
        "risks_count": 3,
        "rps20": 92.77,
        "rps60": 92.33,
        "rps120": 95.62,
        "rps250": 88.55,
        "ma10": 22.44,
        "vcp_quality": null,
        "ma5": 22.96,
        "ma20": 19.08,
        "dist_ma5_pct": -6.9,
        "dist_ma10_pct": -4.7,
        "dist_ma20_pct": 12.1
      },
      {
        "code": "601126",
        "code_full": "601126.SH",
        "name": "四方股份",
        "source_date": "2026/03/12",
        "highlights_count": 7,
        "market_cap": 449.877,
        "pe": 15.5,
        "risks_count": 0,
        "rps20": 87.38,
        "rps60": 94.33,
        "rps120": 95.5,
        "rps250": 96.14,
        "ma10": 63.89,
        "vcp_quality": null,
        "ma5": 59.1,
        "ma20": 68.26,
        "dist_ma5_pct": -3.7,
        "dist_ma10_pct": -10.9,
        "dist_ma20_pct": -16.6
      },
      {
        "code": "002937",
        "code_full": "002937.SZ",
        "name": "兴瑞科技",
        "source_date": "2026/04/23",
        "highlights_count": 5,
        "market_cap": 136.137,
        "pe": 7.7,
        "risks_count": 0,
        "rps20": 93.05,
        "rps60": 95.01,
        "rps120": 95.48,
        "rps250": 91.68,
        "ma10": 43.4,
        "vcp_quality": null,
        "ma5": 43.86,
        "ma20": 39.88,
        "dist_ma5_pct": -1.1,
        "dist_ma10_pct": -0.1,
        "dist_ma20_pct": 8.8
      },
      {
        "code": "002436",
        "code_full": "002436.SZ",
        "name": "兴森科技",
        "source_date": "2026/07/04",
        "highlights_count": 4,
        "market_cap": 686.8381,
        "pe": 16.0,
        "risks_count": 2,
        "rps20": 97.93,
        "rps60": 96.32,
        "rps120": 95.28,
        "rps250": 97.07,
        "ma10": 46.68,
        "vcp_quality": null,
        "ma5": 43.59,
        "ma20": 44.16,
        "dist_ma5_pct": -4.8,
        "dist_ma10_pct": -11.1,
        "dist_ma20_pct": -6.1
      },
      {
        "code": "300323",
        "code_full": "300323.SZ",
        "name": "华灿光电",
        "source_date": "2026/04/29",
        "highlights_count": 5,
        "market_cap": 253.3501,
        "pe": 14.1,
        "risks_count": 2,
        "rps20": 95.44,
        "rps60": 97.13,
        "rps120": 95.09,
        "rps250": 92.93,
        "ma10": 18.4,
        "vcp_quality": null,
        "ma5": 18.25,
        "ma20": 17.26,
        "dist_ma5_pct": -10.7,
        "dist_ma10_pct": -11.5,
        "dist_ma20_pct": -5.6
      },
      {
        "code": "605111",
        "code_full": "605111.SH",
        "name": "新洁能",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 324.1671,
        "pe": 5.7,
        "risks_count": 2,
        "rps20": 98.56,
        "rps60": 96.03,
        "rps120": 94.83,
        "rps250": 91.17,
        "ma10": 82.81,
        "vcp_quality": null,
        "ma5": 89.26,
        "ma20": 72.16,
        "dist_ma5_pct": -6.3,
        "dist_ma10_pct": 1.0,
        "dist_ma20_pct": 15.9
      },
      {
        "code": "002290",
        "code_full": "002290.SZ",
        "name": "禾盛新材",
        "source_date": "2026/06/12",
        "highlights_count": 4,
        "market_cap": 194.0983,
        "pe": 16.8,
        "risks_count": 4,
        "rps20": 84.93,
        "rps60": 90.5,
        "rps120": 94.44,
        "rps250": 95.21,
        "ma10": 86.87,
        "vcp_quality": null,
        "ma5": 86.65,
        "ma20": 85.29,
        "dist_ma5_pct": -5.8,
        "dist_ma10_pct": -6.1,
        "dist_ma20_pct": -4.3
      },
      {
        "code": "688376",
        "code_full": "688376.SH",
        "name": "美埃科技",
        "source_date": "2026/04/28",
        "highlights_count": 6,
        "market_cap": 125.7843,
        "pe": 3.6,
        "risks_count": 1,
        "rps20": 93.42,
        "rps60": 88.38,
        "rps120": 94.36,
        "rps250": 91.19,
        "ma10": 98.09,
        "vcp_quality": null,
        "ma5": 107.18,
        "ma20": 85.53,
        "dist_ma5_pct": -8.6,
        "dist_ma10_pct": -0.1,
        "dist_ma20_pct": 14.5
      },
      {
        "code": "002975",
        "code_full": "002975.SZ",
        "name": "博杰股份",
        "source_date": "2026/06/16",
        "highlights_count": 5,
        "market_cap": 229.6098,
        "pe": 6.4,
        "risks_count": 0,
        "rps20": 93.11,
        "rps60": 93.61,
        "rps120": 94.16,
        "rps250": 97.5,
        "ma10": 131.65,
        "vcp_quality": null,
        "ma5": 121.58,
        "ma20": 132.27,
        "dist_ma5_pct": -5.1,
        "dist_ma10_pct": -12.4,
        "dist_ma20_pct": -12.8
      },
      {
        "code": "688515",
        "code_full": "688515.SH",
        "name": "裕太微-U",
        "source_date": "2026/07/07",
        "highlights_count": 4,
        "market_cap": 167.496,
        "pe": 3.4,
        "risks_count": 2,
        "rps20": 94.81,
        "rps60": 96.13,
        "rps120": 93.85,
        "rps250": 87.78,
        "ma10": 236.66,
        "vcp_quality": null,
        "ma5": 233.46,
        "ma20": 218.3,
        "dist_ma5_pct": -8.3,
        "dist_ma10_pct": -9.6,
        "dist_ma20_pct": -2.0
      },
      {
        "code": "688536",
        "code_full": "688536.SH",
        "name": "思瑞浦",
        "source_date": "2026/04/01",
        "highlights_count": 8,
        "market_cap": 445.1415,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 94.37,
        "rps60": 94.88,
        "rps120": 93.67,
        "rps250": 85.76,
        "ma10": 343.74,
        "vcp_quality": null,
        "ma5": 350.79,
        "ma20": 323.97,
        "dist_ma5_pct": -2.8,
        "dist_ma10_pct": -0.8,
        "dist_ma20_pct": 5.2
      },
      {
        "code": "688652",
        "code_full": "688652.SH",
        "name": "京仪装备",
        "source_date": "2026/05/06",
        "highlights_count": 6,
        "market_cap": 375.4968,
        "pe": 2.6,
        "risks_count": 0,
        "rps20": 95.18,
        "rps60": 90.77,
        "rps120": 93.51,
        "rps250": 93.35,
        "ma10": 182.56,
        "vcp_quality": null,
        "ma5": 206.46,
        "ma20": 160.32,
        "dist_ma5_pct": -1.7,
        "dist_ma10_pct": 11.2,
        "dist_ma20_pct": 26.6
      },
      {
        "code": "301536",
        "code_full": "301536.SZ",
        "name": "星宸科技",
        "source_date": "2026/04/20",
        "highlights_count": 6,
        "market_cap": 485.2255,
        "pe": 2.2,
        "risks_count": 0,
        "rps20": 94.31,
        "rps60": 94.23,
        "rps120": 93.41,
        "rps250": 86.49,
        "ma10": 119.78,
        "vcp_quality": null,
        "ma5": 118.74,
        "ma20": 104.66,
        "dist_ma5_pct": 0.1,
        "dist_ma10_pct": -0.8,
        "dist_ma20_pct": 13.5
      },
      {
        "code": "300346",
        "code_full": "300346.SZ",
        "name": "南大光电",
        "source_date": "2026/06/16",
        "highlights_count": 4,
        "market_cap": 512.3546,
        "pe": 13.9,
        "risks_count": 2,
        "rps20": 95.2,
        "rps60": 88.66,
        "rps120": 93.24,
        "rps250": 85.62,
        "ma10": 81.83,
        "vcp_quality": null,
        "ma5": 81.52,
        "ma20": 70.12,
        "dist_ma5_pct": -6.3,
        "dist_ma10_pct": -6.6,
        "dist_ma20_pct": 9.0
      },
      {
        "code": "688378",
        "code_full": "688378.SH",
        "name": "奥来德",
        "source_date": "2026/06/06",
        "highlights_count": 5,
        "market_cap": 132.8563,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 92.36,
        "rps60": 93.41,
        "rps120": 93.18,
        "rps250": 93.64,
        "ma10": 57.16,
        "vcp_quality": null,
        "ma5": 58.58,
        "ma20": 52.27,
        "dist_ma5_pct": -0.7,
        "dist_ma10_pct": 1.8,
        "dist_ma20_pct": 11.3
      },
      {
        "code": "300236",
        "code_full": "300236.SZ",
        "name": "上海新阳",
        "source_date": "2026/03/12",
        "highlights_count": 5,
        "market_cap": 346.538,
        "pe": 15.0,
        "risks_count": 1,
        "rps20": 90.72,
        "rps60": 89.62,
        "rps120": 92.82,
        "rps250": 93.88,
        "ma10": 116.59,
        "vcp_quality": null,
        "ma5": 114.14,
        "ma20": 106.6,
        "dist_ma5_pct": -1.0,
        "dist_ma10_pct": -3.1,
        "dist_ma20_pct": 6.0
      },
      {
        "code": "300726",
        "code_full": "300726.SZ",
        "name": "宏达电子",
        "source_date": "2026/07/07",
        "highlights_count": 4,
        "market_cap": 276.0151,
        "pe": 8.6,
        "risks_count": 1,
        "rps20": 97.29,
        "rps60": 92.96,
        "rps120": 92.53,
        "rps250": 87.76,
        "ma10": 81.21,
        "vcp_quality": null,
        "ma5": 76.2,
        "ma20": 75.31,
        "dist_ma5_pct": -8.4,
        "dist_ma10_pct": -14.0,
        "dist_ma20_pct": -7.3
      },
      {
        "code": "002810",
        "code_full": "002810.SZ",
        "name": "山东赫达",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 76.9609,
        "pe": 9.8,
        "risks_count": 2,
        "rps20": 76.38,
        "rps60": 89.99,
        "rps120": 92.08,
        "rps250": 87.23,
        "ma10": 24.5,
        "vcp_quality": null,
        "ma5": 24.51,
        "ma20": 23.82,
        "dist_ma5_pct": -10.1,
        "dist_ma10_pct": -10.1,
        "dist_ma20_pct": -7.5
      },
      {
        "code": "300373",
        "code_full": "300373.SZ",
        "name": "扬杰科技",
        "source_date": "2026/07/02",
        "highlights_count": 5,
        "market_cap": 695.7025,
        "pe": 12.4,
        "risks_count": 0,
        "rps20": 97.49,
        "rps60": 94.15,
        "rps120": 92.0,
        "rps250": 93.19,
        "ma10": 137.82,
        "vcp_quality": null,
        "ma5": 134.27,
        "ma20": 121.11,
        "dist_ma5_pct": -2.4,
        "dist_ma10_pct": -4.9,
        "dist_ma20_pct": 8.2
      },
      {
        "code": "002805",
        "code_full": "002805.SZ",
        "name": "丰元股份",
        "source_date": "2026/06/16",
        "highlights_count": 5,
        "market_cap": 69.0354,
        "pe": 10.0,
        "risks_count": 3,
        "rps20": 90.66,
        "rps60": 93.68,
        "rps120": 91.98,
        "rps250": 89.66,
        "ma10": 27.6,
        "vcp_quality": null,
        "ma5": 27.0,
        "ma20": 24.76,
        "dist_ma5_pct": -6.3,
        "dist_ma10_pct": -8.4,
        "dist_ma20_pct": 2.2
      },
      {
        "code": "601958",
        "code_full": "601958.SH",
        "name": "金钼股份",
        "source_date": "2026/07/03",
        "highlights_count": 6,
        "market_cap": 703.0771,
        "pe": 18.2,
        "risks_count": 1,
        "rps20": 92.85,
        "rps60": 88.31,
        "rps120": 91.92,
        "rps250": 92.39,
        "ma10": 27.14,
        "vcp_quality": null,
        "ma5": 25.85,
        "ma20": 25.76,
        "dist_ma5_pct": -9.0,
        "dist_ma10_pct": -13.4,
        "dist_ma20_pct": -8.7
      },
      {
        "code": "002407",
        "code_full": "002407.SZ",
        "name": "多氟多",
        "source_date": "2026/05/06",
        "highlights_count": 5,
        "market_cap": 501.4102,
        "pe": 16.1,
        "risks_count": 2,
        "rps20": 93.26,
        "rps60": 91.94,
        "rps120": 91.72,
        "rps250": 96.75,
        "ma10": 47.87,
        "vcp_quality": null,
        "ma5": 45.57,
        "ma20": 42.22,
        "dist_ma5_pct": -10.1,
        "dist_ma10_pct": -14.4,
        "dist_ma20_pct": -2.9
      },
      {
        "code": "300438",
        "code_full": "300438.SZ",
        "name": "鹏辉能源",
        "source_date": "2026/04/14",
        "highlights_count": 6,
        "market_cap": 342.2232,
        "pe": 11.2,
        "risks_count": 1,
        "rps20": 82.7,
        "rps60": 94.51,
        "rps120": 91.39,
        "rps250": 94.79,
        "ma10": 79.41,
        "vcp_quality": null,
        "ma5": 75.75,
        "ma20": 77.49,
        "dist_ma5_pct": -7.1,
        "dist_ma10_pct": -11.4,
        "dist_ma20_pct": -9.2
      },
      {
        "code": "688401",
        "code_full": "688401.SH",
        "name": "路维光电",
        "source_date": "2026/04/21",
        "highlights_count": 6,
        "market_cap": 168.2141,
        "pe": 3.8,
        "risks_count": 0,
        "rps20": 94.29,
        "rps60": 92.02,
        "rps120": 91.31,
        "rps250": 89.56,
        "ma10": 88.12,
        "vcp_quality": null,
        "ma5": 92.89,
        "ma20": 82.48,
        "dist_ma5_pct": -7.6,
        "dist_ma10_pct": -2.5,
        "dist_ma20_pct": 4.1
      },
      {
        "code": "688390",
        "code_full": "688390.SH",
        "name": "固德威",
        "source_date": "2026/04/29",
        "highlights_count": 5,
        "market_cap": 195.8352,
        "pe": 5.8,
        "risks_count": 2,
        "rps20": 75.63,
        "rps60": 85.57,
        "rps120": 91.09,
        "rps250": 89.88,
        "ma10": 105.64,
        "vcp_quality": null,
        "ma5": 97.41,
        "ma20": 117.09,
        "dist_ma5_pct": -7.9,
        "dist_ma10_pct": -15.1,
        "dist_ma20_pct": -23.4
      },
      {
        "code": "300037",
        "code_full": "300037.SZ",
        "name": "新宙邦",
        "source_date": "2026/03/12",
        "highlights_count": 7,
        "market_cap": 583.7343,
        "pe": 16.5,
        "risks_count": 1,
        "rps20": 92.0,
        "rps60": 92.98,
        "rps120": 90.9,
        "rps250": 93.07,
        "ma10": 88.36,
        "vcp_score": 39,
        "vcp_contraction_ratio": 0.87,
        "vcp_last_depth": 13.4,
        "vcp_dist_peak_pct": 16.3,
        "vcp_nearest_ma": "MA20",
        "vcp_nearest_ma_dist": 2.1,
        "vcp_vol_declining": true,
        "vcp_num_contractions": 7,
        "vcp_depths": "15%→9%→15%→19%→12%→16%→13%",
        "vcp_quality": "SETUP",
        "ma5": 87.24,
        "ma20": 81.97,
        "dist_ma5_pct": -8.0,
        "dist_ma10_pct": -9.2,
        "dist_ma20_pct": -2.1
      },
      {
        "code": "688392",
        "code_full": "688392.SH",
        "name": "骄成超声",
        "source_date": "2026/04/22",
        "highlights_count": 7,
        "market_cap": 258.9765,
        "pe": 3.7,
        "risks_count": 0,
        "rps20": 95.02,
        "rps60": 89.13,
        "rps120": 90.68,
        "rps250": 96.63,
        "ma10": 198.33,
        "vcp_quality": null,
        "ma5": 222.38,
        "ma20": 178.07,
        "dist_ma5_pct": -1.6,
        "dist_ma10_pct": 10.4,
        "dist_ma20_pct": 22.9
      },
      {
        "code": "688372",
        "code_full": "688372.SH",
        "name": "伟测科技",
        "source_date": "2026/06/17",
        "highlights_count": 5,
        "market_cap": 317.0146,
        "pe": 3.7,
        "risks_count": 1,
        "rps20": 85.78,
        "rps60": 86.59,
        "rps120": 90.66,
        "rps250": 87.48,
        "ma10": 170.73,
        "vcp_quality": null,
        "ma5": 178.01,
        "ma20": 162.18,
        "dist_ma5_pct": 2.9,
        "dist_ma10_pct": 7.3,
        "dist_ma20_pct": 13.0
      },
      {
        "code": "002185",
        "code_full": "002185.SZ",
        "name": "华天科技",
        "source_date": "2026/06/30",
        "highlights_count": 4,
        "market_cap": 716.8625,
        "pe": 18.6,
        "risks_count": 2,
        "rps20": 95.3,
        "rps60": 90.81,
        "rps120": 90.03,
        "rps250": 85.84,
        "ma10": 21.33,
        "vcp_quality": null,
        "ma5": 21.11,
        "ma20": 19.64,
        "dist_ma5_pct": 4.9,
        "dist_ma10_pct": 3.9,
        "dist_ma20_pct": 12.8
      },
      {
        "code": "002947",
        "code_full": "002947.SZ",
        "name": "恒铭达",
        "source_date": "2026/03/12",
        "highlights_count": 6,
        "market_cap": 184.4707,
        "pe": 7.4,
        "risks_count": 0,
        "rps20": 84.95,
        "rps60": 93.84,
        "rps120": 89.84,
        "rps250": 91.76,
        "ma10": 76.82,
        "vcp_quality": null,
        "ma5": 73.48,
        "ma20": 82.25,
        "dist_ma5_pct": 0.3,
        "dist_ma10_pct": -4.1,
        "dist_ma20_pct": -10.4
      },
      {
        "code": "300870",
        "code_full": "300870.SZ",
        "name": "欧陆通",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 406.1845,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 77.21,
        "rps60": 90.38,
        "rps120": 89.68,
        "rps250": 94.14,
        "ma10": 320.35,
        "vcp_quality": null,
        "ma5": 297.77,
        "ma20": 307.61,
        "dist_ma5_pct": -5.7,
        "dist_ma10_pct": -12.3,
        "dist_ma20_pct": -8.7
      },
      {
        "code": "688469",
        "code_full": "688469.SH",
        "name": "芯联集成-U",
        "source_date": "2026/07/02",
        "highlights_count": 5,
        "market_cap": 781.2664,
        "pe": 3.1,
        "risks_count": 2,
        "rps20": 92.61,
        "rps60": 86.92,
        "rps120": 87.18,
        "rps250": 85.52,
        "ma10": 9.55,
        "vcp_quality": null,
        "ma5": 10.06,
        "ma20": 8.64,
        "dist_ma5_pct": -6.8,
        "dist_ma10_pct": -1.9,
        "dist_ma20_pct": 8.5
      },
      {
        "code": "002821",
        "code_full": "002821.SZ",
        "name": "凯莱英",
        "source_date": "2026/04/01",
        "highlights_count": 8,
        "market_cap": 539.4758,
        "pe": 9.6,
        "risks_count": 1,
        "rps20": 90.03,
        "rps60": 90.69,
        "rps120": 86.49,
        "rps250": 88.33,
        "ma10": 155.89,
        "vcp_quality": null,
        "ma5": 158.21,
        "ma20": 135.46,
        "dist_ma5_pct": -3.0,
        "dist_ma10_pct": -1.6,
        "dist_ma20_pct": 13.2
      },
      {
        "code": "002273",
        "code_full": "002273.SZ",
        "name": "水晶光电",
        "source_date": "2026/06/12",
        "highlights_count": 7,
        "market_cap": 445.5586,
        "pe": 17.8,
        "risks_count": 2,
        "rps20": 87.91,
        "rps60": 90.44,
        "rps120": 86.44,
        "rps250": 85.07,
        "ma10": 35.77,
        "vcp_quality": null,
        "ma5": 34.76,
        "ma20": 35.46,
        "dist_ma5_pct": -10.5,
        "dist_ma10_pct": -13.0,
        "dist_ma20_pct": -12.3
      }
    ]
  },
  "enriched_candidates": [
    {
      "code": "605111.SH",
      "fetch_time": "2026-07-09T11:35:50+0800",
      "name": "新洁能",
      "pe": 81.9323,
      "pb": 7.3022,
      "ps_ttm": 16.0028,
      "pcf_ttm": 77.4723,
      "valuation_percentile": 77.13,
      "total_shares": 415332567,
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
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "半导体精选指数",
        "养老金指数",
        "汽车芯片指数",
        "IGBT指数"
      ],
      "score_company": 8.2,
      "score_trend": 8.7,
      "score_value": 4.4,
      "highlights": [
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 14% ，创造价值的能力很强。"
        },
        {
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 4.8% ，很受外资机构青睐。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 半导体 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月01日大跌 -7% ，且成交额为近20日均值的 2.2倍 ，抛压很重。"
        },
        {
          "tag": "评级",
          "text": "收盘价比机构一致预测目标价高 39% ，存在高估风险。"
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
          "content": "15:00 今天大跌的原因可能是公司下游工业自动化、光伏储能、汽车电子及泛消费等需求总量未明显提升，压低对其中高端IGBT/MOSFET及功率器件销售与业绩的市场预期。",
          "tags": [
            "快讯",
            "大跌原因"
          ]
        },
        {
          "content": "15:00 今天大跌的原因可能是公司披露其下游工业自动化、光伏储能、汽车电子及泛消费等核心市场需求总量未见显著提升，预示订单与营收增长受限，打击市场对业绩的信心。",
          "tags": [
            "快讯",
            "大跌原因"
          ]
        },
        {
          "content": "新洁能：关于闲置募集资金现金管理赎回的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "09:35股价达到<span style=\"color:#FB475D\"> 86.78 </span>元，创历史新高",
          "tags": [
            "股价新高"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1385364303.26,
      "revenue_yoy": 0.021895,
      "operating_profit": 379989753.36,
      "operating_profit_yoy": 0.008495,
      "net_profit": 332551754.26,
      "net_profit_yoy": 0.0086,
      "gross_profit": 473458143.68,
      "gross_profit_yoy": -0.045298,
      "cogs": 911906159.58,
      "gross_margin": 34.18,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20220929",
      "current_price": 83.62,
      "price": 83.62,
      "ma5": 89.26,
      "ma10": 82.81,
      "ma20": 72.16,
      "dist_ma5_pct": -6.3,
      "dist_ma10_pct": 1.0,
      "dist_ma20_pct": 15.9,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "002290.SZ",
      "fetch_time": "2026-07-09T11:35:50+0800",
      "name": "禾盛新材",
      "pe": 125.5874,
      "pb": 20.3667,
      "ps_ttm": 7.8281,
      "pcf_ttm": 136.3214,
      "valuation_percentile": 90.89,
      "total_shares": 248112330,
      "industries": [
        {
          "name": "家用电器",
          "level": 1
        },
        {
          "name": "家电零部件Ⅱ",
          "level": 2
        },
        {
          "name": "家电零部件Ⅲ",
          "level": 3
        }
      ],
      "concepts": [
        "人工智能+指数",
        "QFII重仓指数",
        "信创产业指数",
        "芯片指数",
        "AI算力指数",
        "GPU指数",
        "家电指数",
        "DeepSeek指数",
        "近期定增指数",
        "苏州工业园区指数"
      ],
      "score_company": 6.5,
      "score_trend": 7.4,
      "score_value": 3.5,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 家电零部件Ⅲ 行业龙头企业。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 14% ，投入资本回报率为 13% ，盈利能力很强。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 5.7% ，较受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 93% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年05月15日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月15日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比为 63% ，销售收入现金含量很低。"
        },
        {
          "tag": "估值",
          "text": "最新综合估值高于近十年 91% 的时间，处于历史高位。"
        }
      ],
      "events": [
        {
          "content": "预计2026/07/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-07-29"
        },
        {
          "content": "在过去的60个交易日内，该股票的价格涨幅高于市场上<span style=\"color:#FB475D\"> 90% </span>的股票",
          "tags": [
            "股价走强"
          ]
        },
        {
          "content": "在过去的10个交易日内，该股票的价格涨幅仅高于市场上<span style=\"color:#00B985\"> 4.1% </span>的股票",
          "tags": [
            "股价走弱"
          ]
        },
        {
          "content": "禾盛新材：关于2026年度以简易程序向特定对象发行股票预案的提示性公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "禾盛新材：关于本次以简易程序向特定对象发行股票不存在直接或通过利益相关方向参与认购的投资者提供财务资助或补偿的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1862499128.7,
      "revenue_yoy": 0.014069,
      "operating_profit": 165042297.97,
      "operating_profit_yoy": 0.685606,
      "net_profit": 141047725.69,
      "net_profit_yoy": 0.685831,
      "gross_profit": 288831178.25,
      "gross_profit_yoy": 0.481492,
      "cogs": 1573667950.45,
      "gross_margin": 15.51,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20210709",
      "current_price": 81.59,
      "price": 81.59,
      "ma5": 86.65,
      "ma10": 86.87,
      "ma20": 85.29,
      "dist_ma5_pct": -5.8,
      "dist_ma10_pct": -6.1,
      "dist_ma20_pct": -4.3,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "688376.SH",
      "fetch_time": "2026-07-09T11:35:50+0800",
      "name": "美埃科技",
      "pe": 116.2602,
      "pb": 6.6515,
      "ps_ttm": 6.226,
      "pcf_ttm": 39.5651,
      "valuation_percentile": 98.98,
      "total_shares": 135251944,
      "industries": [
        {
          "name": "环保",
          "level": 1
        },
        {
          "name": "环保设备Ⅱ",
          "level": 2
        },
        {
          "name": "环保设备Ⅲ",
          "level": 3
        }
      ],
      "concepts": [
        "专精特新小巨人主题指数",
        "专精特新小巨人指数"
      ],
      "score_company": 7.6,
      "score_trend": 8.4,
      "score_value": 3.1,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年04月28日，业绩超预期引发股价大幅上涨，当日收涨 6.26% 。"
        },
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 19% ，收入成长性较强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 7.6% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 2.8亿元 ，较上期增长 4.1% ，占2025年营收 15% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 25% ，未来成长较快。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 93% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月30日大跌 -3.08% ，且成交额为近20日均值的 2.94倍 ，抛压很重。"
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
          "content": "美埃科技：2026-027关于收购控股子公司MayAir HK Holdings Limited少数股东部分股权完成的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "17:29 美埃科技公告，公司此前披露拟以现金人民币1.16亿元收购控股子公司MayAir HK Holdings Limited少数股东Ng Yew Sum先生等合计持有的535股股份（约占18.36%）。截至2026年7月7日，本次交易已完成相应的股份登记手续，收购控股子公司少数股东部分股权的交易已全部完成，公司持有美埃香港控股的股权比例由68.39%提升至86.75%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "18:31 美埃科技公告，公司股票于2026年6月25日、26日、29日连续三个交易日内日收盘价格涨幅偏离值累计达到30%，属于股票交易异常波动。公司2026年经营业绩会受到行业周期、市场竞争加剧、下游市场需求变化、新产品的研发和推广不及预期、原材料成本上升等影响，如公司未能采取有效措施及时应对上述变化，公司将面临经营业绩波动的风险。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "13:33股价达到<span style=\"color:#FB475D\"> 85.8 </span>元，创历史新高",
          "tags": [
            "股价新高"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1486421857.28,
      "revenue_yoy": 0.236424,
      "operating_profit": 153352741.15,
      "operating_profit_yoy": -0.076139,
      "net_profit": 152567751.66,
      "net_profit_yoy": 0.030138,
      "gross_profit": 409274788.02,
      "gross_profit_yoy": 0.113578,
      "cogs": 1077147069.26,
      "gross_margin": 27.53,
      "pe_forward": null,
      "valuation_history_days": 395,
      "valuation_history_from": "20241118",
      "current_price": 97.96,
      "price": 97.96,
      "ma5": 107.18,
      "ma10": 98.09,
      "ma20": 85.53,
      "dist_ma5_pct": -8.6,
      "dist_ma10_pct": -0.1,
      "dist_ma20_pct": 14.5,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "002975.SZ",
      "fetch_time": "2026-07-09T11:35:50+0800",
      "name": "博杰股份",
      "pe": 101.4167,
      "pb": 10.0354,
      "ps_ttm": 11.259,
      "pcf_ttm": 299.5569,
      "valuation_percentile": 82.77,
      "total_shares": 208130736,
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
        "贷款回购指数",
        "英伟达产业链指数",
        "机器人指数",
        "近期定增指数",
        "液冷服务器指数",
        "玻璃基板指数",
        "MLCC指数",
        "磷化铟指数"
      ],
      "score_company": 7.7,
      "score_trend": 7.9,
      "score_value": 4.1,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 419% ，利润成长性强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 1.5亿元 ，较上期增长 29% ，占2025年营收 8.3% ，在手订单充足。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 3.7% ，较受外资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 98% 的股票，走势很强。"
        },
        {
          "tag": "回购",
          "text": "近6月，公司累计回购 88万股 ，占总股本比例 0.42% ，金额合计 3002万元 。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "22:19 博杰股份在互动平台表示，公司对接人形机器人相关测试需求，已实现小批量发货人形机器人IMU测试设备，2025年度人形机器人测试板块实现的营业收入占公司总营收低于1%。公司人形机器人业务当前尚处于业务拓展阶段，业务开展尚存在不确定性风险，提请投资者理性投资。（人民财讯）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "15:43 博杰股份7月7日在互动平台表示，公司与宇树科技暂无直接业务合作。(界面)",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "股东大会日通过增发预案，股价盘中下跌<span style=\"color:#00B985\"> -8.29% </span>",
          "tags": [
            "股价下跌"
          ]
        },
        {
          "content": "博杰股份：北京德恒（深圳）律师事务所关于珠海博杰电子股份有限公司2026年第三次临时股东会的法律意见",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1116706802.44,
      "revenue_yoy": 0.356112,
      "operating_profit": 122079497.25,
      "operating_profit_yoy": 15.175725,
      "net_profit": 115308288.3,
      "net_profit_yoy": 38.050693,
      "gross_profit": 495787343.81,
      "gross_profit_yoy": 0.392401,
      "cogs": 620919458.63,
      "gross_margin": 44.4,
      "pe_forward": null,
      "valuation_history_days": 268,
      "valuation_history_from": "20220207",
      "current_price": 115.33,
      "price": 115.33,
      "ma5": 121.58,
      "ma10": 131.65,
      "ma20": 132.27,
      "dist_ma5_pct": -5.1,
      "dist_ma10_pct": -12.4,
      "dist_ma20_pct": -12.8,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "688515.SH",
      "fetch_time": "2026-07-09T11:35:50+0800",
      "name": "裕太微-U",
      "pe": -144.0592,
      "pb": 11.7087,
      "ps_ttm": 25.3604,
      "pcf_ttm": null,
      "valuation_percentile": 83.79,
      "total_shares": 80000000,
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
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "半导体精选指数",
        "预期提升指数",
        "光芯片指数"
      ],
      "score_company": 6.3,
      "score_trend": 8.5,
      "score_value": 4.2,
      "highlights": [
        {
          "tag": "收现",
          "text": "近5年，收现比达到 112% ，销售收入现金含量较强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 5.7% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 半导体 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        },
        {
          "tag": "强势",
          "text": "近6月，股价涨幅超过A股市场 96% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "净现",
          "text": "近5年，净现比为 -126% ，净利润现金含量较低。"
        },
        {
          "tag": "波动",
          "text": "2026年06月22日，换手率 21% ，短线资金追逐，波动风险较高。"
        }
      ],
      "events": [
        {
          "content": "2027/01/04解禁3018.06万股，占总股本37.73%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2027-01-04"
        },
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "18:12 裕太微公告，公司股票于2026年6月17日、18日、22日连续3个交易日收盘价格涨幅偏离值累计超过30%，属于股票交易异常波动。经自查并向第一大股东发函核实，不存在应披露而未披露的重大事项。公司关注到市场关于高速DSP电芯片业务进展的讨论，特澄清：公司主营业务为高速有线通信芯片研发销售，无面向数据中心的DSP电芯片产品；公司2026年度向特定对象发行A股股票预案拟募集资金用于面向数据中心场景的高速互联研发项目，但具体研发成果和产品形态尚不确定，距离产品化仍有明显距离，对现有主营业务不构成重大影响。公司目前仍处于亏损状态，2025年归母净利润为-1.34亿元，2026年第一季度归母净利润为-4325.77万元。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "10:00股价达到<span style=\"color:#FB475D\"> 271.91 </span>元，创历史新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "在过去的10个交易日内，该股票的价格涨幅仅高于市场上<span style=\"color:#00B985\"> 1.9% </span>的股票",
          "tags": [
            "股价走弱"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 387659317.87,
      "revenue_yoy": 0.456977,
      "operating_profit": -127560794.14,
      "operating_profit_yoy": 0.092193,
      "net_profit": -127503839.02,
      "net_profit_yoy": 0.088895,
      "gross_profit": 165732647.86,
      "gross_profit_yoy": 0.452124,
      "cogs": 221926670.01,
      "gross_margin": 42.75,
      "pe_forward": null,
      "valuation_history_days": 344,
      "valuation_history_from": "20250210",
      "current_price": 213.98,
      "price": 213.98,
      "ma5": 233.46,
      "ma10": 236.66,
      "ma20": 218.3,
      "dist_ma5_pct": -8.3,
      "dist_ma10_pct": -9.6,
      "dist_ma20_pct": -2.0,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "688536.SH",
      "fetch_time": "2026-07-09T11:35:50+0800",
      "name": "思瑞浦",
      "pe": 164.4367,
      "pb": 6.8168,
      "ps_ttm": 17.8398,
      "pcf_ttm": 135.611,
      "valuation_percentile": 50.52,
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
        "专精特新小巨人主题指数",
        "5G应用指数",
        "专精特新小巨人指数",
        "股权激励指数",
        "5G指数",
        "半导体产业指数",
        "芯片指数",
        "半导体精选指数",
        "AIPC指数",
        "智能家居指数",
        "模拟芯片指数",
        "苏州工业园区指数"
      ],
      "score_company": 8.1,
      "score_trend": 8.8,
      "score_value": 6.2,
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
          "tag": "产能",
          "text": "在建工程占总资产 7.7% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 2459万元 ，较上期增长 43% ，占2025年营收 1.1% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 11% ，很受内资机构青睐。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 半导体 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 96% 的股票，走势很强。"
        }
      ],
      "risks": [
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
          "content": "思瑞浦：关于定向可转债转股结果暨股份变动的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "19:34 思瑞浦公告，公司拟以自有资金投资设立苏州同信嘉远投资合伙企业（有限合伙），认缴出资金额为人民币5亿元，占合伙企业全部合伙份额的38.5802%。公司与苏州泓荣聚川投资有限公司、安徽高新元禾璞华私募股权投资基金合伙企业（有限合伙）、中新苏州工业园区创业投资有限公司、苏州工业园区二期产业投资基金（有限合伙）、苏州怡达芯璟投资实业合伙企业（有限合伙）、共青城芯聚利程股权投资基金合伙企业（有限合伙）、苏州产投致盛股权投资基金合伙企业（有限合伙）、苏州产投致兴股权投资基金合伙企业（有限合伙）签订合伙协议，共同开展产业相关投资。本次交易构成关联交易，尚需提交股东会审议。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "思瑞浦：上海兰迪律师事务所关于思瑞浦微电子科技（苏州）股份有限公司2025年限制性股票激励计划调整授予价格暨第一个归属期归属条件成就及作废部分限制性股票的法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "思瑞浦：国浩律师（上海）事务所关于思瑞浦微电子科技（苏州）股份有限公司2023年限制性股票激励计划授予价格调整相关事项的法律意见书",
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
      "valuation_history_days": 299,
      "valuation_history_from": "20220922",
      "current_price": 340.84,
      "price": 340.84,
      "ma5": 350.79,
      "ma10": 343.74,
      "ma20": 323.97,
      "dist_ma5_pct": -2.8,
      "dist_ma10_pct": -0.8,
      "dist_ma20_pct": 5.2,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "688652.SH",
      "fetch_time": "2026-07-09T11:35:50+0800",
      "name": "京仪装备",
      "pe": 228.9823,
      "pb": 16.1477,
      "ps_ttm": 24.5095,
      "pcf_ttm": 68.7843,
      "valuation_percentile": 99.84,
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
        "专精特新小巨人指数",
        "半导体精选指数",
        "半导体设备指数"
      ],
      "score_company": 7.0,
      "score_trend": 9.6,
      "score_value": 3.3,
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
          "text": "公募基金持股 18% ，很受内资机构青睐。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 半导体 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
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
          "content": "10:49 半导体设备板块在盘中出现震荡反弹走势。其中，正帆科技涨幅超过10%，先锋精科、芯源微、华峰测控、京仪装备以及中科飞测的涨幅均超过6%。\n\n行业消息方面，光刻机厂商ASML宣布上调全年营收指引，主要原因是与AI芯片制造相关的先进光刻设备需求保持增长。此外，世界半导体贸易统计组织发布的2026年春季预测显示，2026年全球半导体市场规模预计将达到1.51万亿美元，同比增幅接近90%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:30股价达到<span style=\"color:#FB475D\"> 180.15 </span>元，创历史新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
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
      "valuation_history_days": 145,
      "valuation_history_from": "20251201",
      "current_price": 203.0,
      "price": 203.0,
      "ma5": 206.46,
      "ma10": 182.56,
      "ma20": 160.32,
      "dist_ma5_pct": -1.7,
      "dist_ma10_pct": 11.2,
      "dist_ma20_pct": 26.6,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "301536.SZ",
      "fetch_time": "2026-07-09T11:35:50+0800",
      "name": "星宸科技",
      "pe": 101.2623,
      "pb": 15.6051,
      "ps_ttm": 14.6475,
      "pcf_ttm": 163.7322,
      "valuation_percentile": 93.32,
      "total_shares": 421715232,
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
        "TMT指数",
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "半导体精选指数",
        "具身智能指数",
        "人工智能指数",
        "模拟芯片指数",
        "安防监控指数"
      ],
      "score_company": 7.9,
      "score_trend": 9.1,
      "score_value": 3.5,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 330% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 20% ，投入资本回报率为 17% ，盈利能力很强。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 8.2% ，很受外资机构青睐。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 半导体 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 95% 的股票，走势较强。"
        },
        {
          "tag": "回购",
          "text": "近6月，公司累计回购 174万股 ，占总股本比例 0.41% ，金额合计 1.2亿元 。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "2027/03/29解禁2.34亿股，占总股本55.60%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2027-03-29"
        },
        {
          "content": "预计2026/08/22发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-22"
        },
        {
          "content": "09:17 企查查APP显示，近日，福建昇宸科技有限公司成立，经营范围包含集成电路芯片设计及服务；人工智能行业应用系统集成服务；半导体分立器件销售；人工智能硬件销售等。企查查股权穿透显示，该公司由星宸科技全资持股。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "09:33股价达到<span style=\"color:#FB475D\"> 97.28 </span>元，创历史新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "在过去的120个交易日内，该股票的价格涨幅高于市场上<span style=\"color:#FB475D\"> 90% </span>的股票",
          "tags": [
            "股价走强"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 2166189687.27,
      "revenue_yoy": 0.194989,
      "operating_profit": 202924835.97,
      "operating_profit_yoy": -0.031514,
      "net_profit": 202184328.67,
      "net_profit_yoy": 0.030301,
      "gross_profit": 723911631.76,
      "gross_profit_yoy": 0.109578,
      "cogs": 1442278055.51,
      "gross_margin": 33.42,
      "pe_forward": null,
      "valuation_history_days": 67,
      "valuation_history_from": "20260330",
      "current_price": 118.83,
      "price": 118.83,
      "ma5": 118.74,
      "ma10": 119.78,
      "ma20": 104.66,
      "dist_ma5_pct": 0.1,
      "dist_ma10_pct": -0.8,
      "dist_ma20_pct": 13.5,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "300346.SZ",
      "fetch_time": "2026-07-09T11:35:53+0800",
      "name": "南大光电",
      "pe": 150.0905,
      "pb": 15.3499,
      "ps_ttm": 19.9608,
      "pcf_ttm": 78.3043,
      "valuation_percentile": 72.61,
      "total_shares": 691156903,
      "industries": [
        {
          "name": "电子",
          "level": 1
        },
        {
          "name": "电子化学品Ⅱ",
          "level": 2
        },
        {
          "name": "电子化学品Ⅲ",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "半导体产业指数",
        "集成电路指数",
        "新材料指数",
        "国家大基金指数",
        "半导体材料指数",
        "OLED指数",
        "新型显示技术指数",
        "LED照明指数",
        "LED指数"
      ],
      "score_company": 7.9,
      "score_trend": 8.6,
      "score_value": 4.4,
      "highlights": [
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 19% ，最新季度归母净利润同比增长 30% ，成长能力很强。"
        },
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 9.8% ，创造价值的能力较强。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 6.8% ，较受内资机构青睐。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 电子化学品Ⅱ 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月01日大跌 -4.22% ，且成交额为近20日均值的 1.69倍 ，抛压很重。"
        },
        {
          "tag": "波动",
          "text": "近10天，日均换手率 15% ，短线资金追逐，波动风险较高。"
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
          "content": "15:01 7月3日，A股市场呈现冲高回落走势，三大指数尾盘涨幅有所收窄。全天沪深两市成交额为3.18万亿元，较前一交易日减少2681亿元。市场整体涨多跌少，全市场超过3800只个股上涨。\n\n盘面上，机器人概念股表现突出，板块内四十余只成分股涨停。其中，埃斯顿实现4天3板，日盈电子收获2连板，长盛轴承、卧龙电驱、首开股份涨停。黄金概念持续走强，招金矿业、赤峰黄金录得2连板，四川黄金、西部黄金、山金国际涨停。电网设备板块中，华明装备、金智科技涨停。医药板块亦有活跃表现，石药景峰实现2连板。\n\n下跌方面，半导体材料板块走弱，电子特气与光刻胶方向领跌，多氟多触及跌停，容大感光、南大光电、华特气体跌幅较大。\n\n截至收盘，沪指上涨0.37%，深成指上涨0.64%，创业板指上涨0.07%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "11:00 根据财联社星矿数据统计，7月3日早盘期间，主力资金在板块配置上呈现分化。交运设备、有色金属及建筑材料板块获得主力资金净流入，而电子、半导体及光学光电子板块则出现资金净流出，其中电子板块整体净流出规模超过197亿元。\n\n在个股表现方面，新易盛股价上涨，主力资金净买入额超过20.87亿元。中国巨石、紫金矿业、立讯精密同样获得主力资金净流入。另一方面，京东方A遭遇主力资金净卖出超过36亿元，兆易创新、南大光电及长川科技的资金净流出额也处于市场前列。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "截至2026/06/29，沈洁(公司持股5%以上股东)减持已完成，实际减持累计 <span style=\"color:#00B985\">691万股 </span>，按近二十个交易日成交均价 <span style=\"color:#00B985\">58元/股 </span>，套现 <span style=\"color:#00B985\">4.03亿元 </span>，此次减持后持股数为6045万股 （该主体计划减持不超过691万股，占总股本的1.00%，占其持有公司股份的10.3%，变动价格说明：根据减持时的市场价格及交易方式确定 )<br><br>交易方式：集中竞价、大宗交易",
          "tags": [
            "非控股股东减持"
          ]
        },
        {
          "content": "10:08股价达到<span style=\"color:#FB475D\"> 64.8 </span>元，创历史新高",
          "tags": [
            "股价新高"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1884280819.77,
      "revenue_yoy": 0.068296,
      "operating_profit": 417967710.47,
      "operating_profit_yoy": 0.020992,
      "net_profit": 375464796.38,
      "net_profit_yoy": 0.038146,
      "gross_profit": 747367189.6,
      "gross_profit_yoy": -0.00625,
      "cogs": 1136913630.17,
      "gross_margin": 39.66,
      "pe_forward": null,
      "valuation_history_days": 300,
      "valuation_history_from": "20210709",
      "current_price": 76.42,
      "price": 76.42,
      "ma5": 81.52,
      "ma10": 81.83,
      "ma20": 70.12,
      "dist_ma5_pct": -6.3,
      "dist_ma10_pct": -6.6,
      "dist_ma20_pct": 9.0,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "688378.SH",
      "fetch_time": "2026-07-09T11:35:53+0800",
      "name": "奥来德",
      "pe": 103.4613,
      "pb": 6.5515,
      "ps_ttm": 19.9339,
      "pcf_ttm": 42.0874,
      "valuation_percentile": 95.59,
      "total_shares": 261425164,
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
          "name": "光学元件",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "万得预增指数",
        "OLED指数",
        "光学光电子精选指数",
        "长吉图指数",
        "OLED材料指数"
      ],
      "score_company": 7.7,
      "score_trend": 8.4,
      "score_value": 3.5,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 5950% ，利润成长性强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 117% ，净利润现金含量很高。"
        },
        {
          "tag": "订单",
          "text": "合同负债 1.4亿元 ，较上期增长 860% ，占2025年营收 25% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 光学光电子 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        }
      ],
      "risks": [
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 33% ，扣非净利润占净利润 37% ，收益质量很低。"
        }
      ],
      "events": [
        {
          "content": "2026/08/25解禁831.87万股，占总股本3.18%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-08-25"
        },
        {
          "content": "预计2026/08/20发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-20"
        },
        {
          "content": "公司发布2026半年报预告，股价盘中上涨<span style=\"color:#FB475DC\"> 8.62% </span>，股价收盘涨幅<span style=\"color:#FB475D\"> 4.15% </span>",
          "tags": [
            "股价上涨"
          ]
        },
        {
          "content": "08:20 华为半导体负责人何庭波于7月3日发布《面向多层级电子系统的时间缩微理论》V2版本，在V1基础上补充了工程细节、实测量化数据及演进路线，完善了后摩尔时代缩放理论体系。\n\n证监会就完善上市公司再融资规则公开征求意见，拟建立再融资定向增发储架发行制度，并提升沪深交易所上市公司小额快速融资上限至6亿元。\n\n财政部、税务总局、工业和信息化部公告，自2027年1月1日起，取消节能汽车车船税减半政策，取消纯电动商用车、插电式混合动力汽车、燃料电池商用车免征车船税政策，纯电动及燃料电池乘用车不受影响。\n\n部分充电模块企业因原材料成本上升，已确定自7月1日起对全系产品涨价15%。\n\n华强北存储市场内存条和固态硬盘价格回升，三星、金士顿、闪迪相关产品价格上行。上海多位PC经销商表示零部件和整机价格处于高位，且未来仍有涨价预期。\n\n国务院印发《美丽中国建设“十五五”规划》，提出合理控制煤电装机规模，全面提升可再生能源电力消费比重。\n\n国家药监局综合司就优化细胞与基因治疗药品审评审批事项征求意见，拟将符合条件的药品纳入30日审评审批通道。\n\n7月5日21时43分，长征八号甲运载火箭成功将千帆极轨15组卫星送入预定轨道。\n\n中国人民银行公告，7月6日开展10000亿元买断式逆回购操作，期限为3个月。\n\n市场监管总局、商务部起草《中华人民共和国电子商务法（修正草案征求意见稿）》并公开征求意见。\n\n江波龙预计上半年净利润同比增长62204%-74394%；中电港预计上半年净利同比增长176%-193%。\n\n杭电股份预计上半年净利同比增长852%-958%；永鼎股份预计Q2净利环比增长114%-240%。\n\n国泰海通预计2026年上半年归母净利润200.03亿元至205.11亿元，同比增加164%到171%，创半年度业绩历史新高。\n\n东岳硅材预计上半年净利润同比增长905%-952%；奥来德预计上半年净利同比增长492%-604%；天山铝业预计上半年净利同比增长102%；招商轮船预计上半年净利同比增长214%-248%；东方盛虹预计上半年净利同比增长987%-1195%。\n\n鹏鼎控股拟定增募资不超96亿元；联动科技拟1000万美元收购Northstar Technologies Limited 100%股权；凯瑞德拟8000万元投资艾可萨科技。\n\n中际旭创澄清上游物料被封锁传言不实。天赐材料子公司终止年产24.3万吨锂电及含氟新材料项目。国轩高科子公司上半年出售铜冠铜箔股票收益率达1987%。日联科技子公司认购QES Group Berhad增发股份。\n\n宏和科技第二、三大股东合计减持875.03万股；仕佳光子第三大股东拟减持不超1%股份。\n\n申昊科技拟不超20亿元采购服务器开展算力租赁业务。神州数码中标某国有大行3.71亿元华为智算服务器采购项目。\n\n翰宇药业司美格鲁肽注射液上市申请获受理。益盛药业生脉注射液及补金片被暂停生产销售。\n\nSK海力士寻求在美上市募资290亿美元。美光科技动工扩建日本广岛工厂，投资1.5万亿日元生产HBM芯片。三星电子拟将Q3 DRAM平均售价环比提高20%，且正成为全球大科技公司自研AI芯片核心生产基地。\n\n韩国政府计划推动东南部地区投资超312万亿韩元发展先进制造与AI产业，并设立投资基金支持半导体、物理AI和数据中心项目。\n\n截至7月1日的一周，美国股票基金流出172亿美元。鸿海6月销售额同比增长52.1%。\n\n摩根大通预计黄金短期区间震荡，2026年第三季度均价为4300美元/盎司，第四季度为4500美元/盎司。OPEC+同意8月小幅提高石油产量配额。花旗预计布伦特原油年底可能跌至60美元/桶。美伊新一轮谈判将于11日在巴基斯坦举行。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": null,
          "tags": [
            "2026年中报业绩预告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 389005051.84,
      "revenue_yoy": -0.161249,
      "operating_profit": 20893824.87,
      "operating_profit_yoy": -0.805635,
      "net_profit": 31356053.44,
      "net_profit_yoy": -0.690314,
      "gross_profit": 175491111.3,
      "gross_profit_yoy": -0.261232,
      "cogs": 213513940.54,
      "gross_margin": 45.11,
      "pe_forward": null,
      "valuation_history_days": 309,
      "valuation_history_from": "20220905",
      "current_price": 58.2,
      "price": 58.2,
      "ma5": 58.58,
      "ma10": 57.16,
      "ma20": 52.27,
      "dist_ma5_pct": -0.7,
      "dist_ma10_pct": 1.8,
      "dist_ma20_pct": 11.3,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "300236.SZ",
      "fetch_time": "2026-07-09T11:35:53+0800",
      "name": "上海新阳",
      "pe": 109.4908,
      "pb": 8.2949,
      "ps_ttm": 18.5907,
      "pcf_ttm": 77.2521,
      "valuation_percentile": 78.95,
      "total_shares": 313382153,
      "industries": [
        {
          "name": "电子",
          "level": 1
        },
        {
          "name": "电子化学品Ⅱ",
          "level": 2
        },
        {
          "name": "电子化学品Ⅲ",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "股权激励指数",
        "半导体产业指数",
        "资源股",
        "芯片指数",
        "集成电路指数",
        "养老金指数",
        "中小创蓝筹指数",
        "中芯国际产业链指数",
        "长鑫存储指数",
        "晶圆产业指数",
        "存储器指数",
        "半导体材料指数",
        "模拟芯片指数",
        "半导体硅片指数"
      ],
      "score_company": 8.3,
      "score_trend": 7.8,
      "score_value": 4.1,
      "highlights": [
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 20% ，最新季度归母净利润同比增长 103% ，成长能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 114% ，净利润现金含量较高。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 5.4% ，较受内资机构青睐。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 电子化学品Ⅱ 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 95% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月01日大跌 -4.17% ，且成交额为近20日均值的 1.61倍 ，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/21发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-21"
        },
        {
          "content": "10:13 先进封装板块再度拉升，华天科技、中京电子、朗迪集团、高德红外、同兴达、旭光电子涨停，上海新阳涨超10%，汇成股份、深科达、深科技、太极实业、甬矽电子跟涨。相关ETF方面，科创芯片ETF汇添富（588750）涨1.57%，成交额1.6亿元，芯片ETF广发（159801）涨2.44%，成交额2.17亿元。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "在过去的60个交易日内，该股票的价格涨幅高于市场上<span style=\"color:#FB475D\"> 91% </span>的股票",
          "tags": [
            "股价走强"
          ]
        },
        {
          "content": "10:39股价达到<span style=\"color:#FB475D\"> 114.42 </span>元，创历史新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "上海新阳：关于公司及全资子公司完成工商变更登记的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1393680939.51,
      "revenue_yoy": 0.306174,
      "operating_profit": 226654616.19,
      "operating_profit_yoy": 0.610435,
      "net_profit": 211412597.44,
      "net_profit_yoy": 0.626836,
      "gross_profit": 563832180.82,
      "gross_profit_yoy": 0.358695,
      "cogs": 829848758.69,
      "gross_margin": 40.46,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210709",
      "current_price": 113.01,
      "price": 113.01,
      "ma5": 114.14,
      "ma10": 116.59,
      "ma20": 106.6,
      "dist_ma5_pct": -1.0,
      "dist_ma10_pct": -3.1,
      "dist_ma20_pct": 6.0,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "300726.SZ",
      "fetch_time": "2026-07-09T11:35:53+0800",
      "name": "宏达电子",
      "pe": 62.3583,
      "pb": 5.7266,
      "ps_ttm": 14.2568,
      "pcf_ttm": 74.1603,
      "valuation_percentile": 64.58,
      "total_shares": 411839845,
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
        "华为平台指数",
        "中小创蓝筹指数",
        "军民融合指数",
        "MLCC指数"
      ],
      "score_company": 7.8,
      "score_trend": 8.0,
      "score_value": 4.7,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 71% ，利润成长性强。"
        },
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 15% ，创造价值的能力很强。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 1.5% ，现金分红较高。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 95% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "波动",
          "text": "2026年06月16日，换手率 22% ，短线资金追逐，波动风险较高。"
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
          "content": "在过去的10个交易日内，该股票的价格涨幅仅高于市场上<span style=\"color:#00B985\"> 3.8% </span>的股票",
          "tags": [
            "股价走弱"
          ]
        },
        {
          "content": "在过去的120个交易日内，该股票的价格涨幅高于市场上<span style=\"color:#FB475D\"> 90% </span>的股票",
          "tags": [
            "股价走强"
          ]
        },
        {
          "content": "14:15股价达到<span style=\"color:#FB475D\"> 89.28 </span>元，创近24个月新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "18:10 宏达电子公告，公司于2026年6月17日召开的第四届董事会第十六次会议审议通过了收购控股子公司宏达磁电和宏达恒芯部分股权暨关联交易的议案。陈思铭女士将其持有的宏达磁电4.98万元股权（占注册资本1.51%）和宏达恒芯20万元股权（占注册资本2.5%）全部转让给宏达电子，转让价格分别为369.86万元和387.2万元。交易完成后，宏达电子在宏达磁电和宏达恒芯的持股比例分别增至56.0364%和63.50%。",
          "tags": [
            "快讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1404274174.61,
      "revenue_yoy": 0.188056,
      "operating_profit": 467542097.35,
      "operating_profit_yoy": 0.140739,
      "net_profit": 393263756.68,
      "net_profit_yoy": 0.244264,
      "gross_profit": 817900645.81,
      "gross_profit_yoy": 0.125984,
      "cogs": 586373528.8,
      "gross_margin": 58.24,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210709",
      "current_price": 69.83,
      "price": 69.83,
      "ma5": 76.2,
      "ma10": 81.21,
      "ma20": 75.31,
      "dist_ma5_pct": -8.4,
      "dist_ma10_pct": -14.0,
      "dist_ma20_pct": -7.3,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "002810.SZ",
      "fetch_time": "2026-07-09T11:35:53+0800",
      "name": "山东赫达",
      "pe": 35.992,
      "pb": 3.2155,
      "ps_ttm": 3.5126,
      "pcf_ttm": 15.0963,
      "valuation_percentile": 49.32,
      "total_shares": 349663513,
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
          "name": "其他化学制品",
          "level": 3
        }
      ],
      "concepts": [
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "股权激励指数",
        "可转债正股指数",
        "养老金指数",
        "预期提升指数",
        "万得预增指数",
        "化学制品精选指数"
      ],
      "score_company": 7.9,
      "score_trend": 7.5,
      "score_value": 6.2,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 65% ，利润成长性强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 126% ，净利润现金含量很高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 4.1% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 2.6% ，较受外资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月08日大跌 -9.98% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月08日 至今陷入调整，资金有出逃可能。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/19发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-19"
        },
        {
          "content": "2025年年度：每10股派2元",
          "tags": [
            "分红送转"
          ],
          "date": "2026-07-15"
        },
        {
          "content": "15:00 今天大跌的原因可能是公司公布Q2净利润预计环比下降1%至20%，业绩下滑或幅度不及预期，削弱投资者信心，压低股价。",
          "tags": [
            "快讯",
            "大跌原因"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价盘中下跌<span style=\"color:#00B985\"> -8.34% </span>",
          "tags": [
            "股价下跌"
          ]
        },
        {
          "content": null,
          "tags": [
            "2026年中报业绩预告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1436691620.62,
      "revenue_yoy": 0.001064,
      "operating_profit": 172781189.96,
      "operating_profit_yoy": -0.237041,
      "net_profit": 139322911.37,
      "net_profit_yoy": -0.296512,
      "gross_profit": 368280557.96,
      "gross_profit_yoy": -0.052984,
      "cogs": 1068411062.66,
      "gross_margin": 25.63,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210709",
      "current_price": 22.03,
      "price": 22.03,
      "ma5": 24.51,
      "ma10": 24.5,
      "ma20": 23.82,
      "dist_ma5_pct": -10.1,
      "dist_ma10_pct": -10.1,
      "dist_ma20_pct": -7.5,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "300373.SZ",
      "fetch_time": "2026-07-09T11:35:53+0800",
      "name": "扬杰科技",
      "pe": 50.2387,
      "pb": 7.1441,
      "ps_ttm": 8.9644,
      "pcf_ttm": 42.6053,
      "valuation_percentile": 88.19,
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
        "5G指数",
        "半导体产业指数",
        "半导体精选指数",
        "集成电路指数",
        "中小创蓝筹指数",
        "GDR指数",
        "晶圆产业指数",
        "华为合作半导体企业指数",
        "汽车芯片指数",
        "IGBT指数"
      ],
      "score_company": 8.7,
      "score_trend": 8.6,
      "score_value": 3.7,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 41% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 14% ，投入资本回报率为 12% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 12% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 半导体 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
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
          "content": "13:39 7月7日午后，碳化硅概念板块出现局部波动。露笑科技股价直线拉升并触及涨停板。此前，东微半导已实现20cm涨停，易事特、英杰电气、扬杰科技、三安光电及华微电子等个股跟涨。\n\n行业消息显示，英伟达在算力中心供电白皮书中，将SST确立为下一代800V高压直流供电架构的核心设备。该设备利用碳化硅功率器件的高频特性，能够实现从10kV中压交流到800V直流的一步式转换。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "扬杰科技：江苏泰和律师事务所关于公司2026年第一次临时股东会的法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "07:21 7月起，全球半导体行业迎来新一轮价格调整。记者获悉，近日，芯联集成、斯达半导、扬杰科技、聚辰股份等多家半导体公司向客户发出了涨价函，价格上调幅度为15%至25%。据记者不完全统计，超过20家国内外半导体公司在上半年发布了第一轮涨价函。目前，相关公司均宣布了新一轮涨价通知。细看各家公司的涨价通知函，成本上涨、AI需求爆发是调价的核心诱因。（上海证券报）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "09:31股价达到<span style=\"color:#FB475D\"> 119.68 </span>元，创历史新高",
          "tags": [
            "股价新高"
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
      "valuation_history_from": "20210709",
      "current_price": 131.01,
      "price": 131.01,
      "ma5": 134.27,
      "ma10": 137.82,
      "ma20": 121.11,
      "dist_ma5_pct": -2.4,
      "dist_ma10_pct": -4.9,
      "dist_ma20_pct": 8.2,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "002805.SZ",
      "fetch_time": "2026-07-09T11:35:53+0800",
      "name": "丰元股份",
      "pe": -21.6833,
      "pb": 6.9092,
      "ps_ttm": 1.9332,
      "pcf_ttm": null,
      "valuation_percentile": 61.72,
      "total_shares": 280062508,
      "industries": [
        {
          "name": "电力设备",
          "level": 1
        },
        {
          "name": "电池",
          "level": 2
        },
        {
          "name": "电池化学品",
          "level": 3
        }
      ],
      "concepts": [
        "专精特新小巨人主题指数",
        "QFII重仓指数",
        "业绩预亏指数",
        "固态电池指数",
        "磷酸铁锂电池指数",
        "近期定增指数",
        "锂电正极指数"
      ],
      "score_company": 3.9,
      "score_trend": 8.3,
      "score_value": 5.2,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年04月29日，业绩超预期引发股价跳空高开，当日收涨 10.0% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 186% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 7.7% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 3.7% ，较受外资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 93% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "现金",
          "text": "近5年，净现比为 -331% ，收现比仅为 45% ，净利润与销售收入中的现金含量很低。"
        },
        {
          "tag": "应收",
          "text": "近5年，应收账款周转天数增加 9天 ，坏账损失风险升高。"
        },
        {
          "tag": "偿债",
          "text": "带息债务占全部投入资本 52% ，偿债压力较大。"
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
          "content": "09:32 电池板块盘初拉升，容百科技涨超10%，雄韬股份、丰元股份、圣阳股份、恩捷股份纷纷拉升。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "在过去的250个交易日内，该股票的价格涨幅高于市场上<span style=\"color:#FB475D\"> 90% </span>的股票",
          "tags": [
            "股价走强"
          ]
        },
        {
          "content": "股东大会日通过增发预案，股价盘中上涨<span style=\"color:#FB475DC\"> 9.97% </span>，股价收盘涨幅<span style=\"color:#FB475D\"> 10.00% </span>",
          "tags": [
            "股价上涨"
          ]
        },
        {
          "content": "丰元股份：关于为控股孙公司提供担保的进展公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1172429641.63,
      "revenue_yoy": 0.196991,
      "operating_profit": -409744195.71,
      "operating_profit_yoy": -1.043082,
      "net_profit": -414975959.02,
      "net_profit_yoy": -1.571287,
      "gross_profit": -181395133.36,
      "gross_profit_yoy": -0.682266,
      "cogs": 1353824774.99,
      "gross_margin": -15.47,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20210709",
      "current_price": 25.29,
      "price": 25.29,
      "ma5": 27.0,
      "ma10": 27.6,
      "ma20": 24.76,
      "dist_ma5_pct": -6.3,
      "dist_ma10_pct": -8.4,
      "dist_ma20_pct": 2.2,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "601958.SH",
      "fetch_time": "2026-07-09T11:35:53+0800",
      "name": "金钼股份",
      "pe": 20.4671,
      "pb": 3.491,
      "ps_ttm": 4.7008,
      "pcf_ttm": 31.972,
      "valuation_percentile": 85.07,
      "total_shares": 3226604400,
      "industries": [
        {
          "name": "有色金属",
          "level": 1
        },
        {
          "name": "小金属",
          "level": 2
        },
        {
          "name": "钼",
          "level": 3
        }
      ],
      "concepts": [
        "资源股",
        "西部大开发指数",
        "有色金属指数",
        "小金属指数",
        "西安指数",
        "稀有金属精选指数",
        "西安高新区指数",
        "陕西省国资指数",
        "靶材指数"
      ],
      "score_company": 8.7,
      "score_trend": 7.9,
      "score_value": 3.9,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 钼 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年04月29日，业绩超预期引发股价大幅上涨，当日收涨 6.56% 。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 14% ，投入资本回报率为 18% ，盈利能力很强。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 2.8% ，现金分红极高。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 3.4% ，较受外资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 90% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月23日大跌 -8.76% ，且成交额为近20日均值的 2.06倍 ，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/21发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-21"
        },
        {
          "content": "14:14 小金属板块持续下行，东方锆业、云南锗业跌停，华锡有色此前跌停，宝武镁业、长裕集团、中矿资源、金钼股份、贵研铂业跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "在过去的10个交易日内，该股票的价格涨幅仅高于市场上<span style=\"color:#00B985\"> 2.9% </span>的股票",
          "tags": [
            "股价走弱"
          ]
        },
        {
          "content": "在过去的60个交易日内，该股票的价格涨幅高于市场上<span style=\"color:#FB475D\"> 92% </span>的股票",
          "tags": [
            "股价走强"
          ]
        },
        {
          "content": "09:47 小金属板块盘初拉升，宝武镁业涨停，翔鹭钨业、金钼股份、锡业股份、厦门钨业、中钨高新跟涨。相关ETF方面，有色ETF富国（159168）成交额810.81万元，有色ETF广发（159029）成交额284.88万元。",
          "tags": [
            "快讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 10885028204.63,
      "revenue_yoy": 0.077993,
      "operating_profit": 3008910945.96,
      "operating_profit_yoy": 0.036801,
      "net_profit": 2552455517.11,
      "net_profit_yoy": 0.036651,
      "gross_profit": 4119774173.58,
      "gross_profit_yoy": 0.016356,
      "cogs": 6765254031.05,
      "gross_margin": 37.85,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20210709",
      "current_price": 23.52,
      "price": 23.52,
      "ma5": 25.85,
      "ma10": 27.14,
      "ma20": 25.76,
      "dist_ma5_pct": -9.0,
      "dist_ma10_pct": -13.4,
      "dist_ma20_pct": -8.7,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "002407.SZ",
      "fetch_time": "2026-07-09T11:35:55+0800",
      "name": "多氟多",
      "pe": 93.1699,
      "pb": 5.7128,
      "ps_ttm": 4.6231,
      "pcf_ttm": null,
      "valuation_percentile": 76.23,
      "total_shares": 1190432569,
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
        "资源股",
        "分拆上市指数",
        "AI手机指数",
        "新材料指数",
        "新能源汽车指数",
        "锂电池指数",
        "固态电池指数",
        "钠离子电池指数",
        "动力电池指数",
        "半导体材料指数",
        "六氟磷酸锂指数",
        "三元锂电池指数",
        "PVDF指数",
        "氢氟酸指数",
        "氟化工指数",
        "中原经济区指数",
        "锂电电解液指数",
        "制冷剂指数",
        "萤石指数"
      ],
      "score_company": 7.7,
      "score_trend": 8.6,
      "score_value": 4.5,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年04月24日，业绩超预期引发股价大幅上涨，当日收涨 9.99% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 480% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 14% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 2.7亿元 ，较上期增长 37% ，占2025年营收 2.9% ，在手订单充足。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 4.2% ，很受外资机构青睐；公募基金持股 5.7% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月03日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "波动",
          "text": "近5天，日均换手率 23% ，短线资金追逐，波动风险很高。"
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
          "content": "多氟多：关于归还募集资金的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "16:51 算力硬件及半导体产业链近期持续调整，中际旭创、澜起科技、兆易创新、长电科技等权重股全天冲高回落，最终收跌。半导体材料板块出现补跌，气派科技、立昂微、兴福电子、江钨装备、多氟多、巨化股份等多只个股跌停。\n\n市场整体涨停个股数量维持在百只左右，机器人概念板块表现活跃，超过四十只成分股涨停或涨幅超过10%。其中，埃斯顿实现4天3板，日盈电子、雷赛智能录得2连板，绿的谐波、三花智控、拓普集团等权重股涨幅明显。\n\n创新药板块持续活跃，石药景峰实现2连板，万邦医药、热景生物、信立泰等个股放量冲高。当前市场短线热点呈现高低切换特征，后续可关注中报业绩，在低位赛道寻找补涨机会。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "16:33 多氟多今日跌10.00%，成交额119.63亿元，换手率22.12%，盘后龙虎榜数据显示，深股通专用席位买入4.22亿元并卖出9.15亿元，国泰海通南京太平南路净买入6.03亿元，有3家机构专用席位净卖出2.85亿元。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "预计2026/08/18发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-18"
        }
      ],
      "report_period": "20250930",
      "revenue": 6728835959.46,
      "revenue_yoy": -0.027493,
      "operating_profit": 55694342.19,
      "operating_profit_yoy": -0.34047,
      "net_profit": 64930979.05,
      "net_profit_yoy": 3.370697,
      "gross_profit": 759187930.55,
      "gross_profit_yoy": 0.344863,
      "cogs": 5969648028.91,
      "gross_margin": 11.28,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210709",
      "current_price": 40.98,
      "price": 40.98,
      "ma5": 45.57,
      "ma10": 47.87,
      "ma20": 42.22,
      "dist_ma5_pct": -10.1,
      "dist_ma10_pct": -14.4,
      "dist_ma20_pct": -2.9,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "300438.SZ",
      "fetch_time": "2026-07-09T11:35:55+0800",
      "name": "鹏辉能源",
      "pe": 57.2244,
      "pb": 5.8014,
      "ps_ttm": 2.1883,
      "pcf_ttm": 29.8134,
      "valuation_percentile": 57.19,
      "total_shares": 503343360,
      "industries": [
        {
          "name": "电力设备",
          "level": 1
        },
        {
          "name": "电池",
          "level": 2
        },
        {
          "name": "锂电池",
          "level": 3
        }
      ],
      "concepts": [
        "股权激励指数",
        "QFII重仓指数",
        "养老金指数",
        "锂电池指数",
        "预期提升指数",
        "储能指数",
        "固态电池指数",
        "钠离子电池指数",
        "动力电池指数",
        "TWS耳机指数",
        "ETC指数"
      ],
      "score_company": 8.2,
      "score_trend": 8.2,
      "score_value": 6.1,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年04月29日，业绩超预期引发股价大幅上涨，当日收涨 20.0% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 819% ，利润成长性强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 14亿元 ，较上期增长 70% ，占2025年营收 12% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 5.3% ，很受外资机构青睐；公募基金持股 6.5% ，较受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 93% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "收现",
          "text": "近5年，收现比为 69% ，销售收入现金含量很低。"
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
          "content": "09:42 锂电池板块短线拉升，诺德股份涨停, 中一科技涨超10%，嘉元科技、中瑞股份、铜冠铜箔、鹏辉能源、科达利等跟涨。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "09:28 锂电池板块高开，诺德股份一字涨停，亿纬锂能高开超13%，铜冠铜箔、中瑞股份、鹏辉能源涨幅居前。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "在过去的60个交易日内，该股票的价格涨幅高于市场上<span style=\"color:#FB475D\"> 92% </span>的股票",
          "tags": [
            "股价走强"
          ]
        },
        {
          "content": "10:29股价达到<span style=\"color:#FB475D\"> 92.32 </span>元，创近24个月新高",
          "tags": [
            "股价新高"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 7580860529.35,
      "revenue_yoy": 0.342255,
      "operating_profit": 104220164.37,
      "operating_profit_yoy": 6.778252,
      "net_profit": 104734476.67,
      "net_profit_yoy": 2.384669,
      "gross_profit": 1129603681.34,
      "gross_profit_yoy": 0.422118,
      "cogs": 6451256848.01,
      "gross_margin": 14.9,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210709",
      "current_price": 70.37,
      "price": 70.37,
      "ma5": 75.75,
      "ma10": 79.41,
      "ma20": 77.49,
      "dist_ma5_pct": -7.1,
      "dist_ma10_pct": -11.4,
      "dist_ma20_pct": -9.2,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "688401.SH",
      "fetch_time": "2026-07-09T11:35:55+0800",
      "name": "路维光电",
      "pe": 64.5719,
      "pb": 10.9632,
      "ps_ttm": 14.3262,
      "pcf_ttm": 59.3415,
      "valuation_percentile": 95.57,
      "total_shares": 193349517,
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
        "专精特新小巨人指数",
        "半导体精选指数",
        "可转债正股指数",
        "IPO现场检查指数"
      ],
      "score_company": 8.4,
      "score_trend": 8.9,
      "score_value": 3.4,
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
        },
        {
          "tag": "趋势",
          "text": "公司所属 半导体 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 96% 的股票，走势较强。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/26发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-26"
        },
        {
          "content": "路维光电：北京观韬律师事务所关于深圳市路维光电股份有限公司2026年度向特定对象发行A股股票发行过程和认购对象合规性的法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "路维光电：深圳市路维光电股份有限公司验资报告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "路维光电：深圳市路维光电股份有限公司2026年度向特定对象发行股票发行情况报告书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "路维光电：国信证券股份有限公司关于深圳市路维光电股份有限公司2026年度向特定对象发行股票发行过程和认购对象合规性的报告",
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
      "valuation_history_days": 453,
      "valuation_history_from": "20240819",
      "current_price": 85.88,
      "price": 85.88,
      "ma5": 92.89,
      "ma10": 88.12,
      "ma20": 82.48,
      "dist_ma5_pct": -7.6,
      "dist_ma10_pct": -2.5,
      "dist_ma20_pct": 4.1,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "688390.SH",
      "fetch_time": "2026-07-09T11:35:55+0800",
      "name": "固德威",
      "pe": 71.4563,
      "pb": 6.6414,
      "ps_ttm": 2.0169,
      "pcf_ttm": 23.1397,
      "valuation_percentile": 30.66,
      "total_shares": 243062217,
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
          "name": "逆变器",
          "level": 3
        }
      ],
      "concepts": [
        "专精特新小巨人主题指数",
        "股权激励指数",
        "储能指数",
        "新能源指数",
        "可转债预案指数",
        "光伏指数",
        "能源出海指数",
        "电源设备精选指数",
        "光伏逆变器指数"
      ],
      "score_company": 8.5,
      "score_trend": 5.8,
      "score_value": 7.4,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年04月29日，业绩超预期引发股价大幅上涨，当日收涨 15.1% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 462% ，利润成长性强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 3.0亿元 ，较上期增长 17% ，占2025年营收 3.3% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 9家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 8.2% ，很受外资机构青睐；公募基金持股 5.4% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月05日大跌 -13% ，且成交额为近20日均值的 2.07倍 ，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月29日 至今陷入调整，资金有出逃可能。"
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
          "content": "09:33 光伏设备板块盘初走弱，阳光电源跌超15%，锦浪科技、正泰电源、帝尔激光、固德威、上能电气跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "固德威：北京市天元律师事务所关于固德威技术股份有限公司2026年第三次临时股东会的法律意见",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "在过去的10个交易日内，该股票的价格涨幅仅高于市场上<span style=\"color:#00B985\"> 5.8% </span>的股票",
          "tags": [
            "股价走弱"
          ]
        },
        {
          "content": "10:01 逆变器板块持续走高，正泰电源涨停，固德威涨超10%，锦浪科技、阳光电源、艾罗能源、昱能科技、德业股份等跟涨。消息面上，海关总署近期公布逆变器2026年4月出口数据，出口407.4万台，年内累计出口1515万台，累计出口金额33.6亿美元，同比+30.32%。",
          "tags": [
            "快讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 6194276239.56,
      "revenue_yoy": 0.253041,
      "operating_profit": 84661976.58,
      "operating_profit_yoy": 0.921295,
      "net_profit": 115960506.56,
      "net_profit_yoy": 1.033808,
      "gross_profit": 1366890304.79,
      "gross_profit_yoy": 0.202173,
      "cogs": 4827385934.77,
      "gross_margin": 22.07,
      "pe_forward": null,
      "valuation_history_days": 310,
      "valuation_history_from": "20220905",
      "current_price": 89.7,
      "price": 89.7,
      "ma5": 97.41,
      "ma10": 105.64,
      "ma20": 117.09,
      "dist_ma5_pct": -7.9,
      "dist_ma10_pct": -15.1,
      "dist_ma20_pct": -23.4,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "300037.SZ",
      "fetch_time": "2026-07-09T11:35:55+0800",
      "name": "新宙邦",
      "pe": 42.5964,
      "pb": 5.4002,
      "ps_ttm": 5.2207,
      "pcf_ttm": 36.0343,
      "valuation_percentile": 78.02,
      "total_shares": 753886428,
      "industries": [
        {
          "name": "电力设备",
          "level": 1
        },
        {
          "name": "电池",
          "level": 2
        },
        {
          "name": "电池化学品",
          "level": 3
        }
      ],
      "concepts": [
        "双创100指数",
        "股权激励指数",
        "珠三角指数",
        "资源股",
        "碳中和指数",
        "AI手机指数",
        "深圳本地股指数",
        "可转债正股指数",
        "新材料指数",
        "新能源汽车指数",
        "锂电池指数",
        "特斯拉指数",
        "中小创蓝筹指数"
      ],
      "score_company": 9.3,
      "score_trend": 8.3,
      "score_value": 4.3,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 109% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 14% ，投入资本回报率为 13% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 123% ，净利润现金含量很高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 5.6% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "预测",
          "text": " 12家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 11% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 91% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "偿债",
          "text": "现金短债比为 0.32 ，货币资金对短期债务的保障较弱。"
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
          "content": "09:42 电池板块盘初下挫，德新科技触及跌停，雄韬股份、浙江恒威、吉和昌、力王股份、新宙邦跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "在过去的120个交易日内，该股票的价格涨幅高于市场上<span style=\"color:#FB475D\"> 91% </span>的股票",
          "tags": [
            "股价走强"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是工信部支持固态电解质等材料攻关，新宙邦作为电解液及新型电解质龙头有望受益于政策推动和技术突破。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "新宙邦：北京市中伦（深圳）律师事务所关于深圳新宙邦科技股份有限公司2026年第二次临时股东会的法律意见书",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 6616404669.38,
      "revenue_yoy": 0.167522,
      "operating_profit": 885588672.41,
      "operating_profit_yoy": 0.067748,
      "net_profit": 766972102.4,
      "net_profit_yoy": 0.084499,
      "gross_profit": 1621576451.91,
      "gross_profit_yoy": 0.056372,
      "cogs": 4994828217.47,
      "gross_margin": 24.51,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210709",
      "current_price": 80.27,
      "price": 80.27,
      "ma5": 87.24,
      "ma10": 88.36,
      "ma20": 81.97,
      "dist_ma5_pct": -8.0,
      "dist_ma10_pct": -9.2,
      "dist_ma20_pct": -2.1,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "688392.SH",
      "fetch_time": "2026-07-09T11:35:55+0800",
      "name": "骄成超声",
      "pe": 193.3107,
      "pb": 15.2014,
      "ps_ttm": 33.8074,
      "pcf_ttm": 219.6749,
      "valuation_percentile": 97.32,
      "total_shares": 115733360,
      "industries": [
        {
          "name": "电力设备",
          "level": 1
        },
        {
          "name": "电池",
          "level": 2
        },
        {
          "name": "锂电专用设备",
          "level": 3
        }
      ],
      "concepts": [
        "专精特新小巨人主题指数",
        "专精特新小巨人指数"
      ],
      "score_company": 8.2,
      "score_trend": 9.4,
      "score_value": 3.4,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 锂电专用设备 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 113% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 6.8% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 1.1亿元 ，较上期增长 54% ，占2025年营收 14% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 9家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 12% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 96% 的股票，走势很强。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "15:00 今天大涨的原因可能是公司披露并购重组进展显示交易推进顺利，未来有望通过并购扩充超声设备技术与产能、提升市场份额和业绩预期。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "在过去的20个交易日内，该股票的价格涨幅高于市场上<span style=\"color:#FB475D\"> 95% </span>的股票",
          "tags": [
            "股价走强"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是公司拟以2076.38万元收购子公司剩余40%股权，取得100%控股利于业务整合与提升盈利能力。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "骄成超声：关于收购控股子公司少数股东股权暨关联交易的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 520517440.41,
      "revenue_yoy": 0.27526,
      "operating_profit": 97901473.56,
      "operating_profit_yoy": 6.824508,
      "net_profit": 86964078.78,
      "net_profit_yoy": 3.361346,
      "gross_profit": 338621908.99,
      "gross_profit_yoy": 0.614836,
      "cogs": 181895531.42,
      "gross_margin": 65.05,
      "pe_forward": null,
      "valuation_history_days": 425,
      "valuation_history_from": "20240927",
      "current_price": 218.89,
      "price": 218.89,
      "ma5": 222.38,
      "ma10": 198.33,
      "ma20": 178.07,
      "dist_ma5_pct": -1.6,
      "dist_ma10_pct": 10.4,
      "dist_ma20_pct": 22.9,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "688372.SH",
      "fetch_time": "2026-07-09T11:35:55+0800",
      "name": "伟测科技",
      "pe": 88.5649,
      "pb": 7.5128,
      "ps_ttm": 17.3276,
      "pcf_ttm": 40.5112,
      "valuation_percentile": 97.96,
      "total_shares": 168088361,
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
          "name": "集成电路封测",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "股权激励指数",
        "QFII重仓指数",
        "半导体精选指数",
        "浦东新区指数",
        "可转债预案指数"
      ],
      "score_company": 8.2,
      "score_trend": 9.7,
      "score_value": 3.3,
      "highlights": [
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 36% ，最新季度归母净利润同比增长 173% ，成长能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 18% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.4% ，较受外资机构青睐；公募基金持股 11% ，很受内资机构青睐。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 半导体 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 96% 的股票，收盘价接近 历史新高 ，走势很强。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月01日大跌 -4.52% ，且成交额为近20日均值的 1.86倍 ，抛压很重。"
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
          "content": "08:22 7月7日市场行情显示，上个交易日三大指数集体收跌，其中创业板指表现偏弱，科创50指数呈现探底回升走势。全市场超过3500只个股出现下跌。沪深两市成交额为3.09万亿元，较上周五缩量913亿元。\n\n半导体领域，华为半导体负责人何庭波于7月3日发布“韬定律”V2版本，带动先进封装及EDA概念逆势活跃。概伦电子、华大九天触及20cm涨停，封测板块中伟测科技、甬矽电子、长电科技、通富微电等均有反弹表现。\n\n算力方向，华为中国发布信息称，昇腾将在2026世界人工智能大会展示Atlas 950 SuperPoD和Atlas 850E风冷超节点等产品。受此影响，交换机概念股活跃，星网锐捷录得5天4板，菲菱科思、紫光股份、共进股份跟涨。华为算力相关的铜连接、液冷方向亦有轮动，航天电器、华丰科技创出历史新高。\n\n医药板块方面，国家药监局综合司就《关于优化细胞与基因治疗药品审评审批有关事项的公告(征求意见稿)》公开征求意见。创新药概念早盘冲高，首药控股、甘李药业触及涨停。恒生创新药指数日内震荡回落，海思科、科伦药业、泽璟制药、荣昌生物等机构重仓品种在创出历史新高后出现回调。\n\n进入7月，上市公司分红实施进入高峰期，目前已有2909家公司分配方案实施。高股息红利股表现回暖，受高温用电需求带动动力煤价格上涨影响，煤炭板块反弹，昊华能源封涨停，新集能源、陕西煤业、中煤能源、兖矿能源涨幅均超过5%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "10:49 7月2日，先进封装概念股盘中表现活跃。气派科技触及20cm涨停，甬矽电子涨幅超过10%。此外，唯特偶、银河微电、三佳科技、伟测科技以及颀中科技等个股同步跟涨。\n\n行业消息方面，据MoneyDJ报道，全球外包半导体封装测试（OSAT）供应商日月光近期调整了封装报价，部分涨幅超过20%。此次价格调整涉及晶圆基板芯片封装（CoWoS）及扇出型基板芯片封装（FoCoS）等多种先进封装技术，且已波及部分美国客户。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "11:20股价达到<span style=\"color:#FB475D\"> 182.66 </span>元，创历史新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "伟测科技：独立董事提名人声明与承诺（金敬长）",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1082569285.28,
      "revenue_yoy": 0.462155,
      "operating_profit": 210352359.79,
      "operating_profit_yoy": 2.7675,
      "net_profit": 202431849.12,
      "net_profit_yoy": 2.264092,
      "gross_profit": 418685332.83,
      "gross_profit_yoy": 0.644781,
      "cogs": 663883952.45,
      "gross_margin": 38.68,
      "pe_forward": null,
      "valuation_history_days": 410,
      "valuation_history_from": "20241028",
      "current_price": 183.25,
      "price": 183.25,
      "ma5": 178.01,
      "ma10": 170.73,
      "ma20": 162.18,
      "dist_ma5_pct": 2.9,
      "dist_ma10_pct": 7.3,
      "dist_ma20_pct": 13.0,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "002185.SZ",
      "fetch_time": "2026-07-09T11:35:55+0800",
      "name": "华天科技",
      "pe": 96.6656,
      "pb": 4.3211,
      "ps_ttm": 4.2756,
      "pcf_ttm": 23.9216,
      "valuation_percentile": 86.07,
      "total_shares": 3323423616,
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
          "name": "集成电路封测",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "消费电子产业指数",
        "华为平台指数",
        "5G指数",
        "半导体产业指数",
        "芯片指数",
        "半导体精选指数",
        "RCEP指数",
        "AI手机指数",
        "西部大开发指数",
        "智能家居指数",
        "集成电路指数",
        "国家大基金指数",
        "GPU指数",
        "元宇宙主题指数",
        "存储器指数",
        "长江存储指数"
      ],
      "score_company": 7.5,
      "score_trend": 9.7,
      "score_value": 3.8,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 568% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 7.2% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 半导体 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 97% 的股票，走势很强。"
        }
      ],
      "risks": [
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 5.5% ，扣非净利润占净利润 36% ，收益质量很低。"
        },
        {
          "tag": "波动",
          "text": "近3天，日均换手率 16% ，短线资金追逐，波动风险较高。"
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
          "content": "14:19 7月8日，市场主力资金流向显示，计算机、IT服务及通信等板块呈现净流入态势。与此同时，电子、电新行业及有色金属等板块出现主力资金净流出，其中电子板块净流出金额为117.21亿元。\n\n在个股资金流向方面，紫光股份获主力净买入20.50亿元，浪潮信息、网宿科技、工业富联的主力资金净流入额也处于前列。另一方面，长电科技遭主力净卖出22.49亿元，北京君正、华天科技、佰维存储的主力资金净流出额同样居前。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "11:01 7月8日，市场主力资金流向显示，计算机、IT服务及通信板块呈现净流入态势。与此同时，电子、半导体及电力新能源行业出现资金净流出，其中电子板块净流出规模超过171亿元。\n\n个股方面，中际旭创股价上涨，主力资金净买入额超过15.19亿元。紫光股份、网宿科技、浪潮信息同样获得主力资金净流入。此外，长电科技遭遇主力资金净卖出超过21亿元，兆易创新、华天科技、佰维存储的资金净流出额在市场中较为突出。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "预计2026/08/22发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-22"
        },
        {
          "content": "09:40股价达到<span style=\"color:#FB475D\"> 21.95 </span>元，创历史新高",
          "tags": [
            "股价新高"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 12379789531.54,
      "revenue_yoy": 0.175532,
      "operating_profit": 632563747.99,
      "operating_profit_yoy": 0.548902,
      "net_profit": 569338337.15,
      "net_profit_yoy": 0.530698,
      "gross_profit": 1527320657.84,
      "gross_profit_yoy": 0.18028,
      "cogs": 10852468873.7,
      "gross_margin": 12.34,
      "pe_forward": null,
      "valuation_history_days": 300,
      "valuation_history_from": "20210709",
      "current_price": 22.15,
      "price": 22.15,
      "ma5": 21.11,
      "ma10": 21.33,
      "ma20": 19.64,
      "dist_ma5_pct": 4.9,
      "dist_ma10_pct": 3.9,
      "dist_ma20_pct": 12.8,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "002947.SZ",
      "fetch_time": "2026-07-09T11:35:57+0800",
      "name": "恒铭达",
      "pe": 31.1974,
      "pb": 5.7686,
      "ps_ttm": 6.1384,
      "pcf_ttm": 30.0957,
      "valuation_percentile": 69.72,
      "total_shares": 256209336,
      "industries": [
        {
          "name": "电子",
          "level": 1
        },
        {
          "name": "消费电子",
          "level": 2
        },
        {
          "name": "消费电子零部件及组装",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "贷款回购指数",
        "AI手机指数",
        "电子制造精选指数",
        "折叠屏指数"
      ],
      "score_company": 8.2,
      "score_trend": 7.2,
      "score_value": 4.5,
      "highlights": [
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 23% ，最新季度归母净利润同比增长 40% ，成长能力很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 13% ，投入资本回报率为 13% ，盈利能力很强。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 25% ，未来成长较快。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 3.0% ，较受外资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 91% 的股票，走势较强。"
        },
        {
          "tag": "激励",
          "text": "2026年04月08日，公司发布股票激励计划，当日收涨 9.0% 。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/24发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-24"
        },
        {
          "content": "在过去的250个交易日内，该股票的价格涨幅高于市场上<span style=\"color:#FB475D\"> 91% </span>的股票",
          "tags": [
            "股价走强"
          ]
        },
        {
          "content": "在过去的10个交易日内，该股票的价格涨幅仅高于市场上<span style=\"color:#00B985\"> 8.8% </span>的股票",
          "tags": [
            "股价走弱"
          ]
        },
        {
          "content": "恒铭达：北京市中伦律师事务所关于苏州恒铭达电子科技股份有限公司2026年第三次临时股东会的法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "回购总金额不超过333万元，回购最高价不超过7.56元/股 （预案）",
          "tags": [
            "公司回购限售股"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1962558240.53,
      "revenue_yoy": 0.155078,
      "operating_profit": 467679799.29,
      "operating_profit_yoy": 0.323632,
      "net_profit": 409317335.28,
      "net_profit_yoy": 0.312002,
      "gross_profit": 655297253.95,
      "gross_profit_yoy": 0.176328,
      "cogs": 1307260986.58,
      "gross_margin": 33.39,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210709",
      "current_price": 73.69,
      "price": 73.69,
      "ma5": 73.48,
      "ma10": 76.82,
      "ma20": 82.25,
      "dist_ma5_pct": 0.3,
      "dist_ma10_pct": -4.1,
      "dist_ma20_pct": -10.4,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "300870.SZ",
      "fetch_time": "2026-07-09T11:35:57+0800",
      "name": "欧陆通",
      "pe": 222.3971,
      "pb": 15.7079,
      "ps_ttm": 8.7647,
      "pcf_ttm": 171.0095,
      "valuation_percentile": 96.78,
      "total_shares": 152643542,
      "industries": [
        {
          "name": "电力设备",
          "level": 1
        },
        {
          "name": "其他电源设备Ⅱ",
          "level": 2
        },
        {
          "name": "其他电源设备Ⅲ",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "人工智能+指数",
        "QFII重仓指数",
        "可转债正股指数",
        "IDC(算力租赁)指数",
        "IPO现场检查指数"
      ],
      "score_company": 7.6,
      "score_trend": 7.6,
      "score_value": 3.4,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年04月27日，业绩超预期引发股价大幅上涨，当日收涨 12.7% 。"
        },
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 21% ，收入成长性较强。"
        },
        {
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 6.0% ，很受外资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月23日大跌 -6.18% ，且成交额为近20日均值的 1.66倍 ，抛压很重。"
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
          "content": "在过去的10个交易日内，该股票的价格涨幅仅高于市场上<span style=\"color:#00B985\"> 1.8% </span>的股票",
          "tags": [
            "股价走弱"
          ]
        },
        {
          "content": "19:54 6月以来共19只算力产业链个股获机构调研 其中多数获杠杆资金青睐，据证券时报·数据宝统计，A股中布局算力硬件、模型、平台产业链的个股超过百家，6月以来共有19只算力产业链个股获机构调研，其中12股机构调研家数在10家及以上，通富微电、欧陆通、胜宏科技居前，分别达到84家、50家、44家。机构调研股多数获杠杆资金青睐，统计显示，上述机构调研的19股中12股6月以来获融资净买入，新易盛、佰维存储、东山精密获净买入金额居前，分别为67.96亿元、26.16亿元、17.27亿元。（证券时报）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "17:02 欧陆通发布公告称，公司计划使用自有资金304.97万元，收购王越天所持有的杭州云电科技能源有限公司20%股权。\n\n本次交易完成后，杭州云电科技能源有限公司将由控股子公司变更为欧陆通的全资子公司。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "欧陆通：关于控股股东部分股份质押的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 3387090909.85,
      "revenue_yoy": 0.271581,
      "operating_profit": 252461696.58,
      "operating_profit_yoy": 0.403312,
      "net_profit": 222727356.87,
      "net_profit_yoy": 0.418534,
      "gross_profit": 693489267.13,
      "gross_profit_yoy": 0.22361,
      "cogs": 2693601642.72,
      "gross_margin": 20.47,
      "pe_forward": null,
      "valuation_history_days": 311,
      "valuation_history_from": "20220825",
      "current_price": 280.88,
      "price": 280.88,
      "ma5": 297.77,
      "ma10": 320.35,
      "ma20": 307.61,
      "dist_ma5_pct": -5.7,
      "dist_ma10_pct": -12.3,
      "dist_ma20_pct": -8.7,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "688469.SH",
      "fetch_time": "2026-07-09T11:35:57+0800",
      "name": "芯联集成-U",
      "pe": -155.9519,
      "pb": 6.1921,
      "ps_ttm": 9.5507,
      "pcf_ttm": 37.3324,
      "valuation_percentile": 98.85,
      "total_shares": 8382687172,
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
        "TMT指数",
        "科技龙头指数",
        "三新指数",
        "双循环指数",
        "双创100指数",
        "消费电子产业指数",
        "先进制造指数",
        "半导体产业指数",
        "信创产业指数",
        "数字经济指数",
        "芯片指数",
        "集成电路指数",
        "业绩预亏指数",
        "中芯国际产业链指数",
        "晶圆产业指数",
        "第三代半导体指数"
      ],
      "score_company": 6.2,
      "score_trend": 8.8,
      "score_value": 3.1,
      "highlights": [
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 22% ，收入成长性很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 5.7% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.7% ，较受外资机构青睐；公募基金持股 8.0% ，很受内资机构青睐。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 半导体 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 92% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 -15% ，投入资本回报率为 -7.8% ，盈利能力很弱。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比为 -148% ，净利润现金含量较低。"
        }
      ],
      "events": [
        {
          "content": "2026/09/07解禁2076.75万股，占总股本0.25%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-07"
        },
        {
          "content": "预计2026/08/11发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-11"
        },
        {
          "content": "2026/07/02解禁3631.39万股，占总股本0.43%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-07-02"
        },
        {
          "content": "07:21 7月起，全球半导体行业迎来新一轮价格调整。记者获悉，近日，芯联集成、斯达半导、扬杰科技、聚辰股份等多家半导体公司向客户发出了涨价函，价格上调幅度为15%至25%。据记者不完全统计，超过20家国内外半导体公司在上半年发布了第一轮涨价函。目前，相关公司均宣布了新一轮涨价通知。细看各家公司的涨价通知函，成本上涨、AI需求爆发是调价的核心诱因。（上海证券报）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "截至2026/06/30，绍兴日芯锐企业管理合伙企业(有限合伙)(与一致行动人合计持股5%以上)减持已完成，实际减持累计 <span style=\"color:#00B985\">1319万股 </span>，成交均价为 <span style=\"color:#00B985\">9元/股 </span>，套现 <span style=\"color:#00B985\">1.23亿元 </span>，此次减持后持股数为2.03亿股 （该主体计划减持不超过1319万股，占总股本的0.16%，占其持有公司股份的6.11%，变动价格说明：价格按减持实施时的市场价格及相关规定确定 )",
          "tags": [
            "非控股股东减持"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 5421954397.61,
      "revenue_yoy": 0.192315,
      "operating_profit": -1577423042.18,
      "operating_profit_yoy": 0.043676,
      "net_profit": -1576488174.69,
      "net_profit_yoy": 0.043507,
      "gross_profit": 215364071.96,
      "gross_profit_yoy": 11.978922,
      "cogs": 5206590325.65,
      "gross_margin": 3.97,
      "pe_forward": null,
      "valuation_history_days": 283,
      "valuation_history_from": "20250512",
      "current_price": 9.37,
      "price": 9.37,
      "ma5": 10.06,
      "ma10": 9.55,
      "ma20": 8.64,
      "dist_ma5_pct": -6.8,
      "dist_ma10_pct": -1.9,
      "dist_ma20_pct": 8.5,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "002821.SZ",
      "fetch_time": "2026-07-09T11:35:57+0800",
      "name": "凯莱英",
      "pe": 51.0185,
      "pb": 3.2403,
      "ps_ttm": 8.1729,
      "pcf_ttm": 38.1471,
      "valuation_percentile": 38.98,
      "total_shares": 360780970,
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
        "双循环指数",
        "专精特新小巨人主题指数",
        "自主可控指数",
        "专精特新小巨人指数",
        "RCEP指数",
        "大消费指数",
        "银发经济指数",
        "外资企业指数",
        "宁组合",
        "高瓴资本指数",
        "合资企业指数",
        "创新药指数",
        "反内卷指数",
        "医药数智化指数",
        "医疗物资出口指数"
      ],
      "score_company": 9.1,
      "score_trend": 8.6,
      "score_value": 6.1,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 医疗研发外包 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年04月28日，业绩超预期引发股价跳空高开，但目前股价缺口已回补。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 113% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 10% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 4.0亿元 ，较上期增长 58% ，占2025年营收 5.9% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 11家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.0% ，较受外资机构青睐；公募基金持股 14% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近6月，股价涨幅超过A股市场 92% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月30日大跌 -3.43% ，且成交额为近20日均值的 3.42倍 ，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "2026/09/04解禁99.96万股，占总股本0.28%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-04"
        },
        {
          "content": "预计2026/08/25发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-25"
        },
        {
          "content": "09:54 7月9日，创新药板块在盘中出现震荡回升走势。其中，成都先导股价涨幅超过10%，凯莱英、益方生物、石药创新、科伦药业以及昭衍新药等个股同步跟涨。\n\n近期医药行业迎来多项政策利好。原料药优先审评通告的发布有效缩短了申报周期；2026年医保与商保目录初审通过率达到92%，且创新药预申报机制进一步缩短了商业化进程；此外，第十二批国家集采明确对创新药予以豁免。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "公司发布股权激励计划预案，股价盘中上涨<span style=\"color:#FB475DC\"> 8.29% </span>",
          "tags": [
            "股价上涨"
          ]
        },
        {
          "content": "2026/07/09发布预案公告，本计划拟向激励对象授予339万股 ，约占总股本的 0.94%，授予价格为 76.7元/股 。",
          "tags": [
            "激励计划"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 4629877130.98,
      "revenue_yoy": 0.11825,
      "operating_profit": 914440800.53,
      "operating_profit_yoy": 0.200897,
      "net_profit": 792478500.98,
      "net_profit_yoy": 0.131822,
      "gross_profit": 1964893526.41,
      "gross_profit_yoy": 0.088369,
      "cogs": 2664983604.57,
      "gross_margin": 42.44,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210709",
      "current_price": 153.41,
      "price": 153.41,
      "ma5": 158.21,
      "ma10": 155.89,
      "ma20": 135.46,
      "dist_ma5_pct": -3.0,
      "dist_ma10_pct": -1.6,
      "dist_ma20_pct": 13.2,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    },
    {
      "code": "002273.SZ",
      "fetch_time": "2026-07-09T11:35:57+0800",
      "name": "水晶光电",
      "pe": 36.1061,
      "pb": 4.3619,
      "ps_ttm": 6.0367,
      "pcf_ttm": 27.8258,
      "valuation_percentile": 74.95,
      "total_shares": 1390632221,
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
          "name": "光学元件",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "5G应用指数",
        "消费电子产业指数",
        "华为平台指数",
        "员工持股指数",
        "元宇宙指数",
        "AI手机指数",
        "苹果指数",
        "谷歌指数",
        "元宇宙主题指数",
        "虚拟现实指数",
        "智能驾驶指数",
        "参股宁德时代指数",
        "智能手表指数",
        "小米产业链指数",
        "AI穿戴设备指数",
        "车联网指数",
        "三星指数"
      ],
      "score_company": 8.8,
      "score_trend": 7.3,
      "score_value": 4.0,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 光学元件 行业龙头企业。"
        },
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 19% ，收入成长性较强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 155% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 13% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "预测",
          "text": " 14家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 8.7% ，很受外资机构青睐；公募基金持股 10% ，很受内资机构青睐。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 光学光电子 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月03日大跌 -5.23% ，且成交额为近20日均值的 2.23倍 ，抛压很重。"
        },
        {
          "tag": "质押",
          "text": "大股东质押数占持股数 77% ，若股价下跌，被动减持风险很高。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/24发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-24"
        },
        {
          "content": "17:36 水晶光电发布公告称，公司股票在连续三个交易日内收盘价涨幅偏离值累计超过20%，触发异常波动标准。针对市场关注的AI光学板块，公司表示该业务主要涵盖光存储与光连接领域。其中，光存储业务目前处于量产前的验证阶段，2025年度内尚未产生销售收入，受限于产品工艺验证周期，业务规模的提升仍需时日。\n\n在光连接业务方面，公司已形成滤片、棱镜、硅透镜、玻璃基板及波导的“3+2”产品矩阵。目前，滤片与硅透镜产品正处于客户送样阶段，而玻璃基板与波导等前沿产品尚处于早期技术对接期，尚未形成业绩贡献。\n\n公司强调，近两年业绩增长的主要驱动力依然源自北美大客户的消费电子业务。AI光学作为重点布局的创新方向，由于项目落地与业绩兑现周期较长，短期内难以成为公司整体业绩的主要增长来源。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "17:34 水晶光电公告，近期市场对公司AI光学业务关注度较高。公司AI光学板块主要涉及光存储和光连接业务。光存储业务现阶段正处于量产前验证环节，2025年度至今暂未实现销售收入。受产品工艺验证周期较长影响，业务规模显著提升尚需时间；光连接业务核心聚焦“滤片、棱镜、硅透镜”+“玻璃基板、波导”五大品类，构建“3+2”产品矩阵。其中滤片类、硅透镜类产品目前处于客户送样环节，玻璃基板、波导等前沿产品尚处在早期技术对接阶段，相关产品尚未贡献业绩。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "预计2026/08/24发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-24"
        },
        {
          "content": "在过去的60个交易日内，该股票的价格涨幅高于市场上<span style=\"color:#FB475D\"> 90% </span>的股票",
          "tags": [
            "股价走强"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 5123182541.62,
      "revenue_yoy": 0.087788,
      "operating_profit": 1125484643.74,
      "operating_profit_yoy": 0.144055,
      "net_profit": 988011243.63,
      "net_profit_yoy": 0.123844,
      "gross_profit": 1626162828.53,
      "gross_profit_yoy": 0.093531,
      "cogs": 3497019713.09,
      "gross_margin": 31.74,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210709",
      "current_price": 31.11,
      "price": 31.11,
      "ma5": 34.76,
      "ma10": 35.77,
      "ma20": 35.46,
      "dist_ma5_pct": -10.5,
      "dist_ma10_pct": -13.0,
      "dist_ma20_pct": -12.3,
      "iv_proxy": {
        "basis": "fallback:overall_market",
        "primary_underlying": null,
        "primary_name": "overall_market",
        "iv_rank": null,
        "iv_percentile": null,
        "interpretation": "无数据",
        "sizing": "unknown",
        "guidance": "Overall market IV proxy unavailable; fall back to overall market IV.",
        "alternates": []
      }
    }
  ],
  "active_positions": [],
  "position_prices": {},
  "missed_opportunity_prices": [
    {
      "code": "688536",
      "name": "思瑞浦",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 313.01,
      "return_pct": null
    },
    {
      "code": "688378",
      "name": "奥来德",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 50.24,
      "return_pct": null
    },
    {
      "code": "603203",
      "name": "快克智能",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 63.57,
      "return_pct": null
    },
    {
      "code": "300373",
      "name": "扬杰科技",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 126.72,
      "return_pct": null
    },
    {
      "code": "300302",
      "name": "同有科技",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 40.13,
      "return_pct": null
    },
    {
      "code": "688401",
      "name": "路维光电",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 90.52,
      "return_pct": null
    },
    {
      "code": "002192",
      "name": "融捷股份",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 79.06,
      "return_pct": null
    },
    {
      "code": "002290",
      "name": "禾盛新材",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 78.72,
      "return_pct": null
    },
    {
      "code": "688652",
      "name": "京仪装备",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 216.02,
      "return_pct": null
    },
    {
      "code": "688231",
      "name": "隆达股份",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 36.55,
      "return_pct": null
    },
    {
      "code": "301536",
      "name": "星宸科技",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 114.63,
      "return_pct": null
    },
    {
      "code": "002185",
      "name": "华天科技",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 23.73,
      "return_pct": null
    },
    {
      "code": "688372",
      "name": "伟测科技",
      "recommended_date": "2026-07-08",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 183.44,
      "return_pct": null
    },
    {
      "code": "002407",
      "name": "多氟多",
      "recommended_date": "2026-07-07",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 40.98,
      "return_pct": null
    },
    {
      "code": "300037",
      "name": "新宙邦",
      "recommended_date": "2026-07-06",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 76.16,
      "return_pct": null
    },
    {
      "code": "002273",
      "name": "水晶光电",
      "recommended_date": "2026-07-06",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 31.11,
      "return_pct": null
    },
    {
      "code": "300323",
      "name": "华灿光电",
      "recommended_date": "2026-07-03",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 15.66,
      "return_pct": null
    },
    {
      "code": "300346",
      "name": "南大光电",
      "recommended_date": "2026-07-03",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 75.66,
      "return_pct": null
    },
    {
      "code": "301018",
      "name": "申菱环境",
      "recommended_date": "2026-07-03",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 113.72,
      "return_pct": null
    }
  ],
  "iv_sentiment": {
    "date": "2026-07-09",
    "source": "options-learn backend (/api/history/iv-rank)",
    "core_underlyings": [
      "510050",
      "510300",
      "510500",
      "588000",
      "159915"
    ],
    "etf_iv_data": [],
    "overall_sentiment": {
      "signal": "无数据",
      "detail": "无法获取IV数据",
      "based_on": []
    }
  },
  "entry_regime": {
    "allow_new_positions": false,
    "regime": "panic",
    "breadth_ratio": 0.1824,
    "up": 842,
    "down": 4616,
    "positive_indices": [
      "创业板指"
    ],
    "negative_indices": [
      "上证指数",
      "深证成指"
    ],
    "limit_ups": 36,
    "limit_downs": 21,
    "sizing_multiplier": 0.0,
    "hard_block": true,
    "reason": "Entry regime panic: breadth 0.18:1, 1/3 major indices green, 36 limit-ups / 21 limit-downs. Block new longs."
  },
  "rule_violations": {
    "status": "ok",
    "total_rules": 6,
    "total_violations": 0,
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
        "status": "ok",
        "exit_code": 0,
        "violations": [],
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
  "active_learnings": "## Active Rules (proven, hitRate ≥ 75%)\n- [h013] Strong breadth alone is not enough to force entries; without candidate RPS and MA-distance data, the correct momentum decision is to keep cash. (hitRate: 99%, n=119, confidence: 98%)\n- [h028] Today’s relative leaders are concentrated in communication equipment and adjacent tech hardware, while cyclicals/agri/resource laggards are being de-risked aggressively. (hitRate: 100%, n=38, confidence: 98%)\n- [h023] Raising stops mechanically after +10% works well in weak tapes because it converts a fast winner into a low-risk hold without needing a fresh market call. (hitRate: 100%, n=36, confidence: 97%)\n- [h019] Bottom-list sectors should be treated as hard no-buy zones even when individual names still carry acceptable RPS readings. (hitRate: 100%, n=32, confidence: 97%)\n- [h027] MA-distance discipline remains critical inside hot sectors: a hot sector does not override chase risk when dist_ma5_pct exceeds 6% or dist_ma10_pct exceeds 8%. (hitRate: 100%, n=31, confidence: 97%)\n- [h021] The MA-distance anti-chase rule is doing real work: several visually strong names fail because they are too far above short-term support. (hitRate: 98%, n=89, confidence: 97%)\n- [h017] Low-IV conditions around 16-22% IV rank do not justify freezing risk when breadth is 5.6:1; they argue for normal sizing but tighter discipline on chasing. (hitRate: 100%, n=23, confidence: 96%)\n",
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
