# 每日研究报告 2026-07-30

> 模型: deepseek-v4-pro（DeepSeek V4 Pro primary） · 301598+9245 tokens

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3784.55 | -1.15% |
| 深证成指 | 13141.22 | -3.79% |
| 创业板指 | 3179.58 | -5.89% |
| 科创50 | 1572.25 | -6.34% |

涨跌比: 1901涨 / 3457跌 / 5529总

**热门板块**: 医疗美容(+5.10%), 商用车(+4.02%), 白酒Ⅱ(+3.58%), 厨卫电器(+3.06%), 酒店餐饮(+2.76%)

**冷门板块**: 通信设备(-11.98%), 元件(-8.95%), 电子化学品Ⅱ(-7.84%), 半导体(-7.50%), 消费电子(-6.10%)

PANIC TAPE. Breadth 0.55:1 (1901 up / 3457 down), 0/3 major indices green (上证-1.15%, 深成指-3.79%, 创业板-5.89%, 科创50-6.34%). 51涨停/48跌停, f7_10=484 large-scale heavy selling. IV Rank avg 84.5% extreme across all ETFs (科创50 92.4%, 创业板ETF 96.9%). Violent tech-to-defensive rotation: 通信设备-12%, 半导体-7.5% capitulating; 医疗美容+5%, 白酒+4% bid as safe havens. Likely margin call cascade in crowded AI/semi names. Cash is king — hard block on new positions remains. Portfolio: exiting 中国巨石 (-5.91% stop breach) and 药明康德 (-3.56% in 2 days triggers 3-day rule), holding 恒逸石化 (-1.47%, 3.58% above stop). Post-sell cash ~88%.

## 策略池扫描

扫描 **77** 只策略池股票
(来源: cheesefortune_intersection)

## 今日平仓

### 1. 中国巨石 (600176) — SELL — -5.91%

- **出场价**: ¥36.12
- **持有天数**: 2天
- **板块排名**: top 50% (neutral)

Rule 5硬止损触发: PnL -5.91%超过-5%阈值。现价36.12已跌破止损36.47。入场时股价低于MA5/MA10/MA20三条均线——V1价值陷阱思维残余，V2不应买入均线空头排列的股票。

### 2. 药明康德 (603259) — SELL — -3.56%

- **出场价**: ¥122.0
- **持有天数**: 2天
- **板块排名**: top 50% (neutral)

Rule 5触发: -3.56%在入场2天内(-3% in first 3 days → SELL)。距硬止损120.18仅1.49%，stop_proximity CRITICAL。VCP结构和均线紧凑度仍然健康但规则优先。可等市场企稳后重新评估入场。

## 跳过标的

1. **华峰测控** (688200) (RPS 99.48%) — 半导体板块今日-7.5%位列bottom 5 (Rule 1: 冷门板块不买入). RPS120=99.48, dist_ma5=-1.4% MA结构优秀, 但板块重力压倒个股质量. 等待半导体板块回暖后再评估.
2. **西部矿业** (601168) (RPS 93.67%) — dist_ma20_pct=13.3%超过Rule 2b的12%上限, 中期超买需要回调. RPS120=93.67, H1净利+123%业绩优秀, 但等回调至MA20(32.57)附近再评估.

## 今日研究结论

- 新开仓: 0只
- 平仓: 2只
- 跳过: 2只

### 新教训
- {'text': "均线空头排列(股价<MA5<MA10<MA20)的股票即使RPS再高也不应买入。中国巨石入场时三条均线全部在股价上方——这是V1价值陷阱思维的残余(down -26% from MA20被误读为'抄底机会')。V2应加入规则: 股价低于所有三条均线时自动跳过。", 'type': 'rule', 'tags': ['entry-filter', 'anti-value-trap'], 'evidence_type': 'supporting', 'mechanism': "均线空头排列意味着中期趋势已坏，-26%距MA20不是'便宜'而是趋势衰减的信号。动量交易应顺着趋势方向操作，而非逆势抄底。"}
- {'text': '硬性buy gate(h077)再次验证: 华峰测控(dist_ma5仅-1.4%)和涛涛车业(MA三线紧凑)在恐慌日看起来诱人但系统正确强制空仓。V1会在今天买入并承受明天可能的继续下跌。今天0.55:1的涨跌比下任何新仓都是冒险。', 'type': 'signal', 'tags': ['entry-filter', 'regime-detection'], 'evidence_type': 'supporting', 'related_hypothesis': 'h077', 'mechanism': '恐慌日(Up/Down<1:1 + 3/3指数绿失败)个股信号不可靠。系统性抛压下好股票也会被拖累，此时筛选个股是徒劳的。'}
- {'text': '通信设备-12%、半导体-7.5% vs 医疗美容+5%、白酒+3.6%的极端分化是融资盘踩踏信号。科技赛道前期拥挤度高，一旦触发margin call就是连锁反应。我们幸运地在科技赛道零持仓——昨天的决策避免了今天的灾难。', 'type': 'observation', 'tags': ['sector', 'margin-risk'], 'evidence_type': 'supporting', 'mechanism': '高拥挤度+高融资余额的板块在恐慌日承受双重抛压——持仓者被迫减仓+融资盘被强制平仓。这是通信设备板块日跌12%的核心驱动力。'}
