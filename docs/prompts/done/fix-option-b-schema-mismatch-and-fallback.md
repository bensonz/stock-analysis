# Fix Prompt — Option B implementation schema mismatch + missing Claude fallback JSON

Context:
- Repo: /Users/bz/Work/Personal/stock-analysis
- We already implemented the sequential Claude→GPT Option B pipeline.
- A validation run failed on 2026-03-11.
- Do NOT redesign the architecture. This is a focused bugfix prompt.

## What failed
Running:
```bash
python3 scripts/run_daily.py --run --no-commit
```
failed with:
```text
WARNING: GPT-5.4 pass failed: 'str' object has no attribute 'get'
WARNING: Neither GPT nor Claude produced valid JSON
ERROR: Could not parse LLM response as JSON
```

## Root causes (confirmed)

### 1) `build_summary()` assumes the wrong Phase 1 schema
The actual Phase 1 data shape in `runs/2026-03-11/phase1.json` does NOT match the assumptions in `scripts/llm_client.py`.

Confirmed mismatch examples:

#### `market.indices`
Current code assumes `indices` is a list of dicts:
```python
indices = market.get("indices", [])
for idx in indices:
    name = idx.get("name", idx.get("code", "?"))
```
But actual data is a dict:
```json
"indices": {
  "上证指数": {"code": "sh000001", "close": 4131.755, "change_pct": 0.21, ...},
  "深证成指": {...},
  ...
}
```
So iterating gives string keys (`"上证指数"`), causing:
```python
AttributeError: 'str' object has no attribute 'get'
```

#### `market.sectors`
Current code assumes a list of sector dicts with keys `name` / `change_pct`:
```python
sector_data = market.get("sectors", [])
top = sector_data[:10]
```
But actual data is:
```json
"sectors": {
  "top5": [{"板块名称": "化学原料", "涨跌幅": 5.15}, ...],
  "bottom5": [{"板块名称": "小金属", "涨跌幅": -2.92}, ...]
}
```
So slicing also breaks semantically.

#### `positions`
Current code reads `active_positions`, but actual Phase 1 uses `positions`.

#### `position_prices`
Current code expects `current_price`, but actual entries use `price`.

#### `iv_sentiment`
Current code loops generic top-level keys and expects `iv` / `iv_rank` shape.
Actual data is:
- top-level metadata (`date`, `source`)
- `etf_iv_data`: list of ETF dicts
- `overall_sentiment`: dict with `signal`, `avg_iv_rank`, `avg_iv_percentile`, `implication`

#### `portfolio` / `enriched_candidates` / `active_positions`
These are absent or `None` in actual Phase 1 data and should be handled gracefully.

### 2) Claude fallback JSON is missing
The new pipeline intends:
- Claude pass = research memo + fallback JSON
- GPT pass = final JSON
- if GPT fails, use Claude fallback JSON

But current Claude output is just a research memo, not valid JSON.
So if GPT fails, pipeline has no usable decision object.

## Your task
Fix the implementation so the Option B pipeline works with the REAL Phase 1 schema and always has a fallback path.

## Required changes

### A. Make `build_summary()` schema-aware and defensive
Update `scripts/llm_client.py` `build_summary()` to support the actual Phase 1 structure.

Requirements:
- If `market.indices` is a dict, render it correctly
- If `market.indices` is a list, still support it
- If `market.sectors` is `{top5, bottom5}`, render those correctly
- If `positions` exists, use that instead of `active_positions`
- If `position_prices[*].price` exists, use that instead of `current_price`
- Render IV summary from:
  - `overall_sentiment`
  - `etf_iv_data` list
- Handle missing/None fields without crashing
- Keep the output compact and useful for GPT

Do not assume one fixed schema if the existing codebase may produce both old/new shapes.

### B. Ensure Claude produces fallback JSON
Update the Claude pass behavior so the first pass output includes a parseable JSON decision block somewhere in the response, or add a minimal second Claude fallback step only when needed.

Acceptable solutions:
1. **Preferred:** modify the prompt/instructions so Claude research memo ends with a valid JSON block matching the required final schema
2. **Acceptable:** if pass1 memo has no JSON, do a very small Claude follow-up call that says essentially:
   - convert your analysis into final JSON only
   - no markdown, no explanation
   - this JSON is fallback-only

Important:
- Do NOT bring back the old wasteful 4-pass architecture
- Do NOT reintroduce the old redundant GPT refine pass
- Keep GPT as a single condensed final-decision pass
- Keep timeout/fallback behavior

### C. Preserve current architecture
Keep:
- Claude full prompt + tools
- GPT condensed prompt + no tools + timeout
- GPT primary, Claude fallback

### D. Add minimal validation
Add a focused test or at least a lightweight validation helper so this exact bug would have been caught.

Acceptable options:
- a small unit test for `build_summary()` using a fixture shaped like actual `phase1.json`
- or a test that loads a saved run fixture and verifies `build_summary()` returns a string without exception

## Files likely involved
- `scripts/llm_client.py`
- maybe `agents/ANALYST.md`
- maybe `scripts/run_daily.py`
- optional test file if the repo has a test structure

## Validation steps you should run
Run these after the fix:
```bash
python3 -m py_compile scripts/llm_client.py scripts/run_daily.py
python3 scripts/run_daily.py --phase1
python3 scripts/run_daily.py --run --no-commit
```

## Success criteria
- `--run --no-commit` no longer crashes on `'str' object has no attribute 'get'`
- GPT prompt builds successfully from actual Phase 1 data
- if GPT fails, Claude fallback JSON is still parseable
- output artifacts include usable JSON response(s)
- no unrelated refactors
