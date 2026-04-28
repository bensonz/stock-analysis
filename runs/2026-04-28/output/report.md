# 每日研究报告 2026-04-28

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4067.52 | -0.46% |
| 深证成指 | 14779.88 | -1.44% |
| 创业板指 | 3582.60 | -1.81% |
| 科创50 | 1480.37 | -1.86% |

涨跌比: 1426涨 / 3959跌 / 5488总

**热门板块**: 航海装备Ⅱ(+5.56%), 医疗服务(+4.61%), 林业Ⅱ(+3.95%), 煤炭开采(+2.87%), 工程机械(+2.82%)

**冷门板块**: 电视广播Ⅱ(-4.02%), 家电零部件Ⅱ(-3.68%), 航天装备Ⅱ(-3.54%), 数字媒体(-3.39%), 农业综合Ⅱ(-3.33%)

Breadth 0.36:1 bearish, 74涨停/57跌停, all major indices red (上证-0.46%, 深成指-1.44%, 创业板-1.81%) and entry_regime is explicit panic/hard block. Hot sectors (top 5): 航海装备Ⅱ +5.56%, 医疗服务 +4.61%, 林业Ⅱ +3.95%, 煤炭开采 +2.87%, 工程机械 +2.82%. Cold sectors (bottom 5): 电视广播Ⅱ -4.02%, 家电零部件Ⅱ -3.68%, 航天装备Ⅱ -3.54%, 数字媒体 -3.39%, 农业综合Ⅱ -3.33%. Position sector alignment: 0/0 positions in hot sectors. IV context is mostly low-to-neutral; broad-market proxies like 300ETF/500ETF remain very low IV, but that only affects sizing after the buy gate clears. Today it does not clear.

## 策略池扫描

扫描 **38** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **恩捷股份** (002812) (RPS 93.33%) — Entry regime hard block: breadth 0.36:1, 0/3 major indices green. Candidate itself is technically acceptable (RPS120 93.33, MA distances within limits, fresh Q1 profit growth), but Rule 1 forbids new longs in this tape.
2. **北化股份** (002246) (RPS 90.23%) — Entry regime hard block despite solid setup. RPS120 90.23 is in sweet spot, MA distances are controlled, and catalyst is fresh (profit growth +硝化棉景气/研报), but panic breadth overrides stock quality.
3. **华峰测控** (688200) (RPS 90.95%) — Good momentum name but no buy today. RPS120 90.95 and MA distances pass, yet the broad market fails the minimum long-entry gate; additionally semis are not shown in today's top sectors.
4. **科达制造** (600499) (RPS 89.74%) — Fresh earnings catalyst is positive, but Rule 1 blocks all new entries in a panic regime. Also stock-specific IV proxy is 300ETF IV Rank 8.8%, which would cut size by 50% even if tape improved.
5. **鄂尔多斯** (600295) (RPS 92.38%) — Coal-related sector is one of today's stronger groups and MA distances are fine, but RPS120 92.38 is only entry-eligible in the extended zone when regime allows. Current regime does not.
6. **英科医疗** (300677) (RPS 93.27%) — Medical services is a hot sector and MA distances are healthy, but market regime blocks new longs. Also latest company quick note says Q1 net profit was down 97.16%, which muddies the catalyst despite strong longer-term trend stats.
7. **望变电气** (603191) (RPS 88.91%) — Not enough momentum for a momentum-first entry. RPS120 88.91 is okay, but stock-specific IV proxy is 500ETF IV Rank 5.7% implying half size, and market regime is hard-blocked anyway.
8. **东材科技** (601208) (RPS 91.42%) — Fails anti-chase rule: dist_ma10_pct 8.6% > 8% and dist_ma20_pct 11.3% is close to the upper limit. Also broad market regime blocks entries.
9. **莱特光电** (688150) (RPS 93.31%) — Fails anti-chase rule badly: dist_ma10_pct 11.5% and dist_ma20_pct 21.7% are too extended. Even with strong sector narrative and reports, this is chasing.
10. **上海新阳** (300236) (RPS 88.95%) — Fails anti-chase rule: dist_ma5_pct 9.3% and dist_ma10_pct 11.7% are too far above support. No current setup quality edge justifies ignoring the extension.
11. **杰普特** (688025) (RPS 88.13%) — Fails anti-chase rule: dist_ma10_pct 11.1% and dist_ma20_pct 18.7% are overextended. Strong story, wrong entry.
12. **华懋科技** (603306) (RPS 93.43%) — Sector (汽车零部件) is not in today's hot-sector list and the setup fails anti-chase rule with dist_ma10_pct 14.5% and dist_ma20_pct 21.8%. Also stock IV proxy would force half size.
13. **芯源微** (688037) (RPS 86.43%) — Semiconductor trend is interesting, but today's tape is hostile and the stock is below the preferred momentum range versus top alternatives. No new long under panic regime.

## 今日研究结论

- 新开仓: 0只
- 跳过: 13只

### 新教训
- {'text': 'When breadth collapses below 1:1 and all three major indices are red, the correct V2 action is zero new positions even if several candidates have valid RPS and clean MA structure.', 'type': 'rule', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum entries need broad participation to follow through; in panic tapes, even strong stocks are more likely to get trapped by liquidity-driven selling.'}
- {'text': 'The anti-chase MA-distance rule is actively filtering many visually attractive names today, especially in electronics and equipment.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Extended distance from MA5/MA10/MA20 means weak nearby support and higher snapback risk, which is lethal when market breadth is poor.'}
- {'text': 'Today’s strength is concentrated in defensive or isolated pockets like medical services and coal rather than broad risk-on leadership, so sector heat is not broad enough to override regime weakness.', 'type': 'observation', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'Narrow leadership in a falling tape usually reflects rotation for safety or short-term themes, not the kind of broad impulse that sustains fresh momentum breakouts.'}
- {'text': 'Low IV is not a buy signal by itself; several沪市 candidates would have required half-size due to IV Rank below 15%, but the real blocker today is market regime, not volatility pricing.', 'type': 'heuristic', 'tags': ['position-sizing', 'timing', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h017', 'mechanism': 'IV only throttles sizing after the tape clears; it should not be used to justify forcing entries in a weak market.'}
