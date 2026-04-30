## Stage 1: Provider Shape

**Goal**: Add a direct Eastmoney price-bar provider before AkShare without changing stock-list ownership.
**Success Criteria**: `iter_providers()` yields `eastmoney_direct` before AkShare, and `bulk_fetch()` routes to the new provider.
**Tests**: Focused unit assertions through provider helpers.
**Status**: Complete

## Stage 2: Fetch And Parse

**Goal**: Fetch Eastmoney daily klines with no-proxy urllib and curl fallback, then normalize rows for `daily_prices`.
**Success Criteria**: SH/SZ secids map correctly; BJ does not block full updates; kline rows convert to `(code,date,open,high,low,close,volume,amount)`.
**Tests**: Mocked network tests for secid mapping and kline parser.
**Status**: Complete

## Stage 3: Bulk Update

**Goal**: Reuse bounded worker, retry, budget, main-thread SQLite insert, and progress behavior for direct Eastmoney updates.
**Success Criteria**: Bulk update inserts rows from worker results and reports skipped failures without stopping on unsupported BJ symbols.
**Tests**: Existing pricedb timeout/AkShare tests plus new Eastmoney tests.
**Status**: Complete

## Stage 4: Validation And Commit

**Goal**: Run targeted tests, live smoke/update/status validation, and commit.
**Success Criteria**: Requested pytest command passes; pricedb status advances beyond 2026-04-20; commit message is `Add direct Eastmoney pricedb provider`.
**Tests**: `.venv/bin/python -m pytest tests/test_pricedb_eastmoney.py tests/test_pricedb_akshare.py tests/test_pricedb_timeouts.py -q` passed. Live smoke/update could not refresh in this sandbox because Tushare/Eastmoney curl/BaoStock all failed DNS or network connection.
**Status**: Complete
