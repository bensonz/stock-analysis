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
| 2026-08-04 | 市场机制读数 regime detector v1.1 上线（只读实验：ic20 + stop10，不接规则、不进提示词，报告区段「市场机制读数（只读实验）」） | **2026-10-12 due**: 拉取 8/04 以来全部读数 vs 实际行情，回答"这两个滞后指标在转折点晚多少、有没有一次提前"；决定 接入规则 / 继续只读 / 下线 |
| 2026-09-01 | pit_archive 复活（审计 B7，owner: "revive and come back later"）：接入 run_scheduled.sh，历史回填已启动（4 源 × 2024-12-17 起） | **2026-10-01 due**: `pit_archive.py status` 应显示 4 源全部追平；检查是否有任何研究真的消费了 archive/；无人消费 → 记录成本并再议 keep/kill |
| 2026-09-01 | deep_report TEMPERATURE 0.5→1.0（同日双跑 4/5+4/5，判定边界陡而非骰子问题） | **2026-09-15 due**: 若评分方程（docs/deep_report_scoring/PROPOSAL.md）已批准落地，跑验证计划（同日 2×2 股 + 跨模型）；未批准则催决策 |
| 2026-09-01 | web_fetch 稀薄结果升级 crawl4ai（预算 3/run）+ web_screenshot 上线 | **2026-10-01 due**: 扫 llm_meta.json 统计升级触发次数/成功率/预算耗尽次数；从未触发或全失败 → 简化或下线 |
| 2026-08-28 | CANDIDATE_ALPHA 审计发现 MA 对齐门在 20 日口径反向（+8.75pt gap），结论"需更长窗口复现后再动规则" | **2026-11-01 due**: 数据多两个月后重跑 `python3 scripts/research/candidate_alpha.py --human`，MA-gate 结论仍成立 → 提改 Rule 2b 的正式提案 |

## Resolved

| date | event | outcome |
|---|---|---|
