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

_更新: 2026-10-15 · 共 17 条 · 待定 1 条_

## 2026-10-15 (T-0) 美国 — 美国Anthropic预计将举行上市前的投资者日活动
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-14   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司上市前投资者活动，非系统性事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-10-14 12:02 |
  id: wscn-20261014-8e2a7547

## 2026-10-15 (T-0) 美国 — 美国对中国船舶征收额外港口费
- [x] keep 🤖   impact: medium   direction: risk
  date: 2026-10-14   tz: US   kind: other
  note:
  ai: 保留 · medium/risk · 美国对华船舶加征港口费升级贸易摩擦，利空航运与市场风险偏好（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-10-14 00:00 |
  id: wscn-20261014-9a9fd52e

## 2026-10-15 (T-0) 中国 — 中国台积电第三季法说会
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  ai: 保留 · medium/two_sided · 台积电法说会为全球半导体景气风向标，对A股芯片板块情绪影响明显（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-10-15 14:00 |
  id: wscn-20261015-1ede5314

## 2026-10-15 (T-0) 欧元区 — 欧元区欧洲理事会会议，或讨论对华贸易立场
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  ai: 保留 · medium/two_sided · 欧盟峰会若讨论对华贸易立场，对中欧贸易与市场风险偏好有影响（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-10-15 12:02 |
  id: wscn-20261015-9d8dc326

## 2026-10-16 (T-1) 美国 — 美国特斯拉正式展示新一代“飞行汽车”Roadster
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-15   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 特斯拉产品发布属单一公司事件，非系统性（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-10-15 12:02 |
  id: wscn-20261015-2a6e92f9

## 2026-10-19 (T-4) 美国 — 美国美联储主席沃什将在IMF发表讲话
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-16   tz: US   kind: other
  note:
  ai: 保留 · medium/two_sided · 美联储主席讲话为政策信号窗口，可能影响全球风险偏好与A股（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-10-16 12:02 |
  id: wscn-20261016-f21390bb

## 2026-10-19 (T-4) 中国 — 中国2026金融街论坛年会将于10月19日在京开幕
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-10-19   tz: CN   kind: other
  note:
  ai: 保留 · medium/two_sided · 金融街论坛为高层金融政策场合，监管表态或影响资本市场政策预期（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-10-19 12:02 |
  id: wscn-20261019-6d1a1a18

## 2026-10-20 (T-5) 德国 — 德国英伟达GTC大会（柏林）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-20   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 英伟达GTC为公司技术大会，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-10-20 12:02 |
  id: wscn-20261020-1aaacb8a

## 2026-10-21 (T-6) 德国 — 德国柏林GTC大会，黄仁勋将发表演讲
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-21   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 黄仁勋GTC演讲属公司技术活动，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-10-21 12:02 |
  id: wscn-20261021-2f2142a9

## 2026-10-27 (T-12) 沙特阿拉伯 — 沙特阿拉伯以色列选举
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-10-27   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 以色列选举非大型经济体政治事件，对A股系统性传导有限（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-10-27 12:02 |
  id: wscn-20261027-3c4f02f2

## 2026-10-27 (T-12) 沙特阿拉伯 — 沙特阿拉伯以色列大选
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-27   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-27 00:00 |
  id: wscn-20261027-730308dd

## 2026-11-05 (T-21) 中国 — 第九届中国国际进口博览会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-05   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 进博会为贸易博览会，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-05 12:02 |
  id: wscn-20261105-6153f180

## 2026-11-17 (T-33) 中国 — 中美俄元首将于深圳APEC期间会晤？外交部回应：中方愿同各方一道，共同推动APEC“中国年”取得丰硕成果
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 外交部回应属非确定日程评论，若元首会晤确定可另行跟踪（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-67281d27

## 2026-11-17 (T-33) 中国 — 中国亚太经合组织会议（APEC）11月17日至18日在深圳举办
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · APEC整体会议与11月18日领导人会议重复，不另计（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-7268b241

## 2026-11-18 (T-34) 美国 — 美国微软开发者与IT大会（Microsoft Ignite）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-17   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 微软Ignite为公司技术大会，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-befb8c6f

## 2026-11-18 (T-34) 中国 — 中国普京出席APEC领导人非正式会议
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-18   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 普京出席系APEC领导人会议组成部分，与APEC事件重复（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-18 00:00 |
  id: wscn-20261118-35908d3e

## 2026-11-27 (T-43) 中国 — 中国商务部：中美双方约定在今年11月底前举行下一次人工智能对话
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-27   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 中美AI对话为事务性沟通，非系统性政策事件，对A股整体影响有限（deepseek-v4-pro，2026-10-13）
  src: wallstreetcn imp=4 北京 2026-11-27 12:02 |
  id: wscn-20261127-77abe93e
