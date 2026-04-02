# 每日研究报告 2026-04-02

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3914.59 | -0.86% |
| 深证成指 | 13469.25 | -1.73% |
| 创业板指 | 3168.56 | -2.43% |
| 科创50 | 1260.64 | -2.89% |

涨跌比: 996涨 / 4429跌 / 5486总

**热门板块**: 油服工程(+4.94%), 林业Ⅱ(+4.69%), 油气开采Ⅱ(+2.72%), 养殖业(+2.14%), 饲料(+1.93%)

**冷门板块**: IT服务Ⅱ(-3.57%), 电视广播Ⅱ(-3.51%), 贵金属(-3.47%), 元件(-3.41%), 光伏设备(-3.40%)

Breadth 0.22:1 bearish, 31涨停/16跌停, all 3 major indices red and panic-like participation collapse; hot sectors are oil services, forestry and agriculture while tech/growth and 科创50 lag sharply. IV context is complacent-to-low (overall IV Rank about 11%), which would halve sizing for any new entry, but the regime gate is shut so no new positions.

## 策略池扫描

扫描 **21** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) (RPS 91.15%) — Sector is not in today’s top 30%, and MA chase filter fails: dist_ma5_pct 7.0% and dist_ma10_pct 8.3% exceed the hard limits. Also new-position gate is closed.
2. **烽火通信** (600498) (RPS 95.3%) — RPS120 95.3 is above the standard sweet spot and enters extended territory, but sector is not in today’s top 30% and there is no enriched MA-distance confirmation; with weak regime, skip rather than force.
3. **舒华体育** (605299) (RPS 94.93%) — Hard no-chase violation: dist_ma5_pct 16.0%, dist_ma10_pct 30.7%, dist_ma20_pct 47.9%. Even though momentum is strong, this is excessively extended and the market gate is closed.
4. **华通线缆** (605196) (RPS 95.36%) — RPS120 95.36 is above 95%, which is a skip under Rule 2. Sector also is not in today’s top 30%, so no entry.
5. **海星股份** (603115) (RPS 97.08%) — RPS120 97.08 is above 95%, so this is chasing by rule. No current price data in enriched_candidates to validate MA-distance, and regime is weak.
6. **华懋科技** (603306) (RPS 92.83%) — Sector (汽车零部件) is not in today’s top 30%. Stock-level setup is acceptable, but sector-first rule blocks new entry.
7. **明阳智能** (601615) (RPS 90.8%) — Sector (风电设备) is not in today’s top 30%, and short-term trend is weak with current_price below MA5/MA10/MA20 in enriched data. No entry in this tape.
8. **华鲁恒升** (600426) (RPS 88.62%) — RPS120 88.62 is within range and MA distances are fine, but sector is not in today’s top 30% and new-position gate is closed. Sector-first overrides stock quality.
9. **东材科技** (601208) (RPS 90.86%) — Sector is not in today’s top 30%. Stock is near moving averages, but sector-first rule and weak market regime block entry.
10. **利柏特** (605167) (RPS 93.49%) — Sector is not in today’s top 30%, and although MA distances are acceptable, revenue and net profit are both negative year-on-year while the market gate is closed.
11. **华锡有色** (600301) (RPS 93.29%) — Sector is not in today’s top 30%, and dist_ma20_pct is -13.1%, showing price is materially below intermediate support rather than in a clean momentum launch zone. Skip.
12. **三祥新材** (603663) (RPS 91.77%) — Sector is not in today’s top 30%, and dist_ma20_pct is -12.6%, indicating a broken intermediate trend rather than a proper momentum entry.
13. **芯源微** (688037) (RPS 85.85%) — Semiconductor/tech tape is weak today, sector is not in top 30%, and fundamentals are deteriorating with revenue_yoy -10.35% and net_profit_yoy -124.96%. No entry.

## 今日研究结论

- 新开仓: 0只
- 跳过: 13只

### 新教训
- {'text': 'When breadth collapses to 1:4.4 and all three major indices are red, the correct momentum action is usually no new longs regardless of how many individual candidates still show acceptable RPS readings.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum entries rely on upside participation and follow-through; in weak tapes, even strong charts are more likely to fail or mean-revert.'}
- {'text': 'MA-distance filters are highly valuable on breakout days: several apparent leaders today fail solely because they are too stretched from MA5/MA10/MA20, which is exactly the type of chase risk Rule 2b is designed to block.', 'type': 'heuristic', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When price is too far above short-term support, the reward-to-risk deteriorates and even valid catalysts cannot offset near-term mean reversion risk.'}
- {'text': 'Breakeven-stop positions in weak regimes should often be exited proactively if sector alignment worsens and stop proximity becomes effectively zero.', 'type': 'signal', 'tags': ['exit-rule', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'A stop sitting at the market with no cushion creates gap risk; in a hostile tape, preserving optionality is superior to hoping for a bounce.'}
