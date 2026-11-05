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

_更新: 2026-11-05 · 共 18 条 · 待定 0 条_

## 2026-11-05 (T-0) 美国 — 美国报道：俄罗斯愿在11月4日后恢复俄美乌三方谈判
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-04   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 俄美乌谈判恢复为地缘政治动态，非已排定的系统性事件，且对A股传导有限（deepseek-v4-pro，2026-10-28）
  src: wallstreetcn imp=4 北京 2026-11-04 12:02 |
  id: wscn-20261104-a5725399

## 2026-11-05 (T-0) 中国 — 第九届中国国际进口博览会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-05   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 进博会为贸易博览会，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-05 12:02 |
  id: wscn-20261105-6153f180

## 2026-11-05 (T-0) 美国 — 美国Coherent财报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-04   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件，对A股整体影响有限（deepseek-v4-pro，2026-11-02）
  src: wallstreetcn imp=4 北京 2026-11-05 05:30 |
  id: wscn-20261105-64707b65

## 2026-11-05 (T-0) 中国 — 中国第九届上海进博会 + 虹桥论坛（11月5日-10日）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-05   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 进博会为贸易展会，非系统性政策事件，对A股整体影响有限（deepseek-v4-pro，2026-11-02）
  src: wallstreetcn imp=4 北京 2026-11-05 12:02 |
  id: wscn-20261105-f236f54f

## 2026-11-06 (T-1) 美国 — 美国Lumentum财报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-05   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件，对A股整体影响有限（deepseek-v4-pro，2026-11-02）
  src: wallstreetcn imp=4 北京 2026-11-06 06:00 |
  id: wscn-20261106-c0e222c4

## 2026-11-09 (T-4) 美国 — 美国10月非农就业人口变动(万人)
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-06   tz: US   kind: macro_release
  note:
  ai: 跳过 · medium/two_sided · 与日历上11月9日美国非农就业(NFP)重复，同一数据不同表述（deepseek-v4-pro，2026-10-29）
  src: wallstreetcn imp=4 北京 2026-11-06 21:30 | https://wallstreetcn.com/calendar/US121058/overview
  id: wscn-20261106-US121058

## 2026-11-09 (T-4) 中国 — 中国10月外汇储备(亿美元)
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-07   tz: CN   kind: macro_release
  note:
  ai: 跳过 · low/two_sided · 外汇储备数据对A股市场影响有限，非系统性宏观事件（deepseek-v4-pro，2026-10-29）
  src: wallstreetcn imp=4 北京 2026-11-07 12:02 | https://wallstreetcn.com/calendar/CN191467/overview
  id: wscn-20261107-CN191467

## 2026-11-16 (T-11) 中国 — 中国央行：自11月15日起上调金融机构外汇存款准备金率2个百分点
- [x] keep 🤖   impact: medium   direction: risk
  date: 2026-11-15   tz: CN   kind: other
  note:
  ai: 保留 · medium/risk · 上调外汇存款准备金率收紧离岸人民币流动性，影响汇率与外资情绪（deepseek-v4-pro，2026-11-03）
  src: wallstreetcn imp=4 北京 2026-11-15 00:00 |
  id: wscn-20261115-00b4a7bb

## 2026-11-17 (T-12) 美国 — 美国Anthropic IPO窗口（11月16日当周）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-16   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司IPO窗口，非系统性事件，对A股整体无实质影响（deepseek-v4-pro，2026-10-27）
  src: wallstreetcn imp=4 北京 2026-11-16 12:02 |
  id: wscn-20261116-19ce9494

## 2026-11-17 (T-12) 美国 — 美国沃什：美联储生产率与就业特别工作组将举行听证会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-16   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 美联储工作组听证会属常规程序性会议，非政策信号事件（deepseek-v4-pro，2026-10-16）
  src: wallstreetcn imp=4 北京 2026-11-16 12:02 |
  id: wscn-20261116-7d533f14

## 2026-11-17 (T-12) 中国 — 中美俄元首将于深圳APEC期间会晤？外交部回应：中方愿同各方一道，共同推动APEC“中国年”取得丰硕成果
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 外交部回应属非确定日程评论，若元首会晤确定可另行跟踪（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-67281d27

## 2026-11-17 (T-12) 中国 — 中国亚太经合组织会议（APEC）11月17日至18日在深圳举办
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · APEC整体会议与11月18日领导人会议重复，不另计（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-7268b241

## 2026-11-18 (T-13) 美国 — 美国微软开发者与IT大会（Microsoft Ignite）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-17   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 微软Ignite为公司技术大会，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-befb8c6f

## 2026-11-18 (T-13) 中国 — 中国普京出席APEC领导人非正式会议
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-18   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 普京出席系APEC领导人会议组成部分，与APEC事件重复（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-18 00:00 |
  id: wscn-20261118-35908d3e

## 2026-11-27 (T-22) 中国 — 中国商务部：中美双方约定在今年11月底前举行下一次人工智能对话
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-27   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 中美AI对话为事务性沟通，非系统性政策事件，对A股整体影响有限（deepseek-v4-pro，2026-10-13）
  src: wallstreetcn imp=4 北京 2026-11-27 12:02 |
  id: wscn-20261127-77abe93e

## 2026-12-07 (T-32) 美国 — 美国纳斯达克拟推出全新“23小时”交易时段，美东时间晚9点至凌晨4点
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 交易时段延长属市场基础设施变化，非系统性宏观事件，对A股无直接冲击（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-3ba46065

## 2026-12-07 (T-32) 美国 — 美国美股进入每天23小时的“通宵交易”的时代
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 与另一候选重复，均为美股通宵交易时段启动，非A股系统性事件（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-e4bdae4a

## 2026-12-15 (T-40) 美国 — 美国G20峰会（迈阿密）
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-12-14   tz: US   kind: other
  note:
  ai: 跳过 · medium/two_sided · G20峰会为多边论坛，非系统性政策事件，且与已有关税休战到期等事件重叠，影响有限（deepseek-v4-pro，2026-10-30）
  src: wallstreetcn imp=4 北京 2026-12-14 12:02 |
  id: wscn-20261214-514277a6
