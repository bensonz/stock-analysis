# Progress

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
