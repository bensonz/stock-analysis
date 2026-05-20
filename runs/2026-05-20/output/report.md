# 每日研究报告 2026-05-20

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4150.98 | -0.45% |
| 深证成指 | 15512.08 | -0.37% |
| 创业板指 | 3910.52 | +0.05% |
| 科创50 | 1811.43 | +2.04% |

涨跌比: 1300涨 / 4151跌 / 5500总

**热门板块**: 半导体(+2.76%), 油气开采Ⅱ(+2.58%), 非金属材料Ⅱ(+2.27%), 光伏设备(+2.23%), 非白酒(+1.55%)

**冷门板块**: 文娱用品(-3.79%), 通信服务(-3.47%), 电力(-3.43%), 广告营销(-3.38%), 数字媒体(-2.89%)

Breadth 0.31:1 bearish, 50涨停/29跌停, only 创业板指 green while 上证指数 and 深证成指 are red; this fails the minimum long-entry gate and matches the hard-blocked panic regime. Hot sectors are 半导体(+2.76%), 油气开采Ⅱ(+2.58%), 非金属材料Ⅱ(+2.27%), 光伏设备(+2.23%), 非白酒(+1.55%); cold sectors are 文娱用品(-3.79%), 通信服务(-3.47%), 电力(-3.43%), 广告营销(-3.38%), 数字媒体(-2.89%). Position sector alignment is 0/1 in hot sectors. IV context is mostly low-to-neutral overall, but regime—not IV—is the binding constraint today.

## 策略池扫描

扫描 **55** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **江丰电子** (300666) (RPS 94.65%) — Sector is hot and catalyst is real, but dist_ma5_pct 12.4%, dist_ma10_pct 24.7%, dist_ma20_pct 37.9% all violate anti-chase rule; also entry regime blocks new longs.
2. **伟测科技** (688372) (RPS 93.64%) — 半导体 sector is strong, but dist_ma5_pct 7.1%, dist_ma10_pct 11.7%, dist_ma20_pct 20.7% all exceed buy limits; entry regime also blocks new positions.
3. **德科立** (688205) (RPS 93.56%) — Communication equipment is not in today’s top sector list and dist_ma20_pct 16.0% exceeds the 12% anti-chase limit; no buy in blocked regime.
4. **华锡有色** (600301) (RPS 92.34%) — MA distances are acceptable, but 有色金属 is not in today’s top sector list and broad market regime is panic, so no new entry.
5. **咸亨国际** (605056) (RPS 92.48%) — Setup is near support, but sector is not in today’s top sector list; stock-specific IV proxy also signals half sizing if bought, and regime blocks all fresh longs.
6. **睿创微纳** (688002) (RPS 89.36%) — Sector not in today’s top 5 and dist_ma20_pct 11.3% is close to the upper extension limit while regime is hard-blocked for new longs.
7. **明阳电路** (300739) (RPS 91.43%) — MA distances are within range and RPS is valid, but 元件 sector is not in today’s top sector list; weak breadth means skip rather than force a small buy.
8. **中船特气** (688146) (RPS 91.53%) — 半导体 sector is hot, but dist_ma5_pct 54.8%, dist_ma10_pct 83.7%, dist_ma20_pct 135.2% are extreme chase violations.
9. **芯碁微装** (688630) (RPS 90.44%) — Strong fundamentals, but dist_ma5_pct 9.1%, dist_ma10_pct 20.0%, dist_ma20_pct 39.1% fail anti-chase rule; no buy.
10. **申菱环境** (301018) (RPS 89.26%) — 通用设备 is not in today’s top sector list and dist_ma5_pct 16.3%, dist_ma10_pct 32.0%, dist_ma20_pct 44.5% are too extended.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': 'When breadth is 0.31:1 and only 1 of 3 major indices is green, the correct momentum action is to hold cash even if a few semiconductor names are working.', 'type': 'rule', 'tags': ['sector', 'timing', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Weak market internals overwhelm isolated stock strength; forcing entries in a panic tape reduces follow-through odds.'}
- {'text': 'The MA-distance anti-chase filter is doing heavy lifting again today: many of the strongest candidates are in hot sectors but still unbuyable because they are too far above MA5/MA10/MA20.', 'type': 'signal', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Momentum works best when buying strength near support, not after vertical extensions that raise mean-reversion risk.'}
- {'text': 'A fresh position can stay HOLD even after a -4.38% day if it remains above the hard stop, but weak volume should immediately downgrade any idea of adding capital.', 'type': 'heuristic', 'tags': ['exit-rule', 'position-sizing', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'Price has not invalidated the trade yet, but sub-MAVOL participation signals weak demand and lowers odds of an immediate rebound.'}
