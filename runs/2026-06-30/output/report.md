# 每日研究报告 2026-06-30

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4094.40 | +0.50% |
| 深证成指 | 16205.56 | +2.48% |
| 创业板指 | 4342.71 | +2.99% |
| 科创50 | 2207.86 | +3.85% |

涨跌比: 3054涨 / 2364跌 / 5509总

**热门板块**: 光学光电子(+7.02%), 消费电子(+5.27%), 家电零部件Ⅱ(+5.16%), 通信设备(+5.14%), 军工电子Ⅱ(+5.14%)

**冷门板块**: 炼化及贸易(-3.10%), 农商行Ⅱ(-3.08%), 城商行Ⅱ(-2.77%), 医药商业(-2.71%), 煤炭开采(-2.55%)

半年收官日，科创50暴涨+3.85%领涨，创业板+2.99%，深成指+2.48%，上证+0.50%殿后。涨停172家vs跌停23家，市场广度1.29:1（低于V2严格门槛但系统判定balanced）。光学光电子(+7.02%)、消费电子(+5.27%)、通信设备(+5.14%)领涨；炼化贸易(-3.10%)、银行(-2.8%)领跌。清晰的老经济→科技硬件轮动。IV数据缺失，sizing不做调整。持仓2只均为+32%~+40%大赢家，提升移动止损锁定利润。新开鹏辉能源(锂电池/储能催化)5%+恒铭达(消费电子#2板块低吸)3%。

## 策略池扫描

扫描 **63** 只策略池股票
(来源: cheesefortune_intersection)

## 今日开仓

### 1. 鹏辉能源 (300438) — BUY/moderate

- **入场价**: ¥82.3
- **止损**: ¥78.19
- **目标**: ¥107.0
- **RPS120**: 94.45%
- **板块**: 电池 (ancillary hot (锂电池板块今日强势，与储能/新能源联动))

储能+锂电池双赛道龙头。Q1业绩超预期(净利+819%)，合同负债14亿(+70%)在手订单爆发。今日锂电池板块集体异动(储能签单突破180GWh)。中信建投买入评级，预测26-28年净利CAGR 50%+。6家机构覆盖。near MA5支撑(-0.8%)，RPS120 94.45%甜点区。

### 2. 恒铭达 (002947) — BUY/small

- **入场价**: ¥77.88
- **止损**: ¥73.99
- **目标**: ¥95.0
- **RPS120**: 92.36%
- **板块**: 消费电子 (top 5% (#2 hot sector))

消费电子零部件龙头。#2热板块。0风险因子(极稀缺)。近10日回调至MA20下方，形成低吸机会。营收3年CAGR 23%，净利+31%。AI手机/折叠屏概念。北向3.9%+公募5.4%机构认可。增资远山新材料外延扩张。

## 跳过标的

1. **天准科技** (688003) (RPS 94.55%) — Rule 2b: dist_ma5_pct 6.8% > 6%. Overextended short-term despite strong sector alignment.
2. **华灿光电** (300323) (RPS 93.95%) — Rule 2b: dist_ma5_pct 15.3%, dist_ma10_pct 21.0%, dist_ma20_pct 19.4%. Extreme extension. Sector光学光电子 #1 but must wait for pullback.
3. **新洁能** (605111) (RPS 92.34%) — Rule 2b: dist_ma5_pct 16.9%, dist_ma10_pct 33.3%, dist_ma20_pct 48.1%. Massively overextended. 半导体 sector hot but chasing suicide.
4. **恒逸石化** (000703) (RPS 93.5%) — Sector 炼化及贸易 is #1 BOTTOM sector (-3.10%). Hard no-buy zone per Rule 1. No exceptions regardless of individual fundamentals.
5. **思瑞浦** (688536) (RPS 93.99%) — Rule 2b: dist_ma10_pct 10.5% > 8%. Otherwise excellent (半导体, 577% profit growth). Wait for pullback to MA10.
6. **睿创微纳** (688002) (RPS 90.76%) — Rule 2b: dist_ma10_pct 13.1% > 8%, dist_ma20_pct 16.5% > 12%. 军工电子 #5 sector but overextended.
7. **新宙邦** (300037) (RPS 90.82%) — Rule 2b: dist_ma10_pct 12.5% > 8%. 宁德时代电解液协议是强催化但股价已大幅反应。等回调。

## 今日研究结论

- 新开仓: 2只
- 跳过: 7只

### 新教训
- {'text': "MA-distance Rule 2b eliminated ~20 visually 'strong' names today in a euphoric tape (r4_7+r7_10+r10=1,061). 新洁能/华灿光电/多氟多/京仪装备/美埃科技 all massive runners, all terrible entries. Rule is doing real protective work.", 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h027', 'mechanism': 'In euphoria, the best-looking charts are the most dangerous entries. MA-distance acts as an objective brake on FOMO.'}
- {'text': 'Pullback-to-support entries in hot sectors create asymmetric risk/reward. 恒铭达 below MA20 in #2消费电子 with 0 risks exemplifies the ideal setup: sector gravity up, stock temporarily weak, entry near support.', 'type': 'heuristic', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Hot sector + pullback to MA support = mean-reversion tailwind aligned with sector trend. 0-risk stocks have lower gap-down probability.'}
- {'text': 'Trailing stop discipline on winners (raise after +20%, trail at -10%) is the primary alpha engine. Both positions +32-40% because we let structural theses run while mechanically protecting gains. The trailing stop is more important than entry timing for portfolio returns.', 'type': 'rule', 'tags': ['exit-rule', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'Winners compound; losers get cut at -5%. The asymmetry of +40% vs -5% per position drives portfolio returns. Mechanical trailing stops remove emotion.'}
- {'text': 'VCP data coverage is critically sparse — only 1 of 31 enriched candidates has VCP data. The strongest backtested signal (contraction_ratio < 0.4 → +7.7% avg 10d) cannot be leveraged. Pipeline improvement needed.', 'type': 'observation', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': "VCP scanning coverage gap means we're flying partially blind on the best timing signal."}
- {'text': "Breadth 1.29:1 is below strict 1.5:1 gate but the system's entry_regime correctly allows positions because quality matters more than quantity: 科创50 +3.85%, 3/3 indices green, 172涨停 vs 23跌停, all top sectors tech-led.", 'type': 'signal', 'tags': ['entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Breadth ratio is a blunt tool. In a narrow-but-deep tech rally, concentration in the right sectors matters more than the raw up/down count of all 5509 stocks.'}
