# 每日研究报告 2026-05-28

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4087.86 | -0.14% |
| 深证成指 | 15695.48 | -0.26% |
| 创业板指 | 4054.21 | +0.21% |
| 科创50 | 1838.84 | +1.29% |

涨跌比: 2081涨 / 3286跌 / 5509总

**热门板块**: 玻璃玻纤(+5.63%), 非金属材料Ⅱ(+3.09%), 小金属(+2.68%), 电子化学品Ⅱ(+2.53%), 金属新材料(+2.14%)

**冷门板块**: 贵金属(-3.68%), 家电零部件Ⅱ(-3.38%), 电机Ⅱ(-3.00%), 小家电(-2.49%), 一般零售(-2.29%)

市场弱势：广度0.63:1偏空（2081涨/3286跌），仅创业板指+0.21%微涨，上证-0.14%、深证-0.26%收跌。科创50逆势+1.29%。涨停89家/跌停13家，非恐慌但买盘严重不足。材料板块轮动领涨（玻璃玻纤+5.63%、非金属材料+3.09%、小金属+2.68%），贵金属-3.68%领跌，消费/家电/零售全面走弱。IV分化：500ETF极低7.3%（自满），创业板ETF偏高52%。买入门槛不满足，维持100%现金。

## 策略池扫描

扫描 **57** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **芯碁微装** (688630) (RPS 93.75%) — BUY GATE FAILED: breadth 0.63:1 < 1.5:1, only 1/3 major indices green. Plus Rule 2b: dist_ma20=25.2% > 12%. Strongest fundamental candidate (score 9.3, 0 risks, AI PCB+先进封装 dual catalyst). Re-evaluate when breadth recovers AND price pulls back to MA10 (~273) or MA20 (~233).
2. **伟测科技** (688372) (RPS 93.79%) — BUY GATE FAILED. Rule 2b: dist_ma20=14.9% > 12%. IC封测 leader, strong institutional flow (北向3.9%+公募11%), Q3 net +226%. Revisit on pullback to MA20 ~149.
3. **华锡有色** (600301) (RPS 91.07%) — BUY GATE FAILED. Best sector alignment (小金属 #3 today) but RPS20=11.18% shows very weak short-term momentum — sector tailwind isn't reaching this stock. dist_ma OK. Monitor for RPS20 recovery + breadth normalization.
4. **山东赫达** (002810) (RPS 94.68%) — BUY GATE FAILED. VCP SETUP (ratio 0.72, above 0.4 sweet spot). Near MA20 support (dist_ma20=-0.8%). 化学制品 sector not in top 5 today. Monitor for VCP tightening and breadth recovery.
5. **华峰测控** (688200) (RPS 93.5%) — BUY GATE FAILED. 询价转让@388.98元 creating overhang (1% stake). dist_ma20=22.4% > 12% overextended. Recent -9.62% selloff on 5/21. Gross margin 74.3% impressive but the technical picture is damaged. Skip until transfer completes and price stabilizes.

## 今日研究结论

- 新开仓: 0只
- 跳过: 5只

### 新教训
- {'text': 'Weak breadth regime (0.63:1, 1/3 indices green) correctly triggers new_positions:[] — V2 minimum buy gate is doing its job. [h013] validated: strong breadth alone is not enough; weak breadth is a clear no-go.', 'type': 'heuristic', 'tags': ['entry-filter', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013'}
- {'text': 'Rule 2b MA-distance check blocked 6+ strong candidates today (芯碁微装 dist_ma20=25.2%, 伟测科技 14.9%, 联瑞新材 dist_ma5=11.0%, 明阳电路 dist_ma5=18.0%, 思瑞浦 dist_ma10=12.1%, 帝尔激光 dist_ma5=6.7%). [h027] strongly validated: hot sector does not override chase risk.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h027'}
- {'text': "Materials rotation (玻璃玻纤 +5.63%) is today's dominant theme but the best sector-aligned candidate (华锡有色, RPS20=11.18%) shows no short-term follow-through. Narrow sector leadership: top names carry the sector, laggards left behind. In weak breadth, sector tailwind alone is insufficient.", 'type': 'observation', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'mechanism': 'Sector breadth within hot sectors matters — check whether individual stocks are participating or just the sector ETF is rising.'}
- {'text': "Zero PREMIUM/QUALITY VCP stocks today out of 28 enriched candidates. Only 2 SETUP-level (山东赫达 0.72, 恩捷股份 0.80), both above the 0.4 backtest sweet spot. VCP edge is scarce — when it appears it's valuable, but most days won't have one. Don't force VCP-based decisions.", 'type': 'observation', 'tags': ['timing'], 'evidence_type': 'supporting'}
- {'text': "IV divergence persists: 500ETF IV Rank 7.3% (complacency) vs 创业板ETF 52.0% (elevated). When breadth recovers, 创业板 entries need tighter selectivity. [h017] context: low IV doesn't justify freezing but argues for normal sizing with discipline on chasing.", 'type': 'signal', 'tags': ['position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h017'}
