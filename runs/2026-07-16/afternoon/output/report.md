# 每日研究报告 2026-07-16

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3882.41 | -1.85% |
| 深证成指 | 14488.65 | -1.97% |
| 创业板指 | 3692.46 | -2.95% |
| 科创50 | 1846.88 | -4.02% |

涨跌比: 2499涨 / 2861跌 / 5525总

**热门板块**: 影视院线(+5.23%), 专业连锁Ⅱ(+4.95%), 医疗美容(+3.89%), 广告营销(+3.08%), 养殖业(+2.54%)

**冷门板块**: 玻璃玻纤(-7.83%), 电子化学品Ⅱ(-7.05%), 半导体(-5.67%), 其他电子Ⅱ(-4.88%), 非金属材料Ⅱ(-4.86%)

🔴 PANIC DAY: 三大指数全绿(上证-1.85%, 深证-1.97%, 创业板-2.95%), 科创50暴跌-4.02%。Breadth 0.87:1偏熊, 41跌停vs 48涨停。长鑫科技IPO申购日(¥579B)抽血半导体板块(-5.67%)，中报预告截止日触发'题材→业绩'暴力切换。资金从科技(AI/半导体)涌入消费防御(影视+5.23%/医美+3.89%/养殖+2.54%)。IV极端(avg rank 93.6%, 科创50 IV at all-time high 67.3%)。全现金持仓，不开任何新仓，等待breadth恢复至1.5:1以上。

## 策略池扫描

扫描 **61** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **博杰股份** (002975) (RPS 93.06%) — 最强催化剂(中报预增642-816%，AI服务器测试方案)，RPS120=93.06，MA距离干净(dist_ma5=0.5%, dist_ma10=-4.6%, dist_ma20=-7.9%)。市场regime panic hard block — 正常交易日应为STRONG BUY 8%。7/15曾跌停，等企稳。
2. **荣昌生物** (688331) (RPS 86.52%) — RPS120=86.52(sweet spot)，MA距离良好(dist_ma5=-4.7%, dist_ma10=0.0%)，创新药龙头+基药目录催化，医疗美容hot sector联动。市场regime panic hard block — 正常应为MODERATE BUY。
3. **华天科技** (002185) (RPS 91.77%) — 三重拒绝: (1) 半导体板块bottom 3(-5.67%), (2) 市场regime panic, (3) 今日跌停开盘。中报预增231-275%但4.6亿非经常性损益稀释质量。dist_ma5=-11.9%，深跌中。
4. **凯莱英** (002821) (RPS 89.16%) — dist_ma20_pct=18.1% → Rule 2b hard violation (>12%)。即使市场正常也应跳过。RPS120=89.16在sweet spot但追高溢价太高。
5. **京仪装备** (688652) (RPS 94.56%) — 双重拒绝: 半导体板块bottom 3 + dist_ma20_pct=19.5% → Rule 2b violation。今日创历史新高后回落，高位风险极大。
6. **伟测科技** (688372) (RPS 91.43%) — 半导体板块bottom 3(-5.67%)，市场regime panic。RPS120=91.43，MA距离可接受(dist_ma5=0.0%, dist_ma10=2.4%, dist_ma20=9.4%)，但cold sector + panic = no go。
7. **骄成超声** (688392) (RPS 92.36%) — dist_ma20_pct=12.9% → Rule 2b violation (>12%)。RPS120=92.36在extended zone但无超强catalyst覆盖。市场regime panic。
8. **恒逸石化** (000703) (RPS 94.52%) — RPS20=72.99% < 75% → Rule 2 fail (momentum insufficient)。石化板块不在hot sectors。市场regime panic。dist_ma5=5.3%接近chase zone。
9. **上海新阳** (300236) (RPS 93.85%) — 电子化学品Ⅱ板块bottom 2(-7.05%)，sector gravity压倒一切。RPS120=93.85，MA距离尚可，但板块崩盘级下跌中不接飞刀。
10. **四方股份** (601126) (RPS 94.46%) — dist_ma20=-22.8%，深跌远离所有均线，falling knife。电网设备板块当日有拉升但个股未跟。市场regime panic。

## 今日研究结论

- 新开仓: 0只
- 平仓: 0只
- 跳过: 10只

### 新教训
- {'text': '长鑫科技IPO申购日(¥579B)对半导体板块产生系统性抽血效应：申购日当天半导体-5.67%，科创50 -4.02%。未来遇到板块龙头超大IPO申购日，应提前2-3天减仓该板块所有持仓。', 'type': 'heuristic', 'tags': ['sector', 'exit-rule', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019 (bottom-list sectors = hard no-buy)', 'mechanism': 'IPO申购抽走流动性→比价压制压低存量估值→打新资金锁仓→板块流动性真空→多杀多踩踏'}
- {'text': "中报预告强制截止日(7/15)触发市场从'题材预期'向'业绩验证'暴力切换。前期靠AI概念涨但业绩兜不住估值的半导体小票被集中抛售。这是可预测的年度规律，明年7月上旬应减仓纯概念持仓。", 'type': 'signal', 'tags': ['timing', 'exit-rule'], 'evidence_type': 'supporting', 'mechanism': '预告截止日强制披露→市场集中对前期涨幅进行业绩交叉验证→业绩不达预期的概念票集中抛售→羊群效应扩散至整个板块'}
- {'text': "V2 entry_regime硬阻断今日完美运作：0.87:1 breadth, 0 indices green, f10=41 panic — 没有任何理由开新仓。V1会试图找'小仓位'，V2正确选择了全现金。全现金在市场恐慌日是最优仓位。", 'type': 'rule', 'tags': ['entry-filter', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013 (strong breadth alone not enough; without candidate data, cash is correct)', 'mechanism': '硬阻断规则排除了FOMO驱动的小仓位试探，避免在恐慌日接飞刀'}
- {'text': "'Failed bounce' pattern确认：美股半导体7/14反弹(英伟达+4%, SK海力士+27%)，A股半导体7/16不仅未跟涨反而暴跌-5.67%。这种'该涨不涨'比单纯跟跌更熊，说明内资兑现意愿极强，不是外资情绪问题而是内部结构性出逃。", 'type': 'observation', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'mechanism': '一致性预期落空→强化反向交易→加速资金撤离'}
- {'text': '博杰股份(002975)是中报季最强catalyst：AI服务器测试方案+MLCC高附加值设备双轮驱动，Q2环比+27-80%，642-816%同比增长。MA距离全部正常，RPS在extended zone但有catalyst覆盖。等待市场regime恢复正常后优先买入。', 'type': 'signal', 'tags': ['entry-filter'], 'evidence_type': 'supporting', 'mechanism': 'AI服务器capex→测试设备需求→博杰是国内AI测试方案核心供应商→营收利润双爆发'}
