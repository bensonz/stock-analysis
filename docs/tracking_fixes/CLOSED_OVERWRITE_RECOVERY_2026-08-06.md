# closed/ 覆盖丢单恢复 (2026-08-06)

## 症状 → 根因

组合总览网站开发中，06-09 开仓的持仓规模在 `tracking/closed/` 里查不到对应记录
（300236 的 closed 文件 entryDate 是 07-14 而非 06-09）。根因：
`position_manager.close_position` 写 `closed/{code}.json` —— **同一代码再次
建仓并平仓时直接覆盖旧回合**。`compute_realized_pnl()` 扫描 closed/ 求和，
每次覆盖即刻从账上抹掉旧回合的已实现盈亏 → 现金/总资产错报。

## 损失清单（9 笔，全部从 git 历史恢复）

对照法: runs/*/output/daily_summary.json 的 46 条 SELL 动作 vs closed/ 42 个文件；
恢复法: `git show <该文件最新提交>^:tracking/closed/<code>.json`（覆盖前版本）。

| 回合 | 持有 | 收益 | 已实现(元) |
|------|------|------|-----------|
| 300373 扬杰科技 02-13→03-03 | 18d | -8.21%¹ | (无shares, 按10%仓位推算) |
| 600499 科达制造 02-25→03-10 | 13d | +1.83% | (无shares, 同上) |
| 300037 新宙邦 06-09→06-10 | 1d | -5.29% | -794 |
| 002947 恒铭达 06-09→06-22 | 13d | +2.79% | +699 |
| 300438 鹏辉能源 06-30→07-01 | 1d | -3.24% | -1,068 |
| 300236 上海新阳 06-09→07-02 | 23d | **+29.82%** | **+11,208** |
| 688401 路维光电 06-09→07-02 | 23d | **+30.89%** | **+4,484** |
| 000811 冰轮环境 07-23→07-24 | 1d | -3.85% | -1,320 |
| 002821 凯莱英 07-24²→07-24 | 1d | -3.25% | -1,064 |

¹ tracker 文件 -8.21% vs 当日 summary -8.37%，差 0.16pp，以 tracker 文件为准（已在恢复文件 `_recovered.note` 标注）。
² 文件记录 entryDate=07-23。

恢复文件命名 `{code}_{exitDate}.json`，含 `_recovered` 元数据（来源提交、日期、原因）。

## 账面修正（2026-08-06 noon 价格标记）

| | 修正前 | 修正后 |
|---|---|---|
| realizedPnl | -53,808 | **-47,616** (+6,192) |
| totalEquity | 964,319 | **970,511** |
| totalReturnPct | -3.57% | **-2.95%** |

已平仓交易 42 → 51 笔。注意历史快照(runs/*/positions_snapshot.json)**不回改**——
它们如实记录当时账面（含当时的错误），资产曲线上 07-02 后的一段因此系统性低估
约 1.5 万元（300236/688401 两笔 +30% 盈利在 07-15 覆盖时被抹掉）。曲线自本日起
为修正后口径。

## 结构修复

- `position_manager.close_position` → 写 `closed/{code}_{exitDate}.json`（唯一名）。
  所有读方 (`compute_realized_pnl` / `build_site.load_closed_trades` /
  `backtest.load_closed_trades`) 均 glob `*.json` 读字段，文件名无耦合（已核查）。
- `agents/TRACKER.md` Step 3 命名规范同步更新。
- 回归测试: `scripts/test_pipeline.py::test_reclose_after_reentry_keeps_both_round_trips`。

## 复查命令

```bash
# 对照 summary SELL 数与 closed 文件数（应一致: 51 = 46 SELL + 5 无SELL动作的早期平仓）
ls tracking/closed/ | wc -l
# 任一恢复文件的来源验证
git show $(git log -1 --format=%h -- tracking/closed/300236.json)^:tracking/closed/300236.json
```
