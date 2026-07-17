# 每日研究报告 2026-07-17

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3764.16 | -3.05% |
| 深证成指 | 13706.88 | -5.40% |
| 创业板指 | 3428.63 | -7.15% |
| 科创50 | 1715.40 | -7.12% |

涨跌比: 482涨 / 5001跌 / 5523总

**热门板块**: 国有大型银行Ⅱ(+1.86%), 电力(+1.18%), 炼化及贸易(+1.12%), 铁路公路(+0.62%), 白色家电(+0.49%)

**冷门板块**: 通信设备(-10.84%), 其他电子Ⅱ(-10.25%), 元件(-9.23%), 半导体(-8.36%), 医疗服务(-7.99%)

2026-07-17: PANIC SELL-OFF. Breadth 0.10:1 (482↑/5001↓), 212跌停/35涨停. 上证-3.05%, 深证-5.4%, 创业板-7.15%, 科创50-7.12%. All ETFs at IV Rank 1.0 (max panic). Drivers: US semis rout (费城-3.5%, SK海力士-12%), 中报兑现卖出, 监管打压. Defensive rotation: banks +1.86%, power +1.18%. Tech sectors in freefall: 通信设备-10.84%, 半导体-8.36%. Portfolio 100% cash (¥956K), -4.38% cumulative. Zero new positions — entry regime hard_block. Prepare shopping list for when breadth normalizes.

## 策略池扫描

扫描 **54** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **凯莱英** (002821) (RPS 92.42%) — 医疗服务 sector bottom-5 (-7.99%), dist_ma20_pct +18.8% violates chase rule, panic tape blocks all entries. Excellent fundamentals (9 highlights, 股权激励) but sector gravity + market regime override.
2. **华天科技** (002185) (RPS 93.47%) — 半导体 sector bottom-5 (-8.36%), stock crashed through all MAs (dist_ma5 -14.0%, dist_ma10 -8.1%), 跌停 on 7/15. Former momentum decisively broken.
3. **荣昌生物** (688331) (RPS 89.25%) — 医疗服务 sector bottom-5 (-7.99%). Stock holding at MA5/MA10 (dist_ma5 +0.3%) which is constructive, but sector gravity + panic breadth override. No entry in this tape.
4. **金钼股份** (601958) (RPS 91.35%) — 小金属/有色金属 sector not in top 30%. Commodity rotation not leading. Panic tape blocks all entries regardless of individual stock quality.
5. **中石科技** (300684) (RPS 88.79%) — 电子化学品 sector caught in tech rout. Good MA positioning (dist_ma5 -1.7%) and margin adding signal, but RPS120=88.79% modest and sector is wrong. Entry regime blocked.
6. **新锐股份** (688257) (RPS 99.13%) — RPS120=99.13% very strong, but dist_ma10 -17.2% means stock is in freefall through MAs. RPS is lagging indicator; price action has broken. Panic tape.
7. **博迁新材** (605376) (RPS 99.56%) — RPS120=99.56% extreme, but dist_ma10 -25.1% — stock obliterated, 跌停 7/16. This is catching a falling knife, not buying strength. No current price data needed; MA distances tell the story.

## 今日研究结论

- 新开仓: 0只
- 平仓: 0只
- 跳过: 7只

### 新教训
- {'text': 'Panic breadth (0.10:1, 212跌停) + IV Rank 1.0 across all ETFs = absolute no-entry signal. Every buy-gate condition violated. Cash is the correct position.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'When breadth collapses to <0.5:1 and all 3 major indices are deep red with >100跌停, any new long position has near-certain negative drift. The IV spike to 1.0 confirms genuine panic, not a fleeting dip. Cash preserves capital for the inevitable bounce.'}
- {'text': "Strategy pool (54 stocks) is structurally misaligned with defensive rotations. All names are growth/tech/electronics — zero exposure to today's top-5 sectors (banks, utilities, energy, infra, appliances). When the market rotates defensively, our pool has nothing to offer.", 'type': 'observation', 'tags': ['sector', 'position-sizing'], 'evidence_type': 'supporting', 'mechanism': 'The cheesefortune_intersection pool is generated from momentum/quality screens that inherently favor growth. During risk-off rotations, these stocks are the first to be sold. A broader pool or sector-rotation overlay would be needed to capture defensive flows.'}
- {'text': "In a panic sell-off, negative MA distances across the entire pool indicate broken trends, not buying opportunities. Nearly all 54 stocks show dist_ma5/ma10/ma20 deeply negative — these aren't pullbacks to support; they're trend breakdowns.", 'type': 'heuristic', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'mechanism': "When stocks crash through all MAs simultaneously (dist_ma5, dist_ma10, dist_ma20 all deeply negative), it signals that sellers are in control at every timeframe. The RPS values remain high because they're calculated over longer lookbacks, but the immediate price action has decisively broken prior uptrends."}
- {'text': "The entry_regime hard_block with sizing_multiplier=0.0 correctly prevented deployment of capital. A systematic gate is superior to analyst discretion in panic conditions — it removes the temptation to 'buy the dip' when the dip is still accelerating.", 'type': 'rule', 'tags': ['entry-filter', 'position-sizing'], 'evidence_type': 'supporting', 'mechanism': 'The regime check evaluates 4 independent conditions (breadth ratio, positive indices count, limit-up/down counts, sizing multiplier). When all 4 fail simultaneously, the probability of a false negative (missing a good entry) is far lower than the probability of a false positive (entering into a continuing crash).'}
