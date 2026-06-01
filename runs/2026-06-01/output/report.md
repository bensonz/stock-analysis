# 每日研究报告 2026-06-01

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4057.74 | -0.27% |
| 深证成指 | 15340.36 | -1.51% |
| 创业板指 | 3950.94 | -2.15% |
| 科创50 | 1663.69 | -5.00% |

涨跌比: 3776涨 / 1682跌 / 5509总

**热门板块**: 煤炭开采(+5.60%), 数字媒体(+5.34%), 广告营销(+4.98%), 农产品加工(+4.26%), 焦炭Ⅱ(+3.78%)

**冷门板块**: 玻璃玻纤(-7.47%), 半导体(-5.50%), 元件(-5.41%), 通信设备(-3.73%), 照明设备Ⅱ(-2.74%)

Defensive rotation day: 科创50暴跌-5%领跌，半导体/元件/通信设备全线重挫，AI泡沫退潮。煤炭板块+5.6%逆势暴涨（印尼出口政策催化），焦煤期货+7.2%。三大指数全绿但个股涨多跌少（3776↑/1682↓），典型的'指数跌、个股涨'的板块轮动格局。买入关卡未通过（0/3指数收红），暂停新开仓。IV分化：300ETF极低(14.6%)，创业板偏高(53.5%)，科创50中性(40.2%)。5月制造业PMI 50.0%触及荣枯线。

## 策略池扫描

扫描 **57** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **山东赫达** (002810) (RPS 94.4%) — BUY GATE FAILED: 0/3 major indices green. Best technical setup in pool (RPS120=94.40, VCP=SETUP, all MA distances within tolerance, Q4 profit +127%). Will monitor for re-entry when buy gate clears.
2. **石大胜华** (603026) (RPS 94.87%) — BUY GATE FAILED + 电池板块今日承压（石大胜华跌超8%）。RPS120=94.87 in sweet spot, MA distances all negative (pulled back to support), PE=63.9 but growth justifies. 电解液溶剂全球龙头，港股递表中。
3. **大金重工** (002487) (RPS 89.53%) — BUY GATE FAILED + RPS120=89.53 below 90% preferred range. Strong fundamentals (~61.7亿累计造船订单, 0 risk in enriched data), but RPS momentum not at ideal level + buy gate closed.
4. **湖南裕能** (301358) (RPS 92.05%) — BUY GATE FAILED + 大股东减持进行中。RPS120=92.05, MA distances all negative (near MA20 support), Q4净利+1338%, H股上市筹划。减持压力是额外顾虑。
5. **华峰测控** (688200) (RPS 94.01%) — 半导体 sector in bottom 5 (-5.5%). RPS120=94.01 but sector gravity dominates. 大股东询价转让388.98元，市场解读为减持信号。Rule 1 blocks this regardless of buy gate.
6. **伟测科技** (688372) (RPS 93.41%) — 半导体 sector in bottom 5 (-5.5%). Today 解禁32.37万股. RPS120=93.41, MA distances OK but sector + event headwinds are too strong.
7. **芯碁微装** (688630) (RPS 94.52%) — dist_ma5_pct=11.1% >6% — Rule 2b NON-NEGOTIABLE violation. RPS120=94.52 in sweet spot and fundamentals are excellent (score_company 9.3, 0 risks), but buying 11% above MA5 is chasing. Wait for pullback to MA10 (~292) or MA20 (~249).
8. **联瑞新材** (688300) (RPS 94.5%) — dist_ma5_pct=21.2% — extreme extension. RPS120=94.50 but stock is 62.7% above MA20. Highest mean-reversion risk in the pool. Monitor for pullback below MA5.
9. **国瓷材料** (300285) (RPS 93.33%) — dist_ma5_pct=6.8% >6%, dist_ma10=18.1% >8%, dist_ma20=36.4% >12% — triple violation of Rule 2b. Strong fundamentals (MLCC材料龙头) but massively overextended.
10. **兴森科技** (002436) (RPS 88.07%) — dist_ma10=9.5% >8% — Rule 2b violation. Also 元件 sector in bottom 5 (-5.41%). Double block.
11. **华锡有色** (600301) (RPS 91.19%) — dist_ma5=6.8% >6% — Rule 2b violation. 小金属 sector trending up but stock is chasing. No current price data beyond enriched snapshot.

## 今日研究结论

- 新开仓: 0只
- 跳过: 11只

### 新教训
- {'text': "Buy gate index criterion (≥2 of 3 major indices green) correctly identified a 'rotation not rally' tape today: breadth 2.24:1 bullish but all three indices red, signaling institutional de-risking from large-cap tech into small/mid cyclicals. The index criterion prevents fighting capital flow direction.", 'type': 'signal', 'tags': ['entry-filter', 'market-regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When breadth is positive but major indices are all red, the divergence signals that large-cap/tech names are being sold while mid/small caps catch rotation bids. Opening new longs into this means betting against the direction of institutional capital flow, which dominates short-term returns.'}
- {'text': "Coal sector (+5.6%) driven by Indonesia's single-window export policy (structural, 6-month transition to full implementation). This is the strongest non-tech sector catalyst in weeks. But our strategy pool has zero coal-sector candidates — a pipeline gap.", 'type': 'observation', 'tags': ['sector', 'catalyst'], 'evidence_type': 'supporting', 'mechanism': "Indonesia's policy forces all coal/palm oil/ferroalloy exports through a single state-owned exporter, creating supply-chain friction that could push global coal prices up 5-25%. This is a multi-month catalyst, not a one-day spike."}
- {'text': 'MA-distance discipline (Rule 2b) eliminated 6 otherwise-strong candidates today: 芯碁微装, 联瑞新材, 国瓷材料, 卓易信息, 华锡有色, 兴森科技. These stocks have excellent fundamentals/RPS but are too far above short-term support. This rule is preventing chasing entries that V1 would have made.', 'type': 'heuristic', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Stocks that are 6%+ above MA5 have already captured most short-term returns and face mean-reversion risk from profit-taking. The marginal return of the next 1-2% upside is not worth the 5-10% pullback risk.'}
- {'text': "VCP data coverage is extremely sparse: only 1 of 31 enriched candidates (山东赫达) has VCP quality data. This means we're missing the strongest backtested timing signal (+7.7% avg 10d for PREMIUM) on 97% of the candidate pool.", 'type': 'observation', 'tags': ['data-quality'], 'evidence_type': 'supporting', 'mechanism': "The VCP scanner appears to only flag stocks that pass specific Minervini-style contraction criteria. Many high-RPS stocks with strong fundamentals don't meet these narrow criteria, limiting the signal's coverage. This is a pipeline limitation, not a flaw in the VCP concept."}
