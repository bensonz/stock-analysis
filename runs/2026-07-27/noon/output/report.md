# 每日研究报告 2026-07-27

> 模型: deepseek-v4-pro（DeepSeek V4 Pro primary） · 326785+13941 tokens

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3829.39 | +0.40% |
| 深证成指 | 13969.37 | +1.41% |
| 创业板指 | 3534.83 | +1.55% |
| 科创50 | 1778.79 | -0.47% |

涨跌比: 4893涨 / 561跌 / 5523总

**热门板块**: 玻璃玻纤(+5.89%), 化妆品(+4.84%), 医疗美容(+4.49%), 工程咨询服务Ⅱ(+4.38%), 综合Ⅱ(+4.36%)

**冷门板块**: 油服工程(-3.72%), 油气开采Ⅱ(-2.56%), 保险Ⅱ(-1.45%), 煤炭开采(-1.22%), 半导体(-0.64%)

Breadth 8.72:1 extremely bullish (4893↑/561↓, 74涨停/3跌停). 上证+0.40%, 深证+1.41%, 创业板+1.55%, 科创50-0.47%. IV整体偏高(avg rank 63.95%)但非恐慌，科创50 IV 82.5%需警惕。玻璃玻纤+5.89%领涨，半导体-0.64%垫底。能源/资源板块持续轮出。CXO板块基本面积极强(投融资回暖+订单饱满)但未进入单日top5。Entry regime fully open — deploy 25% capital into 4 positions.

## 策略池扫描

扫描 **49** 只策略池股票
(来源: cheesefortune_intersection)

## 今日开仓

### 1. 凯莱英 (002821) — BUY/strong

- **入场价**: ¥163.54
- **止损**: ¥155.36
- **目标**: ¥195.0
- **RPS120**: 94.71%
- **板块**: 医疗服务 (top 30% (CXO投融资回暖+订单饱满，西南/中信建投确认))

CXO行业景气上行，GLP-1多肽商业化订单放量，股权激励催化，MA20精准支撑

### 2. 冰轮环境 (000811) — BUY/moderate

- **入场价**: ¥42.85
- **止损**: ¥40.71
- **目标**: ¥52.0
- **RPS120**: 99.13%
- **板块**: 通用设备 (top 30% (液冷+算力主题，太平洋证券推荐))

数据中心液冷龙头，并购重组进展，合同负债13亿，算力基建受益

### 3. 昊志机电 (300503) — BUY/moderate

- **入场价**: ¥67.89
- **止损**: ¥64.5
- **目标**: ¥85.0
- **RPS120**: 98.45%
- **板块**: 通用设备 (top 30% (机器人产业链高景气))

H1业绩爆炸(净利+266.57%)，谐波减速器技术突破，机器人+机床双驱动

### 4. 荣昌生物 (688331) — BUY/small

- **入场价**: ¥126.9
- **止损**: ¥120.56
- **目标**: ¥150.0
- **RPS120**: 91.04%
- **板块**: 生物制品 (top 30% (创新药BD出海超1000亿美元，政策利好))

MA三线完美支撑，泰它西普全球首创，创新药出海大年，回购计划

## 跳过标的

1. **华峰测控** (688200) (RPS 99.36%) — 半导体 sector bottom 5 (-0.64%) — Rule 1 hard block
2. **芯碁微装** (688630) (RPS 99.32%) — 半导体 sector bottom 5 + dist_ma5=6.0% borderline Rule 2b
3. **扬杰科技** (300373) (RPS 92.69%) — 半导体 sector bottom 5 — Rule 1 hard block
4. **华丰科技** (688629) (RPS 97.2%) — dist_ma5=7.8% — hard fail Rule 2b (>6%)
5. **星网锐捷** (002396) (RPS 91.2%) — dist_ma5=6.8%, dist_ma10=12.5%, dist_ma20=27.3% — triple fail Rule 2b
6. **星宸科技** (301536) (RPS 95.81%) — dist_ma5=22%, dist_ma10=20.4%, dist_ma20=17.7% — extreme fail Rule 2b
7. **恒逸石化** (000703) (RPS 96.03%) — dist_ma10=8.7% — fail Rule 2b (>8%)
8. **昭衍新药** (603127) (RPS 90.2%) — dist_ma20=13.2% — fail Rule 2b (>12%);利润靠猴子资产重估驱动
9. **药康生物** (688046) (RPS 89.99%) — dist_ma5=7.0% — fail Rule 2b (>6%)
10. **国瓷材料** (300285) (RPS 98.35%) — MA数据异常(price 57 vs MA5 598)，疑似拆股未更新，无法分析
11. **中材科技** (002080) (RPS 95.31%) — 虽然玻璃玻纤sector #1，但个股远低于所有均线(下跌趋势)，RPS20仅74%走弱

## 今日研究结论

- 新开仓: 4只
- 平仓: 0只
- 跳过: 11只

### 新教训
- {'text': 'MA-distance discipline is the hardest-working filter: 7 of 49 candidates fail Rule 2b alone. This confirms h021/h027 — the anti-chase rule prevents FOMO entries into extended names like 星网锐捷 and 星宸科技.', 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021, h027', 'mechanism': 'Stocks with dist_ma5 > 6% or dist_ma10 > 8% have already absorbed near-term buying pressure; entry at these levels carries mean-reversion risk regardless of RPS quality.'}
- {'text': "Sector Rule 1 correctly excludes semiconductor names (华峰测控 score 9.0/0 risks, 芯碁微装 score 9.1/0 risks) that would have been V1's top picks. Even the best stock in a bottom-5 sector is a bad entry. Validates h019.", 'type': 'rule', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Sector gravity dominates individual stock fundamentals in the short term; a stock fighting its sector headwind needs exponentially more catalyst energy to overcome the drag.'}
- {'text': "CXO is a stealth sector leader: 医疗美容 is #3 today but CXO/医疗服务 doesn't appear in top 5 despite strong fundamentals (订单饱满, 投融资+27.7% YoY). Single-day sector top-5 data has blind spots — multi-day sector rankings and web research are essential complements.", 'type': 'observation', 'tags': ['sector'], 'evidence_type': 'supporting', 'mechanism': 'Sectors within the same Level-1 industry (医药生物) can have divergent daily returns; 医疗美容 (consumer-driven) leads while 医疗服务/CXO (B2B) may lag on any given day despite stronger multi-week momentum.'}
- {'text': 'IV rank dispersion is actionable: 科创50 IV 82.5% vs 50ETF 48% — 荣昌生物 gets 4% allocation instead of 6-7% purely due to IV risk. High-IV names need wider stops, and wider stops mean smaller position for same risk budget.', 'type': 'signal', 'tags': ['position-sizing', 'entry-filter'], 'evidence_type': 'supporting', 'mechanism': 'Position sizing = risk budget / stop distance. When IV rank > 75%, implied daily ranges are wider, so even a -5% hard stop can be hit on normal volatility. Reducing size is the correct response.'}
- {'text': '国瓷材料 MA data corruption (price ¥57 vs MA5 ¥598) — this is likely a stock split or corporate action not reflected in MA calculation. The system should flag such anomalies rather than silently computing -90% dist values.', 'type': 'observation', 'tags': ['data-quality'], 'evidence_type': 'supporting', 'mechanism': 'MA calculations using pre-split prices mixed with post-split prices produce garbage distances. A simple sanity check (abs(dist_ma5) < 50%) would catch this.'}
