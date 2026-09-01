# Deep-report scoring equation — proposal (not yet implemented)

**Status**: awaiting owner approval
**Date**: 2026-09-01

## The problem, precisely

Same stock, same fundamentals, runs six days apart: 002293 scored 3/5 on
08-25 and 4/5 on 08-31. On a 5-point scale that reads as a 20% swing with no
fundamental change. 605098 moved 3→4 over five weeks — but that one tracked a
real catalyst (the awaited 中报 confirming), so it was *right*.

What the 2026-09-01 experiment established (2× 002293, same day, parallel,
`TEMPERATURE = 1.0`): **both runs returned 4/5 with near-identical theses.**
Same-day agreement at double the original temperature means the instability is
NOT sampling noise. The rating function is *steep near the 3/4 boundary* —
small legitimate input drift (price −2.5%, 估值分位 84→79, RPS20 11→23) tips
a full point. (n=2; treated as strong hint, not proof.)

Two design constraints set by the owner:

1. **No memory between reports.** Consistency must come from the system
   itself, so the same mechanism transfers across models (Fable, DeepSeek,
   Kimi…) — not from anchoring on the previous answer.
2. Temperature stays at 1.0 — the experiment showed it does not destabilize
   the verdict, and lowering it would only mask boundary-steepness anyway.

So the fix is to make the boundary *principled*: the model scores evidence
against written anchors; **code computes the headline**. The model never
writes "评级 N/5" again.

## The equation

Four sub-scores, each 0–10, each anchored (tables below):

| dim | name | weight | what it reads |
|---|---|---|---|
| F | 基本面 | 0.35 | growth quality, margins, cash conversion, balance sheet |
| V | 估值 | 0.25 | absolute multiples AND percentile vs own history |
| M | 动量/技术 | 0.25 | RPS gate, RPS20, MA position, volume/chip structure |
| R | 风险/赔率 | 0.15 | base-rate drawdown odds, thesis-break proximity, events |

```
W = 0.35·F + 0.25·V + 0.25·M + 0.15·R          (0–10, one decimal)

band:  W ≥ 8.5 → 5/5 │ 7.0–8.4 → 4/5 │ 5.5–6.9 → 3/5 │ 4.0–5.4 → 2/5 │ < 4.0 → 1/5

direction: F ≥ 6 and M ≥ 5 → 看多 │ F ≤ 4 → 看空 │ otherwise → 中性
```

**The report headline shows both:** `评级 4/5（W=7.2）`. This directly answers
the "1 point = 20%" complaint — the continuous W is the real signal; the band
is presentation. A week where W moves 6.8 → 7.1 now *reads* as a 0.3 drift
that happened to cross a line, not a 20% re-rating.

## Anchor tables (v1 — these go verbatim into DEEP_REPORT.md)

Anchors are deliberately coarse (0/2/4/6/8/10) and evidence-referenced; the
model interpolates between them and must cite which anchor clause it matched.

**F 基本面**
- 10: 收入与利润双加速≥20%，毛利率扩张，净现比>100%，无资产负债表隐患
- 8: 利润加速但收入个位数（结构性改善），现金流健康或可解释的单期背离
- 6: 稳态增长，无加速也无恶化；或加速但现金流背离未解释
- 4: 增速回落或质量瑕疵（应收/存货/现金流两项以上恶化）
- 2: 收入利润双降，或依赖非经常损益
- 0: 造假嫌疑 / 持续失血

**V 估值**
- 10: 绝对与相对自身历史均便宜（分位 <20%），且盈利在改善
- 8: 绝对合理、分位 <40%
- 6: 绝对合理、分位 40–70% —— "不贵但也不便宜"
- 4: 分位 70–85%，买入回报依赖盈利兑现而非再估值
- 2: 分位 >85% 且盈利增速回落
- 0: 泡沫定价（PE 与增速严重脱节）

