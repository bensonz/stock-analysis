# 每日研究报告 2026-05-07

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4177.81 | +0.42% |
| 深证成指 | 15645.34 | +1.20% |
| 创业板指 | 3837.48 | +1.57% |
| 科创50 | 1680.62 | +1.43% |

涨跌比: 3474涨 / 1873跌 / 5494总

**热门板块**: 自动化设备(+5.15%), 通信设备(+5.00%), 元件(+4.58%), 广告营销(+4.52%), 环保设备Ⅱ(+4.03%)

**冷门板块**: 煤炭开采(-4.87%), 油气开采Ⅱ(-4.65%), 炼化及贸易(-4.44%), 焦炭Ⅱ(-3.89%), 油服工程(-3.39%)

Breadth 1.85:1 bullish on the surface, 120涨停/57跌停 shows a split and unstable tape; all major indices are green, with 自动化设备/通信设备/元件 leading and coal/oil complex hit hard. IV is mostly low-to-neutral (overall sentiment 偏乐观, avg IV rank 20.6%), so vol is not restrictive by itself, but the regime engine hard-blocks new longs because this qualifies as panic/fragile internals. Result: stay 100% cash despite several decent candidates.

## 策略池扫描

扫描 **54** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **国电南自** (600268) (RPS 90.49%) — Best-looking setup among candidates in a hot sector (电网设备) with RPS120 90.49 and clean MA distances, but entry regime hard-blocks all new longs: 57跌停 and entry_regime.allow_new_positions=false.
2. **科达制造** (600499) (RPS 90.95%) — RPS120 90.95 and MA distances are acceptable, but sector is 专用设备 rather than a listed top sector today, and market regime is hard-blocked for new entries.
3. **云图控股** (002539) (RPS 87.64%) — VCP exists but only SETUP quality with contraction ratio 0.76, not the high-quality tightening preferred; also 农化制品 is not in today's top sector list, and new longs are blocked by regime.
4. **明阳电路** (300739) (RPS 90.53%) — Sector 元件 is hot and MA distances are acceptable, but 10-day event text says price strength only beat 4.8% of the market over the last 10 trading days, showing weak short-term thrust despite RPS120 90.53.
5. **海伦哲** (300201) (RPS 97.63%) — MA distances are clean, but RPS120 97.63 is above the 95% chasing cutoff.
6. **福晶科技** (002222) (RPS 91.88%) — Optics theme is strong fundamentally, but dist_ma5_pct 7.5% exceeds the no-chasing limit of 6%; also not in today's provided top sector list.
7. **莱特光电** (688150) (RPS 94.64%) — Good earnings trend, but dist_ma20_pct 20.3% exceeds the 12% anti-chase limit.
8. **山东赫达** (002810) (RPS 94.87%) — Strong earnings catalyst and RPS120 94.87 fit the extended zone, but dist_ma10_pct 12.0% and dist_ma20_pct 23.1% fail the MA-distance gate.
9. **亚钾国际** (000893) (RPS 92.55%) — MA structure is acceptable and catalyst is strong, but 农化制品 is not in today's top sector list, so at best watchlist logic in V1 terms; V2 says skip if sector is not hot enough.
10. **华宏科技** (002645) (RPS 85.17%) — 环保设备Ⅱ is a hot sector and earnings catalyst is real, but dist_ma5_pct 7.8%, dist_ma10_pct 23.7%, and dist_ma20_pct 38.6% all fail the anti-chase rule.
11. **鼎通科技** (688668) (RPS 91.28%) — 通信设备 is a top sector and catalyst is fresh, but dist_ma5_pct 9.6%, dist_ma10_pct 30.0%, and dist_ma20_pct 41.7% are far beyond allowed entry extension.
12. **长芯博创** (300548) (RPS 92.41%) — Top-sector alignment and fresh Q1 catalyst are positive, but dist_ma5_pct 12.1%, dist_ma10_pct 37.2%, and dist_ma20_pct 52.1% make it a textbook chase.
13. **共达电声** (002655) (RPS 92.88%) — Consumer electronics momentum is strong, but dist_ma5_pct 18.1%, dist_ma10_pct 42.1%, and dist_ma20_pct 62.5% are extreme extension; RPS120 92.88 is fine, setup is not.
14. **江丰电子** (300666) (RPS 94.93%) — Fresh semi earnings catalyst exists, but dist_ma5_pct 12.5%, dist_ma10_pct 25.4%, and dist_ma20_pct 29.0% fail anti-chase; intraday event flow also showed early board weakness.
15. **德福科技** (301511) (RPS 87.87%) — 20cm strength is obvious, but RPS120 87.87 is acceptable while MA extension is absurd: dist_ma5_pct 31.6%, dist_ma10_pct 66.4%, dist_ma20_pct 91.1%. Absolute skip.
16. **咸亨国际** (605056) (RPS 93.83%) — Technically near support, but stock-specific IV proxy is 8.7% so any new size should be halved, and the 10-day price-strength event says recent relative strength is very weak; with regime blocked, no reason to force it.

## 今日研究结论

- 新开仓: 0只
- 跳过: 16只

### 新教训
- {'text': 'A 1.85:1 breadth ratio with all three major indices green can still be a no-buy day if跌停数量 remains elevated; the hard-block should dominate stock-level attractiveness.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'market-regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'High limit-down count signals fragile internal tape and failed breakouts under the surface, which raises gap-down and stop-out risk for fresh momentum entries.'}
- {'text': 'Today strongly reinforces that the MA-distance anti-chase rule is doing the heavy lifting: many of the best catalyst names in hot sectors are simply too extended to touch.', 'type': 'signal', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'When leadership broadens late in a rally, strong names often sit 10% to 40% above short-term support; buying there converts momentum edge into mean-reversion risk.'}
- {'text': 'Hot-sector membership alone is not enough; the highest-quality entries need both sector tailwind and non-extended price structure. 国电南自 stood out because it had both, but even that was vetoed by regime.', 'type': 'heuristic', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'Momentum works best when sector flow, stock-level RPS, and nearby moving-average support align simultaneously.'}
