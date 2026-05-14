# 每日研究报告 2026-05-14

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4177.92 | -1.52% |
| 深证成指 | 15745.74 | -2.14% |
| 创业板指 | 3951.14 | -2.16% |
| 科创50 | 1725.09 | -2.55% |

涨跌比: 1047涨 / 4387跌 / 5495总

**热门板块**: 饲料(+1.55%), 养殖业(+1.51%), 白色家电(+1.04%), 国有大型银行Ⅱ(+1.03%), 航运港口(+0.54%)

**冷门板块**: 林业Ⅱ(-8.63%), 航天装备Ⅱ(-8.18%), 小金属(-4.95%), 广告营销(-4.72%), 数字媒体(-4.39%)

Breadth 0.24:1 bearish, 82涨停/48跌停, all 3 major indices red: 上证-1.52%, 深成指-2.14%, 创业板指-2.16%. Entry regime is explicitly panic and hard-blocked, so new_positions stays empty. Leadership is defensive: 饲料(+1.55%), 养殖业(+1.51%), 白电(+1.04%), 银行(+1.03%), while 林业Ⅱ(-8.63%), 航天装备Ⅱ(-8.18%), 小金属(-4.95%) are among the worst. Stock-specific IV proxies are mostly normal-to-elevated rather than extreme, but IV is irrelevant today because breadth/indices already veto fresh longs.

## 策略池扫描

扫描 **55** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **恩捷股份** (002812) (RPS 93.96%) — No new longs: entry regime hard-blocked (breadth 0.24:1, 0/3 major indices green, 48跌停). Even ignoring regime, battery sector is not in provided top sectors and the catalyst is fresh but tape is too weak.
2. **科达制造** (600499) (RPS 90.79%) — Setup is technically acceptable on MA distance and RPS, but market regime blocks entries. Also sector is not confirmed in today's top 30% from provided sector table.
3. **咸亨国际** (605056) (RPS 93.35%) — No entry: panic regime blocks all new longs. Stock is also below MA10 (dist_ma10_pct -10.0%), showing weak short-term tape rather than strength-on-strength.
4. **万向钱潮** (000559) (RPS 89.15%) — Sector gravity issue: 汽车零部件 is not in today's top sectors, and the stock's RPS120 89.15 is acceptable but not enough to override weak market conditions.
5. **华锡有色** (600301) (RPS 92.84%) — Reject on sector first: 小金属 is explicitly in today's bottom 5 sectors (-4.95%). Cold sector = no entry regardless of individual setup.
6. **江丰电子** (300666) (RPS 94.49%) — No chasing: dist_ma10_pct 13.6% and dist_ma20_pct 22.4% both violate MA-distance limits. Also market regime is hard-blocked.
7. **华峰测控** (688200) (RPS 90.47%) — Overextended: dist_ma5_pct 10.7%, dist_ma10_pct 20.8%, dist_ma20_pct 32.8% all violate anti-chase rule. Panic regime also blocks entries.
8. **中船特气** (688146) (RPS 85.42%) — Fresh catalyst exists, but dist_ma10_pct 14.9% and dist_ma20_pct 43.5% fail anti-chase rule. Company also disclosed uncertainty around six-fluoride tungsten order impact.
9. **上海新阳** (300236) (RPS 87.47%) — Almost qualifies on momentum, but dist_ma10_pct 8.8% and dist_ma20_pct 12.5% are above limits. Market regime also blocks any new position.
10. **伟测科技** (688372) (RPS 93.8%) — No chase: dist_ma5_pct 6.4%, dist_ma10_pct 11.1%, dist_ma20_pct 18.2% all exceed thresholds. Panic tape makes this an easy skip.
11. **欧陆通** (300870) (RPS 89.09%) — Overextended trend stock: dist_ma10_pct 28.3% and dist_ma20_pct 44.4% far above support. Not buyable here, especially in a hard-block regime.
12. **共达电声** (002655) (RPS 94.55%) — Despite strong long-term momentum and shareholder增持 catalyst, dist_ma10_pct 25.2% and dist_ma20_pct 56.2% are extreme. Anti-chase rule says wait.
13. **鼎通科技** (688668) (RPS 92.52%) — Communication equipment theme remains strong fundamentally, but dist_ma10_pct 25.0% and dist_ma20_pct 39.8% fail anti-chase rule. No entry in this tape.
14. **长芯博创** (300548) (RPS 93.71%) — Good growth catalyst, but dist_ma10_pct 26.0% and dist_ma20_pct 48.2% are too extended. Cannot chase into a market-wide selloff.

## 今日研究结论

- 新开仓: 0只
- 跳过: 14只

### 新教训
- {'text': 'When breadth collapses to 0.24:1 with all three major indices red, the correct momentum action is full pass even if several stocks still show high RPS.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum entries need market sponsorship; isolated strength usually fails when index and breadth pressure force de-risking across the tape.'}
- {'text': "Today's candidate pool again shows the anti-chase MA filter doing real work: many popular names have acceptable RPS but are 10-40% above MA10/MA20 and therefore unbuyable.", 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'High-RPS names often become crowded late in a swing; entering far above moving-average support increases mean-reversion risk exactly when market conditions weaken.'}
- {'text': 'Defensive leadership from 饲料、养殖业、白电、银行 while major indices fall suggests capital is hiding rather than expanding risk appetite.', 'type': 'observation', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'When defensive and cash-flow sectors outperform in a down tape, market participants are rotating toward resilience instead of chasing offensive growth.'}
- {'text': 'Cold-sector override remains essential: 华锡有色 had acceptable RPS and support proximity, but 小金属 being bottom-5 sector is enough to reject the trade.', 'type': 'heuristic', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Sector momentum usually dominates single-stock setups; even decent charts lose edge when money is exiting the whole group.'}
