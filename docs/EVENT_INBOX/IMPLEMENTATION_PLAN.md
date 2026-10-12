# Event inbox — implementation plan

Problem: `tracking/events.json` is hand-curated only and was last edited
2026-08-14. It misses events (US midterm 2026-11-03). Owner decision: an
automated source fills an INBOX of candidates; the owner ticks a markdown
checklist; ticked items are promoted into `events.json`.

Flow:

```
akshare.macro_info_ws (华尔街见闻, imp>=4, 45 days)
        │ refresh: drop past / already-in-events.json / already-decided
        ▼
tracking/event_inbox.md      ← owner edits: [x] keep  [-] skip  impact/direction/date/tz/kind/note
        │ promote
        ├─[x]→ tracking/events.json (+ inbox_id)  ──► event_calendar.upcoming() ──► report / prompt
        └─[x]/[-] → tracking/event_inbox_ledger.json (never re-proposed)
```

## Stage 1: Inbox core (fetch, parse/render, dedupe, refresh)

**Goal**: `scripts/event_inbox.py` can fetch candidates, render the inbox,
parse it back, and refresh it without losing owner edits.
**Success Criteria**: round-trip preserves marks/edits; dedupe by `inbox_id`
and fuzzy rule; ledger blocks return; past items dropped; per-date fetch
failure counted, not fatal.
**Tests**: `tests/test_event_inbox.py` (all tmp paths, fake fetch).
**Status**: Complete

## Stage 2: Promote + ledger + CLI + docs

**Goal**: `promote` moves `[x]` into events.json with the existing schema plus
`inbox_id`; `[x]`/`[-]` go to the ledger; CLI `refresh|promote|status`.
CLAUDE.md "Common commands" and docs/RUNBOOK.md updated in the same commit.
**Success Criteria**: promoted event shows in `event_calendar.upcoming()` with
the right A-share impact date; invalid edits are refused loudly and stay in
the inbox.
**Tests**: promote schema; upcoming() impact date; invalid field kept; CLI status.
**Status**: Complete

## Stage 3: Pipeline wiring

**Goal**: `run_daily.py` phase 1 runs promote → refresh before the
event-calendar block; never fails the run; loud `[event-inbox]` line; writes
`input/event_inbox.json` (the run's own record, read by the doctor).
**Success Criteria**: an exception inside the inbox step is caught and printed.
**Tests**: `pipeline_step` records step failures (test_event_inbox); phase1_collect test parametrized inbox-ok / inbox-raises (test_strategy_pool_observability).
**Status**: Complete

## Stage 4: Doctor check

**Goal**: `check_event_inbox_undecided` flags undecided items whose A-share
impact date is within 7 days of the run date. Reads the run's
`input/event_inbox.json` only.
**Success Criteria**: env kind, never promotes to "code change"; skipped with
reason on runs that predate the artifact.
**Tests**: tests/test_doctor.py — T-7 due / T-8 not / past ignored; 6 consecutive slots never streak to code; skip when artifact absent; skip carries step error; window constant pinned to event_inbox.
**Status**: Complete

## Stage 5: End-to-end demo (real network)

**Goal**: real `refresh`; tick only the US midterm (high, two_sided, note on
2026-11-10 tariff-truce deadline); `promote`; `upcoming(days=30)` shows it on
2026-11-04. Separate data commit.
**Status**: Complete

---

# AI triage (owner decision 2026-10-12: "AI decides, owner can overrule")

The owner should not have to open the inbox. Each NEW undecided item gets one
LLM judgement (keep/skip, impact, direction, one-line reason), applied at once.
AI-decided items stay in the inbox (🤖 + `ai:` line) until their impact date,
so the owner can flip them; the owner's version always wins.

```
promote (owner marks + overrides of 🤖 items)
  → refresh (fetch; 🤖 items past impact date retire)
  → triage (new [ ] items without a ledger entry → 1 LLM call → apply)
  → event_calendar read (same run's report sees AI keeps)
```

## Stage 6: AI triage + owner override

**Goal**: `scripts/event_triage.py` (prompt from `agents/EVENT_TRIAGE.md`, one
no-tools call through llm_client's provider, extract `decisions`);
`event_inbox.triage()` validates per item and applies; `promote()` detects owner
overrides against the ledger's AI snapshot; `pipeline_step` runs
promote → refresh → triage. CLI `triage`. CLAUDE.md + RUNBOOK in the same commit.
**Success Criteria**: AI only judges (no new events, no name/date/tz change);
each item judged once; failures stay undecided and retry; owner marks win,
before or after the AI ran; LLM failure never fails the run.
**Tests**: tests/test_event_inbox.py — valid applied; invalid/unknown/missing;
once; owner-first wins; keep→[-] removes; skip→[x] promotes; impact edit updates;
untick reopens; 🤖 removal is no override; retires after impact date; LLM
exception; prompt contents; call_model plumbing with a fake client.
**Status**: Complete

## Stage 7: Report marker

**Goal**: an AI-kept entry renders with 〔AI选入〕 in report.md's 未来事件窗口.
`event_calendar.upcoming()` passes `decided_by` through.
**Tests**: test_event_calendar — marker rendered for decided_by=ai only.
**Status**: Complete

## Stage 8: Doctor + status + weekly audit

**Goal**: doctor env finding when the run's `input/event_inbox.json` records a
triage error (call failed or items left undecided by the AI); `status` shows AI
stats (kept/skipped/high/overrides); WEEKLY_AUDIT step to review AI decisions.
**Tests**: test_doctor — finding on error, on invalid items, none on clean
triage, skip on old runs; test_event_inbox — status AI stats.
**Status**: Not Started

## Stage 9: Live triage

**Goal**: one real call on the 22 undecided items in the worktree's inbox;
decisions table reported; data commit (inbox, ledger, events.json).
**Status**: Not Started
