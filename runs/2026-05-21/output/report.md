# 每日研究报告 2026-05-21

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4077.28 | -2.04% |
| 深证成指 | 15247.27 | -2.07% |
| 创业板指 | 3829.78 | -2.35% |
| 科创50 | 1764.17 | -3.70% |

涨跌比: 695涨 / 4773跌 / 5503总

**热门板块**: 家电零部件Ⅱ(+1.46%), 航空机场(+1.28%), 乘用车(+0.86%), 国有大型银行Ⅱ(+0.83%), 电机Ⅱ(+0.69%)

**冷门板块**: 电子化学品Ⅱ(-5.79%), 其他电子Ⅱ(-5.70%), 油服工程(-5.64%), 通信设备(-5.43%), 橡胶(-5.32%)

Bearish/panic regime. Breadth 0.15:1 bearish, 37涨停/69跌停, broad-based selloff with 4773 decliners and all 3 major indices red (上证-2.04%, 深成指-2.07%, 创业板指-2.35%). Hot sectors are narrow and defensive: 家电零部件Ⅱ +1.46%, 航空机场 +1.28%, 乘用车 +0.86%, 国有大型银行Ⅱ +0.83%, 电机Ⅱ +0.69%; cold sectors led by 电子化学品Ⅱ -5.79%, 其他电子Ⅱ -5.70%, 油服工程 -5.64%, 通信设备 -5.43%, 橡胶 -5.32%. Research checks show liquid-cooling/AI data center themes were active very recently, and 神马电力 still has fresh institutional attention, but today the market is in a hard risk-off unwind. IV context is not the problem: broad-market IV rank is mostly low-to-neutral (overall sentiment 偏乐观, avg IV rank 24.3%), so sizing would normally be fine, but breadth panic fully overrides IV and blocks new positions.

## 策略池扫描

扫描 **55** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **神马电力** (603530) (RPS 94.79%) — Entry regime hard-blocked. Although 电网设备 is relatively resilient and stock MA distances are acceptable (dist_ma5_pct -3.6%, dist_ma10_pct -2.9%, dist_ma20_pct -0.4%) with RPS120 94.79, market breadth is panic and no new longs are allowed.
2. **九安医疗** (002432) (RPS 94.98%) — 医疗器械 not in provided hot-sector top list, and the market buy gate failed. Setup itself is technically acceptable (dist_ma5_pct -1.6%, dist_ma10_pct -0.7%, dist_ma20_pct 5.4%) but sector-first plus panic tape means skip.
3. **恩捷股份** (002812) (RPS 93.56%) — Market hard-block aside, stock is only borderline on RPS and not in provided hot-sector top list. No current entry edge strong enough to override tape; skip.
4. **华锡有色** (600301) (RPS 92.0%) — Technically one of the cleaner pullback setups (dist_ma5_pct -2.6%, dist_ma10_pct -3.1%, dist_ma20_pct 2.4%), but 有色金属 is not in the provided top sectors and the entry regime is panic. Sector-first says no new entry.
5. **睿创微纳** (688002) (RPS 89.26%) — 军工电子 not in provided hot-sector top list. Even though MA distances pass (dist_ma5_pct -5.0%, dist_ma10_pct -3.1%, dist_ma20_pct 9.7%), the market is panic and 科创 risk appetite is weak.
6. **长芯博创** (300548) (RPS 94.83%) — 通信设备 is explicitly in bottom 5 sectors at -5.43%. Sector gravity overrides stock quality; no entry regardless of catalyst or RPS.
7. **德科立** (688205) (RPS 93.74%) — 通信设备 is in the bottom 5 sectors at -5.43%, and dist_ma20_pct 15.0% also exceeds the anti-chase limit. Double disqualifier.
8. **伟测科技** (688372) (RPS 93.6%) — 半导体/科创 today sits in a weak risk-off pocket, and dist_ma20_pct 14.3% exceeds the 12% anti-chase threshold. Skip even before considering the panic regime.
9. **江丰电子** (300666) (RPS 94.37%) — 半导体材料 stock is overextended: dist_ma5_pct 6.7%, dist_ma10_pct 16.8%, dist_ma20_pct 32.2%. Fails non-negotiable MA-distance rule.
10. **芯碁微装** (688630) (RPS 91.33%) — Excellent growth and strong RPS, but dist_ma10_pct 11.5% and dist_ma20_pct 31.3% both fail anti-chase limits. Also market regime blocks new longs.
11. **明阳电路** (300739) (RPS 91.82%) — PCB/元件 not in provided hot-sector top list, and dist_ma10_pct 9.8% plus dist_ma20_pct 14.2% fail MA-distance rule. Skip.
12. **万凯新材** (301216) (RPS 86.91%) — Technicals are acceptable and VCP is present, but 基础化工/塑料 is not in the provided hot-sector leaders and the tape is panic. Without regime support, do not force a starter position.

## 今日研究结论

- 新开仓: 0只
- 跳过: 12只

### 新教训
- {'text': 'When breadth collapses to 0.15:1 with 69跌停 and all 3 major indices red, the correct momentum action is zero new longs even if a few individual charts still pass RPS and MA filters.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'In panic tapes, correlation spikes toward 1 and sector/stock selection edge is overwhelmed by forced de-risking.'}
- {'text': 'The MA-distance anti-chase rule continues to eliminate many superficially attractive leaders such as 江丰电子、芯碁微装、伟测科技 before they become bad entries.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'Large distance above MA10/MA20 means weak nearby support and higher mean-reversion risk, especially after broad-market stress.'}
- {'text': 'Today’s sector tape shows classic defensive hiding: banks, airports, auto pockets and home-appliance parts up, while 通信设备、电子化学品 and other high-beta tech groups lead downside.', 'type': 'observation', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'When capital rotates into lower-beta or policy/earnings-stable groups, momentum longs in speculative tech usually lose follow-through quality.'}
- {'text': 'A clean stock-specific setup is not enough if its sector is on the wrong side of the tape; 长芯博创 and 德科立 both fail first on sector weakness because 通信设备 is bottom-5.', 'type': 'heuristic', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h027', 'mechanism': 'Sector ETFs and basket selling drag even strong single names lower, reducing breakout persistence and increasing false-entry risk.'}
