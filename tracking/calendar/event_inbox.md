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

_更新: 2026-10-28 · 共 29 条 · 待定 0 条_

## 2026-10-28 (T-0) 韩国 — 韩国SK海力士三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-28   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-28 08:00 |
  id: wscn-20261028-1e9f939f

## 2026-10-28 (T-0) 韩国 — 韩国SK海力士三季报及电话会（预计时间）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-28   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报，SK海力士虽为半导体龙头但非系统性影响A股整体的事件（deepseek-v4-pro，2026-10-16）
  src: wallstreetcn imp=4 北京 2026-10-28 12:02 |
  id: wscn-20261028-b84a6961

## 2026-10-29 (T-1) 美国 — 美国谷歌三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-28   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 04:30 |
  id: wscn-20261029-4acfa391

## 2026-10-29 (T-1) 韩国 — 韩国三星电子三季报及电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-29   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 三星电子财报为单一公司事件，对A股整体市场无系统性影响（deepseek-v4-pro，2026-10-16）
  src: wallstreetcn imp=4 北京 2026-10-29 09:00 |
  id: wscn-20261029-6a652201

## 2026-10-29 (T-1) 美国 — 美国微软三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-28   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 05:00 |
  id: wscn-20261029-7da9f94e

## 2026-10-29 (T-1) 欧元区 — 欧元区欧洲央行主要再融资利率
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-29   tz: CN   kind: macro_release
  note:
  ai: 保留 · medium/two_sided · 欧央行利率决议影响全球流动性与风险偏好，对A股有传导效应（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 21:15 | https://wallstreetcn.com/calendar/EA192061/overview
  id: wscn-20261029-EA192061

## 2026-10-29 (T-1) 韩国 — 韩国三星电子三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-29   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 09:00 |
  id: wscn-20261029-c5c83746

## 2026-10-29 (T-1) 美国 — 美国美联储主席沃什召开货币政策新闻发布会
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-28   tz: US   kind: other
  note:
  ai: 跳过 · medium/two_sided · 与FOMC决议同日，已在日历中覆盖，不重复记录（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 02:30 |
  id: wscn-20261029-d84ebcc1

## 2026-10-30 (T-2) 美国 — 美国9月核心PCE物价指数环比
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-29   tz: US   kind: macro_release
  note:
  ai: 保留 · medium/two_sided · 核心PCE为美联储关注的核心通胀指标，影响全球利率预期（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 20:30 | https://wallstreetcn.com/calendar/US111047/overview
  id: wscn-20261029-US111047

## 2026-10-30 (T-2) 美国 — 美国英特尔三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-29   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-30 05:00 |
  id: wscn-20261030-13af1534

## 2026-10-30 (T-2) 日本 — 日本央行行长植田和男召开货币政策新闻发布会
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-30   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 与日本央行决议同日，植田讲话为决议后例行发布会，不单独记录（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-30 14:30 |
  id: wscn-20261030-20cf0df5

## 2026-10-30 (T-2) 美国 — 美国亚马逊三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-29   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-30 05:00 |
  id: wscn-20261030-57b27496

## 2026-10-30 (T-2) 日本 — 日本铠侠财报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-30   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-30 17:45 |
  id: wscn-20261030-6d082d46

## 2026-10-30 (T-2) 日本 — 日本央行公布利率决议
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-30   tz: CN   kind: other
  note:
  ai: 保留 · medium/two_sided · 日本央行利率决议影响全球套息交易与亚太风险偏好（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-30 11:30 |
  id: wscn-20261030-6f9f0b46

## 2026-11-02 (T-5) 美国 — 美国Anthropic计划最快于10月底公开招股说明书
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-30   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司IPO招股说明书，非系统性事件，不构成A股市场整体驱动因素（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-30 12:02 |
  id: wscn-20261030-05065514

## 2026-11-02 (T-5) 中国 — 中国10月官方制造业PMI
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-31   tz: CN   kind: macro_release
  note:
  ai: 跳过 · medium/two_sided · 与日历中11月2日官方制造业PMI为同一事件，日期差异为发布时点不同（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-31 09:30 | https://wallstreetcn.com/calendar/CN151359/overview
  id: wscn-20261031-CN151359

