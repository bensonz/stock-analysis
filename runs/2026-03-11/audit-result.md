# 运行审计 2026-03-11 afternoon

**结论: 🔴 需要改代码**

_生成于 2026-08-23T00:36:30+08:00_

## 需要改代码 (3)

### [invariant] daily_summary 声称新开 002497，持仓快照里没有

- `new-position-not-held:002497`
- newPositions 含 002497 (雅化集团)，但 positions_snapshot.activePositions 不含该代码。T+1 排除了当日开平的解释——两份产物必然有一份在说谎。
- 可疑位置: `scripts/run_daily.py (newPositions written from intent, not from applied outcome)`

### [invariant] daily_summary 声称新开 603191，持仓快照里没有

- `new-position-not-held:603191`
- newPositions 含 603191 (望变电气)，但 positions_snapshot.activePositions 不含该代码。T+1 排除了当日开平的解释——两份产物必然有一份在说谎。
- 可疑位置: `scripts/run_daily.py (newPositions written from intent, not from applied outcome)`

### [invariant] daily_summary 声称新开 600096，持仓快照里没有

- `new-position-not-held:600096`
- newPositions 含 600096 (云天化)，但 positions_snapshot.activePositions 不含该代码。T+1 排除了当日开平的解释——两份产物必然有一份在说谎。
- 可疑位置: `scripts/run_daily.py (newPositions written from intent, not from applied outcome)`

## 检查覆盖

- 已执行: 10/12
- 跳过: 2
  - `check_pricedb_current` — preflight_pricedb has no latest_date/target
  - `check_snapshot_wrote_rows` — no snapshot note in preflight (run predates the writer)

> 本审计只发现，不修复；从不写入 tracking/。
> 它只能抓住已经写了检查的失败形状——没人想过的新 bug 不在覆盖内。
