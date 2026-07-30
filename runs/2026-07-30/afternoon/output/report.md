# 每日研究报告 2026-07-30

> 模型: deepseek-v4-pro（DeepSeek V4 Pro primary） · 146968+7232 tokens

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3804.69 | -0.62% |
| 深证成指 | 13285.80 | -2.73% |
| 创业板指 | 3244.62 | -3.97% |
| 科创50 | 1588.41 | -5.38% |

涨跌比: 1768涨 / 3635跌 / 5528总

**热门板块**: 商用车(+4.41%), 白酒Ⅱ(+3.51%), 农商行Ⅱ(+3.26%), 医疗美容(+3.06%), 厨卫电器(+3.04%)

**冷门板块**: 通信设备(-8.52%), 元件(-8.02%), 电子化学品Ⅱ(-6.51%), 半导体(-6.32%), 非金属材料Ⅱ(-5.81%)

PANIC TAPE. All 3 major indices red (创业板指 -3.97%, 深证成指 -2.73%, 科创50 -5.38%). Breadth 0.49:1 with 83跌停 vs 56涨停. Tech sectors in freefall: 通信设备 -8.52%, 元件 -8.02%, 半导体 -6.32%. Defensive rotation into 商用车 +4.41%, 白酒 +3.51%. IV spike to 91% avg rank across core ETFs — extreme fear. Entry regime HARD BLOCK. Cash is king today.

## 策略池扫描

扫描 **77** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **华峰测控** (688200) (RPS 99.48%) — Sector 半导体 in bottom 5 (-6.32%). RPS120=99.48% and good MA proximity (dist_ma5=-1.4%) don't override sector gravity during liquidation.
2. **中科飞测** (688361) (RPS 99.01%) — Sector 半导体 in bottom 5 (-6.32%). Perfect MA setup (dist_ma5=-0.4%, dist_ma20=-2.2%) but sector-first rule blocks entry.
3. **国瓷材料** (300285) (RPS 98.43%) — Sector 电子化学品Ⅱ in bottom 5 (-6.51%). Good MA proximity but dead sector.
4. **三环集团** (300408) (RPS 98.09%) — Sector 元件 in bottom 5 (-8.02%). Would be a strong candidate in a normal tape.
5. **西部矿业** (601168) (RPS 93.67%) — dist_ma20=13.3% exceeds Rule 2b chase limit (12%). Plus market in panic regime.
6. **药明康德** (603259) (RPS 90.81%) — VCP SETUP with good MA proximity (dist_ma5=0.9%, dist_ma10=1.4%), but sector 医疗服务 not in hot sectors AND market panic regime blocks all new entries. Track for when regime clears.

## 今日研究结论

- 新开仓: 0只
- 平仓: 0只
- 跳过: 6只

### 新教训
- {'text': 'Panic regime correctly blocks entries when 83 stocks hit limit-down and 0/3 major indices are green. Tech sector liquidation validates the sector-first rule: even RPS120=99%+ names in semiconductor/components are getting crushed by sector gravity during deleveraging.', 'type': 'observation', 'tags': ['entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h077', 'mechanism': 'Sector gravity overwhelms individual stock momentum during deleveraging events.'}
- {'text': "V2's hard block prevented FOMO entries into tech. Under V1, 华峰测控 (RPS120=99.48%), 中科飞测 (RPS120=99.01%), and 国瓷材料 (RPS120=98.43%) would have been 'value' entries despite being in sectors down 6-8% today.", 'type': 'rule', 'tags': ['entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h077', 'mechanism': 'Entry regime checks catch macro liquidation that individual stock analysis misses.'}
- {'text': "恒逸石化 (+2.88%) survives precisely because it's outside the tech liquidation. 石油石化 benefits from rotation into resources. Holding neutral-sector positions during panic preserves capital.", 'type': 'observation', 'tags': ['position-sizing', 'sector'], 'evidence_type': 'supporting', 'mechanism': 'During sector rotation, defensive/neutral holdings protect capital while tech leverage unwinds.'}
