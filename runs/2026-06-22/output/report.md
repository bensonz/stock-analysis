# 每日研究报告 2026-06-22

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4163.10 | +1.78% |
| 深证成指 | 16372.50 | +2.13% |
| 创业板指 | 4359.39 | +2.52% |
| 科创50 | 1948.93 | +1.96% |

涨跌比: 2916涨 / 2468跌 / 5512总

**热门板块**: 小金属(+7.55%), 证券Ⅱ(+7.52%), 保险Ⅱ(+5.84%), 农化制品(+5.42%), 非金属材料Ⅱ(+5.37%)

**冷门板块**: 自动化设备(-2.36%), 化妆品(-2.29%), 照明设备Ⅱ(-2.26%), 航天装备Ⅱ(-1.84%), 汽车服务(-1.72%)

Bifurcated bull: all 3 major indices green (上证+1.78%, 深证+2.13%, 创业板+2.52%), 155涨停/34跌停. Breadth 1.18:1 below 1.5:1 entry minimum. f10=34 triggers panic-tape hard block on new positions. Rotation into 小金属 (+7.55%, 算力金属涨价: 钽+158%YTD) and 证券 (+7.52%). Battery/lithium chain surging (碳酸锂+2250元/吨). Portfolio all in mid-range tech subsectors, holding up well. 新宙邦 +20.55% triggers stop-raise. 恒铭达 time-stop SELL at +2.79%. IV data unavailable. Cash at 86.24% — dry powder intact for when regime clears.

## 策略池扫描

扫描 **61** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **融捷股份** (002192) (RPS 94.28%) — REGIME BLOCK — f10=34 triggers panic tape. Otherwise STRONG BUY candidate: RPS120=94.28 (extended zone, sector #1 exception applies), MA all healthy (dist_ma5=-1.5%, dist_ma10=3.6%, dist_ma20=-0.7%), catalyst: 碳酸锂+2250元/吨 today, sector 小金属 #1 at +7.55%. Would allocate 8-10% when regime clears.
2. **恩捷股份** (002812) (RPS 89.53%) — REGIME BLOCK. Solid setup: RPS120=89.53 sweet spot, MA all pass (dist_ma5=4.5%, dist_ma10=7.7%, dist_ma20=-0.5%), lithium battery separator leader, 储能签单180GWh tailwind. Sector 电池化学品, NP growth -125% but V2 ignores valuation for momentum.
3. **华灿光电** (300323) (RPS 93.26%) — REGIME BLOCK. MA healthy (all within 2.3% of MAs). RPS120=93.26 sweet spot. LED龙头, 光学光电子板块走高. But PE negative (-90), gross margin 6.13% — weak fundamentals limit conviction even when regime clears.
4. **华宏科技** (002645) (RPS 94.5%) — dist_ma5=6.1% exceeds Rule 2b 6% limit. dist_ma20=12.6% also borderline. RPS120=94.50 extended zone without sector cover (环保设备 not in top 5). NP +1428% but MA extension is non-negotiable per Rule 2b.
5. **思瑞浦** (688536) (RPS 93.71%) — dist_ma10=8.3% exceeds Rule 2b 8% limit. RPS120=93.71 extended without sector exception. Strong fundamentals (NP +577%, 12 analyst coverage) but timing is wrong. Wait for pullback to MA10 support.
6. **华丰科技** (688629) (RPS 90.53%) — 6/29解禁2.79亿股 (59.63% of total shares) — massive unlock in 7 trading days. MA distances pass but event risk overwhelms any technical setup. Hard pass regardless of regime.
7. **欧陆通** (300870) (RPS 89.1%) — dist_ma10=20.0%, dist_ma5=8.7% — extreme extension. Google GPU电源合作 is strong catalyst but buying at +20% above MA10 is chasing per Rule 2b. No current price data to confirm intraday movement.
8. **芯源微** (688037) (RPS 94.05%) — dist_ma10=9.8% exceeds Rule 2b 8% limit. Semiconductor equipment sector strong (中信证券: WFE +26% 2026) but price extended. Wait for pullback.

## 今日研究结论

- 新开仓: 0只
- 跳过: 8只

### 新教训
- {'text': "f10=34 panic-tape gate correctly blocks entries despite 3/3 green indices + 155 limit-ups. Bifurcated market where hot money chases metals/financials while 34 stocks crash. V1 would have entered on 'indices green' alone. V2 multi-condition gate (breadth 1.18:1 < 1.5:1 + f10≥30 + indices) is robust.", 'type': 'rule', 'tags': ['entry-filter', 'risk-management'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Limit-down stocks signal real distress even when headline indices are green; chasing strength during bifurcated tapes leads to adverse selection.'}
- {'text': '恒铭达 validates mechanical stop-raise + time-stop combination. Raised stop to breakeven at +10% (6/19 peak 93.33), stock cratered -8% in 2 sessions, time stop (10d <3% PnL) caught it before mechanical breach at 83.55. Converted potential loss into +2.79% gain.', 'type': 'signal', 'tags': ['exit-rule', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'Mechanical stop-raise at +10% locks in breakeven; time stop exits underperformers before they erode gains. Together they create an asymmetric payoff: small winners are cut quickly, big winners are protected.'}
- {'text': "新宙邦 +20.55% in 10 days validates V2 principle: catalyst quality (宁德时代30万吨3年协议) > valuation (PE=50). V1 would have downgraded for 'expensive'; V2 lets the revenue-lock catalyst compound. 30万吨 through 2028 = multi-year visibility, not a one-off beat.", 'type': 'heuristic', 'tags': ['sector', 'catalyst-analysis'], 'evidence_type': 'supporting', 'mechanism': 'Long-duration catalysts (3-year supply agreements) provide compounding momentum as each quarter of execution de-risks the forward revenue stream. Valuation is a trailing metric, irrelevant for forward momentum.'}
- {'text': "MA-distance Rule 2b filters ~70% of today's enriched_candidates. After multi-week tech rally, most names are extended. The few passing (融捷, 恩捷, 华灿) are compressing near support. When regime clears, these pullback-ready names are the targets.", 'type': 'observation', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h027', 'mechanism': 'Strong uptrends create extension; Rule 2b ensures we only enter on pullbacks to support, not at the top of momentum waves. This is anti-chasing discipline.'}
- {'text': 'Sector rotation from pure tech to resource+financial is accelerating (小金属 +7.55%, 证券 +7.52%). Next round of entries should include resource-linked names (融捷 in lithium, potentially 华宏 in rare earth) as rotation hedges. Current all-tech portfolio is concentrated.', 'type': 'observation', 'tags': ['sector', 'rotation'], 'evidence_type': 'supporting', 'related_hypothesis': 'h028', 'mechanism': 'AI infrastructure demand is flowing into upstream materials (tantalum, lithium, germanium) creating a commodity-linked second-order play on the AI theme. Resource stocks benefit from both AI demand and supply constraints.'}
