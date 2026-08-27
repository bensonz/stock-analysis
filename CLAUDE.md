# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An automated daily A-share (Chinese stock) momentum-analysis pipeline. Pure-Python data collection feeds an LLM that makes buy/hold/sell decisions, which are then applied to a simulated portfolio and committed to git. It runs **twice per trading day** (~11:35 "noon" intraday and ~15:35 "afternoon" post-close).

The trading philosophy lives in `agents/ANALYST.md` (momentum-first: buy strength via RPS, follow hot sectors, cut losers fast). Read it before touching screening thresholds or decision logic — the magic numbers in the code (RPS 75-95%, `dist_ma5>6%`, breadth 1.5:1, `f10>=30` panic gate) are all specified there and must stay in sync.

## Environment & setup

- Python venv at `.venv` — **activate it first**, then use `python3` (never bare `python`): `source .venv/bin/activate`
- Deps: `pip install -r requirements.txt` (akshare, anthropic, openai, baostock, tushare, pycryptodome, httpx, requests)
- Secrets in `.env` (git-ignored): `IFIND_REFRESH_TOKEN` (primary price source — see below), `TUSHARE_TOKEN`, `TAVILY_API_KEY` (web search), and OpenAI-compatible `OPENAI_*` / `LLM_PROVIDER`. `llm_client.py` also reads env from `~/.claude/settings.json`. (`IFIND_USERNAME`/`IFIND_PASSWORD` are unused by the HTTP API; the refresh token alone suffices.)
- **External dependency:** IV sentiment (`fetch_iv_sentiment.py`) requires the separate *options-learn* backend on `http://localhost:8000`. If it's down, `iv_sentiment.json` comes back empty (`signal: "无数据"`) and the report says "IV data unavailable" — this is a missing dependency, not a pipeline bug. It degrades gracefully (sizing falls back to "unknown").

## Common commands

```bash
# Full daily pipeline: collect → LLM → apply decisions → validate → git commit
python3 scripts/run_daily.py --run
python3 scripts/run_daily.py --run --llm-provider anthropic   # or openai / hybrid
python3 scripts/run_daily.py --run --no-commit                # skip the git commit
python3 scripts/run_daily.py --slot noon --run                # force slot (default: auto from clock)

# Partial phases (useful for debugging)
python3 scripts/run_daily.py --phase1          # data collection only
python3 scripts/run_daily.py --apply FILE      # apply an LLM response file (Phase 3+4)
python3 scripts/run_daily.py --validate [DATE] # validation only
python3 scripts/run_daily.py --list-runs       # list all runs with status
python3 scripts/run_daily.py --reset-to DATE   # roll portfolio state back to end of DATE

# Local price database (SQLite at data/pricedb/ashare_prices.db, git-ignored)
python3 scripts/pricedb.py init      # first-time: fetch stock list + all history
python3 scripts/pricedb.py update    # incremental daily update (run before analysis)
python3 scripts/pricedb.py rps [DATE]# recompute MA-based RPS for all stocks
python3 scripts/pricedb.py status    # DB stats
python3 scripts/pricedb.py snapshot [--date ISO --dry-run --force]
                                     # today's settled bar from sina's REAL-TIME
                                     # feed (hq.sinajs.cn), batched ~100 codes/req,
                                     # ~30s for the universe. The daily-kline
                                     # archive is batch-built and can lag 6h, so
                                     # this is the fast path for the close slot.
                                     # Refuses while the session is open; rejects
                                     # lines stamped before 15:00 (pre-auction).
                                     # Wired into run_daily preflight ahead of
                                     # `update`. NOT a replacement for klines:
                                     # history/backfill/factors still need them.
python3 scripts/pricedb.py repair [--beg ISO --end ISO --dry-run]
                                     # fill partial days via sina per-code klines
                                     # (INSERT OR IGNORE; ends with factor heal)
python3 scripts/pricedb.py factors verify   # factor coverage/lag audit (exit 1 = broken)
python3 scripts/pricedb.py factors heal     # repair a multi-session factor gap
                                     # (ex-div calendar + per-code re-derivation)
python3 scripts/pricedb.py factors rebuild [--code CSV] [--dry-run]
                                     # rebuild whole series from iFinD
                                     # ths_af_stock. DESTRUCTIVE: DELETEs each
                                     # rebuilt code's rows first. Rebuilds a
                                     # code entirely or not at all — iFinD
                                     # anchors its factor base at listing while
                                     # ours anchors at each code's first stored
                                     # date, so a partial splice would fabricate
                                     # a return on the splice date.
python3 scripts/pricedb.py backfill-amount [--beg ISO --end ISO --dry-run]
                                     # fill NULL `amount` from iFinD. Writes
                                     # ONLY that column (OHLCV untouched, so
                                     # first-writer-wins holds) and refuses any
                                     # row whose stored close disagrees with
                                     # iFinD's. Needed because the sina kline
                                     # fallback doesn't publish turnover, and
                                     # INSERT OR IGNORE means re-running
                                     # `update` can never repair those rows.

# Rules engine (mechanical sell/risk checks over current positions)
python3 scripts/run_rules.py --human

# Post-run audit — detection only, NEVER writes tracking/
python3 scripts/doctor.py --open        # what is broken right now, folded by
                                        # problem; also writes audit/OPEN.md.
                                        # exit 1 = something needs a code change
python3 scripts/doctor.py               # audit the most recent run, print + write
python3 scripts/doctor.py --date 2026-08-20 --slot noon
python3 scripts/doctor.py --since 2026-08-01   # sweep/recompute a range

# IV sentiment (needs options-learn backend on :8000)
python3 scripts/fetch_iv_sentiment.py --human

# Static portfolio site (open site/index.html via file://)
python3 scripts/build_site.py
```

