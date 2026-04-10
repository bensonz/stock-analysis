# 每日研究报告 2026-04-10

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3993.73 | +0.69% |
| 深证成指 | 14359.82 | +2.60% |
| 创业板指 | 3465.05 | +4.27% |
| 科创50 | 1369.47 | +1.90% |

涨跌比: 4200涨 / 1171跌 / 5495总

**热门板块**: 电池(+5.86%), 元件(+4.09%), 玻璃玻纤(+4.08%), 证券Ⅱ(+3.97%), 其他电源设备Ⅱ(+3.49%)

**冷门板块**: 林业Ⅱ(-2.48%), 贵金属(-1.83%), 航运港口(-1.38%), 养殖业(-1.04%), 文娱用品(-1.00%)

Breadth 3.59:1 bullish, 80涨停/11跌停, 3/3 major indices green, led by 创业板指 +4.27% and 深证成指 +2.60%. Hot sectors are 电池(+5.86%), 元件(+4.09%), 玻璃玻纤(+4.08%), 证券Ⅱ(+3.97%), 其他电源设备Ⅱ(+3.49%), while 贵金属 and航运港口 are lagging. Web checks support a battery/electronics-led risk-on tape, but stock-specific research quality is poor today because strategy_pool and enriched_candidates are empty. IV context remains extremely complacent: overall avg IV rank 9.16%, with held-position proxies also below 15%, so any new entry would require half sizing and only on fully qualified setups. Since there are no compliant candidates, keep cash and manage current winners.

## 策略池扫描

扫描 **0** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) — No current candidate packet in enriched_candidates, so MA-distance and RPS rules cannot be verified. Even though current_price 14.95 is listed in missed_opportunity_prices, that list is not a valid entry dataset under Rule 2b.
2. **烽火通信** (600498) — Sector tape may be supportive, but there is no enriched_candidates record, so catalyst freshness, MA distance and proper entry validation are missing. Current_price 52.91 exists, but no compliant setup data.
3. **海星股份** (603115) — Current_price 43.0 is available only in missed_opportunity_prices; there is no enriched_candidates data for RPS, MA distance or sector rank. Skip rather than force an under-researched entry.
4. **华通线缆** (605196) — No enriched candidate data, so Rule 2 and Rule 2b cannot be checked. Current_price 47.32 alone is insufficient for a momentum entry decision.
5. **华锡有色** (600301) — Current_price 50.43 is available, but sector 贵金属 is in today's bottom 5 at -1.83%, so cold-sector gravity blocks any new long regardless of stock quality.

## 今日研究结论

- 新开仓: 0只
- 跳过: 5只

### 新教训
- {'text': 'Strong breadth does not override missing setup data; with enriched_candidates empty, the correct momentum action is still to keep cash despite a favorable tape.', 'type': 'rule', 'tags': ['entry-filter', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum entries need both market tailwind and stock-level confirmation. Without RPS/MA-distance/setup data, broad strength can turn into blind chasing.'}
- {'text': "Low IV regime is a sizing throttle, not a direction veto: today's market is strong enough for longs, but sub-15% IV Rank argues for patience and half-sized deployment only when a fully qualified candidate appears.", 'type': 'heuristic', 'tags': ['timing', 'position-sizing', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'Very low implied volatility reflects complacency; upside can continue, but the reward-to-risk on fresh breakout buying is worse if entries are not precise.'}
- {'text': "Volume below MAVOL30 on open positions is not an automatic sell when price is still advancing and stops are intact, but it is a clear 'no add' signal.", 'type': 'signal', 'tags': ['exit-rule', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'Sub-average volume weakens confirmation. Price can still trend higher, but the probability of stall increases, so existing positions can be held while pyramiding should be avoided.'}
