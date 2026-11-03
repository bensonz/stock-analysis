# Deep-report scoring equation — plan

Design: `PROPOSAL.md` (approved by the owner 2026-11-03). Choices: `DECISIONS.md`.

## Stage 1 — Spec (`agents/DEEP_REPORT.md`)
- [x] Replace the free-form 评级 rubric with the four anchor tables (F/V/M/R, verbatim)
- [x] Require the ```scorecard block, next to the predictions block (both stripped)
- [x] H1, 结论 line use the `{{评级}}` placeholder; closing line has no rating number
- [x] Tell the model the W/band/direction rules so its prose agrees with the code
- [x] Mission paragraph and citation-exempt list updated

## Stage 2 — Code (`scripts/research/deep_report.py`)
- [x] `extract_scorecard_block` (strips every block, parses the last, named errors)
- [x] `compute_rating` (pure; weights and band edges as module constants; half-up rounding)
- [x] `stamp_rating` (H1, other tokens, lost-token insertion, model-written 评级 N/5 replaced, 无法计算 path)
- [x] `generate()`: extract on draft and retry; drop revise re-emissions; stamp after verify
- [x] `main()`: `reports/scorecards.jsonl` row (`log_scorecard`) and a stderr rating line
- [x] Retry/truncation nudges start at the `{{评级}}` title and end with scorecard + predictions

## Stage 3 — Verify and tests
- [x] `deep_verify`: `{{评级}}` is not a claim (test only; no code change needed)
- [x] Tests: band edges, direction rules, extraction errors, stamping, generate end-to-end, jsonl

## Stage 4 — Validation runs (before trusting the rating)
- [ ] 2× same-day reports on 002293 and on 605098. Pass: W spread ≤ 0.5 within a day, same band.
- [ ] Same day, writer=anthropic vs writer=openai (DeepSeek). Pass: same band, W spread ≤ 1.0.
- [ ] Score the 002293 08-25 and 08-31 reports by hand against the anchors. If the band
      still flips, move the band edges, not the anchors.
