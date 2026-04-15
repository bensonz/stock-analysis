# 每日研究报告 2026-04-15

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4021.42 | -0.13% |
| 深证成指 | 14445.55 | -1.33% |
| 创业板指 | 3493.58 | -1.83% |
| 科创50 | 1400.15 | -0.35% |

涨跌比: 1688涨 / 3730跌 / 5496总

**热门板块**: 医药商业(+3.42%), 化学制药(+2.56%), 饲料(+1.95%), 物流(+1.89%), 电网设备(+1.74%)

**冷门板块**: 能源金属(-3.64%), 玻璃玻纤(-3.52%), 化学原料(-3.02%), 油服工程(-2.89%), 影视院线(-2.82%)

Breadth 0.45:1 bearish, 67涨停/15跌停, distribution skewed to losers and all 3 major indices are red, so the minimum long-entry gate fails decisively. Hot sectors (top 5): 医药商业 +3.42%, 化学制药 +2.56%, 饲料 +1.95%, 物流 +1.89%, 电网设备 +1.74%. Cold sectors (bottom 5): 能源金属 -3.64%, 玻璃玻纤 -3.52%, 化学原料 -3.02%, 油服工程 -2.89%, 影视院线 -2.82%. Position sector alignment: 0/2 positions in hot sectors. IV context is mostly low/偏乐观; broad-market IV is not a fear spike, but low IV does not override a weak breadth regime, so fresh risk stays at zero.

## 策略池扫描

扫描 **39** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **国电南自** (600268) (RPS 91.19%) — Best-looking candidate by sector fit and MA position, but market buy gate fails badly: breadth only 0.45:1 and 0/3 major indices green. No new positions in this tape despite top-5 sector alignment.
2. **新风光** (688663) (RPS 92.65%) — Sector is hot and MA distances are acceptable, but market regime blocks fresh longs; also 科创50 IV Rank 12.1% implies half sizing if tape were healthy.
3. **英科医疗** (300677) (RPS 93.27%) — Medical-related group is strong and MA distances are clean, but its sub-industry is not explicitly in supplied top sector list and the market buy gate fails. Skip rather than force a defensive entry.
4. **华鲁恒升** (600426) (RPS 88.69%) — MA structure is fine, but sector mapping is weak because supplied bottom list includes 化学原料 and today's leadership is elsewhere. In a weak tape, avoid chemical names outside clear top leadership.
5. **闰土股份** (002440) (RPS 94.42%) — RPS is in range and MA distances are acceptable, but sector evidence is mixed: supplied market leadership is 化学制药, while chemical raw materials are in the bottom list. No current broad market support for new entry.
6. **华锡有色** (600301) (RPS 92.84%) — Sector is wrong. Supplied bottom sectors include 能源金属, and this is a resources/cyclical metals name, so it is WATCH-at-best under Rule 1 and not a buy in this market.
7. **东材科技** (601208) (RPS 91.42%) — Fails anti-chase rule: dist_ma5_pct 7.5% and dist_ma10_pct 10.4% both exceed entry limits. Even if theme news exists, setup is too extended.
8. **华峰测控** (688200) (RPS 90.95%) — Fails anti-chase rule: dist_ma5_pct 8.0% and dist_ma10_pct 9.8% exceed allowed thresholds. Good semicap quality, bad entry location.
9. **广合科技** (001389) (RPS 90.99%) — Fails anti-chase rule badly: dist_ma5_pct 8.6%, dist_ma10_pct 16.0%, dist_ma20_pct 16.4%. Strong stock, wrong spot.
10. **华懋科技** (603306) (RPS 93.43%) — Fails anti-chase rule severely: dist_ma5_pct 15.7%, dist_ma10_pct 22.3%, dist_ma20_pct 19.6%. Also auto-parts sector is not in supplied hot leadership.
11. **博众精工** (688097) (RPS 92.63%) — Fails anti-chase rule: dist_ma5_pct 11.1%, dist_ma10_pct 13.8%, dist_ma20_pct 17.5%. Momentum is obvious, but entry is late.

## 今日研究结论

- 新开仓: 0只
- 跳过: 11只

### 新教训
- {'text': 'When breadth is below 1:1 and all three major indices are red, the correct momentum action is zero new positions even if a few candidates have clean RPS and MA structures.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Weak tape reduces follow-through and increases failure rate of otherwise valid breakouts; sector strength cannot fully overcome poor market participation.'}
- {'text': 'The MA-distance anti-chase filter is doing real work today: several of the strongest names on paper were invalid because they were too far above MA5/MA10/MA20.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Extended names have poor reward-to-risk because the nearest support is too far away, so even strong themes become low-quality entries.'}
- {'text': 'Raised breakeven stops remain valuable in weak tapes: 利柏特 suffered a -9.88% day but the position is still manageable because the stop had already been lifted to entry.', 'type': 'heuristic', 'tags': ['exit-rule', 'position-sizing', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'Mechanical stop raises convert open profit into a low-risk hold and prevent a winner from turning into a portfolio-level problem during tape deterioration.'}
