# 每日研究报告 2026-07-28

> 模型: deepseek-v4-pro（DeepSeek V4 Pro primary） · 300239+9648 tokens

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3813.32 | -1.16% |
| 深证成指 | 13509.68 | -4.52% |
| 创业板指 | 3327.03 | -7.35% |
| 科创50 | 1693.48 | -6.33% |

涨跌比: 2603涨 / 2769跌 / 5525总

**热门板块**: 休闲食品(+3.71%), 国有大型银行Ⅱ(+2.63%), 白酒Ⅱ(+2.36%), 工程咨询服务Ⅱ(+2.30%), 教育(+2.27%)

**冷门板块**: 通信设备(-12.42%), 元件(-9.25%), 半导体(-7.18%), 玻璃玻纤(-7.02%), 其他电子Ⅱ(-6.61%)

PANIC DAY. All 4 major indices deep red: 上证 -1.16%, 深证 -4.52%, 创业板 -7.35%, 科创50 -6.33%. Breadth 0.94:1 (2603↑/2769↓), 68涨停/52跌停. Distribution skewed negative — 287 stocks in f7_10 bucket vs only 26 in r7_10. IV extreme fear (avg rank 74.2%, 科创50 79.9%, 创业板 83.5%, 500ETF深 85.7%). Rotation: violent exit from AI/tech hardware (通信设备 -12.42%, 半导体 -7.18%) into defensives (白酒 +2.36%, 银行 +2.63%, 休闲食品 +3.71%). Global triggers: SK Hynix below IPO, Nvidia -5%, China chip breakthrough fears, oil -8%. Hard block active — no new positions. Sole position 凯莱英 being sold per -3%-in-3-days rule.

## 策略池扫描

扫描 **48** 只策略池股票
(来源: cheesefortune_intersection)

## 今日平仓

### 1. 凯莱英 (002821) — SELL — -3.78%

- **出场价**: ¥157.36
- **持有天数**: 2天
- **板块排名**: middle (医疗服务 not in top/bottom 5)

Rule 5 triggered: -3.78% in first 2 days (entry 163.54, current 157.36). Stop proximity critical at 1.27%. Stock showed relative strength (-3.43% vs 创业板 -7.35%) but V2 discipline requires cutting fast. CXO thesis intact — will re-enter if stock reclaims MA10 (171.09) on above-average volume with market regime normalized.

## 跳过标的

1. **芯碁微装** (688630) (RPS 99.32%) — dist_ma5_pct=+6.0% triggers Rule 2b (no chasing). 专用设备 sector not in hot list. Panic regime.
2. **华丰科技** (688629) (RPS 97.2%) — dist_ma5_pct=+7.8% triggers Rule 2b. 军工电子 sector. Panic regime.
3. **华峰测控** (688200) (RPS 99.36%) — 半导体 sector -7.18% (bottom 3 today). Despite perfect fundamentals (0 risks, RPS120=99.36, MA distances ok), sector gravity blocks entry. Panic regime.
4. **星宸科技** (301536) (RPS 95.81%) — dist_ma5=+22.0%, dist_ma10=+20.4%, dist_ma20=+17.7% — extreme extension on all timeframes. 半导体 bottom 3. Panic regime.
5. **恒逸石化** (000703) (RPS 96.03%) — dist_ma10=+8.7% triggers Rule 2b. Oil crash -8% directly undermines refining margin thesis. Panic regime.
6. **国瓷材料** (300285) (RPS 98.35%) — MA data corrupted (current_price=62.44 but MA5=483.93, dist_ma5=-87.1%). Likely corporate action not reflected. Cannot evaluate reliably. Panic regime.

## 今日研究结论

- 新开仓: 0只
- 平仓: 1只
- 跳过: 6只

### 新教训
- {'text': "-3% in first 3 days triggered on 凯莱英 during a -7.35% market panic day. Stock showed +4pp relative strength vs 创业板. Rule executed as written, but the tension between absolute PnL stop and market-relative performance needs tracking. If 凯莱英 rebounds strongly, consider a 'market-adjusted' variant: trigger only when (PnL - index_return) < -3%.", 'type': 'observation', 'tags': ['exit-rule', 'timing'], 'evidence_type': 'contradicting', 'mechanism': 'The -3% rule was designed for normal markets where a -3% decline signals bad timing. In a -7% index day, a -3% stock decline actually indicates strong relative demand — money is choosing this stock over alternatives. The absolute rule may force selling into relative strength.'}
- {'text': 'Hard block confirmed effective: prevented FOMO entries into 冰轮环境 (dist_ma5 +0.4%, RPS120=99.13) and 华峰测控 (0 risks, RPS120=99.36). Both would have been V1 buys. Cash preservation is correct in panic.', 'type': 'signal', 'tags': ['entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h077', 'mechanism': 'Panic regime rules are doing their job — preventing entries when the probability of a bounce is uncertain and gap risk is elevated.'}
- {'text': "MA data corruption detected in ~6 stocks (国瓷材料, 中材科技, 蔚蓝锂芯, 星网锐捷, 顺络电子, 中远海特). current_price vs MA values show 80-95% discrepancies, likely unadjusted corporate actions. These names should be flagged 'data integrity risk' and excluded from decisions until verified.", 'type': 'observation', 'tags': ['data-quality'], 'evidence_type': 'supporting', 'mechanism': "Stock splits, bonus issues, or rights offerings change share counts and per-share prices. If the MA calculation engine doesn't adjust historical prices, MA values become garbage. The dist_ma values become meaningless for entry/exit decisions."}
- {'text': "Today's sector data confirms h019: 6 of top-10 RPS120 stocks in our pool are in today's bottom 3 sectors (通信设备/元件/半导体). Sector gravity is overwhelming individual stock quality. Bottom-list sectors = hard no-buy zones.", 'type': 'signal', 'tags': ['sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'When a sector is in the bottom 3 by 5-day performance, even the best stocks in that sector get sold indiscriminately as institutions reduce exposure. Stock-level fundamentals cannot overcome sector-level flows during rotation events.'}
- {'text': 'Oil crash (-8% WTI, -9% Brent) is a fresh macro catalyst that voids the refining-margin thesis for 恒逸石化 and any petrochemical exposure. When a commodity underlying the thesis crashes, the thesis is broken regardless of company fundamentals.', 'type': 'signal', 'tags': ['macro', 'entry-filter'], 'evidence_type': 'supporting', 'mechanism': "恒逸石化's bull case was built on elevated refining margins from tight product markets. An 8% oil crash implies either demand destruction or supply glut — both undermine the margin thesis. Catalyst freshness just went from 'ongoing' to 'stale/broken'."}
