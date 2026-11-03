# FUTURE.md — deferred checks with due dates

Things we decided to revisit *later, on purpose*. One line each:
`date decided | what happened | future event (with a DUE date)`.

Rules for this file:
- Every entry carries a **due date** — "later" without a date is how the
  regime experiment below went unreviewed for a month.
- Reviewed weekly: `agents/WEEKLY_AUDIT.md` has a standing step that reads
  this file and flags anything due.
- Resolved entries move to the **Resolved** section with the outcome — never
  deleted, so the record of what we deferred and why survives.

## Open

| date | event | future event |
|---|---|---|
| 2026-08-04 | 市场机制读数 regime detector v1.1 上线（只读实验：ic20 + stop10，不接规则、不进提示词，报告区段「市场机制读数（只读实验）」） | **2026-10-12 due**: 拉取 8/04 以来全部读数 vs 实际行情，回答"这两个滞后指标在转折点晚多少、有没有一次提前"；决定 接入规则 / 继续只读 / 下线。**2026-11-03 周审已取证**（docs/audits/WEEKLY_2026-11-03.md）：与实际一致率 32%（恒报逆风基线 73%），滞后约 11 个交易日，顺风 0/112 次，`--retro` 有前视 → **2026-11-10 due**: owner 三选一 |
| 2026-09-01 | deep_report TEMPERATURE 0.5→1.0（同日双跑 4/5+4/5，判定边界陡而非骰子问题） | **2026-09-15 due**: 若评分方程（docs/deep_report_scoring/PROPOSAL.md）已批准落地，跑验证计划（同日 2×2 股 + 跨模型）；未批准则催决策。**2026-11-03 周审**：PROPOSAL 仍"awaiting owner approval"，未实现，验证计划无从跑；新反例 600150 10-03 同日同数据 4/5 vs 3/5 → **2026-11-10 due**: owner 批/驳 PROPOSAL，并定 TEMPERATURE |

## Resolved

| date | event | outcome |
|---|---|---|
| 2026-09-01 | web_fetch 稀薄结果升级 crawl4ai（预算 3/run）+ web_screenshot 上线 | **2026-11-03 KEEP**: 09-01→11-03 共 72 次运行、153 次 web_fetch，升级触发 8 次、成功 5、失败 3（均 wallstreetcn 60s 超时）、预算耗尽 0。web_screenshot 0 次调用（openai 循环无此工具）——去留列入周审 owner 项。llm_meta.json 不记升级结果，只能从 pipeline.log 反推 |
| 2026-08-28 | CANDIDATE_ALPHA 审计发现 Rule 2b 距离门（❌/🔻，FUTURE 原文误称"MA 对齐门"）在 20 日口径反向（+8.75pt gap） | **2026-11-03 不成立**: 样本外 08-27→ 20 日 gap −1.90pt（聚类 −3.90，t=−1.41，fail>ok 仅 2/11 日）——门的方向正确；❌ 上方 −9.55%（n=46/17 码）。条件未满足，不提 Rule 2b 提案。OOS 仅 11 个日期、单一下跌段，偏弱证据 |
| 2026-10-08 | 账本开始记入分红/送转（000739 与 603259 两笔待回补，干跑合计到账 326.74） | **2026-11-03 通过（实质）**: 10-09 noon 两笔均带 corporateActions（净 189.04 + 137.7 = 326.74），realizedPnl 变动 +870.74 精确对账，Gate 3 两条 dividend，此后无新 invariant（10-09 noon manifest-absent 为 doctor 早于流水线完成的竞态）。字面条件 `dividendCash == 326.74` 设计上不可能成立：该字段只算持仓中的票，000739 同 slot 卖出。至今共 4 笔分红净 1221.94 |
| 2026-09-01 | pit_archive 复活（审计 B7，owner: "revive and come back later"） | **2026-11-03 删除（owner 决定）**: 复活两个月无任何代码读取 archive/；4 源上游可随时重抓（10-15 全量回填仅 20 分钟）。删除 scripts/pit_archive.py、测试、launchd 任务 com.bz.stock-pit 与 archive/（31M，git 历史可找回） |
