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
  "date": "2026-07-22",
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
    "timestamp": "2026-07-22T15:40:47.782830",
    "indices": {
      "上证指数": {
        "code": "sh000001",
        "close": 3867.034,
        "change_pct": 0.07,
        "date": "2026-07-22"
      },
      "深证成指": {
        "code": "sz399001",
        "close": 14061.44,
        "change_pct": -1.42,
        "date": "2026-07-22"
      },
      "创业板指": {
        "code": "sz399006",
        "close": 3566.73,
        "change_pct": -3.23,
        "date": "2026-07-22"
      },
      "科创50": {
        "code": "sh000688",
        "close": 1860.085,
        "change_pct": -2.26,
        "date": "2026-07-22"
      }
    },
    "breadth": {
      "up": 1530,
      "down": 3875,
      "flat": 121,
      "total": 5526,
      "distribution": {
        "f10": 10,
        "f7_10": 66,
        "f4_7": 422,
        "f2_4": 1461,
        "f0_2": 1916,
        "f0": 121,
        "r0_2": 930,
        "r2_4": 305,
        "r4_7": 168,
        "r7_10": 79,
        "r10": 48
      }
    },
    "sectors": {
      "top5": [
        {
          "板块名称": "贵金属",
          "涨跌幅": 6.45
        },
        {
          "板块名称": "医疗美容",
          "涨跌幅": 6.18
        },
        {
          "板块名称": "油服工程",
          "涨跌幅": 4.71
        },
        {
          "板块名称": "工业金属",
          "涨跌幅": 4.26
        },
        {
          "板块名称": "油气开采Ⅱ",
          "涨跌幅": 4.25
        }
      ],
      "bottom5": [
        {
          "板块名称": "玻璃玻纤",
          "涨跌幅": -6.88
        },
        {
          "板块名称": "通信设备",
          "涨跌幅": -4.99
        },
        {
          "板块名称": "游戏Ⅱ",
          "涨跌幅": -4.24
        },
        {
          "板块名称": "元件",
          "涨跌幅": -3.85
        },
        {
          "板块名称": "光学光电子",
          "涨跌幅": -3.24
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
        "market_cap": 165.6881,
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
        "market_cap": 379.3723,
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
        "market_cap": 449.2138,
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
        "market_cap": 587.4855,
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
        "market_cap": 169.1499,
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
        "market_cap": 426.3685,
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
        "market_cap": 218.1317,
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
        "market_cap": 600.5222,
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
        "market_cap": 272.071,
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
        "market_cap": 309.8533,
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
        "highlights_count": 6,
        "market_cap": 338.4513,
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
        "market_cap": 702.1474,
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
        "code": "002655",
        "code_full": "002655.SZ",
        "name": "共达电声",
        "source_date": "2026/07/22",
        "highlights_count": 4,
        "market_cap": 97.0887,
        "pe": 14.4,
        "risks_count": 4,
        "rps20": 87.14,
        "rps60": 99.34,
        "rps120": 98.17,
        "rps250": 94.73,
        "ma10": 36.02,
        "vcp_quality": null,
        "ma5": 32.57,
        "ma20": 39.37,
        "dist_ma5_pct": -12.3,
        "dist_ma10_pct": -20.7,
        "dist_ma20_pct": -27.4
      },
      {
        "code": "001389",
        "code_full": "001389.SZ",
        "name": "广合科技",
        "source_date": "2026/07/22",
        "highlights_count": 6,
        "market_cap": 788.4789,
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
        "market_cap": 580.6065,
        "pe": 5.9,
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
        "market_cap": 489.663,
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
        "source_date": "2026/07/22",
        "highlights_count": 5,
        "market_cap": 740.1221,
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
        "market_cap": 209.4763,
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
        "highlights_count": 5,
        "market_cap": 170.3116,
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
        "highlights_count": 4,
        "market_cap": 793.6453,
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
        "market_cap": 251.7783,
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
        "market_cap": 57.3493,
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
        "market_cap": 104.2516,
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
        "market_cap": 160.6433,
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
        "market_cap": 579.3488,
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
        "market_cap": 185.3465,
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
        "market_cap": 680.423,
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
        "market_cap": 577.7499,
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
        "market_cap": 94.9333,
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
        "market_cap": 104.0472,
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
        "market_cap": 251.9105,
        "pe": 21.9,
        "risks_count": 1,
        "rps20": 88.22,
        "rps60": 89.08,
        "rps120": 93.73,
        "rps250": 93.25,
        "ma10": 25.17,
        "vcp_quality": null,
        "ma5": 23.1,
        "ma20": 28.33,
        "dist_ma5_pct": 1.4,
        "dist_ma10_pct": -7.0,
        "dist_ma20_pct": -17.3
      },
      {
        "code": "688392",
        "code_full": "688392.SH",
        "name": "骄成超声",
        "source_date": "2026/04/22",
        "highlights_count": 6,
        "market_cap": 187.5922,
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
        "market_cap": 357.5603,
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
        "code": "300373",
        "code_full": "300373.SZ",
        "name": "扬杰科技",
        "source_date": "2026/07/22",
        "highlights_count": 4,
        "market_cap": 523.2439,
        "pe": 12.5,
        "risks_count": 0,
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
        "market_cap": 137.1048,
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
        "market_cap": 592.691,
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
        "code": "002192",
        "code_full": "002192.SZ",
        "name": "融捷股份",
        "source_date": "2026/07/20",
        "highlights_count": 5,
        "market_cap": 156.8317,
        "pe": 18.6,
        "risks_count": 5,
        "rps20": 53.03,
        "rps60": 92.36,
        "rps120": 91.66,
        "rps250": 94.22,
        "ma10": 70.95,
        "vcp_quality": null,
        "ma5": 62.0,
        "ma20": 80.53,
        "dist_ma5_pct": -6.1,
        "dist_ma10_pct": -17.9,
        "dist_ma20_pct": -27.7
      },
      {
        "code": "601958",
        "code_full": "601958.SH",
        "name": "金钼股份",
        "source_date": "2026/07/03",
        "highlights_count": 7,
        "market_cap": 691.4613,
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
        "code": "300747",
        "code_full": "300747.SZ",
        "name": "锐科激光",
        "source_date": "2026/07/22",
        "highlights_count": 4,
        "market_cap": 190.0454,
        "pe": 8.0,
        "risks_count": 1,
        "rps20": 88.58,
        "rps60": 89.99,
        "rps120": 91.27,
        "rps250": 90.94,
        "ma10": 39.12,
        "vcp_quality": null,
        "ma5": 35.19,
        "ma20": 45.61,
        "dist_ma5_pct": -10.9,
        "dist_ma10_pct": -19.9,
        "dist_ma20_pct": -31.3
      },
      {
        "code": "002975",
        "code_full": "002975.SZ",
        "name": "博杰股份",
        "source_date": "2026/06/16",
        "highlights_count": 5,
        "market_cap": 177.7436,
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
        "market_cap": 716.3219,
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
        "market_cap": 149.1855,
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
        "source_date": "2026/07/22",
        "highlights_count": 5,
        "market_cap": 782.2566,
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
        "market_cap": 168.8256,
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
        "market_cap": 449.0148,
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
        "code": "688046",
        "code_full": "688046.SH",
        "name": "药康生物",
        "source_date": "2026/07/22",
        "highlights_count": 4,
        "market_cap": 110.7,
        "pe": 4.2,
        "risks_count": 1,
        "rps20": 95.94,
        "rps60": 92.46,
        "rps120": 88.23,
        "rps250": 90.49,
        "ma10": 25.15,
        "vcp_quality": null,
        "ma5": 25.94,
        "ma20": 22.32,
        "dist_ma5_pct": -10.6,
        "dist_ma10_pct": -7.7,
        "dist_ma20_pct": 3.9
      },
      {
        "code": "002947",
        "code_full": "002947.SZ",
        "name": "恒铭达",
        "source_date": "2026/03/12",
        "highlights_count": 4,
        "market_cap": 148.9857,
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
        "market_cap": 336.4874,
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
        "market_cap": 277.0905,
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
        "market_cap": 354.5108,
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
        "market_cap": 360.1368,
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
        "market_cap": 352.9965,
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
      "code": "002980.SZ",
      "fetch_time": "2026-07-22T15:40:47+0800",
      "name": "华盛昌",
      "pe": 213.3745,
      "pb": 14.6762,
      "ps_ttm": 21.314,
      "pcf_ttm": null,
      "valuation_percentile": 97.04,
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
      "score_company": 7.7,
      "score_trend": 7.5,
      "score_value": 3.5,
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
          "text": "近3天，日均换手率 12% ，短线资金追逐，波动风险较高。"
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
      "valuation_history_days": 258,
      "valuation_history_from": "20220418",
      "current_price": 96.63,
      "price": 96.63,
      "ma5": 97.66,
      "ma10": 101.51,
      "ma20": 109.13,
      "dist_ma5_pct": -1.1,
      "dist_ma10_pct": -4.8,
      "dist_ma20_pct": -11.5,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      }
    },
    {
      "code": "605376.SH",
      "fetch_time": "2026-07-22T15:40:47+0800",
      "name": "博迁新材",
      "pe": 156.1493,
      "pb": 21.876,
      "ps_ttm": 28.9214,
      "pcf_ttm": 6659.365,
      "valuation_percentile": 92.21,
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
        "专精特新小巨人主题指数",
        "资源股",
        "专精特新小巨人指数",
        "预期提升指数",
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
          "content": "21:18 博迁新材（605376）今日涨停，全天换手率7.65%，成交额27.12亿元，振幅22.23%。因日振幅值达22.23%，该股登上龙虎榜。数据显示，机构专用席位合计买入1.04亿元，卖出1.02亿元，净买入235.71万元；沪股通专用席位买入1.38亿元，卖出4.04亿元，净卖出2.66亿元；营业部席位合计净买入2.07亿元。上榜前五大买卖营业部合计成交14.33亿元，净卖出5633.46万元。资金流向方面，今日主力资金净流入1434.28万元，其中特大单净流入6175.69万元，大单净流出4741.41万元。截至7月20日，两融余额为8.38亿元，其中融资余额8.32亿元，融券余额642.81万元。公司一季度实现营业收入4.10亿元，同比增长64.02%；净利润7162.63万元，同比增长49.64%。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "17:28 博迁新材公告，公司计划以公司及子公司江苏广豫储能材料有限公司和宁波广迁电子材料有限公司为项目实施主体，分别投资建设“纳米金属镍粉精细化分级扩产项目”“200nm及以下镍粉精细分级扩产项目”“年产600吨超细金属粉体材料项目”，投资金额分别为约3500万元、8900万元和7750万元，总投资金额约2.02亿元。项目目前处于前期筹备阶段，尚未开始建设。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "09:49股价达到 271.52 元，创历史新高",
          "tags": [
            "股价新高"
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
      "current_price": 149.42,
      "price": 149.42,
      "ma5": 176.58,
      "ma10": 209.6,
      "ma20": 215.54,
      "dist_ma5_pct": -15.4,
      "dist_ma10_pct": -28.7,
      "dist_ma20_pct": -30.7,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.8503,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.36,
        "pct_float": 2.16,
        "chg5_pct": -23.81,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301396.SZ",
      "fetch_time": "2026-07-22T15:40:47+0800",
      "name": "宏景科技",
      "pe": 1281.4696,
      "pb": 37.2019,
      "ps_ttm": 37.2415,
      "pcf_ttm": 21.0944,
      "valuation_percentile": 93.29,
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
        "专精特新小巨人指数",
        "QFII重仓指数",
        "AI算力指数",
        "高应收账款指数"
      ],
      "score_company": 6.8,
      "score_trend": 6.9,
      "score_value": 3.8,
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
      "valuation_history_days": 408,
      "valuation_history_from": "20241111",
      "current_price": 192.52,
      "price": 192.52,
      "ma5": 223.42,
      "ma10": 251.44,
      "ma20": 254.91,
      "dist_ma5_pct": -13.8,
      "dist_ma10_pct": -23.4,
      "dist_ma20_pct": -24.5,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 15.21,
        "pct_float": 5.24,
        "chg5_pct": -18.36,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688630.SH",
      "fetch_time": "2026-07-22T15:40:47+0800",
      "name": "芯碁微装",
      "pe": 169.564,
      "pb": 10.7161,
      "ps_ttm": 34.956,
      "pcf_ttm": 204.1656,
      "valuation_percentile": 95.99,
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
        "专精特新小巨人指数",
        "半导体产业指数",
        "股权激励指数",
        "预期提升指数",
        "万得预增指数",
        "半导体设备指数",
        "光刻机指数",
        "专用设备精选指数"
      ],
      "score_company": 9.1,
      "score_trend": 8.1,
      "score_value": 3.6,
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
          "content": "09:21 港股开盘，恒生指数跌0.61%，恒生科技指数跌0.71%。个股方面，沪上阿姨涨14.07%，智谱涨6.64%，灵宝黄金涨6.24%，敏华控股涨6.03%，芯碁微装涨5.84%；滔搏跌14.66%，贝壳-W跌3.27%，网易跌3.26%。",
          "tags": [
            "快讯"
          ]
        },
        {
          "content": "13:36 7月16日午后，半导体设备板块出现持续下挫行情。\n\n其中，圣晖集成股价连续2个交易日跌停。精测电子跌幅超过10%。此外，先导智能、芯碁微装、华海清科、和林微纳、赛腾股份等个股跌幅均超过6%。",
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
      "valuation_history_days": 266,
      "valuation_history_from": "20230403",
      "current_price": 359.78,
      "price": 359.78,
      "ma5": 417.97,
      "ma10": 456.39,
      "ma20": 460.9,
      "dist_ma5_pct": -13.9,
      "dist_ma10_pct": -21.2,
      "dist_ma20_pct": -21.9,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.59,
        "pct_float": 1.8,
        "chg5_pct": -9.66,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301362.SZ",
      "fetch_time": "2026-07-22T15:40:47+0800",
      "name": "民爆光电",
      "pe": 115.626,
      "pb": 7.0448,
      "ps_ttm": 10.2063,
      "pcf_ttm": 81.4784,
      "valuation_percentile": 92.98,
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
        "专精特新小巨人指数",
        "QFII重仓指数",
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
          "text": "近3天，日均换手率 15% ，短线资金追逐，波动风险较高。"
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
      "valuation_history_days": 222,
      "valuation_history_from": "20250804",
      "current_price": 124.8,
      "price": 124.8,
      "ma5": 139.31,
      "ma10": 147.05,
      "ma20": 173.75,
      "dist_ma5_pct": -10.4,
      "dist_ma10_pct": -15.1,
      "dist_ma20_pct": -28.2,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 2.31,
        "pct_float": 4.79,
        "chg5_pct": -27.3,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "000811.SZ",
      "fetch_time": "2026-07-22T15:40:47+0800",
      "name": "冰轮环境",
      "pe": 72.5234,
      "pb": 6.627,
      "ps_ttm": 5.8378,
      "pcf_ttm": 53.2406,
      "valuation_percentile": 99.24,
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
        "山东省国资指数",
        "空气能热泵指数",
        "燃料电池指数",
        "集装箱指数",
        "通用机械精选指数",
        "仪器仪表精选指数",
        "新能源设备指数",
        "冬奥会指数",
        "冷链物流指数",
        "地热指数",
        "地热能指数",
        "余热利用指数",
        "核电通风与空气处理指数",
        "核电阀门指数"
      ],
      "score_company": 9.0,
      "score_trend": 8.4,
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
      "valuation_history_from": "20210722",
      "current_price": 43.26,
      "price": 43.26,
      "ma5": 48.15,
      "ma10": 51.34,
      "ma20": 50.31,
      "dist_ma5_pct": -10.1,
      "dist_ma10_pct": -15.7,
      "dist_ma20_pct": -14.0,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 7.01,
        "pct_float": 1.62,
        "chg5_pct": -14.68,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688257.SH",
      "fetch_time": "2026-07-22T15:40:47+0800",
      "name": "新锐股份",
      "pe": 44.312,
      "pb": 8.3184,
      "ps_ttm": 7.0771,
      "pcf_ttm": 71.5618,
      "valuation_percentile": 93.6,
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
        "专精特新小巨人指数",
        "股权激励指数",
        "有色金属指数",
        "万得预增指数",
        "IPO现场检查指数",
        "通用机械精选指数",
        "仪器仪表精选指数",
        "苏州工业园区指数"
      ],
      "score_company": 8.2,
      "score_trend": 7.4,
      "score_value": 3.7,
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
      "valuation_history_days": 329,
      "valuation_history_from": "20231030",
      "current_price": 68.08,
      "price": 68.08,
      "ma5": 78.03,
      "ma10": 90.98,
      "ma20": 94.2,
      "dist_ma5_pct": -12.8,
      "dist_ma10_pct": -25.2,
      "dist_ma20_pct": -27.7,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 13.72,
        "pct_float": 5.91,
        "chg5_pct": -12.59,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300285.SZ",
      "fetch_time": "2026-07-22T15:40:47+0800",
      "name": "国瓷材料",
      "pe": 97.3555,
      "pb": 8.4449,
      "ps_ttm": 12.8542,
      "pcf_ttm": 68.1259,
      "valuation_percentile": 79.61,
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
      "score_trend": 7.4,
      "score_value": 4.3,
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
          "text": "近90天， 16家 机构给出评级，其中 69% 为“买入”，距目标价的上涨空间为 41% 。"
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
          "text": "近20天，日均换手率 12% ，短线资金追逐，波动风险较高。"
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
          "content": "17:02 7月21日，市场探底回升，创业板指涨超7%，科创50指数涨10.73%。沪深两市成交额2.96万亿元，较前一交易日放量2550亿元。盘面热点轮动，全市场超3100只个股上涨。芯片产业链爆发，雅克科技、亚翔集成、东微半导、北方华创、臻宝科技、新洁能、金海通等涨停。PCB概念走强，宏和科技、金禄电子、广合科技涨停。CPO概念震荡走高，光迅科技涨停，中际旭创涨超13%。算力租赁概念中嘉博创、利通电子涨停。氧化锆概念东方锆业、国瓷材料、三祥新材涨停。油气概念调整。截至收盘，沪指涨1.79%，深成指涨4.81%，创业板指涨7.05%。芯片产业链中，半导体设备领涨，长川科技、北方华创、拓荆科技、华海清科、芯源微等涨停。据全球半导体行业协会（SEMI）报告，预计2026年全球半导体设备销售额将增长23.2%至1659亿美元，2028年将达2295亿美元。PCB、CPO等算力硬件股走高，联特科技、中富电路、金禄电子、生益科技、广合科技等涨停。新易盛在电话会议中表示，1.6T光模块Q2出货量较Q1增长，预计Q3/Q4放量节奏加快。瑞银证券指出，科技板块交易拥挤度缓解后，科技与AI仍是下半年市场主线。\n个股方面，科技赛道全线反弹。半导体方向，兆易创新涨停，雅克科技、华虹宏力、长电科技、通富微电、长川科技等涨停，中芯国际、澜起科技、佰维存储等涨超10%。算力硬件方面，中际旭创涨超13%，生益科技、宏和科技、广合科技等涨停。算力租赁概念中嘉博创、美利云2连板。紫光股份涨停，共进股份录得3天2板。MLCC概念国瓷材料20CM涨停，三环集团涨超18%。后市方面，双创板块放量长阳站稳5日均线，短线止跌企稳。市场要闻方面，腾讯云表示将大规模部署国产化算力，预计2026年Q4部署NPO超级节点。国家药监局批准一款新靶点创新药上市，用于治疗1型发作性睡病。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "16:30 国瓷材料今日涨19.99%，成交额61.00亿元，换手率13.15%，盘后龙虎榜数据显示，深股通专用席位买入4.35亿元并卖出5.65亿元，有4家机构专用席位净卖出2.35亿元。",
          "tags": [
            "快讯"
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
      "valuation_history_from": "20210722",
      "current_price": 56.62,
      "price": 56.62,
      "ma5": 64.84,
      "ma10": 75.6,
      "ma20": 81.7,
      "dist_ma5_pct": -12.7,
      "dist_ma10_pct": -25.1,
      "dist_ma20_pct": -30.7,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 28.38,
        "pct_float": 5.55,
        "chg5_pct": -15.44,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300806.SZ",
      "fetch_time": "2026-07-22T15:40:49+0800",
      "name": "斯迪克",
      "pe": 412.6346,
      "pb": 11.654,
      "ps_ttm": 8.7712,
      "pcf_ttm": 310.9923,
      "valuation_percentile": 95.74,
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
        "专精特新小巨人主题指数",
        "资源股",
        "专精特新小巨人指数",
        "QFII重仓指数",
        "中小创蓝筹指数",
        "对日反制指数",
        "MLCC指数"
      ],
      "score_company": 7.8,
      "score_trend": 6.8,
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
          "text": "近90天， 5家 机构给出评级，其中 80% 为“买入”，距目标价的上涨空间为 35% 。"
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
          "content": "2026/07/20～2027/01/20 吴江(董事，财务总监，董事会秘书)计划增持，变动价格说明：本次增持计划不设价格区间，将根据公司股票价格波动情况及资本市场整体趋势，择机实施增持计划 ，拟增持金额不低于 1250万元  交易方式：通过深圳证券交易所交易系统允许的方式（包括但不限于集中竞价、大宗交易等）增持公司股份。",
          "tags": [
            "管理层增持"
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
      "current_price": 63.91,
      "price": 63.91,
      "ma5": 73.86,
      "ma10": 82.68,
      "ma20": 91.93,
      "dist_ma5_pct": -13.5,
      "dist_ma10_pct": -22.7,
      "dist_ma20_pct": -30.5,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 2.04,
        "pct_float": 1.01,
        "chg5_pct": 40.42,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "688300.SH",
      "fetch_time": "2026-07-22T15:40:49+0800",
      "name": "联瑞新材",
      "pe": 102.8568,
      "pb": 18.71,
      "ps_ttm": 26.4654,
      "pcf_ttm": 133.1009,
      "valuation_percentile": 97.61,
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
        "专精特新小巨人主题指数",
        "资源股",
        "专精特新小巨人指数",
        "可转债正股指数",
        "半导体材料指数",
        "HBM指数"
      ],
      "score_company": 8.5,
      "score_trend": 6.3,
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
        },
        {
          "content": "联瑞新材：联瑞新材关于“联瑞转债”开始转股的公告",
          "tags": [
            "重要公告"
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
      "valuation_history_days": 283,
      "valuation_history_from": "20211115",
      "current_price": 141.0,
      "price": 141.0,
      "ma5": 163.78,
      "ma10": 182.89,
      "ma20": 207.32,
      "dist_ma5_pct": -13.9,
      "dist_ma10_pct": -22.9,
      "dist_ma20_pct": -32.0,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.57,
        "pct_float": 2.62,
        "chg5_pct": -14.38,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "600869.SH",
      "fetch_time": "2026-07-22T15:40:49+0800",
      "name": "远东股份",
      "pe": 308.8819,
      "pb": 7.908,
      "ps_ttm": 1.1851,
      "pcf_ttm": 35.7399,
      "valuation_percentile": 90.34,
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
        "特高压指数",
        "触板指数",
        "智能电网指数",
        "高低压设备精选指数",
        "电气自动化设备精选指数",
        "三元锂电池指数",
        "虚拟电厂指数",
        "光纤指数",
        "电线电缆指数",
        "泛在电力物联网指数",
        "碳纤维指数"
      ],
      "score_company": 7.2,
      "score_trend": 6.4,
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
      "valuation_history_from": "20210722",
      "current_price": 17.06,
      "price": 17.06,
      "ma5": 19.8,
      "ma10": 23.4,
      "ma20": 28.96,
      "dist_ma5_pct": -13.8,
      "dist_ma10_pct": -27.1,
      "dist_ma20_pct": -41.1,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.8503,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 14.23,
        "pct_float": 3.98,
        "chg5_pct": -18.14,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688037.SH",
      "fetch_time": "2026-07-22T15:40:49+0800",
      "name": "芯源微",
      "pe": 995.1795,
      "pb": 25.0256,
      "ps_ttm": 35.0411,
      "pcf_ttm": null,
      "valuation_percentile": 93.43,
      "total_shares": 201766496,
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
        "华为平台指数",
        "半导体产业指数",
        "芯片指数",
        "半导体精选指数",
        "中芯国际产业链指数",
        "长鑫存储指数",
        "半导体设备指数",
        "长江存储指数",
        "华为合作半导体企业指数",
        "限售解禁指数",
        "即将解禁指数",
        "光刻机指数"
      ],
      "score_company": 7.5,
      "score_trend": 8.5,
      "score_value": 3.6,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年04月30日，业绩超预期引发股价大幅上涨，当日收涨 13.2% 。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 3.9% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "预测",
          "text": " 9家 机构预测，2026年-2028年营收和净利润每年增长均超过 25% ，未来成长较快。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 25% ，很受内资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年07月01日大跌 -7.07% ，且成交额为近20日均值的 1.71倍 ，抛压很重。"
        },
        {
          "tag": "收益",
          "text": "近12月，经营活动净收益占利润总额 -108% ，扣非净利润占净利润 20% ，收益质量很低。"
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
          "content": "03:07 A股半导体公司上半年业绩大面积预喜，以江波龙为代表的存储模组企业表现突出。业绩增长主要受AI算力需求爆发及产品涨价驱动，实现营收与利润同步增长。业内分析认为，随着北美云厂商资本开支增加及大模型商业化落地，AI算力需求有望维持高增长，带动算力链条细分环节景气度。截至7月21日，45家披露预告的半导体公司中，42家实现盈利，39家归母净利润同比增长。存储产业方面，TrendForce集邦咨询预计第三季度DRAM及NAND Flash合约价仍将上涨，但涨幅较前几季度收窄。\n半导体设备板块业绩表现扎实，富创精密、先导基电、长川科技等公司上半年净利润均实现同比增长。受益于全球半导体先进制造及存储芯片扩产，半导体设备市场需求快速增长，SEMI上调了2026年全球前道半导体设备市场规模增速预期。目前国内外设备商交付压力较大，交期普遍延长。阿斯麦财报显示其营收与净利润均超预期，并计划在2027年扩产EUV设备。中信建投认为，半导体产业链定价权正向设备与零部件环节结构性上移。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "19:48 7月21日，科创芯片板块出现上涨，科创芯片ETF华宝（589190）场内价格上涨15.31%。个股方面，华虹宏力、芯源微、中科飞测、东芯股份、杰华特等10只股票涨停，中微公司、澜起科技、寒武纪、中芯国际等上涨超10%。市场分析认为，此次反弹受海外市场表现及全球半导体设备销售额增长预期等因素影响。东方财富证券与华安证券认为，科技板块前期回调后配置性价比显现，AI产业景气逻辑持续，业绩驱动行情有望延续。\n科创芯片ETF华宝及其联接基金的申购赎回费率及销售服务费根据持有期限和金额设定，具体费率标准详见基金法律文件。\n科创芯片ETF华宝及其联接基金跟踪上证科创板芯片指数，该指数历史业绩不预示未来表现。基金管理人评估该基金风险等级为R4-中高风险，投资者需根据自身风险承受能力审慎投资。基金过往业绩不代表未来表现，投资有风险。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/21解禁13.92万股，占总股本0.07%",
          "tags": [
            "限售股票解禁"
          ],
          "date": "2026-07-21"
        }
      ],
      "report_period": "20250930",
      "revenue": 990266469.06,
      "revenue_yoy": -0.103514,
      "operating_profit": -23858997.6,
      "operating_profit_yoy": -1.201317,
      "net_profit": -26210297.27,
      "net_profit_yoy": -1.249562,
      "gross_profit": 341834089.41,
      "gross_profit_yoy": -0.159595,
      "cogs": 648432379.65,
      "gross_margin": 34.52,
      "pe_forward": null,
      "valuation_history_days": 277,
      "valuation_history_from": "20211216",
      "current_price": 310.59,
      "price": 310.59,
      "ma5": 360.59,
      "ma10": 376.85,
      "ma20": 338.48,
      "dist_ma5_pct": -13.9,
      "dist_ma10_pct": -17.6,
      "dist_ma20_pct": -8.2,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.41,
        "pct_float": 0.75,
        "chg5_pct": -24.22,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002655.SZ",
      "fetch_time": "2026-07-22T15:40:49+0800",
      "name": "共达电声",
      "pe": 168.5987,
      "pb": 11.6791,
      "ps_ttm": 6.759,
      "pcf_ttm": 199.6595,
      "valuation_percentile": 91.33,
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
      "score_trend": 7.1,
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
          "text": "最新综合估值高于近十年 91% 的时间，处于历史高位。"
        },
        {
          "tag": "评级",
          "text": "近6月，没有机构发布研究报告，机构关注度低。"
        },
        {
          "tag": "波动",
          "text": "2026年06月23日，换手率 26% ，短线资金追逐，波动风险较高。"
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
        },
        {
          "content": "共达电声：共达电声股份有限公司关于完成工商变更登记并换发营业执照的公告",
          "tags": [
            "重要公告"
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
      "valuation_history_from": "20210722",
      "current_price": 28.57,
      "price": 28.57,
      "ma5": 32.57,
      "ma10": 36.02,
      "ma20": 39.37,
      "dist_ma5_pct": -12.3,
      "dist_ma10_pct": -20.7,
      "dist_ma20_pct": -27.4,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      }
    },
    {
      "code": "001389.SZ",
      "fetch_time": "2026-07-22T15:40:49+0800",
      "name": "广合科技",
      "pe": 67.5074,
      "pb": 11.4053,
      "ps_ttm": 12.5505,
      "pcf_ttm": 69.1151,
      "valuation_percentile": 89.47,
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
      "score_trend": 8.1,
      "score_value": 4.0,
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
          "content": "17:02 7月21日，市场探底回升，创业板指涨超7%，科创50指数涨10.73%。沪深两市成交额2.96万亿元，较前一交易日放量2550亿元。盘面热点轮动，全市场超3100只个股上涨。芯片产业链爆发，雅克科技、亚翔集成、东微半导、北方华创、臻宝科技、新洁能、金海通等涨停。PCB概念走强，宏和科技、金禄电子、广合科技涨停。CPO概念震荡走高，光迅科技涨停，中际旭创涨超13%。算力租赁概念中嘉博创、利通电子涨停。氧化锆概念东方锆业、国瓷材料、三祥新材涨停。油气概念调整。截至收盘，沪指涨1.79%，深成指涨4.81%，创业板指涨7.05%。芯片产业链中，半导体设备领涨，长川科技、北方华创、拓荆科技、华海清科、芯源微等涨停。据全球半导体行业协会（SEMI）报告，预计2026年全球半导体设备销售额将增长23.2%至1659亿美元，2028年将达2295亿美元。PCB、CPO等算力硬件股走高，联特科技、中富电路、金禄电子、生益科技、广合科技等涨停。新易盛在电话会议中表示，1.6T光模块Q2出货量较Q1增长，预计Q3/Q4放量节奏加快。瑞银证券指出，科技板块交易拥挤度缓解后，科技与AI仍是下半年市场主线。\n个股方面，科技赛道全线反弹。半导体方向，兆易创新涨停，雅克科技、华虹宏力、长电科技、通富微电、长川科技等涨停，中芯国际、澜起科技、佰维存储等涨超10%。算力硬件方面，中际旭创涨超13%，生益科技、宏和科技、广合科技等涨停。算力租赁概念中嘉博创、美利云2连板。紫光股份涨停，共进股份录得3天2板。MLCC概念国瓷材料20CM涨停，三环集团涨超18%。后市方面，双创板块放量长阳站稳5日均线，短线止跌企稳。市场要闻方面，腾讯云表示将大规模部署国产化算力，预计2026年Q4部署NPO超级节点。国家药监局批准一款新靶点创新药上市，用于治疗1型发作性睡病。",
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
      "valuation_history_days": 72,
      "valuation_history_from": "20260403",
      "current_price": 176.07,
      "price": 176.07,
      "ma5": 185.31,
      "ma10": 184.3,
      "ma20": 196.55,
      "dist_ma5_pct": -5.0,
      "dist_ma10_pct": -4.5,
      "dist_ma20_pct": -10.4,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 12.69,
        "pct_float": 4.78,
        "chg5_pct": -36.4,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688017.SH",
      "fetch_time": "2026-07-22T15:40:49+0800",
      "name": "绿的谐波",
      "pe": 424.5628,
      "pb": 16.4461,
      "ps_ttm": 94.7422,
      "pcf_ttm": 413.9829,
      "valuation_percentile": 95.93,
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
        "专精特新小巨人主题指数",
        "先进制造指数",
        "专精特新小巨人指数",
        "具身智能指数",
        "股权激励指数",
        "人形机器人指数",
        "工业4.0指数",
        "机器人指数",
        "新型工业化指数",
        "减速器指数",
        "宇树机器人指数"
      ],
      "score_company": 8.7,
      "score_trend": 7.9,
      "score_value": 3.5,
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
          "text": " 9家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
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
          "content": "11:53 7月21日，A股机器人板块表现活跃。截至11:20，机器人ETF汇添富（159213）涨超2.5%。成分股中，大族激光涨停，三花智控、绿的谐波涨超4%，汇川技术、拓普集团等涨超2%。大族激光披露，2026年上半年实现净利润12.86亿元，同比增长163.47%。近期举办的2026世界人工智能大会（WAIC）重点展示了机器人场景落地应用，具身智能被列为核心赛道。东方证券分析认为，人形机器人行业关注重点已转向规模化量产与多场景交付，产业链有望迎来催化。\n东吴证券研报指出，人形机器人核心零部件壁垒较高，谐波减速器、丝杠、灵巧手及轻量化材料等环节将受益于行业发展。其中，滚柱丝杠在人形机器人爆发背景下具备增长潜力，灵巧手市场空间广阔，轻量化材料如PEEK在关节模组中应用前景显著。全球科技巨头布局人形机器人，行业量产进程加速。\n风险提示：基金投资存在风险，投资者需阅读法律文件了解风险收益特征。该基金属于中风险等级（R3）产品，适合稳健型（C3）及以上投资者。文中提及个股仅为指数成份股展示，不构成投资建议。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "09:48 减速器板块走低，绿的谐波跌超10%，昊志机电、双环传动、金帝股份、领益智造跟跌。",
          "tags": [
            "快讯"
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
      "current_price": 326.1,
      "price": 326.1,
      "ma5": 373.73,
      "ma10": 410.3,
      "ma20": 396.25,
      "dist_ma5_pct": -12.7,
      "dist_ma10_pct": -20.5,
      "dist_ma20_pct": -17.7,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 25.18,
        "pct_float": 4.21,
        "chg5_pct": -19.79,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "003031.SZ",
      "fetch_time": "2026-07-22T15:40:50+0800",
      "name": "中瓷电子",
      "pe": 77.3425,
      "pb": 7.6385,
      "ps_ttm": 14.5589,
      "pcf_ttm": 42.8963,
      "valuation_percentile": 59.59,
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
        "专精特新小巨人主题指数",
        "华为平台指数",
        "信创产业指数",
        "央企通信指数",
        "手机陶瓷外壳指数",
        "中电科技系指数"
      ],
      "score_company": 6.4,
      "score_trend": 7.1,
      "score_value": 6.0,
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
          "content": "15:41 今日A股市场主要指数集体上涨，上证指数涨1.79%，深证成指涨4.81%，创业板指涨7.05%，科创综指涨8.75%，全市场成交额29742亿元。半导体、存储芯片、光刻机、CPO等概念板块表现活跃。华西证券认为，市场进入震荡修复阶段，建议关注绩优成长股及AI相关产业链。中际旭创今日收涨13.2%，报1136.55元/股，成交额513.02亿元，主力资金净流入29.33亿元。公司专注于AI数据中心光模块业务，此前披露在手订单已覆盖2026年全年，1.6T产品持续起量。此外，中际旭创已通过港交所主板上市聆讯。\n易方达基金、广发基金等机构发布的2026年二季报显示，多位知名基金经理将中际旭创纳入重仓股名单。此外，中际旭创还进入了富国天惠精选成长基金的前十大重仓股。",
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
      "valuation_history_days": 285,
      "valuation_history_from": "20230105",
      "current_price": 107.28,
      "price": 107.28,
      "ma5": 125.64,
      "ma10": 138.37,
      "ma20": 154.11,
      "dist_ma5_pct": -14.6,
      "dist_ma10_pct": -22.5,
      "dist_ma20_pct": -30.4,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.13,
        "pct_float": 2.17,
        "chg5_pct": -14.96,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688200.SH",
      "fetch_time": "2026-07-22T15:40:51+0800",
      "name": "华峰测控",
      "pe": 130.2145,
      "pb": 18.3669,
      "ps_ttm": 52.0992,
      "pcf_ttm": 278.9476,
      "valuation_percentile": 94.03,
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
        "芯片指数",
        "具身智能指数",
        "半导体精选指数",
        "股权激励指数",
        "可转债正股指数",
        "半导体设备指数",
        "模拟芯片指数",
        "可转债预案指数",
        "先进封装指数"
      ],
      "score_company": 9.1,
      "score_trend": 8.3,
      "score_value": 3.6,
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
        },
        {
          "content": "华峰测控：北京德和衡律师事务所关于华峰测控2021年限制性股票激励计划首次授予部分第五个归属期归属条件成就、预留授予部分第四个归属期归属条件成就、授予价格与数量调整及部分限制性股票作废相关事项的法律意见书",
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
      "valuation_history_days": 267,
      "valuation_history_from": "20220218",
      "current_price": 372.91,
      "price": 372.91,
      "ma5": 449.89,
      "ma10": 472.94,
      "ma20": 433.06,
      "dist_ma5_pct": -17.1,
      "dist_ma10_pct": -21.2,
      "dist_ma20_pct": -13.9,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.34,
        "pct_float": 0.53,
        "chg5_pct": -47.63,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688531.SH",
      "fetch_time": "2026-07-22T15:40:51+0800",
      "name": "日联科技",
      "pe": 113.3065,
      "pb": 6.3101,
      "ps_ttm": 17.8366,
      "pcf_ttm": 110.8175,
      "valuation_percentile": 82.49,
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
        "专精特新小巨人主题指数",
        "贷款回购指数",
        "专精特新小巨人指数",
        "股权激励指数",
        "可转债预案指数",
        "专用设备精选指数"
      ],
      "score_company": 9.1,
      "score_trend": 7.6,
      "score_value": 4.4,
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
          "content": "22:15 7月16日，多家A股上市公司披露2026年半年度业绩预告或业绩快报。相关公司包括摩尔线程、欧科亿、凌云光、海光信息、探路者、鼎通科技、日联科技、艾力斯、天合光能、川金诺及苏垦农发等。\n\n摩尔线程公告显示，预计2026年半年度营业收入为16.5亿元至17.5亿元，较上年同期增长135.12%至149.37%。此外，其GPU智算卡MTTS5000已实现规模量产。\n\n欧科亿公告称，预计上半年净利润同比预增46339%至54062%，主要得益于数控刀具产品销量的同比增长。",
          "tags": [
            "资讯"
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
      "valuation_history_days": 306,
      "valuation_history_from": "20250331",
      "current_price": 132.32,
      "price": 132.32,
      "ma5": 152.82,
      "ma10": 166.13,
      "ma20": 169.82,
      "dist_ma5_pct": -13.4,
      "dist_ma10_pct": -20.4,
      "dist_ma20_pct": -22.1,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 5.51,
        "pct_float": 3.66,
        "chg5_pct": -13.64,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688150.SH",
      "fetch_time": "2026-07-22T15:40:51+0800",
      "name": "莱特光电",
      "pe": 83.3772,
      "pb": 8.9533,
      "ps_ttm": 31.5211,
      "pcf_ttm": 62.516,
      "valuation_percentile": 83.93,
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
      "score_trend": 7.2,
      "score_value": 4.2,
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
          "text": " 7家 机构预测，2026年-2028年营收和净利润每年增长均超过 30% ，未来成长很快。"
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
          "content": "莱特光电：关于陕西莱特光电材料股份有限公司向不特定对象发行可转换公司债券的审核中心意见落实函之回复报告（豁免版）",
          "tags": [
            "重要公告"
          ]
        },
        {
          "content": "21:04 莱特光电（688150）披露可转债二次修订公告，发行规模由不超过6.98亿元调整为不超过5.25亿元，取消补充流动资金项目，募集资金将全部投向蒲城新材料生产研发基地及车间数智化升级项目。自2025年11月启动以来，该方案经历两轮下调，累计缩减资金2.41亿元。公司2026年一季度营收与净利润同比分别下降8.20%和24.47%，公司称受海外环境及原材料价格波动影响。此外，公司OLED中间体产能利用率较高，但终端材料产能利用率长期处于低位。\n莱特光电2025年对第一大客户京东方销售收入占比达85.56%，前五大客户占比合计97.07%，业务对单一客户依赖度较高。此次调整在股东大会授权框架内，无需另行表决，但发行仍需交易所审核及证监会注册。截至7月21日收盘，莱特光电股价报44.57元/股。",
          "tags": [
            "资讯"
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
      "valuation_history_days": 282,
      "valuation_history_from": "20240318",
      "current_price": 47.51,
      "price": 47.51,
      "ma5": 50.39,
      "ma10": 56.77,
      "ma20": 55.95,
      "dist_ma5_pct": -5.7,
      "dist_ma10_pct": -16.3,
      "dist_ma20_pct": -15.1,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.28,
        "pct_float": 3.5,
        "chg5_pct": -18.08,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688629.SH",
      "fetch_time": "2026-07-22T15:40:52+0800",
      "name": "华丰科技",
      "pe": 183.7614,
      "pb": 27.4038,
      "ps_ttm": 28.8019,
      "pcf_ttm": 151.2477,
      "valuation_percentile": 78.86,
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
      "score_trend": 8.3,
      "score_value": 4.7,
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
      "valuation_history_days": 259,
      "valuation_history_from": "20250627",
      "current_price": 141.66,
      "price": 141.66,
      "ma5": 173.45,
      "ma10": 184.6,
      "ma20": 168.1,
      "dist_ma5_pct": -18.3,
      "dist_ma10_pct": -23.3,
      "dist_ma20_pct": -15.7,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 19.27,
        "pct_float": 2.61,
        "chg5_pct": -13.53,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688127.SH",
      "fetch_time": "2026-07-22T15:40:52+0800",
      "name": "蓝特光学",
      "pe": 53.2483,
      "pb": 11.3745,
      "ps_ttm": 14.5387,
      "pcf_ttm": 34.2254,
      "valuation_percentile": 73.2,
      "total_shares": 405897700,
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
        "股权激励指数",
        "预期提升指数",
        "虚拟现实指数",
        "光电路交换机(OCS)指数",
        "光学光电子精选指数"
      ],
      "score_company": 9.1,
      "score_trend": 6.4,
      "score_value": 5.0,
      "highlights": [
        {
          "tag": "业绩",
          "text": "2026年04月30日，业绩超预期引发股价跳空高开，但目前股价缺口已回补。"
        },
        {
          "tag": "成长",
          "text": "近3年营业收入每年增长 66% ，最新季度归母净利润同比增长 184% ，成长能力很强。"
        },
        {
          "tag": "盈利",
          "text": "近5年，净资产收益率为 13% ，投入资本回报率为 13% ，盈利能力很强。"
        },
        {
          "tag": "净现",
          "text": "近5年，净现比达到 153% ，净利润现金含量较高。"
        },
        {
          "tag": "产能",
          "text": "在建工程占总资产 13% ，未来产能扩张后，营收有望进一步增长。"
        },
        {
          "tag": "北向",
          "text": "北向资金持股 4.1% ，很受外资机构青睐。"
        }
      ],
      "risks": [
        {
          "tag": "抛压",
          "text": "2026年06月29日大跌 -7.58% ，且成交额为近20日均值的 1.53倍 ，抛压很重。"
        },
        {
          "tag": "调整",
          "text": "前期股价强势， 2026年05月25日 至今陷入调整，资金有出逃可能。"
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
          "content": "2026/07/20 李青松(核心技术人员)增持 2000股 ，类型为 二级市场买卖 ，成交均价为 57.2元/股 ，耗资 11.4万元 ，此次增持后的持股数为67.7万股",
          "tags": [
            "管理层增持"
          ]
        },
        {
          "content": "19:32 蓝特光学发布公告称，公司于2026年7月13日收到上交所下发的审核意见。上交所认为，蓝特光学向特定对象发行股票的申请符合相关发行条件、上市条件以及信息披露要求。\n\n该事项后续仍需取得证监会的同意注册批复后方可正式实施，目前仍存在一定的不确定性。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "19:32 蓝特光学发布公告称，公司于2026年7月13日收到上交所出具的审核意见。上交所认为，公司向特定对象发行股票的申请符合上市条件、发行条件以及信息披露的相关要求。\n\n该事项后续仍需获得证监会的同意注册方可实施，目前尚存在不确定性。",
          "tags": [
            "资讯"
          ]
        }
      ],
      "report_period": "20250930",
      "revenue": 1050900781.41,
      "revenue_yoy": 0.336503,
      "operating_profit": 283950302.21,
      "operating_profit_yoy": 0.56613,
      "net_profit": 252004126.26,
      "net_profit_yoy": 0.553171,
      "gross_profit": 430056597.19,
      "gross_profit_yoy": 0.425894,
      "cogs": 620844184.22,
      "gross_margin": 40.92,
      "pe_forward": null,
      "valuation_history_days": 308,
      "valuation_history_from": "20220922",
      "current_price": 62.41,
      "price": 62.41,
      "ma5": 72.03,
      "ma10": 78.1,
      "ma20": 82.98,
      "dist_ma5_pct": -13.4,
      "dist_ma10_pct": -20.1,
      "dist_ma20_pct": -24.8,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.43,
        "pct_float": 3.86,
        "chg5_pct": -12.85,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301182.SZ",
      "fetch_time": "2026-07-22T15:40:52+0800",
      "name": "凯旺科技",
      "pe": -52.0524,
      "pb": 8.6519,
      "ps_ttm": 6.818,
      "pcf_ttm": null,
      "valuation_percentile": 93.3,
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
      "score_company": 4.6,
      "score_trend": 5.0,
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
      "valuation_history_days": 311,
      "valuation_history_from": "20231225",
      "current_price": 66.0,
      "price": 66.0,
      "ma5": 77.74,
      "ma10": 88.22,
      "ma20": 93.15,
      "dist_ma5_pct": -15.1,
      "dist_ma10_pct": -25.2,
      "dist_ma20_pct": -29.1,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 3.29,
        "pct_float": 6.11,
        "chg5_pct": -11.55,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002937.SZ",
      "fetch_time": "2026-07-22T15:40:52+0800",
      "name": "兴瑞科技",
      "pe": 74.145,
      "pb": 5.3424,
      "ps_ttm": 5.7498,
      "pcf_ttm": 42.1425,
      "valuation_percentile": 85.29,
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
      "score_company": 7.9,
      "score_trend": 7.5,
      "score_value": 4.2,
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
          "text": "近3月，公司累计回购 298万股 ，占总股本比例 0.94% ，金额合计 6840万元 。"
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
        },
        {
          "content": "兴瑞科技：关于提前赎回“兴瑞转债”的第九次提示性公告",
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
      "valuation_history_from": "20210722",
      "current_price": 38.11,
      "price": 38.11,
      "ma5": 40.27,
      "ma10": 41.96,
      "ma20": 41.97,
      "dist_ma5_pct": -5.4,
      "dist_ma10_pct": -9.2,
      "dist_ma20_pct": -9.2,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.27,
        "pct_float": 9.34,
        "chg5_pct": -5.32,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002957.SZ",
      "fetch_time": "2026-07-22T15:40:52+0800",
      "name": "科瑞技术",
      "pe": 53.8599,
      "pb": 5.0118,
      "ps_ttm": 5.9165,
      "pcf_ttm": 46.0448,
      "valuation_percentile": 81.75,
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
        "新能源设备指数",
        "电子烟"
      ],
      "score_company": 8.0,
      "score_trend": 6.3,
      "score_value": 4.1,
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
          "text": "近90天， 7家 机构给出评级，其中 57% 为“买入”，距目标价的上涨空间为 68% 。"
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
      "current_price": 36.41,
      "price": 36.41,
      "ma5": 41.42,
      "ma10": 43.93,
      "ma20": 49.39,
      "dist_ma5_pct": -12.1,
      "dist_ma10_pct": -17.1,
      "dist_ma20_pct": -26.3,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 3.82,
        "pct_float": 2.57,
        "chg5_pct": -18.95,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "000703.SZ",
      "fetch_time": "2026-07-22T15:40:53+0800",
      "name": "恒逸石化",
      "pe": 26.314,
      "pb": 2.2052,
      "ps_ttm": 0.4981,
      "pcf_ttm": 9.8332,
      "valuation_percentile": 74.47,
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
        "油品升级指数",
        "油气改革指数",
        "供应链服务指数",
        "涤纶指数",
        "PTA指数"
      ],
      "score_company": 8.0,
      "score_trend": 8.8,
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
          "content": "02:46 截至7月20日，已有28家石油石化上市公司披露上半年业绩预告，其中15家预增，5家实现扭亏或减亏。受中东地缘冲突影响，全球化工品价格上涨，库存去化带动部分产品盈利改善。炼化一体化企业表现突出，恒逸石化预计上半年归母净利润55亿元至60亿元，同比增长2326.31%至2546.88%，主要受益于海外成品油盈利及PX、苯等产品盈利维持高位，以及己内酰胺-聚酰胺一体化项目投产。荣盛石化预计上半年净利润50亿元至52亿元，同比增长730.45%至763.67%；东方盛虹预计上半年净利润42亿元至50亿元，同比增长987.39%至1194.51%。\n东方盛虹表示，石化行业供需格局改善及原油价格中枢上移，带动产品价差扩大，炼化一体化项目运行平稳。分析认为，炼化一体化龙头规模效应显著，若地缘冲突缓和，产业链定价权将回归供需端。受地缘局势影响，油服工程企业业绩承压，28家公司中6家油服企业有3家首亏，2家续亏，1家预减。中曼石油预计上半年归母净利润同比减少64.68%至70.46%，受伊拉克项目停工影响；惠博普预计亏损9000万元至1.2亿元，受海外项目进度放缓及汇兑损失影响；博迈科预计亏损7800万元至6500万元，受项目周期切换及海外投资节奏后移影响。\n贝肯能源预计上半年亏损1.15亿元至1.25亿元，受汇兑损失及部分钻机停工影响。展望下半年，机构分析认为，传统大宗化工品受益于补库与出口，AI产业催生的新材料需求值得关注。AI算力基建对半导体材料、电子化学品等提出更高要求，电子特气、含氟电子化学品及半导体材料等细分领域景气度有望上行。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "12:59 截至午间收盘，中证石化产业指数录得1.0%的涨幅。在成份股表现方面，恒逸石化触及涨停，和邦生物上涨6.3%，桐昆股份上涨5.5%。\n\n申万宏源证券分析认为，油价中枢呈现上行趋势，预计2026年整体将维持高油价背景，这将使油公司业绩单边受益。随着油价景气度回暖，油气勘探开发的投资力度有望加大。此外，美国乙烷供需格局维持宽松，油价上涨为相关企业业绩提供了较大的弹性空间。",
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
      "valuation_history_from": "20210722",
      "current_price": 14.65,
      "price": 14.65,
      "ma5": 14.2,
      "ma10": 14.17,
      "ma20": 14.24,
      "dist_ma5_pct": 3.2,
      "dist_ma10_pct": 3.4,
      "dist_ma20_pct": 2.9,
      "iv_proxy": {
        "primary_name": "深100ETF",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.76,
        "pct_float": 1.75,
        "chg5_pct": -7.04,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "300323.SZ",
      "fetch_time": "2026-07-22T15:40:53+0800",
      "name": "华灿光电",
      "pe": -67.7731,
      "pb": 2.7942,
      "ps_ttm": 2.821,
      "pcf_ttm": null,
      "valuation_percentile": 68.09,
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
        "新型显示技术指数",
        "LED照明指数",
        "广东省国资指数",
        "LED指数",
        "节能照明指数",
        "蓝宝石指数",
        "氧化锌指数"
      ],
      "score_company": 6.8,
      "score_trend": 7.0,
      "score_value": 4.9,
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
          "content": "19:01 先导智能（300450）公告称，财务总监郭彩霞因个人职业规划辞职，辞任后不再担任公司其他职务。公司董事会已聘任李旭辉担任财务总监。李旭辉曾任职于安凯特电缆、伊顿电力设备、鼎汉技术、华灿光电及浙江长江汽车电子。截至公告日，李旭辉未持有公司股份。",
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
      "valuation_history_from": "20210722",
      "current_price": 11.63,
      "price": 11.63,
      "ma5": 13.36,
      "ma10": 15.32,
      "ma20": 16.57,
      "dist_ma5_pct": -12.9,
      "dist_ma10_pct": -24.1,
      "dist_ma20_pct": -29.8,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 13.95,
        "pct_float": 9.71,
        "chg5_pct": -7.53,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688777.SH",
      "fetch_time": "2026-07-22T15:40:54+0800",
      "name": "中控技术",
      "pe": 171.7972,
      "pb": 6.9325,
      "ps_ttm": 8.5359,
      "pcf_ttm": 252.3671,
      "valuation_percentile": 75.56,
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
      "score_trend": 8.1,
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
        "pct_float": 4.03,
        "chg5_pct": -5.67,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "301536.SZ",
      "fetch_time": "2026-07-22T15:40:54+0800",
      "name": "星宸科技",
      "pe": 121.0196,
      "pb": 18.6498,
      "ps_ttm": 17.5054,
      "pcf_ttm": 195.6778,
      "valuation_percentile": 95.9,
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
        "股权激励指数",
        "人工智能指数",
        "万得预增指数",
        "模拟芯片指数",
        "触板指数",
        "安防监控指数"
      ],
      "score_company": 8.2,
      "score_trend": 9.2,
      "score_value": 3.5,
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
          "content": "10:18股价达到 134.53 元，创历史新高",
          "tags": [
            "股价新高"
          ]
        },
        {
          "content": "15:00 今天大涨的原因可能是公司预计2026年上半年归母净利润大幅增长583.72%-650.42%，反映其视觉AI系统级芯片（AISoC）销量与盈利能力显著提升，提振市场预期。",
          "tags": [
            "快讯",
            "大涨原因"
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
      "valuation_history_days": 76,
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
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.25,
        "pct_float": 4.05,
        "chg5_pct": 18.44,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "688376.SH",
      "fetch_time": "2026-07-22T15:40:54+0800",
      "name": "美埃科技",
      "pe": 85.6263,
      "pb": 4.899,
      "ps_ttm": 4.5855,
      "pcf_ttm": 29.1399,
      "valuation_percentile": 93.79,
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
      "score_trend": 7.2,
      "score_value": 3.4,
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
      "valuation_history_days": 404,
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
        "rzye_yi": 2.17,
        "pct_float": 2.23,
        "chg5_pct": -13.91,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688378.SH",
      "fetch_time": "2026-07-22T15:40:54+0800",
      "name": "奥来德",
      "pe": 81.9636,
      "pb": 5.1902,
      "ps_ttm": 15.7919,
      "pcf_ttm": 33.3422,
      "valuation_percentile": 89.72,
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
      "score_trend": 6.7,
      "score_value": 3.9,
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
          "text": "近90天， 7家 机构给出评级，其中 86% 为“买入”，距目标价的上涨空间为 66% 。"
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
        "rzye_yi": 4.98,
        "pct_float": 4.92,
        "chg5_pct": -7.62,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "600961.SH",
      "fetch_time": "2026-07-22T15:40:54+0800",
      "name": "株冶集团",
      "pe": 12.6467,
      "pb": 4.9851,
      "ps_ttm": 1.0303,
      "pcf_ttm": 9.1374,
      "valuation_percentile": 61.3,
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
        "预期提升指数",
        "有色金属指数",
        "锌电池指数",
        "铅锌矿指数",
        "钴矿指数",
        "央企有色指数",
        "磷化铟指数",
        "蓄电池指数"
      ],
      "score_company": 7.2,
      "score_trend": 7.1,
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
          "text": "近1年，股价涨幅超过A股市场 94% 的股票，走势较强。"
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
      "valuation_history_from": "20210722",
      "current_price": 23.42,
      "price": 23.42,
      "ma5": 23.1,
      "ma10": 25.17,
      "ma20": 28.33,
      "dist_ma5_pct": 1.4,
      "dist_ma10_pct": -7.0,
      "dist_ma20_pct": -17.3,
      "iv_proxy": {
        "primary_name": "300ETF",
        "iv_rank": 0.8503,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 9.7,
        "pct_float": 5.51,
        "chg5_pct": -2.44,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688392.SH",
      "fetch_time": "2026-07-22T15:40:54+0800",
      "name": "骄成超声",
      "pe": 130.0709,
      "pb": 10.2284,
      "ps_ttm": 22.7475,
      "pcf_ttm": 147.8103,
      "valuation_percentile": 89.61,
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
      "score_trend": 7.8,
      "score_value": 3.8,
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
      "valuation_history_days": 434,
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
        "rzye_yi": 4.59,
        "pct_float": 2.38,
        "chg5_pct": -33.19,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688536.SH",
      "fetch_time": "2026-07-22T15:40:55+0800",
      "name": "思瑞浦",
      "pe": 136.048,
      "pb": 5.6399,
      "ps_ttm": 14.7599,
      "pcf_ttm": 112.1989,
      "valuation_percentile": 40.82,
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
      "score_trend": 7.8,
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
          "content": "2026/07/14发布预案公告，本计划拟向激励对象授予134万股 ，约占总股本的 0.97%，授予价格为 201元/股 。",
          "tags": [
            "激励计划"
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
        "rzye_yi": 10.14,
        "pct_float": 2.89,
        "chg5_pct": -10.33,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300373.SZ",
      "fetch_time": "2026-07-22T15:40:55+0800",
      "name": "扬杰科技",
      "pe": 38.1795,
      "pb": 5.4293,
      "ps_ttm": 6.8126,
      "pcf_ttm": 32.3784,
      "valuation_percentile": 62.36,
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
      "score_company": 8.3,
      "score_trend": 7.5,
      "score_value": 5.1,
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
      "valuation_history_from": "20210722",
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
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 16.55,
        "pct_float": 3.1,
        "chg5_pct": -14.16,
        "net5_repay_days": 5,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688401.SH",
      "fetch_time": "2026-07-22T15:40:55+0800",
      "name": "路维光电",
      "pe": 50.5831,
      "pb": 5.2975,
      "ps_ttm": 11.2227,
      "pcf_ttm": 46.4858,
      "valuation_percentile": 85.23,
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
      "score_company": 7.7,
      "score_trend": 7.9,
      "score_value": 4.1,
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
        },
        {
          "content": "路维光电：国信证券股份有限公司关于深圳市路维光电股份有限公司2026年度向特定对象发行A股股票的上市保荐书",
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
      "valuation_history_days": 462,
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
        "rzye_yi": 5.74,
        "pct_float": 4.33,
        "chg5_pct": -14.85,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002821.SZ",
      "fetch_time": "2026-07-22T15:40:55+0800",
      "name": "凯莱英",
      "pe": 53.3818,
      "pb": 3.3904,
      "ps_ttm": 8.5515,
      "pcf_ttm": 39.9142,
      "valuation_percentile": 44.74,
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
        "创新药指数",
        "合资企业指数",
        "反内卷指数",
        "医药数智化指数",
        "医疗物资出口指数"
      ],
      "score_company": 9.2,
      "score_trend": 8.6,
      "score_value": 5.9,
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
          "content": "20:26 2026年二季度，中欧基金投资总监葛兰管理的中欧医疗健康与中欧医疗创新两只医药主题基金跑赢基准。截至二季度末，中欧医疗健康资产净值为247.70亿元。中欧医疗健康前十大重仓股包括凯莱英、百利天恒、恒瑞医药、药明康德、海思科、康龙化成、科伦药业、泰格医药、艾力斯及君实生物-U，持仓集中度升至75.11%。其中，君实生物首次进入前十大重仓，持仓数量由2025年末的578.74万股增至1481.14万股。该基金增持了百利天恒、科伦药业、海思科、恒瑞医药、康龙化成，减持药明康德、泰格医药、艾力斯和凯莱英，信立泰退出前十。中欧医疗创新方面，二季度增持百利天恒、康方生物及凯莱英H股，康龙化成重回前十，海思科、药明康德、药明合联等6只个股遭减持，信立泰退出前十。\n中欧医疗创新对科伦药业持仓数量为1052.21万股。葛兰在二季报中表示，创新药及产业链仍是布局核心，国产创新药海外临床推进及商业化兑现是关注重点。她判断创新产业链景气回升，CXO板块基本面呈现订单回暖与业绩兑现，生命科学上游及医疗器械板块亦有望延续修复。第三季度投资将围绕创新药及产业链主线，兼顾国产化趋势与消费医疗复苏。",
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
          "content": "凯莱英：凯莱英医药集团（天津）股份有限公司2026年第二次临时股东会、2026年第三次A股类别股东会及2026年第三次H股类别股东会的法律意见",
          "tags": [
            "重要公告"
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
      "valuation_history_from": "20210722",
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
        "rzye_yi": 8.86,
        "pct_float": 1.65,
        "chg5_pct": -16.18,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002192.SZ",
      "fetch_time": "2026-07-22T15:40:55+0800",
      "name": "融捷股份",
      "pe": 29.2223,
      "pb": 4.1079,
      "ps_ttm": 13.9831,
      "pcf_ttm": 82.8167,
      "valuation_percentile": 22.65,
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
      "score_trend": 3.8,
      "score_value": 7.6,
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
          "text": "近3月， 锂 板块疲软，走势弱于其他 98.5% 的板块。"
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
          "content": "2026/07/22～2027/01/22 张长虹(实际控制人)计划增持，变动价格说明：本次增持不设置价格区间，将根据市场整体走势及对公司股份价值的合理判断，在实施期限内择机实施增持计划，拟增持金额不超过 6000万元  ，拟增持金额不低于 3000万元  交易方式：通过深圳证券交易所交易系统允许的方式，包括但不限于集中竞价交易、大宗交易等方式增持公司股份",
          "tags": [
            "控股股东增持"
          ]
        },
        {
          "content": "11:36 7月20日，多家锂电池产业链上市公司发布回购或增持计划。亿纬锂能董事刘建华计划6个月内增持10万股；融捷股份拟回购5000万元至1亿元股份，价格不超过73元/股；华友钴业拟回购6亿元至10亿元股份，价格不超过50元/股；科达利董事长提议回购1.5亿元至3亿元股份；天奈科技拟回购1亿元至2亿元股份，价格不超过57.21元/股；恒力石化拟回购2亿元至3亿元股份，价格不超过25元/股；先导智能拟回购2亿至4亿港元H股。\n7月20日上午，证监会主席吴清主持召开投资者座谈会，听取市场意见建议。吴清表示，证监会将坚持防风险、强监管、促高质量发展，维护市场平稳运行，提高上市公司透明度和真实性，更好回报投资者。",
          "tags": [
            "资讯"
          ]
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
      "valuation_history_from": "20210722",
      "current_price": 58.23,
      "price": 58.23,
      "ma5": 62.0,
      "ma10": 70.95,
      "ma20": 80.53,
      "dist_ma5_pct": -6.1,
      "dist_ma10_pct": -17.9,
      "dist_ma20_pct": -27.7,
      "iv_proxy": {
        "primary_name": "500ETF深",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 13.12,
        "pct_float": 8.69,
        "chg5_pct": -7.08,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "601958.SH",
      "fetch_time": "2026-07-22T15:40:55+0800",
      "name": "金钼股份",
      "pe": 20.4657,
      "pb": 3.4908,
      "ps_ttm": 4.7005,
      "pcf_ttm": 31.9698,
      "valuation_percentile": 84.36,
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
      "score_trend": 7.8,
      "score_value": 4.0,
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
          "text": "近1年，股价涨幅超过A股市场 93% 的股票，走势较强。"
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
          "content": "16:52 金钼股份物流分公司机运车间员工韩启龙获评陕西有色金属集团优秀共产党员。韩启龙拥有三十余年党龄，长期扎根装载机操作一线，在理论学习与生产实践中发挥党员先锋作用。\n韩启龙通过优化作业流程，使班组一次装车合格率在两年内从83%提升至99%。在环保消缺及冬季除雪保畅等急难险重任务中，他带头冲锋，保障了厂区物料转运与运输安全。此外，他注重传帮带，指导青年职工提升业务技能，并严格遵守廉洁从业规定。\n韩启龙在三十余年的工作中，通过提升生产指标、攻坚保供任务及培养人才，为企业发展做出贡献。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "14:08 小金属概念板块走高，海南矿业涨停，成都路桥、和邦生物此前封板，飞南资源、铜陵有色、中金黄金、金钼股份、锡业股份等跟涨。相关ETF方面，有色ETF广发（159029）涨5.44%，成交额1559.34万元，有色ETF富国（159168）涨5.42%，成交额2870.27万元。",
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
      "valuation_history_from": "20210722",
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
        "iv_rank": 0.8503,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 11.55,
        "pct_float": 1.69,
        "chg5_pct": -5.61,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "300747.SZ",
      "fetch_time": "2026-07-22T15:40:55+0800",
      "name": "锐科激光",
      "pe": 76.897,
      "pb": 5.3701,
      "ps_ttm": 5.1194,
      "pcf_ttm": 115.5953,
      "valuation_percentile": 47.52,
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
      "score_trend": 5.4,
      "score_value": 5.6,
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
          "text": "近90天， 6家 机构给出评级，其中 67% 为“买入”，距目标价的上涨空间为 51% 。"
        },
        {
          "tag": "公募",
          "text": "公募基金持股 3.2% ，较受内资机构青睐。"
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
          "content": "15:00 今天大涨的原因可能是公司2026上半年营收19.1亿元、归母净利润同比+116.73%，Q2净利环比+178%，受激光器需求回升、提质增效带动毛利率提升及减值减少。",
          "tags": [
            "快讯",
            "大涨原因"
          ]
        },
        {
          "content": "12:00 7月21日，A股PCB概念股集体反弹。截至半日收盘，波长光电、金禄电子、戈碧迦、中富电路、埃科光电、路维光电、昊志机电、国际复材、锐科激光、欧科亿、鼎泰高科、东威科技、斯迪克涨幅居前；顺络电子、宏和科技、江南新材、大族激光、大为股份、木林森涨停。中信建投研报指出，感光干膜是PCB电路图形转印的核心耗材，受益于AI服务器、数据中心及高速网络设备驱动，行业进入结构性增长周期。预计2026年至2030年感光干膜市场空间将持续增长，年均复合增长率约为9.4%。目前全球感光干膜市场由中国台湾及日本企业主导，随着头部PCB企业批量采用国产产品，内资感光干膜市场份额有望提升。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "2026/07/20～2027/01/20 邓中辉(总法律顾问)计划增持，变动价格说明：不设定价格区间，拟增持金额不低于 40.0万元  交易方式：通过深圳证券交易所交易系统集中竞价、大宗交易等方式。",
          "tags": [
            "管理层增持"
          ]
        },
        {
          "content": "2026/07/20～2027/01/20 陈星星(董事长，总经理)计划增持，变动价格说明：不设定价格区间，拟增持金额不低于 80.0万元  交易方式：通过深圳证券交易所交易系统集中竞价、大宗交易等方式。",
          "tags": [
            "管理层增持"
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
      "valuation_history_from": "20210722",
      "current_price": 31.35,
      "price": 31.35,
      "ma5": 35.19,
      "ma10": 39.12,
      "ma20": 45.61,
      "dist_ma5_pct": -10.9,
      "dist_ma10_pct": -19.9,
      "dist_ma20_pct": -31.3,
      "iv_proxy": {
        "primary_name": "创业板ETF",
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.39,
        "pct_float": 4.68,
        "chg5_pct": -8.13,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002975.SZ",
      "fetch_time": "2026-07-22T15:40:56+0800",
      "name": "博杰股份",
      "pe": 76.3249,
      "pb": 7.5526,
      "ps_ttm": 8.4733,
      "pcf_ttm": 225.4428,
      "valuation_percentile": 73.99,
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
      "score_trend": 7.4,
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
      "fetch_time": "2026-07-22T15:40:57+0800",
      "name": "荣昌生物",
      "pe": 55.45,
      "pb": 18.2337,
      "ps_ttm": 21.1843,
      "pcf_ttm": 283.5893,
      "valuation_percentile": 52.58,
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
      "score_company": 7.7,
      "score_trend": 8.2,
      "score_value": 6.3,
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
          "content": "17:09 今日A股三大指数集体上涨，生物医药板块表现亮眼。机构研报指出，全球医疗健康投融资回暖，创新药及创新产业链景气度上行，叠加全球同步研发创新药在中国首报首发，提振了市场信心。截至收盘，生物医药指数上涨1.38%，报2165.94点。成分股中，康龙化成上涨5.58%，凯莱英上涨4.30%，荣昌生物上涨3.69%，泰格医药上涨2.28%，长春高新上涨2.26%。跟踪该指数的生物医药ETF汇添富(159839)今日收涨1.68%，成交额7588万元，规模10.90亿元。该ETF前三大权重股分别为药明康德、复星医药、泰格医药。费率方面，该ETF综合费率为0.60%/年。资金流向显示，该ETF上一交易日主力资金净流入410万元。同赛道中，生物医药ETF天弘上涨1.30%，生物医药ETF华安上涨1.01%。国信证券、爱建证券及中邮证券等机构表示看好创新药及创新产业链的后续表现。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "15:49 截至2026年7月21日15:00，上证科创板生物医药指数(000683)上涨0.94%，成分股美迪西、奕瑞科技、百济神州、艾力斯、荣昌生物分别上涨9.26%、8.95%、6.25%、4.38%、3.69%。科创医药ETF华夏(588130)上涨1.15%，报1.05元；恒生医药ETF华夏(159892)上涨0.28%，报0.73元。政策面上，市场监管总局表示“十五五”期间将前瞻布局生物医药等战略性新兴产业高能级检测平台；京沪两地近期出台支持商业健康险发展政策，旨在拓宽创新药械支付渠道。渤海证券认为，相关政策有望加速商业保险与生物医药产业融合，提升行业商业化能力。此外，恒生医药ETF华夏跟踪的恒生生物科技指数涵盖了通过港交所第18A章上市的公司。",
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
      "valuation_history_days": 280,
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
        "rzye_yi": 9.52,
        "pct_float": 2.1,
        "chg5_pct": -12.11,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300684.SZ",
      "fetch_time": "2026-07-22T15:40:57+0800",
      "name": "中石科技",
      "pe": 43.6708,
      "pb": 7.4225,
      "ps_ttm": 7.9568,
      "pcf_ttm": 37.4148,
      "valuation_percentile": 68.21,
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
      "score_trend": 7.1,
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
      "valuation_history_from": "20210722",
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
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 2.49,
        "pct_float": 2.38,
        "chg5_pct": 49.18,
        "net5_repay_days": 1,
        "signal": "adding"
      }
    },
    {
      "code": "300475.SZ",
      "fetch_time": "2026-07-22T15:40:57+0800",
      "name": "香农芯创",
      "pe": 42.1616,
      "pb": 15.9792,
      "ps_ttm": 1.5305,
      "pcf_ttm": 18.9411,
      "valuation_percentile": 64.9,
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
      "score_trend": 7.0,
      "score_value": 5.3,
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
      "valuation_history_from": "20210722",
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
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 50.74,
        "pct_float": 6.37,
        "chg5_pct": -21.21,
        "net5_repay_days": 3,
        "signal": "deleveraging"
      }
    },
    {
      "code": "605020.SH",
      "fetch_time": "2026-07-22T15:40:57+0800",
      "name": "永和股份",
      "pe": 21.0198,
      "pb": 2.7957,
      "ps_ttm": 2.864,
      "pcf_ttm": 19.5814,
      "valuation_percentile": 46.61,
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
      "score_trend": 7.7,
      "score_value": 6.6,
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
          "text": "近3月，股价涨幅超过A股市场 96% 的股票，走势很强。"
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
      "valuation_history_days": 367,
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
        "iv_rank": 0.8503,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 4.84,
        "pct_float": 2.88,
        "chg5_pct": -8.78,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300037.SZ",
      "fetch_time": "2026-07-22T15:40:57+0800",
      "name": "新宙邦",
      "pe": 33.3107,
      "pb": 4.2229,
      "ps_ttm": 4.0826,
      "pcf_ttm": 28.1791,
      "valuation_percentile": 56.51,
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
        "中小创蓝筹指数",
        "储能指数"
      ],
      "score_company": 9.2,
      "score_trend": 7.2,
      "score_value": 5.7,
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
          "text": "近90天， 12家 机构给出评级，其中 75% 为“买入”，距目标价的上涨空间为 51% 。"
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
      "valuation_history_from": "20210722",
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
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.73,
        "pct_float": 2.58,
        "chg5_pct": -7.94,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "688046.SH",
      "fetch_time": "2026-07-22T15:40:57+0800",
      "name": "药康生物",
      "pe": 69.294,
      "pb": 5.0293,
      "ps_ttm": 13.3281,
      "pcf_ttm": 44.3411,
      "valuation_percentile": 64.97,
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
        "专精特新小巨人指数",
        "创新药指数",
        "医疗服务精选指数"
      ],
      "score_company": 8.2,
      "score_trend": 8.1,
      "score_value": 5.4,
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
          "content": "公司发布2026半年报预告，股价盘中上涨 8.03%",
          "tags": [
            "股价上涨"
          ]
        },
        {
          "content": "16:06 药康生物发布2026年半年度业绩预告，预计实现归母净利润1.04亿元至1.14亿元，同比增长46.67%至60.78%；预计扣非净利润9200万元至1亿元，同比增长46.20%至58.92%。业绩增长主要得益于：海外市场本地化销售服务体系完善，客户规模扩大；国内生物医药行业景气度回升，功能药效业务板块收入提速；生产设施产能利用率提升带来规模效应，且期间费用率有所下降。公司将继续推进国际化战略，并加大研发投入。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "15:53 药康生物公告，预计2026年半年度实现归属于母公司所有者的净利润1.04亿元至1.14亿元，与上年同期相比，将增加3309.45万元至4309.45万元，同比增加46.67%至60.78%。预计2026年半年度归属于母公司所有者的扣除非经常性损益的净利润9200万元至1亿元，与上年同期相比，将增加2907.46万元至3707.46万元，同比增加46.20%至58.92%。报告期内，公司锚定国际化和创新的核心战略，一方面加快海外市场销售网络的布局和完善，另一方面持续加大研发资源投入，技术与产品的行业领先优势得到进一步巩固强化。",
          "tags": [
            "快讯"
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
      "valuation_history_days": 269,
      "valuation_history_from": "20240425",
      "current_price": 23.2,
      "price": 23.2,
      "ma5": 25.94,
      "ma10": 25.15,
      "ma20": 22.32,
      "dist_ma5_pct": -10.6,
      "dist_ma10_pct": -7.7,
      "dist_ma20_pct": 3.9,
      "iv_proxy": {
        "primary_name": "科创50",
        "iv_rank": 1.0,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 1.0,
        "pct_float": 1.0,
        "chg5_pct": -6.62,
        "net5_repay_days": 2,
        "signal": "neutral"
      }
    },
    {
      "code": "002947.SZ",
      "fetch_time": "2026-07-22T15:40:57+0800",
      "name": "恒铭达",
      "pe": 25.9056,
      "pb": 4.7901,
      "ps_ttm": 5.0972,
      "pcf_ttm": 24.9908,
      "valuation_percentile": 58.62,
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
      "score_trend": 6.4,
      "score_value": 5.1,
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
      "valuation_history_from": "20210722",
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
        "rzye_yi": 8.24,
        "pct_float": 7.29,
        "chg5_pct": -1.84,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300870.SZ",
      "fetch_time": "2026-07-22T15:40:57+0800",
      "name": "欧陆通",
      "pe": 184.9959,
      "pb": 13.0662,
      "ps_ttm": 7.2908,
      "pcf_ttm": 142.2503,
      "valuation_percentile": 95.3,
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
      "score_trend": 6.5,
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
          "text": " 4家 机构预测，2026年-2028年营收和净利润每年增长均超过 20% ，未来成长较快。"
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
          "content": "14:35 2026年7月13日，铂科电子更新招股书，再次向联交所主板发起冲击。IPO前，公司以远低于公允值的价格向员工持股平台授予股份，其中G批认购价折让幅度超97%。实控人尹国栋的妻子朱燕辉通过合伙架构成为员工持股平台杭州麒信最大的有限合伙人，该安排引发监管问询。经营方面，公司客户集中度较高，大股东比特微同时为主要客户，且受应收账款周转天数拉长及汇兑损失影响，今年一季度由盈转亏。\n铂科电子在推进B轮及B+轮融资期间，多位投资者减持套现，转让价格较后续融资估值存在折让。中国证监会曾要求公司就近期新增股东入股价格的公允性及是否存在利益输送进行说明。实控人尹国栋通过直接及间接方式合计享有公司62.57%表决权。其妻子朱燕辉虽未在公司任职，但通过持有杭州麒信等平台份额，成为该员工持股平台最大的有限合伙人。公司股权激励计划中，多批次认购价较授出日期公允价值折让幅度均在73%以上。\n铂科电子目前尚未收到中国证监会备案通知书。2023年至2025年，公司收入复合年增长率达100%，今年一季度收入同比增长35.3%。公司业务重心向境外转移，一季度境外销售占比升至78.3%。大股东比特微虽持股比例降至8.52%，但仍为前五大客户。公司与新晋第一大客户比特小鹿的账期长达90天，导致应收账款余额于今年3月末攀升至2.4亿元，且面临汇兑风险。\n按业务板块看，专用算力服务器电源为第一大收入来源，ESS电能转换业务占比有所波动。公司AI算力服务器电源业务收入占比长期不足1%，且未设立专门生产线。研发费用率呈逐年下滑趋势，截至IPO前，公司拥有发明专利11项，少于同业可比公司。受主动下调产品售价影响，公司两大业务线毛利率均出现下滑。\n受营销与研发投入及外汇损失影响，铂科电子今年一季度净亏损532.4万元，经调整净利润同比下降83.6%。经营活动产生的现金流量净额为-7976.6万元，同比由正转负。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "10:10 国盛证券研报指出，随着AI大模型训练带来的算力需求爆发，GPU机柜功率显著攀升，算力机架正由千瓦级迈向兆瓦级。传统低压直流母线方案在单机柜功率超200kW后存在空间挤占及铜材耗材过高等短板。800VDC架构凭借精简架构、降低耗材、原生兼容三大优势成为核心升级方向。英伟达供电方案正经历从传统交流机柜向800VDC Power Rack演进，其中800VDC Power Rack（Sidecar）作为短期主流方案，通过将AC-DC整流外置至独立侧边电源柜，有效释放机柜空间并降低传输损耗。\n在产业布局方面，光宝科技等台系厂商目前处于主导地位，大陆厂商正加速追赶。麦格米特已推出相关Power Shelf产品，欧陆通已供货谷歌，富特科技、奥海科技等企业正向数据中心电源领域拓展。国盛证券建议关注富特科技、宏发股份、欣锐科技、中恒电气、麦格米特、欧陆通、通合科技、优优绿能、奥海科技等公司，并提示下游需求不及预期、技术路线迭代及竞争加剧等风险。",
          "tags": [
            "资讯"
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
      "valuation_history_days": 314,
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
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 10.85,
        "pct_float": 3.26,
        "chg5_pct": -8.83,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "300438.SZ",
      "fetch_time": "2026-07-22T15:40:59+0800",
      "name": "鹏辉能源",
      "pe": 48.2338,
      "pb": 4.8898,
      "ps_ttm": 1.8445,
      "pcf_ttm": 25.1294,
      "valuation_percentile": 52.68,
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
        "预期提升指数",
        "锂电池指数",
        "养老金指数",
        "储能指数",
        "固态电池指数",
        "钠离子电池指数",
        "动力电池指数",
        "TWS耳机指数",
        "扭亏指数",
        "ETC指数"
      ],
      "score_company": 8.3,
      "score_trend": 7.4,
      "score_value": 6.5,
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
          "text": "近90天， 8家 机构给出评级，其中 88% 为“买入”，距目标价的上涨空间为 92% 。"
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
          "content": "14:01 标普全球能源发布2026年度Tier 1清洁能源技术企业榜单，首次新增储能电芯供应商类别，鹏辉能源入选该榜单。鹏辉能源表示，此次入选基于公司在储能领域的技术研发及产品矩阵布局。经营业绩方面，根据公司2026年半年度业绩预告，预计上半年实现归母净利润8亿元至8.66亿元，同比扭亏为盈。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "17:30 鹏辉能源发布2026年半年度业绩预告，预计上半年归母净利润为8亿元至8.66亿元，上年同期为亏损8822.67万元；扣非净利润预计为7.92亿元至8.56亿元，上年同期为亏损1.59亿元。公司表示，业绩增长主要得益于储能行业景气度持续，产品产销两旺，订单增长带动营收与利润扩容。\n鹏辉能源在应急电源高倍率电池、户用储能电芯及工商业储能系统等细分领域具有市场份额优势。公司正推进“海外跃升”战略，已建立十大海外办事处，业务覆盖美国、德国、日本、新加坡、印度等市场。公司董事长夏信德表示，行业正从价格竞争转向价值竞争，需通过上下游协同研发与技术迭代应对市场变化。\n鹏辉能源2025年全年实现营收119.44亿元，归母净利润2.06亿元。2026年上半年业绩预告显示公司经营规模实现增长。",
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
      "valuation_history_from": "20210722",
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
        "iv_rank": 0.8711,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 8.88,
        "pct_float": 3.49,
        "chg5_pct": -21.44,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "002407.SZ",
      "fetch_time": "2026-07-22T15:40:59+0800",
      "name": "多氟多",
      "pe": 67.7097,
      "pb": 4.1517,
      "ps_ttm": 3.3598,
      "pcf_ttm": null,
      "valuation_percentile": 59.54,
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
      "score_company": 8.0,
      "score_trend": 6.7,
      "score_value": 5.5,
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
          "text": "北向资金持股 4.2% ，很受外资机构青睐；公募基金持股 6.9% ，很受内资机构青睐。"
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
          "content": "10:09 截至2026年7月21日，中证新能源汽车指数上涨2.22%，成分股华友钴业、寒锐钴业、国轩高科等上涨。新能源车ETF博时(159824)盘中涨幅一度超3%。据中汽协数据，6月国内新能源车销量164.3万辆，同环比分别增长23.6%和9.8%，其中出口52.3万辆，同环比分别增长155.1%和17.2%。乘联会数据显示，6月新能源乘用车渗透率达62.8%，B级及以上车型零售销量占比54.5%。中信建投证券指出，行业进入政策退坡后的修复周期，二季度市场延续复苏，出口与高端化成为核心增长引擎。中证新能源汽车指数最新PE-TTM为26.13倍，处于近1年0.78%分位。\n截至2026年6月30日，中证新能源汽车指数前十大权重股包括宁德时代、比亚迪、汇川技术、亿纬锂能、三花智控、赣锋锂业、天赐材料、华友钴业、天齐锂业、多氟多，合计占比51.72%。相关产品包括新能源车ETF博时(159824)及其联接基金。",
          "tags": [
            "资讯"
          ]
        },
        {
          "content": "10:27 截至2026年7月20日，中证新能源汽车产业指数成分股表现分化，先导智能、当升科技、宁德时代涨幅居前。新能源车ETF平安（515700）最新报价2.07元，盘中换手率1.81%，成交额2640.39万元。消息面上，比亚迪巴西工厂第10万辆新能源汽车（海鸥车型）正式下线，该工厂在岗员工已超5500人。广发证券分析称，财政部等部门明确自2026年9月起对锂离子蓄电池征收消费税，并对钠离子、固态电池等技术路线给予免税政策，此举将拉大技术路线成本差异。近期磷酸铁锂龙头已上调加工费，叠加三季度需求旺季，产业链景气度有望改善。中证新能源汽车产业指数涵盖整车、电池及材料等领域，前十大权重股包括宁德时代、比亚迪、汇川技术等。\n基金投资存在风险，过往业绩不预示未来表现，投资者应根据自身风险承受能力审慎决策，详细阅读基金法律文件。",
          "tags": [
            "资讯"
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
      "valuation_history_from": "20210722",
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
        "rzye_yi": 20.52,
        "pct_float": 6.31,
        "chg5_pct": -15.75,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    },
    {
      "code": "603127.SH",
      "fetch_time": "2026-07-22T15:40:59+0800",
      "name": "昭衍新药",
      "pe": 72.7419,
      "pb": 4.2532,
      "ps_ttm": 21.3547,
      "pcf_ttm": 71.0274,
      "valuation_percentile": 50.94,
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
        "预期提升指数",
        "万得预增指数",
        "创新药指数",
        "反内卷指数",
        "医疗服务精选指数",
        "CRO指数"
      ],
      "score_company": 8.2,
      "score_trend": 9.5,
      "score_value": 5.7,
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
      "valuation_history_from": "20210722",
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
        "iv_rank": 0.8503,
        "sizing": "tight"
      },
      "margin": {
        "rzye_yi": 6.69,
        "pct_float": 2.16,
        "chg5_pct": 2.07,
        "net5_repay_days": 2,
        "signal": "adding"
      }
    },
    {
      "code": "002056.SZ",
      "fetch_time": "2026-07-22T15:40:59+0800",
      "name": "横店东磁",
      "pe": 19.8426,
      "pb": 3.5095,
      "ps_ttm": 1.5453,
      "pcf_ttm": 10.3191,
      "valuation_percentile": 56.65,
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
        "新材料指数",
        "新能源汽车指数",
        "锂电池指数",
        "苹果指数",
        "特斯拉指数",
        "磷酸铁锂电池指数",
        "新能源指数",
        "光伏指数",
        "能源出海指数",
        "无线充电指数",
        "电源设备精选指数",
        "触板指数",
        "三元锂电池指数",
        "稀土永磁指数",
        "磁悬浮列车指数",
        "钙钛矿电池指数"
      ],
      "score_company": 8.6,
      "score_trend": 7.0,
      "score_value": 5.7,
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
      "valuation_history_from": "20210722",
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
        "rzye_yi": 7.04,
        "pct_float": 1.9,
        "chg5_pct": -12.48,
        "net5_repay_days": 4,
        "signal": "deleveraging"
      }
    }
  ],
  "active_positions": [],
  "position_prices": {},
  "missed_opportunity_prices": [
    {
      "code": "600961",
      "name": "株冶集团",
      "recommended_date": "2026-07-22",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 23.48,
      "return_pct": null
    },
    {
      "code": "601958",
      "name": "金钼股份",
      "recommended_date": "2026-07-22",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 21.43,
      "return_pct": null
    },
    {
      "code": "300373",
      "name": "扬杰科技",
      "recommended_date": "2026-07-22",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 96.3,
      "return_pct": null
    },
    {
      "code": "603127",
      "name": "昭衍新药",
      "recommended_date": "2026-07-22",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 48.06,
      "return_pct": null
    },
    {
      "code": "002821",
      "name": "凯莱英",
      "recommended_date": "2026-07-22",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 164.28,
      "return_pct": null
    },
    {
      "code": "688046",
      "name": "药康生物",
      "recommended_date": "2026-07-22",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 27.0,
      "return_pct": null
    },
    {
      "code": "301536",
      "name": "星宸科技",
      "recommended_date": "2026-07-22",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 137.0,
      "return_pct": null
    },
    {
      "code": "688777",
      "name": "中控技术",
      "recommended_date": "2026-07-22",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 86.0,
      "return_pct": null
    },
    {
      "code": "300684",
      "name": "中石科技",
      "recommended_date": "2026-07-21",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 49.81,
      "return_pct": null
    },
    {
      "code": "688378",
      "name": "奥来德",
      "recommended_date": "2026-07-21",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 39.8,
      "return_pct": null
    },
    {
      "code": "002192",
      "name": "融捷股份",
      "recommended_date": "2026-07-21",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 60.4,
      "return_pct": null
    },
    {
      "code": "605020",
      "name": "永和股份",
      "recommended_date": "2026-07-21",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 33.05,
      "return_pct": null
    },
    {
      "code": "002056",
      "name": "横店东磁",
      "recommended_date": "2026-07-21",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 21.7,
      "return_pct": null
    },
    {
      "code": "300475",
      "name": "香农芯创",
      "recommended_date": "2026-07-21",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 166.6,
      "return_pct": null
    },
    {
      "code": "000703",
      "name": "恒逸石化",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 15.16,
      "return_pct": null
    },
    {
      "code": "688331",
      "name": "荣昌生物",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 126.9,
      "return_pct": null
    },
    {
      "code": "601126",
      "name": "四方股份",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 42.79,
      "return_pct": null
    },
    {
      "code": "688502",
      "name": "茂莱光学",
      "recommended_date": "2026-07-20",
      "recommended_price": null,
      "recommendation": "WATCH",
      "current_price": 386.49,
      "return_pct": null
    }
  ],
  "iv_sentiment": {
    "date": "2026-07-22",
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
        "current_iv": 0.2625,
        "is_live": false,
        "iv_high": 0.2272,
        "iv_low": 0.1137,
        "iv_high_raw": 0.2625,
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
            "date": "2026-07-22",
            "iv": 0.2625
          }
        ],
        "sigma_range": [
          0.105,
          0.2285
        ],
        "name": "50ETF",
        "desc": "大盘蓝筹",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "510300",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 218,
        "current_iv": 0.2285,
        "is_live": false,
        "iv_high": 0.2476,
        "iv_low": 0.1201,
        "iv_high_raw": 0.3137,
        "iv_low_raw": 0.069,
        "iv_rank": 0.8503,
        "iv_rank_raw": 0.6518,
        "iv_percentile": 0.9358,
        "iv_percentile_raw": 0.9156,
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
          0.1097,
          0.2491
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
        "current_iv": 0.2419,
        "is_live": false,
        "iv_high": 0.3531,
        "iv_low": 0.194,
        "iv_high_raw": 0.4544,
        "iv_low_raw": 0.107,
        "iv_rank": 0.3009,
        "iv_rank_raw": 0.3883,
        "iv_percentile": 0.3333,
        "iv_percentile_raw": 0.3289,
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
          0.3546
        ],
        "name": "500ETF",
        "desc": "中证500",
        "interpretation": "中性"
      },
      {
        "underlying": "588000",
        "lookback_days": 252,
        "data_points": 225,
        "data_points_filtered": 214,
        "current_iv": 0.7788,
        "is_live": false,
        "iv_high": 0.6127,
        "iv_low": 0.2467,
        "iv_high_raw": 0.7788,
        "iv_low_raw": 0.126,
        "iv_rank": 1.0,
        "iv_rank_raw": 1.0,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9956,
        "outliers_removed": 11,
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
            "iv": 0.7006
          },
          {
            "date": "2026-07-22",
            "iv": 0.7788
          }
        ],
        "sigma_range": [
          0.1614,
          0.6205
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
        "current_iv": 0.444,
        "is_live": false,
        "iv_high": 0.4789,
        "iv_low": 0.2082,
        "iv_high_raw": 0.6363,
        "iv_low_raw": 0.2082,
        "iv_rank": 0.8711,
        "iv_rank_raw": 0.5508,
        "iv_percentile": 0.9266,
        "iv_percentile_raw": 0.9099,
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
          0.1751,
          0.4808
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
        "current_iv": 0.4068,
        "is_live": false,
        "iv_high": 0.3461,
        "iv_low": 0.1804,
        "iv_high_raw": 0.468,
        "iv_low_raw": 0.1804,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.7872,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.991,
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
          0.1764,
          0.3462
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
        "current_iv": 0.3431,
        "is_live": false,
        "iv_high": 0.258,
        "iv_low": 0.1298,
        "iv_high_raw": 0.3431,
        "iv_low_raw": 0.1298,
        "iv_rank": 1.0,
        "iv_rank_raw": 1.0,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9955,
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
          0.112,
          0.2591
        ],
        "name": "300ETF深",
        "desc": "深市宽基",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      },
      {
        "underlying": "159901",
        "lookback_days": 252,
        "data_points": 222,
        "data_points_filtered": 216,
        "current_iv": 0.3521,
        "is_live": false,
        "iv_high": 0.3391,
        "iv_low": 0.1682,
        "iv_high_raw": 0.4504,
        "iv_low_raw": 0.1682,
        "iv_rank": 1.0,
        "iv_rank_raw": 0.6516,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.982,
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
          0.1466,
          0.3391
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
        "current_iv": 0.756,
        "is_live": false,
        "iv_high": 0.6147,
        "iv_low": 0.184,
        "iv_high_raw": 0.756,
        "iv_low_raw": 0.184,
        "iv_rank": 1.0,
        "iv_rank_raw": 1.0,
        "iv_percentile": 1.0,
        "iv_percentile_raw": 0.9955,
        "outliers_removed": 7,
        "outlier_details": [
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
            "iv": 0.6686
          },
          {
            "date": "2026-07-22",
            "iv": 0.756
          }
        ],
        "sigma_range": [
          0.1661,
          0.6155
        ],
        "name": "科创板50",
        "desc": "科创板（备用代理）",
        "interpretation": "极高 (市场恐慌，可能是超卖反弹机会)"
      }
    ],
    "overall_sentiment": {
      "signal": "极度恐慌",
      "avg_iv_rank": 0.8045,
      "avg_iv_percentile": 0.8391,
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
    "breadth_ratio": 0.3948,
    "up": 1530,
    "down": 3875,
    "positive_indices": [
      "上证指数"
    ],
    "negative_indices": [
      "深证成指",
      "创业板指"
    ],
    "limit_ups": 48,
    "limit_downs": 10,
    "sizing_multiplier": 0.5,
    "hard_block": false,
    "reason": "Entry regime weak: breadth 0.39:1, 1/3 major indices green, 48 limit-ups / 10 limit-downs. Allow entries only with 50% sizing."
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
  "active_learnings": "## Active Rules (proven, hitRate ≥ 75%)\n- [h013] Strong breadth alone is not enough to force entries; without candidate RPS and MA-distance data, the correct momentum decision is to keep cash. (hitRate: 99%, n=129, confidence: 98%)\n- [h028] Today’s relative leaders are concentrated in communication equipment and adjacent tech hardware, while cyclicals/agri/resource laggards are being de-risked aggressively. (hitRate: 100%, n=43, confidence: 98%)\n- [h019] Bottom-list sectors should be treated as hard no-buy zones even when individual names still carry acceptable RPS readings. (hitRate: 100%, n=42, confidence: 98%)\n- [h027] MA-distance discipline remains critical inside hot sectors: a hot sector does not override chase risk when dist_ma5_pct exceeds 6% or dist_ma10_pct exceeds 8%. (hitRate: 100%, n=40, confidence: 98%)\n- [h023] Raising stops mechanically after +10% works well in weak tapes because it converts a fast winner into a low-risk hold without needing a fresh market call. (hitRate: 100%, n=36, confidence: 97%)\n- [h021] The MA-distance anti-chase rule is doing real work: several visually strong names fail because they are too far above short-term support. (hitRate: 98%, n=98, confidence: 97%)\n- [h017] Low-IV conditions around 16-22% IV rank do not justify freezing risk when breadth is 5.6:1; they argue for normal sizing but tighter discipline on chasing. (hitRate: 100%, n=26, confidence: 96%)\n\n## Working Hypotheses (testing, hitRate ≥ 65%)\n- [h077] The hard block is preventing FOMO entries. 新宙邦 (宁德时代协议 catalyst, VCP SETUP) and 奥来德 (dist_ma5 0.3%) would have been tempting buys in V1. V2 correctly forces cash preservation in panic regime. (hitRate: 100%, n=8, confidence: 90%)\n- [h024] Stop-proximity violations deserve proactive action before the hard stop is hit, especially in 科创板 names where gap risk can erase the remaining cushion quickly. (hitRate: 100%, n=5, confidence: 86%)\n",
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
