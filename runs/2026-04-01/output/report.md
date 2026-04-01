# 每日研究报告 2026-04-01

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3948.83 | +1.46% |
| 深证成指 | 13667.17 | +1.40% |
| 创业板指 | 3231.02 | +1.45% |
| 科创50 | 1296.63 | +3.21% |

涨跌比: 4568涨 / 811跌 / 5488总

**热门板块**: 游戏Ⅱ(+4.63%), 酒店餐饮(+4.15%), 化学制药(+4.09%), 医疗服务(+3.92%), 玻璃玻纤(+3.77%)

**冷门板块**: 林业Ⅱ(-4.69%), 航天装备Ⅱ(-2.04%), 轨交设备Ⅱ(-1.11%), 乘用车(-0.70%), 广告营销(-0.48%)

Breadth 5.63:1 bullish, 53涨停/7跌停, all 3 major indices green and 科创50 +3.21%, so the long-entry gate is fully open. Hot sectors (top 5): 游戏Ⅱ +4.63%, 酒店餐饮 +4.15%, 化学制药 +4.09%, 医疗服务 +3.92%, 玻璃玻纤 +3.77%. Cold sectors (bottom 5): 林业Ⅱ -4.69%, 航天装备Ⅱ -2.04%, 轨交设备Ⅱ -1.11%, 乘用车 -0.70%, 广告营销 -0.48%. Position sector alignment: 1/1 positions in hot sectors. IV context is mildly complacent but not extreme: 300ETF IV Rank 16.6%, 500ETF 16.8%, 科创50 22.1%, so sizing can remain normal while strictly avoiding extended entries.

## 策略池扫描

扫描 **21** 只策略池股票
(来源: local_pricedb+cf_cross)

## 今日开仓

### 1. 杰普特 (688025) — BUY/moderate

- **入场价**: ¥216.56
- **止损**: ¥205.73
- **目标**: ¥259.87
- **RPS120**: 86.69%
- **板块**: 激光设备 (top 30%)

Strong broad tape favors fresh momentum; stock sits in RPS sweet spot, has 155% net profit growth, no listed risk factors, and price is not overextended from MA support.

## 跳过标的

1. **国电南自** (600268) (RPS 91.15%) — Sector logic is good and catalyst is fresh, but MA distance fails hard rule: dist_ma5_pct 7.0% and dist_ma10_pct 8.3%, so entry would be chasing.
2. **舒华体育** (605299) (RPS 94.93%) — RPS is in range but stock is massively extended: dist_ma5_pct 16.0%, dist_ma10_pct 30.7%, dist_ma20_pct 47.9%. Non-negotiable no-chasing rule.
3. **烽火通信** (600498) (RPS 95.3%) — RPS120 95.3 is above the allowed buy zone and the available data does not include MA-distance fields in enriched_candidates, so timing/risk control is insufficient for a fresh entry.
4. **华通线缆** (605196) (RPS 95.36%) — RPS120 95.36 is above the buy threshold; also recent 10-day relative strength is weak in the stock notes, so skip rather than chase late.
5. **海星股份** (603115) (RPS 97.08%) — RPS120 97.08 is too extended and above 95% chase zone. No fresh entry.
6. **华懋科技** (603306) (RPS 92.83%) — Sector is in cold group proxy: 汽车/汽车零部件 conflicts with today's bottom sectors where 乘用车 is weak, so despite acceptable MA distances this is not a momentum-first sector entry.
7. **明阳智能** (601615) (RPS 90.8%) — RPS is acceptable but trend quality is poor: current price is below MA5/MA10/MA20 and dist_ma20_pct is -13.5%, showing a broken setup rather than a strength entry.
8. **华鲁恒升** (600426) (RPS 88.62%) — Good company quality, but sector is not in today's top leadership group and catalyst is slower-cycle than current fast money themes; better to focus on hotter sectors.
9. **东材科技** (601208) (RPS 90.86%) — Setup is technically fine, but sector mapping is less clear versus today's top sectors and catalyst is older than the best alternatives. Lower priority than stronger/fresher momentum names.
10. **利柏特** (605167) (RPS 93.49%) — RPS120 93.49 is allowed, but sector is outside today's top leadership list and financial growth is negative year over year, so not strong enough for new capital despite acceptable MA distances.
11. **华锡有色** (600301) (RPS 93.29%) — RPS120 93.29 is acceptable, but 10-day relative strength note is very weak and the stock sits below MA20, suggesting momentum has cooled versus hotter sectors.
12. **三祥新材** (603663) (RPS 91.77%) — RPS is in range, but current price is below MA5/MA10/MA20 and recent 10-day strength note is weak, so setup is not a buy-strength entry.

## 今日研究结论

- 新开仓: 1只
- 跳过: 12只

### 新教训
- {'text': "In a strong breadth regime, the main reason to skip otherwise attractive names is usually extension, not fundamentals; today's best-looking power-equipment candidate still failed solely on MA-distance.", 'type': 'rule', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Strong tapes lift many leaders at once, so late entries often come from buying above near-term support; MA-distance keeps momentum entries aligned with pullback risk control.'}
- {'text': 'Low-IV conditions around 16-22% IV rank do not justify freezing risk when breadth is 5.6:1; they argue for normal sizing but tighter discipline on chasing.', 'type': 'heuristic', 'tags': ['timing', 'position-sizing', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Cheap volatility means trend continuation can persist, but upside surprise from fresh entries comes from proper setup quality, not from paying up far above moving averages.'}
- {'text': 'A live position can remain HOLD even with weak volume if price is above stop and the market regime is strong; weak volume should block adds before it forces an exit.', 'type': 'signal', 'tags': ['exit-rule', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h017', 'mechanism': 'Volume deterioration reduces confirmation but is not itself a sell signal until accompanied by price failure, stop pressure, or time-stop deterioration.'}
