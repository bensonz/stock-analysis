# 每日研究报告 2026-07-28

> 模型: deepseek-v4-pro（DeepSeek V4 Pro primary） · 303029+10597 tokens

## 市场概览

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3820.52 | -0.98% |
| 深证成指 | 13664.80 | -3.42% |
| 创业板指 | 3397.97 | -5.37% |
| 科创50 | 1735.01 | -4.03% |

涨跌比: 2836涨 / 2521跌 / 5529总

**热门板块**: 休闲食品(+3.76%), 教育(+2.81%), 工程咨询服务Ⅱ(+2.73%), 一般零售(+2.30%), 饮料乳品(+2.24%)

**冷门板块**: 通信设备(-9.19%), 元件(-8.11%), 玻璃玻纤(-6.13%), 半导体(-4.88%), 其他电子Ⅱ(-4.86%)

RISK-OFF. 创业板 -5.37%, 科创50 -4.03%, 深证 -3.42%. Breadth 1.125:1 (below 1.5:1 buy gate). Tech massacre: 通信设备 -9.19%, 元件 -8.11%, 半导体 -4.88%. Only consumer defensives green (休闲食品 +3.76%, 饮料乳品 +2.24%). Global semiconductor rout (费城半导体 -22% from June peak) + fund style-control rules driving capitulation. IV elevated across all ETFs (科创50 73%, 创业板 64%). All 5 positions opened yesterday underwater — cutting 4, holding 1. Cash at ~77% after sells. No new positions.

## 策略池扫描

扫描 **46** 只策略池股票
(来源: cheesefortune_intersection)

## 今日平仓

### 1. 冰轮环境 (000811) — SELL — -8.77%

- **出场价**: ¥39.09
- **持有天数**: 1天
- **板块排名**: bottom 60% — 通用设备 not in hot/cold extremes but broad market down

Hard stop triggered: entry ¥42.85, stop ¥40.71, current ¥39.09 (-8.77%). Rule 5: -5% from entry = automatic SELL. 跌停 -9.99% today. No exceptions.

### 2. 广合科技 (001389) — SELL — -4.74%

- **出场价**: ¥152.9
- **持有天数**: 1天
- **板块排名**: bottom 5% — 元件 -8.11%, #2 coldest sector

Dual trigger: (1) Sector '元件' is bottom 5 (-8.11% today) — sector gravity rule mandates sell regardless of thesis. (2) Price ¥152.90 only 0.27% above ¥152.48 stop with -8.72% daily drop. Sector whiplash from hot to cold in one session.

### 3. 昊志机电 (300503) — SELL — -1.72%

- **出场价**: ¥64.54
- **持有天数**: 1天
- **板块排名**: bottom 60% — 通用设备 neutral but heavy selling pressure

Proactive stop-proximity sell per h024. Price ¥64.54 only 0.06% above ¥64.50 stop. 创业板 -5.37% with elevated IV (64%) creates massive gap risk. Yesterday's +2.47% gain fully reversed plus more. Better to exit at ¥64.54 than risk gap-through to ¥62 tomorrow.

### 4. 荣昌生物 (688331) — SELL — -0.84%

- **出场价**: ¥120.42
- **持有天数**: 1天
- **板块排名**: middle 50% — 生物制品 neutral

Stop breached: stop ¥120.56, current ¥120.42 (-0.84%). Today's low ¥119.49 already well below stop. 科创50 IV Rank 73% means gap risk extreme. 泰它西普 thesis still valid but timing wrong — can re-enter when market stabilizes.

## 跳过标的

