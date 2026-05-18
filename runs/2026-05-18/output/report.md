# 每日研究报告 2026-05-18

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4126.35 | -0.22% |
| 深证成指 | 15513.13 | -0.31% |
| 创业板指 | 3909.26 | -0.50% |
| 科创50 | 1712.80 | +0.97% |

涨跌比: 1843涨 / 3567跌 / 5502总

**热门板块**: 油服工程(+3.85%), 元件(+2.83%), 电视广播Ⅱ(+2.52%), 电子化学品Ⅱ(+2.43%), 航天装备Ⅱ(+1.94%)

**冷门板块**: 养殖业(-3.77%), 工程机械(-3.46%), 医疗美容(-3.25%), 贵金属(-2.94%), 动物保健Ⅱ(-2.74%)

Breadth 0.52:1 bearish, 84涨停/55跌停, panic-like tape. 上证-0.22%、深成指-0.31%、创业板指-0.50%，0/3 major indices green, so the minimum long-entry gate decisively fails. Hot groups are narrowly concentrated in 油服工程(+3.85%), 元件(+2.83%), 电子化学品Ⅱ(+2.43%) and 航天装备Ⅱ(+1.94%), while 养殖业(-3.77%)、工程机械(-3.46%)、医疗美容(-3.25%) lead downside. IV context is mixed: broad-market IV is neutral, but 科创50/创业板 proxies are elevated, reinforcing selectivity rather than aggression. With no active positions and entry_regime hard_block=true, the correct action is full cash and no new longs.

## 策略池扫描

扫描 **55** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **江丰电子** (300666) (RPS 94.49%) — No entry: market buy gate failed, and stock also violates anti-chase rule with dist_ma10_pct 13.6% and dist_ma20_pct 22.4%.
2. **莱特光电** (688150) (RPS 94.97%) — Sector is hot and RPS is in extended-allowed zone, but market regime blocks new longs and stock is too extended from MA20 (dist_ma20_pct 22.6%).
3. **恩捷股份** (002812) (RPS 93.96%) — No entry despite acceptable MA profile and strong catalyst because entry regime is hard-blocked; also RPS 93.96% sits in extended zone and needs a stronger tape.
4. **华锡有色** (600301) (RPS 92.84%) — No entry: market panic blocks buys; stock also fails anti-chase rule on dist_ma20_pct 13.2%. Current price data exists in input, but setup is not clean enough for a weak tape.
5. **科达制造** (600499) (RPS 90.79%) — Technically one of the cleaner pullback candidates, but new longs are forbidden because breadth is 0.52:1, 0/3 major indices are green, and f10 is 55.
6. **万向钱潮** (000559) (RPS 89.15%) — MA distances are acceptable, but RPS120 89.15% alone is not enough to override a panic regime; no new positions under current breadth.
7. **咸亨国际** (605056) (RPS 93.35%) — Pulled below MA5/MA10 and lacks confirmation; market buy gate failed, so even a potentially constructive reset is a skip today.
8. **睿创微纳** (688002) (RPS 89.66%) — Sector backdrop is decent, but stock fails anti-chase rule with dist_ma20_pct 18.9%; additionally new longs are blocked by market regime.
9. **鼎通科技** (688668) (RPS 92.52%) — Strong communications trend but badly extended from support: dist_ma10_pct 25.0%, dist_ma20_pct 39.8%. Hard skip.
10. **中船特气** (688146) (RPS 85.42%) — Fresh theme catalyst exists, but stock is too extended from MA10/MA20 and current tape is hostile to breakout buys.

## 今日研究结论

- 新开仓: 0只
- 跳过: 10只

### 新教训
- {'text': 'When breadth is below 1:1 and all three major indices are red, even strong sector leaders should remain on skip_list rather than forcing pilot positions.', 'type': 'rule', 'tags': ['timing', 'entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Weak index participation and heavy downside breadth increase failure rates for otherwise valid momentum setups because breakouts lack market sponsorship.'}
- {'text': 'The anti-chase MA filter is eliminating many of the strongest-looking names for good reason today; most hot names are 10-40% above MA10/MA20.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h021', 'mechanism': 'In euphoric pockets inside a weak tape, extended names have poor reward-to-risk because nearest support is too far below entry.'}
- {'text': 'Today’s better-looking candidates are pullback names like 科达制造 and 万向钱潮, but regime risk dominates stock quality.', 'type': 'observation', 'tags': ['timing', 'sector', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'Setup quality matters only after the market clears the long-entry gate; otherwise even cleaner pullbacks have low follow-through probability.'}
