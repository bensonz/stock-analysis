# 事件收件箱 (event inbox)

> 由 `python3 scripts/event_inbox.py refresh` 生成，每次流水线运行自动刷新
> （来源: 华尔街见闻财经日历，重要性>=3，未来45天）。你只需要打勾：
>
> - `[x]` 保留 → 下次运行（或 `python3 scripts/event_inbox.py promote`）写入 `tracking/events.json`
> - `[-]` 跳过 → 记入台账，不再出现
> - `[ ]` 待定 → 留在这里
>
> 可直接改: 标题里 `—` 后的名称、`impact` (high/medium/low)、`direction` (risk/two_sided/supportive)、
> `date`、`tz` (US=影响其后第一个A股交易日 / CN=当日)、`kind`、`note`。不要改 `src:` 和 `id:` 两行。
> 标题日期 = A股影响日，由 date+tz 推算，重写时刷新。规则与局限: docs/EVENT_INBOX/DECISIONS.md

_更新: 2026-10-12 · 共 91 条 · 待定 91 条_

## 2026-10-12 (T-0) 泰国 — 泰国IMF与世界银行年会：多国央行行长集中亮相、沃什发表讲话
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-12   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-12 12:02 |
  id: wscn-20261012-0a40cdd0

## 2026-10-12 (T-0) 中国 — 中国京东2026年“双11”定档10月12日
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-12   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-12 00:00 |
  id: wscn-20261012-15c49418

## 2026-10-12 (T-0) 挪威 — 挪威2026年诺贝尔经济学奖公布
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-12   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-12 17:45 |
  id: wscn-20261012-1edd67b7

## 2026-10-12 (T-0) 卢森堡 — 卢森堡欧盟各国外长举行会议，讨论俄乌冲突、中东局势
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-12   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-12 14:00 |
  id: wscn-20261012-77ca1ca9

## 2026-10-12 (T-0) 中国 — 中国1至9月社会融资规模增量(亿人民币)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-12   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-12 12:02 | https://wallstreetcn.com/calendar/CN131334/overview
  id: wscn-20261012-CN131334

## 2026-10-12 (T-0) 中国 — 中国1至9月新增人民币贷款(亿人民币)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-12   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-12 12:02 | https://wallstreetcn.com/calendar/CN131335/overview
  id: wscn-20261012-CN131335

## 2026-10-12 (T-0) 中国 — 中国9月M2货币供应同比
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-12   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-12 12:02 | https://wallstreetcn.com/calendar/CN191442/overview
  id: wscn-20261012-CN191442

## 2026-10-13 (T-1) 美国 — 美国继续关注中东局势，特朗普改口称“可能”中选前对伊朗采取军事行动
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-12   tz: US   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-12 12:02 |
  id: wscn-20261012-1ca92ca7

## 2026-10-13 (T-1) 美国 — 美国OCP全球峰会2026（圣何塞，12—15日）
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-12   tz: US   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-12 12:02 |
  id: wscn-20261012-7e75becb

## 2026-10-13 (T-1) 中国 — 中国法国总统外事顾问博纳于10月9日至13日来华，与王毅举行新一轮中法战略对话
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-13   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-13 12:02 |
  id: wscn-20261013-30c97d16

## 2026-10-13 (T-1) 中国 — 中国沪市首份三季报由有研新材发布
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-13   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-13 12:02 |
  id: wscn-20261013-5937fea3

## 2026-10-13 (T-1) 泰国 — 泰国IMF公布2026年10月《世界经济展望》报告。
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-13   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-13 10:00 |
  id: wscn-20261013-8590b7b4

## 2026-10-13 (T-1) 中国 — 中国清华大学经管学院顾问委员会年度会议（新增黄仁勋、苏姿丰等委员）
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-13   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-13 12:02 |
  id: wscn-20261013-8fcb785a

## 2026-10-13 (T-1) 英国 — 英国议会AI安全听证会（美四大实验室出席）
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-13   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-13 12:02 |
  id: wscn-20261013-b6100268

## 2026-10-13 (T-1) 中国 — 中国千问新一代AI眼镜现货发售
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-13   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-13 00:00 |
  id: wscn-20261013-fdece1e8

## 2026-10-14 (T-2) 美国 — 美国苹果举行智能家居新品发布会
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-13   tz: US   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-13 21:02 |
  id: wscn-20261013-108940b2

## 2026-10-14 (T-2) 美国 — 美国半导体产业旗舰展会SEMICON West 2026举行
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-13   tz: US   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-13 12:02 |
  id: wscn-20261013-4e5ecb6e

