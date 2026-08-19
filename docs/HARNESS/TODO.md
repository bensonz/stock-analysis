# Harness TODO

## Stage 1 — signal restoration ✅ (`6ab9377`)
- [x] Delete the dead V1 `watchlist` gate check (120x false alarm)
- [x] Add `gate.note()` severity; rule findings no longer set run status
- [x] A rule that fails to *run* still degrades
- [x] Tests pin all three severities
- [ ] Backfill: recompute status on the 123 historical manifests, or leave them and
      note that pre-08-19 statuses are not comparable  ← decide before doctor reads them

## Stage 2 — doctor.py
- [ ] **2a-i FIRST, TIME-SENSITIVE**: widen history[] schema — OPEN records
      shares/stop/allocatedCapital, RAISE_STOP records old_stop/new_stop, SELL records
      shares/exit_price. Replay coverage starts the day this ships.
      (Review 08-19 verified current entries carry NONE of these fields, 365/365.)
- [x] ~~Audit log/state independence~~ — resolved by review: separate call sites, both
      downstream of one decisions dict; reconciliation proves both writes happened,
      which is what the ghosts violated
- [ ] `replay_position()` — from the 2a-i epoch forward ONLY; checker must know the
      epoch (9 Feb–Mar positions have no history[] at all — zero spurious findings on
      pre-epoch data is part of the acceptance test)
- [ ] Both-direction action↔history reconciliation
- [ ] Conservation: equity identity, Δequity identity, realised identity
- [ ] Cross-artifact: positions.json ↔ tracking/*.json ↔ snapshot ↔ report claims
- [ ] Manifest presence per run dir (21 runs currently have none)
- [ ] History sweep mode (`--since DATE`), not just present tense
- [ ] Known-bad fixture per check (D4)
- [ ] Validation: reproduces all 12 known incidents, zero spurious findings
- [ ] Wire into run_daily (report section, per D1) + site banner

## Stage 3 — drift + fail-loud
- [ ] Trailing-20 structural comparison
- [ ] Sweep for bare excepts / plausible defaults on load-bearing paths
- [ ] Decide which are real bugs vs intentional degradation

## Stage 4 — scheduling
- [x] launchd plist (11:35 / 15:05 CST weekdays — owner moved 15:35→15:05 on 08-19, restoring symmetry with the +5min noon slot; 15:35 was inherited from openclaw, never chosen) — `com.bz.stock-pipeline`,
      source of truth in ops/launchd/, wrapper scripts/run_scheduled.sh, logs in
      data/launchd/ (git-ignored). Installed + smoke-tested 2026-08-19 15:06.
      StartCalendarInterval coalesces missed events on wake; powered-off machine
      runs nothing → D7
- [x] Openclaw pipeline cron removed by owner 2026-08-19 (launchd is sole scheduler)
- [ ] Heartbeat: expected-slot vs landed-manifest, independent of the invoker
- [ ] Decide heartbeat notification channel
- [ ] D7 off-machine dead-man's switch: scheduled GitHub Action checks a run commit
      landed for the expected slot; verify the pipeline PUSHES (not just commits) —
      if it only commits locally, the Action measures push staleness, which still
      catches a dark fortnight

## Stage 5 — daily agent sweep
- [ ] Sweep prompt/spec (standing question + explicit coverage reporting)
- [ ] `docs/audits/daily/YYYY-MM-DD.md` format
- [ ] Schedule after the afternoon run
- [ ] Retention/index so the files stay readable in bulk

## Stage 1 leftovers (from review)
- [ ] The 7 permanently-red tests are normalized deviance in our own quality gate —
      "7 failed" is the new "degraded". Fix, or mark xfail with a written reason each,
      so a fresh red actually stands out.

## 2026-08-19 night — first launchd fire failed (found same evening)
- [ ] **Preflight failures leave no trace**: run_daily exited 2 in preflight
      (pricedb update hard-failed), runs/2026-08-19/afternoon/ has empty
      input/output dirs — no manifest, no log.json. Only data/launchd/pipeline.log
      records it. Fix: write a minimal manifest on preflight failure (status
      failed + provider errors), so manifest-absence always means "never fired".
- [ ] **Fallback starvation**: cmd_update checks ONE shared budget before each
      provider — a throttled akshare consumed all 300s (5566 per-stock calls,
      0 rows each) and sina was SKIPPED, not tried. Violates the akshare→sina
      degrade-gracefully doctrine. Fix options: per-provider budget slice, or
      abort the primary after N consecutive empty responses (throttle signature).
- [ ] eastmoney throttle ESCALATED: 15:40 = empty responses (0 rows), 23:20 =
      connection refused. Sina healthy (0.7s/call). DB healed 08-19 via
      PRICEDB_UPDATE_BUDGET=7200 update (sina gets the remainder).

## Known bugs found on 2026-08-19, not yet fixed
- [ ] 4 unexplained ghost positions: 02-13 (300373), 02-25 (600499), 02-26 (600096),
      03-11 (002497/600096/603191) — root cause never established. Review twist:
      closed/ HAS a 300373 file with entryDate 02-13, so ghosts eventually existed
      without apply ever logging the OPEN
- [ ] `2026-03-11`: `ERROR OPEN 002497: unsupported operand type(s) for //: 'float'`
      — a TypeError in sizing; is it still reachable?
- [ ] 21 run dirs have no manifest at all
- [ ] `runs/*/manifest.json` is written *after* the commit, so it never lands in its
      own run's commit (cosmetic, but it is why failed runs' manifests go uncommitted)
