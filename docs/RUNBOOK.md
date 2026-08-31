# RUNBOOK — operating the pipeline by hand

For the human at the keyboard. What runs when, how to trigger it yourself, how
to know it worked, and what to do when it didn't. (`CLAUDE.md` is the agent's
reference; this is yours. If they disagree, one of them is a bug — say so.)

Everything below assumes:

```bash
cd ~/Work/Personal/stock-analysis
source .venv/bin/activate        # always — bare `python` is never right here
```

## What runs on its own

| when (CST, weekdays) | job | what |
|---|---|---|
| 11:35 | `com.bz.stock-pipeline` | noon run (intraday, unsettled data) |
| 15:05 | `com.bz.stock-pipeline` | afternoon run (post-close, settled) |
| 11:55 / 15:25 | `com.bz.stock-doctor` | audits the run 20 min after each slot |

Both are launchd jobs (`ops/launchd/*.plist`), logging to
`data/launchd/pipeline.log` and `doctor.log`. **The laptop must be awake and
preferably on power** — lid closed on battery means the job is deferred until
wake, and a deferred pipeline + doctor fire *simultaneously*, which produces a
run with no audit (observed 2026-08-26).

```bash
launchctl list | grep com.bz.stock     # are the jobs loaded?
tail -f data/launchd/pipeline.log      # watch a scheduled run live
```

## Triggering a run yourself

```bash
python3 scripts/run_daily.py --run                    # the full pipeline, ~5 min
python3 scripts/run_daily.py --run --no-commit        # ... without the git commit
python3 scripts/run_daily.py --run --slot noon        # force a slot
python3 scripts/run_daily.py --phase1                 # data collection only, no LLM
python3 scripts/run_daily.py --list-runs              # history with status
```

A manual `--run` is *identical* to the scheduled one — same phases, same gates,
same commit. Re-running a slot is safe by design: decisions recompute on
current data, HOLDs are idempotent, and the gates fail closed, so a broken run
leaves the portfolio untouched.

### The three things to know first

1. **The slot comes from the clock.** Before 13:00 → `noon`; after → `afternoon`
   (`run_paths.resolve_slot`). A manual run at 13:30 writes
   `runs/<date>/afternoon/` — and the 15:05 scheduled job will then **overwrite
   that slot**. If you just want to watch it work, run after ~15:10, or let the
   schedule do it.

2. **There is no sandbox.** `--run` and even `--phase1` refresh
   `tracking/positions.json` with live marks — that's the real book. `tracking/`
   is git-committed on every successful run, so any state is recoverable, but
   don't run "just to see" while a scheduled run is minutes away.

3. **Market hours matter.** During the session (9:30–11:30, 13:00–15:00) prices
   are intraday marks and the settled-bar snapshot refuses to write — this is
   correct behaviour, not an error. Post-close runs are the authoritative ones.

## How to know it worked

In order of authority:

```bash
python3 scripts/run_daily.py --list-runs               # status column
cat runs/<date>/<slot>/manifest.json                   # phases, gates, timing
cat runs/<date>/<slot>/audit-result.md                 # the doctor's verdict
python3 scripts/doctor.py                              # re-audit latest now
open site/index.html                                   # equity curve + banner
```

A good run: manifest `status: success, exit_code: 0`, all three gates
`passed: true`, audit `✅ 无发现`. The human-readable output is
`runs/<date>/<slot>/output/report.md`; decisions land in
`output/daily_summary.json`; the book is `tracking/positions.json`.

**Trust the audit over the exit code.** A run can exit 0 while an artifact is
quietly wrong — that's the whole reason the doctor exists. Standing problems
accumulate in `audit/OPEN.md`.

Known cosmetic lie (open bug): the noon audit may say a skipped check is
because "run predates the writer" — actually the snapshot just declines while
the session is open.

## When something is broken

```bash
python3 scripts/doctor.py --open               # what is broken right now, folded
python3 scripts/doctor.py --date D --slot S    # audit one run
python3 scripts/doctor.py --since 2026-08-01   # sweep a range
```

Price data problems (the usual suspect — check `db_health` warnings in the
report banner first):

```bash
python3 scripts/pricedb.py status              # DB stats at a glance
python3 scripts/pricedb.py update              # incremental catch-up (also
                                               #   reconciles adjustment factors)
python3 scripts/pricedb.py factors verify      # exit 1 = factor table broken
python3 scripts/pricedb.py factors heal        # repair a factor gap, then:
python3 scripts/pricedb.py rps                 #   recompute RPS (heal invalidates it)
python3 scripts/pricedb.py repair --beg D --end D   # refill a partial day
```

Portfolio state:

```bash
python3 scripts/run_rules.py --human           # mechanical risk checks, read-only
python3 scripts/run_daily.py --reset-to DATE   # roll the book back to end of DATE
                                               #   (destructive — the audit trail
                                               #   keeps the old commits, but ask
                                               #   yourself twice)
```

Failure patterns seen in production, fastest diagnosis first:

| symptom | first check | usual cause |
|---|---|---|
| run failed at Gate 1, "all sources down" | `nslookup hq.sinajs.cn` | DNS/network outage — data, not code. Re-run when it resolves. |
| "Pricedb is stale — refusing" | `pricedb.py status` | update couldn't fetch; run `update` by hand, then re-run |
| run dir exists, no manifest, no audit | `tail data/launchd/pipeline.log` | died before writing the manifest, or still running — check `pgrep -f run_daily` |
| push failed | — | transient; the commit is local and the next run pushes it |
| report banner warns "adj factors lag prices" | `pricedb.py factors verify` | factor sync missed — `factors heal`, then `rps` |

## Where everything lives

```
runs/<date>/<slot>/input/     phase-1 JSON artifacts (what the model saw)
runs/<date>/<slot>/output/    report.md, candidates.md, daily_summary.json
runs/<date>/<slot>/manifest.json, audit-result.md
tracking/                     the live book (positions, closed/, hypotheses)
audit/OPEN.md                 standing problems, folded by cause
data/pricedb/                 SQLite price DB (git-ignored, rebuildable)
data/launchd/*.log            scheduler logs
site/index.html               derived dashboard — regenerate, never commit
agents/*.md                   the strategy itself (ANALYST.md is the one to read)
```

One structural rule worth knowing when reading `runs/`: **never sort by slot
name** — `"afternoon" < "noon"` alphabetically. Sort by `run_started_at` from
each manifest.
