# 每日研究报告 2026-06-19

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4090.48 | -0.43% |
| 深证成指 | 16030.70 | +0.94% |
| 创业板指 | 4252.39 | +2.05% |
| 科创50 | 1911.51 | +3.84% |

涨跌比: 2023涨 / 3395跌 / 5509总

**热门板块**: 非金属材料Ⅱ(+5.42%), 金属新材料(+4.17%), 通信设备(+4.14%), 半导体(+3.84%), 医疗服务(+3.64%)

**冷门板块**: 保险Ⅱ(-6.42%), 非白酒(-3.98%), 焦炭Ⅱ(-3.85%), 贵金属(-3.40%), 电力(-3.20%)

PANIC TAPE — 上证 -0.43% but 创业板 +2.05% & 科创50 +3.84% ATH. Breadth 0.60:1 (2023↑/3395↓), f10=43跌停, r10=103涨停. Extreme bifurcation: tech/AI stocks surging (中际旭创市值超茅台) while traditional sectors in free-fall (保险 -6.42%). 22 companies issued 异动公告 on 6/18 signaling regulatory attention on frothy tech names. 费城半导体 +6.42% overnight driving A-share semicon sentiment. 美伊谅解备忘录 easing geopolitical risk. IV data unavailable. NO NEW POSITIONS — regime hard-blocks. All 5 existing positions profitable (+10.6% to +30.9%), stops tight. Focus on managing winners and waiting for breadth to improve before deploying ¥652K deployable cash.

## 策略池扫描

扫描 **59** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **华丰科技** (688629) (RPS 90.58%) — CRITICAL: 2.79亿股 (60% of total shares) unlocks 2026-06-29 — 10 days away. Float expansion of this magnitude is catastrophic risk. Plus dist_ma5=8.4% (>6%), dist_ma10=14.0% (>8%) overextended. PERMANENT SKIP until post-unlock consolidation.
2. **华锡有色** (600301) (RPS 94.6%) — 沪锡主力合约日内暴跌6% (from enriched_candidates events) — direct negative catalyst crushing the core product. Sector (小金属) under pressure with 贵金属 in bottom 5.
3. **顺络电子** (002138) (RPS 88.35%) — Most extreme MA extension in entire pool: dist_ma5=13.3%, dist_ma10=21.0%, dist_ma20=40.1%. Triple fail on Rule 2b. Even in a bull regime, this is un-buyable.
4. **欧陆通** (300870) (RPS 89.72%) — 连续3日异常波动公告 (6/12-6/16). dist_ma5=18.3%, dist_ma10=26.9%. PE=319, 100% valuation percentile. Extreme bubble characteristics. Google GPU电源合作 is real catalyst but price has overshot by 3x.
5. **联瑞新材** (688300) (RPS 98.72%) — dist_ma20=71.5% — 70%+ above 20-day MA. Most extreme extension in any candidate. RPS120=98.72% also in chasing zone above 95%.
6. **亚翔集成** (603929) (RPS 99.76%) — RPS120=99.76% far above 95% chasing threshold. dist_ma10=11.6% (>8%), dist_ma20=14.5% (>12%). Triple fail.
7. **兴瑞科技** (002937) (RPS 94.06%) — Triple MA overextension: dist_ma5=9.7%, dist_ma10=18.0%, dist_ma20=21.8%. PE=94, 99% valuation percentile. 汽车零部件 sector neutral.
8. **华峰测控** (688200) (RPS 94.02%) — dist_ma5=14.1% severely overextended. PE=132. Despite 半导体设备 hot sector and SEMI record equipment shipments catalyst, price has run too far from support.
9. **思瑞浦** (688536) (RPS 93.56%) — dist_ma10=8.9% (>8% rule violation). PE=179. 机构目标价高26% — consensus says overvalued. Q1 NP +577% is impressive but already priced in.
10. **华宏科技** (002645) (RPS 94.33%) — dist_ma5=9.4% (>6%), dist_ma10=10.1% (>8%), dist_ma20=15.7% (>12%). Triple fail. 3 risk factors (商誉17%, 质押100%, 换手12%). Despite 稀土/AI-MLCC catalyst, entry risk too high.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': "The entry_regime system correctly identified a panic tape (breadth 0.60:1, f10=43) despite 创业板+科创50 hitting ATHs. The 'average stock' is going down while tech leaders surge — this extreme bifurcation is precisely when new longs should be blocked. The regime detector prevented what would likely be buying into a narrowing, fragile rally.", 'type': 'signal', 'tags': ['entry-filter', 'regime-detection', 'risk-management'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Broad market weakness (3395 stocks down vs 2023 up) means the rally is concentrated in a shrinking number of stocks. Opening new positions into this divergence risks buying just before the leaders also roll over. The 22 companies issuing 异动公告 on 6/18 confirms the rally is getting regulatory attention — a contrarian signal.'}
- {'text': 'Rule 2b (MA-distance anti-chase) is filtering aggressively and correctly. Over 80% of enriched candidates with RPS in the 75-95% sweet spot fail at least one MA distance threshold. Without this rule, V2 would be buying extremely extended stocks. The most extreme example: 联瑞新材 at dist_ma20=71.5% and 顺络电子 at dist_ma20=40.1%.', 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h027', 'mechanism': 'Stocks that have run 20%+ above their 20-day MA have a high probability of mean-reversion in the following 5-10 days. The anti-chase rule forces the system to wait for pullbacks to MA5/MA10 support before entering, which backtests show improves entry timing significantly.'}
- {'text': '10-day time stop with 3% PnL threshold is properly calibrated. Three positions hit day 10 today (恒铭达 +11.70%, 上海新阳 +12.60%, 路维光电 +11.88%) — all well above the 3% threshold. The rule correctly distinguishes winners (keep holding) from dead-money positions (cut). No false positives.', 'type': 'heuristic', 'tags': ['exit-rule', 'timing'], 'evidence_type': 'supporting', 'mechanism': "A 10-day window catches positions that aren't working while giving winners enough time to develop. The 3% PnL threshold is low enough to eject truly stagnant positions but high enough to not trigger on normal consolidation."}
- {'text': '华丰科技 (688629) 60% float unlock on 2026-06-29 is the single biggest risk event in the current candidate pool. A 2.79亿 share unlock represents a potential flood of selling that could crash the stock regardless of fundamentals. This type of event should be a permanent skip until post-unlock consolidation proves the market can absorb the supply.', 'type': 'rule', 'tags': ['entry-filter', 'risk-management'], 'evidence_type': 'observation', 'mechanism': 'When 60% of total shares become freely tradable, early investors and pre-IPO shareholders who have been locked up for years have enormous incentive to sell. The supply shock typically overwhelms any fundamental thesis for 2-4 weeks post-unlock.'}
