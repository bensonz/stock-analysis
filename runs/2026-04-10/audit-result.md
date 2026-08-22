# 运行审计 2026-04-10 afternoon

**结论: 🟡 需要人工操作**

_生成于 2026-08-23T00:36:30+08:00_

## 需要人工操作 (1)

### [env] 数据源 eastmoney 状态 down

- `source-unhealthy:eastmoney`
- {"status": "down", "error": "<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1006)>"}
- **连续第 2 次**（始于 2026-04-09）

## 检查覆盖

- 已执行: 10/12
- 跳过: 2
  - `check_pricedb_current` — preflight_pricedb has no latest_date/target
  - `check_snapshot_wrote_rows` — no snapshot note in preflight (run predates the writer)

> 本审计只发现，不修复；从不写入 tracking/。
> 它只能抓住已经写了检查的失败形状——没人想过的新 bug 不在覆盖内。
