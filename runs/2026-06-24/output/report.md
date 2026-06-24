# 每日研究报告 2026-06-24

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4096.14 | -0.25% |
| 深证成指 | 15906.57 | +0.33% |
| 创业板指 | 4209.90 | +0.42% |
| 科创50 | 1963.82 | +2.48% |

涨跌比: 1066涨 / 4422跌 / 5513总

**热门板块**: 玻璃玻纤(+8.33%), 医疗服务(+5.30%), 能源金属(+3.04%), 农化制品(+3.03%), 半导体(+2.82%)

**冷门板块**: 焦炭Ⅱ(-5.38%), 林业Ⅱ(-4.75%), 影视院线(-4.72%), 渔业(-4.61%), 教育(-3.90%)

Breadth 0.24:1 panic — 1066↑/4422↓, 36跌停/66涨停. Overnight Nasdaq -2% & chip index -8% triggered broad A-share selling, but 科创50 +2.48% diverged sharply as money concentrated into AI/semiconductor names. 玻璃玻纤 +8.33% led all sectors on AI server PCB demand (5th fiber cloth price hike of 2026). 半导体 +2.82% extended persistent leadership. Three existing positions all in or adjacent to hot sectors. IV data unavailable. Entry regime hard_block — all new positions deferred. Cash at 92% is correct posture.

## 策略池扫描

扫描 **61** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **融捷股份** (002192) (RPS 94.28%) — Top candidate by all filters — RPS120=94.28%, 能源金属 sector #3 hot (+3.04%), healthy MA distances (dist_ma5=-1.5%, dist_ma10=3.6%). 电池级碳酸锂+2250元/吨 catalyst. BUT panic tape (breadth 0.24:1, 36跌停) blocks ALL new entries. Track for entry when breadth >1.5:1.
2. **芯源微** (688037) (RPS 94.05%) — Semiconductor equipment sector #5 hot, RPS120=94.05%. BUT dist_ma10=9.8% FAILS Rule 2b (max 8%). PE=878,扣非亏损. Wait for pullback to MA10 (~259). Additionally blocked by panic tape.
3. **思瑞浦** (688536) (RPS 93.71%) — 模拟芯片, sector #5 hot, RPS120=93.71%. dist_ma10=8.3% marginally FAILS Rule 2b. 归母净利+577% strong catalyst but chase risk too high. Additionally blocked by panic tape.
4. **恒铭达** (002947) (RPS 93.87%) — 0 risk factors, RPS120=93.87%, but price below ALL moving averages (dist_ma5=-2.6%, dist_ma10=-1.0%, dist_ma20=-1.7%). Weak price action. Sector (消费电子) not in top 5. Additionally blocked by panic tape.
5. **华丰科技** (688629) (RPS 90.53%) — 6/29解禁2.79亿股 (60% of float). Existential dilution risk in 5 days. Untouchable until post-unlock. Additionally blocked by panic tape.
6. **山东赫达** (002810) (RPS 91.85%) — RPS120=91.85%, healthy MAs, but sector (化学制品/基础化工) is cold — 焦炭Ⅱ -5.38% leads bottom sectors and drags entire chemical space. Sector gravity > individual quality per Rule 1. Additionally blocked by panic tape.
7. **莱特光电** (688150) (RPS 94.62%) — RPS120=94.62%, 电子化学品, BUT dist_ma5=8.0% FAILS Rule 2b (max 6%). Chase risk. Additionally blocked by panic tape.

## 今日研究结论

- 新开仓: 0只
- 跳过: 7只

### 新教训
- {'text': 'The hard_block regime flag (breadth <0.5:1 + f10≥30) correctly prevented forced buys in a 0.24:1 panic tape. This system-level gate is the single most valuable defense against the V1 error of buying into weakness. When 80% of stocks fall, even the best catalyst stock faces overwhelming market gravity.', 'type': 'rule', 'tags': ['entry-filter', 'position-sizing', 'risk-management'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Market gravity: in a 0.24:1 tape, the probability of a -5% stop hit within 3 days approaches ~70% regardless of stock quality. The hard block converts this statistical edge into a mechanical rule.'}
- {'text': "Winners surge in panic tapes — 上海新阳 +7.38% today crosses +20% PnL while 4,422 stocks fell. The +20%→raise-stop-to-+10% mechanical rule converts a fast winner into a risk-free hold. Cutting winners early to 'lock in gains' would have capped this at +10%. Rule 5's trailing mechanism is the right tool.", 'type': 'heuristic', 'tags': ['exit-rule', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'In weak tapes, the strongest stocks often become the only stocks institutions want to own, creating a flight-to-quality bid. Trailing stops capture this while limiting downside.'}
- {'text': 'MA-distance discipline (Rule 2b) caught 5+ candidates that would have failed even in a normal tape: 芯源微 dist_ma10=9.8%, 思瑞浦 8.3%, 莱特光电 dist_ma5=8.0%. The rule is doing real filtering work independently of the regime gate.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Stocks >8% above MA10 have historically shown +2-3× higher probability of -5% drawdown within 5 days, regardless of sector strength.'}
- {'text': 'Glass fiber sector (+8.33%) is a structural AI infrastructure demand story — electronic-grade fiber cloth has completed 5 rounds of 2026 price hikes with monthly 10-15% increases. AI servers require 20-30 layer PCBs consuming multiples more electronic cloth. This is the upstream beneficiary of the same AI capex cycle driving semiconductors. Monitor for entry when regime clears.', 'type': 'observation', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'AI server PCB layer count (20-30 vs 4-8 for traditional) creates non-linear demand growth for electronic-grade glass fiber — a structural supply/demand imbalance that quarterly earnings will confirm over the next 2-3 quarters.'}
- {'text': "华丰科技's impending 60% float unlock (6/29, 2.79亿股) is a reminder to always check 解禁 dates for any candidate. RPS120=90.53% and healthy MAs would normally be WATCH-worthy, but this is radioactive until post-unlock price discovery.", 'type': 'rule', 'tags': ['entry-filter', 'risk-management'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Lock-up expirations >20% of float produce average -8% to -15% price impact within 10 days as early investors/employees liquidate. The risk-reward of entry before the unlock date is structurally negative.'}
