# 每日研究报告 2026-04-01

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3942.64 | +1.30% |
| 深证成指 | 13680.46 | +1.50% |
| 创业板指 | 3240.60 | +1.75% |
| 科创50 | 1295.65 | +3.13% |

涨跌比: 4224涨 / 1144跌 / 5485总

**热门板块**: 酒店餐饮(+6.04%), 游戏Ⅱ(+5.78%), 医疗服务(+5.22%), 化学制药(+4.73%), 生物制品(+4.18%)

**冷门板块**: 林业Ⅱ(-5.29%), 油气开采Ⅱ(-2.43%), 航天装备Ⅱ(-2.08%), 轨交设备Ⅱ(-1.23%), 光伏设备(-1.20%)

Breadth 3.69:1 bullish, 64涨停/15跌停, all 3 major indices green and 科创50 +3.13%, so the regime is risk-on. Hot sectors (top 5): 酒店餐饮 +6.04%, 游戏Ⅱ +5.78%, 医疗服务 +5.22%, 化学制药 +4.73%, 生物制品 +4.18%. Cold sectors (bottom 5): 林业Ⅱ -5.29%, 油气开采Ⅱ -2.43%, 航天装备Ⅱ -2.08%, 轨交设备Ⅱ -1.23%, 光伏设备 -1.20%. Position sector alignment: 0/2 positions in hot sectors. IV context is mildly complacent but not extreme: overall avg IV rank about 23%, stock-level proxies for current names remain in normal sizing range.

## 策略池扫描

扫描 **21** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) (RPS 91.15%) — Sector is not in the provided top 30% leadership list and MA chase filter fails: dist_ma5_pct 7.0% and dist_ma10_pct 8.3%, both above allowed entry limits. Good earnings catalyst, but this is chasing.
2. **舒华体育** (605299) (RPS 94.93%) — Not buying strength after a spike this extended: dist_ma5_pct 16.0%, dist_ma10_pct 30.7%, dist_ma20_pct 47.9% all fail the non-negotiable MA distance rule.
3. **烽火通信** (600498) (RPS 95.3%) — RPS120 95.3% is above the allowed range and effectively in chase territory; also this sector is not in the provided top 30% sector leadership list for today.
4. **华通线缆** (605196) (RPS 95.36%) — RPS120 95.36% is above the normal buy range, and although its industry is电网设备, that sector is not in the provided top-5 hot sectors today. No need to force an entry.
5. **海星股份** (603115) (RPS 97.08%) — RPS120 97.08% is above 95%, which is a skip under the framework. Wait for a pullback rather than chase.
6. **华懋科技** (603306) (RPS 92.83%) — Sector (汽车零部件) is not in the provided top leadership group, and the stock also has weak recent price-strength note in events. No current price advantage signal beyond that.
7. **明阳智能** (601615) (RPS 90.8%) — Sector (风电设备) is not in the provided top 30% leadership set, and price sits below MA5/10/20 with dist_ma20_pct -13.5%, showing weak tape rather than breakout strength.
8. **华鲁恒升** (600426) (RPS 88.62%) — RPS120 88.62 is acceptable, but sector is not in the provided top sector leadership list and catalyst looks more medium-term than fresh. Better as skip than forced buy.
9. **东材科技** (601208) (RPS 90.86%) — Sector is outside the provided top leadership list, and despite acceptable MA distances the edge is not strong enough without sector confirmation.
10. **利柏特** (605167) (RPS 93.49%) — Sector (建筑装饰/专业工程) is not in the provided top leadership list. Fresh contract news exists, but sector-first rule keeps this as skip.
11. **华锡有色** (600301) (RPS 93.29%) — Sector (有色金属/小金属) is not in today's provided top leadership list, and dist_ma20_pct -13.1% shows price is materially below MA20 rather than in a clean momentum continuation.
12. **三祥新材** (603663) (RPS 91.77%) — Sector is not in the provided top sector leaders, and dist_ma20_pct -12.6% shows the stock is trading below medium support rather than breaking out from a tight setup.

## 今日研究结论

- 新开仓: 0只
- 跳过: 12只

### 新教训
- {'text': "Strong market breadth does not override the MA-distance anti-chase rule; today's best-looking short-term winners like 舒华体育 and 国电南自 still fail because they are too far above MA5/MA10.", 'type': 'rule', 'tags': ['entry-filter', 'timing', 'discipline'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Broad rallies create many tempting breakaway candles, but extension from short MAs raises mean-reversion risk and worsens reward-to-risk even in good tapes.'}
- {'text': 'Sector-first filtering materially shrinks the buy list even on a bullish tape; many individual candidates had acceptable RPS but their industries were not in the provided hot-sector leadership bucket.', 'type': 'heuristic', 'tags': ['sector', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': 'Momentum persistence is stronger when both stock and sector align; isolated stock strength without sector tailwind is less reliable for fresh entries.'}
- {'text': 'Low-IV backdrop is a sizing input, not a buy trigger. With avg IV rank around 23%, entries should still demand sector leadership and non-extended price structure.', 'type': 'signal', 'tags': ['timing', 'position-sizing', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Cheap volatility can support trend continuation, but it also increases vulnerability to abrupt pullbacks if entries are made after extension.'}
