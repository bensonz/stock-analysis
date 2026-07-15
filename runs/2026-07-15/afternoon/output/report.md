# 每日研究报告 2026-07-15

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3955.58 | -0.29% |
| 深证成指 | 14779.40 | -0.97% |
| 创业板指 | 3804.70 | -1.21% |
| 科创50 | 1924.27 | -4.25% |

涨跌比: 3351涨 / 2098跌 / 5525总

**热门板块**: 医疗美容(+8.18%), 影视院线(+5.24%), 医疗服务(+4.83%), 游戏Ⅱ(+4.63%), 化学制药(+4.15%)

**冷门板块**: 航天装备Ⅱ(-7.36%), 半导体(-5.58%), 非金属材料Ⅱ(-5.50%), 光学光电子(-5.21%), 其他电子Ⅱ(-4.90%)

Breadth 1.60:1 weak-positive (3,351 up / 2,098 down), 74涨停 / 39跌停. All 3 major indices red (上证 -0.29%, 深证 -0.97%, 创业板 -1.21%), 科创50 crashed -4.25%. IV extreme: 科创50 IV Rank=1.00, overall 0.788 avg — 极度恐慌. Major style rotation in progress: semiconductor/tech (bottom sectors) bleeding out, medical/pharma complex (top sectors) surging across all sub-sectors. 0 active positions, ¥956K cash. Entry regime hard-blocks new positions — regime is 'panic' with 0/3 indices green and 39跌停 above threshold. Stay cash, monitor medical rotation for entry when regime clears.

## 策略池扫描

扫描 **62** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **凯莱英** (002821) (RPS 89.16%) — Hot sector (#3 医疗服务 +4.83%), RPS120=89.16% sweet spot, 0 risks, 9 highlights, equity incentive catalyst. BUT dist_ma20_pct=18.1% violates Rule 2b (max 12%). Extreme extension above MA20. Wait for pullback to ~¥155 zone. Also: entry regime hard blocks new positions regardless.
2. **荣昌生物** (688331) (RPS 86.52%) — Medical/biotech sector benefiting from rotation. RPS120=86.52% sweet spot. MA distances acceptable (dist_ma5=-4.7%, dist_ma10=0.0%, dist_ma20=9.9%). Technical setup constructive. However: entry regime hard blocks all new positions — 0/3 major indices green, 39跌停.
3. **博杰股份** (002975) (RPS 93.06%) — H1 earnings +642-816% catalyst, MA distances constructive (dist_ma5=0.5%, near support). RPS120=93.06% in extended zone — needs sector top 10% exception. Sector (自动化设备) not in top 30%. Also blocked by entry regime.
4. **京仪装备** (688652) (RPS 94.56%) — 半导体 sector in bottom 5 (-5.58%). Automatic no-buy per Rule 1. dist_ma20_pct=19.5% also violates Rule 2b. 0 risks, 6 highlights — would be interesting in a tech uptrend.
5. **华天科技** (002185) (RPS 91.77%) — 半导体 sector cold (-5.58%). dist_ma10_pct=9.3% exceeds 8% Rule 2b limit. Stock spiked on H1 earnings (+6.42% on 07/14) but sector gravity and MA extension make it un-buyable.
6. **茂莱光学** (688502) (RPS 89.84%) — 光学光电子 sector in bottom 5 (-5.21%). dist_ma20_pct=14.4% violates Rule 2b. PE >1500 — sanity check red flag. Automatic skip.
7. **奥来德** (688378) (RPS 93.42%) — 光学光电子 sector cold. Automatic no-buy zone per Rule 1 regardless of individual fundamentals.
8. **思瑞浦** (688536) (RPS 93.46%) — 半导体 sector cold (-5.58%). 8 highlights, strong fundamentals, but sector gravity kills any entry thesis. Wait for semiconductor stabilization.

## 今日研究结论

- 新开仓: 0只
- 平仓: 0只
- 跳过: 8只

### 新教训
- {'text': 'Style rotation can kill a strategy pool overnight: 60%+ of strategy pool is in semiconductor/tech sectors now in the bottom 5. High-RPS pools naturally concentrate in recent winners, creating sector-concentration risk when rotation hits. When hot sectors rotate, the entire candidate pool becomes invalid simultaneously.', 'type': 'observation', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'mechanism': 'RPS filters select stocks with strong recent momentum, which clusters them in recently-hot sectors. When those sectors rotate out (as semiconductor just did), the candidate pool becomes almost entirely un-buyable.'}
- {'text': 'MA-distance kills even perfect hot-sector candidates: 凯莱英 has everything (sector #3, RPS sweet spot 89%, 0 risks, 9 highlights, equity incentive catalyst, 10 analysts) but dist_ma20=18.1% is a hard stop. Rule 2b prevented buying an extended stock that would face mean-reversion headwinds. Validates h027.', 'type': 'signal', 'tags': ['entry-filter', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h027', 'mechanism': 'Even in a hot sector, stocks that have run 18% above their 20-day moving average face strong gravitational pull back to the mean. Entering here would mean buying after most of the move has occurred.'}
- {'text': "Hard block regime correctly prevented forcing entries: V1 would have found a way to 'small buy' — V2's discipline of returning empty new_positions when 0/3 indices green and 39跌停 is the right call. Cash preservation in panic regimes is more important than catching rotation early.", 'type': 'rule', 'tags': ['entry-filter', 'position-sizing'], 'evidence_type': 'supporting', 'mechanism': 'When the buy gate fails, forcing a small position turns a 0% return day into a potential -5% stop-loss day. The expected value of forcing entries in panic regimes is negative.'}
- {'text': 'Medical/pharma rotation is broad and multi-sub-sector, not a one-stock phenomenon. 医疗美容 +8.18%, 医疗服务 +4.83%, 化学制药 +4.15%, 生物制品 and innovation drugs all moving. When regime clears, 凯莱英 (医疗服务) and 荣昌生物 (生物制品) should be priority candidates. Multiple sub-sectors moving together increases durability.', 'type': 'heuristic', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'mechanism': 'Coordinated multi-sub-sector moves suggest genuine institutional rotation rather than retail speculation, giving the trend higher persistence probability.'}
