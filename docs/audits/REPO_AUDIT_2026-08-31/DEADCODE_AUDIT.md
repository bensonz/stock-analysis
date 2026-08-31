# Dead-Code Audit — 2026-08-31

*Verbatim report from the read-only dead-code survey agent. No files
modified; pipeline not run; tracking/ verified untouched throughout.*

## Headline

The Python is unusually clean: only 8 unreferenced top-level definitions
across ~39,000 LOC, and zero duplicated function bodies across files. The rot
is in the TEST layer: one file that fires live network requests at a retired
provider on every pytest run, seven "tests" that can never fail, and twelve
integration tests the documented command has silently been unable to run.

## Deletion candidates

### CERTAIN

**scripts/test_eastmoney.py (27 LOC)** — no test functions or classes at all;
a bare module-level `for host in HOSTS:` loop issuing four real HTTPS
requests to push2.eastmoney.com with timeout=10. Named test_*.py, so pytest
imports it at collection: EVERY pytest run makes four live calls to a
formally retired provider, costing up to 40s when eastmoney throttles. Its
only commit is 591f011 (2026-03-04) "switch all market data to Sina" — the
very commit that stopped using eastmoney. Zero importers, zero references.

### LIKELY (~600 LOC)

**scripts/fetch_price.py (107) + scripts/fetch_and_save.py (187)** —
standalone AkShare CLIs predating the pipeline. Nothing imports them; no
plist or shell script invokes them. Only references are agents/TRACKER.md,
RESEARCHER.md, ORCHESTRATOR.md — and only ANALYST.md, DEEP_REPORT.md,
DEEP_VERIFY.md are actually loaded by code, so those mentions are
documentation, not execution. Corroborating: fetch_and_save.py writes to
data/prices/, data/market/, data/crawl/ — all EMPTY since the 2026-03-05
migration. Deleting requires editing the three agent docs in the same commit.

**scripts/research/vcp_backtest.py (282)** — the only module with genuinely
ZERO references anywhere. Contains dead get_index_return (:56).

**scripts/test_hypothesis_manager.py::TestHistoricalReplay::test_replay_existing_runs**
— delete; see red-tests section.

### NEEDS-DECISION (~400 LOC)

**scripts/pit_archive.py (209) + tests/test_pit_archive.py** — coherent
point-in-time archive CLI; output tells the story: archive/margin_sse/ newest
file 2025-01-09, the other three declared sources have no directory at all.
Abandoned initiative, not broken.

**requirements.txt: baostock, tushare, httpx** — all three NEVER imported.
The retired fetchers take an already-constructed client as a parameter and
NOTHING constructs one; only test fakes do. httpx is a transitive dep of
anthropic/openai — direct pin redundant. akshare (14 imports), requests (23),
pycryptodome (2), anthropic, openai genuinely used.

**Eight unreferenced functions/classes** (AST cross-file, names + attributes
+ all markdown/shell text):
- cheesefortune_client.py:278 get_strategy_signals
- data_collector.py:637 _parse_strategy_stocks
- pricedb/__init__.py:265 _reset_trade_calendar_cache — FLAGGED: test hook shape
- ifind_client.py:399 reset_client — same
- research/deep_verify.py:307 covered_spans
- research/vcp_backtest.py:56 get_index_return
- contracts.py:39 class Severity — superseded by GateResult's lists

**Five empty directories** — watchlist/, tracking/daily/, data/prices/,
data/market/, data/crawl/ — all emptied by the 2026-03-05 migration.

## The 7 red tests

Run in isolation with tracking/ hashed before/after; git stayed clean.

**Five in test_hypothesis_manager.py are a wall-clock time bomb, not a bug.**
All feed hardcoded evidence dates 2026-03-01..17; add_evidence stamps
lastTested = ev_date, _auto_lifecycle compares to date.today() against
RETIRE_STALE_DAYS = 30 → today everything is ~180d stale and retired before
the promotion chain runs. Green when they landed (2026-03-10); rotted
~2026-04-06. RECOMMENDATION: derive dates from date.today() - timedelta.
Do NOT touch RETIRE_STALE_DAYS; that constant is doctrine.

