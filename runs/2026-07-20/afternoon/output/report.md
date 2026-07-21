# 每日研究报告 2026-07-20

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3796.28 | +0.85% |
| 深证成指 | 13610.23 | -0.71% |
| 创业板指 | 3443.10 | +0.42% |
| 科创50 | 1718.69 | +0.19% |

涨跌比: 1740涨 / 3710跌 / 5525总

**热门板块**: 油气开采Ⅱ(+9.14%), 油服工程(+7.19%), 白酒Ⅱ(+5.58%), 煤炭开采(+5.57%), 保险Ⅱ(+4.94%)

**冷门板块**: 玻璃玻纤(-10.16%), 电子化学品Ⅱ(-10.06%), 非金属材料Ⅱ(-9.31%), 元件(-8.26%), 塑料(-7.41%)

PANIC regime with deceptive index. 上证 +0.85% driven by energy/financial heavyweight rotation; underneath, breadth 0.47:1 with 267 limit-downs. Tech/semiconductor sectors in liquidation (-8% to -10%). IV Rank 1.0 across all ETFs — extreme fear. CSRC holding stabilization meeting today; SOEs deploying ¥500B+. Oil surge on US-Iran conflict driving resource rotation. 100% cash is the correct position. No new entries until breadth recovers above 1.5:1 and f10 drops below 30.

## 策略池扫描

扫描 **50** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **恒逸石化** (000703) (RPS 95.65%) — Market regime HARD BLOCK (breadth 0.47:1, 267 limit-downs). Sector 石油石化 is hot (+9.14%) but RPS120=95.65% in extended zone. Not in enriched_candidates — insufficient data to size even if regime allowed.
2. **凯莱英** (002821) (RPS 92.87%) — Market regime HARD BLOCK. Sector 医药生物 not in top 30%. RPS120=92.87% in sweet spot but dist_ma5=-8.1% — stock in correction, not basing. CRO sector whipsawed 7/15→7/17.
3. **永和股份** (605020) (RPS 89.12%) — Market regime HARD BLOCK. Sector 化学制品 near bottom zones (塑料 -7.41%). RPS120=89.12%, dist_ma5=-4.6%. Buyback catalyst (¥1.5-3B) is positive but sector gravity against it.
4. **中石科技** (300684) (RPS 89.66%) — Sector 电子化学品Ⅱ is BOTTOM 2 today at -10.06% — hard no-buy zone per Rule 1 regardless of individual stock quality. RPS120=89.66%.
5. **荣昌生物** (688331) (RPS 89.78%) — Market regime HARD BLOCK. Sector 医药生物 not in top 30%. RPS120=89.78%, dist_ma5=-12.5% — deep in liquidation. Strong fundamentals (revenue +42%, 公募 34%) but price is truth.
6. **昭衍新药** (603127) (RPS 86.13%) — dist_ma20_pct=+19.5% from enriched data — violates Rule 2b hard cap (>12% from MA20). Also 跌停 7/17 with sector whipsaw. Enriched data confirms MA20 extension risk.
7. **中控技术** (688777) (RPS 94.96%) — Market regime HARD BLOCK. Sector 自动化设备 neutral. PE=189 (red flag per enriched data), dist_ma5=-7.0%. Margin signal: deleveraging (net5_repay_days=5). No sector catalyst edge.
8. **四方股份** (601126) (RPS 93.29%) — Market regime HARD BLOCK. RPS20=12.23 — near-zero short-term momentum, stock in deep correction. Sector 电网设备 not in today's hot sectors despite fundamental quality (score_company 9.4).

## 今日研究结论

- 新开仓: 0只
- 平仓: 0只
- 跳过: 8只

### 新教训
- {'text': "Hard block confirmed effective: 上证 +0.85% masks 267 limit-downs and 0.47:1 breadth. V1 would have seen 'index green' and bought into a trap tape. V2 correctly reads breadth and stays cash. The index gain is entirely driven by heavyweight resource/financial rotation while the broad market liquidates.", 'type': 'rule', 'tags': ['entry-filter', 'breadth'], 'evidence_type': 'supporting', 'related_hypothesis': 'h077', 'mechanism': 'Index-level gains from heavyweight rotation hide severe underlying breadth deterioration. The up/down ratio and limit-down count are far more informative than headline index changes for momentum entry decisions.'}
- {'text': 'IV Rank at 1.0 across ALL ETFs simultaneously signals systemic panic, not isolated fear. Historically a bottoming signal — but momentum framework correctly waits for breadth recovery + sector stabilization rather than catching knives. The opportunity cost of waiting 1-3 days for confirmation is far lower than the risk of entering during a liquidation cascade.', 'type': 'heuristic', 'tags': ['entry-filter', 'timing', 'volatility'], 'evidence_type': 'supporting', 'mechanism': "Extreme IV across all underlyings means options market pricing systemic meltdown risk. While this often precedes a V-bottom, the momentum framework's edge comes from entering after trend re-establishment, not before."}
- {'text': 'When broad sell-off hits, even highest-quality stocks show dist_ma5_pct of -10% to -30% — these are liquidation events, not pullbacks. The MA-distance framework works in reverse: stocks that crashed through all MAs in days have broken trend structure and need weeks to rebuild bases before re-entry.', 'type': 'observation', 'tags': ['entry-filter', 'timing', 'technical'], 'evidence_type': 'supporting', 'mechanism': 'A stock -15% below MA5 has broken its short-term trend. Momentum entries require an established uptrend; these stocks are in downtrends and need to form new bases before they become actionable.'}
- {'text': "Geopolitics-driven sector rotations (US-Iran → energy surge) tend to reverse quickly when headlines shift. The framework's implicit requirement for sector persistence protects against chasing one-day spikes into sectors that may not sustain.", 'type': 'signal', 'tags': ['sector', 'macro'], 'evidence_type': 'observation', 'mechanism': 'Supply-shock-driven sector moves (oil, defense) are headline-dependent. Unlike earnings-driven or policy-driven sector moves, they can reverse within hours if conflict de-escalates. Momentum framework should demand multi-day sector confirmation before entering geopolitically-driven sectors.'}
- {'text': 'CSRC stabilization meeting + SOE buying (¥500B+) may create a short-term bounce, but policy-driven bounces in momentum-down tapes create false entry signals. Wait for market-driven breadth improvement, not policy headlines.', 'type': 'observation', 'tags': ['macro', 'entry-filter'], 'evidence_type': 'observation', 'mechanism': 'Policy interventions create transient liquidity events that fade. True regime change requires sustained breadth improvement (>1.5:1 for 2+ consecutive days) before re-entering.'}
