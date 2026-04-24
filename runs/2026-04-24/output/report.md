# 每日研究报告 2026-04-24

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4069.37 | -0.58% |
| 深证成指 | 14837.69 | -1.37% |
| 创业板指 | 3638.28 | -2.20% |
| 科创50 | 1458.31 | +1.80% |

涨跌比: 1454涨 / 3932跌 / 5499总

**热门板块**: 能源金属(+2.86%), 半导体(+1.55%), 化妆品(+1.50%), 农化制品(+1.18%), 服装家纺(+1.16%)

**冷门板块**: 通信设备(-5.60%), 航天装备Ⅱ(-5.57%), 油服工程(-2.90%), 广告营销(-2.89%), 贵金属(-2.85%)

Breadth 0.37:1 bearish, 52涨停/34跌停, all 3 major indices red while only 科创50 is positive; this is a panic tape and fails the minimum long-entry gate. Hot sectors (top 5): 能源金属 +2.86%, 半导体 +1.55%, 化妆品 +1.50%, 农化制品 +1.18%, 服装家纺 +1.16%. Cold sectors (bottom 5): 通信设备 -5.60%, 航天装备Ⅱ -5.57%, 油服工程 -2.90%, 广告营销 -2.89%, 贵金属 -2.85%. Position sector alignment: 1/3 positions in hot sectors. IV context is complacent-to-low overall (overall avg IV rank 12.41%; many 60x/科创 proxies <15%), which is a sizing headwind for new longs but secondary today because the regime hard-block already says no new positions.

## 策略池扫描

扫描 **39** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **华峰测控** (688200) (RPS 90.95%) — 半导体 is a hot sector and RPS120 90.95 is ideal, but entry regime is hard-blocked (breadth 0.37:1, 0/3 major indices green). Even without the regime issue, 科创50 IV Rank 11.3% implies reduced sizing.
2. **新风光** (688663) (RPS 92.65%) — 电网设备 has stock-specific strength and MA distances are healthy, but the sector is not in today's top 30% by provided sector table, and the market regime blocks all new longs.
3. **恩捷股份** (002812) (RPS 93.33%) — RPS120 93.33 is allowed only in stronger conditions, but sector 电池 is not in the hot-sector list and today's quick note says 电池板块开盘走弱. Panic regime means no new entry.
4. **科达制造** (600499) (RPS 89.74%) — Fresh earnings catalyst is attractive and MA distances are fine, but RPS120 89.74 alone is not enough when the market is in panic mode and 专用设备 is not in the provided top-sector list.
5. **英科医疗** (300677) (RPS 93.27%) — Setup is technically clean with RPS120 93.27 and healthy MA distances, but 医疗器械 is not a top-30% sector in today's sector data and the tape does not permit fresh risk.
6. **广合科技** (001389) (RPS 90.99%) — Strong fundamentals and momentum, but dist_ma10_pct 10.3% breaches the no-chase rule (>8%), and market regime blocks entries anyway.
7. **兴福电子** (688545) (RPS 91.38%) — 半导体-related backdrop is supportive, but dist_ma10_pct 9.5% breaches the MA-distance anti-chase rule. Also no new longs in current regime.
8. **江苏博云** (301003) (RPS 87.81%) — Already held; no add. Sector 塑料 is not in today's top sector list, so despite open profit the name is hold-only, not an add-on entry.

## 今日研究结论

- 新开仓: 0只
- 跳过: 8只

### 新教训
- {'text': 'When breadth is below 1:1 and all three major indices are red, the correct momentum action is to stop initiating longs even if several candidates still pass RPS and MA filters.', 'type': 'rule', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Weak tape suppresses breakout follow-through and raises gap-down risk, so stock-level strength is less likely to convert into profitable new entries.'}
- {'text': 'Cold-sector exits should be enforced aggressively: a profitable stock in the worst sector bucket can lose leadership faster than its individual chart signals the breakdown.', 'type': 'heuristic', 'tags': ['sector', 'exit-rule', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'Sector outflows hit liquidity and sentiment across the group first, so exiting a weakening sector protects gains before individual stops are tested.'}
- {'text': 'Stop-proximity warnings become much more important in panic tapes; a stock sitting only ~1% above stop should often be sold proactively rather than managed mechanically.', 'type': 'signal', 'tags': ['exit-rule', 'timing', 'risk-management'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'In weak markets, gap risk and cascading selling can skip exact stop levels, so pre-emptive exits reduce slippage.'}
