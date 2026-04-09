# 每日研究报告 2026-04-09

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3965.70 | -0.73% |
| 深证成指 | 13999.55 | -0.31% |
| 创业板指 | 3325.29 | -0.67% |
| 科创50 | 1350.03 | -0.20% |

涨跌比: 1039涨 / 4404跌 / 5491总

**热门板块**: 元件(+1.62%), 油气开采Ⅱ(+1.55%), 环保设备Ⅱ(+1.15%), 电子化学品Ⅱ(+0.79%), 其他电源设备Ⅱ(+0.73%)

**冷门板块**: 厨卫电器(-3.52%), 林业Ⅱ(-3.19%), 旅游及景区(-3.05%), 游戏Ⅱ(-3.05%), 数字媒体(-2.88%)

Breadth 0.24:1 bearish, 48涨停/10跌停, but declines are broad-based with 4404 stocks down and all 3 major indices red (上证-0.73%, 深成-0.31%, 创业板-0.67%). Hot sectors (top 5): 元件 +1.62%, 油气开采Ⅱ +1.55%, 环保设备Ⅱ +1.15%, 电子化学品Ⅱ +0.79%, 其他电源设备Ⅱ +0.73%. Cold sectors (bottom 5): 厨卫电器 -3.52%, 林业Ⅱ -3.19%, 旅游及景区 -3.05%, 游戏Ⅱ -3.05%, 数字媒体 -2.88%. Position sector alignment: 1/2 positions in hot sectors. Research checks suggest electronics strength and oil-price support in oil/gas, but the market-wide tape is too weak for fresh longs. IV context is neutral-to-low (overall avg IV rank 26.4%), so no volatility-based brake for current holds, but also no reason to force entries in a weak regime.

## 策略池扫描

扫描 **0** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) — No new entries allowed: entry regime is weak with breadth 0.24:1 and 0/3 major indices green. Also no enriched candidate MA-distance/VCP data provided for validation.
2. **烽火通信** (600498) — No new entries allowed under Rule 1 buy gate. No current candidate-level RPS/MA distance data in enriched_candidates, so cannot validate a momentum entry.
3. **海星股份** (603115) — Skip by regime, not by story: breadth is far below the 1.5:1 minimum and all 3 major indices are red. No enriched candidate data available.
4. **华通线缆** (605196) — Weak tape means no fresh risk. Also cannot verify Rule 2b MA-distance check because enriched_candidates is empty.
5. **华锡有色** (600301) — No new positions in a weak regime. Without enriched candidate inputs, sector rank/RPS/MA extension cannot be confirmed.

## 今日研究结论

- 新开仓: 0只
- 跳过: 5只

### 新教训
- {'text': 'When breadth collapses to 0.24:1 and 0/3 major indices are green, the correct V2 action is to open no new positions even if a few sectors are still green.', 'type': 'rule', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Weak index confirmation and poor breadth mean sector winners are less likely to produce clean follow-through; cash preserves optionality for the next strong tape.'}
- {'text': 'Sub-MAVOL30 participation on both active positions means price gains are acceptable for now but should not be interpreted as strong momentum confirmation.', 'type': 'signal', 'tags': ['timing', 'exit-rule', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Low volume advances often lack sponsorship; if price stalls, these names can lose momentum quickly despite being above entry.'}
- {'text': 'With strategy_pool at 0 stocks and enriched_candidates empty, the process edge shifts from stock picking to disciplined non-action.', 'type': 'observation', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Momentum systems lose money when they manufacture setups from incomplete data; absence of validated candidates is itself a decision input.'}
