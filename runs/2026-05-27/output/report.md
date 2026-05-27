# 每日研究报告 2026-05-27

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4099.23 | -1.11% |
| 深证成指 | 15809.79 | -0.42% |
| 创业板指 | 4071.41 | +0.70% |
| 科创50 | 1851.68 | -0.86% |

涨跌比: 831涨 / 4645跌 / 5510总

**热门板块**: 综合Ⅱ(+2.56%), 电池(+1.64%), 影视院线(+1.59%), 光伏设备(+1.32%), 电网设备(+0.76%)

**冷门板块**: 贵金属(-5.05%), 非金属材料Ⅱ(-4.17%), 林业Ⅱ(-3.95%), 油服工程(-3.57%), 工业金属(-3.51%)

Breadth 0.18:1 panic, 45涨停/38跌停, 4645 stocks down and only 创业板指 green while 上证指数/深证成指 both red. Hot sectors (top 5): 综合Ⅱ +2.56%, 电池 +1.64%, 影视院线 +1.59%, 光伏设备 +1.32%, 电网设备 +0.76%. Cold sectors (bottom 5): 贵金属 -5.05%, 非金属材料Ⅱ -4.17%, 林业Ⅱ -3.95%, 油服工程 -3.57%, 工业金属 -3.51%. Position sector alignment: 0/1 positions in hot sectors. IV context is mixed: broad-market proxies like 300ETF IV Rank 14.2% are complacent, while 创业板ETF IV Rank 51.8% is elevated; regardless, entry regime is hard-blocked by panic breadth, so no fresh longs.

## 策略池扫描

扫描 **54** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **山东赫达** (002810) (RPS 94.9%) — No new longs in panic regime. Candidate itself is one of the cleaner setups with RPS120 94.9 and VCP quality SETUP, but entry gate is hard-blocked by breadth 0.18:1 and only 1 of 3 major indices green.
2. **湖南裕能** (301358) (RPS 93.78%) — Sector is in today's top group (电池), and catalyst is strong, but no entry in panic regime. Also recent event flow notes the stock's 10-day strength is weak and current price is below MA5/MA10, so this is not a must-act long today.
3. **睿创微纳** (688002) (RPS 89.59%) — Technical shape is acceptable with dist_ma5_pct 0.4, dist_ma10_pct -2.7, dist_ma20_pct 8.0, but sector is not in the provided top sector list and market regime blocks fresh risk. Skip despite decent RPS.
4. **德科立** (688205) (RPS 94.86%) — No new longs in panic tape. Even aside from regime, same-day event flow shows communication/network equipment weakened intraday, so this is not the session to buy the dip.
5. **江丰电子** (300666) (RPS 93.84%) — Fails anti-chase rule: dist_ma10_pct 8.0 is at the upper limit and dist_ma20_pct 25.5 is well above the 12% maximum. Market regime also blocks entries.
6. **伟测科技** (688372) (RPS 93.5%) — Almost qualifies on momentum and near-term MA support, but dist_ma20_pct 13.9 exceeds the 12% anti-chase cap. Panic regime means no exception.
7. **欧陆通** (300870) (RPS 92.91%) — Sector backdrop is constructive, but dist_ma20_pct 31.2 fails anti-chase rule badly. In a panic tape, extended names are automatic skips.
8. **帝尔激光** (300776) (RPS 90.89%) — 光伏设备 is hot, but this is textbook chasing: dist_ma5_pct 9.4, dist_ma10_pct 30.4, dist_ma20_pct 62.3 all violate entry limits.
9. **华锡有色** (600301) (RPS 91.57%) — Held name, not a new buy candidate. Sector is cold and current position should be exited rather than added.

## 今日研究结论

- 新开仓: 0只
- 跳过: 9只

### 新教训
- {'text': 'When breadth collapses to 0.18:1 with 38跌停 and only 1 of 3 major indices green, even strong-looking setups in hot sectors should default to no new positions.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'In panic tapes, individual momentum signals have lower follow-through because forced selling and index pressure dominate stock-specific setups.'}
- {'text': 'Cold-sector gravity remains stronger than single-stock PnL: a profitable resource position can still become a sell once its sector falls into the bottom cluster during a broad de-risking day.', 'type': 'heuristic', 'tags': ['sector', 'exit-rule', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h028', 'mechanism': 'When capital rotates out of cyclicals/materials, winners in those groups lose sponsorship quickly and downside can accelerate before the stock-level stop is reached.'}
- {'text': "The MA-distance anti-chase filter is still doing useful work inside today's stronger groups; several hot-sector names fail because they are 20%+ above MA20.", 'type': 'signal', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Extended names have poor reward-to-risk because nearest support is too far below, so even correct themes can produce bad entries.'}
