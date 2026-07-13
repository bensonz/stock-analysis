# 每日研究报告 2026-07-13

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3934.74 | -1.54% |
| 深证成指 | 14654.49 | -2.61% |
| 创业板指 | 3751.33 | -2.38% |
| 科创50 | 2026.96 | -1.84% |

涨跌比: 891涨 / 4574跌 / 5524总

**热门板块**: 中药Ⅱ(+2.98%), 航天装备Ⅱ(+2.24%), 国有大型银行Ⅱ(+2.17%), 城商行Ⅱ(+2.14%), 油气开采Ⅱ(+1.97%)

**冷门板块**: 其他电子Ⅱ(-9.63%), 玻璃玻纤(-7.52%), 地面兵装Ⅱ(-7.11%), 军工电子Ⅱ(-6.24%), 影视院线(-6.21%)

PANIC TAPE — breadth 0.19:1 (891 up, 4574 down), 53跌停 vs 28涨停. All 3 major indices red (上证 -1.54%, 深证 -2.61%, 创业板 -2.38%). Tech/AI leading collapse, defensive rotation into 中药(+2.98%) and 银行(+2.17%). IV data unavailable. New positions hard-blocked. Only position 宏达电子 being sold at -11.44% loss after all stops triggered. Cash 97.5% is the right allocation.

## 策略池扫描

扫描 **64** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **京仪装备** (688652) (RPS 94.56%) — Panic tape hard block. Secondary: dist_ma20_pct=19.5%, wildly overextended above MA20 support even if tape were good.
2. **茂莱光学** (688502) (RPS 89.84%) — Panic tape hard block. Secondary: dist_ma20_pct=14.4% (>12% rule breached), PE=1739 extreme valuation.
3. **凯莱英** (002821) (RPS 89.16%) — Panic tape hard block. Secondary: dist_ma20_pct=18.1% (>12% rule breached). Otherwise interesting — medical CDMO in hot-adjacent 医药生物 sector, RPS120=89.16%, dist_ma5=2.1% tight. Revisit when tape improves and MA20 gap closes.
4. **上海新阳** (300236) (RPS 93.85%) — Panic tape hard block. Secondary: RPS120=93.85% sweet spot, dist_ma5=0.0% perfectly tight to MA5, but 电子化学品Ⅱ sector getting crushed in broad tech selloff. Top candidate to revisit when tape stabilizes.
5. **伟测科技** (688372) (RPS 91.43%) — Panic tape hard block. Secondary: dist_ma20=9.4% acceptable, dist_ma5=0.0% tight, but 半导体 sector leading today's selloff.
6. **四方股份** (601126) (RPS 94.46%) — Panic tape hard block. Secondary: RPS120=94.46% borderline extended, dist_ma5=-7.8% in pullback but dist_ma20=-20.0% very broken. Stock in clear downtrend.
7. **宏达电子** (300726) (RPS 91.85%) — Being SELL executed today. Sector 军工电子Ⅱ in bottom 5, -11.44% in 3 days, all stops triggered.

## 今日研究结论

- 新开仓: 0只
- 跳过: 7只

### 新教训
- {'text': 'Sector gravity is absolute: 宏达电子 was entered in 军工电子Ⅱ which was already in a verified multi-day downtrend (07-02 -6.16%, 07-03 -5.06%, 07-07 -3.99% before our 07-10 entry). The MLCC龙头 thesis was irrelevant — sector crushed it for -11.44% in 3 days. Never enter a stock when its sector is in a confirmed downtrend, regardless of individual fundamentals.', 'type': 'rule', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Sector fund flows dominate individual stock narratives. When institutional money exits a sector, even the strongest individual names get dragged down by forced selling and deteriorating sentiment.'}
- {'text': "Entry regime hard block prevented disaster: breadth 0.19:1 correctly blocked all new positions. V1 would have forced a 'SMALL BUY' and compounded losses. Cash is a position — and today it's the best one. The regime system is V2's single most valuable feature.", 'type': 'signal', 'tags': ['entry-filter', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When breadth is below 0.2:1 and all major indices are red, the probability of any individual long working is near zero. The regime gate converts a discretionary dilemma into a mechanical rule.'}
- {'text': 'Weekend gap risk is especially dangerous for stocks already showing weakness. 宏达电子 closed Friday at 67.45, opened Monday at 67.62, then collapsed to 61.40 — gapping cleanly through the 65.86 stop with no chance to exit. For positions that are already -2.7% on day 0 with a deteriorating sector, consider proactive Friday exit rather than holding through weekend uncertainty.', 'type': 'heuristic', 'tags': ['exit-rule', 'timing'], 'evidence_type': 'supporting', 'mechanism': '周五效应: weak stocks held through weekends face 2.5 days of news risk with no ability to trade. If a position is already showing stress on Friday, the asymmetric risk (small chance of bounce vs large chance of gap-down) favors exit.'}
- {'text': 'Defense sector rotation is bifurcated: 航天装备 (+2.24%) and 军工电子 (-6.24%) diverged sharply. The market rewarded commercial space (rocket recovery catalyst) while punishing component suppliers. Not all sub-sectors within a theme move together — need to verify the specific sub-sector trend, not just the broad industry.', 'type': 'observation', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'mechanism': 'Catalysts flow unevenly within industry groups. 长征十号乙 success directly benefits 航天装备 while 军工电子 components face different demand drivers and de-rating pressures.'}
