# 每日研究报告 2026-05-01

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

Breadth 1.17:1 weak-to-fragile, only 1/3 major indices green, 98涨停/55跌停; 科创50 and semis are leading but the minimum buy gate fails and entry_regime is explicitly hard-blocked as panic. Hot sectors (top 5): 半导体 +4.71%, 综合Ⅱ +4.03%, 航天装备Ⅱ +3.88%, 家电零部件Ⅱ +2.90%, 风电设备 +2.63%. Cold sectors (bottom 5): 游戏Ⅱ -3.59%, 贸易Ⅱ -2.76%, 酒店餐饮 -2.65%, 燃气Ⅱ -2.60%, 玻璃玻纤 -2.46%. Position sector alignment: 0/0 positions in hot sectors. IV context: no usable IV data, so no IV-based sizing adjustment, but regime alone is enough to keep new_positions empty.

## 策略池扫描

扫描 **37** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **华峰测控** (688200) (RPS 90.95%) — Sector is hot and RPS120 90.95 is in the sweet spot, but entry regime hard-blocks new longs; additionally stock is in semiconductor equipment leadership and better bought only when breadth gate reopens.
2. **深科达** (688328) (RPS 90.76%) — RPS120 90.76 and MA distances are acceptable, but sector is not in provided top-5 list and entry regime is hard-blocked; no new positions under 1.17:1 breadth and only 1/3 major indices green.
3. **北化股份** (002246) (RPS 90.23%) — Good setup with RPS120 90.23, clean MA structure and Q1 profit growth, but sector is not confirmed in top sector list and market buy gate failed; skip rather than force a small buy.
4. **科达制造** (600499) (RPS 89.74%) — Catalyst is real and MA distances are healthy, but RPS120 89.74 is acceptable only if regime allows; current entry regime is hard-blocked.
5. **东材科技** (601208) (RPS 91.42%) — Fresh FR-4/PP price hike catalyst exists, but dist_ma10_pct 8.6 and dist_ma20_pct 11.3 breach the no-chasing threshold on MA10; also regime blocks new entries.
6. **芯源微** (688037) (RPS 86.43%) — Sector is hot and MA distances are fine, but RPS120 86.43 comes with conflicting earnings details in input and current regime is hard-blocked; no need to force entry in a panic tape.
7. **亚钾国际** (000893) (RPS 94.01%) — RPS120 94.01 is allowed, but stock is below MA5/MA10/MA20 after prior heavy selling risk and its sector is not in provided hot-sector list; not a sector-first long today.
8. **云图控股** (002539) (RPS 85.18%) — MA structure is acceptable and fertilizer catalyst exists, but RPS120 85.18 lacks confirmed sector leadership from the provided sector table and regime blocks fresh risk.
9. **华锡有色** (600301) (RPS 92.84%) — RPS120 92.84 is in the extended zone but sector leadership is not confirmed and same-day input shows both rebound and sharp weakness in the small-metals complex; not clean enough for a blocked tape.
10. **鄂尔多斯** (600295) (RPS 92.38%) — RPS120 92.38 and MA structure are fine, but sector is not in top provided sector list and catalyst is weaker than tech/material winners; sector-first rule keeps this as skip.
11. **广合科技** (001389) (RPS 90.99%) — Strong PCB growth story, but dist_ma10_pct 10.3 breaches the anti-chase rule; even without regime block this is too extended from support.
12. **莱特光电** (688150) (RPS 93.31%) — RPS120 93.31 is acceptable under extended-zone logic, but dist_ma10_pct 11.5 and dist_ma20_pct 21.7 clearly violate no-chasing rules.
13. **上海新阳** (300236) (RPS 88.95%) — Sector is supportive and earnings growth is strong, but dist_ma5_pct 9.3 and dist_ma10_pct 11.7 violate anti-chase thresholds. Skip extended setups.
14. **明阳电路** (300739) (RPS 90.54%) — RPS120 90.54 is fine, but dist_ma5_pct 13.5 and dist_ma10_pct 14.6 are extreme extensions. Non-negotiable chase filter says no.

## 今日研究结论

- 新开仓: 0只
- 跳过: 14只

### 新教训
- {'text': 'When a leadership pocket exists (科创50 +5.19%, 半导体 +4.71%) but the broad-entry gate fails, the correct move is still cash; isolated strength does not override tape risk.', 'type': 'rule', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum entries work best when sector leadership and market breadth confirm each other. Without breadth confirmation, follow-through odds drop and gap risk rises.'}
- {'text': 'The MA-distance anti-chase filter removed several attractive names today, especially 东材科技、广合科技、莱特光电、上海新阳、明阳电路; this rule is preventing emotional buying into stretched winners.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Even in strong sectors, excessive distance from MA5/MA10/MA20 increases mean-reversion risk and worsens stop placement.'}
- {'text': 'Among non-extended candidates, 华峰测控、北化股份、科达制造 had the cleanest technical structures, so they should remain top-of-list for recheck once breadth improves.', 'type': 'observation', 'tags': ['sector', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'Preserving a ready list of technically valid names allows fast deployment when the regime flips from blocked to open.'}
- {'text': 'Fresh price/supply catalysts remain powerful in materials and PCB chain: FR-4/PP price hikes support 东材科技, while lithium pricing and Q1 acceleration support 科达制造, but catalyst quality cannot override regime and extension rules.', 'type': 'heuristic', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'Catalysts drive relative strength, but entry quality still depends on market regime and distance from support.'}
