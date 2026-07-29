# 每日研究报告 2026-07-29

> 模型: deepseek-v4-pro（DeepSeek V4 Pro primary） · 310408+9358 tokens

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3793.18 | -0.53% |
| 深证成指 | 13452.05 | -0.43% |
| 创业板指 | 3311.32 | -0.47% |
| 科创50 | 1622.03 | -4.22% |

涨跌比: 3430涨 / 2001跌 / 5525总

**热门板块**: 教育(+4.67%), 休闲食品(+4.48%), 游戏Ⅱ(+4.03%), 非白酒(+3.67%), 饮料乳品(+3.35%)

**冷门板块**: 电子化学品Ⅱ(-5.99%), 半导体(-5.61%), 元件(-5.09%), 玻璃玻纤(-4.59%), 非金属材料Ⅱ(-4.24%)

Day 2 of global tech rout triggered by Meta announcing AI computing capacity sales. 科创50 -4.22% (cumulative -10.5% in 2 days), 创业板指 -0.47% (cumulative -7.8%). Breadth 1.71:1 misleadingly positive — 2,380 stocks barely up (r0_2), small-cap defensive rotation masking large-cap tech hemorrhage. IV extreme: avg rank 72%, 科创50 77.6%, 创业板 83.1% — panic zone. Consumer defensive sectors lead (教育 +4.67%, 休闲食品 +4.48%) but strategy pool has zero exposure. Buy gate FAILED (0/3 major indices green). Cash is the correct position.

## 策略池扫描

扫描 **50** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **国瓷材料** (300285) (RPS 98.35%) — Sector 电子化学品Ⅱ in bottom 5 (-5.99%) — hard no-buy per h019. MLCC catalyst irrelevant against sector gravity.
2. **华峰测控** (688200) (RPS 99.48%) — Sector 半导体 in bottom 5 (-5.61%). Score 9.0, 5 highlights, but sector gravity wins. dist_ma20 -19.1% — stock in freefall.
3. **星宸科技** (301536) (RPS 97.45%) — Sector 半导体 in bottom 5. RPS120 97.45% strong but sector is hard no-buy. dist_ma5 -8.5%.
4. **广合科技** (001389) (RPS 98.39%) — Sector 元件 in bottom 5 (-5.09%). PCB sell-off day. Plus 57.55% shares unlocking Apr 2027.
5. **中材科技** (002080) (RPS 94.55%) — Sector 玻璃玻纤 in bottom 5 (-4.59%). dist_ma20 -29.8% — extreme decline. Electronic cloth thesis intact but timing wrong.
6. **中远海特** (600428) (RPS 93.2%) — dist_ma20_pct +14.2% — FAILS Rule 2b (>12% hard cap). Strong shipping thesis but stock is overextended above MA20. Wait for pullback.
7. **恒逸石化** (000703) (RPS 97.06%) — Strongest catalyst in pool (H1 profit +2300%, 40 institutions surveyed, Brunei refinery moat). MA distances all clean. BUT buy gate failed (0/3 indices green), sector 石油石化 not top-30%. Top candidate to enter when gate reopens.
8. **养元饮品** (603156) (RPS 90.81%) — Only pool stock in top-5 sector (饮料乳品 +3.35%). MA distances clean. BUT buy gate failed. Consumer defensive, revenue declining -7.6% — watch for gate reopening.
9. **芯碁微装** (688630) (RPS 99.54%) — Score 9.1, 0 risks, semiconductor equipment leader. dist_ma20 -15.1% declining. Sector 专用设备 (mid-pack) but broader tech contagion. Wait for sector stabilization.
10. **斯迪克** (300806) (RPS 97.18%) — dist_ma20 -46.1% — stock in extreme freefall. MLCC theme doesn't matter when stock has collapsed 46% below MA20.

## 今日研究结论

- 新开仓: 0只
- 平仓: 0只
- 跳过: 10只

### 新教训
- {'text': 'Buy gate (2/3 major indices green) correctly prevented entries during day-2 tech rout. Automated regime checker said allow_new_positions=true but indices were all red. Always verify indices manually — breadth alone (1.71:1) is misleading when large-cap tech is bleeding.', 'type': 'rule', 'tags': ['entry-filter', 'risk-management'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Breadth can be positive even when major indices are negative if small-caps/defensive stocks are up. The 2/3 green index rule captures large-cap and sector-leadership quality that breadth misses.'}
- {'text': "Strategy pool has zero stocks in today's top 4 hot sectors (教育, 休闲食品, 游戏, 非白酒). Structural tech/manufacturing bias means we're correctly forced to cash when tech sells off. This is a feature, not a bug — momentum framework shouldn't chase sectors it doesn't understand.", 'type': 'observation', 'tags': ['sector', 'portfolio-construction'], 'evidence_type': 'supporting', 'mechanism': "The cheesefortune intersection pool is naturally concentrated in growth/tech/manufacturing. When those sectors lead, we outperform. When they don't, cash preserves capital for the next rotation."}
- {'text': 'Meta AI surplus panic is likely overreaction (capex still $125-145B, doubling YoY; multiple analysts confirm). Creates potential snap-back in semiconductor names but only after indices stop making new lows. Do not front-run.', 'type': 'signal', 'tags': ['timing', 'sector'], 'evidence_type': 'supporting', 'mechanism': 'Sentiment-driven selloffs in secular growth themes (AI infrastructure) historically mean-revert within 5-10 days. The key is waiting for confirmation (green indices, sector stabilization) rather than catching the falling knife.'}
- {'text': '恒逸石化 (000703) is the strongest dormant candidate: 2300% profit growth, 40 institutional surveys, EPS estimates revised +48%, MA distances all clean (dist_ma20 +4.5%), PE only 26.8x. Should be first entry when buy gate reopens.', 'type': 'heuristic', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'mechanism': 'The combination of massive earnings acceleration + institutional validation + clean technicals + reasonable valuation is rare. The only missing piece is market regime.'}
- {'text': 'h019 (bottom-list sectors = hard no-buy) saved us from analyzing 12 stocks in detail. V1 would have written 500+ words on each. V2 bins them in one line. Efficiency gain is massive and reduces FOMO.', 'type': 'heuristic', 'tags': ['entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Sector gravity explains 40-60% of individual stock returns in A-shares. Filtering by sector first eliminates most candidates before any detailed analysis, reducing cognitive load and FOMO-driven mistakes.'}
