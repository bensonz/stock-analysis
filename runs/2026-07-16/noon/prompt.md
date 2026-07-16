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
  "date": "2026-07-16",
  "portfolio": {
    "startingCapital": 1000000,
    "totalEquity": 956221.0,
    "cash": 956221.0,
    "investedValue": 0.0,
    "unrealizedPnl": 0.0,
    "realizedPnl": -43779.0,
    "totalPnl": -43779.0,
    "totalReturnPct": -4.38,
    "positionsUsed": 0,
    "positionsMax": 10,
    "cashPct": 100.0,
    "dayPnl": 0.0,
    "minCashPct": 0,
    "minCashValue": 0.0,
    "deployableCash": 956221.0
  },
  "market": {
    "timestamp": "2026-07-16T11:40:49.705812",
    "indices": {
      "上证指数": {
        "code": "sh000001",
        "close": 3923.203,
        "change_pct": -0.82,
        "date": "2026-07-16"
      },
      "深证成指": {
        "code": "sz399001",
        "close": 14657.07,
        "change_pct": -0.83,
        "date": "2026-07-16"
      },
      "创业板指": {
        "code": "sz399006",
        "close": 3738.96,
        "change_pct": -1.73,
        "date": "2026-07-16"
      },
      "科创50": {
        "code": "sh000688",
        "close": 1905.869,
        "change_pct": -0.96,
        "date": "2026-07-16"
      }
    },
    "breadth": {
      "up": 3282,
      "down": 2119,
      "flat": 125,
      "total": 5526,
      "distribution": {
        "f10": 7,
        "f7_10": 40,
        "f4_7": 212,
        "f2_4": 562,
        "f0_2": 1298,
        "f0": 125,
        "r0_2": 2092,
        "r2_4": 892,
        "r4_7": 191,
        "r7_10": 57,
        "r10": 50
      }
    },
    "sectors": {
      "top5": [
        {
          "板块名称": "专业连锁Ⅱ",
          "涨跌幅": 4.99
        },
        {
          "板块名称": "影视院线",
          "涨跌幅": 4.5
        },
        {
          "板块名称": "广告营销",
          "涨跌幅": 3.08
        },
        {
          "板块名称": "饲料",
          "涨跌幅": 2.98
        },
        {
          "板块名称": "养殖业",
          "涨跌幅": 2.93
        }
      ],
      "bottom5": [
        {
          "板块名称": "玻璃玻纤",
          "涨跌幅": -5.28
        },
        {
          "板块名称": "电子化学品Ⅱ",
          "涨跌幅": -3.48
        },
        {
          "板块名称": "通信设备",
          "涨跌幅": -3.32
        },
        {
          "板块名称": "其他电源设备Ⅱ",
          "涨跌幅": -2.94
        },
        {
          "板块名称": "其他电子Ⅱ",
          "涨跌幅": -2.66
        }
      ]
    }
  },
  "strategy_pool": {
    "source": "cheesefortune_intersection",
    "total_stocks": 62,
    "stocks": [
      {
        "code": "002980",
        "code_full": "002980.SZ",
        "name": "华盛昌",
        "source_date": "2026/04/30",
        "highlights_count": 5,
        "market_cap": 193.4543,
        "pe": 6.2,
        "risks_count": 2,
        "rps20": 94.45,
        "rps60": 99.9,
        "rps120": 99.61,
        "rps250": 97.37,
        "ma10": 103.82,
        "vcp_quality": null,
        "ma5": 95.78,
        "ma20": 111.65,
        "dist_ma5_pct": -8.9,
        "dist_ma10_pct": -16.0,
        "dist_ma20_pct": -21.9
      },
      {
        "code": "605376",
        "code_full": "605376.SH",
        "name": "博迁新材",
        "source_date": "2026/07/11",
        "highlights_count": 5,
        "market_cap": 482.5735,
        "pe": 5.6,
        "risks_count": 2,
        "rps20": 98.82,
        "rps60": 98.98,
        "rps120": 99.51,
        "rps250": 99.25,
        "ma10": 242.69,
        "vcp_quality": null,
        "ma5": 224.88,
        "ma20": 216.46,
        "dist_ma5_pct": -17.0,
        "dist_ma10_pct": -23.1,
        "dist_ma20_pct": -13.8
      },
      {
        "code": "301396",
        "code_full": "301396.SZ",
        "name": "宏景科技",
        "source_date": "2026/05/13",
        "highlights_count": 4,
        "market_cap": 496.3898,
        "pe": 3.6,
        "risks_count": 2,
        "rps20": 81.32,
        "rps60": 99.14,
        "rps120": 99.43,
        "rps250": 96.6,
        "ma10": 281.29,
        "vcp_quality": null,
        "ma5": 255.3,
        "ma20": 246.91,
        "dist_ma5_pct": -13.9,
        "dist_ma10_pct": -21.8,
        "dist_ma20_pct": -11.0
      },
      {
        "code": "688257",
        "code_full": "688257.SH",
        "name": "新锐股份",
        "source_date": "2026/07/14",
        "highlights_count": 4,
        "market_cap": 284.4238,
        "pe": 4.7,
        "risks_count": 1,
        "rps20": 91.98,
        "rps60": 95.88,
        "rps120": 99.33,
        "rps250": 97.72,
        "ma10": 100.49,
        "vcp_quality": null,
        "ma5": 98.38,
        "ma20": 99.1,
        "dist_ma5_pct": -20.2,
        "dist_ma10_pct": -21.9,
        "dist_ma20_pct": -20.8
      },
      {
        "code": "301362",
        "code_full": "301362.SZ",
        "name": "民爆光电",
        "source_date": "2026/06/16",
        "highlights_count": 4,
        "market_cap": 211.0506,
        "pe": 2.9,
        "risks_count": 1,
        "rps20": 84.16,
        "rps60": 99.55,
        "rps120": 99.29,
        "rps250": 97.68,
        "ma10": 159.12,
        "vcp_quality": null,
        "ma5": 145.58,
        "ma20": 181.48,
        "dist_ma5_pct": -0.1,
        "dist_ma10_pct": -8.6,
        "dist_ma20_pct": -19.9
      },
      {
        "code": "300285",
        "code_full": "300285.SZ",
        "name": "国瓷材料",
        "source_date": "2026/07/08",
        "highlights_count": 7,
        "market_cap": 676.8961,
        "pe": 14.5,
        "risks_count": 2,
        "rps20": 99.84,
        "rps60": 99.04,
        "rps120": 99.25,
        "rps250": 98.44,
        "ma10": 86.48,
        "vcp_quality": null,
        "ma5": 76.15,
        "ma20": 81.18,
        "dist_ma5_pct": -13.2,
        "dist_ma10_pct": -23.6,
        "dist_ma20_pct": -18.6
      },
      {
        "code": "688630",
        "code_full": "688630.SH",
        "name": "芯碁微装",
        "source_date": "2026/03/12",
        "highlights_count": 6,
        "market_cap": 631.1001,
        "pe": 5.2,
        "risks_count": 0,
        "rps20": 98.99,
        "rps60": 98.83,
        "rps120": 99.17,
        "rps250": 99.11,
        "ma10": 501.08,
        "vcp_quality": null,
        "ma5": 482.54,
        "ma20": 453.21,
        "dist_ma5_pct": -4.7,
        "dist_ma10_pct": -8.3,
        "dist_ma20_pct": 1.4
      },
      {
        "code": "600869",
        "code_full": "600869.SH",
        "name": "远东股份",
        "source_date": "2026/06/29",
        "highlights_count": 5,
        "market_cap": 453.4138,
        "pe": 31.4,
        "risks_count": 5,
        "rps20": 97.71,
        "rps60": 98.48,
        "rps120": 99.0,
        "rps250": 99.07,
        "ma10": 26.24,
        "vcp_quality": null,
        "ma5": 21.84,
        "ma20": 30.36,
        "dist_ma5_pct": -9.6,
        "dist_ma10_pct": -24.8,
        "dist_ma20_pct": -35.0
      },
      {
        "code": "688668",
        "code_full": "688668.SH",
        "name": "鼎通科技",
        "source_date": "2026/04/08",
        "highlights_count": 5,
        "market_cap": 457.2254,
        "pe": 5.5,
        "risks_count": 1,
        "rps20": 97.63,
        "rps60": 97.91,
        "rps120": 98.92,
        "rps250": 99.51,
        "ma10": 355.8,
        "vcp_quality": null,
        "ma5": 333.88,
        "ma20": 370.15,
        "dist_ma5_pct": -1.5,
        "dist_ma10_pct": -7.5,
        "dist_ma20_pct": -11.1
      },
      {
        "code": "300806",
        "code_full": "300806.SZ",
        "name": "斯迪克",
        "source_date": "2026/04/28",
        "highlights_count": 5,
        "market_cap": 348.4068,
        "pe": 6.6,
        "risks_count": 2,
        "rps20": 94.96,
        "rps60": 97.11,
        "rps120": 98.9,
        "rps250": 98.93,
        "ma10": 93.76,
        "vcp_quality": null,
        "ma5": 84.39,
        "ma20": 93.33,
        "dist_ma5_pct": -8.6,
        "dist_ma10_pct": -17.7,
        "dist_ma20_pct": -17.4
      },
      {
        "code": "000811",
        "code_full": "000811.SZ",
        "name": "冰轮环境",
        "source_date": "2026/06/12",
        "highlights_count": 4,
        "market_cap": 499.7127,
        "pe": 28.1,
        "risks_count": 2,
        "rps20": 99.05,
        "rps60": 99.28,
        "rps120": 98.82,
        "rps250": 97.43,
        "ma10": 52.85,
        "vcp_quality": null,
        "ma5": 51.19,
        "ma20": 48.91,
        "dist_ma5_pct": -0.8,
        "dist_ma10_pct": -3.9,
        "dist_ma20_pct": 3.8
      },
      {
        "code": "688300",
        "code_full": "688300.SH",
        "name": "联瑞新材",
        "source_date": "2026/05/06",
        "highlights_count": 6,
        "market_cap": 401.5874,
        "pe": 6.6,
        "risks_count": 1,
        "rps20": 99.49,
        "rps60": 99.43,
        "rps120": 98.78,
        "rps250": 96.69,
        "ma10": 216.31,
        "vcp_quality": null,
        "ma5": 192.87,
        "ma20": 208.34,
        "dist_ma5_pct": -10.4,
        "dist_ma10_pct": -20.1,
        "dist_ma20_pct": -17.0
      },
      {
        "code": "603061",
        "code_full": "603061.SH",
        "name": "金海通",
        "source_date": "2026/07/10",
        "highlights_count": 4,
        "market_cap": 325.2408,
        "pe": 3.3,
        "risks_count": 1,
        "rps20": 96.86,
        "rps60": 93.41,
        "rps120": 98.39,
        "rps250": 98.26,
        "ma10": 463.99,
        "vcp_quality": null,
        "ma5": 444.7,
        "ma20": 396.05,
        "dist_ma5_pct": -11.9,
        "dist_ma10_pct": -15.5,
        "dist_ma20_pct": -1.0
      },
      {
        "code": "300620",
        "code_full": "300620.SZ",
        "name": "光库科技",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 717.0918,
        "pe": 9.3,
        "risks_count": 1,
        "rps20": 95.32,
        "rps60": 97.48,
        "rps120": 98.11,
        "rps250": 99.56,
        "ma10": 324.64,
        "vcp_quality": null,
        "ma5": 297.82,
        "ma20": 331.1,
        "dist_ma5_pct": -8.3,
        "dist_ma10_pct": -15.9,
        "dist_ma20_pct": -17.5
      },
      {
        "code": "688037",
        "code_full": "688037.SH",
        "name": "芯源微",
        "source_date": "2026/07/10",
        "highlights_count": 5,
        "market_cap": 751.7875,
        "pe": 6.5,
        "risks_count": 3,
        "rps20": 97.22,
        "rps60": 95.37,
        "rps120": 97.8,
        "rps250": 96.34,
        "ma10": 377.98,
        "vcp_quality": null,
        "ma5": 381.71,
        "ma20": 316.89,
        "dist_ma5_pct": 1.7,
        "dist_ma10_pct": 2.7,
        "dist_ma20_pct": 22.4
      },
      {
        "code": "003031",
        "code_full": "003031.SZ",
        "name": "中瓷电子",
        "source_date": "2026/07/01",
        "highlights_count": 5,
        "market_cap": 582.3092,
        "pe": 5.5,
        "risks_count": 1,
        "rps20": 93.17,
        "rps60": 97.15,
        "rps120": 97.58,
        "rps250": 95.61,
        "ma10": 153.92,
        "vcp_quality": null,
        "ma5": 141.5,
        "ma20": 157.2,
        "dist_ma5_pct": -7.9,
        "dist_ma10_pct": -15.4,
        "dist_ma20_pct": -17.1
      },
      {
        "code": "300776",
        "code_full": "300776.SZ",
        "name": "帝尔激光",
        "source_date": "2026/06/29",
        "highlights_count": 4,
        "market_cap": 402.4658,
        "pe": 7.1,
        "risks_count": 0,
        "rps20": 97.49,
        "rps60": 97.3,
        "rps120": 97.21,
        "rps250": 94.28,
        "ma10": 176.28,
        "vcp_quality": null,
        "ma5": 158.95,
        "ma20": 169.97,
        "dist_ma5_pct": -6.8,
        "dist_ma10_pct": -15.9,
        "dist_ma20_pct": -12.8
      },
      {
        "code": "688127",
        "code_full": "688127.SH",
        "name": "蓝特光学",
        "source_date": "2026/06/20",
        "highlights_count": 6,
        "market_cap": 294.357,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 85.78,
        "rps60": 96.34,
        "rps120": 97.03,
        "rps250": 96.14,
        "ma10": 87.07,
        "vcp_quality": null,
        "ma5": 81.62,
        "ma20": 85.16,
        "dist_ma5_pct": -5.2,
        "dist_ma10_pct": -11.1,
        "dist_ma20_pct": -9.1
      },
      {
        "code": "301182",
        "code_full": "301182.SZ",
        "name": "凯旺科技",
        "source_date": "2026/04/24",
        "highlights_count": 4,
        "market_cap": 78.8996,
        "pe": 4.5,
        "risks_count": 3,
        "rps20": 94.57,
        "rps60": 98.26,
        "rps120": 96.92,
        "rps250": 93.84,
        "ma10": 96.61,
        "vcp_quality": null,
        "ma5": 88.65,
        "ma20": 93.92,
        "dist_ma5_pct": -11.9,
        "dist_ma10_pct": -19.2,
        "dist_ma20_pct": -16.9
      },
      {
        "code": "688017",
        "code_full": "688017.SH",
        "name": "绿的谐波",
        "source_date": "2026/07/08",
        "highlights_count": 4,
        "market_cap": 707.8009,
        "pe": 5.8,
        "risks_count": 2,
        "rps20": 97.45,
        "rps60": 96.13,
        "rps120": 96.88,
        "rps250": 93.59,
        "ma10": 414.98,
        "vcp_quality": null,
        "ma5": 442.42,
        "ma20": 391.13,
        "dist_ma5_pct": -11.6,
        "dist_ma10_pct": -5.8,
        "dist_ma20_pct": -0.0
      },
      {
        "code": "688150",
        "code_full": "688150.SH",
        "name": "莱特光电",
        "source_date": "2026/04/16",
        "highlights_count": 5,
        "market_cap": 199.8907,
        "pe": 4.3,
        "risks_count": 1,
        "rps20": 86.73,
        "rps60": 97.28,
        "rps120": 96.66,
        "rps250": 93.11,
        "ma10": 61.29,
        "vcp_quality": null,
        "ma5": 59.84,
        "ma20": 56.18,
        "dist_ma5_pct": -12.8,
        "dist_ma10_pct": -14.9,
        "dist_ma20_pct": -7.2
      },
      {
        "code": "688531",
        "code_full": "688531.SH",
        "name": "日联科技",
        "source_date": "2026/06/16",
        "highlights_count": 7,
        "market_cap": 257.4986,
        "pe": 3.2,
        "risks_count": 0,
        "rps20": 95.99,
        "rps60": 97.89,
        "rps120": 96.62,
        "rps250": 92.44,
        "ma10": 173.92,
        "vcp_quality": null,
        "ma5": 178.91,
        "ma20": 176.61,
        "dist_ma5_pct": -5.2,
        "dist_ma10_pct": -2.5,
        "dist_ma20_pct": -4.0
      },
      {
        "code": "300005",
        "code_full": "300005.SZ",
        "name": "探路者",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 166.7546,
        "pe": 16.7,
        "risks_count": 2,
        "rps20": 94.85,
        "rps60": 92.9,
        "rps120": 95.87,
        "rps250": 90.08,
        "ma10": 21.84,
        "vcp_quality": null,
        "ma5": 20.08,
        "ma20": 19.96,
        "dist_ma5_pct": -8.6,
        "dist_ma10_pct": -15.9,
        "dist_ma20_pct": -8.0
      },
      {
        "code": "600345",
        "code_full": "600345.SH",
        "name": "长江通信",
        "source_date": "2026/07/14",
        "highlights_count": 4,
        "market_cap": 186.1979,
        "pe": 25.5,
        "risks_count": 2,
        "rps20": 90.76,
        "rps60": 95.5,
        "rps120": 95.83,
        "rps250": 92.58,
        "ma10": 58.44,
        "vcp_quality": null,
        "ma5": 55.7,
        "ma20": 60.25,
        "dist_ma5_pct": -4.6,
        "dist_ma10_pct": -9.1,
        "dist_ma20_pct": -11.8
      },
      {
        "code": "688629",
        "code_full": "688629.SH",
        "name": "华丰科技",
        "source_date": "2026/07/15",
        "highlights_count": 5,
        "market_cap": 786.6683,
        "pe": 3.0,
        "risks_count": 1,
        "rps20": 94.51,
        "rps60": 95.76,
        "rps120": 95.82,
        "rps250": 95.07,
        "ma10": 183.36,
        "vcp_quality": null,
        "ma5": 200.24,
        "ma20": 161.96,
        "dist_ma5_pct": 3.1,
        "dist_ma10_pct": 12.6,
        "dist_ma20_pct": 27.4
      },
      {
        "code": "002937",
        "code_full": "002937.SZ",
        "name": "兴瑞科技",
        "source_date": "2026/04/23",
        "highlights_count": 5,
        "market_cap": 130.3224,
        "pe": 7.8,
        "risks_count": 0,
        "rps20": 93.11,
        "rps60": 94.94,
        "rps120": 95.7,
        "rps250": 91.98,
        "ma10": 43.06,
        "vcp_quality": null,
        "ma5": 41.82,
        "ma20": 41.08,
        "dist_ma5_pct": -4.8,
        "dist_ma10_pct": -7.5,
        "dist_ma20_pct": -3.1
      },
      {
        "code": "300570",
        "code_full": "300570.SZ",
        "name": "太辰光",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 447.0538,
        "pe": 9.6,
        "risks_count": 1,
        "rps20": 97.73,
        "rps60": 97.2,
        "rps120": 95.66,
        "rps250": 95.15,
        "ma10": 222.69,
        "vcp_quality": null,
        "ma5": 205.68,
        "ma20": 220.31,
        "dist_ma5_pct": -7.8,
        "dist_ma10_pct": -14.9,
        "dist_ma20_pct": -14.0
      },
      {
        "code": "002957",
        "code_full": "002957.SZ",
        "name": "科瑞技术",
        "source_date": "2026/07/15",
        "highlights_count": 4,
        "market_cap": 177.3166,
        "pe": 6.9,
        "risks_count": 2,
        "rps20": 91.0,
        "rps60": 97.4,
        "rps120": 95.6,
        "rps250": 95.21,
        "ma10": 47.68,
        "vcp_quality": null,
        "ma5": 44.4,
        "ma20": 51.42,
        "dist_ma5_pct": -3.8,
        "dist_ma10_pct": -10.4,
        "dist_ma20_pct": -16.9
      },
      {
        "code": "300323",
        "code_full": "300323.SZ",
        "name": "华灿光电",
        "source_date": "2026/04/29",
        "highlights_count": 4,
        "market_cap": 217.6441,
        "pe": 14.1,
        "risks_count": 2,
        "rps20": 94.0,
        "rps60": 97.17,
        "rps120": 95.44,
        "rps250": 93.05,
        "ma10": 17.85,
        "vcp_quality": null,
        "ma5": 15.72,
        "ma20": 17.11,
        "dist_ma5_pct": -12.1,
        "dist_ma10_pct": -22.6,
        "dist_ma20_pct": -19.3
      },
      {
        "code": "605111",
        "code_full": "605111.SH",
        "name": "新洁能",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 269.0524,
        "pe": 5.8,
        "risks_count": 2,
        "rps20": 98.72,
        "rps60": 95.86,
        "rps120": 95.11,
        "rps250": 91.77,
        "ma10": 83.4,
        "vcp_quality": null,
        "ma5": 80.21,
        "ma20": 73.47,
        "dist_ma5_pct": -13.7,
        "dist_ma10_pct": -17.0,
        "dist_ma20_pct": -5.8
      },
      {
        "code": "688167",
        "code_full": "688167.SH",
        "name": "炬光科技",
        "source_date": "2026/07/15",
        "highlights_count": 4,
        "market_cap": 337.7236,
        "pe": 4.5,
        "risks_count": 2,
        "rps20": 39.1,
        "rps60": 90.99,
        "rps120": 95.09,
        "rps250": 97.92,
        "ma10": 324.4,
        "vcp_quality": null,
        "ma5": 296.57,
        "ma20": 366.81,
        "dist_ma5_pct": -9.0,
        "dist_ma10_pct": -16.8,
        "dist_ma20_pct": -26.4
      },
      {
        "code": "002290",
        "code_full": "002290.SZ",
        "name": "禾盛新材",
        "source_date": "2026/06/12",
        "highlights_count": 4,
        "market_cap": 177.8717,
        "pe": 16.8,
        "risks_count": 4,
        "rps20": 81.87,
        "rps60": 90.85,
        "rps120": 94.85,
        "rps250": 95.23,
        "ma10": 85.05,
        "vcp_quality": null,
        "ma5": 81.58,
        "ma20": 83.79,
        "dist_ma5_pct": -9.2,
        "dist_ma10_pct": -12.9,
        "dist_ma20_pct": -11.6
      },
      {
        "code": "688376",
        "code_full": "688376.SH",
        "name": "美埃科技",
        "source_date": "2026/04/28",
        "highlights_count": 5,
        "market_cap": 110.7308,
        "pe": 3.6,
        "risks_count": 1,
        "rps20": 94.98,
        "rps60": 90.58,
        "rps120": 94.72,
        "rps250": 92.18,
        "ma10": 101.73,
        "vcp_quality": null,
        "ma5": 99.46,
        "ma20": 87.27,
        "dist_ma5_pct": -11.1,
        "dist_ma10_pct": -13.1,
        "dist_ma20_pct": 1.3
      },
      {
        "code": "688777",
        "code_full": "688777.SH",
        "name": "中控技术",
        "source_date": "2026/07/13",
        "highlights_count": 4,
        "market_cap": 757.6431,
        "pe": 5.6,
        "risks_count": 2,
        "rps20": 95.26,
        "rps60": 89.48,
        "rps120": 94.68,
        "rps250": 89.23,
        "ma10": 111.85,
        "vcp_quality": null,
        "ma5": 104.67,
        "ma20": 106.92,
        "dist_ma5_pct": -6.7,
        "dist_ma10_pct": -12.7,
        "dist_ma20_pct": -8.6
      },
      {
        "code": "688652",
        "code_full": "688652.SH",
        "name": "京仪装备",
        "source_date": "2026/05/06",
        "highlights_count": 6,
        "market_cap": 297.36,
        "pe": 2.6,
        "risks_count": 0,
        "rps20": 96.5,
        "rps60": 93.24,
        "rps120": 94.56,
        "rps250": 94.4,
        "ma10": 194.95,
        "vcp_quality": null,
        "ma5": 204.59,
        "ma20": 165.89,
        "dist_ma5_pct": -3.1,
        "dist_ma10_pct": 1.7,
        "dist_ma20_pct": 19.5
      },
      {
        "code": "000703",
        "code_full": "000703.SZ",
        "name": "恒逸石化",
        "source_date": "2026/06/08",
        "highlights_count": 5,
        "market_cap": 553.3622,
        "pe": 15.1,
        "risks_count": 3,
        "rps20": 72.99,
        "rps60": 85.89,
        "rps120": 94.52,
        "rps250": 90.18,
        "ma10": 14.27,
        "vcp_quality": null,
        "ma5": 13.96,
        "ma20": 14.12,
        "dist_ma5_pct": 5.3,
        "dist_ma10_pct": 2.9,
        "dist_ma20_pct": 4.0
      },
      {
        "code": "601126",
        "code_full": "601126.SH",
        "name": "四方股份",
        "source_date": "2026/03/12",
        "highlights_count": 7,
        "market_cap": 413.4703,
        "pe": 15.5,
        "risks_count": 1,
        "rps20": 79.3,
        "rps60": 93.57,
        "rps120": 94.46,
        "rps250": 95.86,
        "ma10": 57.9,
        "vcp_quality": null,
        "ma5": 55.06,
        "ma20": 64.43,
        "dist_ma5_pct": -9.6,
        "dist_ma10_pct": -14.0,
        "dist_ma20_pct": -22.8
      },
      {
        "code": "688515",
        "code_full": "688515.SH",
        "name": "裕太微-U",
        "source_date": "2026/07/07",
        "highlights_count": 4,
        "market_cap": 140.752,
        "pe": 3.4,
        "risks_count": 2,
        "rps20": 93.52,
        "rps60": 96.27,
        "rps120": 94.17,
        "rps250": 88.02,
        "ma10": 234.67,
        "vcp_quality": null,
        "ma5": 219.05,
        "ma20": 217.69,
        "dist_ma5_pct": -8.3,
        "dist_ma10_pct": -14.4,
        "dist_ma20_pct": -7.8
      },
      {
        "code": "301536",
        "code_full": "301536.SZ",
        "name": "星宸科技",
        "source_date": "2026/04/20",
        "highlights_count": 6,
        "market_cap": 451.5305,
        "pe": 2.3,
        "risks_count": 0,
        "rps20": 95.52,
        "rps60": 94.51,
        "rps120": 93.99,
        "rps250": 87.33,
        "ma10": 119.2,
        "vcp_quality": null,
        "ma5": 116.18,
        "ma20": 109.97,
        "dist_ma5_pct": -6.7,
        "dist_ma10_pct": -9.1,
        "dist_ma20_pct": -1.4
      },
      {
        "code": "300346",
        "code_full": "300346.SZ",
        "name": "南大光电",
        "source_date": "2026/06/16",
        "highlights_count": 4,
        "market_cap": 460.9325,
        "pe": 13.9,
        "risks_count": 2,
        "rps20": 96.66,
        "rps60": 90.32,
        "rps120": 93.89,
        "rps250": 86.9,
        "ma10": 80.67,
        "vcp_quality": null,
        "ma5": 74.3,
        "ma20": 73.35,
        "dist_ma5_pct": -9.9,
        "dist_ma10_pct": -17.0,
        "dist_ma20_pct": -8.7
      },
      {
        "code": "300236",
        "code_full": "300236.SZ",
        "name": "上海新阳",
        "source_date": "2026/03/12",
        "highlights_count": 4,
        "market_cap": 324.5386,
        "pe": 15.0,
        "risks_count": 1,
        "rps20": 91.79,
        "rps60": 91.42,
        "rps120": 93.85,
        "rps250": 94.22,
        "ma10": 118.23,
        "vcp_quality": null,
        "ma5": 115.64,
        "ma20": 110.19,
        "dist_ma5_pct": -3.3,
        "dist_ma10_pct": -5.4,
        "dist_ma20_pct": 1.5
      },
      {
        "code": "688536",
        "code_full": "688536.SH",
        "name": "思瑞浦",
        "source_date": "2026/04/01",
        "highlights_count": 8,
        "market_cap": 397.8645,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 93.76,
        "rps60": 94.53,
        "rps120": 93.46,
        "rps250": 85.31,
        "ma10": 339.87,
        "vcp_quality": null,
        "ma5": 332.64,
        "ma20": 323.24,
        "dist_ma5_pct": -8.8,
        "dist_ma10_pct": -10.7,
        "dist_ma20_pct": -6.1
      },
      {
        "code": "688378",
        "code_full": "688378.SH",
        "name": "奥来德",
        "source_date": "2026/06/06",
        "highlights_count": 5,
        "market_cap": 130.7387,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 92.3,
        "rps60": 93.1,
        "rps120": 93.42,
        "rps250": 93.75,
        "ma10": 57.02,
        "vcp_quality": null,
        "ma5": 55.45,
        "ma20": 52.57,
        "dist_ma5_pct": -7.9,
        "dist_ma10_pct": -10.4,
        "dist_ma20_pct": -2.8
      },
      {
        "code": "688106",
        "code_full": "688106.SH",
        "name": "金宏气体",
        "source_date": "2026/07/15",
        "highlights_count": 6,
        "market_cap": 202.8038,
        "pe": 6.0,
        "risks_count": 3,
        "rps20": 91.92,
        "rps60": 94.43,
        "rps120": 93.12,
        "rps250": 89.13,
        "ma10": 40.16,
        "vcp_quality": null,
        "ma5": 37.65,
        "ma20": 34.52,
        "dist_ma5_pct": -0.8,
        "dist_ma10_pct": -7.0,
        "dist_ma20_pct": 8.2
      },
      {
        "code": "002975",
        "code_full": "002975.SZ",
        "name": "博杰股份",
        "source_date": "2026/06/16",
        "highlights_count": 5,
        "market_cap": 233.2521,
        "pe": 6.4,
        "risks_count": 1,
        "rps20": 91.09,
        "rps60": 93.35,
        "rps120": 93.06,
        "rps250": 97.51,
        "ma10": 124.83,
        "vcp_quality": null,
        "ma5": 118.44,
        "ma20": 129.28,
        "dist_ma5_pct": 0.5,
        "dist_ma10_pct": -4.6,
        "dist_ma20_pct": -7.9
      },
      {
        "code": "300373",
        "code_full": "300373.SZ",
        "name": "扬杰科技",
        "source_date": "2026/07/02",
        "highlights_count": 5,
        "market_cap": 573.5579,
        "pe": 12.4,
        "risks_count": 0,
        "rps20": 98.12,
        "rps60": 94.06,
        "rps120": 92.95,
        "rps250": 93.39,
        "ma10": 136.77,
        "vcp_quality": null,
        "ma5": 128.52,
        "ma20": 123.3,
        "dist_ma5_pct": -9.7,
        "dist_ma10_pct": -15.1,
        "dist_ma20_pct": -5.9
      },
      {
        "code": "688392",
        "code_full": "688392.SH",
        "name": "骄成超声",
        "source_date": "2026/04/22",
        "highlights_count": 6,
        "market_cap": 217.5787,
        "pe": 3.8,
        "risks_count": 1,
        "rps20": 96.17,
        "rps60": 91.34,
        "rps120": 92.36,
        "rps250": 97.13,
        "ma10": 208.0,
        "vcp_quality": null,
        "ma5": 219.14,
        "ma20": 183.75,
        "dist_ma5_pct": -5.4,
        "dist_ma10_pct": -0.3,
        "dist_ma20_pct": 12.9
      },
      {
        "code": "688401",
        "code_full": "688401.SH",
        "name": "路维光电",
        "source_date": "2026/04/21",
        "highlights_count": 5,
        "market_cap": 153.2263,
        "pe": 3.9,
        "risks_count": 0,
        "rps20": 94.79,
        "rps60": 93.39,
        "rps120": 92.1,
        "rps250": 90.46,
        "ma10": 89.58,
        "vcp_quality": null,
        "ma5": 89.23,
        "ma20": 83.03,
        "dist_ma5_pct": -4.8,
        "dist_ma10_pct": -5.2,
        "dist_ma20_pct": 2.3
      },
      {
        "code": "002810",
        "code_full": "002810.SZ",
        "name": "山东赫达",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 72.8349,
        "pe": 9.8,
        "risks_count": 2,
        "rps20": 71.13,
        "rps60": 89.23,
        "rps120": 91.94,
        "rps250": 86.62,
        "ma10": 23.39,
        "vcp_quality": null,
        "ma5": 21.61,
        "ma20": 23.4,
        "dist_ma5_pct": -7.7,
        "dist_ma10_pct": -14.8,
        "dist_ma20_pct": -14.8
      },
      {
        "code": "002185",
        "code_full": "002185.SZ",
        "name": "华天科技",
        "source_date": "2026/07/15",
        "highlights_count": 4,
        "market_cap": 768.0432,
        "pe": 18.6,
        "risks_count": 3,
        "rps20": 97.18,
        "rps60": 92.24,
        "rps120": 91.77,
        "rps250": 88.24,
        "ma10": 22.46,
        "vcp_quality": null,
        "ma5": 23.84,
        "ma20": 20.99,
        "dist_ma5_pct": -11.9,
        "dist_ma10_pct": -6.5,
        "dist_ma20_pct": 0.0
      },
      {
        "code": "601958",
        "code_full": "601958.SH",
        "name": "金钼股份",
        "source_date": "2026/07/03",
        "highlights_count": 7,
        "market_cap": 695.3332,
        "pe": 18.2,
        "risks_count": 1,
        "rps20": 92.87,
        "rps60": 87.41,
        "rps120": 91.59,
        "rps250": 92.04,
        "ma10": 25.92,
        "vcp_quality": null,
        "ma5": 23.73,
        "ma20": 25.54,
        "dist_ma5_pct": -4.3,
        "dist_ma10_pct": -12.4,
        "dist_ma20_pct": -11.1
      },
      {
        "code": "688372",
        "code_full": "688372.SH",
        "name": "伟测科技",
        "source_date": "2026/06/17",
        "highlights_count": 4,
        "market_cap": 248.9052,
        "pe": 3.7,
        "risks_count": 1,
        "rps20": 87.32,
        "rps60": 87.88,
        "rps120": 91.43,
        "rps250": 88.82,
        "ma10": 174.56,
        "vcp_quality": null,
        "ma5": 178.78,
        "ma20": 163.5,
        "dist_ma5_pct": 0.0,
        "dist_ma10_pct": 2.4,
        "dist_ma20_pct": 9.4
      },
      {
        "code": "002407",
        "code_full": "002407.SZ",
        "name": "多氟多",
        "source_date": "2026/05/06",
        "highlights_count": 4,
        "market_cap": 403.3186,
        "pe": 16.1,
        "risks_count": 2,
        "rps20": 92.91,
        "rps60": 92.67,
        "rps120": 91.06,
        "rps250": 96.83,
        "ma10": 45.33,
        "vcp_quality": null,
        "ma5": 39.76,
        "ma20": 42.89,
        "dist_ma5_pct": -13.7,
        "dist_ma10_pct": -24.3,
        "dist_ma20_pct": -20.0
      },
      {
        "code": "300037",
        "code_full": "300037.SZ",
        "name": "新宙邦",
        "source_date": "2026/03/12",
        "highlights_count": 7,
        "market_cap": 506.6117,
        "pe": 16.5,
        "risks_count": 1,
        "rps20": 92.44,
        "rps60": 93.33,
        "rps120": 90.63,
        "rps250": 93.01,
        "ma10": 81.01,
        "vcp_quality": null,
        "ma5": 71.71,
        "ma20": 81.12,
        "dist_ma5_pct": -8.6,
        "dist_ma10_pct": -19.1,
        "dist_ma20_pct": -19.2
      },
      {
        "code": "300438",
        "code_full": "300438.SZ",
        "name": "鹏辉能源",
        "source_date": "2026/04/14",
        "highlights_count": 6,
        "market_cap": 347.3573,
        "pe": 11.2,
        "risks_count": 2,
        "rps20": 78.52,
        "rps60": 94.12,
        "rps120": 89.96,
        "rps250": 94.7,
        "ma10": 74.33,
        "vcp_quality": null,
        "ma5": 69.3,
        "ma20": 75.59,
        "dist_ma5_pct": -2.3,
        "dist_ma10_pct": -8.9,
        "dist_ma20_pct": -10.4
      },
      {
        "code": "688502",
        "code_full": "688502.SH",
        "name": "茂莱光学",
        "source_date": "2026/06/07",
        "highlights_count": 6,
        "market_cap": 285.5728,
        "pe": 3.3,
        "risks_count": 1,
        "rps20": 92.12,
        "rps60": 91.73,
        "rps120": 89.84,
        "rps250": 85.87,
        "ma10": 603.75,
        "vcp_quality": null,
        "ma5": 615.62,
        "ma20": 534.99,
        "dist_ma5_pct": -0.6,
        "dist_ma10_pct": 1.4,
        "dist_ma20_pct": 14.4
      },
      {
        "code": "002821",
        "code_full": "002821.SZ",
        "name": "凯莱英",
        "source_date": "2026/04/01",
        "highlights_count": 9,
        "market_cap": 706.2287,
        "pe": 9.6,
        "risks_count": 1,
        "rps20": 92.97,
        "rps60": 92.79,
        "rps120": 89.16,
        "rps250": 89.67,
        "ma10": 162.47,
        "vcp_quality": null,
        "ma5": 162.79,
        "ma20": 143.35,
        "dist_ma5_pct": 4.0,
        "dist_ma10_pct": 4.2,
        "dist_ma20_pct": 18.1
      },
      {
        "code": "002947",
        "code_full": "002947.SZ",
        "name": "恒铭达",
        "source_date": "2026/03/12",
        "highlights_count": 6,
        "market_cap": 161.8218,
        "pe": 7.4,
        "risks_count": 1,
        "rps20": 77.41,
        "rps60": 93.53,
        "rps120": 88.82,
        "rps250": 91.11,
        "ma10": 72.72,
        "vcp_quality": null,
        "ma5": 70.62,
        "ma20": 79.11,
        "dist_ma5_pct": -7.2,
        "dist_ma10_pct": -9.9,
        "dist_ma20_pct": -17.2
      },
      {
        "code": "688469",
        "code_full": "688469.SH",
        "name": "芯联集成-U",
        "source_date": "2026/07/10",
        "highlights_count": 4,
        "market_cap": 665.5854,
        "pe": 3.1,
        "risks_count": 2,
        "rps20": 94.35,
        "rps60": 87.45,
        "rps120": 88.21,
        "rps250": 86.74,
        "ma10": 9.72,
        "vcp_quality": null,
        "ma5": 9.5,
        "ma20": 8.71,
        "dist_ma5_pct": -7.2,
        "dist_ma10_pct": -9.3,
        "dist_ma20_pct": 1.3
      },
      {
        "code": "300870",
        "code_full": "300870.SZ",
        "name": "欧陆通",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 380.3877,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 59.26,
        "rps60": 88.64,
        "rps120": 88.19,
        "rps250": 93.69,
        "ma10": 294.56,
        "vcp_quality": null,
        "ma5": 270.39,
        "ma20": 306.56,
        "dist_ma5_pct": -9.4,
        "dist_ma10_pct": -16.9,
        "dist_ma20_pct": -20.1
      },
      {
        "code": "688331",
        "code_full": "688331.SH",
        "name": "荣昌生物",
        "source_date": "2026/07/06",
        "highlights_count": 5,
        "market_cap": 801.558,
        "pe": 4.2,
        "risks_count": 1,
        "rps20": 82.29,
        "rps60": 88.02,
        "rps120": 86.52,
        "rps250": 92.5,
        "ma10": 132.41,
        "vcp_quality": null,
        "ma5": 138.99,
        "ma20": 120.49,
        "dist_ma5_pct": -4.7,
        "dist_ma10_pct": 0.0,
        "dist_ma20_pct": 9.9
      },
      {
        "code": "300304",
        "code_full": "300304.SZ",
        "name": "云意电气",
        "source_date": "2026/07/13",
        "highlights_count": 4,
        "market_cap": 109.3289,
        "pe": 14.3,
        "risks_count": 2,
        "rps20": 92.89,
        "rps60": 87.94,
        "rps120": 85.66,
        "rps250": 89.43,
        "ma10": 15.8,
        "vcp_quality": null,
        "ma5": 14.32,
        "ma20": 16.37,
        "dist_ma5_pct": -11.1,
        "dist_ma10_pct": -19.4,
        "dist_ma20_pct": -22.2
      }
    ]
  },
  "enriched_candidates": [
    {
      "code": "002290.SZ",
      "fetch_time": "2026-07-16T11:40:49+0800",
      "name": "禾盛新材",
      "pe": 112.172,
      "pb": 18.1912,
      "ps_ttm": 6.9919,
      "pcf_ttm": 121.7594,
      "valuation_percentile": 90.18,
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
        "信创产业指数",
        "芯片指数",
        "QFII重仓指数",
        "AI算力指数",
        "GPU指数",
        "家电指数",
        "近期定增指数",
        "DeepSeek指数",
        "苏州工业园区指数"
      ],
      "score_company": 6.5,
      "score_trend": 6.8,
      "score_value": 3.6,
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
          "text": "最新综合估值高于近十年 90% 的时间，处于历史高位。"
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
          "content": "禾盛新材：关于2026年度以简易程序向特定对象发行股票预案的提示性公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "增发股票7443.37万股，募集资金不超过1.9亿元（预案）",
          "tags": [
            "增发融资"
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
      "valuation_history_from": "20210716",
      "current_price": 74.07,
      "price": 74.07,
      "ma5": 81.58,
      "ma10": 85.05,
      "ma20": 83.79,
      "dist_ma5_pct": -9.2,
      "dist_ma10_pct": -12.9,
      "dist_ma20_pct": -11.6,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 0.35,
        "pct_float": 0.2,
        "chg5_pct": 266.63,
        "net5_repay_days": 0,
        "signal": "adding"
      }
    },
    {
      "code": "688376.SH",
      "fetch_time": "2026-07-16T11:40:49+0800",
      "name": "美埃科技",
      "pe": 94.7157,
      "pb": 5.419,
      "ps_ttm": 5.0723,
      "pcf_ttm": 32.2332,
      "valuation_percentile": 97.87,
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
      "score_company": 7.5,
      "score_trend": 7.7,
      "score_value": 3.2,
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
          "content": "美埃科技：中信建投证券股份有限公司关于美埃（中国）环境科技股份有限公司股东向特定机构投资者询价转让股份相关资格的核查意见",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "19:13 美埃科技公告，持股5%以上股东Tecable Engineering Sdn. Bhd.拟通过询价转让方式转让其持有的公司首发前股份614.04万股，占公司总股本比例为4.54%，转让原因为自身资金需求。本次询价转让不通过集中竞价或大宗交易方式进行，受让方为具备相应定价能力和风险承受能力的机构投资者，受让后6个月内不得转让。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "09:41 7月10日，半导体设备板块表现活跃。深科达实现20cm两连板，亚翔集成与旭光电子此前涨停，国林科技、茂莱光学、美埃科技及至纯科技等个股涨幅居前。\n\n行业消息方面，美光科技披露了投资计划，预计到2035年，其对美国本土的投资总额将增加至超过2500亿美元。该计划主要受人工智能领域对内存需求增长的驱动，美光科技目标是将美国产能占其DRAM总产量的比例提升至40%。",
          "tags": [
            "资讯"
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
      "valuation_history_days": 400,
      "valuation_history_from": "20241118",
      "current_price": 88.42,
      "price": 88.42,
      "ma5": 99.46,
      "ma10": 101.73,
      "ma20": 87.27,
      "dist_ma5_pct": -11.1,
      "dist_ma10_pct": -13.1,
      "dist_ma20_pct": 1.3,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 2.52,
        "pct_float": 2.28,
        "chg5_pct": -20.38,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688777.SH",
      "fetch_time": "2026-07-16T11:40:49+0800",
      "name": "中控技术",
      "pe": 187.5223,
      "pb": 7.567,
      "ps_ttm": 9.3172,
      "pcf_ttm": 275.4668,
      "valuation_percentile": 75.73,
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
        "工业软件指数"
      ],
      "score_company": 8.2,
      "score_trend": 8.1,
      "score_value": 4.5,
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
          "tag": "公募",
          "text": "公募基金持股 16% ，很受内资机构青睐。"
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
          "content": "中控技术：中控技术股份有限公司关于调整暨聘任部分高级管理人员的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "20:09 近日，中控技术与南通星辰合成材料有限公司（简称“南通星辰”）正式签署全面深化的战略合作协议。双方将充分融合中控技术在流程工业自动化与工业AI领域的技术积淀，以及南通星辰在化工新材料行业的深厚场景经验，以中控技术自主研发的时间序列大模型平台TPT为核心技术底座，围绕工厂“内操智能化、外操无人化”两大核心方向开展全方位深度协同，合力打造化工新材料行业工业AI智能化示范标杆。(人民财讯)",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "孙华丰 任副总裁",
          "tags": [
            "管理层变更"
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
      "valuation_history_days": 293,
      "valuation_history_from": "20221125",
      "current_price": 97.68,
      "price": 97.68,
      "ma5": 104.67,
      "ma10": 111.85,
      "ma20": 106.92,
      "dist_ma5_pct": -6.7,
      "dist_ma10_pct": -12.7,
      "dist_ma20_pct": -8.6,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 31.81,
        "pct_float": 4.22,
        "chg5_pct": -1.31,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688652.SH",
      "fetch_time": "2026-07-16T11:40:49+0800",
      "name": "京仪装备",
      "pe": 181.3148,
      "pb": 12.7862,
      "ps_ttm": 19.4073,
      "pcf_ttm": 54.4653,
      "valuation_percentile": 98.11,
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
      "score_company": 7.4,
      "score_trend": 8.4,
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
          "content": "09:27 半导体板块低开，至纯科技触及跌停，有研硅、臻宝科技、德明利、京仪装备、兆易创新跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "09:30股价达到 180.15 元，创历史新高",
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
      "valuation_history_days": 150,
      "valuation_history_from": "20251201",
      "current_price": 198.26,
      "price": 198.26,
      "ma5": 204.59,
      "ma10": 194.95,
      "ma20": 165.89,
      "dist_ma5_pct": -3.1,
      "dist_ma10_pct": 1.7,
      "dist_ma20_pct": 19.5,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 3.49,
        "pct_float": 1.63,
        "chg5_pct": -40.15,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "000703.SZ",
      "fetch_time": "2026-07-16T11:40:49+0800",
      "name": "恒逸石化",
      "pe": 24.4581,
      "pb": 2.0496,
      "ps_ttm": 0.463,
      "pcf_ttm": 9.1396,
      "valuation_percentile": 73.36,
      "total_shares": 3821562147,
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
          "name": "炼油化工",
          "level": 3
        }
      ],
      "concepts": [
        "贷款回购指数",
        "资源股",
        "西部大开发指数",
        "可转债正股指数",
        "万得预增指数",
        "借壳上市指数",
        "石化精选指数",
        "油品升级指数",
        "油气改革指数",
        "供应链服务指数",
        "涤纶指数",
        "PTA指数"
      ],
      "score_company": 8.0,
      "score_trend": 8.5,
      "score_value": 4.3,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年06月26日，业绩超预期引发股价大幅上涨，当日收涨 7.34% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 2044% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 11% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 3.3% ，较受外资机构青睐。"
        },
        {
          "tag": "回购",
          "text": "近2月，公司累计回购 7957万股 ，占总股本比例 2.1% ，金额合计 10亿元 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月29日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "毛利",
          "text": "毛利率为 6.7% ，行业处于衰退期，或企业缺乏竞争力。"
        },
        {
          "tag": "偿债",
          "text": "现金短债比为 0.23 ，带息债务占全部投入资本 67% ，现金保障很弱，偿债压力很大。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/11发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-11"
        },
        {
          "content": "12:59 截至午间收盘，中证石化产业指数录得1.0%的涨幅。在成份股表现方面，恒逸石化触及涨停，和邦生物上涨6.3%，桐昆股份上涨5.5%。\n\n申万宏源证券分析认为，油价中枢呈现上行趋势，预计2026年整体将维持高油价背景，这将使油公司业绩单边受益。随着油价景气度回暖，油气勘探开发的投资力度有望加大。此外，美国乙烷供需格局维持宽松，油价上涨为相关企业业绩提供了较大的弹性空间。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "11:31 7月14日早盘市场呈现冲高回落走势，沪指跌破3900点，科创50指数半日跌幅为3.45%。沪深两市半日成交额合计1.63万亿元，较前一交易日缩量2272亿元。全市场超过2900只个股下跌，盘面热点表现较为分散。\n\n板块方面，油气概念持续活跃，蓝焰控股涨停，通源石油与科力股份涨幅均超过15%。医药商业板块表现强势，药易购实现20cm涨停，人民同泰亦封涨停。煤炭板块中的大有能源涨停，化工板块的恒逸石化、金煤科技及江苏索普均封涨停。\n\n下跌方面，AI服务器概念走弱，中国长城跌停。半导体材料板块出现集体调整，上海合晶、有研硅及沪硅产业跌幅明显。截至午间收盘，沪指下跌0.66%，深成指下跌0.42%，创业板指下跌0.29%。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 83885464697.74,
      "revenue_yoy": -0.115272,
      "operating_profit": 354428780.49,
      "operating_profit_yoy": 0.308904,
      "net_profit": 242449906.41,
      "net_profit_yoy": -0.264826,
      "gross_profit": 3668604065.21,
      "gross_profit_yoy": -0.043501,
      "cogs": 80216860632.53,
      "gross_margin": 4.37,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20210716",
      "current_price": 14.69,
      "price": 14.69,
      "ma5": 13.96,
      "ma10": 14.27,
      "ma20": 14.12,
      "dist_ma5_pct": 5.3,
      "dist_ma10_pct": 2.9,
      "dist_ma20_pct": 4.0,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.5,
        "pct_float": 1.91,
        "chg5_pct": -8.0,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "601126.SH",
      "fetch_time": "2026-07-16T11:40:49+0800",
      "name": "四方股份",
      "pe": 46.7945,
      "pb": 8.7866,
      "ps_ttm": 4.7114,
      "pcf_ttm": 38.1621,
      "valuation_percentile": 97.37,
      "total_shares": 833105500,
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
        "碳中和指数",
        "数字能源指数",
        "工业4.0指数",
        "特高压指数",
        "限售解禁指数",
        "即将解禁指数",
        "华为鲲鹏指数",
        "智能电网指数",
        "电气自动化设备精选指数",
        "高低压设备精选指数",
        "虚拟电厂指数",
        "泛在电力物联网指数"
      ],
      "score_company": 9.4,
      "score_trend": 5.7,
      "score_value": 3.4,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 电网自动化设备 行业龙头企业。"
        },
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 18% ，收入成长性较强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 15% ，投入资本回报率为 16% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 147% ，净利润现金含量较高。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 3.6% ，现金分红极高。"
        },
        {
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 6.3% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月21日 至今陷入调整，资金有出逃可能。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/27发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-27"
        },
        {
          "content": "10:43 电网设备板块短线拉升，中国西电涨停，中元股份涨超10%，万胜智能、安科瑞、四方股份、迦南智能、双杰电气跟涨。相关ETF方面，电网设备ETF广发（159320）涨2.98%，成交额5101.2万元，电网设备ETF易方达（560390）涨2.81%，成交额8538.61万元。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "16:39 四方股份公告，公司已于2026年6月16日向香港联合交易所有限公司递交了境外发行股份（H股）并在香港联交所主板挂牌上市的申请，并于同日在香港联交所网站刊登了本次发行的申请材料。",
          "tags": [
            "快讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 6131570784.23,
      "revenue_yoy": 0.203857,
      "operating_profit": 779571698.85,
      "operating_profit_yoy": 0.130677,
      "net_profit": 703388366.53,
      "net_profit_yoy": 0.152858,
      "gross_profit": 1886379732.76,
      "gross_profit_yoy": 0.099029,
      "cogs": 4245191051.47,
      "gross_margin": 30.77,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210716",
      "current_price": 49.77,
      "price": 49.77,
      "ma5": 55.06,
      "ma10": 57.9,
      "ma20": 64.43,
      "dist_ma5_pct": -9.6,
      "dist_ma10_pct": -14.0,
      "dist_ma20_pct": -22.8,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7994,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 23.25,
        "pct_float": 5.68,
        "chg5_pct": -3.71,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688515.SH",
      "fetch_time": "2026-07-16T11:40:49+0800",
      "name": "裕太微-U",
      "pe": -121.0574,
      "pb": 9.3278,
      "ps_ttm": 20.2033,
      "pcf_ttm": null,
      "valuation_percentile": 77.19,
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
      "score_company": 5.9,
      "score_trend": 7.6,
      "score_value": 4.6,
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
          "text": "近3月，股价涨幅超过A股市场 94% 的股票，走势较强。"
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
          "content": "10:00股价达到 271.91 元，创历史新高",
          "tags": [
            "股价新高"
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
      "valuation_history_days": 349,
      "valuation_history_from": "20250210",
      "current_price": 200.79,
      "price": 200.79,
      "ma5": 219.05,
      "ma10": 234.67,
      "ma20": 217.69,
      "dist_ma5_pct": -8.3,
      "dist_ma10_pct": -14.4,
      "dist_ma20_pct": -7.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.72,
        "pct_float": 6.53,
        "chg5_pct": -23.29,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301536.SZ",
      "fetch_time": "2026-07-16T11:40:49+0800",
      "name": "星宸科技",
      "pe": 95.6398,
      "pb": 14.7386,
      "ps_ttm": 13.8342,
      "pcf_ttm": 154.641,
      "valuation_percentile": 88.57,
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
      "score_company": 8.1,
      "score_trend": 8.5,
      "score_value": 3.9,
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
          "text": "近6月，股价涨幅超过A股市场 95% 的股票，走势较强。"
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
          "content": "09:33股价达到 97.28 元，创历史新高",
          "tags": [
            "股价新高"
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
      "valuation_history_days": 72,
      "valuation_history_from": "20260330",
      "current_price": 108.39,
      "price": 108.39,
      "ma5": 116.18,
      "ma10": 119.2,
      "ma20": 109.97,
      "dist_ma5_pct": -6.7,
      "dist_ma10_pct": -9.1,
      "dist_ma20_pct": -1.4,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9921,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 7.81,
        "pct_float": 3.9,
        "chg5_pct": 10.23,
        "net5_repay_days": 0,
        "signal": "adding"
      }
    },
    {
      "code": "300346.SZ",
      "fetch_time": "2026-07-16T11:40:51+0800",
      "name": "南大光电",
      "pe": 127.2209,
      "pb": 13.011,
      "ps_ttm": 16.9194,
      "pcf_ttm": 66.373,
      "valuation_percentile": 69.47,
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
      "score_company": 7.7,
      "score_trend": 8.1,
      "score_value": 4.5,
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
          "text": "2026年06月29日，换手率 21% ，短线资金追逐，波动风险较高。"
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
          "content": "14:39 电子化学品板块持续拉升，菲沃泰涨停，上海新阳涨超15%，中船特气涨超10%，广钢气体、瑞联新材、安集科技、南大光电、晶瑞电材跟涨。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "15:01 7月3日，A股市场呈现冲高回落走势，三大指数尾盘涨幅有所收窄。全天沪深两市成交额为3.18万亿元，较前一交易日减少2681亿元。市场整体涨多跌少，全市场超过3800只个股上涨。\n\n盘面上，机器人概念股表现突出，板块内四十余只成分股涨停。其中，埃斯顿实现4天3板，日盈电子收获2连板，长盛轴承、卧龙电驱、首开股份涨停。黄金概念持续走强，招金矿业、赤峰黄金录得2连板，四川黄金、西部黄金、山金国际涨停。电网设备板块中，华明装备、金智科技涨停。医药板块亦有活跃表现，石药景峰实现2连板。\n\n下跌方面，半导体材料板块走弱，电子特气与光刻胶方向领跌，多氟多触及跌停，容大感光、南大光电、华特气体跌幅较大。\n\n截至收盘，沪指上涨0.37%，深成指上涨0.64%，创业板指上涨0.07%。",
          "tags": [
            "资讯"
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
      "valuation_history_from": "20210716",
      "current_price": 66.95,
      "price": 66.95,
      "ma5": 74.3,
      "ma10": 80.67,
      "ma20": 73.35,
      "dist_ma5_pct": -9.9,
      "dist_ma10_pct": -17.0,
      "dist_ma20_pct": -8.7,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9921,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 28.32,
        "pct_float": 6.47,
        "chg5_pct": -8.32,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300236.SZ",
      "fetch_time": "2026-07-16T11:40:51+0800",
      "name": "上海新阳",
      "pe": 87.4148,
      "pb": 6.6225,
      "ps_ttm": 14.8423,
      "pcf_ttm": 61.6762,
      "valuation_percentile": 76.05,
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
        "资源股",
        "半导体产业指数",
        "芯片指数",
        "集成电路指数",
        "股权激励指数",
        "养老金指数",
        "中小创蓝筹指数",
        "中芯国际产业链指数",
        "长鑫存储指数",
        "晶圆产业指数",
        "存储器指数",
        "半导体材料指数",
        "模拟芯片指数",
        "光刻机指数"
      ],
      "score_company": 7.5,
      "score_trend": 8.1,
      "score_value": 4.2,
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
          "content": "14:39 电子化学品板块持续拉升，菲沃泰涨停，上海新阳涨超15%，中船特气涨超10%，广钢气体、瑞联新材、安集科技、南大光电、晶瑞电材跟涨。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "10:13 先进封装板块再度拉升，华天科技、中京电子、朗迪集团、高德红外、同兴达、旭光电子涨停，上海新阳涨超10%，汇成股份、深科达、深科技、太极实业、甬矽电子跟涨。相关ETF方面，科创芯片ETF汇添富（588750）涨1.57%，成交额1.6亿元，芯片ETF广发（159801）涨2.44%，成交额2.17亿元。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "10:39股价达到 114.42 元，创历史新高",
          "tags": [
            "股价新高"
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
      "valuation_history_from": "20210719",
      "current_price": 111.83,
      "price": 111.83,
      "ma5": 115.64,
      "ma10": 118.23,
      "ma20": 110.19,
      "dist_ma5_pct": -3.3,
      "dist_ma10_pct": -5.4,
      "dist_ma20_pct": 1.5,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9921,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 13.1,
        "pct_float": 4.54,
        "chg5_pct": 1.67,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "688536.SH",
      "fetch_time": "2026-07-16T11:40:51+0800",
      "name": "思瑞浦",
      "pe": 146.5183,
      "pb": 6.074,
      "ps_ttm": 15.8958,
      "pcf_ttm": 120.8337,
      "valuation_percentile": 44.6,
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
        "5G指数",
        "专精特新小巨人指数",
        "半导体产业指数",
        "芯片指数",
        "半导体精选指数",
        "AIPC指数",
        "智能家居指数",
        "股权激励指数",
        "模拟芯片指数",
        "苏州工业园区指数"
      ],
      "score_company": 8.3,
      "score_trend": 7.9,
      "score_value": 6.6,
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
          "text": "近3月，股价涨幅超过A股市场 96% 的股票，走势较强。"
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
          "content": "公司发布股权激励计划预案，股价盘中上涨 8.03% ，股价收盘涨幅 6.95%",
          "tags": [
            "股价上涨"
          ]
        },
        {
          "content": "2026/07/14发布预案公告，本计划拟向激励对象授予134万股 ，约占总股本的 0.97%，授予价格为 201元/股 。",
          "tags": [
            "激励计划"
          ]
        },
        {
          "content": "思瑞浦：国浩律师（上海）事务所关于思瑞浦微电子科技（苏州）股份有限公司2026年第二次临时股东会之法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "思瑞浦：关于定向可转债转股结果暨股份变动的公告",
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
      "valuation_history_days": 301,
      "valuation_history_from": "20220922",
      "current_price": 303.44,
      "price": 303.44,
      "ma5": 332.64,
      "ma10": 339.87,
      "ma20": 323.24,
      "dist_ma5_pct": -8.8,
      "dist_ma10_pct": -10.7,
      "dist_ma20_pct": -6.1,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 11.3,
        "pct_float": 2.89,
        "chg5_pct": -11.72,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688378.SH",
      "fetch_time": "2026-07-16T11:40:51+0800",
      "name": "奥来德",
      "pe": 98.5168,
      "pb": 6.2384,
      "ps_ttm": 18.9812,
      "pcf_ttm": 40.076,
      "valuation_percentile": 95.0,
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
      "score_company": 8.2,
      "score_trend": 8.2,
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
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 96% 的股票，走势很强。"
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
          "content": "16:29 国芳集团发布业绩预告，预计2026年半年度归属于上市公司股东的净利润在6800.00万元至7500.00万元之间，较上年同期增长200.25%至231.16%。\n\n公司表示，业绩增长主要得益于主力门店升级改造后带来的客流与销售额提升，以及处置奥来德股票所获得的投资收益增加。\n\n根据测算，公司第二季度净利润预计为0.26亿元至0.33亿元，相较于第一季度的0.42亿元，环比变动幅度预计下降19%至36%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价盘中上涨 8.62% ，股价收盘涨幅 4.15%",
          "tags": [
            "股价上涨"
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
      "valuation_history_days": 311,
      "valuation_history_from": "20220905",
      "current_price": 51.08,
      "price": 51.08,
      "ma5": 55.45,
      "ma10": 57.02,
      "ma20": 52.57,
      "dist_ma5_pct": -7.9,
      "dist_ma10_pct": -10.4,
      "dist_ma20_pct": -2.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.39,
        "pct_float": 4.48,
        "chg5_pct": -4.46,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688106.SH",
      "fetch_time": "2026-07-16T11:40:51+0800",
      "name": "金宏气体",
      "pe": 211.5232,
      "pb": 5.0546,
      "ps_ttm": 6.967,
      "pcf_ttm": 40.0484,
      "valuation_percentile": 80.51,
      "total_shares": 535384888,
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
        "专精特新小巨人主题指数",
        "贷款回购指数",
        "专精特新小巨人指数",
        "资源股",
        "中芯国际产业链指数",
        "半导体材料指数",
        "氢能指数",
        "工业气体指数"
      ],
      "score_company": 7.3,
      "score_trend": 7.8,
      "score_value": 4.1,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 67% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 12% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 3346万元 ，较上期增长 31% ，占2025年营收 1.2% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 电子化学品Ⅱ 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        },
        {
          "tag": "激励",
          "text": "2026年07月14日，公司发布股票激励计划，当日收涨 7.6% 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月03日大跌 -16.2% ，且成交额为近20日均值的 2.24倍 ，抛压很重。"
        },
        {
          "tag": "商誉",
          "text": "商誉占净资产 11% ，商誉减值风险较高。"
        },
        {
          "tag": "波动",
          "text": "近10天，日均换手率 13% ，短线资金追逐，波动风险较高。"
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
          "content": "公司发布2026半年报预告，股价开盘下跌 -7.92%",
          "tags": [
            "股价下跌"
          ]
        },
        {
          "content": "08:05 国家统计局发布数据，2026上半年GDP同比增长4.7%；6月规模以上工业增加值同比增长5.3%；1-6月全国固定资产投资同比下降5.7%；上半年社会消费商品和服务零售总额同比增长2.7%。\n\n央行数据显示，2026年6月末社会融资规模存量为462.06万亿元；上半年社会融资规模增量累计20.84万亿元，同比增长7.4%；上半年人民币存款增加17.76万亿元，人民币贷款增加10.72万亿元；6月末广义货币(M2)余额356.71万亿元，同比增长8%。央行副行长邹澜表示，将加大逆周期和跨周期调节力度。\n\n国家统计局发言人王冠华称，上半年规模以上工业企业集成电路产量增长23.1%，达2798亿块，平均每天生产超15亿块。\n\n网信办发布7款手机端侧生成式人工智能服务备案信息，包括Apple智能、AndesGPT、华为小艺AI、vivo蓝心、小米澎湃AI、盖乐世AI及努比亚豆包手机大模型。\n\n国家能源局数据显示，6月全社会用电量8981亿千瓦时，同比增长3.7%；1-6月累计50999亿千瓦时，同比增长5.3%。\n\n上市公司业绩与动态方面：金宏气体预计Q2净利环比增长1081%-1331%；大普微预计Q2净利环比增长124%-164%；江丰电子预计上半年净利同比增长90%-122%；佰维存储预计上半年净利同比增长3200%-3422%；嘉元科技预计上半年净利同比预增879%-961%。国海证券拟竞买大通证券51.59%股份；精测电子拟收购上海精测半导体41.17%股权；天智航拟购买上海骨科控股权。仕佳光子拟定增募资不超28亿元；灿勤科技拟募资不超8.51亿元；中国巨石拟投建2.5亿米电子布生产线。\n\n行业方面，全球半导体协会预计2028年全球半导体制造设备销售额达2295亿美元。力积电7月起将存储代工报价上调45%。\n\n国际局势与经济方面，美军针对伊朗发起打击，伊朗表示目前无谈判计划。美联储理事库克称通胀有望降温。美联储褐皮书显示经济小幅增长。英伟达CEO黄仁勋表示下一代AI加速计算系统已进入生产阶段。苹果寻求收购芯片公司。阿斯麦计划提高设备价格。Anthropic正筹备IPO。三星电子考虑外包谷歌TPU I/O芯片后端设计。\n\n周三美股收涨，道指涨0.29%，纳指涨0.62%，标普500涨0.38%。存储概念股下跌，SK海力士跌超9%，美光科技、闪迪、西部数据跌超8%。热门中概股普涨。WTI原油涨0.33%，布伦特原油涨0.26%，COMEX黄金跌0.07%，COMEX白银跌1.7%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "22:13 7月15日，多家A股上市公司披露2026年半年度业绩预告。涉及公司包括佰维存储、嘉元科技、江丰电子、大普微、金宏气体、华联控股、凯尔达、移为通信、泰和科技、思特威、孩子王及鹏辉能源。\n\n其中，佰维存储预计上半年净利润为70亿元至75亿元，同比增长幅度在3200%至3422%之间，公司表示业绩增长主要受AI算力需求增长及存储行业景气度提升影响。\n\n大普微预计上半年净利润为12亿元至13亿元，实现同比扭亏为盈。公司指出，全球AI技术发展带动了数据中心企业级存储需求的增长。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 2030958763.69,
      "revenue_yoy": 0.093261,
      "operating_profit": 153525951.67,
      "operating_profit_yoy": -0.417746,
      "net_profit": 128768712.78,
      "net_profit_yoy": -0.420621,
      "gross_profit": 608416104.66,
      "gross_profit_yoy": -0.01025,
      "cogs": 1422542659.03,
      "gross_margin": 29.96,
      "pe_forward": null,
      "valuation_history_days": 329,
      "valuation_history_from": "20220617",
      "current_price": 37.35,
      "price": 37.35,
      "ma5": 37.65,
      "ma10": 40.16,
      "ma20": 34.52,
      "dist_ma5_pct": -0.8,
      "dist_ma10_pct": -7.0,
      "dist_ma20_pct": 8.2,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 11.97,
        "pct_float": 5.9,
        "chg5_pct": 3.96,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "002975.SZ",
      "fetch_time": "2026-07-16T11:40:51+0800",
      "name": "博杰股份",
      "pe": 93.5201,
      "pb": 9.2541,
      "ps_ttm": 10.3824,
      "pcf_ttm": 276.2329,
      "valuation_percentile": 83.33,
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
        "万得预增指数",
        "机器人指数",
        "液冷服务器指数",
        "MLCC指数",
        "玻璃基板指数",
        "磷化铟指数"
      ],
      "score_company": 8.1,
      "score_trend": 8.1,
      "score_value": 4.1,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月14日，业绩超预期引发股价大幅上涨，当日收涨 10.0% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 149% ，利润成长性强。"
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
          "tag": "回购",
          "text": "近6月，公司累计回购 88万股 ，占总股本比例 0.42% ，金额合计 3002万元 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月15日大跌 -10% ，股价跌停，抛压很重。"
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
          "content": "09:27 7月15日，部分市场焦点股竞价情况如下：\n\n恒尚节能（11天10板）高开1.58%。\n\n医药板块方面，哈药股份（3板）高开5.88%，济民健康（4天2板）低开1.51%。\n\n光通信板块方面，宿迁联盛（6天3板）低开2.12%，东山精密（4天2板）高开0.24%，博杰股份（4天2板）高开3.60%。\n\n其他概念股方面，分红送转概念信通电子（2板）高开4.81%，电解铝板块宏桥控股（2板）高开3.49%，并购重组概念中岩大地（3天2板）低开2.10%，玻璃基板概念三峡新材（3天2板）高开1.09%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是公司预计2026年上半年归母净利润同比大幅增长642.86%–816.20%，显示电子测试与工业自动化业务收入和盈利能力显著改善。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价盘中上涨 8.07% ，股价收盘涨幅 10.00%",
          "tags": [
            "股价上涨"
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
      "valuation_history_days": 269,
      "valuation_history_from": "20220207",
      "current_price": 119.06,
      "price": 119.06,
      "ma5": 118.44,
      "ma10": 124.83,
      "ma20": 129.28,
      "dist_ma5_pct": 0.5,
      "dist_ma10_pct": -4.6,
      "dist_ma20_pct": -7.9,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      }
    },
    {
      "code": "300373.SZ",
      "fetch_time": "2026-07-16T11:40:51+0800",
      "name": "扬杰科技",
      "pe": 41.707,
      "pb": 5.9309,
      "ps_ttm": 7.442,
      "pcf_ttm": 35.3699,
      "valuation_percentile": 68.37,
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
      "score_company": 8.2,
      "score_trend": 7.8,
      "score_value": 4.7,
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
          "content": "扬杰科技：关于董事离任的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "董事（刘从宁）离任",
          "tags": [
            "管理层变更"
          ]
        },
        {
          "content": "13:39 7月7日午后，碳化硅概念板块出现局部波动。露笑科技股价直线拉升并触及涨停板。此前，东微半导已实现20cm涨停，易事特、英杰电气、扬杰科技、三安光电及华微电子等个股跟涨。\n\n行业消息显示，英伟达在算力中心供电白皮书中，将SST确立为下一代800V高压直流供电架构的核心设备。该设备利用碳化硅功率器件的高频特性，能够实现从10kV中压交流到800V直流的一步式转换。",
          "tags": [
            "资讯"
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
      "valuation_history_from": "20210716",
      "current_price": 116.08,
      "price": 116.08,
      "ma5": 128.52,
      "ma10": 136.77,
      "ma20": 123.3,
      "dist_ma5_pct": -9.7,
      "dist_ma10_pct": -15.1,
      "dist_ma20_pct": -5.9,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9921,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 19.28,
        "pct_float": 3.37,
        "chg5_pct": -13.42,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688392.SH",
      "fetch_time": "2026-07-16T11:40:51+0800",
      "name": "骄成超声",
      "pe": 147.8508,
      "pb": 11.6266,
      "ps_ttm": 25.857,
      "pcf_ttm": 168.0152,
      "valuation_percentile": 94.41,
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
      "score_company": 7.7,
      "score_trend": 8.4,
      "score_value": 3.5,
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
          "text": " 8家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 12% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月10日大跌 -15.7% ，且成交额为近20日均值的 1.57倍 ，抛压很重。"
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
          "content": "骄成超声：江苏世纪同仁律师事务所关于上海骄成超声波技术股份有限公司2026年第三次临时股东会的法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是公司披露并购重组进展显示交易推进顺利，未来有望通过并购扩充超声设备技术与产能、提升市场份额和业绩预期。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是公司拟以2076.38万元收购子公司剩余40%股权，取得100%控股利于业务整合与提升盈利能力。",
          "tags": [
            "快讯",
            "大涨原因"
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
      "valuation_history_days": 430,
      "valuation_history_from": "20240927",
      "current_price": 207.41,
      "price": 207.41,
      "ma5": 219.14,
      "ma10": 208.0,
      "ma20": 183.75,
      "dist_ma5_pct": -5.4,
      "dist_ma10_pct": -0.3,
      "dist_ma20_pct": 12.9,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.87,
        "pct_float": 3.16,
        "chg5_pct": 1.09,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "688401.SH",
      "fetch_time": "2026-07-16T11:40:53+0800",
      "name": "路维光电",
      "pe": 52.8001,
      "pb": 8.9646,
      "ps_ttm": 11.7145,
      "pcf_ttm": 48.5232,
      "valuation_percentile": 90.76,
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
      "score_company": 7.7,
      "score_trend": 8.0,
      "score_value": 3.7,
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
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "2027/01/15解禁1202.02万股，占总股本6.22%",
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
      "valuation_history_days": 458,
      "valuation_history_from": "20240819",
      "current_price": 84.95,
      "price": 84.95,
      "ma5": 89.23,
      "ma10": 89.58,
      "ma20": 83.03,
      "dist_ma5_pct": -4.8,
      "dist_ma10_pct": -5.2,
      "dist_ma20_pct": 2.3,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.74,
        "pct_float": 4.67,
        "chg5_pct": 3.71,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "002810.SZ",
      "fetch_time": "2026-07-16T11:40:53+0800",
      "name": "山东赫达",
      "pe": 35.2395,
      "pb": 3.2491,
      "ps_ttm": 3.4392,
      "pcf_ttm": 14.7806,
      "valuation_percentile": 45.83,
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
        "万得预增指数",
        "预期提升指数",
        "化学制品精选指数"
      ],
      "score_company": 8.3,
      "score_trend": 5.1,
      "score_value": 6.4,
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
          "content": "回购总金额不超过1163万元，回购最高价不超过6.21元/股 （预案）",
          "tags": [
            "公司回购限售股"
          ]
        },
        {
          "content": "15:00 今天大跌的原因可能是公司公布Q2净利润预计环比下降1%至20%，业绩下滑或幅度不及预期，削弱投资者信心，压低股价。",
          "tags": [
            "快讯",
            "大跌原因"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价盘中下跌 -8.34%",
          "tags": [
            "股价下跌"
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
      "valuation_history_from": "20210716",
      "current_price": 19.94,
      "price": 19.94,
      "ma5": 21.61,
      "ma10": 23.39,
      "ma20": 23.4,
      "dist_ma5_pct": -7.7,
      "dist_ma10_pct": -14.8,
      "dist_ma20_pct": -14.8,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 2.16,
        "pct_float": 3.2,
        "chg5_pct": -7.75,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002185.SZ",
      "fetch_time": "2026-07-16T11:40:53+0800",
      "name": "华天科技",
      "pe": 85.548,
      "pb": 3.8241,
      "ps_ttm": 3.7838,
      "pcf_ttm": 21.1703,
      "valuation_percentile": 88.83,
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
        "股权激励指数",
        "成交额TOP10指数",
        "国家大基金指数",
        "GPU指数",
        "元宇宙主题指数"
      ],
      "score_company": 7.5,
      "score_trend": 9.6,
      "score_value": 3.7,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月14日，业绩超预期引发股价大幅上涨，当日收涨 6.42% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 191% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 7.2% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "趋势",
          "text": "公司所属 半导体 行业，自 2026年04月 以来持续走强，正处于上涨趋势中。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月15日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 5.5% ，扣非净利润占净利润 36% ，收益质量很低。"
        },
        {
          "tag": "波动",
          "text": "近3天，日均换手率 23% ，短线资金追逐，波动风险很高。"
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
          "content": "09:27 存储芯片板块大幅低开，德明利、华天科技、通富微电跌停开盘，精测电子跌超15%，天山电子、香农芯创、澜起科技跌幅居前。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "18:12 科技赛道近期出现整体调整，半导体板块成为市场主要领跌方向。德明利、华天科技、长电科技等个股跌停，沐曦股份、佰维存储、江波龙、长川科技、北京君正、江丰电子、雅克科技等权重股跌幅均超过8%。此次下跌涵盖了存储芯片、先进封装、算力芯片、半导体设备及电子材料等产业链环节，板块呈现普跌态势。作为此前市场的核心主线，半导体板块需出现止跌企稳信号，以修复市场信心。\n\n另一方面，东山精密、生益科技、通富微电、长飞光纤等已披露中报业绩预增的标的，今日表现相对抗跌，显示出业绩基本面的防御性。后续可重点关注中报高预增的科技股，若此类品种在充分换手消化浮筹后企稳拉升，有望带动板块情绪回暖，并对科技板块的估值修复产生正向影响。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价盘中上涨 8.99% ，股价收盘涨幅 6.42%",
          "tags": [
            "股价上涨"
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
      "valuation_history_from": "20210716",
      "current_price": 21.0,
      "price": 21.0,
      "ma5": 23.84,
      "ma10": 22.46,
      "ma20": 20.99,
      "dist_ma5_pct": -11.9,
      "dist_ma10_pct": -6.5,
      "dist_ma20_pct": 0.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 30.85,
        "pct_float": 4.02,
        "chg5_pct": -2.99,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "601958.SH",
      "fetch_time": "2026-07-16T11:40:53+0800",
      "name": "金钼股份",
      "pe": 20.6966,
      "pb": 3.5302,
      "ps_ttm": 4.7536,
      "pcf_ttm": 32.3303,
      "valuation_percentile": 84.65,
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
      "score_company": 8.6,
      "score_trend": 7.5,
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
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 33% ，利润成长性强。"
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
          "text": "近1年，股价涨幅超过A股市场 91% 的股票，走势较强。"
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
          "content": "14:08 小金属概念板块走高，海南矿业涨停，成都路桥、和邦生物此前封板，飞南资源、铜陵有色、中金黄金、金钼股份、锡业股份等跟涨。相关ETF方面，有色ETF广发（159029）涨5.44%，成交额1559.34万元，有色ETF富国（159168）涨5.42%，成交额2870.27万元。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "16:05 金钼股份发布公告称，公司董事会已收到段志毅提交的书面辞职报告。由于工作调动，段志毅申请辞去公司总经理职务，该辞职报告自送达董事会之日起生效。\n\n段志毅在离任总经理职务后，将继续在公司第六届董事会担任董事。目前，金钼股份正积极推进新任总经理的聘任工作，以尽快完成相关程序。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "总经理（段志毅）离任",
          "tags": [
            "管理层变更"
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
      "valuation_history_from": "20210716",
      "current_price": 22.71,
      "price": 22.71,
      "ma5": 23.73,
      "ma10": 25.92,
      "ma20": 25.54,
      "dist_ma5_pct": -4.3,
      "dist_ma10_pct": -12.4,
      "dist_ma20_pct": -11.1,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7994,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 12.24,
        "pct_float": 1.76,
        "chg5_pct": -2.66,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688372.SH",
      "fetch_time": "2026-07-16T11:40:53+0800",
      "name": "伟测科技",
      "pe": 69.4656,
      "pb": 5.8926,
      "ps_ttm": 13.5909,
      "pcf_ttm": 31.7748,
      "valuation_percentile": 79.27,
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
        "半导体精选指数",
        "QFII重仓指数",
        "浦东新区指数",
        "股权激励指数",
        "可转债预案指数"
      ],
      "score_company": 8.0,
      "score_trend": 8.4,
      "score_value": 4.5,
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
          "content": "11:20股价达到 182.66 元，创历史新高",
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
      "valuation_history_days": 415,
      "valuation_history_from": "20241028",
      "current_price": 178.8,
      "price": 178.8,
      "ma5": 178.78,
      "ma10": 174.56,
      "ma20": 163.5,
      "dist_ma5_pct": 0.0,
      "dist_ma10_pct": 2.4,
      "dist_ma20_pct": 9.4,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.68,
        "pct_float": 4.29,
        "chg5_pct": -5.78,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "002407.SZ",
      "fetch_time": "2026-07-16T11:40:53+0800",
      "name": "多氟多",
      "pe": 75.097,
      "pb": 4.6046,
      "ps_ttm": 3.7264,
      "pcf_ttm": null,
      "valuation_percentile": 65.21,
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
        "万得预增指数",
        "固态电池指数",
        "钠离子电池指数",
        "动力电池指数",
        "长鑫存储指数",
        "半导体材料指数",
        "六氟磷酸锂指数",
        "三元锂电池指数",
        "PVDF指数",
        "氟化工指数",
        "氢氟酸指数",
        "中原经济区指数",
        "锂电电解液指数"
      ],
      "score_company": 7.9,
      "score_trend": 7.2,
      "score_value": 5.1,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 1066% ，利润成长性强。"
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
          "text": "近10天，日均换手率 18% ，短线资金追逐，波动风险较高。"
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
          "content": "13:46 7月13日早盘，多氟多股价跌停。截至午间收盘，公司股价报36.99元/股，跌幅为10%。消息面上，7月10日晚，多氟多对外披露2026年半年度业绩预告。公司预计2026年上半年实现归属于上市公司股东的净利润为4.5亿元至5.6亿元，同比增长776.68%至990.98%。但业绩主要由一季度业绩贡献。根据公司此前披露的一季报。2026年一季度，多氟多共实现归母净利润约3.76亿元，同比增长480.14%。由此计算，多氟多第二季度归母净利润预计仅为0.74亿元至1.84亿元，环比大幅下滑51%至80%。对此，多氟多方面回应记者，公司所在行业确实有季节性波动，价格和出货量都有波动。二季度属于锂电行业的淡季。上游碳酸锂涨价对公司有影响。为了应对原材料涨价，公司产品也会考虑涨价。从三方报价看，六氟磷酸锂目前价格在10万元/吨左右。公司具体产品情况以正式半年报为准。(中证金牛座)",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价开盘下跌 -10.00%",
          "tags": [
            "股价下跌"
          ]
        },
        {
          "content": "08:03 国务院常务会议听取数字中国建设情况汇报，强调推进新一代通信网与算力网建设，加强前沿科技攻关及安全风险防控。商务部与海关总署公告，即日起对氦气实施临时禁止出口管理。长征十号乙运载火箭实现一子级可控回收，预计年底前完成复用飞行，该火箭首次规模化应用液化天然气制备的高纯甲烷燃料。国务院原则同意中医药振兴发展十五五规划。7月10日全国用电负荷达15.18亿千瓦，创历史新高。国家网信办披露2026年5月至6月新增120款生成式人工智能服务备案。长江存储IPO辅导工作于7月10日更新。深圳证监局对涉嫌编造共进股份虚假信息的人员立案调查。证监局正对基金销售机构开展合规摸底。鼎龙股份玻璃基板软抛光垫已完成送样，华工科技TGV玻璃通孔激光加工装备完成定型。多家上市公司发布业绩预告，其中粤海饲料、杉杉股份、紫光股份、亿道信息、方正科技、风华高科、翔鹭钨业、中信证券、香农芯创、融捷股份等披露上半年业绩变动情况。烽火通信拟定增募资不超过29.13亿元并收购藤仓烽火股权，陕鼓动力拟收购陕西秦风气体股权，中国人寿拟出资49.99亿元成立半导体产业基金，东阳光签署算力服务合同，日科化学拟收购亘元新材，领益智造参与富通嘉善重整。星网宇达澄清卫星通信业务与长征十号乙运载火箭技术无关联。世运电路、多氟多披露业绩变动，巨力索具因误导性陈述被罚450万元。中国卫星上半年预计扭亏为盈，赛力斯、广汽集团、牧原股份预计上半年亏损。国际方面，美军与伊朗发生军事冲突。三星电子计划将龙仁芯片工厂投产提前至2029年。SK海力士CEO称存储芯片短缺或持续至2030年后。苹果公司起诉OpenAI窃取商业机密，OpenAI予以回应。美联储报告显示美国通胀升温，总体PCE同比升至4.1%。上周五美股收涨，SK海力士ADR上市首日收涨近13%，热门中概股涨跌不一。国际油价与贵金属期货价格波动。",
          "tags": [
            "资讯"
          ]
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
      "valuation_history_from": "20210716",
      "current_price": 34.33,
      "price": 34.33,
      "ma5": 39.76,
      "ma10": 45.33,
      "ma20": 42.89,
      "dist_ma5_pct": -13.7,
      "dist_ma10_pct": -24.3,
      "dist_ma20_pct": -20.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 24.36,
        "pct_float": 6.67,
        "chg5_pct": -16.69,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300037.SZ",
      "fetch_time": "2026-07-16T11:40:53+0800",
      "name": "新宙邦",
      "pe": 36.649,
      "pb": 4.6462,
      "ps_ttm": 4.4917,
      "pcf_ttm": 31.0032,
      "valuation_percentile": 67.23,
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
        "资源股",
        "珠三角指数",
        "碳中和指数",
        "AI手机指数",
        "深圳本地股指数",
        "股权激励指数",
        "可转债正股指数",
        "新材料指数",
        "新能源汽车指数",
        "锂电池指数",
        "特斯拉指数",
        "中小创蓝筹指数",
        "万得预增指数"
      ],
      "score_company": 9.2,
      "score_trend": 7.4,
      "score_value": 4.9,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 105% ，利润成长性强。"
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
          "tag": "评级",
          "text": "近90天， 11家 机构给出评级，其中 82% 为“买入”，距目标价的上涨空间为 61% 。"
        },
        {
          "tag": "预测",
          "text": " 9家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 11% ，很受内资机构青睐。"
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
          "content": "11:52 企查查APP显示，近日，淮安新原邦科技有限公司成立，法定代表人为易欢，注册资本为3000万元，经营范围包含：电子专用材料制造；电子专用材料研发；电子专用材料销售；合成材料销售；新材料技术研发等。企查查股权穿透显示，该公司由新宙邦持股的深圳新源邦科技有限公司全资持股。（人民财讯）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "22:36 7月9日，多家A股上市公司披露2026年中期业绩预告。相关公司包括工业富联、紫金矿业、兆易创新、大族数控、大族激光、鼎龙股份、天赐材料、新宙邦、天华新能、三维通信、大连电瓷、美畅股份、全志科技、神火股份、西部矿业、财通证券、恩捷股份及飞龙股份。\n\n工业富联公告显示，预计上半年净利润为234亿元至244亿元，同比增长幅度在93%至101%之间，其中云服务商AI服务器营业收入同比增长超过230%。\n\n兆易创新公告称，预计上半年净利润约为69亿元，同比增长约1099%，主要得益于公司存储芯片产品实现量价齐升。",
          "tags": [
            "资讯"
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
      "valuation_history_from": "20210716",
      "current_price": 65.53,
      "price": 65.53,
      "ma5": 71.71,
      "ma10": 81.01,
      "ma20": 81.12,
      "dist_ma5_pct": -8.6,
      "dist_ma10_pct": -19.1,
      "dist_ma20_pct": -19.2,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9921,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.49,
        "pct_float": 2.58,
        "chg5_pct": -21.54,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300438.SZ",
      "fetch_time": "2026-07-16T11:40:53+0800",
      "name": "鹏辉能源",
      "pe": 55.5131,
      "pb": 5.6279,
      "ps_ttm": 2.1229,
      "pcf_ttm": 28.9218,
      "valuation_percentile": 58.08,
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
        "QFII重仓指数",
        "股权激励指数",
        "养老金指数",
        "锂电池指数",
        "储能指数",
        "固态电池指数",
        "钠离子电池指数",
        "动力电池指数",
        "预期提升指数",
        "TWS耳机指数",
        "ETC指数"
      ],
      "score_company": 8.3,
      "score_trend": 7.7,
      "score_value": 6.1,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 1278% ，利润成长性强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 14亿元 ，较上期增长 70% ，占2025年营收 12% ，在手订单充足。"
        },
        {
          "tag": "评级",
          "text": "近90天， 9家 机构给出评级，其中 78% 为“买入”，距目标价的上涨空间为 46% 。"
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
          "text": "近1年，股价涨幅超过A股市场 95% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月21日 至今陷入调整，资金有出逃可能。"
        },
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
          "content": "09:32 锂电池板块短线走低，鹏辉能源跌超10%，蔚蓝锂芯、德福科技、铜冠铜箔、诺德股份等跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "22:13 7月15日，多家A股上市公司披露2026年半年度业绩预告。涉及公司包括佰维存储、嘉元科技、江丰电子、大普微、金宏气体、华联控股、凯尔达、移为通信、泰和科技、思特威、孩子王及鹏辉能源。\n\n其中，佰维存储预计上半年净利润为70亿元至75亿元，同比增长幅度在3200%至3422%之间，公司表示业绩增长主要受AI算力需求增长及存储行业景气度提升影响。\n\n大普微预计上半年净利润为12亿元至13亿元，实现同比扭亏为盈。公司指出，全球AI技术发展带动了数据中心企业级存储需求的增长。",
          "tags": [
            "资讯"
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
      "valuation_history_from": "20210716",
      "current_price": 67.73,
      "price": 67.73,
      "ma5": 69.3,
      "ma10": 74.33,
      "ma20": 75.59,
      "dist_ma5_pct": -2.3,
      "dist_ma10_pct": -8.9,
      "dist_ma20_pct": -10.4,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9921,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 11.3,
        "pct_float": 4.05,
        "chg5_pct": 19.65,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "688502.SH",
      "fetch_time": "2026-07-16T11:40:55+0800",
      "name": "茂莱光学",
      "pe": 1501.0688,
      "pb": 23.6685,
      "ps_ttm": 38.1181,
      "pcf_ttm": 666.7685,
      "valuation_percentile": 96.4,
      "total_shares": 52800748,
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
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "可转债正股指数",
        "光刻机指数",
        "光学光电子精选指数"
      ],
      "score_company": 6.9,
      "score_trend": 7.7,
      "score_value": 3.3,
      "highlights": [
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 17% ，收入成长性较强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 116% ，净利润现金含量较高。"
        },
        {
          "tag": "订单",
          "text": "合同负债 1208万元 ，较上期增长 4.8% ，占2025年营收 1.7% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 6.1% ，较受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 96% 的股票，走势很强。"
        }
      ],
      "risks": [
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 29% ，扣非净利润占净利润 60% ，收益质量很低。"
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
          "content": "2026/07/10 ZHOU WEI(核心技术人员)减持 1.00万股 ，类型为 二级市场买卖 ，成交均价为 641元/股 ，套现 641万元 ，此次减持后的持股数为15.5万股",
          "tags": [
            "非控股股东减持"
          ]
        },
        {
          "content": "09:41 7月10日，半导体设备板块表现活跃。深科达实现20cm两连板，亚翔集成与旭光电子此前涨停，国林科技、茂莱光学、美埃科技及至纯科技等个股涨幅居前。\n\n行业消息方面，美光科技披露了投资计划，预计到2035年，其对美国本土的投资总额将增加至超过2500亿美元。该计划主要受人工智能领域对内存需求增长的驱动，美光科技目标是将美国产能占其DRAM总产量的比例提升至40%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:34 光刻机概念股盘初拉升，国林科技涨超10%，茂莱光学、旭光电子、美埃科技、赛微电子、晶方科技跟涨。相关ETF方面，科创半导体ETF华夏（588170）涨1.79%，成交额12.41亿元，半导体设备ETF广发（560780）涨2.67%，成交额1.46亿元。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "茂莱光学：中国国际金融股份有限公司关于南京茂莱光学科技股份有限公司开展外汇套期保值业务的核查意见",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 503181010.35,
      "revenue_yoy": 0.340525,
      "operating_profit": 49206815.16,
      "operating_profit_yoy": 0.948071,
      "net_profit": 45691406.04,
      "net_profit_yoy": 0.865669,
      "gross_profit": 240282354.69,
      "gross_profit_yoy": 0.329414,
      "cogs": 262898655.66,
      "gross_margin": 47.75,
      "pe_forward": null,
      "valuation_history_days": 326,
      "valuation_history_from": "20250310",
      "current_price": 612.01,
      "price": 612.01,
      "ma5": 615.62,
      "ma10": 603.75,
      "ma20": 534.99,
      "dist_ma5_pct": -0.6,
      "dist_ma10_pct": 1.4,
      "dist_ma20_pct": 14.4,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.84,
        "pct_float": 2.4,
        "chg5_pct": -10.46,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002821.SZ",
      "fetch_time": "2026-07-16T11:40:55+0800",
      "name": "凯莱英",
      "pe": 61.369,
      "pb": 3.8976,
      "ps_ttm": 9.831,
      "pcf_ttm": 45.8864,
      "valuation_percentile": 50.16,
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
        "宁组合",
        "外资企业指数",
        "高瓴资本指数",
        "合资企业指数",
        "创新药指数",
        "反内卷指数",
        "医药数智化指数",
        "医疗物资出口指数"
      ],
      "score_company": 9.2,
      "score_trend": 9.6,
      "score_value": 5.5,
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
          "text": " 9家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.0% ，较受外资机构青睐；公募基金持股 14% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 97% 的股票，收盘价接近 一年新高 ，走势很强。"
        },
        {
          "tag": "激励",
          "text": "2026年07月09日，公司发布股票激励计划，当日收涨 7.8% 。"
        }
      ],
      "risks": [
        {
          "tag": "评级",
          "text": "收盘价比机构一致预测目标价高 26% ，存在高估风险。"
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
          "content": "09:33股价达到 185.0 元，创近24个月新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "09:31 医疗服务板块直线拉升，大湖股份涨停，凯莱英、博济医药、奥浦迈、毕得医药、益诺思等纷纷走高。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "回购总金额不超过432万元，回购最高价不超过51.9元/股 （预案）",
          "tags": [
            "公司回购限售股"
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
      "valuation_history_from": "20210716",
      "current_price": 169.33,
      "price": 169.33,
      "ma5": 162.79,
      "ma10": 162.47,
      "ma20": 143.35,
      "dist_ma5_pct": 4.0,
      "dist_ma10_pct": 4.2,
      "dist_ma20_pct": 18.1,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.57,
        "pct_float": 1.7,
        "chg5_pct": 24.36,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "002947.SZ",
      "fetch_time": "2026-07-16T11:40:55+0800",
      "name": "恒铭达",
      "pe": 28.3434,
      "pb": 5.2409,
      "ps_ttm": 5.5768,
      "pcf_ttm": 27.3426,
      "valuation_percentile": 63.51,
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
        "贷款回购指数",
        "专精特新小巨人指数",
        "AI手机指数",
        "电子制造精选指数",
        "折叠屏指数"
      ],
      "score_company": 8.2,
      "score_trend": 6.6,
      "score_value": 4.8,
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
          "text": "近6月，股价涨幅超过A股市场 89% 的股票，走势较强。"
        },
        {
          "tag": "激励",
          "text": "2026年04月08日，公司发布股票激励计划，当日收涨 9.0% 。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月27日 至今陷入调整，资金有出逃可能。"
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
          "content": "恒铭达：北京市中伦律师事务所关于苏州恒铭达电子科技股份有限公司2026年第三次临时股东会的法律意见书",
          "tags": [
            "重要公告"
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
      "valuation_history_from": "20210716",
      "current_price": 65.52,
      "price": 65.52,
      "ma5": 70.62,
      "ma10": 72.72,
      "ma20": 79.11,
      "dist_ma5_pct": -7.2,
      "dist_ma10_pct": -9.9,
      "dist_ma20_pct": -17.2,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.39,
        "pct_float": 6.7,
        "chg5_pct": -3.14,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688469.SH",
      "fetch_time": "2026-07-16T11:40:55+0800",
      "name": "芯联集成-U",
      "pe": -132.8603,
      "pb": 5.0093,
      "ps_ttm": 7.7265,
      "pcf_ttm": 30.2019,
      "valuation_percentile": 87.84,
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
        "信创产业指数",
        "半导体产业指数",
        "数字经济指数",
        "芯片指数",
        "集成电路指数",
        "业绩预亏指数",
        "中芯国际产业链指数",
        "晶圆产业指数",
        "第三代半导体指数"
      ],
      "score_company": 6.3,
      "score_trend": 8.1,
      "score_value": 3.7,
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
          "content": "14:40 科创50指数尾盘跌超4%，晶合集成、华润微、芯联集成跌幅居前。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "芯联集成：芯联集成电路制造股份有限公司关于变更持续督导保荐代表人的公告",
          "tags": [
            "重要公告"
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
      "valuation_history_days": 288,
      "valuation_history_from": "20250512",
      "current_price": 8.82,
      "price": 8.82,
      "ma5": 9.5,
      "ma10": 9.72,
      "ma20": 8.71,
      "dist_ma5_pct": -7.2,
      "dist_ma10_pct": -9.3,
      "dist_ma20_pct": 1.3,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 18.24,
        "pct_float": 3.91,
        "chg5_pct": 6.59,
        "net5_repay_days": 0,
        "signal": "adding"
      }
    },
    {
      "code": "300870.SZ",
      "fetch_time": "2026-07-16T11:40:55+0800",
      "name": "欧陆通",
      "pe": 202.0825,
      "pb": 14.273,
      "ps_ttm": 7.9641,
      "pcf_ttm": 155.3887,
      "valuation_percentile": 95.89,
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
      "score_company": 8.2,
      "score_trend": 7.3,
      "score_value": 3.5,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年04月27日，业绩超预期引发股价大幅上涨，但目前股价已回落。"
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
          "content": "13:27 7月14日，数据中心电源板块在午后表现活跃。麦格米特在4个交易日内实现2个涨停，中恒电气、雄韬股份、欧陆通及新雷能等个股随之跟涨。\n\n中信证券发布研报指出，AI电源对功率器件的拉动作用预计将持续增强。随着HVDC与SST技术趋势的发展，相关领域的长期增量空间将逐步打开。预计本轮涨价趋势有望延续至2027年，相关厂商或将迎来收入快速增长与盈利能力修复的周期。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:41 7月10日，数据中心电源板块表现活跃。中恒电气股价实现两连板，麦格米特涨幅超过8%，雄韬股份、欧陆通以及科华数据等个股跟涨。\n\n中信证券发布研报指出，功率器件行业正受到二轮涨价周期确认与AI电源需求增长的双重影响。从中长期视角分析，AI电源对功率器件的拉动作用将持续增强。随着HVDC与SST技术趋势的发展，长期增量空间有望打开，预计本轮涨价趋势或将持续至2027年。",
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
      "valuation_history_days": 312,
      "valuation_history_from": "20220825",
      "current_price": 244.85,
      "price": 244.85,
      "ma5": 270.39,
      "ma10": 294.56,
      "ma20": 306.56,
      "dist_ma5_pct": -9.4,
      "dist_ma10_pct": -16.9,
      "dist_ma20_pct": -20.1,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9921,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 11.9,
        "pct_float": 3.13,
        "chg5_pct": -11.77,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688331.SH",
      "fetch_time": "2026-07-16T11:40:55+0800",
      "name": "荣昌生物",
      "pe": 61.9131,
      "pb": 20.3589,
      "ps_ttm": 23.6534,
      "pcf_ttm": 316.6437,
      "valuation_percentile": 59.63,
      "total_shares": 564477483,
      "industries": [
        {
          "name": "医药生物",
          "level": 1
        },
        {
          "name": "生物制品",
          "level": 2
        },
        {
          "name": "其他生物制品",
          "level": 3
        }
      ],
      "concepts": [
        "双创100指数",
        "贷款回购指数",
        "大消费指数",
        "股权激励指数",
        "创新药指数",
        "生物科技等权指数",
        "单克隆抗体指数",
        "生物制品精选指数"
      ],
      "score_company": 7.6,
      "score_trend": 9.1,
      "score_value": 5.7,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 其他生物制品 行业龙头企业。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 62% ，最新季度归母净利润同比增长 229% ，成长能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 9.2% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 2.7% ，较受外资机构青睐；公募基金持股 34% ，很受内资机构青睐。"
        },
        {
          "tag": "回购",
          "text": "近6月，公司累计回购 19万股 ，占总股本比例 0.03% ，金额合计 2000万元 。"
        }
      ],
      "risks": [
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 21% ，扣非净利润占净利润 22% ，收益质量很低。"
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
          "content": "13:04 7月9日午后，创新药概念板块出现拉升行情。\n\n华森制药股价直线封涨停。此外，盘龙药业、汉森制药、益方生物、马应龙以及荣昌生物等相关个股亦呈现快速冲高走势。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "13:04 7月9日午后，创新药概念板块出现拉升。华森制药股价触及涨停，盘龙药业、汉森制药、益方生物、马应龙以及荣昌生物等相关个股也呈现快速冲高走势。\n\n消息面上，国家卫生健康委、国家中医药局、国家疾控局于7月9日联合发布了2026年版国家基本药物目录。此次调整后，目录内药品数量由原先的685种增加至794种。其中，化学药品和生物制品涵盖476种，中成药包含318种，旨在进一步满足群众在疾病防治方面的基本用药需求。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "10:36股价达到 156.9 元，创历史新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "荣昌生物：H股公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1719833029.78,
      "revenue_yoy": 0.422673,
      "operating_profit": -537269154.58,
      "operating_profit_yoy": 0.491156,
      "net_profit": -550700575.38,
      "net_profit_yoy": 0.486012,
      "gross_profit": 1449239580.2,
      "gross_profit_yoy": 0.503159,
      "cogs": 270593449.58,
      "gross_margin": 84.27,
      "pe_forward": null,
      "valuation_history_days": 278,
      "valuation_history_from": "20240401",
      "current_price": 132.47,
      "price": 132.47,
      "ma5": 138.99,
      "ma10": 132.41,
      "ma20": 120.49,
      "dist_ma5_pct": -4.7,
      "dist_ma10_pct": 0.0,
      "dist_ma20_pct": 9.9,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.83,
        "pct_float": 2.14,
        "chg5_pct": -0.7,
        "net5_repay_days": 3,
        "signal": "neutral"
      }
    },
    {
      "code": "300304.SZ",
      "fetch_time": "2026-07-16T11:40:55+0800",
      "name": "云意电气",
      "pe": 24.7598,
      "pb": 3.2395,
      "ps_ttm": 4.6062,
      "pcf_ttm": 33.928,
      "valuation_percentile": 60.14,
      "total_shares": 878143718,
      "industries": [
        {
          "name": "汽车",
          "level": 1
        },
        {
          "name": "汽车零部件",
          "level": 2
        },
        {
          "name": "汽车电子电气系统",
          "level": 3
        }
      ],
      "concepts": [
        "人工智能+指数",
        "专精特新小巨人主题指数",
        "消费电子产业指数",
        "专精特新小巨人指数",
        "员工持股指数",
        "QFII重仓指数",
        "养老金指数",
        "智能驾驶指数",
        "汽配指数",
        "汽车配件精选指数",
        "汽车胎压监测指数"
      ],
      "score_company": 6.9,
      "score_trend": 6.2,
      "score_value": 4.9,
      "highlights": [
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 12% ，创造价值的能力较强。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 4.3% ，较受内资机构青睐。"
        },
        {
          "tag": "增持",
          "text": "近1月，控股股东和管理层累计实际增持 263万股 ，占总股本比例 0.30% ，金额合计 3279万元 。"
        },
        {
          "tag": "回购",
          "text": "近6月，公司累计回购 816万股 ，占总股本比例 0.93% ，金额合计 1.1亿元 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月29日大跌 -11.1% ，且成交额为近20日均值的 1.58倍 ，抛压很重。"
        },
        {
          "tag": "评级",
          "text": "近3月，没有机构发布研究报告，机构关注度低。"
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
          "content": "18:50 云意电气公告，董事兼副总经理张晶女士基于对公司未来发展的信心和长期投资价值的认同，计划自2026年1月23日起6个月内以集中竞价方式增持公司股份，增持金额不低于500万元且不高于1000万元。2026年1月23日至2026年7月10日，张晶女士以自有资金通过集中竞价交易方式累计增持公司股份36.6万股，占公司总股本0.04%，增持总金额为505.48万元，本次增持计划已实施完毕。增持后张晶女士直接持有公司股份36.6万股，占总股本0.04%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "云意电气：北京市康达律师事务所关于江苏云意电气股份有限公司实际控制人、董事长兼总经理增持公司股份专项核查的法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "2026/07/10 张晶(董事、高管)增持 1000股 ，类型为 竞价交易 ，成交均价为 14.8元/股 ，耗资 1.48万元 ，此次增持后的持股数为36.6万股",
          "tags": [
            "管理层增持"
          ]
        },
        {
          "content": "2026/07/10 付红玲(董事、高管)增持 1200股 ，类型为 竞价交易 ，成交均价为 14.8元/股 ，耗资 1.78万元 ，此次增持后的持股数为719万股",
          "tags": [
            "控股股东增持"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1666113048.81,
      "revenue_yoy": 0.070509,
      "operating_profit": 425290029.88,
      "operating_profit_yoy": 0.13893,
      "net_profit": 384191710.28,
      "net_profit_yoy": 0.157014,
      "gross_profit": 568909634.53,
      "gross_profit_yoy": 0.123259,
      "cogs": 1097203414.28,
      "gross_margin": 34.15,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210716",
      "current_price": 12.74,
      "price": 12.74,
      "ma5": 14.32,
      "ma10": 15.8,
      "ma20": 16.37,
      "dist_ma5_pct": -11.1,
      "dist_ma10_pct": -19.4,
      "dist_ma20_pct": -22.2,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.9921,
        "sizing": "tight"
      }
    }
  ],
  "active_positions": [],
  "position_prices": {},
  "missed_opportunity_prices": [
    {
      "code": "002821",
      "name": "凯莱英",
      "recommended_date": "2026-07-15",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 188.85,
      "return_pct": null
    },
    {
      "code": "688331",
      "name": "荣昌生物",
      "recommended_date": "2026-07-15",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 141.69,
      "return_pct": null
    },
    {
      "code": "002975",
      "name": "博杰股份",
      "recommended_date": "2026-07-15",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 104.64,
      "return_pct": null
    },
    {
      "code": "688652",
      "name": "京仪装备",
      "recommended_date": "2026-07-15",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 171.05,
      "return_pct": null
    },
    {
      "code": "002185",
      "name": "华天科技",
      "recommended_date": "2026-07-15",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 21.0,
      "return_pct": null
    },
    {
      "code": "688502",
      "name": "茂莱光学",
      "recommended_date": "2026-07-15",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 528.25,
      "return_pct": null
    },
    {
      "code": "688378",
      "name": "奥来德",
      "recommended_date": "2026-07-15",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 47.84,
      "return_pct": null
    },
    {
      "code": "688536",
      "name": "思瑞浦",
      "recommended_date": "2026-07-15",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 278.91,
      "return_pct": null
    },
    {
      "code": "300346",
      "name": "南大光电",
      "recommended_date": "2026-07-15",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 64.13,
      "return_pct": null
    },
    {
      "code": "000703",
      "name": "恒逸石化",
      "recommended_date": "2026-07-15",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 14.09,
      "return_pct": null
    },
    {
      "code": "002407",
      "name": "多氟多",
      "recommended_date": "2026-07-14",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 33.03,
      "return_pct": null
    },
    {
      "code": "601126",
      "name": "四方股份",
      "recommended_date": "2026-07-14",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 48.2,
      "return_pct": null
    },
    {
      "code": "688392",
      "name": "骄成超声",
      "recommended_date": "2026-07-14",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 184.24,
      "return_pct": null
    },
    {
      "code": "002810",
      "name": "山东赫达",
      "recommended_date": "2026-07-14",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 20.08,
      "return_pct": null
    },
    {
      "code": "688372",
      "name": "伟测科技",
      "recommended_date": "2026-07-14",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 143.88,
      "return_pct": null
    },
    {
      "code": "300236",
      "name": "上海新阳",
      "recommended_date": "2026-07-14",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 98.52,
      "return_pct": null
    },
    {
      "code": "002980",
      "name": "华盛昌",
      "recommended_date": "2026-07-14",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 112.35,
      "return_pct": null
    },
    {
      "code": "605376",
      "name": "博迁新材",
      "recommended_date": "2026-07-14",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 173.37,
      "return_pct": null
    },
    {
      "code": "ALL_67",
      "name": "全策略池67只",
      "recommended_date": "2026-07-13",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": null,
      "return_pct": null
    },
    {
      "code": "300726",
      "name": "宏达电子",
      "recommended_date": "2026-07-13",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 56.57,
      "return_pct": null
    }
  ],
  "iv_sentiment": {
    "date": "2026-07-16",
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
        "data_points_filtered": 219,
        "current_iv": 0.209,
        "is_live": false,
        "iv_high": 0.2245,
        "iv_low": 0.1137,
        "iv_high_raw": 0.2503,
        "iv_low_raw": 0.1137,
        "iv_rank": 0.86,
        "iv_rank_raw": 0.6977,
        "iv_percentile": 0.9361,
        "iv_percentile_raw": 0.9111,
        "outliers_removed": 6,
        "outlier_details": [
          {
            "date": "2025-08-25",
            "iv": 0.2287
          },
          {
            "date": "2025-08-26",
            "iv": 0.2272
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
          }
        ],
        "sigma_range": [
          0.1067,
          0.2254
        ],
        "name": "50ETF",
        "desc": "大盘蓝筹",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "510300",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 216,
        "current_iv": 0.2198,
        "is_live": false,
        "iv_high": 0.2448,
        "iv_low": 0.1201,
        "iv_high_raw": 0.2694,
        "iv_low_raw": 0.069,
        "iv_rank": 0.7994,
        "iv_rank_raw": 0.7525,
        "iv_percentile": 0.9259,
        "iv_percentile_raw": 0.8978,
        "outliers_removed": 9,
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
            "date": "2025-08-19",
            "iv": 0.2451
          },
          {
            "date": "2025-08-20",
            "iv": 0.255
          },
          {
            "date": "2025-08-25",
            "iv": 0.2476
          },
          {
            "date": "2025-08-28",
            "iv": 0.2471
          },
          {
            "date": "2026-02-02",
            "iv": 0.2467
          },
          {
            "date": "2026-04-16",
            "iv": 0.069
          },
          {
            "date": "2026-04-17",
            "iv": 0.099
          }
        ],
        "sigma_range": [
          0.1122,
          0.245
        ],
        "name": "300ETF",
        "desc": "沪深300",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "510500",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 215,
        "current_iv": 0.3374,
        "is_live": false,
        "iv_high": 0.3465,
        "iv_low": 0.194,
        "iv_high_raw": 0.3769,
        "iv_low_raw": 0.107,
        "iv_rank": 0.9405,
        "iv_rank_raw": 0.8537,
        "iv_percentile": 0.9442,
        "iv_percentile_raw": 0.9111,
        "outliers_removed": 10,
        "outlier_details": [
          {
            "date": "2025-08-18",
            "iv": 0.3616
          },
          {
            "date": "2025-08-20",
            "iv": 0.3523
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
            "date": "2025-09-05",
            "iv": 0.3575
          },
          {
            "date": "2025-10-17",
            "iv": 0.3519
          },
          {
            "date": "2026-02-02",
            "iv": 0.3531
          },
          {
            "date": "2026-03-23",
            "iv": 0.353
          },
          {
            "date": "2026-04-16",
            "iv": 0.128
          },
          {
            "date": "2026-04-17",
            "iv": 0.107
          }
        ],
        "sigma_range": [
          0.1791,
          0.3495
        ],
        "name": "500ETF",
        "desc": "中证500",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "588000",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 215,
        "current_iv": 0.6724,
        "is_live": false,
        "iv_high": 0.5861,
        "iv_low": 0.2467,
        "iv_high_raw": 0.6724,
        "iv_low_raw": 0.126,
        "iv_rank": 1.0,
        "iv_rank_raw": 1.0,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9956,
        "outliers_removed": 10,
        "outlier_details": [
          {
            "date": "2025-08-25",
            "iv": 0.6237
          },
          {
            "date": "2025-08-28",
            "iv": 0.6222
          },
          {
            "date": "2025-08-29",
            "iv": 0.6345
          },
          {
            "date": "2026-04-16",
            "iv": 0.145
          },
          {
            "date": "2026-04-17",
            "iv": 0.126
          },
          {
            "date": "2026-06-30",
            "iv": 0.6103
          },
          {
            "date": "2026-07-01",
            "iv": 0.6127
          },
          {
            "date": "2026-07-09",
            "iv": 0.6098
          },
          {
            "date": "2026-07-15",
            "iv": 0.6334
          },
          {
            "date": "2026-07-16",
            "iv": 0.6724
          }
        ],
        "sigma_range": [
          0.1749,
          0.5945
        ],
        "name": "科创50",
        "desc": "科创板",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159915",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 215,
        "current_iv": 0.4608,
        "is_live": false,
        "iv_high": 0.4628,
        "iv_low": 0.2082,
        "iv_high_raw": 0.5002,
        "iv_low_raw": 0.2082,
        "iv_rank": 0.9921,
        "iv_rank_raw": 0.865,
        "iv_percentile": 0.986,
        "iv_percentile_raw": 0.955,
        "outliers_removed": 7,
        "outlier_details": [
          {
            "date": "2025-08-29",
            "iv": 0.4704
          },
          {
            "date": "2025-09-05",
            "iv": 0.5002
          },
          {
            "date": "2025-09-16",
            "iv": 0.4678
          },
          {
            "date": "2025-09-17",
            "iv": 0.4913
          },
          {
            "date": "2025-09-18",
            "iv": 0.473
          },
          {
            "date": "2025-09-22",
            "iv": 0.4652
          },
          {
            "date": "2025-09-26",
            "iv": 0.472
          }
        ],
        "sigma_range": [
          0.1825,
          0.4639
        ],
        "name": "创业板ETF",
        "desc": "创业板",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159922",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 210,
        "current_iv": 0.35,
        "is_live": false,
        "iv_high": 0.3274,
        "iv_low": 0.1825,
        "iv_high_raw": 0.3669,
        "iv_low_raw": 0.1804,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.9096,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.973,
        "outliers_removed": 12,
        "outlier_details": [
          {
            "date": "2025-09-04",
            "iv": 0.3669
          },
          {
            "date": "2025-09-05",
            "iv": 0.344
          },
          {
            "date": "2025-09-17",
            "iv": 0.3356
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
            "date": "2025-09-22",
            "iv": 0.3397
          },
          {
            "date": "2025-09-23",
            "iv": 0.3495
          },
          {
            "date": "2025-10-17",
            "iv": 0.3461
          },
          {
            "date": "2025-12-22",
            "iv": 0.1804
          },
          {
            "date": "2026-02-02",
            "iv": 0.352
          },
          {
            "date": "2026-03-23",
            "iv": 0.361
          },
          {
            "date": "2026-07-16",
            "iv": 0.35
          }
        ],
        "sigma_range": [
          0.182,
          0.3341
        ],
        "name": "500ETF深",
        "desc": "深市中盘",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159919",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 212,
        "current_iv": 0.2256,
        "is_live": false,
        "iv_high": 0.2511,
        "iv_low": 0.1298,
        "iv_high_raw": 0.2815,
        "iv_low_raw": 0.1298,
        "iv_rank": 0.79,
        "iv_rank_raw": 0.6316,
        "iv_percentile": 0.9245,
        "iv_percentile_raw": 0.8829,
        "outliers_removed": 10,
        "outlier_details": [
          {
            "date": "2025-08-15",
            "iv": 0.2539
          },
          {
            "date": "2025-08-18",
            "iv": 0.2642
          },
          {
            "date": "2025-08-19",
            "iv": 0.2575
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
            "date": "2025-08-26",
            "iv": 0.2553
          },
          {
            "date": "2025-08-27",
            "iv": 0.2549
          },
          {
            "date": "2025-08-28",
            "iv": 0.2577
          },
          {
            "date": "2025-08-29",
            "iv": 0.2576
          },
          {
            "date": "2026-06-23",
            "iv": 0.2815
          }
        ],
        "sigma_range": [
          0.1165,
          0.2519
        ],
        "name": "300ETF深",
        "desc": "深市宽基",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159901",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 214,
        "current_iv": 0.3242,
        "is_live": false,
        "iv_high": 0.3242,
        "iv_low": 0.1682,
        "iv_high_raw": 0.3484,
        "iv_low_raw": 0.1682,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.8657,
        "iv_percentile": 0.9953,
        "iv_percentile_raw": 0.9595,
        "outliers_removed": 8,
        "outlier_details": [
          {
            "date": "2025-08-18",
            "iv": 0.3358
          },
          {
            "date": "2025-08-19",
            "iv": 0.3319
          },
          {
            "date": "2025-08-20",
            "iv": 0.3484
          },
          {
            "date": "2025-08-21",
            "iv": 0.327
          },
          {
            "date": "2025-08-29",
            "iv": 0.3406
          },
          {
            "date": "2026-06-23",
            "iv": 0.3391
          },
          {
            "date": "2026-07-02",
            "iv": 0.3346
          },
          {
            "date": "2026-07-13",
            "iv": 0.3275
          }
        ],
        "sigma_range": [
          0.1537,
          0.3263
        ],
        "name": "深100ETF",
        "desc": "深市蓝筹",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "588080",
        "lookback_days": 252,
        "data_points": 224,
        "data_points_filtered": 215,
        "current_iv": 0.6613,
        "is_live": false,
        "iv_high": 0.5904,
        "iv_low": 0.184,
        "iv_high_raw": 0.6613,
        "iv_low_raw": 0.184,
        "iv_rank": 1.0,
        "iv_rank_raw": 1.0,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9955,
        "outliers_removed": 9,
        "outlier_details": [
          {
            "date": "2025-08-25",
            "iv": 0.604
          },
          {
            "date": "2025-08-28",
            "iv": 0.5935
          },
          {
            "date": "2025-08-29",
            "iv": 0.6042
          },
          {
            "date": "2026-06-30",
            "iv": 0.6147
          },
          {
            "date": "2026-07-01",
            "iv": 0.6163
          },
          {
            "date": "2026-07-02",
            "iv": 0.5965
          },
          {
            "date": "2026-07-09",
            "iv": 0.6087
          },
          {
            "date": "2026-07-15",
            "iv": 0.6485
          },
          {
            "date": "2026-07-16",
            "iv": 0.6613
          }
        ],
        "sigma_range": [
          0.1787,
          0.5916
        ],
        "name": "科创板50",
        "desc": "科创板（备用代理）",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      }
    ],
    "overall_sentiment": {
      "signal": "极度恐慌",
      "avg_iv_rank": 0.9184,
      "avg_iv_percentile": 0.9584,
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
    "breadth_ratio": 1.5488,
    "up": 3282,
    "down": 2119,
    "positive_indices": [],
    "negative_indices": [
      "上证指数",
      "深证成指",
      "创业板指"
    ],
    "limit_ups": 50,
    "limit_downs": 7,
    "sizing_multiplier": 1.0,
    "hard_block": false,
    "reason": "Entry regime balanced: breadth 1.55:1, 0/3 major indices green, 50 limit-ups / 7 limit-downs. Allow normal sizing."
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
  "active_learnings": "## Active Rules (proven, hitRate ≥ 75%)\n- [h013] Strong breadth alone is not enough to force entries; without candidate RPS and MA-distance data, the correct momentum decision is to keep cash. (hitRate: 99%, n=124, confidence: 98%)\n- [h028] Today’s relative leaders are concentrated in communication equipment and adjacent tech hardware, while cyclicals/agri/resource laggards are being de-risked aggressively. (hitRate: 100%, n=41, confidence: 98%)\n- [h019] Bottom-list sectors should be treated as hard no-buy zones even when individual names still carry acceptable RPS readings. (hitRate: 100%, n=38, confidence: 98%)\n- [h023] Raising stops mechanically after +10% works well in weak tapes because it converts a fast winner into a low-risk hold without needing a fresh market call. (hitRate: 100%, n=36, confidence: 97%)\n- [h027] MA-distance discipline remains critical inside hot sectors: a hot sector does not override chase risk when dist_ma5_pct exceeds 6% or dist_ma10_pct exceeds 8%. (hitRate: 100%, n=37, confidence: 97%)\n- [h021] The MA-distance anti-chase rule is doing real work: several visually strong names fail because they are too far above short-term support. (hitRate: 98%, n=93, confidence: 97%)\n- [h017] Low-IV conditions around 16-22% IV rank do not justify freezing risk when breadth is 5.6:1; they argue for normal sizing but tighter discipline on chasing. (hitRate: 100%, n=25, confidence: 96%)\n\n## Working Hypotheses (testing, hitRate ≥ 65%)\n- [h024] Stop-proximity violations deserve proactive action before the hard stop is hit, especially in 科创板 names where gap risk can erase the remaining cushion quickly. (hitRate: 100%, n=5, confidence: 86%)\n",
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
