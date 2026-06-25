# 每日研究报告 2026-06-25

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4125.76 | +0.36% |
| 深证成指 | 16285.83 | +1.46% |
| 创业板指 | 4336.74 | +2.01% |
| 科创50 | 2072.50 | +4.18% |

涨跌比: 1155涨 / 4300跌 / 5512总

**热门板块**: 玻璃玻纤(+6.28%), 元件(+5.11%), 航空机场(+4.72%), 半导体(+4.09%), 证券Ⅱ(+3.55%)

**冷门板块**: 贵金属(-3.94%), 其他家电Ⅱ(-3.90%), 油气开采Ⅱ(-3.74%), 工业金属(-3.39%), 广告营销(-2.91%)

Façade rally: 上证+0.36%, 深证+1.46%, 创业板+2.01%, 科创50+4.18% — but breadth 0.27:1 (1155 up vs 4300 down), 51跌停. Large-cap semis mask broad distribution. Resources cratering (金-3.94%, 工业金属-3.39%). IV data unavailable across all proxies. Entry regime hard_block. Cash at 91.9%. HOLD all 3 positions, RAISE_STOP on 路维光电 to +10%.

## 策略池扫描

扫描 **59** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **恒铭达** (002947) (RPS 93.37%) — Cleanest MA setup in entire pool (dist_ma5=-1.6%, dist_ma10=0.7%, dist_ma20=-0.6%). RPS120=93.37% sweet spot. 0 risk factors. Score 8.2/7.7. BUT breadth 0.27:1 with f10=51 — entry regime hard_block. Top priority candidate when breadth improves.
2. **电光科技** (002730) (RPS 92.49%) — All MA distances negative (healthy pullback): dist_ma5=-3.8%, dist_ma10=-0.5%, dist_ma20=-4.7%. RPS120=92.49%. 数据中心定增14亿 catalyst. BUT breadth blocks. Monitor for entry when regime clears.
3. **思瑞浦** (688536) (RPS 93.8%) — 半导体 sector (#4 hot). RPS120=93.8%. Revenue +80%, net profit +228%, 12 analysts cover. BUT dist_ma10=11.7% > 8% MA rule violation + breadth block. Needs pullback to MA10.
4. **华丰科技** (688629) (RPS 90.62%) — dist_ma5=1.7%, dist_ma10=7.2% (acceptable). 历史新高. BUT 6/29解禁2.79亿股 (59.63% of float) is an impossible risk to ignore. Breadth also blocks.
5. **株冶集团** (600961) (RPS 91.21%) — 工业金属 sector bottom 4 (-3.39%). Sector gravity death sentence. dist_ma5=18.6% severely overextended. 9/8解禁29.93% also looming. Triple disqualification.
6. **欧科亿** (688308) (RPS 99.92%) — RPS120=99.92% > 95% chasing zone. dist_ma5=9%, dist_ma20=36.7%. Triple MA violation. No current price data available beyond enriched_candidates snapshot.

## 今日研究结论

- 新开仓: 0只
- 跳过: 6只

### 新教训
- {'text': 'Façade Rally pattern: 4 green indices + 0.27:1 breadth + 51跌停 = trap tape. Large-cap semis lifted 科创50 +4.18% while 78% of stocks declined. The entry regime hard_block is 100% correct — indices alone are insufficient to gauge buyability.', 'type': 'signal', 'tags': ['entry-filter', 'market-regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Index-weighted mega-caps (especially in 科创50) can mask broad distribution. Up/Down ratio and f10 count are better real-time breadth gauges than index color.'}
- {'text': '路维光电 consecutive 13-16× volume days (6/24: 15.82×, 6/25: 13.84×) on positive price action is the strongest institutional accumulation signal in portfolio history. This validates holding through weakness and letting winners run.', 'type': 'observation', 'tags': ['exit-rule', 'position-sizing'], 'evidence_type': 'supporting', 'mechanism': 'Extreme volume on consecutive up days in a narrow-thesis stock (掩膜版国产替代) with capacity expansion milestones suggests concentrated institutional positioning. Distribution would show high volume on down days.'}
- {'text': '24/26 enriched candidates fail V2 MA-distance thresholds (6%/8%/12%). Only 恒铭达 and 电光科技 pass all three. This validates that the anti-chase filter is working at scale — the market is in a momentum-driven phase where most stocks are overextended.', 'type': 'signal', 'tags': ['timing', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021, h027', 'mechanism': 'Late-stage sector momentum creates widespread MA extensions. The V2 thresholds function as an automatic cooling-off period, preventing entry at prices likely to mean-revert.'}
- {'text': "Resources/commodities rotation accelerating: 贵金属 -3.94%, 工业金属 -3.39%, 油气 -3.74%. Gold broke $4,000 for first time in 7 months. Our 0% commodity exposure is an accidental win from V2's sector-first approach.", 'type': 'observation', 'tags': ['sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h028', 'mechanism': 'USD strength + global recession fears driving commodity selloff. A-share resource stocks suffer dual pressure from global macro and domestic policy tightening.'}
