# 每日研究报告 2026-05-27

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4093.73 | -1.25% |
| 深证成指 | 15736.47 | -0.88% |
| 创业板指 | 4045.77 | +0.07% |
| 科创50 | 1815.45 | -2.80% |

涨跌比: 974涨 / 4489跌 / 5507总

**热门板块**: 综合Ⅱ(+2.74%), 白酒Ⅱ(+2.18%), 煤炭开采(+1.70%), 影视院线(+1.50%), 电池(+1.40%)

**冷门板块**: 非金属材料Ⅱ(-5.65%), 贵金属(-5.40%), 林业Ⅱ(-5.19%), 家电零部件Ⅱ(-4.36%), 工业金属(-3.97%)

PANIC TAPE: Breadth 0.22:1 (974 up / 4489 down), 39 stocks at 跌停, only 创业板指 barely green (+0.07%). Quant cascade + wave of insider selling at tech highs driving broad rout. Defense sectors (白酒+2.18%, 煤炭+1.70%) the only hiding spots. 科创50 -2.80% leads losses. Battery (+1.40%) lone resilient growth sector. IV mixed: 300ETF complacent at 14.2% rank, 创业板 elevated at 51.8%. NO new positions — hard_block active. 100% cash.

## 策略池扫描

扫描 **54** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **伟测科技** (688372) (RPS 93.5%) — Best candidate in pool: RPS120=93.5%, dist_ma5=+0.3% (ideal pullback to MA5), 0 risk factors, semiconductor testing leader. Sector trending. BUT regime is panic (breath 0.22:1, hard_block=true). Priority watch for when regime clears.
2. **睿创微纳** (688002) (RPS 89.59%) — RPS120=89.6%, dist_ma5=+0.4% (at MA5 support), 0 risks, defense electronics leader, 7.5% northbound. SKIP: panic regime.
3. **山东赫达** (002810) (RPS 94.9%) — Only VCP stock (SETUP quality), RPS120=94.9%, earnings beat catalyst, dist_ma5=-2.6% (pulled back to near MA5). SKIP: panic regime + 化学制品 sector not in top 30% today.
4. **德科立** (688205) (RPS 94.86%) — RPS120=94.9%, dist_ma10=-0.2% (tight to MA10 support), CPO theme. SKIP: panic regime + PE=497 red flag.
5. **湖南裕能** (301358) (RPS 93.78%) — Battery sector #5 hot (+1.40%), RPS120=93.8%, profit +1338%, lithium tailwind. dist_ma5=-6.8% (pulled back below MA5). SKIP: panic regime.
6. **芯碁微装** (688630) (RPS 92.93%) — RPS120=92.9%, 0 risks, semicon equipment. BUT dist_ma10=+11.4% (Rule 2b violation: >8% chasing risk). SKIP: regime + overextended.
7. **联瑞新材** (688300) (RPS 92.41%) — dist_ma5=+8.5% (Rule 2b violation), dist_ma20=+40.6%. Extreme overextension. SKIP: regime + massive chasing risk.
8. **民爆光电** (301362) (RPS 99.82%) — dist_ma5=+19.0%, dist_ma20=+83.3%. Comically overextended. SKIP: regime + chasing.
9. **帝尔激光** (300776) (RPS 90.89%) — dist_ma5=+9.4%, dist_ma20=+62.3%. Extreme extension. SKIP: regime + chasing risk.
10. **凯旺科技** (301182) (RPS 94.49%) — dist_ma5=+9.4%, negative PE (loss-making), RPS120=94.5%. SKIP: regime + chasing + weak fundamentals.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': 'Hard_block regime filter validated: breadth 0.22:1 + 1/3 indices green correctly prevents entry into a quant-driven sell-off. Cash is the right position today.', 'type': 'signal', 'tags': ['entry-filter', 'regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When breadth collapses below 0.5:1 with only one index barely hanging on, even the best individual stock setups will be overwhelmed by systematic selling. The regime filter prevents buying into a falling knife.'}
- {'text': "Today's sector rotation is textbook risk-off: 白酒 +2.18%, 煤炭 +1.70% (defense) vs non-ferrous materials -5.65%, precious metals -5.40% (cyclicals crushed). Momentum strategies should sit out risk-off rotations entirely — these defensive sectors produce flat/slow returns, not the 10-20% runs we target.", 'type': 'observation', 'tags': ['sector', 'regime'], 'evidence_type': 'supporting', 'mechanism': "Risk-off sectors (liquor, coal, conglomerates) are low-volatility havens. They don't generate momentum profits. When the market rotates into them, it means risk appetite has collapsed and momentum strategies have no edge."}
- {'text': '电池 sector resilience (+1.40%) against a -2.80% 科创50 rout suggests genuine fundamental support from lithium price surge (+12.8% MoM) and record battery production (249GWh). When regime clears, battery/lithium chain stocks should be priority #1 for new entries.', 'type': 'signal', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'mechanism': "Sectors that hold green during a broad panic are showing relative strength backed by real demand. Battery production hitting records + lithium price rising creates fundamental support that shorts can't easily break."}
- {'text': '伟测科技 (688372) and 睿创微纳 (688002) both show ideal pullback-to-MA setups: dist_ma5 < 1%, 0 risk factors, strong fundamentals. These are the highest-conviction re-entry candidates when breadth improves. Low-risk pullback entries in strong sectors typically rebound fastest after a sell-off.', 'type': 'heuristic', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'mechanism': "Stocks that have already pulled back to MA5/MA10 support during a panic have already done their mean-reversion work. When the market stabilizes, they don't need to 'catch down' to their MAs before rallying — they're already at the launchpad."}
- {'text': "Multiple candidates in today's pool would fail Rule 2b even in a healthy regime: 联瑞新材 (dist_ma5=+8.5%), 帝尔激光 (+9.4%), 凯旺科技 (+9.4%), 民爆光电 (+19.0%). The MA-distance filter is doing real work keeping us from chasing extended names that would get crushed first in a sell-off. h027 confirmed.", 'type': 'rule', 'tags': ['entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h027', 'mechanism': "Extended stocks (dist_ma5 > 6%) have the most gravity to overcome. In a panic, they're the first profit-taking targets and suffer the largest drawdowns. The MA-distance filter protects against this systematically."}
