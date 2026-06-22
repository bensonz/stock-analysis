# 每日研究报告 2026-06-22

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4098.01 | +0.18% |
| 深证成指 | 16077.20 | +0.29% |
| 创业板指 | 4284.03 | +0.74% |
| 科创50 | 1911.91 | +0.02% |

涨跌比: 1234涨 / 4245跌 / 5512总

**冷门板块**: 化妆品(-4.24%), 航天装备Ⅱ(-4.10%), 自动化设备(-4.00%), 酒店餐饮(-3.65%), 电机Ⅱ(-3.62%)

PANIC TAPE — breadth 0.29:1 (1234 up / 4245 down), 72跌停/88涨停. Indices superficially green (上证+0.18%, 深证+0.29%, 创业板+0.74%) but this is an index illusion: big-cap AI/semiconductor names holding up indices while 77% of stocks fall. f4_7=937 shows broad mid-cap damage. US-Iran negotiation whipsaw adding geopolitical uncertainty. IV data unavailable. No new positions — hard block.

## 策略池扫描

扫描 **63** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **融捷股份** (002192) (RPS 94.28%) — PANIC TAPE HARD BLOCK (breadth 0.29:1, f10=72). Would be top candidate otherwise: RPS120=94.28, all MA distances healthy (dist_ma5=-1.5%, dist_ma10=3.6%, dist_ma20=-0.7%), 碳酸锂+2250元/吨 catalyst, Q1 NP +1288%.
2. **思瑞浦** (688536) (RPS 93.71%) — PANIC TAPE HARD BLOCK. Additionally dist_ma10=8.3% exceeds chase rule (max 8%). RPS120=93.71, Q1 NP +577%, 12家机构覆盖, strong semiconductor sector alignment.
3. **芯源微** (688037) (RPS 94.05%) — PANIC TAPE HARD BLOCK. Additionally dist_ma10=9.8% exceeds chase rule. Semiconductor设备龙头, RPS120=94.05. Strong sector but overextended.
4. **华宏科技** (002645) (RPS 94.5%) — PANIC TAPE HARD BLOCK. Additionally dist_ma20=12.6% exceeds chase rule (max 12%). 稀土+环保设备, NP +595%, hitting all-time highs — too extended.
5. **华峰测控** (688200) (RPS 93.69%) — PANIC TAPE HARD BLOCK. Additionally dist_ma5=19.2% massively exceeds chase rule (max 6%). RPS120=93.69, semiconductor设备但严重超买。

## 今日研究结论

- 新开仓: 0只
- 跳过: 5只

### 新教训
- {'text': 'Index illusion: 上证+0.18%/深证+0.29%/创业板+0.74% all green, but breadth was 0.29:1 with 72 stocks at limit-down. This is a dangerous divergence where big-cap index stocks mask broad-based selling. The entry_regime hard_block (triggered by breadth <1.5:1 and f10>30) correctly prevented new positions into a rout.', 'type': 'signal', 'tags': ['entry-filter', 'market-regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When indices are green but breadth is severely negative, institutional money is consolidating into a few large-cap names while de-risking the rest. Opening new positions in this environment means buying into distribution in 77% of the market.'}
- {'text': 'The +10% mechanical stop-raise rule protected 恒铭达: stock peaked at +11.7% on 6/19, stop raised to breakeven ¥83.55. Today -4.48%, price now ¥86.45 — only 3.35% from stop. Without the mechanical raise, original stop at ¥79.37 would leave much more room for loss. The rule converts winners into low-risk holds without requiring a market call.', 'type': 'rule', 'tags': ['exit-rule', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'Mechanical stop-raise at +10% to breakeven creates an asymmetric payoff: if the stock continues higher, you participate fully; if it reverses, you exit at cost. This is especially valuable in weak-tape environments.'}
- {'text': "新宙邦's 宁德时代 30万吨/3年 contract catalyst is the strongest type in this market: revenue visibility locked through 2028 via a binding agreement with the industry giant. Stock +19.2% in 10 days. Contract-based catalysts (not earnings beats, not concepts) provide multi-month momentum because the revenue is contractually committed, not forecasted.", 'type': 'heuristic', 'tags': ['catalyst', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Binding revenue contracts eliminate the uncertainty that causes momentum stocks to gap down on earnings. The market can model minimum revenue floors, which attracts institutional accumulation over weeks/months rather than days.'}
- {'text': 'f10=72 while indices green is a structural warning of market bifurcation. When 72 stocks hit limit-down but the index is flat-to-up, it signals that money is fleeing broad market names into a narrow set of AI/semiconductor leaders. This narrow leadership is historically unsustainable — either breadth broadens (laggards catch up) or leaders get dragged down (risk-off contagion). Tight stops on all positions are essential.', 'type': 'signal', 'tags': ['market-regime', 'exit-rule'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Bifurcated markets concentrate risk: if the few leaders reverse, there are no offsetting gains from the broad market. This creates fat-tail risk for concentrated momentum portfolios. Mechanical stops are the only defense.'}
