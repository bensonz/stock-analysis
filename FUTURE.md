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
| 2026-11-03 | deep_report 评分方程已实现（PLAN.md Stage 1–3）；Stage 4 验证未跑 | **2026-11-17 due**: 跑 docs/deep_report_scoring/PLAN.md Stage 4：002293、605098 各同日 2 次（W 差 ≤ 0.5、同档）；同日 writer=anthropic vs openai（同档、W 差 ≤ 1.0）；手评 002293 08-25 / 08-31 两份旧报告。注意 11-10→11-13 试用期 ANTHROPIC_MODEL=Fable 5.2，anthropic 臂按当时写手记录 |
| 2026-11-10 | 日常决策模型 DeepSeek V4 Pro → Fable 5.2 试用一周（owner）。`.env`: `LLM_PROVIDER=anthropic`, `ANTHROPIC_MODEL=claude-fable-5-2`（旧值留作注释；副作用：deep_report 撰写与 event triage 也用 Fable）。首跑 11-10 noon；修复 9f143c5c（relay 吞掉 temperature 400）。切换前 1 例无工具对比（11-09 afternoon）两模型决策相同，不足以下结论 | **2026-11-13 due**（周五收盘后）: 复核 11-10 noon → 11-13 afternoon 共 8 个 slot：运行状态与 doctor 结果、每次 tokens/耗时/成本、`empty stream … retrying` 次数、决策（new_positions/卖出/market_call）、数字是否可回溯。仅作描述，不作盈亏结论（样本太短）。owner 定：保留 / 回退（还原两行注释） |

## Resolved

| date | event | outcome |
|---|---|---|
| 2026-09-01 | deep_report TEMPERATURE 0.5→1.0（同日双跑 4/5+4/5，判定边界陡而非骰子问题） | **2026-11-03 落地**: owner 批准 PROPOSAL 并实现（8239546a、293d337c、8ff1785d）——代码按锚定 scorecard 计算评级，模型不再写评级；TEMPERATURE 定为 1.0。11-03 周审写下的 11-10 due 早于批准，属过期条目（11-10 移入）。Stage 4 验证另列 Open，due 2026-11-17 |
| 2026-09-01 | web_fetch 稀薄结果升级 crawl4ai（预算 3/run）+ web_screenshot 上线 | **2026-11-03 KEEP**: 09-01→11-03 共 72 次运行、153 次 web_fetch，升级触发 8 次、成功 5、失败 3（均 wallstreetcn 60s 超时）、预算耗尽 0。web_screenshot 0 次调用（openai 循环无此工具）——去留列入周审 owner 项。llm_meta.json 不记升级结果，只能从 pipeline.log 反推 |
| 2026-08-28 | CANDIDATE_ALPHA 审计发现 Rule 2b 距离门（❌/🔻，FUTURE 原文误称"MA 对齐门"）在 20 日口径反向（+8.75pt gap） | **2026-11-03 不成立**: 样本外 08-27→ 20 日 gap −1.90pt（聚类 −3.90，t=−1.41，fail>ok 仅 2/11 日）——门的方向正确；❌ 上方 −9.55%（n=46/17 码）。条件未满足，不提 Rule 2b 提案。OOS 仅 11 个日期、单一下跌段，偏弱证据 |
| 2026-10-08 | 账本开始记入分红/送转（000739 与 603259 两笔待回补，干跑合计到账 326.74） | **2026-11-03 通过（实质）**: 10-09 noon 两笔均带 corporateActions（净 189.04 + 137.7 = 326.74），realizedPnl 变动 +870.74 精确对账，Gate 3 两条 dividend，此后无新 invariant（10-09 noon manifest-absent 为 doctor 早于流水线完成的竞态）。字面条件 `dividendCash == 326.74` 设计上不可能成立：该字段只算持仓中的票，000739 同 slot 卖出。至今共 4 笔分红净 1221.94 |
| 2026-09-01 | pit_archive 复活（审计 B7，owner: "revive and come back later"） | **2026-11-03 删除（owner 决定）**: 复活两个月无任何代码读取 archive/；4 源上游可随时重抓（10-15 全量回填仅 20 分钟）。删除 scripts/pit_archive.py、测试、launchd 任务 com.bz.stock-pit 与 archive/（31M，git 历史可找回） |
| 2026-08-04 | 市场机制读数 regime detector v1.1 上线（只读实验：ic20 + stop10，不接规则、不进提示词） | **2026-11-03 下线（owner 决定）**: 08-05→11-03 共 112 次读数。与实际一致率 32%，而恒报"逆风"为 73%；转折点平均晚约 11 个交易日，4 次转折中 3 次反向翻转；顺风 0/112。`--retro` 有前视，阈值是事后拟合的。删除 scripts/regime_detector.py、测试、报告区段与网站徽章；gex_audition Q4 自带止损率函数副本。旧 runs/*/input/regime.json 保留为历史 |
