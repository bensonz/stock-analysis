# 每日研究报告 2026-05-05

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4112.16 | +0.11% |
| 深证成指 | 15107.55 | -0.09% |
| 创业板指 | 3677.15 | -0.27% |
| 科创50 | 1571.07 | +5.19% |

涨跌比: 2878涨 / 2461跌 / 5462总

**热门板块**: 半导体(+4.71%), 综合Ⅱ(+4.03%), 航天装备Ⅱ(+3.88%), 家电零部件Ⅱ(+2.90%), 风电设备(+2.63%)

**冷门板块**: 游戏Ⅱ(-3.59%), 贸易Ⅱ(-2.76%), 酒店餐饮(-2.65%), 燃气Ⅱ(-2.60%), 玻璃玻纤(-2.46%)

Breadth 1.17:1 fragile, 98涨停/55跌停, only 上证指数 green while 深成指/创业板指 are red; this fails the minimum long-entry gate and matches the system hard block on new longs. Hot sectors (top 5): 半导体 +4.71%, 综合Ⅱ +4.03%, 航天装备Ⅱ +3.88%, 家电零部件Ⅱ +2.90%, 风电设备 +2.63%. Cold sectors (bottom 5): 游戏Ⅱ -3.59%, 贸易Ⅱ -2.76%, 酒店餐饮 -2.65%, 燃气Ⅱ -2.60%, 玻璃玻纤 -2.46%. Position sector alignment: 0/0 positions in hot sectors. Research check suggests semiconductor/科创50 strength is driving the tape, with wind equipment also supported by installation expectations, but the market is too internally messy for fresh momentum risk. IV context is unavailable, so no stock-level IV throttle can be applied.

## 策略池扫描

扫描 **47** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **莱特光电** (688150) (RPS 94.69%) — Sector is favorable, but entry blocked: dist_ma10_pct 10.3% and dist_ma20_pct 22.5% both violate anti-chase limits.
2. **明阳电路** (300739) (RPS 90.65%) — MA distances are acceptable and RPS fits, but no new positions allowed because entry regime is hard-blocked: breadth 1.17:1, only 1 of 3 major indices green, 55跌停.
3. **北化股份** (002246) (RPS 87.81%) — RPS and MA positioning are acceptable, with VCP SETUP near MA support, but sector is not confirmed among today’s top leadership and regime hard-block blocks fresh longs.
4. **云图控股** (002539) (RPS 87.72%) — Price structure is controlled and RPS is acceptable, but sector is not in provided top leadership list and market regime blocks new entries.
5. **科达制造** (600499) (RPS 91.17%) — Good earnings catalyst and acceptable MA stretch, but dist_ma20_pct 12.5% exceeds the 12% ceiling; also regime blocks new entries.
6. **鄂尔多斯** (600295) (RPS 92.35%) — MA distances are fine, but sector is not in top leadership and stock lacks stronger momentum edge versus better tech leaders.
7. **亚钾国际** (000893) (RPS 93.34%) — Current price is below MA5/MA10/MA20 with weakening structure; not the kind of strength to buy in a blocked tape.
8. **华锡有色** (600301) (RPS 92.93%) — Setup is near moving averages, but RPS120 92.93 is only acceptable with stronger sector leadership; small-metals leadership is not confirmed in provided sector ranks.
9. **华峰测控** (688200) (RPS 91.25%) — Excellent sector and earnings trend, but dist_ma5_pct 9.3%, dist_ma10_pct 16.5%, dist_ma20_pct 23.9% all fail anti-chase rules.
10. **东材科技** (601208) (RPS 92.17%) — Fresh price-raise catalyst is interesting, but dist_ma10_pct 13.0% and dist_ma20_pct 19.6% fail anti-chase limits.
11. **广合科技** (001389) (RPS 92.58%) — Strong AI/PCB growth story, but dist_ma5_pct 13.5%, dist_ma10_pct 27.9%, dist_ma20_pct 34.9% indicate severe extension.
12. **上海新阳** (300236) (RPS 88.86%) — Semiconductor-adjacent sector is hot, but dist_ma5_pct 9.4%, dist_ma10_pct 18.7%, dist_ma20_pct 19.0% all violate anti-chase rules.
13. **芯源微** (688037) (RPS 88.89%) — Hot semiconductor sector and fresh catalyst, but rps120 88.89 with dist_ma5_pct 14.6%, dist_ma10_pct 21.3%, dist_ma20_pct 29.7% is too extended to chase.
14. **鼎通科技** (688668) (RPS 90.11%) — Strong catalyst and institutional flow, but dist_ma5_pct 16.4%, dist_ma10_pct 37.0%, dist_ma20_pct 45.4% are extreme extension.
15. **洁美科技** (002859) (RPS 86.35%) — Trend is good, but dist_ma5_pct 11.0%, dist_ma10_pct 17.2%, dist_ma20_pct 19.4% fail anti-chase limits.
16. **咸亨国际** (605056) (RPS 94.5%) — Price sits below MA5 and MA10, showing loss of short-term thrust; not the right tape to bottom-fish.

## 今日研究结论

- 新开仓: 0只
- 跳过: 16只

### 新教训
- {'text': 'A split tape with a very strong 科创50 and semiconductor surge can still be a no-entry day when the broad buy gate fails.', 'type': 'rule', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Index-level leadership concentrated in one risk cluster does not offset weak breadth, only 1/3 major indices green, and elevated limit-down count; momentum entries need both leadership and healthy participation.'}
- {'text': 'The MA-distance anti-chase rule is excluding many of the strongest-looking names in semis, PCB and communication hardware today, which is exactly its job.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Names like 华峰测控、东材科技、广合科技、上海新阳、鼎通科技 all have valid narratives but are stretched too far above short-term support, making reward/risk poor for fresh entries.'}
- {'text': 'Best blocked candidates today are the ones with acceptable MA distance first, not the ones with the strongest headline momentum.', 'type': 'heuristic', 'tags': ['entry-filter', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'In a weak regime, preserving a shortlist of technically non-extended names like 明阳电路、北化股份、云图控股 is more useful than reacting to already vertical leaders.'}
