# 每日研究报告 2026-07-02

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4075.31 | -0.90% |
| 深证成指 | 15782.35 | -2.09% |
| 创业板指 | 4112.97 | -3.47% |
| 科创50 | 2053.69 | -4.61% |

涨跌比: 3226涨 / 2147跌 / 5517总

**热门板块**: 林业Ⅱ(+7.98%), 贵金属(+6.39%), 电机Ⅱ(+3.27%), 橡胶(+3.20%), 工程机械(+2.81%)

**冷门板块**: 通信设备(-5.39%), 半导体(-4.85%), 元件(-4.77%), 消费电子(-3.59%), 其他电子Ⅱ(-3.05%)

Distribution day. All 4 major indices red (科创50 -4.61%, 创业板 -3.47%). Breadth 1.50:1 barely positive; 135涨停/6跌停. Clear tech→commodities rotation: semiconductors/communication/electronics collapsing, gold/precious metals surging. Both positions hit trailing stops intraday — selling out. 0/3 indices green blocks new entries. IV data unavailable. Cash is the right position.

## 策略池扫描

扫描 **66** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **多氟多** (002407) (RPS 92.28%) — Rule 2b triple violation: dist_ma5_pct 12.2% (>6%), dist_ma10_pct 25.4% (>8%), dist_ma20_pct 41.5% (>12%). Extreme overextension.
2. **京仪装备** (688652) (RPS 92.3%) — Rule 2b violation dist_ma10_pct 20.6% (>8%), dist_ma20_pct 31.7%. Sector 半导体 bottom 5 (Rule 1).
3. **华灿光电** (300323) (RPS 94.84%) — Rule 2b violation: dist_ma5_pct 10.8% (>6%), dist_ma10_pct 22.8% (>8%). 光学光电子 sector not clearly top 30%.
4. **新洁能** (605111) (RPS 94.01%) — Sector 半导体 bottom 5 at -4.85% (Rule 1). Yesterday -7% selloff with abnormal volume. dist_ma20_pct 26.2% extreme.
5. **思瑞浦** (688536) (RPS 94.13%) — Sector 半导体 bottom 5 at -4.85% (Rule 1). dist_ma20_pct 11.4% approaching Rule 2b limit.
6. **德科立** (688205) (RPS 94.03%) — Sector 通信设备 DEAD LAST at -5.39% (Rule 1 hard skip). Stock in downtrend: dist_ma20_pct -16.3%, RPS20 only 77.92.
7. **固德威** (688390) (RPS 92.7%) — 光伏设备 sector weak. Stock in freefall: dist_ma20_pct -22.4%, RPS20 only 80.63. Not a momentum play.
8. **骄成超声** (688392) (RPS 89.72%) — Rule 2b triple violation: dist_ma5_pct 11.4% (>6%), dist_ma10_pct 25.9%, dist_ma20_pct 36.4%. No entry at any price.

## 今日研究结论

- 新开仓: 0只
- 跳过: 8只

### 新教训
- {'text': 'Buy-gate rule (≥2/3 major indices green) correctly prevented entries on a distribution day. Breadth 1.50:1 barely passed but 0/3 indices green = no fresh risk.', 'type': 'rule', 'tags': ['entry-filter', 'market-regime'], 'evidence_type': 'supporting', 'mechanism': 'When all major indices are red despite decent breadth, gains are concentrated in defensive/rotation sectors while momentum positions get crushed. Deploying capital here would be fighting the tape.'}
- {'text': 'Trailing stops converted +30%+ gains into realized profits. Both 上海新阳 and 路维光电 had monster runs; the mechanical -10% trail from highs locked in the bulk of those gains before the semiconductor rout hit.', 'type': 'heuristic', 'tags': ['exit-rule', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'Trailing stops work especially well for momentum winners: they let the stock run while automatically tightening as the stock rises, creating an asymmetric payoff where most of the gain is protected.'}
- {'text': 'Tech-to-commodities rotation is a regime shift signal. 科创50 -4.61% vs 贵金属 +6.39% on the same day is not noise. Next hot money likely flows to resources/cyclicals. Monitor gold, machinery, and chemical sectors for future entries when buy-gate clears.', 'type': 'signal', 'tags': ['sector', 'market-regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h028', 'mechanism': 'Late-cycle rotations from growth/tech to value/commodities often signal risk appetite contraction. Gold strength + tech weakness = classic defensive posture.'}
- {'text': 'MA-distance rule (h027) continues filtering out dangerous entries. Multiple candidates with excellent RPS (多氟多 RPS120=92.3, 京仪装备 RPS120=92.3) were un-buyable due to extreme MA extensions. This rule would have prevented buying into the very stocks that got crushed today.', 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h027', 'mechanism': 'Stocks trading 20%+ above MA10 have already priced in weeks of good news. Any disappointment or sector rotation triggers violent mean reversion, as seen across the semiconductor complex today.'}
