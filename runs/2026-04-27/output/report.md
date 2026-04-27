# 每日研究报告 2026-04-27

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4083.17 | +0.08% |
| 深证成指 | 14981.80 | +0.28% |
| 创业板指 | 3645.38 | -0.61% |
| 科创50 | 1506.39 | +3.63% |

涨跌比: 3178涨 / 2222跌 / 5495总

**热门板块**: 半导体(+4.10%), 其他家电Ⅱ(+3.92%), 化妆品(+3.82%), 消费电子(+3.65%), 商用车(+3.00%)

**冷门板块**: 白酒Ⅱ(-3.10%), 小金属(-2.58%), 基础建设(-2.08%), 航海装备Ⅱ(-1.80%), 普钢(-1.76%)

Breadth 1.43:1 mildly positive but below the 1.5:1 long-entry gate, with 84涨停/54跌停 showing unstable internals. 2 of 3 major indices are green, but 创业板指 is red while 科创50 surges, pointing to narrow tech leadership rather than clean broad risk-on. Hot sectors are 半导体(+4.1%), 其他家电Ⅱ(+3.92%), 化妆品(+3.82%), 消费电子(+3.65%), 商用车(+3.0%); cold sectors are 白酒Ⅱ(-3.1%), 小金属(-2.58%), 基础建设(-2.08%), 航海装备Ⅱ(-1.8%), 普钢(-1.76%). Position sector alignment: 0/1 positions in top-5 hot sectors. IV context is complacent overall: market-wide avg IV rank 12.4%, with many沪市/科创 proxies below 15%, so even if setup quality is good, fresh sizing should be reduced or skipped. Net: tech leadership is real, but the regime remains blocked for new positions today.

## 策略池扫描

扫描 **39** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **恩捷股份** (002812) (RPS 93.33%) — Battery catalyst is real and fresh with profit growth and board strength, but entry regime hard-blocks new longs; additionally sector is not in provided top-5 sector leaders today, so skip despite valid setup.
2. **华峰测控** (688200) (RPS 90.95%) — Semiconductor sector is hot and stock quality is good, but board-specific IV proxy is only 11.3% so sizing would be halved, and the market entry gate is hard-blocked. Candidate is acceptable on MA distance but no new position under current regime.
3. **北化股份** (002246) (RPS 90.23%) — RPS and MA distances are acceptable and catalyst is fresh, but sector is not in the provided top leaders and entry regime blocks fresh longs. VCP is only SETUP, not enough to override regime.
4. **科达制造** (600499) (RPS 89.74%) — Earnings catalyst is strong, but RPS120 89.74 sits in range while sector is not among today's top leaders and new long gate is blocked. Also沪市IV proxy is near 0%, which would force half sizing even if regime improved.
5. **东材科技** (601208) (RPS 91.42%) — Trend and earnings are strong, but dist_ma10_pct 8.6% breaches the anti-chase rule and new longs are blocked by regime.
6. **兴福电子** (688545) (RPS 91.38%) — Semiconductor materials theme is hot, but dist_ma10_pct 9.5% fails the non-negotiable MA-distance chase filter; entry regime also blocks new longs.
7. **广合科技** (001389) (RPS 90.99%) — Strong PCB/AI hardware trend and fresh high, but dist_ma10_pct 10.3% fails anti-chase rule. No new position.
8. **上海新阳** (300236) (RPS 88.95%) — Semiconductor material trend is constructive, but dist_ma5_pct 9.3% and dist_ma10_pct 11.7% both violate anti-chase limits.
9. **莱特光电** (688150) (RPS 93.31%) — Electronic chemicals trend is up and catalyst exists, but dist_ma10_pct 11.5% and dist_ma20_pct 21.7% are far too extended for a fresh entry.
10. **华锡有色** (600301) (RPS 92.84%) — Sector 小金属 is in the bottom-5 cold sectors today. Rule 1 says no entry regardless of individual setup.
11. **鄂尔多斯** (600295) (RPS 92.38%) — Steel-related sector exposure is out of favor and not in top 30% of today's sector leaders; no entry despite acceptable MA position.
12. **望变电气** (603191) (RPS 88.91%) — Power grid theme is not in the provided top leaders today, and stock RPS120 88.91 is acceptable but lacks sector confirmation. With regime blocked, skip.
13. **华懋科技** (603306) (RPS 93.43%) — Sector not in top leaders, stock had a recent heavy drop risk, and dist_ma10_pct 14.5% plus dist_ma20_pct 21.8% violate anti-chase rule.

## 今日研究结论

- 新开仓: 0只
- 跳过: 13只

### 新教训
- {'text': 'A positive index mix alone is not enough for new longs; breadth 1.43:1 with 54跌停 still behaves like a blocked tape, so cash is a valid momentum position.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'market-regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When upside participation is only modest and limit-down count stays high, breakouts face higher failure risk even inside hot sectors.'}
- {'text': 'The MA-distance anti-chase rule is filtering many of the strongest-looking tech names today, which is exactly its job in euphoric sub-tapes.', 'type': 'signal', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Extended stocks far above MA5/MA10/MA20 have poor reward-to-risk because support is too distant and mean reversion risk rises sharply.'}
- {'text': 'Raised stops must still be respected after sharp earnings-driven gaps reverse; a winner that collapses double digits in one day should not be given narrative room.', 'type': 'heuristic', 'tags': ['exit-rule', 'position-sizing', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'Mechanical stop discipline converts prior open profit into realized capital and prevents a momentum name from turning into a hope trade.'}