1. **华丰科技** (688629) (RPS 97.2%) — Rule 2b: dist_ma5 +7.8% > 6%. Sector 军工电子 not in top 30%. 询价转让 ¥126.66 adds supply overhang. No entry regardless of quality.
2. **昭衍新药** (603127) (RPS 90.2%) — Rule 2b: dist_ma20 +13.2% > 12%. H1业绩催化 is genuine but price already extended beyond safe entry. Sector not top 30%. Wait for pullback to MA10/MA20.
3. **药康生物** (688046) (RPS 89.99%) — Rule 2b: dist_ma5 +7.0% > 6% AND dist_ma20 +15.5% > 12%. Multiple extension triggers. Good catalyst (H1 +47-61%) but chasing into overextended tape.
4. **恒逸石化** (000703) (RPS 96.03%) — Rule 2b: dist_ma10 +8.7% > 8%. Sector 炼化及贸易 not in top 30%. 业绩爆炸 (+2326%) but price already ran. Margin deleveraging.
5. **芯碁微装** (688630) (RPS 99.32%) — dist_ma5 +6.0% at Rule 2b threshold. Sector 专用设备 not in top 30%. Market buy gate failed. Would need pullback to MA5 before entry.
6. **星宸科技** (301536) (RPS 95.81%) — Rule 2b: dist_ma5 +22.0%, dist_ma10 +20.4%, dist_ma20 +17.7% — extreme overextension on all timeframes. Sector 半导体 bottom 4. No current price needed to reject.

## 今日研究结论

- 新开仓: 0只
- 平仓: 4只
- 跳过: 6只

### 新教训
- {'text': 'Yesterday opened 5 positions into a tape where breadth was already deteriorating and tech selloff was accelerating globally. The V2 buy gate correctly blocks new positions today (breadth 1.125:1, 0/4 indices green), but yesterday should have been more cautious. Lesson: when all major IV proxies are >60% and the global semi rout is ongoing, even a passing buy gate should be treated with reduced sizing.', 'type': 'rule', 'tags': ['entry-filter', 'position-sizing', 'timing'], 'evidence_type': 'contradicting', 'related_hypothesis': 'h017', 'mechanism': 'Elevated IV (>60% across all ETFs) signals market stress. Opening 5 positions when IV is high and global sector is in freefall amplifies gap risk. The buy gate should incorporate IV as a sizing throttle even when breadth technically passes.'}
- {'text': "Sector gravity validated in real-time: 元件 was a hot sector when 广合科技 was opened yesterday. Today it's bottom 2 at -8.11%. This whiplash — from leader to laggard in one session — is the exact scenario Rule 1 (sector-first) is designed to protect against. When a position's sector drops into the cold zone, sell immediately regardless of thesis.", 'type': 'signal', 'tags': ['sector', 'exit-rule'], 'evidence_type': 'supporting', 'related_hypothesis': 'h019', 'mechanism': "In a risk-off rotation, yesterday's momentum leaders become today's funding sources for defensive rotation. Sectors that led on the way up lead on the way down, magnifying individual stock losses."}
- {'text': 'h024 (proactive stop-proximity selling) is the single most valuable defense rule. 昊志机电 at 0.06% cushion and 广合科技 at 0.27% cushion in a -5.37% 创业板 day would almost certainly gap through stops tomorrow. Selling now at known prices avoids the 扬杰科技 scenario (-8.37% gap-through).', 'type': 'heuristic', 'tags': ['exit-rule', 'timing'], 'evidence_type': 'supporting', 'related_hypothesis': 'h024', 'mechanism': 'When a stock is within 1% of its stop and the market is down >3%, the probability of a gap-through overnight exceeds 50%. The expected value of proactive selling exceeds waiting for the exact stop trigger.'}
- {'text': "凯莱英's relative strength (-2.58% vs 创业板 -5.37%) is a valid HOLD signal even in a bad tape. The stock is showing genuine resilience at MA20 support (dist_ma20 +0.1%). In momentum frameworks, a stock that falls less than the market during a selloff is exhibiting relative strength and deserves patience.", 'type': 'observation', 'tags': ['position-sizing', 'exit-rule'], 'evidence_type': 'supporting', 'mechanism': 'During broad selloffs, relative performance vs index is a cleaner signal than absolute PnL. Stocks holding MA20 support while the index breaks down are showing institutional support.'}
