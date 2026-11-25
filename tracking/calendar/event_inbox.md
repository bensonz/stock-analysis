# 事件收件箱 (event inbox)

> 由 `python3 scripts/event_inbox.py refresh` 生成，每次流水线运行自动刷新
> （来源: 华尔街见闻财经日历，重要性>=4，未来45天）。新候选由 AI 先决定（🤖 + `ai:` 行），
> 保留的立即写入 `tracking/calendar/events.json`。你不必打开这里；想推翻就直接改：
>
> - 🤖 项: 改勾选或任一字段 = 推翻 AI，你的版本生效（`[-]` 从 events.json 撤下，`[x]` 写入，
>   改 impact/direction 等 = 更新条目，`[ ]` = 撤回 AI 决定、留给你定）。🤖 项在A股影响日过后自动移出
> - `[x]` 保留 → 下次运行（或 `python3 scripts/event_inbox.py promote`）写入 `tracking/calendar/events.json`
> - `[-]` 跳过 → 记入台账，不再出现
> - `[ ]` 待定 → 留在这里
>
> 可直接改: 标题里 `—` 后的名称、`impact` (high/medium/low)、`direction` (risk/two_sided/supportive)、
> `date`、`tz` (US=影响其后第一个A股交易日 / CN=当日)、`kind`、`note`。不要改 `ai:`、`src:` 和 `id:` 三行（🤖 可留可删）。
> 标题日期 = A股影响日，由 date+tz 推算，重写时刷新。规则与局限: docs/EVENT_INBOX/DECISIONS.md

_更新: 2026-11-25 · 共 12 条 · 待定 0 条_

## 2026-11-25 (T-0) 中国 — 中国美团Q3电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-25   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性重要公司，不构成A股整体驱动（deepseek-v4-pro，2026-11-23）
  src: wallstreetcn imp=4 北京 2026-11-25 19:00 |
  id: wscn-20261125-367fd332

## 2026-11-26 (T-1) 美国 — 美国10月PCE物价指数环比
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-25   tz: US   kind: macro_release
  note:
  ai: 保留 · medium/two_sided · 美联储最关注的通胀指标，影响12月FOMC降息预期，进而影响A股风险偏好（deepseek-v4-pro，2026-11-20）
  src: wallstreetcn imp=4 北京 2026-11-25 21:30 | https://wallstreetcn.com/calendar/US111046/overview
  id: wscn-20261125-US111046

## 2026-11-26 (T-1) 美国 — 美国10月核心PCE物价指数环比
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-25   tz: US   kind: macro_release
  note:
  ai: 跳过 · medium/two_sided · 与PCE物价指数同一时间发布，核心PCE已包含在整体PCE数据中，避免重复（deepseek-v4-pro，2026-11-20）
  src: wallstreetcn imp=4 北京 2026-11-25 21:30 | https://wallstreetcn.com/calendar/US111047/overview
  id: wscn-20261125-US111047

## 2026-11-27 (T-2) 中国 — 中国商务部：中美双方约定在今年11月底前举行下一次人工智能对话
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-27   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 中美AI对话为事务性沟通，非系统性政策事件，对A股整体影响有限（deepseek-v4-pro，2026-10-13）
  src: wallstreetcn imp=4 北京 2026-11-27 12:02 |
  id: wscn-20261127-77abe93e

## 2026-12-02 (T-7) 美国 — 黄仁勋12月1日出席美国国会听证会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-01   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司高管国会听证，非系统性政策事件，对A股整体影响有限（deepseek-v4-pro，2026-11-18）
  src: wallstreetcn imp=4 北京 2026-12-01 12:02 |
  id: wscn-20261201-76439df1

## 2026-12-07 (T-12) 美国 — 美国特朗普将对多晶硅及其衍生产品加征关税
- [x] keep 🤖   impact: medium   direction: risk
  date: 2026-12-04   tz: US   kind: other
  note:
  ai: 保留 · medium/risk · 美国对多晶硅加征关税，直接冲击中国光伏产业链出口，对A股相关板块构成下行风险（deepseek-v4-pro，2026-11-17）
  src: wallstreetcn imp=4 北京 2026-12-04 00:00 |
  id: wscn-20261204-fbc64ee6

## 2026-12-07 (T-12) 美国 — 美国纳斯达克拟推出全新“23小时”交易时段，美东时间晚9点至凌晨4点
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 交易时段延长属市场基础设施变化，非系统性宏观事件，对A股无直接冲击（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-3ba46065

## 2026-12-07 (T-12) 美国 — 美国美股进入每天23小时的“通宵交易”的时代
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 与另一候选重复，均为美股通宵交易时段启动，非A股系统性事件（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-e4bdae4a

## 2026-12-14 (T-19) 美国 — 12月11日：美国政府拨款到期日
- [x] keep 🤖   impact: medium   direction: risk
  date: 2026-12-11   tz: US   kind: other
  note:
  ai: 保留 · medium/risk · 美国政府拨款到期，若停摆将扰动全球风险偏好，对A股有外溢压力（deepseek-v4-pro，2026-11-25）
  src: wallstreetcn imp=4 北京 2026-12-11 00:00 |
  id: wscn-20261211-ad2c14ce

## 2026-12-15 (T-20) 美国 — 美国G20峰会（迈阿密）
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-12-14   tz: US   kind: other
  note:
  ai: 跳过 · medium/two_sided · G20峰会为多边论坛，非系统性政策事件，且与已有关税休战到期等事件重叠，影响有限（deepseek-v4-pro，2026-10-30）
  src: wallstreetcn imp=4 北京 2026-12-14 12:02 |
  id: wscn-20261214-514277a6

## 2026-12-15 (T-20) 美国 — 美国2026年迈阿密G20领导人峰会（12月14日–15日）
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-12-14   tz: US   kind: other
  note:
  ai: 保留 · medium/two_sided · G20峰会涉及中美关系与贸易政策，可能释放系统性信号（deepseek-v4-pro，2026-11-25）
  src: wallstreetcn imp=4 北京 2026-12-14 00:00 |
  id: wscn-20261214-ea87ba7f

## 2027-01-04 (T-40) 美国 — 1月3日：美国第120届国会宣誓就职
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2027-01-03   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 美国国会换届属常规政治日程，对A股无直接系统性影响（deepseek-v4-pro，2026-11-25）
  src: wallstreetcn imp=4 北京 2027-01-03 12:02 |
  id: wscn-20270103-03b7842e