## 2026-10-14 (T-2) 美国 — 美国美联储理事沃勒发表讲话
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-13   tz: US   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-13 15:45 |
  id: wscn-20261013-e797d0ea

## 2026-10-14 (T-2) 中国 — 中国2026世界储能大会
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-14   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-14 12:02 |
  id: wscn-20261014-2cf70eda

## 2026-10-14 (T-2) 中国 — 中国2026湾区半导体产业生态博览会
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-14   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-14 12:02 |
  id: wscn-20261014-57fc3f5b

## 2026-10-14 (T-2) 荷兰 — 荷兰ASML三季报及电话会
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-14   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-14 13:00 |
  id: wscn-20261014-88ab3212

## 2026-10-14 (T-2) 中国 — 中国2026人工智能产业大会将于10月14日至16日在济南举办
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-14   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-14 12:02 |
  id: wscn-20261014-9db8b6ea

## 2026-10-14 (T-2) 中国 — 中国9月CPI同比
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-14   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=4 北京 2026-10-14 09:30 | https://wallstreetcn.com/calendar/CN111275/overview
  id: wscn-20261014-CN111275

## 2026-10-14 (T-2) 中国 — 中国9月PPI同比
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-14   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-14 09:30 | https://wallstreetcn.com/calendar/CN111291/overview
  id: wscn-20261014-CN111291

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

## 2026-10-14 (T-2) 日本 — 日本央行召开市场操作会议
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-14   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-14 12:02 |
  id: wscn-20261014-b4f2132b

## 2026-10-14 (T-2) 泰国 — 泰国美联储理事鲍曼发表讲话。
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-14   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-14 17:40 |
  id: wscn-20261014-cd1f7974

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

## 2026-10-15 (T-3) 美国 — 美国美联储公布经济状况褐皮书
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-14   tz: US   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-15 02:00 |
  id: wscn-20261015-034b48a4

## 2026-10-15 (T-3) 中国 — 中国台积电第三季法说会
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-15 14:00 |
  id: wscn-20261015-1ede5314

## 2026-10-15 (T-3) 中国 — 中国传音控股港股IPO上市交易
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-15 09:20 |
  id: wscn-20261015-43bfae0e

## 2026-10-15 (T-3) 中国 — 英伟达中国开发者日15日至16日在苏州举行
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-15 12:02 |
  id: wscn-20261015-7a446fc2

## 2026-10-15 (T-3) 中国 — 中国第140届广交会开幕
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-15 12:02 |
  id: wscn-20261015-94440f92

## 2026-10-15 (T-3) 欧元区 — 欧元区欧洲理事会会议，或讨论对华贸易立场
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-15 12:02 |
  id: wscn-20261015-9d8dc326

## 2026-10-15 (T-3) 中国 — 中国阶跃正式开源Step 5 Preview
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-15 00:00 |
  id: wscn-20261015-b1c3d7a0

## 2026-10-15 (T-3) 中国 — 中国淘宝天猫“双11”活动开启
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-15 20:00 |
  id: wscn-20261015-b6ee2bae

## 2026-10-15 (T-3) 泰国 — 泰国20国集团(G20)财长和央行行长会议
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-15   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-15 12:02 |
  id: wscn-20261015-bc0d824e

## 2026-10-16 (T-4) 美国 — 美国特斯拉正式展示新一代“飞行汽车”Roadster
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-15   tz: US   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-15 12:02 |
  id: wscn-20261015-2a6e92f9

## 2026-10-16 (T-4) 美国 — 美国10月10日当周首次申请失业救济人数(万人)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-15   tz: US   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-15 20:30 | https://wallstreetcn.com/calendar/US121055/overview
  id: wscn-20261015-US121055

## 2026-10-16 (T-4) 美国 — 美国9月零售销售环比
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-15   tz: US   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-15 20:30 | https://wallstreetcn.com/calendar/US171206/overview
  id: wscn-20261015-US171206

## 2026-10-19 (T-7) 美国 — 美国财政部季度交易商问卷将发布
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-16   tz: US   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-16 12:02 |
  id: wscn-20261016-5f40c957

## 2026-10-19 (T-7) 美国 — 美国iPhone Duo开启预售
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-16   tz: US   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-16 00:00 |
  id: wscn-20261016-6fca1ff1

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

## 2026-10-19 (T-7) 中国 — 中国三季度GDP同比
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-19   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-19 10:00 | https://wallstreetcn.com/calendar/CN101256/overview
  id: wscn-20261019-CN101256

