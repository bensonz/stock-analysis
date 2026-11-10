# 运行审计 2026-11-10 noon

**结论: 🟡 需要人工操作**

_生成于 2026-11-10T13:22:34+08:00_

## 需要人工操作 (1)

### [env] 股票列表未在当日刷新（最后 2026-11-09）

- `stock-list-stale`
- 新上市股票不会进入价格库，也不会进入 RPS 与候选池。
- 可疑位置: `scripts/pricedb refresh_stock_list`
- 处理: `python3 scripts/pricedb.py stocks && python3 scripts/pricedb.py update`

## 检查覆盖

- 已执行: 15/17
- 跳过: 2
  - `check_pricedb_current` — preflight_pricedb has no latest_date/target
  - `check_snapshot_wrote_rows` — no snapshot note in preflight (run predates the writer)

> 本审计只发现，不修复；从不写入 tracking/。
> 它只能抓住已经写了检查的失败形状——没人想过的新 bug 不在覆盖内。
