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
- [x] 2× same-day reports on 002293 and on 605098. Pass: W spread ≤ 0.5 within a day, same band.
      **2026-11-21: pass.** 002293 W 6.8 / 6.5 (band 3, 3); 605098 W 6.9 / 6.9 (band 3, 3). Writer
      Claude Opus 5.5, verify DeepSeek. Caveat: Tavily was over quota, so 5 of 6 bear passes
      came back empty — this tests scoring stability on thin research, not report quality.
- [x] Same day, writer=anthropic vs writer=openai (DeepSeek). Pass: same band, W spread ≤ 1.0.
      **2026-11-21: 1 pass, 1 fail on band only.** 002293: DeepSeek W 6.6 vs Claude 6.5–6.8, band 3
      both. 605098: DeepSeek W 7.3 (band 4) vs Claude 6.9 (band 3) — spread 0.4, inside the limit,
      but it straddles the 7.0 edge. Moving the edge only moves where this happens; reports
      already print W beside the band. Owner decides. Same Tavily caveat; DeepSeek's 605098
      report has 0 external links.
- [x] Score the 002293 08-25 and 08-31 reports by hand against the anchors. If the band
      still flips, move the band edges, not the anchors. **2026-11-21: no flip.** Both land in
      band 3 (published 3/5 and 4/5). 08-25: F 7.5 / V 4 / M 6 / R 6 → W 6.0. 08-31:
      F 7.5 / V 4 / M 7.5 / R 6 → W 6.4. The only change is RPS20 11→23, which crosses the M
      anchor line (6→8) but moves W by ~0.4. Band edges stay.
