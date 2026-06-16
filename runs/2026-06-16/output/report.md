# 每日研究报告 2026-06-16

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4091.89 | -0.11% |
| 深证成指 | 15675.25 | +0.93% |
| 创业板指 | 4102.94 | +1.72% |
| 科创50 | 1758.42 | +0.58% |

涨跌比: 2729涨 / 2677跌 / 5514总

**热门板块**: 玻璃玻纤(+8.93%), 元件(+4.01%), 其他电源设备Ⅱ(+3.99%), 金属新材料(+3.96%), 小金属(+3.89%)

**冷门板块**: 航运港口(-2.76%), 工业金属(-2.67%), 冶钢原料(-2.57%), 保险Ⅱ(-2.21%), 煤炭开采(-2.07%)

Breadth 1.02:1 indecisive — 2729 up vs 2677 down, 141涨停/11跌停. 深证+0.93%, 创业板+1.72% green but 上证-0.11%. Tech/electronics materials leading (玻璃玻纤+8.93%, 元件+4.01%), resources rolling over (工业金属-2.67%). IV data unavailable. No new positions today — breadth gate failed (1.02 < 1.5). Focus on managing 5 existing positions: raise stop on 兴森科技 (+10.92%), monitor 路维光电/新宙邦 for +10% stop-raise triggers. 87% cash is appropriate for this tape.

## 策略池扫描

扫描 **50** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **平安电工** (001359) (RPS 94.88%) — Triple MA violation: dist_ma5=13.8%, dist_ma10=21.2%, dist_ma20=23.1%. Sector (塑料/膜材料) not in top 30%. PE 92, valuation 100th percentile.
2. **华峰测控** (688200) (RPS 94.32%) — Stock BELOW all MAs (dist_ma5=-7.5%, dist_ma10=-16.7%, dist_ma20=-17.5%). This is breakdown, not momentum. Sector (半导体设备) warm but stock itself is falling — sector gravity not helping.
3. **华锡有色** (600301) (RPS 94.3%) — dist_ma5=11.8% > 6% chase limit. 沪锡期货暴跌6% as fundamental headwind. Despite sector #5 (小金属 +3.89%), the commodity price risk is dominant.
4. **思瑞浦** (688536) (RPS 93.38%) — dist_ma5=8.4% > 6% chase limit. Strong fundamentals (rev +80%, NP +228%) but MA extension is non-negotiable per Rule 2b.
5. **奥来德** (688378) (RPS 93.9%) — Best candidate on paper: all MAs healthy, RPS in sweet spot, sector warm. BUT breadth gate closed (1.02:1 < 1.5:1). PE 100, revenue declining -16%. Watch for next opportunity when breadth improves.
6. **欧陆通** (300870) (RPS 89.81%) — dist_ma5=22.9%, dist_ma10=28.8% — extreme chase. Sector #3 (其他电源设备 +3.99%) but MA extension disqualifying. Google GPU power supply catalyst is strong — revisit on pullback.
7. **华丰科技** (688629) (RPS 90.16%) — 60.57% share unlock on 2026-06-29 — massive dilution event. Structural risk. Automatic disqualification regardless of fundamentals.
8. **华宏科技** (002645) (RPS 94.18%) — dist_ma20=11.5% near 12% hard limit. 3 risk factors including 100% controlling shareholder pledge. Sector (环保设备) not in top 30%.
9. **兴瑞科技** (002937) (RPS 93.73%) — Triple MA violation: dist_ma5=9.6% > 6%, dist_ma10=16.4% > 8%, dist_ma20=18.9% > 12%. Sector (汽车零部件) not in top 30%.
10. **恩捷股份** (002812) (RPS 89.16%) — RPS20=64.55 — momentum fading hard. VCP SETUP but contraction ratio 0.80 too loose. NP -125% YoY. Sector (电池) neutral.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': 'Breadth 1.02:1 is a hard no-new-positions signal even with 2/3 indices green. The market is split down the middle — indecision, not opportunity. Best action is to manage existing winners and wait for breadth confirmation above 1.5:1.', 'type': 'rule', 'tags': ['entry-filter', 'market-regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': "When up/down is near parity, there's no broad directional consensus. New entries opened in such conditions face 50/50 odds of immediate headwinds. The V2 framework correctly gates on breadth > 1.5:1 — this is the regime filter doing real work."}
- {'text': "MA-distance violations on EXISTING positions (兴森科技 10.7/10.0/17.2%) are yellow flags for adding, not red flags for selling. Let the trail stop do the work — selling winners because MAs are stretched is the old V1 'value trap' instinct.", 'type': 'heuristic', 'tags': ['position-sizing', 'exit-rule'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': "Stocks in strong uptrends routinely trade above short-term MAs. The correct response is: (a) do not add to extended positions, (b) raise stops mechanically to lock in gains per Rule 5, (c) let the trend continue until the stop is hit. Selling because 'it's gone too far' is the classic mistake of leaving money on the table."}
- {'text': 'Multiple positions clustered near +10% stop-raise threshold (路维光电 +9.09%, 新宙邦 +7.70%) is confirmation the V2 mechanical discipline is working. No overthinking needed — just raise stops when triggered.', 'type': 'observation', 'tags': ['exit-rule', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'The +10% → breakeven rule converts winning trades into risk-free holds without requiring a fresh market call. This is especially valuable in indecisive tapes like today, where the market direction is unclear but individual stocks are working.'}
- {'text': "华丰科技's 60.57% share unlock (2026-06-29, 13 days away) is an automatic disqualification. Binary dilution events dominate all other factors — fundamentals, sector, RPS become irrelevant when 61% of shares become freely tradable.", 'type': 'rule', 'tags': ['entry-filter', 'risk-management'], 'evidence_type': 'supporting', 'mechanism': "Massive unlocks create forced selling pressure as locked-up shareholders (often at near-zero cost basis) seek liquidity. Even if the stock doesn't immediately crash, the overhang suppresses price discovery and creates asymmetric downside risk. No exception should be made for 'good companies' — the structural risk is too large."}
- {'text': "Today's sector rotation confirms persistent tech/electronics materials leadership. 玻璃玻纤 +8.93% and 元件 +4.01% are the new leaders, while 工业金属 -2.67% and 煤炭 -2.07% continue to roll over. This is consistent with the multi-week trend identified in h028.", 'type': 'signal', 'tags': ['sector', 'market-regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h028', 'mechanism': "The rotation from cyclicals/resources into tech hardware supply chain is being driven by AI infrastructure buildout demand. Glass/fiber (玻璃玻纤) benefits from data center optical connectivity; components (元件) benefit from PCB/passive component demand. This is not a one-day spike — it's a multi-week regime."}
