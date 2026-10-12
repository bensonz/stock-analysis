# Event inbox — progress log

## 2026-10-12

- Worktree `/Users/bz/Work/Personal/stock-analysis-event-inbox`, branch
  `feat/event-inbox` (live repo's 15:05 run `git add`s the whole tree).
- Probed the source: 46 daily calls take ~10 s. `重要性` goes up to **4**
  (midterm is 4, not 3). 18/46 dates raised `KeyError 'public_date'`: read the
  akshare source — that is akshare failing on an EMPTY item list (no events
  listed yet for that day), not a network error. Counted separately as
  "empty days"; other exceptions count as fetch errors.
- `akshare.macro_info_ws` calls `requests.get` with no timeout → wrapped in
  `pricedb.providers._run_with_timeout` + an overall deadline.
- Stages 1+2 landed as ONE commit: the CLI lives in the same module as the
  core, and CLAUDE.md/RUNBOOK must ship with the CLI, so splitting would have
  meant committing an artificial CLI-less module first.
- `tests/test_event_inbox.py`: 26 unit (fake fetch, tmp paths) + 1 integration
  (real API, passed). Root conftest LIVE_STATE now also fingerprints
  `tracking/event_inbox.md` and `tracking/event_inbox_ledger.json`.
- Stage 3: wired into `phase1_collect` just before the event-calendar block.
  `tests/test_strategy_pool_observability.py` runs the real phase1_collect —
  it would have hit the network and written the live tracking/ inbox, so it
  now stubs `event_inbox` in sys.modules (same pattern as fetch_iv_sentiment)
  and is parametrized to prove a raising inbox costs only its own artifact.
- The worktree has no price DB (git-ignored); `data/pricedb` is a symlink to
  the main repo's for the test suite. Untracked, never committed.
