# 每日研究报告 2026-06-11

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3985.99 | -0.18% |
| 深证成指 | 14926.04 | -0.19% |
| 创业板指 | 3863.00 | +0.21% |
| 科创50 | 1645.01 | -0.44% |

涨跌比: 1178涨 / 4153跌 / 5514总

**热门板块**: 焦炭Ⅱ(+2.38%), 油服工程(+2.18%), 油气开采Ⅱ(+1.90%), 农业综合Ⅱ(+1.73%), 农化制品(+1.55%)

**冷门板块**: 数字媒体(-3.51%), 航天装备Ⅱ(-3.16%), 广告营销(-2.41%), 电机Ⅱ(-2.27%), 家电零部件Ⅱ(-2.22%)

PANIC TAPE — breadth 0.28:1 (1,178 up / 4,153 down), 10跌停/19涨停. 仅创业板微涨+0.21%. 触发因素: 美股SOX暴跌-10.3%(费城半导体)溢出, 非农超预期打击降息预期. A股资金从科技/AI全面撤出, 涌入焦炭/油服/油气/农业等资源防御板块. 4持仓均在科技相关板块, 与今日热点0重合. IV数据缺失. 新开仓硬性禁止.

## 策略池扫描

扫描 **52** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **新宙邦** (300037) (RPS 86.34%) — Market panic hard block. VCP SETUP (ratio 0.48), RPS120=86.34% in sweet spot, good MA distances, 宁德时代电解液大单催化。但 battery chemicals sector not in top 30%，且 breadth 0.28:1 不允许任何新开仓。正常市场下会考虑 SMALL BUY。
2. **奥来德** (688378) (RPS 94.36%) — Market panic hard block. RPS120=94.36% sweet spot, 光学光电子 sector recently hot, OLED材料龙头。但今日资金从科技全面撤退，即使标的优质也不入场。
3. **伟测科技** (688372) (RPS 93.73%) — Market panic hard block. RPS120=93.73%, 半导体封测, 净利+173%增长, MA distances all within safe range. 正常市场下是BUY候选。今日不买。
4. **思瑞浦** (688536) (RPS 92.12%) — Market panic hard block. 模拟芯片龙头, RPS120=92.12%, 净利+577%爆发增长, MA distances safe。今日不买。

## 今日研究结论

- 新开仓: 0只
- 跳过: 4只

### 新教训
- {'text': 'US semiconductor 3-sigma crash (SOX -10.3%) → A-share tech sectors follow with 1-4 day lag → defensive rotation to resources. Pattern: money exits AI/semiconductor/optics and enters coal/oil/agriculture. This should be formalized into a macro-regime detection rule.', 'type': 'signal', 'tags': ['sector', 'macro', 'entry-filter'], 'evidence_type': 'supporting', 'mechanism': 'US rate expectations shock via nonfarm payrolls → global re-rating of growth/tech → A-share institutional money rotates defensively. The SOX crash magnitude (-10.3%) is a 3-sigma event that overwhelms any individual stock catalyst.'}
- {'text': 'Stop proximity rule validated again: 兴森科技 at 1.71% from stop in 0.28:1 breadth tape = proactive sell is correct. The 扬杰科技 W10 precedent (1.8% → gapped to -8.37%) shows gap risk is real when breadth is this bad.', 'type': 'rule', 'tags': ['exit-rule', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'In weak breadth, buyers disappear and sellers dominate the close. A stock within 2% of stop at open can gap through it before any liquidity emerges. Proactive exit preserves capital for re-entry when conditions improve.'}
- {'text': "Relative strength in weak tape is the best signal: 上海新阳 (+0.75%) and 路维光电 (+2.60%) both green while 75% of market red. This confirms their sector leadership and institutional support. Same pattern as [h028] — today's relative leaders are more likely to be tomorrow's absolute leaders when tape recovers.", 'type': 'heuristic', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h028', 'mechanism': 'Stocks that hold green in a 0.28:1 breadth day have genuine buying demand, not just passive drift. When market recovers, these are the first stocks institutions add to.'}
- {'text': "Sector-first framework catches rotation immediately: 0/4 positions in today's hot sectors. If resource/cyclical rotation persists 3+ days, Rule 1 triggers across all positions regardless of individual stock PnL. The framework is working as designed.", 'type': 'observation', 'tags': ['sector', 'exit-rule'], 'evidence_type': 'supporting', 'mechanism': 'Sector gravity: in a rotation, even strong individual stocks get dragged by sector flows. The 3-day rule gives time to distinguish temporary rotation from regime change.'}
