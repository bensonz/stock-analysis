# 运行审计 2026-08-12 noon

**结论: 🟡 需要人工操作**

_生成于 2026-08-27T18:14:39+08:00_

## 需要人工操作 (13)

### [env] 阶段 collect 失败

- `phase-failed:collect`
- 无错误详情
- 处理: `python3 scripts/run_daily.py --slot noon --run`

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:47425c61`
- position 000703 (恒逸石化): price fetch error: all 3 sources failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:170cc7e6`
- position 002138 (顺络电子): price fetch error: all 3 sources failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:c4d3620a`
- position 300001 (特锐德): price fetch error: all 3 sources failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:a1a4bf64`
- position 300408 (三环集团): price fetch error: all 3 sources failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:9f956a85`
- position 600885 (宏发股份): price fetch error: all 3 sources failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:d3ec8495`
- position 603127 (昭衍新药): price fetch error: all 3 sources failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:f981b8cc`
- position 603259 (药明康德): price fetch error: all 3 sources failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:a2ab1121`
- position 688981 (中芯国际): price fetch error: all 3 sources failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:f6701cbe`
- only 0/3 major indices have valid data

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:002e6dfb`
- breadth total=0 (expected >=1000 for A-share market)

### [env] 数据健康告警: screening data is 1 session(s) stale (latest 2026-08-11, expected 2026

- `db-health-warning:50a825a4`
- screening data is 1 session(s) stale (latest 2026-08-11, expected 2026-08-12)
- 可疑位置: `scripts/pricedb.py db_health`
- 处理: `python3 scripts/pricedb.py factors verify`

### [env] 抽查 20 只、实际核对 0 只

- `db-health-spot-check-verified-nothing`
- spot_check: {"date": "2026-08-11", "sampled": 20, "checked": 0, "fetch_failures": 20, "mismatches": []}。0 处不一致来自 0 次比对，不能读作数据无误。
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
