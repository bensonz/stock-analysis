# 每日研究报告 2026-06-23

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4147.55 | -0.37% |
| 深证成指 | 16072.11 | -1.83% |
| 创业板指 | 4260.49 | -2.27% |
| 科创50 | 1940.65 | -0.42% |

涨跌比: 3386涨 / 2027跌 / 5516总

**热门板块**: 化学制药(+3.04%), 动物保健Ⅱ(+2.77%), 国有大型银行Ⅱ(+2.66%), 个护用品(+2.51%), 生物制品(+2.50%)

**冷门板块**: 贵金属(-7.86%), 工业金属(-6.39%), 能源金属(-5.35%), 元件(-5.23%), 小金属(-4.75%)

Risk-off rotation day. All 3 major indices red (上证-0.37%, 深证-1.83%, 创业板-2.27%). Breadth 1.67:1 decent but thin — most gains in r0_2 bucket. 104涨停/19跌停. Defensive sweep: pharma/bio/banks dominate top 5, metals/commodities crash in bottom 5. Buy gate FAILS (0/3 indices green) → no new positions. Portfolio: all 4 positions down, 1 in bottom-5 sector (元件). IV data unavailable. Cash is the right position today.

## 策略池扫描

扫描 **62** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **融捷股份** (002192) (RPS 94.28%) — Sector 能源金属 is bottom 5 (-5.35%). Hard skip per Rule 1. RPS120=94.28 and MA healthy would otherwise make this attractive.
2. **华宏科技** (002645) (RPS 94.5%) — dist_ma5_pct=6.1% > 6%. Rule 2b non-negotiable — chasing. Sector 环保设备 not in top performers.
3. **莱特光电** (688150) (RPS 94.62%) — dist_ma5_pct=8.0% > 6%, dist_ma10_pct=13.6% > 8%. Severely overextended. RPS120=94.62 in sweet spot but MA violations override.
4. **思瑞浦** (688536) (RPS 93.71%) — dist_ma10_pct=8.3% > 8%. Rule 2b triggered. Great fundamentals (NP+577%, 12家机构预测) but price too far from support.
5. **应流股份** (603308) (RPS 91.47%) — dist_ma5_pct=6.3% > 6%. Chasing. Also sector 通用设备 not in hot list. 13家机构预测+30% growth is strong but timing is wrong.
6. **兴瑞科技** (002937) (RPS 94.36%) — dist_ma10_pct=10.6% > 8%, dist_ma20_pct=15.5% > 12%. Extended. Sector 汽车零部件 not in top performers.
7. **电光科技** (002730) (RPS 92.77%) — dist_ma5_pct=6.4% > 6%. Overextended short-term. 定增14亿数据中心项目 is interesting catalyst but timing wrong.
8. **芯源微** (688037) (RPS 94.05%) — dist_ma10_pct=9.8% > 8%. Chasing. Semiconductor equipment sector strong but stock is extended.
9. **禾盛新材** (002290) (RPS 94.68%) — Passes RPS (94.68) and MA filters. Sector 家用电器 not in top 5. Buy gate fails (all 3 indices red). Top candidate when market turns.
10. **恒铭达** (002947) (RPS 93.87%) — Passes all filters: RPS=93.87, 0 risks, all MA distances negative (pullback zone). Best technical setup in pool. But buy gate fails. First to buy when market clears.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': "Sector gravity kills: 元件 went from hot to bottom-5 in a single rotation day, dragging 兴森科技 -8.07%. V2's Rule 1 (sector-first, cold sector = no entry) is validated again. Even a +23% winning position becomes vulnerable when its sector crashes.", 'type': 'observation', 'tags': ['sector', 'exit-rule'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Sector-level fund flows dominate individual stock fundamentals on rotation days. When institutional money rotates out of an entire sector (元件 today), even the strongest individual names get sold indiscriminately.'}
- {'text': 'Buy gate discipline prevented forced entries into a weak tape. All 3 major indices red + breadth only 1.67:1. The automated entry_regime said allow_new_positions=true, but actual index data contradicted it. Manual override of automated flags is correct when the tape tells a different story.', 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': "Index-level weakness signals institutional risk reduction even when breadth is technically positive. The '2 of 3 indices must be green' rule is a harder filter than pure breadth ratio and prevents buying into distribution."}
- {'text': 'MA-distance Rule 2b filtered 45 of 62 candidates (73%) today. Many visually compelling stocks (思瑞浦, 莱特光电, 芯源微) were eliminated purely on extension. This rule is doing heavy lifting in preventing chase entries during a weak tape.', 'type': 'observation', 'tags': ['entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'In a market where indices are declining, stocks extended above MA5/MA10 are prime targets for mean-reversion trades by algos and institutional sellers. The 6%/8%/12% thresholds act as a circuit breaker against buying into these reversion zones.'}
- {'text': 'Defensive sector sweep (pharma +4 stocks in top 5, banks #3, all commodities bottom 5) is a classic risk-off signal. When this pattern appears, existing momentum positions in tech/cyclical sectors should have stops tightened, not loosened.', 'type': 'signal', 'tags': ['sector', 'exit-rule'], 'evidence_type': 'supporting', 'mechanism': "Risk-off rotation from cyclicals to defensives precedes broader selloffs. The pattern of 'all hot sectors = defensive, all cold sectors = cyclical' is a leading indicator that institutional money is reducing risk exposure."}
