# Fix: `pricedb.py update` can hang indefinitely on dead TCP sockets

## Problem

The `pricedb update` subprocess (invoked by `scripts/run_daily.py` Phase 1 prep) can hang forever when a data-provider TCP socket goes dead mid-read. Observed 2026-04-14 11:35 cron run: `pricedb.py update` subprocess sat at 0% CPU for 15+ minutes with an `ESTABLISHED` TCP connection to a provider endpoint, never timing out. This blocks the entire daily pipeline.

Workaround in use: `PRICEDB_SKIP_UPDATE=1`. Not a real fix — we still want fresh prices daily.

## Root cause

Two layers contribute:

1. **Provider clients don't always set a socket read timeout.**
   - **Tushare:** initialized at `scripts/pricedb.py:182` with `ts.pro_api(token=token, timeout=30)` — but the `timeout` kwarg on `pro_api` controls request-level retries in some versions, not the underlying `requests` socket read timeout. When the HTTP connection stalls mid-body, the call can block.
   - **BaoStock:** the `bs.query_*` calls go over a long-lived persistent socket (baostock uses its own socket protocol, not HTTPS). There is **no user-facing timeout knob** — if the socket dies silently, reads block until OS TCP keepalive (often many minutes).
   - **AkShare spot backfill (`_backfill_from_akshare_spot`):** uses akshare's default session with no explicit timeout.

2. **The Tushare retry wrapper `_call_tushare` at `scripts/pricedb.py:276-287` does not impose a wall-clock deadline.** If a single API call hangs, all 3 retries can hang.

## Goal

Guarantee that any single network operation in `pricedb.py` fails within a bounded time, propagates a clear error, and lets the higher-level update flow either retry with a different provider or exit cleanly. The pipeline must never see a subprocess sitting idle for more than ~90 seconds on a dead socket.

## Implementation

### 1. Introduce a global network budget at the top of `scripts/pricedb.py`

Add near the existing constants (around line 33-40):

```python
# Per-API-call hard timeout (socket read + connect). If a single call exceeds
# this, we fail fast and let the retry/provider-fallback logic handle it.
PRICEDB_CALL_TIMEOUT_SEC = float(os.getenv("PRICEDB_CALL_TIMEOUT", "30"))

# Per-update overall wall-clock budget. Enforced at the top of cmd_update.
# Pipeline cron is on a 15-minute window; default stays well under that.
PRICEDB_UPDATE_BUDGET_SEC = float(os.getenv("PRICEDB_UPDATE_BUDGET", "600"))
```

### 2. Wrap *every* provider call with a thread-based timeout helper

Pure signals don't work reliably in subprocesses, and we can't always control a library's internal socket. Use a worker thread + `.join(timeout)` pattern. Add this helper near `_call_tushare`:

```python
import threading

class _TimeoutError(RuntimeError):
    """Raised when a pricedb network call exceeds PRICEDB_CALL_TIMEOUT_SEC."""


def _run_with_timeout(label: str, func, timeout: float = PRICEDB_CALL_TIMEOUT_SEC):
    """Run func() in a daemon thread; raise _TimeoutError if it exceeds `timeout`.

    The hung thread is abandoned (daemon), so the process can still exit;
    sockets will be reaped by the OS on process teardown.
    """
    result: list = [None]
    error: list[BaseException | None] = [None]

    def _target():
        try:
            result[0] = func()
        except BaseException as e:
            error[0] = e

    t = threading.Thread(target=_target, name=f"pricedb:{label}", daemon=True)
    t.start()
    t.join(timeout)

    if t.is_alive():
        raise _TimeoutError(f"{label} exceeded {timeout:.0f}s timeout")

    if error[0] is not None:
        raise error[0]

    return result[0]
```

### 3. Refactor `_call_tushare` to use the timeout wrapper

Replace the existing `_call_tushare` body with:

