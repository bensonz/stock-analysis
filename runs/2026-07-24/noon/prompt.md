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
  "date": "2026-07-24",
  "portfolio": {
    "startingCapital": 1000000,
    "totalEquity": 954471.0,
    "cash": 889233.0,
    "investedValue": 65238.0,
    "unrealizedPnl": -1750.0,
    "realizedPnl": -43779.0,
    "totalPnl": -45529.0,
    "totalReturnPct": -4.55,
    "positionsUsed": 2,
    "positionsMax": 10,
    "cashPct": 93.17,
    "dayPnl": -1750.0,
    "minCashPct": 0,
    "minCashValue": 0.0,
    "deployableCash": 889233.0
  },
  "market": {
    "timestamp": "2026-07-24T11:40:45.556993",
    "indices": {
      "上证指数": {
        "code": "sh000001",
        "close": 3830.194,
        "change_pct": -1.2,
        "date": "2026-07-24"
      },
      "深证成指": {
        "code": "sz399001",
        "close": 13873.5,
        "change_pct": -1.77,
        "date": "2026-07-24"
      },
      "创业板指": {
        "code": "sz399006",
        "close": 3511.75,
        "change_pct": -1.78,
        "date": "2026-07-24"
      },
      "科创50": {
        "code": "sh000688",
        "close": 1794.479,
        "change_pct": 0.27,
        "date": "2026-07-24"
      }
    },
    "breadth": {
      "up": 548,
      "down": 4939,
      "flat": 40,
      "total": 5527,
      "distribution": {
        "f10": 4,
        "f7_10": 77,
        "f4_7": 694,
        "f2_4": 2734,
        "f0_2": 1430,
        "f0": 40,
        "r0_2": 310,
        "r2_4": 111,
        "r4_7": 66,
        "r7_10": 29,
        "r10": 32
      }
    },
    "sectors": {
      "top5": [
        {
          "板块名称": "地面兵装Ⅱ",
          "涨跌幅": 3.65
        },
        {
          "板块名称": "半导体",
          "涨跌幅": 0.59
        },
        {
          "板块名称": "国有大型银行Ⅱ",
          "涨跌幅": 0.41
        },
        {
          "板块名称": "股份制银行Ⅱ",
          "涨跌幅": 0.27
        },
        {
          "板块名称": "城商行Ⅱ",
          "涨跌幅": 0.11
        }
      ],
      "bottom5": [
        {
          "板块名称": "贵金属",
          "涨跌幅": -4.56
        },
        {
          "板块名称": "工业金属",
          "涨跌幅": -4.54
        },
        {
          "板块名称": "医疗美容",
          "涨跌幅": -3.82
        },
        {
          "板块名称": "广告营销",
          "涨跌幅": -3.61
        },
        {
          "板块名称": "数字媒体",
          "涨跌幅": -3.59
        }
      ]
    }
  },
  "strategy_pool": {
    "source": "cheesefortune_intersection",
    "total_stocks": 50,
    "stocks": [
      {
        "code": "002980",
        "code_full": "002980.SZ",
        "name": "华盛昌",
        "source_date": "2026/04/30",
        "highlights_count": 5,
        "market_cap": 160.2144,
        "pe": 6.2,
        "risks_count": 2,
        "rps20": 44.26,
        "rps60": 99.98,
        "rps120": 99.78,
        "rps250": 97.77,
        "ma10": 93.96,
        "vcp_quality": null,
        "ma5": 89.61,
        "ma20": 102.84,
        "dist_ma5_pct": -5.6,
        "dist_ma10_pct": -10.0,
        "dist_ma20_pct": -17.7
      },
      {
        "code": "301396",
        "code_full": "301396.SZ",
        "name": "宏景科技",
        "source_date": "2026/05/13",
        "highlights_count": 4,
        "market_cap": 410.5059,
        "pe": 3.7,
        "risks_count": 1,
        "rps20": 84.01,
        "rps60": 99.04,
        "rps120": 99.56,
        "rps250": 95.69,
        "ma10": 219.58,
        "vcp_quality": null,
        "ma5": 199.24,
        "ma20": 255.37,
        "dist_ma5_pct": -4.1,
        "dist_ma10_pct": -13.0,
        "dist_ma20_pct": -25.2
      },
      {
        "code": "688630",
        "code_full": "688630.SH",
        "name": "芯碁微装",
        "source_date": "2026/03/12",
        "highlights_count": 6,
        "market_cap": 562.5796,
        "pe": 5.3,
        "risks_count": 0,
        "rps20": 97.97,
        "rps60": 99.3,
        "rps120": 99.46,
        "rps250": 99.25,
        "ma10": 420.68,
        "vcp_quality": null,
        "ma5": 378.45,
        "ma20": 459.07,
        "dist_ma5_pct": 6.0,
        "dist_ma10_pct": -4.7,
        "dist_ma20_pct": -12.6
      },
      {
        "code": "605376",
        "code_full": "605376.SH",
        "name": "博迁新材",
        "source_date": "2026/07/11",
        "highlights_count": 5,
        "market_cap": 383.0086,
        "pe": 5.6,
        "risks_count": 1,
        "rps20": 90.38,
        "rps60": 97.09,
        "rps120": 99.4,
        "rps250": 98.93,
        "ma10": 174.93,
        "vcp_quality": null,
        "ma5": 148.57,
        "ma20": 209.06,
        "dist_ma5_pct": -2.4,
        "dist_ma10_pct": -17.1,
        "dist_ma20_pct": -30.6
      },
      {
        "code": "000811",
        "code_full": "000811.SZ",
        "name": "冰轮环境",
        "source_date": "2026/06/12",
        "highlights_count": 4,
        "market_cap": 425.2768,
        "pe": 28.1,
        "risks_count": 2,
        "rps20": 99.56,
        "rps60": 99.56,
        "rps120": 99.28,
        "rps250": 98.04,
        "ma10": 46.69,
        "vcp_quality": null,
        "ma5": 42.67,
        "ma20": 50.3,
        "dist_ma5_pct": 0.4,
        "dist_ma10_pct": -8.2,
        "dist_ma20_pct": -14.8
      },
      {
        "code": "301362",
        "code_full": "301362.SZ",
        "name": "民爆光电",
        "source_date": "2026/06/16",
        "highlights_count": 4,
        "market_cap": 170.2591,
        "pe": 2.9,
        "risks_count": 1,
        "rps20": 4.85,
        "rps60": 97.01,
        "rps120": 99.07,
        "rps250": 97.18,
        "ma10": 130.13,
        "vcp_quality": null,
        "ma5": 116.34,
        "ma20": 153.24,
        "dist_ma5_pct": 0.3,
        "dist_ma10_pct": -10.4,
        "dist_ma20_pct": -23.9
      },
      {
        "code": "688257",
        "code_full": "688257.SH",
        "name": "新锐股份",
        "source_date": "2026/07/14",
        "highlights_count": 4,
        "market_cap": 215.5738,
        "pe": 4.7,
        "risks_count": 1,
        "rps20": 31.5,
        "rps60": 94.96,
        "rps120": 98.61,
        "rps250": 97.25,
        "ma10": 76.13,
        "vcp_quality": null,
        "ma5": 66.26,
        "ma20": 89.99,
        "dist_ma5_pct": -7.3,
        "dist_ma10_pct": -19.4,
        "dist_ma20_pct": -31.8
      },
      {
        "code": "300503",
        "code_full": "300503.SZ",
        "name": "昊志机电",
        "source_date": "2026/07/24",
        "highlights_count": 5,
        "market_cap": 209.2552,
        "pe": 10.3,
        "risks_count": 2,
        "rps20": 87.69,
        "rps60": 94.54,
        "rps120": 98.53,
        "rps250": 97.1,
        "ma10": 77.09,
        "vcp_quality": null,
        "ma5": 69.25,
        "ma20": 85.52,
        "dist_ma5_pct": -2.0,
        "dist_ma10_pct": -11.9,
        "dist_ma20_pct": -20.6
      },
      {
        "code": "300285",
        "code_full": "300285.SZ",
        "name": "国瓷材料",
        "source_date": "2026/07/08",
        "highlights_count": 7,
        "market_cap": 606.7039,
        "pe": 14.5,
        "risks_count": 2,
        "rps20": 98.05,
        "rps60": 98.79,
        "rps120": 98.49,
        "rps250": 97.83,
        "ma10": 63.29,
        "vcp_quality": null,
        "ma5": 57.5,
        "ma20": 79.39,
        "dist_ma5_pct": 5.8,
        "dist_ma10_pct": -3.9,
        "dist_ma20_pct": -23.4
      },
      {
        "code": "688300",
        "code_full": "688300.SH",
        "name": "联瑞新材",
        "source_date": "2026/05/06",
        "highlights_count": 6,
        "market_cap": 307.5835,
        "pe": 6.6,
        "risks_count": 0,
        "rps20": 91.45,
        "rps60": 99.34,
        "rps120": 98.47,
        "rps250": 95.65,
        "ma10": 158.64,
        "vcp_quality": null,
        "ma5": 136.96,
        "ma20": 197.91,
        "dist_ma5_pct": -6.3,
        "dist_ma10_pct": -19.1,
        "dist_ma20_pct": -35.2
      },
      {
        "code": "001389",
        "code_full": "001389.SZ",
        "name": "广合科技",
        "source_date": "2026/07/22",
        "highlights_count": 6,
        "market_cap": 758.6982,
        "pe": 2.3,
        "risks_count": 1,
        "rps20": 84.49,
        "rps60": 97.23,
        "rps120": 98.13,
        "rps250": 97.57,
        "ma10": 176.79,
        "vcp_quality": null,
        "ma5": 167.23,
        "ma20": 190.27,
        "dist_ma5_pct": -4.0,
        "dist_ma10_pct": -9.2,
        "dist_ma20_pct": -15.6
      },
      {
        "code": "600869",
        "code_full": "600869.SH",
        "name": "远东股份",
        "source_date": "2026/06/29",
        "highlights_count": 6,
        "market_cap": 346.441,
        "pe": 31.4,
        "risks_count": 5,
        "rps20": 20.7,
        "rps60": 95.74,
        "rps120": 98.11,
        "rps250": 98.1,
        "ma10": 18.45,
        "vcp_quality": null,
        "ma5": 15.88,
        "ma20": 25.32,
        "dist_ma5_pct": -1.7,
        "dist_ma10_pct": -15.4,
        "dist_ma20_pct": -38.4
      },
      {
        "code": "002655",
        "code_full": "002655.SZ",
        "name": "共达电声",
        "source_date": "2026/07/22",
        "highlights_count": 4,
        "market_cap": 94.3908,
        "pe": 14.4,
        "risks_count": 3,
        "rps20": 62.9,
        "rps60": 99.18,
        "rps120": 98.07,
        "rps250": 94.31,
        "ma10": 30.69,
        "vcp_quality": null,
        "ma5": 26.84,
        "ma20": 37.19,
        "dist_ma5_pct": -3.5,
        "dist_ma10_pct": -15.6,
        "dist_ma20_pct": -30.4
      },
      {
        "code": "300806",
        "code_full": "300806.SZ",
        "name": "斯迪克",
        "source_date": "2026/04/28",
        "highlights_count": 6,
        "market_cap": 267.9006,
        "pe": 6.6,
        "risks_count": 2,
        "rps20": 58.54,
        "rps60": 93.37,
        "rps120": 98.03,
        "rps250": 98.76,
        "ma10": 68.98,
        "vcp_quality": null,
        "ma5": 59.69,
        "ma20": 85.24,
        "dist_ma5_pct": -1.0,
        "dist_ma10_pct": -14.3,
        "dist_ma20_pct": -30.7
      },
      {
        "code": "688017",
        "code_full": "688017.SH",
        "name": "绿的谐波",
        "source_date": "2026/07/08",
        "highlights_count": 4,
        "market_cap": 565.1884,
        "pe": 5.9,
        "risks_count": 1,
        "rps20": 92.26,
        "rps60": 96.73,
        "rps120": 97.95,
        "rps250": 94.45,
        "ma10": 371.98,
        "vcp_quality": null,
        "ma5": 329.79,
        "ma20": 385.85,
        "dist_ma5_pct": -4.0,
        "dist_ma10_pct": -14.9,
        "dist_ma20_pct": -17.9
      },
      {
        "code": "688200",
        "code_full": "688200.SH",
        "name": "华峰测控",
        "source_date": "2026/07/22",
        "highlights_count": 5,
        "market_cap": 721.5689,
        "pe": 6.4,
        "risks_count": 0,
        "rps20": 93.5,
        "rps60": 95.24,
        "rps120": 97.89,
        "rps250": 95.93,
        "ma10": 437.8,
        "vcp_quality": null,
        "ma5": 384.79,
        "ma20": 435.52,
        "dist_ma5_pct": -4.1,
        "dist_ma10_pct": -15.7,
        "dist_ma20_pct": -15.3
      },
      {
        "code": "688531",
        "code_full": "688531.SH",
        "name": "日联科技",
        "source_date": "2026/06/16",
        "highlights_count": 6,
        "market_cap": 204.9059,
        "pe": 3.3,
        "risks_count": 0,
        "rps20": 55.46,
        "rps60": 98.53,
        "rps120": 97.72,
        "rps250": 93.11,
        "ma10": 150.21,
        "vcp_quality": null,
        "ma5": 130.06,
        "ma20": 162.26,
        "dist_ma5_pct": -2.7,
        "dist_ma10_pct": -15.8,
        "dist_ma20_pct": -22.0
      },
      {
        "code": "003031",
        "code_full": "003031.SZ",
        "name": "中瓷电子",
        "source_date": "2026/07/01",
        "highlights_count": 4,
        "market_cap": 485.2878,
        "pe": 5.5,
        "risks_count": 2,
        "rps20": 42.29,
        "rps60": 96.61,
        "rps120": 97.6,
        "rps250": 94.86,
        "ma10": 120.26,
        "vcp_quality": null,
        "ma5": 106.69,
        "ma20": 144.1,
        "dist_ma5_pct": 0.8,
        "dist_ma10_pct": -10.5,
        "dist_ma20_pct": -25.3
      },
      {
        "code": "688629",
        "code_full": "688629.SH",
        "name": "华丰科技",
        "source_date": "2026/07/15",
        "highlights_count": 4,
        "market_cap": 728.6984,
        "pe": 3.0,
        "risks_count": 1,
        "rps20": 98.07,
        "rps60": 97.87,
        "rps120": 97.44,
        "rps250": 96.23,
        "ma10": 176.37,
        "vcp_quality": null,
        "ma5": 157.18,
        "ma20": 171.1,
        "dist_ma5_pct": 7.8,
        "dist_ma10_pct": -3.9,
        "dist_ma20_pct": -0.9
      },
      {
        "code": "688150",
        "code_full": "688150.SH",
        "name": "莱特光电",
        "source_date": "2026/04/16",
        "highlights_count": 5,
        "market_cap": 164.7177,
        "pe": 4.3,
        "risks_count": 2,
        "rps20": 53.57,
        "rps60": 97.19,
        "rps120": 97.14,
        "rps250": 92.04,
        "ma10": 49.6,
        "vcp_quality": null,
        "ma5": 45.01,
        "ma20": 55.29,
        "dist_ma5_pct": -6.0,
        "dist_ma10_pct": -14.7,
        "dist_ma20_pct": -23.5
      },
      {
        "code": "002937",
        "code_full": "002937.SZ",
        "name": "兴瑞科技",
        "source_date": "2026/04/23",
        "highlights_count": 4,
        "market_cap": 99.1955,
        "pe": 7.8,
        "risks_count": 1,
        "rps20": 95.76,
        "rps60": 96.42,
        "rps120": 96.9,
        "rps250": 92.81,
        "ma10": 37.84,
        "vcp_quality": null,
        "ma5": 34.34,
        "ma20": 40.62,
        "dist_ma5_pct": -8.6,
        "dist_ma10_pct": -17.0,
        "dist_ma20_pct": -22.7
      },
      {
        "code": "301182",
        "code_full": "301182.SZ",
        "name": "凯旺科技",
        "source_date": "2026/04/24",
        "highlights_count": 4,
        "market_cap": 55.9024,
        "pe": 4.5,
        "risks_count": 3,
        "rps20": 63.63,
        "rps60": 95.96,
        "rps120": 96.8,
        "rps250": 92.99,
        "ma10": 71.68,
        "vcp_quality": null,
        "ma5": 60.58,
        "ma20": 86.64,
        "dist_ma5_pct": -3.7,
        "dist_ma10_pct": -18.6,
        "dist_ma20_pct": -32.7
      },
      {
        "code": "000703",
        "code_full": "000703.SZ",
        "name": "恒逸石化",
        "source_date": "2026/06/08",
        "highlights_count": 5,
        "market_cap": 604.5711,
        "pe": 15.1,
        "risks_count": 3,
        "rps20": 94.09,
        "rps60": 89.19,
        "rps120": 96.42,
        "rps250": 93.52,
        "ma10": 14.56,
        "vcp_quality": null,
        "ma5": 15.08,
        "ma20": 14.61,
        "dist_ma5_pct": 4.9,
        "dist_ma10_pct": 8.7,
        "dist_ma20_pct": 8.3
      },
      {
        "code": "301536",
        "code_full": "301536.SZ",
        "name": "星宸科技",
        "source_date": "2026/04/20",
        "highlights_count": 4,
        "market_cap": 554.3447,
        "pe": 2.3,
        "risks_count": 2,
        "rps20": 98.61,
        "rps60": 96.63,
        "rps120": 96.24,
        "rps250": 90.12,
        "ma10": 113.76,
        "vcp_quality": null,
        "ma5": 112.34,
        "ma20": 116.42,
        "dist_ma5_pct": 22.0,
        "dist_ma10_pct": 20.4,
        "dist_ma20_pct": 17.7
      },
      {
        "code": "002957",
        "code_full": "002957.SZ",
        "name": "科瑞技术",
        "source_date": "2026/07/15",
        "highlights_count": 4,
        "market_cap": 157.9974,
        "pe": 7.0,
        "risks_count": 3,
        "rps20": 24.32,
        "rps60": 95.12,
        "rps120": 95.93,
        "rps250": 94.83,
        "ma10": 39.78,
        "vcp_quality": null,
        "ma5": 36.13,
        "ma20": 45.45,
        "dist_ma5_pct": 4.1,
        "dist_ma10_pct": -5.4,
        "dist_ma20_pct": -17.2
      },
      {
        "code": "688777",
        "code_full": "688777.SH",
        "name": "中控技术",
        "source_date": "2026/07/13",
        "highlights_count": 5,
        "market_cap": 659.4565,
        "pe": 5.6,
        "risks_count": 2,
        "rps20": 88.82,
        "rps60": 86.56,
        "rps120": 95.67,
        "rps250": 90.24,
        "ma10": 95.5,
        "vcp_quality": null,
        "ma5": 90.03,
        "ma20": 105.07,
        "dist_ma5_pct": -4.5,
        "dist_ma10_pct": -9.9,
        "dist_ma20_pct": -18.2
      },
      {
        "code": "002821",
        "code_full": "002821.SZ",
        "name": "凯莱英",
        "source_date": "2026/04/01",
        "highlights_count": 7,
        "market_cap": 590.0212,
        "pe": 9.6,
        "risks_count": 1,
        "rps20": 99.6,
        "rps60": 96.91,
        "rps120": 95.17,
        "rps250": 92.26,
        "ma10": 171.09,
        "vcp_quality": null,
        "ma5": 164.36,
        "ma20": 163.49,
        "dist_ma5_pct": -0.5,
        "dist_ma10_pct": -4.4,
        "dist_ma20_pct": 0.0
      },
      {
        "code": "688378",
        "code_full": "688378.SH",
        "name": "奥来德",
        "source_date": "2026/06/06",
        "highlights_count": 5,
        "market_cap": 102.3741,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 79.48,
        "rps60": 91.76,
        "rps120": 94.83,
        "rps250": 94.25,
        "ma10": 47.13,
        "vcp_quality": null,
        "ma5": 41.67,
        "ma20": 51.54,
        "dist_ma5_pct": -4.5,
        "dist_ma10_pct": -15.6,
        "dist_ma20_pct": -22.8
      },
      {
        "code": "300323",
        "code_full": "300323.SZ",
        "name": "华灿光电",
        "source_date": "2026/04/29",
        "highlights_count": 4,
        "market_cap": 186.4826,
        "pe": 14.1,
        "risks_count": 2,
        "rps20": 33.96,
        "rps60": 96.24,
        "rps120": 94.54,
        "rps250": 91.01,
        "ma10": 12.97,
        "vcp_quality": null,
        "ma5": 11.49,
        "ma20": 15.69,
        "dist_ma5_pct": -0.0,
        "dist_ma10_pct": -11.4,
        "dist_ma20_pct": -26.8
      },
      {
        "code": "688376",
        "code_full": "688376.SH",
        "name": "美埃科技",
        "source_date": "2026/04/28",
        "highlights_count": 5,
        "market_cap": 91.011,
        "pe": 3.6,
        "risks_count": 1,
        "rps20": 93.3,
        "rps60": 91.28,
        "rps120": 94.32,
        "rps250": 92.4,
        "ma10": 81.07,
        "vcp_quality": null,
        "ma5": 70.27,
        "ma20": 88.43,
        "dist_ma5_pct": -0.1,
        "dist_ma10_pct": -13.4,
        "dist_ma20_pct": -20.6
      },
      {
        "code": "688536",
        "code_full": "688536.SH",
        "name": "思瑞浦",
        "source_date": "2026/04/01",
        "highlights_count": 6,
        "market_cap": 352.0925,
        "pe": 5.8,
        "risks_count": 1,
        "rps20": 74.47,
        "rps60": 95.48,
        "rps120": 94.26,
        "rps250": 88.17,
        "ma10": 282.57,
        "vcp_quality": null,
        "ma5": 251.2,
        "ma20": 312.27,
        "dist_ma5_pct": 3.1,
        "dist_ma10_pct": -8.4,
        "dist_ma20_pct": -17.1
      },
      {
        "code": "688392",
        "code_full": "688392.SH",
        "name": "骄成超声",
        "source_date": "2026/04/22",
        "highlights_count": 6,
        "market_cap": 178.1831,
        "pe": 3.8,
        "risks_count": 1,
        "rps20": 96.76,
        "rps60": 94.01,
        "rps120": 93.78,
        "rps250": 97.39,
        "ma10": 183.74,
        "vcp_quality": null,
        "ma5": 159.72,
        "ma20": 188.12,
        "dist_ma5_pct": 1.5,
        "dist_ma10_pct": -11.8,
        "dist_ma20_pct": -13.8
      },
      {
        "code": "002432",
        "code_full": "002432.SZ",
        "name": "九安医疗",
        "source_date": "2026/07/15",
        "highlights_count": 4,
        "market_cap": 342.3388,
        "pe": 16.1,
        "risks_count": 3,
        "rps20": 76.95,
        "rps60": 96.69,
        "rps120": 93.58,
        "rps250": 88.21,
        "ma10": 70.29,
        "vcp_quality": null,
        "ma5": 77.31,
        "ma20": 67.99,
        "dist_ma5_pct": -5.0,
        "dist_ma10_pct": 4.5,
        "dist_ma20_pct": 8.1
      },
      {
        "code": "300373",
        "code_full": "300373.SZ",
        "name": "扬杰科技",
        "source_date": "2026/07/22",
        "highlights_count": 4,
        "market_cap": 506.0741,
        "pe": 12.5,
        "risks_count": 0,
        "rps20": 95.86,
        "rps60": 92.55,
        "rps120": 93.22,
        "rps250": 92.71,
        "ma10": 103.49,
        "vcp_quality": null,
        "ma5": 93.58,
        "ma20": 120.66,
        "dist_ma5_pct": -0.5,
        "dist_ma10_pct": -10.0,
        "dist_ma20_pct": -22.8
      },
      {
        "code": "688401",
        "code_full": "688401.SH",
        "name": "路维光电",
        "source_date": "2026/04/21",
        "highlights_count": 4,
        "market_cap": 136.0985,
        "pe": 3.9,
        "risks_count": 0,
        "rps20": 85.27,
        "rps60": 94.38,
        "rps120": 93.17,
        "rps250": 91.88,
        "ma10": 75.03,
        "vcp_quality": null,
        "ma5": 66.14,
        "ma20": 81.26,
        "dist_ma5_pct": 0.9,
        "dist_ma10_pct": -11.0,
        "dist_ma20_pct": -17.8
      },
      {
        "code": "688331",
        "code_full": "688331.SH",
        "name": "荣昌生物",
        "source_date": "2026/07/06",
        "highlights_count": 5,
        "market_cap": 703.2825,
        "pe": 4.3,
        "risks_count": 1,
        "rps20": 97.2,
        "rps60": 92.39,
        "rps120": 91.87,
        "rps250": 94.79,
        "ma10": 132.36,
        "vcp_quality": null,
        "ma5": 126.19,
        "ma20": 128.45,
        "dist_ma5_pct": 0.6,
        "dist_ma10_pct": -4.1,
        "dist_ma20_pct": -1.2
      },
      {
        "code": "601958",
        "code_full": "601958.SH",
        "name": "金钼股份",
        "source_date": "2026/07/03",
        "highlights_count": 5,
        "market_cap": 705.0131,
        "pe": 18.2,
        "risks_count": 2,
        "rps20": 79.88,
        "rps60": 86.42,
        "rps120": 91.81,
        "rps250": 92.34,
        "ma10": 21.77,
        "vcp_quality": null,
        "ma5": 20.8,
        "ma20": 24.73,
        "dist_ma5_pct": 3.0,
        "dist_ma10_pct": -1.6,
        "dist_ma20_pct": -13.3
      },
      {
        "code": "603156",
        "code_full": "603156.SH",
        "name": "养元饮品",
        "source_date": "2026/03/12",
        "highlights_count": 7,
        "market_cap": 445.004,
        "pe": 8.4,
        "risks_count": 1,
        "rps20": 74.45,
        "rps60": 92.81,
        "rps120": 91.5,
        "rps250": 85.17,
        "ma10": 40.17,
        "vcp_quality": null,
        "ma5": 35.76,
        "ma20": 42.9,
        "dist_ma5_pct": -2.2,
        "dist_ma10_pct": -12.9,
        "dist_ma20_pct": -18.5
      },
      {
        "code": "300684",
        "code_full": "300684.SZ",
        "name": "中石科技",
        "source_date": "2026/03/12",
        "highlights_count": 5,
        "market_cap": 144.5132,
        "pe": 8.5,
        "risks_count": 2,
        "rps20": 92.64,
        "rps60": 87.57,
        "rps120": 91.2,
        "rps250": 94.49,
        "ma10": 59.16,
        "vcp_quality": null,
        "ma5": 50.36,
        "ma20": 61.2,
        "dist_ma5_pct": -4.2,
        "dist_ma10_pct": -18.4,
        "dist_ma20_pct": -21.2
      },
      {
        "code": "300747",
        "code_full": "300747.SZ",
        "name": "锐科激光",
        "source_date": "2026/07/22",
        "highlights_count": 5,
        "market_cap": 191.5618,
        "pe": 8.0,
        "risks_count": 1,
        "rps20": 49.08,
        "rps60": 89.49,
        "rps120": 91.08,
        "rps250": 89.87,
        "ma10": 34.94,
        "vcp_quality": null,
        "ma5": 32.73,
        "ma20": 41.7,
        "dist_ma5_pct": 4.2,
        "dist_ma10_pct": -2.4,
        "dist_ma20_pct": -18.2
      },
      {
        "code": "603127",
        "code_full": "603127.SH",
        "name": "昭衍新药",
        "source_date": "2026/07/08",
        "highlights_count": 6,
        "market_cap": 363.359,
        "pe": 8.9,
        "risks_count": 3,
        "rps20": 98.55,
        "rps60": 91.48,
        "rps120": 91.04,
        "rps250": 95.99,
        "ma10": 46.79,
        "vcp_quality": null,
        "ma5": 49.07,
        "ma20": 42.48,
        "dist_ma5_pct": -2.1,
        "dist_ma10_pct": 2.7,
        "dist_ma20_pct": 13.1
      },
      {
        "code": "688046",
        "code_full": "688046.SH",
        "name": "药康生物",
        "source_date": "2026/07/22",
        "highlights_count": 4,
        "market_cap": 110.208,
        "pe": 4.2,
        "risks_count": 1,
        "rps20": 98.65,
        "rps60": 94.58,
        "rps120": 90.72,
        "rps250": 92.36,
        "ma10": 25.28,
        "vcp_quality": null,
        "ma5": 25.22,
        "ma20": 23.38,
        "dist_ma5_pct": 7.0,
        "dist_ma10_pct": 6.8,
        "dist_ma20_pct": 15.5
      },
      {
        "code": "600428",
        "code_full": "600428.SH",
        "name": "中远海特",
        "source_date": "2026/07/13",
        "highlights_count": 5,
        "market_cap": 302.9288,
        "pe": 24.2,
        "risks_count": 0,
        "rps20": 98.79,
        "rps60": 92.97,
        "rps120": 90.66,
        "rps250": 86.41,
        "ma10": 10.52,
        "vcp_quality": null,
        "ma5": 10.96,
        "ma20": 9.38,
        "dist_ma5_pct": 0.7,
        "dist_ma10_pct": 4.9,
        "dist_ma20_pct": 17.7
      },
      {
        "code": "002975",
        "code_full": "002975.SZ",
        "name": "博杰股份",
        "source_date": "2026/06/16",
        "highlights_count": 5,
        "market_cap": 180.8656,
        "pe": 6.4,
        "risks_count": 1,
        "rps20": 42.16,
        "rps60": 92.93,
        "rps120": 90.26,
        "rps250": 97.16,
        "ma10": 101.19,
        "vcp_quality": null,
        "ma5": 86.45,
        "ma20": 116.42,
        "dist_ma5_pct": 0.5,
        "dist_ma10_pct": -14.1,
        "dist_ma20_pct": -25.4
      },
      {
        "code": "688222",
        "code_full": "688222.SH",
        "name": "成都先导",
        "source_date": "2026/07/09",
        "highlights_count": 4,
        "market_cap": 113.3924,
        "pe": 6.2,
        "risks_count": 0,
        "rps20": 96.28,
        "rps60": 85.34,
        "rps120": 89.99,
        "rps250": 91.92,
        "ma10": 32.56,
        "vcp_quality": null,
        "ma5": 29.65,
        "ma20": 31.35,
        "dist_ma5_pct": -4.9,
        "dist_ma10_pct": -13.4,
        "dist_ma20_pct": -10.0
      },
      {
        "code": "002192",
        "code_full": "002192.SZ",
        "name": "融捷股份",
        "source_date": "2026/07/20",
        "highlights_count": 5,
        "market_cap": 166.9583,
        "pe": 18.6,
        "risks_count": 5,
        "rps20": 35.26,
        "rps60": 92.31,
        "rps120": 89.13,
        "rps250": 93.82,
        "ma10": 64.74,
        "vcp_quality": null,
        "ma5": 60.26,
        "ma20": 77.92,
        "dist_ma5_pct": 6.7,
        "dist_ma10_pct": -0.7,
        "dist_ma20_pct": -17.5
      },
      {
        "code": "300438",
        "code_full": "300438.SZ",
        "name": "鹏辉能源",
        "source_date": "2026/04/14",
        "highlights_count": 5,
        "market_cap": 304.2207,
        "pe": 11.2,
        "risks_count": 2,
        "rps20": 38.68,
        "rps60": 93.57,
        "rps120": 85.81,
        "rps250": 95.24,
        "ma10": 63.33,
        "vcp_quality": null,
        "ma5": 59.71,
        "ma20": 71.37,
        "dist_ma5_pct": 1.2,
        "dist_ma10_pct": -4.6,
        "dist_ma20_pct": -15.3
      },
      {
        "code": "300475",
        "code_full": "300475.SZ",
        "name": "香农芯创",
        "source_date": "2026/07/22",
        "highlights_count": 5,
        "market_cap": 765.447,
        "pe": 11.1,
        "risks_count": 2,
        "rps20": 96.54,
        "rps60": 94.56,
        "rps120": 85.75,
        "rps250": 99.53,
        "ma10": 198.54,
        "vcp_quality": null,
        "ma5": 166.88,
        "ma20": 238.15,
        "dist_ma5_pct": -2.3,
        "dist_ma10_pct": -17.9,
        "dist_ma20_pct": -31.5
      },
      {
        "code": "301345",
        "code_full": "301345.SZ",
        "name": "涛涛车业",
        "source_date": "2026/07/09",
        "highlights_count": 7,
        "market_cap": 257.3449,
        "pe": 3.3,
        "risks_count": 1,
        "rps20": 97.08,
        "rps60": 89.09,
        "rps120": 85.71,
        "rps250": 97.93,
        "ma10": 251.59,
        "vcp_quality": null,
        "ma5": 242.83,
        "ma20": 240.79,
        "dist_ma5_pct": -2.8,
        "dist_ma10_pct": -6.2,
        "dist_ma20_pct": -2.0
      },
      {
        "code": "300037",
        "code_full": "300037.SZ",
        "name": "新宙邦",
        "source_date": "2026/03/12",
        "highlights_count": 7,
        "market_cap": 462.8863,
        "pe": 16.5,
        "risks_count": 1,
        "rps20": 72.6,
        "rps60": 92.73,
        "rps120": 85.22,
        "rps250": 91.68,
        "ma10": 64.6,
        "vcp_quality": null,
        "ma5": 60.07,
        "ma20": 76.48,
        "dist_ma5_pct": 2.2,
        "dist_ma10_pct": -5.0,
        "dist_ma20_pct": -19.7
      }
    ]
  },
  "enriched_candidates": [
    {
      "code": "002980.SZ",
      "fetch_time": "2026-07-24T11:40:45+0800",
      "name": "华盛昌",
      "pe": 198.6403,
      "pb": 13.6627,
      "ps_ttm": 19.8422,
      "pcf_ttm": null,
      "valuation_percentile": 96.45,
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
        "光模块(CPO)指数",
        "光通信指数",
        "光伏指数",
        "智能体指数",
        "触板指数",
        "核废水指数",
        "抗核辐射指数"
      ],
      "score_company": 7.6,
      "score_trend": 7.2,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 电工仪器仪表 行业龙头企业。"
        },
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
          "tag": "波动",
          "text": "近5天，日均换手率 11% ，短线资金追逐，波动风险较高。"
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
          "content": "22:17 爱丽家居公告称，拟以自有及自筹资金收购欧康诺不低于77.08%股权，整体估值不超过6.5亿元。同时，控股股东博华企管拟向欧康诺实控人赵铭及其一致行动人转让20%上市公司股份。欧康诺主营存储测试设备，2025年净利润610.68万元，2026年上半年净利润为3719.67万元。交易双方约定四年业绩承诺期（2026-2029年），扣非净利润累计不低于2.3亿元。\n本次转让的20%股份中，15%锁定36个月，5%与业绩承诺挂钩。若未达业绩承诺或发生减值，该5%股份将用于抵扣补偿义务。法律人士指出，仅5%股权用于业绩补偿比例偏低，建议公司披露分层转让的商业逻辑及风险约束措施。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "16:06 华盛昌发布2026年半年度业绩预告，预计上半年归母净利润为7000万元至8000万元，同比增长61.02%至84.02%。公司表示，业绩增长主要系全资子公司伽蓝特并表所致。华盛昌于4月17日签署协议，以4.6亿元现金收购伽蓝特100%股权，并于5月23日完成工商变更。伽蓝特主营光通信测试设备，客户包括华为、中兴、Lumentum及Intel等。\n华盛昌2025年经营活动现金流量净额同比下降73.39%，并以伽蓝特股权质押获取3.22亿元长期并购贷款。该收购交易作价约14倍PE，并设有三年累计净利润不低于1.15亿元的对赌协议。伽蓝特6月实现净利润2500万元至2900万元。分析人士指出，华盛昌通过收购切入光模块测试领域，旨在补齐高端光电测试短板，但需关注企业文化、研发体系及供应链整合风险，且双方在前端获客逻辑上存在差异。\n市场关注华盛昌在光通信测试及MLCC检测领域的布局。多位受访者认为，MLCC检测在公司营收中占比微乎其微，难以对整体业绩形成实质拉动，市场对MLCC的关注更多源于产业链情绪传导。华盛昌专业测试仪器业务在2025年上半年收入占比为11.6%，MLCC检测占比更低。当前市场对MLCC需求呈现结构性分化，高端AI服务器及工业规格产品需求紧张。",
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
      "valuation_history_days": 259,
      "valuation_history_from": "20220418",
      "current_price": 84.59,
      "price": 84.59,
      "ma5": 89.61,
      "ma10": 93.96,
      "ma20": 102.84,
      "dist_ma5_pct": -5.6,
      "dist_ma10_pct": -10.0,
      "dist_ma20_pct": -17.7,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6814,
        "sizing": "selective"
      }
    },
    {
      "code": "301396.SZ",
      "fetch_time": "2026-07-24T11:40:45+0800",
      "name": "宏景科技",
      "pe": 1095.887,
      "pb": 31.8143,
      "ps_ttm": 31.8482,
      "pcf_ttm": 18.0395,
      "valuation_percentile": 92.07,
      "total_shares": 214924565,
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
        "科技龙头指数",
        "专精特新小巨人主题指数",
        "QFII重仓指数",
        "专精特新小巨人指数",
        "AI算力指数",
        "高应收账款指数"
      ],
      "score_company": 6.8,
      "score_trend": 6.2,
      "score_value": 3.9,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 IT服务Ⅲ 行业龙头企业。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 119% ，销售收入现金含量很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 12% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 7.3% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "偿债",
          "text": "带息债务占全部投入资本 83% ，偿债压力很大。"
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
          "content": "00:34 大位科技发布公告回复上交所2025年年报问询函。公司2025年实现营业收入4.36亿元，同比增长7.59%，但扣非前后净利润均亏损。回复函指出，公司IDC业务毛利率有所修复，但算力与云服务毛利率大幅下滑，且整体毛利率落后于同行；公司目前尚不具备独立开展大规模、高标准AIDC业务的完整能力。针对2024年签署的定制化数据中心采购框架协议，2025年仅确认收入207.12万元，公司解释称该项目为“先签后建”，建设周期约一年，交付及调试后于2025年11月开始计费，截至2025年末客户上架率为7.39%。2026年上半年该项目上架率呈逐月提升趋势。\n大位科技在回复中坦言，在超高密度算力机房配套、大规模RDMA高速网络、规模化液冷技术、AI算力软件体系及重资产投入等AIDC核心要素方面存在阶段性短板。2025年，公司算力与云服务毛利率从2024年的28.36%降至12.83%。公司将毛利率下降归因于中低端算力赛道竞争加剧、产品同质化、高端算力产品占比低、设备租赁模式成本较高以及规模效应不足导致固定成本难以分摊。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:32 7月20日早盘，算力租赁概念股表现活跃。其中，利通电子实现涨停，行云科技、亚康股份涨幅超过10%，宏景科技、浙数文化、润泽科技等个股跟涨。\n\n消息面上，月之暗面Kimi于7月19日发布通知，决定即日起暂停C端新用户订阅，将现有算力资源优先保障已订阅用户权益。目前，公司正全速推进算力扩容，待新算力到位后，将逐步恢复订阅名额直至全面开放。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "宏景科技：关于与关联方共同投资设立合资公司暨关联交易的公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1550970081.55,
      "revenue_yoy": 5.954852,
      "operating_profit": 124376827.05,
      "operating_profit_yoy": 4.042172,
      "net_profit": 107989973.3,
      "net_profit_yoy": 4.46188,
      "gross_profit": 236497172.99,
      "gross_profit_yoy": 4.070431,
      "cogs": 1314472908.56,
      "gross_margin": 15.25,
      "pe_forward": null,
      "valuation_history_days": 410,
      "valuation_history_from": "20241111",
      "current_price": 191.0,
      "price": 191.0,
      "ma5": 199.24,
      "ma10": 219.58,
      "ma20": 255.37,
      "dist_ma5_pct": -4.1,
      "dist_ma10_pct": -13.0,
      "dist_ma20_pct": -25.2,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 15.8,
        "pct_float": 5.85,
        "chg5_pct": -0.49,
        "net5_repay_days": 3,
        "signal": "neutral"
      }
    },
    {
      "code": "688630.SH",
      "fetch_time": "2026-07-24T11:40:45+0800",
      "name": "芯碁微装",
      "pe": 171.2783,
      "pb": 10.8245,
      "ps_ttm": 35.3093,
      "pcf_ttm": 206.2299,
      "valuation_percentile": 94.63,
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
        "专精特新小巨人主题指数",
        "半导体产业指数",
        "股权激励指数",
        "专精特新小巨人指数",
        "万得预增指数",
        "半导体设备指数",
        "光刻机指数",
        "专用设备精选指数"
      ],
      "score_company": 9.1,
      "score_trend": 7.7,
      "score_value": 3.7,
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
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
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
          "content": "08:45 深交所公告，港股通标的证券名单发生调整并自2026年7月24日起生效，调入禾赛-W（新）、圣邦股份、芯碁微装。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "20:32 国金证券李阳团队认为，CoWoS-L架构因具备无掩模缝合和良率优势，有望成为先进封装主流工艺。台积电预计到2026年底CoWoS-L占2.5D封装产能超50%，2027年将达70%。芯碁微装的先进封装直写光刻设备已导入长电、通富、甬矽等国内头部封测厂。预计全球先进封装直写光刻设备市场规模将从2024年的2亿元增长至2030年的31亿元。\n需求端数据显示国产算力景气度高：国内头部模型日均Token消耗量呈指数级增长，国产大模型绑定国产GPU芯片，寒武纪26Q1期末预付款同比大幅增长。封测行业出现“AI挤占”现象，AI相关需求高速增长，日月光等厂商上调先进封装报价。国内主流封测企业稼动率回升，长电科技、通富微电、甬矽电子、汇成股份、盛合晶微等企业积极扩产。\nCoWoS-L封装由top die、重组插层和基板组成，通过模塑化合物包围的TIV提供垂直路径。芯碁微装设备主要应用于中介层曝光。国产算力需求强劲，豆包全系产品日均Token消耗量增长显著，寒武纪预付款大幅增加。封测行业结构性分化明显，AI相关需求旺盛，国内封测企业订单预期乐观。\n受原料成本上涨及供给紧俏影响，日月光上调CoWoS、FoCoS等先进封装报价。国内5家主流上市封测企业2025年营收平均增速21%，26Q1增速19%，归母净利增速明显。长电科技、通富微电、甬矽电子、汇成股份、盛合晶微等公司均有高端先进封测产能扩产计划。\nCoWoS工艺路线迭代主要体现在中介层，包括CoWoS、CoWoS-R和CoWoS-L。CoWoS技术核心在于硅中介层，其制造流程复杂，涉及TSV形成、绝缘层沉积、阻挡层与种子层沉积、铜电镀填充、CMP平坦化及RDL制作等关键步骤。\n先进封装材料包括光刻胶、电镀液、刻蚀剂、溅射靶材、底部填充等。环氧塑封料（EMC）国产化率较低，高性能EMC国产化率仅10-20%。华海诚科通过收购衡所华威成为国内龙头，联瑞新材为衡所华威主要硅微粉供应商。\n湿电子化学品包括电镀液、蚀刻液、清洗液等。飞凯材料、艾森股份、上海新阳等厂商在先进制程湿电子化学品领域有布局。临时键合胶在晶圆承载系统中起重要作用，飞凯材料、鼎龙股份有相关布局，芯源微提供临时键合、解键合设备。\n江丰电子和有研新材在超高纯金属溅射靶材领域市场份额领先。底部填充胶是保证倒片封装和TSV工艺可靠性的关键，德邦科技提供包括底部填充胶在内的综合封装材料解决方案。\n康强电子引线框架产品产能处于满产状态。新技术方面，CoPoS技术通过大型矩形面板实现“化圆为方”，玻璃基板具备热膨胀系数接近硅、电气绝缘性能优异等优势。碳化硅（SiC）中介层因高热导率，被视为应对AI芯片高功耗散热挑战的潜在方案。\n国金证券提示风险：封装技术存在不确定性，国产替代进度可能不及预期，行业竞争格局可能恶化。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "芯碁微装：港股公告：翌日披露报表",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "芯碁微装：关于悉数行使超额配售权的公告",
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
      "valuation_history_days": 267,
      "valuation_history_from": "20230403",
      "current_price": 401.0,
      "price": 401.0,
      "ma5": 378.45,
      "ma10": 420.68,
      "ma20": 459.07,
      "dist_ma5_pct": 6.0,
      "dist_ma10_pct": -4.7,
      "dist_ma20_pct": -12.6,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.68,
        "pct_float": 1.91,
        "chg5_pct": 0.75,
        "net5_repay_days": 3,
        "signal": "neutral"
      }
    },
    {
      "code": "605376.SH",
      "fetch_time": "2026-07-24T11:40:45+0800",
      "name": "博迁新材",
      "pe": 151.1554,
      "pb": 21.1763,
      "ps_ttm": 27.9964,
      "pcf_ttm": 6446.3862,
      "valuation_percentile": 92.1,
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
      "score_company": 8.4,
      "score_trend": 6.8,
      "score_value": 3.8,
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
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
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
      "valuation_history_days": 291,
      "valuation_history_from": "20221209",
      "current_price": 145.02,
      "price": 145.02,
      "ma5": 148.57,
      "ma10": 174.93,
      "ma20": 209.06,
      "dist_ma5_pct": -2.4,
      "dist_ma10_pct": -17.1,
      "dist_ma20_pct": -30.6,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.4995,
        "sizing": "normal"
      },
      "margin": {
        "rzye_yi": 7.66,
        "pct_float": 2.0,
        "chg5_pct": -13.83,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "000811.SZ",
      "fetch_time": "2026-07-24T11:40:45+0800",
      "name": "冰轮环境",
      "pe": 69.5563,
      "pb": 6.3558,
      "ps_ttm": 5.5989,
      "pcf_ttm": 51.0623,
      "valuation_percentile": 99.09,
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
        "能源出海指数",
        "氢能指数",
        "山东省国资指数",
        "空气能热泵指数",
        "燃料电池指数",
        "集装箱指数",
        "新能源设备指数",
        "通用机械精选指数",
        "仪器仪表精选指数",
        "冬奥会指数",
        "冷链物流指数",
        "地热指数",
        "地热能指数",
        "余热利用指数",
        "核电通风与空气处理指数",
        "核电阀门指数"
      ],
      "score_company": 9.0,
      "score_trend": 8.1,
      "score_value": 3.4,
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
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 4.2% ，很受外资机构青睐；公募基金持股 11% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月13日大跌 -10% ，股价跌停，抛压很重。"
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
        },
        {
          "content": "冰轮环境：关于收购控股子公司北京华源泰盟节能设备有限公司少数股权涉及关联交易的公告",
          "tags": [
            "重要公告"
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
      "valuation_history_from": "20210726",
      "current_price": 42.85,
      "price": 42.85,
      "ma5": 42.67,
      "ma10": 46.69,
      "ma20": 50.3,
      "dist_ma5_pct": 0.4,
      "dist_ma10_pct": -8.2,
      "dist_ma20_pct": -14.8,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.5775,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 7.69,
        "pct_float": 1.83,
        "chg5_pct": 13.5,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "301362.SZ",
      "fetch_time": "2026-07-24T11:40:45+0800",
      "name": "民爆光电",
      "pe": 114.5864,
      "pb": 6.9814,
      "ps_ttm": 10.1145,
      "pcf_ttm": 80.7459,
      "valuation_percentile": 92.74,
      "total_shares": 145944676,
      "industries": [
        {
          "name": "家用电器",
          "level": 1
        },
        {
          "name": "照明设备Ⅱ",
          "level": 2
        },
        {
          "name": "照明设备Ⅲ",
          "level": 3
        }
      ],
      "concepts": [
        "专精特新小巨人主题指数",
        "QFII重仓指数",
        "专精特新小巨人指数",
        "AI算力指数",
        "LED照明指数",
        "高频PCB指数"
      ],
      "score_company": 7.8,
      "score_trend": 6.8,
      "score_value": 3.8,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 照明设备Ⅲ 行业龙头企业。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 114% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 5.7% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 3.2% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "波动",
          "text": "2026年07月14日，换手率 21% ，短线资金追逐，波动风险较高。"
        }
      ],
      "events": [
        {
          "content": "2027/02/04解禁1.05亿股，占总股本71.95%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2027-02-04"
        },
        {
          "content": "预计2026/08/25发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-25"
        },
        {
          "content": "民爆光电：中信证券股份有限公司关于深圳民爆光电股份有限公司发行股份购买资产暨关联交易之独立财务顾问报告（修订稿）",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "民爆光电：中信证券股份有限公司关于深圳民爆光电股份有限公司本次交易符合“小额快速”审核条件的专项核查意见",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1230420066.15,
      "revenue_yoy": -0.000409,
      "operating_profit": 164808152.79,
      "operating_profit_yoy": -0.206349,
      "net_profit": 147935759.82,
      "net_profit_yoy": -0.199203,
      "gross_profit": 349684411.27,
      "gross_profit_yoy": -0.084385,
      "cogs": 880735654.88,
      "gross_margin": 28.42,
      "pe_forward": null,
      "valuation_history_days": 224,
      "valuation_history_from": "20250804",
      "current_price": 116.66,
      "price": 116.66,
      "ma5": 116.34,
      "ma10": 130.13,
      "ma20": 153.24,
      "dist_ma5_pct": 0.3,
      "dist_ma10_pct": -10.4,
      "dist_ma20_pct": -23.9,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 2.23,
        "pct_float": 4.68,
        "chg5_pct": -19.37,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688257.SH",
      "fetch_time": "2026-07-24T11:40:45+0800",
      "name": "新锐股份",
      "pe": 41.9742,
      "pb": 7.8795,
      "ps_ttm": 6.7037,
      "pcf_ttm": 67.7863,
      "valuation_percentile": 91.6,
      "total_shares": 355263279,
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
        "股权激励指数",
        "专精特新小巨人指数",
        "有色金属指数",
        "万得预增指数",
        "IPO现场检查指数",
        "通用机械精选指数",
        "仪器仪表精选指数",
        "苏州工业园区指数"
      ],
      "score_company": 8.2,
      "score_trend": 7.1,
      "score_value": 3.9,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月14日，业绩超预期引发股价大幅上涨，当日收涨 12.5% 。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 36% ，最新季度归母净利润同比增长 390% ，成长能力很强。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 5.9% ，很受内资机构青睐。"
        },
        {
          "tag": "增持",
          "text": "近1月，控股股东和管理层累计实际增持 57万股 ，占总股本比例 0.16% ，金额合计 304万元 。"
        }
      ],
      "risks": [
        {
          "tag": "商誉",
          "text": "商誉占净资产 12% ，商誉减值风险较高。"
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
          "content": "新锐股份：新锐股份关于2026年度向特定对象发行A股股票申请获得中国证券监督管理委员会同意注册批复的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "16:20 新锐股份发布公告称，公司已收到中国证监会下发的《关于同意苏州新锐合金工具股份有限公司向特定对象发行股票注册的批复》，其向特定对象发行股票的注册申请已获得正式批准。\n\n根据公告，该批复自同意注册之日起12个月内有效。公司董事会将按照相关规定推进后续发行事宜，并依法履行信息披露义务。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是公司披露并购重组进展且预计2026年上半年归母净利5.30-6.30亿元，同比大增约425%-524%，显示并购将显著提升硬质合金工具业务盈利",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价盘中上涨 8.23% ，股价收盘涨幅 12.54%",
          "tags": [
            "股价上涨"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1788509874.88,
      "revenue_yoy": 0.321076,
      "operating_profit": 224896823.51,
      "operating_profit_yoy": 0.209725,
      "net_profit": 189797978.29,
      "net_profit_yoy": 0.219395,
      "gross_profit": 578949940.54,
      "gross_profit_yoy": 0.348258,
      "cogs": 1209559934.34,
      "gross_margin": 32.37,
      "pe_forward": null,
      "valuation_history_days": 330,
      "valuation_history_from": "20231030",
      "current_price": 61.4,
      "price": 61.4,
      "ma5": 66.26,
      "ma10": 76.13,
      "ma20": 89.99,
      "dist_ma5_pct": -7.3,
      "dist_ma10_pct": -19.4,
      "dist_ma20_pct": -31.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 13.58,
        "pct_float": 6.3,
        "chg5_pct": -8.01,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300503.SZ",
      "fetch_time": "2026-07-24T11:40:45+0800",
      "name": "昊志机电",
      "pe": 69.6492,
      "pb": 12.6539,
      "ps_ttm": 9.7547,
      "pcf_ttm": 130.7368,
      "valuation_percentile": 84.71,
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
        "具身智能指数",
        "股权激励指数",
        "人形机器人指数",
        "工业4.0指数",
        "预期提升指数",
        "富士康产业链指数",
        "新型工业化指数",
        "通用机械精选指数",
        "仪器仪表精选指数",
        "3D玻璃指数",
        "减速器指数",
        "工业母机指数"
      ],
      "score_company": 7.7,
      "score_trend": 7.5,
      "score_value": 4.1,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月21日，业绩超预期引发股价大幅上涨，当日收涨 13.3% 。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 24% ，最新季度归母净利润同比增长 196% ，成长能力很强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 4.3% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 2073万元 ，较上期增长 61% ，占2025年营收 1.3% ，在手订单充足。"
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
          "tag": "波动",
          "text": "2026年07月07日，换手率 20% ，短线资金追逐，波动风险较高。"
        }
      ],
      "events": [
        {
          "content": "06:30 昊志机电主营业务涵盖电主轴、转台、直线电机、谐波减速器、伺服电机及数控系统等，产品应用于数控机床、机器人、新能源汽车燃料电池及商业航天等领域。2026年上半年，公司实现营收11.66亿元，同比增长65.86%；归母净利润2.32亿元，同比增长266.57%；毛利率由35.84%提升至42.45%，ROE由5.13%增至15.55%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是公司主营（主轴、转台、减速器、运动控制器等）产品销售驱动营业收入同比大增65.86%，归母净利润同比暴增266.57%，且Q2环比增长55%，业绩超预期。",
          "tags": [
            "快讯",
            "大涨原因"
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
      "valuation_history_from": "20210726",
      "current_price": 67.89,
      "price": 67.89,
      "ma5": 69.25,
      "ma10": 77.09,
      "ma20": 85.52,
      "dist_ma5_pct": -2.0,
      "dist_ma10_pct": -11.9,
      "dist_ma20_pct": -20.6,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 8.89,
        "pct_float": 5.43,
        "chg5_pct": -5.82,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300285.SZ",
      "fetch_time": "2026-07-24T11:40:48+0800",
      "name": "国瓷材料",
      "pe": 92.5751,
      "pb": 8.0302,
      "ps_ttm": 12.2231,
      "pcf_ttm": 64.7807,
      "valuation_percentile": 80.01,
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
        "科技龙头指数",
        "三新指数",
        "双创100指数",
        "贷款回购指数",
        "资源股",
        "员工持股指数",
        "QFII重仓指数",
        "新材料指数",
        "有色金属指数",
        "高瓴资本指数",
        "对日反制指数",
        "MLCC指数",
        "手机外壳指数",
        "手机陶瓷外壳指数",
        "碳纳米管指数",
        "锆产业指数",
        "尾气治理指数"
      ],
      "score_company": 8.3,
      "score_trend": 7.5,
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
          "text": "近90天， 16家 机构给出评级，其中 69% 为“买入”，距目标价的上涨空间为 38% 。"
        },
        {
          "tag": "预测",
          "text": " 13家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
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
          "text": "近3天，日均换手率 16% ，短线资金追逐，波动风险较高。"
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
          "content": "02:56 近期MLCC产业链调研显示，供需格局偏紧，主力企业产线满载，出厂价保持稳定。上游材料商订单充沛，部分企业扩产线已被客户提前锁定。离型膜、陶瓷粉及金属粉等主要原材料厂商产线开满，部分企业实行三班倒生产。受AI服务器等新兴应用需求带动，MLCC用量显著增加，相关材料出货量持续攀升。\n国瓷材料因原辅材料价格上涨，自7月27日起上调氧化锆粉体销售价格，涨幅约10%—40%。国内MLCC企业如三环集团表示，今年二季度起产品价格上调后未回调。三环集团预计2026年上半年盈利同比增长45%—65%，增长得益于行业景气度提升及产品价格修复。业内指出，AI服务器对高容MLCC需求形成虹吸效应，导致日韩厂商转产高容产品，推动行业涨价。\n业内人士认为，AI服务器带来的爆发式增量需求正推动MLCC进入新一轮景气周期。机构数据显示，AI服务器对MLCC的消耗量远高于手机和汽车。中商产业研究院预测，受新能源汽车、AI服务器及5G通信等需求拉动，全球MLCC市场规模至2030年将持续增长。上游原料厂商正竞相扩产，部分企业已与村田、三星电机等签署战略协议，新增产能获提前锁单。\n洁美科技正加速推进广东肇庆及天津基地离型膜产线建设，预计2026年底产能将达7.4亿平方米，并已启动安吉基地高端产品扩产计划。博迁新材拟投资约2.02亿元建设超细金属粉体材料扩产项目，以满足MLCC小型化、高容值需求。业内分析认为，本轮景气周期为国产MLCC产业链提供了国产替代机遇，随着产能落地，本土企业市场份额有望提升。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "17:02 7月21日，市场探底回升，创业板指涨超7%，科创50指数涨10.73%。沪深两市成交额2.96万亿元，较前一交易日放量2550亿元。盘面热点轮动，全市场超3100只个股上涨。芯片产业链爆发，雅克科技、亚翔集成、东微半导、北方华创、臻宝科技、新洁能、金海通等涨停。PCB概念走强，宏和科技、金禄电子、广合科技涨停。CPO概念震荡走高，光迅科技涨停，中际旭创涨超13%。算力租赁概念中嘉博创、利通电子涨停。氧化锆概念东方锆业、国瓷材料、三祥新材涨停。油气概念调整。截至收盘，沪指涨1.79%，深成指涨4.81%，创业板指涨7.05%。芯片产业链中，半导体设备领涨，长川科技、北方华创、拓荆科技、华海清科、芯源微等涨停。据全球半导体行业协会（SEMI）报告，预计2026年全球半导体设备销售额将增长23.2%至1659亿美元，2028年将达2295亿美元。PCB、CPO等算力硬件股走高，联特科技、中富电路、金禄电子、生益科技、广合科技等涨停。新易盛在电话会议中表示，1.6T光模块Q2出货量较Q1增长，预计Q3/Q4放量节奏加快。瑞银证券指出，科技板块交易拥挤度缓解后，科技与AI仍是下半年市场主线。\n个股方面，科技赛道全线反弹。半导体方向，兆易创新涨停，雅克科技、华虹宏力、长电科技、通富微电、长川科技等涨停，中芯国际、澜起科技、佰维存储等涨超10%。算力硬件方面，中际旭创涨超13%，生益科技、宏和科技、广合科技等涨停。算力租赁概念中嘉博创、美利云2连板。紫光股份涨停，共进股份录得3天2板。MLCC概念国瓷材料20CM涨停，三环集团涨超18%。后市方面，双创板块放量长阳站稳5日均线，短线止跌企稳。市场要闻方面，腾讯云表示将大规模部署国产化算力，预计2026年Q4部署NPO超级节点。国家药监局批准一款新靶点创新药上市，用于治疗1型发作性睡病。",
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
      "valuation_history_from": "20210726",
      "current_price": 60.85,
      "price": 60.85,
      "ma5": 57.5,
      "ma10": 63.29,
      "ma20": 79.39,
      "dist_ma5_pct": 5.8,
      "dist_ma10_pct": -3.9,
      "dist_ma20_pct": -23.4,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 32.08,
        "pct_float": 6.18,
        "chg5_pct": 5.46,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "688300.SH",
      "fetch_time": "2026-07-24T11:40:48+0800",
      "name": "联瑞新材",
      "pe": 98.6943,
      "pb": 17.9529,
      "ps_ttm": 25.3943,
      "pcf_ttm": 127.7143,
      "valuation_percentile": 97.43,
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
      "score_company": 8.5,
      "score_trend": 6.2,
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
          "tag": "预测",
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
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
        },
        {
          "content": "09:41 7月9日，先进封装概念股表现活跃。朗迪集团、同兴达、三佳科技、中京电子等个股涨停，太极实业、联瑞新材、雅克科技、华海诚科等个股跟涨。\n\n市场分析认为，随着科技巨头加大对AI芯片的自研力度，AI算力需求正由通用GPU向专用ASIC领域扩展。在此背景下，芯片设计、先进制程代工以及封装测试等产业链环节有望获得发展机遇。",
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
      "valuation_history_days": 284,
      "valuation_history_from": "20211115",
      "current_price": 128.32,
      "price": 128.32,
      "ma5": 136.96,
      "ma10": 158.64,
      "ma20": 197.91,
      "dist_ma5_pct": -6.3,
      "dist_ma10_pct": -19.1,
      "dist_ma20_pct": -35.2,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.29,
        "pct_float": 2.7,
        "chg5_pct": -10.75,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "001389.SZ",
      "fetch_time": "2026-07-24T11:40:48+0800",
      "name": "广合科技",
      "pe": 65.277,
      "pb": 11.0285,
      "ps_ttm": 12.1358,
      "pcf_ttm": 66.8316,
      "valuation_percentile": 86.55,
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
        "电路板指数",
        "元件精选指数",
        "可转债预案指数",
        "高频PCB指数"
      ],
      "score_company": 8.9,
      "score_trend": 7.9,
      "score_value": 4.2,
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
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 40% ，未来成长很快。"
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
          "content": "02:45 7月以来，共有375家A股上市公司获机构调研，其中新易盛、京东方A、华灿光电、华勤技术等22家公司获50家以上机构调研。新易盛获417家机构调研居首，公司称二季度业绩预告与年初预期基本吻合。京东方A获243家机构调研，公司表示未来折旧金额及资本开支预计将逐渐下降。在已发布半年度业绩相关公告的调研公司中，超七成实现业绩报喜，恒逸石化、三维通信、凯尔达预计净利润同比增长超1000%。分行业看，获调研且业绩预喜的公司中，电子行业数量居首，电力设备、基础化工及有色金属行业紧随其后。\n研究机构Omdia数据显示，2026年中国半导体市场规模预测值上调。在上述375家获调研公司中，67家获外资机构调研，其中电子行业公司有19家。广合科技、沪电股份、华勤技术等电子行业公司获外资机构调研较多。调研内容显示，外资机构关注相关公司的全球化布局，广合科技泰国工厂正推进产能爬坡，沪电股份泰国基地已进入规模化运营阶段。",
          "tags": [
            "资讯"
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
      "valuation_history_days": 74,
      "valuation_history_from": "20260403",
      "current_price": 160.5,
      "price": 160.5,
      "ma5": 167.23,
      "ma10": 176.79,
      "ma20": 190.27,
      "dist_ma5_pct": -4.0,
      "dist_ma10_pct": -9.2,
      "dist_ma20_pct": -15.6,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.5775,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 13.02,
        "pct_float": 5.32,
        "chg5_pct": -4.51,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "600869.SH",
      "fetch_time": "2026-07-24T11:40:48+0800",
      "name": "远东股份",
      "pe": 297.75,
      "pb": 7.623,
      "ps_ttm": 1.1424,
      "pcf_ttm": 34.4518,
      "valuation_percentile": 89.73,
      "total_shares": 2219352746,
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
          "name": "线缆部件及其他",
          "level": 3
        }
      ],
      "concepts": [
        "贷款回购指数",
        "碳中和指数",
        "锂电池指数",
        "光通信指数",
        "数字能源指数",
        "宁德时代产业链指数",
        "智慧城市指数",
        "电动物流车指数",
        "触板指数",
        "特高压指数",
        "智能电网指数",
        "高低压设备精选指数",
        "电气自动化设备精选指数",
        "虚拟电厂指数",
        "三元锂电池指数",
        "电线电缆指数",
        "光纤指数",
        "泛在电力物联网指数",
        "碳纤维指数"
      ],
      "score_company": 7.1,
      "score_trend": 6.0,
      "score_value": 3.9,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 线缆部件及其他 行业龙头企业。"
        },
        {
          "tag": "业绩",
          "text": "2026年04月22日，业绩超预期引发股价大幅上涨，当日收涨 9.99% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 110% ，利润成长性强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 6.4% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 15亿元 ，较上期增长 30% ，占2025年营收 5.3% ，在手订单充足。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 4.0% ，较受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月20日大跌 -10% ，股价跌停，抛压很重。"
        },
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 20% ，收益质量较低。"
        },
        {
          "tag": "商誉",
          "text": "商誉占净资产 14% ，商誉减值风险较高。"
        },
        {
          "tag": "偿债",
          "text": "带息债务占全部投入资本 64% ，偿债压力很大。"
        },
        {
          "tag": "质押",
          "text": "大股东质押数占持股数 80% ，若股价下跌，被动减持风险很高。"
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
          "content": "02:46 长飞光纤执行董事兼总裁庄丹表示，AI算力增长驱动通信网络升级，光纤光缆需求进入增长周期，预计未来一两年保偏光纤需求将有10倍至20倍增长。杭电股份披露再融资预案，拟募资不超过28.8亿元，其中13.81亿元投向光纤预制棒及新型光纤项目。多家光纤光缆行业公司发布上半年业绩预增公告，长飞光纤、亨通光电、中天科技预计归母净利润均实现增长。\n烽火通信拟投资9.4亿元建设多模和特种光纤产业智能制造工厂。由于光棒产能紧缺，亨通光电、烽火通信、远东股份、通鼎互联、合盛硅业、大族激光等公司启动光棒扩产计划。其中，亨通光电内蒙古基地光棒扩产预计今年底或明年一季度投产；烽火通信拟投超10亿元建设光纤预制棒项目；杭电股份拟建年产1200吨光纤预制棒项目；大族激光拟投资25.2亿元建设光纤及光棒项目；合盛硅业年产3200吨光纤预制棒项目已获备案。\n中信建投研报认为，AI发展拉动光纤需求，行业目前供不应求，多数扩产项目产能释放需待明年下半年或更晚。烽火通信认为，全球光纤光缆需求具有长期增长支撑。长飞光纤方面表示，预计未来3年至5年AI算力基础设施将保持高投入，光纤短缺持续时间取决于供需平衡。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "18:37 科陆电子公告，预计2026年上半年归属于上市公司股东的净利润亏损1.8亿元至2.6亿元，上年同期盈利1.9亿元，同比下降194.70%-236.78%。扣非净利润亏损1.9亿元至2.7亿元，同比下降231.99%-287.57%。营业收入21亿元至23亿元，同比下降约10.6%-18.4%。业绩变动原因：部分海外储能项目因选址变更导致交付延期，叠加南方电网市场禁入处理措施影响，营收同比下滑；行业竞争加剧及磷酸铁锂电芯等原材料价格上涨致毛利率下降；美元及埃及镑汇率下跌产生汇兑损失；光明智慧能源产业园部分资产出售计提减值准备约2500万元；参股子公司车电网经营承压，拟对其股权计提长期股权投资减值准备。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "远东股份：国浩律师（上海）事务所关于远东智慧能源股份有限公司差异化分红事项之专项法律意见书",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 20209305513.55,
      "revenue_yoy": 0.109077,
      "operating_profit": 176730060.06,
      "operating_profit_yoy": 2.252229,
      "net_profit": 158511949,
      "net_profit_yoy": 2.0628,
      "gross_profit": 1839065948.79,
      "gross_profit_yoy": -0.021199,
      "cogs": 18370239564.76,
      "gross_margin": 9.1,
      "pe_forward": null,
      "valuation_history_days": 303,
      "valuation_history_from": "20210726",
      "current_price": 15.61,
      "price": 15.61,
      "ma5": 15.88,
      "ma10": 18.45,
      "ma20": 25.32,
      "dist_ma5_pct": -1.7,
      "dist_ma10_pct": -15.4,
      "dist_ma20_pct": -38.4,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.4995,
        "sizing": "normal"
      },
      "margin": {
        "rzye_yi": 13.79,
        "pct_float": 3.98,
        "chg5_pct": -7.35,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002655.SZ",
      "fetch_time": "2026-07-24T11:40:48+0800",
      "name": "共达电声",
      "pe": 161.0612,
      "pb": 11.157,
      "ps_ttm": 6.4569,
      "pcf_ttm": 190.7334,
      "valuation_percentile": 90.34,
      "total_shares": 364584000,
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
        "消费电子产业指数",
        "华为平台指数",
        "贷款回购指数",
        "QFII重仓指数",
        "AI手机指数",
        "智能家居指数",
        "苹果指数",
        "智能手表指数",
        "小米产业链指数",
        "半导体材料指数",
        "TWS耳机指数",
        "三星指数",
        "直播带货指数",
        "智能音箱指数",
        "网红经济指数",
        "语音识别指数",
        "超硬材料指数"
      ],
      "score_company": 5.6,
      "score_trend": 6.5,
      "score_value": 3.7,
      "highlights": [
        {
          "tag": "收现",
          "text": "近5年，收现比达到 111% ，销售收入现金含量较强。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 4.7% ，较受内资机构青睐。"
        },
        {
          "tag": "增持",
          "text": "近1月，控股股东累计实际增持 753万股 ，占总股本比例 2.1% ，金额合计 2.6亿元 。"
        },
        {
          "tag": "激励",
          "text": "2026年04月28日，公司发布股票激励计划，当日收涨 7.8% 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月17日大跌 -9.99% ，股价跌停，抛压很重。"
        },
        {
          "tag": "估值",
          "text": "最新综合估值高于近十年 90% 的时间，处于历史高位。"
        },
        {
          "tag": "评级",
          "text": "近6月，没有机构发布研究报告，机构关注度低。"
        }
      ],
      "events": [
        {
          "content": "预计2026/08/15发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-15"
        },
        {
          "content": "06:12 截至7月22日，7月以来共有111家A股上市公司披露回购预案，拟回购金额合计约101.8亿元。其中，中远海控、华友钴业、三环集团等公司拟回购金额居前。中远海控拟回购5000万股至1亿股，预计金额7.7亿元至15.4亿元；华友钴业拟回购6亿元至10亿元；三环集团拟回购4.5亿元至9亿元。此外，吉祥航空、上海莱士、世运电路、恒力石化等企业拟回购金额均超1亿元。同期，三峡能源、中国铝业、中国建筑等央企披露增持计划。\n三峡集团计划在未来12个月内增持三峡能源股份，金额不低于15亿元、不高于30亿元。中国铝业控股股东及一致行动人拟增持A股及H股股份，金额10亿元至20亿元，增持比例不超过总股本的2%。中国建筑控股股东中建集团拟增持A股股份，金额5亿元至10亿元。此外，川投能源、潍柴动力、共达电声、赛力斯等企业也披露了增持公告。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/21～2027/01/21 上海韦豪创芯投资管理有限公司(控股股东的一致行动人)计划增持，变动价格说明：不超过35元/股，将根据公司股票价格波动情况及市场整体趋势，择机实施增持计划，拟增持金额不超过 2.50亿元  ，拟增持金额不低于 1.50亿元",
          "tags": [
            "控股股东增持"
          ]
        },
        {
          "content": "截至2026/07/15，上海韦豪创芯投资管理有限公司(控股股东的一致行动人)增持已完成，实际增持累计 753万股 ，按近二十个交易日成交均价 34元/股 ，耗资 2.59亿元 ，此次增持后持股数为2653万股 （该主体计划增持，变动价格说明：本次增持计划不设定价格区间，拟增持金额不超过2.50亿元 )交易方式：集中竞价交易",
          "tags": [
            "控股股东增持"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1040619652.61,
      "revenue_yoy": 0.196422,
      "operating_profit": 84386311.28,
      "operating_profit_yoy": 0.215869,
      "net_profit": 65954038.98,
      "net_profit_yoy": 0.196785,
      "gross_profit": 295388861.64,
      "gross_profit_yoy": 0.244573,
      "cogs": 745230790.97,
      "gross_margin": 28.39,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210726",
      "current_price": 25.89,
      "price": 25.89,
      "ma5": 26.84,
      "ma10": 30.69,
      "ma20": 37.19,
      "dist_ma5_pct": -3.5,
      "dist_ma10_pct": -15.6,
      "dist_ma20_pct": -30.4,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6814,
        "sizing": "selective"
      }
    },
    {
      "code": "300806.SZ",
      "fetch_time": "2026-07-24T11:40:48+0800",
      "name": "斯迪克",
      "pe": 395.4434,
      "pb": 11.1684,
      "ps_ttm": 8.4058,
      "pcf_ttm": 298.0358,
      "valuation_percentile": 95.47,
      "total_shares": 453300503,
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
        "专精特新小巨人主题指数",
        "QFII重仓指数",
        "专精特新小巨人指数",
        "中小创蓝筹指数",
        "对日反制指数",
        "MLCC指数"
      ],
      "score_company": 7.7,
      "score_trend": 6.2,
      "score_value": 3.6,
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
          "tag": "评级",
          "text": "近90天， 5家 机构给出评级，其中 80% 为“买入”，距目标价的上涨空间为 41% 。"
        },
        {
          "tag": "预测",
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 25% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.9% ，很受外资机构青睐；公募基金持股 5.2% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 -138% ，扣非净利润占净利润 51% ，收益质量很低。"
        },
        {
          "tag": "偿债",
          "text": "现金短债比为 0.17 ，带息债务占全部投入资本 60% ，现金保障很弱，偿债压力很大。"
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
          "content": "2025年年度：每10股转4股派0.15元",
          "tags": [
            "分红送转"
          ],
          "date": "2026-07-27"
        },
        {
          "content": "12:00 7月21日，A股PCB概念股集体反弹。截至半日收盘，波长光电、金禄电子、戈碧迦、中富电路、埃科光电、路维光电、昊志机电、国际复材、锐科激光、欧科亿、鼎泰高科、东威科技、斯迪克涨幅居前；顺络电子、宏和科技、江南新材、大族激光、大为股份、木林森涨停。中信建投研报指出，感光干膜是PCB电路图形转印的核心耗材，受益于AI服务器、数据中心及高速网络设备驱动，行业进入结构性增长周期。预计2026年至2030年感光干膜市场空间将持续增长，年均复合增长率约为9.4%。目前全球感光干膜市场由中国台湾及日本企业主导，随着头部PCB企业批量采用国产产品，内资感光干膜市场份额有望提升。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/20～2027/01/20 王超(副经理)计划增持，变动价格说明：本次增持计划不设价格区间，将根据公司股票价格波动情况及资本市场整体趋势，择机实施增持计划 ，拟增持金额不低于 500万元  交易方式：通过深圳证券交易所交易系统允许的方式（包括但不限于集中竞价、大宗交易等）增持公司股份。",
          "tags": [
            "非控股股东增持"
          ]
        },
        {
          "content": "2026/07/20～2027/01/20 姜章健(副经理)计划增持，变动价格说明：本次增持计划不设价格区间，将根据公司股票价格波动情况及资本市场整体趋势，择机实施增持计划 ，拟增持金额不低于 500万元  交易方式：通过深圳证券交易所交易系统允许的方式（包括但不限于集中竞价、大宗交易等）增持公司股份。",
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
      "valuation_history_days": 282,
      "valuation_history_from": "20211125",
      "current_price": 59.1,
      "price": 59.1,
      "ma5": 59.69,
      "ma10": 68.98,
      "ma20": 85.24,
      "dist_ma5_pct": -1.0,
      "dist_ma10_pct": -14.3,
      "dist_ma20_pct": -30.7,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 3.31,
        "pct_float": 1.72,
        "chg5_pct": 60.0,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "688017.SH",
      "fetch_time": "2026-07-24T11:40:48+0800",
      "name": "绿的谐波",
      "pe": 400.9765,
      "pb": 15.5324,
      "ps_ttm": 89.4788,
      "pcf_ttm": 390.9843,
      "valuation_percentile": 94.27,
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
        "宇树机器人指数"
      ],
      "score_company": 8.7,
      "score_trend": 7.7,
      "score_value": 3.6,
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
          "text": " 8家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
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
          "content": "10:14 企查查APP显示，近日，斯凯孚机器人精密轴承（宁波）有限公司成立，经营范围包含智能机器人的研发；智能机器人销售；工业机器人制造；人工智能硬件销售等。企查查股权穿透显示，该公司由绿的谐波等共同持股。（人民财讯）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "11:53 7月21日，A股机器人板块表现活跃。截至11:20，机器人ETF汇添富（159213）涨超2.5%。成分股中，大族激光涨停，三花智控、绿的谐波涨超4%，汇川技术、拓普集团等涨超2%。大族激光披露，2026年上半年实现净利润12.86亿元，同比增长163.47%。近期举办的2026世界人工智能大会（WAIC）重点展示了机器人场景落地应用，具身智能被列为核心赛道。东方证券分析认为，人形机器人行业关注重点已转向规模化量产与多场景交付，产业链有望迎来催化。\n东吴证券研报指出，人形机器人核心零部件壁垒较高，谐波减速器、丝杠、灵巧手及轻量化材料等环节将受益于行业发展。其中，滚柱丝杠在人形机器人爆发背景下具备增长潜力，灵巧手市场空间广阔，轻量化材料如PEEK在关节模组中应用前景显著。全球科技巨头布局人形机器人，行业量产进程加速。\n风险提示：基金投资存在风险，投资者需阅读法律文件了解风险收益特征。该基金属于中风险等级（R3）产品，适合稳健型（C3）及以上投资者。文中提及个股仅为指数成份股展示，不构成投资建议。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "绿的谐波：关于募集资金投资项目延期的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "绿的谐波：2025年度审计报告(更正后)",
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
      "valuation_history_days": 314,
      "valuation_history_from": "20220829",
      "current_price": 316.7,
      "price": 316.7,
      "ma5": 329.79,
      "ma10": 371.98,
      "ma20": 385.85,
      "dist_ma5_pct": -4.0,
      "dist_ma10_pct": -14.9,
      "dist_ma20_pct": -17.9,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 24.68,
        "pct_float": 4.37,
        "chg5_pct": -14.61,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688200.SH",
      "fetch_time": "2026-07-24T11:40:48+0800",
      "name": "华峰测控",
      "pe": 127.7915,
      "pb": 18.0252,
      "ps_ttm": 51.1297,
      "pcf_ttm": 273.7568,
      "valuation_percentile": 91.13,
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
        "芯片指数",
        "股权激励指数",
        "半导体精选指数",
        "可转债正股指数",
        "半导体设备指数",
        "模拟芯片指数",
        "可转债预案指数",
        "先进封装指数"
      ],
      "score_company": 9.0,
      "score_trend": 7.9,
      "score_value": 3.7,
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
          "text": " 10家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
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
          "content": "10:35 半导体设备板块再度拉升，托伦斯涨超10%，华峰测控、长川科技、金海通、华海清科、中微公司等跟涨。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "华峰测控：华峰测控关于修改《公司章程》的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "华峰测控：北京德和衡律师事务所关于华峰测控有限公司2024年限制性股票激励计划首次授予第二个归属期归属条件成就、预留授予第一个归属期归属条件成就、授予价格与数量调整及部分限制性股票作废相关事项的法律意见书",
          "tags": [
            "重要公告"
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
      "valuation_history_days": 268,
      "valuation_history_from": "20220218",
      "current_price": 369.0,
      "price": 369.0,
      "ma5": 384.79,
      "ma10": 437.8,
      "ma20": 435.52,
      "dist_ma5_pct": -4.1,
      "dist_ma10_pct": -15.7,
      "dist_ma20_pct": -15.3,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.52,
        "pct_float": 0.63,
        "chg5_pct": -16.31,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688531.SH",
      "fetch_time": "2026-07-24T11:40:49+0800",
      "name": "日联科技",
      "pe": 110.2415,
      "pb": 6.1395,
      "ps_ttm": 17.3541,
      "pcf_ttm": 107.8197,
      "valuation_percentile": 81.15,
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
      "score_trend": 7.3,
      "score_value": 4.5,
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
          "tag": "预测",
          "text": " 11家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
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
          "content": "2026/07/20 程树刚(核心技术人员)增持 2200股 ，类型为 二级市场买卖 ，成交均价为 128元/股 ，耗资 28.1万元 ，此次增持后的持股数为2610股",
          "tags": [
            "管理层增持"
          ]
        },
        {
          "content": "2026/07/21 程树刚(核心技术人员)减持 2600股 ，类型为 二级市场买卖 ，成交均价为 118元/股 ，套现 30.8万元 ，此次减持后的持股数为10股",
          "tags": [
            "管理层减持"
          ]
        },
        {
          "content": "2026/07/21 程树刚(董事)增持 2400股 ，类型为 二级市场买卖 ，成交均价为 118元/股 ，耗资 28.2万元 ，此次增持后的持股数为5010股",
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
      "valuation_history_days": 308,
      "valuation_history_from": "20250331",
      "current_price": 126.5,
      "price": 126.5,
      "ma5": 130.06,
      "ma10": 150.21,
      "ma20": 162.26,
      "dist_ma5_pct": -2.7,
      "dist_ma10_pct": -15.8,
      "dist_ma20_pct": -22.0,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.56,
        "pct_float": 3.92,
        "chg5_pct": -5.29,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "003031.SZ",
      "fetch_time": "2026-07-24T11:40:50+0800",
      "name": "中瓷电子",
      "pe": 75.7093,
      "pb": 7.4772,
      "ps_ttm": 14.2515,
      "pcf_ttm": 41.9905,
      "valuation_percentile": 58.45,
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
        "手机陶瓷外壳指数",
        "中电科技系指数"
      ],
      "score_company": 6.4,
      "score_trend": 6.6,
      "score_value": 6.1,
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
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月17日大跌 -10% ，股价跌停，抛压很重。"
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
          "content": "21:00 中瓷电子常务副总经理（代总经理）梁向阳表示，公司正依托技术创新与产业整合，推动电子陶瓷、第三代半导体及高频芯片业务协同发展。目前，公司光通信陶瓷外壳与基板全球市占率领先，半导体设备精密零部件正加速国产替代。其中，静电卡盘、陶瓷加热盘等产品已实现技术突破，部分产品已进入量产或小批量出货阶段，未来将成为公司增长的重要支撑。\n在第三代半导体领域，子公司国联万众的8英寸碳化硅产线已投产，车规级产品实现规模化商用，并向风光储等领域延伸。氮化镓射频业务聚焦5G-A、6G及低空经济等前沿领域，处于技术迭代与示范应用阶段。此外，通过收购雄安太芯，公司补齐了太赫兹芯片技术短板。梁向阳指出，公司已构建起涵盖技术、服务与成本的核心竞争力，光通信器件产品已适配3.2Tbps及以上传输需求，并具备较强的市场响应速度。\n梁向阳表示，中瓷电子将继续发挥央企平台优势，通过人才激励与产业布局优化提升竞争力。公司确立了深耕主业、健全股东回报机制及通过合规并购完善产品矩阵的发展战略，旨在实现产业价值与资本市场价值的同步提升。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/01/20～2026/07/10股东户数增加 74%",
          "tags": [
            "股东户数增加"
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
      "valuation_history_days": 286,
      "valuation_history_from": "20230105",
      "current_price": 107.59,
      "price": 107.59,
      "ma5": 106.69,
      "ma10": 120.26,
      "ma20": 144.1,
      "dist_ma5_pct": 0.8,
      "dist_ma10_pct": -10.5,
      "dist_ma20_pct": -25.3,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6814,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 8.59,
        "pct_float": 2.35,
        "chg5_pct": 3.72,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "688629.SH",
      "fetch_time": "2026-07-24T11:40:50+0800",
      "name": "华丰科技",
      "pe": 171.3956,
      "pb": 25.5598,
      "ps_ttm": 26.8637,
      "pcf_ttm": 141.0699,
      "valuation_percentile": 76.32,
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
      "score_company": 8.1,
      "score_trend": 7.7,
      "score_value": 4.8,
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
          "content": "20:58 7月20日，翔宇医疗与河南省洛阳正骨医院联合共建的“脑机接口骨科创新转化联合中心”在洛阳揭牌。双方将聚焦骨伤全周期康复需求，推进脑机接口技术在骨科康复场景的落地应用，研发智能化康复技术与装备，并开展人才培养与临床研究，推动中医骨伤诊疗与运动康复的智能化升级。\n此次合作是翔宇医疗布局脑机交互康复领域的重要举措。双方将依托临床资源，推进脑机接口技术在骨伤预防、诊疗及康复全周期的应用探索，加速技术从实验室走向临床。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "华丰科技：关于开立募集资金现金管理产品专用结算账户的公告",
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
      "valuation_history_days": 261,
      "valuation_history_from": "20250627",
      "current_price": 169.49,
      "price": 169.49,
      "ma5": 157.18,
      "ma10": 176.37,
      "ma20": 171.1,
      "dist_ma5_pct": 7.8,
      "dist_ma10_pct": -3.9,
      "dist_ma20_pct": -0.9,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 20.0,
        "pct_float": 2.79,
        "chg5_pct": 0.78,
        "net5_repay_days": 3,
        "signal": "neutral"
      }
    },
    {
      "code": "688150.SH",
      "fetch_time": "2026-07-24T11:40:50+0800",
      "name": "莱特光电",
      "pe": 78.0194,
      "pb": 8.378,
      "ps_ttm": 29.4956,
      "pcf_ttm": 58.4987,
      "valuation_percentile": 78.93,
      "total_shares": 402437585,
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
        "OLED指数",
        "可转债预案指数"
      ],
      "score_company": 7.6,
      "score_trend": 6.4,
      "score_value": 4.5,
      "highlights": [
        {
          "tag": "净现",
          "text": "近5年，净现比达到 134% ，净利润现金含量很高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 5.5% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "预测",
          "text": " 7家 机构预测，2026年-2028年营收和净利润每年增长均超过 40% ，未来成长很快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 4.5% ，较受内资机构青睐。"
        },
        {
          "tag": "回购",
          "text": "近6月，公司累计回购 212万股 ，占总股本比例 0.53% ，金额合计 5001万元 。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年05月26日大跌 -13.3% ，且成交额为近20日均值的 2.5倍 ，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月26日 至今陷入调整，资金有出逃可能。"
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
          "content": "莱特光电：北京市中伦律师事务所关于陕西莱特光电材料股份有限公司向不特定对象发行可转换公司债券的法律意见书",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "莱特光电：陕西莱特光电材料股份有限公司向不特定对象发行可转换公司债券的证券募集说明书（上会稿）",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "莱特光电：陕西莱特光电材料股份有限公司关于向不特定对象发行可转换公司债券的审核中心意见落实函回复及募集说明书等申请文件更新的提示性公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "莱特光电：中信证券股份有限公司关于陕西莱特光电材料股份有限公司向不特定对象发行可转换公司债券之发行保荐书",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 423036664.64,
      "revenue_yoy": 0.187665,
      "operating_profit": 205676250.19,
      "operating_profit_yoy": 0.392451,
      "net_profit": 179859585.96,
      "net_profit_yoy": 0.386167,
      "gross_profit": 313785251.1,
      "gross_profit_yoy": 0.326988,
      "cogs": 109251413.54,
      "gross_margin": 74.17,
      "pe_forward": null,
      "valuation_history_days": 283,
      "valuation_history_from": "20240318",
      "current_price": 42.32,
      "price": 42.32,
      "ma5": 45.01,
      "ma10": 49.6,
      "ma20": 55.29,
      "dist_ma5_pct": -6.0,
      "dist_ma10_pct": -14.7,
      "dist_ma20_pct": -23.5,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.29,
        "pct_float": 3.82,
        "chg5_pct": -12.21,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002937.SZ",
      "fetch_time": "2026-07-24T11:40:50+0800",
      "name": "兴瑞科技",
      "pe": 73.263,
      "pb": 5.2788,
      "ps_ttm": 5.6813,
      "pcf_ttm": 41.6411,
      "valuation_percentile": 76.66,
      "total_shares": 316009729,
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
        "TMT指数",
        "可转债正股指数",
        "汽车配件精选指数"
      ],
      "score_company": 7.8,
      "score_trend": 6.8,
      "score_value": 4.7,
      "highlights": [
        {
          "tag": "ROIC",
          "text": "近5年，投入资本回报率为 12% ，创造价值的能力较强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 157% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.9% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "回购",
          "text": "近6月，公司累计回购 298万股 ，占总股本比例 0.94% ，金额合计 6840万元 。"
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
          "content": "预计2026/08/28发布中报",
          "tags": [
            "2026年中报"
          ],
          "date": "2026-08-28"
        },
        {
          "content": "13:01股价达到 46.3 元，创历史新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "09:30股价达到 37.58 元，创历史新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "兴瑞科技：关于提前赎回“兴瑞转债”的第十次提示性公告",
          "tags": [
            "重要公告"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1328139371.71,
      "revenue_yoy": -0.101335,
      "operating_profit": 133950621.06,
      "operating_profit_yoy": -0.385704,
      "net_profit": 117864791.81,
      "net_profit_yoy": -0.385839,
      "gross_profit": 318848106.74,
      "gross_profit_yoy": -0.197356,
      "cogs": 1009291264.97,
      "gross_margin": 24.01,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210726",
      "current_price": 31.39,
      "price": 31.39,
      "ma5": 34.34,
      "ma10": 37.84,
      "ma20": 40.62,
      "dist_ma5_pct": -8.6,
      "dist_ma10_pct": -17.0,
      "dist_ma20_pct": -22.7,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6814,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 10.23,
        "pct_float": 10.34,
        "chg5_pct": -3.99,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301182.SZ",
      "fetch_time": "2026-07-24T11:40:50+0800",
      "name": "凯旺科技",
      "pe": -49.2417,
      "pb": 8.124,
      "ps_ttm": 6.4019,
      "pcf_ttm": null,
      "valuation_percentile": 92.84,
      "total_shares": 95821700,
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
          "name": "安防设备",
          "level": 3
        }
      ],
      "concepts": [
        "TMT指数",
        "专精特新小巨人主题指数",
        "专精特新小巨人指数"
      ],
      "score_company": 4.5,
      "score_trend": 4.8,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年04月27日，业绩超预期引发股价大幅上涨，但目前股价已回落。"
        },
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 19% ，收入成长性较强。"
        },
        {
          "tag": "收现",
          "text": "近5年，收现比达到 113% ，销售收入现金含量较强。"
        },
        {
          "tag": "户数",
          "text": "2026年02月10日至2026年05月29日期间，股东户数减少 34% ，大资金买入。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月29日大跌 -6.07% ，且成交额为近20日均值的 1.61倍 ，抛压很重。"
        },
        {
          "tag": "存货",
          "text": "近5年，存货周转天数增加 128天 ，存货减值风险升高。"
        },
        {
          "tag": "评级",
          "text": "近6月，没有机构发布研究报告，机构关注度低。"
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
          "content": "10:48股价达到 94.7 元，创历史新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是公司披露并购重组取得实质性进展，相关标的有望补强精密线缆连接组件技术与产能、扩展客户渠道并提升业绩预期。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 514708602.52,
      "revenue_yoy": 0.175542,
      "operating_profit": -65875714.57,
      "operating_profit_yoy": -0.194638,
      "net_profit": -45857497.03,
      "net_profit_yoy": -0.084972,
      "gross_profit": 21907775.22,
      "gross_profit_yoy": 3.303047,
      "cogs": 492800827.3,
      "gross_margin": 4.26,
      "pe_forward": null,
      "valuation_history_days": 312,
      "valuation_history_from": "20231225",
      "current_price": 58.34,
      "price": 58.34,
      "ma5": 60.58,
      "ma10": 71.68,
      "ma20": 86.64,
      "dist_ma5_pct": -3.7,
      "dist_ma10_pct": -18.6,
      "dist_ma20_pct": -32.7,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 3.2,
        "pct_float": 6.28,
        "chg5_pct": -10.66,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "000703.SZ",
      "fetch_time": "2026-07-24T11:40:50+0800",
      "name": "恒逸石化",
      "pe": 27.3202,
      "pb": 2.2895,
      "ps_ttm": 0.5171,
      "pcf_ttm": 10.2092,
      "valuation_percentile": 80.84,
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
        "万得预增指数",
        "石化精选指数",
        "预期提升指数",
        "油品升级指数",
        "油气改革指数",
        "供应链服务指数",
        "涤纶指数",
        "PTA指数"
      ],
      "score_company": 8.0,
      "score_trend": 8.9,
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
          "content": "02:45 7月以来，共有375家A股上市公司获机构调研，其中新易盛、京东方A、华灿光电、华勤技术等22家公司获50家以上机构调研。新易盛获417家机构调研居首，公司称二季度业绩预告与年初预期基本吻合。京东方A获243家机构调研，公司表示未来折旧金额及资本开支预计将逐渐下降。在已发布半年度业绩相关公告的调研公司中，超七成实现业绩报喜，恒逸石化、三维通信、凯尔达预计净利润同比增长超1000%。分行业看，获调研且业绩预喜的公司中，电子行业数量居首，电力设备、基础化工及有色金属行业紧随其后。\n研究机构Omdia数据显示，2026年中国半导体市场规模预测值上调。在上述375家获调研公司中，67家获外资机构调研，其中电子行业公司有19家。广合科技、沪电股份、华勤技术等电子行业公司获外资机构调研较多。调研内容显示，外资机构关注相关公司的全球化布局，广合科技泰国工厂正推进产能爬坡，沪电股份泰国基地已进入规模化运营阶段。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "02:46 截至7月20日，已有28家石油石化上市公司披露上半年业绩预告，其中15家预增，5家实现扭亏或减亏。受中东地缘冲突影响，全球化工品价格上涨，库存去化带动部分产品盈利改善。炼化一体化企业表现突出，恒逸石化预计上半年归母净利润55亿元至60亿元，同比增长2326.31%至2546.88%，主要受益于海外成品油盈利及PX、苯等产品盈利维持高位，以及己内酰胺-聚酰胺一体化项目投产。荣盛石化预计上半年净利润50亿元至52亿元，同比增长730.45%至763.67%；东方盛虹预计上半年净利润42亿元至50亿元，同比增长987.39%至1194.51%。\n东方盛虹表示，石化行业供需格局改善及原油价格中枢上移，带动产品价差扩大，炼化一体化项目运行平稳。分析认为，炼化一体化龙头规模效应显著，若地缘冲突缓和，产业链定价权将回归供需端。受地缘局势影响，油服工程企业业绩承压，28家公司中6家油服企业有3家首亏，2家续亏，1家预减。中曼石油预计上半年归母净利润同比减少64.68%至70.46%，受伊拉克项目停工影响；惠博普预计亏损9000万元至1.2亿元，受海外项目进度放缓及汇兑损失影响；博迈科预计亏损7800万元至6500万元，受项目周期切换及海外投资节奏后移影响。\n贝肯能源预计上半年亏损1.15亿元至1.25亿元，受汇兑损失及部分钻机停工影响。展望下半年，机构分析认为，传统大宗化工品受益于补库与出口，AI产业催生的新材料需求值得关注。AI算力基建对半导体材料、电子化学品等提出更高要求，电子特气、含氟电子化学品及半导体材料等细分领域景气度有望上行。",
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
      "valuation_history_from": "20210726",
      "current_price": 15.82,
      "price": 15.82,
      "ma5": 15.08,
      "ma10": 14.56,
      "ma20": 14.61,
      "dist_ma5_pct": 4.9,
      "dist_ma10_pct": 8.7,
      "dist_ma20_pct": 8.3,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.5775,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 9.49,
        "pct_float": 1.58,
        "chg5_pct": -6.73,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301536.SZ",
      "fetch_time": "2026-07-24T11:40:50+0800",
      "name": "星宸科技",
      "pe": 116.314,
      "pb": 17.9246,
      "ps_ttm": 16.8247,
      "pcf_ttm": 188.0693,
      "valuation_percentile": 98.0,
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
        "触板指数",
        "安防监控指数"
      ],
      "score_company": 8.1,
      "score_trend": 9.1,
      "score_value": 3.4,
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
          "text": "近3天，日均换手率 18% ，短线资金追逐，波动风险较高。"
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
      "valuation_history_days": 78,
      "valuation_history_from": "20260330",
      "current_price": 137.0,
      "price": 137.0,
      "ma5": 112.34,
      "ma10": 113.76,
      "ma20": 116.42,
      "dist_ma5_pct": 22.0,
      "dist_ma10_pct": 20.4,
      "dist_ma20_pct": 17.7,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 10.47,
        "pct_float": 4.25,
        "chg5_pct": 30.78,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "002957.SZ",
      "fetch_time": "2026-07-24T11:40:52+0800",
      "name": "科瑞技术",
      "pe": 51.6502,
      "pb": 4.8062,
      "ps_ttm": 5.6737,
      "pcf_ttm": 44.1559,
      "valuation_percentile": 84.12,
      "total_shares": 419982466,
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
        "股权激励指数",
        "深圳本地股指数",
        "人形机器人指数",
        "外资企业指数",
        "苹果指数",
        "光模块(CPO)指数",
        "工业4.0指数",
        "合资企业指数",
        "触板指数",
        "新能源设备指数",
        "电子烟"
      ],
      "score_company": 8.0,
      "score_trend": 6.5,
      "score_value": 4.0,
      "highlights": [
        {
          "tag": "净现",
          "text": "近5年，净现比达到 137% ，净利润现金含量很高。"
        },
        {
          "tag": "订单",
          "text": "合同负债 9.5亿元 ，较上期增长 17% ，占2025年营收 36% ，在手订单充足。"
        },
        {
          "tag": "评级",
          "text": "近90天， 7家 机构给出评级，其中 57% 为“买入”，距目标价的上涨空间为 59% 。"
        },
        {
          "tag": "户数",
          "text": "2026年06月18日至2026年07月10日期间，股东户数减少 31% ，大资金买入。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月17日大跌 -9.99% ，股价跌停，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年06月03日 至今陷入调整，资金有出逃可能。"
        },
        {
          "tag": "收益",
          "text": "近12月，扣非净利润占净利润 60% ，收益质量较低。"
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
          "content": "科瑞技术：关于使用部分自有闲置资金进行理财的进展公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "12:45 科瑞技术7月1日在互动平台表示，公司积极承接国内大客户需求，已为国内大客户提供液冷相关设备。目前营收占比较小，敬请注意投资风险。（人民财讯）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "2026/01/30～2026/06/30股东户数增加 123%",
          "tags": [
            "股东户数增加"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1761190834.25,
      "revenue_yoy": 0.002158,
      "operating_profit": 294460718.69,
      "operating_profit_yoy": 0.300605,
      "net_profit": 273760038.81,
      "net_profit_yoy": 0.360408,
      "gross_profit": 614201016.32,
      "gross_profit_yoy": -0.101483,
      "cogs": 1146989817.93,
      "gross_margin": 34.87,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210726",
      "current_price": 37.62,
      "price": 37.62,
      "ma5": 36.13,
      "ma10": 39.78,
      "ma20": 45.45,
      "dist_ma5_pct": 4.1,
      "dist_ma10_pct": -5.4,
      "dist_ma20_pct": -17.2,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6814,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 3.9,
        "pct_float": 2.48,
        "chg5_pct": -6.71,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688777.SH",
      "fetch_time": "2026-07-24T11:40:52+0800",
      "name": "中控技术",
      "pe": 164.7854,
      "pb": 6.6496,
      "ps_ttm": 8.1875,
      "pcf_ttm": 242.0669,
      "valuation_percentile": 70.82,
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
      "score_trend": 7.5,
      "score_value": 4.8,
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
          "text": " 13家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
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
          "content": "11:53 7月21日，A股机器人板块表现活跃。截至11:20，机器人ETF汇添富（159213）涨超2.5%。成分股中，大族激光涨停，三花智控、绿的谐波涨超4%，汇川技术、拓普集团等涨超2%。大族激光披露，2026年上半年实现净利润12.86亿元，同比增长163.47%。近期举办的2026世界人工智能大会（WAIC）重点展示了机器人场景落地应用，具身智能被列为核心赛道。东方证券分析认为，人形机器人行业关注重点已转向规模化量产与多场景交付，产业链有望迎来催化。\n东吴证券研报指出，人形机器人核心零部件壁垒较高，谐波减速器、丝杠、灵巧手及轻量化材料等环节将受益于行业发展。其中，滚柱丝杠在人形机器人爆发背景下具备增长潜力，灵巧手市场空间广阔，轻量化材料如PEEK在关节模组中应用前景显著。全球科技巨头布局人形机器人，行业量产进程加速。\n风险提示：基金投资存在风险，投资者需阅读法律文件了解风险收益特征。该基金属于中风险等级（R3）产品，适合稳健型（C3）及以上投资者。文中提及个股仅为指数成份股展示，不构成投资建议。",
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
      "valuation_history_days": 295,
      "valuation_history_from": "20221125",
      "current_price": 86.0,
      "price": 86.0,
      "ma5": 90.03,
      "ma10": 95.5,
      "ma20": 105.07,
      "dist_ma5_pct": -4.5,
      "dist_ma10_pct": -9.9,
      "dist_ma20_pct": -18.2,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 28.84,
        "pct_float": 4.4,
        "chg5_pct": -6.53,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002821.SZ",
      "fetch_time": "2026-07-24T11:40:52+0800",
      "name": "凯莱英",
      "pe": 52.4453,
      "pb": 3.3309,
      "ps_ttm": 8.4015,
      "pcf_ttm": 39.2141,
      "valuation_percentile": 42.91,
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
        "专精特新小巨人指数",
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
      "score_trend": 8.0,
      "score_value": 5.9,
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
          "text": " 8家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
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
          "content": "22:00 7月22日，上海湾区生物医药创新发展主题活动在金山区举行。金山区委书记袁罡表示，金山将深度融入全市生物医药发展战略，重点推进抗体药物、新型疫苗、细胞与基因治疗等产业化进程。金山区生物医药产业规模稳步增长，今年一季度产业规模增速达25.4%，去年产业规模达377亿元。上海湾区生物医药港目前已集聚生物医药企业逾120家，规模以上企业75家，涵盖科济制药、青赛生物、凯莱英、南模生物等企业。\n科济药业研发的一款注射液获批上市，为全球首款针对实体瘤的CAR-T细胞治疗产品。目前国家药品监督管理局已批准9款CAR-T细胞产品上市，其中3款产品的产业化生产落地金山。活动期间，还举行了青年项目路演及圆桌对话，探讨生物医药产业链协同与创新创业机遇。",
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
      "valuation_history_from": "20210726",
      "current_price": 163.54,
      "price": 163.54,
      "ma5": 164.36,
      "ma10": 171.09,
      "ma20": 163.49,
      "dist_ma5_pct": -0.5,
      "dist_ma10_pct": -4.4,
      "dist_ma20_pct": 0.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6814,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 8.84,
        "pct_float": 1.7,
        "chg5_pct": -13.46,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688378.SH",
      "fetch_time": "2026-07-24T11:40:52+0800",
      "name": "奥来德",
      "pe": 78.9735,
      "pb": 5.0008,
      "ps_ttm": 15.2158,
      "pcf_ttm": 32.1259,
      "valuation_percentile": 86.66,
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
      "score_value": 4.0,
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
          "text": "近90天， 6家 机构给出评级，其中 83% 为“买入”，距目标价的上涨空间为 78% 。"
        },
        {
          "tag": "预测",
          "text": " 3家 机构预测，2026年-2028年营收和净利润每年增长均超过 25% ，未来成长较快。"
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
      "valuation_history_days": 313,
      "valuation_history_from": "20220905",
      "current_price": 39.8,
      "price": 39.8,
      "ma5": 41.67,
      "ma10": 47.13,
      "ma20": 51.54,
      "dist_ma5_pct": -4.5,
      "dist_ma10_pct": -15.6,
      "dist_ma20_pct": -22.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.96,
        "pct_float": 5.25,
        "chg5_pct": -8.36,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300323.SZ",
      "fetch_time": "2026-07-24T11:40:52+0800",
      "name": "华灿光电",
      "pe": -64.3564,
      "pb": 2.7257,
      "ps_ttm": 2.7517,
      "pcf_ttm": null,
      "valuation_percentile": 64.32,
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
      "score_trend": 6.4,
      "score_value": 5.2,
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
          "tag": "分红",
          "text": "近5年，从未实施现金分红，为一毛不拔的铁公鸡。"
        },
        {
          "tag": "波动",
          "text": "2026年06月26日，换手率 22% ，短线资金追逐，波动风险较高。"
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
      "valuation_history_from": "20210726",
      "current_price": 11.49,
      "price": 11.49,
      "ma5": 11.49,
      "ma10": 12.97,
      "ma20": 15.69,
      "dist_ma5_pct": -0.0,
      "dist_ma10_pct": -11.4,
      "dist_ma20_pct": -26.8,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 14.09,
        "pct_float": 10.33,
        "chg5_pct": -3.16,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688376.SH",
      "fetch_time": "2026-07-24T11:40:52+0800",
      "name": "美埃科技",
      "pe": 81.3205,
      "pb": 4.6526,
      "ps_ttm": 4.3549,
      "pcf_ttm": 27.6746,
      "valuation_percentile": 89.05,
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
      "score_value": 3.5,
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
      "valuation_history_days": 406,
      "valuation_history_from": "20241118",
      "current_price": 70.19,
      "price": 70.19,
      "ma5": 70.27,
      "ma10": 81.07,
      "ma20": 88.43,
      "dist_ma5_pct": -0.1,
      "dist_ma10_pct": -13.4,
      "dist_ma20_pct": -20.6,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 2.21,
        "pct_float": 2.43,
        "chg5_pct": -2.34,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688536.SH",
      "fetch_time": "2026-07-24T11:40:52+0800",
      "name": "思瑞浦",
      "pe": 130.2248,
      "pb": 5.3986,
      "ps_ttm": 14.1282,
      "pcf_ttm": 107.3965,
      "valuation_percentile": 40.18,
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
        "5G指数",
        "专精特新小巨人主题指数",
        "半导体产业指数",
        "芯片指数",
        "股权激励指数",
        "半导体精选指数",
        "专精特新小巨人指数",
        "AIPC指数",
        "智能家居指数",
        "模拟芯片指数",
        "苏州工业园区指数"
      ],
      "score_company": 8.4,
      "score_trend": 7.7,
      "score_value": 6.9,
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
      "valuation_history_days": 303,
      "valuation_history_from": "20220922",
      "current_price": 258.96,
      "price": 258.96,
      "ma5": 251.2,
      "ma10": 282.57,
      "ma20": 312.27,
      "dist_ma5_pct": 3.1,
      "dist_ma10_pct": -8.4,
      "dist_ma20_pct": -17.1,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 11.78,
        "pct_float": 3.41,
        "chg5_pct": 8.42,
        "net5_repay_days": 4,
        "signal": "adding"
      }
    },
    {
      "code": "688392.SH",
      "fetch_time": "2026-07-24T11:40:52+0800",
      "name": "骄成超声",
      "pe": 122.8719,
      "pb": 9.6623,
      "ps_ttm": 21.4886,
      "pcf_ttm": 139.6295,
      "valuation_percentile": 83.92,
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
      "score_trend": 7.4,
      "score_value": 4.1,
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
          "text": " 5家 机构预测，2026年-2028年营收和净利润每年增长均超过 25% ，未来成长较快。"
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
          "content": "11:59 为应对算力瓶颈，中国计划在未来五年内投入约2万亿元人民币建设数据中心。7月21日，A股芯片概念股集体反弹，正帆科技、臻宝科技、托伦斯涨停，华虹宏力涨超17%，东芯股份涨超16%，精智达、长川科技、精测电子、普冉股份涨超14%，骄成超声涨超13%，北京君正、江丰电子、中微公司、鼎龙股份涨超12%，圣邦股份涨超11%，澜起科技、京仪装备、华海清科、安集科技涨超10%，北方华创、大为股份涨停。消息面上，智谱已完成一座全部采用国产芯片的大型数据中心建设，并已开始部分运营，该中心旨在支持GLM平台开发。智谱目前已建成或运营多个计算集群，每个集群配备超过1万块芯片。",
          "tags": [
            "资讯"
          ]
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
      "valuation_history_days": 436,
      "valuation_history_from": "20240927",
      "current_price": 162.09,
      "price": 162.09,
      "ma5": 159.72,
      "ma10": 183.74,
      "ma20": 188.12,
      "dist_ma5_pct": 1.5,
      "dist_ma10_pct": -11.8,
      "dist_ma20_pct": -13.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.84,
        "pct_float": 2.71,
        "chg5_pct": -13.11,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002432.SZ",
      "fetch_time": "2026-07-24T11:40:54+0800",
      "name": "九安医疗",
      "pe": 13.8055,
      "pb": 1.5133,
      "ps_ttm": 27.2998,
      "pcf_ttm": null,
      "valuation_percentile": 60.92,
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
      "score_company": 7.7,
      "score_trend": 8.6,
      "score_value": 5.2,
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
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 -16% ，收益质量很低。"
        },
        {
          "tag": "波动",
          "text": "近5天，日均换手率 14% ，短线资金追逐，波动风险较高。"
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
          "content": "02:47 九安医疗以有限合伙人身份出资1亿元参与投资天津砺思星雀创业投资合伙企业（有限合伙）。近日，公司收到通知，该基金已完成募集，募集资金总额为9.28亿元。公司作为有限合伙人进行财务性投资，本次投资无保本及最低收益承诺，存在投资回收期长、流动性低及无法实现预期收益的风险。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "20:05 据报道，大模型企业月之暗面计划于8月启动上市前最后一轮融资，目标投前估值500亿美元，并可能在6个月内赴港上市。九安医疗曾于2023年及2024年投资月之暗面，并于2026年2月参与领投。\n九安医疗三次投资月之暗面时，后者估值均低于最新目标估值。近期月之暗面发布Kimi K3模型，在AI代码能力评测中表现突出。受相关消息影响，九安医疗近期股价出现波动。\n九安医疗近年来构建了涵盖智元机器人、松延动力、深度求索等项目的投资版图，并持有小米、小鹏汽车、腾讯控股等股票及部分美国市场资产。公司将投资业务分为资产管理与科创投资两部分，科创投资聚焦硬科技、医疗大健康及人工智能等领域。\n九安医疗医疗主业受卫生检测需求变化影响，营收连续三年下降。2026年一季度公司营收同比下滑，但半年度预报显示归母净利润同比大幅增长，主要受投资收益驱动。目前公司经营体系包含医疗健康主业与大类资产配置投资，市场对其定位存在不同视角。",
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
      "valuation_history_from": "20210726",
      "current_price": 73.48,
      "price": 73.48,
      "ma5": 77.31,
      "ma10": 70.29,
      "ma20": 67.99,
      "dist_ma5_pct": -5.0,
      "dist_ma10_pct": 4.5,
      "dist_ma20_pct": 8.1,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6814,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 13.82,
        "pct_float": 4.04,
        "chg5_pct": -4.76,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300373.SZ",
      "fetch_time": "2026-07-24T11:40:54+0800",
      "name": "扬杰科技",
      "pe": 35.8361,
      "pb": 5.096,
      "ps_ttm": 6.3944,
      "pcf_ttm": 30.3911,
      "valuation_percentile": 57.58,
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
      "score_trend": 7.3,
      "score_value": 5.4,
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
          "tag": "产能",
          "text": "在建工程占总资产 12% ，未来产能扩张后，营收有望进一步增长。"
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
      "valuation_history_from": "20210726",
      "current_price": 93.14,
      "price": 93.14,
      "ma5": 93.58,
      "ma10": 103.49,
      "ma20": 120.66,
      "dist_ma5_pct": -0.5,
      "dist_ma10_pct": -10.0,
      "dist_ma20_pct": -22.8,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 16.18,
        "pct_float": 3.2,
        "chg5_pct": -4.97,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688401.SH",
      "fetch_time": "2026-07-24T11:40:54+0800",
      "name": "路维光电",
      "pe": 50.1952,
      "pb": 5.2568,
      "ps_ttm": 11.1366,
      "pcf_ttm": 46.1293,
      "valuation_percentile": 82.59,
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
      "score_trend": 7.6,
      "score_value": 4.2,
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
          "content": "15:28 7月21日，A股三大指数集体高开，盘初下探后迎来反弹，午后涨幅扩大。截至收盘，上证综指涨1.79%，报3864.37点；深证成指涨4.81%，报14264.29点；创业板指涨7.05%，报3685.97点。两市及北交所共3101只股票上涨，2301只下跌。沪深两市成交总额29571亿元，较前一交易日增加2549亿元。盘面上，半导体、算力硬件产业链领涨，金融科技、锂电池、机器人等题材活跃；电力、油气、金融、白酒板块调整。\n半导体板块中，格科微、托伦斯、臻宝科技、杰华特、华虹宏力、东微半导等超80股涨停或涨超10%。电子板块中，三环集团、路维光电、芯源微、北京君正、拓荆科技等超150股涨停或涨超10%。机械设备板块中，瑞晨环保、正帆科技、精智达、精测电子、埃科光电等超50股涨停或涨超10%。煤炭股领跌，辽宁能源、淮北矿业、安泰集团、潞安环能、陕西煤业、平煤股份跌超4%。石油石化板块中，通源石油、潜能恒信、ST洲际、泰山石油跌超7%。银行股方面，宁波银行、中国银行、工商银行、农业银行、建设银行、交通银行跌超2%。\n针对市场走势，西南证券认为当前调整为前期上涨后的正常整固，市场具备中长期配置价值。中金公司研报指出，全球市场进入“中场休息”阶段，战术层面三季度调整或将持续，战略层面看好科技行情及广义安全资产。华西证券认为市场最激烈的抛压盘或已过去，未来将进入震荡修复阶段。光大证券表示，受地缘因素及海外科技股估值调整影响，市场观望情绪浓厚，短线或以震荡磨底、结构性轮动为主。东方证券认为，短期去杠杆阶段有望在月底结束，目前至月底是较好的布局期。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "路维光电：深圳市路维光电股份有限公司2026年度向特定对象发行股票上市公告书",
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
      "valuation_history_days": 464,
      "valuation_history_from": "20240819",
      "current_price": 66.76,
      "price": 66.76,
      "ma5": 66.14,
      "ma10": 75.03,
      "ma20": 81.26,
      "dist_ma5_pct": 0.9,
      "dist_ma10_pct": -11.0,
      "dist_ma20_pct": -17.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.0,
        "pct_float": 4.68,
        "chg5_pct": -2.51,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688331.SH",
      "fetch_time": "2026-07-24T11:40:54+0800",
      "name": "荣昌生物",
      "pe": 52.9394,
      "pb": 17.4081,
      "ps_ttm": 20.2251,
      "pcf_ttm": 270.7492,
      "valuation_percentile": 51.26,
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
        "股权激励指数",
        "大消费指数",
        "创新药指数",
        "生物科技等权指数",
        "单克隆抗体指数",
        "生物制品精选指数"
      ],
      "score_company": 7.6,
      "score_trend": 7.9,
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
          "text": "北向资金持股 2.7% ，较受外资机构青睐；公募基金持股 28% ，很受内资机构青睐。"
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
          "content": "08:00 兴证金工团队指出，2026年上半年中国创新药对外授权约1100亿美元，再创历史新高。医药产业被列为“新兴支柱产业”，创新药板块基本面延续向上趋势，随着市场资金再平衡，板块进入估值修复阶段。\n中国创新药研发数量位居全球首位。政策支持下，审评审批速度显著提升，医保谈判机制成熟，创新药在核心医院市场占比由2015年的21%增长至2024年的29%。同时，中国药企在临床入组速度及研发成本控制方面具备效率优势。\n中国企业在ADC、双/多特异性抗体、细胞与基因治疗等新技术平台竞争力增强，研发项目占比超50%。科伦博泰、百利天恒、荣昌生物等企业通过差异化设计在ADC领域取得进展。\n国内政策持续支持创新药发展，包括医保与商保双层支付体系的初步成型及创新药首发价格机制的优化。2026年上半年中国创新药对外授权交易总额突破1000亿美元，出海模式正从单一权益转让向平台合作演变。\n创新药板块正由估值驱动向业绩与全球化兑现驱动转变。随着海外临床进展及商业化分成落地，国产重磅创新药有望进入海外销售阶段。\nADC药物持续迭代，AI制药在药物研发全流程的应用提升了效率与成功率。胰腺癌治疗及减重领域（如礼来、诺和诺德、辉瑞、罗氏相关管线）均取得研发进展。\n小核酸药物在慢病领域展现潜力，TCE实体瘤疗法及通用CAR-T技术持续突破。AI制药在药效及成药性维度赋能药物设计。\n2025年CXO板块收入同比增长12.7%，归母净利润同比增长131.9%。药明康德、康龙化成、药明合联、药明生物、皓元医药、药石科技等公司订单增长，CDMO领域新分子订单需求旺盛。\nCXO板块外需韧性强劲，内需CRO复苏趋势明确。随着创新药BD出海及融资回暖，临床前和临床CRO新签订单呈现量价齐升趋势，预计2026年起业绩有望反转。\n国证港股通创新药指数、恒生生物科技指数与中证创新药产业指数在配置上各有侧重。截至2026年7月，创新药主题基金总规模突破1300亿元，板块估值处于历史中低水平。\n建议根据风险偏好选择指数产品。南方国证港股通创新药ETF（159297）、南方恒生生物科技ETF（159615）及南方中证创新药ETF（159858）分别覆盖不同市场。南方基金资产管理规模位居行业前列。\n南方基金构建了多元化产品矩阵，通过上述三只ETF为投资者提供创新药领域的指数化配置选择。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "17:35 华东医药上市以来累计分红25次，金额达88.73亿元。作为曾获社保基金长期重仓的医药白马股，公司在仿制药和医药商业业务驱动下曾保持高增长。受集采政策影响，仿制药利润空间收窄，公司营收增速放缓。为应对转型，公司研发投入从2019年的10.55亿元增至2024年的25.06亿元。\n华东医药通过收购Sinclair Pharma及代理产品布局医美赛道，并加大创新药研发。2025年研发费用达24.72亿元，主要由自有资金覆盖。公司目前拥有90余项创新药管线，涵盖肿瘤、内分泌及自身免疫领域。2025年创新产品销售及代理服务收入合计23.4亿元，同比增长64.2%，占医药工业营业收入比重为15.81%。\n2025年华东医药营业利润同比下降5.01%，主要受研发费用化支出、海外子公司经营亏损及商誉减值影响。剔除商誉减值后，扣非净利润同比增长1.13%。公司经营活动现金流净额持续为正，2025年为42.46亿元，支撑了研发投入与分红。此外，公司面临海外并购资产培育期亏损、商誉减值风险及应收账款增速高于营收增速的挑战。",
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
      "valuation_history_days": 281,
      "valuation_history_from": "20240401",
      "current_price": 126.9,
      "price": 126.9,
      "ma5": 126.19,
      "ma10": 132.36,
      "ma20": 128.45,
      "dist_ma5_pct": 0.6,
      "dist_ma10_pct": -4.1,
      "dist_ma20_pct": -1.2,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.49,
        "pct_float": 2.14,
        "chg5_pct": -6.04,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "601958.SH",
      "fetch_time": "2026-07-24T11:40:54+0800",
      "name": "金钼股份",
      "pe": 19.1317,
      "pb": 3.3932,
      "ps_ttm": 4.5691,
      "pcf_ttm": 31.0756,
      "valuation_percentile": 85.0,
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
      "score_trend": 8.1,
      "score_value": 4.0,
      "highlights": [
        {
          "tag": "龙头",
          "text": "公司为 钼 行业龙头企业。"
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
          "text": "近1年，股价涨幅超过A股市场 93% 的股票，走势较强。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月23日大跌 -8.76% ，且成交额为近20日均值的 2.06倍 ，抛压很重。"
        },
        {
          "tag": "估值",
          "text": "最新综合估值高于近十年 85% 的时间，处于历史高位。"
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
          "content": "21:03 金钼股份冶炼分公司党群工作部部长朱文凯，通过制定党建工作要点、完善考核办法及建立目标责任制，将党建工作与生产经营深度融合。他通过走访调研，指导各党支部补齐工作短板，提升基层党建工作实效。\n朱文凯牵头创建“赤焰炼初心”党建品牌，并总结形成“1557”工作法，针对不同车间党支部特点开展针对性指导。在他的推动下，分公司多个党支部获得集团及省国资委的标杆或示范称号。此外，他通过成立“党员先锋队”及推动“揭榜挂帅”机制，将党建工作嵌入设备检修及重点项目建设中，保障了生产经营任务的推进。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "15:37 金钼股份发布业绩快报，上半年营业收入79.18亿元，同比增长13.79%；净利润17.4亿元，同比增长25.91%。面对各类钼产品价格较上年同期上升的良好机遇，公司通过狠抓精细管理、强化产销协同、抢抓产品价格高点、有效压控成本、积极开拓新产品新市场等一揽子举措，实现营业收入、归母净利润等经营指标同比均有提升。",
          "tags": [
            "快讯"
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
      "valuation_history_from": "20210726",
      "current_price": 21.43,
      "price": 21.43,
      "ma5": 20.8,
      "ma10": 21.77,
      "ma20": 24.73,
      "dist_ma5_pct": 3.0,
      "dist_ma10_pct": -1.6,
      "dist_ma20_pct": -13.3,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.4995,
        "sizing": "normal"
      },
      "margin": {
        "rzye_yi": 11.48,
        "pct_float": 1.63,
        "chg5_pct": -5.15,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "603156.SH",
      "fetch_time": "2026-07-24T11:40:55+0800",
      "name": "养元饮品",
      "pe": 32.1639,
      "pb": 5.3002,
      "ps_ttm": 7.5992,
      "pcf_ttm": 25.4449,
      "valuation_percentile": 96.89,
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
      "score_trend": 7.0,
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
          "content": "17:58 养元饮品董事长姚奎章表示，公司正通过供给侧改革应对消费变迁。在稳固“六个核桃”基本盘方面，公司将持续挖掘核桃营养价值，通过产品规格调整推动产品日常化消费，并推行“3+6”全域深度分销模式，在稳固传统渠道的同时拓展新兴渠道。\n在增量业务上，养元饮品推出“六个核桃植物奶”系列，旨在解决动物蛋白摄入的健康顾虑。对于代理业务，姚奎章强调其仅为渠道能力的变现，公司主业仍聚焦核桃植物蛋白产品。此外，公司对外投资遵循审慎原则，确保不影响主业经营。\n姚奎章表示，公司重视投资者回报，坚持稳定的现金分红政策。未来三到五年，公司将继续深耕核桃饮品主业与植物基赛道，致力于提升经营质量，追求长期稳健发展。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "11:58 截至2026年7月21日午间收盘，中证主要消费指数下跌1.39%。成分股中，养元饮品、东鹏饮料、安琪酵母上涨，牧原股份、泸州老窖、温氏股份下跌。商务部近期召开全国消费品以旧换新年中工作推进电视电话会议，强调要抓实抓细消费品以旧换新政策，优化补贴流程，提升群众获得感。东方证券分析指出，《扩大消费“十五五”规划》明确2030年社零总额目标，强化了消费增长预期，政策在服务消费、商品消费及创新领域提供动能，食品饮料等低估值板块有望迎来修复。截至2026年6月30日，中证主要消费指数前十大权重股包括伊利股份、贵州茅台、五粮液、牧原股份、温氏股份、泸州老窖、海天味业、山西汾酒、海大集团、东鹏饮料，合计占比67.69%。消费ETF（512600）跟踪该指数，场外投资者可通过消费ETF联接基金（009180）进行布局。",
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
      "valuation_history_from": "20210726",
      "current_price": 34.98,
      "price": 34.98,
      "ma5": 35.76,
      "ma10": 40.17,
      "ma20": 42.9,
      "dist_ma5_pct": -2.2,
      "dist_ma10_pct": -12.9,
      "dist_ma20_pct": -18.5,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.4995,
        "sizing": "normal"
      },
      "margin": {
        "rzye_yi": 4.45,
        "pct_float": 1.0,
        "chg5_pct": -5.45,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300684.SZ",
      "fetch_time": "2026-07-24T11:40:55+0800",
      "name": "中石科技",
      "pe": 41.0836,
      "pb": 6.9827,
      "ps_ttm": 7.4854,
      "pcf_ttm": 35.1982,
      "valuation_percentile": 64.77,
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
      "score_company": 8.2,
      "score_trend": 6.4,
      "score_value": 4.5,
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
          "text": "北向资金持股 4.1% ，很受外资机构青睐；公募基金持股 3.0% ，较受内资机构青睐。"
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
      "valuation_history_from": "20210726",
      "current_price": 48.25,
      "price": 48.25,
      "ma5": 50.36,
      "ma10": 59.16,
      "ma20": 61.2,
      "dist_ma5_pct": -4.2,
      "dist_ma10_pct": -18.4,
      "dist_ma20_pct": -21.2,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 2.42,
        "pct_float": 2.45,
        "chg5_pct": 7.51,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "300747.SZ",
      "fetch_time": "2026-07-24T11:40:55+0800",
      "name": "锐科激光",
      "pe": 75.4161,
      "pb": 5.2667,
      "ps_ttm": 5.0209,
      "pcf_ttm": 113.3693,
      "valuation_percentile": 46.75,
      "total_shares": 561600000,
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
        "消费电子产业指数",
        "先进制造指数",
        "人形机器人指数",
        "触板指数",
        "激光指数",
        "央企新型工业化指数",
        "航天科工系指数"
      ],
      "score_company": 7.3,
      "score_trend": 5.0,
      "score_value": 5.7,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月21日，业绩超预期引发股价大幅上涨，当日收涨 14.7% 。"
        },
        {
          "tag": "利润",
          "text": "最新季度，归母净利润同比增长 108% ，利润成长性强。"
        },
        {
          "tag": "评级",
          "text": "近90天， 7家 机构给出评级，其中 57% 为“买入”，距目标价的上涨空间为 38% 。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 3.2% ，较受内资机构青睐。"
        },
        {
          "tag": "增持",
          "text": "近1月，管理层累计实际增持 3.6万股 ，占总股本比例 0.01% ，金额合计 113万元 。"
        }
      ],
      "risks": [
        {
          "tag": "收益",
          "text": "近12月，扣非净利润占净利润 60% ，收益质量较低。"
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
          "content": "13:38 7月20日，锐科激光发布2026年半年度业绩快报。报告期内，公司实现营业总收入19.10亿元，同比增长14.75%；归母净利润1.58亿元，同比增长116.73%；扣非净利润同比大幅增长。公司正推进全产业链产线布局：武汉睿芯启动高功率掺杂特种光纤数字化生产线二期项目；上海国神光电建设超快激光器研发生产基地，预计2026年内投产；锐科新型光源产研基地一期项目进入全面建设阶段。\n2026上半年，锐科激光针对新能源、算力、低空经济、3D打印、医疗科研五大领域推出多款新品。新能源方面，推出RayWeld焊接解决方案及单模小型化风冷500W MOPA脉冲激光器；算力方面，布局特种光纤、超快激光器及500W连续绿光激光器；低空经济方面，迭代升级轻量化户外风冷3kW光纤激光器；3D打印方面，发布小型化500W增材制造专用光纤激光器。\n公司推出单模块1000W 1940nm掺铥光纤激光器，适用于泌尿外科手术、皮肤美容、精密塑料焊接及科研场景。随着三大产能项目投产及新品放量，公司将继续拓展高附加值市场。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/21 陈星星(董事、高管)增持 2.62万股 ，类型为 竞价交易 ，成交均价为 31.7元/股 ，耗资 83.1万元 ，此次增持后的持股数为2.62万股",
          "tags": [
            "管理层增持"
          ]
        },
        {
          "content": "2026/07/21 邓先琨(高管、董秘)增持 9700股 ，类型为 竞价交易 ，成交均价为 31.2元/股 ，耗资 30.3万元 ，此次增持后的持股数为9700股",
          "tags": [
            "管理层增持"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是公司2026上半年营收19.1亿元、归母净利润同比+116.73%，Q2净利环比+178%，受激光器需求回升、提质增效带动毛利率提升及减值减少。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 2505678215.77,
      "revenue_yoy": 0.066688,
      "operating_profit": 127191232.53,
      "operating_profit_yoy": 0.021014,
      "net_profit": 129081619.12,
      "net_profit_yoy": 0.036921,
      "gross_profit": 493465473.61,
      "gross_profit_yoy": -0.078134,
      "cogs": 2012212742.16,
      "gross_margin": 19.69,
      "pe_forward": null,
      "valuation_history_days": 302,
      "valuation_history_from": "20210726",
      "current_price": 34.11,
      "price": 34.11,
      "ma5": 32.73,
      "ma10": 34.94,
      "ma20": 41.7,
      "dist_ma5_pct": 4.2,
      "dist_ma10_pct": -2.4,
      "dist_ma20_pct": -18.2,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 8.39,
        "pct_float": 4.71,
        "chg5_pct": -1.28,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "603127.SH",
      "fetch_time": "2026-07-24T11:40:56+0800",
      "name": "昭衍新药",
      "pe": 70.0769,
      "pb": 4.0974,
      "ps_ttm": 20.5722,
      "pcf_ttm": 68.4252,
      "valuation_percentile": 50.23,
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
      "score_trend": 9.4,
      "score_value": 5.8,
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
          "content": "09:17 Wind数据显示，截至7月20日，A股504家医药生物公司中已有94家披露上半年业绩预告。其中，55家公司净利润实现正增长。创新药产业链及CXO板块表现亮眼，富祥股份、昭衍新药、美迪西等公司净利增幅居前；传统制药与部分医疗器械企业则面临较大经营压力。昭衍新药预计上半年归母净利润同比增长884.9%至1377.4%，主要受生物资产价格上行及自然增值影响；海思科预计上半年归母净利润同比增长513.25%至575.35%，得益于创新药放量及对外授权项目首付款确认；康龙化成预计上半年营业收入与归母净利润均实现增长，主要得益于战略客户拓展及小分子CDMO项目推进。\n创新药及CXO板块业绩增长主要受海外授权交易（BD）驱动。2026年上半年，中国创新药企披露BD交易123笔，交易金额逾1030.35亿美元，首付款合计逾49.75亿美元。医保谈判提速及规则优化也改善了创新药的商业化预期，恒瑞医药、百济神州、信达生物等龙头品种加速进入医保目录。行业分化加剧，已披露预告的公司中，44家预计亏损，占比46.8%。医疗器械板块中，万东医疗预计上半年净利润亏损1.01亿元至0.83亿元，主要受“以价换量”策略、采购节奏拉长及核心零部件成本高位影响。\n传统中药企业中，昆药集团、益佰制药、中恒集团等预计上半年出现亏损。疫苗企业万泰生物预计上半年归母净利润亏损1.16亿元至1.40亿元，主要受九价HPV疫苗销售费用增加及存货跌价准备等因素影响。政策方面，国家卫健委发布《国家基本药物目录（2026年版）》，首次将4款国产一类创新药纳入遴选范围。今年上半年我国共批准38个1类创新药上市，自主研发创新药占比显著提升。东海证券研报认为，医药生物板块估值处于近一年低位，创新药及CXO板块全年业绩增长可期。\n机构分析指出，国内创新药企在国际化方面竞争力持续增强，BD交易热度不减。西南证券研报建议关注下半年BD出海、AI医疗、脑机接口等科技主题及中药红利资产，预计医药板块将呈现K型分化。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "13:41 昭衍新药发布2026年半年度业绩预告，预计上半年营收为6.69亿元至7.39亿元，同比最高增长10.5%；归母净利润预计为6亿元至9亿元，同比增幅在884.9%至1377.4%之间。公司表示，利润增长主要源于生物资产公允价值变动，该项贡献净利润约7.03亿元至7.77亿元。若剔除此项影响，实验室服务及其他业务净利润处于亏损1.42亿元至盈利6497万元区间。\n实验猴价格上涨是影响业绩的重要因素。随着生物药研发需求增加，尤其是多抗、ADC、小核酸等复杂生物药对非人灵长类动物模型的依赖，实验猴市场供需缺口扩大。数据显示，食蟹猴采购单价在过去一年内显著上涨。昭衍新药通过提前布局，截至2025年末拥有超过2万只实验猴。\n昭衍新药通过重资产投入积累了实验动物资源，相关饲养及折旧成本有所上升。一季度新签订单约9.1亿元，同比增长111.6%；在手订单约31亿元，同比增长40.9%。公司指出，实验猴价格上涨在提升资产估值的同时，也增加了采购成本，对主营业务毛利率造成压力。此外，公司提示生物资产公允价值波动及市场情绪风险。\n昭衍新药上半年利润增长主要受资产重估驱动，主营业务的持续盈利能力及应对猴价周期波动的能力仍待市场检验。",
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
      "valuation_history_from": "20210726",
      "current_price": 48.06,
      "price": 48.06,
      "ma5": 49.07,
      "ma10": 46.79,
      "ma20": 42.48,
      "dist_ma5_pct": -2.1,
      "dist_ma10_pct": 2.7,
      "dist_ma20_pct": 13.1,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.4995,
        "sizing": "normal"
      },
      "margin": {
        "rzye_yi": 6.98,
        "pct_float": 2.29,
        "chg5_pct": 4.78,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "688046.SH",
      "fetch_time": "2026-07-24T11:40:56+0800",
      "name": "药康生物",
      "pe": 66.5206,
      "pb": 4.8281,
      "ps_ttm": 12.7946,
      "pcf_ttm": 42.5665,
      "valuation_percentile": 69.95,
      "total_shares": 410000000,
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
        "专精特新小巨人主题指数",
        "股权激励指数",
        "专精特新小巨人指数",
        "创新药指数",
        "医疗服务精选指数"
      ],
      "score_company": 8.3,
      "score_trend": 8.7,
      "score_value": 5.2,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年07月22日，业绩超预期引发股价大幅上涨，当日收涨 10.7% 。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 15% ，最新季度归母净利润同比增长 51% ，成长能力很强。"
        },
        {
          "tag": "预测",
          "text": " 7家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 3.0% ，较受外资机构青睐；公募基金持股 7.3% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月17日大跌 -20% ，股价跌停，抛压很重。"
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
          "content": "15:00 今天大涨的原因可能是公司预计2026年上半年净利润同比增长46.67%至60.78%，显示其实验动物模型产品与相关技术服务销售规模和盈利能力显著提升，利好业绩预期。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "公司发布2026半年报预告，股价盘中上涨 8.03% ，股价收盘涨幅 10.66%",
          "tags": [
            "股价上涨"
          ]
        },
        {
          "content": "16:06 药康生物发布2026年半年度业绩预告，预计实现归母净利润1.04亿元至1.14亿元，同比增长46.67%至60.78%；预计扣非净利润9200万元至1亿元，同比增长46.20%至58.92%。业绩增长主要得益于：海外市场本地化销售服务体系完善，客户规模扩大；国内生物医药行业景气度回升，功能药效业务板块收入提速；生产设施产能利用率提升带来规模效应，且期间费用率有所下降。公司将继续推进国际化战略，并加大研发投入。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 575576818.48,
      "revenue_yoy": 0.129206,
      "operating_profit": 120290164.38,
      "operating_profit_yoy": 0.212471,
      "net_profit": 109900074.6,
      "net_profit_yoy": 0.118982,
      "gross_profit": 368462244.84,
      "gross_profit_yoy": 0.135745,
      "cogs": 207114573.64,
      "gross_margin": 64.02,
      "pe_forward": null,
      "valuation_history_days": 270,
      "valuation_history_from": "20240425",
      "current_price": 27.0,
      "price": 27.0,
      "ma5": 25.22,
      "ma10": 25.28,
      "ma20": 23.38,
      "dist_ma5_pct": 7.0,
      "dist_ma10_pct": 6.8,
      "dist_ma20_pct": 15.5,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 0.86,
        "pct_float": 0.78,
        "chg5_pct": -32.9,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "600428.SH",
      "fetch_time": "2026-07-24T11:40:56+0800",
      "name": "中远海特",
      "pe": 16.1167,
      "pb": 1.7345,
      "ps_ttm": 1.2076,
      "pcf_ttm": 4.0897,
      "valuation_percentile": 65.7,
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
          "text": "近6月，股价涨幅超过A股市场 96% 的股票，收盘价接近 一年新高 ，走势较强。"
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
          "content": "2025年年度：每10股派3.25元",
          "tags": [
            "分红送转"
          ],
          "date": "2026-07-30"
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
        },
        {
          "content": "陈帅 任提名委员会委员",
          "tags": [
            "管理层变更"
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
      "valuation_history_days": 303,
      "valuation_history_from": "20210726",
      "current_price": 11.04,
      "price": 11.04,
      "ma5": 10.96,
      "ma10": 10.52,
      "ma20": 9.38,
      "dist_ma5_pct": 0.7,
      "dist_ma10_pct": 4.9,
      "dist_ma20_pct": 17.7,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.4995,
        "sizing": "normal"
      },
      "margin": {
        "rzye_yi": 3.84,
        "pct_float": 1.42,
        "chg5_pct": 9.24,
        "net5_repay_days": 3,
        "signal": "adding"
      }
    },
    {
      "code": "002975.SZ",
      "fetch_time": "2026-07-24T11:40:57+0800",
      "name": "博杰股份",
      "pe": 75.219,
      "pb": 7.4431,
      "ps_ttm": 8.3506,
      "pcf_ttm": 222.1764,
      "valuation_percentile": 73.79,
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
      "score_trend": 6.9,
      "score_value": 4.5,
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
      "valuation_history_days": 271,
      "valuation_history_from": "20220207",
      "current_price": 86.9,
      "price": 86.9,
      "ma5": 86.45,
      "ma10": 101.19,
      "ma20": 116.42,
      "dist_ma5_pct": 0.5,
      "dist_ma10_pct": -14.1,
      "dist_ma20_pct": -25.4,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6814,
        "sizing": "selective"
      }
    },
    {
      "code": "688222.SH",
      "fetch_time": "2026-07-24T11:40:57+0800",
      "name": "成都先导",
      "pe": 92.9251,
      "pb": 7.6743,
      "ps_ttm": 19.6832,
      "pcf_ttm": 49.0339,
      "valuation_percentile": 49.5,
      "total_shares": 400680000,
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
        "外资企业指数",
        "创新药指数",
        "合资企业指数",
        "反内卷指数",
        "医药数智化指数",
        "生物科技等权指数",
        "医疗物资出口指数",
        "医疗服务精选指数",
        "CRO指数",
        "基因检测指数"
      ],
      "score_company": 8.1,
      "score_trend": 6.7,
      "score_value": 5.7,
      "highlights": [
        {
          "tag": "收入",
          "text": "近3年，营业收入每年增长 21% ，收入成长性较强。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 10% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "订单",
          "text": "合同负债 4482万元 ，较上期增长 23% ，占2025年营收 8.5% ，在手订单充足。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 4.1% ，很受外资机构青睐。"
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
          "content": "成都先导：成都先导药物开发股份有限公司关于放弃对参股公司增资扩股的优先认购权暨关联交易的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "成都先导：成都先导药物开发股份有限公司关于制定部分公司治理制度的公告",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是国家第十二批集采明确豁免创新药，有利于保护创新药定价和研发回报，利好从事药物研发与技术服务的成都先导。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是医保/商保目录初审通过率92%、创新药预申报加速商业化且国家集采豁免创新药，预计将提升创新药申报与研发外包需求，利好成都先导。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 369793830.73,
      "revenue_yoy": 0.239797,
      "operating_profit": 103104064.01,
      "operating_profit_yoy": 2.9632,
      "net_profit": 91758272.13,
      "net_profit_yoy": 2.200974,
      "gross_profit": 202839802.09,
      "gross_profit_yoy": 0.378322,
      "cogs": 166954028.64,
      "gross_margin": 54.85,
      "pe_forward": null,
      "valuation_history_days": 259,
      "valuation_history_from": "20220418",
      "current_price": 28.2,
      "price": 28.2,
      "ma5": 29.65,
      "ma10": 32.56,
      "ma20": 31.35,
      "dist_ma5_pct": -4.9,
      "dist_ma10_pct": -13.4,
      "dist_ma20_pct": -10.0,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 0.7985,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.31,
        "pct_float": 4.69,
        "chg5_pct": -0.96,
        "net5_repay_days": 3,
        "signal": "neutral"
      }
    },
    {
      "code": "002192.SZ",
      "fetch_time": "2026-07-24T11:40:57+0800",
      "name": "融捷股份",
      "pe": 30.2029,
      "pb": 4.2458,
      "ps_ttm": 14.4523,
      "pcf_ttm": 85.5957,
      "valuation_percentile": 26.98,
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
      "score_value": 7.3,
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
          "tag": "公募",
          "text": "公募基金持股 3.1% ，较受内资机构青睐。"
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
          "content": "06:30 宁德时代旗下的雅江斯诺威矿业发展有限公司（以下简称斯诺威矿业）锂矿开发项目环境影响评价文件已获甘孜州生态环境局受理。该项目采矿规模规划为150万吨/年，目前已与代加工厂签订协议。斯诺威矿业拟与天齐锂业旗下天齐盛合、四川省自然资源投资集团旗下天府锂业合资共建“甲基卡1号尾矿库”，预计2028年建成。有知情人士表示，项目实际投产最快可能在2029年。\n斯诺威矿业已增资入股锂盐加工企业四川能投鼎盛锂业有限公司，持股比例为21%。根据测算，斯诺威项目达产后年平均营业收入预计为12.48亿元，利润总额预计为3.89亿元。甲基卡矿区规划涉及多家企业，包括融达锂业、天齐锂业及斯诺威矿业等，采选总规模规划为375万吨/年。\n斯诺威矿业、天齐盛合与天府锂业拟共同建设“甲基卡1号尾矿库”，预计2027年末具备排尾条件，2028年全面建成。此外，矿区取水工程拟由合资企业四川淼威水务有限公司建设，预计2026年9月开工；供电工程则由斯诺威矿业、天齐锂业、盛新锂能的合资企业四川天盛时代新能源有限公司负责建设。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "06:30 宁德时代旗下的雅江斯诺威新能源锂矿开发项目环境影响评价文件已获甘孜州生态环境局受理。该项目建成后采矿规模预计达150万吨/年。目前，斯诺威矿业已与天齐锂业旗下天齐盛合、四川省自然资源投资集团旗下天府锂业达成合作，拟合资共建“甲基卡1号尾矿库”，预计2028年全面建成。在配套选厂建成前，原矿将外运至四川星唯新材料科技有限公司进行代加工。\n斯诺威矿业已增资入股川能动力子公司鼎盛锂业，持股比例为21%，布局锂盐加工环节。根据测算，项目达产后年平均营业收入为12.48亿元，利润总额为3.89亿元。甲基卡矿区规划包括斯诺威矿业、融达锂业及天齐锂业等多个锂矿项目，采选总规模规划为375万吨/年。\n甲基卡1号尾矿库已于2026年5月完成立项备案，预计2028年投入运行。此外，矿区取水工程由斯诺威矿业与天齐盛合合资的四川淼威水务有限公司负责，供电工程由斯诺威矿业、天齐锂业、盛新锂能的合资企业四川天盛时代新能源有限公司建设。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/22～2027/01/22 张长虹(实际控制人)计划增持，变动价格说明：本次增持不设置价格区间，将根据市场整体走势及对公司股份价值的合理判断，在实施期限内择机实施增持计划，拟增持金额不超过 6000万元  ，拟增持金额不低于 3000万元  交易方式：通过深圳证券交易所交易系统允许的方式，包括但不限于集中竞价交易、大宗交易等方式增持公司股份",
          "tags": [
            "控股股东增持"
          ]
        },
        {
          "content": "回购总金额不超过1.00亿元，回购最高价不超过73.0元/股 （预案）",
          "tags": [
            "公司回购流通股"
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
      "valuation_history_from": "20210726",
      "current_price": 64.3,
      "price": 64.3,
      "ma5": 60.26,
      "ma10": 64.74,
      "ma20": 77.92,
      "dist_ma5_pct": 6.7,
      "dist_ma10_pct": -0.7,
      "dist_ma20_pct": -17.5,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6814,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 13.6,
        "pct_float": 8.16,
        "chg5_pct": -2.77,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "300438.SZ",
      "fetch_time": "2026-07-24T11:40:57+0800",
      "name": "鹏辉能源",
      "pe": 54.4286,
      "pb": 5.5178,
      "ps_ttm": 2.0814,
      "pcf_ttm": 28.3568,
      "valuation_percentile": 50.47,
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
        "锂电池指数",
        "养老金指数",
        "储能指数",
        "固态电池指数",
        "钠离子电池指数",
        "动力电池指数",
        "预期提升指数",
        "TWS耳机指数",
        "扭亏指数",
        "ETC指数"
      ],
      "score_company": 8.3,
      "score_trend": 7.2,
      "score_value": 6.7,
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
          "text": "近90天， 8家 机构给出评级，其中 88% 为“买入”，距目标价的上涨空间为 100% 。"
        },
        {
          "tag": "预测",
          "text": " 6家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 5.3% ，很受外资机构青睐；公募基金持股 13% ，很受内资机构青睐。"
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
          "content": "18:15 7月23日，电池产业链领涨。新能源电池ETF（159071）场内价格上涨3.93%。成份股中，明阳电气、金盘科技涨超10%，德业股份涨停，鹏辉能源涨超9%，阳光电源涨超7%，固德威、伊戈尔、上能电器涨超6%，亿纬锂能涨超4%。消息面上，发改委、能源局印发《可再生能源发展“十五五”规划》，提出到2030年可再生能源发电总装机达到35亿千瓦左右，风电和太阳能发电总装机达到28亿千瓦以上。东吴证券研报分析，随着容量电价机制落地及全球储能需求增长，储能产业链景气度有望持续。\n新能源电池ETF（159071）由华宝基金管理，跟踪国证新能源电池指数，风险等级为R3-中风险。投资人应阅读基金法律文件，了解风险收益特征。基金过往业绩不预示未来表现。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "10:22 2026年7月23日，受资产重组、业绩改善及股东增持等因素影响，新能股份盘中触及涨停。受此提振，新能源电池指数盘中上涨1.036%。储能电池ETF易方达(159566)盘中涨幅1.228%，成交额4365万元。该ETF前十大权重股包括阳光电源、亿纬锂能、宁德时代等。持仓方面，2026年二季度新进重仓股为海博思创、鹏辉能源。资金面上，储能电池ETF易方达近5个交易日主力资金累计净流入1182万元。东吴证券在《储能2026年中策略》中指出，全球储能市场需求增长，当前新能源电池指数市盈率为24.91倍。",
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
      "valuation_history_from": "20210726",
      "current_price": 60.44,
      "price": 60.44,
      "ma5": 59.71,
      "ma10": 63.33,
      "ma20": 71.37,
      "dist_ma5_pct": 1.2,
      "dist_ma10_pct": -4.6,
      "dist_ma20_pct": -15.3,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 8.46,
        "pct_float": 3.46,
        "chg5_pct": -15.48,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300475.SZ",
      "fetch_time": "2026-07-24T11:40:57+0800",
      "name": "香农芯创",
      "pe": 40.8121,
      "pb": 15.4678,
      "ps_ttm": 1.4815,
      "pcf_ttm": 18.3348,
      "valuation_percentile": 61.66,
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
      "score_company": 8.8,
      "score_trend": 6.6,
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
          "text": "公募基金持股 10% ，很受内资机构青睐。"
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
          "content": "17:47 上周A股市场整体调整，创业板50指数下跌10.67%。市场调整主要受科技成长板块资金流出影响。创业板50指数聚焦信息技术、新能源、金融科技及医药四大新质生产力赛道。截至2026年7月17日，创业板50ETF华安（159949）近六年ROE保持在15%至19%区间，2025年及2026年一季度归母净利润增速分别为21.58%和42.38%，当前估值37.88倍。2026年6月15日，指数调入天华新能、香农芯创、光库科技、迈为股份、罗博特科，调出神州泰岳、机器人、智飞生物、泰格医药、康龙化成。\n通信板块方面，新易盛、天孚通信发布上半年业绩预告，光通信行业受全球AI算力资本开支及产业景气度支撑，中长期配置价值受关注。新能源电池板块中，储能电池出货量增长，动力电池行业准入门槛提高，产业链盈利修复趋势持续。电子板块中，存储芯片与AI硬件产业链业绩表现突出，江波龙、北京君正、香农芯创上半年业绩预增，半导体设备及先进封装等环节景气度有望攀升。\n创业板50ETF华安（159949）跟踪创业板50指数，涵盖通信、电子、新能源电池、互联网金融、生物医药五大领域。该基金过去一年日均成交额19.64亿元，最新规模208.24亿元。本基金为股票型基金，具有较高风险与预期收益特征，过往业绩不预示未来表现。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "15:00 今天大跌的原因可能是海外存储巨头暴跌引发行业需求走弱与价格下探，压缩公司国产存储产品和电子元器件分销的收入与毛利，触发市场抛售。",
          "tags": [
            "快讯",
            "大跌原因"
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
      "valuation_history_from": "20210726",
      "current_price": 163.02,
      "price": 163.02,
      "ma5": 166.88,
      "ma10": 198.54,
      "ma20": 238.15,
      "dist_ma5_pct": -2.3,
      "dist_ma10_pct": -17.9,
      "dist_ma20_pct": -31.5,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 50.11,
        "pct_float": 6.83,
        "chg5_pct": -4.1,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301345.SZ",
      "fetch_time": "2026-07-24T11:40:58+0800",
      "name": "涛涛车业",
      "pe": 30.078,
      "pb": 7.5413,
      "ps_ttm": 6.2513,
      "pcf_ttm": 34.5782,
      "valuation_percentile": 78.23,
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
      "score_trend": 7.6,
      "score_value": 4.5,
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
          "tag": "订单",
          "text": "合同负债 6724万元 ，较上期增长 18% ，占2025年营收 1.7% ，在手订单充足。"
        },
        {
          "tag": "预测",
          "text": " 9家 机构预测，2026年-2028年营收和净利润每年增长均超过 25% ，未来成长较快。"
        },
        {
          "tag": "股东",
          "text": "北向资金持股 14% ，很受外资机构青睐；公募基金持股 10% ，很受内资机构青睐；2026年01月30日至2026年07月20日期间，股东户数减少 33% ，大资金买入。"
        },
        {
          "tag": "强势",
          "text": "近1年，股价涨幅超过A股市场 90% 的股票，走势较强。"
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
          "content": "16:42 涛涛车业已收到中国证监会境外发行上市备案通知书，拟发行不超过1393.40万股境外上市普通股并在香港联交所上市。过去三年，公司收入从21.44亿元增长至39.41亿元，净利润从2.80亿元攀升至8.16亿元。公司存货账面值从2023年末的7.15亿元增至2025年末的17.06亿元，存货周转天数从183天延长至232天，2025年末已计提存货减值拨备1427万元。\n涛涛车业由曹马涛于2015年发起设立，其创业资金由祖父曹桂成出资，父亲曹跃进执掌的涛涛集团提供设备、库存及专利支持。2023年3月，涛涛车业在深交所创业板上市。公司业务分为电动出行产品和动力运动产品，其中电动低速车业务增长迅速，2025年收入达19.57亿元，占总收入比重升至49.8%，经销商网络已覆盖美国大部分地区。\n受市场竞争加剧及低价竞品冲击，涛涛车业的电动滑板车、电动平衡车及电动自行车产品线收入出现下滑。目前，曹马涛正推动公司冲击港交所，计划实现A+H两地上市。股权结构显示，曹马涛合计控制公司67.41%的表决权，其胞妹曹侠淑控制约5.6%的表决权，父亲曹跃进担任公司非执行董事。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2027/09/21解禁2850.00万股，占总股本26.14%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2027-09-21"
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
      "valuation_history_days": 323,
      "valuation_history_from": "20250321",
      "current_price": 235.99,
      "price": 235.99,
      "ma5": 242.83,
      "ma10": 251.59,
      "ma20": 240.79,
      "dist_ma5_pct": -2.8,
      "dist_ma10_pct": -6.2,
      "dist_ma20_pct": -2.0,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 3.7,
        "pct_float": 4.48,
        "chg5_pct": 17.72,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "300037.SZ",
      "fetch_time": "2026-07-24T11:40:58+0800",
      "name": "新宙邦",
      "pe": 33.479,
      "pb": 4.2443,
      "ps_ttm": 4.1033,
      "pcf_ttm": 28.3215,
      "valuation_percentile": 55.05,
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
        "股权激励指数",
        "碳中和指数",
        "AI手机指数",
        "深圳本地股指数",
        "可转债正股指数",
        "新材料指数",
        "新能源汽车指数",
        "锂电池指数",
        "特斯拉指数",
        "储能指数",
        "固态电池指数"
      ],
      "score_company": 9.2,
      "score_trend": 7.2,
      "score_value": 5.8,
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
          "text": "近90天， 12家 机构给出评级，其中 75% 为“买入”，距目标价的上涨空间为 52% 。"
        },
        {
          "tag": "预测",
          "text": " 9家 机构预测，2026年-2028年营收和净利润每年增长均超过 15% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 12% ，很受内资机构青睐。"
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
          "content": "07:28 百川盈孚数据显示，7月23日，碳酸亚乙烯酯（VC）均价报20万元/吨，单日涨价2万元/吨，涨幅11.11%，近一周累计涨幅超过21%，最新价格已超过去年12月17.5万元/吨的高点，时隔4年多再度站上20万元/吨。据悉，本轮VC价格走高，主要由于强国标及储能需求提振，行业库存见底，电池巨头提前锁单等影响。A股中，拥有VC相关产能的上市公司合计有十多家。其中，华盛锂电目前拥有VC产能1.4万吨，富祥股份拟将VC年产能从8000吨提升至1万吨，泰和科技VC项目一期的设计产能为年产1万吨，孚日股份VC精制产能是1万吨。此外，新宙邦、海科新源拥有产能约1万吨，宏源药业、海辰药业分别拥有产能7000吨、6000吨。（人民财讯）",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "11:52 企查查APP显示，近日，淮安新原邦科技有限公司成立，法定代表人为易欢，注册资本为3000万元，经营范围包含：电子专用材料制造；电子专用材料研发；电子专用材料销售；合成材料销售；新材料技术研发等。企查查股权穿透显示，该公司由新宙邦持股的深圳新源邦科技有限公司全资持股。（人民财讯）",
          "tags": [
            "快讯"
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
      "valuation_history_from": "20210726",
      "current_price": 61.4,
      "price": 61.4,
      "ma5": 60.07,
      "ma10": 64.6,
      "ma20": 76.48,
      "dist_ma5_pct": 2.2,
      "dist_ma10_pct": -5.0,
      "dist_ma20_pct": -19.7,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.6594,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 8.88,
        "pct_float": 2.65,
        "chg5_pct": -4.99,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    }
  ],
  "active_positions": [
    {
      "code": "000811",
      "name": "冰轮环境",
      "entryDate": "2026-07-23",
      "entryPrice": 42.85,
      "targetPrice": 50.3,
      "stopLoss": 40.71,
      "currentStop": 40.71,
      "thesis": "液冷龙头+144%YTD，并购华源泰盟进展，合同负债¥13B创新高，AI数据中心散热需求结构性增长。近MA5(0.4%)，RPS20=99.56%极强。",
      "sector": "通用设备",
      "rps120": 99.28,
      "catalysts": [],
      "shares": 800,
      "allocation_pct": 4.0,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 0.5775,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 7.69,
        "pct_float": 1.83,
        "chg5_pct": 13.5,
        "net5_repay_days": 3,
        "signal": "adding"
      },
      "history": [
        {
          "date": "2026-07-23",
          "price": 42.85,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 冰轮环境"
        }
      ]
    },
    {
      "code": "002821",
      "name": "凯莱英",
      "entryDate": "2026-07-23",
      "entryPrice": 163.54,
      "targetPrice": 195.0,
      "stopLoss": 155.36,
      "currentStop": 155.36,
      "thesis": "CXO龙头回踩MA20支撑(0.0%偏离)，RPS20=99.6%极强短期动量，GLP-1/多肽CDMO高速增长，全球生物医药融资4倍YoY回暖，创新药BD出海H1达$997B。2026年营收目标+27%。",
      "sector": "医疗服务",
      "rps120": 95.17,
      "catalysts": [],
      "shares": 200,
      "allocation_pct": 5.0,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 0.6814,
        "sizing": "selective"
      },
      "margin": {
        "rzye_yi": 8.84,
        "pct_float": 1.7,
        "chg5_pct": -13.46,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      },
      "history": [
        {
          "date": "2026-07-23",
          "price": 163.54,
          "change_pct": 0,
          "action": "OPEN",
          "note": "LLM开仓 凯莱英"
        }
      ]
    }
  ],
  "position_prices": {
    "000811": {
      "code": "000811",
      "name": "冰轮环境",
      "date": "2026-07-24",
      "price": 41.2,
      "open": 40.63,
      "high": 42.57,
      "low": 40.03,
      "prev_close": 42.85,
      "change_pct": -3.85,
      "volume": 323669,
      "amount": 1342755310.34,
      "source": "sina",
      "mavol30": 3812.0,
      "volume_below_mavol30": false
    },
    "002821": {
      "code": "002821",
      "name": "凯莱英",
      "date": "2026-07-24",
      "price": 161.39,
      "open": 163.0,
      "high": 165.96,
      "low": 158.79,
      "prev_close": 163.54,
      "change_pct": -1.31,
      "volume": 49065,
      "amount": 796940558.75,
      "source": "sina",
      "mavol30": 981.2,
      "volume_below_mavol30": false
    }
  },
  "missed_opportunity_prices": [
    {
      "code": "688037",
      "name": "芯源微",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 340.06,
      "return_pct": null
    },
    {
      "code": "688200",
      "name": "华峰测控",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 362.13,
      "return_pct": null
    },
    {
      "code": "300285",
      "name": "国瓷材料",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 57.27,
      "return_pct": null
    },
    {
      "code": "001389",
      "name": "广合科技",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 161.28,
      "return_pct": null
    },
    {
      "code": "301536",
      "name": "星宸科技",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 131.68,
      "return_pct": null
    },
    {
      "code": "688629",
      "name": "华丰科技",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 158.08,
      "return_pct": null
    },
    {
      "code": "688046",
      "name": "药康生物",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 25.92,
      "return_pct": null
    },
    {
      "code": "002192",
      "name": "融捷股份",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 62.43,
      "return_pct": null
    },
    {
      "code": "000703",
      "name": "恒逸石化",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 15.74,
      "return_pct": null
    },
    {
      "code": "603127",
      "name": "昭衍新药",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 46.3,
      "return_pct": null
    },
    {
      "code": "600428",
      "name": "中远海特",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 10.81,
      "return_pct": null
    },
    {
      "code": "002980",
      "name": "华盛昌",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 81.44,
      "return_pct": null
    },
    {
      "code": "605376",
      "name": "博迁新材",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 140.38,
      "return_pct": null
    },
    {
      "code": "601958",
      "name": "金钼股份",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 20.83,
      "return_pct": null
    },
    {
      "code": "600961",
      "name": "株冶集团",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 22.65,
      "return_pct": null
    },
    {
      "code": "688630",
      "name": "芯碁微装",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 405.04,
      "return_pct": null
    },
    {
      "code": "002432",
      "name": "九安医疗",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 67.98,
      "return_pct": null
    },
    {
      "code": "688331",
      "name": "荣昌生物",
      "recommended_date": "2026-07-23",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 121.15,
      "return_pct": null
    },
    {
      "code": "002821",
      "name": "凯莱英",
      "recommended_date": "2026-07-22",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 161.39,
      "return_pct": null
    },
    {
      "code": "300373",
      "name": "扬杰科技",
      "recommended_date": "2026-07-22",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 90.39,
      "return_pct": null
    },
    {
      "code": "688777",
      "name": "中控技术",
      "recommended_date": "2026-07-22",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 82.49,
      "return_pct": null
    },
    {
      "code": "300684",
      "name": "中石科技",
      "recommended_date": "2026-07-21",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 46.86,
      "return_pct": null
    },
    {
      "code": "688378",
      "name": "奥来德",
      "recommended_date": "2026-07-21",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 38.35,
      "return_pct": null
    }
  ],
  "iv_sentiment": {
    "date": "2026-07-24",
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
        "current_iv": 0.164,
        "is_live": false,
        "iv_high": 0.2272,
        "iv_low": 0.1137,
        "iv_high_raw": 0.2625,
        "iv_low_raw": 0.1137,
        "iv_rank": 0.4432,
        "iv_rank_raw": 0.338,
        "iv_percentile": 0.5115,
        "iv_percentile_raw": 0.4933,
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
          0.1049,
          0.2282
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
        "current_iv": 0.1838,
        "is_live": false,
        "iv_high": 0.2476,
        "iv_low": 0.1201,
        "iv_high_raw": 0.3137,
        "iv_low_raw": 0.069,
        "iv_rank": 0.4995,
        "iv_rank_raw": 0.4691,
        "iv_percentile": 0.5734,
        "iv_percentile_raw": 0.5644,
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
          0.1096,
          0.2486
        ],
        "name": "300ETF",
        "desc": "沪深300",
        "interpretation": "中性"
      },
      {
        "underlying": "510500",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 216,
        "current_iv": 0.2863,
        "is_live": false,
        "iv_high": 0.3531,
        "iv_low": 0.194,
        "iv_high_raw": 0.4544,
        "iv_low_raw": 0.107,
        "iv_rank": 0.5801,
        "iv_rank_raw": 0.5161,
        "iv_percentile": 0.7731,
        "iv_percentile_raw": 0.7511,
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
            "iv": 0.3659
          }
        ],
        "sigma_range": [
          0.1754,
          0.3545
        ],
        "name": "500ETF",
        "desc": "中证500",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "588000",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 215,
        "current_iv": 0.5465,
        "is_live": false,
        "iv_high": 0.6222,
        "iv_low": 0.2467,
        "iv_high_raw": 0.7788,
        "iv_low_raw": 0.126,
        "iv_rank": 0.7985,
        "iv_rank_raw": 0.6441,
        "iv_percentile": 0.9116,
        "iv_percentile_raw": 0.88,
        "outliers_removed": 10,
        "outlier_details": [
          {
            "date": "2025-08-25",
            "iv": 0.6237
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
            "iv": 0.7006
          },
          {
            "date": "2026-07-22",
            "iv": 0.7788
          }
        ],
        "sigma_range": [
          0.1612,
          0.6237
        ],
        "name": "科创50",
        "desc": "科创板",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159915",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 218,
        "current_iv": 0.3867,
        "is_live": false,
        "iv_high": 0.4789,
        "iv_low": 0.2082,
        "iv_high_raw": 0.6363,
        "iv_low_raw": 0.2082,
        "iv_rank": 0.6594,
        "iv_rank_raw": 0.417,
        "iv_percentile": 0.7523,
        "iv_percentile_raw": 0.7387,
        "outliers_removed": 4,
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
          }
        ],
        "sigma_range": [
          0.1758,
          0.4818
        ],
        "name": "创业板ETF",
        "desc": "创业板",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "159922",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 212,
        "current_iv": 0.2933,
        "is_live": false,
        "iv_high": 0.3461,
        "iv_low": 0.1804,
        "iv_high_raw": 0.468,
        "iv_low_raw": 0.1804,
        "iv_rank": 0.6814,
        "iv_rank_raw": 0.3926,
        "iv_percentile": 0.8208,
        "iv_percentile_raw": 0.7838,
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
            "iv": 0.3716
          },
          {
            "date": "2026-07-22",
            "iv": 0.4068
          }
        ],
        "sigma_range": [
          0.1771,
          0.3466
        ],
        "name": "500ETF深",
        "desc": "深市中盘",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "159919",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 216,
        "current_iv": 0.1861,
        "is_live": false,
        "iv_high": 0.258,
        "iv_low": 0.1298,
        "iv_high_raw": 0.3431,
        "iv_low_raw": 0.1298,
        "iv_rank": 0.4393,
        "iv_rank_raw": 0.264,
        "iv_percentile": 0.5787,
        "iv_percentile_raw": 0.5631,
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
          0.1119,
          0.2587
        ],
        "name": "300ETF深",
        "desc": "深市宽基",
        "interpretation": "中性"
      },
      {
        "underlying": "159901",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 216,
        "current_iv": 0.2669,
        "is_live": false,
        "iv_high": 0.3391,
        "iv_low": 0.1682,
        "iv_high_raw": 0.4504,
        "iv_low_raw": 0.1682,
        "iv_rank": 0.5775,
        "iv_rank_raw": 0.3497,
        "iv_percentile": 0.7407,
        "iv_percentile_raw": 0.7207,
        "outliers_removed": 6,
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
            "iv": 0.3723
          },
          {
            "date": "2026-07-22",
            "iv": 0.3521
          }
        ],
        "sigma_range": [
          0.1467,
          0.3392
        ],
        "name": "深100ETF",
        "desc": "深市蓝筹",
        "interpretation": "偏高 (市场谨慎，波动率偏贵)"
      },
      {
        "underlying": "588080",
        "lookback_days": 252,
        "data_points": 224,
        "data_points_filtered": 218,
        "current_iv": 0.5356,
        "is_live": false,
        "iv_high": 0.6163,
        "iv_low": 0.184,
        "iv_high_raw": 0.756,
        "iv_low_raw": 0.184,
        "iv_rank": 0.8133,
        "iv_rank_raw": 0.6147,
        "iv_percentile": 0.8991,
        "iv_percentile_raw": 0.875,
        "outliers_removed": 6,
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
          }
        ],
        "sigma_range": [
          0.1657,
          0.6185
        ],
        "name": "科创板50",
        "desc": "科创板（备用代理）",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      }
    ],
    "overall_sentiment": {
      "signal": "偏悲观",
      "avg_iv_rank": 0.5961,
      "avg_iv_percentile": 0.7044,
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
    "allow_new_positions": false,
    "regime": "panic",
    "breadth_ratio": 0.111,
    "up": 548,
    "down": 4939,
    "positive_indices": [],
    "negative_indices": [
      "上证指数",
      "深证成指",
      "创业板指"
    ],
    "limit_ups": 32,
    "limit_downs": 4,
    "sizing_multiplier": 0.0,
    "hard_block": true,
    "reason": "Entry regime panic: breadth 0.11:1, 0/3 major indices green, 32 limit-ups / 4 limit-downs. Block new longs."
  },
  "rule_violations": {
    "status": "violations",
    "total_rules": 6,
    "total_violations": 2,
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
            "code": "000811",
            "name": "冰轮环境",
            "rule": "stop_proximity",
            "severity": "CRITICAL",
            "currentPrice": 41.2,
            "stopLoss": 40.71,
            "distance_pct": 1.19,
            "suggestion": "🔴 CRITICAL — only 1.2% above stop! Gap risk is real (03-03 lesson: 扬杰科技 gapped to -8.37%). Strongly recommend proactive stop-loss NOW. Don't wait for exact trigger."
          },
          {
            "code": "002821",
            "name": "凯莱英",
            "rule": "stop_proximity",
            "severity": "WATCH",
            "currentPrice": 161.39,
            "stopLoss": 155.36,
            "distance_pct": 3.74,
            "suggestion": "🟠 WATCH — 3.7% above stop. Monitor closely. No immediate action but be ready."
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
  "active_learnings": "## Active Rules (proven, hitRate ≥ 75%)\n- [h013] Strong breadth alone is not enough to force entries; without candidate RPS and MA-distance data, the correct momentum decision is to keep cash. (hitRate: 99%, n=129, confidence: 98%)\n- [h028] Today’s relative leaders are concentrated in communication equipment and adjacent tech hardware, while cyclicals/agri/resource laggards are being de-risked aggressively. (hitRate: 100%, n=47, confidence: 98%)\n- [h019] Bottom-list sectors should be treated as hard no-buy zones even when individual names still carry acceptable RPS readings. (hitRate: 100%, n=44, confidence: 98%)\n- [h027] MA-distance discipline remains critical inside hot sectors: a hot sector does not override chase risk when dist_ma5_pct exceeds 6% or dist_ma10_pct exceeds 8%. (hitRate: 100%, n=41, confidence: 98%)\n- [h023] Raising stops mechanically after +10% works well in weak tapes because it converts a fast winner into a low-risk hold without needing a fresh market call. (hitRate: 100%, n=36, confidence: 97%)\n- [h021] The MA-distance anti-chase rule is doing real work: several visually strong names fail because they are too far above short-term support. (hitRate: 98%, n=100, confidence: 97%)\n- [h017] Low-IV conditions around 16-22% IV rank do not justify freezing risk when breadth is 5.6:1; they argue for normal sizing but tighter discipline on chasing. (hitRate: 100%, n=26, confidence: 96%)\n- [h077] The hard block is preventing FOMO entries. 新宙邦 (宁德时代协议 catalyst, VCP SETUP) and 奥来德 (dist_ma5 0.3%) would have been tempting buys in V1. V2 correctly forces cash preservation in panic regime. (hitRate: 100%, n=10, confidence: 92%)\n\n## Working Hypotheses (testing, hitRate ≥ 65%)\n- [h024] Stop-proximity violations deserve proactive action before the hard stop is hit, especially in 科创板 names where gap risk can erase the remaining cushion quickly. (hitRate: 100%, n=5, confidence: 86%)\n",
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
