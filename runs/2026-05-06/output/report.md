# 每日研究报告 2026-05-06

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4158.09 | +1.12% |
| 深证成指 | 15458.77 | +2.32% |
| 创业板指 | 3780.34 | +2.81% |
| 科创50 | 1661.53 | +5.76% |

涨跌比: 3752涨 / 1620跌 / 5492总

**热门板块**: 玻璃玻纤(+7.33%), 半导体(+5.42%), 其他电子Ⅱ(+5.12%), 贵金属(+5.11%), 综合Ⅱ(+4.92%)

**冷门板块**: 油气开采Ⅱ(-4.27%), 油服工程(-3.95%), 酒店餐饮(-3.65%), 旅游及景区(-2.24%), 教育(-2.14%)

Breadth 2.32:1 bullish on the surface, 3/3 major indices green and 115涨停, but 63跌停 keeps the tape unstable enough for the system's hard block on new longs. Hot sectors (top 5): 玻璃玻纤 +7.33%, 半导体 +5.42%, 其他电子Ⅱ +5.12%, 贵金属 +5.11%, 综合Ⅱ +4.92%. Cold sectors (bottom 5): 油气开采Ⅱ -4.27%, 油服工程 -3.95%, 酒店餐饮 -3.65%, 旅游及景区 -2.24%, 教育 -2.14%. Position sector alignment: 0/0 positions in hot sectors. IV context remains complacent-to-low overall, with several main-board proxies below 15% IV Rank and 科创/创业板 only neutral-low, so fresh risk should be selective even without the regime block.

## 策略池扫描

扫描 **53** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **福晶科技** (002222) (RPS 91.88%) — Sector hot and earnings catalyst real, but fails anti-chase rule: dist_ma5_pct 7.5% > 6% and dist_ma20_pct 16.3% > 12%; entry regime also hard-blocks new longs
2. **科达制造** (600499) (RPS 90.95%) — RPS120 90.95 and catalyst are acceptable, but sector is not in provided top 5 and entry regime is hard-blocked; additionally dist_ma20_pct 14.5% > 12%
3. **亚钾国际** (000893) (RPS 92.55%) — Good MA setup and earnings catalyst, but sector is not in provided top 5 and current regime blocks new entries; only top-sector names qualify for buys
4. **云图控股** (002539) (RPS 87.64%) — VCP only SETUP and RPS120 87.64 is acceptable, but sector is not in provided top 5 and entry regime hard-blocks all new longs
5. **咸亨国际** (605056) (RPS 93.83%) — MA distances are healthy, but sector is not in provided top 5, recent event flow shows price weakness, and stock IV proxy says half sizing; regime still blocks entries
6. **明阳电路** (300739) (RPS 90.53%) — Technically not overextended, but sector is not in provided top 5 and recent event notes 10-day relative weakness; regime blocks entries
7. **莱特光电** (688150) (RPS 94.64%) — Electronic materials trend is strong and catalyst is real, but fails anti-chase rule with dist_ma20_pct 20.3% > 12%; regime also blocks new longs
8. **东材科技** (601208) (RPS 92.31%) — Fresh price/catalyst story from覆铜板涨价 and Q1 growth, but fails anti-chase rule: dist_ma5_pct 7.8% > 6%, dist_ma10_pct 15.8% > 8%, dist_ma20_pct 25.0% > 12%
9. **华峰测控** (688200) (RPS 90.87%) — Semiconductor sector is hot and fundamentals are strong, but fails anti-chase rule with dist_ma5_pct 6.5% > 6%, dist_ma10_pct 14.1% > 8%, dist_ma20_pct 22.4% > 12%
10. **上海新阳** (300236) (RPS 88.03%) — Sector tailwind exists, but anti-chase rule fails: dist_ma5_pct 7.0% > 6%, dist_ma10_pct 18.4% > 8%, dist_ma20_pct 21.0% > 12%
11. **鼎通科技** (688668) (RPS 91.28%) — Fresh earnings and institutional flow are strong, but stock is far too extended: dist_ma5_pct 9.6%, dist_ma10_pct 30.0%, dist_ma20_pct 41.7%; no chasing
12. **广合科技** (001389) (RPS 93.18%) — PCB catalyst and growth are strong, but RPS120 93.18 is in extended zone and MA distance is extreme: dist_ma5_pct 17.1%, dist_ma10_pct 32.7%, dist_ma20_pct 44.2%
13. **富创精密** (688409) (RPS 91.01%) — Semiconductor sector is hot and profit growth is explosive, but RPS120 91.01 is invalidated by anti-chase rule: dist_ma5_pct 9.6%, dist_ma10_pct 25.0%, dist_ma20_pct 34.3%
14. **海伦哲** (300201) (RPS 97.63%) — Only candidate in sweet-spot MA range with acceptable RPS120 97.63? No—RPS is above 95 and therefore skip; sector leadership also not confirmed in provided top 5

## 今日研究结论

- 新开仓: 0只
- 跳过: 14只

### 新教训
- {'text': 'Today confirms h021 again: even on a strong index day, the MA-distance anti-chase rule eliminates most apparent leaders and prevents buying late-stage extensions.', 'type': 'rule', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Broad rallies pull many stocks far above MA5/MA10/MA20 at once; buying those names increases mean-reversion risk just when crowd enthusiasm peaks.'}
- {'text': 'A bullish tape with 115涨停 can still be unbuyable when 63跌停 coexist; the market is strong but internally violent, so breadth alone should not override the hard regime block.', 'type': 'signal', 'tags': ['timing', 'entry-filter', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'High limit-up count signals opportunity, but elevated limit-down count signals unstable participation and poor entry quality for fresh momentum trades.'}
- {'text': 'The best-looking candidates today are concentrated in hot tech sectors, but almost all fail because extension is more dangerous than missing the first leg.', 'type': 'observation', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'When sector momentum becomes obvious, many names gap too far from support; waiting for MA5/MA10 resets preserves asymmetric entries.'}
- {'text': 'Low-IV conditions in several main-board proxies argue for smaller or zero deployment even when trend is positive; no need to force exposure when both regime and extension filters say no.', 'type': 'heuristic', 'tags': ['position-sizing', 'timing', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h017', 'mechanism': 'Compressed implied volatility often coincides with market complacency; if setup quality is not elite, expected reward-to-risk deteriorates.'}
