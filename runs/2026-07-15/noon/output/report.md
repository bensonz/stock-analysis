# 每日研究报告 2026-07-15

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3963.90 | -0.08% |
| 深证成指 | 14868.23 | -0.38% |
| 创业板指 | 3837.23 | -0.36% |
| 科创50 | 1936.06 | -3.67% |

涨跌比: 3682涨 / 1772跌 / 5525总

**热门板块**: 医疗美容(+8.24%), 医疗服务(+6.47%), 化学制药(+5.89%), 影视院线(+5.48%), 生物制品(+4.56%)

**冷门板块**: 航天装备Ⅱ(-5.66%), 半导体(-4.72%), 光学光电子(-4.44%), 非金属材料Ⅱ(-4.09%), 电子化学品Ⅱ(-3.81%)

Breadth 2.08:1 deceptively bullish but all three major indices red (上证 -0.08%, 深证 -0.38%, 创业板 -0.36%). 科创50 crashed -3.67%. Massive sector rotation: healthcare/medical surging +5-8% while semiconductors/tech collapsing -4-5%. IV extreme across all boards (科创50 IV Rank 100%, 创业板 93%). Buy gate FAILS — all 4 existing positions hit stops. Cash is king today.

## 策略池扫描

扫描 **59** 只策略池股票
(来源: cheesefortune_intersection)

## 今日平仓

### 1. 上海新阳 (300236) — SELL — -6.00%

- **出场价**: ¥105.12
- **持有天数**: 1天
- **板块排名**: bottom 5% (电子化学品Ⅱ -3.81%)

-6.0% in 1 day. -5% stop broken (¥105.12 < ¥106.24). -3% in first 3 days triggered. Sector 电子化学品 bottom 5 (-3.81%). Sector gravity overriding individual thesis.

### 2. 金钼股份 (601958) — SELL — -3.21%

- **出场价**: ¥21.98
- **持有天数**: 1天
- **板块排名**: mid (钼/小金属 not in top or bottom 5)

-3.21% in 1 day triggers -3% in first 3 days rule. Stop distance only 1.87% with gap risk. Resource rotation fading. 钼 thesis structurally intact but timing was wrong — re-enter when sector stabilizes.

### 3. 伟测科技 (688372) — SELL — -8.43%

- **出场价**: ¥150.19
- **持有天数**: 1天
- **板块排名**: bottom 5% (半导体 -4.72%)

-8.43% in 1 day. -5% stop massively broken (¥150.19 vs stop ¥169.86). -3% in first 3 days triggered. Sector 半导体 bottom 5 (-4.72%). Entry was overextended — stock had run significantly pre-entry.

### 4. 路维光电 (688401) — SELL — -9.23%

- **出场价**: ¥77.11
- **持有天数**: 1天
- **板块排名**: bottom 5% (半导体材料, under 半导体 -4.72%)

-9.23% in 1 day. -5% stop broken (¥77.11 < ¥80.70). -3% in first 3 days triggered. Sector 半导体材料 bottom 5. 0 risk factors meant nothing against sector gravity — validates Rule 1 (Sector First).

## 跳过标的

