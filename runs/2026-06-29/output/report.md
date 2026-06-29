# 每日研究报告 2026-06-29

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4073.90 | +1.16% |
| 深证成指 | 15812.87 | +0.19% |
| 创业板指 | 4216.70 | +0.54% |
| 科创50 | 2126.01 | +4.61% |

涨跌比: 2469涨 / 2933跌 / 5512总

**热门板块**: 化学制药(+7.42%), 生物制品(+7.34%), 医疗服务(+6.83%), 电子化学品Ⅱ(+4.70%), 半导体(+4.54%)

**冷门板块**: 玻璃玻纤(-5.64%), 非金属材料Ⅱ(-5.32%), 综合Ⅱ(-3.94%), 塑料(-3.38%), 通信设备(-2.83%)

Narrow rally: all 3 major indices green (上证+1.16%, 深证+0.19%, 创业板+0.54%), 科创50 surging +4.61%, but breadth 0.84:1 bearish with 75跌停 vs 127涨停. Healthcare (化学制药+7.42%) new leadership on foreign drug manufacturing policy catalyst. Electronics/semiconductor still strong but slipping. Resources liquidated. Entry regime hard-blocks new longs: Up/Down 0.84 < 1.5 gate + f10=75 ≥ 30 panic threshold. Two existing winners at +37%/+30% — raising trailing stops. 92.9% cash. IV data unavailable across all underlyings.

## 策略池扫描

扫描 **63** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **新宙邦** (300037) (RPS 90.79%) — Top-tier catalyst (宁德时代电解液5/10/15万吨3年协议), RPS120=90.79 sweet spot, VCP=SETUP, MA distances clean (dist_ma5=-2.9%). Would be STRONG BUY at 7% allocation. BLOCKED by entry regime hard block (breadth 0.84:1, f10=75). Queue for re-evaluation when regime clears.
2. **思瑞浦** (688536) (RPS 93.92%) — Sector 半导体 #5 hot, net profit +577%, RPS120=93.92, MA distances clean. Would be BUY at 5-7%. BLOCKED by entry regime hard block.
3. **鹏辉能源** (300438) (RPS 95.0%) — 819% net profit growth, 储能满产, 中信建投买入评级. RPS120=95.0 extended zone but 0 risk factors. MA pristine (dist_ma5=0.9%). Would be BUY at 5-7%. BLOCKED by entry regime.
4. **多氟多** (002407) (RPS 91.87%) — Rule 2b violation: dist_ma5=9.3% (>6%), dist_ma10=17.7% (>8%), dist_ma20=20.4% (>12%). Non-negotiable MA distance skip despite strong 氟化工涨停 catalyst. Also regime blocked.
5. **新洁能** (605111) (RPS 91.52%) — Rule 2b violation: dist_ma5=16.8%, dist_ma10=31.4%, dist_ma20=44.0%. Massively extended. Sector 半导体 hot but price is light-years from support.
6. **莱特光电** (688150) (RPS 94.9%) — Rule 2b: dist_ma10=11.4% (>8%). Sector 电子化学品Ⅱ #4 but one MA violation. Also regime blocked. Current price ¥59.40 (from enriched_candidates data).

## 今日研究结论

- 新开仓: 0只
- 跳过: 6只

### 新教训
- {'text': 'Narrow rally (科创50 +4.61% with breadth 0.84:1) signals money concentration in big-cap tech/healthcare, not broad participation. This pattern is a red flag for adding new momentum positions — our winners happen to be in the right spots, but adding more would be over-concentration when breadth warns. Cash is the correct default.', 'type': 'observation', 'tags': ['market-regime', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When more stocks decline than advance despite index gains, liquidity is funneling into a narrow set of names. Adding to the same theme during this pattern increases correlation risk without the safety net of broad market support.'}
- {'text': 'Healthcare rotation (化学制药 +7.42%, 生物制品 +7.34%, 医疗服务 +6.83% occupying top 3 spots) driven by 商务部/发改委/财政部 joint policy on foreign drug manufacturing — a structural catalyst. Our strategy pool contains zero healthcare candidates. This is a diversification gap requiring pool expansion.', 'type': 'signal', 'tags': ['sector', 'pool-construction'], 'evidence_type': 'observation', 'mechanism': "Regime-level sector shifts create winners outside our scanning scope. When top 3 sectors are absent from a 63-stock pool, the pool's sector bias (electronics/semiconductor/chemicals) becomes a structural blind spot."}
- {'text': 'Trailing stop at current-10% after +30-37% gains is the correct mechanical discipline. Moving 上海新阳 stop from ¥103.36 to ¥115.90 and 路维光电 from ¥79.84 to ¥85.10 locks in +23.3% and +17.2% respectively while giving each trade 10% breathing room. This converts fast winners into low-risk holds without subjective judgment.', 'type': 'heuristic', 'tags': ['exit-rule', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'After +20%, the +10% stop becomes inadequate — a reversion to stop destroys ~14% of current value. Current-10% trail preserves the majority of paper gains while allowing normal volatility. The 10% buffer is wide enough to avoid whipsaw but tight enough to protect.'}
- {'text': "Rule 2b (MA-distance anti-chase) filtered out 4 of 7 visually strong names today: 多氟多(dist_ma5=9.3%), 新洁能(16.8%), 莱特光电(dist_ma10=11.4%), 共达电声(dist_ma10=16.3%). These would have been V1 buys and are now correctly skipped. The rule's hit rate continues validating its non-negotiable status.", 'type': 'signal', 'tags': ['entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021, h027', 'mechanism': "Stocks extended >6% above MA5 or >8% above MA10 have elevated mean-reversion risk regardless of sector strength. The 'hot sector exception' temptation is precisely what Rule 2b is designed to prevent. Even in #4-5 ranked sectors, MA distance discipline applies."}