**TestHistoricalReplay::test_replay_existing_runs — DELETE.** Walks
runs/*/response.json assuming dicts; one file is a bare list. Production
already guards that shape deliberately (run_daily._extract_json:2748-2753).
Deeper: response.json is GIT-IGNORED — the test's inputs are untracked local
state; it can never pass on a clean clone.

**test_pipeline.py::test_entry_regime_throttles_strong_market — FIX + RENAME.**
Commit a9d2077 (2026-07-03) deliberately changed STRONG_TAPE_SIZE_MULTIPLIER
0.75 → 1.0 with inline rationale; test wasn't updated and now asserts the
opposite of its own name.

## Two things that look fine but are broken

**`pytest --run-integration` has NEVER worked.** The two conftests use
incompatible mechanisms (tests/: --run-integration option; scripts/:
-m integration), both hooks run globally. Probed:

    pytest                                  → 12 integration STILL SKIPPED
    pytest --run-integration                → 12 STILL SKIPPED
    pytest -m integration                   → 12 STILL SKIPPED
    pytest -m integration --run-integration → runs them

The documented command silently skips all 12; they've been dead since May.

**scripts/test_full_pipeline.py contributes 7 tests that can never fail.**
Zero assert statements — check() prints ✓/✗ and increments counters only
main() reads. Under pytest, failing checks are invisible green. Worse,
test_4_rules subprocesses the whole rule engine against LIVE
tracking/positions.json on every full-suite run. (test_pricedb_smoke.py and
test_simulation.py are also assert-free but honest main()-guarded tools.)

## Looks dead but load-bearing — DO NOT DELETE

- scripts/pricedb.py (25-line shim) — subprocessed by path from run_daily at
  four sites; __main__.py enables python3 -m pricedb
- All six scripts/rules/check_*.py — exec'd by run_rules.py, zero importers
  by design
- scripts/hypothesis_manager.py — FULLY LIVE: injected into every prompt
  (run_daily.py:1276-1278), written back at :1971-1977; hypotheses.json 403KB,
  committed today. One dead surface inside it: the `stale-check` CLI
  subcommand (:552) has NO caller → RETIRE_STALE_DAYS is effectively dead in
  production because _auto_lifecycle only runs from add_evidence — a
  hypothesis receiving no evidence is never evaluated for staleness. Live
  data: 180 hypotheses, ZERO retired in five months.
- scripts/vcp_scanner.py — wired at run_daily.py:895, reaches the prompt (69
  mentions today); sparse coverage is a data property. No renderer consumes
  it — it reaches the model only through the raw pool payload.
- Retired provider fetchers — documented policy; tests pin them OUT of the chain
- scripts/oneoff/*.py — "kept for the record" per CLAUDE.md
- scripts/research/*.py — all except vcp_backtest have live reproduce commands
- docs/IFIND_EVAL/*.py — provenance for FINDINGS.md
- Fixtures: NO ORPHANS (all loaded by named tests)
- No __pycache__ tracked; every .gitignore path resolves

## Reclaimable LOC

| bucket | scope | LOC |
|---|---|---|
| CERTAIN | 1 file | 27 |
| LIKELY | 3 files + 1 test method | ~600 |
| NEEDS-DECISION | pit_archive pair, 8 fns, 3 reqs | ~400 |

~1,000 of ~39,000 LOC (2.6%). The higher-value fixes are NOT deletions: the
broken --run-integration flag, the 7 assertion-free tests, and
test_eastmoney.py taxing every suite run.

## Doc drift (for the docs owner)

- .gitignore:14 points at scripts/deep_report.py (now scripts/research/)
- Every research/ module's usage docstring prints the pre-move path
- LIVE, not cosmetic: scripts/event_calendar.py:121,124,128 embeds
  "scripts/index_event_study.py --expiry-study" into event notes RENDERED
  INTO report.md daily; same stale path stored in tracking/events.json:47
