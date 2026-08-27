# 运行审计 2026-08-20 afternoon

**结论: 🟡 需要人工操作**

_生成于 2026-08-27T18:14:39+08:00_

## 需要人工操作 (5)

### [env] 阶段 collect 失败

- `phase-failed:collect`
- 无错误详情
- 处理: `python3 scripts/run_daily.py --slot afternoon --run`

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:bc693771`
- latest price day is partial (454 rows vs ~5210) — run 'pricedb.py repair'
- 处理: `python3 scripts/pricedb.py repair`

### [env] 数据健康告警: latest day 2026-08-20 is PARTIAL (454 rows vs ~5210 normal) — run 'pri

- `db-health-warning:84ad516e`
- latest day 2026-08-20 is PARTIAL (454 rows vs ~5210 normal) — run 'pricedb.py repair'
- 可疑位置: `scripts/pricedb.py db_health`
- 处理: `python3 scripts/pricedb.py factors verify`

### [env] 数据健康告警: adj factors lag prices (2026-08-19 < 2026-08-20) — run 'pricedb.py fac

- `db-health-warning:c924b422`
- adj factors lag prices (2026-08-19 < 2026-08-20) — run 'pricedb.py factors heal'
- 可疑位置: `scripts/pricedb.py db_health`
- 处理: `python3 scripts/pricedb.py factors verify`

### [env] 抽查 20 只、实际核对 0 只

- `db-health-spot-check-verified-nothing`
- spot_check: {"date": "2026-08-20", "sampled": 20, "checked": 0, "fetch_failures": 20, "mismatches": []}。0 处不一致来自 0 次比对，不能读作数据无误。
- 处理: `python3 scripts/pricedb.py status`

## 检查覆盖

- 已执行: 8/14
- 跳过: 6
  - `check_new_positions_absent_from_snapshot` — snapshot missing or unreadable
  - `check_action_on_code_not_held` — snapshot missing or unreadable
  - `check_sold_position_still_held` — snapshot missing or unreadable
  - `check_duplicate_active_positions` — snapshot missing or unreadable
  - `check_postrun_marks_are_from_run_day` — snapshot missing or unreadable
  - `check_snapshot_wrote_rows` — no snapshot note in preflight (run predates the writer)

> 本审计只发现，不修复；从不写入 tracking/。
> 它只能抓住已经写了检查的失败形状——没人想过的新 bug 不在覆盖内。
