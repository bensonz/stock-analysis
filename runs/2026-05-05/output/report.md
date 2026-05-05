# 每日研究报告 2026-05-05

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4112.16 | +0.11% |
| 深证成指 | 15107.55 | -0.09% |
| 创业板指 | 3677.15 | -0.27% |
| 科创50 | 1571.07 | +5.19% |

涨跌比: 2878涨 / 2461跌 / 5462总

**热门板块**: 半导体(+4.71%), 综合Ⅱ(+4.03%), 航天装备Ⅱ(+3.88%), 家电零部件Ⅱ(+2.90%), 风电设备(+2.63%)

**冷门板块**: 游戏Ⅱ(-3.59%), 贸易Ⅱ(-2.76%), 酒店餐饮(-2.65%), 燃气Ⅱ(-2.60%), 玻璃玻纤(-2.46%)

Breadth 1.17:1 weak/panic, 98涨停/55跌停, only 上证指数 green while 深证成指 and 创业板指 are red; 科创50 +5.19% and 半导体 +4.71% show narrow high-beta leadership, but the buy gate fails on breadth and index confirmation. Hot sectors (top 5): 半导体 +4.71%, 综合Ⅱ +4.03%, 航天装备Ⅱ +3.88%, 家电零部件Ⅱ +2.90%, 风电设备 +2.63%. Cold sectors (bottom 5): 游戏Ⅱ -3.59%, 贸易Ⅱ -2.76%, 酒店餐饮 -2.65%, 燃气Ⅱ -2.60%, 玻璃玻纤 -2.46%. Position sector alignment: 0/0 positions in hot sectors. IV context: no usable IV data, so no sizing edge from volatility sentiment; regime block remains decisive.

## 策略池扫描

扫描 **47** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **普冉股份** (688766) (RPS 98.92%) — Sector is hot and MA distances are acceptable, but rps120 98.92 is above the 95 chase ceiling; skip and wait for pullback.
2. **北化股份** (002246) (RPS 87.81%) — Good near-support setup and VCP=SETUP, but entry regime blocks all new longs; also sector is not confirmed in today's top leadership list.
3. **云图控股** (002539) (RPS 87.72%) — MA distances are clean and rps120 87.72 is valid, but sector is not in today's top leadership group and entry regime hard-blocks new positions.
4. **科达制造** (600499) (RPS 91.17%) — Strong earnings/lithium catalyst and acceptable MA profile, but dist_ma20_pct 12.5 exceeds the 12% anti-chase limit; entry regime also blocks new longs.
5. **鄂尔多斯** (600295) (RPS 92.35%) — MA profile and rps120 are acceptable, but sector is not in today's top 30% leadership set and catalyst is weaker than semiconductor/defense leaders.
6. **亚钾国际** (000893) (RPS 93.34%) — Fundamentals are strong, but sector is not in today's top leadership group; current price 54.05 is below MA5/MA10/MA20, so this is not a clean momentum entry now.
7. **华锡有色** (600301) (RPS 92.93%) — Price is near moving averages and rps120 92.93 is in range, but sector leadership is weaker than today's semiconductor/aviation leaders and entry regime blocks fresh risk.
8. **华峰测控** (688200) (RPS 91.25%) — Semiconductor leader with strong catalyst, but dist_ma5_pct 9.3, dist_ma10_pct 16.5 and dist_ma20_pct 23.9 all violate anti-chase rules.
9. **东材科技** (601208) (RPS 92.17%) — Earnings and price-hike catalyst are real, but dist_ma10_pct 13.0 and dist_ma20_pct 19.6 are too extended; no chasing.
10. **明阳电路** (300739) (RPS 90.65%) — One of the cleaner charts with current price 27.13 near MA5 26.77/MA10 25.87/MA20 27.2, but sector is not in today's top leadership list and entry regime hard-blocks new longs.
11. **咸亨国际** (605056) (RPS 94.5%) — Current price 25.04 is below MA5/MA10 and trend has weakened; not a buy-strength entry despite acceptable rps120.
12. **博云新材** (002297) (RPS 93.79%) — Defense/aviation sector is hot and catalyst is strong, but dist_ma10_pct 9.4 and dist_ma20_pct 44.7 violate anti-chase rules.
13. **莱特光电** (688150) (RPS 94.69%) — Sector trend is positive and earnings catalyst is valid, but dist_ma10_pct 10.3 and dist_ma20_pct 22.5 are too extended for a new entry.
14. **广合科技** (001389) (RPS 92.58%) — High-quality PCB growth story, but dist_ma5_pct 13.5, dist_ma10_pct 27.9 and dist_ma20_pct 34.9 are extreme extension; skip chasing.
15. **芯源微** (688037) (RPS 88.89%) — Semiconductor sector is the day's strongest, but rps120 88.89 is fine while MA distances are far too extended: 14.6% above MA5, 21.3% above MA10, 29.7% above MA20.

## 今日研究结论

- 新开仓: 0只
- 跳过: 15只

### 新教训
- {'text': "A hot leading sector is not enough when market breadth fails the minimum gate; today's semiconductor surge coexists with only 1.17:1 breadth, 1/3 major indices green, and 55跌停, so the correct action is still no new positions.", 'type': 'rule', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Narrow leadership can produce attractive charts, but weak cross-market participation increases breakout failure risk for fresh entries.'}
- {'text': 'The anti-chase MA rule is doing real work again: many of the strongest candidates today are exactly the ones far above MA5/MA10/MA20, especially in semiconductors and AI hardware.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'When price is stretched too far from short-term support, even strong momentum names become poor risk-reward entries because mean reversion can hit before trend continuation.'}
- {'text': 'In a mixed tape, the best future buy list often comes from stocks that pass RPS and support-distance checks but are blocked by regime, such as 北化股份、云图控股、明阳电路; these should be first reviewed when breadth improves.', 'type': 'heuristic', 'tags': ['timing', 'sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Separating stock quality from regime timing prevents forced entries today while preserving prepared names for the next valid risk-on window.'}
