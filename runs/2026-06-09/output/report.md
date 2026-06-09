# 每日研究报告 2026-06-09

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3979.68 | +0.51% |
| 深证成指 | 15007.11 | +1.25% |
| 创业板指 | 3884.54 | +1.91% |
| 科创50 | 1644.16 | +2.98% |

涨跌比: 2471涨 / 2908跌 / 5517总

**热门板块**: 玻璃玻纤(+7.82%), 综合Ⅱ(+5.69%), 电子化学品Ⅱ(+5.01%), 元件(+4.56%), 半导体(+4.18%)

**冷门板块**: 油服工程(-4.85%), 焦炭Ⅱ(-4.01%), 航天装备Ⅱ(-3.34%), 油气开采Ⅱ(-3.29%), 炼化及贸易(-2.77%)

Indices green (科创50 +2.98%, 创业板 +1.91%) but breadth deeply negative (0.85:1, 2,908 down vs 2,471 up). Classic large-cap tech masking broad distribution. Hot sectors: glass fiber +7.82% (AI CCL super-cycle), electronic chemicals +5.01%, semiconductors +4.18%. Cold: old energy (oil services -4.85%, coal -4.01%). IV: 科创50 elevated (56.3%), large caps low (23.8%). No new positions — breadth gate failed. 100% cash.

## 策略池扫描

扫描 **55** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **上海新阳** (300236) (RPS 89.68%) — Best candidate on paper (电子化学品Ⅱ top 3 sector, RPS120 89.68%, all MA distances within limits, 0 risks). Skipped because breadth gate failed: Up/Down ratio 0.85:1 < 1.5:1 minimum. Will prioritize if breadth recovers.
2. **思瑞浦** (688536) (RPS 91.71%) — Strong candidate (半导体 top 5 sector, RPS120 91.71%, MA distances all within limits, net profit +577%). Skipped: breadth gate failure. Currently pulling back to MA support — good entry zone if breadth improves.
3. **芯源微** (688037) (RPS 92.83%) — Acceptable candidate (半导体 sector, RPS120 92.83%, MA distances within limits). Skipped: breadth gate failure + negative earnings trend + PE 702 raises sanity concerns despite V2 ignoring valuation.
4. **华峰测控** (688200) (RPS 94.97%) — Rule 2b automatic skip: dist_ma5_pct=+7.9% > 6% threshold. Overextended short-term regardless of sector strength.
5. **江丰电子** (300666) (RPS 93.67%) — Rule 2b skip: dist_ma5_pct=+6.4% > 6%. Also RPS120=93.67% in extended zone without sector exception to override.
6. **绿的谐波** (688017) (RPS 93.89%) — Extreme extension: dist_ma5=+16.3%, dist_ma10=+21.2%, dist_ma20=+46.5%. All three MA distance rules violated. RPS120=93.89% extended zone.
7. **三祥新材** (603663) (RPS 93.97%) — dist_ma5=+8.5% > 6%, dist_ma10=+21.0% > 8%, dist_ma20=+35.6% > 12%. Triple MA violation. Also sector (化学原料) not confirmed top 30%.
8. **华宏科技** (002645) (RPS 93.1%) — 环保设备 sector not in top 30% hot sectors. Also 4 risk factors including 大股东100%质押 and 商誉占净资产17%. RPS is strong but sector gravity wins.
9. **华锡有色** (600301) (RPS 91.83%) — 小金属 sector not hot. RPS20=50.75% — near-term momentum dead. dist_ma5=-9.9% — broken chart. 沪锡期货暴跌6% headwind.
10. **恩捷股份** (002812) (RPS 89.79%) — 电池 sector not in top hot sectors. Stock below all MAs (dist_ma5=-7.0%, dist_ma10=-12.6%, dist_ma20=-16.0%) — sustained downtrend, broken chart.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': 'Index-green/breadth-red tape (today: indices +0.5%~+3.0% but 2,908 down vs 2,471 up) is the most dangerous entry environment for momentum strategies. Large-cap tech masking broad distribution = buying into a narrowing rally top. Treat as hard block regardless of system flags.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': "When breadth is negative but indices are green, large-cap concentration is lifting the index while the median stock declines. Momentum entries in this regime face immediate headwinds from poor market internals. h013 already established strong breadth alone isn't enough — this is the inverse case."}
- {'text': 'Glass fiber (玻璃玻纤) sector is in a confirmed structural super-cycle driven by AI CCL demand, not a short-term spike. Electronic cloth prices have risen monthly since Oct 2025, cumulative +50%+, supply bottleneck (日東纺) until 2027. No glass fiber stocks in current strategy pool — this is a coverage gap.', 'type': 'observation', 'tags': ['sector'], 'evidence_type': 'supporting', 'mechanism': 'AI servers require 5x more electronic cloth per unit vs traditional servers. Single-source supplier (日東纺, 90%+ share) cannot expand capacity until 2027. Chinese producers (中国巨石, 国际复材, 山东玻纤) are the marginal suppliers capturing price. Monthly price hikes = recurring catalyst.'}
- {'text': "MA-distance Rule 2b filtered 15+ candidates today that would otherwise have 'passed' on RPS and sector alone. This rule is the single most important entry-timing filter and is working as designed. The market is extended broadly — many strong names are too far above support.", 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021, h027', 'mechanism': 'Stocks that spike far above short-term MAs have high mean-reversion probability within 3-5 days. Even in hot sectors, the arithmetic of distance-from-support dominates short-term returns. h021 and h027 already validated this.'}
- {'text': "VCP scanner coverage is thin (1/27 enriched candidates has VCP data, only SETUP quality). Either the scanner calibration is too strict or the current pool is dominated by trending/extended names that don't form contraction patterns. Worth investigating whether scanner parameters need adjustment for this market regime.", 'type': 'observation', 'tags': ['timing', 'entry-filter'], 'evidence_type': 'contradicting', 'mechanism': "VCP patterns require price contraction + declining volatility. In a momentum-driven tape where stocks are expanding ranges, VCP setups become rare. The scanner's utility may be regime-dependent — most valuable in consolidating/range-bound markets, less so in trending ones."}
- {'text': "The breadth buy gate (Up/Down ≥ 1.5:1) correctly blocked entries today despite system flag allowing new positions. V1's biggest error was over-relying on individual stock quality while ignoring market internals. Today 0.85:1 breadth = unambiguous 'no.' This is the system working as intended.", 'type': 'heuristic', 'tags': ['entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': "Breadth ratio captures the 'participation' dimension that indices miss. When only large caps are carrying the tape, the probability of a momentum stock continuing its trend is lower because there's no broad buying pressure to absorb supply. h013 established this principle."}
