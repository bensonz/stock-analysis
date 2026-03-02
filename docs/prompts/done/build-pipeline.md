# Stock Analysis Pipeline Redesign

## Task
Build the new script-first pipeline as described in `docs/WORKFLOW-REDESIGN.md`. 

## What to build

### 1. `scripts/data_collector.py` — All data fetching
- `fetch_strategy_pool()` — Use CheeseForTune API (existing `cheesefortune_client.py`) to get the strategy stock list. The browser scrape currently gets the list from `https://stock.cheesefortune.com/strategy/stock/detail/352390`. Check if the API can provide this (look at the client's endpoints). If not, fall back to scraping with the existing client.
- `batch_enrich(stocks)` — Use `cheesefortune_client.py batch` for stocks in RPS 75-95% zone
- `fetch_market_overview()` — Use AkShare for indices (上证/深证/创业板/科创50). Wrap in try/except, return partial data on failure.
- `fetch_position_prices(positions)` — Use AkShare via existing `fetch_price.py` logic
- `fetch_missed_opportunity_prices(recent_watchlists)` — Get current prices for past recommendations
- All functions return dicts, handle errors gracefully, never crash
- **Important:** Eastmoney domains go through Surge proxy on this machine. The Surge config has been updated to route `eastmoney.com` DIRECT, but if you see proxy errors, the issue is Surge TUN mode. Don't try NO_PROXY — it doesn't work at TUN level.

### 2. `scripts/position_manager.py` — Position state machine
- `load_active_positions()` — Read all `tracking/*.json` (skip positions.json)
- `close_position(code, reason, exit_price, lesson)` — Move to `tracking/closed/`, update fields
- `open_position(data)` — Create `tracking/{code}.json`
- `update_position(code, updates)` — Update history, stop, price
- `regenerate_positions_json()` — ALWAYS called after any mutation. Scans `tracking/*.json`, skips closed, writes `tracking/positions.json`
- `save_daily_summary(date, actions)` — Write `tracking/daily/YYYY-MM-DD.json`

### 3. `scripts/report_generator.py` — Generate reports from data
- `generate_watchlist_json(date, data, decisions)` — Write `watchlist/YYYY-MM-DD.json`
- `generate_report_md(date, data, decisions)` — Write `reports/YYYY-MM-DD.md`
- Report should NOT include position status (that's tracker's domain). Only market overview + stock recommendations.

### 4. `scripts/validator.py` — Consistency checks
- `validate_data(data)` — Check Phase 1 output completeness
- `validate_output(date)` — Check all output files exist and are consistent:
  - positions.json matches tracking/*.json active set
  - No closed positions in tracking/ root
  - watchlist/YYYY-MM-DD.json exists and is valid JSON
  - reports/YYYY-MM-DD.md exists
  - daily summary exists

### 5. `scripts/run_daily.py` — Main orchestrator
- Phase 1: Call data_collector functions, save raw data to `data/`
- Phase 2: Build LLM prompt from collected data, call LLM (via `sessions_spawn` or direct API — use subprocess to call `openclaw` CLI or just format the prompt and print it for now. See "LLM Integration" below)
- Phase 3: Parse LLM response, apply decisions via position_manager, generate reports
- Phase 4: Validate, git commit, print summary
- **Error handling:** Each phase logs errors but continues. Partial data is OK. 
- **Logging:** Write `logs/YYYY-MM-DD.json` with timing, errors, phase results

### 6. `agents/ANALYST.md` — Single analysis prompt (replaces 3 agents)
- Rewrite as the LLM prompt template
- Input: structured JSON with market data, positions, watchlist, learnings
- Output: structured JSON with decisions (see WORKFLOW-REDESIGN.md for schema)
- Must handle: position evaluation, new position candidates, missed opportunities, learnings

### LLM Integration
For the LLM call in `run_daily.py`, use this approach:
- Write the full prompt + data to a temp file
- Print it to stdout with a clear marker like `=== LLM_PROMPT_START ===` / `=== LLM_PROMPT_END ===`
- For now, the script can be called by an OpenClaw cron job that reads the prompt output and feeds it to the LLM
- OR: use `subprocess` to call `openclaw` CLI if there's a one-shot mode
- The key design: data collection + execution are deterministic Python. Only the analysis step needs LLM.

## Existing code to reuse
- `scripts/cheesefortune_client.py` — CheeseForTune API client (keep as-is, import from it)
- `scripts/fetch_price.py` — AkShare price fetcher (reuse the get_stock_price logic)
- `scripts/fetch_and_save.py` — Market data fetcher (reuse the market snapshot logic)
- `LEARNINGS.md` — Read as context for LLM
- `tracking/*.json` — Position files (existing format, keep compatible)

## Constraints
- Python 3.11+ (venv at `.venv/`)
- Dependencies: akshare, requests (already in venv)
- Don't add new dependencies unless absolutely necessary
- Keep existing file formats compatible (tracking/*.json, watchlist/*.json, etc.)
- All scripts should work standalone: `python scripts/run_daily.py`
- Use pathlib for all file paths
- Type hints on all functions

## Testing
- Add `scripts/test_pipeline.py` with basic tests for each module
- Test validator catches common issues (missing files, position mismatch)
- Test position_manager state transitions (open, close, update)

## Do NOT
- Touch `scripts/cheesefortune_client.py` (it works fine)
- Change tracking file format (backward compatible)
- Add browser dependencies
- Add external API keys or services
