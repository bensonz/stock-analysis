# 每日研究报告 2026-04-03

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3878.72 | -1.03% |
| 深证成指 | 13360.11 | -0.94% |
| 创业板指 | 3153.25 | -0.61% |
| 科创50 | 1257.67 | -0.36% |

涨跌比: 718涨 / 4747跌 / 5487总

**热门板块**: 通信设备(+3.32%), 电子化学品Ⅱ(+1.62%), 自动化设备(+1.09%), 元件(+1.07%), 光学光电子(+0.60%)

**冷门板块**: 林业Ⅱ(-6.47%), 焦炭Ⅱ(-5.46%), 农业综合Ⅱ(-4.51%), 燃气Ⅱ(-3.66%), 种植业(-3.42%)

Market regime weak. Breadth 0.15:1 bearish, 37涨停/38跌停, heavy downside skew with 3142 stocks down more than 2%. All 3 major indices are red (上证-1.03%, 深成指-0.94%, 创业板指-0.61%), so the minimum long-entry gate clearly fails and f10=38 signals panic tape. Hot sectors (top 5): 通信设备(+3.32%), 电子化学品Ⅱ(+1.62%), 自动化设备(+1.09%), 元件(+1.07%), 光学光电子(+0.60%). Cold sectors (bottom 5): 林业Ⅱ(-6.47%), 焦炭Ⅱ(-5.46%), 农业综合Ⅱ(-4.51%), 燃气Ⅱ(-3.66%), 种植业(-3.42%). Position sector alignment: 0/0 positions in hot sectors. Research check confirms pockets of strength are catalyst-backed: 国电南自年报显示2025年营收96.44亿元、归母净利润同比+40.95%、电网自动化订货53.85亿元；通信设备方向有1.6T光模块/光通信升级叙事支撑；烽火通信有耐辐照光纤技术突破消息。但 these are observational only today, not actionable buys. IV context is low-to-neutral overall (avg IV rank 18.1%); this would cap sizing in calmer tapes, but today regime weakness overrides IV and keeps new_positions empty.

## 策略池扫描

扫描 **21** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) (RPS 91.15%) — Entry regime weak and fails hard gate; breadth only 0.15:1, 0/3 major indices green, f10=38 panic threshold breached. Also MA chase rule fails: dist_ma5_pct 7.0% and dist_ma10_pct 8.3% exceed limits.
2. **烽火通信** (600498) (RPS 95.3%) — Sector is hot and catalyst is real, but no new long allowed in current weak regime. In addition, rps120 95.3 is above allowed chase ceiling without pullback.
3. **舒华体育** (605299) (RPS 94.93%) — Not in a provided top sector and MA extension is extreme: dist_ma5_pct 16.0%, dist_ma10_pct 30.7%, dist_ma20_pct 47.9%. No-chasing rule blocks entry even before regime filter.
4. **杰普特** (688025) (RPS 86.69%) — Sector rank is favorable and MA distances are acceptable, but market regime blocks all new positions; breadth is panic-like and 3 major indices are all red.
5. **芯源微** (688037) (RPS 85.85%) — Weak regime blocks entries. Stock also lacks near-term momentum leadership versus best names: rps120 85.85 but recent event flow shows adjustment and 20-day relative performance weakness.
6. **华懋科技** (603306) (RPS 92.83%) — Sector not in provided top 30% and current market tape does not permit exploratory buys. Catalyst is M&A/resumption news, but not enough to override sector-first and regime rules.
7. **东材科技** (601208) (RPS 90.86%) — Sector not in provided top 30%; PET铜箔-related move is too narrow for a weak tape. Regime filter also blocks all fresh entries.
8. **华锡有色** (600301) (RPS 93.29%) — Sector not in provided top 30%, and stock sits below MA20 with dist_ma20_pct -13.1%, showing pullback rather than confirmed breakout leadership. Regime filter blocks new positions anyway.
9. **明阳智能** (601615) (RPS 90.8%) — Sector not in provided hot list and recent tape is weak; 20-day relative performance weakness plus price below MA10/MA20 indicates no momentum confirmation.
10. **华鲁恒升** (600426) (RPS 88.62%) — Sector not in provided top 30% and catalyst is more medium-term pricing/earnings repair than immediate momentum ignition. With weak breadth, no need to force chemical names.
11. **利柏特** (605167) (RPS 93.49%) — Sector not in provided hot list; contract news is positive but stock has weak recent 10-day relative strength note and market regime blocks all fresh risk.
12. **三祥新材** (603663) (RPS 91.77%) — Sector not in provided top 30%, and price is below MA20 with dist_ma20_pct -12.6%, so timing is not breakout-ready. Weak regime means skip.

## 今日研究结论

- 新开仓: 0只
- 跳过: 12只

### 新教训
- {'text': 'When breadth collapses below 1:1 and all three major indices are red, even the #1 sector should usually be treated as relative-strength observation rather than an entry signal.', 'type': 'rule', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'In panic tapes, cross-sector selling pressure dominates single-stock catalysts; isolated leaders can still work later, but initial entries have poor payoff asymmetry.'}
- {'text': 'MA-distance checks remain critical on strong event names: 国电南自 had valid earnings/news momentum, but dist_ma5_pct>6% and dist_ma10_pct>8% still mark it as a chase.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Fresh catalysts improve direction but do not eliminate mean-reversion risk after a short-term vertical move away from support.'}
- {'text': 'Today’s market shows a useful distinction between sector leadership and market permission: 通信设备/自动化设备 are leadership groups, but the tape does not grant buying permission.', 'type': 'heuristic', 'tags': ['sector', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'Sector ranking helps build the next watch universe, while breadth and index confirmation decide whether capital should actually be deployed.'}
