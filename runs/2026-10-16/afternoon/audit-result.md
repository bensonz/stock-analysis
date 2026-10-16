# 运行审计 2026-10-16 afternoon

**结论: 🟡 需要人工操作**

_生成于 2026-10-16T16:02:53+08:00_

## 需要人工操作 (3)

### [env] 数据源 sina 状态 down

- `source-unhealthy:sina`
- {"status": "down", "error": "HTTPSConnectionPool(host='hq.sinajs.cn', port=443): Max retries exceeded with url: /list=s_sh000001 (Caused by NameResolutionError(\"HTTPSConnection(host='hq.sinajs.cn', port=443): Failed to resolve 'hq.sinajs.cn' ([Errno 8] nodename nor servname provided, or not known)\"))"}

### [env] 数据源 cheesefortune 状态 down

- `source-unhealthy:cheesefortune`
- {"status": "down", "error": "<urlopen error [Errno 8] nodename nor servname provided, or not known>"}

### [env] 数据健康告警: adj factors lag prices (2026-10-15 < 2026-10-16) — run 'pricedb.py fac

- `db-health-warning:c924b422`
- adj factors lag prices (2026-10-15 < 2026-10-16) — run 'pricedb.py factors heal'
- 可疑位置: `scripts/pricedb.py db_health`
- 处理: `python3 scripts/pricedb.py factors verify`

## 检查覆盖

- 已执行: 17/17

> 本审计只发现，不修复；从不写入 tracking/。
> 它只能抓住已经写了检查的失败形状——没人想过的新 bug 不在覆盖内。
