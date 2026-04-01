# 每日研究报告 2026-04-01

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3948.55 | +1.46% |
| 深证成指 | 13706.52 | +1.70% |
| 创业板指 | 3247.52 | +1.96% |
| 科创50 | 1298.20 | +3.33% |

涨跌比: 4495涨 / 887跌 / 5485总

**热门板块**: 游戏Ⅱ(+6.00%), 酒店餐饮(+5.96%), 医疗服务(+5.39%), 化学制药(+4.95%), 生物制品(+4.55%)

**冷门板块**: 林业Ⅱ(-5.31%), 油气开采Ⅱ(-2.93%), 航天装备Ⅱ(-1.67%), 轨交设备Ⅱ(-1.09%), 光伏设备(-0.90%)

Breadth 5.1:1 bullish, 66涨停/15跌停, broad-based rally with all 3 major indices green and 科创50 +3.33%. Hot sectors (top 5): 游戏Ⅱ +6.0%, 酒店餐饮 +5.96%, 医疗服务 +5.39%, 化学制药 +4.95%, 生物制品 +4.55%. Cold sectors (bottom 5): 林业Ⅱ -5.31%, 油气开采Ⅱ -2.93%, 航天装备Ⅱ -1.67%, 轨交设备Ⅱ -1.09%, 光伏设备 -0.9%. Position sector alignment: 0/2 positions in hot sectors. IV context is mildly complacent overall (avg IV rank 15.5%); stock-specific IV is normal for科创 names but low for many main-board names, so any new non-KeChuang entries should be half-sized. Despite strong regime, today's candidate list lacks clean names inside the provided top leadership sectors, so no new positions.

## 策略池扫描

扫描 **21** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) (RPS 91.15%) — Sector is not in provided top hot-sector list, and MA chase filter fails: dist_ma5_pct 7.0% > 6% and dist_ma10_pct 8.3% > 8%.
2. **舒华体育** (605299) (RPS 94.93%) — RPS120 94.93 is allowed zone, but MA chase filter badly fails: dist_ma5_pct 16.0%, dist_ma10_pct 30.7%, dist_ma20_pct 47.9%. Also stock-specific IV proxy says half sizing, but extension already disqualifies entry.
3. **烽火通信** (600498) (RPS 95.3%) — RPS120 95.30 is above the allowed upper bound; skip and wait for pullback. No enriched MA-distance data provided, so no fresh entry chase.
4. **华通线缆** (605196) (RPS 95.36%) — RPS120 95.36 is above the allowed upper bound; skip rather than chase. Sector also is not in provided top hot-sector list.
5. **海星股份** (603115) (RPS 97.08%) — RPS120 97.08 is too extended above the buy zone. Sector is also not in provided top hot-sector list.
6. **华懋科技** (603306) (RPS 92.83%) — Sector (汽车零部件) is not in provided top hot-sector list. Even though MA distances are acceptable, sector-first rule blocks the entry.
7. **明阳智能** (601615) (RPS 90.8%) — Sector (风电设备) is not in provided top hot-sector list, and MA structure is weak with price below MA10 and MA20; no sector tailwind for a momentum entry.
8. **华鲁恒升** (600426) (RPS 88.62%) — Sector (基础化工/农化制品) is not in provided top hot-sector list; this is not where today's leadership is concentrated.
9. **东材科技** (601208) (RPS 90.86%) — Sector (基础化工/塑料) is not in provided top hot-sector list. Setup is technically acceptable, but sector-first rule keeps it as skip.
10. **利柏特** (605167) (RPS 93.49%) — Sector (建筑装饰/专业工程) is not in provided top hot-sector list. Fresh contract news exists, but sector gravity is missing and recent 10-day relative weakness is noted in the input.
11. **华锡有色** (600301) (RPS 93.29%) — Sector (有色金属/小金属) is not in provided top hot-sector list, and price is 13.1% below MA20 in enriched data, showing setup damage rather than clean momentum continuation.
12. **三祥新材** (603663) (RPS 91.77%) — Sector (基础化工/化学原料) is not in provided top hot-sector list, and enriched data shows dist_ma20_pct -12.6%, indicating a damaged setup rather than a clean breakout entry.

## 今日研究结论

- 新开仓: 0只
- 跳过: 12只

### 新教训
- {'text': 'Strong market breadth alone is not enough to justify fresh longs when candidate sectors are not the actual leadership groups in the provided sector table.', 'type': 'heuristic', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Broad index strength can lift many stocks temporarily, but momentum persistence usually concentrates in a smaller set of leading sectors; forcing entries outside those groups reduces follow-through odds.'}
- {'text': 'The MA-distance anti-chase rule is doing real work: several visually strong names fail because they are too far above short-term support.', 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'When price gets too stretched above MA5/MA10/MA20, upside becomes dependent on continued euphoria instead of support-based demand, raising mean-reversion risk.'}
- {'text': 'Stop-proximity warnings deserve special attention even on bullish tape; a stock can be in a rising market and still be the wrong stock.', 'type': 'signal', 'tags': ['exit-rule', 'position-management'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Relative weakness inside a strong tape often identifies laggards where capital is rotating away, so tight risk control matters more than market-level optimism.'}
