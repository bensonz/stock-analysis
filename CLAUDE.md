# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An automated daily A-share (Chinese stock) momentum-analysis pipeline. Pure-Python data collection feeds an LLM that makes buy/hold/sell decisions, which are then applied to a simulated portfolio and committed to git. It runs **twice per trading day** (~11:35 "noon" intraday and ~15:35 "afternoon" post-close).

The trading philosophy lives in `agents/ANALYST.md` (momentum-first: buy strength via RPS, follow hot sectors, cut losers fast). Read it before touching screening thresholds or decision logic — the magic numbers in the code (RPS 75-95%, `dist_ma5>6%`, breadth 1.5:1, `f10>=30` panic gate) are all specified there and must stay in sync.

## Environment & setup

- Python venv at `.venv` — **activate it first**, then use `python3` (never bare `python`): `source .venv/bin/activate`
- Deps: `pip install -r requirements.txt` (akshare, anthropic, openai, baostock, tushare, pycryptodome, httpx, requests)
- Secrets in `.env` (git-ignored): `TUSHARE_TOKEN`, `TAVILY_API_KEY` (web search), and OpenAI-compatible `OPENAI_*` / `LLM_PROVIDER`. `llm_client.py` also reads env from `~/.claude/settings.json`.
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

# Rules engine (mechanical sell/risk checks over current positions)
python3 scripts/run_rules.py --human

# IV sentiment (needs options-learn backend on :8000)
python3 scripts/fetch_iv_sentiment.py --human
```

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
   - RPS + MA screening from the local price DB via `rps_calculator.py`. **Upstream hard gate:** a stock must have `rps120>=85, rps250>=85, rps60>=70` AND MA alignment `MA20 > MA120 > MA250` to survive (`data_collector.py`). This is the real tradeable filter — the candidates report is just display on top of it.
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

## State & the self-improvement loop

- **`tracking/`** is the live portfolio state: `positions.json` (active), `closed/` (exited), `portfolio_config.json`, `hypotheses.json`. Schema in `TRACKER_SCHEMA.md`.
- **`scripts/rules/`** — the mechanical risk engine. Each `check_*.py` is a standalone script that reads `positions.json` on **stdin** and emits violations on **stdout**; `run_rules.py` runs them all. Rules encode hard-won sell discipline (time-decay, overextended-entry, stop-proximity, breakout-failure, volume, IV filter). Each rule file's docstring carries its own track record and evolution notes tied to `LEARNINGS.md` entries — preserve that history when editing.
- **`LEARNINGS.md`** (large, ~188KB) is the accumulated trading post-mortem, read into the LLM prompt every run and updated after. `agents/*.md` (ANALYST, RESEARCHER, TRACKER, EVOLVER, ORCHESTRATOR, DAILY_AUDIT, WEEKLY_AUDIT) are the prompt specs for each role. Changes to strategy belong in these markdown specs, not hardcoded in Python.

## Data sources & fallbacks

Price history (`pricedb.py`) fetches through a fallback chain — Tushare Pro → Eastmoney direct → AkShare → BaoStock — because any single source flakes. When adding data fetching, follow this "try sources in order, degrade gracefully, never hard-fail the run" pattern rather than assuming one API is up. Real-time position prices use Sina Finance with kline fallbacks (`data_collector.py`).
