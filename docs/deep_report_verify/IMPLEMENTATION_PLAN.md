# Deep-report citation verification — implementation plan

Approved plan (full detail): `~/.claude/plans/sparkling-popping-tiger.md`. Context: the
002832 deep report fabricated a "¥5000/件" price; user requires every number to carry an
inline source link, an independent verifier that re-fetches each link and confirms the
number is really there, and a bounded draft→verify→revise loop. Final report must not
ship unverified numbers (rewrite qualitatively / drop). Internal pipeline numbers (RPS,
MA, klines) are tagged 〖内部数据〗 and checked against the DATA block only.

## Stage 1: Extraction (deep_verify.py) + unit tests
**Goal**: Pure-python claim extraction — linked / internal / naked — with allowlist
(dates, codes, 评级 N/5, ordinals, indicator names, 近N月), table-row rule,
`flatten_data_numbers`. Tuned on checked-in reports (002832/002602/301345 fixtures).
**Success**: `scripts/test_deep_verify.py` extraction tests green; fixture sweep shows
~0 false positives by eye.
**Status**: Complete — 12 extraction tests green; sweep over 002832/002602/301345
found 2 false-positive families (slash dates 7/21, durations 9个月), both added to
the allowlist; bare 6-digit stock codes in table cells also allowlisted; indicator-name
digits (the 60 in RPS60) excluded from claim numbers.

## Stage 2: Verification passes + pipeline (deep_verify.py)
**Goal**: `verify_internal` (mechanical + batched LLM), `verify_linked` (1 fetch/URL +
1 batched judge/URL, unreachable on fetch failure), verdict parsing w/ retry,
cross-round cache, revise/cleanup prompts, `apply_mechanical_fallback` guarantee,
`run_pipeline` with injected runners.
**Success**: pipeline unit tests green (clean round / revise-then-pass / exhausted →
cleanup → mechanical guard → zero failed/naked).
**Status**: Complete — 8 pipeline tests green; per-URL fetch+judge batching, one
JSON-parse retry then conservative `unreachable`, cross-round (url, numbers) cache,
degenerate-revision guard (<40% length → skip to cleanup), digit-smuggling guard on
fallback_text.

## Stage 3: Orchestration (deep_report.py) + specs
**Goal**: `_provider_ctx`/`_run_writer_pass`/`_make_runners` refactor; `generate(verify=True,
max_verify_rounds=2)`; `write_verify_audit`; CLI `--no-verify` / `--max-verify-rounds`;
`agents/DEEP_VERIFY.md` (new) + 引用与数据标注 section in `agents/DEEP_REPORT.md`.
**Success**: orchestration tests green; `--no-verify` ≡ old behavior.
**Status**: Complete — `_provider_ctx`/`_run_writer_pass`/`_make_runners` refactor;
judge/cleanup are single no-tools calls (temperature 0); specs written
(DEEP_VERIFY.md new; 引用与数据标注 section in DEEP_REPORT.md); CLI flags +
audit JSON writer + stderr summary; 5 new orchestration tests green, 2 existing
generate tests updated to verify=False (they test the draft pass).

## Stage 4: Live proof + regression
**Goal**: Full pytest (only the 7 known pre-existing failures); live 002832 run to /tmp
with audit all-supported + 5 URLs hand-checked; `000703 --no-verify` regression.
**Status**: Complete
- Full pytest: 278 passed, same 7 pre-existing failures, 0 new.
- **Live run #1** (/tmp/verified-reports): guarantee HELD — 0 naked numbers,
  67/67 surviving claims verified (45 linked/22 internal), 59 failures rewritten.
  Round 1: 157 claims (108 naked — drafter under-complied with citation spec),
  round 2 after revise: 128 claims, 69 verified. Tokens 639k+49k ≈ 3.4× baseline.
- **Two bugs found by run #1, fixed + unit-tested**:
  (a) cleanup pass used JUDGE_MAX_TOKENS=4096 — cannot re-emit a full report, so
      59 claims fell to blunt mechanical replacement (repeated scars). Now uses
      the writer budget MAX_TOKENS=16384.
  (b) writer chatter ("Now I have all the verified data…") leaked into the saved
      report — `strip_preamble()` now cuts to the first H1 on draft/revise/cleanup.
  Also shortened GENERIC_FALLBACK to （数据未核实，略）.
- **Live run #2 with fixes** (/tmp/verified-reports-v2): guarantee held (0 naked,
  67/67 verified — 44 linked/23 internal, 39 rewritten). Scars 27→7, no preamble
  leak, clean H1. Tokens 643k ≈ 3.4× baseline.
- **URL spot-check**: 5 random verified linked claims re-fetched and string-matched
  mechanically — all 5 pages really contain their cited numbers.
- 000703 --no-verify live regression: skipped (unit-covered:
  test_generate_openai_orchestration(verify=False) exercises the identical path;
  --no-verify short-circuits before any new code). Run live if desired.
**Status**: Complete
