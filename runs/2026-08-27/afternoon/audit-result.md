# 运行审计 2026-08-27 afternoon

**结论: 🟡 需要人工操作**

_生成于 2026-08-27T18:14:39+08:00_

## 需要人工操作 (2)

### [env] 数据健康告警: adj factors lag prices (2026-08-26 < 2026-08-27) — run 'pricedb.py fac

- `db-health-warning:c924b422`
- adj factors lag prices (2026-08-26 < 2026-08-27) — run 'pricedb.py factors heal'
- 可疑位置: `scripts/pricedb.py db_health`
- 处理: `python3 scripts/pricedb.py factors verify`

### [env] 抽查 20 只、实际核对 0 只

- `db-health-spot-check-verified-nothing`
- spot_check: {"date": "2026-08-27", "sampled": 20, "checked": 0, "fetch_failures": 20, "mismatches": []}。0 处不一致来自 0 次比对，不能读作数据无误。
- 处理: `python3 scripts/pricedb.py status`

## 检查覆盖

- 已执行: 14/14

> 本审计只发现，不修复；从不写入 tracking/。
> 它只能抓住已经写了检查的失败形状——没人想过的新 bug 不在覆盖内。
