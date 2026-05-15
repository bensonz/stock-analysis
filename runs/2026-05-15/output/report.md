# 每日研究报告 2026-05-15

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4135.39 | -1.02% |
| 深证成指 | 15561.37 | -1.17% |
| 创业板指 | 3929.06 | -0.56% |
| 科创50 | 1696.26 | -1.67% |

涨跌比: 1816涨 / 3584跌 / 5497总

**热门板块**: 其他家电Ⅱ(+5.72%), 电机Ⅱ(+3.61%), 小家电(+2.68%), 家电零部件Ⅱ(+2.26%), 文娱用品(+2.03%)

**冷门板块**: 玻璃玻纤(-6.12%), 贵金属(-5.81%), 工业金属(-5.08%), 航天装备Ⅱ(-3.68%), 非金属材料Ⅱ(-3.44%)

Breadth 0.51:1 bearish, 73涨停/45跌停, all 3 major indices red; entry regime explicitly marked panic, so no new positions. Hot sectors were narrow household-appliance/electromechanical pockets, while 玻璃玻纤/贵金属/工业金属 led downside. Semi/advanced packaging news flow remains constructive, and恩捷股份 has a fresh 自贡50亿平方米隔膜扩产 catalyst, but the market gate is closed. IV context unavailable, so no IV-based sizing adjustment can override the hard regime block.

## 策略池扫描

扫描 **56** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **恩捷股份** (002812) (RPS 93.96%) — No new entry: market buy gate failed hard (breadth 0.51:1, 0/3 major indices green, panic regime). Stock-specific setup is acceptable on price support with rps120 93.96 and fresh 50亿平米隔膜扩产 catalyst, but new longs are blocked by regime.
2. **科达制造** (600499) (RPS 90.79%) — No new entry: regime blocks all fresh longs. Setup is technically orderly (dist_ma5_pct -5.1, dist_ma10_pct -3.8, dist_ma20_pct 2.0) and rps120 90.79 is in range, but weak tape overrides.
3. **咸亨国际** (605056) (RPS 93.35%) — No new entry: regime blocks all fresh longs. Price sits below MA5/MA10 with rps120 93.35, so this is not a chase, but the market environment is too weak for opening risk.
4. **万向钱潮** (000559) (RPS 89.15%) — Skip: rps120 89.15 is fine and MA distances are controlled, but sector is 汽车零部件, which is not shown among today's hot sectors; with panic tape, non-leading sectors are automatic skip.
5. **华锡有色** (600301) (RPS 92.84%) — Skip: sector is 有色/小金属 while 贵金属 and 工业金属 are both in the market bottom group today. Even though rps120 92.84 is workable, sector gravity is against it and regime is panic.
6. **江丰电子** (300666) (RPS 94.49%) — Skip: semiconductor trend/catalyst is real, but dist_ma10_pct 13.6 and dist_ma20_pct 22.4 violate the anti-chase rule. Also regime blocks new longs.
7. **华峰测控** (688200) (RPS 90.47%) — Skip: strong semiconductor catalyst, but dist_ma5_pct 10.7, dist_ma10_pct 20.8 and dist_ma20_pct 32.8 are far beyond entry limits. Clear anti-chase rejection.
8. **中船特气** (688146) (RPS 85.42%) — Skip: electronic chemicals/semiconductor theme is strong, but dist_ma10_pct 14.9 and dist_ma20_pct 43.5 fail MA-distance rules. Regime also blocks entries.
9. **上海新阳** (300236) (RPS 87.47%) — Skip: catalyst/fundamentals are decent, but dist_ma10_pct 16.4 and dist_ma20_pct 22.5 are too extended for a fresh entry.
10. **伟测科技** (688372) (RPS 93.8%) — Skip: fresh growth and semi trend are supportive, but dist_ma5_pct 6.4, dist_ma10_pct 11.1 and dist_ma20_pct 18.2 all breach the anti-chase thresholds.
11. **欧陆通** (300870) (RPS 89.09%) — Skip: sector had relative strength, but dist_ma10_pct 28.3 and dist_ma20_pct 44.4 are extreme extension. No chasing in a weak tape.
12. **共达电声** (002655) (RPS 94.55%) — Skip: rps120 94.55 is allowed, but dist_ma10_pct 23.1 and dist_ma20_pct 57.2 are severe anti-chase violations; risk notes also mention heavy volatility and prior sharp selloff.
13. **鼎通科技** (688668) (RPS 92.52%) — Skip: communications momentum remains strong, but dist_ma10_pct 25.0 and dist_ma20_pct 39.8 are far too extended for a proper entry.
14. **长芯博创** (300548) (RPS 93.71%) — Skip: strong communication/CPO catalyst, but dist_ma10_pct 26.0 and dist_ma20_pct 48.2 violate the non-negotiable MA-distance rule.
15. **莱特光电** (688150) (RPS 94.97%) — Skip: rps120 94.97 is within the extended zone and catalyst is real, but dist_ma20_pct 22.6 is too stretched. Also market regime blocks new positions.

## 今日研究结论

- 新开仓: 0只
- 跳过: 15只

### 新教训
- {'text': 'When the tape is panic-level, even acceptable pullback entries with valid RPS should remain unfilled; regime filter must dominate stock quality.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum entries need both stock strength and market participation. In a 0.51:1 breadth tape with 0/3 major indices green, isolated setups have poor follow-through and higher gap risk.'}
- {'text': 'The MA-distance anti-chase rule eliminated many visually attractive semis/communication names today, which is exactly its job in euphoric sub-themes.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Leaders can stay strong, but extreme distance from MA10/MA20 means poor reward-to-risk for new money because support is too far below entry.'}
- {'text': 'Today’s strongest candidates were not fundamentally weak; they were mostly disqualified by extension rather than lack of catalyst, reinforcing that setup quality matters more than narrative quality.', 'type': 'observation', 'tags': ['entry-filter', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Strong narratives attract fast money and create overbought conditions. Waiting for price to compress back toward MA5/MA10 improves asymmetry without needing to abandon the theme.'}
- {'text': 'Sector leadership today was narrow and defensive-leaning, while major indices and breadth were weak; treat this as unstable rotation, not a healthy momentum expansion.', 'type': 'heuristic', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'When only a few niche sectors rise while the broad list is red and limit-downs stay elevated, sector strength is less likely to propagate into durable swing entries.'}
