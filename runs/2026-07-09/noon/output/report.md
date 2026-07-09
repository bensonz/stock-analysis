# 每日研究报告 2026-07-09

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3952.49 | -0.46% |
| 深证成指 | 14887.99 | -0.35% |
| 创业板指 | 3850.21 | +0.13% |
| 科创50 | 2080.50 | +3.19% |

涨跌比: 842涨 / 4616跌 / 5521总

**热门板块**: 半导体(+3.05%), 油服工程(+2.60%), 综合Ⅱ(+1.38%), 非金属材料Ⅱ(+1.05%), 计算机设备(+0.92%)

**冷门板块**: 能源金属(-6.28%), 小金属(-5.11%), 工业金属(-3.66%), 特钢Ⅱ(-3.57%), 金属新材料(-3.50%)

PANIC TAPE — Breadth 0.18:1 (842 up / 4616 down), 36涨停/21跌停. Only 创业板指 (+0.13%) green; 上证指数 -0.46%, 深证成指 -0.35%. 科创50 outlier at +3.19% driven by semiconductor rally on WSTS $1.51T forecast and chipmaker price hikes. Metals/resources in freefall (能源金属 -6.28%, 小金属 -5.11%). Classic risk-off rotation: cyclicals being liquidated, tech/semis the only bid. HARD BLOCK on new positions. IV data unavailable. Capital preservation mode.

## 策略池扫描

扫描 **58** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **扬杰科技** (300373) (RPS 92.0%) — WOULD BE STRONG BUY but market regime HARD BLOCK. Sector (半导体) #1 at +3.05%, RPS120=92.0% sweet spot, active price-hike catalyst (15-25% across 20+ chipmakers), 0 risks, clean MA profile (dist_ma5=-2.4%, dist_ma10=-4.9%, dist_ma20=+8.2%). Priority #1 when breadth clears.
2. **思瑞浦** (688536) (RPS 93.67%) — WOULD BE BUY but market regime HARD BLOCK. Sector #1, RPS120=93.67% extended but covered by sector top 10%, 8 highlights, profit growth 577%, clean MAs.
3. **路维光电** (688401) (RPS 91.31%) — WOULD BE BUY but market regime HARD BLOCK. Sector #1, RPS120=91.31% sweet spot, 0 risks, pulled back near MA10 support, strong fundamentals.
4. **京仪装备** (688652) (RPS 93.51%) — Rule 2b SKIP: dist_ma10=+11.2% (>8%) and dist_ma20=+26.6% (>12%). Extreme extension even within hot sector. Also PE=229, valuation 99.8th percentile.
5. **伟测科技** (688372) (RPS 90.66%) — Rule 2b SKIP: dist_ma20=+13.0% (>12%). Stock is too far above 20-day MA. Wait for pullback.
6. **新洁能** (605111) (RPS 94.83%) — Rule 2b SKIP: dist_ma20=+15.9% (>12%). Also PE=82 vs sector median, recent -7% selloff with 2.2x volume suggests distribution.
7. **星宸科技** (301536) (RPS 93.41%) — Rule 2b SKIP: dist_ma20=+13.5% (>12%). Extended from support.
8. **华天科技** (002185) (RPS 90.03%) — Rule 2b SKIP: dist_ma20=+12.8% (>12%). Recent主力资金净流出 heavily.
9. **金钼股份** (601958) (RPS 91.92%) — Sector (小金属) in bottom 5 (-5.11%). Rule 1: dead sector = no entry. dist_ma10=-13.4% shows steep decline.
10. **多氟多** (002407) (RPS 91.72%) — Recent 跌停 (-10%), sector (化学制品) not in top 30%, high volatility (日均换手23%). dist_ma5=-10.1%.
11. **山东赫达** (002810) (RPS 92.08%) — 跌停 yesterday (-9.98%) on Q2 guidance miss. Sector not hot. dist_ma5=-10.1%. Damaged goods.
12. **南大光电** (300346) (RPS 93.24%) — Sector (电子化学品Ⅱ) not confirmed top 30%. RPS120=93.24% extended without sector cover. 股东减持 691万股 recently.
13. **新宙邦** (300037) (RPS 90.9%) — Sector (电池) mid-pack. VCP=SETUP but contraction_ratio=0.87 too high (need <0.4 for PREMIUM/QUALITY). dist_ma5=-8.0% shows pullback but no urgency.
14. **凯莱英** (002821) (RPS 86.49%) — Today's 股权激励 catalyst is fresh but sector (医疗服务) not in top 30%. RPS120=86.49% below ideal range. Monitor for sector rotation.

## 今日研究结论

- 新开仓: 0只
- 跳过: 14只

### 新教训
- {'text': "Breadth 0.18:1 with only 创业板指 green is a hard no-go regardless of individual stock quality. Even semiconductor +3.05% and multiple clean setups (扬杰科技, 思瑞浦, 路维光电) cannot override the regime gate. This validates V2's sector-first framework.", 'type': 'rule', 'tags': ['entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When 84% of stocks are declining, even the strongest sectors face gravitational pull. The probability of a new position surviving the tape is too low to justify risk.'}
- {'text': "Of 6 semiconductor candidates (RPS>90%), 4 fail Rule 2b (dist_ma20>12%). The MA-distance filter is not overly restrictive — it's accurately identifying names that already ran too far. Only 扬杰科技 and 思瑞浦 pass all MA checks.", 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h027', 'mechanism': 'In a sector rally, early movers run far above MAs while laggards catch up. The MA-distance rule prevents buying the early movers at extension and directs attention to the catch-up plays that still have room.'}
- {'text': '扬杰科技 emerges as the cleanest setup across all dimensions: sector #1, RPS 92.0% sweet spot, active price-hike catalyst (20+ chipmakers raising 15-25%), 0 risks, all MA distances within bounds. When market clears, this should be the first buy with 8-10% allocation.', 'type': 'heuristic', 'tags': ['position-sizing', 'sector'], 'evidence_type': 'supporting', 'mechanism': 'Multi-factor alignment (sector + RPS + catalyst + technicals + risk) is rare. When it occurs, conviction should be maximum because each factor independently supports the entry.'}
- {'text': "Today's 'gap-up and fade' pattern (四大股指集体高开 → broad selloff to -0.46%/-0.35%) is a classic distribution signal. The morning enthusiasm was absorbed by institutional selling. This pattern typically precedes continued weakness and reinforces the cash-only stance.", 'type': 'observation', 'tags': ['timing', 'entry-filter'], 'evidence_type': 'supporting', 'mechanism': 'Gap-up opens attract retail buying while institutions use the liquidity to distribute. The resulting fade confirms that smart money is reducing risk, not adding.'}
