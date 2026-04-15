# 每日研究报告 2026-04-15

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4041.45 | +0.37% |
| 深证成指 | 14603.61 | -0.25% |
| 创业板指 | 3550.25 | -0.23% |
| 科创50 | 1424.71 | +1.40% |

涨跌比: 2506涨 / 2819跌 / 5494总

**热门板块**: 黑色家电(+3.11%), 航天装备Ⅱ(+3.00%), 医药商业(+2.80%), 专业连锁Ⅱ(+2.27%), 游戏Ⅱ(+2.27%)

**冷门板块**: 能源金属(-3.03%), 化学原料(-2.57%), 油服工程(-2.46%), 油气开采Ⅱ(-2.30%), 玻璃玻纤(-2.12%)

Breadth 0.89:1 weak, 52涨停/9跌停, not panic but below the minimum long-entry gate; only 上证指数 is green while 深证成指 and 创业板指 are red. Hot sectors (top 5): 黑色家电 +3.11%, 航天装备Ⅱ +3.00%, 医药商业 +2.80%, 专业连锁Ⅱ +2.27%, 游戏Ⅱ +2.27%. Cold sectors (bottom 5): 能源金属 -3.03%, 化学原料 -2.57%, 油服工程 -2.46%, 油气开采Ⅱ -2.30%, 玻璃玻纤 -2.12%. Position sector alignment: 0/2 positions in hot sectors. IV context is generally low/optimistic; several small-cap proxies are below 15% IV Rank, so fresh risk should be throttled, but today the breadth gate already says no new positions.

## 策略池扫描

扫描 **39** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **国电南自** (600268) (RPS 91.19%) — Setup is acceptable on MA distances and RPS120 91.19, and catalyst is fresh, but market buy gate fails: breadth only 0.89:1 and only 1 of 3 major indices is green. Skip new entries in weak tape.
2. **新风光** (688663) (RPS 92.65%) — Electric grid theme has policy support and MA distances are still within limits, but entry regime fails. Also stock-specific IV proxy rank is 12.1%, which would require half sizing even if tape were stronger.
3. **英科医疗** (300677) (RPS 93.27%) — Medical side is relatively strong, but no current sector top-30% confirmation from supplied sector table and catalyst quality is partly commodity-driven. In weak market regime, avoid fresh longs despite valid MA distances.
4. **华鲁恒升** (600426) (RPS 88.69%) — Sector headwind: chemical-related groups are weak today with 化学原料 in bottom 5. Stock RPS120 88.69 is fine, but sector gravity is against the trade.
5. **闰土股份** (002440) (RPS 94.42%) — Chemical/dye exposure sits against today's weak chemical tape, and company-specific news mentions oil-price-driven cost pressure. Even though RPS120 94.42 is in range and MA distances are fine, sector is wrong.
6. **华锡有色** (600301) (RPS 92.84%) — Resources are in cold tape with 能源金属 bottom-ranked. Fresh report catalyst exists, but sector is not buyable under sector-first rule.
7. **东材科技** (601208) (RPS 91.42%) — Fails no-chasing rule: dist_ma5_pct 7.5% and dist_ma10_pct 10.4% exceed limits.
8. **华峰测控** (688200) (RPS 90.95%) — Fails no-chasing rule: dist_ma5_pct 8.0% and dist_ma10_pct 9.8% exceed limits, despite strong semiconductor catalyst and 0 risk factors.
9. **广合科技** (001389) (RPS 90.99%) — Fails no-chasing rule badly: dist_ma5_pct 8.6%, dist_ma10_pct 16.0%, dist_ma20_pct 16.4%. Strong stock, wrong entry.
10. **华懋科技** (603306) (RPS 93.43%) — Fails no-chasing rule severely with dist_ma5_pct 15.7%, dist_ma10_pct 22.3%, dist_ma20_pct 19.6%. No current price chase allowed.
11. **博众精工** (688097) (RPS 92.63%) — Fails no-chasing rule: dist_ma5_pct 11.1%, dist_ma10_pct 13.8%, dist_ma20_pct 17.5%.

## 今日研究结论

- 新开仓: 0只
- 跳过: 11只

### 新教训
- {'text': 'Weak breadth should override attractive single-stock setups; today several candidates had legal RPS and acceptable MA structure, but the correct action is still no new positions because breadth was below 1:1 and only one major index was green.', 'type': 'rule', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum entries depend on follow-through. When the average stock is down, even strong charts have lower odds of clean continuation.'}
- {'text': 'The no-chasing MA filter remains essential in strong themes: many of the visually strongest names today were disqualified by excessive distance from MA5/MA10/MA20.', 'type': 'heuristic', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'Extended entries compress reward-to-risk and leave little nearby support, increasing mean-reversion risk.'}
- {'text': 'Mechanical stop promotion after a fast winner continues to reduce damage: 利柏特 gave back sharply today, but the prior raise to breakeven kept the trade from turning into a loser.', 'type': 'signal', 'tags': ['exit-rule', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'In weak or mixed tape, locking a winner at breakeven converts a momentum trade into a low-risk optionality hold.'}
- {'text': 'Low-IV conditions are not a buy signal by themselves; several small/mid-cap candidates had IV Rank below 15%, which argues for reduced sizing rather than aggressive initiation.', 'type': 'observation', 'tags': ['position-sizing', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h017', 'mechanism': 'Cheap volatility often coincides with complacency, so breakouts need stronger market confirmation to stick.'}
