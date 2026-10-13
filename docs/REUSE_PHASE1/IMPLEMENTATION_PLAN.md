# --run --reuse-phase1

Re-run a slot from its saved `phase1.json` instead of collecting again.
Trigger: 2026-10-13 afternoon failed Gate 2 (LLM gave new position 600546 no
`target`); the only rerun was a full `--run`, ~4 min of fetch for data that
had not changed.

## Stage 1: Loader

**Goal**: `run_daily.load_saved_phase1(run_dir, date, slot, snapshot_fn)`
**Success Criteria**: re-attaches `learnings` / `hypothesis_prompt` / `_hypothesis_data`; refuses missing file, other date, other slot, missing snapshot, moved book
**Tests**: `tests/test_reuse_phase1.py` (7)
**Status**: Complete

## Stage 2: Wire into `--run`

**Goal**: `--reuse-phase1` skips health check, preflight, phase 1; Gate 1 still runs (no auto-heal); prior manifest's `health_check` / `preflight_pricedb` carried over
**Success Criteria**: prompt from reloaded data byte-identical to the original run's
**Tests**: manual diff on 2026-10-13 afternoon — identical (147,888 bytes)
**Status**: Complete

## Stage 3: Docs

**Goal**: CLAUDE.md commands, RUNBOOK trigger section + failure table
**Status**: Complete
