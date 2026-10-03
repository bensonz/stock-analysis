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

## 2026-10-03 — Stage 3: 600150 re-run
- Bear pass: 8 rounds, ~15 searches (incl. English USTR query), 291k+13k tokens.
  Brief item #1 = 301 truce expiry 2026-11-10; also found 北海造船 fire, lock-up
  (already past), RMB, Q3 date. 4 dated events.
- Report: 4/5 again, but 核心观点 now leads with the 11-10 date; §3 关键日期 table
  present; 风险一 fire / 风险二 growth+FX / 风险三 301 (argued down to 5–15% on the
  9/26 八点共识); momentum base rate moved to 附 line. Pass criteria 5/5.
- Cost: whole run 562k+64k tokens, 17.4 min (vs 238k+36k, 10.2 min on 10-01) —
  ~2.4×, above the +30–50% estimate (tool-loop context re-sent every round).
- Follow-ups found (not fixed):
  1. verifier tag guard stamps 〖内部数据〗 on dates/ordinals/bands that happen to
     match DATA numbers: "9·10〖内部数据〗", "第5〖内部数据〗条", "5-15%〖内部数据〗",
     "2026年9月23-25日〖内部数据〗" — false provenance labels (pre-existing; the
     10-01 report had "15–40%〖内部数据〗").
  2. writer still emits a stray leading "# 报告" H1 (md_to_pdf hides it).
  3. two §3 rows have no source link ("—"); verifier can't see it (no numbers).
  4. bear-pass cost: cap rounds or trim fetched page text if 2.4× is too much.
