# 运行审计 2026-09-03 afternoon

**结论: 🟡 需要人工操作**

_生成于 2026-09-03T15:25:05+08:00_

## 需要人工操作 (3)

### [env] 阶段 llm_analysis 失败

- `phase-failed:llm_analysis`
- 无错误详情
- 处理: `python3 scripts/run_daily.py --slot afternoon --run`

### [env] phase2_to_phase3 硬闸门拦截

- `gate-hard-fail:phase2_to_phase3:ba2bd65b`
- new position 600988: missing required field 'target'

### [env] 抽查 20 只、实际核对 0 只

- `db-health-spot-check-verified-nothing`
- spot_check: {"date": "2026-09-03", "sampled": 20, "checked": 0, "fetch_failures": 20, "mismatches": []}。0 处不一致来自 0 次比对，不能读作数据无误。
- 处理: `python3 scripts/pricedb.py status`

## 检查覆盖

- 已执行: 9/14
- 跳过: 5
  - `check_new_positions_absent_from_snapshot` — snapshot missing or unreadable
  - `check_action_on_code_not_held` — snapshot missing or unreadable
  - `check_sold_position_still_held` — snapshot missing or unreadable
  - `check_duplicate_active_positions` — snapshot missing or unreadable
  - `check_postrun_marks_are_from_run_day` — snapshot missing or unreadable

> 本审计只发现，不修复；从不写入 tracking/。
> 它只能抓住已经写了检查的失败形状——没人想过的新 bug 不在覆盖内。
