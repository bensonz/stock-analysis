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