**M 动量/技术**
- 10: RPS 三线过闸且 RPS20>60，价稳于 MA10 上，量价健康，筹码集中
- 8: 三线过闸，短线整固（RPS20 20–60），未破位
- 6: 三线过闸但 RPS20<20（短线明显退潮），或贴线拉锯
- 4: 一线跌破闸门，或放量破位后未收复
- 2: 两线以上跌破，趋势反转中
- 0: 全面破位

**R 风险/赔率**（注意：高分 = 风险低）
- 10: 无临近事件，base-rate 回撤频率 <40%，止损/仓位纪律有明确挂靠点
- 8: 常规动量池回撤风险（base-rate 60–70%）但有结构支撑位
- 6: 回撤 base-rate 高 + 单一可跟踪风险点（如现金流待验证）
- 4: 两个以上未出清的风险点，或重大事件在 2 周内
- 2: 论点依赖单一未验证假设
- 0: 已出现证伪证据

## Mechanics (where each piece lives)

1. **`agents/DEEP_REPORT.md`**: replace the free-form rating instruction with
   the anchor tables + a required output block:

   ```scorecard
   {"F": 7.5, "F_anchor": "利润加速但收入个位数……",
    "V": 5.0, "V_anchor": "分位 77%，回报依赖盈利兑现",
    "M": 6.5, "M_anchor": "三线过闸、RPS20=23 短线退潮",
    "R": 6.0, "R_anchor": "回撤 base-rate 65.7% + 现金流待验证"}
   ```

   Each `_anchor` must quote the matched anchor clause AND name the article
   fact that satisfies it. The model does NOT output a 1–5 rating.

2. **`scripts/research/deep_report.py`** (~40 lines): parse the scorecard
   block (same extraction pattern as the existing ```predictions block),
   compute W/band/direction in `compute_rating(scores) -> (W, band, direction)`
   — a pure function — and stamp the title line itself. Missing/malformed
   scorecard → report published with `评级 无法计算（scorecard 缺失）`, never a
   guessed number: absence stays visible, per the null-visibility rule.

3. **Verify pass** (v1 = nothing new): the existing number-verifier already
   covers facts the anchors cite. A dedicated anchor-consistency check
   (does `F_anchor` actually match the F value's anchor row?) is a v2 item.

4. **Calibration log**: append `(date, code, F, V, M, R, W, band, model)` to a
   `reports/scorecards.jsonl`. After ~20 reports this answers "is W drifting
   with the market or with the model?" — measurable, no memory involved.

## Validation plan (before switching the default)

1. Re-run the experiment shape: 2× same-day per stock on 002293 + 605098.
   **Pass**: W spread ≤ 0.5 within a day; bands identical.
2. Cross-model: same day, writer=anthropic vs writer=openai (DeepSeek).
   **Pass**: bands agree; W spread ≤ 1.0. This is the owner's actual
   requirement — the rubric is the thing that transfers, and this measures it.
3. Retrodict the 002293 pair by hand: score 08-25 and 08-31 against the
   anchors. Expected outcome: 08-25 ≈ V=4, M=6 → W≈6.0 (3/5); 08-31 ≈ V=4.5,
   M=6.5 → W≈6.4 (3/5, borderline). If the anchors *still* produce a band
   flip, the bands move, not the anchors — that argument now happens on paper
   with numbers instead of inside a sampled paragraph.

## Cost

Spec edit + ~40 lines + tests (parse, compute_rating boundaries, missing-block
visibility) ≈ half a day. Validation runs ≈ 8 deep reports of API spend.

## Explicitly rejected alternatives

- **Feeding the prior report in** — owner decision: no memory; cross-model
  consistency must not depend on a previous answer to anchor on.
- **Lowering temperature** — tested 2026-09-01: same-day verdicts already
  agree at T=1.0. The instability lives at the band boundary, not in the dice.
- **Ensembling (k runs, majority band)** — treats the symptom at k× cost, and
  the median of a steep function is still steep.
