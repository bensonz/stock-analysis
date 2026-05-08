# 每日研究报告 2026-05-08

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4178.69 | -0.03% |
| 深证成指 | 15566.42 | -0.48% |
| 创业板指 | 3798.04 | -0.91% |
| 科创50 | 1639.66 | -2.34% |

涨跌比: 3630涨 / 1741跌 / 5491总

**热门板块**: 航天装备Ⅱ(+7.82%), 其他家电Ⅱ(+6.09%), 贸易Ⅱ(+3.35%), 家电零部件Ⅱ(+2.56%), 航空装备Ⅱ(+2.52%)

**冷门板块**: 综合Ⅱ(-3.52%), 电池(-2.61%), 能源金属(-2.39%), 冶钢原料(-2.13%), 半导体(-2.03%)

Breadth 2.09:1 constructive on the surface, with 118涨停/33跌停, but the long-entry gate fails because 0 of 上证指数/深证成指/创业板指 are green and f10 is above the 30 panic threshold. Hot spots are 航天装备Ⅱ(+7.82%), 其他家电Ⅱ(+6.09%), 贸易Ⅱ(+3.35%), while 电池(-2.61%) and 半导体(-2.03%) are cold. IV context is mostly low-to-neutral (overall avg IV rank about 25%; most main-board proxies sub-20%, 科创50 around 42%), so volatility is not the blocker; regime confirmation is. Result: stay in cash, keep a ready list of clean-MA names in strong sectors, do not chase extended leaders.

## 策略池扫描

扫描 **57** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **福晶科技** (002222) (RPS 92.23%) — No new long despite strong stock: entry regime hard-blocked (0/3 major indices green, f10=33). Also dist_ma20_pct 12.7% exceeds anti-chase limit.
2. **伟测科技** (688372) (RPS 93.8%) — Best-looking setup among semis on MA distance, but sector is bottom 5 today and entry regime is blocked. Sector-first rule overrides.
3. **科达制造** (600499) (RPS 90.79%) — Technically acceptable with dist_ma5_pct -1.9%, dist_ma10_pct -0.2%, dist_ma20_pct 7.0 and strong earnings catalyst, but not buying because market buy gate failed.
4. **国电南自** (600268) (RPS 89.92%) — Electric grid is one of the stronger underlying groups and MA structure is clean, but market regime hard-blocks new entries; no forced starter positions.
5. **咸亨国际** (605056) (RPS 93.35%) — MA structure is fine and trend is intact, but catalyst is weaker/older and market regime does not permit small buys.
6. **江丰电子** (300666) (RPS 94.49%) — Semiconductor sector is in bottom 5 and dist_ma10_pct 11.9% plus dist_ma20_pct 17.8% fail anti-chase limits.
7. **华峰测控** (688200) (RPS 90.47%) — Strong earnings and clean short-term structure, but semiconductor sector is cold and dist_ma20_pct 16.0% exceeds limit.
8. **共达电声** (002655) (RPS 94.55%) — Overextended: dist_ma5_pct 25.3%, dist_ma10_pct 55.3%, dist_ma20_pct 84.3%. Anti-chase rule rejects regardless of momentum.
9. **长芯博创** (300548) (RPS 93.71%) — Overextended after strong run: dist_ma5_pct 6.6%, dist_ma10_pct 33.9%, dist_ma20_pct 53.5%. Fails MA-distance rule.
10. **德福科技** (301511) (RPS 91.71%) — Sector is bottom 5 (电池) and the stock is extremely extended with dist_ma5_pct 27.9%, dist_ma10_pct 69.5%, dist_ma20_pct 104.3%.
11. **万向钱潮** (000559) (RPS 89.15%) — RPS is acceptable, but dist_ma5_pct 7.1% and dist_ma10_pct 8.1% breach anti-chase thresholds; auto parts is not in top sector leadership set.
12. **华锡有色** (600301) (RPS 92.84%) — No current sector leadership support from provided sector table and dist_ma5_pct 7.5%, dist_ma10_pct 11.3%, dist_ma20_pct 15.5% all fail anti-chase limits.

## 今日研究结论

- 新开仓: 0只
- 跳过: 12只

### 新教训
- {'text': 'When 0/3 major indices are green, even a 2.09:1 up/down ratio with 118 limit-ups is not enough to open new longs; breadth alone can mislead if index confirmation is absent.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'market-regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'A positive breadth tape without index confirmation often reflects fragmented speculative activity rather than durable institutional trend participation.'}
- {'text': 'The anti-chase MA filter is eliminating many of the visually strongest names today, especially in batteries, optical/AI, and metals.', 'type': 'signal', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Large distance from MA10/MA20 raises mean-reversion risk and worsens reward-to-risk even when the narrative and RPS look attractive.'}
- {'text': "Among today's candidates, the highest-quality deferred names are those with clean MA structure but blocked only by regime, such as 科达制造、国电南自、咸亨国际.", 'type': 'heuristic', 'tags': ['timing', 'sector', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': "If the market gate reopens, the best entries usually come from names already near support rather than from the day's most extended leaders."}
- {'text': 'Sector gravity still dominates stock quality: several semiconductor names have strong earnings and high RPS, but with 半导体 in the bottom 5 today they downgrade from buy candidates to skips.', 'type': 'rule', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Cold sector flows cap follow-through and increase breakout failure risk even for fundamentally strong leaders.'}
