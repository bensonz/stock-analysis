# 运行审计 2026-09-02 noon

**结论: 🟡 需要人工操作**

_生成于 2026-09-02T15:25:04+08:00_

## 需要人工操作 (8)

### [env] 阶段 collect 失败

- `phase-failed:collect`
- 无错误详情
- 处理: `python3 scripts/run_daily.py --slot noon --run`

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:47425c61`
- position 000703 (恒逸石化): price fetch error: all 3 sources failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:b4e3b3c0`
- position 002913 (奥士康): price fetch error: all 3 sources failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:f981b8cc`
- position 603259 (药明康德): price fetch error: all 3 sources failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:f6701cbe`
- only 0/3 major indices have valid data

### [env] phase1_to_phase2 硬闸门拦截

- `gate-hard-fail:phase1_to_phase2:002e6dfb`
- breadth total=0 (expected >=1000 for A-share market)

### [env] 数据源 sina 状态 down

- `source-unhealthy:sina`
- {"status": "down", "error": "HTTPSConnectionPool(host='hq.sinajs.cn', port=443): Max retries exceeded with url: /list=s_sh000001 (Caused by NameResolutionError(\"HTTPSConnection(host='hq.sinajs.cn', port=443): Failed to resolve 'hq.sinajs.cn' ([Errno 8] nodename nor servname provided, or not known)\"))"}

### [env] 数据源 cheesefortune 状态 down

- `source-unhealthy:cheesefortune`
- {"status": "down", "error": "<urlopen error [Errno 8] nodename nor servname provided, or not known>"}

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
