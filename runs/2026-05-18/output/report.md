# 每日研究报告 2026-05-18

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4131.53 | -0.09% |
| 深证成指 | 15530.23 | -0.20% |
| 创业板指 | 3914.88 | -0.36% |
| 科创50 | 1709.96 | +0.81% |

涨跌比: 2373涨 / 3003跌 / 5499总

**热门板块**: 元件(+3.44%), 油服工程(+3.37%), 通信服务(+2.88%), 电子化学品Ⅱ(+2.62%), 电视广播Ⅱ(+2.37%)

**冷门板块**: 工程机械(-3.76%), 养殖业(-3.23%), 医疗美容(-3.20%), 林业Ⅱ(-2.72%), 航海装备Ⅱ(-2.69%)

Breadth 0.79:1 bearish, 102涨停/56跌停, all 3 major indices red while only 科创50 rose 0.81%; hot sectors were 元件(+3.44%), 油服工程(+3.37%), 通信服务(+2.88%), 电子化学品Ⅱ(+2.62%), 电视广播Ⅱ(+2.37%), cold sectors were 工程机械(-3.76%), 养殖业(-3.23%), 医疗美容(-3.20%), 林业Ⅱ(-2.72%), 航海装备Ⅱ(-2.69%). Position sector alignment: 0/0 positions in hot sectors. IV context is mixed-to-neutral overall (avg IV Rank 40.0%), with 科创 proxies elevated around 54.5%, so even absent the hard block, sizing would need selectivity. Entry gate fails decisively: up/down ratio below 1, 0 of 上证/深成/创业板 green, and f10 at 56 signals a panic-style tape; stay in cash.

## 策略池扫描

扫描 **55** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **莱特光电** (688150) (RPS 94.97%) — Sector is hot and RPS120 94.97 is acceptable via top-sector exception, but entry blocked today by market regime; additionally dist_ma20_pct 22.6% exceeds no-chase limit
2. **江丰电子** (300666) (RPS 94.49%) — Semiconductor trend is strong and company catalyst is real, but dist_ma10_pct 13.6% and dist_ma20_pct 22.4% violate MA distance rule; also no new longs in panic regime
3. **恩捷股份** (002812) (RPS 93.96%) — RPS120 93.96 is in extended zone and price is near support, but sector is not in today's provided top sectors and market regime hard-blocks new entries
4. **华锡有色** (600301) (RPS 92.84%) — Setup is close to support, but current_price 59.38 sits 13.2% above MA20 which breaks the no-chase rule; market regime also blocks entries
5. **科达制造** (600499) (RPS 90.79%) — Technically one of the cleaner pullback setups with RPS120 90.79 and mild MA extension, but sector is not in today's top sector list and entry regime is hard-blocked
6. **万向钱潮** (000559) (RPS 89.15%) — RPS120 89.15 is valid and MA distance is controlled, but 汽车零部件 is not in today's top sector list and quarterly event shows 2026Q1 revenue and net profit declined; no new longs in current tape
7. **咸亨国际** (605056) (RPS 93.35%) — Price is below MA10 and not extended, but RPS120 93.35 is only acceptable with strong sector support and 通用设备 is not in today's top sectors; market regime blocks entries
8. **睿创微纳** (688002) (RPS 89.66%) — Military-electronics trend data is constructive, but dist_ma20_pct 18.9% exceeds no-chase limit and sector is not in today's top sector list; no entry
9. **鼎通科技** (688668) (RPS 92.52%) — Communication equipment theme is hot, but dist_ma10_pct 25.0% and dist_ma20_pct 39.8% are far beyond chase thresholds; skip despite strong catalyst
10. **中船特气** (688146) (RPS 85.42%) — Semiconductor-material narrative is strong, but dist_ma10_pct 14.9% and dist_ma20_pct 43.5% violate MA distance rule; additionally company flagged abnormal volatility in event feed
11. **华峰测控** (688200) (RPS 90.47%) — High-quality semiconductor leader, but dist_ma5_pct 10.7%, dist_ma10_pct 20.8%, and dist_ma20_pct 32.8% make this an obvious chase; no entry
12. **上海新阳** (300236) (RPS 87.47%) — Electronic chemicals sector is hot and earnings growth is strong, but dist_ma10_pct 16.4% and dist_ma20_pct 22.5% exceed entry limits; skip
13. **伟测科技** (688372) (RPS 93.8%) — Fundamentals and sector are good, but dist_ma5_pct 6.4%, dist_ma10_pct 11.1%, and dist_ma20_pct 18.2% all breach no-chase levels; not buyable here
14. **欧陆通** (300870) (RPS 89.09%) — Power-supply theme has momentum, but dist_ma10_pct 28.3% and dist_ma20_pct 44.4% are extreme extension; skip
15. **共达电声** (002655) (RPS 94.55%) — RPS120 94.55 is acceptable and current_price 38.1 is provided, but dist_ma10_pct 23.1% and dist_ma20_pct 57.2% are far too extended; also recent heavy-pressure risk noted in input
16. **长芯博创** (300548) (RPS 93.71%) — Communication equipment leadership is intact, but dist_ma10_pct 26.0% and dist_ma20_pct 48.2% violate no-chase rule; skip even with earnings catalyst

## 今日研究结论

- 新开仓: 0只
- 跳过: 16只

### 新教训
- {'text': 'When breadth is below 1:1 and all three major indices are red, even a 102涨停 tape is still a no-entry environment; isolated leaders do not override regime failure.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum entries need both leadership and participation. A split tape with many limit-downs increases failure risk for late entries even inside hot themes.'}
- {'text': "Today's candidate pool again shows the MA-distance anti-chase rule doing the heavy lifting: many strongest stories in semis, CPO, and electronic chemicals are simply too far above MA10/MA20 to buy.", 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'When a stock is already 15%-40% above intermediate support, upside-to-stop asymmetry collapses and even correct themes become poor trades.'}
- {'text': 'The best-looking non-chase setups today are pullback names such as 科达制造 and 万向钱潮, but sector-first discipline still requires passing on them when their sectors are not among the market leaders.', 'type': 'heuristic', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'mechanism': 'Clean chart location alone is not enough; relative sector sponsorship is what turns acceptable setups into actual momentum trades.'}
