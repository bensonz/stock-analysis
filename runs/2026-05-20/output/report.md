# 每日研究报告 2026-05-20

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4162.19 | -0.18% |
| 深证成指 | 15569.98 | +0.00% |
| 创业板指 | 3921.79 | +0.34% |
| 科创50 | 1832.02 | +3.20% |

涨跌比: 1638涨 / 3803跌 / 5499总

**热门板块**: 半导体(+4.18%), 光伏设备(+2.68%), 非金属材料Ⅱ(+2.31%), 油气开采Ⅱ(+1.83%), 非白酒(+1.54%)

**冷门板块**: 电力(-3.89%), 通信服务(-3.76%), 文娱用品(-3.51%), 广告营销(-3.44%), 数字媒体(-2.94%)

Breadth 0.43:1 bearish, 71涨停/43跌停, clearly a panic-style tape despite 科创50 +3.2% and 半导体 +4.18% leading. Only 1 of 3 major indices was green, so the long-entry gate fails and new positions stay at zero. Hot sectors: 半导体、光伏设备、非金属材料Ⅱ、油气开采Ⅱ、非白酒; cold sectors: 电力、通信服务、文娱用品、广告营销、数字媒体. Position sector alignment: 0/1 in hot sectors. IV context is mixed-to-benign: broad market IV is low-to-neutral, while 创业板/科创 proxies are normal, so IV is not the blocker here—breadth and panic distribution are.

## 策略池扫描

扫描 **54** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **江丰电子** (300666) (RPS 94.65%) — Sector is hot (半导体) and catalyst is fresh, but dist_ma5_pct 12.4%, dist_ma10_pct 24.7%, dist_ma20_pct 37.9% all violate anti-chase rule; also entry regime hard-blocks new longs.
2. **德科立** (688205) (RPS 93.56%) — Communication-equipment trend is decent and price is near MA5/MA10, but dist_ma20_pct 16.0% exceeds max 12%; market entry gate is also closed.
3. **华锡有色** (600301) (RPS 92.34%) — MA distances are acceptable, but sector is not in the listed top sectors and breadth regime is panic, so no new entry despite acceptable pullback setup.
4. **咸亨国际** (605056) (RPS 92.48%) — MA distances are acceptable and catalyst exists, but sector is not in the listed top 30% and stock-specific IV proxy says half sizing; with hard-blocked regime this becomes a skip, not a buy.
5. **睿创微纳** (688002) (RPS 89.36%) — Good military-electronics trend and acceptable MA distances, but sector is not in today's listed hot sectors and regime blocks fresh longs.
6. **明阳电路** (300739) (RPS 91.43%) — Technically closest to valid entry among candidates, but sector is not in listed top sectors and panic breadth blocks all new positions.
7. **万凯新材** (301216) (RPS 86.97%) — No re-entry after exit: sector not in listed hot sectors, first-3-days downside rule was violated, and current tape does not permit recycling capital into the same weak setup.

## 今日研究结论

- 新开仓: 0只
- 跳过: 7只

### 新教训
- {'text': 'A hot leading sector does not override the market-level buy gate; today semiconductors were strong, but breadth 0.43:1 with 43跌停 still correctly forces new_positions to empty.', 'type': 'rule', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When leadership narrows while most stocks fall, breakouts have lower follow-through and higher reversal risk, so sector strength alone is insufficient.'}
- {'text': 'The anti-chase MA-distance rule continues to do real work: many of the strongest-looking semiconductor names failed because they were far above MA5/MA10/MA20 despite fresh catalysts.', 'type': 'signal', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Momentum names extended far from support have poor reward-to-risk because even small pullbacks can be sharp mean reversions.'}
- {'text': 'The -3% in first 3 days exit rule should be applied on closing damage, not just mark-to-market vs entry, when a fresh position immediately loses momentum and volume confirmation weakens.', 'type': 'heuristic', 'tags': ['exit-rule', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'A new entry that cannot hold within the first 72 hours in a weak tape is usually mistimed; fast exits preserve mental and financial capital for better setups.'}
