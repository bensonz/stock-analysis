# 运行审计 2026-04-12 afternoon

**结论: 🔴 需要改代码**

_生成于 2026-08-23T23:53:14+08:00_

## 需要改代码 (1)

### [invariant] 该时段没有 manifest

- `manifest-absent`
- 运行目录存在但没有 manifest.json——无法区分'跑了但死在写清单前'与'根本没跑'。预检失败零留痕就是这个洞。
- 可疑位置: `scripts/run_daily.py (write the manifest before preflight)`

## 检查覆盖

- 已执行: 0/12

> 本审计只发现，不修复；从不写入 tracking/。
> 它只能抓住已经写了检查的失败形状——没人想过的新 bug 不在覆盖内。
