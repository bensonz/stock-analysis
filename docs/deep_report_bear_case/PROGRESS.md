# Progress

## 2026-10-03
- Diagnosis done (see IMPLEMENTATION_PLAN trigger). User approved A+B+C+D, 600150
  as the foundation test case. Tracking files created; pass criteria fixed pre-run.
- Stage 1 done: DEEP_REPORT.md gets mandatory bear searches (workflow step 3),
  核心观点 must name the top risk, new §3 关键日期 table, §4 风险提示 slot rules
  (≥2 specific, severity order, no bundling, base-rate drawdown as an extra line,
  dated risks use the date as horizon/expires).
- Caught and removed test leakage: the first spec draft quoted the 600150 answer
  (301 port fees, 2026-11-09). Spec examples must stay generic or the 600150
  re-run measures nothing. Same rule applied to DEEP_BEAR.md.
- agents/DEEP_BEAR.md written (5+ searches incl. English for foreign-gov actions;
  linked facts only; dated events as ```events JSON).
- Stage 2 code delegated (deep_report.py + tests + RUNBOOK).
- Stage 2 done (subagent, reviewed): build_bear_prompt / run_bear_pass /
  extract_bear_events / write_bear_brief, build_prompt(bear_brief=), generate(bear=),
  --no-bear. Existing generate tests pinned bear=False, no assertion loosened.
  Full suite 875 passed / 12 skipped. Known gap: brief is written after generate()
  returns, so a writer crash loses it (acceptable for now).
