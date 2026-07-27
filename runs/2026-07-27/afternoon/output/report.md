# 每日研究报告 2026-07-27

> 模型: deepseek-v4-pro（DeepSeek V4 Pro primary） · 97127+11844 tokens

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3858.24 | +1.15% |
| 深证成指 | 14148.73 | +2.72% |
| 创业板指 | 3590.79 | +3.16% |
| 科创50 | 1807.95 | +1.16% |

涨跌比: 5195涨 / 286跌 / 5525总

**热门板块**: 玻璃玻纤(+10.56%), 元件(+6.23%), 综合Ⅱ(+5.31%), 化妆品(+5.28%), 酒店餐饮(+5.27%)

**冷门板块**: 油服工程(-3.47%), 油气开采Ⅱ(-1.80%), 饮料乳品(-1.47%), 保险Ⅱ(-1.03%), 房屋建设Ⅱ(-0.43%)

Breadth 18.2:1 extremely bullish, 121涨停/7跌停, broad-based rally. 三大指数全红(创业板+3.16%领涨)。Tech/AI主线回归，玻璃玻纤(+10.56%)和元件(+6.23%)领涨。IV偏高(科创50 IV Rank 71.9%, 创业板59.6%)但已从上周极端值回落，恐慌消退中。持仓4只均在中游板块，0只在top5但在18:1普涨下可接受。新增广合科技(元件#2板块)作为sector-aligned仓位。

## 策略池扫描

扫描 **47** 只策略池股票
(来源: cheesefortune_intersection)

## 今日开仓

### 1. 广合科技 (001389) — BUY/strong

- **入场价**: ¥160.5
- **止损**: ¥152.48
- **目标**: ¥190.0
- **RPS120**: 98.01%
- **板块**: 元件 (top 5 (#2 at +6.23%))

PCB龙头，元件sector今日#2 (+6.23%)，AI算力硬件链核心受益。北向12%+公募6.2%机构重仓。泰国工厂产能爬坡提供增长。股价从MA20(189.91)回调至160.50，买在弱势等反弹。

## 跳过标的

1. **星宸科技** (301536) (RPS 95.81%) — dist_ma5=+22.0%, dist_ma10=+20.4%, dist_ma20=+17.7% — extreme overextension, Rule 2b hard block. All three MA distance thresholds violated.
2. **药康生物** (688046) (RPS 89.99%) — dist_ma5=+7.0% (>6%), dist_ma20=+15.5% (>12%) — Rule 2b. Multiple MA thresholds violated despite 业绩预增 catalyst.
3. **华丰科技** (688629) (RPS 97.2%) — dist_ma5=+7.8% (>6%) — Rule 2b overextension. Also 股东询价转让减持1.39% creating near-term overhang.
4. **恒逸石化** (000703) (RPS 96.03%) — dist_ma10=+8.7% (>8%) — Rule 2b. Also sector 炼化及贸易 not in hot sectors. 业绩预增+2000% already priced in.
5. **昭衍新药** (603127) (RPS 90.2%) — dist_ma20=+13.2% (>12%) — Rule 2b. 业绩增长主要来自生物资产公允价值变动，主营业务仍在亏损区间，质量存疑。
6. **养元饮品** (603156) (RPS 91.18%) — Sector 饮料乳品 in bottom 5 (-1.47%) — Rule 1 hard block. No entry regardless of individual quality.
7. **国瓷材料** (300285) (RPS 98.35%) — MA data unreliable (dist_ma5=-90.4%). Likely data pipeline error from stock split/corporate action. Cannot apply Rule 2b — skip.
8. **顺络电子** (002138) (RPS 88.12%) — MA data unreliable (dist_ma5=-83.1%). Likely data pipeline error. Also 7/31中报即将发布 — event risk.

## 今日研究结论

- 新开仓: 1只
- 平仓: 0只
- 跳过: 8只

### 新教训
- {'text': "18:1 breadth days demand aggressive sector-first deployment. Today's #2 sector 元件 had a pristine candidate (广合科技 RPS120=98%) that was easy to overlook without explicit sector screen. Future runs should scan top-5 sectors first, then filter for candidates, not the reverse.", 'type': 'heuristic', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h028', 'mechanism': 'In extreme breadth environments, sector leadership is the primary alpha signal. Stocks in top sectors benefit from both beta (market) and alpha (sector rotation), creating a double tailwind.'}
- {'text': 'Multiple enriched_candidates show corrupted MA data (dist -60% to -95%). These are likely unadjusted for stock splits or rights issues. The pipeline needs to detect and flag these — corrupted MAs make Rule 2b impossible to apply, forcing us to skip otherwise viable candidates.', 'type': 'observation', 'tags': ['entry-filter', 'data-quality'], 'evidence_type': 'supporting', 'mechanism': "When MA calculation doesn't account for corporate actions (splits, bonus issues), the distance percentages become nonsensical. Affected stocks: 国瓷材料, 蔚蓝锂芯, 星网锐捷, 中远海特, 顺络电子, 融捷股份."}
- {'text': 'Opening 4 positions on the same day creates correlated stop-proximity risk. 3 of 4 opened today have stop-proximity flags. In a high-IV environment (科创50 71.9%), a single gap-down morning could trigger multiple simultaneous stops. Future entries should stagger over 2-3 days even in strong regimes.', 'type': 'rule', 'tags': ['position-sizing', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h024', 'mechanism': 'Same-day entries share the same entry price basis, so market-wide open gaps affect all simultaneously. Staggering entry dates diversifies the gap-risk timing.'}
