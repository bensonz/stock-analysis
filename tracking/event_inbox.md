# 事件收件箱 (event inbox)

> 由 `python3 scripts/event_inbox.py refresh` 生成，每次流水线运行自动刷新
> （来源: 华尔街见闻财经日历，重要性>=4，未来45天）。你只需要打勾：
>
> - `[x]` 保留 → 下次运行（或 `python3 scripts/event_inbox.py promote`）写入 `tracking/events.json`
> - `[-]` 跳过 → 记入台账，不再出现
> - `[ ]` 待定 → 留在这里
>
> 可直接改: 标题里 `—` 后的名称、`impact` (high/medium/low)、`direction` (risk/two_sided/supportive)、
> `date`、`tz` (US=影响其后第一个A股交易日 / CN=当日)、`kind`、`note`。不要改 `src:` 和 `id:` 两行。
> 标题日期 = A股影响日，由 date+tz 推算，重写时刷新。规则与局限: docs/EVENT_INBOX/DECISIONS.md

_更新: 2026-10-12 · 共 22 条 · 待定 22 条_

## 2026-10-12 (T-0) 泰国 — 泰国IMF与世界银行年会：多国央行行长集中亮相、沃什发表讲话
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-12   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-12 12:02 |
  id: wscn-20261012-0a40cdd0

## 2026-10-13 (T-1) 美国 — 美国继续关注中东局势，特朗普改口称“可能”中选前对伊朗采取军事行动
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-12   tz: US   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-12 12:02 |
  id: wscn-20261012-1ca92ca7

## 2026-10-14 (T-2) 美国 — 美国苹果举行智能家居新品发布会
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-13   tz: US   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-13 21:02 |
  id: wscn-20261013-108940b2

## 2026-10-14 (T-2) 中国 — 中国9月CPI同比
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-14   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=4 北京 2026-10-14 09:30 | https://wallstreetcn.com/calendar/CN111275/overview
  id: wscn-20261014-CN111275

## 2026-10-14 (T-2) 中国 — 中国9月出口同比(按美元计)
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-14   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=4 北京 2026-10-14 12:02 | https://wallstreetcn.com/calendar/CN131320/overview
  id: wscn-20261014-CN131320

## 2026-10-14 (T-2) 中国 — 中国9月进口同比(按美元计)
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-14   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=4 北京 2026-10-14 12:02 | https://wallstreetcn.com/calendar/CN131321/overview
  id: wscn-20261014-CN131321

## 2026-10-15 (T-3) 美国 — 美国Anthropic预计将举行上市前的投资者日活动
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-14   tz: US   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-14 12:02 |
  id: wscn-20261014-8e2a7547

## 2026-10-15 (T-3) 美国 — 美国对中国船舶征收额外港口费
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-14   tz: US   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-14 00:00 |
  id: wscn-20261014-9a9fd52e

## 2026-10-15 (T-3) 中国 — 中国台积电第三季法说会
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-15 14:00 |
  id: wscn-20261015-1ede5314

## 2026-10-15 (T-3) 欧元区 — 欧元区欧洲理事会会议，或讨论对华贸易立场
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-15 12:02 |
  id: wscn-20261015-9d8dc326

## 2026-10-16 (T-4) 美国 — 美国特斯拉正式展示新一代“飞行汽车”Roadster
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-15   tz: US   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-15 12:02 |
  id: wscn-20261015-2a6e92f9

## 2026-10-19 (T-7) 美国 — 美国美联储主席沃什将在IMF发表讲话
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-16   tz: US   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-16 12:02 |
  id: wscn-20261016-f21390bb

## 2026-10-19 (T-7) 中国 — 中国2026金融街论坛年会将于10月19日在京开幕
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-19   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-19 12:02 |
  id: wscn-20261019-6d1a1a18

## 2026-10-20 (T-8) 德国 — 德国英伟达GTC大会（柏林）
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-20   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-20 12:02 |
  id: wscn-20261020-1aaacb8a

## 2026-10-21 (T-9) 德国 — 德国柏林GTC大会，黄仁勋将发表演讲
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-21   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-21 12:02 |
  id: wscn-20261021-2f2142a9

## 2026-10-27 (T-15) 沙特阿拉伯 — 沙特阿拉伯以色列选举
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-27   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-27 12:02 |
  id: wscn-20261027-3c4f02f2

## 2026-11-05 (T-24) 中国 — 第九届中国国际进口博览会
- [ ] keep   impact: high   direction: two_sided
  date: 2026-11-05   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-11-05 12:02 |
  id: wscn-20261105-6153f180

## 2026-11-17 (T-36) 中国 — 中美俄元首将于深圳APEC期间会晤？外交部回应：中方愿同各方一道，共同推动APEC“中国年”取得丰硕成果
- [ ] keep   impact: high   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-67281d27

## 2026-11-17 (T-36) 中国 — 中国亚太经合组织会议（APEC）11月17日至18日在深圳举办
- [ ] keep   impact: high   direction: two_sided
  date: 2026-11-17   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-7268b241

## 2026-11-18 (T-37) 美国 — 美国微软开发者与IT大会（Microsoft Ignite）
- [ ] keep   impact: high   direction: two_sided
  date: 2026-11-17   tz: US   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-befb8c6f

## 2026-11-18 (T-37) 中国 — 中国APEC领导人非正式会议
- [ ] keep   impact: high   direction: two_sided
  date: 2026-11-18   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-11-18 12:02 |
  id: wscn-20261118-226309d5

## 2026-11-18 (T-37) 中国 — 中国普京出席APEC领导人非正式会议
- [ ] keep   impact: high   direction: two_sided
  date: 2026-11-18   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-11-18 00:00 |
  id: wscn-20261118-35908d3e
