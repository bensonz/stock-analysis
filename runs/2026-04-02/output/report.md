# 每日研究报告 2026-04-02

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3927.61 | -0.53% |
| 深证成指 | 13548.46 | -1.15% |
| 创业板指 | 3189.72 | -1.78% |
| 科创50 | 1268.90 | -2.26% |

涨跌比: 1190涨 / 4220跌 / 5485总

**热门板块**: 林业Ⅱ(+3.72%), 养殖业(+2.56%), 饲料(+2.24%), 油服工程(+2.18%), 航运港口(+2.10%)

**冷门板块**: 电视广播Ⅱ(-3.00%), IT服务Ⅱ(-2.95%), 广告营销(-2.82%), 房地产服务(-2.74%), 橡胶(-2.66%)

Market regime weak. Breadth 0.28:1 bearish, 23涨停/16跌停, with 1190 up vs 4220 down and all 3 major indices red. Hot sectors (top 5): 林业Ⅱ +3.72%, 养殖业 +2.56%, 饲料 +2.24%, 油服工程 +2.18%, 航运港口 +2.10%. Cold sectors (bottom 5): 电视广播Ⅱ -3.00%, IT服务Ⅱ -2.95%, 广告营销 -2.82%, 房地产服务 -2.74%, 橡胶 -2.66%. Position sector alignment: 0/2 positions in hot sectors. IV context is complacent-to-extremely-low (overall avg IV rank 11.0%), which would halve new sizing if entries were allowed, but the buy gate is closed anyway.

## 策略池扫描

扫描 **21** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) (RPS 91.15%) — Entry regime is weak: breadth only 0.28:1, 0/3 major indices green. Also fails no-chasing rule with dist_ma5_pct 7.0% and dist_ma10_pct 8.3%.
2. **舒华体育** (605299) (RPS 94.93%) — Fails MA distance gate badly: dist_ma5_pct 16.0%, dist_ma10_pct 30.7%, dist_ma20_pct 47.9%. Even aside from weak tape, this is pure chase.
3. **烽火通信** (600498) (RPS 95.3%) — RPS120 95.3 is above the allowed chase zone, and no enriched MA-distance data is provided, which is a risk factor. Weak market regime means no new long anyway.
4. **华通线缆** (605196) (RPS 95.36%) — RPS120 95.36 is above the preferred entry zone and market regime blocks fresh positions. No need to force entries in weak tape.
5. **海星股份** (603115) (RPS 97.08%) — RPS120 97.08 is above 95%, so skip chasing. No current price data in enriched MA-distance set to support a disciplined entry.
6. **华懋科技** (603306) (RPS 92.83%) — Sector is 汽车零部件, not in today’s top sector leadership, and market regime is weak. Stock quality is secondary when sector and tape are wrong.
7. **明阳智能** (601615) (RPS 90.8%) — Sector is not in today’s top leadership and trend quality is poor: dist_ma10_pct -9.6%, dist_ma20_pct -13.5%, indicating breakdown rather than constructive strength.
8. **华鲁恒升** (600426) (RPS 88.62%) — RPS120 88.62 is acceptable, but sector is not in today’s top leadership and the market buy gate is decisively closed. Skip rather than force a starter position.
9. **东材科技** (601208) (RPS 90.86%) — RPS120 90.86 is fine, but sector leadership is absent and market breadth is too weak for new longs. No fresh risk in a 0/3 green-index tape.
10. **利柏特** (605167) (RPS 93.49%) — RPS120 93.49 is allowed, MA distances are acceptable, and contract catalyst is real, but sector is not among today’s leaders and the market regime blocks new entries.
11. **华锡有色** (600301) (RPS 93.29%) — RPS120 93.29 is allowed, but sector is not in today’s top leadership and dist_ma20_pct is -13.1%, showing it has already lost short-term structure. Weak tape means skip.
12. **三祥新材** (603663) (RPS 91.77%) — Sector is not in today’s top leadership and dist_ma20_pct -12.6% shows technical damage after prior run. Not a fresh momentum entry here.

## 今日研究结论

- 新开仓: 0只
- 跳过: 12只

### 新教训
- {'text': 'When the entry regime is this weak (breadth 0.28:1, 0/3 major indices green), the correct momentum action is often zero new positions even if several candidates still have acceptable RPS readings.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum entries need broad participation to follow through; isolated stock strength fails more often when the tape is distribution-heavy.'}
- {'text': 'Raising stops mechanically after +10% works well in weak tapes because it converts a fast winner into a low-risk hold without needing a fresh market call.', 'type': 'heuristic', 'tags': ['exit-rule', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'In a deteriorating market, protecting open profits is more valuable than maximizing upside variance.'}
- {'text': 'Stop-proximity violations deserve proactive action before the hard stop is hit, especially in 科创板 names where gap risk can erase the remaining cushion quickly.', 'type': 'signal', 'tags': ['exit-rule', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'Once price is within 1-2% of the stop, randomness and opening gaps dominate; waiting for exact triggers worsens realized exits.'}
