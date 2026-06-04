# 每日研究报告 2026-06-04

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4057.78 | -0.64% |
| 深证成指 | 15661.57 | -0.27% |
| 创业板指 | 4088.88 | -0.83% |
| 科创50 | 1738.06 | +0.69% |

涨跌比: 1344涨 / 4121跌 / 5512总

**热门板块**: 元件(+4.42%), 电子化学品Ⅱ(+3.99%), 光学光电子(+3.60%), 其他电子Ⅱ(+3.10%), 焦炭Ⅱ(+2.46%)

**冷门板块**: 工业金属(-4.49%), 商用车(-3.65%), 油服工程(-3.47%), 电池(-3.32%), 综合Ⅱ(-3.19%)

PANIC regime: breadth 0.33:1 (1,344 up / 4,121 down), all 3 major indices red, 92涨停/34跌停. K-shaped divergence — electronics/AI hardware complex (元件+4.4%, 电子化学品+4.0%, 光学光电子+3.6%) holds gains while cyclicals and industrials are dumped (-4.5% industrial metals). IV mixed: 科创50 elevated at 56.3%, 300ETF complacent at 23.8%. This suggests institutional rotation INTO tech quality, not broad liquidation. Hard block on new positions — 100% cash is correct.

## 策略池扫描

扫描 **50** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **上海新阳** (300236) (RPS 89.06%) — BEST SETUP TODAY but PANIC hard block. 电子化学品Ⅱ (top 2 sector, +3.99%), RPS120=89.06% sweet spot, all MA distances within limits (dist_ma5=-7.5% pullback to support), 0 risk factors, net profit +103% YoY catalyst. Strong BUY candidate when market gate reopens.
2. **华灿光电** (300323) (RPS 91.76%) — 光学光电子 (top 3 sector, +3.6%), RPS120=91.76% sweet spot, BUT dist_ma5_pct=8.4% exceeds 6% hard cap (Rule 2b). Also still loss-making and sector overextended. Wait for pullback to MA5.
3. **兴森科技** (002436) (RPS 88.07%) — 元件 (TOP 1 sector, +4.42%), RPS120=88.07% in range, BUT dist_ma5=8.8% (>6%), dist_ma10=15.0% (>8%), 5 risk factors. Extreme extension. Must consolidate before entry.
4. **国瓷材料** (300285) (RPS 93.33%) — 电子化学品Ⅱ (top 2), RPS120=93.33% slightly above sweet spot, BUT dist_ma5=11.6%, dist_ma10=25.2%, dist_ma20=46.2% — triple MA violation. Hit new high intraday then sold off. Classic chasing trap.
5. **华丰科技** (688629) (RPS 86.29%) — RPS120=86.29% (low end), MA distances OK, BUT 61% lockup expiry June 29 (25 days away). Massive dilution risk. Avoid until post-expiry clarity. Sector 军工电子 not confirmed in top 30%.
6. **四川黄金** (001337) (RPS 93.59%) — Sector (贵金属/工业金属 -4.49%) in BOTTOM zone. Sector gravity wins regardless of stock quality. RPS120=93.59% irrelevant when sector is getting destroyed.
7. **华宏科技** (002645) (RPS 92.43%) — dist_ma5=15.1% — extreme extension (Rule 2b). dist_ma20=34.9%. 大股东100%质押 = forced liquidation risk. RPS120=92.43% doesn't matter when the chart is vertical and insiders can't afford a dip.
8. **华峰测控** (688200) (RPS 94.01%) — dist_ma20=19.2% (>12% hard cap). 10-day price momentum in bottom 6.2% — weak recent tape despite high RPS120=94.01%. 大股东询价转让 at ¥388.98 creates overhang.

## 今日研究结论

- 新开仓: 0只
- 跳过: 8只

### 新教训
- {'text': "Entry_regime hard block correctly prevented new positions on a panic day (breadth 0.33:1, 0/3 green indices, f10=34). This discipline alone preserves capital when 75% of stocks are declining. V2's simplest rule may be its most valuable.", 'type': 'signal', 'tags': ['entry-filter', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When breadth is below 1:1 and all major indices are red, even the strongest individual setups face systematic selling pressure that overwhelms stock-specific catalysts. Cash is the correct position.'}
- {'text': 'K-shaped market days create deceptive signals: 元件 +4.42% while 4,121 stocks decline. The hot sectors can tempt cherry-picking, but individual stock selection cannot overcome the systematic selling pressure. 300236 上海新阳 looked perfect on paper — the correct decision was still to skip.', 'type': 'observation', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Institutional rotation creates pockets of strength even on broad selloff days. These pockets often reverse the next day if the selling accelerates. Wait for breadth to confirm before entering.'}
- {'text': 'MA-distance Rule 2b filters out ~50% of enriched candidates today. Of 25 reviewed, 12+ failed dist_ma5>6% or dist_ma10>8% or dist_ma20>12%. Confirmed by active learnings h021 and h027 — this rule is essential and should never be overridden.', 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Stocks extended far above short-term MAs have high mean-reversion risk. The best entries come from pullbacks to MA5/MA10/MA20 support within an uptrend, not from chasing vertical moves.'}
- {'text': "华丰科技 688629 has 61% lockup expiry on June 29. Even if technicals improve, this massive dilution overhang makes it untouchable until post-expiry. Add 'major lockup expiry within 30 days' as a hard skip criterion for new positions.", 'type': 'heuristic', 'tags': ['entry-filter', 'position-sizing'], 'evidence_type': 'supporting', 'mechanism': 'Lockup expiries >20% of float create asymmetric downside risk. Insiders and pre-IPO investors are incentivized to sell immediately, creating selling pressure that no catalyst can overcome in the short term.'}
- {'text': 'The strongest candidate (300236 上海新阳) is a pullback-to-support setup (dist_ma5=-7.5%), not a breakout. When the market gate reopens, prioritize stocks that have corrected to MA support within hot sectors over stocks hitting new highs. This aligns with the VCP concept — contraction before expansion.', 'type': 'observation', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'mechanism': 'Pullbacks within uptrends offer better risk/reward than breakouts because the stop (entry -5%) is closer to natural support levels, while upside remains intact. Breakouts in a weak tape often fail immediately.'}