**`site/index.html` is a derived artifact and is git-ignored.** It is a pure
function of `tracking/`, `runs/`, and `data/index_cache/`, rebuilt (~0.5s) after
every manifest write — including on failed runs, so the page always matches what
actually landed on disk and carries a red banner naming the failure. Never commit
it; regenerate instead. Sort runs by `run_started_at`, never by slot name.

### Tests

`pytest` with a custom `integration` marker. Integration tests hit real external APIs and are **skipped by default**:

```bash
pytest                          # unit tests only (integration skipped)
pytest --run-integration        # include tests that hit real APIs
pytest tests/test_contracts.py  # a single file
pytest scripts/test_pipeline.py::test_name   # a single test
```

Note test files live in **two** places: `tests/` and `scripts/test_*.py` (both are collected). `scripts/conftest.py` mirrors `tests/conftest.py` so the marker works when running `pytest scripts/` directly.

## Pipeline architecture (the big picture)

`scripts/run_daily.py` is the orchestrator. Four phases, gated by data contracts:

1. **Phase 1 — DATA COLLECTION** (pure Python, no LLM). `data_collector.py` assembles the candidate universe and writes each artifact as a separate JSON into the run's `input/` dir:
   - Strategy pool from **CheeseForTune** (芝士财富) via `cheesefortune_client.py` (reverse-engineered API, JWT + AES-signed requests) — `intersect.json`, `crawl.json`.
   - RPS screening from the local price DB via `rps_calculator.py`. **The live gate** is `_build_strategy_intersection` in `run_daily.py`: the crawl is intersected with the local RPS universe and a stock survives only if `rps60`, `rps120` and `rps250` are **all `> INTERSECT_MIN_RPS` (85.0, strict)**. There is **no MA-alignment check and no RPS ceiling** on this path — so most of what survives sits above the RPS 75–95 band `ANALYST.md` Rule 2 permits (26 of 45 on 2026-08-27). The pool table in the prompt flags those `OVER-EXTENDED`; skipping them is left to the model.
     - `data_collector.fetch_strategy_pool_local()` screens differently — `rps>=80` **plus** MA alignment `MA20 > MA120 > MA250` — and is the **outage fallback only**, used when the crawl returns an empty pool (`fetch_strategy_pool_with_fallback`). Do not treat it as a second opinion: it admits a different set, and `input/strategy_pool_debug.json` records which path produced the pool.
     - MA *distance* (`dist_ma5/10/20`) filters nothing in Python. It is enforced by the LLM via `ANALYST.md` Rule 2b, and rendered in `candidates.md` as `❌` (extended far **above** — chasing, Rule 2b), `🔻 BELOW` (far below — broken trend, split out of `❌` on 2026-08-28), `⏳ >95`, or `✅ PASS`. Those labels are **display only**; see `docs/audits/CANDIDATE_ALPHA.md`.
   - Market breadth/sectors (`market.json`), position prices (`prices.json` — **empty `{}` when the portfolio holds nothing**, which is normal), IV sentiment (`iv_sentiment.json`).
2. **Phase 2 — ANALYSIS** (LLM). `llm_client.py` sends the assembled prompt (system prompt = `agents/ANALYST.md` + `LEARNINGS.md`) to the model with a tool-use loop (`web_search` via Tavily, `web_fetch`). Provider modes: `anthropic` (Claude only), `openai` (GPT only), `hybrid` (Claude research pass → GPT final decision). Returns structured buy/hold/sell decisions.
3. **Phase 3 — EXECUTION** (pure Python). `position_manager.py` applies decisions to the simulated portfolio in `tracking/`.
4. **Phase 4 — VALIDATION + COMMIT**. `validator.py` checks all output artifacts exist and are consistent; `contracts.py` defines the per-phase input/output contracts and fails loudly on violations. On success, results are git-committed (unless `--no-commit`).

### Run directory layout (read `scripts/run_paths.py` before touching run I/O)

```
runs/<YYYY-MM-DD>/<slot>/input/     # phase-1 JSON artifacts (source data)
runs/<YYYY-MM-DD>/<slot>/output/    # report.md, candidates.md, decisions
```

- `slot` is `noon` (clock hour < 13) or `afternoon` (>= 13), auto-derived at start; override with `--slot`. The two daily runs write to separate slots so neither clobbers the other.
- **Legacy runs** (pre-slot) live at `runs/<date>/input|output` with no slot subdir and are treated as an implicit `afternoon`.
- **Gotcha:** `"afternoon" < "noon"` alphabetically — never sort runs by slot name. Sort by `run_started_at` from each run's `manifest.json`.
- Large regenerable per-run files (`phase1.json`, `prompt.md`, `response.json`) are git-ignored; `input/`, `output/`, and `log.json` are tracked.

