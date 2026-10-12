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
- Stage 4: `check_event_inbox_undecided` (env, per-run id — see D8). The
  window is a local constant `INBOX_REMIND_DAYS`, not imported: event_inbox
  imports akshare + pricedb, and the doctor must survive those breaking. A
  test pins the two constants equal.
- First live refresh: 96 candidates (imp>=3), 0 fetch errors, 18 empty days.
  It dropped 中国9月CPI同比 as a fuzzy "duplicate" of the hand-written US CPI
  → fix: fuzzy now needs the same tz (D5). Second refresh: 96 fetched, 92
  new, 4 fuzzy dups (美国9月CPI/核心CPI vs the hand CPI entry; FOMC 上限/下限
  vs FOMC利率决议 10-28 — all genuine), 0 errors, 18 empty days.
- 48 of those land inside the 7-day doctor window → the doctor check now
  emits ONE finding per run listing all due items (D11), not one per item.
- Demo: ticked only the midterm ([x], high, two_sided, kind political, note
  on the 2026-11-10 tariff-truce deadline), `promote` → events.json +1 with
  inbox_id `wscn-20261103-8615302d`; `upcoming(days=30)` lists it at
  2026-11-04 (T-23). Ledger has 1 keep. 91 items left undecided for the owner.
- Full suite: 976 passed, 13 skipped (integration).

## 2026-10-12 (later) — AI triage

- Worktree `/Users/bz/Work/Personal/stock-analysis-event-triage`, branch
  `feat/event-triage` from master 5e19ea6. `data/pricedb` symlinked for tests
  (untracked: the `.gitignore` rule `data/pricedb/` does not match a symlink,
  so it shows as `??` — never `git add -A` here).
- Provider check: from the main repo `.env`, `LLM_PROVIDER` → openai,
  `OPENAI_MODEL=deepseek-v4-pro` (label "DeepSeek V4 Pro"), base URL
  api.deepseek.com. The worktree has no `.env`, so llm_client falls back to
  defaults there — a real call from the worktree needs the main `.env`.
- Stage 6: `scripts/event_triage.py` + `agents/EVENT_TRIAGE.md`;
  `event_inbox.triage()`, override-aware `promote()`, `ai_retired` in refresh,
  `pipeline_step` promote → refresh → triage, CLI `triage`. The old
  `test_pipeline_step_*` tests would have reached the real LLM (KR CPI is a new
  undecided item) — an autouse fixture now makes any real call fail the test.
  First spec draft used the real midterm id as its JSON example — it showed up in
  every prompt (caught by a test asserting the id was NOT sent); now fake ids.
- Full suite: 1003 passed, 13 skipped (baseline 977 + 26 new).
- Stage 7: `event_calendar.upcoming()` now copies `decided_by`; report.md's
  未来事件窗口 line gets 〔AI选入〕 after the name for AI keeps only. The Phase-2
  prompt section and the site are unchanged (kept minimal).
