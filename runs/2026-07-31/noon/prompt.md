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

### Rule 2: Buy Strength (RPS ≥75%)
- **Sweet spot: RPS120 ≥ 80%** — confirmed working from V1 data. Higher is stronger.
- **No upper cap** — RPS120 in the high 90s (even 100) is the *strongest* relative strength, not a disqualifier. Momentum-first means we want the leaders. A high RPS is buyable — the only thing that makes it "too hot" is price extension, which Rule 2b handles.
- **Below 75%**: Skip — not enough momentum.
- **The sole "too extended" guard is Rule 2b (MA distance), NOT the RPS level.** A very high RPS name is fine as long as price hasn't spiked far above its MAs; prefer entries near MA5/MA10 support.

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
| RPS 80-92% hard cutoff | RPS ≥75%, no upper cap (Rule 2b guards extension) |
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
  "date": "2026-07-31",
  "portfolio": {
    "startingCapital": 1000000,
    "totalEquity": 941655.0,
    "cash": 916263.0,
    "investedValue": 25392.0,
    "unrealizedPnl": 432.0,
    "realizedPnl": -58777.0,
    "totalPnl": -58345.0,
    "totalReturnPct": -5.83,
    "positionsUsed": 1,
    "positionsMax": 10,
    "cashPct": 97.3,
    "dayPnl": -288.0,
    "minCashPct": 0,
    "minCashValue": 0.0,
    "deployableCash": 916263.0
  },
  "market": {
    "timestamp": "2026-07-31T11:40:49.428433",
    "indices": {
      "上证指数": {
        "code": "sh000001",
        "close": 3833.654,
        "change_pct": 0.76,
        "date": "2026-07-31"
      },
      "深证成指": {
        "code": "sz399001",
        "close": 13705.42,
        "change_pct": 3.16,
        "date": "2026-07-31"
      },
      "创业板指": {
        "code": "sz399006",
        "close": 3408.15,
        "change_pct": 5.04,
        "date": "2026-07-31"
      },
      "科创50": {
        "code": "sh000688",
        "close": 1682.275,
        "change_pct": 5.91,
        "date": "2026-07-31"
      }
    },
    "breadth": {
      "up": 4517,
      "down": 903,
      "flat": 108,
      "total": 5528,
      "distribution": {
        "f10": 0,
        "f7_10": 1,
        "f4_7": 29,
        "f2_4": 132,
        "f0_2": 741,
        "f0": 108,
        "r0_2": 1643,
        "r2_4": 1218,
        "r4_7": 986,
        "r7_10": 582,
        "r10": 88
      }
    },
    "sectors": {
      "top5": [
        {
          "板块名称": "广告营销",
          "涨跌幅": 8.86
        },
        {
          "板块名称": "通信设备",
          "涨跌幅": 7.69
        },
        {
          "板块名称": "元件",
          "涨跌幅": 7.66
        },
        {
          "板块名称": "自动化设备",
          "涨跌幅": 7.32
        },
        {
          "板块名称": "IT服务Ⅱ",
          "涨跌幅": 7.08
        }
      ],
      "bottom5": [
        {
          "板块名称": "国有大型银行Ⅱ",
          "涨跌幅": -3.6
        },
        {
          "板块名称": "股份制银行Ⅱ",
          "涨跌幅": -2.36
        },
        {
          "板块名称": "城商行Ⅱ",
          "涨跌幅": -2.15
        },
        {
          "板块名称": "保险Ⅱ",
          "涨跌幅": -2.03
        },
        {
          "板块名称": "白色家电",
          "涨跌幅": -1.93
        }
      ]
    }
  },
  "strategy_pool": {
    "source": "cheesefortune_intersection",
    "total_stocks": 75,
    "stocks": [
      {
        "code": "688146",
        "code_full": "688146.SH",
        "name": "中船特气",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1506.9176,
        "pe": 3.2,
        "risks_count": 2,
        "rps20": null,
        "rps60": 100.0,
        "rps120": 100.0,
        "rps250": 99.84,
        "ma10": 245.14,
        "vcp_quality": null,
        "ma5": 264.52,
        "ma20": 279.88,
        "dist_ma5_pct": 13.9,
        "dist_ma10_pct": 22.9,
        "dist_ma20_pct": 7.6
      },
      {
        "code": "688498",
        "code_full": "688498.SH",
        "name": "源杰科技",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 1265.9198,
        "pe": 3.6,
        "risks_count": 1,
        "rps20": 70.02,
        "rps60": 99.84,
        "rps120": 99.76,
        "rps250": 99.96,
        "ma10": 1457.24,
        "vcp_quality": null,
        "ma5": 1352.4,
        "ma20": 1595.56,
        "dist_ma5_pct": -9.2,
        "dist_ma10_pct": -15.7,
        "dist_ma20_pct": -23.0
      },
      {
        "code": "300604",
        "code_full": "300604.SZ",
        "name": "长川科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1557.4977,
        "pe": 9.2,
        "risks_count": 1,
        "rps20": 98.61,
        "rps60": 99.28,
        "rps120": 99.74,
        "rps250": 99.72,
        "ma10": 291.08,
        "vcp_quality": null,
        "ma5": 289.37,
        "ma20": 308.02,
        "dist_ma5_pct": -6.3,
        "dist_ma10_pct": -6.9,
        "dist_ma20_pct": -12.0
      },
      {
        "code": "301377",
        "code_full": "301377.SZ",
        "name": "鼎泰高科",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1412.0696,
        "pe": 3.6,
        "risks_count": 1,
        "rps20": 28.14,
        "rps60": 99.24,
        "rps120": 99.7,
        "rps250": 99.94,
        "ma10": 402.52,
        "vcp_quality": null,
        "ma5": 389.43,
        "ma20": 450.7,
        "dist_ma5_pct": -7.2,
        "dist_ma10_pct": -10.2,
        "dist_ma20_pct": -19.8
      },
      {
        "code": "002980",
        "code_full": "002980.SZ",
        "name": "华盛昌",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 120.3266,
        "pe": 6.2,
        "risks_count": 2,
        "rps20": 14.12,
        "rps60": 99.96,
        "rps120": 99.68,
        "rps250": 99.05,
        "ma10": 86.85,
        "vcp_quality": null,
        "ma5": 79.53,
        "ma20": 94.87,
        "dist_ma5_pct": -11.2,
        "dist_ma10_pct": -18.7,
        "dist_ma20_pct": -25.6
      },
      {
        "code": "688630",
        "code_full": "688630.SH",
        "name": "芯碁微装",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 439.3688,
        "pe": 5.3,
        "risks_count": 0,
        "rps20": 50.67,
        "rps60": 99.3,
        "rps120": 99.56,
        "rps250": 99.23,
        "ma10": 383.38,
        "vcp_quality": null,
        "ma5": 388.32,
        "ma20": 435.3,
        "dist_ma5_pct": -9.9,
        "dist_ma10_pct": -8.7,
        "dist_ma20_pct": -19.6
      },
      {
        "code": "002281",
        "code_full": "002281.SZ",
        "name": "光迅科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1261.0621,
        "pe": 16.9,
        "risks_count": 1,
        "rps20": 30.63,
        "rps60": 99.7,
        "rps120": 99.5,
        "rps250": 98.66,
        "ma10": 186.23,
        "vcp_quality": null,
        "ma5": 182.59,
        "ma20": 206.15,
        "dist_ma5_pct": -7.3,
        "dist_ma10_pct": -9.1,
        "dist_ma20_pct": -17.9
      },
      {
        "code": "688200",
        "code_full": "688200.SH",
        "name": "华峰测控",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 674.524,
        "pe": 6.4,
        "risks_count": 0,
        "rps20": 96.87,
        "rps60": 98.94,
        "rps120": 99.48,
        "rps250": 98.44,
        "ma10": 375.4,
        "vcp_quality": null,
        "ma5": 366.01,
        "ma20": 435.17,
        "dist_ma5_pct": -1.4,
        "dist_ma10_pct": -3.9,
        "dist_ma20_pct": -17.1
      },
      {
        "code": "688308",
        "code_full": "688308.SH",
        "name": "欧科亿",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 123.8497,
        "pe": 5.6,
        "risks_count": 3,
        "rps20": 1.58,
        "rps60": 98.01,
        "rps120": 99.46,
        "rps250": 99.35,
        "ma10": 95.94,
        "vcp_quality": null,
        "ma5": 91.65,
        "ma20": 125.12,
        "dist_ma5_pct": -6.0,
        "dist_ma10_pct": -10.1,
        "dist_ma20_pct": -31.1
      },
      {
        "code": "002384",
        "code_full": "002384.SZ",
        "name": "东山精密",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 2963.541,
        "pe": 16.3,
        "risks_count": 2,
        "rps20": 60.95,
        "rps60": 99.86,
        "rps120": 99.3,
        "rps250": 99.78,
        "ma10": 216.52,
        "vcp_quality": null,
        "ma5": 197.64,
        "ma20": 228.7,
        "dist_ma5_pct": -9.0,
        "dist_ma10_pct": -17.0,
        "dist_ma20_pct": -21.4
      },
      {
        "code": "000811",
        "code_full": "000811.SZ",
        "name": "冰轮环境",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 332.0831,
        "pe": 28.1,
        "risks_count": 2,
        "rps20": 98.14,
        "rps60": 99.46,
        "rps120": 99.22,
        "rps250": 98.97,
        "ma10": 852.14,
        "vcp_quality": null,
        "ma5": 741.76,
        "ma20": 1017.37,
        "dist_ma5_pct": -95.5,
        "dist_ma10_pct": -96.1,
        "dist_ma20_pct": -96.7
      },
      {
        "code": "605376",
        "code_full": "605376.SH",
        "name": "博迁新材",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 348.2419,
        "pe": 5.6,
        "risks_count": 1,
        "rps20": 12.61,
        "rps60": 94.88,
        "rps120": 99.16,
        "rps250": 98.64,
        "ma10": 145.99,
        "vcp_quality": null,
        "ma5": 143.4,
        "ma20": 189.04,
        "dist_ma5_pct": 0.8,
        "dist_ma10_pct": -1.0,
        "dist_ma20_pct": -23.5
      },
      {
        "code": "688347",
        "code_full": "688347.SH",
        "name": "华虹宏力",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 3996.7707,
        "pe": 2.9,
        "risks_count": 1,
        "rps20": 99.31,
        "rps60": 99.62,
        "rps120": 99.12,
        "rps250": 99.68,
        "ma10": 328.67,
        "vcp_quality": null,
        "ma5": 306.1,
        "ma20": 331.55,
        "dist_ma5_pct": -11.7,
        "dist_ma10_pct": -17.8,
        "dist_ma20_pct": -18.5
      },
      {
        "code": "688361",
        "code_full": "688361.SH",
        "name": "中科飞测",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1137.655,
        "pe": 3.2,
        "risks_count": 3,
        "rps20": 99.72,
        "rps60": 98.66,
        "rps120": 99.01,
        "rps250": 98.85,
        "ma10": 350.16,
        "vcp_quality": null,
        "ma5": 362.18,
        "ma20": 368.64,
        "dist_ma5_pct": -0.4,
        "dist_ma10_pct": 3.0,
        "dist_ma20_pct": -2.2
      },
      {
        "code": "688120",
        "code_full": "688120.SH",
        "name": "华海清科",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1331.4238,
        "pe": 4.1,
        "risks_count": 2,
        "rps20": 99.13,
        "rps60": 99.04,
        "rps120": 98.83,
        "rps250": 97.55,
        "ma10": 259.53,
        "vcp_quality": null,
        "ma5": 264.13,
        "ma20": 281.45,
        "dist_ma5_pct": 1.7,
        "dist_ma10_pct": 3.5,
        "dist_ma20_pct": -4.5
      },
      {
        "code": "600176",
        "code_full": "600176.SH",
        "name": "中国巨石",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 1466.349,
        "pe": 27.2,
        "risks_count": 1,
        "rps20": 44.38,
        "rps60": 97.41,
        "rps120": 98.69,
        "rps250": 97.69,
        "ma10": 702.91,
        "vcp_quality": null,
        "ma5": 610.96,
        "ma20": 943.2,
        "dist_ma5_pct": -94.0,
        "dist_ma10_pct": -94.8,
        "dist_ma20_pct": -96.1
      },
      {
        "code": "000657",
        "code_full": "000657.SZ",
        "name": "中钨高新",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1102.8445,
        "pe": 12.7,
        "risks_count": 2,
        "rps20": 8.75,
        "rps60": 88.64,
        "rps120": 98.63,
        "rps250": 99.45,
        "ma10": 303.98,
        "vcp_quality": null,
        "ma5": 266.88,
        "ma20": 373.15,
        "dist_ma5_pct": -81.9,
        "dist_ma10_pct": -84.1,
        "dist_ma20_pct": -87.0
      },
      {
        "code": "002353",
        "code_full": "002353.SZ",
        "name": "杰瑞股份",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 1287.2939,
        "pe": 16.4,
        "risks_count": 2,
        "rps20": 38.75,
        "rps60": 94.76,
        "rps120": 98.47,
        "rps250": 98.54,
        "ma10": 131.06,
        "vcp_quality": null,
        "ma5": 139.81,
        "ma20": 143.27,
        "dist_ma5_pct": -0.1,
        "dist_ma10_pct": 6.6,
        "dist_ma20_pct": -2.5
      },
      {
        "code": "300285",
        "code_full": "300285.SZ",
        "name": "国瓷材料",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 610.9912,
        "pe": 14.5,
        "risks_count": 2,
        "rps20": 34.81,
        "rps60": 98.62,
        "rps120": 98.43,
        "rps250": 97.65,
        "ma10": 58.6,
        "vcp_quality": null,
        "ma5": 59.21,
        "ma20": 70.98,
        "dist_ma5_pct": -0.1,
        "dist_ma10_pct": 0.9,
        "dist_ma20_pct": -16.7
      },
      {
        "code": "001389",
        "code_full": "001389.SZ",
        "name": "广合科技",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 621.1398,
        "pe": 2.3,
        "risks_count": 2,
        "rps20": 50.97,
        "rps60": 97.47,
        "rps120": 98.35,
        "rps250": 97.57,
        "ma10": 165.65,
        "vcp_quality": null,
        "ma5": 157.05,
        "ma20": 176.92,
        "dist_ma5_pct": -7.0,
        "dist_ma10_pct": -11.9,
        "dist_ma20_pct": -17.5
      },
      {
        "code": "301165",
        "code_full": "301165.SZ",
        "name": "锐捷网络",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 1135.9091,
        "pe": 3.6,
        "risks_count": 0,
        "rps20": 99.96,
        "rps60": 99.1,
        "rps120": 98.13,
        "rps250": 97.15,
        "ma10": 114.98,
        "vcp_quality": null,
        "ma5": 121.97,
        "ma20": 107.19,
        "dist_ma5_pct": -13.9,
        "dist_ma10_pct": -8.7,
        "dist_ma20_pct": -2.0
      },
      {
        "code": "688300",
        "code_full": "688300.SH",
        "name": "联瑞新材",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 252.9631,
        "pe": 6.7,
        "risks_count": 0,
        "rps20": 2.2,
        "rps60": 99.16,
        "rps120": 98.11,
        "rps250": 96.88,
        "ma10": 130.21,
        "vcp_quality": null,
        "ma5": 123.46,
        "ma20": 165.18,
        "dist_ma5_pct": -6.1,
        "dist_ma10_pct": -11.0,
        "dist_ma20_pct": -29.8
      },
      {
        "code": "300408",
        "code_full": "300408.SZ",
        "name": "三环集团",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 2093.2183,
        "pe": 11.6,
        "risks_count": 0,
        "rps20": 14.04,
        "rps60": 98.55,
        "rps120": 98.09,
        "rps250": 96.76,
        "ma10": 103.51,
        "vcp_quality": null,
        "ma5": 105.54,
        "ma20": 120.98,
        "dist_ma5_pct": 3.2,
        "dist_ma10_pct": 5.2,
        "dist_ma20_pct": -10.0
      },
      {
        "code": "300857",
        "code_full": "300857.SZ",
        "name": "协创数据",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 917.5068,
        "pe": 6.0,
        "risks_count": 1,
        "rps20": 57.13,
        "rps60": 95.62,
        "rps120": 97.89,
        "rps250": 98.62,
        "ma10": 229.59,
        "vcp_quality": null,
        "ma5": 226.5,
        "ma20": 259.39,
        "dist_ma5_pct": -9.5,
        "dist_ma10_pct": -10.7,
        "dist_ma20_pct": -21.0
      },
      {
        "code": "300502",
        "code_full": "300502.SZ",
        "name": "新易盛",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 5174.0866,
        "pe": 10.4,
        "risks_count": 0,
        "rps20": 54.14,
        "rps60": 98.84,
        "rps120": 97.75,
        "rps250": 99.86,
        "ma10": 488.85,
        "vcp_quality": null,
        "ma5": 458.48,
        "ma20": 514.15,
        "dist_ma5_pct": -8.1,
        "dist_ma10_pct": -13.8,
        "dist_ma20_pct": -18.1
      },
      {
        "code": "300308",
        "code_full": "300308.SZ",
        "name": "中际旭创",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 10106.5073,
        "pe": 14.3,
        "risks_count": 2,
        "rps20": 38.51,
        "rps60": 98.98,
        "rps120": 97.67,
        "rps250": 99.92,
        "ma10": 1034.88,
        "vcp_quality": null,
        "ma5": 1010.99,
        "ma20": 1096.3,
        "dist_ma5_pct": -5.9,
        "dist_ma10_pct": -8.1,
        "dist_ma20_pct": -13.3
      },
      {
        "code": "688017",
        "code_full": "688017.SH",
        "name": "绿的谐波",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 478.4916,
        "pe": 5.9,
        "risks_count": 1,
        "rps20": 33.37,
        "rps60": 95.34,
        "rps120": 97.65,
        "rps250": 93.22,
        "ma10": 314.07,
        "vcp_quality": null,
        "ma5": 298.36,
        "ma20": 364.57,
        "dist_ma5_pct": -4.9,
        "dist_ma10_pct": -9.7,
        "dist_ma20_pct": -22.2
      },
      {
        "code": "301536",
        "code_full": "301536.SZ",
        "name": "星宸科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 438.5838,
        "pe": 2.3,
        "risks_count": 2,
        "rps20": 98.83,
        "rps60": 98.15,
        "rps120": 97.63,
        "rps250": 92.35,
        "ma10": 119.96,
        "vcp_quality": null,
        "ma5": 127.58,
        "ma20": 118.79,
        "dist_ma5_pct": -1.4,
        "dist_ma10_pct": 4.9,
        "dist_ma20_pct": 5.9
      },
      {
        "code": "000703",
        "code_full": "000703.SZ",
        "name": "恒逸石化",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 613.3607,
        "pe": 15.2,
        "risks_count": 3,
        "rps20": 97.68,
        "rps60": 91.97,
        "rps120": 97.37,
        "rps250": 95.25,
        "ma10": 137.59,
        "vcp_quality": null,
        "ma5": 125.69,
        "ma20": 139.09,
        "dist_ma5_pct": -87.2,
        "dist_ma10_pct": -88.3,
        "dist_ma20_pct": -88.5
      },
      {
        "code": "002938",
        "code_full": "002938.SZ",
        "name": "鹏鼎控股",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1762.4866,
        "pe": 7.8,
        "risks_count": 1,
        "rps20": 34.99,
        "rps60": 97.45,
        "rps120": 97.29,
        "rps250": 97.29,
        "ma10": 91.26,
        "vcp_quality": null,
        "ma5": 87.55,
        "ma20": 94.93,
        "dist_ma5_pct": -3.5,
        "dist_ma10_pct": -7.4,
        "dist_ma20_pct": -11.0
      },
      {
        "code": "003031",
        "code_full": "003031.SZ",
        "name": "中瓷电子",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 410.9092,
        "pe": 5.5,
        "risks_count": 3,
        "rps20": 6.77,
        "rps60": 95.97,
        "rps120": 97.2,
        "rps250": 93.85,
        "ma10": 106.6,
        "vcp_quality": null,
        "ma5": 104.19,
        "ma20": 128.07,
        "dist_ma5_pct": -5.4,
        "dist_ma10_pct": -7.5,
        "dist_ma20_pct": -23.0
      },
      {
        "code": "688531",
        "code_full": "688531.SH",
        "name": "日联科技",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 169.7669,
        "pe": 3.3,
        "risks_count": 0,
        "rps20": 12.36,
        "rps60": 98.49,
        "rps120": 97.16,
        "rps250": 96.48,
        "ma10": 126.47,
        "vcp_quality": null,
        "ma5": 122.88,
        "ma20": 149.18,
        "dist_ma5_pct": -4.5,
        "dist_ma10_pct": -7.3,
        "dist_ma20_pct": -21.4
      },
      {
        "code": "600522",
        "code_full": "600522.SH",
        "name": "中天科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 945.3871,
        "pe": 23.7,
        "risks_count": 2,
        "rps20": 2.28,
        "rps60": 94.78,
        "rps120": 97.04,
        "rps250": 94.66,
        "ma10": 32.67,
        "vcp_quality": null,
        "ma5": 31.27,
        "ma20": 40.76,
        "dist_ma5_pct": -6.2,
        "dist_ma10_pct": -10.2,
        "dist_ma20_pct": -28.0
      },
      {
        "code": "300806",
        "code_full": "300806.SZ",
        "name": "斯迪克",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 242.4025,
        "pe": 6.6,
        "risks_count": 4,
        "rps20": 2.38,
        "rps60": 86.85,
        "rps120": 96.84,
        "rps250": 97.59,
        "ma10": 55.62,
        "vcp_quality": null,
        "ma5": 48.83,
        "ma20": 72.93,
        "dist_ma5_pct": -15.7,
        "dist_ma10_pct": -26.0,
        "dist_ma20_pct": -43.6
      },
      {
        "code": "688629",
        "code_full": "688629.SH",
        "name": "华丰科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 562.2806,
        "pe": 3.0,
        "risks_count": 1,
        "rps20": 92.59,
        "rps60": 96.11,
        "rps120": 96.4,
        "rps250": 95.71,
        "ma10": 152.03,
        "vcp_quality": null,
        "ma5": 146.88,
        "ma20": 170.17,
        "dist_ma5_pct": -8.5,
        "dist_ma10_pct": -11.6,
        "dist_ma20_pct": -21.0
      },
      {
        "code": "002463",
        "code_full": "002463.SZ",
        "name": "沪电股份",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 1857.973,
        "pe": 15.9,
        "risks_count": 1,
        "rps20": 41.76,
        "rps60": 97.61,
        "rps120": 96.36,
        "rps250": 98.22,
        "ma10": 117.28,
        "vcp_quality": null,
        "ma5": 111.29,
        "ma20": 125.08,
        "dist_ma5_pct": -5.4,
        "dist_ma10_pct": -10.3,
        "dist_ma20_pct": -15.9
      },
      {
        "code": "603203",
        "code_full": "603203.SH",
        "name": "快克智能",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 115.4381,
        "pe": 9.7,
        "risks_count": 1,
        "rps20": 11.68,
        "rps60": 95.91,
        "rps120": 96.06,
        "rps250": 94.23,
        "ma10": 41.55,
        "vcp_quality": null,
        "ma5": 40.06,
        "ma20": 52.89,
        "dist_ma5_pct": -5.1,
        "dist_ma10_pct": -8.5,
        "dist_ma20_pct": -28.1
      },
      {
        "code": "601991",
        "code_full": "601991.SH",
        "name": "大唐发电",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 1077.0906,
        "pe": 19.6,
        "risks_count": 3,
        "rps20": 21.25,
        "rps60": 98.23,
        "rps120": 95.94,
        "rps250": 91.99,
        "ma10": 6.3,
        "vcp_quality": null,
        "ma5": 6.32,
        "ma20": 6.6,
        "dist_ma5_pct": -2.4,
        "dist_ma10_pct": -2.1,
        "dist_ma20_pct": -6.5
      },
      {
        "code": "002821",
        "code_full": "002821.SZ",
        "name": "凯莱英",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 526.5598,
        "pe": 9.7,
        "risks_count": 1,
        "rps20": 99.52,
        "rps60": 97.93,
        "rps120": 95.88,
        "rps250": 92.25,
        "ma10": 163.53,
        "vcp_quality": null,
        "ma5": 159.42,
        "ma20": 164.99,
        "dist_ma5_pct": -2.8,
        "dist_ma10_pct": -5.2,
        "dist_ma20_pct": -6.0
      },
      {
        "code": "688008",
        "code_full": "688008.SH",
        "name": "澜起科技",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 2401.7747,
        "pe": 7.0,
        "risks_count": 1,
        "rps20": 44.73,
        "rps60": 93.8,
        "rps120": 95.82,
        "rps250": 96.01,
        "ma10": 212.74,
        "vcp_quality": null,
        "ma5": 220.03,
        "ma20": 246.33,
        "dist_ma5_pct": -5.7,
        "dist_ma10_pct": -2.5,
        "dist_ma20_pct": -15.8
      },
      {
        "code": "002432",
        "code_full": "002432.SZ",
        "name": "九安医疗",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 289.9724,
        "pe": 16.1,
        "risks_count": 4,
        "rps20": 91.72,
        "rps60": 98.51,
        "rps120": 95.74,
        "rps250": 91.42,
        "ma10": 73.24,
        "vcp_quality": null,
        "ma5": 69.46,
        "ma20": 67.77,
        "dist_ma5_pct": -3.8,
        "dist_ma10_pct": -8.8,
        "dist_ma20_pct": -1.4
      },
      {
        "code": "688777",
        "code_full": "688777.SH",
        "name": "中控技术",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 639.2811,
        "pe": 5.6,
        "risks_count": 2,
        "rps20": 25.33,
        "rps60": 87.15,
        "rps120": 95.44,
        "rps250": 89.78,
        "ma10": 85.95,
        "vcp_quality": null,
        "ma5": 81.86,
        "ma20": 96.46,
        "dist_ma5_pct": -2.4,
        "dist_ma10_pct": -7.0,
        "dist_ma20_pct": -17.2
      },
      {
        "code": "002916",
        "code_full": "002916.SZ",
        "name": "深南电路",
        "source_date": "2026/07/29",
        "highlights_count": 9,
        "market_cap": 1937.919,
        "pe": 8.6,
        "risks_count": 1,
        "rps20": 33.96,
        "rps60": 94.98,
        "rps120": 95.23,
        "rps250": 98.26,
        "ma10": 336.82,
        "vcp_quality": null,
        "ma5": 331.57,
        "ma20": 383.01,
        "dist_ma5_pct": -4.7,
        "dist_ma10_pct": -6.2,
        "dist_ma20_pct": -17.5
      },
      {
        "code": "000938",
        "code_full": "000938.SZ",
        "name": "紫光股份",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 960.9868,
        "pe": 26.7,
        "risks_count": 4,
        "rps20": 99.78,
        "rps60": 97.59,
        "rps120": 94.41,
        "rps250": 86.02,
        "ma10": 263.45,
        "vcp_quality": null,
        "ma5": 238.25,
        "ma20": 257.78,
        "dist_ma5_pct": -85.9,
        "dist_ma10_pct": -87.2,
        "dist_ma20_pct": -87.0
      },
      {
        "code": "688378",
        "code_full": "688378.SH",
        "name": "奥来德",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 86.9239,
        "pe": 5.9,
        "risks_count": 2,
        "rps20": 23.9,
        "rps60": 87.47,
        "rps120": 94.39,
        "rps250": 95.31,
        "ma10": 39.84,
        "vcp_quality": null,
        "ma5": 38.01,
        "ma20": 47.6,
        "dist_ma5_pct": -4.7,
        "dist_ma10_pct": -9.1,
        "dist_ma20_pct": -23.9
      },
      {
        "code": "688536",
        "code_full": "688536.SH",
        "name": "思瑞浦",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 300.8527,
        "pe": 5.8,
        "risks_count": 2,
        "rps20": 25.66,
        "rps60": 95.66,
        "rps120": 94.21,
        "rps250": 86.97,
        "ma10": 247.72,
        "vcp_quality": null,
        "ma5": 244.23,
        "ma20": 289.62,
        "dist_ma5_pct": -1.7,
        "dist_ma10_pct": -3.1,
        "dist_ma20_pct": -17.1
      },
      {
        "code": "603127",
        "code_full": "603127.SH",
        "name": "昭衍新药",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 300.114,
        "pe": 8.9,
        "risks_count": 3,
        "rps20": 99.64,
        "rps60": 94.84,
        "rps120": 94.15,
        "rps250": 96.58,
        "ma10": 47.83,
        "vcp_quality": null,
        "ma5": 46.59,
        "ma20": 45.05,
        "dist_ma5_pct": -5.7,
        "dist_ma10_pct": -8.1,
        "dist_ma20_pct": -2.5
      },
      {
        "code": "600236",
        "code_full": "600236.SH",
        "name": "桂冠电力",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 843.4144,
        "pe": 26.3,
        "risks_count": 2,
        "rps20": 96.16,
        "rps60": 94.46,
        "rps120": 94.11,
        "rps250": 89.64,
        "ma10": 85.94,
        "vcp_quality": null,
        "ma5": 74.15,
        "ma20": 83.77,
        "dist_ma5_pct": -85.6,
        "dist_ma10_pct": -87.5,
        "dist_ma20_pct": -87.2
      },
      {
        "code": "002080",
        "code_full": "002080.SZ",
        "name": "中材科技",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 710.3497,
        "pe": 19.7,
        "risks_count": 3,
        "rps20": 12.22,
        "rps60": 89.46,
        "rps120": 94.09,
        "rps250": 97.77,
        "ma10": 51.03,
        "vcp_quality": null,
        "ma5": 47.93,
        "ma20": 64.17,
        "dist_ma5_pct": -9.0,
        "dist_ma10_pct": -14.5,
        "dist_ma20_pct": -32.0
      },
      {
        "code": "000988",
        "code_full": "000988.SZ",
        "name": "华工科技",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 916.013,
        "pe": 26.1,
        "risks_count": 2,
        "rps20": 9.11,
        "rps60": 95.82,
        "rps120": 94.03,
        "rps250": 95.61,
        "ma10": 1021.05,
        "vcp_quality": null,
        "ma5": 884.71,
        "ma20": 1292.12,
        "dist_ma5_pct": -89.7,
        "dist_ma10_pct": -91.1,
        "dist_ma20_pct": -92.9
      },
      {
        "code": "002203",
        "code_full": "002203.SZ",
        "name": "海亮股份",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 395.3278,
        "pe": 18.5,
        "risks_count": 5,
        "rps20": 25.45,
        "rps60": 94.3,
        "rps120": 93.89,
        "rps250": 90.21,
        "ma10": 17.87,
        "vcp_quality": null,
        "ma5": 17.84,
        "ma20": 19.15,
        "dist_ma5_pct": -0.5,
        "dist_ma10_pct": -0.6,
        "dist_ma20_pct": -7.2
      },
      {
        "code": "600428",
        "code_full": "600428.SH",
        "name": "中远海特",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 301.2825,
        "pe": 24.3,
        "risks_count": 0,
        "rps20": 99.49,
        "rps60": 95.44,
        "rps120": 93.79,
        "rps250": 89.66,
        "ma10": 10.91,
        "vcp_quality": null,
        "ma5": 10.99,
        "ma20": 9.97,
        "dist_ma5_pct": 2.2,
        "dist_ma10_pct": 3.0,
        "dist_ma20_pct": 12.8
      },
      {
        "code": "600961",
        "code_full": "600961.SH",
        "name": "株冶集团",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 234.1008,
        "pe": 21.9,
        "risks_count": 2,
        "rps20": 41.11,
        "rps60": 88.84,
        "rps120": 93.69,
        "rps250": 93.81,
        "ma10": 22.85,
        "vcp_quality": null,
        "ma5": 22.85,
        "ma20": 26.1,
        "dist_ma5_pct": -0.8,
        "dist_ma10_pct": -0.8,
        "dist_ma20_pct": -13.2
      },
      {
        "code": "601168",
        "code_full": "601168.SH",
        "name": "西部矿业",
        "source_date": "2026/07/29",
        "highlights_count": 8,
        "market_cap": 873.3695,
        "pe": 19.0,
        "risks_count": 0,
        "rps20": 97.49,
        "rps60": 88.72,
        "rps120": 93.67,
        "rps250": 94.58,
        "ma10": 35.34,
        "vcp_quality": null,
        "ma5": 37.11,
        "ma20": 32.57,
        "dist_ma5_pct": -0.5,
        "dist_ma10_pct": 4.4,
        "dist_ma20_pct": 13.3
      },
      {
        "code": "000725",
        "code_full": "000725.SZ",
        "name": "京东方A",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 1985.576,
        "pe": 25.5,
        "risks_count": 2,
        "rps20": 68.63,
        "rps60": 95.72,
        "rps120": 93.63,
        "rps250": 85.01,
        "ma10": 29.65,
        "vcp_quality": null,
        "ma5": 26.24,
        "ma20": 35.08,
        "dist_ma5_pct": -79.6,
        "dist_ma10_pct": -81.9,
        "dist_ma20_pct": -84.7
      },
      {
        "code": "002975",
        "code_full": "002975.SZ",
        "name": "博杰股份",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 144.3179,
        "pe": 6.4,
        "risks_count": 2,
        "rps20": 3.54,
        "rps60": 95.74,
        "rps120": 93.46,
        "rps250": 97.82,
        "ma10": 86.23,
        "vcp_quality": null,
        "ma5": 83.22,
        "ma20": 104.27,
        "dist_ma5_pct": -7.4,
        "dist_ma10_pct": -10.7,
        "dist_ma20_pct": -26.1
      },
      {
        "code": "688376",
        "code_full": "688376.SH",
        "name": "美埃科技",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 80.9212,
        "pe": 3.7,
        "risks_count": 1,
        "rps20": 55.62,
        "rps60": 86.73,
        "rps120": 93.24,
        "rps250": 90.98,
        "ma10": 68.55,
        "vcp_quality": null,
        "ma5": 66.83,
        "ma20": 84.94,
        "dist_ma5_pct": -2.5,
        "dist_ma10_pct": -5.0,
        "dist_ma20_pct": -23.3
      },
      {
        "code": "300323",
        "code_full": "300323.SZ",
        "name": "华灿光电",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 162.1376,
        "pe": 14.1,
        "risks_count": 2,
        "rps20": 11.66,
        "rps60": 95.18,
        "rps120": 93.14,
        "rps250": 87.66,
        "ma10": 11.45,
        "vcp_quality": null,
        "ma5": 11.17,
        "ma20": 14.34,
        "dist_ma5_pct": -3.5,
        "dist_ma10_pct": -5.8,
        "dist_ma20_pct": -24.8
      },
      {
        "code": "002245",
        "code_full": "002245.SZ",
        "name": "蔚蓝锂芯",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 258.1951,
        "pe": 18.1,
        "risks_count": 2,
        "rps20": 30.4,
        "rps60": 96.45,
        "rps120": 92.96,
        "rps250": 90.8,
        "ma10": 16.74,
        "vcp_quality": null,
        "ma5": 16.49,
        "ma20": 18.63,
        "dist_ma5_pct": -2.7,
        "dist_ma10_pct": -4.1,
        "dist_ma20_pct": -13.8
      },
      {
        "code": "688392",
        "code_full": "688392.SH",
        "name": "骄成超声",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 138.8685,
        "pe": 3.8,
        "risks_count": 1,
        "rps20": 69.05,
        "rps60": 91.25,
        "rps120": 92.84,
        "rps250": 96.8,
        "ma10": 153.52,
        "vcp_quality": null,
        "ma5": 147.32,
        "ma20": 183.08,
        "dist_ma5_pct": -9.0,
        "dist_ma10_pct": -12.7,
        "dist_ma20_pct": -26.8
      },
      {
        "code": "300373",
        "code_full": "300373.SZ",
        "name": "扬杰科技",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 445.1648,
        "pe": 12.5,
        "risks_count": 0,
        "rps20": 38.87,
        "rps60": 89.04,
        "rps120": 92.42,
        "rps250": 91.44,
        "ma10": 92.58,
        "vcp_quality": null,
        "ma5": 89.87,
        "ma20": 110.88,
        "dist_ma5_pct": -2.5,
        "dist_ma10_pct": -5.4,
        "dist_ma20_pct": -21.0
      },
      {
        "code": "688401",
        "code_full": "688401.SH",
        "name": "路维光电",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 119.1144,
        "pe": 3.9,
        "risks_count": 0,
        "rps20": 38.79,
        "rps60": 93.24,
        "rps120": 91.68,
        "rps250": 91.69,
        "ma10": 65.71,
        "vcp_quality": null,
        "ma5": 65.27,
        "ma20": 77.2,
        "dist_ma5_pct": -4.0,
        "dist_ma10_pct": -4.6,
        "dist_ma20_pct": -18.8
      },
      {
        "code": "688256",
        "code_full": "688256.SH",
        "name": "寒武纪",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 6549.5144,
        "pe": 6.0,
        "risks_count": 0,
        "rps20": 61.8,
        "rps60": 98.17,
        "rps120": 91.59,
        "rps250": 95.77,
        "ma10": 1232.87,
        "vcp_quality": null,
        "ma5": 1197.98,
        "ma20": 1340.38,
        "dist_ma5_pct": -4.3,
        "dist_ma10_pct": -7.0,
        "dist_ma20_pct": -14.4
      },
      {
        "code": "688331",
        "code_full": "688331.SH",
        "name": "荣昌生物",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 629.0537,
        "pe": 4.3,
        "risks_count": 1,
        "rps20": 96.48,
        "rps60": 92.99,
        "rps120": 91.55,
        "rps250": 95.37,
        "ma10": 123.59,
        "vcp_quality": null,
        "ma5": 120.99,
        "ma20": 130.32,
        "dist_ma5_pct": -2.2,
        "dist_ma10_pct": -4.3,
        "dist_ma20_pct": -9.2
      },
      {
        "code": "000977",
        "code_full": "000977.SZ",
        "name": "浪潮信息",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 1014.4237,
        "pe": 26.1,
        "risks_count": 1,
        "rps20": 99.39,
        "rps60": 95.08,
        "rps120": 91.49,
        "rps250": 86.67,
        "ma10": 510.74,
        "vcp_quality": null,
        "ma5": 450.09,
        "ma20": 524.99,
        "dist_ma5_pct": -84.7,
        "dist_ma10_pct": -86.5,
        "dist_ma20_pct": -86.8
      },
      {
        "code": "603162",
        "code_full": "603162.SH",
        "name": "海通发展",
        "source_date": "2026/07/30",
        "highlights_count": 5,
        "market_cap": 146.1336,
        "pe": 3.3,
        "risks_count": 2,
        "rps20": 93.05,
        "rps60": 89.4,
        "rps120": 91.21,
        "rps250": 91.12,
        "ma10": 10.77,
        "vcp_quality": null,
        "ma5": 11.03,
        "ma20": 10.32,
        "dist_ma5_pct": 0.1,
        "dist_ma10_pct": 2.5,
        "dist_ma20_pct": 6.9
      },
      {
        "code": "603156",
        "code_full": "603156.SH",
        "name": "养元饮品",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 470.7137,
        "pe": 8.4,
        "risks_count": 2,
        "rps20": 44.93,
        "rps60": 93.16,
        "rps120": 90.85,
        "rps250": 87.25,
        "ma10": 36.26,
        "vcp_quality": null,
        "ma5": 36.77,
        "ma20": 40.87,
        "dist_ma5_pct": 1.6,
        "dist_ma10_pct": 3.0,
        "dist_ma20_pct": -8.6
      },
      {
        "code": "603259",
        "code_full": "603259.SH",
        "name": "药明康德",
        "source_date": "2026/07/29",
        "highlights_count": 9,
        "market_cap": 3744.0185,
        "pe": 8.2,
        "risks_count": 0,
        "rps20": 98.91,
        "rps60": 93.84,
        "rps120": 90.81,
        "rps250": 93.26,
        "ma10": 124.81,
        "vcp_score": 52,
        "vcp_contraction_ratio": 0.99,
        "vcp_last_depth": 13.4,
        "vcp_dist_peak_pct": 6.4,
        "vcp_nearest_ma": "MA10",
        "vcp_nearest_ma_dist": 1.4,
        "vcp_vol_declining": true,
        "vcp_num_contractions": 6,
        "vcp_depths": "14%→16%→8%→20%→9%→13%",
        "vcp_quality": "SETUP",
        "ma5": 125.33,
        "ma20": 124.65,
        "dist_ma5_pct": 0.9,
        "dist_ma10_pct": 1.4,
        "dist_ma20_pct": 1.5
      },
      {
        "code": "603296",
        "code_full": "603296.SH",
        "name": "华勤技术",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 1194.7668,
        "pe": 2.9,
        "risks_count": 1,
        "rps20": 94.95,
        "rps60": 95.02,
        "rps120": 90.35,
        "rps250": 86.75,
        "ma10": 82.29,
        "vcp_quality": null,
        "ma5": 86.36,
        "ma20": 78.62,
        "dist_ma5_pct": -3.1,
        "dist_ma10_pct": 1.7,
        "dist_ma20_pct": 6.4
      },
      {
        "code": "688981",
        "code_full": "688981.SH",
        "name": "中芯国际",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 10528.9353,
        "pe": 6.0,
        "risks_count": 0,
        "rps20": 94.53,
        "rps60": 93.74,
        "rps120": 88.14,
        "rps250": 87.32,
        "ma10": 145.15,
        "vcp_quality": null,
        "ma5": 140.04,
        "ma20": 150.3,
        "dist_ma5_pct": -6.5,
        "dist_ma10_pct": -9.8,
        "dist_ma20_pct": -12.9
      },
      {
        "code": "002138",
        "code_full": "002138.SZ",
        "name": "顺络电子",
        "source_date": "2026/07/29",
        "highlights_count": 6,
        "market_cap": 323.3337,
        "pe": 19.1,
        "risks_count": 1,
        "rps20": 10.08,
        "rps60": 89.2,
        "rps120": 88.08,
        "rps250": 85.27,
        "ma10": 42.66,
        "vcp_quality": null,
        "ma5": 43.11,
        "ma20": 50.37,
        "dist_ma5_pct": 0.1,
        "dist_ma10_pct": 1.2,
        "dist_ma20_pct": -14.3
      },
      {
        "code": "300811",
        "code_full": "300811.SZ",
        "name": "铂科新材",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 224.1667,
        "pe": 6.5,
        "risks_count": 3,
        "rps20": 8.42,
        "rps60": 90.61,
        "rps120": 88.06,
        "rps250": 93.02,
        "ma10": 64.25,
        "vcp_quality": null,
        "ma5": 62.54,
        "ma20": 75.58,
        "dist_ma5_pct": -4.1,
        "dist_ma10_pct": -6.7,
        "dist_ma20_pct": -20.7
      },
      {
        "code": "301345",
        "code_full": "301345.SZ",
        "name": "涛涛车业",
        "source_date": "2026/07/29",
        "highlights_count": 7,
        "market_cap": 246.778,
        "pe": 3.3,
        "risks_count": 1,
        "rps20": 98.38,
        "rps60": 91.81,
        "rps120": 87.73,
        "rps250": 98.36,
        "ma10": 248.01,
        "vcp_quality": null,
        "ma5": 247.18,
        "ma20": 246.73,
        "dist_ma5_pct": -2.0,
        "dist_ma10_pct": -2.3,
        "dist_ma20_pct": -1.8
      },
      {
        "code": "002056",
        "code_full": "002056.SZ",
        "name": "横店东磁",
        "source_date": "2026/07/29",
        "highlights_count": 4,
        "market_cap": 327.7825,
        "pe": 20.0,
        "risks_count": 1,
        "rps20": 38.22,
        "rps60": 89.08,
        "rps120": 85.22,
        "rps250": 88.57,
        "ma10": 22.22,
        "vcp_quality": null,
        "ma5": 21.38,
        "ma20": 25.43,
        "dist_ma5_pct": -2.3,
        "dist_ma10_pct": -6.0,
        "dist_ma20_pct": -17.9
      },
      {
        "code": "688183",
        "code_full": "688183.SH",
        "name": "生益电子",
        "source_date": "2026/07/29",
        "highlights_count": 5,
        "market_cap": 690.1752,
        "pe": 5.4,
        "risks_count": 0,
        "rps20": 29.29,
        "rps60": 92.87,
        "rps120": 85.1,
        "rps250": 97.73,
        "ma10": 103.69,
        "vcp_quality": null,
        "ma5": 96.51,
        "ma20": 114.09,
        "dist_ma5_pct": -3.7,
        "dist_ma10_pct": -10.4,
        "dist_ma20_pct": -18.6
      }
    ]
  },
  "enriched_candidates": [
    {
      "code": "688146.SH",
      "fetch_time": "2026-07-31T11:40:49+0800",
      "name": "中船特气",
      "pe": 305.8665,
      "pb": 26.2479,
      "ps_ttm": 50.4736,
      "pcf_ttm": 1532.0737,
      "valuation_percentile": 96.55,
      "total_shares": 529411765,
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
        "科技龙头指数",
        "双创100指数",
        "QFII重仓指数",
        "半导体精选指数",
        "双百企业指数",
        "国家大基金指数",
        "半导体材料指数",
        "对日反制指数",
        "央企电子指数",
        "工业气体指数",
        "六氟化钨指数"
      ],
      "score_company": 8.5,
      "score_trend": 8.5,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 半导体材料 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 171% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.6% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 9.1% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "解禁",
          "text": "2026年10月21日，解禁 3.84亿股 ，占总股本 73% ，若股东减持，股价或受影响。"
        },
        {
          "tag": "波动",
          "text": "近3天，日均换手率 18% ，短线资金追逐，波动风险较高。"
        }
      ],
      "events": [
        {
          "content": "2026/10/21解禁3.84亿股，占总股本72.62%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-10-21"
        },
        {
          "content": "09:39 光刻机板块再度走弱，中船特气、捷众科技跌超8%，波长光电、东方嘉盛、茂莱光学跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "01:16 截至7月28日，首批QFII已进入14家上市公司前十大流通股东名单，持仓总市值约119.95亿元。其中，瑞银集团二季度新进宁德时代2736.66万股。QFII二季度加仓金煤科技、中兰环保，减仓沃华医药、优彩资源，其余10只个股为新进。从业绩看，昊志机电上半年净利润同比增长266.57%，中船特气、海南矿业、沃华医药净利润增速均超50%，金煤科技实现扭亏为盈。\n优彩资源上半年净利润同比增长103.87%。二季度以来，融资资金加仓中船特气、宁德时代、昊志机电均超8亿元。中船特气表示，目前六氟化钨产能为2000吨/年，正有序推进产能建设。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "公司发布2026半年报报告，股价盘中下跌 -10.94%",
          "tags": [
            "股价下跌"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1607244514.48,
      "revenue_yoy": 0.148987,
      "operating_profit": 268034217.06,
      "operating_profit_yoy": -0.011596,
      "net_profit": 245496529.29,
      "net_profit_yoy": 0.03984,
      "gross_profit": 474378970.24,
      "gross_profit_yoy": 0.114345,
      "cogs": 1132865544.24,
      "gross_margin": 29.52,
      "pe_forward": null,
      "valuation_history_days": 306,
      "valuation_history_from": "20250421",
      "current_price": 301.17,
      "price": 301.17,
      "ma5": 264.52,
      "ma10": 245.14,
      "ma20": 279.88,
      "dist_ma5_pct": 13.9,
      "dist_ma10_pct": 22.9,
      "dist_ma20_pct": 7.6,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 20.91,
        "pct_float": 5.07,
        "chg5_pct": -3.31,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688498.SH",
      "fetch_time": "2026-07-31T11:40:49+0800",
      "name": "源杰科技",
      "pe": 396.7935,
      "pb": 57.3187,
      "ps_ttm": 161.9566,
      "pcf_ttm": 723.2038,
      "valuation_percentile": 75.2,
      "total_shares": 124500377,
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
        "QFII重仓指数",
        "成交额TOP20指数",
        "股权激励指数",
        "芯片指数",
        "半导体精选指数",
        "外资企业指数",
        "光模块(CPO)指数",
        "万得预增指数",
        "光电路交换机(OCS)指数",
        "光芯片指数"
      ],
      "score_company": 8.8,
      "score_trend": 7.3,
      "score_value": 5.0,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 分立器件 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 1295% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 4.9% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 10家 机构给出评级，其中 60% 为“买入”，距目标价的上涨空间为 55% 。"
        },
        {
          "tag": "预测",
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 2.4% ，较受外资机构青睐；公募基金持股 28% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月20日大跌 -15.3% ，且成交额为近20日均值的 1.52倍 ，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "2027/03/15解禁90.35万股，占总股本0.73%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2027-03-15"
        },
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "09:48 分立器件板块持续走高，炬光科技、长光华芯、燕东微涨超10%，锴威特、东微半导、宏微科技、源杰科技、新洁能等跟涨。",
          "tags": [
            "快讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 383249487.47,
      "revenue_yoy": 1.150938,
      "operating_profit": 116982116.09,
      "operating_profit_yoy": 21.73919,
      "net_profit": 105892793.49,
      "net_profit_yoy": 193.486456,
      "gross_profit": 209876825.11,
      "gross_profit_yoy": 2.966991,
      "cogs": 173372662.36,
      "gross_margin": 54.76,
      "pe_forward": null,
      "valuation_history_days": 384,
      "valuation_history_from": "20241223",
      "current_price": 1228.0,
      "price": 1228.0,
      "ma5": 1352.4,
      "ma10": 1457.24,
      "ma20": 1595.56,
      "dist_ma5_pct": -9.2,
      "dist_ma10_pct": -15.7,
      "dist_ma20_pct": -23.0,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 26.58,
        "pct_float": 2.13,
        "chg5_pct": -21.73,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300604.SZ",
      "fetch_time": "2026-07-31T11:40:49+0800",
      "name": "长川科技",
      "pe": 108.842,
      "pb": 34.0377,
      "ps_ttm": 29.2411,
      "pcf_ttm": 738.065,
      "valuation_percentile": 85.26,
      "total_shares": 634418614,
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
        "HALO指数",
        "TMT指数",
        "科技龙头指数",
        "双创100指数",
        "华为平台指数",
        "半导体产业指数",
        "股权激励指数",
        "集成电路指数",
        "芯片指数",
        "半导体精选指数",
        "国家大基金指数",
        "半导体设备指数",
        "华为合作半导体企业指数"
      ],
      "score_company": 8.9,
      "score_trend": 7.8,
      "score_value": 4.2,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年06月23日，业绩超预期引发股价大幅上涨，当日收涨 4.06% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 89% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 18% ，投入资本回报率为 12% ，盈利能力很强。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 5.9% ，很受外资机构青睐；公募基金持股 24% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月10日大跌 -5.8% ，且成交额为近20日均值的 1.58倍 ，抛压很重。"
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
          "content": "15:03 7月28日A股四大指数集体下跌，创业板指盘中跌6.51%，上证指数跌1.29%，深证成指跌4.10%，沪深300跌2.71%。算力硬件产业链下挫，存储器、CPO、PCB方向领跌。创业板ETF富国(159971)盘中跌6.60%，成交额2.17亿元，换手率11.12%，规模19.53亿元。该ETF前5个交易日累计上涨4.4%，近5日均成交1.63亿元，主力资金连续4个交易日净流出。根据2026年二季报，创业板ETF富国前十大权重股中，中际旭创跌13.68%，宁德时代跌1.66%，新易盛跌15.09%，胜宏科技跌10.73%，天孚通信跌11.72%。持仓方面，2026年二季度新进重仓股为三环集团、江波龙、长川科技，汇川技术、迈瑞医疗、温氏股份退出前十大。该ETF综合费率0.20%/年，配有场外联接基金。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "长川科技：杭州长川科技股份有限公司关于签署募集资金三方及四方监管协议的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "20:36 7月27日，长鑫科技在科创板挂牌交易，发行价8.66元，收盘价49元，涨幅465%，市值达3.28万亿元，单日成交额1412亿元。浙江资本参与了长鑫科技的投资，其中阿里云计算有限公司持股3.85%，阿里网络技术有限公司持股1.12%，浙江国资旗下的浙江富浙通过国家集成电路产业投资基金二期参与投资，宁波国资通过甬欣燕创基金参与了C轮融资。\n长鑫科技上市带动了产业链上下游企业，包括中国巨石、江丰电子、长川科技等。浙江力积存储科技股份有限公司正开展高带宽内存研发。浙江省工信院数字所负责人徐精兵表示，浙江需加强芯片、存储、光通信等硬件基础设施层产业发展。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "长川科技：国浩律师（杭州）事务所关于杭州长川科技股份有限公司2025年度向特定对象发行A股股票发行过程及认购对象合规性的法律意见书",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 3778887661.52,
      "revenue_yoy": 0.490451,
      "operating_profit": 864293672.17,
      "operating_profit_yoy": 1.25081,
      "net_profit": 863754995.63,
      "net_profit_yoy": 1.285267,
      "gross_profit": 2058787423.69,
      "gross_profit_yoy": 0.448563,
      "cogs": 1720100237.83,
      "gross_margin": 54.48,
      "pe_forward": null,
      "valuation_history_days": 300,
      "valuation_history_from": "20210802",
      "current_price": 271.0,
      "price": 271.0,
      "ma5": 289.37,
      "ma10": 291.08,
      "ma20": 308.02,
      "dist_ma5_pct": -6.3,
      "dist_ma10_pct": -6.9,
      "dist_ma20_pct": -12.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 29.26,
        "pct_float": 2.43,
        "chg5_pct": -25.69,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301377.SZ",
      "fetch_time": "2026-07-31T11:40:49+0800",
      "name": "鼎泰高科",
      "pe": 249.1694,
      "pb": 22.9103,
      "ps_ttm": 61.1158,
      "pcf_ttm": 615.201,
      "valuation_percentile": 91.47,
      "total_shares": 424044934,
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
          "name": "金属制品",
          "level": 3
        }
      ],
      "concepts": [
        "双创100指数",
        "专精特新小巨人主题指数",
        "股权激励指数",
        "专精特新小巨人指数",
        "通用机械精选指数",
        "仪器仪表精选指数"
      ],
      "score_company": 9.5,
      "score_trend": 5.3,
      "score_value": 3.9,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 金属制品 行业龙头企业。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 28% ，最新季度归母净利润同比增长 370% ，成长能力很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 15% ，投入资本回报率为 14% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 5.5% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 4.4% ，很受外资机构青睐；公募基金持股 19% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月29日大跌 -6.14% ，且成交额为近20日均值的 1.71倍 ，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "2027/05/24解禁3.13亿股，占总股本73.71%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2027-05-24"
        },
        {
          "content": "预计2026/08/20发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-20"
        },
        {
          "content": "09:21 港股开盘，恒生指数涨0.26%，恒生科技指数涨0.43%。个股方面，新东方-S涨14.68%，明略科技-W涨8.7%，途虎-W涨4.88%，东方甄选涨3.86%，基本半导体涨3.56%；鼎泰高科跌5.17%，ASMPT跌4.75%，卧安机器人跌3.33%，华虹宏力跌3.14%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "鼎泰高科：关于H股配发结果的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1457322044.31,
      "revenue_yoy": 0.291296,
      "operating_profit": 318744275.03,
      "operating_profit_yoy": 0.631179,
      "net_profit": 280947751.9,
      "net_profit_yoy": 0.628107,
      "gross_profit": 592010724.12,
      "gross_profit_yoy": 0.474263,
      "cogs": 865311320.19,
      "gross_margin": 40.62,
      "pe_forward": null,
      "valuation_history_days": 406,
      "valuation_history_from": "20241122",
      "current_price": 361.28,
      "price": 361.28,
      "ma5": 389.43,
      "ma10": 402.52,
      "ma20": 450.7,
      "dist_ma5_pct": -7.2,
      "dist_ma10_pct": -10.2,
      "dist_ma20_pct": -19.8,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.02,
        "pct_float": 1.53,
        "chg5_pct": 2.54,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "002980.SZ",
      "fetch_time": "2026-07-31T11:40:49+0800",
      "name": "华盛昌",
      "pe": 164.1383,
      "pb": 11.2897,
      "ps_ttm": 16.3957,
      "pcf_ttm": null,
      "valuation_percentile": 94.23,
      "total_shares": 189401160,
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
          "name": "电工仪器仪表",
          "level": 3
        }
      ],
      "concepts": [
        "QFII重仓指数",
        "AI应用指数",
        "预期提升指数",
        "光模块(CPO)指数",
        "光通信指数",
        "光伏指数",
        "智能体指数",
        "核废水指数",
        "触板指数",
        "抗核辐射指数"
      ],
      "score_company": 7.2,
      "score_trend": 6.4,
      "score_value": 3.7,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月15日，业绩超预期引发股价跳空高开，但目前股价缺口已回补。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 19% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 1694万元 ，较上期增长 107% ，占2025年营收 2.1% ，在手订单充足。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 5.3% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月17日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月22日 至今陷入调整，资金有出逃可能。"
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
          "content": "07:39 国家电网今年上半年完成固定资产投资超3100亿元，同比增长12.6%；南方电网完成固定资产投资近893亿元，同比增长14.79%。国家能源局表示，“十五五”期间全国电网固定资产投资将超5万亿元。国家电网、南方电网及内蒙古电力集团均已披露“十五五”期间的投资规划，旨在加强新型电力系统建设，推动跨区输电通道与新能源配套工程落地。\n国家发展改革委与国家能源局发布《可再生能源发展“十五五”规划》，提出适度超前推进电网基础设施建设。受政策及全球电力需求增长驱动，电网设备行业市场规模预计持续扩大。今年以来，华盛昌、杭电股份等22家电网设备公司累计涨幅超过10%。其中，华盛昌上半年预计净利润同比增长61.02%至84.02%；杭电股份上半年预计净利润同比增长852.03%至957.82%。\n远东股份上半年电池储能及相关业务订单同比增长262.14%。截至7月23日，电网设备行业融资余额合计近413亿元，较2025年末增长超7.5%。其中，华明装备、南网科技、思源电气、东方电子等16家公司今年以来机构调研家数不低于10家，且融资余额较去年末增幅超过10%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "22:17 爱丽家居公告称，拟以自有及自筹资金收购欧康诺不低于77.08%股权，整体估值不超过6.5亿元。同时，控股股东博华企管拟向欧康诺实控人赵铭及其一致行动人转让20%上市公司股份。欧康诺主营存储测试设备，2025年净利润610.68万元，2026年上半年净利润为3719.67万元。交易双方约定四年业绩承诺期（2026-2029年），扣非净利润累计不低于2.3亿元。\n本次转让的20%股份中，15%锁定36个月，5%与业绩承诺挂钩。若未达业绩承诺或发生减值，该5%股份将用于抵扣补偿义务。法律人士指出，仅5%股权用于业绩补偿比例偏低，建议公司披露分层转让的商业逻辑及风险约束措施。",
          "tags": [
            "资讯"
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
      "revenue": 530015857.54,
      "revenue_yoy": -0.054925,
      "operating_profit": 70665126.89,
      "operating_profit_yoy": -0.421411,
      "net_profit": 64106611.6,
      "net_profit_yoy": -0.419854,
      "gross_profit": 232366901.99,
      "gross_profit_yoy": -0.1163,
      "cogs": 297648955.55,
      "gross_margin": 43.84,
      "pe_forward": null,
      "valuation_history_days": 260,
      "valuation_history_from": "20220418",
      "current_price": 70.59,
      "price": 70.59,
      "ma5": 79.53,
      "ma10": 86.85,
      "ma20": 94.87,
      "dist_ma5_pct": -11.2,
      "dist_ma10_pct": -18.7,
      "dist_ma20_pct": -25.6,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      }
    },
    {
      "code": "688630.SH",
      "fetch_time": "2026-07-31T11:40:49+0800",
      "name": "芯碁微装",
      "pe": 145.2562,
      "pb": 9.1799,
      "ps_ttm": 29.9449,
      "pcf_ttm": 174.8975,
      "valuation_percentile": 85.96,
      "total_shares": 146505116,
      "industries": [
        {
          "name": "机械设备",
          "level": 1
        },
        {
          "name": "专用设备",
          "level": 2
        },
        {
          "name": "其他专用设备",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "双创100指数",
        "半导体产业指数",
        "专精特新小巨人主题指数",
        "股权激励指数",
        "专精特新小巨人指数",
        "万得预增指数",
        "半导体设备指数",
        "光刻机指数",
        "专用设备精选指数"
      ],
      "score_company": 9.1,
      "score_trend": 7.2,
      "score_value": 4.3,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 其他专用设备 行业龙头企业。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 34% ，最新季度归母净利润同比增长 109% ，成长能力很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 11% ，投入资本回报率为 12% ，盈利能力很强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 1.2亿元 ，较上期增长 109% ，占2025年营收 8.4% ，在手订单充足。"
        },
        {
          "tag": "评级",
          "text": "近90天， 8家 机构给出评级，其中 88% 为“买入”，距目标价的上涨空间为 37% 。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 2.9% ，较受外资机构青睐；公募基金持股 10% ，很受内资机构青睐。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/27发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-27"
        },
        {
          "content": "16:10 港股收盘，恒生指数涨0.2%，恒生科技指数跌1.25%。恒指港股通ETF银华（159318）涨0.08%，港股通科技ETF鹏华（159751）跌1.55%。板块方面，可选消费经销Ⅳ、可选消费经销Ⅲ板块涨幅靠前；焦炭加工Ⅲ、焦炭加工Ⅳ板块跌幅靠前。个股方面，新东方-S涨18.84%，德适-B涨14.8%，国富量子涨11.18%，旺山旺水-B涨10.58%，安克创新涨10.25%；明略科技-W跌27.66%，芯碁微装跌17.39%，智谱跌16.55%，天数智芯跌14.71%，映恩生物-B跌13.7%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "12:01 港股午间收盘，恒生指数跌0.05%，恒生科技指数跌1.14%。恒指港股通ETF银华（159318）持平，港股通科技ETF鹏华（159751）跌1.89%。板块方面，建筑产品Ⅲ、建筑产品Ⅳ板块涨幅靠前；IT咨询与其他服务、IT服务板块跌幅靠前。个股方面，新东方-S涨17.08%，安克创新涨9.88%，中升控股涨7.78%，江南布衣涨7.68%，旺山旺水-B涨7.62%；明略科技-W跌17.55%，智谱跌16.46%，芯碁微装跌13.42%，剑桥科技跌12.76%，埃斯顿跌10.94%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "芯碁微装：国泰海通证券股份有限公司关于公司向特定对象发行股票募投项目结项并将节余募集资金永久补充流动资金及注销相关募集资金专户、理财产品专用结算账户的专项核查意见",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "芯碁微装：关于向特定对象发行股票募投项目结项并将节余募集资金永久补充流动资金及注销相关募集资金专户、理财产品专用结算账户的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 933504506.54,
      "revenue_yoy": 0.300311,
      "operating_profit": 220138591.24,
      "operating_profit_yoy": 0.331095,
      "net_profit": 198812348.7,
      "net_profit_yoy": 0.282033,
      "gross_profit": 392940189.83,
      "gross_profit_yoy": 0.335179,
      "cogs": 540564316.71,
      "gross_margin": 42.09,
      "pe_forward": null,
      "valuation_history_days": 269,
      "valuation_history_from": "20230403",
      "current_price": 349.92,
      "price": 349.92,
      "ma5": 388.32,
      "ma10": 383.38,
      "ma20": 435.3,
      "dist_ma5_pct": -9.9,
      "dist_ma10_pct": -8.7,
      "dist_ma20_pct": -19.6,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.85,
        "pct_float": 2.24,
        "chg5_pct": -2.68,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002281.SZ",
      "fetch_time": "2026-07-31T11:40:49+0800",
      "name": "光迅科技",
      "pe": 131.8189,
      "pb": 9.8728,
      "ps_ttm": 10.9436,
      "pcf_ttm": 70.5427,
      "valuation_percentile": 97.32,
      "total_shares": 827848838,
      "industries": [
        {
          "name": "通信",
          "level": 1
        },
        {
          "name": "通信设备",
          "level": 2
        },
        {
          "name": "通信网络设备及器件",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "国企改革指数",
        "华为平台指数",
        "半导体产业指数",
        "新基建指数",
        "5G指数",
        "RCEP指数",
        "股权激励指数",
        "芯片指数",
        "AI算力指数",
        "AIPC指数",
        "国企混改指数",
        "量子技术指数",
        "光模块(CPO)指数",
        "数据中心互联指数",
        "东数西算指数",
        "央企通信指数"
      ],
      "score_company": 8.9,
      "score_trend": 7.1,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 56% ，利润成长性强。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 111% ，销售收入现金含量较强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 11亿元 ，较上期增长 154% ，占2025年营收 9.2% ，在手订单充足。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 4.7% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月17日大跌 -10% ，股价跌停，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "2026/12/16解禁1295.14万股，占总股本1.56%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-12-16"
        },
        {
          "content": "预计2026/08/20发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-20"
        },
        {
          "content": "21:20 2026年7月30日，华福证券发布机械设备行业研究报告，指出AI技术正在重构激光行业需求边界，推动产业跃迁。\n报告认为，激光技术正从传统加工工具向AI制造转型。传统激光产业受工业市场需求收缩影响，竞争加剧。2025年，人工智能的发展带动了激光在集成电路和半导体材料微加工领域的应用，中国市场增长动力主要来自AI催动的数据中心与高速通信需求、消费级激光产品放量及进口替代。随着AI算力需求爆发，数据中心光模块需求激增，CPO及CW激光器订单预期增长。激光产业链涵盖上游材料与器件、中游激光器制造及下游应用。上游激光芯片及光电器件准入门槛较高；中游半导体激光器泵浦源作为核心器件，占总成本30-80%。2025年全球激光设备市场销售收入约240亿美元，中国市场为958亿元。\nAI核心制造场景需求包括：PCB钻孔环节的激光钻孔机；TGV通孔环节的激光诱导深度刻蚀（LIDE）及直接激光烧蚀技术；以及光通信激光器环节，光模块作为AI网络端重要环节，其TOSA组件中的激光器需求持续增长。报告建议关注上游核心元器件厂商：源杰科技、长光华芯、仕佳光子、光迅科技、福晶科技、炬光科技、波长光电、腾景科技、光库科技、长进光子；中游激光器厂商：锐科激光、杰普特、英诺激光、德龙激光；下游激光设备厂商：大族激光、华工科技、大族数控、帝尔激光、联赢激光、海目星、亚威股份。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/31解禁637.03万股，占总股本0.77%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-07-31"
        },
        {
          "content": "光迅科技：武汉光迅科技股份有限公司薪酬与考核委员会2026年第二次会议意见",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 8531642135.18,
      "revenue_yoy": 0.58646,
      "operating_profit": 789786641.08,
      "operating_profit_yoy": 0.58836,
      "net_profit": 696937341.14,
      "net_profit_yoy": 0.537025,
      "gross_profit": 1974108982.75,
      "gross_profit_yoy": 0.548403,
      "cogs": 6557533152.43,
      "gross_margin": 23.14,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20210802",
      "current_price": 169.26,
      "price": 169.26,
      "ma5": 182.59,
      "ma10": 186.23,
      "ma20": 206.15,
      "dist_ma5_pct": -7.3,
      "dist_ma10_pct": -9.1,
      "dist_ma20_pct": -17.9,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 35.94,
        "pct_float": 3.02,
        "chg5_pct": -13.28,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688200.SH",
      "fetch_time": "2026-07-31T11:40:49+0800",
      "name": "华峰测控",
      "pe": 131.0344,
      "pb": 18.4826,
      "ps_ttm": 52.4272,
      "pcf_ttm": 280.7037,
      "valuation_percentile": 88.88,
      "total_shares": 200575083,
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
        "科技龙头指数",
        "双创100指数",
        "半导体产业指数",
        "具身智能指数",
        "股权激励指数",
        "芯片指数",
        "半导体精选指数",
        "可转债正股指数",
        "半导体设备指数",
        "模拟芯片指数",
        "可转债预案指数",
        "先进封装指数"
      ],
      "score_company": 9.0,
      "score_trend": 7.7,
      "score_value": 3.9,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 52% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 13% ，投入资本回报率为 13% ，盈利能力很强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 1.0亿元 ，较上期增长 31% ，占2025年营收 7.6% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 4.6% ，很受外资机构青睐；公募基金持股 20% ，很受内资机构青睐。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/31发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-31"
        },
        {
          "content": "2026/08/04解禁17.61万股，占总股本0.09%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-08-04"
        },
        {
          "content": "华峰测控：华峰测控关于“华峰转债”转股价格调整的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "14:55 7月27日，长鑫科技（688825）在上海证券交易所科创板挂牌上市。公司发行价为每股8.66元，募资净额295亿元。上市首日，长鑫科技开盘价报12.10元，截至午间收盘报13.05元。\n长鑫科技募资将投向存储晶圆产线技术改造、DRAM存储工艺升级及前沿技术研发。其中，约205亿元资金预计在未来两至三年内用于设备采购。科创半导体ETF华夏（588170）重仓股包括华海清科、中微公司、中科飞测、拓荆科技和华峰测控等设备标的。截至7月23日，科创半导体ETF华夏（588170）近20个交易日份额增加278.98亿份，最新份额达327.63亿份。长鑫科技目前DRAM月产能约12万片，募投项目达产后预计提升至约18万片。后续市场关注设备招标验证进度及晶圆代工企业的资本开支指引。\n截至发稿，科创半导体ETF华夏（588170）盘中上涨3.37%，报1.013元。上证科创板半导体材料设备主题指数（950125）同期上涨约3.13%。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 939315871.52,
      "revenue_yoy": 0.512102,
      "operating_profit": 421498300.38,
      "operating_profit_yoy": 0.840866,
      "net_profit": 386924067.95,
      "net_profit_yoy": 0.815747,
      "gross_profit": 697919022.35,
      "gross_profit_yoy": 0.485258,
      "cogs": 241396849.17,
      "gross_margin": 74.3,
      "pe_forward": null,
      "valuation_history_days": 269,
      "valuation_history_from": "20220218",
      "current_price": 360.82,
      "price": 360.82,
      "ma5": 366.01,
      "ma10": 375.4,
      "ma20": 435.17,
      "dist_ma5_pct": -1.4,
      "dist_ma10_pct": -3.9,
      "dist_ma20_pct": -17.1,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 3.99,
        "pct_float": 0.59,
        "chg5_pct": -1.65,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688308.SH",
      "fetch_time": "2026-07-31T11:40:51+0800",
      "name": "欧科亿",
      "pe": 45.7701,
      "pb": 4.9131,
      "ps_ttm": 7.6252,
      "pcf_ttm": null,
      "valuation_percentile": 72.13,
      "total_shares": 158781708,
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
          "name": "金属制品",
          "level": 3
        }
      ],
      "concepts": [
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "万得预增指数",
        "电路板指数",
        "对日反制指数",
        "通用机械精选指数",
        "仪器仪表精选指数"
      ],
      "score_company": 7.8,
      "score_trend": 5.8,
      "score_value": 5.1,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 2802% ，利润成长性强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 2506万元 ，较上期增长 61% ，占2025年营收 1.7% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 3.8% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月20日大跌 -20% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月23日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比为 62% ，销售收入现金含量很低。"
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
          "content": "17:35 国金证券观点认为，Q3科技产业主要驱动力在于英伟达Vera Rubin与谷歌TPU进入量产阶段，算力紧缺仍是核心矛盾。英伟达Vera Rubin NVL72正在全球加速部署，已在CoreWeave、Google Cloud、Microsoft Azure及Oracle云基础设施运行。TPU方面，Alphabet确认TPU系统销售已于Q2启动交付，预计2026年收入加速，2027年确认多数收入。供给端，HBM4三家供应商已认证量产，SK海力士称需求超供给；Alphabet上调2026年资本开支指引至1950-2050亿美元。\nAlphabet Q2财报显示，收入1198亿美元，同比增长24%；Google Cloud收入248亿美元，同比增长82%。资本开支449亿美元，其中六成投向服务器。TPU系统销售模式打开云服务外增长空间。产业链方面，机柜、PCB、光互联是主线，工业富联Rubin机柜Q3量产，Spectrum-6确立CPO为标配。电容方面，三星电机MLCC涨价信号明确，AI服务器高容值产品现货价格涨幅显著。\n国金证券列示相关标的：超核心供应商包括工业富联、胜宏科技；海外算力链包括中际旭创、新易盛、东山精密、江海股份、中钨高新、蓝思科技、东阳光、光智科技、先导基电、火炬电子、三环集团、欧科亿、天孚通信、鼎泰高科、领益智造、兆易创新、鹏鼎控股、唯科科技、海川智能、天岳先进、大普微、源杰科技、麦格米特、景旺电子、英维克、京东方等；国内算力链包括寒武纪、海光信息、长鑫科技、中芯国际、华虹半导体、中科曙光、浪潮信息、胜蓝股份、华勤技术、国科微、中国长城、晶科科技、罗曼股份、盈峰环境、芯原股份、亿田智能、豫能控股、星环科技、鸿日达、盛视科技、神州数码、润泽科技、大位科技、润建股份、奥飞数据、瑞晟智能、科华数据、潍柴重机、欧陆通、杰创智能、奥尼电子；大模型与云厂商包括智谱、MiniMax、阿里巴巴、腾讯控股、金山云、百度集团、优刻得、首都在线、网宿科技、云赛智联、青云科技等。风险提示：Rubin量产爬坡不及预期、TPU收入确认节奏风险、HBM与高端元器件供给瓶颈风险。\nVera Rubin平台由七颗芯片与五类机架托盘组成，英伟达官方确认其系统协同设计。Vera Rubin NVL72机柜已在CoreWeave、Google Cloud、Microsoft Azure与Oracle云基础设施运行，CoreWeave实测显示其每兆瓦token吞吐量达Grace Blackwell NVL72的10倍。\nRubin GPU采用双芯粒设计，搭载288GB HBM4，带宽22TB/s。第三代Transformer引擎支持NVFP4精度，算力较Blackwell大幅提升。Vera Rubin NVL144机柜由72颗Rubin GPU与36颗Vera CPU构成。HBM4方面，三星电子、SK海力士、美光三家供应商已通过认证并量产，预计2026年Q3全面规模化量产。\n英伟达定义G3.5存储层以优化KV Cache，CMX平台由BlueField-4 DPU管理，单柜管理约9600TB闪存。该平台旨在提升token生成速度与能效，使存储系统成为AI基础设施的关键环节。\nVera CPU专为数据搬运与Agent推理设计，Groq 3 LPX定位低时延推理加速器。Spectrum-6以太网交换机采用CPO技术，英伟达确认其为首款进入量产阶段的此类产品，相比可插拔收发器功耗降低5倍。\nAlphabet Q2财报显示，Google Cloud积压订单达5140亿美元。管理层上调2026年资本开支指引，并预告2027年将显著增长。TPU系统销售已于Q2启动交付，预计2027年进入收入放量期。\n机柜环节，工业富联Rubin整机柜Q3启动量产。PCB环节，Vera Rubin NVL144采用中央PCB中板，价值量较GB代际提升。光模块环节，ConnectX-9提升端口带宽至1.6Tb/s，CPO随Spectrum-6确立为官方标配。\n液冷与供电方面，Vera Rubin NVL144采用100%液冷设计，800VDC高压直流确立为参考架构。电容方面，三星电机已与大型科技企业签署AI服务器MLCC长期供货合同，高端高容MLCC供需紧张预计持续至2027年上半年。\n相关标的与风险提示同前文所述。报告由国金证券发布，分析师为刘高畅、郑元昊、孙恺祈。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "13:38 A股半导体材料板块近期表现活跃，科创新材料ETF（589180）成交额放量。中船特气披露2026年半年报，上半年实现营业收入19.04亿元，同比增长83.13%；归母净利润3.48亿元，同比增长95.63%；扣非净利润3.26亿元，同比增长117.08%。国联民生证券指出，AI性能提升驱动算力与功耗增加，带动AI金属材料需求扩张，叠加供给约束与国产替代，行业迎来需求与价格共振。\n开源证券分析认为，AI材料领域需关注具备盈利兑现能力的品种。半导体材料方面，硅片行业存在高端缺口；碳化硅有待需求导入；光刻胶高端产品依赖进口；电子特气国产替代稳步推进；溅射靶材高端品类产能爬坡。此外，PCB材料、光模块材料、光纤材料、被动元器件及液冷材料等细分领域均受技术升级与国产替代驱动，呈现不同程度的供需格局变化。\n基金投资存在风险，过往业绩不预示未来表现。科创新材料ETF（589180）标的指数为上证科创板新材料指数，2021年至2025年涨跌幅分别为46.14%、-35.84%、-27.61%、-15.92%、55.70%。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1023296780.65,
      "revenue_yoy": 0.143388,
      "operating_profit": 49261644.2,
      "operating_profit_yoy": -0.509262,
      "net_profit": 48140353.72,
      "net_profit_yoy": -0.461947,
      "gross_profit": 200180860.26,
      "gross_profit_yoy": -0.134136,
      "cogs": 823115920.39,
      "gross_margin": 19.56,
      "pe_forward": null,
      "valuation_history_days": 293,
      "valuation_history_from": "20221212",
      "current_price": 86.2,
      "price": 86.2,
      "ma5": 91.65,
      "ma10": 95.94,
      "ma20": 125.12,
      "dist_ma5_pct": -6.0,
      "dist_ma10_pct": -10.1,
      "dist_ma20_pct": -31.1,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 7.21,
        "pct_float": 5.82,
        "chg5_pct": -12.7,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002384.SZ",
      "fetch_time": "2026-07-31T11:40:51+0800",
      "name": "东山精密",
      "pe": 156.5082,
      "pb": 14.1045,
      "ps_ttm": 7.1493,
      "pcf_ttm": 62.9965,
      "valuation_percentile": 96.22,
      "total_shares": 1831607532,
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
          "name": "印制电路板",
          "level": 3
        }
      ],
      "concepts": [
        "A50指数",
        "TMT指数",
        "三新指数",
        "科技龙头指数",
        "人工智能+指数",
        "5G应用指数",
        "消费电子产业指数",
        "华为平台指数",
        "成交额TOP20指数",
        "新基建指数",
        "5G指数",
        "信创产业指数",
        "成交额TOP10指数",
        "元宇宙指数"
      ],
      "score_company": 8.9,
      "score_trend": 7.1,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 印制电路板 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 509% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 5.5% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 5.0% ，很受外资机构青睐；公募基金持股 21% ，很受内资机构青睐。"
        },
        {
          "tag": "回购",
          "text": "近1月，公司累计回购 12万股 ，占总股本比例 0.01% ，金额合计 2294万元 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月28日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "商誉",
          "text": "商誉占净资产 21% ，商誉减值风险较高。"
        }
      ],
      "events": [
        {
          "content": "2028/06/28解禁1.26亿股，占总股本6.86%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2028-06-28"
        },
        {
          "content": "预计2026/08/22发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-22"
        },
        {
          "content": "10:34 今日上午，AI硬件板块走低，中际旭创、新易盛、天孚通信、源杰科技、东山精密等股价下跌。中际旭创H股今日上市，盘中跌破980港元发行价。针对1.6T光模块价格降幅较大的传闻，中际旭创表示，公司1.6T产品平均销售价格远高于传言，行业不存在恶性竞争，需求旺盛且原材料紧缺，交付计划已排至2027年，部分客户已给出2028年指引。此外，中际旭创公告称，董事长兼总裁刘圣提议公司以40亿元至80亿元回购A股股票。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "公司发布回购公告，股价盘中上涨 8.23% ，股价收盘涨幅 6.09%",
          "tags": [
            "股价上涨"
          ]
        },
        {
          "content": "截至2026/07/28，公司累计回购 11.5万股 ，占总股本比例为 0.01% ，最高成交价为 201元/股 ，最低成交价为 199元/股 ，耗资 2294万元  （进行中）",
          "tags": [
            "公司回购流通股"
          ],
          "date": "2027-07-21"
        }
      ],
      "report_period": "20250930",
      "revenue": 27070627389.75,
      "revenue_yoy": 0.022834,
      "operating_profit": 1505435477.18,
      "operating_profit_yoy": 0.176449,
      "net_profit": 1223574692.49,
      "net_profit_yoy": 0.146902,
      "gross_profit": 3732385967.73,
      "gross_profit_yoy": 0.032792,
      "cogs": 23338241422.02,
      "gross_margin": 13.79,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20210802",
      "current_price": 179.78,
      "price": 179.78,
      "ma5": 197.64,
      "ma10": 216.52,
      "ma20": 228.7,
      "dist_ma5_pct": -9.0,
      "dist_ma10_pct": -17.0,
      "dist_ma20_pct": -21.4,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 109.81,
        "pct_float": 4.9,
        "chg5_pct": -19.31,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "000811.SZ",
      "fetch_time": "2026-07-31T11:40:51+0800",
      "name": "冰轮环境",
      "pe": 59.1381,
      "pb": 5.4039,
      "ps_ttm": 4.7604,
      "pcf_ttm": 43.4142,
      "valuation_percentile": 98.42,
      "total_shares": 992477985,
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
          "name": "制冷空调设备",
          "level": 3
        }
      ],
      "concepts": [
        "贷款回购指数",
        "双百企业指数",
        "氢能指数",
        "能源出海指数",
        "空气能热泵指数",
        "山东省国资指数",
        "燃料电池指数",
        "集装箱指数",
        "新能源设备指数",
        "通用机械精选指数",
        "仪器仪表精选指数",
        "冬奥会指数",
        "冷链物流指数",
        "地热指数",
        "余热利用指数",
        "核电通风与空气处理指数",
        "核电阀门指数",
        "地热能指数"
      ],
      "score_company": 9.0,
      "score_trend": 7.3,
      "score_value": 3.5,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 制冷空调设备 行业龙头企业。"
        },
        {
          "tag": "订单",
          "text": "合同负债 13亿元 ，较上期增长 3.7% ，占2025年营收 18% ，在手订单充足。"
        },
        {
          "tag": "评级",
          "text": "近90天， 7家 机构给出评级，其中 86% 为“买入”，距目标价的上涨空间为 84% 。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 4.2% ，很受外资机构青睐；公募基金持股 11% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月28日大跌 -9.99% ，股价跌停，抛压很重。"
        },
        {
          "tag": "商誉",
          "text": "商誉占净资产 12% ，商誉减值风险较高。"
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
          "content": "16:40 太平洋证券分析师指出，电子行业半年报业绩增长主要集中在存储、海外算力及半导体设备领域。存储板块受益于AI服务器需求提升及备货旺季，供给端存在缺口；半导体设备受全球扩产及国产替代驱动，订单增长具有持续性。传媒行业方面，游戏板块维持高景气，二季度上市公司业绩实现环比增长，估值处于历史较低水平，看好恺英网络。\n机械行业方面，液冷技术成为散热领域重点，冰轮环境受益于全球算力建设，合同负债创新高；宁波精达通过并购拓展北美液冷市场，订单增长显著。通信行业中，光纤板块受无人机及算力需求驱动，长飞光纤业绩表现超预期；光模块板块景气度回升，剑桥科技二季度业绩环比增长，中际旭创获推荐。\n计算机行业方面，算力链相关的服务器硬件及算力租赁业务业绩增长符合预期，海外算力投入持续，看好智微智能与联想集团。文中列举了电子、传媒、机械、通信及计算机各细分领域的参考研报信息及投资评级说明。\n列示了各行业相关研究报告的发布时间及作者信息，并声明本报告仅向签约客户提供，不构成投资建议，投资者需自主决策并承担风险。\n声明报告信息来源于公开资料，不对准确性作保证，太平洋证券及其关联机构可能持有相关证券头寸，版权归太平洋证券所有。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "于2026-07-17接待9位投资者调研。",
          "tags": [
            "机构调研"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是公司披露并购重组取得实质性进展，相关资产/资金安排和整合方案更明晰，有望增强高效节能装备业务规模与盈利预期。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 4834976275.63,
      "revenue_yoy": -0.024466,
      "operating_profit": 597858322.44,
      "operating_profit_yoy": 0.041605,
      "net_profit": 488069735.53,
      "net_profit_yoy": -0.037361,
      "gross_profit": 1347581743.7,
      "gross_profit_yoy": 0.014727,
      "cogs": 3487394531.93,
      "gross_margin": 27.87,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 33.46,
      "price": 33.46,
      "ma5": 741.76,
      "ma10": 852.14,
      "ma20": 1017.37,
      "dist_ma5_pct": -95.5,
      "dist_ma10_pct": -96.1,
      "dist_ma20_pct": -96.7,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.8795,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.22,
        "pct_float": 1.9,
        "chg5_pct": -15.59,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "605376.SH",
      "fetch_time": "2026-07-31T11:40:51+0800",
      "name": "博迁新材",
      "pe": 149.5612,
      "pb": 20.953,
      "ps_ttm": 27.7011,
      "pcf_ttm": 6378.3993,
      "valuation_percentile": 89.89,
      "total_shares": 261600000,
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
          "name": "镍",
          "level": 3
        }
      ],
      "concepts": [
        "资源股",
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "有色金属指数",
        "新能源指数",
        "举牌指数"
      ],
      "score_company": 8.3,
      "score_trend": 6.2,
      "score_value": 4.0,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 镍 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 50% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.9% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 2.9% ，较受外资机构青睐；公募基金持股 16% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月16日大跌 -10% ，股价跌停，抛压很重。"
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
          "content": "02:56 近期MLCC产业链调研显示，供需格局偏紧，主力企业产线满载，出厂价保持稳定。上游材料商订单充沛，部分企业扩产线已被客户提前锁定。离型膜、陶瓷粉及金属粉等主要原材料厂商产线开满，部分企业实行三班倒生产。受AI服务器等新兴应用需求带动，MLCC用量显著增加，相关材料出货量持续攀升。\n国瓷材料因原辅材料价格上涨，自7月27日起上调氧化锆粉体销售价格，涨幅约10%—40%。国内MLCC企业如三环集团表示，今年二季度起产品价格上调后未回调。三环集团预计2026年上半年盈利同比增长45%—65%，增长得益于行业景气度提升及产品价格修复。业内指出，AI服务器对高容MLCC需求形成虹吸效应，导致日韩厂商转产高容产品，推动行业涨价。\n业内人士认为，AI服务器带来的爆发式增量需求正推动MLCC进入新一轮景气周期。机构数据显示，AI服务器对MLCC的消耗量远高于手机和汽车。中商产业研究院预测，受新能源汽车、AI服务器及5G通信等需求拉动，全球MLCC市场规模至2030年将持续增长。上游原料厂商正竞相扩产，部分企业已与村田、三星电机等签署战略协议，新增产能获提前锁单。\n洁美科技正加速推进广东肇庆及天津基地离型膜产线建设，预计2026年底产能将达7.4亿平方米，并已启动安吉基地高端产品扩产计划。博迁新材拟投资约2.02亿元建设超细金属粉体材料扩产项目，以满足MLCC小型化、高容值需求。业内分析认为，本轮景气周期为国产MLCC产业链提供了国产替代机遇，随着产能落地，本土企业市场份额有望提升。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "博迁新材：江苏博迁新材料股份有限公司关于增加2026年度日常关联交易预计的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "博迁新材：江苏博迁新材料股份有限公司关于投资建设新项目的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "21:18 博迁新材（605376）今日涨停，全天换手率7.65%，成交额27.12亿元，振幅22.23%。因日振幅值达22.23%，该股登上龙虎榜。数据显示，机构专用席位合计买入1.04亿元，卖出1.02亿元，净买入235.71万元；沪股通专用席位买入1.38亿元，卖出4.04亿元，净卖出2.66亿元；营业部席位合计净买入2.07亿元。上榜前五大买卖营业部合计成交14.33亿元，净卖出5633.46万元。资金流向方面，今日主力资金净流入1434.28万元，其中特大单净流入6175.69万元，大单净流出4741.41万元。截至7月20日，两融余额为8.38亿元，其中融资余额8.32亿元，融券余额642.81万元。公司一季度实现营业收入4.10亿元，同比增长64.02%；净利润7162.63万元，同比增长49.64%。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 805335723.32,
      "revenue_yoy": 0.107872,
      "operating_profit": 168359785.42,
      "operating_profit_yoy": 0.844432,
      "net_profit": 151584153.31,
      "net_profit_yoy": 0.781687,
      "gross_profit": 254663675.87,
      "gross_profit_yoy": 0.665078,
      "cogs": 550672047.45,
      "gross_margin": 31.62,
      "pe_forward": null,
      "valuation_history_days": 293,
      "valuation_history_from": "20221209",
      "current_price": 144.58,
      "price": 144.58,
      "ma5": 143.4,
      "ma10": 145.99,
      "ma20": 189.04,
      "dist_ma5_pct": 0.8,
      "dist_ma10_pct": -1.0,
      "dist_ma20_pct": -23.5,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7475,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 7.14,
        "pct_float": 2.05,
        "chg5_pct": -1.99,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688347.SH",
      "fetch_time": "2026-07-31T11:40:51+0800",
      "name": "华虹宏力",
      "pe": 885.119,
      "pb": 9.6518,
      "ps_ttm": 24.2568,
      "pcf_ttm": 77.7717,
      "valuation_percentile": 91.67,
      "total_shares": 1737726402,
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
        "科技龙头指数",
        "双创100指数",
        "半导体产业指数",
        "芯片指数",
        "半导体精选指数",
        "浦东新区指数",
        "ASIC芯片指数",
        "晶圆产业指数",
        "模拟芯片指数",
        "半导体硅片指数"
      ],
      "score_company": 6.7,
      "score_trend": 7.5,
      "score_value": 3.9,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 513% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 14% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 12亿元 ，较上期增长 25% ，占2025年营收 6.9% ，在手订单充足。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 22% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月10日大跌 -7.65% ，且成交额为近20日均值的 1.57倍 ，抛压很重。"
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
          "content": "09:21 港股开盘，恒生指数跌0.08%，恒生科技指数涨0.3%。个股方面，中际旭创涨15.0%，长飞光纤光缆涨15.0%，兆易创新涨14.99%，华虹宏力涨14.98%，建滔集团涨14.97%；新东方-S跌7.97%，小米集团-W跌5.61%，珍酒李渡跌3.4%，蒙牛乳业跌3.24%，京东集团-SW跌3.19%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "华虹宏力：港股公告：董事会日期公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "09:48 科创50指数跌幅扩大至3%，现报1627.37点。成分股中，华虹宏力、源杰科技跌超7%。",
          "tags": [
            "快讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 12583393068.62,
      "revenue_yoy": 0.198158,
      "operating_profit": -582039658.21,
      "operating_profit_yoy": -0.759464,
      "net_profit": -680770213.32,
      "net_profit_yoy": -1.076752,
      "gross_profit": 2380709392.59,
      "gross_profit_yoy": 0.318232,
      "cogs": 10202683676.03,
      "gross_margin": 18.92,
      "pe_forward": null,
      "valuation_history_days": 227,
      "valuation_history_from": "20250807",
      "current_price": 270.2,
      "price": 270.2,
      "ma5": 306.1,
      "ma10": 328.67,
      "ma20": 331.55,
      "dist_ma5_pct": -11.7,
      "dist_ma10_pct": -17.8,
      "dist_ma20_pct": -18.5,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 25.51,
        "pct_float": 2.72,
        "chg5_pct": -20.82,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688361.SH",
      "fetch_time": "2026-07-31T11:40:51+0800",
      "name": "中科飞测",
      "pe": 22724.8842,
      "pb": 25.0322,
      "ps_ttm": 59.5864,
      "pcf_ttm": null,
      "valuation_percentile": 95.16,
      "total_shares": 352051671,
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
        "科技龙头指数",
        "双创100指数",
        "专精特新小巨人主题指数",
        "股权激励指数",
        "半导体精选指数",
        "专精特新小巨人指数",
        "长鑫存储指数"
      ],
      "score_company": 6.7,
      "score_trend": 8.2,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 51% ，收入成长性很强。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 115% ，销售收入现金含量很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.9% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 8.8亿元 ，较上期增长 56% ，占2025年营收 43% ，在手订单充足。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 24% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "收益",
          "text": "近12月，扣非净利润占净利润 -3459% ，收益质量很低。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比为 -643% ，净利润现金含量很低。"
        },
        {
          "tag": "评级",
          "text": "收盘价比机构一致预测目标价高 27% ，存在高估风险。"
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
          "content": "15:38 中国人寿近日减持兆易创新引发市场关注。公告显示，中国人寿旗下8个单一资管计划于7月8日合计卖出约110.97万股兆易创新，变现约6.82亿元，成交价格区间为611.46元至624.61元。中国人寿回应称，该操作属于基于投资配置需要的常态化投资行为。天使投资人郭涛表示，险资高位减持属于常规调仓，旨在锁定浮盈并控制净值波动，并不违背长期价值投资逻辑。\n专家认为，本次减持由中国人寿8只资管计划同步执行，属于半年度考核节点的统一风控调仓，并非看空国产存储赛道。中国人寿在权益投资方面倾向明显，截至2025年末，其投资资产中股票和基金配置比例有所上升，并重仓了多家A股上市公司，包括工商银行、中信银行、南京银行、中国石化、中国神华、国投电力、东山精密、源杰科技、阳光电源、三花智控、海康威视及伊利股份等。\n2025年，中国人寿总投资收益达3876.94亿元，归母净利润同比增长44.1%。截至2026年一季度末，中国人寿重仓181家A股上市公司。持仓市值较大的股票包括中国联通、中国平安、美的集团、工商银行和长江电力。此外，公司还持有雅克科技、长电科技、中科飞测等半导体公司。中国人寿预计2026年上半年归母净利润同比增长215%至235%，主要得益于资产配置优化及投资业绩增长。\n中国人寿副总裁、首席投资官刘晖曾表示，公司投资策略包括坚定做多中国资产、加大高股息股票配置及灵活开展战术调整。在会计准则影响下，中国人寿FVTPL股票占投资组合比例较高，股市波动对利润端影响显著，这解释了其在股市向好时净利润增速较快，而在股市回调时利润波动较大的现象。\n除二级市场投资外，中国人寿还通过参设基金加码科技产业，包括长三角人工智能基金及半导体产业股权投资基金等。专家认为，二级市场投资作为财务配置工具，与产业基金在产业扶持和赛道布局上形成互补。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "19:50 7月27日，科创芯片板块宽幅震荡，科创芯片ETF华宝（589190）盘中一度跌逾4%，后回升收涨0.87%。个股方面，中船特气、成都华微涨超15%，中科飞测、富创精密、源杰科技、思特威-W等跟涨。长鑫科技上市首日收涨465.82%，全天成交额超1400亿元。市场消息称长鑫存储与字节跳动签署了五年期协议。行业机构数据显示，长鑫存储全球市场份额有所提升。产业链方面，长鑫科技募资扩产预计将带动国产半导体设备与材料发展。科创芯片ETF华宝标的指数成份股中，部分公司已披露2026年半年度业绩预告，表现亮眼。国联民生证券认为，国内半导体产业进入全链条景气周期，自主可控转化为业绩增量。大同证券建议关注半导体设备、材料及芯片等订单充足、业绩确定性强的方向。\n科创芯片ETF华宝（589190）及其联接基金（A类021224、C类021225）跟踪上证科创板芯片指数，重点布局集成电路与半导体设备领域。该ETF综合费率为0.38%。\n风险提示：科创芯片ETF华宝及其联接基金被动跟踪上证科创板芯片指数，指数历史业绩不预示未来表现。基金管理人评估该基金风险评级为R4-中高风险，适合适当性评级C4及以上投资者。投资人应阅读基金法律文件，了解风险收益特征，谨慎投资。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/14解禁188.84万股，占总股本0.54%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-07-14"
        },
        {
          "content": "中科飞测：深圳中科飞测科技股份有限公司关于获得政府补助的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1201724435.3,
      "revenue_yoy": 0.479174,
      "operating_profit": -13797278.21,
      "operating_profit_yoy": 0.737484,
      "net_profit": -14698489.56,
      "net_profit_yoy": 0.716713,
      "gross_profit": 624562971.46,
      "gross_profit_yoy": 0.611851,
      "cogs": 577161463.84,
      "gross_margin": 51.97,
      "pe_forward": null,
      "valuation_history_days": 294,
      "valuation_history_from": "20250519",
      "current_price": 360.7,
      "price": 360.7,
      "ma5": 362.18,
      "ma10": 350.16,
      "ma20": 368.64,
      "dist_ma5_pct": -0.4,
      "dist_ma10_pct": 3.0,
      "dist_ma20_pct": -2.2,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.42,
        "pct_float": 0.74,
        "chg5_pct": -29.72,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688120.SH",
      "fetch_time": "2026-07-31T11:40:51+0800",
      "name": "华海清科",
      "pe": 126.5299,
      "pb": 18.3226,
      "ps_ttm": 28.1298,
      "pcf_ttm": 174.7378,
      "valuation_percentile": 95.21,
      "total_shares": 496281438,
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
        "科技龙头指数",
        "双创100指数",
        "国企改革指数",
        "贷款回购指数",
        "半导体产业指数",
        "专精特新小巨人主题指数",
        "半导体精选指数",
        "专精特新小巨人指数",
        "长鑫存储指数",
        "科改示范企业指数",
        "半导体设备指数",
        "长江存储指数"
      ],
      "score_company": 8.9,
      "score_trend": 8.3,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 37% ，收入成长性很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 15% ，投入资本回报率为 14% ，盈利能力很强。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 117% ，销售收入现金含量很强。"
        },
        {
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 25% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.8% ，较受外资机构青睐；公募基金持股 20% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月10日大跌 -5.64% ，且成交额为近20日均值的 1.77倍 ，抛压很重。"
        },
        {
          "tag": "商誉",
          "text": "商誉占净资产 10% ，商誉减值风险较高。"
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
          "content": "2026/08/03解禁155.03万股，占总股本0.31%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-08-03"
        },
        {
          "content": "02:06 7月27日，长鑫科技上市，收盘价较发行价上涨近466%。合肥国资作为最大股东持有其约36.79%股份。长鑫科技完成约144.37亿元战略配售，30家投资者参与，其中12家为A股上市公司，涵盖半导体设备、材料、封装测试及存储接口等领域，包括中微公司、安集科技、沪硅产业、澜起科技、华勤技术、传音控股、中兴通讯、屹唐股份、拓荆科技、西安奕材、通富微电、TCL科技。此外，小米、腾讯、阿里云、美团、蔚来和奇瑞等下游应用企业也参与了战略配售。\n西安奕材作为长鑫科技硅片供应商，其背后有陕西集成电路基金持股。沈阳的拓荆科技则成为长鑫科技PECVD/ALD/SACVD设备供应商。在长鑫科技产业链上下游中，上海、北京、深圳、无锡、天津等地企业布局较多。其中，华海清科、屹唐股份、北方华创等京津冀企业涉及半导体设备制造；无锡的长电科技、盛合晶微专注于先进封测，雅克科技则供应半导体前驱体。\n武汉的鼎龙股份作为CMP抛光垫供应商，国内市场份额较高。甘肃天水的华天科技通过聚焦封装测试细分赛道，成为集成电路封测企业，2024年天水集成电路产量位居前列。长鑫科技的产业链扩张带动了相关城市在半导体领域的产业卡位与生态重塑。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "华海清科：2026年限制性股票激励计划实施考核管理办法（修订稿）",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 3193795521.45,
      "revenue_yoy": 0.302769,
      "operating_profit": 868206861.88,
      "operating_profit_yoy": 0.067067,
      "net_profit": 791422825.58,
      "net_profit_yoy": 0.098126,
      "gross_profit": 1408082318.27,
      "gross_profit_yoy": 0.335611,
      "cogs": 1785713203.18,
      "gross_margin": 44.09,
      "pe_forward": null,
      "valuation_history_days": 259,
      "valuation_history_from": "20240611",
      "current_price": 268.7,
      "price": 268.7,
      "ma5": 264.13,
      "ma10": 259.53,
      "ma20": 281.45,
      "dist_ma5_pct": 1.7,
      "dist_ma10_pct": 3.5,
      "dist_ma20_pct": -4.5,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 14.96,
        "pct_float": 1.12,
        "chg5_pct": -13.24,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "600176.SH",
      "fetch_time": "2026-07-31T11:40:51+0800",
      "name": "中国巨石",
      "pe": 40.29,
      "pb": 4.8836,
      "ps_ttm": 7.8235,
      "pcf_ttm": 34.1135,
      "valuation_percentile": 96.3,
      "total_shares": 4003136728,
      "industries": [
        {
          "name": "建筑材料",
          "level": 1
        },
        {
          "name": "玻璃玻纤",
          "level": 2
        },
        {
          "name": "玻纤制造",
          "level": 3
        }
      ],
      "concepts": [
        "HALO指数",
        "三新指数",
        "中字头央企指数",
        "出海贸易指数",
        "贷款回购指数",
        "资源股",
        "成交额TOP20指数",
        "RCEP指数",
        "股权激励指数",
        "一带一路指数",
        "新材料指数",
        "养老金指数",
        "国企混改指数",
        "电路板指数",
        "机构大额买入指数",
        "老基建指数",
        "融资租赁指数",
        "国资改革指数"
      ],
      "score_company": 9.3,
      "score_trend": 7.2,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 玻纤制造 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 76% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 15% ，投入资本回报率为 13% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 4.2% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 11家 机构给出评级，其中 82% 为“买入”，距目标价的上涨空间为 47% 。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 5.5% ，很受外资机构青睐；公募基金持股 6.5% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月13日大跌 -10% ，股价跌停，抛压很重。"
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
          "content": "07:52 电子布作为覆铜板和印制电路板的核心增强材料，上半年行业已完成五轮价格上调。据卓创资讯统计，7月初电子纱G75主流成交价较6月初上涨，7628电子布价格环比上涨。东吴证券研报显示，7月下旬电子纱价格较月初继续上涨，7628电子布价格与月初持平。上半年主流规格产品市场均价较2025年第三季度低位上涨约100%。本轮涨价主要受AI算力需求增长及织布机产能、电子纱原料供给约束影响。据中国覆铜板行业协会数据，2025年国内电子布需求量增长至37亿米，广发证券测算2026年中性情形下普通电子布供需缺口约1.13亿米。国盛证券认为，当前普通布与高端特种布供需仍紧，行业维持高景气。中国巨石7月公告，全资子公司拟投资约24亿元建设年产2.5亿米电子布生产线。\n国际复材表示，公司风电纱及电子布产品产能处于满负荷运行状态，在手订单储备充足。截至7月28日，已有8只电子布概念股预告半年度业绩，金安国纪、宏和科技、国际复材、生益科技净利润预计同比翻倍，中国巨石预计同比增长75%，日发精机预计扭亏为盈。金安国纪预计上半年归母净利润同比增长935.75%至1063.45%，公司目前电子玻纤布产能约1.6亿米/年，正在安徽宁国建设年产6000万米扩建项目，计划2026年下半年投产。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "20:36 7月27日，长鑫科技在科创板挂牌交易，发行价8.66元，收盘价49元，涨幅465%，市值达3.28万亿元，单日成交额1412亿元。浙江资本参与了长鑫科技的投资，其中阿里云计算有限公司持股3.85%，阿里网络技术有限公司持股1.12%，浙江国资旗下的浙江富浙通过国家集成电路产业投资基金二期参与投资，宁波国资通过甬欣燕创基金参与了C轮融资。\n长鑫科技上市带动了产业链上下游企业，包括中国巨石、江丰电子、长川科技等。浙江力积存储科技股份有限公司正开展高带宽内存研发。浙江省工信院数字所负责人徐精兵表示，浙江需加强芯片、存储、光通信等硬件基础设施层产业发展。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 13904196236.9,
      "revenue_yoy": 0.195324,
      "operating_profit": 3323093752.44,
      "operating_profit_yoy": 0.772712,
      "net_profit": 2673070961.32,
      "net_profit_yoy": 0.685081,
      "gross_profit": 4508103067.46,
      "gross_profit_yoy": 0.632685,
      "cogs": 9396093169.44,
      "gross_margin": 32.42,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 36.63,
      "price": 36.63,
      "ma5": 610.96,
      "ma10": 702.91,
      "ma20": 943.2,
      "dist_ma5_pct": -94.0,
      "dist_ma10_pct": -94.8,
      "dist_ma20_pct": -96.1,
      "iv_proxy": {
        "primary_name": "50ETF",
        "iv_rank": 0.6353,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 39.28,
        "pct_float": 2.7,
        "chg5_pct": 17.11,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "000657.SZ",
      "fetch_time": "2026-07-31T11:40:53+0800",
      "name": "中钨高新",
      "pe": 58.3218,
      "pb": 11.3703,
      "ps_ttm": 5.4355,
      "pcf_ttm": null,
      "valuation_percentile": 89.75,
      "total_shares": 2278604400,
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
          "name": "钨",
          "level": 3
        }
      ],
      "concepts": [
        "HALO指数",
        "中字头央企指数",
        "资源股",
        "QFII重仓指数",
        "股权激励指数",
        "双百企业指数",
        "养老金指数",
        "有色金属指数",
        "借壳上市指数",
        "万得预增指数",
        "电路板指数",
        "小金属指数",
        "对日反制指数",
        "央企有色指数",
        "稀有金属精选指数",
        "钨矿指数",
        "六氟化钨指数"
      ],
      "score_company": 8.5,
      "score_trend": 5.9,
      "score_value": 3.8,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 钨 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年07月14日，业绩超预期引发股价大幅上涨，当日收涨 7.83% 。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 17% ，最新季度归母净利润同比增长 297% ，成长能力很强。"
        },
        {
          "tag": "评级",
          "text": "近90天， 5家 机构给出评级，其中 100% 为“买入”，距目标价的上涨空间为 40% 。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 4.2% ，很受外资机构青睐；公募基金持股 5.8% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月23日大跌 -5.38% ，且成交额为近20日均值的 1.82倍 ，抛压很重。"
        },
        {
          "tag": "板块",
          "text": "近3月， 小金属 板块疲软，走势弱于其他 89.3% 的板块。"
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
          "content": "2026/08/03解禁66.32万股，占总股本0.03%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-08-03"
        },
        {
          "content": "19:22 国家统计局数据显示，1-6月全国规模以上工业企业利润总额同比增长18.7%，其中有色金属冶炼和压延加工业利润同比增长99.4%。7月29日，A股有色金属板块走强，海亮股份、西部黄金、金田股份、金钼股份、明泰铝业、国城矿业、宝钛股份、西部超导等成分股涨幅居前。海亮股份公告称，控股股东海亮集团计划自2026年7月29日起6个月内增持公司股份，金额不低于6亿元且不超过10亿元。\n全球有色金属供给约束强化，铜、铝等核心工业金属新增供给有限。ICSG数据显示2026年前5个月全球铜矿产量同比下降1.9%，铜精矿加工费持续处于低位。铝方面，LME铝库存降至1998年以来最低。此外，稀土、钨、锑等品种受环保及进口因素影响供给收紧。同时，AI数据中心、电网升级及新能源产业需求持续增长，推动有色金属行业利润增长，拉动规模以上工业企业利润增长4.7个百分点。\n2026年上半年有色金属行业业绩预喜，紫金矿业、洛阳钼业、江西铜业、中国铝业、云铝股份、天山铝业、中钨高新、翔鹭钨业、天齐锂业等企业预计净利润同比均有增长。机构观点认为，黄金受益于央行购金及避险需求，具备配置价值。高盛对冲基金业务主管Tony Pasquariello认为当前是建立黄金结构性多头头寸的时机。国新证券研报指出，矿产金公司估值处于低位，具备估值修复与价格弹性双重潜力。\n恒力期货认为，铜市基本面偏强，库存去化与供应偏紧支撑铜价，中长期紧平衡格局难改。华泰证券指出，有色板块相对估值处于历史低位，看好其估值修复弹性，认为2026-2027年行业供需格局偏短缺，板块具备高赔率特征。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "程豹 任财务总监",
          "tags": [
            "管理层变更"
          ]
        },
        {
          "content": "财务总监（胡佳超）离任",
          "tags": [
            "管理层变更"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 12755273585.43,
      "revenue_yoy": 0.133933,
      "operating_profit": 1086749512.25,
      "operating_profit_yoy": 0.25993,
      "net_profit": 931703961.52,
      "net_profit_yoy": 0.207657,
      "gross_profit": 2783920447.15,
      "gross_profit_yoy": 0.178862,
      "cogs": 9971353138.28,
      "gross_margin": 21.83,
      "pe_forward": null,
      "valuation_history_days": 300,
      "valuation_history_from": "20210802",
      "current_price": 48.4,
      "price": 48.4,
      "ma5": 266.88,
      "ma10": 303.98,
      "ma20": 373.15,
      "dist_ma5_pct": -81.9,
      "dist_ma10_pct": -84.1,
      "dist_ma20_pct": -87.0,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.8795,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 22.18,
        "pct_float": 3.15,
        "chg5_pct": -2.93,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002353.SZ",
      "fetch_time": "2026-07-31T11:40:53+0800",
      "name": "杰瑞股份",
      "pe": 49.4932,
      "pb": 6.0906,
      "ps_ttm": 8.2446,
      "pcf_ttm": 45.5144,
      "valuation_percentile": 90.77,
      "total_shares": 1023855833,
      "industries": [
        {
          "name": "机械设备",
          "level": 1
        },
        {
          "name": "专用设备",
          "level": 2
        },
        {
          "name": "能源及重型设备",
          "level": 3
        }
      ],
      "concepts": [
        "HALO指数",
        "三新指数",
        "出海贸易指数",
        "贷款回购指数",
        "分拆上市指数",
        "专精特新小巨人主题指数",
        "员工持股指数",
        "RCEP指数",
        "高端装备制造指数",
        "一带一路指数",
        "天然气指数",
        "养老金指数",
        "GDR指数",
        "可燃冰指数",
        "页岩气指数",
        "油价上调指数"
      ],
      "score_company": 9.5,
      "score_trend": 7.4,
      "score_value": 3.8,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 能源及重型设备 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 26% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 12% ，投入资本回报率为 12% ，盈利能力很强。"
        },
        {
          "tag": "评级",
          "text": "近90天， 13家 机构给出评级，其中 62% 为“买入”，距目标价的上涨空间为 66% 。"
        },
        {
          "tag": "预测",
          "text": " 8家 机构预测，2026年-2028年营收和净利润每年增长均超过 25% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 9.1% ，很受外资机构青睐；公募基金持股 16% ，很受内资机构青睐。"
        },
        {
          "tag": "增持",
          "text": "近1月，管理层累计实际增持 3.3万股 ，金额合计 473万元 。"
        },
        {
          "tag": "回购",
          "text": "近6月，公司累计回购 362万股 ，占总股本比例 0.35% ，金额合计 1.5亿元 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月28日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月23日 至今陷入调整，资金有出逃可能。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/14发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-14"
        },
        {
          "content": "16:16 7月29日，A股能源板块震荡攀升，能源ETF汇添富（159930）收涨1.34%。成分股中，潞安环能、广汇能源、杰瑞股份等煤炭及油服股上涨，石油股表现分化。中东地缘局势反复，市场避险情绪升温，布伦特原油价格反弹。煤炭方面，新修订的《防治煤矿冲击地压细则》将于9月23日起施行；动力煤价格维持僵持，高温天气提振火电耗煤需求；焦炭市场则迎来钢厂降价。\n国金证券指出，中东航道及输油管道扰动导致全球原油流通规模收缩，地缘风险溢价抬升，带动油价及国内炼化盈利改善。大同证券认为，国内煤矿安全管控收紧压制产能释放，叠加高温天气带来的火电耗煤需求及油价上涨后的替代需求，煤炭供需偏紧格局延续，价格维持高位震荡。\n基金投资存在风险，投资者应根据自身风险承受能力审慎决策。文中提及个股仅为指数成份股展示，不构成投资建议。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/28 李慧涛(高管)增持 2000股 ，类型为 竞价交易 ，成交均价为 140元/股 ，耗资 28.0万元 ，此次增持后的持股数为19.6万股",
          "tags": [
            "管理层增持"
          ]
        },
        {
          "content": "2026/07/28 路伟(高管)增持 2000股 ，类型为 竞价交易 ，成交均价为 140元/股 ，耗资 28.0万元 ，此次增持后的持股数为21.7万股",
          "tags": [
            "管理层增持"
          ]
        },
        {
          "content": "2026/07/28 李志勇(董事)增持 2100股 ，类型为 竞价交易 ，成交均价为 140元/股 ，耗资 29.4万元 ，此次增持后的持股数为73.4万股",
          "tags": [
            "管理层增持"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 10419812013.74,
      "revenue_yoy": 0.294908,
      "operating_profit": 2204868730.06,
      "operating_profit_yoy": 0.154555,
      "net_profit": 1865256648.41,
      "net_profit_yoy": 0.131505,
      "gross_profit": 3260359009.51,
      "gross_profit_yoy": 0.166887,
      "cogs": 7159453004.23,
      "gross_margin": 31.29,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 139.7,
      "price": 139.7,
      "ma5": 139.81,
      "ma10": 131.06,
      "ma20": 143.27,
      "dist_ma5_pct": -0.1,
      "dist_ma10_pct": 6.6,
      "dist_ma20_pct": -2.5,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 7.76,
        "pct_float": 0.89,
        "chg5_pct": -8.45,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300285.SZ",
      "fetch_time": "2026-07-31T11:40:53+0800",
      "name": "国瓷材料",
      "pe": 104.7394,
      "pb": 9.0854,
      "ps_ttm": 13.8292,
      "pcf_ttm": 73.2928,
      "valuation_percentile": 80.33,
      "total_shares": 997048299,
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
        "三新指数",
        "科技龙头指数",
        "双创100指数",
        "贷款回购指数",
        "资源股",
        "QFII重仓指数",
        "成交额TOP20指数",
        "员工持股指数",
        "新材料指数",
        "有色金属指数",
        "高瓴资本指数",
        "对日反制指数",
        "MLCC指数",
        "手机外壳指数",
        "手机陶瓷外壳指数",
        "氮化铝指数",
        "碳纳米管指数"
      ],
      "score_company": 8.3,
      "score_trend": 7.7,
      "score_value": 4.2,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 电子化学品Ⅲ 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年04月28日，业绩超预期引发股价大幅上涨，当日收涨 5.77% 。"
        },
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 10% ，创造价值的能力较强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 4.1% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 14家 机构给出评级，其中 64% 为“买入”，距目标价的上涨空间为 37% 。"
        },
        {
          "tag": "预测",
          "text": " 9家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 2.8% ，较受外资机构青睐；公募基金持股 3.7% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "商誉",
          "text": "商誉占净资产 25% ，商誉减值风险较高。"
        },
        {
          "tag": "波动",
          "text": "近3天，日均换手率 17% ，短线资金追逐，波动风险较高。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/06发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-06"
        },
        {
          "content": "13:35 MLCC概念股盘中走强，风华高科涨停，斯迪克、昀冢科技、三环集团、国瓷材料、宏达电子、火炬电子等跟涨。消息面上，三星电机近期连续披露两笔AI服务器专用MLCC供货合同，年内长协总额达约7500亿韩元。业内分析认为，全球头部云厂商及AI企业为保障算力建设，通过年度长协锁定产能，反映出AI服务器高端被动元件供需偏紧。此外，村田制作所与三星电机均有扩产计划。\n据中国电子元件行业协会报告，预计2026年全球MLCC市场规模约1341亿元。目前全球主要制造商包括村田、太阳诱电、京瓷、TDK、三星电机、国巨、华新科技、风华高科、三环集团、微容电子等。光大证券指出，随着海外厂商优化产品结构，国内厂商有望承接消费电子、家电及工业控制等领域的增量需求。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "02:56 近期MLCC产业链调研显示，供需格局偏紧，主力企业产线满载，出厂价保持稳定。上游材料商订单充沛，部分企业扩产线已被客户提前锁定。离型膜、陶瓷粉及金属粉等主要原材料厂商产线开满，部分企业实行三班倒生产。受AI服务器等新兴应用需求带动，MLCC用量显著增加，相关材料出货量持续攀升。\n国瓷材料因原辅材料价格上涨，自7月27日起上调氧化锆粉体销售价格，涨幅约10%—40%。国内MLCC企业如三环集团表示，今年二季度起产品价格上调后未回调。三环集团预计2026年上半年盈利同比增长45%—65%，增长得益于行业景气度提升及产品价格修复。业内指出，AI服务器对高容MLCC需求形成虹吸效应，导致日韩厂商转产高容产品，推动行业涨价。\n业内人士认为，AI服务器带来的爆发式增量需求正推动MLCC进入新一轮景气周期。机构数据显示，AI服务器对MLCC的消耗量远高于手机和汽车。中商产业研究院预测，受新能源汽车、AI服务器及5G通信等需求拉动，全球MLCC市场规模至2030年将持续增长。上游原料厂商正竞相扩产，部分企业已与村田、三星电机等签署战略协议，新增产能获提前锁单。\n洁美科技正加速推进广东肇庆及天津基地离型膜产线建设，预计2026年底产能将达7.4亿平方米，并已启动安吉基地高端产品扩产计划。博迁新材拟投资约2.02亿元建设超细金属粉体材料扩产项目，以满足MLCC小型化、高容值需求。业内分析认为，本轮景气周期为国产MLCC产业链提供了国产替代机遇，随着产能落地，本土企业市场份额有望提升。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "国瓷材料：关于公司氧化锆粉体价格调整的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 3283812196.8,
      "revenue_yoy": 0.107068,
      "operating_profit": 636889734.44,
      "operating_profit_yoy": 0.037712,
      "net_profit": 551568775.42,
      "net_profit_yoy": 0.021391,
      "gross_profit": 1242366254.88,
      "gross_profit_yoy": 0.056426,
      "cogs": 2041445941.92,
      "gross_margin": 37.83,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 59.12,
      "price": 59.12,
      "ma5": 59.21,
      "ma10": 58.6,
      "ma20": 70.98,
      "dist_ma5_pct": -0.1,
      "dist_ma10_pct": 0.9,
      "dist_ma20_pct": -16.7,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 34.83,
        "pct_float": 6.66,
        "chg5_pct": 13.99,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "001389.SZ",
      "fetch_time": "2026-07-31T11:40:53+0800",
      "name": "广合科技",
      "pe": 57.6589,
      "pb": 9.7414,
      "ps_ttm": 10.7195,
      "pcf_ttm": 59.0322,
      "valuation_percentile": 77.5,
      "total_shares": 472709164,
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
          "name": "印制电路板",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "出海贸易指数",
        "股权激励指数",
        "预期提升指数",
        "电路板指数",
        "元件精选指数",
        "可转债预案指数",
        "高频PCB指数"
      ],
      "score_company": 8.8,
      "score_trend": 5.8,
      "score_value": 4.7,
      "highlights": [
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 39% ，最新季度归母净利润同比增长 116% ，成长能力很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 19% ，投入资本回报率为 19% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 115% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 4.9% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 12% ，很受外资机构青睐；公募基金持股 6.2% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月17日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年07月01日 至今陷入调整，资金有出逃可能。"
        }
      ],
      "events": [
        {
          "content": "2027/04/02解禁2.72亿股，占总股本57.55%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2027-04-02"
        },
        {
          "content": "预计2026/08/08发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-08"
        },
        {
          "content": "09:33 印制电路板板块低开下挫，东山精密跌超7%，景旺电子、广合科技、深南电路、红板科技等跟跌。",
          "tags": [
            "快讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 3835129024.17,
      "revenue_yoy": 0.430666,
      "operating_profit": 824328613.01,
      "operating_profit_yoy": 0.474528,
      "net_profit": 723819563.55,
      "net_profit_yoy": 0.469698,
      "gross_profit": 1336538015.43,
      "gross_profit_yoy": 0.497225,
      "cogs": 2498591008.74,
      "gross_margin": 34.85,
      "pe_forward": null,
      "valuation_history_days": 79,
      "valuation_history_from": "20260403",
      "current_price": 146.0,
      "price": 146.0,
      "ma5": 157.05,
      "ma10": 165.65,
      "ma20": 176.92,
      "dist_ma5_pct": -7.0,
      "dist_ma10_pct": -11.9,
      "dist_ma20_pct": -17.5,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.8795,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 12.05,
        "pct_float": 6.02,
        "chg5_pct": -6.01,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301165.SZ",
      "fetch_time": "2026-07-31T11:40:53+0800",
      "name": "锐捷网络",
      "pe": 181.1874,
      "pb": 27.3583,
      "ps_ttm": 8.7288,
      "pcf_ttm": 103.8199,
      "valuation_percentile": 98.55,
      "total_shares": 1113636363,
      "industries": [
        {
          "name": "通信",
          "level": 1
        },
        {
          "name": "通信设备",
          "level": 2
        },
        {
          "name": "通信网络设备及器件",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "双创100指数",
        "股权激励指数",
        "AI AGENT(小龙虾）指数",
        "预期提升指数",
        "光模块(CPO)指数",
        "通讯设备精选指数",
        "光电路交换机(OCS)指数",
        "超节点指数"
      ],
      "score_company": 8.4,
      "score_trend": 8.7,
      "score_value": 3.4,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月03日，业绩超预期引发股价跳空高开，但目前股价缺口已回补。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 60% ，利润成长性强。"
        },
        {
          "tag": "ROE",
          "text": "近5年，净资产收益率为 15% ，获取收益的能力较强。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 111% ，销售收入现金含量较强。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/15发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-15"
        },
        {
          "content": "19:53 7月28日，广东奥飞数据科技股份有限公司与锐捷网络股份有限公司在福州正式签署战略合作框架协议。双方将围绕智算网络基础设施建设、数据中心项目网络建设、算力租赁业务等方向开展深入合作，携手为客户提供更高效、可靠的“算力+网络”一体化解决方案。（人民财讯）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "10:14 共封装光学(CPO)板块持续走低，新易盛、源杰科技跌超10%，联讯仪器、中际旭创、锐捷网络等跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "09:37股价达到 115.8 元，创历史新高",
          "tags": [
            "股价新高"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 10680288404.21,
      "revenue_yoy": 0.274973,
      "operating_profit": 750878188.26,
      "operating_profit_yoy": 1.355543,
      "net_profit": 680444598.95,
      "net_profit_yoy": 0.652608,
      "gross_profit": 3640354138.33,
      "gross_profit_yoy": 0.232327,
      "cogs": 7039934265.88,
      "gross_margin": 34.08,
      "pe_forward": null,
      "valuation_history_days": 408,
      "valuation_history_from": "20241121",
      "current_price": 105.0,
      "price": 105.0,
      "ma5": 121.97,
      "ma10": 114.98,
      "ma20": 107.19,
      "dist_ma5_pct": -13.9,
      "dist_ma10_pct": -8.7,
      "dist_ma20_pct": -2.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.86,
        "pct_float": 0.6,
        "chg5_pct": -16.53,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688300.SH",
      "fetch_time": "2026-07-31T11:40:53+0800",
      "name": "联瑞新材",
      "pe": 90.0191,
      "pb": 16.3748,
      "ps_ttm": 23.1622,
      "pcf_ttm": 116.4882,
      "valuation_percentile": 96.41,
      "total_shares": 241469190,
      "industries": [
        {
          "name": "基础化工",
          "level": 1
        },
        {
          "name": "非金属材料Ⅱ",
          "level": 2
        },
        {
          "name": "非金属材料Ⅲ",
          "level": 3
        }
      ],
      "concepts": [
        "资源股",
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "可转债正股指数",
        "半导体材料指数",
        "HBM指数"
      ],
      "score_company": 8.4,
      "score_trend": 5.4,
      "score_value": 3.5,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 非金属材料Ⅲ 行业龙头企业。"
        },
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 23% ，收入成长性很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 16% ，投入资本回报率为 16% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.8% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 5家 机构给出评级，其中 60% 为“买入”，距目标价的上涨空间为 48% 。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 4.2% ，较受内资机构青睐。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/15发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-15"
        },
        {
          "content": "联瑞新材：联瑞新材关于“联瑞转债”预计满足赎回条件的提示性公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "14:00 创新药概念走强，脑机接口概念股表现活跃，我国医疗服务体系规模持续增长，2025年获批创新药数量较多。锂电池板块方面，宁德时代拟回购股份，电解液添加剂VC均价近期出现上涨。人形机器人概念震荡反弹，智元创新启动赴港上市流程，行业正从技术突破向规模化商业化迈进。机构分析认为，市场回暖受内外因素共同推动，包括美债收益率回落及科技产业景气预期修复。当前市场风险偏好由收缩向修复过渡，短期预计延续震荡回升格局，配置上关注半导体、存储、算力硬件及创新药、锂电储能和机器人等方向。\n截至2026年7月27日13:51，上证科创板200指数上涨1.20%，成分股诺唯赞、泛亚微透、迈信林等上涨。科创200ETF鹏华上涨1.55%，最新价报1.51元。该ETF跟踪上证科创板200指数，该指数选取科创板市值较小且流动性较好的证券作为样本。截至2026年6月30日，上证科创板200指数前十大权重股包括汇成股份、杰普特、鼎通科技、甬矽电子、嘉元科技、聚和材料、新锐股份、伟测科技、兴福电子、联瑞新材。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "20:32 国金证券李阳团队认为，CoWoS-L架构因具备无掩模缝合和良率优势，有望成为先进封装主流工艺。台积电预计到2026年底CoWoS-L占2.5D封装产能超50%，2027年将达70%。芯碁微装的先进封装直写光刻设备已导入长电、通富、甬矽等国内头部封测厂。预计全球先进封装直写光刻设备市场规模将从2024年的2亿元增长至2030年的31亿元。\n需求端数据显示国产算力景气度高：国内头部模型日均Token消耗量呈指数级增长，国产大模型绑定国产GPU芯片，寒武纪26Q1期末预付款同比大幅增长。封测行业出现“AI挤占”现象，AI相关需求高速增长，日月光等厂商上调先进封装报价。国内主流封测企业稼动率回升，长电科技、通富微电、甬矽电子、汇成股份、盛合晶微等企业积极扩产。\nCoWoS-L封装由top die、重组插层和基板组成，通过模塑化合物包围的TIV提供垂直路径。芯碁微装设备主要应用于中介层曝光。国产算力需求强劲，豆包全系产品日均Token消耗量增长显著，寒武纪预付款大幅增加。封测行业结构性分化明显，AI相关需求旺盛，国内封测企业订单预期乐观。\n受原料成本上涨及供给紧俏影响，日月光上调CoWoS、FoCoS等先进封装报价。国内5家主流上市封测企业2025年营收平均增速21%，26Q1增速19%，归母净利增速明显。长电科技、通富微电、甬矽电子、汇成股份、盛合晶微等公司均有高端先进封测产能扩产计划。\nCoWoS工艺路线迭代主要体现在中介层，包括CoWoS、CoWoS-R和CoWoS-L。CoWoS技术核心在于硅中介层，其制造流程复杂，涉及TSV形成、绝缘层沉积、阻挡层与种子层沉积、铜电镀填充、CMP平坦化及RDL制作等关键步骤。\n先进封装材料包括光刻胶、电镀液、刻蚀剂、溅射靶材、底部填充等。环氧塑封料（EMC）国产化率较低，高性能EMC国产化率仅10-20%。华海诚科通过收购衡所华威成为国内龙头，联瑞新材为衡所华威主要硅微粉供应商。\n湿电子化学品包括电镀液、蚀刻液、清洗液等。飞凯材料、艾森股份、上海新阳等厂商在先进制程湿电子化学品领域有布局。临时键合胶在晶圆承载系统中起重要作用，飞凯材料、鼎龙股份有相关布局，芯源微提供临时键合、解键合设备。\n江丰电子和有研新材在超高纯金属溅射靶材领域市场份额领先。底部填充胶是保证倒片封装和TSV工艺可靠性的关键，德邦科技提供包括底部填充胶在内的综合封装材料解决方案。\n康强电子引线框架产品产能处于满产状态。新技术方面，CoPoS技术通过大型矩形面板实现“化圆为方”，玻璃基板具备热膨胀系数接近硅、电气绝缘性能优异等优势。碳化硅（SiC）中介层因高热导率，被视为应对AI芯片高功耗散热挑战的潜在方案。\n国金证券提示风险：封装技术存在不确定性，国产替代进度可能不及预期，行业竞争格局可能恶化。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "联瑞新材：联瑞新材关于可转债投资者适当性要求的风险提示性公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 823840389.56,
      "revenue_yoy": 0.187588,
      "operating_profit": 250665221.26,
      "operating_profit_yoy": 0.204983,
      "net_profit": 220024328.18,
      "net_profit_yoy": 0.190123,
      "gross_profit": 341128422.6,
      "gross_profit_yoy": 0.166247,
      "cogs": 482711966.96,
      "gross_margin": 41.41,
      "pe_forward": null,
      "valuation_history_days": 285,
      "valuation_history_from": "20211115",
      "current_price": 115.88,
      "price": 115.88,
      "ma5": 123.46,
      "ma10": 130.21,
      "ma20": 165.18,
      "dist_ma5_pct": -6.1,
      "dist_ma10_pct": -11.0,
      "dist_ma20_pct": -29.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 7.97,
        "pct_float": 3.15,
        "chg5_pct": -2.48,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300408.SZ",
      "fetch_time": "2026-07-31T11:40:53+0800",
      "name": "三环集团",
      "pe": 79.519,
      "pb": 8.2724,
      "ps_ttm": 23.2113,
      "pcf_ttm": 81.938,
      "valuation_percentile": 96.57,
      "total_shares": 1987861671,
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
        "三新指数",
        "科技龙头指数",
        "双循环指数",
        "双创100指数",
        "自主可控指数",
        "5G应用指数",
        "先进制造指数",
        "消费电子产业指数",
        "贷款回购指数",
        "华为平台指数",
        "QFII重仓指数"
      ],
      "score_company": 9.4,
      "score_trend": 7.5,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 被动元件 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年07月21日，业绩超预期引发股价大幅上涨，当日收涨 18.2% 。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 26% ，最新季度归母净利润同比增长 60% ，成长能力很强。"
        },
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 11% ，创造价值的能力较强。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 4.8% ，很受外资机构青睐；公募基金持股 14% ，很受内资机构青睐。"
        },
        {
          "tag": "回购",
          "text": "近6月，公司累计回购 1368万股 ，占总股本比例 0.69% ，金额合计 11亿元 。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/28发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-28"
        },
        {
          "content": "06:33 上市公司增持回购热潮仍在延续。7月30日晚，多家A股公司披露回购及重要股东增持计划。从回购规模看：三环集团以最高10亿元的回购上限领跑；东阳光则拟推出“回购+增持”合计上限达12亿元的组合拳，彰显对公司长期发展的坚定信心。在本轮增持回购潮中，细分产业龙头公司行动快、力度大。在业内看来，行业龙头公司的回购行为有望起到标杆和引领作用，带动更多的上市公司加入回购增持队伍。（上证报）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "05:59 近期A股市场波动，MLCC板块表现活跃。7月30日，风华高科、昀冢科技等概念股盘中涨幅明显，最终风华高科收涨6.29%，昀冢科技收涨16.16%。行业内出现关于MLCC供应周期变化的讨论，有观点认为AI产业需求带动了高端MLCC市场景气度提升。国内MLCC材料企业负责人表示，今年以来行业景气度持续上升，订单能见度提升，目前处于满负荷生产状态，部分订单出现延迟交付。洁美科技调研记录显示，其离型膜业务自今年3月起销量同比增幅超100%，预计明年上半年将持续供不应求，公司计划调整产品结构，侧重中高端产品。此外，产业链传出涨价消息，韩国三星电机通知自8月1日起全系列MLCC产品出货价格上调30%；日本太阳诱电宣布自9月1日起执行新的调价政策。据公开数据，全球MLCC市场由日韩企业主导，村田、三星电机、太阳诱电、TDK、京瓷五家企业合计市场份额达77.3%。\n对于产品价格调整，国内某MLCC企业表示产品价格随行就市，看好行业发展前景。7月30日晚间，三环集团披露第二次回购股份方案，拟回购资金总额为5亿元至10亿元。此前，该公司于7月21日披露了回购方案，拟回购4.5亿元至9亿元，截至目前已完成首次回购，实际回购金额为8.9亿元，回购成交价区间为99.10元/股至110.50元/股，累计回购股份854.73万股。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/21至2026/07/30，公司累计回购 855万股，占总股本比例为 0.43% ，最高成交价为 111元/股 ，最低成交价为 99.1元/股 ，耗资 8.95亿元  （已完成）",
          "tags": [
            "公司回购流通股"
          ]
        },
        {
          "content": "回购总金额不超过10.0亿元，回购最高价不超过135元/股 （预案）",
          "tags": [
            "公司回购流通股"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 6508368850.01,
      "revenue_yoy": 0.209559,
      "operating_profit": 2258305300.6,
      "operating_profit_yoy": 0.226382,
      "net_profit": 1957938593.36,
      "net_profit_yoy": 0.220879,
      "gross_profit": 2765305562,
      "gross_profit_yoy": 0.201647,
      "cogs": 3743063288.01,
      "gross_margin": 42.49,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 108.89,
      "price": 108.89,
      "ma5": 105.54,
      "ma10": 103.51,
      "ma20": 120.98,
      "dist_ma5_pct": 3.2,
      "dist_ma10_pct": 5.2,
      "dist_ma20_pct": -10.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 38.64,
        "pct_float": 1.96,
        "chg5_pct": 8.59,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "300857.SZ",
      "fetch_time": "2026-07-31T11:40:53+0800",
      "name": "协创数据",
      "pe": 60.6106,
      "pb": 20.6675,
      "ps_ttm": 6.5135,
      "pcf_ttm": 53.8486,
      "valuation_percentile": 84.58,
      "total_shares": 489363040,
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
        "科技龙头指数",
        "双创100指数",
        "出海贸易指数",
        "股权激励指数",
        "设备更新指数",
        "AI算力指数",
        "存储器指数",
        "AIGC指数",
        "万得预增指数",
        "电子制造精选指数"
      ],
      "score_company": 8.3,
      "score_trend": 6.4,
      "score_value": 4.3,
      "highlights": [
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 71% ，最新季度归母净利润同比增长 261% ，成长能力很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 19% ，投入资本回报率为 10.0% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 16% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 5.4% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月26日 至今陷入调整，资金有出逃可能。"
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
          "content": "协创数据：关于公司为全资子公司提供担保的进展公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是协创数据披露2026年上半年净利同比暴增247%–340%，且二季度环比持平至增长0–53%，反映其一体化硬件软件产品销量与盈利能力显著改善，市场预期业绩扩张推动股价上涨。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "13:16 东芯股份公告，预计二季度净利润环比增长262%-291%，上半年预计实现净利润6.40亿元-6.80亿元，同比扭亏为盈。星宸科技预计2026年上半年归母净利润为8.20亿元-9.00亿元，同比增长583.72%-650.42%。国元证券分析称，苹果AI服务在中国落地及新机散热需求增加，有望带动消费电子硬件供应链升级。截至2026年7月21日，国证消费电子主题指数上涨6.92%，消费电子ETF鹏华上涨6.93%，报1.25元。该指数由50家消费电子产业上市公司组成，截至6月30日，前十大权重股包括兆易创新、东山精密、立讯精密、京东方A、胜宏科技、三环集团、佰维存储、长电科技、TCL科技、协创数据。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价开盘上涨 5.52% ，股价收盘涨幅 3.40%",
          "tags": [
            "股价上涨"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 8330610619.94,
      "revenue_yoy": 0.544254,
      "operating_profit": 759782267.55,
      "operating_profit_yoy": 0.217859,
      "net_profit": 684757921.7,
      "net_profit_yoy": 0.237568,
      "gross_profit": 1470763719.5,
      "gross_profit_yoy": 0.527452,
      "cogs": 6859846900.44,
      "gross_margin": 17.65,
      "pe_forward": null,
      "valuation_history_days": 323,
      "valuation_history_from": "20220728",
      "current_price": 205.0,
      "price": 205.0,
      "ma5": 226.5,
      "ma10": 229.59,
      "ma20": 259.39,
      "dist_ma5_pct": -9.5,
      "dist_ma10_pct": -10.7,
      "dist_ma20_pct": -21.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 69.67,
        "pct_float": 7.63,
        "chg5_pct": -3.27,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300502.SZ",
      "fetch_time": "2026-07-31T11:40:55+0800",
      "name": "新易盛",
      "pe": 53.164,
      "pb": 29.4108,
      "ps_ttm": 19.6021,
      "pcf_ttm": 69.7461,
      "valuation_percentile": 76.55,
      "total_shares": 1394256684,
      "industries": [
        {
          "name": "通信",
          "level": 1
        },
        {
          "name": "通信设备",
          "level": 2
        },
        {
          "name": "通信网络设备及器件",
          "level": 3
        }
      ],
      "concepts": [
        "A50指数",
        "HALO指数",
        "TMT指数",
        "科技龙头指数",
        "双创100指数",
        "出海贸易指数",
        "人工智能+指数",
        "成交额TOP20指数",
        "新基建指数",
        "5G指数"
      ],
      "score_company": 9.3,
      "score_trend": 7.1,
      "score_value": 4.9,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 通信网络设备及器件 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 99% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 31% ，投入资本回报率为 35% ，盈利能力很强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 2.9亿元 ，较上期增长 222% ，占2025年营收 1.2% ，在手订单充足。"
        },
        {
          "tag": "评级",
          "text": "近90天， 10家 机构给出评级，其中 80% 为“买入”，距目标价的上涨空间为 49% 。"
        },
        {
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 40% ，未来成长很快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 6.4% ，很受外资机构青睐；公募基金持股 27% ，很受内资机构青睐。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/25发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-25"
        },
        {
          "content": "11:10 创业板人工智能ETF华夏（159381）、科创创业人工智能ETF景顺（159142）、科创人工智能ETF广发（588760）涨超8%。AI相关个股持续走强，昆仑万维20cm涨停，金山办公涨超15%，澜起科技、寒武纪、新易盛等涨超6%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "10:35 7月31日，A股存储芯片及CPO板块反弹。存储芯片板块中，兆易创新、德明利、太极实业涨停，北京君正、佰维存储、江波龙涨幅超过10%。长鑫科技盘中涨近13%，总市值一度突破4万亿元。截至发稿，兆易创新、德明利涨幅回落，长鑫科技涨超8%。据市值数据平台Companiesmarketcap显示，按7月30日美股收盘价计算，长鑫科技全球市值排名位列第24位。CPO概念方面，中际旭创、新易盛、联讯仪器、天孚通信涨幅均超10%。此外，韩国股市SK海力士、三星电子股价涨超20%，韩国综合股价指数盘中涨幅一度超15%，韩国证券交易所对主板和创业板启动临时停牌措施。隔夜美股方面，受美国二季度经济增速放缓及6月核心PCE数据通胀降温影响，市场对美联储短期加息预期下降，美股三大股指集体上涨。光通信与存储板块个股普涨，闪迪涨近26%，SK海力士涨超17%，Lumentum、西部数据涨超15%，AMD、Credo涨逾13%，英特尔涨逾11%，Arm涨超7%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价开盘上涨 6.03% ，股价收盘涨幅 5.62%",
          "tags": [
            "股价上涨"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 16504791211.36,
      "revenue_yoy": 2.217035,
      "operating_profit": 7046213011.26,
      "operating_profit_yoy": 2.772801,
      "net_profit": 6327092507.84,
      "net_profit_yoy": 2.84375,
      "gross_profit": 7798014585.97,
      "gross_profit_yoy": 2.590269,
      "cogs": 8706776625.39,
      "gross_margin": 47.25,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 421.2,
      "price": 421.2,
      "ma5": 458.48,
      "ma10": 488.85,
      "ma20": 514.15,
      "dist_ma5_pct": -8.1,
      "dist_ma10_pct": -13.8,
      "dist_ma20_pct": -18.1,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 208.94,
        "pct_float": 4.49,
        "chg5_pct": -22.5,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300308.SZ",
      "fetch_time": "2026-07-31T11:40:55+0800",
      "name": "中际旭创",
      "pe": 69.6976,
      "pb": 30.0853,
      "ps_ttm": 20.4046,
      "pcf_ttm": 86.1129,
      "valuation_percentile": 83.5,
      "total_shares": 1115234641,
      "industries": [
        {
          "name": "通信",
          "level": 1
        },
        {
          "name": "通信设备",
          "level": 2
        },
        {
          "name": "通信网络设备及器件",
          "level": 3
        }
      ],
      "concepts": [
        "A50指数",
        "HALO指数",
        "TMT指数",
        "科技龙头指数",
        "双创100指数",
        "出海贸易指数",
        "人工智能+指数",
        "华为平台指数",
        "QFII重仓指数",
        "成交额TOP20指数",
        "新基建指数"
      ],
      "score_company": 9.5,
      "score_trend": 7.3,
      "score_value": 4.2,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 通信网络设备及器件 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年04月17日，业绩超预期引发股价跳空高开，当日收涨 5.11% 。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 76% ，最新季度归母净利润同比增长 262% ，成长能力很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 23% ，投入资本回报率为 24% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 4.2% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 11家 机构给出评级，其中 82% 为“买入”，距目标价的上涨空间为 71% 。"
        },
        {
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 40% ，未来成长很快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 6.6% ，很受外资机构青睐；公募基金持股 18% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月30日大跌 -9.15% ，且成交额为近20日均值的 1.52倍 ，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月23日 至今陷入调整，资金有出逃可能。"
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
          "content": "10:35 7月31日，A股存储芯片及CPO板块反弹。存储芯片板块中，兆易创新、德明利、太极实业涨停，北京君正、佰维存储、江波龙涨幅超过10%。长鑫科技盘中涨近13%，总市值一度突破4万亿元。截至发稿，兆易创新、德明利涨幅回落，长鑫科技涨超8%。据市值数据平台Companiesmarketcap显示，按7月30日美股收盘价计算，长鑫科技全球市值排名位列第24位。CPO概念方面，中际旭创、新易盛、联讯仪器、天孚通信涨幅均超10%。此外，韩国股市SK海力士、三星电子股价涨超20%，韩国综合股价指数盘中涨幅一度超15%，韩国证券交易所对主板和创业板启动临时停牌措施。隔夜美股方面，受美国二季度经济增速放缓及6月核心PCE数据通胀降温影响，市场对美联储短期加息预期下降，美股三大股指集体上涨。光通信与存储板块个股普涨，闪迪涨近26%，SK海力士涨超17%，Lumentum、西部数据涨超15%，AMD、Credo涨逾13%，英特尔涨逾11%，Arm涨超7%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:00 7月30日共有3509只个股获融资资金买入，有298股买入金额超亿元。其中，中际旭创、C长鑫、兆易创新融资买入金额排名前三，分别获买入73.45亿元、52.10亿元、51.06亿元。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "中际旭创：关于境外发行股份（H股）并在香港联交所上市进展的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 25004800851.32,
      "revenue_yoy": 0.444312,
      "operating_profit": 8838676999.07,
      "operating_profit_yoy": 1.004064,
      "net_profit": 7569731091.52,
      "net_profit_yoy": 0.95521,
      "gross_profit": 10187243120.36,
      "gross_profit_yoy": 0.765918,
      "cogs": 14817557730.96,
      "gross_margin": 40.74,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 951.0,
      "price": 951.0,
      "ma5": 1010.99,
      "ma10": 1034.88,
      "ma20": 1096.3,
      "dist_ma5_pct": -5.9,
      "dist_ma10_pct": -8.1,
      "dist_ma20_pct": -13.3,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 321.66,
        "pct_float": 3.35,
        "chg5_pct": -20.04,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688017.SH",
      "fetch_time": "2026-07-31T11:40:55+0800",
      "name": "绿的谐波",
      "pe": 404.1645,
      "pb": 15.656,
      "ps_ttm": 90.1902,
      "pcf_ttm": 394.093,
      "valuation_percentile": 89.26,
      "total_shares": 183330125,
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
          "name": "机器人",
          "level": 3
        }
      ],
      "concepts": [
        "双创100指数",
        "先进制造指数",
        "专精特新小巨人主题指数",
        "具身智能指数",
        "股权激励指数",
        "专精特新小巨人指数",
        "人形机器人指数",
        "工业4.0指数",
        "机器人指数",
        "新型工业化指数",
        "减速器指数",
        "宇树机器人指数",
        "外骨骼机器人指数"
      ],
      "score_company": 8.6,
      "score_trend": 7.2,
      "score_value": 4.0,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 机器人 行业龙头企业。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 6.0% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "预测",
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 5.1% ，很受外资机构青睐；公募基金持股 7.1% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "收现",
          "text": "近5年，收现比为 72% ，销售收入现金含量较低。"
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
          "content": "17:46 上半年机器人赛道出现降价趋势，宇树将R1人形机器人售价降至3万元以下，松延动力小布米到手价降至约9000元，星尘智能T1起售价降至8.99万元。受产业确定性增强影响，上游供应商开始跨界布局。绿的谐波与斯凯孚签署协议成立合资公司，聚焦高精密轴承部件；双环传动则通过子公司环动科技布局RV减速器、精密配件及谐波减速器业务。\n兆威机电发布B20型号灵巧手整机，并计划投资8亿元建设灵巧手产业园。随着比亚迪、长安、小鹏、小米等车企入局，行业供给增加，降价压力持续。本体厂商倾向于全栈自研以降低成本，宇树通过自研电机、减速器等核心零部件，毛利率有所提升，并掌握了供应链议价权。\n短期内本体厂商仍需依赖供应商，如中大力德与宇树签署了长期订单。但长期来看，价格战将传导压力至供应链，促使双方关系更加“在商言商”。未来车企跨界入局可能进一步加剧博弈，供应商需通过提升不可替代性来应对市场竞争。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "10:14 企查查APP显示，近日，斯凯孚机器人精密轴承（宁波）有限公司成立，经营范围包含智能机器人的研发；智能机器人销售；工业机器人制造；人工智能硬件销售等。企查查股权穿透显示，该公司由绿的谐波等共同持股。（人民财讯）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "绿的谐波：关于募集资金投资项目延期的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 406652949.93,
      "revenue_yoy": 0.47362,
      "operating_profit": 106100199.52,
      "operating_profit_yoy": 0.605419,
      "net_profit": 94933887.21,
      "net_profit_yoy": 0.584647,
      "gross_profit": 148826302.96,
      "gross_profit_yoy": 0.364319,
      "cogs": 257826646.97,
      "gross_margin": 36.6,
      "pe_forward": null,
      "valuation_history_days": 316,
      "valuation_history_from": "20220829",
      "current_price": 283.66,
      "price": 283.66,
      "ma5": 298.36,
      "ma10": 314.07,
      "ma20": 364.57,
      "dist_ma5_pct": -4.9,
      "dist_ma10_pct": -9.7,
      "dist_ma20_pct": -22.2,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 22.42,
        "pct_float": 4.69,
        "chg5_pct": -6.65,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301536.SZ",
      "fetch_time": "2026-07-31T11:40:55+0800",
      "name": "星宸科技",
      "pe": 102.4519,
      "pb": 15.7884,
      "ps_ttm": 14.8196,
      "pcf_ttm": 165.6555,
      "valuation_percentile": 85.56,
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
        "双创100指数",
        "专精特新小巨人主题指数",
        "具身智能指数",
        "股权激励指数",
        "半导体精选指数",
        "专精特新小巨人指数",
        "万得预增指数",
        "人工智能指数",
        "模拟芯片指数",
        "安防监控指数"
      ],
      "score_company": 8.1,
      "score_trend": 8.6,
      "score_value": 4.2,
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
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月23日大跌 -4.05% ，且成交额为近20日均值的 2.16倍 ，抛压很重。"
        },
        {
          "tag": "波动",
          "text": "近3天，日均换手率 15% ，短线资金追逐，波动风险较高。"
        }
      ],
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
          "content": "16:19 2026年7月22日收盘，创业板指数下跌3.23%。成分股中，锐捷网络、星宸科技、全志科技涨幅居前，铜冠铜箔、国际复材、精测电子跌幅居前。创业板ETF华夏（159957）收跌3.73%，成交3.75亿元；创业板成长ETF华夏（159967）收跌4.35%，成交15.56亿元。Wind数据显示，截至7月20日，全市场17只创业板指ETF月内净流入超200亿元，境内共有51只跟踪创业板指的基金产品，规模合计近1200亿元。境外资本方面，2026年一季度，QFII对创业板指样本股持仓市值119亿元，较2025年底增长2.4倍；陆港通持仓市值达5734亿元，较2025年底增长14%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "10:18股价达到 134.53 元，创历史新高",
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
      "valuation_history_days": 83,
      "valuation_history_from": "20260330",
      "current_price": 125.83,
      "price": 125.83,
      "ma5": 127.58,
      "ma10": 119.96,
      "ma20": 118.79,
      "dist_ma5_pct": -1.4,
      "dist_ma10_pct": 4.9,
      "dist_ma20_pct": 5.9,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.05,
        "pct_float": 5.16,
        "chg5_pct": -8.58,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "000703.SZ",
      "fetch_time": "2026-07-31T11:40:55+0800",
      "name": "恒逸石化",
      "pe": 27.5474,
      "pb": 2.3086,
      "ps_ttm": 0.5215,
      "pcf_ttm": 10.2941,
      "valuation_percentile": 81.85,
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
        "借壳上市指数",
        "石化精选指数",
        "万得预增指数",
        "油品升级指数",
        "油气改革指数",
        "供应链服务指数",
        "涤纶指数",
        "PTA指数"
      ],
      "score_company": 8.0,
      "score_trend": 9.5,
      "score_value": 4.1,
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
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 98% 的股票，走势很强。"
        },
        {
          "tag": "回购",
          "text": "近3月，公司累计回购 7957万股 ，占总股本比例 2.1% ，金额合计 10亿元 。"
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
          "content": "22:06 7月30日，现货商品乙酸乙烯酯价格为6675.00元/吨，单日上涨6.37%，近一周累计上涨11.72%，近一个月累计上涨15.09%。乙酸乙烯酯（VAM）作为乙烯下游、PVA/EVA上游的核心原料，广泛应用于光伏封装、胶黏剂、涂料及包装领域。近期新能源与包装需求保持旺盛，带动采购增加。同时，行业内存在装置检修、部分工厂停车或延迟开工的情况，导致现货流通资源偏紧。此外，上游乙烯、醋酸价格波动抬升了成本，供应端对价格形成支撑，推动了现货价格上涨。相关个股包括恒逸石化、天富龙、汇隆新材、华西股份、优彩资源。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "02:45 7月以来，共有375家A股上市公司获机构调研，其中新易盛、京东方A、华灿光电、华勤技术等22家公司获50家以上机构调研。新易盛获417家机构调研居首，公司称二季度业绩预告与年初预期基本吻合。京东方A获243家机构调研，公司表示未来折旧金额及资本开支预计将逐渐下降。在已发布半年度业绩相关公告的调研公司中，超七成实现业绩报喜，恒逸石化、三维通信、凯尔达预计净利润同比增长超1000%。分行业看，获调研且业绩预喜的公司中，电子行业数量居首，电力设备、基础化工及有色金属行业紧随其后。\n研究机构Omdia数据显示，2026年中国半导体市场规模预测值上调。在上述375家获调研公司中，67家获外资机构调研，其中电子行业公司有19家。广合科技、沪电股份、华勤技术等电子行业公司获外资机构调研较多。调研内容显示，外资机构关注相关公司的全球化布局，广合科技泰国工厂正推进产能爬坡，沪电股份泰国基地已进入规模化运营阶段。",
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
      "valuation_history_from": "20210802",
      "current_price": 16.05,
      "price": 16.05,
      "ma5": 125.69,
      "ma10": 137.59,
      "ma20": 139.09,
      "dist_ma5_pct": -87.2,
      "dist_ma10_pct": -88.3,
      "dist_ma20_pct": -88.5,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.8795,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.91,
        "pct_float": 1.46,
        "chg5_pct": -7.42,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "002938.SZ",
      "fetch_time": "2026-07-31T11:40:55+0800",
      "name": "鹏鼎控股",
      "pe": 51.7528,
      "pb": 5.9439,
      "ps_ttm": 4.9206,
      "pcf_ttm": 24.3889,
      "valuation_percentile": 89.89,
      "total_shares": 2317536658,
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
          "name": "印制电路板",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "三新指数",
        "科技龙头指数",
        "双循环指数",
        "出海贸易指数",
        "人工智能+指数",
        "自主可控指数",
        "5G应用指数",
        "先进制造指数",
        "消费电子产业指数",
        "华为平台指数",
        "珠三角指数",
        "新基建指数"
      ],
      "score_company": 8.8,
      "score_trend": 7.3,
      "score_value": 3.7,
      "highlights": [
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 12% ，创造价值的能力较强。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 2.3% ，现金分红极高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 9.4% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 9家 机构给出评级，其中 78% 为“买入”，距目标价的上涨空间为 37% 。"
        },
        {
          "tag": "预测",
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月28日大跌 -10% ，股价跌停，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/12发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-12"
        },
        {
          "content": "15:00 今天大跌的原因可能是PCB行业整体需求疲软，市场对鹏鼎控股未来业绩预期悲观。",
          "tags": [
            "快讯",
            "大跌原因"
          ]
        },
        {
          "content": "06:30 鹏鼎控股发布公告，拟投资100亿元建设深圳第三园区，打造人工智能高阶类载板及柔性电路板智造基地，项目计划2026年7月启动，2033年投产。该园区将重点建设面向AI算力基础设施和智能终端的高端PCB研发及生产能力。今年以来，鹏鼎控股已累计投资三笔百亿级项目，合计金额达337.3亿元。公司相关负责人表示，此举旨在顺应下游市场需求，抢抓AI产业发展机遇。\n鹏鼎控股深圳第三园区项目将建设集研发、智能制造、数字化运营于一体的生产基地，布局AI服务器用高阶类载板、高阶HDI及AI终端用高阶柔性电路板。南开大学金融发展研究院院长田利辉认为，此举有助于公司补全“云—管—端”全链条布局，从单一PCB制造商向AI硬件系统解决方案供应商转型，并降低对苹果产业链的依赖。此外，公司此前已披露定增预案，拟募资不超过96亿元投向淮安庆鼎AI服务器及高速光模块项目，与深圳园区形成双中心协同。\n苏商银行特约研究员高政扬指出，淮安基地聚焦AI服务器与光模块高阶HDI产能，深圳基地聚焦类载板与柔性板研发，双中心协同有助于公司切入AI产业链。针对财务压力，鹏鼎控股在公告中提示了项目建设、市场匹配及资金财务风险，表示将根据资金状况灵活把控投资节奏。今年一季度，鹏鼎控股扣非归母净利润同比下滑31.85%，大规模扩产对财务构成一定压力。\n田利辉分析称，虽然短期存在折旧与研发投入压力，但AI服务器PCB订单能见度已锁定至2027年，长期价值逻辑坚实。鹏鼎控股相关负责人表示，公司自有资金充裕，资产负债率处于行业较低水平，且项目分阶段投产，不会对短期业绩产生不利影响。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "鹏鼎控股：鹏鼎控股（深圳）股份有限公司关于申请银行授信额度的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "鹏鼎控股：鹏鼎控股（深圳）股份有限公司关于投资建设深圳第三园区项目的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 26855433185.29,
      "revenue_yoy": 0.143437,
      "operating_profit": 2809623220.5,
      "operating_profit_yoy": 0.323226,
      "net_profit": 2392939388.84,
      "net_profit_yoy": 0.212301,
      "gross_profit": 5542297874.02,
      "gross_profit_yoy": 0.153029,
      "cogs": 21313135311.27,
      "gross_margin": 20.64,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 84.5,
      "price": 84.5,
      "ma5": 87.55,
      "ma10": 91.26,
      "ma20": 94.93,
      "dist_ma5_pct": -3.5,
      "dist_ma10_pct": -7.4,
      "dist_ma20_pct": -11.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 12.81,
        "pct_float": 0.73,
        "chg5_pct": -7.1,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "003031.SZ",
      "fetch_time": "2026-07-31T11:40:55+0800",
      "name": "中瓷电子",
      "pe": 69.1746,
      "pb": 6.8318,
      "ps_ttm": 13.0214,
      "pcf_ttm": 38.3661,
      "valuation_percentile": 50.39,
      "total_shares": 451052859,
      "industries": [
        {
          "name": "通信",
          "level": 1
        },
        {
          "name": "通信设备",
          "level": 2
        },
        {
          "name": "通信终端及配件",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "中字头央企指数",
        "华为平台指数",
        "专精特新小巨人主题指数",
        "信创产业指数",
        "央企通信指数",
        "中电科技系指数",
        "手机陶瓷外壳指数",
        "氮化铝指数"
      ],
      "score_company": 6.4,
      "score_trend": 6.3,
      "score_value": 6.5,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 通信终端及配件 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 57% ，利润成长性强。"
        },
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 10% ，创造价值的能力较强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 132% ，净利润现金含量很高。"
        },
        {
          "tag": "户数",
          "text": "2026年06月18日至2026年07月20日期间，股东户数减少 31% ，大资金买入。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月17日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月26日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "评级",
          "text": "近6月，没有机构发布研究报告，机构关注度低。"
        }
      ],
      "events": [
        {
          "content": "2026/09/11解禁1.11亿股，占总股本24.59%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-11"
        },
        {
          "content": "预计2026/08/25发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-25"
        },
        {
          "content": "中瓷电子：关于控股子公司河北博威集成电路有限公司使用部分闲置募集资金进行现金管理的进展公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "中瓷电子：关于控股子公司河北博威集成电路有限公司使用部分闲置募集资金进行现金管理到期赎回的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "中瓷电子：关于使用部分闲置募集资金进行现金管理到期赎回公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 2143361604.63,
      "revenue_yoy": 0.136177,
      "operating_profit": 533714271.66,
      "operating_profit_yoy": 0.19171,
      "net_profit": 500964846.15,
      "net_profit_yoy": 0.180047,
      "gross_profit": 792645249.02,
      "gross_profit_yoy": 0.219947,
      "cogs": 1350716355.61,
      "gross_margin": 36.98,
      "pe_forward": null,
      "valuation_history_days": 288,
      "valuation_history_from": "20230105",
      "current_price": 98.55,
      "price": 98.55,
      "ma5": 104.19,
      "ma10": 106.6,
      "ma20": 128.07,
      "dist_ma5_pct": -5.4,
      "dist_ma10_pct": -7.5,
      "dist_ma20_pct": -23.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 7.8,
        "pct_float": 2.52,
        "chg5_pct": -7.01,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688531.SH",
      "fetch_time": "2026-07-31T11:40:55+0800",
      "name": "日联科技",
      "pe": 105.855,
      "pb": 5.8951,
      "ps_ttm": 16.6635,
      "pcf_ttm": 103.5296,
      "valuation_percentile": 77.16,
      "total_shares": 165593939,
      "industries": [
        {
          "name": "机械设备",
          "level": 1
        },
        {
          "name": "专用设备",
          "level": 2
        },
        {
          "name": "其他专用设备",
          "level": 3
        }
      ],
      "concepts": [
        "贷款回购指数",
        "专精特新小巨人主题指数",
        "股权激励指数",
        "专精特新小巨人指数",
        "可转债预案指数",
        "专用设备精选指数"
      ],
      "score_company": 9.0,
      "score_trend": 6.3,
      "score_value": 4.8,
      "highlights": [
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 34% ，最新季度归母净利润同比增长 77% ，成长能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 4.5% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 1.4亿元 ，较上期增长 30% ，占2025年营收 13% ，在手订单充足。"
        },
        {
          "tag": "评级",
          "text": "近90天， 10家 机构给出评级，其中 90% 为“买入”，距目标价的上涨空间为 52% 。"
        },
        {
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 5.4% ，很受外资机构青睐；公募基金持股 3.4% ，较受内资机构青睐。"
        },
        {
          "tag": "回购",
          "text": "近2月，公司累计回购 22万股 ，占总股本比例 0.14% ，金额合计 1209万元 。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "2026/09/30解禁5081.51万股，占总股本30.69%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-30"
        },
        {
          "content": "预计2026/08/15发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-15"
        },
        {
          "content": "2026/07/21 程树刚(董事)增持 2400股 ，类型为 二级市场买卖 ，成交均价为 118元/股 ，耗资 28.2万元 ，此次增持后的持股数为5010股",
          "tags": [
            "管理层增持"
          ]
        },
        {
          "content": "2026/07/20 程树刚(核心技术人员)增持 2200股 ，类型为 二级市场买卖 ，成交均价为 128元/股 ，耗资 28.1万元 ，此次增持后的持股数为2610股",
          "tags": [
            "管理层增持"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 737085605.14,
      "revenue_yoy": 0.440124,
      "operating_profit": 137761117.76,
      "operating_profit_yoy": 0.166309,
      "net_profit": 123891565.83,
      "net_profit_yoy": 0.179562,
      "gross_profit": 325980864.83,
      "gross_profit_yoy": 0.408721,
      "cogs": 411104740.31,
      "gross_margin": 44.23,
      "pe_forward": null,
      "valuation_history_days": 313,
      "valuation_history_from": "20250331",
      "current_price": 117.3,
      "price": 117.3,
      "ma5": 122.88,
      "ma10": 126.47,
      "ma20": 149.18,
      "dist_ma5_pct": -4.5,
      "dist_ma10_pct": -7.3,
      "dist_ma20_pct": -21.4,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.41,
        "pct_float": 4.6,
        "chg5_pct": 1.19,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "600522.SH",
      "fetch_time": "2026-07-31T11:40:57+0800",
      "name": "中天科技",
      "pe": 31.3132,
      "pb": 2.6936,
      "ps_ttm": 1.7894,
      "pcf_ttm": 25.3882,
      "valuation_percentile": 87.66,
      "total_shares": 3412949652,
      "industries": [
        {
          "name": "通信",
          "level": 1
        },
        {
          "name": "通信设备",
          "level": 2
        },
        {
          "name": "通信线缆及配套",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "QFII重仓指数",
        "新基建指数",
        "5G指数",
        "信创产业指数",
        "RCEP指数",
        "碳中和指数",
        "一带一路指数",
        "量子技术指数",
        "预期提升指数",
        "光通信指数",
        "通讯设备精选指数",
        "宽带提速指数",
        "深海科技指数",
        "特高压指数",
        "海上丝绸之路指数",
        "海上风电指数",
        "电线电缆指数"
      ],
      "score_company": 9.0,
      "score_trend": 4.6,
      "score_value": 4.2,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 61% ，利润成长性强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 135% ，净利润现金含量很高。"
        },
        {
          "tag": "评级",
          "text": "近90天， 5家 机构给出评级，其中 60% 为“买入”，距目标价的上涨空间为 98% 。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 8.9% ，很受外资机构青睐；公募基金持股 6.9% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月13日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月26日 至今陷入调整，资金有出逃可能。"
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
          "content": "02:30 截至7月29日，A股已有24家光通信产业链上市公司披露上半年业绩预告，其中18家预喜。长飞光纤、杭电股份、亨通光电、中天科技、永鼎股份等上游企业业绩增长，通鼎互联、华脉科技实现扭亏。中游方面，新易盛预计净利润同比增长，中际旭创拟回购股份，德科立、剑桥科技、光迅科技业绩预增。\n下游光器件环节中，源杰科技、天孚通信、光库科技、东田微、三环集团等企业上半年业绩均实现增长。行业供需结构性紧张，算力需求驱动高速光器件需求上行，上游核心元器件供给瓶颈凸显。新易盛表示，全球人工智能算力基础设施建设推进带动高端产品出货。银河证券研报认为，行业景气度由AI算力需求爆发驱动。华西证券研报指出，全球光模块行业面临上游高端芯片供给约束。\n天孚通信表示，交付受上游高速光芯片等物料供给制约，预计供应拐点将至。中际旭创表示，行业需求旺盛，公司产品定价具备竞争力。业内人士预计，光模块供不应求局面或持续至2028年，NPO、CPO等新技术方向持续加速，行业长期向上趋势不变。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "13:04 通信线缆及配套板块重挫，长飞光纤跌超9%，长盈通、亨通光电、永鼎股份、中天科技等跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "中天科技：北京市环球律师事务所上海分所关于江苏中天科技股份有限公司差异化权益分派事项的法律意见书",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 37974445700.59,
      "revenue_yoy": 0.10652,
      "operating_profit": 2804902895.75,
      "operating_profit_yoy": 0.050669,
      "net_profit": 2357139502.07,
      "net_profit_yoy": 0.023475,
      "gross_profit": 5549288006.54,
      "gross_profit_yoy": 0.022219,
      "cogs": 32425157694.05,
      "gross_margin": 14.61,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 29.34,
      "price": 29.34,
      "ma5": 31.27,
      "ma10": 32.67,
      "ma20": 40.76,
      "dist_ma5_pct": -6.2,
      "dist_ma10_pct": -10.2,
      "dist_ma20_pct": -28.0,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7475,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 52.88,
        "pct_float": 5.59,
        "chg5_pct": 0.06,
        "net5_repay_days": 3,
        "signal": "neutral"
      }
    },
    {
      "code": "300806.SZ",
      "fetch_time": "2026-07-31T11:40:57+0800",
      "name": "斯迪克",
      "pe": 412.1037,
      "pb": 11.6727,
      "ps_ttm": 8.7599,
      "pcf_ttm": 310.5922,
      "valuation_percentile": 93.53,
      "total_shares": 633731915,
      "industries": [
        {
          "name": "基础化工",
          "level": 1
        },
        {
          "name": "塑料",
          "level": 2
        },
        {
          "name": "膜材料",
          "level": 3
        }
      ],
      "concepts": [
        "资源股",
        "QFII重仓指数",
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "中小创蓝筹指数",
        "对日反制指数",
        "MLCC指数"
      ],
      "score_company": 7.6,
      "score_trend": 5.8,
      "score_value": 3.7,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 膜材料 行业龙头企业。"
        },
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 18% ，收入成长性较强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 128% ，净利润现金含量很高。"
        },
        {
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.9% ，很受外资机构青睐；公募基金持股 5.2% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月26日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 -138% ，扣非净利润占净利润 51% ，收益质量很低。"
        },
        {
          "tag": "偿债",
          "text": "现金短债比为 0.17 ，带息债务占全部投入资本 60% ，现金保障很弱，偿债压力很大。"
        },
        {
          "tag": "板块",
          "text": "近3月， 膜材料 板块疲软，走势弱于其他 84.9% 的板块。"
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
          "content": "14:36 PCB概念午后持续走强，东方材料、红板科技、矩子科技、国际复材、宏和科技、贤丰控股、景旺电子涨停，贝斯特涨超10%，方邦股份、智信精密、斯迪克、泰和科技、金安国纪跟涨。相关ETF方面，消费电子ETF汇添富（159178）涨1.23%，成交额1427.69万元，消费电子ETF富国（561100）涨1.68%，成交额5934.94万元。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "13:35 MLCC概念股盘中走强，风华高科涨停，斯迪克、昀冢科技、三环集团、国瓷材料、宏达电子、火炬电子等跟涨。消息面上，三星电机近期连续披露两笔AI服务器专用MLCC供货合同，年内长协总额达约7500亿韩元。业内分析认为，全球头部云厂商及AI企业为保障算力建设，通过年度长协锁定产能，反映出AI服务器高端被动元件供需偏紧。此外，村田制作所与三星电机均有扩产计划。\n据中国电子元件行业协会报告，预计2026年全球MLCC市场规模约1341亿元。目前全球主要制造商包括村田、太阳诱电、京瓷、TDK、三星电机、国巨、华新科技、风华高科、三环集团、微容电子等。光大证券指出，随着海外厂商优化产品结构，国内厂商有望承接消费电子、家电及工业控制等领域的增量需求。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/20～2027/01/20 杨比(董事，副经理)计划增持，变动价格说明：本次增持计划不设价格区间，将根据公司股票价格波动情况及资本市场整体趋势，择机实施增持计划 ，拟增持金额不低于 1250万元  交易方式：通过深圳证券交易所交易系统允许的方式（包括但不限于集中竞价、大宗交易等）增持公司股份。",
          "tags": [
            "管理层增持"
          ]
        },
        {
          "content": "2026/07/20～2027/01/20 王超(副经理)计划增持，变动价格说明：本次增持计划不设价格区间，将根据公司股票价格波动情况及资本市场整体趋势，择机实施增持计划 ，拟增持金额不低于 500万元  交易方式：通过深圳证券交易所交易系统允许的方式（包括但不限于集中竞价、大宗交易等）增持公司股份。",
          "tags": [
            "非控股股东增持"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 2238758028.17,
      "revenue_yoy": 0.115652,
      "operating_profit": 31998807.37,
      "operating_profit_yoy": 0.363512,
      "net_profit": 45260131.5,
      "net_profit_yoy": -0.158126,
      "gross_profit": 499740031.28,
      "gross_profit_yoy": 0.070336,
      "cogs": 1739017996.89,
      "gross_margin": 22.32,
      "pe_forward": null,
      "valuation_history_days": 283,
      "valuation_history_from": "20211125",
      "current_price": 41.15,
      "price": 41.15,
      "ma5": 48.83,
      "ma10": 55.62,
      "ma20": 72.93,
      "dist_ma5_pct": -15.7,
      "dist_ma10_pct": -26.0,
      "dist_ma20_pct": -43.6,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 3.63,
        "pct_float": 2.08,
        "chg5_pct": 14.91,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "688629.SH",
      "fetch_time": "2026-07-31T11:40:57+0800",
      "name": "华丰科技",
      "pe": 148.6315,
      "pb": 22.165,
      "ps_ttm": 23.2958,
      "pcf_ttm": 122.3335,
      "valuation_percentile": 55.9,
      "total_shares": 468254966,
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
        "西部大开发指数",
        "科改示范企业指数",
        "高速铜连接指数",
        "华为鲲鹏指数",
        "华鲲振宇指数"
      ],
      "score_company": 8.0,
      "score_trend": 6.3,
      "score_value": 6.2,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 军工电子Ⅲ 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 230% ，利润成长性强。"
        },
        {
          "tag": "ROE",
          "text": "近5年，净资产收益率为 11% ，获取收益的能力较强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.9% ，未来产能扩张后，营收有望进一步增长。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月14日大跌 -11.8% ，且成交额为近20日均值的 1.74倍 ，抛压很重。"
        }
      ],
      "events": [
        {
          "content": "2026/12/14解禁726.21万股，占总股本1.55%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-12-14"
        },
        {
          "content": "预计2026/08/29发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-29"
        },
        {
          "content": "15:00 今天大跌的原因可能是公司股东绵阳华飞等10家合伙企业通过询价转让方式减持股份，市场对减持带来的抛售压力产生担忧。",
          "tags": [
            "快讯",
            "大跌原因"
          ]
        },
        {
          "content": "华丰科技：中国国际金融股份有限公司关于四川华丰科技股份有限公司股东向特定机构投资者询价转让股份相关资格的核查意见",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1659174540.1,
      "revenue_yoy": 1.214709,
      "operating_profit": 225744940.91,
      "operating_profit_yoy": 5.132281,
      "net_profit": 216659714.23,
      "net_profit_yoy": 5.061553,
      "gross_profit": 510533726.29,
      "gross_profit_yoy": 3.076896,
      "cogs": 1148640813.81,
      "gross_margin": 30.77,
      "pe_forward": null,
      "valuation_history_days": 266,
      "valuation_history_from": "20250627",
      "current_price": 134.46,
      "price": 134.46,
      "ma5": 146.88,
      "ma10": 152.03,
      "ma20": 170.17,
      "dist_ma5_pct": -8.5,
      "dist_ma10_pct": -11.6,
      "dist_ma20_pct": -21.0,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 18.23,
        "pct_float": 3.29,
        "chg5_pct": -10.16,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002463.SZ",
      "fetch_time": "2026-07-31T11:40:57+0800",
      "name": "沪电股份",
      "pe": 46.9253,
      "pb": 12.7542,
      "ps_ttm": 9.5574,
      "pcf_ttm": 68.1555,
      "valuation_percentile": 93.19,
      "total_shares": 1924363537,
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
          "name": "印制电路板",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "消费电子产业指数",
        "华为平台指数",
        "新基建指数",
        "5G指数",
        "高盈利成长股",
        "股权激励指数",
        "元宇宙指数",
        "AI应用指数",
        "AI AGENT(小龙虾）指数"
      ],
      "score_company": 9.8,
      "score_trend": 7.2,
      "score_value": 3.7,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月14日，业绩超预期引发股价大幅上涨，当日收涨 10.0% 。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 37% ，最新季度归母净利润同比增长 82% ，成长能力很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 20% ，投入资本回报率为 17% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 7.6% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 6家 机构给出评级，其中 100% 为“买入”，距目标价的上涨空间为 47% 。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 9.0% ，很受外资机构青睐；公募基金持股 12% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月20日大跌 -10% ，股价跌停，抛压很重。"
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
          "content": "07:30 信达证券投研团队覆盖多个行业，过往曾对部分个股进行挖掘。然而，部分研报在相关公司股价上涨后仍维持“买入”评级，风险提示充分性受到质疑。典型案例包括舍得酒业、豆神教育及嘉必优。其中，舍得酒业在2026年4月被维持“买入”评级，但自2025年8月至2026年7月，其股价累计跌幅超43%。豆神教育在2025年8月研报发布时处于阶段高位，随后股价震荡下行，并于2026年5月被实施ST，截至2026年7月29日，股价较研报发布日跌幅超70%。\n嘉必优在2025年8月被信达证券维持“买入”评级，随后股价步入下行通道，至2026年7月29日累计跌幅超70%。另一方面，信达证券研报亦有股价表现较好的案例，如沪电股份和百奥赛图，研报发布后股价均有显著上涨。针对研报审慎性问题，证监会《发布证券研究报告暂行规定》要求证券公司遵循独立、客观、公平、审慎原则，防范利益冲突，禁止传播误导性信息。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "11:18 长江证券研报指出，PCB及CCL板块多家公司披露2026年半年度业绩预告。CCL端，生益科技预计归母净利润同比增长117%至131%。PCB端，沪电股份、深南电路、生益电子预计归母净利润均实现较快增长。按半年度预告区间测算，上述公司Q2归母净利润均较一季度环比提升，显示产业景气度持续验证。AI算力需求扩张及技术升级拉动了高多层、高密度、低损耗PCB需求，相关厂商业绩增长已体现需求向利润端传导。\n长江证券认为，铜价高位运行、电子布涨价及高频高速铜箔供应偏紧，推动覆铜板进入价格传导阶段，金安国纪、华正新材和生益科技通过提价、扩产及产品结构优化实现盈利提升。同时，服务器平台升级带动对高速覆铜板需求，行业正由需求扩张迈向量价共振，高阶PCB与高速CCL仍是核心受益方向。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "沪电股份：关于为控股子公司提供担保的进展公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 13512390231,
      "revenue_yoy": 0.499558,
      "operating_profit": 3111766705,
      "operating_profit_yoy": 0.486993,
      "net_profit": 2713321370,
      "net_profit_yoy": 0.482509,
      "gross_profit": 4783765597,
      "gross_profit_yoy": 0.485769,
      "cogs": 8728624634,
      "gross_margin": 35.4,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 105.25,
      "price": 105.25,
      "ma5": 111.29,
      "ma10": 117.28,
      "ma20": 125.08,
      "dist_ma5_pct": -5.4,
      "dist_ma10_pct": -10.3,
      "dist_ma20_pct": -15.9,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 47.04,
        "pct_float": 2.53,
        "chg5_pct": -10.98,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "603203.SH",
      "fetch_time": "2026-07-31T11:40:57+0800",
      "name": "快克智能",
      "pe": 85.1696,
      "pb": 9.2426,
      "ps_ttm": 10.9165,
      "pcf_ttm": 46.6406,
      "valuation_percentile": 85.97,
      "total_shares": 330011653,
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
        "华为平台指数",
        "专精特新小巨人主题指数",
        "专精特新小巨人指数",
        "AI手机指数",
        "苹果指数",
        "工业4.0指数",
        "机器人指数",
        "半导体设备指数",
        "新能源设备指数",
        "机器视觉指数"
      ],
      "score_company": 8.1,
      "score_trend": 4.7,
      "score_value": 3.9,
      "highlights": [
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 17% ，创造价值的能力很强。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 2.9% ，现金分红极高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 6.0% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月20日大跌 -10% ，股价跌停，抛压很重。"
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
          "content": "快克智能：北京市天元律师事务所关于快克智能装备股份有限公司2025年限制性股票激励计划部分回购注销及首次授予部分第一个解除限售期解除限售条件成就的法律意见",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "2026/07/24解禁233.57万股，占总股本0.71%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-07-24"
        },
        {
          "content": "快克智能：北京市天元律师事务所关于快克智能装备股份有限公司2025年限制性股票激励计划部分限制性股票回购注销及首次授予部分第一个解除限售期解除限售条件成就的法律意见",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "回购总金额不超过2.46万元 （预案）",
          "tags": [
            "公司回购限售股"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 808154881.98,
      "revenue_yoy": 0.182997,
      "operating_profit": 225486155.25,
      "operating_profit_yoy": 0.290802,
      "net_profit": 197826145.51,
      "net_profit_yoy": 0.227572,
      "gross_profit": 399662344.7,
      "gross_profit_yoy": 0.210998,
      "cogs": 408492537.28,
      "gross_margin": 49.45,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 38.03,
      "price": 38.03,
      "ma5": 40.06,
      "ma10": 41.55,
      "ma20": 52.89,
      "dist_ma5_pct": -5.1,
      "dist_ma10_pct": -8.5,
      "dist_ma20_pct": -28.1,
      "iv_proxy": {
        "primary_name": "500ETF",
        "iv_rank": 0.9451,
        "sizing": "tight"
      }
    },
    {
      "code": "601991.SH",
      "fetch_time": "2026-07-31T11:40:57+0800",
      "name": "大唐发电",
      "pe": 13.6476,
      "pb": 2.9801,
      "ps_ttm": 0.9046,
      "pcf_ttm": 2.9587,
      "valuation_percentile": 85.11,
      "total_shares": 18506710504,
      "industries": [
        {
          "name": "公用事业",
          "level": 1
        },
        {
          "name": "电力",
          "level": 2
        },
        {
          "name": "火力发电",
          "level": 3
        }
      ],
      "concepts": [
        "大央企重组指数",
        "煤电重组指数",
        "电力股精选指数",
        "央企电力燃气指数",
        "煤制烯烃指数",
        "电改指数",
        "火电指数",
        "近期定增指数",
        "CDM指数",
        "阶梯电价指数",
        "大唐系指数"
      ],
      "score_company": 7.2,
      "score_trend": 7.5,
      "score_value": 4.0,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 火力发电 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年04月29日，业绩超预期引发股价跳空高开，当日收涨 6.19% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 29% ，利润成长性强。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 111% ，销售收入现金含量较强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 6.9% ，未来产能扩张后，营收有望进一步增长。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月24日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月03日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "偿债",
          "text": "现金短债比为 0.15 ，带息债务占全部投入资本 64% ，现金保障很弱，偿债压力很大。"
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
          "content": "17:27 7月29日，A股电力板块午后发力，京能电力涨停，桂冠电力此前已封板。截至收盘，桂冠电力市值达861亿元，年内累计涨近43%。乐山电力、华光环能、宝新能源、大唐发电等跟涨。电网设备板块同步回升，汉缆股份、三变科技、海兴电力涨停。电力板块走强受多地用电负荷刷新纪录影响。辽宁电网全社会最大用电负荷达4410万千瓦，刷新历史纪录。7月以来，江苏、浙江、广东等多地电网用电负荷持续刷新历史峰值，全国最高负荷达15.51亿千瓦。国家发展改革委预计今夏全国最高用电负荷将达16亿千瓦。国际能源署报告指出，全球电力需求预计今明两年保持较快增长。长城证券认为，短期高温天气及煤价回升对电价形成支撑，火电龙头估值处近三年低位，具备修复潜力；水电来水改善带动发电量提升，防御配置价值突出。国金证券指出，煤电龙头具备股息基础，看好火电板块业绩逐季度改善。长江证券建议关注国电电力、陕西能源、华能蒙电、华能国际、华电国际、华润电力、福能股份、长江电力、国投电力、川投能源、华能水电、中国核电、中广核电力、龙源电力、新天绿色能源、中闽能源等。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "02:15 “十五五”规划将新型电网与算力网纳入国家“六张网”顶层规划。到2030年，全国电力总装机预计达54亿千瓦，风电、太阳能发电装机比重超过50%。国电南瑞表示，电网角色正从电力传输通道升级为新型能源体系的核心枢纽。大唐发电指出，新型电网与新型电力系统需一体规划建设。平高电气认为，新型电网形态将从单向逐级升级为“主配微协同”。中国核电表示，核电作为清洁低碳基荷电源，在多能互补模式中作用凸显。\n2026年上半年，国家电网固定资产投资3100亿元，同比增长12.6%；南方电网投资892.62亿元，同比增长14.79%。大唐发电正布局三北新能源外送基地、城市热电联产及东部智慧能源项目。平高电气近期中标多项国家电网特高压项目。在算电协同方面，国电南瑞已完成跨时空双向柔性调度验证，推动算力中心向可调度资源转型。\n中信证券分析，算电协同对应总投资规模约2万亿元，年均复合增速达42%。新华资产研究员认为，新型电网相关需求为市场提供了优质底层资产。公用事业板块2025年自由现金流同比提升，火电板块自由现金流大幅转正。长江电力承诺2026年至2030年分红率不低于归母净利润的70%。华夏久盈研究员表示，电力行业现金流稳定，与保险负债久期匹配。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "大唐发电：大唐发电H股通函",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "大唐发电：大唐发电2026年半年度上网电量完成情况公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 89344803000,
      "revenue_yoy": -0.018189,
      "operating_profit": 11633806000,
      "operating_profit_yoy": 0.437537,
      "net_profit": 9420521000,
      "net_profit_yoy": 0.463668,
      "gross_profit": 17341744000,
      "gross_profit_yoy": 0.3008,
      "cogs": 72003059000,
      "gross_margin": 19.41,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 6.17,
      "price": 6.17,
      "ma5": 6.32,
      "ma10": 6.3,
      "ma20": 6.6,
      "dist_ma5_pct": -2.4,
      "dist_ma10_pct": -2.1,
      "dist_ma20_pct": -6.5,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7475,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 7.16,
        "pct_float": 0.99,
        "chg5_pct": 0.76,
        "net5_repay_days": 3,
        "signal": "neutral"
      }
    },
    {
      "code": "002821.SZ",
      "fetch_time": "2026-07-31T11:40:57+0800",
      "name": "凯莱英",
      "pe": 50.3851,
      "pb": 3.2001,
      "ps_ttm": 8.0715,
      "pcf_ttm": 37.6736,
      "valuation_percentile": 37.44,
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
        "RCEP指数",
        "大消费指数",
        "银发经济指数",
        "专精特新小巨人指数",
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
      "score_trend": 7.3,
      "score_value": 6.3,
      "highlights": [
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
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.0% ，较受外资机构青睐；公募基金持股 20% ，很受内资机构青睐。"
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
          "content": "凯莱英：关于向控股子公司增资暨关联交易的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "07:30 在2026年(第43届)全国医药工业信息年会上，2025年度中国医药工业主营业务收入前100位企业名单揭晓。国药集团、华润医药、齐鲁制药、远大集团、诺和诺德(中国)、复星医药、石药集团、恒瑞医药、正大天晴、上海医药位列前10位。2025年百强企业主营业务收入合计10002.2亿元，同比下降约0.5%。入围门槛为30.0亿元。34家企业实现营收和利润双增长，35家双下降。百强企业平均研发费用达8.4亿元，研发强度从8.2%提升至8.4%。\n百强名单包括：中国医药集团、华润医药、齐鲁制药、远大集团、诺和诺德(中国)、复星医药、石药集团、恒瑞医药、正大天晴、上海医药、拜耳医药保健、修正药业、北京诺华制药、科伦药业、沈阳三生制药、威高集团、晖致制药(大连)、广州医药集团、阿斯利康制药、人福医药、新和成、赛诺菲(中国)、扬子江药业、丽珠医药、江苏豪森药业、信达生物、江西济民可信、长春高新、步长制药、珠海联邦制药、北京同仁堂、鲁南制药、西安杨森、云南白药、东阳光实业、新华制药、杭州默沙东、华海药业、华北制药、天津市医药集团、鱼跃医疗、以岭药业、普洛药业、默克制药(江苏)、费森尤斯卡比(中国)、凯莱英、海正药业、上海罗氏制药、辉瑞制药、浙江医药、先声药业、哈药集团、济川药业、鲁抗医药、北京泰德制药、康恩贝、乐普医疗、九洲药业、海普瑞、上海创诺医药、恩华药业、红日药业、康弘药业、华兰生物、赫力昂(苏州)、青峰医药、绿叶医药、礼来苏州制药、海思科、上海勃林格殷格翰、片仔癀、四川好医生攀西药业、成都倍特药业、信立泰、上海莱士、南京健友、京新药业、东富龙、东北制药、石家庄四药、仙琚制药、羚锐制药、特宝生物、中美天津史克、神威药业、齐都药业、贝达药业、辰欣科技、东软医疗、苏中健康、广州康臣药业、华邦健康、安图生物、康缘药业、贵州健兴药业、卫材(中国)、瑞阳制药。\n名单还包括健康元、楚天科技、九典制药。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:33股价达到 185.0 元，创近24个月新高",
          "tags": [
            "股价新高"
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
      "valuation_history_from": "20210802",
      "current_price": 155.01,
      "price": 155.01,
      "ma5": 159.42,
      "ma10": 163.53,
      "ma20": 164.99,
      "dist_ma5_pct": -2.8,
      "dist_ma10_pct": -5.2,
      "dist_ma20_pct": -6.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.19,
        "pct_float": 1.77,
        "chg5_pct": -4.3,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688008.SH",
      "fetch_time": "2026-07-31T11:40:58+0800",
      "name": "澜起科技",
      "pe": 100.9121,
      "pb": 12.8063,
      "ps_ttm": 45.3209,
      "pcf_ttm": 104.899,
      "valuation_percentile": 73.98,
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
        "成交额TOP20指数"
      ],
      "score_company": 9.4,
      "score_trend": 7.2,
      "score_value": 4.6,
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
          "text": "近90天， 5家 机构给出评级，其中 60% 为“买入”，距目标价的上涨空间为 96% 。"
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
          "content": "11:10 创业板人工智能ETF华夏（159381）、科创创业人工智能ETF景顺（159142）、科创人工智能ETF广发（588760）涨超8%。AI相关个股持续走强，昆仑万维20cm涨停，金山办公涨超15%，澜起科技、寒武纪、新易盛等涨超6%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "09:23 兆易创新涨14.99%，澜起科技涨14.96%。消息方面，韩国综合指数涨超16%，其中SK海力士涨超28%，三星电子涨逾24%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "澜起科技：H股公告-翌日披露报表",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "截至2026/07/30，公司累计回购 50.0万股 ，占总股本比例为 0.04% ，最高成交价为 210元/股 ，最低成交价为 192元/股 ，耗资 1.03亿元  （进行中）",
          "tags": [
            "公司回购流通股"
          ],
          "date": "2026-10-24"
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
      "valuation_history_from": "20210802",
      "current_price": 207.5,
      "price": 207.5,
      "ma5": 220.03,
      "ma10": 212.74,
      "ma20": 246.33,
      "dist_ma5_pct": -5.7,
      "dist_ma10_pct": -2.5,
      "dist_ma20_pct": -15.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 147.14,
        "pct_float": 6.53,
        "chg5_pct": -8.42,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002432.SZ",
      "fetch_time": "2026-07-31T11:40:59+0800",
      "name": "九安医疗",
      "pe": 13.792,
      "pb": 1.5118,
      "ps_ttm": 27.2731,
      "pcf_ttm": null,
      "valuation_percentile": 52.92,
      "total_shares": 465893881,
      "industries": [
        {
          "name": "医药生物",
          "level": 1
        },
        {
          "name": "医疗器械",
          "level": 2
        },
        {
          "name": "体外诊断",
          "level": 3
        }
      ],
      "concepts": [
        "贷款回购指数",
        "小米产业链指数",
        "医药数智化指数",
        "肺炎主题指数",
        "医疗改革指数",
        "移动医疗指数",
        "健康中国指数",
        "新冠肺炎检测指数",
        "互联网医疗指数",
        "Kimi指数",
        "新冠抗原检测指数",
        "移动健康指数"
      ],
      "score_company": 7.6,
      "score_trend": 7.1,
      "score_value": 5.7,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 体外诊断 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年07月15日，业绩超预期引发股价跳空高开，当日收涨 10.0% 。"
        },
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 26% ，创造价值的能力较强。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 2.7% ，较受外资机构青睐；公募基金持股 6.2% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月20日大跌 -8.46% ，且成交额为近20日均值的 4.76倍 ，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月27日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 -16% ，收益质量很低。"
        },
        {
          "tag": "波动",
          "text": "近10天，日均换手率 12% ，短线资金追逐，波动风险较高。"
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
          "content": "07:36 截至7月27日，医药生物行业102家上市公司披露2026年中期业绩预告。其中，业绩预增、略增或扭亏的企业共47家，占比约46%。九安医疗、吉林敖东、艾力斯等企业预计净利润居前，以预告净利润下限统计，上述5家公司预计上半年净利润超过10亿元。九安医疗预计上半年归母净利润为28亿元至34亿元，同比增长204.29%至269.5%，主要系科创投资领域底层标的估值上涨。吉林敖东预计上半年归母净利润为19.22亿元至21.79亿元，同比增长50%至70%，主要系投资收益增加。石药创新预计上半年归母净利润为11.8亿元至13.6亿元，实现扭亏为盈，主要源于生物制药业务研发成果兑现及产品获批上市。\n富祥股份预计上半年归母净利润为1.65亿元至2.15亿元，同比扭亏为盈，主要受新能源业务驱动。此外，医药生物行业有45家公司预计上半年亏损，包括昆药集团、珍宝岛、双鹭药业等。昆药集团预计上半年归母净利润为-4亿元至-3.3亿元，由盈转亏，主要受行业政策收紧、市场环境调整及自身经营模式转型影响。珍宝岛预计上半年归母净利润为-2.55亿元至-2.98亿元，主要因主要产品销售未达预期及客户回款延迟导致信用减值损失增加。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "02:47 九安医疗以有限合伙人身份出资1亿元参与投资天津砺思星雀创业投资合伙企业（有限合伙）。近日，公司收到通知，该基金已完成募集，募集资金总额为9.28亿元。公司作为有限合伙人进行财务性投资，本次投资无保本及最低收益承诺，存在投资回收期长、流动性低及无法实现预期收益的风险。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "九安医疗：关于与专业投资机构共同投资的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价开盘上涨 10.00% ，股价收盘涨幅 10.00%",
          "tags": [
            "股价上涨"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1069311569.11,
      "revenue_yoy": -0.488871,
      "operating_profit": 1595068871.16,
      "operating_profit_yoy": -0.122416,
      "net_profit": 1587758433.66,
      "net_profit_yoy": 0.035331,
      "gross_profit": 699316044.79,
      "gross_profit_yoy": -0.53366,
      "cogs": 369995524.32,
      "gross_margin": 65.4,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 66.81,
      "price": 66.81,
      "ma5": 69.46,
      "ma10": 73.24,
      "ma20": 67.77,
      "dist_ma5_pct": -3.8,
      "dist_ma10_pct": -8.8,
      "dist_ma20_pct": -1.4,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 12.59,
        "pct_float": 4.35,
        "chg5_pct": -4.14,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688777.SH",
      "fetch_time": "2026-07-31T11:40:59+0800",
      "name": "中控技术",
      "pe": 190.379,
      "pb": 7.6823,
      "ps_ttm": 9.4591,
      "pcf_ttm": 279.6633,
      "valuation_percentile": 69.14,
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
      "score_trend": 7.2,
      "score_value": 4.9,
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
          "text": " 11家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
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
          "content": "14:37 2026年二季度基金季报显示，上证380ETF易方达新进重仓股包括源杰科技、华虹宏力、中科飞测、华峰测控、中控技术、芯源微、剑桥科技、长飞光纤、士兰微。今日午盘，上证380指数上涨1.054%，报6721.19点。上证380ETF易方达(530380)午盘上涨1.703%，成交额586万元，换手率3.89%，基金规模1.51亿元。资金面上，该ETF上一交易日主力资金净流出21万元，近5个交易日累计净流入31万元。前十大权重股合计占比14.49%，其中源杰科技涨2.88%，中科飞测涨6.97%。该ETF综合费率0.20%/年，近1月跟踪误差0.058%，近1年超基准年化+3.39%，并配有场外联接基金。",
          "tags": [
            "资讯"
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
      "valuation_history_days": 297,
      "valuation_history_from": "20221125",
      "current_price": 79.9,
      "price": 79.9,
      "ma5": 81.86,
      "ma10": 85.95,
      "ma20": 96.46,
      "dist_ma5_pct": -2.4,
      "dist_ma10_pct": -7.0,
      "dist_ma20_pct": -17.2,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 26.47,
        "pct_float": 4.16,
        "chg5_pct": -7.55,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002916.SZ",
      "fetch_time": "2026-07-31T11:40:59+0800",
      "name": "深南电路",
      "pe": 57.788,
      "pb": 12.7635,
      "ps_ttm": 8.2496,
      "pcf_ttm": 60.4757,
      "valuation_percentile": 88.58,
      "total_shares": 681166595,
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
          "name": "印制电路板",
          "level": 3
        }
      ],
      "concepts": [
        "HALO指数",
        "TMT指数",
        "中特估指数",
        "三新指数",
        "科技龙头指数",
        "出海贸易指数",
        "人工智能+指数",
        "5G应用指数",
        "消费电子产业指数",
        "华为平台指数",
        "珠三角指数",
        "新基建指数"
      ],
      "score_company": 9.5,
      "score_trend": 7.1,
      "score_value": 3.9,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 印制电路板 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 55% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 16% ，投入资本回报率为 14% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 144% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 6.6% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 3.5亿元 ，较上期增长 104% ，占2025年营收 1.5% ，在手订单充足。"
        },
        {
          "tag": "评级",
          "text": "近90天， 9家 机构给出评级，其中 100% 为“买入”，距目标价的上涨空间为 92% 。"
        },
        {
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 2.8% ，较受外资机构青睐；公募基金持股 7.3% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月28日大跌 -10% ，股价跌停，抛压很重。"
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
          "content": "09:33 印制电路板板块低开下挫，东山精密跌超7%，景旺电子、广合科技、深南电路、红板科技等跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "11:18 长江证券研报指出，PCB及CCL板块多家公司披露2026年半年度业绩预告。CCL端，生益科技预计归母净利润同比增长117%至131%。PCB端，沪电股份、深南电路、生益电子预计归母净利润均实现较快增长。按半年度预告区间测算，上述公司Q2归母净利润均较一季度环比提升，显示产业景气度持续验证。AI算力需求扩张及技术升级拉动了高多层、高密度、低损耗PCB需求，相关厂商业绩增长已体现需求向利润端传导。\n长江证券认为，铜价高位运行、电子布涨价及高频高速铜箔供应偏紧，推动覆铜板进入价格传导阶段，金安国纪、华正新材和生益科技通过提价、扩产及产品结构优化实现盈利提升。同时，服务器平台升级带动对高速覆铜板需求，行业正由需求扩张迈向量价共振，高阶PCB与高速CCL仍是核心受益方向。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "于2026-07-16接待5位投资者调研。",
          "tags": [
            "机构调研"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 16754015317.37,
      "revenue_yoy": 0.283882,
      "operating_profit": 2571070322.26,
      "operating_profit_yoy": 0.605669,
      "net_profit": 2328338717.68,
      "net_profit_yoy": 0.564768,
      "gross_profit": 4725392875.1,
      "gross_profit_yoy": 0.397739,
      "cogs": 12028622442.27,
      "gross_margin": 28.2,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 316.01,
      "price": 316.01,
      "ma5": 331.57,
      "ma10": 336.82,
      "ma20": 383.01,
      "dist_ma5_pct": -4.7,
      "dist_ma10_pct": -6.2,
      "dist_ma20_pct": -17.5,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 16.36,
        "pct_float": 0.87,
        "chg5_pct": -1.62,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "000938.SZ",
      "fetch_time": "2026-07-31T11:40:59+0800",
      "name": "紫光股份",
      "pe": 47.1384,
      "pb": 6.529,
      "ps_ttm": 0.9636,
      "pcf_ttm": 81.1351,
      "valuation_percentile": 50.84,
      "total_shares": 2860079874,
      "industries": [
        {
          "name": "计算机",
          "level": 1
        },
        {
          "name": "IT服务Ⅱ",
          "level": 2
        },
        {
          "name": "IT服务Ⅲ",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "三新指数",
        "科技龙头指数",
        "双循环指数",
        "5G应用指数",
        "半导体产业指数",
        "新基建指数",
        "数字经济指数",
        "5G指数",
        "员工持股指数",
        "信创产业指数",
        "AI备案指数",
        "成交额TOP10指数"
      ],
      "score_company": 8.6,
      "score_trend": 7.2,
      "score_value": 5.6,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 IT服务Ⅲ 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 92% ，利润成长性强。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 132% ，销售收入现金含量很强。"
        },
        {
          "tag": "评级",
          "text": "近90天， 12家 机构给出评级，其中 75% 为“买入”，距目标价的上涨空间为 60% 。"
        },
        {
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 3.3% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月23日大跌 -5.46% ，且成交额为近20日均值的 1.78倍 ，抛压很重。"
        },
        {
          "tag": "商誉",
          "text": "商誉占净资产 90% ，商誉减值风险很高。"
        },
        {
          "tag": "偿债",
          "text": "现金短债比为 0.28 ，带息债务占全部投入资本 66% ，现金保障很弱，偿债压力很大。"
        },
        {
          "tag": "波动",
          "text": "近10天，日均换手率 15% ，短线资金追逐，波动风险较高。"
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
          "content": "23:44 紫光股份在互动平台表示，公司51.2T CPO硅光数据中心交换机产品，2025年已实现批量交付部署，融合核心技术优势，创新散热与智能无损网络设计，有效降低时延和功耗。800G国芯智算交换机依托国产核心芯片，安全可控属性突出，广泛适配政府、金融、运营商、能源等对信息安全要求极高的行业场景，能够具备支撑大规模算力集群组网的能力。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "16:25 紫光股份今日跌10.00%，成交额132.73亿元，换手率12.22%，盘后龙虎榜数据显示，深股通专用席位买入6.66亿元并卖出8.57亿元，东方财富长春人民大街席位净买入2.14亿元，有4家机构专用席位净卖出4.83亿元。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "紫光股份：2026年第四次临时股东会法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "王竑弢 任法定代表人",
          "tags": [
            "管理层变更"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 77321505402.98,
      "revenue_yoy": 0.314111,
      "operating_profit": 1897831396.93,
      "operating_profit_yoy": -0.119504,
      "net_profit": 1722764196.83,
      "net_profit_yoy": -0.148601,
      "gross_profit": 10608273139.34,
      "gross_profit_yoy": 0.024923,
      "cogs": 66713232263.64,
      "gross_margin": 13.72,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20210802",
      "current_price": 33.6,
      "price": 33.6,
      "ma5": 238.25,
      "ma10": 263.45,
      "ma20": 257.78,
      "dist_ma5_pct": -85.9,
      "dist_ma10_pct": -87.2,
      "dist_ma20_pct": -87.0,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.8795,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 46.42,
        "pct_float": 4.83,
        "chg5_pct": -6.62,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688378.SH",
      "fetch_time": "2026-07-31T11:40:59+0800",
      "name": "奥来德",
      "pe": 75.0798,
      "pb": 4.7542,
      "ps_ttm": 14.4656,
      "pcf_ttm": 30.542,
      "valuation_percentile": 76.1,
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
      "score_company": 8.0,
      "score_trend": 4.9,
      "score_value": 4.5,
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
          "tag": "产能",
          "text": "在建工程占总资产 2.7% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 1.4亿元 ，较上期增长 860% ，占2025年营收 25% ，在手订单充足。"
        },
        {
          "tag": "评级",
          "text": "近90天， 7家 机构给出评级，其中 86% 为“买入”，距目标价的上涨空间为 89% 。"
        }
      ],
      "risks": [
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 33% ，扣非净利润占净利润 37% ，收益质量很低。"
        },
        {
          "tag": "板块",
          "text": "近3月， 光学元件 板块疲软，走势弱于其他 93.2% 的板块。"
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
          "content": "03:16 奥来德于2026年7月24日召开董事会，审议通过了关于首次公开发行股票超募资金投资项目结项并将节余募集资金永久补充流动资金的议案。结项项目包括“钙钛矿结构型太阳能电池蒸镀设备的开发项目”及“低成本有机钙钛矿载流子传输材料和长寿命器件开发项目”。该事项无需提交股东会审议。\n公司通过严控项目开支、优化资源配置及开展现金管理，形成了资金节余。计划将专户内剩余的1,462.56万元（实际金额以转出当日为准）永久补充流动资金，并办理相关募集资金专户销户手续。保荐机构东方证券对上述事项无异议，认为符合相关法律法规要求。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "奥来德：东方证券股份有限公司关于吉林奥来德光电材料股份有限公司首次公开发行股票超募资金投资项目结项并将节余募集资金永久补充流动资金的核查意见",
          "tags": [
            "重要公告"
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
      "valuation_history_days": 314,
      "valuation_history_from": "20220905",
      "current_price": 36.22,
      "price": 36.22,
      "ma5": 38.01,
      "ma10": 39.84,
      "ma20": 47.6,
      "dist_ma5_pct": -4.7,
      "dist_ma10_pct": -9.1,
      "dist_ma20_pct": -23.9,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.9,
        "pct_float": 6.12,
        "chg5_pct": 1.55,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "688536.SH",
      "fetch_time": "2026-07-31T11:40:59+0800",
      "name": "思瑞浦",
      "pe": 121.85,
      "pb": 5.0514,
      "ps_ttm": 13.2196,
      "pcf_ttm": 100.4898,
      "valuation_percentile": 32.95,
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
        "智能家居指数",
        "AIPC指数",
        "模拟芯片指数",
        "苏州工业园区指数"
      ],
      "score_company": 8.3,
      "score_trend": 6.8,
      "score_value": 7.4,
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
          "content": "公司发布股权激励计划预案，股价盘中上涨 8.03% ，股价收盘涨幅 6.95%",
          "tags": [
            "股价上涨"
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
      "valuation_history_days": 304,
      "valuation_history_from": "20220922",
      "current_price": 240.0,
      "price": 240.0,
      "ma5": 244.23,
      "ma10": 247.72,
      "ma20": 289.62,
      "dist_ma5_pct": -1.7,
      "dist_ma10_pct": -3.1,
      "dist_ma20_pct": -17.1,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.5,
        "pct_float": 3.55,
        "chg5_pct": -9.6,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "603127.SH",
      "fetch_time": "2026-07-31T11:40:59+0800",
      "name": "昭衍新药",
      "pe": 64.2203,
      "pb": 3.7549,
      "ps_ttm": 18.853,
      "pcf_ttm": 62.7066,
      "valuation_percentile": 39.6,
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
      "score_trend": 8.3,
      "score_value": 6.4,
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
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
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
      "valuation_history_from": "20210802",
      "current_price": 43.94,
      "price": 43.94,
      "ma5": 46.59,
      "ma10": 47.83,
      "ma20": 45.05,
      "dist_ma5_pct": -5.7,
      "dist_ma10_pct": -8.1,
      "dist_ma20_pct": -2.5,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7475,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 6.19,
        "pct_float": 2.46,
        "chg5_pct": -1.79,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "600236.SH",
      "fetch_time": "2026-07-31T11:41:00+0800",
      "name": "桂冠电力",
      "pe": 22.0445,
      "pb": 4.936,
      "ps_ttm": 7.6395,
      "pcf_ttm": 11.6243,
      "valuation_percentile": 95.74,
      "total_shares": 7882377802,
      "industries": [
        {
          "name": "公用事业",
          "level": 1
        },
        {
          "name": "电力",
          "level": 2
        },
        {
          "name": "水力发电",
          "level": 3
        }
      ],
      "concepts": [
        "碳中和指数",
        "西部大开发指数",
        "双百企业指数",
        "电力股精选指数",
        "万得绿电指数",
        "央企电力燃气指数",
        "电改指数",
        "水电指数",
        "电解铝指数",
        "大唐系指数"
      ],
      "score_company": 7.8,
      "score_trend": 9.0,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 40% ，利润成长性强。"
        },
        {
          "tag": "ROE",
          "text": "近5年，净资产收益率为 13% ，获取收益的能力很强。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 3.2% ，现金分红较高。"
        },
        {
          "tag": "强势",
          "text": "近6月，股价涨幅超过A股市场 97% 的股票，走势很强。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月23日大跌 -7.19% ，且成交额为近20日均值的 3.19倍 ，抛压很重。"
        },
        {
          "tag": "偿债",
          "text": "现金短债比为 0.24 ，带息债务占全部投入资本 50% ，现金保障很弱，偿债压力很大。"
        }
      ],
      "events": [
        {
          "content": "2026年半年度：每10股派1.2元（预案）",
          "tags": [
            "分红送转"
          ]
        },
        {
          "content": "桂冠电力：广西桂冠电力股份有限公司关于对中国大唐集团财务有限公司风险持续评估报告的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "桂冠电力：广西桂冠电力股份有限公司对外投资的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "桂冠电力：广西桂冠电力股份有限公司与关联人共同投资的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 7335479334.64,
      "revenue_yoy": -0.002479,
      "operating_profit": 3253371406.85,
      "operating_profit_yoy": 0.115996,
      "net_profit": 2766394705.31,
      "net_profit_yoy": 0.107115,
      "gross_profit": 4079377214.71,
      "gross_profit_yoy": 0.128125,
      "cogs": 3256102119.93,
      "gross_margin": 55.61,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 10.7,
      "price": 10.7,
      "ma5": 74.15,
      "ma10": 85.94,
      "ma20": 83.77,
      "dist_ma5_pct": -85.6,
      "dist_ma10_pct": -87.5,
      "dist_ma20_pct": -87.2,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7475,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 1.43,
        "pct_float": 0.17,
        "chg5_pct": 2.31,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "002080.SZ",
      "fetch_time": "2026-07-31T11:41:01+0800",
      "name": "中材科技",
      "pe": 37.7329,
      "pb": 3.7563,
      "ps_ttm": 2.3483,
      "pcf_ttm": 20.1526,
      "valuation_percentile": 86.3,
      "total_shares": 1678123584,
      "industries": [
        {
          "name": "建筑材料",
          "level": 1
        },
        {
          "name": "玻璃玻纤",
          "level": 2
        },
        {
          "name": "玻纤制造",
          "level": 3
        }
      ],
      "concepts": [
        "HALO指数",
        "三新指数",
        "中字头央企指数",
        "资源股",
        "碳中和指数",
        "新材料指数",
        "锂电池指数",
        "养老金指数",
        "电路板指数",
        "新能源指数",
        "老基建指数",
        "氢能指数",
        "燃料电池指数",
        "风力发电指数",
        "电子布指数",
        "覆铜板指数",
        "玻璃纤维指数",
        "中国建材集团指数",
        "LNG指数",
        "中建材系指数"
      ],
      "score_company": 8.7,
      "score_trend": 3.6,
      "score_value": 4.2,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 40% ，利润成长性强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 158% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.0% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 4.2亿元 ，较上期增长 7.7% ，占2025年营收 1.4% ，在手订单充足。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 4.5% ，很受外资机构青睐；公募基金持股 4.7% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月16日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月29日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "偿债",
          "text": "现金短债比为 0.14 ，货币资金对短期债务的保障很弱。"
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
          "content": "15:01 国际复材发布2026年上半年业绩预告，预计归母净利润为5.8亿元至6.8亿元，同比增长151%至194%。公司表示，业绩增长主要受电子级玻璃纤维及制品价格上涨带动。公司在5月份业绩说明会上透露，风电纱、电子布及高频低介电相关产品处于满负荷运行状态，在手订单充足，年产8万吨电子级玻璃纤维智能制造生产线已于2025年内点火投产。\n行业扩产潮引发供给压力担忧。国际复材于2025年12月公告拟投资16.93亿元建设年产3600万米高频高速电子纤维布项目。中材科技亦有相关低介电纤维布扩产计划。业内分析认为，高端电子布缺货态势预计2026年全年持续，但2027年下半年或2028年可能缓解。财务方面，国际复材2026年一季度应收账款达25.42亿元，经营活动现金流量净额为-8399.21万元，同比由正转负。公司在建工程规模增长，截至2026年一季度末，有息负债合计超过117亿元，货币资金为20.60亿元。\n国际复材面临重资产、高应收、紧现金的财务结构，电子布项目建设周期长，下游回款周期拉长，存在资金链风险。2025年公司资产减值损失达3.07亿元，涵盖存货、固定资产及应收款项，显示行业产能过剩与价格波动风险。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "12:45 国际复材发布2026年上半年业绩预告，预计归母净利润为5.8亿元至6.8亿元，同比增长151%至194%。公司表示，业绩增长主要受电子级玻璃纤维及制品价格上涨影响。受电子布市场需求及价格波动影响，公司股价在2026年上半年出现较大波动。经营数据显示，2026年一季度公司营收22.15亿元，应收账款为25.42亿元，经营现金流净额为-8399.21万元。\n行业扩产方面，国际复材于2025年12月公告拟投资16.93亿元建设高频高速电子纤维布项目，建设期至2027年6月。中材科技亦有相关低介电纤维布项目布局。财务数据显示，国际复材2026年一季度末有息负债合计超过117亿元，货币资金为20.60亿元，在建工程规模较期初大幅增长，短期债务压力及财务安全边际受到市场关注。\n国际复材面临重资产、高应收及紧现金的财务结构，电子布项目建设周期较长，需持续投入资金。2025年公司资产减值损失达3.07亿元，涵盖存货、固定资产及应收款项。在行业产能与价格波动背景下，公司资金链风险及后续经营情况仍需审慎考量。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "中材科技：北京市嘉源律师事务所关于中材科技股份有限公司2026年第二次临时股东会的法律意见书",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 21700618098.45,
      "revenue_yoy": 0.290883,
      "operating_profit": 1993899595.22,
      "operating_profit_yoy": 1.221464,
      "net_profit": 1741127886.8,
      "net_profit_yoy": 1.290205,
      "gross_profit": 4269605611.42,
      "gross_profit_yoy": 0.42598,
      "cogs": 17431012487.03,
      "gross_margin": 19.68,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 43.62,
      "price": 43.62,
      "ma5": 47.93,
      "ma10": 51.03,
      "ma20": 64.17,
      "dist_ma5_pct": -9.0,
      "dist_ma10_pct": -14.5,
      "dist_ma20_pct": -32.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 11.66,
        "pct_float": 1.64,
        "chg5_pct": 0.2,
        "net5_repay_days": 3,
        "signal": "neutral"
      }
    },
    {
      "code": "000988.SZ",
      "fetch_time": "2026-07-31T11:41:01+0800",
      "name": "华工科技",
      "pe": 57.553,
      "pb": 8.5502,
      "ps_ttm": 6.4069,
      "pcf_ttm": 224.1312,
      "valuation_percentile": 90.7,
      "total_shares": 1005502707,
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
          "name": "激光设备",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "5G应用指数",
        "消费电子产业指数",
        "贷款回购指数",
        "华为平台指数",
        "QFII重仓指数",
        "新基建指数",
        "5G指数",
        "元宇宙指数",
        "AI手机指数",
        "人形机器人指数",
        "英伟达产业链指数",
        "苹果指数"
      ],
      "score_company": 8.5,
      "score_trend": 6.0,
      "score_value": 3.9,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 激光设备 行业龙头企业。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 56% ，利润成长性强。"
        },
        {
          "tag": "ROE",
          "text": "近5年，净资产收益率为 12% ，获取收益的能力较强。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 2.5% ，较受外资机构青睐。"
        },
        {
          "tag": "增持",
          "text": "近1月，管理层累计实际增持 14万股 ，占总股本比例 0.01% ，金额合计 1368万元 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月16日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年07月01日 至今陷入调整，资金有出逃可能。"
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
          "content": "21:20 2026年7月30日，华福证券发布机械设备行业研究报告，指出AI技术正在重构激光行业需求边界，推动产业跃迁。\n报告认为，激光技术正从传统加工工具向AI制造转型。传统激光产业受工业市场需求收缩影响，竞争加剧。2025年，人工智能的发展带动了激光在集成电路和半导体材料微加工领域的应用，中国市场增长动力主要来自AI催动的数据中心与高速通信需求、消费级激光产品放量及进口替代。随着AI算力需求爆发，数据中心光模块需求激增，CPO及CW激光器订单预期增长。激光产业链涵盖上游材料与器件、中游激光器制造及下游应用。上游激光芯片及光电器件准入门槛较高；中游半导体激光器泵浦源作为核心器件，占总成本30-80%。2025年全球激光设备市场销售收入约240亿美元，中国市场为958亿元。\nAI核心制造场景需求包括：PCB钻孔环节的激光钻孔机；TGV通孔环节的激光诱导深度刻蚀（LIDE）及直接激光烧蚀技术；以及光通信激光器环节，光模块作为AI网络端重要环节，其TOSA组件中的激光器需求持续增长。报告建议关注上游核心元器件厂商：源杰科技、长光华芯、仕佳光子、光迅科技、福晶科技、炬光科技、波长光电、腾景科技、光库科技、长进光子；中游激光器厂商：锐科激光、杰普特、英诺激光、德龙激光；下游激光设备厂商：大族激光、华工科技、大族数控、帝尔激光、联赢激光、海目星、亚威股份。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "16:07 7月27日，湖北自贸板块与湖北板块指数涨幅达2%。湖北ETF博时（159743）当日上涨5.008%，成交额469万元，沪深300指数同期上涨1.15%。成分股中，帝尔激光涨8.76%，兴福电子、三安光电均涨4.76%。湖北ETF博时综合费率为0.60%/年，近1月跟踪误差0.079%。截至2026年二季度末，该ETF规模约1.43亿元，换手率3.28%。前十大权重股中，精测电子涨3.27%，光迅科技涨3.24%，华工科技涨3.30%，三安光电涨4.76%，烽火通信涨4.04%。较上季，鼎龙股份、高德红外、兴福电子、帝尔激光新进前十大重仓股。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/21 熊文(高管、董事)增持 2.00万股 ，类型为 竞价交易 ，成交均价为 95.3元/股 ，耗资 191万元 ，此次增持后的持股数为15.3万股",
          "tags": [
            "管理层增持"
          ]
        },
        {
          "content": "2026/07/21 马新强(董事、高管)增持 5.00万股 ，类型为 竞价交易 ，成交均价为 99.4元/股 ，耗资 497万元 ，此次增持后的持股数为35.0万股",
          "tags": [
            "管理层增持"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 11037981451.57,
      "revenue_yoy": 0.22621,
      "operating_profit": 1463594686.01,
      "operating_profit_yoy": 0.424112,
      "net_profit": 1313538331.11,
      "net_profit_yoy": 0.397976,
      "gross_profit": 2394919674.02,
      "gross_profit_yoy": 0.268063,
      "cogs": 8643061777.55,
      "gross_margin": 21.7,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 91.1,
      "price": 91.1,
      "ma5": 884.71,
      "ma10": 1021.05,
      "ma20": 1292.12,
      "dist_ma5_pct": -89.7,
      "dist_ma10_pct": -91.1,
      "dist_ma20_pct": -92.9,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.8795,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 78.55,
        "pct_float": 8.58,
        "chg5_pct": -10.8,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002203.SZ",
      "fetch_time": "2026-07-31T11:41:01+0800",
      "name": "海亮股份",
      "pe": 40.7039,
      "pb": 2.5095,
      "ps_ttm": 0.4855,
      "pcf_ttm": null,
      "valuation_percentile": 72.24,
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
      "score_trend": 6.9,
      "score_value": 4.4,
      "highlights": [
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.3% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "评级",
          "text": "近90天， 6家 机构给出评级，其中 83% 为“买入”，距目标价的上涨空间为 36% 。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 4.0% ，很受外资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 92% 的股票，走势较强。"
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
          "content": "09:46 7月30日，A股三大指数集体低开，沪指跌0.43%，深成指跌0.93%，创业板指跌1.40%，科创50跌1.51%。盘面上，黄金、油气、有色金属、煤炭板块涨幅居前；电子、电力设备、计算机、机械设备、商贸零售板块跌幅居前。受隔夜美股半导体板块下挫影响，科技板块表现较弱。全市场上涨家数不足两成。隔夜美联储维持利率不变，美股三大股指显著下跌。国内方面，央行预告合计投放2.1万亿元隔夜逆回购，九部门联合印发科技金融数据开发利用通知。此外，中际旭创、京东方A、海亮股份、兆易创新等公司披露回购增持方案。\n今日A股三大指数集体低开，科创50与创业板指跌幅居前。受美股半导体板块重挫及美债收益率上升影响，电子、电力设备板块领跌。央行预告合计2.1万亿元逆回购护航流动性，多家龙头公司披露大额回购增持方案。机构认为短期市场或维持震荡再平衡，科技主线受外部扰动，低位板块轮动修复有望延续。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "02:01 海亮股份第九届董事会第十四次会议审议通过了《关于购买控股子公司部分股权暨关联交易的议案》及召开2026年第五次临时股东会的议案。本次关联交易涉及购买控股子公司部分股权，关联董事已回避表决。\n海亮股份拟以97,159.8万元收购控股子公司甘肃海亮18.6916%的股权，交易完成后持股比例将增至67.2897%。公司表示此举旨在优化股权结构、提升治理水平及盈利能力。\n公司拟与深创投新材料基金、工融金投及海亮集团签署协议，受让上述转让方持有的甘肃海亮共计18.6916%股权。本次交易构成关联交易，不构成重大资产重组，尚需股东会批准。\n披露了交易对手方深创投新材料基金、工融金投及关联方海亮集团的基本情况。海亮集团为公司控股股东，上述各方均不属于失信被执行人。\n甘肃海亮主要从事电子专用材料制造及销售等业务。截至2026年6月30日，甘肃海亮存续借款余额合计18.15亿元，部分由公司提供连带责任保证担保。\n本次交易定价以浙江中企华资产评估有限公司出具的评估报告为依据，采用收益法评估，甘肃海亮股东全部权益评估值为515,118.75万元，增值率34.31%。最终确定交易价格为97,159.8万元。\n海亮股份与海亮集团签署股权转让协议，受让其持有的4.6729%股权，价款为242,828,000元，约定于2026年8月28日前支付。\n海亮股份与深创投新材料基金签署协议，以607,070,000元受让其持有的甘肃海亮股权。\n海亮股份与工融金投签署协议，以12,170.00万元受让其持有的部分股权。交易完成后，工融金投仍持有甘肃海亮4.6729%股权。\n本次交易不涉及人员安置及高层变动。独立董事认为交易定价公允，决策程序合规。同时提示铜箔行业存在周期性波动风险。\n海亮集团计划在6个月内增持公司股份，金额不低于6亿元且不超过10亿元。海亮集团已取得中国建设银行提供的8.6亿元股票增持贷款承诺。\n公司定于2026年8月14日召开2026年第五次临时股东会，审议购买控股子公司股权等议案。\n股东可通过深交所交易系统或互联网投票系统参加本次临时股东会投票。\n提供了股东会授权委托书格式及相关投票说明。",
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
      "valuation_history_from": "20210802",
      "current_price": 17.76,
      "price": 17.76,
      "ma5": 17.84,
      "ma10": 17.87,
      "ma20": 19.15,
      "dist_ma5_pct": -0.5,
      "dist_ma10_pct": -0.6,
      "dist_ma20_pct": -7.2,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.25,
        "pct_float": 2.69,
        "chg5_pct": 4.66,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "600428.SH",
      "fetch_time": "2026-07-31T11:41:01+0800",
      "name": "中远海特",
      "pe": 16.8623,
      "pb": 1.9145,
      "ps_ttm": 1.2635,
      "pcf_ttm": 4.2789,
      "valuation_percentile": 65.8,
      "total_shares": 2743920395,
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
        "中字头央企指数",
        "国企改革指数",
        "贷款回购指数",
        "珠三角指数",
        "一带一路特估指数",
        "一带一路指数",
        "中非合作指数",
        "央企物流运输指数",
        "深海科技指数",
        "海上丝绸之路指数",
        "航运精选指数",
        "港口精选指数",
        "中远海运系指数",
        "中远海运集团指数",
        "粤港澳自贸区指数"
      ],
      "score_company": 7.3,
      "score_trend": 9.8,
      "score_value": 5.0,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月10日，业绩超预期引发股价跳空高开，当日收涨 10.0% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 95% ，利润成长性强。"
        },
        {
          "tag": "分红",
          "text": "近5年，股息收益率均值达到 3.1% ，现金分红较高。"
        },
        {
          "tag": "订单",
          "text": "合同负债 13亿元 ，较上期增长 29% ，占2025年营收 5.8% ，在手订单充足。"
        },
        {
          "tag": "强势",
          "text": "近3月，股价涨幅超过A股市场 99% 的股票，收盘价接近 一年新高 ，走势很强。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "2026/09/21解禁2.99亿股，占总股本10.88%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-21"
        },
        {
          "content": "预计2026/08/27发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-27"
        },
        {
          "content": "09:31股价达到 11.31 元，创近24个月新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "中远海特：关于中远海运特种运输股份有限公司2026年第二次临时股东会的法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "中远海特：中远海运特种运输股份有限公司关于委托中船澄西建造8艘6万吨级多用途重吊船的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 16610522356.82,
      "revenue_yoy": 0.379243,
      "operating_profit": 2107481674.49,
      "operating_profit_yoy": 0.358654,
      "net_profit": 1763024837.6,
      "net_profit_yoy": 0.289424,
      "gross_profit": 3569777483.78,
      "gross_profit_yoy": 0.434728,
      "cogs": 13040744873.04,
      "gross_margin": 21.49,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 11.24,
      "price": 11.24,
      "ma5": 10.99,
      "ma10": 10.91,
      "ma20": 9.97,
      "dist_ma5_pct": 2.2,
      "dist_ma10_pct": 3.0,
      "dist_ma20_pct": 12.8,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7475,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 3.47,
        "pct_float": 1.29,
        "chg5_pct": -7.04,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "600961.SH",
      "fetch_time": "2026-07-31T11:41:01+0800",
      "name": "株冶集团",
      "pe": 12.2692,
      "pb": 4.8363,
      "ps_ttm": 0.9995,
      "pcf_ttm": 8.8647,
      "valuation_percentile": 59.26,
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
        "QFII重仓指数",
        "专精特新小巨人主题指数",
        "有色金属指数",
        "锌电池指数",
        "铅锌矿指数",
        "钴矿指数",
        "央企有色指数",
        "磷化铟指数",
        "蓄电池指数"
      ],
      "score_company": 7.0,
      "score_trend": 6.4,
      "score_value": 5.6,
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
          "text": "公募基金持股 3.8% ，较受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 95% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "分红",
          "text": "近5年，从未实施现金分红，为一毛不拔的铁公鸡。"
        },
        {
          "tag": "板块",
          "text": "近3月， 铅锌 板块疲软，走势弱于其他 89% 的板块。"
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
          "content": "18:46 东方证券发布有色金属行业研究报告指出，锌作为关键工业金属，其供给端存在刚性，且AI算力需求拉动的新型基建及高景气造船行业有望带来超预期需求。在供给端，全球精矿供给分布集中，近年勘探投入下行及矿山品位下降，预计2026年起精矿产量增速下行；冶炼环节受矿端紧缺、副产品收益下降及电力成本约束，产能或趋紧；国内再生锌环节整治趋严，供给约束显现。在需求端，镀锌板消费占比60%，AI数据中心建设预计带动用锌量从2025年的14万吨增长至2030年的34万吨；船舶行业订单充足，牺牲阳极用锌量年复合增速有望达5%。预计2028年锌市场将出现明显供给缺口，价格具备上行空间。\n金融属性方面，随着美国通胀数据降温，加息预期有望回摆，为锌价提供向上弹性。报告建议关注具备自给锌精矿、冶炼规模大且可同步回收稀散金属的公司，重点关注株冶集团，同时关注驰宏锌锗、中金岭南、金徽股份。",
          "tags": [
            "资讯"
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
      "valuation_history_from": "20210802",
      "current_price": 22.66,
      "price": 22.66,
      "ma5": 22.85,
      "ma10": 22.85,
      "ma20": 26.1,
      "dist_ma5_pct": -0.8,
      "dist_ma10_pct": -0.8,
      "dist_ma20_pct": -13.2,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7475,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 9.49,
        "pct_float": 5.78,
        "chg5_pct": 3.65,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "601168.SH",
      "fetch_time": "2026-07-31T11:41:02+0800",
      "name": "西部矿业",
      "pe": 15.1581,
      "pb": 4.0178,
      "ps_ttm": 1.296,
      "pcf_ttm": 6.6478,
      "valuation_percentile": 86.56,
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
      "score_trend": 9.6,
      "score_value": 3.8,
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
          "content": "西部矿业：关于公司控股子公司西部矿业集团财务有限公司的风险持续评估报告",
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
      "valuation_history_from": "20210802",
      "current_price": 36.91,
      "price": 36.91,
      "ma5": 37.11,
      "ma10": 35.34,
      "ma20": 32.57,
      "dist_ma5_pct": -0.5,
      "dist_ma10_pct": 4.4,
      "dist_ma20_pct": 13.3,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7475,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 20.31,
        "pct_float": 2.33,
        "chg5_pct": 3.22,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "000725.SZ",
      "fetch_time": "2026-07-31T11:41:02+0800",
      "name": "京东方A",
      "pe": 34.6781,
      "pb": 1.5396,
      "ps_ttm": 1.0066,
      "pcf_ttm": 4.355,
      "valuation_percentile": 51.41,
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
        "贷款回购指数",
        "华为平台指数",
        "QFII重仓指数",
        "成交额TOP20指数"
      ],
      "score_company": 8.4,
      "score_trend": 7.2,
      "score_value": 5.3,
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
      "valuation_history_from": "20210802",
      "current_price": 5.36,
      "price": 5.36,
      "ma5": 26.24,
      "ma10": 29.65,
      "ma20": 35.08,
      "dist_ma5_pct": -79.6,
      "dist_ma10_pct": -81.9,
      "dist_ma20_pct": -84.7,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.8795,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 118.16,
        "pct_float": 6.23,
        "chg5_pct": -3.43,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002975.SZ",
      "fetch_time": "2026-07-31T11:41:03+0800",
      "name": "博杰股份",
      "pe": 67.6481,
      "pb": 6.6939,
      "ps_ttm": 7.5101,
      "pcf_ttm": 199.814,
      "valuation_percentile": 65.08,
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
      "score_company": 8.0,
      "score_trend": 6.0,
      "score_value": 5.0,
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
          "text": "2026年07月30日大跌 -9.99% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月26日 至今陷入调整，资金有出逃可能。"
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
          "content": "02:03 受AI算力需求爆发影响，MLCC供应趋紧，带动被动元器件行业景气度回升。A股12家MLCC概念公司中，11家上半年实现盈利且同比提升。其中，博杰股份预计上半年归母净利润同比增长642.86%至816.20%；雅创电子预计同比增长439%至561.49%；风华高科预计同比增长61.84%至79.82%。相关公司表示，业绩增长主要得益于AI算力需求旺盛、国产替代深化及高端产品布局。\nAI服务器中MLCC用量显著高于普通服务器，已成为重要成本项。受产能及原材料因素限制，全球MLCC供给释放速度受限。7月以来，被动元器件行业出现新一轮价格调整，国巨已调涨全系列电容产品价格。分销商反馈，目前MLCC渠道价格分化，AI及车规级高端高容产品持续缺货且价格上涨，预计下半年高端高容产品价格将维持上涨趋势。\nTrendForce集邦咨询报告指出，随着新款AI芯片平台量产，高端MLCC下半年缺货风险提升，预计第四季度为关键观察期。村田、三星电机、太阳诱电等龙头企业订单积压压力增加，整体市场订单出货比（BB Ratio）升至1.04，供给短缺风险持续升高。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/01/20～2026/07/10股东户数增加 110%",
          "tags": [
            "股东户数增加"
          ]
        },
        {
          "content": "09:27 7月15日，部分市场焦点股竞价情况如下：\n\n恒尚节能（11天10板）高开1.58%。\n\n医药板块方面，哈药股份（3板）高开5.88%，济民健康（4天2板）低开1.51%。\n\n光通信板块方面，宿迁联盛（6天3板）低开2.12%，东山精密（4天2板）高开0.24%，博杰股份（4天2板）高开3.60%。\n\n其他概念股方面，分红送转概念信通电子（2板）高开4.81%，电解铝板块宏桥控股（2板）高开3.49%，并购重组概念中岩大地（3天2板）低开2.10%，玻璃基板概念三峡新材（3天2板）高开1.09%。",
          "tags": [
            "资讯"
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
      "valuation_history_days": 272,
      "valuation_history_from": "20220207",
      "current_price": 77.04,
      "price": 77.04,
      "ma5": 83.22,
      "ma10": 86.23,
      "ma20": 104.27,
      "dist_ma5_pct": -7.4,
      "dist_ma10_pct": -10.7,
      "dist_ma20_pct": -26.1,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      }
    },
    {
      "code": "688376.SH",
      "fetch_time": "2026-07-31T11:41:03+0800",
      "name": "美埃科技",
      "pe": 77.648,
      "pb": 4.4424,
      "ps_ttm": 4.1582,
      "pcf_ttm": 26.4248,
      "valuation_percentile": 78.59,
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
      "score_trend": 5.6,
      "score_value": 4.1,
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
          "tag": "评级",
          "text": "近90天， 5家 机构给出评级，其中 80% 为“买入”，距目标价的上涨空间为 45% 。"
        },
        {
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 25% ，未来成长较快。"
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
          "content": "11:40 财通证券研报指出，AI训练及推理需求增长带动先进逻辑芯片、HBM及先进封装扩产，全球半导体资本开支进入上行周期。据测算，全球主要半导体企业2026年资本开支合计约1894.8亿美元，同比增长28.8%。基于此，该行预计2026-2028年洁净室建设产值分别为207、252、305亿美元，需求有望进入集中放量阶段。台积电、美光、三星及SK海力士等企业的重点项目在2025-2028年密集推进，将转化为洁净室及机电工程需求。\n财通证券认为，具备核心客户绑定、海外交付经验和高端项目业绩的企业有望受益。相关公司包括：亚翔集成、圣晖集成、柏诚股份、深桑达A、太极实业、华康洁净及美埃科技。风险提示：宏观经济波动、半导体投产不及预期、测算差异风险。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "美埃科技：中信建投证券股份有限公司关于美埃（中国）环境科技股份有限公司股东向特定机构投资者询价转让股份相关资格的核查意见",
          "tags": [
            "重要公告"
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
      "valuation_history_days": 411,
      "valuation_history_from": "20241118",
      "current_price": 65.15,
      "price": 65.15,
      "ma5": 66.83,
      "ma10": 68.55,
      "ma20": 84.94,
      "dist_ma5_pct": -2.5,
      "dist_ma10_pct": -5.0,
      "dist_ma20_pct": -23.3,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 1.93,
        "pct_float": 2.39,
        "chg5_pct": -11.08,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300323.SZ",
      "fetch_time": "2026-07-31T11:41:03+0800",
      "name": "华灿光电",
      "pe": -55.9548,
      "pb": 2.6132,
      "ps_ttm": 2.6383,
      "pcf_ttm": null,
      "valuation_percentile": 54.81,
      "total_shares": 1622998797,
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
          "name": "LED",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "业绩预亏指数",
        "AI穿戴设备指数",
        "Mini LED指数",
        "LED照明指数",
        "新型显示技术指数",
        "广东省国资指数",
        "LED指数",
        "节能照明指数",
        "蓝宝石指数",
        "氧化锌指数"
      ],
      "score_company": 6.8,
      "score_trend": 5.6,
      "score_value": 5.8,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 LED 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年04月29日，业绩超预期引发股价大幅上涨，当日收涨 6.67% 。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 47% ，最新季度归母净利润同比增长 152% ，成长能力很强。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 3.6% ，较受外资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年07月02日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "分红",
          "text": "近5年，从未实施现金分红，为一毛不拔的铁公鸡。"
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
          "content": "07:00 过去十年，京东方被市场视为典型的周期型制造公司。随着产能建设高峰期过去，资本开支和折旧规模下降，公司财务结构改善，经营性净现金流提升。京东方通过分红和注销式回购回报股东，资本模式正从CAPEX驱动转向FCF驱动，市场对其定价逻辑或将从周期PE估值转向FCF定价。\n在LCD领域，全球格局趋于集中，周期波动减弱。在OLED领域，京东方量产了中国首条8.6代AMOLED产线，并实现了多项技术突破，在显示领域具备标准制定权。显示器件业务作为底层资产，提供了高现金流与稳定性。\n京东方与康宁在玻璃基封装载板、可折叠玻璃、钙钛矿玻璃基板及光互连领域达成合作。公司依托显示技术、玻璃基加工和集成制造能力，布局玻璃基封装载板、光互连及钙钛矿三条业务线，旨在解决AI算力基础设施的物理瓶颈。\n京东方董事长陈炎顺提出“第N曲线”理论，将显示产业底蕴延伸至AI应用、光电互联及高端制造。公司将玻璃基加工作为核心载体，通过稳健的显示业务基本盘与AI基建新赛道，寻求未来增长。\n此部分为滚动资讯播报，无实质性新增内容。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "02:45 7月以来，共有375家A股上市公司获机构调研，其中新易盛、京东方A、华灿光电、华勤技术等22家公司获50家以上机构调研。新易盛获417家机构调研居首，公司称二季度业绩预告与年初预期基本吻合。京东方A获243家机构调研，公司表示未来折旧金额及资本开支预计将逐渐下降。在已发布半年度业绩相关公告的调研公司中，超七成实现业绩报喜，恒逸石化、三维通信、凯尔达预计净利润同比增长超1000%。分行业看，获调研且业绩预喜的公司中，电子行业数量居首，电力设备、基础化工及有色金属行业紧随其后。\n研究机构Omdia数据显示，2026年中国半导体市场规模预测值上调。在上述375家获调研公司中，67家获外资机构调研，其中电子行业公司有19家。广合科技、沪电股份、华勤技术等电子行业公司获外资机构调研较多。调研内容显示，外资机构关注相关公司的全球化布局，广合科技泰国工厂正推进产能爬坡，沪电股份泰国基地已进入规模化运营阶段。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "华灿光电：关于使用部分闲置募集资金进行现金管理的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 4129071094.98,
      "revenue_yoy": 0.398441,
      "operating_profit": -247200388.81,
      "operating_profit_yoy": 0.452304,
      "net_profit": -195656259.36,
      "net_profit_yoy": 0.45584,
      "gross_profit": 253223465.16,
      "gross_profit_yoy": 162.023979,
      "cogs": 3875847629.82,
      "gross_margin": 6.13,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 10.78,
      "price": 10.78,
      "ma5": 11.17,
      "ma10": 11.45,
      "ma20": 14.34,
      "dist_ma5_pct": -3.5,
      "dist_ma10_pct": -5.8,
      "dist_ma20_pct": -24.8,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 13.51,
        "pct_float": 11.39,
        "chg5_pct": -3.31,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002245.SZ",
      "fetch_time": "2026-07-31T11:41:03+0800",
      "name": "蔚蓝锂芯",
      "pe": 35.9536,
      "pb": 3.5613,
      "ps_ttm": 3.2198,
      "pcf_ttm": 18.9616,
      "valuation_percentile": 62.85,
      "total_shares": 1707639594,
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
        "专精特新小巨人主题指数",
        "股权激励指数",
        "锂电池指数",
        "养老金指数",
        "固态电池指数",
        "钠离子电池指数",
        "LED照明指数",
        "金改指数",
        "三元锂电池指数",
        "节能照明指数",
        "物流电商平台指数",
        "金融改革指数",
        "舟山新区指数",
        "合同能源管理指数",
        "长三角自贸区"
      ],
      "score_company": 8.5,
      "score_trend": 6.4,
      "score_value": 5.4,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月14日，业绩超预期引发股价大幅上涨，当日收涨 10.0% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 64% ，利润成长性强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 2.1亿元 ，较上期增长 742% ，占2025年营收 2.5% ，在手订单充足。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 6.4% ，很受外资机构青睐；公募基金持股 7.5% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月07日大跌 -7.06% ，且成交额为近20日均值的 1.51倍 ，抛压很重。"
        },
        {
          "tag": "偿债",
          "text": "现金短债比为 0.31 ，货币资金对短期债务的保障较弱。"
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
          "content": "15:00 今天大涨的原因可能是公司披露BBU备电业务在产品开发、客户拓展、产能准备和订单交付上均有序推进，提升业绩和成长预期。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "09:32 锂电池板块短线走低，鹏辉能源跌超10%，蔚蓝锂芯、德福科技、铜冠铜箔、诺德股份等跟跌。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价盘中上涨 8.69% ，股价收盘涨幅 10.01%",
          "tags": [
            "股价上涨"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 5814429411.23,
      "revenue_yoy": 0.201713,
      "operating_profit": 653430544.85,
      "operating_profit_yoy": 0.72211,
      "net_profit": 567618109.56,
      "net_profit_yoy": 0.728916,
      "gross_profit": 1151783114.18,
      "gross_profit_yoy": 0.445764,
      "cogs": 4662646297.05,
      "gross_margin": 19.81,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210802",
      "current_price": 16.05,
      "price": 16.05,
      "ma5": 16.49,
      "ma10": 16.74,
      "ma20": 18.63,
      "dist_ma5_pct": -2.7,
      "dist_ma10_pct": -4.1,
      "dist_ma20_pct": -13.8,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.45,
        "pct_float": 2.66,
        "chg5_pct": -8.83,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688392.SH",
      "fetch_time": "2026-07-31T11:41:03+0800",
      "name": "骄成超声",
      "pe": 104.9377,
      "pb": 8.252,
      "ps_ttm": 18.3521,
      "pcf_ttm": 119.2495,
      "valuation_percentile": 63.16,
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
      "score_company": 7.3,
      "score_trend": 6.2,
      "score_value": 5.1,
      "highlights": [
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
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
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
          "content": "骄成超声：容诚会计师事务所（特殊普通合伙）关于上海骄成超声波技术股份有限公司向特定对象发行股票申请文件的审核问询函的回复",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "骄成超声：关于上海骄成超声波技术股份有限公司向特定对象发行股票申请文件的审核问询函的回复",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "骄成超声：关于向特定对象发行股票申请文件审核问询函回复的提示性公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "骄成超声：关于更换持续督导保荐代表人的公告",
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
      "valuation_history_days": 441,
      "valuation_history_from": "20240927",
      "current_price": 134.02,
      "price": 134.02,
      "ma5": 147.32,
      "ma10": 153.52,
      "ma20": 183.08,
      "dist_ma5_pct": -9.0,
      "dist_ma10_pct": -12.7,
      "dist_ma20_pct": -26.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.46,
        "pct_float": 3.21,
        "chg5_pct": -9.09,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300373.SZ",
      "fetch_time": "2026-07-31T11:41:03+0800",
      "name": "扬杰科技",
      "pe": 34.0663,
      "pb": 4.8443,
      "ps_ttm": 6.0786,
      "pcf_ttm": 28.8901,
      "valuation_percentile": 47.13,
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
      "score_trend": 7.0,
      "score_value": 5.9,
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
      "valuation_history_from": "20210802",
      "current_price": 87.6,
      "price": 87.6,
      "ma5": 89.87,
      "ma10": 92.58,
      "ma20": 110.88,
      "dist_ma5_pct": -2.5,
      "dist_ma10_pct": -5.4,
      "dist_ma20_pct": -21.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 15.3,
        "pct_float": 3.44,
        "chg5_pct": -1.15,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688401.SH",
      "fetch_time": "2026-07-31T11:41:04+0800",
      "name": "路维光电",
      "pe": 47.4072,
      "pb": 4.9649,
      "ps_ttm": 10.518,
      "pcf_ttm": 43.5671,
      "valuation_percentile": 66.1,
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
      "score_trend": 6.9,
      "score_value": 5.4,
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
      "valuation_history_days": 469,
      "valuation_history_from": "20240819",
      "current_price": 62.68,
      "price": 62.68,
      "ma5": 65.27,
      "ma10": 65.71,
      "ma20": 77.2,
      "dist_ma5_pct": -4.0,
      "dist_ma10_pct": -4.6,
      "dist_ma20_pct": -18.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.41,
        "pct_float": 4.82,
        "chg5_pct": -10.39,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688256.SH",
      "fetch_time": "2026-07-31T11:41:04+0800",
      "name": "寒武纪",
      "pe": 260.8498,
      "pb": 57.9077,
      "ps_ttm": 85.6929,
      "pcf_ttm": 408.5027,
      "valuation_percentile": 52.08,
      "total_shares": 628292969,
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
        "双循环指数",
        "双创100指数",
        "茅指数",
        "人工智能+指数",
        "消费电子产业指数",
        "半导体产业指数",
        "成交额TOP20指数",
        "新基建指数",
        "5G指数",
        "股权激励指数",
        "成交额TOP10指数"
      ],
      "score_company": 8.5,
      "score_trend": 7.1,
      "score_value": 6.4,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 数字芯片设计 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年04月30日，业绩超预期引发股价跳空高开，当日收涨 20.0% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 185% ，利润成长性强。"
        },
        {
          "tag": "订单",
          "text": "合同负债 4.0亿元 ，较上期增长 64674% ，占2025年营收 6.1% ，在手订单充足。"
        },
        {
          "tag": "评级",
          "text": "近90天， 6家 机构给出评级，其中 100% 为“买入”，距目标价的上涨空间为 47% 。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 50% ，未来成长很快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.5% ，较受外资机构青睐；公募基金持股 13% ，很受内资机构青睐。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/08发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-08"
        },
        {
          "content": "11:10 创业板人工智能ETF华夏（159381）、科创创业人工智能ETF景顺（159142）、科创人工智能ETF广发（588760）涨超8%。AI相关个股持续走强，昆仑万维20cm涨停，金山办公涨超15%，澜起科技、寒武纪、新易盛等涨超6%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "09:52 7月28日晚，寒武纪发布《2026年限制性股票激励计划（草案）》，拟授予500万股限制性股票，占总股本0.80%，授予价格为750元/股。方案包含首次授予400万股及预留100万股。首次授予对象为945人，其中6名董事、高管及核心技术人员获授36万股，939名其他激励对象获授364万股。按7月29日收盘价1146.9元/股计算，首次授予部分人均账面价差约167.9万元。该计划尚需股东大会审议通过。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/29发布预案公告，本计划拟向激励对象授予500万股 ，约占总股本的 0.80%，授予价格为 750元/股 。",
          "tags": [
            "激励计划"
          ]
        },
        {
          "content": "寒武纪：关于变更注册资本及修订《公司章程》并办理工商变更登记的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 4607424363.66,
      "revenue_yoy": 23.863793,
      "operating_profit": 1605699534.07,
      "operating_profit_yoy": 3.205898,
      "net_profit": 1604038056.13,
      "net_profit_yoy": 3.201892,
      "gross_profit": 2547577811.67,
      "gross_profit_yoy": 23.892441,
      "cogs": 2059846551.99,
      "gross_margin": 55.29,
      "pe_forward": null,
      "valuation_history_days": 326,
      "valuation_history_from": "20220721",
      "current_price": 1146.9,
      "price": 1146.9,
      "ma5": 1197.98,
      "ma10": 1232.87,
      "ma20": 1340.38,
      "dist_ma5_pct": -4.3,
      "dist_ma10_pct": -7.0,
      "dist_ma20_pct": -14.4,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 171.64,
        "pct_float": 2.62,
        "chg5_pct": -8.44,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688331.SH",
      "fetch_time": "2026-07-31T11:41:05+0800",
      "name": "荣昌生物",
      "pe": 49.9571,
      "pb": 16.4274,
      "ps_ttm": 19.0857,
      "pcf_ttm": 255.4966,
      "valuation_percentile": 42.93,
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
      "score_trend": 6.2,
      "score_value": 6.9,
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
          "tag": "评级",
          "text": "近90天， 5家 机构给出评级，其中 80% 为“买入”，距目标价的上涨空间为 39% 。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 2.7% ，较受外资机构青睐；公募基金持股 28% ，很受内资机构青睐。"
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
          "content": "17:42 荣昌生物公告，公司此前审议通过回购方案，拟以2500万元~5000万元回购公司股份，回购价格不超过149元/股，用于员工持股计划或股权激励。2026年7月30日，公司首次通过集中竞价交易方式回购股份13000股，占总股本比例0.0023%，成交最高价109.99元/股，最低价109元/股，支付总金额142.82万元（不含交易费用）。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "17:25 7月28日，国家药监局公示信息显示，荣昌生物伊立芙普α眼内注射液（RC28-E）的注册申请已列入送达公示清单。荣昌生物回应称，根据国家药监局审评建议，公司决定主动撤回本次药品注册申请，后续将补充临床病例数研究后再次提交。目前，RC28-E的对外授权合作正常推进。\nRC28-E的Ⅲ期临床研究已达到预设主要终点，证实了非劣效性及良好的安全耐受性。此次补充临床病例数研究，旨在增加安全性暴露人群数量，无需重做Ⅲ期临床试验。此前，凯因科技、智飞生物、悦康药业等企业亦曾因补充临床研究数据而主动撤回上市申请。\nRC28-E为全球首创VEGF/FGF双靶点眼科药物。专家指出，该药物通过双通路治疗糖尿病黄斑水肿，机制独特，安全性特征与现有抗VEGF药物相似。目前全球范围内尚无同靶点竞品进入临床试验阶段。",
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
          "content": "截至2026/07/31，公司累计回购 1.30万股 ，占总股本比例为 0.00% ，最高成交价为 110元/股 ，最低成交价为 109元/股 ，耗资 143万元  （进行中）",
          "tags": [
            "公司回购流通股"
          ],
          "date": "2027-07-20"
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
      "valuation_history_days": 283,
      "valuation_history_from": "20240401",
      "current_price": 118.28,
      "price": 118.28,
      "ma5": 120.99,
      "ma10": 123.59,
      "ma20": 130.32,
      "dist_ma5_pct": -2.2,
      "dist_ma10_pct": -4.3,
      "dist_ma20_pct": -9.2,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.34,
        "pct_float": 2.36,
        "chg5_pct": -2.52,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "000977.SZ",
      "fetch_time": "2026-07-31T11:41:05+0800",
      "name": "浪潮信息",
      "pe": 41.7589,
      "pb": 4.7967,
      "ps_ttm": 0.6956,
      "pcf_ttm": null,
      "valuation_percentile": 62.64,
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
      "score_trend": 7.4,
      "score_value": 5.0,
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
          "text": "近90天， 14家 机构给出评级，其中 71% 为“买入”，距目标价的上涨空间为 33% 。"
        },
        {
          "tag": "预测",
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 2.5% ，较受外资机构青睐；公募基金持股 4.6% ，较受内资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近6月，股价涨幅超过A股市场 90% 的股票，走势较强。"
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
          "content": "14:25 企查查APP显示，近日，合肥浩澜潮智创业投资合伙企业（有限合伙）成立，经营范围包含：创业投资（限投资未上市企业）；以自有资金从事投资活动。企查查股权穿透显示，该企业由浪潮信息等共同出资。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "17:35 国金证券观点认为，Q3科技产业主要驱动力在于英伟达Vera Rubin与谷歌TPU进入量产阶段，算力紧缺仍是核心矛盾。英伟达Vera Rubin NVL72正在全球加速部署，已在CoreWeave、Google Cloud、Microsoft Azure及Oracle云基础设施运行。TPU方面，Alphabet确认TPU系统销售已于Q2启动交付，预计2026年收入加速，2027年确认多数收入。供给端，HBM4三家供应商已认证量产，SK海力士称需求超供给；Alphabet上调2026年资本开支指引至1950-2050亿美元。\nAlphabet Q2财报显示，收入1198亿美元，同比增长24%；Google Cloud收入248亿美元，同比增长82%。资本开支449亿美元，其中六成投向服务器。TPU系统销售模式打开云服务外增长空间。产业链方面，机柜、PCB、光互联是主线，工业富联Rubin机柜Q3量产，Spectrum-6确立CPO为标配。电容方面，三星电机MLCC涨价信号明确，AI服务器高容值产品现货价格涨幅显著。\n国金证券列示相关标的：超核心供应商包括工业富联、胜宏科技；海外算力链包括中际旭创、新易盛、东山精密、江海股份、中钨高新、蓝思科技、东阳光、光智科技、先导基电、火炬电子、三环集团、欧科亿、天孚通信、鼎泰高科、领益智造、兆易创新、鹏鼎控股、唯科科技、海川智能、天岳先进、大普微、源杰科技、麦格米特、景旺电子、英维克、京东方等；国内算力链包括寒武纪、海光信息、长鑫科技、中芯国际、华虹半导体、中科曙光、浪潮信息、胜蓝股份、华勤技术、国科微、中国长城、晶科科技、罗曼股份、盈峰环境、芯原股份、亿田智能、豫能控股、星环科技、鸿日达、盛视科技、神州数码、润泽科技、大位科技、润建股份、奥飞数据、瑞晟智能、科华数据、潍柴重机、欧陆通、杰创智能、奥尼电子；大模型与云厂商包括智谱、MiniMax、阿里巴巴、腾讯控股、金山云、百度集团、优刻得、首都在线、网宿科技、云赛智联、青云科技等。风险提示：Rubin量产爬坡不及预期、TPU收入确认节奏风险、HBM与高端元器件供给瓶颈风险。\nVera Rubin平台由七颗芯片与五类机架托盘组成，英伟达官方确认其系统协同设计。Vera Rubin NVL72机柜已在CoreWeave、Google Cloud、Microsoft Azure与Oracle云基础设施运行，CoreWeave实测显示其每兆瓦token吞吐量达Grace Blackwell NVL72的10倍。\nRubin GPU采用双芯粒设计，搭载288GB HBM4，带宽22TB/s。第三代Transformer引擎支持NVFP4精度，算力较Blackwell大幅提升。Vera Rubin NVL144机柜由72颗Rubin GPU与36颗Vera CPU构成。HBM4方面，三星电子、SK海力士、美光三家供应商已通过认证并量产，预计2026年Q3全面规模化量产。\n英伟达定义G3.5存储层以优化KV Cache，CMX平台由BlueField-4 DPU管理，单柜管理约9600TB闪存。该平台旨在提升token生成速度与能效，使存储系统成为AI基础设施的关键环节。\nVera CPU专为数据搬运与Agent推理设计，Groq 3 LPX定位低时延推理加速器。Spectrum-6以太网交换机采用CPO技术，英伟达确认其为首款进入量产阶段的此类产品，相比可插拔收发器功耗降低5倍。\nAlphabet Q2财报显示，Google Cloud积压订单达5140亿美元。管理层上调2026年资本开支指引，并预告2027年将显著增长。TPU系统销售已于Q2启动交付，预计2027年进入收入放量期。\n机柜环节，工业富联Rubin整机柜Q3启动量产。PCB环节，Vera Rubin NVL144采用中央PCB中板，价值量较GB代际提升。光模块环节，ConnectX-9提升端口带宽至1.6Tb/s，CPO随Spectrum-6确立为官方标配。\n液冷与供电方面，Vera Rubin NVL144采用100%液冷设计，800VDC高压直流确立为参考架构。电容方面，三星电机已与大型科技企业签署AI服务器MLCC长期供货合同，高端高容MLCC供需紧张预计持续至2027年上半年。\n相关标的与风险提示同前文所述。报告由国金证券发布，分析师为刘高畅、郑元昊、孙恺祈。",
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
      "valuation_history_from": "20210802",
      "current_price": 69.08,
      "price": 69.08,
      "ma5": 450.09,
      "ma10": 510.74,
      "ma20": 524.99,
      "dist_ma5_pct": -84.7,
      "dist_ma10_pct": -86.5,
      "dist_ma20_pct": -86.8,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.8795,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 41.61,
        "pct_float": 4.11,
        "chg5_pct": -12.31,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "603162.SH",
      "fetch_time": "2026-07-31T11:41:05+0800",
      "name": "海通发展",
      "pe": 16.2798,
      "pb": 3.0122,
      "ps_ttm": 2.4009,
      "pcf_ttm": 8.9418,
      "valuation_percentile": 37.63,
      "total_shares": 1375615155,
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
        "万得预增指数",
        "航运精选指数",
        "港口精选指数",
        "两岸融合指数"
      ],
      "score_company": 8.2,
      "score_trend": 8.2,
      "score_value": 7.4,
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
          "text": "近6月，股价涨幅超过A股市场 95% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月19日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "解禁",
          "text": "2026年09月29日，解禁 9.33亿股 ，占总股本 68% ，若股东减持，股价或受影响。"
        }
      ],
      "events": [
        {
          "content": "2026/09/29解禁9.33亿股，占总股本67.82%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-29"
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
        },
        {
          "content": "15:00 今天大涨的原因可能是海通发展半年报显示主营干散货运输收入大增（营业收入34.71亿元、归母净利润同比增长502.60%），反映运价回升、运力利用和经营效率显著提升，盈利能力大幅改善。",
          "tags": [
            "快讯",
            "大涨原因"
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
      "valuation_history_days": 322,
      "valuation_history_from": "20250331",
      "current_price": 11.04,
      "price": 11.04,
      "ma5": 11.03,
      "ma10": 10.77,
      "ma20": 10.32,
      "dist_ma5_pct": 0.1,
      "dist_ma10_pct": 2.5,
      "dist_ma20_pct": 6.9,
      "iv_proxy": {
        "primary_name": "500ETF",
        "iv_rank": 0.9451,
        "sizing": "tight"
      }
    },
    {
      "code": "603156.SH",
      "fetch_time": "2026-07-31T11:41:05+0800",
      "name": "养元饮品",
      "pe": 34.5439,
      "pb": 5.6924,
      "ps_ttm": 8.1615,
      "pcf_ttm": 27.3277,
      "valuation_percentile": 97.46,
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
      "score_trend": 7.6,
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
      "valuation_history_from": "20210802",
      "current_price": 37.35,
      "price": 37.35,
      "ma5": 36.77,
      "ma10": 36.26,
      "ma20": 40.87,
      "dist_ma5_pct": 1.6,
      "dist_ma10_pct": 3.0,
      "dist_ma20_pct": -8.6,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7475,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 4.8,
        "pct_float": 1.02,
        "chg5_pct": 9.96,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "603259.SH",
      "fetch_time": "2026-07-31T11:41:05+0800",
      "name": "药明康德",
      "pe": 18.9171,
      "pb": 4.7894,
      "ps_ttm": 7.8944,
      "pcf_ttm": 21.6323,
      "valuation_percentile": 34.9,
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
      "score_trend": 8.8,
      "score_value": 6.8,
      "highlights": [
        {
          "tag": "A/H",
          "text": "A/H溢价率仅为 -8% ，从流动性而言，A股吸引力较高。"
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
          "text": "近3月，股价涨幅超过A股市场 98% 的股票，走势很强。"
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
          "content": "02:11 江苏汉邦科技股份有限公司（证券简称：汉邦科技，代码：688755）发布回购报告书。公司拟以集中竞价交易方式回购股份，回购金额不低于3,000万元且不超过5,000万元，回购价格不超过39.41元/股，期限为董事会审议通过之日起3个月内。回购资金来源为自有资金或自筹资金（含专项贷款，已取得兴业银行淮安分行贷款承诺函）。回购用途为维护公司价值及股东权益。公司持股5%以上股东上海药明康德新药开发有限公司、杭州清科致盛投资合伙企业及其一致行动人存在减持计划。\n本次回购方案已于2026年7月23日经公司第二届董事会第五次会议审议通过。截至2026年7月22日，公司股票收盘价为22.15元/股，符合相关回购规定。回购期限内，若触及资金上限、董事会决议终止或资金下限等条件，回购期限可提前届满。\n公司已取得兴业银行淮安分行出具的《贷款承诺函》，承诺贷款金额不超过4,500万元，专项用于回购股票。具体回购数量及比例以实施结果为准，若遇除权除息事项将进行相应调整。\n截至2026年3月31日，公司总资产194,447.87万元，归属于上市公司股东的净资产126,593.90万元。本次回购资金上限占上述财务数据比例较小，预计不会对公司经营、财务及未来发展产生重大影响。公司董事、高管、控股股东及实控人在回购决议前6个月内无买卖公司股份行为，且回购期间暂无增减持计划。\n本次回购股份拟在披露回购结果暨股份变动公告12个月后采用集中竞价方式出售；若3年内未实施，将依法注销。董事会授权管理层办理回购相关事宜，包括设立专用账户、择机回购及调整方案等。\n公司已在中国证券登记结算有限责任公司上海分公司开立回购专用证券账户（号码：B888681859）。公司提示，回购方案存在价格超出上限、重大事项导致终止、监管政策变化等不确定性风险。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "17:07 据香港交易所披露，摩根大通（JPMorgan）对无锡药明康德新药开发股份有限公司 - H股的多头持仓比例于2026年7月23日从11.26%降至10.48%。",
          "tags": [
            "快讯"
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
      "valuation_history_from": "20210802",
      "current_price": 126.5,
      "price": 126.5,
      "ma5": 125.33,
      "ma10": 124.81,
      "ma20": 124.65,
      "dist_ma5_pct": 0.9,
      "dist_ma10_pct": 1.4,
      "dist_ma20_pct": 1.5,
      "iv_proxy": {
        "primary_name": "50ETF",
        "iv_rank": 0.6353,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 50.22,
        "pct_float": 1.62,
        "chg5_pct": -5.42,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "603296.SH",
      "fetch_time": "2026-07-31T11:41:05+0800",
      "name": "华勤技术",
      "pe": 29.1388,
      "pb": 4.152,
      "ps_ttm": 0.7027,
      "pcf_ttm": 70.6546,
      "valuation_percentile": 84.83,
      "total_shares": 1516201463,
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
        "科技龙头指数",
        "出海贸易指数",
        "股权激励指数",
        "AI手机指数",
        "浦东新区指数",
        "AIPC指数",
        "上海自贸区指数",
        "电子制造精选指数",
        "超节点指数"
      ],
      "score_company": 7.8,
      "score_trend": 8.9,
      "score_value": 4.1,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 83% ，利润成长性强。"
        },
        {
          "tag": "评级",
          "text": "近90天， 13家 机构给出评级，其中 85% 为“买入”，距目标价的上涨空间为 38% 。"
        },
        {
          "tag": "预测",
          "text": " 7家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 4.3% ，很受外资机构青睐。"
        },
        {
          "tag": "强势",
          "text": "近6月，股价涨幅超过A股市场 96% 的股票，走势较强。"
        },
        {
          "tag": "增持",
          "text": "近1月，控股股东和管理层累计实际增持 54万股 ，占总股本比例 0.04% ，金额合计 4029万元 。"
        },
        {
          "tag": "回购",
          "text": "近1月，公司累计回购 26万股 ，占总股本比例 0.02% ，金额合计 2007万元 。"
        }
      ],
      "risks": [
        {
          "tag": "毛利",
          "text": "毛利率为 8.0% ，行业处于衰退期，或企业缺乏竞争力。"
        }
      ],
      "events": [
        {
          "content": "2027/02/12解禁6.16亿股，占总股本40.65%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2027-02-12"
        },
        {
          "content": "预计2026/08/26发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-26"
        },
        {
          "content": "华勤技术：华勤技术H股公告-翌日披露报表",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "16:59 华勤技术公告，公司此前审议通过回购方案，拟以不低于1.5亿元且不超过2亿元的自有资金回购A股股份，用于股权激励或员工持股计划，回购价格不超过100元/股。2026年7月30日，公司首次通过集中竞价方式回购股份25.5万股，占总股本0.0168%，成交最高价80元/股，最低价76.75元/股，支付总金额2007.32万元（不含交易费用）。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "华勤技术：北京市中伦律师事务所关于华勤技术股份有限公司实际控制人增持股份的专项核查意见",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 128881887357.29,
      "revenue_yoy": 0.695593,
      "operating_profit": 3448039628.77,
      "operating_profit_yoy": 0.627592,
      "net_profit": 3115029696.15,
      "net_profit_yoy": 0.531887,
      "gross_profit": 10109886674.11,
      "gross_profit_yoy": 0.367849,
      "cogs": 118772000683.18,
      "gross_margin": 7.84,
      "pe_forward": null,
      "valuation_history_days": 235,
      "valuation_history_from": "20250808",
      "current_price": 83.65,
      "price": 83.65,
      "ma5": 86.36,
      "ma10": 82.29,
      "ma20": 78.62,
      "dist_ma5_pct": -3.1,
      "dist_ma10_pct": 1.7,
      "dist_ma20_pct": 6.4,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.7475,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 10.53,
        "pct_float": 1.67,
        "chg5_pct": -7.79,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688981.SH",
      "fetch_time": "2026-07-31T11:41:06+0800",
      "name": "中芯国际",
      "pe": 216.711,
      "pb": 5.7426,
      "ps_ttm": 15.9301,
      "pcf_ttm": 41.4426,
      "valuation_percentile": 81.7,
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
      "score_trend": 7.7,
      "score_value": 4.0,
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
          "text": "近90天， 10家 机构给出评级，其中 70% 为“买入”，距目标价的上涨空间为 39% 。"
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
      "valuation_history_days": 325,
      "valuation_history_from": "20220718",
      "current_price": 130.9,
      "price": 130.9,
      "ma5": 140.04,
      "ma10": 145.15,
      "ma20": 150.3,
      "dist_ma5_pct": -6.5,
      "dist_ma10_pct": -9.8,
      "dist_ma20_pct": -12.9,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 108.5,
        "pct_float": 4.41,
        "chg5_pct": -5.75,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002138.SZ",
      "fetch_time": "2026-07-31T11:41:06+0800",
      "name": "顺络电子",
      "pe": 35.4788,
      "pb": 6.0981,
      "ps_ttm": 5.0002,
      "pcf_ttm": 23.8318,
      "valuation_percentile": 59.7,
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
        "贷款回购指数",
        "华为平台指数",
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
      "score_trend": 5.1,
      "score_value": 5.2,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月31日，业绩超预期引发股价大幅上涨。"
        },
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 18% ，收入成长性较强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 13% ，投入资本回报率为 11% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.9% ，未来产能扩张后，营收有望进一步增长。"
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
          "text": "现金短债比为 0.20 ，货币资金对短期债务的保障很弱。"
        }
      ],
      "events": [
        {
          "content": "公司发布2026半年报报告，股价开盘上涨 7.23%",
          "tags": [
            "股价上涨"
          ]
        },
        {
          "content": "18:35 顺络电子公告，2026年上半年营业收入38.59亿元，同比增长19.67%。归属于上市公司股东的净利润4.47亿元，同比下降7.98%。归属于上市公司股东的扣除非经常性损益的净利润4.34亿元，同比下降6.21%。公司计划不派发现金红利，不送红股，不以公积金转增股本。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "12:00 7月21日，A股PCB概念股集体反弹。截至半日收盘，波长光电、金禄电子、戈碧迦、中富电路、埃科光电、路维光电、昊志机电、国际复材、锐科激光、欧科亿、鼎泰高科、东威科技、斯迪克涨幅居前；顺络电子、宏和科技、江南新材、大族激光、大为股份、木林森涨停。中信建投研报指出，感光干膜是PCB电路图形转印的核心耗材，受益于AI服务器、数据中心及高速网络设备驱动，行业进入结构性增长周期。预计2026年至2030年感光干膜市场空间将持续增长，年均复合增长率约为9.4%。目前全球感光干膜市场由中国台湾及日本企业主导，随着头部PCB企业批量采用国产产品，内资感光干膜市场份额有望提升。",
          "tags": [
            "资讯"
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
      "valuation_history_from": "20210802",
      "current_price": 43.15,
      "price": 43.15,
      "ma5": 43.11,
      "ma10": 42.66,
      "ma20": 50.37,
      "dist_ma5_pct": 0.1,
      "dist_ma10_pct": 1.2,
      "dist_ma20_pct": -14.3,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 13.36,
        "pct_float": 4.35,
        "chg5_pct": 0.49,
        "net5_repay_days": 3,
        "signal": "neutral"
      }
    },
    {
      "code": "300811.SZ",
      "fetch_time": "2026-07-31T11:41:07+0800",
      "name": "铂科新材",
      "pe": 56.5267,
      "pb": 7.9443,
      "ps_ttm": 12.8215,
      "pcf_ttm": 75.5084,
      "valuation_percentile": 62.34,
      "total_shares": 406614701,
      "industries": [
        {
          "name": "有色金属",
          "level": 1
        },
        {
          "name": "金属新材料",
          "level": 2
        },
        {
          "name": "磁性材料",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "华为平台指数",
        "QFII重仓指数",
        "英伟达产业链指数",
        "中小创蓝筹指数",
        "ASIC芯片指数",
        "稀土永磁指数",
        "金属非金属新材料精选指数"
      ],
      "score_company": 7.8,
      "score_trend": 5.2,
      "score_value": 5.8,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 磁性材料 行业龙头企业。"
        },
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 18% ，收入成长性较强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 14% ，投入资本回报率为 13% ，盈利能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 6.9% ，未来产能扩张后，营收有望进一步增长。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月22日大跌 -5.84% ，且成交额为近20日均值的 1.81倍 ，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月22日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比为 66% ，销售收入现金含量很低。"
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
          "content": "15:28 铂科新材（300811）应收账款规模持续走高，影响现金流与盈利弹性。截至2025年年末，公司贸易应收款达10.39亿元，占全年营收比重为57.7%。2023年至2026年前3个月，公司贸易应收款项及应收票据亏损准备累计近1.56亿元。此外，公司存在安全生产合规隐患，2025年4月惠州生产基地曾发生有限空间窒息事故，被当地应急管理局处以73万元行政处罚。公司在多地设有高温、密闭等高危生产工序，面临生产管控风险。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "16:12 铂科新材主营合金软磁粉芯、AI芯片电感及定制合金软磁粉末，是全产业链垂直整合磁材企业。公司长期合作华为、比亚迪、阳光电源、ABB、台达、MPS、伟创力等海内外龙头，产品应用于AI算力、新能源车、光伏储能及工业电源等领域。公司销售以直销为主，2023年至2026年一季度，前五大客户营收占比在44.1%至47.5%之间，存在客户集中度较高的经营风险。公司由杜江华、周后强、阮佳林、罗志敏四人共同创立，四人合计持股超46%。2025年公司实施统一董事薪酬制度，执行董事薪酬标准调整，创始人收益主要来自股权分红与激励。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1300792094.49,
      "revenue_yoy": 0.060294,
      "operating_profit": 356383220.67,
      "operating_profit_yoy": 0.050781,
      "net_profit": 296811221.06,
      "net_profit_yoy": 0.041402,
      "gross_profit": 527162481.58,
      "gross_profit_yoy": 0.05746,
      "cogs": 773629612.91,
      "gross_margin": 40.53,
      "pe_forward": null,
      "valuation_history_days": 277,
      "valuation_history_from": "20211230",
      "current_price": 59.96,
      "price": 59.96,
      "ma5": 62.54,
      "ma10": 64.25,
      "ma20": 75.58,
      "dist_ma5_pct": -4.1,
      "dist_ma10_pct": -6.7,
      "dist_ma20_pct": -20.7,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.67,
        "pct_float": 5.8,
        "chg5_pct": -4.47,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301345.SZ",
      "fetch_time": "2026-07-31T11:41:07+0800",
      "name": "涛涛车业",
      "pe": 29.8013,
      "pb": 7.472,
      "ps_ttm": 6.1938,
      "pcf_ttm": 34.2601,
      "valuation_percentile": 75.22,
      "total_shares": 109049071,
      "industries": [
        {
          "name": "汽车",
          "level": 1
        },
        {
          "name": "摩托车及其他",
          "level": 2
        },
        {
          "name": "摩托车",
          "level": 3
        }
      ],
      "concepts": [
        "出海贸易指数",
        "股权激励指数",
        "设备更新指数",
        "万得预增指数"
      ],
      "score_company": 9.5,
      "score_trend": 7.1,
      "score_value": 4.8,
      "highlights": [
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 36% ，最新季度归母净利润同比增长 42% ，成长能力很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 22% ，投入资本回报率为 19% ，盈利能力很强。"
        },
        {
          "tag": "分红",
          "text": "近3年，股息收益率均值达到 2.6% ，现金分红较高。"
        },
        {
          "tag": "评级",
          "text": "近90天， 7家 机构给出评级，其中 57% 为“买入”，距目标价的上涨空间为 43% 。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 25% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 14% ，很受外资机构青睐；公募基金持股 10% ，很受内资机构青睐；2026年02月13日至2026年07月20日期间，股东户数减少 25% ，大资金买入。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 92% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "解禁",
          "text": "2026年09月21日，解禁 4512.80万股 ，占总股本 41% ，若股东减持，股价或受影响。"
        }
      ],
      "events": [
        {
          "content": "2026/09/21解禁4512.80万股，占总股本41.38%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-21"
        },
        {
          "content": "预计2026/08/24发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-24"
        },
        {
          "content": "06:23 截至7月22日，申万汽车行业89家A股上市车企披露2026年中期业绩预告。其中，30家企业业绩偏正面，占比34%。从盈利规模看，长城汽车、长安汽车、宁波华翔等上半年预计净利润居前；广汽集团、北汽蓝谷、赛力斯等预计亏损超15亿元。宁波华翔、立中集团、涛涛车业等预计净利润超过5亿元。其中，宁波华翔预计上半年归母净利润6.1亿元至6.9亿元，同比扭亏为盈。此外，一汽解放、西上海、青岛双星、新朋股份、宁波华翔、顺景科技等6家公司预计上半年净利润同比增长超过200%。一汽解放预计上半年归母净利润2.70亿元至3.20亿元，同比增长1273.64%至1528.02%。\n广汽集团预计上半年归母净亏损40.6亿元至45.7亿元，亏损规模同比扩大。公司表示，受国内市场竞争加剧、自主品牌销售投入加大、产品结构变动、原材料成本上涨及合资品牌经营承压等因素影响，利润同比下降。北汽蓝谷预计归母净亏损17.7亿元至19.7亿元，受益于整车销量提升及降本措施，实现减亏。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/09/21解禁4512.80万股，占总股本41.38%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-09-21"
        }
      ],
      "report_period": "20250930",
      "revenue": 2772810512.76,
      "revenue_yoy": 0.248897,
      "operating_profit": 718420856.65,
      "operating_profit_yoy": 0.860164,
      "net_profit": 606541820.03,
      "net_profit_yoy": 1.012653,
      "gross_profit": 1173162973.8,
      "gross_profit_yoy": 0.454977,
      "cogs": 1599647538.96,
      "gross_margin": 42.31,
      "pe_forward": null,
      "valuation_history_days": 328,
      "valuation_history_from": "20250321",
      "current_price": 242.3,
      "price": 242.3,
      "ma5": 247.18,
      "ma10": 248.01,
      "ma20": 246.73,
      "dist_ma5_pct": -2.0,
      "dist_ma10_pct": -2.3,
      "dist_ma20_pct": -1.8,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 3.74,
        "pct_float": 4.72,
        "chg5_pct": 5.75,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "002056.SZ",
      "fetch_time": "2026-07-31T11:41:07+0800",
      "name": "横店东磁",
      "pe": 19.3481,
      "pb": 3.422,
      "ps_ttm": 1.5068,
      "pcf_ttm": 10.062,
      "valuation_percentile": 42.61,
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
      "score_trend": 6.2,
      "score_value": 6.5,
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
      "valuation_history_from": "20210802",
      "current_price": 20.88,
      "price": 20.88,
      "ma5": 21.38,
      "ma10": 22.22,
      "ma20": 25.43,
      "dist_ma5_pct": -2.3,
      "dist_ma10_pct": -6.0,
      "dist_ma20_pct": -17.9,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.9441,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 7.12,
        "pct_float": 2.17,
        "chg5_pct": 4.29,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "688183.SH",
      "fetch_time": "2026-07-31T11:41:07+0800",
      "name": "生益电子",
      "pe": 47.0555,
      "pb": 14.283,
      "ps_ttm": 7.8283,
      "pcf_ttm": 39.357,
      "valuation_percentile": 70.92,
      "total_shares": 837591234,
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
          "name": "印制电路板",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "科技龙头指数",
        "双创100指数",
        "出海贸易指数",
        "股权激励指数",
        "电路板指数",
        "元件精选指数"
      ],
      "score_company": 8.6,
      "score_trend": 5.4,
      "score_value": 4.9,
      "highlights": [
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 101% ，利润成长性强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 13% ，投入资本回报率为 11% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 147% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 7.1% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "回购",
          "text": "近6月，公司累计回购 56万股 ，占总股本比例 0.07% ，金额合计 5001万元 。"
        }
      ],
      "risks": [],
      "events": [
        {
          "content": "预计2026/08/15发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-15"
        },
        {
          "content": "11:18 长江证券研报指出，PCB及CCL板块多家公司披露2026年半年度业绩预告。CCL端，生益科技预计归母净利润同比增长117%至131%。PCB端，沪电股份、深南电路、生益电子预计归母净利润均实现较快增长。按半年度预告区间测算，上述公司Q2归母净利润均较一季度环比提升，显示产业景气度持续验证。AI算力需求扩张及技术升级拉动了高多层、高密度、低损耗PCB需求，相关厂商业绩增长已体现需求向利润端传导。\n长江证券认为，铜价高位运行、电子布涨价及高频高速铜箔供应偏紧，推动覆铜板进入价格传导阶段，金安国纪、华正新材和生益科技通过提价、扩产及产品结构优化实现盈利提升。同时，服务器平台升级带动对高速覆铜板需求，行业正由需求扩张迈向量价共振，高阶PCB与高速CCL仍是核心受益方向。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "10:29 科创50指数跌幅扩大至3%，现报1753.32点。成分股中，源杰科技跌超10%，生益电子、佰维存储跌超7%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价盘中上涨 8.30% ，股价收盘涨幅 14.21%",
          "tags": [
            "股价上涨"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 6828942763.59,
      "revenue_yoy": 1.147914,
      "operating_profit": 1259167039.02,
      "operating_profit_yoy": 5.634878,
      "net_profit": 1114677828.12,
      "net_profit_yoy": 4.976069,
      "gross_profit": 2183686365.16,
      "gross_profit_yoy": 2.198296,
      "cogs": 4645256398.43,
      "gross_margin": 31.98,
      "pe_forward": null,
      "valuation_history_days": 277,
      "valuation_history_from": "20230227",
      "current_price": 92.91,
      "price": 92.91,
      "ma5": 96.51,
      "ma10": 103.69,
      "ma20": 114.09,
      "dist_ma5_pct": -3.7,
      "dist_ma10_pct": -10.4,
      "dist_ma20_pct": -18.6,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.8907,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 16.12,
        "pct_float": 2.34,
        "chg5_pct": -12.78,
        "net5_repay_days": 3,
        "signal": "deleveraging"
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
        "iv_rank": 0.8795,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.91,
        "pct_float": 1.46,
        "chg5_pct": -7.42,
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
        }
      ]
    }
  ],
  "position_prices": {
    "000703": {
      "code": "000703",
      "name": "恒逸石化",
      "date": "2026-07-31",
      "price": 15.87,
      "open": 15.42,
      "high": 16.01,
      "low": 15.15,
      "prev_close": 16.05,
      "change_pct": -1.12,
      "volume": 425242,
      "amount": 664839871.78,
      "source": "sina",
      "mavol30": 8067.47,
      "volume_below_mavol30": false
    }
  },
  "missed_opportunity_prices": [
    {
      "code": "688200",
      "name": "华峰测控",
      "recommended_date": "2026-07-30",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 371.32,
      "return_pct": null
    },
    {
      "code": "688361",
      "name": "中科飞测",
      "recommended_date": "2026-07-30",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 364.78,
      "return_pct": null
    },
    {
      "code": "300285",
      "name": "国瓷材料",
      "recommended_date": "2026-07-30",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 64.8,
      "return_pct": null
    },
    {
      "code": "300408",
      "name": "三环集团",
      "recommended_date": "2026-07-30",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 115.07,
      "return_pct": null
    },
    {
      "code": "601168",
      "name": "西部矿业",
      "recommended_date": "2026-07-30",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 37.8,
      "return_pct": null
    },
    {
      "code": "603259",
      "name": "药明康德",
      "recommended_date": "2026-07-30",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 127.62,
      "return_pct": null
    },
    {
      "code": "688146",
      "name": "中船特气",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 297.87,
      "return_pct": null
    },
    {
      "code": "688498",
      "name": "源杰科技",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 1134.7,
      "return_pct": null
    },
    {
      "code": "300604",
      "name": "长川科技",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 269.86,
      "return_pct": null
    },
    {
      "code": "688256",
      "name": "寒武纪",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 1128.02,
      "return_pct": null
    },
    {
      "code": "600428",
      "name": "中远海特",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 11.31,
      "return_pct": null
    },
    {
      "code": "000938",
      "name": "紫光股份",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 35.02,
      "return_pct": null
    },
    {
      "code": "002353",
      "name": "杰瑞股份",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 135.5,
      "return_pct": null
    },
    {
      "code": "301536",
      "name": "星宸科技",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 115.98,
      "return_pct": null
    },
    {
      "code": "001389",
      "name": "广合科技",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 142.46,
      "return_pct": null
    },
    {
      "code": "002080",
      "name": "中材科技",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 44.14,
      "return_pct": null
    },
    {
      "code": "000703",
      "name": "恒逸石化",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 15.87,
      "return_pct": null
    },
    {
      "code": "603156",
      "name": "养元饮品",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 39.07,
      "return_pct": null
    },
    {
      "code": "688630",
      "name": "芯碁微装",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 343.52,
      "return_pct": null
    },
    {
      "code": "300806",
      "name": "斯迪克",
      "recommended_date": "2026-07-29",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 42.88,
      "return_pct": null
    },
    {
      "code": "688629",
      "name": "华丰科技",
      "recommended_date": "2026-07-28",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 137.08,
      "return_pct": null
    }
  ],
  "iv_sentiment": {
    "date": "2026-07-31",
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
        "current_iv": 0.1858,
        "is_live": false,
        "iv_high": 0.2272,
        "iv_low": 0.1137,
        "iv_high_raw": 0.2625,
        "iv_low_raw": 0.1137,
        "iv_rank": 0.6353,
        "iv_rank_raw": 0.4845,
        "iv_percentile": 0.765,
        "iv_percentile_raw": 0.7378,
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
          0.1048,
          0.2283
        ],
        "name": "50ETF",
        "desc": "大盘蓝筹",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "510300",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 218,
        "current_iv": 0.2154,
        "is_live": false,
        "iv_high": 0.2476,
        "iv_low": 0.1201,
        "iv_high_raw": 0.3137,
        "iv_low_raw": 0.069,
        "iv_rank": 0.7475,
        "iv_rank_raw": 0.5983,
        "iv_percentile": 0.8716,
        "iv_percentile_raw": 0.8533,
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
          0.2492
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
        "current_iv": 0.3485,
        "is_live": false,
        "iv_high": 0.3575,
        "iv_low": 0.194,
        "iv_high_raw": 0.4544,
        "iv_low_raw": 0.107,
        "iv_rank": 0.9451,
        "iv_rank_raw": 0.6952,
        "iv_percentile": 0.9722,
        "iv_percentile_raw": 0.9422,
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
          0.174,
          0.3588
        ],
        "name": "500ETF",
        "desc": "中证500",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "588000",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 217,
        "current_iv": 0.5921,
        "is_live": false,
        "iv_high": 0.6345,
        "iv_low": 0.2467,
        "iv_high_raw": 0.7788,
        "iv_low_raw": 0.126,
        "iv_rank": 0.8907,
        "iv_rank_raw": 0.714,
        "iv_percentile": 0.9631,
        "iv_percentile_raw": 0.9378,
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
          0.1593,
          0.6351
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
        "current_iv": 0.4893,
        "is_live": false,
        "iv_high": 0.4893,
        "iv_low": 0.2082,
        "iv_high_raw": 0.6363,
        "iv_low_raw": 0.2082,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.6567,
        "iv_percentile": 0.9954,
        "iv_percentile_raw": 0.973,
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
            "date": "2026-07-30",
            "iv": 0.5331
          }
        ],
        "sigma_range": [
          0.1748,
          0.4908
        ],
        "name": "创业板ETF",
        "desc": "创业板",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159922",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 212,
        "current_iv": 0.34,
        "is_live": false,
        "iv_high": 0.3495,
        "iv_low": 0.1804,
        "iv_high_raw": 0.468,
        "iv_low_raw": 0.1804,
        "iv_rank": 0.9441,
        "iv_rank_raw": 0.555,
        "iv_percentile": 0.9811,
        "iv_percentile_raw": 0.9369,
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
          0.1772,
          0.3513
        ],
        "name": "500ETF深",
        "desc": "深市中盘",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159919",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 216,
        "current_iv": 0.2237,
        "is_live": false,
        "iv_high": 0.258,
        "iv_low": 0.1298,
        "iv_high_raw": 0.3431,
        "iv_low_raw": 0.1298,
        "iv_rank": 0.7325,
        "iv_rank_raw": 0.4403,
        "iv_percentile": 0.875,
        "iv_percentile_raw": 0.8514,
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
          0.1118,
          0.2589
        ],
        "name": "300ETF深",
        "desc": "深市宽基",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "159901",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 217,
        "current_iv": 0.3198,
        "is_live": false,
        "iv_high": 0.3406,
        "iv_low": 0.1682,
        "iv_high_raw": 0.4504,
        "iv_low_raw": 0.1682,
        "iv_rank": 0.8795,
        "iv_rank_raw": 0.5372,
        "iv_percentile": 0.9447,
        "iv_percentile_raw": 0.9234,
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
          0.146,
          0.3421
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
        "current_iv": 0.6208,
        "is_live": false,
        "iv_high": 0.6208,
        "iv_low": 0.184,
        "iv_high_raw": 0.756,
        "iv_low_raw": 0.184,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.7636,
        "iv_percentile": 0.9954,
        "iv_percentile_raw": 0.9643,
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
          0.1624,
          0.631
        ],
        "name": "科创板50",
        "desc": "科创板（备用代理）",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      }
    ],
    "overall_sentiment": {
      "signal": "极度恐慌",
      "avg_iv_rank": 0.8437,
      "avg_iv_percentile": 0.9135,
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
    "regime": "strong",
    "breadth_ratio": 5.0022,
    "up": 4517,
    "down": 903,
    "positive_indices": [
      "上证指数",
      "深证成指",
      "创业板指"
    ],
    "negative_indices": [],
    "limit_ups": 88,
    "limit_downs": 0,
    "sizing_multiplier": 1.0,
    "hard_block": false,
    "reason": "Entry regime strong: breadth 5.00:1, 3/3 major indices green, 88 limit-ups / 0 limit-downs. Allow entries at full size; per-stock overextension is filtered individually (dist_ma)."
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
  "active_learnings": "## Active Rules (proven, hitRate ≥ 75%)\n- [h013] Strong breadth alone is not enough to force entries; without candidate RPS and MA-distance data, the correct momentum decision is to keep cash. (hitRate: 99%, n=130, confidence: 98%)\n- [h019] Bottom-list sectors should be treated as hard no-buy zones even when individual names still carry acceptable RPS readings. (hitRate: 100%, n=50, confidence: 98%)\n- [h028] Today’s relative leaders are concentrated in communication equipment and adjacent tech hardware, while cyclicals/agri/resource laggards are being de-risked aggressively. (hitRate: 100%, n=50, confidence: 98%)\n- [h027] MA-distance discipline remains critical inside hot sectors: a hot sector does not override chase risk when dist_ma5_pct exceeds 6% or dist_ma10_pct exceeds 8%. (hitRate: 100%, n=42, confidence: 98%)\n- [h023] Raising stops mechanically after +10% works well in weak tapes because it converts a fast winner into a low-risk hold without needing a fresh market call. (hitRate: 100%, n=36, confidence: 97%)\n- [h021] The MA-distance anti-chase rule is doing real work: several visually strong names fail because they are too far above short-term support. (hitRate: 98%, n=102, confidence: 97%)\n- [h077] The hard block is preventing FOMO entries. 新宙邦 (宁德时代协议 catalyst, VCP SETUP) and 奥来德 (dist_ma5 0.3%) would have been tempting buys in V1. V2 correctly forces cash preservation in panic regime. (hitRate: 100%, n=17, confidence: 95%)\n- [h017] Low-IV conditions around 16-22% IV rank do not justify freezing risk when breadth is 5.6:1; they argue for normal sizing but tighter discipline on chasing. (hitRate: 96%, n=28, confidence: 93%)\n- [h024] Stop-proximity violations deserve proactive action before the hard stop is hit, especially in 科创板 names where gap risk can erase the remaining cushion quickly. (hitRate: 91%, n=11, confidence: 85%)\n",
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
