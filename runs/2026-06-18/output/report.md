# 每日研究报告 2026-06-18

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 4090.48 | -0.43% |
| 深证成指 | 16030.70 | +0.94% |
| 创业板指 | 4252.39 | +2.05% |
| 科创50 | 1911.51 | +3.84% |

涨跌比: 2023涨 / 3395跌 / 5509总

**热门板块**: 非金属材料Ⅱ(+5.31%), 通信设备(+4.18%), 金属新材料(+4.13%), 半导体(+3.80%), 小金属(+3.69%)

**冷门板块**: 保险Ⅱ(-6.42%), 焦炭Ⅱ(-3.80%), 非白酒(-3.56%), 贵金属(-3.42%), 文娱用品(-3.23%)

Bifurcated tape: 科创50 +3.84% / 创业板 +2.05% vs 上证 -0.43%. Breadth 0.60:1 bearish (2023 up / 3395 down), 103涨停/43跌停. Tech (半导体/通信设备/非金属材料) leads driven by MLCC/CCL涨价 + SEMI设备创纪录 + NOR Flash合约价翻倍. Traditional sectors (保险 -6.42%/贵金属 -3.42%/焦炭 -3.80%) in liquidation. 3400+ stocks falling. Entry regime HARD BLOCK: no new positions. 5 existing positions all profitable (+8% to +31%), 4/5 in tech-adjacent sectors, 1/5 in top-5 hot sector. All stops at breakeven or better. IV data unavailable — normal sizing on holdings.

## 策略池扫描

扫描 **56** 只策略池股票
(来源: cheesefortune_intersection)

## 跳过标的

1. **华峰测控** (688200) (RPS 94.02%) — ENTRY REGIME HARD BLOCK. Even if regime allowed: dist_ma5=14.1% >6% (Rule 2b chase violation). Stock gapped above MA5 — extreme short-term overextension despite strong fundamentals (SEMI设备出货创纪录 catalyst, 半导体 sector #4, 0 risk factors).
2. **思瑞浦** (688536) (RPS 93.56%) — ENTRY REGIME HARD BLOCK. Even if regime allowed: dist_ma10=8.9% >8% (Rule 2b). NP +577%, 12 analysts, 半导体 sector #4 — excellent fundamentals but overextended from MA10 support. Wait for pullback to MA10 (~306).
3. **华锡有色** (600301) (RPS 94.6%) — ENTRY REGIME HARD BLOCK. Even if regime allowed: 沪锡主力合约暴跌6%+ today (per events data '沪锡主力合约日内暴跌逾6%、价格跌破40万元/吨') — direct negative catalyst for tin-related company. Sector (小金属 #5) is hot but company-specific headwind conflicts. MA distances healthy (2.2/5.2/9.8) but catalyst conflict kills entry.
4. **融捷股份** (002192) (RPS 94.41%) — ENTRY REGIME HARD BLOCK. Even if regime allowed: sector (能源金属/锂) not in today's top 5 — fails Rule 1 sector alignment. RPS120=94.41 in extended zone without sector exception coverage. 碳酸锂涨价 catalyst positive but sector gravity missing.
5. **华灿光电** (300323) (RPS 93.55%) — ENTRY REGIME HARD BLOCK. Even if regime allowed: sector (光学光电子) not in top 5 today. MA distances are exceptionally tight (2.7/0.6/1.2%) — textbook VCP-like consolidation near MAs. PE negative (loss-making, -94x). Would be interesting if sector flips hot but not today.

## 今日研究结论

- 新开仓: 0只
- 跳过: 5只

### 新教训
- {'text': "Breadth panic (0.60:1, f10=43) with tech indices soaring (科创50 +3.84%) creates a 'bear market in disguise.' 3400+ stocks falling while a few dozen semiconductor names rip. The entry regime hard_block correctly prevents opening positions into a tape where mean-reversion risk in crowded tech trades is elevated. Cash is the correct position when only one sector is working.", 'type': 'heuristic', 'tags': ['entry-filter', 'sector'], 'evidence_type': 'supporting', 'related_hypothesis': 'h013', 'mechanism': "Extreme sector bifurcation creates fragility: if tech profit-taking triggers, there is no bid from traditional sectors to absorb selling. The breadth data reveals the market's true internal condition that headline indices (driven by tech heavyweights) conceal."}
- {'text': "Today's PnL dispersion confirms the bifurcation: 兴森科技 +8.91% (purest PCB/IC substrate play, riding #1 market theme directly) vs. 新宙邦/上海新阳/路维光电/恒铭达 all negative. Adjacent-sector diversification into tech-adjacent names (电子化学品, 消费电子, 电池) provided no protection — only the purest theme exposure worked. In future strong-regime entries, concentrate harder into leading themes rather than diversifying into adjacencies.", 'type': 'observation', 'tags': ['position-sizing', 'sector'], 'evidence_type': 'supporting', 'mechanism': 'In bifurcated markets, capital flows are binary: into the top 1-2 themes or out. Adjacent sectors get neither the full upside of leaders nor the safety of cash. Diversification is dilution.'}
- {'text': '兴森科技 +30.93% in 3 days demonstrates Rule 5 trailing stops: raising from breakeven (39.76) to +10% (43.74) at the +20% trigger, now trailing to +20% (47.71) at +30%. Exceptional winners should not be allowed to turn into breakeven trades. The trailing stop converts a windfall into a guaranteed +20% return while preserving further upside.', 'type': 'rule', 'tags': ['exit-rule'], 'evidence_type': 'supporting', 'related_hypothesis': 'h023', 'mechanism': 'Mechanical trailing stops remove emotional decision-making from winner management. The +30% PnL is real; the trailing stop ensures at minimum +20% is banked regardless of what happens tomorrow.'}
