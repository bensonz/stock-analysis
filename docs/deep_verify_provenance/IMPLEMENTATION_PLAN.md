# Deep verify: honest 〖内部数据〗 provenance

Trigger (2026-10-03, 600150 re-run): published text carried 〖内部数据〗 on things
that are not DATA — the writer's own probability band "5-15%〖内部数据〗", an
incident label "9·10〖内部数据〗", "第5〖内部数据〗条", a date range. Worse: claim
c021 "9月广船国际逾10亿" (a web fact, no link) verified as internal because
`internal_numbers_match` only asks "does every number occur somewhere in DATA" —
true for almost any 1–2 digit number. Across all saved audits: 961 verified
internal claims, 135 with no distinctive number (decimal or ≥3 significant digits).
Owner: accuracy over token cost.

## Stage 1: Allowlist exemptions + bear-block wording
**Goal**: never extract as claims: judgment bands 「判断」（5–15% / <15% / >40%）,
middle-dot incident labels (9·10, 9・10), CJK date ranges (9月23-25日), 第N条/项/点/款,
bold list ordinals (**1.). Do NOT allowlist bare thresholds (≥15%, >20%).
Writer prompt: answer the bear brief in substance, never cite it by item number.
**Tests**: one extraction test per form; threshold "同比增长>20%" stays a claim.
**Status**: Complete — also: tags covering only exempt text make no claim and are
  stripped from published text (`strip_exempt_tags`, start + end of run_pipeline).
  Replay over all saved reports: only 2 claims change, both correct (a date range, 9·10).

## Stage 2: Anchor rule — coincidental matches go to the judge
**Goal**: split `internal_numbers_present` (all numbers in DATA — used for naked→
internal conversion and tag-guard candidates) from `internal_numbers_match`
(present AND ≥1 distinctive number — the mechanical "verified" shortcut). No-anchor
internal claims go to the LLM judge. Judge sees the full DATA (minus long series)
so true numbers from summary/intro/peers are not scrubbed. One cache-key builder:
no-anchor claims keyed by context, so a judged "15%" does not verify another "15%".
Claims whose tokens are all date fragments are dropped at extraction.
**Tests**: c021-shaped claim → judge; judge-supported weak claim survives cleanup
`_classify`; anchored claim still mechanical; context-keyed cache.
**Status**: Complete — has_anchor / internal_numbers_present / internal_numbers_match
  (= present AND anchored) / _internal_key used at all 3 cache sites; judge gets full
  DATA. 6 new tests; test_flatten_and_match rewritten to assert the new routing
  (present ≠ verified), not loosened. Known gap: a weak naked number that first
  appears AFTER cleanup has no judge verdict → mechanical fallback scrubs it.

## Stage 3: Live re-measure (600150)
**Pass criteria** (written before the run):
  (a) a c021-shaped claim (web fact, weak numbers, no link) fails or ends up linked;
  (b) no （数据未核实，略） on a claim whose numbers are genuinely in DATA;
  (c) no 〖内部数据〗 on a band, ordinal, incident label or date in the report;
  (d) 0 judge errors, 0 unverified remaining.
**Status**: Complete — 4/4 PASS (run 3, 2026-10-03, 107/107 verified, 19.3 min):
  (a) PASS — round 1 the judge failed 5 weak-number claims tagged 〖内部数据〗 that
      were web facts (25人 deaths, 50万元 fine, 约60% USD revenue…); the old rule
      would have passed them mechanically. Round 2: all re-sourced with links.
  (b) PASS — zero （数据未核实，略）.
  (c) PASS — no tag on any band/label/ordinal/date; remaining short-number tags
      (≥80 gate, 21倍 PE, RPS percentiles, 15% base-rate threshold) judge-verified.
  (d) PASS — 0 judge errors, 0 unverified.
