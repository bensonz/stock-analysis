<!-- 由 scripts/doctor.py --open 生成, 不要手改. -->
<!-- 要接受某条发现, 编辑同目录的 ACCEPTED.md. -->

```
未结审计发现  (按问题归并, 不按实例)
==============================================================

## 需要改代码 (2)

  ▸ manifest_present  [invariant]
      5 次 / 5 天   2026-02-02 … 2026-04-12   最长连续 3
      改这里: scripts/run_daily.py (write the manifest before preflight)
        · 2026-02-05 afternoon 该时段没有 manifest
        · 2026-02-10 afternoon 该时段没有 manifest
        · 2026-02-11 afternoon 该时段没有 manifest
        · 2026-04-12 afternoon 该时段没有 manifest
        · … 另有 1 次更早的

  ▸ source_unhealthy  [env]
      16 次 / 13 天   2026-04-09 … 2026-08-25   最长连续 10
        · 2026-08-25 noon      数据源 sina 状态 down
        · 2026-08-25 noon      数据源 cheesefortune 状态 down
        · 2026-08-25 afternoon 数据源 sina 状态 down
        · 2026-08-25 afternoon 数据源 cheesefortune 状态 down
        · … 另有 12 次更早的


## 需要人工操作 (5)

  ▸ phase_failed  [env]
      9 次 / 9 天   2026-05-28 … 2026-08-25
      执行:   python3 scripts/run_daily.py --slot afternoon --run
        · 2026-07-20 afternoon 阶段 apply 失败
        · 2026-08-12 noon      阶段 collect 失败
        · 2026-08-20 afternoon 阶段 collect 失败
        · 2026-08-25 noon      阶段 collect 失败
        · … 另有 5 次更早的

  ▸ gate_hard_fail  [env]
      23 次 / 9 天   2026-05-28 … 2026-08-25
      执行:   python3 scripts/pricedb.py repair
        · 2026-08-25 noon      phase1_to_phase2 硬闸门拦截
        · 2026-08-25 noon      phase1_to_phase2 硬闸门拦截
        · 2026-08-25 noon      phase1_to_phase2 硬闸门拦截
        · 2026-08-25 noon      phase1_to_phase2 硬闸门拦截
        · … 另有 19 次更早的

  ▸ snapshot_wrote_rows  [env]
      1 次 / 1 天   2026-08-26
      执行:   python3 scripts/pricedb.py snapshot --date 2026-08-26 --dry-run
        · 2026-08-26 afternoon 快照写入 0 行

  ▸ db_health_warnings  [env]
      7 次 / 6 天   2026-08-12 … 2026-08-28   最长连续 2
      改这里: scripts/pricedb.py db_health
      执行:   python3 scripts/pricedb.py factors verify
        · 2026-08-24 afternoon 数据健康告警: adj factors lag prices (2026-08-21 < 2026-08-24) — run 'pricedb.py fac
        · 2026-08-25 noon      数据健康告警: adj factors lag prices (2026-08-21 < 2026-08-24) — run 'pricedb.py fac
        · 2026-08-27 afternoon 数据健康告警: adj factors lag prices (2026-08-26 < 2026-08-27) — run 'pricedb.py fac
        · 2026-08-28 afternoon 数据健康告警: adj factors lag prices (2026-08-27 < 2026-08-28) — run 'pricedb.py fac
        · … 另有 3 次更早的

  ▸ db_health_spot_check  [env]
      6 次 / 6 天   2026-08-12 … 2026-08-28
      执行:   python3 scripts/pricedb.py status
        · 2026-08-21 afternoon 抽查 20 只、实际核对 0 只
        · 2026-08-24 afternoon 抽查 20 只、实际核对 0 只
        · 2026-08-27 afternoon 抽查 20 只、实际核对 0 只
        · 2026-08-28 afternoon 抽查 20 只、实际核对 0 只
        · … 另有 2 次更早的


## 已知并接受 (1)

  ▸ new_positions_absent_from_snapshot  [invariant]
      11 次 / 8 天   2026-03-11 … 2026-08-20
      改这里: scripts/run_daily.py (newPositions written from intent, not from applied outcome)
      已接受: 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-08-20 noon 的产物保持原样不改写
        · 2026-07-31 afternoon daily_summary 声称新开 688536，持仓快照里没有
        · 2026-08-04 noon      daily_summary 声称新开 000739，持仓快照里没有
        · 2026-08-17 noon      daily_summary 声称新开 688019，持仓快照里没有
        · 2026-08-20 noon      daily_summary 声称新开 688222，持仓快照里没有
        · … 另有 7 次更早的


```
