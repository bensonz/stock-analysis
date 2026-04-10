# 每日研究报告 2026-04-10

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3991.14 | +0.63% |
| 深证成指 | 14239.89 | +1.74% |
| 创业板指 | 3410.39 | +2.62% |
| 科创50 | 1367.01 | +1.72% |

涨跌比: 4425涨 / 970跌 / 5495总

**热门板块**: 玻璃玻纤(+3.89%), 证券Ⅱ(+3.57%), 电池(+3.44%), 其他电源设备Ⅱ(+3.29%), 其他电子Ⅱ(+2.97%)

**冷门板块**: 贵金属(-1.70%), 航运港口(-1.05%), 白酒Ⅱ(-0.72%), 工业金属(-0.69%), 文娱用品(-0.68%)

Breadth 4.56:1 bullish, 63涨停/5跌停, 3/3 major indices green, broad-based rally led by 玻璃玻纤、证券、电池 and electronics. Research confirms 玻纤 strength is tied to 宏和科技年报净利同比+785.55% and electronic glass-fiber cloth price improvement; batteries and electronics also have supportive industry narratives, while brokers are participating in the risk-on move. IV context is complacent: overall avg IV Rank about 9.16%, with position proxies 300ETF 8.3% and 科创50 7.8%, so new-entry sizing should be cut in half even when the regime is strong. However, there are no validated enriched_candidates today, so no fresh positions should be opened.

## 策略池扫描

扫描 **0** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) — No current candidate packet in enriched_candidates, so RPS/MA-distance/VCP checks required by the framework cannot be verified. Strong breadth alone is not enough to force entries.
2. **烽火通信** (600498) — No current candidate packet in enriched_candidates, so catalyst freshness may be interesting but the mandatory entry checks on sector rank, MA distance and setup quality cannot be confirmed.
3. **海星股份** (603115) — No current candidate packet in enriched_candidates and no verified MA-distance data. Under Rule 2b, missing MA data is a risk factor; without a full candidate record, skip rather than force a buy.
4. **华通线缆** (605196) — No current candidate packet in enriched_candidates. Market regime is strong, but the framework still requires stock-level confirmation before opening new risk.
5. **华锡有色** (600301) — Industrial metals are in today's cold list proxy and the stock is not in today's validated candidate set. Cold-sector exposure is against the sector-first rule.

## 今日研究结论

- 新开仓: 0只
- 跳过: 5只

### 新教训
- {'text': 'When strategy_pool and enriched_candidates are empty, even a 4.56:1 breadth day should still produce no new positions; strong tape is a permission slip, not a substitute for stock-level setup data.', 'type': 'rule', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum entries need both market tailwind and a valid individual setup. Without RPS/MA/VCP data, the system cannot distinguish strength from chase risk.'}
- {'text': 'Low IV Rank remains a sizing throttle, not a directional sell signal. Existing winners can be held, but fresh exposure should stay constrained when IV proxies are near 8%.', 'type': 'heuristic', 'tags': ['position-sizing', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Very low IV reflects complacency: trends can continue, but the reward-to-new-entry profile worsens because volatility expansion risk rises from a low base.'}
- {'text': "Sub-MAVOL30 volume on both open positions is not yet an exit signal by itself when price is rising and stops are intact, but it is a clear 'do not add' condition.", 'type': 'signal', 'tags': ['timing', 'exit-rule', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Weak volume reduces confidence in follow-through. It does not negate price strength immediately, but it lowers the probability that a breakout leg can accelerate.'}
