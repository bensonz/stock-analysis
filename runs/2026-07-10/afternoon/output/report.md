# 每日研究报告 2026-07-10

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3996.16 | -1.00% |
| 深证成指 | 15046.67 | -2.29% |
| 创业板指 | 3842.73 | -4.37% |
| 科创50 | 2064.98 | -5.53% |

涨跌比: 3772涨 / 1678跌 / 5521总

**热门板块**: 航天装备Ⅱ(+10.24%), 航海装备Ⅱ(+4.78%), 风电设备(+4.39%), 广告营销(+4.24%), 医疗服务(+4.12%)

**冷门板块**: 电子化学品Ⅱ(-8.23%), 半导体(-6.23%), 元件(-5.18%), 电池(-5.03%), 通信设备(-4.22%)

Rotation day, not crash. Breadth 2.25:1 (3772↑/1678↓, 95涨停/8跌停) but all 4 major indices red. Tech/semiconductor crushed: 科创50 -5.53%, 半导体板块 -6.23% on Meta 'compute surplus' fears. Defense/aerospace surging: 航天装备Ⅱ +10.24% on 长征十号乙 rocket launch. Money rotating out of crowded AI trades into defense. Buy gate FAILED (0/3 indices green) → no new positions. IV data unavailable. Portfolio: -1.78% total, 92% cash. Exiting 奥来德 (-4.01% day 0, bad timing), holding 宏达电子 (-2.71%, defense tailwind).

## 策略池扫描

扫描 **63** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **凯莱英** (002821) (RPS 88.03%) — Market buy gate failed (0/3 indices green) + dist_ma20=22.7% extreme chase risk even if gate were open. Sector (医疗服务) is top 5 — worth tracking if gate clears and stock pulls back.
2. **荣昌生物** (688331) (RPS 85.45%) — Market buy gate failed + dist_ma20=15.3% above 12% chase limit. Healthcare-adjacent sector, watch for pullback to MA10.
3. **上海新阳** (300236) (RPS 93.33%) — Sector 电子化学品Ⅱ is #1 BOTTOM at -8.23% — hard no-buy zone (h019). Also dist_ma5=9.7% chase.
4. **京仪装备** (688652) (RPS 94.18%) — Sector 半导体 is bottom 5 at -6.23% — hard no-buy zone. Also dist_ma10=16.2% extreme chase.
5. **茂莱光学** (688502) (RPS 89.17%) — dist_ma20=21.8% extreme extension — even if sector were hot, this is un-buyable. PE=1739, speculative optical name.
6. **扬杰科技** (300373) (RPS 92.51%) — Sector 半导体 bottom 5. Despite 涨价 catalyst (7月起涨价15-25%), sector gravity dominates. No entry in bottom sectors (h019).
7. **四方股份** (601126) (RPS 94.91%) — Market buy gate failed. Sector (电网设备) not in top 30%. RPS120=94.91 in extended zone without sector exception.
8. **伟测科技** (688372) (RPS 90.99%) — Sector 半导体 bottom 5. dist_ma20=13.5% above 12% chase limit. Two strikes.

## 今日研究结论

- 新开仓: 0只
- 跳过: 8只

### 新教训
- {'text': "业绩预告超级催化(+492~604%)在预告前已被充分定价时，是'卖事实'事件而非买入事件。奥来德7/5公告→7/6冲高¥60.33→7/10跌至¥51.24(-15%)。判断标准：公告前5日累计涨幅>15%时，公告日大概率是出货日。", 'type': 'heuristic', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'mechanism': '埋伏资金在业绩预告前建仓，公告日利用流动性出货。强催化+前期大涨=利好出尽。'}
- {'text': '指数与广度背离(广度2.25:1但4大指数全绿)是板块剧烈轮动的信号，不是安全的入场环境。今日科创50 -5.53%但航天装备+10.24%，说明资金在板块间极端转移，新开仓容易被夹在中间。Rule 1的buy gate(≥2指数翻红)正确过滤了这种假强势。', 'type': 'signal', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': '指数权重股被集中抛售时，即使大部分股票上涨，整体市场偏空，新开仓胜率低。'}
- {'text': 'h019再次验证：底部板块(bottom 5)是硬性不买入区域。今日半导体-6.23%、电子化学品-8.23%、电池-5.03%——在这些板块买入的任何个股今天都会遭受重创，无论个股质量多好。', 'type': 'rule', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019'}
- {'text': '军工电子板块(宏达电子)因航天装备Ⅱ+10.24%的板块联动效应而相对抗跌(-3.75% vs 科创50 -5.53%)。持有逻辑成立：当所在板块与top板块有供应链关系时，可享受溢出效应。', 'type': 'observation', 'tags': ['sector', 'position-sizing'], 'evidence_type': 'supporting', 'mechanism': '航天装备(主机厂)暴涨→军工电子(配套)跟涨但幅度较小。板块上下游联动效应存在。'}
- {'text': '-3%首3日规则今天拯救了组合。奥来德如果继续持有到-5%止损线(¥50.71)，会多亏约1%。在坏timing的入场中，更快止损=更少损失。Rule 5的10天→3天加速止损是正确的。', 'type': 'rule', 'tags': ['exit-rule', 'timing'], 'evidence_type': 'supporting', 'mechanism': '入场时机错误时，越早认错损失越小。-3%首3日规则比-5%硬止损提前截断了错误。'}
