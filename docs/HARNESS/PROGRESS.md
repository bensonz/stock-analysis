# Harness progress log

## 2026-08-19

**Archaeology.** Swept every run for "report claimed a position that never opened, or
apply errored": **12 runs**. Seven had a SKIP explaining it (invisible before the
08-17 Gate-3 check); **four vanished with no SKIP and no ERROR** — 02-13 (300373),
02-25 (600499), 02-26 (600096), 03-11 (002497/600096/603191). 03-11 also threw
`ERROR OPEN 002497: unsupported operand type(s) for //: 'float'`.

Causal chain worth remembering: 02-13's ghost 300373 produced
`ERROR HOLD 300373: Position file not found` on **03-03**, three weeks later. Neither
end was noticed.

**Why none of it surfaced.** 116/123 runs (**94%**) were `degraded`; 120 of those on
one soft warn, `missing watchlist` — a check for a V1 response field that V2 replaced
months ago and that must not be present. A dead check painted 94% of history abnormal,
so nothing could stand out.

**Same disease one layer up.** The openclaw cron job reports 64 errors in 203 runs, 60
of them `cron: job execution timed out`, including every run 08-14 → 08-19 — all of
which succeeded. Pipeline wall-clock is p50 207s / p90 392s / p99 720s, and only 4% of
136 runs exceed the 600s timeout. The timeout bounds the *agent session*, not the work.

**Shipped**: Stage 1 (`6ab9377`). Dead check deleted; `gate.note()` added; rule
findings no longer set status; a rule that fails to run still degrades. 14 of the last
15 runs recompute `degraded → success`; the one still flagged is legitimately stale.

**Next**: Stage 2 doctor.py, starting with the log/state independence audit — if
Phase 3 writes both from one object, replay proves nothing and the design changes.

## 2026-08-19 (later) — plan review

Self-review before building. Three material findings, all folded into the plan:

1. **2a replay was unimplementable as written** (verified): all 365 history entries
   across 63 positions carry only {date, slot, price, change_pct, action, note} —
   no shares/stop/capital. 9 Feb–Mar positions have no history[] at all — exactly
   the ghost era. Split 2a into schema-widening (ships first, time-sensitive) /
   action↔history reconciliation (possible today) / full replay post-epoch.
2. **Heartbeat blind spot**: same-machine watchers can't see machine-off — plausibly
   the real cause of the 33pp gap. Added D7 off-machine dead-man's switch (GitHub
   Action over run commits).
3. **Ordering inverted cost/benefit**: heartbeat is hours and covers the most
   expensive class; doctor is days. Execution order revised.

Also: drift gets a mandatory observe-only burn-in; sweep findings persist until
acknowledged (D8); the 7 permanently-red tests flagged as our own normalized
deviance; 300373 oddity logged (closed/ has the "ghost" with entryDate 02-13).

## 2026-08-19 (afternoon) — 2a-i shipped, scheduler swapped

- **2a-i** (`4bfacb6`): OPEN events record shares/stop/allocatedCapital, SELL
  records shares, RAISE_STOP records old→RESULTING stop (refused lowers marked
  `stop_not_raised`, never recorded as applied). `HISTORY_SCHEMA_EPOCH =
  2026-08-19` importable from position_manager. Today's afternoon run is the
  first recorded in replayable form.
- **Scheduler**: owner removed the openclaw cron; launchd agent
  `com.bz.stock-pipeline` installed 15:06, verified loaded, wrapper smoke-tested
  (--list-runs through the venv). First scheduled fire: 15:35 same day.
- Also same day, before these: data cleanup (`e512d98`) — see commit for the
  census; the cleanup itself caught a test leaking synthetic trades into the
  live closed/ (CLOSED_DIR import-binding), guard widened to all position files.
