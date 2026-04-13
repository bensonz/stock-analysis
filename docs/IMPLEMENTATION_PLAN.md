## Stage 1: Define Entry Guardrails

**Goal**: Record the scope for disabling forced daily entries and moving portfolio controls into code.
**Success Criteria**: Plan, todo, checklist, and decision notes exist and reflect the requested guardrails.
**Tests**: N/A
**Status**: Complete

## Stage 2: Enforce Portfolio Cash Constraints

**Goal**: Add a real `min_cash_pct` reserve and size new entries from currently available cash.
**Success Criteria**: Portfolio config includes `min_cash_pct`; `open_position()` rejects entries that would breach cash reserve and no longer sizes from starting capital.
**Tests**: Position sizing and reserve checks in unit tests.
**Status**: Complete

## Stage 3: Throttle New Buys By Market Regime

**Goal**: Make market regime affect fresh position sizing instead of requiring a strong day for every buy.
**Success Criteria**: Panic or missing-data sessions still veto new longs, while weak and strong sessions apply deterministic sizing throttles at apply time.
**Tests**: Apply-layer tests for weak and strong market gating.
**Status**: Complete

## Stage 4: Validate And Close

**Goal**: Verify the new guardrails and update progress tracking.
**Success Criteria**: Relevant tests pass and tracking notes show completion.
**Tests**: `py_compile` plus focused Python tests.
**Status**: Complete

## Stage 5: Replay 2026-03-13 From Saved Inputs

**Goal**: Re-run March 13 using the saved pre-run snapshot, saved Phase 1 payload, and saved response JSON without refetching data.
**Success Criteria**: Tracking state and `runs/2026-03-13/output/` reflect the new guardrails; replay avoids duplicating learnings under the current date.
**Tests**: Replay script output plus `--validate 2026-03-13`
**Status**: Complete