## 2026-10-19 (T-7) 中国 — 中国9月规模以上工业增加值同比
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-19   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-19 10:00 | https://wallstreetcn.com/calendar/CN141330/overview
  id: wscn-20261019-CN141330

## 2026-10-19 (T-7) 中国 — 中国1至9月全国房地产开发投资
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-19   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-19 10:00 | https://wallstreetcn.com/calendar/CN161376/overview
  id: wscn-20261019-CN161376

## 2026-10-19 (T-7) 中国 — 中国1至9月社会消费品零售总额同比
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-19   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-19 10:00 | https://wallstreetcn.com/calendar/CN171402/overview
  id: wscn-20261019-CN171402

## 2026-10-19 (T-7) 中国 — 中国9月社会消费品零售总额同比
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-19   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-19 10:00 | https://wallstreetcn.com/calendar/CN171405/overview
  id: wscn-20261019-CN171405

## 2026-10-20 (T-8) 德国 — 德国英伟达GTC大会（柏林）
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-20   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-20 12:02 |
  id: wscn-20261020-1aaacb8a

## 2026-10-20 (T-8) 中国 — 中国10月一年期贷款市场报价利率(LPR)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-20   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-20 09:00 | https://wallstreetcn.com/calendar/CN191480/overview
  id: wscn-20261020-CN191480

## 2026-10-20 (T-8) 中国 — 中国10月五年期贷款市场报价利率(LPR)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-20   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-20 09:00 | https://wallstreetcn.com/calendar/CN191481/overview
  id: wscn-20261020-CN191481

## 2026-10-20 (T-8) 中国 — 中国APEC财政部长会议
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-20   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-20 12:02 |
  id: wscn-20261020-cdbe9df9

## 2026-10-21 (T-9) 中国 — 中国2026 世界智能网联汽车大会
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-21   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-21 12:02 |
  id: wscn-20261021-45398480

## 2026-10-23 (T-11) 美国 — 美国10月17日当周首次申请失业救济人数(万人)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-22   tz: US   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-22 20:30 | https://wallstreetcn.com/calendar/US121055/overview
  id: wscn-20261022-US121055

## 2026-10-23 (T-11) 欧元区 — 欧元区10月制造业PMI初值
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-23   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-23 16:00 | https://wallstreetcn.com/calendar/EA192084/overview
  id: wscn-20261023-EA192084

## 2026-10-26 (T-14) 中国 — 中国上交所/中证指数修订上证系列指数正式实施
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-26   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-26 09:30 |
  id: wscn-20261026-e73f5eb0

## 2026-10-27 (T-15) 沙特阿拉伯 — 沙特阿拉伯以色列选举
- [ ] keep   impact: high   direction: two_sided
  date: 2026-10-27   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-10-27 12:02 |
  id: wscn-20261027-3c4f02f2

## 2026-10-28 (T-16) 美国 — 美国苹果10月第二场发布会：首款触控MacBook与新iPad mini同步亮相
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-27   tz: US   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-27 12:02 |
  id: wscn-20261027-4e676232

## 2026-10-29 (T-17) 中国 — 中国腾讯全球数字生态大会（深圳）
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-29   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-29 12:02 |
  id: wscn-20261029-31d09512

## 2026-10-29 (T-17) 欧元区 — 欧元区欧洲央行存款便利利率
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-29   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-29 21:15 | https://wallstreetcn.com/calendar/EA192060/overview
  id: wscn-20261029-EA192060

## 2026-10-29 (T-17) 欧元区 — 欧元区欧洲央行主要再融资利率
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-29   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-29 21:15 | https://wallstreetcn.com/calendar/EA192061/overview
  id: wscn-20261029-EA192061

## 2026-10-29 (T-17) 欧元区 — 欧元区欧洲央行边际贷款利率
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-29   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-29 21:15 | https://wallstreetcn.com/calendar/EA192062/overview
  id: wscn-20261029-EA192062

## 2026-10-29 (T-17) 欧元区 — 欧元区欧加峰会
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-29   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-29 12:02 |
  id: wscn-20261029-abd7e4fd

## 2026-10-30 (T-18) 美国 — 美国三季度实际GDP年化季环比初值
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-29   tz: US   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-29 20:30 | https://wallstreetcn.com/calendar/US101000/overview
  id: wscn-20261029-US101000

## 2026-10-30 (T-18) 美国 — 美国10月24日当周首次申请失业救济人数(万人)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-29   tz: US   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-10-29 20:30 | https://wallstreetcn.com/calendar/US121055/overview
  id: wscn-20261029-US121055

