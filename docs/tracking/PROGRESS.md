# Progress

## 2026-04-09: Contract-Based Pipeline Gates (Harness Engineering)

### Completed
1. **`scripts/contracts.py`** — New module: PipelineGate, GateResult, RunManifest, validate_phase1_gate, validate_llm_output_gate, validate_phase3_gate, check_source_health
2. **`scripts/data_collector.py`** — Added `_fetch_position_prices_sina()` (Sina real-time primary), `_enrich_with_mavol30()`, rewrote `fetch_position_prices()` with 3-source fallback (Sina -> AkShare -> CheeseForTune)
3. **`scripts/run_daily.py`** — Wired in pre-flight health check, Gate 1/2/3, manifest.json, proper exit codes and status (SUCCESS/DEGRADED/FAILED)
4. **`tests/test_contracts.py`** — 54 unit tests, all passing
5. **`tests/conftest.py`** — Pytest config with `--run-integration` flag

### Key Behaviors
- Missing prices → Gate 1 hard fail, no LLM call, exit 1
- Stale pool → soft warning, DEGRADED status
- LLM forgets position → Gate 2 hard fail
- Apply errors → Gate 3 hard fail
- Clean run → manifest.json with SUCCESS

## 2026-03-15: Stop Forced Daily Entries

### Completed
1. Replaced the deterministic weak-market hard block with a regime-based sizing throttle in Phase 3; panic sessions still veto new longs, while weak and strong sessions scale allocation down
2. Enforced `min_cash_pct` and available-cash sizing in `position_manager.py`
3. Exposed reserve/deployable cash in portfolio summaries for the PM pass
4. Added focused tests for sizing and entry gating

## 2026-03-15: Replay 2026-03-13

### Completed
1. Restored the March 13 pre-run snapshot without deleting the saved run directory
2. Replayed the saved March 13 decisions against saved `phase1.json`
3. Suppressed `new_learnings` during replay to avoid duplicating them under 2026-03-15
4. Revalidated `2026-03-13` after replay

## 2026-03-11: Fix Option B Schema Mismatch + Fallback

### Completed
1. **`build_summary()` schema fix** — handles actual Phase 1 data: dict indices, {top5,bottom5} sectors, `positions` key, `price` in position_prices, structured iv_sentiment, None/missing fields
2. **Claude fallback JSON** — added Pass 1b: if memo has no JSON, small follow-up call extracts it
3. **Architecture preserved** — Claude full+tools → GPT condensed+no-tools unchanged
4. **10 new tests** — `test_build_summary.py` covers all schema variants + real phase1.json

## 2026-03-11: Architecture Option B — Sequential Claude→GPT Pipeline

### Completed
1. **`scripts/llm_client.py`** — Replaced 4-pass with 2-pass sequential handoff
   - Pass 1: Claude (full prompt + tools) → research memo + fallback JSON
   - Pass 2: GPT-5.4 (condensed ~30KB + memo, no tools, 120s timeout) → final JSON
   - Added `build_summary()`, `build_gpt_prompt()`, `_parse_json_from_text()`
   - Preserved `call_llm_v1()` for rollback
2. **`scripts/run_daily.py`** — Updated for new return format, `--legacy-llm` flag
3. **`agents/ANALYST.md`** — Research memo output mode with fallback JSON

### Impact
- ~71% input token reduction, eliminates GPT hanging on 213KB prompts
- GPT sees ~30-40KB instead of 213KB, single call with 120s timeout

## 2026-03-05: Refactor Date-Grouped Runs

### Completed
1. **data_collector.py** — Added `output_dir` param to save functions + updated `load_recent_watchlists`
2. **report_generator.py** — Added `output_dir` param to generate functions
3. **position_manager.py** — Added `output_dir` param to `save_daily_summary`
4. **run_daily.py** — Full restructure for date-grouped runs
   - `runs/YYYY-MM-DD/input/` — pre-run snapshot + collected data
   - `runs/YYYY-MM-DD/output/` — post-run snapshot + watchlist/report/summary
   - `runs/YYYY-MM-DD/phase1.json`, `prompt.md`, `response.json`, `log.json`
   - `snapshot_positions()` / `restore_snapshot()` — full state snapshots
   - `check_snapshot_consistency()` — drift detection between runs
   - `--reset-to DATE` — restore state to end of any prior date
   - `--list-runs` — show all runs with completion status
   - `--validate DATE` — validate specific date's output
