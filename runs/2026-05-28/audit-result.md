# 运行审计 2026-05-28 afternoon

**结论: 🟡 需要人工操作**

_生成于 2026-08-23T00:36:31+08:00_

## 需要人工操作 (4)

### [env] 阶段 llm_analysis 失败

- `phase-failed:llm_analysis`
- 无错误详情
- 处理: `python3 scripts/run_daily.py --slot afternoon --run`

### [env] phase2_to_phase3 硬闸门拦截

- `gate-hard-fail:phase2_to_phase3:ba2bd65b`
- new position 688002: missing required field 'target'

### [env] phase2_to_phase3 硬闸门拦截

- `gate-hard-fail:phase2_to_phase3:ba2bd65b`
- new position 600301: missing required field 'target'

### [env] phase2_to_phase3 硬闸门拦截

- `gate-hard-fail:phase2_to_phase3:ba2bd65b`
- new position 002812: missing required field 'target'

## 检查覆盖

- 已执行: 10/12
- 跳过: 2
  - `check_postrun_marks_are_from_run_day` — no positions to mark
  - `check_snapshot_wrote_rows` — no snapshot note in preflight (run predates the writer)

> 本审计只发现，不修复；从不写入 tracking/。
> 它只能抓住已经写了检查的失败形状——没人想过的新 bug 不在覆盖内。