## 2026-11-02 (T-21) 中国 — 中国10月官方制造业PMI
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-10-31   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-10-31 09:30 | https://wallstreetcn.com/calendar/CN151359/overview
  id: wscn-20261031-CN151359

## 2026-11-02 (T-21) 中国 — 中国10月RatingDog制造业PMI
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-02   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-11-02 09:45 | https://wallstreetcn.com/calendar/CN151371/overview
  id: wscn-20261102-CN151371

## 2026-11-02 (T-21) 欧元区 — 欧元区10月制造业PMI终值
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-02   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-11-02 17:00 | https://wallstreetcn.com/calendar/EA192084/overview
  id: wscn-20261102-EA192084

## 2026-11-02 (T-21) 中国 — 中国2026年世界互联网大会乌镇峰会将于11月2日至5日举行
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-02   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-11-02 12:02 |
  id: wscn-20261102-bad4e529

## 2026-11-03 (T-22) 美国 — 美国10月ISM制造业指数
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-02   tz: US   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-11-02 23:00 | https://wallstreetcn.com/calendar/US151132/overview
  id: wscn-20261102-US151132

## 2026-11-03 (T-22) 韩国 — 韩国10月CPI同比
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-03   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-11-03 07:00 | https://wallstreetcn.com/calendar/KR2608052/overview
  id: wscn-20261103-KR2608052

## 2026-11-05 (T-24) 美国 — 美国10月ADP就业人数变动(万人)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-04   tz: US   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-11-04 21:15 | https://wallstreetcn.com/calendar/US121065/overview
  id: wscn-20261104-US121065

## 2026-11-05 (T-24) 美国 — 美国10月ISM非制造业指数
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-04   tz: US   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-11-04 23:00 | https://wallstreetcn.com/calendar/US151138/overview
  id: wscn-20261104-US151138

## 2026-11-05 (T-24) 中国 — 第九届中国国际进口博览会
- [ ] keep   impact: high   direction: two_sided
  date: 2026-11-05   tz: CN   kind: other
  note:
  src: wallstreetcn imp=4 北京 2026-11-05 12:02 |
  id: wscn-20261105-6153f180

## 2026-11-05 (T-24) 英国 — 英国央行政策利率
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-05   tz: CN   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-11-05 20:00 | https://wallstreetcn.com/calendar/UK191670/overview
  id: wscn-20261105-UK191670

## 2026-11-06 (T-25) 美国 — 美国10月31日当周首次申请失业救济人数(万人)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-05   tz: US   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-11-05 21:30 | https://wallstreetcn.com/calendar/US121055/overview
  id: wscn-20261105-US121055

## 2026-11-09 (T-28) 美国 — 美国10月失业率
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-06   tz: US   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-11-06 21:30 | https://wallstreetcn.com/calendar/US121050/overview
  id: wscn-20261106-US121050

## 2026-11-09 (T-28) 美国 — 美国10月非农就业人口变动(万人)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-06   tz: US   kind: macro_release
  note:
  src: wallstreetcn imp=3 北京 2026-11-06 21:30 | https://wallstreetcn.com/calendar/US121058/overview
  id: wscn-20261106-US121058

## 2026-11-09 (T-28) 中国 — 中国10月CPI同比
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-09   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-11-09 09:30 | https://wallstreetcn.com/calendar/CN111275/overview
  id: wscn-20261109-CN111275

## 2026-11-09 (T-28) 中国 — 中国10月PPI同比
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-09   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-11-09 09:30 | https://wallstreetcn.com/calendar/CN111291/overview
  id: wscn-20261109-CN111291

## 2026-11-09 (T-28) 中国 — 中国1至10月社会融资规模增量(亿人民币)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-09   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-11-09 12:02 | https://wallstreetcn.com/calendar/CN131334/overview
  id: wscn-20261109-CN131334

## 2026-11-09 (T-28) 中国 — 中国1至10月新增人民币贷款(亿人民币)
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-09   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-11-09 12:02 | https://wallstreetcn.com/calendar/CN131335/overview
  id: wscn-20261109-CN131335

## 2026-11-09 (T-28) 中国 — 中国10月M2货币供应同比
- [ ] keep   impact: medium   direction: two_sided
  date: 2026-11-09   tz: CN   kind: other
  note:
  src: wallstreetcn imp=3 北京 2026-11-09 12:02 | https://wallstreetcn.com/calendar/CN191442/overview
  id: wscn-20261109-CN191442

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