```python
def _call_tushare(label: str, func):
    """Call a Tushare API with retries and per-call timeout."""
    last_error: BaseException | None = None
    for attempt in range(TUSHARE_RETRIES):
        try:
            return _run_with_timeout(label, func)
        except _TimeoutError as e:
            last_error = e
            # Don't sleep on timeout — the socket is dead, retry immediately
            # with a fresh call (the tushare client pools connections, but
            # each .daily() should open a new HTTP request).
            if attempt == TUSHARE_RETRIES - 1:
                raise RuntimeError(f"{label} failed: {e}") from e
        except Exception as e:
            last_error = e
            if attempt == TUSHARE_RETRIES - 1:
                raise RuntimeError(f"{label} failed: {e}") from e
            time.sleep(TUSHARE_RETRY_DELAY * (attempt + 1))
    raise RuntimeError(f"{label} failed: {last_error}")
```

### 4. Wrap BaoStock calls too

BaoStock's `login()`, `query_*`, and `logout()` all go over its persistent socket. Wrap each call site in `_run_with_timeout`. Specifically:

- `iter_providers()` — the `bs.login()` call near line 190:
  ```python
  login_result = _run_with_timeout("BaoStock login", lambda: bs.login())
  ```
- `fetch_stock_list_baostock()` — the `bs.query_all_stock(day=day)` call:
  ```python
  rows = _baostock_rows(
      _run_with_timeout(f"BaoStock query_all_stock {day}", lambda: bs.query_all_stock(day=day))
  )
  ```
- `_fetch_klines_baostock()` — the `bs.query_history_k_data_plus(...)` call:
  ```python
  result = _run_with_timeout(
      f"BaoStock k_data {stock['code']}",
      lambda: bs.query_history_k_data_plus(
          code_full,
          "date,code,open,high,low,close,volume,amount",
          start_date=_yyyymmdd_to_iso(beg),
          end_date=_yyyymmdd_to_iso(end),
          frequency="d",
          adjustflag="3",
      ),
  )
  ```
