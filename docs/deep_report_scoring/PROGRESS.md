# Progress

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
