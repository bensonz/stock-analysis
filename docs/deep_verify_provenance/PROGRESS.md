# Progress

## 2026-10-03
- Found during the 600150 bear-case smoke test. 135/961 verified internal claims
  rest on coincidental small-number matches (c021: web fact passed as DATA).
- Plan + pass criteria written before code (advisor-reviewed).
- Stage 1 done: 5 exemption forms + strip_exempt_tags + writer told not to cite
  the brief by number. Suite 885 passed / 12 skipped.
- Stage 2 done: anchor rule + single cache key + full-DATA judge. Suite 891 passed / 12 skipped.
  Expect ~135/961 historically-mechanical claims to route to the judge instead.

## 2026-10-03 — Stage 3 live run (600150 run 3)
- 4/4 pass criteria. Verdict moved to 中性 3/5 (run 1: 看多 4/5) — different
  draft at temperature 1.0, not attributable to this change.
- NEW accuracy gap (not fixed): a claim whose only number is a date is exempt, so
  "中美整体休战已宣布延长至2027年1月10日" went out unlinked and unchecked. It is the
  writer's main 缓冲因素 for rating the 301 port-fee restart 8–15%. Its source in
  the bear brief (TechTimes 2026-09-29) is headlined "USTR Section 301 Chinese ship
  fees still expire November 9 despite Bessent's truce extension" — i.e. the
  source says the truce extension does NOT cover the ship fees. The verifier
  checks numbers, not the logic a probability rests on.
- NEW ledger gap: prediction ids are <code>-<date>-jN, so a same-day re-run logged
  "3 bets (0 new)" — the ledger keeps run 1's bets (5–15%, exp 2026-12-15) while
  the published report says 8–15%, exp 2026-11-30.
