# 每日研究报告 2026-07-08

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4011.05 | +0.52% |
| 深证成指 | 15237.45 | +0.08% |
| 创业板指 | 3949.04 | +0.95% |
| 科创50 | 2064.20 | +3.13% |

涨跌比: 1886涨 / 3458跌 / 5520总

**热门板块**: 计算机设备(+3.61%), IT服务Ⅱ(+3.54%), 通信设备(+2.95%), 半导体(+2.83%), 油服工程(+2.62%)

**冷门板块**: 能源金属(-4.89%), 电机Ⅱ(-4.45%), 家电零部件Ⅱ(-3.20%), 养殖业(-3.10%), 饲料(-3.01%)

False rally day: indices green (上证 +0.52%, 创业板 +0.95%, 科创50 +3.13%) but breadth decisively bearish at 0.545:1 (1886↑/3458↓). Yesterday 上证 lost 4000 for 4th time in 2026, ~4800 stocks fell. Today's bounce is narrow — only tech/AI hardware sectors (半导体 +2.83%, 计算机设备 +3.61%, 通信设备 +2.95%) are green. Energy metals crash (-4.89%, 融捷股份/盛新锂能跌停). IV data unavailable. Buy gate FAILS: breadth well below 1.5:1 minimum. Holding 100% cash (¥985K). No new positions until breadth recovers.

## 策略池扫描

扫描 **69** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **扬杰科技** (300373) (RPS 92.0%) — Breadth gate FAIL (0.545:1 < 1.5:1). 半导体 sector top 4 (+2.83%), RPS120 92.0% sweet spot, catalyst: 涨价函15-25%, dist_ma OK. Would BUY 5-7% if breadth normalizes.
2. **思瑞浦** (688536) (RPS 93.67%) — Breadth gate FAIL. 半导体 sector top 4, RPS120 93.67% (extended but sector top 10%), 净利+577%, dist_ma tight (-2.8%/-0.8%/+5.2%). Would BUY if breadth ≥ 1.5:1.
3. **路维光电** (688401) (RPS 91.31%) — Breadth gate FAIL. 半导体 sector top 4, RPS120 91.31% in sweet spot, 0 risks, 北向3.9%. High-conviction skip — first to buy when breadth recovers.
4. **奥来德** (688378) (RPS 93.18%) — Breadth gate FAIL. 光学光电子 sector related to hot tech, H1业绩预告净利+492-604%, 合同负债+860%. Would SMALL BUY if breadth recovers.
5. **华天科技** (002185) (RPS 90.03%) — Rule 2b: dist_ma20_pct +12.8% > 12%. Extreme MA20 extension. Also dist_ma5 +4.9% approaching 6% threshold. Skip regardless of breadth.
6. **京仪装备** (688652) (RPS 93.51%) — Rule 2b: dist_ma10_pct +11.2% > 8%, dist_ma20_pct +26.6% > 12%. Extreme overextension. Hard skip.
7. **伟测科技** (688372) (RPS 90.66%) — Rule 2b: dist_ma20_pct +13.0% > 12%. dist_ma10 +7.3% approaching 8%. Overextended from support.
8. **隆达股份** (688231) (RPS 92.51%) — Rule 2b: dist_ma5_pct +10.2% > 6%, dist_ma10_pct +8.4% > 8%. Double MA violation. Hard skip.
9. **融捷股份** (002192) (RPS 93.14%) — 能源金属 sector bottom 1 (-4.89%), sector-wide lithium crash, 触及跌停 today. Cold sector = no entry regardless of RPS.
10. **禾盛新材** (002290) (RPS 94.44%) — 家电零部件 sector bottom 3 (-3.20%). Cold sector gravity. Also 10-day relative strength at 4.1% percentile — stock already deteriorating.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': 'False rally divergence detected: all 3 major indices green but breadth at 0.545:1 with ~2x more decliners. Large-cap tech (科创50 +3.13%) masks broad distribution. The breadth ratio is a more honest signal than index color — the buy gate correctly blocked entries.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013 (strong breadth alone insufficient; need candidate data) — extended: even green indices are insufficient when breadth contradicts', 'mechanism': 'Institutional rotation into defensive large-caps creates index-level strength that hides broad-based distribution. The up/down ratio captures what the index color conceals.'}
- {'text': '能源金属 sector whipsaw: went from +5% leader (June 24 lithium surge) to -4.89% bottom (July 8 lithium crash with multiple limit-downs) in 10 days. Sector momentum spikes without persistence confirmation are traps.', 'type': 'observation', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': "h019 (bottom-list sectors = hard no-buy zones) and h028 (today's leaders in tech hardware, cyclicals being de-risked)", 'mechanism': 'Commodity-linked sectors (lithium, energy metals) are prone to violent reversals driven by futures prices and supply/demand news cycles rather than sustainable earnings trends.'}
- {'text': 'Semiconductor sector resilience continues: despite broad market selling, 半导体 +2.83% and remains in top 4. AI-driven price hike cycle (扬杰科技/芯联集成/斯达半导 all issuing涨价函 15-25%), ASML raised guidance, advanced packaging demand provide persistent catalyst. When breadth normalizes, semiconductor should be first sector to buy.', 'type': 'observation', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h028', 'mechanism': 'The semiconductor super-cycle (WSTS forecasts $1.51T global market in 2026, ~90% YoY) provides a structural demand tailwind that sector rotation and profit-taking cannot easily derail.'}
- {'text': 'MA-distance Rule 2b doing real work: 4 otherwise-attractive stocks (华天科技 +12.8% MA20, 京仪装备 +26.6% MA20, 伟测科技 +13.0% MA20, 隆达股份 +10.2% MA5) blocked by overextension rules. A less disciplined system would have bought these — and faced high mean-reversion risk in a weak tape.', 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h027 (MA-distance discipline remains critical inside hot sectors)', 'mechanism': 'Stocks that have run far above their moving averages have already priced in near-term catalysts. In a weak tape, the probability of profit-taking pulling them back to support is high.'}
