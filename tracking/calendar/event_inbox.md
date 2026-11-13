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

_更新: 2026-11-13 · 共 22 条 · 待定 0 条_

## 2026-11-16 (T-3) 中国 — 中国央行：自11月15日起上调金融机构外汇存款准备金率2个百分点
- [x] keep 🤖   impact: medium   direction: risk
  date: 2026-11-15   tz: CN   kind: other
  note:
  ai: 保留 · medium/risk · 上调外汇存款准备金率收紧离岸人民币流动性，影响汇率与外资情绪（deepseek-v4-pro，2026-11-03）
  src: wallstreetcn imp=4 北京 2026-11-15 00:00 |
  id: wscn-20261115-00b4a7bb

## 2026-11-16 (T-3) 中国 — 中国百度Q3财报与电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-16   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-16 20:30 |
  id: wscn-20261116-03051ef9

## 2026-11-16 (T-3) 中国 — 中国10月规模以上工业增加值同比
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-16   tz: CN   kind: macro_release
  note:
  ai: 保留 · medium/two_sided · 中国10月工业增加值反映经济动能，影响A股周期板块与整体风险偏好（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-16 10:00 | https://wallstreetcn.com/calendar/CN141330/overview
  id: wscn-20261116-CN141330

## 2026-11-16 (T-3) 中国 — 中国10月社会消费品零售总额同比
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-16   tz: CN   kind: macro_release
  note:
  ai: 保留 · medium/two_sided · 中国10月社零反映消费复苏力度，影响A股消费板块与宏观预期（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-16 10:00 | https://wallstreetcn.com/calendar/CN171405/overview
  id: wscn-20261116-CN171405

## 2026-11-17 (T-4) 美国 — 美国Anthropic IPO窗口（11月16日当周）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-16   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司IPO窗口，非系统性事件，对A股整体无实质影响（deepseek-v4-pro，2026-10-27）
  src: wallstreetcn imp=4 北京 2026-11-16 12:02 |
  id: wscn-20261116-19ce9494

## 2026-11-17 (T-4) 美国 — 美国沃什：美联储生产率与就业特别工作组将举行听证会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-16   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 美联储工作组听证会属常规程序性会议，非政策信号事件（deepseek-v4-pro，2026-10-16）
  src: wallstreetcn imp=4 北京 2026-11-16 12:02 |
  id: wscn-20261116-7d533f14

## 2026-11-17 (T-4) 中国 — 中国京东Q3财报与电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-17 20:00 |
  id: wscn-20261117-441050e5

## 2026-11-17 (T-4) 中国 — 中美俄元首将于深圳APEC期间会晤？外交部回应：中方愿同各方一道，共同推动APEC“中国年”取得丰硕成果
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 外交部回应属非确定日程评论，若元首会晤确定可另行跟踪（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-67281d27

## 2026-11-17 (T-4) 中国 — 中国亚太经合组织会议（APEC）11月17日至18日在深圳举办
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · APEC整体会议与11月18日领导人会议重复，不另计（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-7268b241

## 2026-11-18 (T-5) 美国 — 美国微软开发者与IT大会（Microsoft Ignite）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-17   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 微软Ignite为公司技术大会，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-befb8c6f

## 2026-11-18 (T-5) 中国 — 中国普京出席APEC领导人非正式会议
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-18   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 普京出席系APEC领导人会议组成部分，与APEC事件重复（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-18 00:00 |
  id: wscn-20261118-35908d3e

## 2026-11-18 (T-5) 美国 — 美国英伟达Q3财报与电话会
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: US   kind: other
  note:
  ai: 保留 · medium/two_sided · 英伟达财报影响全球AI产业链情绪，对A股算力与科技板块有传导效应（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-18 06:00 |
  id: wscn-20261118-646a4873

## 2026-11-18 (T-5) 中国 — 中国腾讯Q3财报与电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-18   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-18 20:00 |
  id: wscn-20261118-e4445883

## 2026-11-19 (T-6) 美国 — 黄仁勋出席美国国会听证会，就绯闻作情况说明
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-18   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司高管听证会，非系统性事件，对A股整体影响有限（deepseek-v4-pro，2026-11-09）
  src: wallstreetcn imp=4 北京 2026-11-18 12:02 |
  id: wscn-20261118-c425eb3b

## 2026-11-19 (T-6) 美国 — 美国Anthropic IPO 定价
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-18   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司IPO定价，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-18 12:02 |
  id: wscn-20261118-eb340fe4

## 2026-11-19 (T-6) 美国 — 美国英伟达临时CEO召开全体员工会议
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-18   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司内部会议，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-19 01:00 |
  id: wscn-20261119-cddf248a

## 2026-11-19 (T-6) 中国 — 中国阿里巴巴Q3财报与电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-19   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-19 20:00 |
  id: wscn-20261119-d3fe72f1

## 2026-11-20 (T-7) 美国 — 美国Anthropic 纳斯达克上市
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-19   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司上市，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-19 21:30 |
  id: wscn-20261119-86d16232

## 2026-11-27 (T-14) 中国 — 中国商务部：中美双方约定在今年11月底前举行下一次人工智能对话
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-27   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 中美AI对话为事务性沟通，非系统性政策事件，对A股整体影响有限（deepseek-v4-pro，2026-10-13）
  src: wallstreetcn imp=4 北京 2026-11-27 12:02 |
  id: wscn-20261127-77abe93e

## 2026-12-07 (T-24) 美国 — 美国纳斯达克拟推出全新“23小时”交易时段，美东时间晚9点至凌晨4点
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 交易时段延长属市场基础设施变化，非系统性宏观事件，对A股无直接冲击（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-3ba46065

## 2026-12-07 (T-24) 美国 — 美国美股进入每天23小时的“通宵交易”的时代
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 与另一候选重复，均为美股通宵交易时段启动，非A股系统性事件（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-e4bdae4a

## 2026-12-15 (T-32) 美国 — 美国G20峰会（迈阿密）
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-12-14   tz: US   kind: other
  note:
  ai: 跳过 · medium/two_sided · G20峰会为多边论坛，非系统性政策事件，且与已有关税休战到期等事件重叠，影响有限（deepseek-v4-pro，2026-10-30）
  src: wallstreetcn imp=4 北京 2026-12-14 12:02 |
  id: wscn-20261214-514277a6
