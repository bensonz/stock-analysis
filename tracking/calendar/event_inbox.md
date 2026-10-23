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

_更新: 2026-10-23 · 共 32 条 · 待定 0 条_

## 2026-10-26 (T-3) 巴西 — 巴西将举行总统选举第二轮决选
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-25   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 巴西总统选举对A股市场系统性影响有限，非主要经济体政治事件（deepseek-v4-pro，2026-10-19）
  src: wallstreetcn imp=4 北京 2026-10-25 00:00 |
  id: wscn-20261025-39997f26

## 2026-10-26 (T-3) 巴西 — 巴西将举行总统选举第二轮决选投票开始
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-25   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 巴西大选对A股无系统性影响，非主要经济体政治事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-25 00:00 |
  id: wscn-20261025-a1f9c500

## 2026-10-26 (T-3) 巴西 — 巴西将举行总统选举第二轮决选投票结果或出炉
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-26   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 巴西大选结果对A股无系统性影响，非主要经济体政治事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-26 00:00 |
  id: wscn-20261026-627c8855

## 2026-10-26 (T-3) 中国 — 中国第二十届中央委员会第五次全体会议召开
- [x] keep 🤖   impact: high   direction: two_sided
  date: 2026-10-26   tz: CN   kind: other
  note:
  ai: 保留 · high/two_sided · 二十届五中全会为顶层政策会议，可能定调重大经济与改革方向（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-26 12:02 |
  id: wscn-20261026-c915d7ca

## 2026-10-27 (T-4) 沙特阿拉伯 — 沙特阿拉伯以色列选举
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-27   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 以色列选举非大型经济体政治事件，对A股系统性传导有限（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-10-27 12:02 |
  id: wscn-20261027-3c4f02f2

## 2026-10-27 (T-4) 沙特阿拉伯 — 沙特阿拉伯以色列大选
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-27   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 沙特以色列大选非系统性事件，对A股市场影响有限（deepseek-v4-pro，2026-10-15）
  src: wallstreetcn imp=4 北京 2026-10-27 00:00 |
  id: wscn-20261027-730308dd

## 2026-10-27 (T-4) 韩国 — 韩国SK海力士三季报及电话会（预计时间）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-27   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报，SK海力士非A股系统性重要标的，对大盘影响有限（deepseek-v4-pro，2026-10-16）
  src: wallstreetcn imp=4 北京 2026-10-27 12:02 |
  id: wscn-20261027-b84a6961

## 2026-10-28 (T-5) 韩国 — 韩国SK海力士三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-28   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-28 08:00 |
  id: wscn-20261028-1e9f939f

## 2026-10-28 (T-5) 韩国 — 韩国SK海力士三季报及电话会（预计时间）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-28   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报，SK海力士虽为半导体龙头但非系统性影响A股整体的事件（deepseek-v4-pro，2026-10-16）
  src: wallstreetcn imp=4 北京 2026-10-28 12:02 |
  id: wscn-20261028-b84a6961

## 2026-10-29 (T-6) 美国 — 美国谷歌三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-28   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 04:30 |
  id: wscn-20261029-4acfa391

## 2026-10-29 (T-6) 韩国 — 韩国三星电子三季报及电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-29   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 三星电子财报为单一公司事件，对A股整体市场无系统性影响（deepseek-v4-pro，2026-10-16）
  src: wallstreetcn imp=4 北京 2026-10-29 09:00 |
  id: wscn-20261029-6a652201

## 2026-10-29 (T-6) 美国 — 美国微软三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-28   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 05:00 |
  id: wscn-20261029-7da9f94e

## 2026-10-29 (T-6) 欧元区 — 欧元区欧洲央行主要再融资利率
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-29   tz: CN   kind: macro_release
  note:
  ai: 保留 · medium/two_sided · 欧央行利率决议影响全球流动性与风险偏好，对A股有传导效应（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 21:15 | https://wallstreetcn.com/calendar/EA192061/overview
  id: wscn-20261029-EA192061

## 2026-10-29 (T-6) 韩国 — 韩国三星电子三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-29   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 09:00 |
  id: wscn-20261029-c5c83746

## 2026-10-29 (T-6) 美国 — 美国美联储主席沃什召开货币政策新闻发布会
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-28   tz: US   kind: other
  note:
  ai: 跳过 · medium/two_sided · 与FOMC决议同日，已在日历中覆盖，不重复记录（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 02:30 |
  id: wscn-20261029-d84ebcc1

## 2026-10-30 (T-7) 美国 — 美国9月核心PCE物价指数环比
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-29   tz: US   kind: macro_release
  note:
  ai: 保留 · medium/two_sided · 核心PCE为美联储关注的核心通胀指标，影响全球利率预期（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-29 20:30 | https://wallstreetcn.com/calendar/US111047/overview
  id: wscn-20261029-US111047

