# 每日研究报告 2026-05-26

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4117.85 | -0.84% |
| 深证成指 | 15718.98 | -0.87% |
| 创业板指 | 4000.50 | -0.51% |
| 科创50 | 1841.35 | -2.88% |

涨跌比: 942涨 / 4506跌 / 5508总

**热门板块**: 贵金属(+2.26%), 工业金属(+1.79%), 电机Ⅱ(+1.38%), 玻璃玻纤(+1.11%), 饲料(+1.11%)

**冷门板块**: 航天装备Ⅱ(-4.90%), 其他电子Ⅱ(-4.47%), 电视广播Ⅱ(-4.45%), 综合Ⅱ(-4.19%), 军工电子Ⅱ(-3.75%)

Breadth 0.21:1 bearish/panic, 44涨停/29跌停, and 0/3 of 上证指数/深证成指/创业板指 are green, so the buy gate is decisively closed. Hot sectors (top 5): 贵金属(+2.26%), 工业金属(+1.79%), 电机Ⅱ(+1.38%), 玻璃玻纤(+1.11%), 饲料(+1.11%). Cold sectors (bottom 5): 航天装备Ⅱ(-4.90%), 其他电子Ⅱ(-4.47%), 电视广播Ⅱ(-4.45%), 综合Ⅱ(-4.19%), 军工电子Ⅱ(-3.75%). Position sector alignment: 1/1 positions in hot sectors. IV context is mixed: main-board proxies are complacent/low IV while 创业板IV偏高, but IV is secondary today because panic breadth already blocks all new longs.

## 策略池扫描

扫描 **56** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **腾景科技** (688195) (RPS 98.22%) — No new positions allowed: entry regime is panic with breadth 942/4506, 0/3 major indices green. Even though MA distances are acceptable and RPS is strong, market gate blocks entries.
2. **山东赫达** (002810) (RPS 94.9%) — No new positions allowed in current tape; additionally only VCP SETUP and not PREMIUM/QUALITY. Technicals are acceptable, but regime block overrides.
3. **德科立** (688205) (RPS 94.86%) — Sector tape is under pressure and market regime blocks entries. Also has upcoming 2026-05-27解禁 and RPS 94.86 is in extended zone without a clean market backdrop.
4. **华锡有色** (600301) (RPS 91.21%) — Already held; no add because weak market default is no new exposure despite strong sector and acceptable MA structure.
5. **睿创微纳** (688002) (RPS 89.59%) — Sector (军工电子Ⅱ) is in today's bottom 5 / cold bucket, so WATCH-at-best under Rule 1 and never a BUY.
6. **粤桂股份** (000833) (RPS 94.98%) — Sector (综合Ⅱ) is in today's bottom 5 / cold bucket. Sector gravity overrides stock-level catalyst and fundamentals.
7. **江丰电子** (300666) (RPS 93.84%) — Fails anti-chase MA rule: dist_ma10_pct 8.0 is at limit but dist_ma20_pct 25.5 exceeds 12%. No entry.
8. **伟测科技** (688372) (RPS 93.5%) — Fails anti-chase MA rule: dist_ma20_pct 13.9 exceeds 12%, so even a strong semi name is not buyable here.
9. **欧陆通** (300870) (RPS 92.91%) — Fails anti-chase MA rule: dist_ma20_pct 31.2 exceeds 12%. Also current market regime blocks new longs.
10. **芯碁微装** (688630) (RPS 92.93%) — Fails anti-chase MA rule: dist_ma10_pct 11.4 and dist_ma20_pct 31.5 both exceed limits.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': '当日最强板块也无法覆盖系统性弱势，breadth仅0.21:1且三大指数全绿时，最优动作是冻结新开仓而不是在强股里硬挑例外。', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': '极弱广度说明赚钱效应高度收缩，个股胜率会被系统性抛压吞噬，先判断市场再判断个股能显著减少逆势开仓。'}
- {'text': 'MA距离规则今天继续有效：大量高RPS候选股并非不能涨，而是已经远离MA10/MA20，买点质量差于趋势质量。', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': '动量股最容易在情绪高点出现均线乖离过大，后续更依赖接力而非支撑，回撤风险明显上升。'}
- {'text': '资源方向在大盘恐慌中承担避险/防御角色，现有仓位若恰好处于热板块，应优先持有而不是因指数转弱机械减仓。', 'type': 'observation', 'tags': ['sector', 'exit-rule', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h028', 'mechanism': '当资金从高波动成长撤出时，会回流到有现货逻辑或商品映射的资源股，板块相对强度能抵消部分指数压力。'}
