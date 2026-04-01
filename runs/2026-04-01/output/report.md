# 每日研究报告 2026-04-01

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3944.80 | +1.36% |
| 深证成指 | 13640.05 | +1.20% |
| 创业板指 | 3222.59 | +1.18% |
| 科创50 | 1293.48 | +2.96% |

涨跌比: 4392涨 / 970跌 / 5488总

**热门板块**: 游戏Ⅱ(+4.89%), 化学制药(+4.57%), 医疗服务(+4.13%), 酒店餐饮(+4.09%), 生物制品(+3.90%)

**冷门板块**: 林业Ⅱ(-4.99%), 航天装备Ⅱ(-2.29%), 轨交设备Ⅱ(-1.12%), 乘用车(-0.85%), 风电设备(-0.79%)

Breadth 4.53:1 bullish, 52涨停/8跌停, all 3 major indices green and 科创50 +2.96%, so regime is strong enough for fresh risk. Hot sectors by provided data are 游戏Ⅱ(+4.89%), 化学制药(+4.57%), 医疗服务(+4.13%), 酒店餐饮(+4.09%), 生物制品(+3.90%); cold sectors are 林业Ⅱ(-4.99%), 航天装备Ⅱ(-2.29%), 轨交设备Ⅱ(-1.12%), 乘用车(-0.85%), 风电设备(-0.79%). Position sector alignment: 0/2 positions in hot sectors. IV context is mildly complacent but not extreme: stock proxies and broad market IV ranks mostly 16%-22%, which allows normal sizing but argues against chasing extended names.

## 策略池扫描

扫描 **21** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) (RPS 91.15%) — Sector fit is decent, but MA chase rule fails: dist_ma5_pct 7.0% and dist_ma10_pct 8.3%, both above allowed limits. Wait for pullback.
2. **舒华体育** (605299) (RPS 94.93%) — Fails no-chasing rule badly: dist_ma5_pct 16.0%, dist_ma10_pct 30.7%, dist_ma20_pct 47.9%. Even with strong momentum, this is extended.
3. **烽火通信** (600498) (RPS 95.3%) — RPS120 95.3 is above the allowed buy zone (>95 treated as chasing), and only strategy_pool data is available with no enriched MA-distance confirmation. Skip rather than chase.
4. **华通线缆** (605196) (RPS 95.36%) — RPS120 95.36 is above the allowed buy zone, and stock-level data shows recent 10-day relative weakness despite longer-term strength. Skip the extended setup.
5. **海星股份** (603115) (RPS 97.08%) — RPS120 97.08 is too extended under Rule 2. No current enriched MA-distance data provided here to justify exception, so skip.
6. **华懋科技** (603306) (RPS 92.83%) — Sector is auto weak from provided market sectors: 乘用车 is bottom-5 today, so auto parts is not an entry sector even though stock is near MA support.
7. **明阳智能** (601615) (RPS 90.8%) — Sector is auto weak from provided market sectors: 风电设备 is bottom-5 today. Sector gravity overrides stock setup.
8. **华鲁恒升** (600426) (RPS 88.62%) — RPS120 88.62 is acceptable and MA distances are fine, but sector is not in the provided top 30% leadership set and catalyst freshness is not strong enough to force an entry.
9. **东材科技** (601208) (RPS 90.86%) — Setup is technically acceptable, but its sector is not in the provided top leadership list; with many hotter areas in the tape, this is skip rather than dilute focus.
10. **利柏特** (605167) (RPS 93.49%) — Sector not in provided top leadership list, and fundamentals are mixed with revenue_yoy -23.44% and net_profit_yoy -11.15%. No need to reach down the quality curve in a strong tape.
11. **华锡有色** (600301) (RPS 93.29%) — Recent 10-day relative weakness is severe in the input, and dist_ma20_pct is -13.1%, showing loss of near-term trend. Not a clean momentum entry now.
12. **三祥新材** (603663) (RPS 91.77%) — dist_ma20_pct is -12.6%, beyond the MA20 tolerance band, indicating broken short-term structure rather than a fresh momentum entry.

## 今日研究结论

- 新开仓: 0只
- 跳过: 12只

### 新教训
- {'text': "In strong breadth tapes, the bigger failure mode is still chasing extension, not lack of candidates; today's best-looking breakouts were filtered mainly by MA-distance, not by market regime.", 'type': 'rule', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Broad market strength can support new longs, but if price is already too far above MA5/MA10/MA20, reward-to-risk deteriorates and mean reversion risk dominates.'}
- {'text': 'Bottom-list sectors should be treated as hard no-buy zones even when individual names still carry acceptable RPS readings.', 'type': 'heuristic', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Relative strength at the stock level decays quickly when sector flow turns against it; sector gravity tends to overwhelm single-name quality.'}
- {'text': 'Low-IV conditions today did not require throttling size, but they do reinforce the need to avoid late entries because complacent volatility leaves less buffer for sloppy timing.', 'type': 'signal', 'tags': ['timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'When IV rank is in the normal-low zone, positions can be taken normally, but upside from vol expansion is smaller, so entry precision matters more.'}
