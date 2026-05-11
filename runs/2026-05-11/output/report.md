# 每日研究报告 2026-05-11

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4219.13 | +0.94% |
| 深证成指 | 15895.75 | +2.13% |
| 创业板指 | 3911.32 | +3.03% |
| 科创50 | 1726.98 | +5.27% |

涨跌比: 2995涨 / 2340跌 / 5494总

**热门板块**: 半导体(+6.86%), 电子化学品Ⅱ(+5.71%), 工程机械(+4.98%), 其他电子Ⅱ(+4.81%), 光伏设备(+3.78%)

**冷门板块**: 贵金属(-2.79%), 航运港口(-2.58%), 酒店餐饮(-1.97%), 游戏Ⅱ(-1.69%), 化妆品(-1.66%)

Breadth 1.28:1偏中性偏强，103涨停/26跌停，3大指数全绿转红且科创50大涨5.27%，说明资金集中进攻成长科技；但上涨家数优势不够，新仓硬门槛未过。Hot sectors (top 5): 半导体(+6.86%), 电子化学品Ⅱ(+5.71%), 工程机械(+4.98%), 其他电子Ⅱ(+4.81%), 光伏设备(+3.78%). Cold sectors (bottom 5): 贵金属(-2.79%), 航运港口(-2.58%), 酒店餐饮(-1.97%), 游戏Ⅱ(-1.69%), 化妆品(-1.66%). Position sector alignment: 0/0 positions in hot sectors. IV context: overall sentiment 偏乐观, avg IV rank 24.2%; most tech proxies are in normal sizing range, so the throttle is breadth/extension, not IV.

## 策略池扫描

扫描 **54** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **伟测科技** (688372) (RPS 93.8%) — Sector is hot and RPS120 93.8 is acceptable, but this is extended-zone momentum and better than most because MA distances pass; still skipped because market buy gate fails with up/down ratio only 1.28:1 below the required 1.5:1.
2. **科达制造** (600499) (RPS 90.79%) — MA distances are clean and RPS120 90.79 is in the sweet spot, but sector is not confirmed in today top 30% leaders and regime buy gate fails; no forced entry.
3. **咸亨国际** (605056) (RPS 93.35%) — Chart is not extended and RPS120 93.35 is acceptable, but it is in 通用设备 rather than today's top leadership sectors; also stock-specific IV proxy rank 13.2% would require half sizing even if regime were stronger.
4. **上海新阳** (300236) (RPS 87.47%) — Sector is hot, but dist_ma10_pct 8.8% and dist_ma20_pct 12.5% violate the no-chase thresholds. Non-negotiable skip.
5. **莱特光电** (688150) (RPS 94.97%) — Sector is hot and catalyst is real, but dist_ma20_pct 22.6% exceeds the 12% anti-chase limit. Skip despite momentum.
6. **洁美科技** (002859) (RPS 86.88%) — Other electronics is hot, but dist_ma10_pct 9.4% and dist_ma20_pct 13.2% are beyond entry limits. Skip.
7. **江丰电子** (300666) (RPS 94.49%) — 半导体 is the #1 sector and fundamentals/catalyst are strong, but dist_ma10_pct 11.9% and dist_ma20_pct 17.8% violate the MA distance rule.
8. **华峰测控** (688200) (RPS 90.47%) — 半导体 leader with strong institutional support, but dist_ma20_pct 16.0% exceeds the 12% limit. Skip rather than chase.
9. **中船特气** (688146) (RPS 85.42%) — 半导体 sector tailwind is positive, but dist_ma10_pct 14.9% and dist_ma20_pct 43.5% are far too extended for a fresh entry.
10. **鼎通科技** (688668) (RPS 92.52%) — Communication setup has strong catalyst, but dist_ma10_pct 25.0% and dist_ma20_pct 39.8% make it a textbook chase. Skip.
11. **长芯博创** (300548) (RPS 93.71%) — Momentum is strong, but dist_ma5_pct 6.6%, dist_ma10_pct 33.9%, and dist_ma20_pct 53.5% all fail anti-chase rules.
12. **德福科技** (301511) (RPS 91.71%) — Battery catalyst is powerful, but dist_ma5_pct 27.9%, dist_ma10_pct 69.5%, and dist_ma20_pct 104.3% are extreme extension. Hard skip.
13. **万向钱潮** (000559) (RPS 89.15%) — Automobile parts is not in today's top leadership sectors, and latest event text shows 2026Q1 revenue down 19.84% and net profit down 15.84%. Sector-first says no entry.
14. **华锡有色** (600301) (RPS 92.84%) — Small metals strength is visible, but today's market sector board shows 贵金属 in the bottom group and this stock also fails MA limits with dist_ma5_pct 7.5%, dist_ma10_pct 11.3%, dist_ma20_pct 15.5%.

## 今日研究结论

- 新开仓: 0只
- 跳过: 14只

### 新教训
- {'text': "今天是典型的'指数强、个股广度一般'环境：3大指数全红且103只涨停，但上涨/下跌仅1.28:1，低于1.5:1新开仓硬门槛，最优动作是空仓等待而不是勉强试单。", 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': '指数被强主线和权重成长拉动时，若广度跟不上，追涨的新仓容错率会明显下降。'}
- {'text': '今天大量热门候选股被MA距离规则拦下，说明h021仍在生效：真正的问题不是找不到强股，而是强股大多已经离短期支撑太远。', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': '均线乖离过大意味着短线盈亏比恶化，哪怕主线正确，也容易先经历均值回归。'}
- {'text': '当前最值得跟踪的可执行候选不是最猛的涨停型品种，而是像伟测科技、科达制造、咸亨国际这类相对未过度乖离的名字；一旦广度从1.28:1修复到1.5:1以上，它们更容易成为低追高风险的首批入场对象。', 'type': 'heuristic', 'tags': ['timing', 'entry-filter', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': '先筛掉过度扩张个股，再等待市场广度确认，可以同时满足顺势和不追高。'}
- {'text': 'IV环境整体偏乐观但不极低，多数科技候选股的个股代理IV Rank在28%-39%之间，说明问题不在波动率定价，而在市场广度和个股延伸度；IV不是今天不开仓的主因。', 'type': 'observation', 'tags': ['position-sizing', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h017', 'mechanism': '当IV处于正常区间时，是否开仓更多取决于breadth gate和MA距离约束。'}
