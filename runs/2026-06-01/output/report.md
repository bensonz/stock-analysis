# 每日研究报告 2026-06-01

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4063.72 | -0.12% |
| 深证成指 | 15481.10 | -0.60% |
| 创业板指 | 4001.52 | -0.90% |
| 科创50 | 1694.60 | -3.24% |

涨跌比: 3875涨 / 1571跌 / 5511总

**热门板块**: 数字媒体(+5.01%), 广告营销(+4.68%), 煤炭开采(+4.38%), 游戏Ⅱ(+3.18%), 燃气Ⅱ(+3.13%)

**冷门板块**: 玻璃玻纤(-6.36%), 元件(-3.52%), 半导体(-3.24%), 通信设备(-2.18%), 照明设备Ⅱ(-2.00%)

Buy gate FAILED: 0/3 major indices green (上证 -0.12%, 深证 -0.60%, 创业板 -0.90%). Breadth 2.47:1 superficially healthy but 科创50 -3.24% reveals heavy tech distribution. Major sector rotation underway: semiconductor/component/comms equipment in bottom 5, media/coal/gas surging. IV mixed — 500ETF IV Rank 7.5% (extreme complacency), 创业板 53.5% (elevated). No new positions. 100% cash.

## 策略池扫描

扫描 **57** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **华峰测控** (688200) (RPS 94.01%) — 半导体 sector in bottom 3 of all sectors (-3.24%). Sector gravity block — no entry regardless of stock quality.
2. **伟测科技** (688372) (RPS 93.41%) — 半导体 sector in bottom 3. Also has 今日解禁32.37万股 event.
3. **江丰电子** (300666) (RPS 93.1%) — 半导体 sector in bottom 3. Hard sector block.
4. **芯源微** (688037) (RPS 92.45%) — 半导体 sector in bottom 3. Also revenue -10.35% YoY, net profit deeply negative.
5. **思瑞浦** (688536) (RPS 91.34%) — 半导体 sector in bottom 3. Despite strong fundamentals (净利+577%), sector gravity wins.
6. **兴森科技** (002436) (RPS 88.07%) — 元件 sector in bottom 2 (-3.52%) + dist_ma10 9.5% exceeds 8% chase limit. Double kill.
7. **芯碁微装** (688630) (RPS 94.52%) — dist_ma5 +11.1% >6%, dist_ma10 +18.4% >8%, dist_ma20 +38.6% >12%. All three MA-distance limits breached. Extremely overextended.
8. **联瑞新材** (688300) (RPS 94.5%) — dist_ma20 +62.7% — most extreme overextension in entire pool. All MA limits breached by huge margins.
9. **国瓷材料** (300285) (RPS 93.33%) — dist_ma5 +6.8% >6% chase limit. Also dist_ma20 +36.4% extreme.
10. **卓易信息** (688258) (RPS 93.28%) — dist_ma5 +7.1% >6% chase limit. Also management selling (核心技术人员减持 in May).
11. **华锡有色** (600301) (RPS 91.19%) — dist_ma5 +6.8% >6%, dist_ma10 +7.3% approaching 8% limit.
12. **华宏科技** (002645) (RPS 92.43%) — dist_ma20 +15.3% >12% limit. Also 大股东质押100% — extreme risk.
13. **石大胜华** (603026) (RPS 94.87%) — 电池 sector not in confirmed top 30%. PE 65 with negative net profit. Revenue growth only +11%, gross margin 4.5% — weak fundamentals for a momentum play.
14. **山东赫达** (002810) (RPS 94.4%) — 化学制品 sector not in confirmed top 30%. VCP SETUP only (contraction ratio 0.72 — too loose). Would reconsider if sector rank improves.
15. **大金重工** (002487) (RPS 89.53%) — 风电设备 sector not in confirmed top 30%. Best fundamentals in pool (score 9.2, 0 risks) but sector rank unclear. On watch for when sector data confirms top 30%.

## 今日研究结论

- 新开仓: 0只
- 跳过: 15只

### 新教训
- {'text': 'Buy gate discipline prevented forced entries on a day when 0/3 major indices are green despite decent 2.47:1 breadth. The index-level signal correctly flagged the rotation risk. Supporting evidence: 科创50 -3.24%, semiconductor/component/comms equipment sectors all in bottom 5.', 'type': 'rule', 'tags': ['entry-filter', 'regime-detection'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Breadth can be misleadingly positive when small-cap retail stocks rise while institutional money rotates out of large-cap growth leaders. Index-level confirmation catches this divergence.'}
- {'text': 'MA-distance Rule 2b is the single most effective filter today — it eliminated 芯碁微装 (dist_ma20 +38.6%), 联瑞新材 (+62.7%), and 6+ other candidates that would otherwise look attractive on RPS alone. These are the stocks most likely to mean-revert violently.', 'type': 'heuristic', 'tags': ['entry-filter', 'risk-management'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021, h027', 'mechanism': 'Stocks that have run +20-60% above their 20-day moving average have exhausted short-term buyers. The next marginal trade is overwhelmingly likely to be profit-taking, not new entries.'}
- {'text': 'The strategy pool (Cheesefortune intersection) has ~40% concentration in 半导体/电子 sectors. When these sectors rotate out (like today), the pool produces almost zero viable candidates. V3 should expand sector coverage to include media, commodities, and defensive sectors.', 'type': 'observation', 'tags': ['sector', 'strategy-design'], 'evidence_type': 'supporting', 'mechanism': 'Sector concentration risk in the sourcing pool creates a structural bias — when the dominant sector falls out of favor, the entire candidate pipeline goes dry simultaneously.'}
- {'text': "Semiconductor sector appearing in bottom 5 with 科创50 -3.24% suggests institutional distribution, not retail panic (f10 only 19). This is a 'quiet rotation' — the kind that doesn't trigger panic signals but causes sustained underperformance. Sell-side rotation, not buy-side panic.", 'type': 'signal', 'tags': ['sector', 'regime-detection'], 'evidence_type': 'supporting', 'related_hypothesis': 'h028', 'mechanism': 'Low f10 + high sector drawdown = institutions quietly reallocating, not retail dumping. These rotations tend to persist for weeks, not days.'}
