# 每日研究报告 2026-06-25

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4120.28 | +0.23% |
| 深证成指 | 16344.08 | +1.82% |
| 创业板指 | 4371.99 | +2.84% |
| 科创50 | 2066.33 | +3.87% |

涨跌比: 1231涨 / 4228跌 / 5512总

**热门板块**: 玻璃玻纤(+6.84%), 元件(+6.01%), 半导体(+4.53%), 航空机场(+4.27%), 非金属材料Ⅱ(+3.54%)

**冷门板块**: 油气开采Ⅱ(-5.38%), 贵金属(-4.24%), 工业金属(-3.95%), 其他家电Ⅱ(-3.81%), 广告营销(-3.13%)

Extreme bifurcation: 科创50 +3.87% masks breadth 0.29:1 (1231↑/4228↓) with 91跌停. Semiconductor ecosystem (半导体+4.53%, 元件+6.01%, 玻璃玻纤+6.84%) is the only pocket of life — driven by AI capex, 光刻胶断供, and electronic cloth supply crunch. Resources routed (油气-5.38%, 贵金属-4.24%, 工业金属-3.95%). All 3 positions are in the winning cluster and up +20%+. New entries HARD BLOCKED by panic regime. Portfolio 91.76% cash. IV data unavailable.

## 策略池扫描

扫描 **60** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **华灿光电** (300323) (RPS 93.43%) — HARD BLOCK: market regime panic (breadth 0.29:1, 91跌停). Would be STRONG BUY candidate otherwise: 光学光电子 top sector, RPS120=93.43 sweet spot, clean MAs (2.8/2.3/1.5), Q1 profit turnaround +152%, revenue +110%, LED芯片龙头, 京东方体系。Track for immediate entry when breadth normalizes above 1.5:1.
2. **恒铭达** (002947) (RPS 93.37%) — HARD BLOCK: market regime. Cleanest MA setup in entire candidate pool (dist_ma5=-1.6%, dist_ma10=0.7%, dist_ma20=-0.6%), 0 risk factors, RPS120=93.37, 消费电子 sector, 净利+31%, 4家机构预测增速>25%。Revisit immediately when buy gate reopens.
3. **思瑞浦** (688536) (RPS 93.8%) — HARD BLOCK: market regime + dist_ma10=11.7% exceeds 8% chase threshold. 半导体模拟芯片龙头, 净利+577%, 12家机构覆盖, 创24月新高. Wait for pullback to MA10 support + regime clearance.
4. **华丰科技** (688629) (RPS 90.62%) — HARD BLOCK: market regime + 6/29解禁2.79亿股(59.63% of float) creates massive overhang 4 trading days away. RPS120=90.62, clean MAs, 军工电子龙头, 净利+230%。Cannot enter ahead of a 60% unlock regardless of regime.
5. **睿创微纳** (688002) (RPS 90.2%) — HARD BLOCK: market regime + dist_ma10=12.6% chase violation. Score 9.3, 0 risks, 军工电子龙头, 净利+60%, 北向7.5%+公募21%. Strong candidate on pullback to MA10.
6. **芯源微** (688037) (RPS 94.53%) — HARD BLOCK: market regime + triple MA-distance violation (dist_ma5=15.6%, dist_ma10=23.9%, dist_ma20=24.5%). PE=952 with net losses,收益质量低(扣非仅占净利20%). Chasing extreme at any regime.
7. **株冶集团** (600961) (RPS 91.21%) — Double rejection: (1) sector 工业金属 in bottom 5 (-3.95%), hard no-buy zone; (2) dist_ma5=18.6%, dist_ma10=31.8% — extreme chase. RPS120=91.21 but sector gravity dominates.
8. **顺络电子** (002138) (RPS 89.67%) — HARD BLOCK: market regime. dist_ma20=32% extreme extension despite 元件 being #2 hot sector. 6/23 -9.99%跌停 signals fragility. TLVR/AI数据中心 thesis valid but timing impossible.

## 今日研究结论

- 新开仓: 0只
- 跳过: 8只

### 新教训
- {'text': "Index-green + breadth-red divergence is the most dangerous tape for new entries. Today: all 4 indices green (科创50 +3.87%) but breadth 0.29:1 with 91跌停. The multi-condition buy gate (breadth ≥1.5:1 AND f10<30) correctly prevented entries into what looked like a rally. This validates the V2 framework's insistence on breadth + limits checks beyond simple index direction.", 'type': 'signal', 'tags': ['entry-filter', 'regime', 'risk-management'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Mega-cap semiconductor/金融权重股 can lift indices mechanically while the median stock sells off. Breadth ratio captures the true underlying tape. Low breadth + high 跌停 = liquidity crisis beneath surface, where even good stocks get dragged down by forced selling.'}
- {'text': "Semiconductor ecosystem concentration is the portfolio's edge AND its risk. All 3 holdings (新宙邦/上海新阳/路维光电) are semiconductor-adjacent, which is why they're all +20%+ while the market bleeds. The sector-first framework correctly concentrated capital into the only pocket of strength. However, 91.76% cash is the necessary hedge — if semis reverse, rotate out fast.", 'type': 'observation', 'tags': ['sector', 'position-sizing', 'concentration'], 'evidence_type': 'supporting', 'related_hypothesis': 'h028', 'mechanism': "In a bifurcated market, concentration in the winning cluster beats diversification. Cash acts as the diversifier. The framework's 'hot sector or nothing' rule forced capital into the only place it could survive today's 0.29:1 tape."}
- {'text': 'VCP data continues to be absent from the enriched_candidates pipeline. All 60 strategy pool stocks show vcp_quality=null. VCP is currently a dead feature in the data feed — decisions must rely on MA distances and RPS alone until the VCP scanner is fixed. This does not break the framework but removes a proven edge (backtest shows +7.7% avg 10d return for PREMIUM VCP setups).', 'type': 'observation', 'tags': ['timing', 'data-quality'], 'evidence_type': 'supporting', 'mechanism': 'VCP scanner appears disconnected from the enrichment pipeline. Without contraction ratios and depth sequences, we lose the single strongest technical signal from backtesting.'}
