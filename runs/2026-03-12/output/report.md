# 每日研究报告 2026-03-12

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4129.10 | -0.10% |
| 深证成指 | 14374.87 | -0.63% |
| 创业板指 | 3317.52 | -0.96% |
| 科创50 | 1383.65 | -1.24% |

涨跌比: 1494涨 / 3893跌 / 5482总

**热门板块**: 煤炭开采(+4.35%), 风电设备(+4.30%), 焦炭Ⅱ(+2.95%), 燃气Ⅱ(+2.67%), 养殖业(+2.05%)

**冷门板块**: 工程机械(-3.54%), 航天装备Ⅱ(-3.35%), 林业Ⅱ(-2.95%), 地面兵装Ⅱ(-2.46%), 军工电子Ⅱ(-2.33%)

指数偏弱，上证-0.10%、深成指-0.63%、创业板-0.96%、科创50-1.24%。Breadth 0.38:1 bearish，64涨停/7跌停，虽然涨停数量不低，但下跌家数3893远超上涨1494，属于分化偏弱市，且分布主要集中在小幅下跌区间。Hot sectors (top 5): 煤炭开采(+4.35%), 风电设备(+4.30%), 焦炭Ⅱ(+2.95%), 燃气Ⅱ(+2.67%), 养殖业(+2.05%). Cold sectors (bottom 5): 工程机械(-3.54%), 航天装备Ⅱ(-3.35%), 林业Ⅱ(-2.95%), 地面兵装Ⅱ(-2.46%), 军工电子Ⅱ(-2.33%). Position sector alignment: 1/3 positions in hot sectors. IV context: overall avg IV Rank only 4.15%, a complacent market regime, so new position sizing should be cut by 50% and only the strongest sector setups should be bought.

## 策略池扫描

扫描 **23** 只策略池股票
(来源: local_pricedb)

## 今日开仓

### 1. 明阳智能 (601615) — BUY/small

- **入场价**: ¥22.03
- **止损**: ¥20.93
- **目标**: ¥26.5
- **RPS120**: 94.8%
- **板块**: 风电设备 (top 10%)

风电设备是今日最强方向之一，板块催化来自风电拉升与新能源建设预期，明阳智能具备龙头属性、利润高增和机构覆盖，且MA距离合规，不属于追高买点。

## 跳过标的

1. **望变电气** (603191) (RPS 94.26%) — RPS120 94.26 and sector quality is good, but dist_ma20_pct 8.2% is acceptable while sector is not in today's top-5 leadership; with IV Rank extremely low, prefer the stronger sector leader setup first
2. **浙江龙盛** (600352) (RPS 91.15%) — Catalyst is real and fresh from dye price hikes, but sector is not in today's top leadership and current_price 15.41 is below ma5/ma10/ma20, showing momentum pause rather than active strength despite RPS120 91.15
3. **赤峰黄金** (600988) (RPS 91.82%) — RPS120 91.82 and current_price 42.35 is within MA limits, but贵金属/黄金 is not in provided top sector list today; avoid opening outside top-30% sector rule even with strong macro catalyst
4. **海星股份** (603115) (RPS 91.42%) — Fails no-chasing rule: dist_ma10_pct 6.4% is acceptable but dist_ma20_pct 15.2% exceeds the 12% limit, so entry would be chasing
5. **皖维高新** (600063) (RPS 86.08%) — Fails no-chasing rule with dist_ma5_pct 8.9% and dist_ma10_pct 10.4%; even with chemical-fiber strength, extension is too large for a fresh entry
6. **华懋科技** (603306) (RPS 93.31%) — Auto parts sector is not in the provided top sector list, so despite RPS120 93.31 and acceptable MA distances, sector-first rule blocks entry
7. **中原内配** (002448) — No current price data in the main input set for analysis context here, and auto parts is not in the provided top sector list; sector-first rule blocks entry

## 今日研究结论

- 新开仓: 1只
- 跳过: 7只

### 新教训
- {'text': '前3日-3%快速止损比等待硬止损更重要；国机精工和豪迈科技都在开仓3日内明显走弱，说明入场时机错误时应立即撤退。', 'type': 'rule', 'tags': ['exit-rule', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h004', 'mechanism': '强势股若真处于资金主升，开仓后通常很快给正反馈；前3日即明显亏损，往往代表买在错误节奏或错误板块。'}
- {'text': '低IV环境下，新仓应进一步偏向当日最强板块而非仅仅中期趋势板块；今天市场整体下跌时，只有最强的风电/煤炭等方向更有承接。', 'type': 'heuristic', 'tags': ['sector', 'timing', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h001', 'mechanism': 'IV极低意味着市场对波动定价过低，弱势板块中的个股更容易在回撤日失去承接，资金会集中抱团最强主线。'}
- {'text': '染料涨价这类基本面催化如果股价已经回到MA下方，不应仅凭题材新鲜度开仓，必须等价格重新证明强势。', 'type': 'signal', 'tags': ['entry-filter', 'sector', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h003', 'mechanism': '催化决定方向，但短线买点仍由价格结构决定；跌回均线下方说明资金抢筹阶段已暂停。'}
