# 每日研究报告 2026-05-08

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4162.27 | -0.43% |
| 深证成指 | 15495.22 | -0.94% |
| 创业板指 | 3795.44 | -0.98% |
| 科创50 | 1630.24 | -2.90% |

涨跌比: 3026涨 / 2308跌 / 5491总

**热门板块**: 航运港口(+2.65%), 电机Ⅱ(+2.64%), 贸易Ⅱ(+2.55%), 航天装备Ⅱ(+2.51%), 其他家电Ⅱ(+2.42%)

**冷门板块**: 半导体(-2.93%), 能源金属(-2.76%), 冶钢原料(-2.72%), 综合Ⅱ(-2.71%), 医疗服务(-2.07%)

Breadth 1.31:1 mixed-to-weak, 90涨停/34跌停, but 0/3 major indices green and entry_regime is hard-blocked as panic. Hot pockets are 航运港口、电机、贸易、航天装备, while 半导体 leads the downside at -2.93%, showing rotation rather than broad momentum. IV context is mostly low-to-neutral (overall IV sentiment 偏乐观; stock proxies mostly 18%-42% IV rank), so volatility is not the problem—the problem is failed regime confirmation. Per Rule 1, no new positions today.

## 策略池扫描

扫描 **57** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **国电南自** (600268) (RPS 89.92%) — Entry regime hard-blocked: breadth 1.31:1 is below the 1.5:1 gate and 0/3 major indices are green. Setup itself is orderly (rps120 89.92, dist_ma5_pct 0.5, dist_ma10_pct -0.4, dist_ma20_pct 3.4) and sector is supportive, but no new longs in this tape.
2. **科达制造** (600499) (RPS 90.79%) — Would be one of the cleaner candidates on metrics (rps120 90.79; dist_ma5_pct -1.9, dist_ma10_pct -0.2, dist_ma20_pct 7.0) with earnings catalyst, but the market buy gate failed and no current sector ranking beyond daily top/bottom confirms top-30% status.
3. **福晶科技** (002222) (RPS 92.23%) — Technically too extended for a fresh entry: dist_ma20_pct 12.7 exceeds the 12% hard chase limit. Also market regime blocks new longs.
4. **伟测科技** (688372) (RPS 93.8%) — Semiconductor is in today's bottom 5 sectors at -2.93%, so sector gravity is wrong for a new entry despite acceptable MA distances and strong earnings growth.
5. **江丰电子** (300666) (RPS 94.49%) — Sector is wrong: 半导体 is bottom 5 at -2.93%. Also dist_ma10_pct 11.9 and dist_ma20_pct 17.8 both violate the anti-chase limits.
6. **华锡有色** (600301) (RPS 92.84%) — Overextended after the move: dist_ma5_pct 7.5, dist_ma10_pct 11.3 and dist_ma20_pct 15.5 all violate the MA-distance rule. Market regime also blocks entries.
7. **共达电声** (002655) (RPS 94.55%) — Hard fail on anti-chase rule: dist_ma5_pct 25.3, dist_ma10_pct 55.3, dist_ma20_pct 84.3. No matter how strong the narrative, this is not a valid fresh entry.
8. **长芯博创** (300548) (RPS 93.71%) — Hard fail on anti-chase rule: dist_ma5_pct 6.6, dist_ma10_pct 33.9, dist_ma20_pct 53.5. Too extended for momentum entry here.
9. **德福科技** (301511) (RPS 91.71%) — Hard fail on anti-chase rule: dist_ma5_pct 27.9, dist_ma10_pct 69.5, dist_ma20_pct 104.3. Also current market regime does not permit new risk.
10. **万向钱潮** (000559) (RPS 89.15%) — RPS120 89.15 is acceptable, but dist_ma5_pct 7.1 and dist_ma10_pct 8.1 both exceed chase limits, and there is no regime clearance for new positions.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': 'The entry gate prevented forcing otherwise decent setups like 国电南自 and 科达制造 in a tape where breadth was only 1.31:1 and all 3 major indices were red.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When index confirmation is absent, individual momentum names lose follow-through probability even if their stock-level structure is fine.'}
- {'text': 'The MA-distance anti-chase rule is doing heavy lifting again: many of the strongest-looking names today are invalid purely because they are too far above MA10/MA20.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Late entries after vertical expansion shift the reward/risk against the trader by increasing mean-reversion risk and widening the distance to support.'}
- {'text': "Sector-first filtering matters more on distribution days: today's bottom-ranked 半导体 group still contains high-RPS stocks, but the sector tape is hostile enough to override stock strength.", 'type': 'heuristic', 'tags': ['sector', 'timing', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'When a whole leadership pocket is under pressure, even quality components are more likely to see failed breakouts or poor continuation.'}