## 2026-11-02 (T-5) 中国 — 中国10月底，苹果国行Apple Intelligence上线测试版（接入阿里千问）
- [-] keep 🤖   impact: low   direction: supportive
  date: 2026-10-31   tz: CN   kind: other
  note:
  ai: 跳过 · low/supportive · 产品功能上线，非系统性政策或宏观事件，对A股大盘影响有限（deepseek-v4-pro，2026-10-16）
  src: wallstreetcn imp=4 北京 2026-10-31 12:02 |
  id: wscn-20261031-c88c7231

## 2026-11-04 (T-7) 马耳他 — 马耳他以色列议会选举投票结束，最终结果11月4日正式公布
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-04   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 马耳他以色列议会选举为小国政治事件，对A股无系统性影响（deepseek-v4-pro，2026-10-28）
  src: wallstreetcn imp=4 北京 2026-11-04 12:02 |
  id: wscn-20261104-4255f0b5

## 2026-11-05 (T-8) 美国 — 美国报道：俄罗斯愿在11月4日后恢复俄美乌三方谈判
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-04   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 俄美乌谈判恢复为地缘政治动态，非已排定的系统性事件，且对A股传导有限（deepseek-v4-pro，2026-10-28）
  src: wallstreetcn imp=4 北京 2026-11-04 12:02 |
  id: wscn-20261104-a5725399

## 2026-11-05 (T-8) 中国 — 第九届中国国际进口博览会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-05   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 进博会为贸易博览会，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-05 12:02 |
  id: wscn-20261105-6153f180

## 2026-11-17 (T-20) 美国 — 美国Anthropic IPO窗口（11月16日当周）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-16   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司IPO窗口，非系统性事件，对A股整体无实质影响（deepseek-v4-pro，2026-10-27）
  src: wallstreetcn imp=4 北京 2026-11-16 12:02 |
  id: wscn-20261116-19ce9494

## 2026-11-17 (T-20) 美国 — 美国沃什：美联储生产率与就业特别工作组将举行听证会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-16   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 美联储工作组听证会属常规程序性会议，非政策信号事件（deepseek-v4-pro，2026-10-16）
  src: wallstreetcn imp=4 北京 2026-11-16 12:02 |
  id: wscn-20261116-7d533f14

## 2026-11-17 (T-20) 中国 — 中美俄元首将于深圳APEC期间会晤？外交部回应：中方愿同各方一道，共同推动APEC“中国年”取得丰硕成果
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 外交部回应属非确定日程评论，若元首会晤确定可另行跟踪（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-67281d27

## 2026-11-17 (T-20) 中国 — 中国亚太经合组织会议（APEC）11月17日至18日在深圳举办
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · APEC整体会议与11月18日领导人会议重复，不另计（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-7268b241

## 2026-11-18 (T-21) 美国 — 美国微软开发者与IT大会（Microsoft Ignite）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-17   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 微软Ignite为公司技术大会，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-befb8c6f

## 2026-11-18 (T-21) 中国 — 中国普京出席APEC领导人非正式会议
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-18   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 普京出席系APEC领导人会议组成部分，与APEC事件重复（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-18 00:00 |
  id: wscn-20261118-35908d3e

## 2026-11-27 (T-30) 中国 — 中国商务部：中美双方约定在今年11月底前举行下一次人工智能对话
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-27   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 中美AI对话为事务性沟通，非系统性政策事件，对A股整体影响有限（deepseek-v4-pro，2026-10-13）
  src: wallstreetcn imp=4 北京 2026-11-27 12:02 |
  id: wscn-20261127-77abe93e

## 2026-12-07 (T-40) 美国 — 美国纳斯达克拟推出全新“23小时”交易时段，美东时间晚9点至凌晨4点
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 交易时段延长属市场基础设施变化，非系统性宏观事件，对A股无直接冲击（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-3ba46065

## 2026-12-07 (T-40) 美国 — 美国美股进入每天23小时的“通宵交易”的时代
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 与另一候选重复，均为美股通宵交易时段启动，非A股系统性事件（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-e4bdae4a