## 2026-10-30 (T-7) 美国 — 美国英特尔三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-29   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-30 05:00 |
  id: wscn-20261030-13af1534

## 2026-10-30 (T-7) 日本 — 日本央行行长植田和男召开货币政策新闻发布会
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-30   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 与日本央行决议同日，植田讲话为决议后例行发布会，不单独记录（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-30 14:30 |
  id: wscn-20261030-20cf0df5

## 2026-10-30 (T-7) 美国 — 美国亚马逊三季报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-29   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-30 05:00 |
  id: wscn-20261030-57b27496

## 2026-10-30 (T-7) 日本 — 日本铠侠财报电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-30   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报电话会，非系统性事件（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-30 17:45 |
  id: wscn-20261030-6d082d46

## 2026-10-30 (T-7) 日本 — 日本央行公布利率决议
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-30   tz: CN   kind: other
  note:
  ai: 保留 · medium/two_sided · 日本央行利率决议影响全球套息交易与亚太风险偏好（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-30 11:30 |
  id: wscn-20261030-6f9f0b46

## 2026-11-02 (T-10) 中国 — 中国10月官方制造业PMI
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-31   tz: CN   kind: macro_release
  note:
  ai: 跳过 · medium/two_sided · 与日历中11月2日官方制造业PMI为同一事件，日期差异为发布时点不同（deepseek-v4-pro，2026-10-23）
  src: wallstreetcn imp=4 北京 2026-10-31 09:30 | https://wallstreetcn.com/calendar/CN151359/overview
  id: wscn-20261031-CN151359

## 2026-11-02 (T-10) 中国 — 中国10月底，苹果国行Apple Intelligence上线测试版（接入阿里千问）
- [-] keep 🤖   impact: low   direction: supportive
  date: 2026-10-31   tz: CN   kind: other
  note:
  ai: 跳过 · low/supportive · 产品功能上线，非系统性政策或宏观事件，对A股大盘影响有限（deepseek-v4-pro，2026-10-16）
  src: wallstreetcn imp=4 北京 2026-10-31 12:02 |
  id: wscn-20261031-c88c7231

## 2026-11-05 (T-13) 中国 — 第九届中国国际进口博览会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-05   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 进博会为贸易博览会，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-05 12:02 |
  id: wscn-20261105-6153f180

## 2026-11-17 (T-25) 美国 — 美国沃什：美联储生产率与就业特别工作组将举行听证会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-16   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 美联储工作组听证会属常规程序性会议，非政策信号事件（deepseek-v4-pro，2026-10-16）
  src: wallstreetcn imp=4 北京 2026-11-16 12:02 |
  id: wscn-20261116-7d533f14

## 2026-11-17 (T-25) 中国 — 中美俄元首将于深圳APEC期间会晤？外交部回应：中方愿同各方一道，共同推动APEC“中国年”取得丰硕成果
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 外交部回应属非确定日程评论，若元首会晤确定可另行跟踪（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-67281d27

## 2026-11-17 (T-25) 中国 — 中国亚太经合组织会议（APEC）11月17日至18日在深圳举办
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · APEC整体会议与11月18日领导人会议重复，不另计（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-7268b241

## 2026-11-18 (T-26) 美国 — 美国微软开发者与IT大会（Microsoft Ignite）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-17   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 微软Ignite为公司技术大会，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-befb8c6f

## 2026-11-18 (T-26) 中国 — 中国普京出席APEC领导人非正式会议
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-18   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 普京出席系APEC领导人会议组成部分，与APEC事件重复（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-18 00:00 |
  id: wscn-20261118-35908d3e

## 2026-11-27 (T-35) 中国 — 中国商务部：中美双方约定在今年11月底前举行下一次人工智能对话
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-27   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 中美AI对话为事务性沟通，非系统性政策事件，对A股整体影响有限（deepseek-v4-pro，2026-10-13）
  src: wallstreetcn imp=4 北京 2026-11-27 12:02 |
  id: wscn-20261127-77abe93e

## 2026-12-07 (T-45) 美国 — 美国纳斯达克拟推出全新“23小时”交易时段，美东时间晚9点至凌晨4点
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 交易时段延长属市场基础设施变化，非系统性宏观事件，对A股无直接冲击（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-3ba46065

## 2026-12-07 (T-45) 美国 — 美国美股进入每天23小时的“通宵交易”的时代
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 与另一候选重复，均为美股通宵交易时段启动，非A股系统性事件（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-e4bdae4a