1. **凯莱英** (002821) (RPS 89.16%) — Buy gate failed (0/3 indices green). Even if gate passed: dist_ma20=18.1% violates Rule 2b (>12% non-negotiable). Hot sector (医疗服务 +6.47%) and fresh catalyst (股权激励 7/9), but overextended. Wait for pullback to MA20 zone (~¥155).
2. **荣昌生物** (688331) (RPS 86.52%) — Buy gate failed. Hot sector (生物制品 +4.56%), dist_ma10=0% (on MA10 support), RPS120=86.52%. But still deeply unprofitable (net profit -5.5亿) and IV Rank 100% on 科创50 makes entries dangerous.
3. **京仪装备** (688652) (RPS 94.56%) — Sector dead (半导体 -4.72% → Rule 1 hard skip). dist_ma20=19.5% → Rule 2b violation. Stock hit all-time high at open (¥180.15) then reversed — classic distribution pattern.
4. **南大光电** (300346) (RPS 93.89%) — Sector 电子化学品 in bottom 5 (-3.81%). Rule 1: no entries in bottom 30% sectors regardless of individual quality. RPS120=93.89% but sector gravity wins.
5. **茂莱光学** (688502) (RPS 89.84%) — Sector 光学光电子 in bottom 5 (-4.44%). dist_ma20=14.4% violates Rule 2b. PE=1545 — extreme valuation even by momentum standards. Multiple blocking issues.
6. **恒逸石化** (000703) (RPS 94.52%) — Buy gate failed. RPS120=94.52% in extended zone (92-95%). dist_ma5=5.3% near the 6% chase threshold. Oil catalyst real but sector not top 30%.
7. **博杰股份** (002975) (RPS 93.06%) — Buy gate failed. Great setup (H1 earnings +642-816%, dist_ma5=0.5% ideal entry, RPS120=93.06%) but sector 自动化设备 not in top 5. Timing wrong due to broad market weakness.

## 今日研究结论

- 新开仓: 0只
- 平仓: 4只
- 跳过: 7只

### 新教训
- {'text': "The '2/3 indices green' buy gate prevented new positions during a deceptive tape: breadth was 2.08:1 (bullish) but all three major indices were red. Without this gate, capital would have been deployed into healthcare names just as the rotation intensified. The gate correctly identified regime weakness despite bullish breadth.", 'type': 'rule', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': "Breadth alone can be misleading when large-cap indices are weak — the up stocks are concentrated in small-caps while the index-weight sectors are being liquidated. Requiring index confirmation filters out 'false breadth' signals."}
- {'text': "Sector concentration killed the portfolio: all 4 positions (100% of deployed capital) were in semiconductor/electronic sectors, all of which appeared in today's bottom 5 sectors. Diversification rule needed: max 50% in any single sector family.", 'type': 'rule', 'tags': ['position-sizing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'When a sector family (semiconductor + electronic chemicals + optical) rotates out simultaneously, concentrated portfolios have zero defense. Sector-family caps force diversification even within a momentum framework.'}
- {'text': "IV Rank 100% on 科创50 was a screaming sell signal that was ignored at entry. All 4 positions opened yesterday were 688/300 codes with IV Rank 87-100%. Per V2 IV rules, entries in IV>75% should use 'only strongest setups with wider stops' — yet all were standard-sized. The vol expansion crushed positions within 1 day.", 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h017', 'mechanism': 'Extreme IV signals regime instability — the market is pricing in large moves. Entering during extreme IV with standard sizing guarantees that adverse moves exceed normal stop distances. Need to either size down 50% or widen stops proportionally.'}
- {'text': "The -3% in first 3 days rule correctly identified bad-timing entries on all 4 positions within 1 day. This sub-rule is doing more work than the -5% stop because it catches the 'entered at the wrong moment' problem before the full stop is hit. In V1, these positions would have been held and rationalized.", 'type': 'rule', 'tags': ['exit-rule', 'timing'], 'evidence_type': 'supporting', 'mechanism': "When a position is down -3%+ within the first 1-3 days, it almost always means the entry timing was wrong — either the sector was about to rotate or the stock was overextended. Fast exit prevents the -3% from becoming -8% while the trader 'waits for the thesis to play out.'"}
- {'text': "科创50 has now broken down twice in 2 weeks: -7.7% on 7/2 and -3.67% today. When a sector-leading index breaks down twice, do NOT buy dips in that sector. The trend has changed from 'pullback in an uptrend' to 'distribution/rotation.' This should have been recognized before yesterday's 4-tech-position entry.", 'type': 'observation', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'mechanism': 'A single large drop can be a buying opportunity; a second large drop in the same direction within 2 weeks confirms trend change. The second breakdown validates the first as structural, not noise.'}
