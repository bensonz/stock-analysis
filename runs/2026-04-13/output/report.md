# 每日研究报告 2026-04-13

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3978.20 | -0.20% |
| 深证成指 | 14356.09 | +0.33% |
| 创业板指 | 3466.72 | +0.52% |
| 科创50 | 1374.83 | +0.76% |

涨跌比: 1741涨 / 3621跌 / 5494总

**热门板块**: 玻璃玻纤(+8.05%), 能源金属(+2.65%), 养殖业(+2.47%), 林业Ⅱ(+2.36%), 电池(+2.20%)

**冷门板块**: 游戏Ⅱ(-3.94%), 航运港口(-2.40%), 动物保健Ⅱ(-2.18%), 医药商业(-2.13%), 电网设备(-1.89%)

Breadth 0.48:1 bearish, 71涨停/9跌停, weak participation despite 2 of 3 major indices green; this fails the minimum long-entry gate, so no new positions. Hot sectors (top 5): 玻璃玻纤 +8.05%, 能源金属 +2.65%, 养殖业 +2.47%, 林业Ⅱ +2.36%, 电池 +2.20%. Cold sectors (bottom 5): 游戏Ⅱ -3.94%, 航运港口 -2.40%, 动物保健Ⅱ -2.18%, 医药商业 -2.13%, 电网设备 -1.89%. Position sector alignment: 0/2 positions in hot sectors. Web checks show ongoing order/EPC support for 利柏特 and semicap policy/domestic-substitution support for 芯源微, but tape is too weak for fresh risk. IV context is generally low; small-cap/科创 proxies are especially low, which would reduce sizing even if entries were allowed.

## 策略池扫描

扫描 **198** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **伟测科技** (688372) (RPS 94.7%) — Market regime blocks new entries; breadth is only 0.48:1 despite stock-specific catalyst and clean MA distances. Also 科创板 IV Rank 12.2% implies half sizing even if tape improved.
2. **华峰测控** (688200) (RPS 90.7%) — Strong semicap setup with 0 risk factors and MA alignment, but market buy gate fails and 科创板 IV Rank is only 12.2%, so no new position today.
3. **新宙邦** (300037) (RPS 78.28%) — Battery sector is in today’s top 5 and catalyst is fresh, but market regime is weak so acceptable stock still becomes skip rather than buy.
4. **桂冠电力** (600236) (RPS 92.16%) — Setup is orderly and catalyst is fresh, but sector is not in today’s hot top bucket and new long entries are disallowed by breadth.
5. **中原内配** (002448) (RPS 74.07%) — Sector 汽车零部件 is not in today’s hot sectors, stock momentum is below the 75 floor for V2 entries, and no buy is allowed in weak tape.
6. **振江股份** (603507) (RPS 90.92%) — Fails no-chasing rule with dist_ma5_pct 6.4%, dist_ma10_pct 9.7%, dist_ma20_pct 16.4%; overextended even before considering weak market.
7. **科捷智能** (688455) (RPS 91.58%) — Fails no-chasing rule badly with dist_ma5_pct 19.4%, dist_ma10_pct 23.0%, dist_ma20_pct 18.9%; do not chase vertical extension.
8. **山东赫达** (002810) (RPS 92.34%) — Fails no-chasing rule with dist_ma5_pct 11.3%, dist_ma10_pct 16.3%, dist_ma20_pct 21.3%, so setup is invalid for fresh entry.
9. **广合科技** (001389) (RPS 90.0%) — Strong trend and catalyst, but current extension is close to chase territory and market regime already says no new positions.

## 今日研究结论

- 新开仓: 0只
- 跳过: 9只

### 新教训
- {'text': 'Weak breadth can completely override otherwise valid momentum candidates; today had 2 of 3 major indices green and 71涨停, but up/down was only 0.48:1, so the correct action is zero new longs.', 'type': 'rule', 'tags': ['sector', 'entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Index resilience without stock-level participation usually means narrow strength; new entries have lower follow-through when breadth is this weak.'}
- {'text': 'Volume confirmation remains the main near-term weakness in current holdings; both active positions are above entry, but each is trading at only about half of MAVOL30, which argues for hold-not-add rather than aggressive pyramiding.', 'type': 'signal', 'tags': ['exit-rule', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'Low-volume advances are more vulnerable to stalling, so letting winners run should not be confused with adding into weak participation.'}
- {'text': 'Today’s strongest candidate list still contains many technical traps: several names with acceptable RPS were disqualified by MA-distance extension rather than weak fundamentals.', 'type': 'observation', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': 'In late-stage momentum bursts, extension risk rises faster than catalyst quality, so MA-distance is the cleanest anti-chase filter.'}
