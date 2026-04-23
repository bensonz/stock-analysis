# 每日研究报告 2026-04-23

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4073.71 | -0.79% |
| 深证成指 | 14945.20 | -1.53% |
| 创业板指 | 3684.12 | -1.83% |
| 科创50 | 1419.62 | -2.17% |

涨跌比: 1068涨 / 4333跌 / 5495总

**热门板块**: 油气开采Ⅱ(+3.58%), 油服工程(+3.43%), 医疗美容(+2.30%), 煤炭开采(+1.82%), 黑色家电(+1.52%)

**冷门板块**: 贵金属(-5.46%), 小金属(-5.43%), 非金属材料Ⅱ(-4.55%), 工业金属(-3.59%), 其他电子Ⅱ(-3.36%)

Breadth 0.25:1 bearish/panic, 38涨停/27跌停, and 0/3 major indices green. Top sectors are 油气开采Ⅱ +3.58%, 油服工程 +3.43%, 医疗美容 +2.30%, 煤炭开采 +1.82%, 黑色家电 +1.52%; cold sectors include 贵金属 -5.46%, 小金属 -5.43%, 非金属材料Ⅱ -4.55%, 工业金属 -3.59%, 其他电子Ⅱ -3.36%. Position sector alignment: 0/3 positions in hot sectors. IV is broadly neutral with core avg IV rank about 39.9%; stock proxies are mostly normal, but IV does not override the hard entry block.

## 策略池扫描

扫描 **39** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **新风光** (688663) (RPS 92.65%) — No new positions because entry regime is hard-blocked: breadth 0.25:1 and 0/3 major indices green. Individually acceptable MA distances and 电网设备 catalyst are not enough in panic tape.
2. **国电南自** (600268) (RPS 91.19%) — Already held; no add. Entry regime blocked, volume below MAVOL30, price only 2.68% above stop.
3. **江苏博云** (301003) (RPS 87.81%) — Already held; no add. Entry regime blocked. Although MA distances are healthy and VCP SETUP exists, the broad tape is panic and sector is not today's top-5.
4. **华峰测控** (688200) (RPS 90.95%) — No new positions in panic tape. Semiconductor is not in today's top-5 sectors, though company has strong earnings and 0 listed risks. Keep on research radar only.
5. **英科医疗** (300677) (RPS 93.27%) — Medical beauty is hot but this stock is 医疗耗材, not confirmed same top sector. Entry regime blocked by breadth and indices; no fresh long.
6. **东材科技** (601208) (RPS 91.42%) — Fails non-negotiable MA distance check: dist_ma10_pct 8.6% exceeds 8% threshold. Also no new positions in panic tape.
7. **兴福电子** (688545) (RPS 91.38%) — Fails MA distance check: dist_ma10_pct 9.5% exceeds 8% threshold. No new positions in panic tape.
8. **华懋科技** (603306) (RPS 93.43%) — Fails MA distance check: dist_ma10_pct 14.5% and dist_ma20_pct 21.8% are overextended. No chasing.
9. **莱特光电** (688150) (RPS 93.31%) — Fails MA distance check: dist_ma10_pct 11.5% and dist_ma20_pct 21.7% exceed limits. No chasing.
10. **华锡有色** (600301) (RPS 92.84%) — Sector 小金属 is in bottom-5 cold sectors at -5.43%; sector-first rule makes it skip regardless of individual quality.
11. **永兴材料** (002756) (RPS 97.37%) — Likely lithium/small metals exposure while 小金属 is bottom-5 cold; additionally RPS120 97.37 is above 95 chasing zone.
12. **烽火通信** (600498) (RPS 95.38%) — Already held; no add. RPS120 95.38 is above preferred new-entry ceiling and market entry gate is hard-blocked.

## 今日研究结论

- 新开仓: 0只
- 跳过: 12只

### 新教训
- {'text': 'When breadth collapses below 0.3:1 and all three major indices are red, even sector leaders should be treated as hold-only, not add/buy candidates.', 'type': 'rule', 'tags': ['entry-filter', 'breadth', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Panic breadth raises correlation and gap risk; individual catalysts are less predictive than market-wide de-risking pressure.'}
- {'text': 'Raised stops are doing their job: 江苏博云 and 烽火通信 remain profitable holds despite a weak tape because prior profit protection converts them into asymmetric existing-risk positions.', 'type': 'signal', 'tags': ['exit-rule', 'risk-management', 'let-winners-run'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'Existing winners can be held through volatility if stops have already removed or reduced downside; this is different from initiating new risk.'}
- {'text': 'Stop proximity plus below-average volume is a warning combination for marginal winners or slight losers; 国电南自 should not be averaged down or given thesis exceptions.', 'type': 'heuristic', 'tags': ['exit-rule', 'volume', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h017', 'mechanism': 'Weak volume on a down move near stop indicates demand is not confirming the catalyst; the correct response is readiness to sell, not conviction-based adding.'}
