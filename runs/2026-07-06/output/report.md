# 每日研究报告 2026-07-06

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4046.70 | +0.08% |
| 深证成指 | 15541.62 | -0.36% |
| 创业板指 | 3999.28 | -0.51% |
| 科创50 | 2014.38 | +1.96% |

涨跌比: 1838涨 / 3577跌 / 5517总

**热门板块**: 养殖业(+3.03%), 航海装备Ⅱ(+2.53%), 摩托车及其他(+2.40%), 炼化及贸易(+2.40%), 其他电源设备Ⅱ(+2.28%)

**冷门板块**: 玻璃玻纤(-7.94%), 林业Ⅱ(-5.15%), 光学光电子(-3.65%), 金属新材料(-3.59%), 小金属(-3.43%)

Weak/risk-off tape: breadth 0.51:1 (1838↑/3577↓), only 上证指数 barely green (+0.08%), 深证成指 -0.36%, 创业板指 -0.51%. 科创50 outlier +1.96% on 韬定律V2 catalyst. f10=28 near panic threshold, limit-ups 65/limit-downs 28. IV data unavailable — blind spot. Defensive rotation (养殖业 +3.03%) vs cyclicals selling (小金属 -3.43%, 光学光电子 -3.65%). All new positions blocked; focus on selling losers. Cash 93.15% → will rise to ~98% after鹏辉+金钼 exits.

## 策略池扫描

扫描 **66** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **思瑞浦** (688536) (RPS 93.67%) — Buy gate fail (breadth 0.51:1, only 1/3 indices green). Would be #1 buy otherwise: 韬定律V2半导体催化, Q净利+577%, dist_ma5 -2.8% perfect MA pullback, 0 major risk factors. Top candidate to buy when market regime improves.
2. **新宙邦** (300037) (RPS 90.9%) — Buy gate fail. VCP SETUP (ratio 0.87), score_company 9.3 (highest in pool), 固态电解质政策催化, dist_ma5 -4.8% near MA10 support. 12机构覆盖, very high quality.
3. **扬杰科技** (300373) (RPS 92.0%) — Buy gate fail. 全系列涨价10-15% fresh catalyst (July 1生效), but dist_ma5 -6.6% near chase threshold. 0 risk factors. Watch for pullback to MA5 at ~¥142.
4. **奥来德** (688378) (RPS 93.18%) — Sector 光学光电子 in bottom 5 (-3.65%) — hard no per Rule 1. 中报预告+492-604% impressive but sector gravity wins.
5. **水晶光电** (002273) (RPS 86.44%) — Sector 光学光电子 in bottom 5 — hard no. 行业龙头 but sector drag is too strong. Also 大股东质押77% risk.
6. **隆达股份** (688231) (RPS 92.51%) — Sector 金属新材料 in bottom 5 + dist_ma5 +10.2% chasing violation. Double disqualifier.
7. **多氟多** (002407) (RPS 91.72%) — 7月3日跌停(-10%), 龙虎榜机构净卖出2.85亿, 深股通卖出9.15亿. Distribution in progress, stay away.

## 今日研究结论

- 新开仓: 0只
- 跳过: 7只

### 新教训
- {'text': 'Buy gate saved us from bad entries: breadth 0.51:1 + only 1/3 indices green correctly blocked all new positions. Without this gate, we would have bought 思瑞浦/新宙邦 into a weakening tape and likely repeated the鹏辉能源/金钼股份 pattern.', 'type': 'rule', 'tags': ['entry-filter', 'position-sizing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': 'The buy gate prevents opening new risk during deteriorating breadth, which is when mean-reversion risk is highest and new positions are most likely to fail in their first 3-5 days.'}
- {'text': '-3% in first 3 days rule caught two bad entries (鹏辉能源 -4.14%, 金钼股份 -6.27%). Both were opened July 3 — the day after July 2 crash (创业板-5.71%). Buying dips 1 day post-crash without stabilization = bad timing. Wait for breadth to normalize before new entries.', 'type': 'signal', 'tags': ['exit-rule', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'Post-crash day-1 bounces are often sucker rallies. The -3% rule acts as a fast-fail mechanism that limits damage from ill-timed entries. The speed of loss (3 days to -4%/-6%) confirms bad entry timing, not bad thesis.'}
- {'text': "Sector gravity confirmed: 金钼股份's sector (小金属) was in bottom 5 (-3.43%), and the stock fell -6.27% in 3 days. Sector weakness crushed individual stock thesis (钼价上涨, 矿产资源法). Hot sector mediocre stock > cold sector great stock.", 'type': 'heuristic', 'tags': ['sector', 'entry-filter'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': 'In weak markets, sector flows dominate individual fundamentals. When a sector hits bottom 5, institutional rotation out of the entire sector creates selling pressure that individual catalysts cannot overcome.'}
- {'text': '韬定律 V2 is driving the only green index (科创50 +1.96%) amid broad weakness. This is the dominant asymmetric catalyst right now. When the buy gate reopens, semiconductor stocks (especially 模拟芯片设计/先进封装/EDA) should be priority targets. 思瑞浦 is the cleanest setup.', 'type': 'observation', 'tags': ['sector', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': None, 'mechanism': "Catalyst-driven sectors can decouple from broad market weakness. 韬定律 represents a structural re-rating of China's semiconductor ecosystem. The V2 release with engineering details converts theoretical promise into investable roadmap, attracting institutional capital even in weak tape."}
