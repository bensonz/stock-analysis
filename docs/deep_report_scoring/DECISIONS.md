# Decisions

## D1 — placeholder token, stamped after verify (2026-11-03)
The writer emits `{{评级}}` in the H1 and the 结论 line; code replaces it once
the verify pipeline has finished. Options: let the model copy a code-computed
rating (impossible: the scorecard comes in the same reply), or stamp before
verify. Stamping after verify keeps `W=7.2` away from the number verifier, and
the model never writes a rating at all. A rating the model writes anyway is
replaced in place (warned on stderr): a `方向 ｜ 评级 N/5` span becomes the full
computed `方向 ｜ 评级 N/5（W=…）`, so the model's direction never survives beside
the computed one; a bare `评级 N/5` becomes the computed band; a bold
`**结论：方向（…）**` with no rating gets the computed form in place of its
direction. A verdict line is inserted under the title only when no `结论：` line
(the closing `最终结论` does not count) carries the rating. The title is the H1
with `{{评级}}`, else the one naming 深度研究报告, else the first that is not a
stray `# 报告` — that stray heading stays untouched so md_to_pdf still drops it.

## D2 — the draft's scorecard stands over revise re-emissions
Revise and cleanup passes get the full writer spec, so they may emit a new
scorecard block. Those blocks are stripped and ignored. Revisions exist to fix
numbers, not to re-judge the stock; letting them re-score would bring back the
instability the equation removes. A writer *retry* (degenerate or truncated
draft) is still a draft, so its valid scorecard replaces a missing or invalid one.
The same holds for a re-emitted `predictions` block: it is stripped after verify
and ignored, so the draft's bets stand and the block is never published (before
this, a revise re-emission leaked into 14 published reports).

## D3 — missing/invalid scorecard → visible 无法计算, no retry for the block
The report is published with `评级 无法计算（scorecard <reason>）` and the
jsonl row carries the error. Option rejected: re-ask the writer only for the
block — that costs a long-context call, and the re-asked scores would be made
after the fact. Absence stays visible (null-visibility rule); the error rate
is measurable from `reports/scorecards.jsonl`.

## D4 — direction rule kept as proposed (flagged to owner)
`F ≥ 6 and M ≥ 5 → 看多; F ≤ 4 → 看空; else 中性`, independent of the band. So
看空 or 中性 can pair with band 4 (e.g. F=4, V=M=R=10 → W=7.9, 4/5, 看空).
Kept exactly as approved; a test pins the current behaviour. If the validation
runs show such pairs in real reports, the owner decides whether direction
should cap the band.
