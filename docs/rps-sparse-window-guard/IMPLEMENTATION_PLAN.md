## Stage 1: Capture The Failure

**Goal**: Record the concrete failure mode behind the empty 2026-04-14 intersection.
**Success Criteria**: Repo notes explain the sparse-date MA-window collapse and bad cache reuse.
**Tests**: N/A
**Status**: Complete

## Stage 2: Fix RPS Date Selection

**Goal**: Make MA/RPS calculations use only sufficiently covered trading dates and reject undersized cache entries.
**Success Criteria**: `compute_ma_rps()` no longer collapses to sparse partial-refresh dates near the head of `daily_prices`.
**Tests**: Regression test for sparse dates inside the trailing MA window.
**Status**: Complete

## Stage 3: Add Regression Coverage

**Goal**: Prevent bad cache reuse and sparse-window regressions.
**Success Criteria**: Tests fail on the old behavior and pass on the new behavior.
**Tests**: Pytest coverage for sparse windows and undersized cache rows.
**Status**: Complete

## Stage 4: Validate Against Today's Run

**Goal**: Recompute the affected RPS/intersection path and confirm the result is no longer empty.
**Success Criteria**: Local verification shows a realistic intersection count for `2026-04-14`.
**Tests**: Manual recomputation against `data/pricedb/ashare_prices.db`.
**Status**: Complete
