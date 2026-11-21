# Progress

## 2026-11-21 (Stage 4 validation)
- Done: 6 reports in `reports/stage4-2026-11-21/` (git-ignored; rows in
  `reports/scorecards.jsonl`) plus hand scoring of the 08-25/08-31 reports.
  Repeatability passes (spread 0.3 and 0.0). Writer comparison: 002293 same
  band; 605098 splits 3/4 across the 7.0 edge (W 6.9 vs 7.3). Hand scoring: no
  flip (both band 3). Scores do not copy any example values.
- Caveat: Tavily web search was over quota (1001/1000) for all runs. 5 of 6 bear
  passes hit 15 tool rounds and returned nothing. One Claude run died on 3
  relay empty-stream retries and was rerun.
- Side effect: every deep_report run appends to `tracking/ledgers/predictions.jsonl`.
  The 8 rows from these validation runs were reverted, because they were made
  on degraded research. Any rerun must do the same.
- Next: owner decides on the 605098 edge case. Optional: rerun the writer pair
  once Tavily works, to test on full research.
- Blocked: Tavily quota.

## 2026-11-03 (review fixes)
- Done: `stamp_rating` replaces a model-written `方向 ｜ 评级 N/5` in place (no
  second, contradicting 结论 line); it stamps the real title, not a stray
  `# 报告`; a re-emitted `predictions` block is stripped after verify; the spec
  forbids score numbers in prose. D1 and D2 updated.
- Next: Stage 4 validation runs (unchanged).
- Blocked: nothing.

## 2026-11-03
- Done: owner approved the proposal. Stages 1–3 of PLAN.md: spec anchors +
  scorecard block + `{{评级}}` placeholders; `extract_scorecard_block`,
  `compute_rating`, `stamp_rating`, `log_scorecard` in deep_report.py; tests.
- Next: Stage 4 validation runs (≈8 deep reports). Watch one risk: the spec's
  scorecard example uses the proposal's values (7.5/5.0/6.5/6.0, from the
  002293 discussion). If same-day runs cluster on those exact values, the
  example is anchoring the model and the 002293 check measures nothing —
  replace the example values first.
- Blocked: nothing.
