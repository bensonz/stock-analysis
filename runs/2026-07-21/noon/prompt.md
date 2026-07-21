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
  "date": "2026-07-21",
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
    "timestamp": "2026-07-21T11:40:45.373585",
    "indices": {
      "上证指数": {
        "code": "sh000001",
        "close": 3819.655,
        "change_pct": 0.62,
        "date": "2026-07-21"
      },
      "深证成指": {
        "code": "sz399001",
        "close": 14074.22,
        "change_pct": 3.41,
        "date": "2026-07-21"
      },
      "创业板指": {
        "code": "sz399006",
        "close": 3622.27,
        "change_pct": 5.2,
        "date": "2026-07-21"
      },
      "科创50": {
        "code": "sh000688",
        "close": 1837.943,
        "change_pct": 6.94,
        "date": "2026-07-21"
      }
    },
    "breadth": {
      "up": 2601,
      "down": 2807,
      "flat": 118,
      "total": 5526,
      "distribution": {
        "f10": 24,
        "f7_10": 79,
        "f4_7": 260,
        "f2_4": 749,
        "f0_2": 1695,
        "f0": 118,
        "r0_2": 1268,
        "r2_4": 638,
        "r4_7": 435,
        "r7_10": 214,
        "r10": 46
      }
    },
    "sectors": {
      "top5": [
        {
          "板块名称": "半导体",
          "涨跌幅": 8.43
        },
        {
          "板块名称": "电子化学品Ⅱ",
          "涨跌幅": 8.43
        },
        {
          "板块名称": "玻璃玻纤",
          "涨跌幅": 7.28
        },
        {
          "板块名称": "通信设备",
          "涨跌幅": 6.77
        },
        {
          "板块名称": "元件",
          "涨跌幅": 6.15
        }
      ],
      "bottom5": [
        {
          "板块名称": "油气开采Ⅱ",
          "涨跌幅": -3.76
        },
        {
          "板块名称": "煤炭开采",
          "涨跌幅": -3.32
        },
        {
          "板块名称": "油服工程",
          "涨跌幅": -3.31
        },
        {
          "板块名称": "国有大型银行Ⅱ",
          "涨跌幅": -2.74
        },
        {
          "板块名称": "炼化及贸易",
          "涨跌幅": -2.7
        }
      ]
    }
  },
  "strategy_pool": {
    "source": "cheesefortune_intersection",
    "total_stocks": 52,
    "stocks": [
      {
        "code": "002980",
        "code_full": "002980.SZ",
        "name": "华盛昌",
        "source_date": "2026/04/30",
        "highlights_count": 5,
        "market_cap": 164.7222,
        "pe": 6.2,
        "risks_count": 2,
        "rps20": 82.62,
        "rps60": 99.96,
        "rps120": 99.58,
        "rps250": 97.43,
        "ma10": 101.51,
        "vcp_quality": null,
        "ma5": 97.66,
        "ma20": 109.13,
        "dist_ma5_pct": -1.1,
        "dist_ma10_pct": -4.8,
        "dist_ma20_pct": -11.5
      },
      {
        "code": "605376",
        "code_full": "605376.SH",
        "name": "博迁新材",
        "source_date": "2026/07/11",
        "highlights_count": 5,
        "market_cap": 351.7997,
        "pe": 5.6,
        "risks_count": 1,
        "rps20": 97.57,
        "rps60": 98.17,
        "rps120": 99.52,
        "rps250": 99.05,
        "ma10": 209.6,
        "vcp_quality": null,
        "ma5": 176.58,
        "ma20": 215.54,
        "dist_ma5_pct": -15.4,
        "dist_ma10_pct": -28.7,
        "dist_ma20_pct": -30.7
      },
      {
        "code": "301396",
        "code_full": "301396.SZ",
        "name": "宏景科技",
        "source_date": "2026/05/13",
        "highlights_count": 4,
        "market_cap": 426.4963,
        "pe": 3.6,
        "risks_count": 1,
        "rps20": 68.95,
        "rps60": 99.03,
        "rps120": 99.5,
        "rps250": 96.11,
        "ma10": 251.44,
        "vcp_quality": null,
        "ma5": 223.42,
        "ma20": 254.91,
        "dist_ma5_pct": -13.8,
        "dist_ma10_pct": -23.4,
        "dist_ma20_pct": -24.5
      },
      {
        "code": "688630",
        "code_full": "688630.SH",
        "name": "芯碁微装",
        "source_date": "2026/03/12",
        "highlights_count": 6,
        "market_cap": 503.9776,
        "pe": 5.3,
        "risks_count": 0,
        "rps20": 99.09,
        "rps60": 99.01,
        "rps120": 99.38,
        "rps250": 99.13,
        "ma10": 456.39,
        "vcp_quality": null,
        "ma5": 417.97,
        "ma20": 460.9,
        "dist_ma5_pct": -13.9,
        "dist_ma10_pct": -21.2,
        "dist_ma20_pct": -21.9
      },
      {
        "code": "301362",
        "code_full": "301362.SZ",
        "name": "民爆光电",
        "source_date": "2026/06/16",
        "highlights_count": 4,
        "market_cap": 155.3581,
        "pe": 2.9,
        "risks_count": 1,
        "rps20": 32.57,
        "rps60": 98.53,
        "rps120": 99.19,
        "rps250": 97.26,
        "ma10": 147.05,
        "vcp_quality": null,
        "ma5": 139.31,
        "ma20": 173.75,
        "dist_ma5_pct": -10.4,
        "dist_ma10_pct": -15.1,
        "dist_ma20_pct": -28.2
      },
      {
        "code": "000811",
        "code_full": "000811.SZ",
        "name": "冰轮环境",
        "source_date": "2026/06/12",
        "highlights_count": 4,
        "market_cap": 398.9761,
        "pe": 28.1,
        "risks_count": 2,
        "rps20": 99.37,
        "rps60": 99.46,
        "rps120": 99.11,
        "rps250": 97.81,
        "ma10": 51.34,
        "vcp_quality": null,
        "ma5": 48.15,
        "ma20": 50.31,
        "dist_ma5_pct": -10.1,
        "dist_ma10_pct": -15.7,
        "dist_ma20_pct": -14.0
      },
      {
        "code": "688257",
        "code_full": "688257.SH",
        "name": "新锐股份",
        "source_date": "2026/07/14",
        "highlights_count": 4,
        "market_cap": 207.6159,
        "pe": 4.7,
        "risks_count": 1,
        "rps20": 84.49,
        "rps60": 95.98,
        "rps120": 98.99,
        "rps250": 97.57,
        "ma10": 90.98,
        "vcp_quality": null,
        "ma5": 78.03,
        "ma20": 94.2,
        "dist_ma5_pct": -12.8,
        "dist_ma10_pct": -25.2,
        "dist_ma20_pct": -27.7
      },
      {
        "code": "300285",
        "code_full": "300285.SZ",
        "name": "国瓷材料",
        "source_date": "2026/07/08",
        "highlights_count": 7,
        "market_cap": 497.7265,
        "pe": 14.5,
        "risks_count": 2,
        "rps20": 99.57,
        "rps60": 98.91,
        "rps120": 98.83,
        "rps250": 98.09,
        "ma10": 75.6,
        "vcp_quality": null,
        "ma5": 64.84,
        "ma20": 81.7,
        "dist_ma5_pct": -12.7,
        "dist_ma10_pct": -25.1,
        "dist_ma20_pct": -30.7
      },
      {
        "code": "300806",
        "code_full": "300806.SZ",
        "name": "斯迪克",
        "source_date": "2026/04/28",
        "highlights_count": 6,
        "market_cap": 243.377,
        "pe": 6.6,
        "risks_count": 2,
        "rps20": 89.15,
        "rps60": 94.87,
        "rps120": 98.49,
        "rps250": 98.82,
        "ma10": 82.68,
        "vcp_quality": null,
        "ma5": 73.86,
        "ma20": 91.93,
        "dist_ma5_pct": -13.5,
        "dist_ma10_pct": -22.7,
        "dist_ma20_pct": -30.5
      },
      {
        "code": "688300",
        "code_full": "688300.SH",
        "name": "联瑞新材",
        "source_date": "2026/05/06",
        "highlights_count": 6,
        "market_cap": 294.0853,
        "pe": 6.6,
        "risks_count": 0,
        "rps20": 98.56,
        "rps60": 99.36,
        "rps120": 98.47,
        "rps250": 95.88,
        "ma10": 182.89,
        "vcp_quality": null,
        "ma5": 163.78,
        "ma20": 207.32,
        "dist_ma5_pct": -13.9,
        "dist_ma10_pct": -22.9,
        "dist_ma20_pct": -32.0
      },
      {
        "code": "600869",
        "code_full": "600869.SH",
        "name": "远东股份",
        "source_date": "2026/06/29",
        "highlights_count": 5,
        "market_cap": 340.6706,
        "pe": 31.4,
        "risks_count": 5,
        "rps20": 92.54,
        "rps60": 97.08,
        "rps120": 98.45,
        "rps250": 98.6,
        "ma10": 23.4,
        "vcp_quality": null,
        "ma5": 19.8,
        "ma20": 28.96,
        "dist_ma5_pct": -13.8,
        "dist_ma10_pct": -27.1,
        "dist_ma20_pct": -41.1
      },
      {
        "code": "688037",
        "code_full": "688037.SH",
        "name": "芯源微",
        "source_date": "2026/07/10",
        "highlights_count": 4,
        "market_cap": 602.7774,
        "pe": 6.6,
        "risks_count": 2,
        "rps20": 98.38,
        "rps60": 96.46,
        "rps120": 98.27,
        "rps250": 97.04,
        "ma10": 376.85,
        "vcp_quality": null,
        "ma5": 360.59,
        "ma20": 338.48,
        "dist_ma5_pct": -13.9,
        "dist_ma10_pct": -17.6,
        "dist_ma20_pct": -8.2
      },
      {
        "code": "001389",
        "code_full": "001389.SZ",
        "name": "广合科技",
        "source_date": "2026/07/20",
        "highlights_count": 6,
        "market_cap": 749.0549,
        "pe": 2.3,
        "risks_count": 1,
        "rps20": 90.47,
        "rps60": 96.8,
        "rps120": 97.76,
        "rps250": 97.3,
        "ma10": 184.3,
        "vcp_quality": null,
        "ma5": 185.31,
        "ma20": 196.55,
        "dist_ma5_pct": -5.0,
        "dist_ma10_pct": -4.5,
        "dist_ma20_pct": -10.4
      },
      {
        "code": "688017",
        "code_full": "688017.SH",
        "name": "绿的谐波",
        "source_date": "2026/07/08",
        "highlights_count": 4,
        "market_cap": 551.6037,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 96.98,
        "rps60": 96.82,
        "rps120": 97.66,
        "rps250": 94.3,
        "ma10": 410.3,
        "vcp_quality": null,
        "ma5": 373.73,
        "ma20": 396.25,
        "dist_ma5_pct": -12.7,
        "dist_ma10_pct": -20.5,
        "dist_ma20_pct": -17.7
      },
      {
        "code": "003031",
        "code_full": "003031.SZ",
        "name": "中瓷电子",
        "source_date": "2026/07/01",
        "highlights_count": 4,
        "market_cap": 451.0529,
        "pe": 5.5,
        "risks_count": 2,
        "rps20": 81.83,
        "rps60": 96.62,
        "rps120": 97.54,
        "rps250": 95.11,
        "ma10": 138.37,
        "vcp_quality": null,
        "ma5": 125.64,
        "ma20": 154.11,
        "dist_ma5_pct": -14.6,
        "dist_ma10_pct": -22.5,
        "dist_ma20_pct": -30.4
      },
      {
        "code": "688200",
        "code_full": "688200.SH",
        "name": "华峰测控",
        "source_date": "2026/07/17",
        "highlights_count": 5,
        "market_cap": 708.1504,
        "pe": 6.4,
        "risks_count": 0,
        "rps20": 94.08,
        "rps60": 95.26,
        "rps120": 97.42,
        "rps250": 95.18,
        "ma10": 472.94,
        "vcp_quality": null,
        "ma5": 449.89,
        "ma20": 433.06,
        "dist_ma5_pct": -17.1,
        "dist_ma10_pct": -21.2,
        "dist_ma20_pct": -13.9
      },
      {
        "code": "688531",
        "code_full": "688531.SH",
        "name": "日联科技",
        "source_date": "2026/06/16",
        "highlights_count": 6,
        "market_cap": 195.4008,
        "pe": 3.3,
        "risks_count": 0,
        "rps20": 89.66,
        "rps60": 98.35,
        "rps120": 97.4,
        "rps250": 92.9,
        "ma10": 166.13,
        "vcp_quality": null,
        "ma5": 152.82,
        "ma20": 169.82,
        "dist_ma5_pct": -13.4,
        "dist_ma10_pct": -20.4,
        "dist_ma20_pct": -22.1
      },
      {
        "code": "688150",
        "code_full": "688150.SH",
        "name": "莱特光电",
        "source_date": "2026/04/16",
        "highlights_count": 4,
        "market_cap": 167.414,
        "pe": 4.3,
        "risks_count": 2,
        "rps20": 78.44,
        "rps60": 97.55,
        "rps120": 97.24,
        "rps250": 92.58,
        "ma10": 56.77,
        "vcp_quality": null,
        "ma5": 50.39,
        "ma20": 55.95,
        "dist_ma5_pct": -5.7,
        "dist_ma10_pct": -16.3,
        "dist_ma20_pct": -15.1
      },
      {
        "code": "688629",
        "code_full": "688629.SH",
        "name": "华丰科技",
        "source_date": "2026/07/15",
        "highlights_count": 5,
        "market_cap": 671.8522,
        "pe": 3.0,
        "risks_count": 1,
        "rps20": 96.78,
        "rps60": 97.21,
        "rps120": 97.22,
        "rps250": 95.64,
        "ma10": 184.6,
        "vcp_quality": null,
        "ma5": 173.45,
        "ma20": 168.1,
        "dist_ma5_pct": -18.3,
        "dist_ma10_pct": -23.3,
        "dist_ma20_pct": -15.7
      },
      {
        "code": "688127",
        "code_full": "688127.SH",
        "name": "蓝特光学",
        "source_date": "2026/06/20",
        "highlights_count": 6,
        "market_cap": 237.9372,
        "pe": 5.8,
        "risks_count": 2,
        "rps20": 65.24,
        "rps60": 95.22,
        "rps120": 96.98,
        "rps250": 95.91,
        "ma10": 78.1,
        "vcp_quality": null,
        "ma5": 72.03,
        "ma20": 82.98,
        "dist_ma5_pct": -13.4,
        "dist_ma10_pct": -20.1,
        "dist_ma20_pct": -24.8
      },
      {
        "code": "301182",
        "code_full": "301182.SZ",
        "name": "凯旺科技",
        "source_date": "2026/04/24",
        "highlights_count": 4,
        "market_cap": 54.6471,
        "pe": 4.5,
        "risks_count": 3,
        "rps20": 92.03,
        "rps60": 97.51,
        "rps120": 96.96,
        "rps250": 93.88,
        "ma10": 88.22,
        "vcp_quality": null,
        "ma5": 77.74,
        "ma20": 93.15,
        "dist_ma5_pct": -15.1,
        "dist_ma10_pct": -25.2,
        "dist_ma20_pct": -29.1
      },
      {
        "code": "002937",
        "code_full": "002937.SZ",
        "name": "兴瑞科技",
        "source_date": "2026/04/23",
        "highlights_count": 4,
        "market_cap": 108.3913,
        "pe": 7.8,
        "risks_count": 1,
        "rps20": 95.66,
        "rps60": 96.08,
        "rps120": 96.29,
        "rps250": 92.6,
        "ma10": 41.96,
        "vcp_quality": null,
        "ma5": 40.27,
        "ma20": 41.97,
        "dist_ma5_pct": -5.4,
        "dist_ma10_pct": -9.2,
        "dist_ma20_pct": -9.2
      },
      {
        "code": "002957",
        "code_full": "002957.SZ",
        "name": "科瑞技术",
        "source_date": "2026/07/15",
        "highlights_count": 4,
        "market_cap": 137.6283,
        "pe": 6.9,
        "risks_count": 3,
        "rps20": 69.17,
        "rps60": 96.34,
        "rps120": 95.75,
        "rps250": 94.85,
        "ma10": 43.93,
        "vcp_quality": null,
        "ma5": 41.42,
        "ma20": 49.39,
        "dist_ma5_pct": -12.1,
        "dist_ma10_pct": -17.1,
        "dist_ma20_pct": -26.3
      },
      {
        "code": "000703",
        "code_full": "000703.SZ",
        "name": "恒逸石化",
        "source_date": "2026/06/08",
        "highlights_count": 5,
        "market_cap": 577.438,
        "pe": 15.1,
        "risks_count": 3,
        "rps20": 81.87,
        "rps60": 87.21,
        "rps120": 95.65,
        "rps250": 92.03,
        "ma10": 14.17,
        "vcp_quality": null,
        "ma5": 14.2,
        "ma20": 14.24,
        "dist_ma5_pct": 3.2,
        "dist_ma10_pct": 3.4,
        "dist_ma20_pct": 2.9
      },
      {
        "code": "300323",
        "code_full": "300323.SZ",
        "name": "华灿光电",
        "source_date": "2026/04/29",
        "highlights_count": 4,
        "market_cap": 175.7708,
        "pe": 14.1,
        "risks_count": 2,
        "rps20": 86.82,
        "rps60": 97.0,
        "rps120": 95.38,
        "rps250": 92.4,
        "ma10": 15.32,
        "vcp_quality": null,
        "ma5": 13.36,
        "ma20": 16.57,
        "dist_ma5_pct": -12.9,
        "dist_ma10_pct": -24.1,
        "dist_ma20_pct": -29.8
      },
      {
        "code": "688777",
        "code_full": "688777.SH",
        "name": "中控技术",
        "source_date": "2026/07/13",
        "highlights_count": 5,
        "market_cap": 719.9825,
        "pe": 5.6,
        "risks_count": 2,
        "rps20": 93.73,
        "rps60": 86.07,
        "rps120": 94.96,
        "rps250": 88.99,
        "ma10": 101.14,
        "vcp_quality": null,
        "ma5": 94.05,
        "ma20": 107.1,
        "dist_ma5_pct": -7.0,
        "dist_ma10_pct": -13.5,
        "dist_ma20_pct": -18.3
      },
      {
        "code": "301536",
        "code_full": "301536.SZ",
        "name": "星宸科技",
        "source_date": "2026/04/20",
        "highlights_count": 4,
        "market_cap": 449.7593,
        "pe": 2.3,
        "risks_count": 0,
        "rps20": 96.76,
        "rps60": 94.93,
        "rps120": 94.8,
        "rps250": 87.92,
        "ma10": 112.51,
        "vcp_quality": null,
        "ma5": 105.83,
        "ma20": 113.28,
        "dist_ma5_pct": -13.2,
        "dist_ma10_pct": -18.4,
        "dist_ma20_pct": -18.9
      },
      {
        "code": "688376",
        "code_full": "688376.SH",
        "name": "美埃科技",
        "source_date": "2026/04/28",
        "highlights_count": 5,
        "market_cap": 86.5883,
        "pe": 3.6,
        "risks_count": 1,
        "rps20": 95.8,
        "rps60": 91.54,
        "rps120": 94.7,
        "rps250": 92.32,
        "ma10": 92.77,
        "vcp_quality": null,
        "ma5": 80.56,
        "ma20": 89.24,
        "dist_ma5_pct": -14.2,
        "dist_ma10_pct": -25.5,
        "dist_ma20_pct": -22.5
      },
      {
        "code": "688378",
        "code_full": "688378.SH",
        "name": "奥来德",
        "source_date": "2026/06/06",
        "highlights_count": 5,
        "market_cap": 99.9951,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 91.32,
        "rps60": 92.0,
        "rps120": 93.93,
        "rps250": 94.08,
        "ma10": 52.52,
        "vcp_quality": null,
        "ma5": 47.92,
        "ma20": 52.89,
        "dist_ma5_pct": -11.9,
        "dist_ma10_pct": -19.6,
        "dist_ma20_pct": -20.2
      },
      {
        "code": "600961",
        "code_full": "600961.SH",
        "name": "株冶集团",
        "source_date": "2026/07/20",
        "highlights_count": 4,
        "market_cap": 230.9895,
        "pe": 21.9,
        "risks_count": 1,
        "rps20": 88.22,
        "rps60": 89.08,
        "rps120": 93.73,
        "rps250": 93.25,
        "ma10": 27.12,
        "vcp_quality": null,
        "ma5": 24.45,
        "ma20": 28.49,
        "dist_ma5_pct": -9.5,
        "dist_ma10_pct": -18.4,
        "dist_ma20_pct": -22.4
      },
      {
        "code": "688392",
        "code_full": "688392.SH",
        "name": "骄成超声",
        "source_date": "2026/04/22",
        "highlights_count": 6,
        "market_cap": 162.5938,
        "pe": 3.8,
        "risks_count": 1,
        "rps20": 97.24,
        "rps60": 93.47,
        "rps120": 93.69,
        "rps250": 97.32,
        "ma10": 204.63,
        "vcp_quality": null,
        "ma5": 185.13,
        "ma20": 188.51,
        "dist_ma5_pct": -16.4,
        "dist_ma10_pct": -24.4,
        "dist_ma20_pct": -17.9
      },
      {
        "code": "688536",
        "code_full": "688536.SH",
        "name": "思瑞浦",
        "source_date": "2026/04/01",
        "highlights_count": 6,
        "market_cap": 316.1929,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 90.2,
        "rps60": 94.71,
        "rps120": 93.49,
        "rps250": 86.48,
        "ma10": 313.35,
        "vcp_quality": null,
        "ma5": 282.66,
        "ma20": 318.83,
        "dist_ma5_pct": -14.4,
        "dist_ma10_pct": -22.7,
        "dist_ma20_pct": -24.1
      },
      {
        "code": "601126",
        "code_full": "601126.SH",
        "name": "四方股份",
        "source_date": "2026/03/12",
        "highlights_count": 7,
        "market_cap": 344.9057,
        "pe": 15.5,
        "risks_count": 1,
        "rps20": 12.23,
        "rps60": 92.1,
        "rps120": 93.29,
        "rps250": 95.36,
        "ma10": 53.77,
        "vcp_quality": null,
        "ma5": 49.19,
        "ma20": 61.22,
        "dist_ma5_pct": -9.5,
        "dist_ma10_pct": -17.2,
        "dist_ma20_pct": -27.3
      },
      {
        "code": "300373",
        "code_full": "300373.SZ",
        "name": "扬杰科技",
        "source_date": "2026/07/21",
        "highlights_count": 4,
        "market_cap": 472.1692,
        "pe": 12.4,
        "risks_count": 1,
        "rps20": 97.85,
        "rps60": 93.0,
        "rps120": 93.15,
        "rps250": 92.86,
        "ma10": 118.96,
        "vcp_quality": null,
        "ma5": 105.94,
        "ma20": 123.89,
        "dist_ma5_pct": -12.2,
        "dist_ma10_pct": -21.8,
        "dist_ma20_pct": -24.9
      },
      {
        "code": "688401",
        "code_full": "688401.SH",
        "name": "路维光电",
        "source_date": "2026/04/21",
        "highlights_count": 4,
        "market_cap": 121.7842,
        "pe": 3.9,
        "risks_count": 0,
        "rps20": 93.41,
        "rps60": 94.43,
        "rps120": 93.03,
        "rps250": 91.63,
        "ma10": 83.96,
        "vcp_quality": null,
        "ma5": 75.97,
        "ma20": 82.79,
        "dist_ma5_pct": -14.2,
        "dist_ma10_pct": -22.3,
        "dist_ma20_pct": -21.2
      },
      {
        "code": "002821",
        "code_full": "002821.SZ",
        "name": "凯莱英",
        "source_date": "2026/04/01",
        "highlights_count": 8,
        "market_cap": 586.3052,
        "pe": 9.6,
        "risks_count": 1,
        "rps20": 98.03,
        "rps60": 95.38,
        "rps120": 92.87,
        "rps250": 91.2,
        "ma10": 168.8,
        "vcp_quality": null,
        "ma5": 176.34,
        "ma20": 153.77,
        "dist_ma5_pct": -8.1,
        "dist_ma10_pct": -4.0,
        "dist_ma20_pct": 5.3
      },
      {
        "code": "002810",
        "code_full": "002810.SZ",
        "name": "山东赫达",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 64.2682,
        "pe": 9.9,
        "risks_count": 2,
        "rps20": 55.85,
        "rps60": 87.6,
        "rps120": 92.02,
        "rps250": 87.01,
        "ma10": 21.81,
        "vcp_quality": null,
        "ma5": 20.02,
        "ma20": 23.17,
        "dist_ma5_pct": -5.3,
        "dist_ma10_pct": -13.1,
        "dist_ma20_pct": -18.2
      },
      {
        "code": "688502",
        "code_full": "688502.SH",
        "name": "茂莱光学",
        "source_date": "2026/06/07",
        "highlights_count": 4,
        "market_cap": 192.1525,
        "pe": 3.3,
        "risks_count": 2,
        "rps20": 93.1,
        "rps60": 93.93,
        "rps120": 91.7,
        "rps250": 87.65,
        "ma10": 585.97,
        "vcp_quality": null,
        "ma5": 546.35,
        "ma20": 551.54,
        "dist_ma5_pct": -16.7,
        "dist_ma10_pct": -22.4,
        "dist_ma20_pct": -17.5
      },
      {
        "code": "002192",
        "code_full": "002192.SZ",
        "name": "融捷股份",
        "source_date": "2026/07/20",
        "highlights_count": 4,
        "market_cap": 145.5887,
        "pe": 18.6,
        "risks_count": 5,
        "rps20": 53.03,
        "rps60": 92.36,
        "rps120": 91.66,
        "rps250": 94.22,
        "ma10": 78.15,
        "vcp_quality": null,
        "ma5": 67.28,
        "ma20": 83.67,
        "dist_ma5_pct": -7.4,
        "dist_ma10_pct": -20.3,
        "dist_ma20_pct": -25.5
      },
      {
        "code": "601958",
        "code_full": "601958.SH",
        "name": "金钼股份",
        "source_date": "2026/07/03",
        "highlights_count": 7,
        "market_cap": 657.9046,
        "pe": 18.2,
        "risks_count": 1,
        "rps20": 90.93,
        "rps60": 85.81,
        "rps120": 91.33,
        "rps250": 91.73,
        "ma10": 23.21,
        "vcp_quality": null,
        "ma5": 21.64,
        "ma20": 25.39,
        "dist_ma5_pct": -8.7,
        "dist_ma10_pct": -14.9,
        "dist_ma20_pct": -22.2
      },
      {
        "code": "002975",
        "code_full": "002975.SZ",
        "name": "博杰股份",
        "source_date": "2026/06/16",
        "highlights_count": 5,
        "market_cap": 170.022,
        "pe": 6.4,
        "risks_count": 1,
        "rps20": 77.47,
        "rps60": 93.22,
        "rps120": 91.17,
        "rps250": 97.34,
        "ma10": 114.92,
        "vcp_quality": null,
        "ma5": 108.78,
        "ma20": 126.3,
        "dist_ma5_pct": -16.6,
        "dist_ma10_pct": -21.0,
        "dist_ma20_pct": -28.1
      },
      {
        "code": "688331",
        "code_full": "688331.SH",
        "name": "荣昌生物",
        "source_date": "2026/07/06",
        "highlights_count": 5,
        "market_cap": 694.9282,
        "pe": 4.3,
        "risks_count": 1,
        "rps20": 93.81,
        "rps60": 90.77,
        "rps120": 89.78,
        "rps250": 93.55,
        "ma10": 136.39,
        "vcp_quality": null,
        "ma5": 132.6,
        "ma20": 125.46,
        "dist_ma5_pct": -12.5,
        "dist_ma10_pct": -14.9,
        "dist_ma20_pct": -7.5
      },
      {
        "code": "300684",
        "code_full": "300684.SZ",
        "name": "中石科技",
        "source_date": "2026/03/12",
        "highlights_count": 5,
        "market_cap": 144.1538,
        "pe": 8.5,
        "risks_count": 2,
        "rps20": 91.2,
        "rps60": 86.39,
        "rps120": 89.66,
        "rps250": 93.9,
        "ma10": 67.13,
        "vcp_quality": null,
        "ma5": 64.34,
        "ma20": 62.64,
        "dist_ma5_pct": -15.3,
        "dist_ma10_pct": -18.8,
        "dist_ma20_pct": -13.0
      },
      {
        "code": "300475",
        "code_full": "300475.SZ",
        "name": "香农芯创",
        "source_date": "2026/07/20",
        "highlights_count": 5,
        "market_cap": 721.5918,
        "pe": 11.1,
        "risks_count": 2,
        "rps20": 96.94,
        "rps60": 94.25,
        "rps120": 89.22,
        "rps250": 99.57,
        "ma10": 235.82,
        "vcp_quality": null,
        "ma5": 209.84,
        "ma20": 247.32,
        "dist_ma5_pct": -17.0,
        "dist_ma10_pct": -26.2,
        "dist_ma20_pct": -29.6
      },
      {
        "code": "605020",
        "code_full": "605020.SH",
        "name": "永和股份",
        "source_date": "2026/06/13",
        "highlights_count": 6,
        "market_cap": 161.1122,
        "pe": 5.0,
        "risks_count": 1,
        "rps20": 95.88,
        "rps60": 91.86,
        "rps120": 89.12,
        "rps250": 85.16,
        "ma10": 39.38,
        "vcp_quality": null,
        "ma5": 35.4,
        "ma20": 37.64,
        "dist_ma5_pct": -4.6,
        "dist_ma10_pct": -14.2,
        "dist_ma20_pct": -10.3
      },
      {
        "code": "300037",
        "code_full": "300037.SZ",
        "name": "新宙邦",
        "source_date": "2026/03/12",
        "highlights_count": 7,
        "market_cap": 429.6399,
        "pe": 16.5,
        "risks_count": 1,
        "rps20": 91.08,
        "rps60": 93.67,
        "rps120": 88.63,
        "rps250": 92.28,
        "ma10": 75.12,
        "vcp_quality": null,
        "ma5": 66.01,
        "ma20": 80.14,
        "dist_ma5_pct": -8.5,
        "dist_ma10_pct": -19.6,
        "dist_ma20_pct": -24.6
      },
      {
        "code": "002947",
        "code_full": "002947.SZ",
        "name": "恒铭达",
        "source_date": "2026/03/12",
        "highlights_count": 4,
        "market_cap": 137.0976,
        "pe": 7.4,
        "risks_count": 1,
        "rps20": 22.31,
        "rps60": 93.53,
        "rps120": 88.21,
        "rps250": 90.15,
        "ma10": 68.65,
        "vcp_quality": null,
        "ma5": 63.48,
        "ma20": 75.85,
        "dist_ma5_pct": -10.9,
        "dist_ma10_pct": -17.7,
        "dist_ma20_pct": -25.5
      },
      {
        "code": "300870",
        "code_full": "300870.SZ",
        "name": "欧陆通",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 283.1538,
        "pe": 5.9,
        "risks_count": 1,
        "rps20": 14.24,
        "rps60": 85.18,
        "rps120": 87.59,
        "rps250": 92.7,
        "ma10": 267.23,
        "vcp_quality": null,
        "ma5": 242.1,
        "ma20": 300.94,
        "dist_ma5_pct": -16.0,
        "dist_ma10_pct": -23.9,
        "dist_ma20_pct": -32.4
      },
      {
        "code": "300438",
        "code_full": "300438.SZ",
        "name": "鹏辉能源",
        "source_date": "2026/04/14",
        "highlights_count": 5,
        "market_cap": 291.9391,
        "pe": 11.2,
        "risks_count": 2,
        "rps20": 51.9,
        "rps60": 93.77,
        "rps120": 87.02,
        "rps250": 94.89,
        "ma10": 69.51,
        "vcp_quality": null,
        "ma5": 66.02,
        "ma20": 74.74,
        "dist_ma5_pct": -5.8,
        "dist_ma10_pct": -10.5,
        "dist_ma20_pct": -16.8
      },
      {
        "code": "002407",
        "code_full": "002407.SZ",
        "name": "多氟多",
        "source_date": "2026/05/06",
        "highlights_count": 4,
        "market_cap": 334.7496,
        "pe": 16.1,
        "risks_count": 2,
        "rps20": 92.23,
        "rps60": 92.64,
        "rps120": 86.94,
        "rps250": 96.55,
        "ma10": 39.11,
        "vcp_quality": null,
        "ma5": 34.02,
        "ma20": 42.49,
        "dist_ma5_pct": -8.2,
        "dist_ma10_pct": -20.1,
        "dist_ma20_pct": -26.5
      },
      {
        "code": "603127",
        "code_full": "603127.SH",
        "name": "昭衍新药",
        "source_date": "2026/07/08",
        "highlights_count": 6,
        "market_cap": 352.1937,
        "pe": 8.9,
        "risks_count": 3,
        "rps20": 94.06,
        "rps60": 86.75,
        "rps120": 86.13,
        "rps250": 94.24,
        "ma10": 44.48,
        "vcp_quality": null,
        "ma5": 48.27,
        "ma20": 40.12,
        "dist_ma5_pct": -0.7,
        "dist_ma10_pct": 7.7,
        "dist_ma20_pct": 19.5
      },
      {
        "code": "002056",
        "code_full": "002056.SZ",
        "name": "横店东磁",
        "source_date": "2026/05/28",
        "highlights_count": 5,
        "market_cap": 352.0205,
        "pe": 19.9,
        "risks_count": 1,
        "rps20": 96.17,
        "rps60": 90.89,
        "rps120": 85.17,
        "rps250": 89.01,
        "ma10": 27.23,
        "vcp_quality": null,
        "ma5": 24.93,
        "ma20": 28.32,
        "dist_ma5_pct": -3.6,
        "dist_ma10_pct": -11.7,
        "dist_ma20_pct": -15.1
      }
    ]
  },
  "enriched_candidates": [
    {
      "code": "688777.SH",
      "fetch_time": "2026-07-21T11:40:45+0800",
      "name": "中控技术",
      "pe": 186.3994,
      "pb": 7.5217,
      "ps_ttm": 9.2613,
      "pcf_ttm": 273.8173,
      "valuation_percentile": 74.32,
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
      "score_company": 8.3,
      "score_trend": 8.0,
      "score_value": 4.7,
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
          "text": " 15家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
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
          "content": "17:37 2026世界人工智能大会（WAIC）期间，中控技术展示自主运行工厂AOP等工业AI产品。据介绍，公司自主运行工厂AOP以时间序列大模型TPT为工厂智慧大脑，以通用控制系统UCS为工业神经中枢，构建起完整的“识别-评估-决策-执行”智能闭环，让工厂实现了从“被动应对”到“主动防御”的转变。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "中控技术：中控技术股份有限公司关于调整暨聘任部分高级管理人员的公告",
          "tags": [
            "重要公告"
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
      "valuation_history_days": 294,
      "valuation_history_from": "20221125",
      "current_price": 87.5,
      "price": 87.5,
      "ma5": 94.05,
      "ma10": 101.14,
      "ma20": 107.1,
      "dist_ma5_pct": -7.0,
      "dist_ma10_pct": -13.5,
      "dist_ma20_pct": -18.3,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 30.0,
        "pct_float": 4.19,
        "chg5_pct": -6.03,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301536.SZ",
      "fetch_time": "2026-07-21T11:40:45+0800",
      "name": "星宸科技",
      "pe": 105.1095,
      "pb": 16.198,
      "ps_ttm": 15.204,
      "pcf_ttm": 169.9527,
      "valuation_percentile": 88.24,
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
        "具身智能指数",
        "半导体精选指数",
        "预期提升指数",
        "人工智能指数",
        "模拟芯片指数",
        "安防监控指数"
      ],
      "score_company": 8.2,
      "score_trend": 8.6,
      "score_value": 4.0,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 831% ，利润成长性强。"
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
          "content": "预计2026/08/27发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-27"
        },
        {
          "content": "15:00 今天大涨的原因可能是公司公告2026年上半年净利润预计同比暴增583.72%-650.42%，市场预期其视觉AI系统级芯片（AISoC）销量与毛利率显著提升，盈利能力大幅改善。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价开盘上涨 20.00% ，股价收盘涨幅 16.11%",
          "tags": [
            "股价上涨"
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
      "valuation_history_days": 75,
      "valuation_history_from": "20260330",
      "current_price": 91.85,
      "price": 91.85,
      "ma5": 105.83,
      "ma10": 112.51,
      "ma20": 113.28,
      "dist_ma5_pct": -13.2,
      "dist_ma10_pct": -18.4,
      "dist_ma20_pct": -18.9,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.01,
        "pct_float": 4.52,
        "chg5_pct": 16.15,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "688376.SH",
      "fetch_time": "2026-07-21T11:40:45+0800",
      "name": "美埃科技",
      "pe": 85.2649,
      "pb": 4.8783,
      "ps_ttm": 4.5661,
      "pcf_ttm": 29.0169,
      "valuation_percentile": 84.57,
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
      "score_company": 7.3,
      "score_trend": 6.6,
      "score_value": 3.8,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年04月28日，业绩超预期引发股价大幅上涨，但目前股价已回落。"
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
      "valuation_history_days": 403,
      "valuation_history_from": "20241118",
      "current_price": 69.13,
      "price": 69.13,
      "ma5": 80.56,
      "ma10": 92.77,
      "ma20": 89.24,
      "dist_ma5_pct": -14.2,
      "dist_ma10_pct": -25.5,
      "dist_ma20_pct": -22.5,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 2.09,
        "pct_float": 2.41,
        "chg5_pct": -22.36,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688378.SH",
      "fetch_time": "2026-07-21T11:40:45+0800",
      "name": "奥来德",
      "pe": 80.9349,
      "pb": 5.125,
      "ps_ttm": 15.5938,
      "pcf_ttm": 32.9238,
      "valuation_percentile": 85.73,
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
      "score_trend": 6.4,
      "score_value": 4.1,
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
          "tag": "评级",
          "text": "近90天， 7家 机构给出评级，其中 86% 为“买入”，距目标价的上涨空间为 82% 。"
        },
        {
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
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
      "valuation_history_days": 312,
      "valuation_history_from": "20220905",
      "current_price": 42.23,
      "price": 42.23,
      "ma5": 47.92,
      "ma10": 52.52,
      "ma20": 52.89,
      "dist_ma5_pct": -11.9,
      "dist_ma10_pct": -19.6,
      "dist_ma20_pct": -20.2,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.26,
        "pct_float": 5.71,
        "chg5_pct": 2.55,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "600961.SH",
      "fetch_time": "2026-07-21T11:40:45+0800",
      "name": "株冶集团",
      "pe": 12.1131,
      "pb": 4.7749,
      "ps_ttm": 0.9868,
      "pcf_ttm": 8.752,
      "valuation_percentile": 59.19,
      "total_shares": 1072872703,
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
          "name": "铅锌",
          "level": 3
        }
      ],
      "concepts": [
        "专精特新小巨人主题指数",
        "QFII重仓指数",
        "有色金属指数",
        "锌电池指数",
        "铅锌矿指数",
        "钴矿指数",
        "央企有色指数",
        "磷化铟指数",
        "蓄电池指数"
      ],
      "score_company": 7.1,
      "score_trend": 6.9,
      "score_value": 5.8,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 145% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 32% ，投入资本回报率为 17% ，盈利能力很强。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 11% ，很受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 93% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "分红",
          "text": "近5年，从未实施现金分红，为一毛不拔的铁公鸡。"
        }
      ],
      "events": [
        {
          "content": "2026/09/08解禁3.21亿股，占总股本29.93%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-08"
        },
        {
          "content": "预计2026/08/19发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-19"
        },
        {
          "content": "10:05 贵金属板块走弱，招金黄金跌超7%，晓程科技、西部黄金、四川黄金、株冶集团等跟跌。",
          "tags": [
            "快讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 16048295428.98,
      "revenue_yoy": 0.115375,
      "operating_profit": 1079119649.21,
      "operating_profit_yoy": 0.517862,
      "net_profit": 856623442.95,
      "net_profit_yoy": 0.438565,
      "gross_profit": 1980019317.39,
      "gross_profit_yoy": 0.51115,
      "cogs": 14068276111.59,
      "gross_margin": 12.34,
      "pe_forward": null,
      "valuation_history_days": 301,
      "valuation_history_from": "20210721",
      "current_price": 22.12,
      "price": 22.12,
      "ma5": 24.45,
      "ma10": 27.12,
      "ma20": 28.49,
      "dist_ma5_pct": -9.5,
      "dist_ma10_pct": -18.4,
      "dist_ma20_pct": -22.4,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.47,
        "pct_float": 5.85,
        "chg5_pct": -6.86,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688392.SH",
      "fetch_time": "2026-07-21T11:40:45+0800",
      "name": "骄成超声",
      "pe": 128.3003,
      "pb": 10.0892,
      "ps_ttm": 22.4379,
      "pcf_ttm": 145.7983,
      "valuation_percentile": 78.62,
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
      "score_company": 7.6,
      "score_trend": 7.1,
      "score_value": 4.4,
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
          "content": "14:22 锂电专用设备板块重挫，龙鑫智能跌超18%，骄成超声、星云股份、杭可科技、利元亨等跟跌。",
          "tags": [
            "快讯"
          ]
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
      "valuation_history_days": 433,
      "valuation_history_from": "20240927",
      "current_price": 154.8,
      "price": 154.8,
      "ma5": 185.13,
      "ma10": 204.63,
      "ma20": 188.51,
      "dist_ma5_pct": -16.4,
      "dist_ma10_pct": -24.4,
      "dist_ma20_pct": -17.9,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.89,
        "pct_float": 3.01,
        "chg5_pct": -32.29,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688536.SH",
      "fetch_time": "2026-07-21T11:40:45+0800",
      "name": "思瑞浦",
      "pe": 129.1578,
      "pb": 5.3543,
      "ps_ttm": 14.0124,
      "pcf_ttm": 106.5166,
      "valuation_percentile": 35.54,
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
        "股权激励指数",
        "AIPC指数",
        "智能家居指数",
        "模拟芯片指数",
        "苏州工业园区指数"
      ],
      "score_company": 8.4,
      "score_trend": 7.3,
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
          "content": "思瑞浦：上海兰迪律师事务所关于思瑞浦微电子科技（苏州）股份有限公司2026年限制性股票激励计划（草案）的法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "思瑞浦：国浩律师（上海）事务所关于思瑞浦微电子科技（苏州）股份有限公司2026年第二次临时股东会之法律意见书",
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
      "valuation_history_days": 302,
      "valuation_history_from": "20220922",
      "current_price": 242.08,
      "price": 242.08,
      "ma5": 282.66,
      "ma10": 313.35,
      "ma20": 318.83,
      "dist_ma5_pct": -14.4,
      "dist_ma10_pct": -22.7,
      "dist_ma20_pct": -24.1,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.57,
        "pct_float": 3.4,
        "chg5_pct": -9.12,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "601126.SH",
      "fetch_time": "2026-07-21T11:40:45+0800",
      "name": "四方股份",
      "pe": 42.2018,
      "pb": 7.9244,
      "ps_ttm": 4.2489,
      "pcf_ttm": 34.4167,
      "valuation_percentile": 95.43,
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
        "限售解禁指数",
        "即将解禁指数",
        "特高压指数",
        "华为鲲鹏指数",
        "智能电网指数",
        "电气自动化设备精选指数",
        "高低压设备精选指数",
        "虚拟电厂指数",
        "泛在电力物联网指数"
      ],
      "score_company": 9.4,
      "score_trend": 5.3,
      "score_value": 3.6,
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
      "valuation_history_from": "20210721",
      "current_price": 44.5,
      "price": 44.5,
      "ma5": 49.19,
      "ma10": 53.77,
      "ma20": 61.22,
      "dist_ma5_pct": -9.5,
      "dist_ma10_pct": -17.2,
      "dist_ma20_pct": -27.3,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 20.51,
        "pct_float": 6.0,
        "chg5_pct": -11.45,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300373.SZ",
      "fetch_time": "2026-07-21T11:40:47+0800",
      "name": "扬杰科技",
      "pe": 38.1792,
      "pb": 5.4292,
      "ps_ttm": 6.8125,
      "pcf_ttm": 32.3782,
      "valuation_percentile": 52.65,
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
        "IGBT指数",
        "汽车芯片指数"
      ],
      "score_company": 8.2,
      "score_trend": 7.1,
      "score_value": 5.6,
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
          "tag": "产能",
          "text": "在建工程占总资产 12% ，未来产能扩张后，营收有望进一步增长。"
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
        },
        {
          "content": "16:22 扬杰科技公告，预计2026年上半年净利润为7.22亿元~8.42亿元，比上年同期增长20.00%~40.00%。2026年上半年，功率半导体行业受益于AI服务器、新能源汽车、光储等领域需求爆发，叠加8英寸成熟制程产能紧缺，呈现景气度上行、量价齐升的发展态势。报告期内，公司聚焦主业，积极落实产品领先战略，通过持续研发投入完善高附加值产品矩阵，实现营业收入同比增长约30%。",
          "tags": [
            "快讯"
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
      "valuation_history_from": "20210721",
      "current_price": 93.07,
      "price": 93.07,
      "ma5": 105.94,
      "ma10": 118.96,
      "ma20": 123.89,
      "dist_ma5_pct": -12.2,
      "dist_ma10_pct": -21.8,
      "dist_ma20_pct": -24.9,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 16.87,
        "pct_float": 3.58,
        "chg5_pct": -12.48,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688401.SH",
      "fetch_time": "2026-07-21T11:40:47+0800",
      "name": "路维光电",
      "pe": 50.9994,
      "pb": 5.3411,
      "ps_ttm": 11.315,
      "pcf_ttm": 46.8683,
      "valuation_percentile": 69.44,
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
        "专精特新小巨人指数",
        "半导体精选指数",
        "可转债正股指数",
        "IPO现场检查指数"
      ],
      "score_company": 7.6,
      "score_trend": 7.3,
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
          "content": "路维光电：深圳市路维光电股份有限公司2026年度向特定对象发行股票上市公告书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "路维光电：国信证券股份有限公司关于深圳市路维光电股份有限公司2026年度向特定对象发行A股股票的上市保荐书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "路维光电：路维光电关于因向特定对象发行股票调整“路维转债”转股价格暨转股停复牌的公告",
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
      "valuation_history_days": 461,
      "valuation_history_from": "20240819",
      "current_price": 65.21,
      "price": 65.21,
      "ma5": 75.97,
      "ma10": 83.96,
      "ma20": 82.79,
      "dist_ma5_pct": -14.2,
      "dist_ma10_pct": -22.3,
      "dist_ma20_pct": -21.2,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.77,
        "pct_float": 5.03,
        "chg5_pct": -12.37,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002821.SZ",
      "fetch_time": "2026-07-21T11:40:47+0800",
      "name": "凯莱英",
      "pe": 53.7256,
      "pb": 3.4122,
      "ps_ttm": 8.6066,
      "pcf_ttm": 40.1713,
      "valuation_percentile": 42.59,
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
        "自主可控指数",
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "RCEP指数",
        "大消费指数",
        "银发经济指数",
        "宁组合",
        "外资企业指数",
        "高瓴资本指数",
        "创新药指数",
        "合资企业指数",
        "反内卷指数",
        "医药数智化指数",
        "医疗物资出口指数"
      ],
      "score_company": 9.2,
      "score_trend": 8.1,
      "score_value": 6.0,
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
          "text": " 8家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.0% ，较受外资机构青睐；公募基金持股 14% ，很受内资机构青睐。"
        },
        {
          "tag": "激励",
          "text": "2026年07月09日，公司发布股票激励计划，当日收涨 7.8% 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月16日大跌 -8.05% ，且成交额为近20日均值的 1.7倍 ，抛压很重。"
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
          "content": "09:49 7月17日早盘，CRO概念板块出现震荡调整走势，其中实验动物相关个股跌幅居前。\n\n昭衍新药股价跌停，凯莱英盘中触及跌停。此外，药康生物、百奥赛图、泓博医药、睿智医药以及普蕊斯等个股跌幅均超过10%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:33股价达到 185.0 元，创近24个月新高",
          "tags": [
            "股价新高"
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
      "valuation_history_from": "20210721",
      "current_price": 161.99,
      "price": 161.99,
      "ma5": 176.34,
      "ma10": 168.8,
      "ma20": 153.77,
      "dist_ma5_pct": -8.1,
      "dist_ma10_pct": -4.0,
      "dist_ma20_pct": 5.3,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.38,
        "pct_float": 1.82,
        "chg5_pct": 3.49,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "002810.SZ",
      "fetch_time": "2026-07-21T11:40:47+0800",
      "name": "山东赫达",
      "pe": 32.2398,
      "pb": 2.9724,
      "ps_ttm": 3.1464,
      "pcf_ttm": 13.5224,
      "valuation_percentile": 34.04,
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
      "score_company": 8.3,
      "score_trend": 4.7,
      "score_value": 7.2,
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
          "content": "山东赫达：北京市齐致（济南）律师事务所关于山东赫达第三期股权激励计划调整股票期权行权价格及限制性股票回购价格的法律意见书",
          "tags": [
            "重要公告"
          ]
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
      "valuation_history_from": "20210721",
      "current_price": 18.95,
      "price": 18.95,
      "ma5": 20.02,
      "ma10": 21.81,
      "ma20": 23.17,
      "dist_ma5_pct": -5.3,
      "dist_ma10_pct": -13.1,
      "dist_ma20_pct": -18.2,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 2.05,
        "pct_float": 3.46,
        "chg5_pct": -3.91,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "688502.SH",
      "fetch_time": "2026-07-21T11:40:47+0800",
      "name": "茂莱光学",
      "pe": 1130.9073,
      "pb": 17.8318,
      "ps_ttm": 28.7182,
      "pcf_ttm": 502.3443,
      "valuation_percentile": 67.75,
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
      "score_company": 6.7,
      "score_trend": 5.4,
      "score_value": 4.8,
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
          "tag": "公募",
          "text": "公募基金持股 6.1% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月20日大跌 -20% ，股价跌停，抛压很重。"
        },
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
          "content": "于2026-07-17接待1位投资者调研。",
          "tags": [
            "机构调研"
          ]
        },
        {
          "content": "于2026-07-16接待8位投资者调研。",
          "tags": [
            "机构调研"
          ]
        },
        {
          "content": "2026/07/10 ZHOU WEI(核心技术人员)减持 1.00万股 ，类型为 二级市场买卖 ，成交均价为 641元/股 ，套现 641万元 ，此次减持后的持股数为15.5万股",
          "tags": [
            "非控股股东减持"
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
      "valuation_history_days": 329,
      "valuation_history_from": "20250310",
      "current_price": 454.9,
      "price": 454.9,
      "ma5": 546.35,
      "ma10": 585.97,
      "ma20": 551.54,
      "dist_ma5_pct": -16.7,
      "dist_ma10_pct": -22.4,
      "dist_ma20_pct": -17.5,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.9,
        "pct_float": 2.55,
        "chg5_pct": -28.75,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002192.SZ",
      "fetch_time": "2026-07-21T11:40:47+0800",
      "name": "融捷股份",
      "pe": 28.0162,
      "pb": 3.9384,
      "ps_ttm": 13.406,
      "pcf_ttm": 79.3988,
      "valuation_percentile": 21.21,
      "total_shares": 259655203,
      "industries": [
        {
          "name": "有色金属",
          "level": 1
        },
        {
          "name": "能源金属",
          "level": 2
        },
        {
          "name": "锂",
          "level": 3
        }
      ],
      "concepts": [
        "QFII重仓指数",
        "锂电池指数",
        "万得预增指数",
        "锂矿指数",
        "ATL电池指数"
      ],
      "score_company": 6.1,
      "score_trend": 4.2,
      "score_value": 7.7,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 1004% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 22% ，投入资本回报率为 23% ，盈利能力很强。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 112% ，销售收入现金含量较强。"
        },
        {
          "tag": "回购",
          "text": "公司公告自2026年07月21日起，拟回购不超过 1.0亿元 ，回购价格不超过 73元/股 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月08日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月07日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "评级",
          "text": "近6月，没有机构发布研究报告，机构关注度低。"
        },
        {
          "tag": "板块",
          "text": "近3月， 锂 板块疲软，走势弱于其他 98.8% 的板块。"
        },
        {
          "tag": "波动",
          "text": "近20天，日均换手率 11% ，短线资金追逐，波动风险较高。"
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
          "content": "回购总金额不超过1.00亿元，回购最高价不超过73.0元/股 （预案）",
          "tags": [
            "公司回购流通股"
          ]
        },
        {
          "content": "融捷股份：关于增加2026年度日常关联交易预计的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "19:22 融捷股份公告，拟使用不超过1亿元回购公司股份，回购价格不超过73元/股。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "10:43 7月20日，锂矿概念板块出现震荡回落走势。\n\n个股方面，天齐锂业盘中触及跌停。此外，融捷股份、盛新锂能、永杉锂业、赣锋锂业以及永兴材料等相关个股均出现不同程度的下跌。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 509588946.16,
      "revenue_yoy": 0.262115,
      "operating_profit": 172499892.32,
      "operating_profit_yoy": -0.12786,
      "net_profit": 139599016.27,
      "net_profit_yoy": -0.203315,
      "gross_profit": 233695202,
      "gross_profit_yoy": 0.258972,
      "cogs": 275893744.16,
      "gross_margin": 45.86,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20210721",
      "current_price": 62.3,
      "price": 62.3,
      "ma5": 67.28,
      "ma10": 78.15,
      "ma20": 83.67,
      "dist_ma5_pct": -7.4,
      "dist_ma10_pct": -20.3,
      "dist_ma20_pct": -25.5,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 12.98,
        "pct_float": 8.94,
        "chg5_pct": -7.65,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "601958.SH",
      "fetch_time": "2026-07-21T11:40:47+0800",
      "name": "金钼股份",
      "pe": 19.9894,
      "pb": 3.4095,
      "ps_ttm": 4.5911,
      "pcf_ttm": 31.2258,
      "valuation_percentile": 83.03,
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
      "score_trend": 7.6,
      "score_value": 4.2,
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
          "text": "近1年，股价涨幅超过A股市场 94% 的股票，走势较强。"
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
      "valuation_history_from": "20210721",
      "current_price": 19.76,
      "price": 19.76,
      "ma5": 21.64,
      "ma10": 23.21,
      "ma20": 25.39,
      "dist_ma5_pct": -8.7,
      "dist_ma10_pct": -14.9,
      "dist_ma20_pct": -22.2,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 11.38,
        "pct_float": 1.73,
        "chg5_pct": -6.76,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "002975.SZ",
      "fetch_time": "2026-07-21T11:40:47+0800",
      "name": "博杰股份",
      "pe": 74.5642,
      "pb": 7.3783,
      "ps_ttm": 8.2779,
      "pcf_ttm": 220.2423,
      "valuation_percentile": 71.82,
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
        "玻璃基板指数",
        "MLCC指数",
        "磷化铟指数"
      ],
      "score_company": 8.1,
      "score_trend": 7.2,
      "score_value": 4.6,
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
      "valuation_history_days": 270,
      "valuation_history_from": "20220207",
      "current_price": 90.77,
      "price": 90.77,
      "ma5": 108.78,
      "ma10": 114.92,
      "ma20": 126.3,
      "dist_ma5_pct": -16.6,
      "dist_ma10_pct": -21.0,
      "dist_ma20_pct": -28.1,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      }
    },
    {
      "code": "688331.SH",
      "fetch_time": "2026-07-21T11:40:49+0800",
      "name": "荣昌生物",
      "pe": 54.5592,
      "pb": 17.9408,
      "ps_ttm": 20.8439,
      "pcf_ttm": 279.0332,
      "valuation_percentile": 50.03,
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
      "score_company": 7.7,
      "score_trend": 8.2,
      "score_value": 6.4,
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
          "text": "公司公告自2026年07月20日起，拟回购不超过 5000万元 ，回购价格不超过 149元/股 。"
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
          "content": "19:19 7月20日，医药板块出现修复行情。港股通创新药ETF（520880）与港股通医疗ETF（159137）分别上涨4.17%和3.27%；A股药ETF（562050）与医疗ETF（512170）分别上涨2.5%。个股方面，映恩生物-B相关产品拟纳入突破性疗法，股价盘中冲高；荣昌生物拟回购股份，股价上涨9.84%；艾力斯半年利润增长，股价上涨11.09%；恒瑞医药披露累计回购进展，股价上涨4.47%。近期，多家公募机构通过权益变动增持百奥赛图-B、三生制药、石药集团、科伦博泰生物等创新药龙头。长江证券研报指出，创新药产业景气度提升，核心品种商业化及全球化进展显著，具备低位成长资产属性。\n基金管理人提示，ETF基金费率详见法律文件。文中提及的指数成份股仅作展示，不构成投资建议。中证制药指数与恒生港股通创新药精选指数历史收益及波动率各异，过往业绩不预示未来表现。相关基金风险等级及适宜投资者类型需参考基金法律文件，投资人须对自主投资行为负责。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "18:28 7月20日，A股市场呈现分化行情，沪综指收红，资金流向石化、煤炭、电力等高股息板块，而AI、半导体等科技赛道回调。近期，中国国新、中国诚通等国家队资金增持核心资产，多家券商及中国铝业等央企宣布回购增持计划。业内分析认为，市场回调主要受地缘政治及全球科技股联动调整影响，中长期上涨逻辑未变。\n7月19日及20日，中国国新与中国诚通宣布增持央企及科技类股票。此外，华安证券、国联民生、荣昌生物、世运电路、建龙微纳等多家上市公司发布回购计划，中国铝业、中国中车、国电南瑞、中煤能源、国投电力等央企亦披露增持或回购安排。证监会拟召开座谈会听取市场意见。中信证券研报指出，指数行情处于休整至新一轮行情的酝酿阶段，投资主线集中于央国企核心资产与科技赛道。\n摩根士丹利、高盛、渣打、瑞银等机构对AI产业前景持积极观点，认为AI正从概念走向收入兑现，且政策支持力度持续。海通国际首席经济学家张忆东表示，AI浪潮周期尚未结束。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "公司发布回购公告，股价盘中上涨 8.27% ，股价收盘涨幅 6.12%",
          "tags": [
            "股价上涨"
          ]
        },
        {
          "content": "回购总金额不超过5000万元，回购最高价不超过149元/股 （预案）",
          "tags": [
            "公司回购流通股"
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
      "valuation_history_days": 279,
      "valuation_history_from": "20240401",
      "current_price": 116.01,
      "price": 116.01,
      "ma5": 132.6,
      "ma10": 136.39,
      "ma20": 125.46,
      "dist_ma5_pct": -12.5,
      "dist_ma10_pct": -14.9,
      "dist_ma20_pct": -7.5,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.73,
        "pct_float": 2.22,
        "chg5_pct": -8.48,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300684.SZ",
      "fetch_time": "2026-07-21T11:40:49+0800",
      "name": "中石科技",
      "pe": 44.0112,
      "pb": 7.4803,
      "ps_ttm": 8.0188,
      "pcf_ttm": 37.7064,
      "valuation_percentile": 64.65,
      "total_shares": 299509223,
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
        "华为平台指数",
        "股权激励指数",
        "苹果指数",
        "液冷服务器指数"
      ],
      "score_company": 8.3,
      "score_trend": 6.8,
      "score_value": 4.7,
      "highlights": [
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 11% ，投入资本回报率为 12% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 138% ，净利润现金含量很高。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 2.4% ，现金分红极高。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 4.1% ，很受外资机构青睐；公募基金持股 7.2% ，很受内资机构青睐。"
        },
        {
          "tag": "回购",
          "text": "公司公告自2026年07月20日起，拟回购不超过 6000万元 ，回购价格不超过 90元/股 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月07日大跌 -6.76% ，且成交额为近20日均值的 2.46倍 ，抛压很重。"
        },
        {
          "tag": "波动",
          "text": "2026年07月06日，换手率 23% ，短线资金追逐，波动风险较高。"
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
          "content": "回购总金额不超过6000万元，回购最高价不超过90.0元/股 （预案）",
          "tags": [
            "公司回购流通股"
          ]
        },
        {
          "content": "2026/07/06解禁40.40万股，占总股本0.13%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-07-06"
        }
      ],
      "report_period": "20250930",
      "revenue": 1298271497.36,
      "revenue_yoy": 0.184543,
      "operating_profit": 285123778.28,
      "operating_profit_yoy": 0.868577,
      "net_profit": 251710320.5,
      "net_profit_yoy": 0.917729,
      "gross_profit": 440321826.14,
      "gross_profit_yoy": 0.305961,
      "cogs": 857949671.22,
      "gross_margin": 33.92,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210721",
      "current_price": 54.5,
      "price": 54.5,
      "ma5": 64.34,
      "ma10": 67.13,
      "ma20": 62.64,
      "dist_ma5_pct": -15.3,
      "dist_ma10_pct": -18.8,
      "dist_ma20_pct": -13.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 2.49,
        "pct_float": 2.53,
        "chg5_pct": 126.25,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "300475.SZ",
      "fetch_time": "2026-07-21T11:40:49+0800",
      "name": "香农芯创",
      "pe": 41.9821,
      "pb": 15.9112,
      "ps_ttm": 1.524,
      "pcf_ttm": 18.8605,
      "valuation_percentile": 60.03,
      "total_shares": 469541767,
      "industries": [
        {
          "name": "电子",
          "level": 1
        },
        {
          "name": "其他电子Ⅱ",
          "level": 2
        },
        {
          "name": "其他电子Ⅲ",
          "level": 3
        }
      ],
      "concepts": [
        "科技龙头指数",
        "双创100指数",
        "出海贸易指数",
        "股权激励指数",
        "英伟达产业链指数",
        "万得预增指数",
        "长鑫存储指数",
        "股权转让指数",
        "HBM指数",
        "其他电子精选指数"
      ],
      "score_company": 8.7,
      "score_trend": 6.4,
      "score_value": 5.4,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 其他电子Ⅲ 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 1617% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 18% ，投入资本回报率为 17% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 128% ，净利润现金含量很高。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 4.4% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月13日大跌 -20% ，股价跌停，抛压很重。"
        },
        {
          "tag": "商誉",
          "text": "商誉占净资产 22% ，商誉减值风险较高。"
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
          "content": "15:00 今天大跌的原因可能是海外存储巨头暴跌引发行业需求走弱与价格下探，压缩公司国产存储产品和电子元器件分销的收入与毛利，触发市场抛售。",
          "tags": [
            "快讯",
            "大跌原因"
          ]
        },
        {
          "content": "09:32 存储芯片板块延续跌势，德明利连续第三日跌停，华天科技、江波龙、香农芯创、佰维存储跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "香农芯创：关于为全资子公司提供担保及接受关联方提供担保暨关联交易的进展公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 26399539611.22,
      "revenue_yoy": 0.598986,
      "operating_profit": 439066745.42,
      "operating_profit_yoy": 0.017872,
      "net_profit": 345857201.83,
      "net_profit_yoy": -0.016709,
      "gross_profit": 827468805.73,
      "gross_profit_yoy": -0.034952,
      "cogs": 25572070805.49,
      "gross_margin": 3.13,
      "pe_forward": null,
      "valuation_history_days": 300,
      "valuation_history_from": "20210721",
      "current_price": 174.1,
      "price": 174.1,
      "ma5": 209.84,
      "ma10": 235.82,
      "ma20": 247.32,
      "dist_ma5_pct": -17.0,
      "dist_ma10_pct": -26.2,
      "dist_ma20_pct": -29.6,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 49.27,
        "pct_float": 7.12,
        "chg5_pct": -22.31,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "605020.SH",
      "fetch_time": "2026-07-21T11:40:49+0800",
      "name": "永和股份",
      "pe": 21.135,
      "pb": 2.9763,
      "ps_ttm": 3.1479,
      "pcf_ttm": 19.6887,
      "valuation_percentile": 51.56,
      "total_shares": 510818723,
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
        "股权激励指数",
        "可转债预案指数",
        "化学制品精选指数",
        "PVDF指数",
        "氟化工指数",
        "环氧丙烷指数"
      ],
      "score_company": 7.9,
      "score_trend": 7.3,
      "score_value": 6.3,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 91% ，利润成长性强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 152% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 13% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 1.4亿元 ，较上期增长 56% ，占2025年营收 2.6% ，在手订单充足。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 96% 的股票，走势较强。"
        },
        {
          "tag": "回购",
          "text": "近1月，公司累计回购 96万股 ，占总股本比例 0.19% ，金额合计 2999万元 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月03日大跌 -7.6% ，且成交额为近20日均值的 2.13倍 ，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "2026/09/15解禁789.47万股，占总股本1.55%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-15"
        },
        {
          "content": "预计2026/08/17发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-17"
        },
        {
          "content": "截至2026/07/21，公司累计回购 95.6万股 ，占总股本比例为 0.19% ，最高成交价为 31.6元/股 ，最低成交价为 31.1元/股 ，耗资 2999万元",
          "tags": [
            "公司回购流通股",
            "进行中"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 3785575712.97,
      "revenue_yoy": 0.120414,
      "operating_profit": 562127344.63,
      "operating_profit_yoy": 2.29087,
      "net_profit": 470371656.41,
      "net_profit_yoy": 2.199143,
      "gross_profit": 985491163.68,
      "gross_profit_yoy": 0.736713,
      "cogs": 2800084549.29,
      "gross_margin": 26.03,
      "pe_forward": null,
      "valuation_history_days": 366,
      "valuation_history_from": "20230710",
      "current_price": 33.78,
      "price": 33.78,
      "ma5": 35.4,
      "ma10": 39.38,
      "ma20": 37.64,
      "dist_ma5_pct": -4.6,
      "dist_ma10_pct": -14.2,
      "dist_ma20_pct": -10.3,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.89,
        "pct_float": 3.08,
        "chg5_pct": -11.03,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300037.SZ",
      "fetch_time": "2026-07-21T11:40:49+0800",
      "name": "新宙邦",
      "pe": 34.4531,
      "pb": 4.3678,
      "ps_ttm": 4.2226,
      "pcf_ttm": 29.1456,
      "valuation_percentile": 44.04,
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
        "股权激励指数",
        "深圳本地股指数",
        "AI手机指数",
        "可转债正股指数",
        "新能源汽车指数",
        "新材料指数",
        "锂电池指数",
        "特斯拉指数",
        "储能指数",
        "固态电池指数"
      ],
      "score_company": 9.2,
      "score_trend": 7.0,
      "score_value": 6.5,
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
          "text": "近90天， 12家 机构给出评级，其中 75% 为“买入”，距目标价的上涨空间为 64% 。"
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
      "valuation_history_from": "20210721",
      "current_price": 60.4,
      "price": 60.4,
      "ma5": 66.01,
      "ma10": 75.12,
      "ma20": 80.14,
      "dist_ma5_pct": -8.5,
      "dist_ma10_pct": -19.6,
      "dist_ma20_pct": -24.6,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.98,
        "pct_float": 2.88,
        "chg5_pct": -8.11,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002947.SZ",
      "fetch_time": "2026-07-21T11:40:49+0800",
      "name": "恒铭达",
      "pe": 24.9522,
      "pb": 4.6139,
      "ps_ttm": 4.9095,
      "pcf_ttm": 24.0711,
      "valuation_percentile": 54.29,
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
      "score_trend": 5.9,
      "score_value": 5.3,
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
          "content": "恒铭达：北京市中伦律师事务所关于苏州恒铭达电子科技股份有限公司2026年第四次临时股东会的法律意见书",
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
      "valuation_history_from": "20210721",
      "current_price": 56.53,
      "price": 56.53,
      "ma5": 63.48,
      "ma10": 68.65,
      "ma20": 75.85,
      "dist_ma5_pct": -10.9,
      "dist_ma10_pct": -17.7,
      "dist_ma20_pct": -25.5,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.09,
        "pct_float": 7.63,
        "chg5_pct": -5.12,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300870.SZ",
      "fetch_time": "2026-07-21T11:40:49+0800",
      "name": "欧陆通",
      "pe": 173.3571,
      "pb": 12.2441,
      "ps_ttm": 6.832,
      "pcf_ttm": 133.3007,
      "valuation_percentile": 93.3,
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
      "score_trend": 5.6,
      "score_value": 3.6,
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
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
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
          "content": "10:10 国盛证券研报指出，随着AI大模型训练带来的算力需求爆发，GPU机柜功率显著攀升，算力机架正由千瓦级迈向兆瓦级。传统低压直流母线方案在单机柜功率超200kW后存在空间挤占及铜材耗材过高等短板。800VDC架构凭借精简架构、降低耗材、原生兼容三大优势成为核心升级方向。英伟达供电方案正经历从传统交流机柜向800VDC Power Rack演进，其中800VDC Power Rack（Sidecar）作为短期主流方案，通过将AC-DC整流外置至独立侧边电源柜，有效释放机柜空间并降低传输损耗。\n在产业布局方面，光宝科技等台系厂商目前处于主导地位，大陆厂商正加速追赶。麦格米特已推出相关Power Shelf产品，欧陆通已供货谷歌，富特科技、奥海科技等企业正向数据中心电源领域拓展。国盛证券建议关注富特科技、宏发股份、欣锐科技、中恒电气、麦格米特、欧陆通、通合科技、优优绿能、奥海科技等公司，并提示下游需求不及预期、技术路线迭代及竞争加剧等风险。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "13:27 7月14日，数据中心电源板块在午后表现活跃。麦格米特在4个交易日内实现2个涨停，中恒电气、雄韬股份、欧陆通及新雷能等个股随之跟涨。\n\n中信证券发布研报指出，AI电源对功率器件的拉动作用预计将持续增强。随着HVDC与SST技术趋势的发展，相关领域的长期增量空间将逐步打开。预计本轮涨价趋势有望延续至2027年，相关厂商或将迎来收入快速增长与盈利能力修复的周期。",
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
      "valuation_history_days": 313,
      "valuation_history_from": "20220825",
      "current_price": 203.4,
      "price": 203.4,
      "ma5": 242.1,
      "ma10": 267.23,
      "ma20": 300.94,
      "dist_ma5_pct": -16.0,
      "dist_ma10_pct": -23.9,
      "dist_ma20_pct": -32.4,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.48,
        "pct_float": 3.7,
        "chg5_pct": -12.06,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300438.SZ",
      "fetch_time": "2026-07-21T11:40:49+0800",
      "name": "鹏辉能源",
      "pe": 54.5587,
      "pb": 5.5311,
      "ps_ttm": 2.0864,
      "pcf_ttm": 28.4246,
      "valuation_percentile": 47.38,
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
        "预期提升指数",
        "储能指数",
        "固态电池指数",
        "钠离子电池指数",
        "动力电池指数",
        "TWS耳机指数",
        "扭亏指数",
        "ETC指数"
      ],
      "score_company": 8.3,
      "score_trend": 7.1,
      "score_value": 6.9,
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
          "text": "近90天， 9家 机构给出评级，其中 78% 为“买入”，距目标价的上涨空间为 73% 。"
        },
        {
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 5.3% ，很受外资机构青睐；公募基金持股 6.5% ，较受内资机构青睐。"
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
          "content": "17:30 鹏辉能源发布2026年半年度业绩预告，预计上半年归母净利润为8亿元至8.66亿元，上年同期为亏损8822.67万元；扣非净利润预计为7.92亿元至8.56亿元，上年同期为亏损1.59亿元。公司表示，业绩增长主要得益于储能行业景气度持续，产品产销两旺，订单增长带动营收与利润扩容。\n鹏辉能源在应急电源高倍率电池、户用储能电芯及工商业储能系统等细分领域具有市场份额优势。公司正推进“海外跃升”战略，已建立十大海外办事处，业务覆盖美国、德国、日本、新加坡、印度等市场。公司董事长夏信德表示，行业正从价格竞争转向价值竞争，需通过上下游协同研发与技术迭代应对市场变化。\n鹏辉能源2025年全年实现营收119.44亿元，归母净利润2.06亿元。2026年上半年业绩预告显示公司经营规模实现增长。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:32 锂电池板块短线走低，鹏辉能源跌超10%，蔚蓝锂芯、德福科技、铜冠铜箔、诺德股份等跟跌。",
          "tags": [
            "快讯"
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
      "valuation_history_from": "20210721",
      "current_price": 62.18,
      "price": 62.18,
      "ma5": 66.02,
      "ma10": 69.51,
      "ma20": 74.74,
      "dist_ma5_pct": -5.8,
      "dist_ma10_pct": -10.5,
      "dist_ma20_pct": -16.8,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.52,
        "pct_float": 4.06,
        "chg5_pct": -9.23,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002407.SZ",
      "fetch_time": "2026-07-21T11:40:51+0800",
      "name": "多氟多",
      "pe": 66.2552,
      "pb": 4.0625,
      "ps_ttm": 3.2877,
      "pcf_ttm": null,
      "valuation_percentile": 55.97,
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
        "新能源汽车指数",
        "新材料指数",
        "锂电池指数",
        "固态电池指数",
        "钠离子电池指数",
        "动力电池指数",
        "万得预增指数",
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
      "score_trend": 6.5,
      "score_value": 5.8,
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
          "text": "2026年07月20日大跌 -9.99% ，股价跌停，抛压很重。"
        },
        {
          "tag": "波动",
          "text": "近20天，日均换手率 16% ，短线资金追逐，波动风险较高。"
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
          "content": "10:27 截至2026年7月20日，中证新能源汽车产业指数成分股表现分化，先导智能、当升科技、宁德时代涨幅居前。新能源车ETF平安（515700）最新报价2.07元，盘中换手率1.81%，成交额2640.39万元。消息面上，比亚迪巴西工厂第10万辆新能源汽车（海鸥车型）正式下线，该工厂在岗员工已超5500人。广发证券分析称，财政部等部门明确自2026年9月起对锂离子蓄电池征收消费税，并对钠离子、固态电池等技术路线给予免税政策，此举将拉大技术路线成本差异。近期磷酸铁锂龙头已上调加工费，叠加三季度需求旺季，产业链景气度有望改善。中证新能源汽车产业指数涵盖整车、电池及材料等领域，前十大权重股包括宁德时代、比亚迪、汇川技术等。\n基金投资存在风险，过往业绩不预示未来表现，投资者应根据自身风险承受能力审慎决策，详细阅读基金法律文件。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "19:33 多氟多在互动平台表示，公司自主研发的G5级电子级氢氟酸，现已持续稳定批量供应台积电、三星、华虹、长鑫存储等海内外头部逻辑芯片与存储晶圆厂商。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价开盘下跌 -10.00%",
          "tags": [
            "股价下跌"
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
      "valuation_history_from": "20210721",
      "current_price": 31.24,
      "price": 31.24,
      "ma5": 34.02,
      "ma10": 39.11,
      "ma20": 42.49,
      "dist_ma5_pct": -8.2,
      "dist_ma10_pct": -20.1,
      "dist_ma20_pct": -26.5,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 21.34,
        "pct_float": 7.04,
        "chg5_pct": -13.09,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "603127.SH",
      "fetch_time": "2026-07-21T11:40:51+0800",
      "name": "昭衍新药",
      "pe": 72.6543,
      "pb": 4.2481,
      "ps_ttm": 21.3289,
      "pcf_ttm": 70.9418,
      "valuation_percentile": 48.56,
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
        "创新药指数",
        "万得预增指数",
        "反内卷指数",
        "医疗服务精选指数",
        "CRO指数"
      ],
      "score_company": 8.2,
      "score_trend": 9.3,
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
          "tag": "订单",
          "text": "合同负债 10亿元 ，较上期增长 22% ，占2025年营收 63% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 7.0% ，较受内资机构青睐。"
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
          "content": "02:36 昭衍新药2026年A股限制性股票激励计划授予条件已成就。公司于2026年6月4日确定授予日，原计划向280名激励对象授予316.23万股。因实施2025年年度权益分派，授予价格由19.17元/股调整为19.05元/股。在缴款阶段，42名激励对象因个人原因放弃认购，合计放弃52.6万股。最终实际授予人数为238人，实际授予数量为263.63万股，募集资金总额为50,221,515.00元。\n公司已向中国证券登记结算有限责任公司上海分公司申请办理263.63万股限制性股票登记。该部分股份由无限售条件流通股变更为有限售条件流通股，股份来源为公司二级市场回购的A股普通股。公司将继续办理后续登记工作并履行信息披露义务。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "13:25 2026年7月20日盘中，创新药及CRO概念活跃，上证科创板生物医药指数上涨1.99%。益方生物、荣昌生物、迈威生物等个股上涨。全球生物医药投融资回暖，2026年上半年交易总额同比增58.5%，带动产业链订单增加。开源证券指出，CXO及创新药公司中报业绩普遍超预期。此外，基药目录更新新增794种药品，华福证券认为政策利好中药及医药流通板块。上证科创板生物医药指数前十大权重股包括联影医疗、艾力斯、百济神州等。科创医药ETF嘉实（588700）跟踪该指数，另有科创医药ETF嘉实联接基金（021061）可供布局。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "昭衍新药：H股公告：变更联席公司秘书、授权代表及法律程序文件代理人",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "李晶莹 任法律程序文件代理人",
          "tags": [
            "管理层变更"
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
      "valuation_history_from": "20210721",
      "current_price": 47.93,
      "price": 47.93,
      "ma5": 48.27,
      "ma10": 44.48,
      "ma20": 40.12,
      "dist_ma5_pct": -0.7,
      "dist_ma10_pct": 7.7,
      "dist_ma20_pct": 19.5,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.34,
        "pct_float": 2.14,
        "chg5_pct": 11.26,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "002056.SZ",
      "fetch_time": "2026-07-21T11:40:51+0800",
      "name": "横店东磁",
      "pe": 20.7471,
      "pb": 3.6694,
      "ps_ttm": 1.6157,
      "pcf_ttm": 10.7896,
      "valuation_percentile": 51.14,
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
        "员工持股指数",
        "QFII重仓指数",
        "新能源汽车指数",
        "新材料指数",
        "锂电池指数",
        "苹果指数",
        "特斯拉指数",
        "磷酸铁锂电池指数",
        "新能源指数",
        "光伏指数",
        "能源出海指数",
        "无线充电指数",
        "电源设备精选指数",
        "三元锂电池指数",
        "稀土永磁指数",
        "磁悬浮列车指数",
        "钙钛矿电池指数",
        "触板指数"
      ],
      "score_company": 8.6,
      "score_trend": 6.7,
      "score_value": 6.0,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 光伏电池组件 行业龙头企业。"
        },
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
        },
        {
          "content": "11:29股价达到 29.57 元，创历史新高",
          "tags": [
            "股价新高"
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
      "valuation_history_from": "20210721",
      "current_price": 24.04,
      "price": 24.04,
      "ma5": 24.93,
      "ma10": 27.23,
      "ma20": 28.32,
      "dist_ma5_pct": -3.6,
      "dist_ma10_pct": -11.7,
      "dist_ma20_pct": -15.1,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 7.43,
        "pct_float": 2.11,
        "chg5_pct": -6.33,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    }
  ],
  "active_positions": [],
  "position_prices": {},
  "missed_opportunity_prices": [
    {
      "code": "000703",
      "name": "恒逸石化",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 14.25,
      "return_pct": null
    },
    {
      "code": "002821",
      "name": "凯莱英",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 165.34,
      "return_pct": null
    },
    {
      "code": "605020",
      "name": "永和股份",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 33.23,
      "return_pct": null
    },
    {
      "code": "300684",
      "name": "中石科技",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 50.2,
      "return_pct": null
    },
    {
      "code": "688331",
      "name": "荣昌生物",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 124.86,
      "return_pct": null
    },
    {
      "code": "603127",
      "name": "昭衍新药",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 48.0,
      "return_pct": null
    },
    {
      "code": "688777",
      "name": "中控技术",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 93.31,
      "return_pct": null
    },
    {
      "code": "601126",
      "name": "四方股份",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 43.47,
      "return_pct": null
    },
    {
      "code": "301536",
      "name": "星宸科技",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 118.99,
      "return_pct": null
    },
    {
      "code": "002056",
      "name": "横店东磁",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 22.69,
      "return_pct": null
    },
    {
      "code": "688502",
      "name": "茂莱光学",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 398.0,
      "return_pct": null
    },
    {
      "code": "600961",
      "name": "株冶集团",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 22.49,
      "return_pct": null
    },
    {
      "code": "002185",
      "name": "华天科技",
      "recommended_date": "2026-07-17",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 17.64,
      "return_pct": null
    },
    {
      "code": "601958",
      "name": "金钼股份",
      "recommended_date": "2026-07-17",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 20.93,
      "return_pct": null
    },
    {
      "code": "688257",
      "name": "新锐股份",
      "recommended_date": "2026-07-17",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 63.25,
      "return_pct": null
    },
    {
      "code": "605376",
      "name": "博迁新材",
      "recommended_date": "2026-07-17",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 145.35,
      "return_pct": null
    },
    {
      "code": "688652",
      "name": "京仪装备",
      "recommended_date": "2026-07-17",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 154.92,
      "return_pct": null
    },
    {
      "code": "688536",
      "name": "思瑞浦",
      "recommended_date": "2026-07-17",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 245.85,
      "return_pct": null
    },
    {
      "code": "300373",
      "name": "扬杰科技",
      "recommended_date": "2026-07-17",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 96.3,
      "return_pct": null
    },
    {
      "code": "002975",
      "name": "博杰股份",
      "recommended_date": "2026-07-16",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 83.43,
      "return_pct": null
    },
    {
      "code": "688372",
      "name": "伟测科技",
      "recommended_date": "2026-07-16",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 131.6,
      "return_pct": null
    },
    {
      "code": "688392",
      "name": "骄成超声",
      "recommended_date": "2026-07-16",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 159.88,
      "return_pct": null
    },
    {
      "code": "300236",
      "name": "上海新阳",
      "recommended_date": "2026-07-16",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 89.68,
      "return_pct": null
    }
  ],
  "iv_sentiment": {
    "date": "2026-07-21",
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
        "current_iv": 0.2585,
        "is_live": false,
        "iv_high": 0.2272,
        "iv_low": 0.1137,
        "iv_high_raw": 0.2585,
        "iv_low_raw": 0.1137,
        "iv_rank": 1.0,
        "iv_rank_raw": 1.0,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9956,
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
            "date": "2026-07-21",
            "iv": 0.2585
          }
        ],
        "sigma_range": [
          0.1053,
          0.2277
        ],
        "name": "50ETF",
        "desc": "大盘蓝筹",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "510300",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 217,
        "current_iv": 0.2848,
        "is_live": false,
        "iv_high": 0.2476,
        "iv_low": 0.1201,
        "iv_high_raw": 0.3137,
        "iv_low_raw": 0.069,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.8819,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9911,
        "outliers_removed": 8,
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
          },
          {
            "date": "2026-07-21",
            "iv": 0.2848
          }
        ],
        "sigma_range": [
          0.1089,
          0.2501
        ],
        "name": "300ETF",
        "desc": "沪深300",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "510500",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 216,
        "current_iv": 0.4442,
        "is_live": false,
        "iv_high": 0.3531,
        "iv_low": 0.194,
        "iv_high_raw": 0.4544,
        "iv_low_raw": 0.107,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.9706,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9911,
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
            "date": "2025-09-05",
            "iv": 0.3575
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
            "iv": 0.4442
          }
        ],
        "sigma_range": [
          0.1738,
          0.3572
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
        "current_iv": 0.7312,
        "is_live": false,
        "iv_high": 0.6127,
        "iv_low": 0.2467,
        "iv_high_raw": 0.7362,
        "iv_low_raw": 0.126,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.9918,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9911,
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
            "date": "2026-07-15",
            "iv": 0.6334
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
            "iv": 0.7312
          }
        ],
        "sigma_range": [
          0.1647,
          0.6136
        ],
        "name": "科创50",
        "desc": "科创板",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159915",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 217,
        "current_iv": 0.6079,
        "is_live": false,
        "iv_high": 0.473,
        "iv_low": 0.2082,
        "iv_high_raw": 0.6363,
        "iv_low_raw": 0.2082,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.9337,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.991,
        "outliers_removed": 5,
        "outlier_details": [
          {
            "date": "2025-09-05",
            "iv": 0.5002
          },
          {
            "date": "2025-09-17",
            "iv": 0.4913
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
            "date": "2026-07-21",
            "iv": 0.6079
          }
        ],
        "sigma_range": [
          0.1721,
          0.4833
        ],
        "name": "创业板ETF",
        "desc": "创业板",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159922",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 213,
        "current_iv": 0.4768,
        "is_live": false,
        "iv_high": 0.3461,
        "iv_low": 0.1804,
        "iv_high_raw": 0.4768,
        "iv_low_raw": 0.1804,
        "iv_rank": 1.0,
        "iv_rank_raw": 1.0,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9955,
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
            "date": "2025-09-23",
            "iv": 0.3495
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
            "date": "2026-07-17",
            "iv": 0.36
          },
          {
            "date": "2026-07-20",
            "iv": 0.468
          },
          {
            "date": "2026-07-21",
            "iv": 0.4768
          }
        ],
        "sigma_range": [
          0.1741,
          0.3475
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
        "current_iv": 0.2744,
        "is_live": false,
        "iv_high": 0.2553,
        "iv_low": 0.1298,
        "iv_high_raw": 0.3036,
        "iv_low_raw": 0.1298,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.832,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.982,
        "outliers_removed": 10,
        "outlier_details": [
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
            "date": "2026-07-21",
            "iv": 0.2744
          }
        ],
        "sigma_range": [
          0.1138,
          0.2565
        ],
        "name": "300ETF深",
        "desc": "深市宽基",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159901",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 217,
        "current_iv": 0.4375,
        "is_live": false,
        "iv_high": 0.3391,
        "iv_low": 0.1682,
        "iv_high_raw": 0.4504,
        "iv_low_raw": 0.1682,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.9543,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.991,
        "outliers_removed": 5,
        "outlier_details": [
          {
            "date": "2025-08-20",
            "iv": 0.3484
          },
          {
            "date": "2025-08-29",
            "iv": 0.3406
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
            "iv": 0.4375
          }
        ],
        "sigma_range": [
          0.1454,
          0.3397
        ],
        "name": "深100ETF",
        "desc": "深市蓝筹",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "588080",
        "lookback_days": 252,
        "data_points": 224,
        "data_points_filtered": 217,
        "current_iv": 0.7668,
        "is_live": false,
        "iv_high": 0.6087,
        "iv_low": 0.184,
        "iv_high_raw": 0.7668,
        "iv_low_raw": 0.184,
        "iv_rank": 1.0,
        "iv_rank_raw": 1.0,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9955,
        "outliers_removed": 7,
        "outlier_details": [
          {
            "date": "2026-06-30",
            "iv": 0.6147
          },
          {
            "date": "2026-07-01",
            "iv": 0.6163
          },
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
            "iv": 0.7668
          }
        ],
        "sigma_range": [
          0.1676,
          0.6114
        ],
        "name": "科创板50",
        "desc": "科创板（备用代理）",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      }
    ],
    "overall_sentiment": {
      "signal": "极度恐慌",
      "avg_iv_rank": 1.0,
      "avg_iv_percentile": 1.0,
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
    "regime": "weak",
    "breadth_ratio": 0.9266,
    "up": 2601,
    "down": 2807,
    "positive_indices": [
      "上证指数",
      "深证成指",
      "创业板指"
    ],
    "negative_indices": [],
    "limit_ups": 46,
    "limit_downs": 24,
    "sizing_multiplier": 0.5,
    "hard_block": false,
    "reason": "Entry regime weak: breadth 0.93:1, 3/3 major indices green, 46 limit-ups / 24 limit-downs. Allow entries only with 50% sizing."
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
  "active_learnings": "## Active Rules (proven, hitRate ≥ 75%)\n- [h013] Strong breadth alone is not enough to force entries; without candidate RPS and MA-distance data, the correct momentum decision is to keep cash. (hitRate: 99%, n=127, confidence: 98%)\n- [h019] Bottom-list sectors should be treated as hard no-buy zones even when individual names still carry acceptable RPS readings. (hitRate: 100%, n=41, confidence: 98%)\n- [h028] Today’s relative leaders are concentrated in communication equipment and adjacent tech hardware, while cyclicals/agri/resource laggards are being de-risked aggressively. (hitRate: 100%, n=42, confidence: 98%)\n- [h027] MA-distance discipline remains critical inside hot sectors: a hot sector does not override chase risk when dist_ma5_pct exceeds 6% or dist_ma10_pct exceeds 8%. (hitRate: 100%, n=38, confidence: 98%)\n- [h023] Raising stops mechanically after +10% works well in weak tapes because it converts a fast winner into a low-risk hold without needing a fresh market call. (hitRate: 100%, n=36, confidence: 97%)\n- [h021] The MA-distance anti-chase rule is doing real work: several visually strong names fail because they are too far above short-term support. (hitRate: 98%, n=96, confidence: 97%)\n- [h017] Low-IV conditions around 16-22% IV rank do not justify freezing risk when breadth is 5.6:1; they argue for normal sizing but tighter discipline on chasing. (hitRate: 100%, n=25, confidence: 96%)\n\n## Working Hypotheses (testing, hitRate ≥ 65%)\n- [h077] The hard block is preventing FOMO entries. 新宙邦 (宁德时代协议 catalyst, VCP SETUP) and 奥来德 (dist_ma5 0.3%) would have been tempting buys in V1. V2 correctly forces cash preservation in panic regime. (hitRate: 100%, n=6, confidence: 88%)\n- [h024] Stop-proximity violations deserve proactive action before the hard stop is hit, especially in 科创板 names where gap risk can erase the remaining cushion quickly. (hitRate: 100%, n=5, confidence: 86%)\n",
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
