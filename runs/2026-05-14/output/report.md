# 每日研究报告 2026-05-14

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4199.19 | -1.02% |
| 深证成指 | 15831.83 | -1.60% |
| 创业板指 | 3960.51 | -1.93% |
| 科创50 | 1742.63 | -1.55% |

涨跌比: 1141涨 / 4306跌 / 5497总

**热门板块**: 航运港口(+1.50%), 国有大型银行Ⅱ(+1.39%), 养殖业(+1.31%), 饲料(+1.11%), 白色家电(+0.69%)

**冷门板块**: 航天装备Ⅱ(-5.43%), 林业Ⅱ(-4.07%), 小金属(-3.88%), 能源金属(-3.38%), 综合Ⅱ(-3.31%)

Breadth 0.26:1 bearish, 63涨停/27跌停, all 3 major indices red and entry_regime explicitly flags panic with hard_block=true. Hot sectors are mostly defensive/relative-strength pockets (航运港口、国有大型银行Ⅱ、白色家电) while high-beta groups like 航天装备Ⅱ、小金属、能源金属 lead downside. IV context is mixed: broad-market IV mostly neutral, but 科创50/创业板 proxies are elevated, reinforcing selectivity; regardless, regime gate fails, so no new positions today.

## 策略池扫描

扫描 **53** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **莱特光电** (688150) (RPS 94.97%) — No entry. Market hard-blocked for new longs; additionally dist_ma20_pct 22.6% exceeds anti-chase rule even though RPS120 94.97 and earnings growth are solid.
2. **恩捷股份** (002812) (RPS 93.96%) — No entry. Market hard-blocked for new longs; setup is one of the cleaner ones on MA distance, but sector is not in today's top leadership list and breadth regime forbids fresh risk.
3. **科达制造** (600499) (RPS 90.79%) — No entry. Market hard-blocked for new longs; technicals are acceptable, but sector is not in today's top 30% leadership and stock has weaker short-term event signal in events.
4. **咸亨国际** (605056) (RPS 93.35%) — No entry. Market hard-blocked for new longs; RPS120 93.35 is fine and MA structure is calm, but score_trend is weaker and there is no strong fresh catalyst in today's tape.
5. **万向钱潮** (000559) (RPS 89.15%) — Skip. RPS120 89.15 is acceptable, but sector is 汽车零部件, not in today's top leadership, and latest event shows 2026年第一季度营收同比下降19.84%、净利润同比下降15.84%。
6. **华锡有色** (600301) (RPS 92.84%) — Skip. Sector 小金属 is in today's bottom 5 at -3.88%; no entry regardless of stock quality. Also dist_ma20_pct 13.2% exceeds anti-chase threshold.
7. **江丰电子** (300666) (RPS 94.49%) — Skip. Sector trend was strong before, but today market is risk-off and stock fails anti-chase with dist_ma10_pct 13.6% and dist_ma20_pct 22.4%.
8. **华峰测控** (688200) (RPS 90.47%) — Skip. Strong fundamentals/catalyst, but anti-chase violation is severe: dist_ma5_pct 10.7%, dist_ma10_pct 20.8%, dist_ma20_pct 32.8%. Above 95% chasing risk profile in practice.
9. **中船特气** (688146) (RPS 85.42%) — Skip. Fresh news exists, but stock fails anti-chase with dist_ma10_pct 14.9% and dist_ma20_pct 43.5%; additionally current market regime blocks all new longs.
10. **上海新阳** (300236) (RPS 87.47%) — Skip. Closest to buyable on price structure, but dist_ma10_pct 8.8% and dist_ma20_pct 12.5% both exceed allowed limits, and market breadth is too weak for any fresh entry.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': 'When the top-performing sectors are defensive groups like 航运港口、国有大型银行、白色家电 while all major indices are red, treat sector strength as relative defense rather than a green light for aggressive momentum buying.', 'type': 'signal', 'tags': ['sector', 'timing', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Defensive leadership during index-wide liquidation usually means capital is hiding, not broadly embracing risk, so stock-level breakouts have lower follow-through.'}
- {'text': 'The MA-distance anti-chase rule remains crucial: many fundamentally attractive names today failed only because they are too far above MA10/MA20, which matters even more on a panic tape.', 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'In weak breadth, stretched names lose nearest support quickly, so overextension turns good stories into bad entries.'}
- {'text': 'A panic breadth ratio below 0.3:1 with 0/3 major indices green should default the system to full cash, even if the candidate list still contains high-RPS names.', 'type': 'heuristic', 'tags': ['timing', 'entry-filter', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum edge comes from both stock strength and market sponsorship; when sponsorship disappears, stock selection quality cannot compensate for tape risk.'}
