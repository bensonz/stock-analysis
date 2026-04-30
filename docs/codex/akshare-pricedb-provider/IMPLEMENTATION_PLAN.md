## Stage 1: Understand Existing Provider Flow

**Goal**: Identify where stock-list refresh and price-bar updates are coupled.
**Success Criteria**: Existing provider APIs and update fallback behavior are understood.
**Tests**: None.
**Status**: Complete

## Stage 2: Add AkShare Historical Provider

**Goal**: Add bounded, retrying, parallel AkShare daily historical fetch for price bars.
**Success Criteria**: AkShare maps historical daily columns into `daily_prices` and writes only from the main thread.
**Tests**: Focused unit tests for row normalization and bulk insertion.
**Status**: Complete

## Stage 3: Rework Update Fallback

**Goal**: Let update use the existing/Tushare stock universe without requiring Tushare `trade_cal`, then fall through to AkShare price bars.
**Success Criteria**: Tushare stock list remains optional/preferred, AkShare can update prices without an AkShare stock list.
**Tests**: Existing timeout tests and local pricedb tests.
**Status**: Complete

## Stage 4: Validate and Commit

**Goal**: Run requested commands and commit the focused change.
**Success Criteria**: `pricedb.py update`, `pricedb.py status`, and relevant tests complete or any blocker is documented.
**Tests**: `.venv/bin/python scripts/pricedb.py update`; `.venv/bin/python scripts/pricedb.py status`; focused pytest.
**Status**: Complete