## The audit layer (`scripts/doctor.py`, `audit/`)

Runs 20 min after each pipeline slot as **`com.bz.stock-doctor`** — a separate
launchd job on purpose: a pipeline that dies hard must not take down the report
saying so. Writes `runs/<date>/<slot>/audit-result.{md,json}` beside the
manifest it judges, plus the standing view at `audit/OPEN.md`.

Findings are one of two kinds, and the split is the whole design:

- **invariant** — internally contradictory in a way no market condition can
  produce (a `newPositions` entry the snapshot doesn't hold; a gate reporting
  failure under a `status: success`). First occurrence is already a defect.
- **env** — the outside world misbehaved. Weather until `PROMOTE_AFTER = 3`
  consecutive occurrences, then treated as a design gap. Recurrence is *derived*
  by re-reading prior `audit-result.json`, never stored in a ledger.

Two rules to keep intact when editing:

1. **It never writes `tracking/`.** Detection only (D12). A system that repairs
   its own trade records produces numbers nobody can audit.
2. **Checks stay independent of the writers they audit.** `newPositions` is
   written from the execution outcome (`_not_opened`) rather than from
   `positions.json` precisely so the doctor's snapshot comparison isn't a
   tautology. Don't "simplify" either side to share a source.

A check that can't run is reported as **skipped with its reason** — silently
passing on a missing artifact is the exact lie this layer exists to catch.
`audit/ACCEPTED.md` is the only human-authored input (doctor reads, never
writes); entries are per *instance id*, so accepting history doesn't mute a
fresh recurrence. Historical runs are judged against `ARTIFACT_EPOCHS`, not
today's contract.

## State & the self-improvement loop

- **`tracking/`** is the live portfolio state: `positions.json` (active), `closed/` (exited), `portfolio_config.json`, `hypotheses.json`. Schema in `TRACKER_SCHEMA.md`.
- **`scripts/rules/`** — the mechanical risk engine. Each `check_*.py` is a standalone script that reads `positions.json` on **stdin** and emits violations on **stdout**; `run_rules.py` runs them all. Rules encode hard-won sell discipline (time-decay, overextended-entry, stop-proximity, breakout-failure, volume, IV filter). Each rule file's docstring carries its own track record and evolution notes tied to `LEARNINGS.md` entries — preserve that history when editing.
- **`LEARNINGS.md`** (large, ~188KB) is the accumulated trading post-mortem, read into the LLM prompt every run and updated after. `agents/*.md` (ANALYST, RESEARCHER, TRACKER, EVOLVER, ORCHESTRATOR, DAILY_AUDIT, WEEKLY_AUDIT) are the prompt specs for each role. Changes to strategy belong in these markdown specs, not hardcoded in Python.

## Data sources & fallbacks

Price history (`pricedb.py`) fetches through a three-provider chain — **iFinD primary → AkShare → Sina** (doctrine set 2026-08-25 when the paid iFinD seat landed; supersedes the 2026-08-01 "AkShare → Sina" doctrine that followed the eastmoney IP-throttle outage). The free chain is deliberately KEPT behind iFinD rather than retired: iFinD is a single commercial dependency whose token can lapse, and `db_health` gates the pipeline, so an outage with no fallback would hard-stop the run. eastmoney direct/clist, baostock and tushare remain RETIRED for price bars — do not re-add them, their fetchers survive only as internal helpers for factor derivation and forensics.

When adding data fetching, follow the "try sources in order, degrade gracefully, never hard-fail the run" pattern, and make every degradation LOUD: `db_health` (staleness/partial/spot-audit) rides into the prompt, the report banner, and the phase-1 contract.

**iFinD specifics** (`scripts/ifind_client.py`; full API reference in `docs/IFIND_EVAL/IFIND_API_GUIDE.md`, evaluation in `FINDINGS.md`). Auth is `IFIND_REFRESH_TOKEN` → a ~7-day access token cached at `data/ifind_token.json` (git-ignored, 0600). The client imports nothing from this project on purpose, so `pricedb` and `data_collector` can both depend on it without a cycle. Three traps are load-bearing and all fail *silently*:

- `date_sequence` takes `indipara` (list of dicts), **not** `indicators`.
- `ths_the_sw_industry_stock` params are `[level, date]` — **level first**. Reversed, it returns `""` with `errorcode: 0`, not an error.
- **Volume units differ per endpoint**: `cmd_history_quotation` and `high_frequency` return 股 (÷100 to store 手); `real_time_quotation` returns 手 already. Getting this wrong is a silent 100× error.

Real-time position prices, market breadth, sector ranking and index quotes all try iFinD first and fall back to the Sina paths (`data_collector.py`); breadth and sectors share one universe pull so they can't disagree. `input/ifind_candidates.json` holds iwencai natural-language screens as a **display-only second opinion** — it does NOT feed the hard RPS/MA gate, same posture as `regime.json`.
