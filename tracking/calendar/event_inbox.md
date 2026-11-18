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

_更新: 2026-11-18 · 共 16 条 · 待定 0 条_

## 2026-11-18 (T-0) 美国 — 美国微软开发者与IT大会（Microsoft Ignite）
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-17   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 微软Ignite为公司技术大会，非系统性政策事件（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-17 12:02 |
  id: wscn-20261117-befb8c6f

## 2026-11-18 (T-0) 中国 — 中国普京出席APEC领导人非正式会议
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-18   tz: CN   kind: other
  note:
  ai: 跳过 · medium/two_sided · 普京出席系APEC领导人会议组成部分，与APEC事件重复（deepseek-v4-pro，2026-10-12）
  src: wallstreetcn imp=4 北京 2026-11-18 00:00 |
  id: wscn-20261118-35908d3e

## 2026-11-18 (T-0) 美国 — 美国英伟达Q3财报与电话会
- [x] keep 🤖   impact: medium   direction: two_sided
  date: 2026-11-17   tz: US   kind: other
  note:
  ai: 保留 · medium/two_sided · 英伟达财报影响全球AI产业链情绪，对A股算力与科技板块有传导效应（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-18 06:00 |
  id: wscn-20261118-646a4873

## 2026-11-18 (T-0) 中国 — 中国腾讯Q3财报与电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-18   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-18 20:00 |
  id: wscn-20261118-e4445883

## 2026-11-19 (T-1) 美国 — 黄仁勋出席美国国会听证会，就绯闻作情况说明
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-18   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司高管听证会，非系统性事件，对A股整体影响有限（deepseek-v4-pro，2026-11-09）
  src: wallstreetcn imp=4 北京 2026-11-18 12:02 |
  id: wscn-20261118-c425eb3b

## 2026-11-19 (T-1) 美国 — 黄仁勋出席美国国会听证会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-18   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司高管国会听证，非系统性政策事件，且与英伟达财报同日，影响已被覆盖（deepseek-v4-pro，2026-11-16）
  src: wallstreetcn imp=4 北京 2026-11-18 12:02 |
  id: wscn-20261118-e71c5d98

## 2026-11-19 (T-1) 美国 — 美国Anthropic IPO 定价
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-18   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司IPO定价，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-18 12:02 |
  id: wscn-20261118-eb340fe4

## 2026-11-19 (T-1) 中国 — 中国习近平将同俄罗斯总统普京、美国总统特朗普举行中俄美元首会晤
- [x] keep 🤖   impact: high   direction: two_sided
  date: 2026-11-19   tz: CN   kind: other
  note:
  ai: 保留 · high/two_sided · 中俄美元首会晤涉及大国关系与贸易政策走向，可能系统性影响A股风险偏好（deepseek-v4-pro，2026-11-16）
  src: wallstreetcn imp=4 北京 2026-11-19 12:02 |
  id: wscn-20261119-6f690f3d

## 2026-11-19 (T-1) 美国 — 美国英伟达临时CEO召开全体员工会议
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-18   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司内部会议，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-19 01:00 |
  id: wscn-20261119-cddf248a

## 2026-11-19 (T-1) 中国 — 中国阿里巴巴Q3财报与电话会
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-19   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司财报，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-19 20:00 |
  id: wscn-20261119-d3fe72f1

## 2026-11-20 (T-2) 美国 — 美国Anthropic 纳斯达克上市
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-19   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 单一公司上市，非系统性事件（deepseek-v4-pro，2026-11-13）
  src: wallstreetcn imp=4 北京 2026-11-19 21:30 |
  id: wscn-20261119-86d16232

## 2026-11-27 (T-9) 中国 — 中国商务部：中美双方约定在今年11月底前举行下一次人工智能对话
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-11-27   tz: CN   kind: other
  note:
  ai: 跳过 · low/two_sided · 中美AI对话为事务性沟通，非系统性政策事件，对A股整体影响有限（deepseek-v4-pro，2026-10-13）
  src: wallstreetcn imp=4 北京 2026-11-27 12:02 |
  id: wscn-20261127-77abe93e

## 2026-12-07 (T-19) 美国 — 美国特朗普将对多晶硅及其衍生产品加征关税
- [x] keep 🤖   impact: medium   direction: risk
  date: 2026-12-04   tz: US   kind: other
  note:
  ai: 保留 · medium/risk · 美国对多晶硅加征关税，直接冲击中国光伏产业链出口，对A股相关板块构成下行风险（deepseek-v4-pro，2026-11-17）
  src: wallstreetcn imp=4 北京 2026-12-04 00:00 |
  id: wscn-20261204-fbc64ee6

## 2026-12-07 (T-19) 美国 — 美国纳斯达克拟推出全新“23小时”交易时段，美东时间晚9点至凌晨4点
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 交易时段延长属市场基础设施变化，非系统性宏观事件，对A股无直接冲击（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-3ba46065

## 2026-12-07 (T-19) 美国 — 美国美股进入每天23小时的“通宵交易”的时代
- [-] keep 🤖   impact: low   direction: two_sided
  date: 2026-12-06   tz: US   kind: other
  note:
  ai: 跳过 · low/two_sided · 与另一候选重复，均为美股通宵交易时段启动，非A股系统性事件（deepseek-v4-pro，2026-10-21）
  src: wallstreetcn imp=4 北京 2026-12-06 00:00 |
  id: wscn-20261206-e4bdae4a

## 2026-12-15 (T-27) 美国 — 美国G20峰会（迈阿密）
- [-] keep 🤖   impact: medium   direction: two_sided
  date: 2026-12-14   tz: US   kind: other
  note:
  ai: 跳过 · medium/two_sided · G20峰会为多边论坛，非系统性政策事件，且与已有关税休战到期等事件重叠，影响有限（deepseek-v4-pro，2026-10-30）
  src: wallstreetcn imp=4 北京 2026-12-14 12:02 |
  id: wscn-20261214-514277a6
