# 每日研究报告 2026-07-10

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4067.07 | +0.76% |
| 深证成指 | 15493.28 | +0.61% |
| 创业板指 | 3991.98 | -0.65% |
| 科创50 | 2176.82 | -0.41% |

涨跌比: 4314涨 / 1140跌 / 5521总

**热门板块**: 广告营销(+6.85%), 医疗服务(+5.94%), 生物制品(+5.10%), 电视广播Ⅱ(+4.77%), 航海装备Ⅱ(+4.56%)

**冷门板块**: 电子化学品Ⅱ(-3.11%), 电池(-2.13%), 橡胶(-1.65%), 证券Ⅱ(-0.75%), 半导体(-0.57%)

Broad rally with healthcare/media rotation leading. Breadth 3.78:1 bullish (4314 up/1140 down), 77涨停/2跌停, no panic. 上证 +0.76%, 深证 +0.61% green; 创业板 -0.65% lagging on tech weakness. Semiconductors correcting after +326% 1yr run — 费城半导体 -11.38% 2-day spillover. Capital rotating from overbought tech into healthcare (创新药政策利好), media, and defense. IV data unavailable — normal sizing.

## 策略池扫描

扫描 **62** 只策略池股票
(来源: cheesefortune_intersection)

## 今日开仓

### 1. 奥来德 (688378) — BUY/moderate

- **入场价**: ¥53.38
- **止损**: ¥50.71
- **目标**: ¥62.0
- **RPS120**: 93.31%
- **板块**: 光学光电子 (middle (was #1 sector 6/30, not in bottom 5 today))

OLED蒸发机龙头，H1净利预增492-604%(7/5公告)，光学光电子板块前期强势现回调至MA20支撑(+2.0%)，催化剂极新鲜，设备业务放量驱动

### 2. 宏达电子 (300726) — BUY/small

- **入场价**: ¥69.33
- **止损**: ¥65.86
- **目标**: ¥80.0
- **RPS120**: 92.19%
- **板块**: 军工电子Ⅱ (middle (was top 10 sector 6/30, not in bottom 5 today))

军工电子MLCC龙头，Q1净利+71%，RPS加速上行(RPS20 97.21%)，短期回调至均线下方提供低吸机会，但10日走弱(仅超3.8%个股)需警惕

## 跳过标的

1. **凯莱英** (002821) (RPS 88.03%) — Sector TOP 5 (医疗服务 +5.94%) but dist_ma20 +22.7% >12% → Rule 2b MA distance violation. Overextended, wait for pullback.
2. **荣昌生物** (688331) (RPS 85.45%) — Sector TOP 5 (生物制品 +5.10%) but dist_ma20 +15.3% >12% → Rule 2b MA distance violation.
3. **华天科技** (002185) (RPS 90.98%) — Sector 半导体 in BOTTOM 5 (-0.57%) → hard no-buy per h019. Also dist_ma5 +18.1%, dist_ma20 +30.4% massively overextended.
4. **京仪装备** (688652) (RPS 94.18%) — Sector 半导体 in BOTTOM 5 → hard no-buy per h019. dist_ma20 +35.5% extremely overextended.
5. **上海新阳** (300236) (RPS 93.33%) — Sector 电子化学品Ⅱ in BOTTOM 5 (-3.11%) → hard no-buy. dist_ma5 +9.7% >6%, dist_ma20 +16.9% >12% → multi-rule MA violation.
6. **博杰股份** (002975) (RPS 93.65%) — Robot concept but <1% revenue exposure. 增发 caused -8.29% selloff. Catalyst is thin. Technicals OK but no edge.
7. **恒逸石化** (000703) (RPS 94.28%) — RPS20 at 71.67% <75% → momentum fading below threshold. 跌停 6/29, high debt risk.
8. **山东赫达** (002810) (RPS 92.02%) — 跌停 7/8 on Q2 earnings miss, dist_ma5 -10.5%. Severe negative catalyst, no entry.
9. **多氟多** (002407) (RPS 91.31%) — 跌停 7/3, project delay announced, 5-day avg turnover 19% → volatile. Skip.
10. **欧陆通** (300870) (RPS 89.01%) — RPS20 at 71.69% <75% → momentum below threshold. 10-day relative strength only 1.8%.
11. **茂莱光学** (688502) (RPS 89.17%) — dist_ma10 +8.3% >8%, dist_ma20 +21.8% >12% → Rule 2b MA violation. PE 1829 extreme but valuation not primary filter.
12. **四方股份** (601126) (RPS 94.91%) — RPS20 84.05% decelerating sharply from RPS120 94.91%. Deep pullback below all MAs. Trend rolling over. H-share listing uncertain catalyst.
13. **扬杰科技** (300373) (RPS 92.51%) — Sector 半导体 in BOTTOM 5 → hard no-buy per h019. Despite涨价 catalyst, sector gravity wins.

## 今日研究结论

- 新开仓: 2只
- 跳过: 13只

### 新教训
- {'text': 'Semiconductor sector correction (费城半导体-11.38% in 2 days, A-shares -10%+ from peak) correctly triggers h019 hard-no-buy, eliminating 12/31 candidates. Rule working as designed.', 'type': 'rule', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Global semiconductor profit-taking after +326% 1yr run creates sector-wide gravity that overwhelms individual stock strength.'}
- {'text': 'Hot sector + MA violation = still no-buy. Both healthcare candidates (凯莱英, 荣昌生物) in TOP 5 sectors fail dist_ma20 >12%. h027 validated: MA discipline must hold even in hot sectors.', 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h027', 'mechanism': 'Mean-reversion risk from extreme MA extension (>12% above MA20) dominates sector tailwind in the short term (5-10 day horizon).'}
- {'text': "RPS trajectory divergence pattern identified: 宏达电子 RPS20(97.21) > RPS60(92.82) > RPS120(92.19) = accelerating, but 10-day relative strength only 3.8% = recent weakness. This pattern needs outcome tracking to determine if it's a normal pullback or reversal signal.", 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'mechanism': 'RPS measures cumulative relative return, so a stock that was very strong 20-60 days ago can still have high RPS20 even if the last 10 days are weak. This creates a lag effect that can mask emerging weakness.'}
- {'text': 'Pullback to MA20 + fresh earnings catalyst (>100% growth) may be a repeatable entry pattern. 奥来德 at dist_ma20 +2.0% with 5-day-old +500% beat mirrors best setups from V1 backtesting. Track 10-day forward return.', 'type': 'heuristic', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'mechanism': 'Fresh catalyst provides fundamental re-rating urgency while MA20 proximity provides technical support, creating an asymmetric risk/reward setup.'}
