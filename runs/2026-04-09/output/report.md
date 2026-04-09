# 每日研究报告 2026-04-09

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3966.17 | -0.72% |
| 深证成指 | 13996.27 | -0.33% |
| 创业板指 | 3323.30 | -0.73% |
| 科创50 | 1343.95 | -0.65% |

涨跌比: 1140涨 / 4299跌 / 5491总

**热门板块**: 油气开采Ⅱ(+2.41%), 元件(+1.60%), 环保设备Ⅱ(+1.41%), 通信设备(+1.39%), 油服工程(+1.23%)

**冷门板块**: 个护用品(-3.44%), 厨卫电器(-3.34%), 游戏Ⅱ(-3.32%), 林业Ⅱ(-3.25%), 数字媒体(-3.10%)

Breadth 0.27:1 bearish, 64涨停/14跌停, all 3 major indices red, so the minimum long-entry gate fails decisively and new_positions stay empty. Today's relative strength was concentrated in 油气开采Ⅱ(+2.41%), 元件(+1.6%), 环保设备Ⅱ(+1.41%), 通信设备(+1.39%), and 油服工程(+1.23%), while 个护用品(-3.44%), 厨卫电器(-3.34%), 游戏Ⅱ(-3.32%), 林业Ⅱ(-3.25%), and 数字媒体(-3.1%) lagged. Position sector alignment: 1/2 positions in today's hot sectors. IV context is complacent to extremely low (overall avg IV rank 9.11%; stock proxies 8.3% and 7.7%), which argues for smaller sizing in general and no fresh risk in today's weak tape.

## 策略池扫描

扫描 **0** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) — No entry today because market buy gate failed: breadth only 0.27:1 and 0/3 major indices green. Also no enriched candidate MA-distance/RPS package provided for validation.
2. **烽火通信** (600498) — Communication equipment is relatively strong, but weak regime overrides stock setup. No current candidate MA-distance/VCP data supplied, so no compliant new entry.
3. **海星股份** (603115) — No new positions in a weak tape. Candidate lacks enriched MA-distance and catalyst validation package in today's input.
4. **华通线缆** (605196) — Even if theme may be interesting, buy gate is closed today and no enriched candidate metrics were provided for a rules-compliant momentum entry.
5. **华锡有色** (600301) — Commodity strength is not enough to override a failed market regime gate. No enriched candidate MA-distance/RPS detail in today's input.

## 今日研究结论

- 新开仓: 0只
- 跳过: 5只

### 新教训
- {'text': 'When breadth collapses to 0.27:1 with 0/3 major indices green, the correct momentum action is to freeze new buying even if a few sectors still print green.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'In weak tapes, isolated sector strength usually cannot overcome market-wide supply; preserving cash prevents forcing low-odds entries.'}
- {'text': 'Ultra-low IV did not create a bullish entry edge today; instead it coincided with a complacent tape that rolled over broadly, reinforcing the need to throttle or avoid new risk.', 'type': 'signal', 'tags': ['timing', 'position-sizing', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Low IV means the market is priced for calm; when breadth breaks, volatility can expand suddenly and punish fresh longs.'}
- {'text': 'Positions can be held through a weak day if they remain above stop and within early holding windows, but sub-1.5% MAVOL30 participation is a clear warning against adding.', 'type': 'heuristic', 'tags': ['exit-rule', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Low volume means weak sponsorship; price can still hold, but probability of sustained momentum is lower without confirmation.'}
