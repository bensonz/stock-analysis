# 运行审计 2026-08-17 noon

**结论: 🔴 需要改代码**

_生成于 2026-08-23T00:36:31+08:00_

## 需要改代码 (1)

### [invariant] daily_summary 声称新开 688019，持仓快照里没有

- `new-position-not-held:688019`
- newPositions 含 688019 (安集科技)，但 positions_snapshot.activePositions 不含该代码。T+1 排除了当日开平的解释——两份产物必然有一份在说谎。
- 可疑位置: `scripts/run_daily.py (newPositions written from intent, not from applied outcome)`

## 检查覆盖

- 已执行: 11/12
- 跳过: 1
  - `check_snapshot_wrote_rows` — no snapshot note in preflight (run predates the writer)

> 本审计只发现，不修复；从不写入 tracking/。
> 它只能抓住已经写了检查的失败形状——没人想过的新 bug 不在覆盖内。
