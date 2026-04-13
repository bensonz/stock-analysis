## Stage 1: Diagnose Empty Pool And Artifact Gaps

**Goal**: Determine why the 2026-04-10 run produced an empty strategy pool and which Phase 1 artifacts are conditional versus expected.
**Success Criteria**: Root cause identified from code and run data; expected artifact contract documented for implementation.
**Tests**: Manual inspection of `runs/2026-04-10/*` and targeted reproduction of local strategy-pool stage counts.
**Status**: Complete

## Stage 2: Improve Phase 1 Observability

**Goal**: Always emit machine-readable Phase 1 diagnostics for strategy-pool generation, including empty `rps.json` / `vcp.json` and a new `strategy_pool_debug.json`.
**Success Criteria**: Every run writes the same core input artifacts even when the candidate pool is empty, and the debug artifact explains stage counts and fallback decisions.
**Tests**: Targeted unit/integration-style checks on generated run artifacts for empty-pool and non-empty-pool scenarios.
**Status**: Complete

## Stage 3: Fix Empty-Pool Fallback Behavior

**Goal**: Prevent strong-market days from silently ending with a zero-stock strategy pool when the local+cross-check path filters everything out but a remote strategy pool is still available.
**Success Criteria**: Strategy-pool logic preserves a usable fallback path and records why it was used.
**Tests**: Reproduction against the 2026-04-10 conditions and targeted tests around fallback selection.
**Status**: Complete

## Stage 4: Validate And Document Daily Run Expectations

**Goal**: Verify the updated behavior and make the daily run artifact expectations explicit.
**Success Criteria**: Relevant tests pass, manual verification succeeds, and the new artifact contract is reflected in tracking notes.
**Tests**: Relevant pytest suites plus manual inspection of generated run outputs.
**Status**: Complete
