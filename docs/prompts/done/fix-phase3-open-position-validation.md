# Fix Prompt — Phase 3 open_position failure after Option B validation

Context:
- Repo: /Users/bz/Work/Personal/stock-analysis
- The Option B Claude→GPT pipeline now runs successfully enough to produce `response.json` / `response_gpt.json`.
- Full validation run on 2026-03-11 completed with exit code 0, but Phase 3 apply had OPEN errors.
- This is a focused apply-layer bugfix prompt, not an architecture redesign.

## What failed
During:
```bash
python3 scripts/run_daily.py --run --no-commit
```
Phase 3 logged:
```text
ERROR OPEN 002497: unsupported operand type(s) for //: 'float' and 'NoneType'
ERROR OPEN 603191: unsupported operand type(s) for //: 'float' and 'NoneType'
ERROR OPEN 600096: unsupported operand type(s) for //: 'float' and 'NoneType'
```

## Root cause (confirmed)
The generated `response.json` contains `new_positions` entries like:
```json
{
  "code": "002497",
  "name": "雅化集团",
  "entry_price": null,
  "allocation_pct": 3,
  "stop": null,
  "target": null,
  ...
}
```

Then `scripts/run_daily.py` passes that into `open_position()`:
```python
open_position({
    "entryPrice": p["entry_price"],
    "targetPrice": p.get("target", p.get("targetPrice", 0)),
    "stopLoss": p.get("stop", p.get("stopLoss", 0)),
    ...
})
```

Then `scripts/position_manager.py` does:
```python
entry_price = data["entryPrice"]
capital = config["starting_capital"] * alloc_pct / 100
shares = int(capital // entry_price)
```
If `entryPrice` is `None`, this becomes:
```python
float // None
```
which causes the observed crash.

## Key diagnosis
This is not just a generic type-check problem. The system currently allows the LLM to emit incomplete `new_positions` objects with missing:
- `entry_price`
- `stop` / `stopLoss`
- `target` / `targetPrice`

For Phase 3 apply, these fields must be valid or the position must be skipped/rejected.

## Your task
Fix the apply pipeline so invalid `new_positions` do not crash execution, and ideally enrich/fill missing fields before apply when reliable market data exists.

## Required changes

### A. Add validation/normalization for `new_positions` before `open_position()`
In `scripts/run_daily.py`, before calling `open_position()`, normalize each proposed new position.

Required behavior:
- If `entry_price` is missing/null:
  - try to infer it from available Phase 1 market data for that code (preferred)
  - if no reliable price is available, skip the open with a clear log message
- If `stop`/`stopLoss` is missing/null:
  - either derive a conservative default from entry price / system rules if such a rule already exists in the repo
  - or skip with a clear log message
- If `target`/`targetPrice` is missing/null:
  - either derive a default if the system has a rule
  - or allow open only if target is truly optional everywhere downstream

Do not pass `None` into `open_position()` for required numeric fields.

### B. Make `open_position()` defensive
In `scripts/position_manager.py`, add explicit validation near the top of `open_position()`.

Requirements:
- Validate `entryPrice` is numeric and > 0 before sizing math
- Validate other required fields before use
- Raise a clear ValueError like:
  - `Missing or invalid entryPrice for 002497`
  instead of low-level `unsupported operand type(s) for //: 'float' and 'NoneType'`

This is important even if run_daily is fixed — defense in depth.

### C. Prefer deterministic enrichment over trusting the LLM
If Phase 1 already has the live/close price for a stock, use that to fill missing `entry_price`.

Likely data sources to inspect:
- `data["enriched"]` or similar candidate enrichment structure
- `data["strategy_pool"]["stocks"]`
- other Phase 1 per-stock data already loaded in memory

The LLM should not be the only source of execution-critical numeric fields when the pipeline already has market data.

### D. Decide and document the contract for `new_positions`
Tighten the contract so either:
1. LLM must always emit execution-ready values (`entry_price`, `stop`, `target`), OR
2. Phase 3 is officially responsible for filling them from deterministic market data before execution.

Pick one consistent approach and implement it cleanly. My recommendation: Phase 3 should enrich missing execution fields from deterministic data.

### E. Optional but recommended: update prompts/schema guidance
If helpful, update the LLM instructions/schema so the model is asked to provide these fields when possible.
But do not rely on prompt compliance alone.

## Validation steps to run
After your fix, run:
```bash
python3 -m py_compile scripts/position_manager.py scripts/run_daily.py scripts/llm_client.py
python3 scripts/run_daily.py --run --no-commit
```

## Success criteria
- No more `float // NoneType` errors during Phase 3 opens
- Invalid new positions are either enriched successfully or skipped cleanly
- `open_position()` emits clear validation errors when given bad data
- No unrelated refactors
- Preserve the working Option B LLM pipeline