- `close_provider()` — the `provider.logout()` call (don't let a shutdown hang, either):
  ```python
  if provider_name == PROVIDER_BAOSTOCK:
      try:
          _run_with_timeout("BaoStock logout", lambda: provider.logout(), timeout=5)
      except Exception:
          pass
  ```

### 5. Wrap the AkShare spot fallback

In `_backfill_from_akshare_spot`, wrap the `ak.stock_zh_a_spot_em()` call:

```python
df = _run_with_timeout("AkShare spot", lambda: ak.stock_zh_a_spot_em())
```

### 6. Enforce an overall wall-clock budget in `cmd_update`

At the top of `cmd_update()`, before entering the provider loop:

```python
update_start_ts = time.monotonic()

def _budget_exceeded() -> bool:
    return (time.monotonic() - update_start_ts) > PRICEDB_UPDATE_BUDGET_SEC
```

Check `_budget_exceeded()` at three points inside the provider loop:

1. **Before** trying each provider — skip remaining providers if the budget is blown (log and continue to exit).
2. **Inside `_bulk_fetch_tushare`** — the trade-date loop is the longest single sequence; after each trade date, check the budget and `raise RuntimeError("update budget exceeded")` so the provider's `except` clause catches it and can try the next provider (though if the first exhausted the budget, the fallback check above will skip).
3. **Inside the BaoStock per-stock loop** (`_bulk_fetch_baostock`, if that's where the loop lives — follow the same pattern).

To pass the budget check into the helpers cleanly, either:

- Make `_budget_exceeded` a module-level function that reads a module-level `_UPDATE_DEADLINE` variable set at the start of `cmd_update`, OR
- Pass `deadline_ts: float | None = None` as an optional kwarg through `_bulk_fetch_tushare` / `_bulk_fetch_baostock`.

Pick the approach that matches the surrounding style; module-level is simpler given this is a script, not a library.

### 7. Set an explicit socket-level default as a belt-and-suspenders

At the very top of `scripts/pricedb.py` (right after imports), set the default socket timeout **only for this process**:

```python
import socket
socket.setdefaulttimeout(PRICEDB_CALL_TIMEOUT_SEC)
```

This protects against any library that creates raw sockets without explicit timeouts (some baostock paths, some urllib fallbacks). It does **not** replace the per-call thread timeouts — use both. The socket default catches unexpected paths; the thread wrapper catches calls that hold the GIL or ignore socket deadlines.

### 8. Surface errors in `run_daily.py` (no change needed to logic)

The existing handler at `scripts/run_daily.py:577-584` already catches exceptions from the subprocess and logs them to `log["errors"]` as a warning, then continues. With timeouts enforced inside `pricedb.py`, the subprocess will now actually exit with non-zero and a clear error message ("BaoStock k_data 600519 exceeded 30s timeout"), letting the pipeline continue with the existing price DB data.

That existing continuation behavior is correct — keep it. Do NOT add a subprocess-level timeout in `run_daily.py`; the in-process timeouts are better (clearer error messages, per-call granularity).

## Tests

Add `tests/test_pricedb_timeouts.py` (or extend an existing test file). Use pytest.

1. **`test_run_with_timeout_returns_value`** — fast function returns its value untouched.
2. **`test_run_with_timeout_propagates_exception`** — if `func` raises `ValueError`, caller gets `ValueError`.
3. **`test_run_with_timeout_raises_on_hang`** — `func = lambda: time.sleep(5)` with `timeout=0.5` raises `_TimeoutError` within ~0.6s (use `time.monotonic()` to assert).
4. **`test_call_tushare_retries_on_timeout`** — mock a function that sleeps > timeout on the first call but returns quickly on the second; assert `_call_tushare` succeeds after retry and that the total elapsed time is bounded (< `PRICEDB_CALL_TIMEOUT_SEC * 2 + slack`).
5. **`test_call_tushare_eventually_raises`** — func sleeps longer than timeout for all retries; assert `RuntimeError` is raised and elapsed time < `PRICEDB_CALL_TIMEOUT_SEC * TUSHARE_RETRIES + slack`.

Keep tests pure-Python (no real network). Monkeypatch `PRICEDB_CALL_TIMEOUT_SEC` to something small (0.3s) for speed.

## Acceptance criteria

- [ ] `python scripts/pricedb.py update` never hangs more than `PRICEDB_UPDATE_BUDGET_SEC` (default 600s) total, even if a provider socket goes dead.
- [ ] Any single provider API call that stalls past `PRICEDB_CALL_TIMEOUT_SEC` (default 30s) raises a clear `RuntimeError` containing the label and timeout.
- [ ] On timeout, the retry wrapper tries again (Tushare) or falls through to the next provider (at the provider-loop level).
- [ ] All new tests pass: `pytest tests/test_pricedb_timeouts.py -xvs`
- [ ] Existing `pricedb` tests still pass (run full suite).
- [ ] Happy path on a healthy network is unchanged in behavior and performance (timeout overhead per call is negligible — thread creation is microseconds).
- [ ] Env-var override works: `PRICEDB_CALL_TIMEOUT=5 python scripts/pricedb.py update` tightens the budget for debugging.

## Files touched (expected)

- **MODIFIED:** `scripts/pricedb.py` — timeout helper, call wrappers, budget, socket default
- **NEW:** `tests/test_pricedb_timeouts.py`
- **NO CHANGE:** `scripts/run_daily.py` — existing error handling already correct

## Out of scope

- Don't switch providers or rewrite the Tushare client.
- Don't add async/aiohttp.
- Don't change the SQLite schema or data format.
- Don't add a queue/job system — this is a single-process script.
- Don't try to kill the hung thread mid-flight (Python has no clean way). Daemon abandonment is acceptable; the process exits shortly after.

## Manual verification

After merging:

```bash
# Normal run (should behave exactly like today on healthy network)
cd /Users/bz/Work/Personal/stock-analysis
python3 scripts/pricedb.py update

# Force a tight timeout to prove timeouts trigger (will likely fail but fast)
PRICEDB_CALL_TIMEOUT=1 python3 scripts/pricedb.py update

# Verify pipeline integrates cleanly
python3 scripts/run_daily.py --run
```

Expect: first call completes normally (~30-60s). Second call fails within seconds with clear timeout messages. Third call succeeds or fails within the budget, never hangs.
