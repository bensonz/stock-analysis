# 每日研究报告 2026-04-01

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3944.80 | +1.36% |
| 深证成指 | 13640.05 | +1.20% |
| 创业板指 | 3222.59 | +1.18% |
| 科创50 | 1293.48 | +2.96% |

涨跌比: 4392涨 / 970跌 / 5488总

**热门板块**: 游戏Ⅱ(+4.91%), 化学制药(+4.47%), 酒店餐饮(+4.10%), 医疗服务(+4.07%), 生物制品(+3.72%)

**冷门板块**: 林业Ⅱ(-5.12%), 航天装备Ⅱ(-2.36%), 轨交设备Ⅱ(-1.10%), 乘用车(-0.82%), 风电设备(-0.78%)

Breadth 4.53:1 bullish, 52涨停/8跌停, 3/3 major indices green, not a panic tape. 科创50 +2.96% confirms growth appetite. Hot sectors in provided data are 游戏Ⅱ、化学制药、酒店餐饮、医疗服务、生物制品, while 风电设备/乘用车 remain cold. IV context is mildly complacent but not extreme for most stock proxies (roughly 16%-22% IV Rank), so sizing can stay normal; however, many candidates are extended, so despite strong regime the correct action is no new positions until pullbacks appear.

## 策略池扫描

扫描 **21** 只策略池股票
(来源: local_pricedb+cf_cross)

## 跳过标的

1. **国电南自** (600268) (RPS 91.15%) — Fresh earnings catalyst is strong and sector logic is valid, but fails non-negotiable MA chase rule: dist_ma5_pct 7.0% and dist_ma10_pct 8.3%, both above allowed limits.
2. **舒华体育** (605299) (RPS 94.93%) — RPS120 94.93 is allowed only with exceptions, but entry is invalid because stock is massively extended: dist_ma5_pct 16.0%, dist_ma10_pct 30.7%, dist_ma20_pct 47.9%.
3. **烽火通信** (600498) (RPS 95.3%) — RPS120 95.3 is above the allowed upper bound; also 2026-03-31 change_pct was 13.38%, indicating a breakout day that is too extended to chase without pullback support.
4. **华通线缆** (605196) (RPS 95.36%) — RPS120 95.36 is above allowed range and recent 10-day relative strength note says short-term price performance only beat 2.6% of market, so momentum quality is mixed.
5. **海星股份** (603115) (RPS 97.08%) — RPS120 97.08 is too extended under Rule 2. Wait for pullback rather than chase.
6. **华懋科技** (603306) (RPS 92.83%) — Sector is wrong: 汽车零部件 aligns with today's cold area as 乘用车 is bottom 5. Sector-first rule blocks entry.
7. **明阳智能** (601615) (RPS 90.8%) — Sector is wrong: 风电设备 is in today's bottom 5. Sector gravity overrides acceptable RPS.
8. **华鲁恒升** (600426) (RPS 88.62%) — RPS120 88.62 is acceptable, but provided sector list does not place its group among top sectors and catalyst is older/less urgent than stronger momentum names.
9. **东材科技** (601208) (RPS 90.86%) — Setup is technically fine, but sector not confirmed in today's top 30% list and there is no fresh catalyst beyond older PET铜箔/业绩 narrative, so not enough sector-first edge for entry.
10. **利柏特** (605167) (RPS 93.49%) — Recent contract news is positive, but RPS120 93.49 sits in upper zone without clear sector leadership in today's provided data; short-term price note also says last 10-day performance only beat 8.8% of market.
11. **华锡有色** (600301) (RPS 93.29%) — Recent 10-day price strength is weak in input and current price is below MA20 by 13.1%, showing loss of near-term momentum quality despite acceptable long-cycle RPS.
12. **三祥新材** (603663) (RPS 91.77%) — RPS120 qualifies, but current price is below MA20 by 12.6% and recent 10-day strength note is weak, indicating broken near-term momentum rather than buyable strength.

## 今日研究结论

- 新开仓: 0只
- 跳过: 12只

### 新教训
- {'text': '强市场并不等于随便追；今天最强的电网设备候选国电南自，仍然因为 dist_ma5_pct 和 dist_ma10_pct 双双超标而应放弃新开仓。', 'type': 'rule', 'tags': ['entry-filter', 'timing', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': '市场给了做多窗口，但过度偏离均线会显著抬高均值回归风险；强板块里也要等回踩支撑，而不是见强就追。'}
- {'text': 'RPS 90附近配合可接受均线距离，仍然是当前最稳健的新仓形态；RPS>95 的候选今天多数都处在不可追状态。', 'type': 'heuristic', 'tags': ['entry-filter', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h001', 'mechanism': '90附近说明趋势已经成立但尚未极端拥挤，而95以上往往对应短线情绪过热、追高后胜率下降。'}
- {'text': '冷板块约束依然有效：风电设备和汽车链即使个股RPS尚可，也应先服从 sector-first 规则。', 'type': 'signal', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': '', 'mechanism': '个股强度可以滞后于板块资金撤退，板块一旦掉入底部区域，后续承接通常变差，继续开仓性价比下降。'}
