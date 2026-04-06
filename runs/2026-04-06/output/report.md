# 每日研究报告 2026-04-06

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3880.10 | -1.00% |
| 深证成指 | 13352.90 | -0.99% |
| 创业板指 | 3149.60 | -0.73% |
| 科创50 | 1256.21 | -0.47% |

涨跌比: 716涨 / 4746跌 / 5486总

**热门板块**: 通信设备(+3.19%), 电子化学品Ⅱ(+1.40%), 自动化设备(+1.10%), 元件(+1.04%), 光学光电子(+0.73%)

**冷门板块**: 林业Ⅱ(-6.61%), 焦炭Ⅱ(-5.46%), 农业综合Ⅱ(-4.64%), 燃气Ⅱ(-3.65%), 渔业(-3.63%)

Bearish/panic regime. Breadth 0.15:1 bearish, 39涨停/46跌停, all 3 major indices red; this fails the minimum long-entry gate by a wide margin. Hot sectors (top 5): 通信设备(+3.19%), 电子化学品Ⅱ(+1.40%), 自动化设备(+1.10%), 元件(+1.04%), 光学光电子(+0.73%). Cold sectors (bottom 5): 林业Ⅱ(-6.61%), 焦炭Ⅱ(-5.46%), 农业综合Ⅱ(-4.64%), 燃气Ⅱ(-3.65%), 渔业(-3.63%). Position sector alignment: 0/0 positions in hot sectors. Web checks suggest AI/通信 remains the only visible strength pocket while broad selling is driven by profit-taking/risk-off; IV context unavailable, so no stock-level throttle benefit applies. With breadth below 1:1 and f10=46, this is a no-new-position day.

## 策略池扫描

扫描 **20** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) (RPS 91.15%) — Entry regime blocks all new longs: breadth only 0.15:1, 0/3 major indices green, 46跌停 > 39涨停. Stock also fails MA chase rule with dist_ma5_pct 7.0% and dist_ma10_pct 8.3%.
2. **烽火通信** (600498) (RPS 95.3%) — Sector is hot, but this is still a skip today: entry regime is weak and the stock is overextended with dist_ma5_pct 11.2% and dist_ma10_pct 13.1%, violating the no-chasing rule.
3. **杰普特** (688025) (RPS 86.69%) — Automatic equipment is a relative-strength pocket and RPS120 86.69 is in range, but market regime forbids new entries. Recent news flow is mixed and stock-specific catalyst is less urgent than sector tape risk.
4. **东材科技** (601208) (RPS 90.86%) — RPS120 90.86 and MA distances are acceptable, but sector is not in the provided top 30% list and the market buy gate is decisively closed. No new long in weak tape.
5. **利柏特** (605167) (RPS 93.49%) — Individual setup is acceptable on MA distance, but sector is not in the top-performing group and breadth is far below the 1.5:1 minimum. Sector-first rule and regime gate both say skip.
6. **华懋科技** (603306) (RPS 92.83%) — Sector (汽车零部件) is not in the provided hot-sector list, and the market regime is weak. Corporate action catalyst exists, but sector gravity and poor tape keep it out.
7. **华锡有色** (600301) (RPS 93.29%) — Commodity/minor metals are not in the provided top sector list, and dist_ma20_pct is -13.1%, showing loss of near-term structure. Weak market means no countertrend commodity entries.
8. **三祥新材** (603663) (RPS 91.77%) — RPS120 is in range, but sector is not in the hot-sector top group and dist_ma20_pct is -12.6%, beyond the MA20 threshold. Fails both sector-first and MA-distance discipline.
9. **芯源微** (688037) (RPS 85.85%) — Semiconductor equipment had intraday activity, but sector is not in the provided top 30% list and the company has negative net_profit_yoy. In this market, that is a skip, not a small buy.
10. **华通线缆** (605196) (RPS 95.36%) — 电网设备 is a relative-strength sector, but RPS120 95.36 is above the allowed zone without a clear top-10% sector exception from the provided sector table, and the market regime blocks all new entries anyway.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': 'When breadth collapses to 0.15:1 with all three major indices red, even strong-sector candidates should be skipped outright; preserving cash is the momentum action, not a missed trade.', 'type': 'rule', 'tags': ['sector', 'entry-filter', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum entries need market participation to follow through. In a broad liquidation tape, isolated strength tends to fail or become untradable due to poor entry timing.'}
- {'text': 'MA-distance discipline remains critical inside hot sectors: a hot sector does not override chase risk when dist_ma5_pct exceeds 6% or dist_ma10_pct exceeds 8%.', 'type': 'heuristic', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'In weak regimes, extended names have less room for upside expansion and much higher snapback risk, so buying pullbacks is superior to buying spikes.'}
- {'text': 'Today’s relative leaders are concentrated in communication equipment and adjacent tech hardware, while cyclicals/agri/resource laggards are being de-risked aggressively.', 'type': 'observation', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'When the market sells off broadly but one tech cluster still leads the board, capital is narrowing into perceived growth defensiveness rather than embracing a full risk-on rally.'}
