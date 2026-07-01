# Prompt: Fix swapped-args regression breaking `/api/alerts/scan` (options-learn backend)

> **Repo:** `options-learn` backend (deployed `/opt/options-learn` on Aliyun, `ssh aliyun`).
> **Severity:** HIGH — the daily options scanner has returned **all-null IV data (0 alerts) since ~2026-06-30** because of this bug. It looks like "no setups / IV feed down" but it's actually a code regression from the recently-added DB-snapshot path (`build_market_context_from_db`).

## Root cause (verified from live backend traceback)

`app/services/alert_scanner.py`:

- Function signature (line ~746):
  ```python
  def build_market_context_from_db(code: str, db: Session) -> MarketContext | None:
  ```
  → expects **(code, db)**.

- Call site (line ~739) inside `_build_market_context(code: str, db: Session)`:
  ```python
  if _has_fresh_snapshot(db, code):
      ctx = build_market_context_from_db(db, code)   # ❌ args swapped
  ```

`db` (a `Session`) is passed into the `code` param and `code` (a `str`) into the `db` param. Then inside the function:
```python
db.query(DailyIVSummary)   # db is actually the string code → AttributeError
```
Live backend log:
```
Market context failed for 510050
  File ".../alert_scanner.py", line 739, in _build_market_context
    ctx = build_market_context_from_db(db, code)
  File ".../alert_scanner.py", line 754, in build_market_context_from_db
    db.query(DailyIVSummary)
AttributeError: 'str' object has no attribute 'query'
```
This fires for all 9 underlyings → every MarketContext fails → scan returns null IV/VRP for everything → 0 recommendations.

## Fix (one line)

At line ~739 in `_build_market_context`, swap the arguments to match the signature:
```python
ctx = build_market_context_from_db(code, db)
```

## Also check (same class of bug)

Grep the file for every call to `build_market_context_from_db(` and `_has_fresh_snapshot(` and confirm argument order matches each function's signature. Confirm `_build_market_context_live(code, db)` is called consistently too. Normalize the parameter order across these helpers if they disagree (pick `(code, db)` everywhere, since `scan_alerts(db)` / `build_market_context_from_db(code, db)` already use it).

## Acceptance criteria

- `GET /api/alerts/scan` returns **non-null** `iv_percentile` / `avg_vrp` for underlyings that have snapshot data (should match the real IV ranks — e.g. semis in the 90–100th percentile range recently).
- No `AttributeError: 'str' object has no attribute 'query'` in `docker compose logs backend`.
- Add/extend a unit test that calls `build_market_context_from_db` and `_build_market_context` with a real Session and asserts a populated `MarketContext` (would have caught the swap).
- Latency stays low (this is the fast DB path — should be well under 1s per the earlier latency fix).

## Deploy / verify

```
ssh aliyun
cd /opt/options-learn
git pull            # after merge
docker compose build backend && docker compose up -d backend
curl -s --noproxy '*' http://localhost:8080/api/alerts/scan | python3 -m json.tool | head -40   # expect real IV numbers, not null
docker compose logs --tail=30 backend                                                            # no AttributeError
```
