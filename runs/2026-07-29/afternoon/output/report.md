# 每日研究报告 2026-07-29

> 模型: deepseek-v4-pro（DeepSeek V4 Pro primary） · 669283+13559 tokens

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3828.47 | +0.40% |
| 深证成指 | 13658.44 | +1.10% |
| 创业板指 | 3378.70 | +1.55% |
| 科创50 | 1678.74 | -0.87% |

涨跌比: 4253涨 / 1215跌 / 5525总

**热门板块**: 教育(+5.39%), 游戏Ⅱ(+5.37%), 休闲食品(+4.64%), 专业连锁Ⅱ(+3.71%), 饮料乳品(+3.63%)

**冷门板块**: 半导体(-1.73%), 计算机设备(-1.56%), 电子化学品Ⅱ(-1.54%), 橡胶(-1.46%), IT服务Ⅱ(-1.24%)

Breadth 3.5:1 bullish, 86涨停/12跌停, but deeply divergent: consumer/food surging (食品饮料+2% intraday) vs semiconductors collapsing (费城半导体 -4.49% overnight, 科创50 -0.87%). IV extreme fear (avg rank 86.4%). Global AI sell-off contagion meets China consumption stimulus — clear sector rotation underway. Deploying 15% into 3 non-tech names, holding 84% cash.

## 策略池扫描

扫描 **83** 只策略池股票
(来源: cheesefortune_intersection)

## 今日开仓

### 1. 药明康德 (603259) — BUY/strong

- **入场价**: ¥126.5
- **止损**: ¥120.18
- **目标**: ¥152.0
- **RPS120**: 90.81%
- **板块**: 医药生物 (neutral (not in bottom 30%))

CDMO龙头，完美MA汇聚(距MA5/10/20均在2%以内)，VCP SETUP，0风险9亮点，创新药出海+订单增长双催化，贝莱德增持至6.06%

### 2. 中国巨石 (600176) — BUY/moderate

- **入场价**: ¥38.39
- **止损**: ¥36.47
- **目标**: ¥50.0
- **RPS120**: 98.69%
- **板块**: 建筑材料 (neutral (not in bottom 30%))

电子布5轮涨价AI算力驱动，H1净利+65-85%，股价从高点大幅回调(-26%距MA20)提供入场机会，12家券商覆盖83%买入评级

### 3. 恒逸石化 (000703) — BUY/small

- **入场价**: ¥15.6
- **止损**: ¥14.82
- **目标**: ¥21.0
- **RPS120**: 97.37%
- **板块**: 石油石化 (neutral (not in bottom 30%))

H1净利暴增+2326-2547%，文莱炼化独特资产享受税收+市场化定价红利，PTA产能周期见底，10亿回购进行中

## 跳过标的

1. **中船特气** (688146) (RPS 100.0%) — Double violation: sector 半导体 in bottom 5% + dist_ma5=13.9% (Rule 2b chase block)
2. **源杰科技** (688498) (RPS 99.76%) — Sector 半导体 in bottom 5% (global AI chip sell-off). Despite RPS120=99.76%, sector gravity blocks entry
3. **长川科技** (300604) (RPS 99.74%) — Sector 半导体 in bottom 5%. Solid fundamentals but sector headwinds dominate
4. **华峰测控** (688200) (RPS 99.48%) — Sector 半导体 in bottom 5%. MA setup clean (dist_ma5=-1.4%) but sector-first rule blocks
5. **寒武纪** (688256) (RPS 91.59%) — Sector 半导体 in bottom 5%. Was a strong name but sector rotation against tech
6. **西部矿业** (601168) (RPS 93.67%) — Rule 2b violation: dist_ma20=13.3% > 12%. Copper cycle strong but price overextended vs MA20
7. **中远海特** (600428) (RPS 93.79%) — Rule 2b violation: dist_ma20=12.8% > 12%. Shipping cycle hot but chased too far
8. **紫光股份** (000938) (RPS 94.41%) — Sector IT服务Ⅱ in bottom 5%. Also 4 risks including 90% goodwill ratio — structural weakness
9. **杰瑞股份** (002353) (RPS 98.47%) — $1.465B gas turbine contract has NO 2026 earnings impact per company disclosure. Sector neutral, near-term catalyst weak despite strong fundamentals
10. **国瓷材料** (300285) (RPS 98.43%) — Sector 电子化学品Ⅱ in bottom 5%. MLCC涨价 catalyst exists but sector headwinds block

## 今日研究结论

- 新开仓: 3只
- 平仓: 0只
- 跳过: 10只

### 新教训
- {'text': 'When 80%+ of strategy pool is in cold sectors (semiconductors -1.73%), the correct V2 response is to shrink to the minority of neutral-sector candidates rather than force entries into familiar tech names. Skip ~65 semiconductor-related candidates, focus on 药明康德/中国巨石/恒逸石化 in three different non-tech sectors.', 'type': 'heuristic', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Sector gravity: institutional flows dominate individual stock momentum when a sector rotates into the bottom 30%. Global AI/semi sell-off (费城半导体 -4.49%) creates persistent headwinds.'}
- {'text': "VCP SETUP at MA confluence (药明康德: all three MA distances <2%) is an unusually strong setup. VCP timing edge + MA anti-chase rule converging at same zone = rare 'spring coil' entry that historically precedes institutional accumulation.", 'type': 'signal', 'tags': ['timing', 'position-sizing'], 'evidence_type': 'supporting', 'mechanism': 'Multi-timeframe MA agreement means participants across horizons concur on value. Combined with VCP contraction, this is a low-risk directional setup.'}
- {'text': 'High IV (>75%) does not mean freeze — it means selective deployment. 86% avg IV Rank with 3.5:1 breadth is not a panic regime. Deploy 15% (not 0%, not 50%), keep 84% cash, widen stops for IV whipsaws.', 'type': 'rule', 'tags': ['position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h017', 'mechanism': 'IV throttles sizing, not decision-making. Strong breadth + high IV = normal sizing with wider stops, not cash-hoarding.'}
- {'text': 'The consumer-tech seesaw rotation is the dominant narrative. Food/beverage surging on policy, semiconductors collapsing on global cycle fears. Multi-day forces suggest this persists — avoid cold side entirely.', 'type': 'observation', 'tags': ['sector'], 'evidence_type': 'supporting', 'mechanism': 'Driven by US chip contagion + Morgan Stanley memory peak call + China stimulus + institutional rebalancing from over-owned tech to under-owned consumer.'}