5. **validator.py** — Updated to check `runs/<date>/output/` with legacy fallbacks
6. **.gitignore** — Ignore large regenerable files (phase1.json, prompt.md, response.json)

## 2026-03-02: Pipeline Redesign Build

### Completed
1. **scripts/position_manager.py** — Position state machine
   - load/open/close/update positions
   - regenerate_positions_json (always after mutations)
   - save_daily_summary

2. **scripts/data_collector.py** — All data fetching
   - fetch_strategy_pool (API + crawl file fallback)
   - batch_enrich (CheeseForTune API)
   - fetch_market_overview (AkShare)
   - fetch_position_prices (AkShare)
   - fetch_missed_opportunity_prices
   - load_recent_watchlists

3. **scripts/report_generator.py** — Report generation
   - generate_watchlist_json
   - generate_report_md (market + recommendations only, no positions)

4. **scripts/validator.py** — Consistency checks
   - validate_data (Phase 1 completeness)
   - validate_output (file existence, position sync, JSON validity)

5. **scripts/run_daily.py** — Main orchestrator
   - Phase 1: data collection
   - Phase 2: LLM prompt output
   - Phase 3: apply decisions (--apply FILE)
   - Phase 4: validate + log

6. **agents/ANALYST.md** — Single analysis prompt
   - Structured JSON input/output
   - Decision framework (stop rules, profit protection, RPS zones)

7. **scripts/test_pipeline.py** — 20 tests, all passing
   - position_manager: 7 tests
   - validator: 6 tests
   - report_generator: 2 tests
   - run_daily parser: 4 tests

### Notes
- CheeseForTune API doesn't have a strategy pool list endpoint (tried 2 URLs)
- Falls back to loading from data/crawl/*.json (most recent file)
- Strategy API endpoint could be added later if discovered

## 2026-03-03: Portfolio Value Tracking + Position Sizing + Self-Evolution

### Completed
1. **tracking/portfolio_config.json** — Starting capital 1M, max 10% per position
2. **position_manager.py** — Portfolio tracking
   - `load_portfolio_config()` / `compute_realized_pnl()` — new functions
   - `open_position()` accepts `allocation_pct`, computes shares/allocatedCapital
   - `regenerate_positions_json()` outputs full portfolio summary block
   - Per-position: shares, allocatedCapital, currentValue, unrealizedPnl, weight_pct
   - Portfolio: totalEquity, cash, unrealized/realized P&L, totalReturnPct, dayPnl
3. **agents/ANALYST.md** — Sizing rules + self-evolution
   - Position sizing rules (1-10% based on conviction)
   - `allocation_pct` in new_positions JSON example
   - Self-evolution section: agent can create rule scripts via `new_scripts` output
4. **run_daily.py** — Full pipeline integration
   - Phase 1: run rules on current state, include `rule_violations` in prompt data
   - Phase 2: include portfolio summary + allocation data in LLM prompt
   - Phase 3: pass `allocation_pct`, handle `new_scripts`, post-apply rule check
   - Phase 4: include rule violations in validation output
   - Daily summary uses actual dollar P&L (equity, unrealized, realized, cashPct)
5. **Rules integration** — `scripts/rules/` + `scripts/run_rules.py` (pre-existing)
   - 3 rules active: check_time_decay, check_overextended_entry, check_stop_proximity
   - Rules run in Phase 1, Phase 3 (post-apply), Phase 4 (validation)
   - Agent can create new rules via `new_scripts` JSON output

### Acceptance Criteria Status
- [x] positions.json has portfolio block with equity, cash, P&L, return %
- [x] Each position has shares, allocatedCapital, currentValue, unrealizedPnl, weight_pct
- [x] Agent can specify allocation_pct (1-10%) for new positions
- [x] scripts/rules/ exists, run_rules.py works, 3 rules active
- [x] Agent can output new_scripts, pipeline creates them
- [x] Rule violations included in Phase 2 prompt data
- [x] Daily summary uses actual dollar P&L
