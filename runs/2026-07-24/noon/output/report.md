# 每日研究报告 2026-07-24

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3830.19 | -1.20% |
| 深证成指 | 13873.50 | -1.77% |
| 创业板指 | 3511.75 | -1.78% |
| 科创50 | 1794.48 | +0.27% |

涨跌比: 548涨 / 4939跌 / 5527总

**热门板块**: 地面兵装Ⅱ(+3.65%), 半导体(+0.59%), 国有大型银行Ⅱ(+0.41%), 股份制银行Ⅱ(+0.27%), 城商行Ⅱ(+0.11%)

**冷门板块**: 贵金属(-4.56%), 工业金属(-4.54%), 医疗美容(-3.82%), 广告营销(-3.61%), 数字媒体(-3.59%)

PANIC TAPE — Breadth 0.11:1 (548 up, 4939 down). All 3 major indices red (上证-1.20%, 深证-1.77%, 创业板-1.78%). 32涨停/4跌停. Distribution heavily negative: 2734 stocks down 2-4%, 694 down 4-7%. IV elevated: 科创50 IV rank 79.85% (panic), 创业板 65.94%. Defense (+3.65%) and banks (+0.11~0.41%) are the only hiding places; resources (-4.5%) aggressively sold. BofA calls chip selloff 'a summer reset, not a fundamental reversal.' Entry gate: HARD BLOCK — no new positions. Portfolio: SELL 冰轮环境 (-3.85% in 1 day), HOLD 凯莱英 (-1.31%).

## 策略池扫描

扫描 **50** 只策略池股票
(来源: cheesefortune_intersection)

## 今日平仓

### 1. 冰轮环境 (000811) — SELL — -3.85%

- **出场价**: ¥41.2
- **持有天数**: 1天
- **板块排名**: neutral (通用设备 not in top/bottom 5)

Rule 5 double trigger: (1) -3.85% from entry in <3 days = automatic SELL; (2) Stop proximity CRITICAL — only 1.19% above 40.71 stop, gap risk is real. Thesis (datacenter liquid cooling, AI demand, 合同负债¥13B) is valid but entry timing was terrible. Cut now, re-enter when market regime clears.

## 跳过标的

1. **芯碁微装** (688630) (RPS 99.46%) — HARD BLOCK: panic regime (breadth 0.11:1, 0/3 indices green). Would be top pick otherwise — semiconductor sector #2, RPS120=99.46, CoWoS-L catalyst, 调入港股通, 0 risks. dist_ma5=6.0% borderline chase.
2. **昊志机电** (300503) (RPS 98.53%) — HARD BLOCK: panic regime. Best MA setup in candidate pool (dist_ma5=-2.0%), H1净利+266%, 机器人+主轴双驱动. dist_ma5=-2.0% means no chase risk. Would be STRONG BUY in normal tape.
3. **国瓷材料** (300285) (RPS 98.49%) — HARD BLOCK: panic regime. MLCC涨价+氧化锆提价10-40% catalyst fresh. RPS120=98.49. dist_ma5=5.8% — tight but acceptable. 16家机构评级, 69%买入.
4. **华丰科技** (688629) (RPS 97.44%) — HARD BLOCK + Rule 2b violation (dist_ma5_pct=7.8% > 6% chase threshold). Military electronics + 高速铜连接概念. Strong fundamentals (Q rev+121%, net profit+506%).
5. **星宸科技** (301536) (RPS 96.24%) — HARD BLOCK + severe Rule 2b violation (dist_ma5=22.0%, dist_ma10=20.4%, dist_ma20=17.7% — all three thresholds blown). Stock has run way too far from support.
6. **恒逸石化** (000703) (RPS 96.42%) — HARD BLOCK + Rule 2b violation (dist_ma10=8.7% > 8%). 炼化, H1净利+2326-2547% but sector (石油石化) not hot.

## 今日研究结论

- 新开仓: 0只
- 平仓: 1只
- 跳过: 6只

### 新教训
- {'text': 'Hard block (h077) prevents FOMO entries again: 芯碁微装 (港股通调入, semiconductor #2, 0 risks) and 昊志机电 (H1 +266%, perfect MA setup) would have been bought in V1. V2 correctly preserves cash in panic breadth (0.11:1).', 'type': 'observation', 'tags': ['entry-filter', 'regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h077', 'mechanism': 'Panic breadth means systematic selling overwhelms stock-specific catalysts. Even perfect setups get dragged down.'}
- {'text': 'Stop proximity rule (h024) validated: 冰轮环境 at 1.19% above stop triggered proactive SELL. Waiting for exact -5% trigger in panic tape risks gap-through (扬杰科技 lesson). Proactive action saved capital.', 'type': 'rule', 'tags': ['exit-rule', 'risk-management'], 'evidence_type': 'supporting', 'related_hypothesis': 'h024', 'mechanism': 'In fast-moving panic tapes, hard stops get gapped through. Proactive exit at 1-2% above stop is superior to waiting for the exact trigger.'}
- {'text': "The -3% in 3 days rule (V2 Rule 5) caught a bad entry on day 1. 冰轮环境 went from entry to -3.85% in one session. V1 would have rationalized 'thesis still valid' and held. V2 cuts immediately — correct behavior.", 'type': 'rule', 'tags': ['exit-rule', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'When a stock drops -3%+ immediately after entry, it signals bad timing regardless of thesis quality. Fast cuts preserve capital for better entries.'}
- {'text': 'Sector gravity confirmed: defense (+3.65%) and banks are the only green sectors in a risk-off rotation. When this pattern emerges, even strong stocks in neutral sectors get dragged. 通用设备 (冰轮环境) is not buoyed by sector tailwinds.', 'type': 'signal', 'tags': ['sector', 'regime'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Risk-off rotations create a gravitational pull: capital flows to defense/banks, everything else suffers regardless of individual merit.'}
- {'text': "V2's entry regime gate (0.11:1 breadth, 0/3 indices green → hard block) is the single most important improvement from V1. V1's -3.1% loss came partly from forcing entries in deteriorating conditions. Cash is a valid position.", 'type': 'observation', 'tags': ['entry-filter', 'regime', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h077', 'mechanism': "The entry gate converts ambiguous 'maybe wait' signals into binary yes/no decisions, eliminating the paralysis and FOMO that plagued V1."}
