# 每日研究报告 2026-07-13

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3913.79 | -2.06% |
| 深证成指 | 14522.85 | -3.48% |
| 创业板指 | 3723.52 | -3.10% |
| 科创50 | 1994.32 | -3.42% |

涨跌比: 801涨 / 4683跌 / 5524总

**热门板块**: 中药Ⅱ(+3.31%), 油气开采Ⅱ(+3.01%), 农商行Ⅱ(+2.60%), 国有大型银行Ⅱ(+2.54%), 城商行Ⅱ(+2.26%)

**冷门板块**: 其他电子Ⅱ(-11.52%), 玻璃玻纤(-8.65%), 地面兵装Ⅱ(-8.50%), 光学光电子(-7.99%), 军工电子Ⅱ(-7.90%)

PANIC DAY. 美伊冲突升级推高油价（布伦特$78+），全球Risk-off。上证-2.06%，深证-3.48%，创业板-3.10%。涨跌比0.17:1（801涨/4683跌），187跌停，33涨停。科技/半导体板块重灾区（其他电子-11.5%，光学光电子-8%，军工电子-7.9%），防御板块（中药+3.3%，油气+3%，银行+2.3-2.6%）避险。IV数据缺失。Entry regime hard_block=true，0仓位，100%现金（¥979,809）。等恐慌消退。

## 策略池扫描

扫描 **67** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **全策略池67只** (ALL_67) — Market panic: breadth 0.17:1 (need 1.5:1), 0/3 major indices green, 187 limit-downs, entry_regime hard_block=true. No new positions allowed today.
2. **华天科技** (002185) (RPS 91.77%) — dist_ma5_pct +9.0%, dist_ma20_pct +23.5% — severely overextended per Rule 2b. Even without panic, this is un-buyable at current levels.
3. **凯莱英** (002821) (RPS 89.16%) — dist_ma20_pct +18.1% — extreme extension per Rule 2b (>12% hard cutoff). Interesting healthcare candidate otherwise, with equity incentive catalyst.
4. **京仪装备** (688652) (RPS 94.56%) — dist_ma20_pct +19.5% — extreme extension per Rule 2b. Semiconductor equipment sector also in heavy selloff zone.
5. **多氟多** (002407) (RPS 91.06%) — H1 earnings preview revealed Q2 net profit dropped 51-80% QoQ. Stock hit limit-down (-10%). Catalyst is negative, not positive. Fundamental breakdown.
6. **宏达电子** (300726) (RPS 91.85%) — Sector (军工电子Ⅱ) in bottom 5 today at -7.90%. No entry in cold sectors regardless of individual setup.
7. **奥来德** (688378) (RPS 93.42%) — Sector (光学光电子) -7.99% today, in bottom 5. dist_ma5 -7.9% shows ongoing decline. No entry.
8. **茂莱光学** (688502) (RPS 89.84%) — dist_ma20_pct +14.4% — extreme extension. Sector (光学光电子) in bottom 5. PE 1700x with low earnings quality.
9. **荣昌生物** (688331) (RPS 86.52%) — Interesting biotech candidate (sector adjacent to hot 中药). But dist_ma20 +9.9% is elevated. Also posting net losses. Wait for pullback + regime improvement.
10. **上海新阳** (300236) (RPS 93.85%) — Best technical setup in pool: dist_ma5 0.0% (at MA5), RPS120 93.85%. But sector (电子化学品) in broad tech selloff. Wait for sector stabilization.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': '市场恐慌日（涨跌比0.17:1, 187跌停）完美验证了entry_regime硬禁买规则——如果今天开新仓几乎必定遭遇-5%止损。V2的weak-market default正在保护资金。', 'type': 'heuristic', 'tags': ['entry-filter', 'risk-management'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': '恐慌日开盘即被套的概率极高，因卖盘碾压买盘。等待恐慌消退再入场是动量策略核心原则。'}
- {'text': '策略池67只股票几乎全在今日暴跌板块（半导体/电子/军工-7%~-11%），而上涨板块（中药/油气/银行）在池中无覆盖。Sector-first规则被完全验证：板块重力>个股Alpha。', 'type': 'observation', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': '在-7%到-11%的板块跌幅面前，任何个股的RPS/催化/基本面都是次要的。'}
- {'text': '美伊冲突→油价跳涨→Risk-off→科技暴跌→防御上涨的传导链今日完美演绎。关注冲突是否缓和（停火谈判），这将是科技股反弹的关键信号。', 'type': 'signal', 'tags': ['macro', 'sector'], 'evidence_type': 'supporting', 'mechanism': '地缘冲突推高能源成本+不确定性→资金从高beta成长股撤出→涌入防御资产。冲突缓和则反向。'}
- {'text': '多氟多H1累计+777%~991%但Q2环比-51%~-80%仍跌停——市场只看边际变化。催化剂的方向和新鲜度>总量。H1高增已被priced in，Q2恶化才是新信息。', 'type': 'heuristic', 'tags': ['catalyst', 'entry-filter'], 'evidence_type': 'supporting', 'mechanism': "市场定价边际变化。业绩预告的'总量'已被提前消化，环比恶化才是新信息。"}
