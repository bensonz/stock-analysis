# Harness TODO

## Stage 1 — signal restoration ✅ (`6ab9377`)
- [x] Delete the dead V1 `watchlist` gate check (120x false alarm)
- [x] Add `gate.note()` severity; rule findings no longer set run status
- [x] A rule that fails to *run* still degrades
- [x] Tests pin all three severities
- [ ] Backfill: recompute status on the 123 historical manifests, or leave them and
      note that pre-08-19 statuses are not comparable  ← decide before doctor reads them

## Stage 2 — doctor.py
- [ ] **FIRST**: audit whether `log.json` actions and `tracking/*.json` history are
      written independently (if not, replay is decorative — see plan 2a precondition)
- [ ] `replay_position()` — rebuild shares/currentStop/allocatedCapital from history[]
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
- [ ] launchd plist for the pipeline (11:35 / 15:35 Asia/Shanghai, weekdays)
- [ ] Retire the openclaw pipeline cron job (keep the agent for the sweep)
- [ ] Heartbeat: expected-slot vs landed-manifest, independent of the invoker
- [ ] Decide heartbeat notification channel

## Stage 5 — daily agent sweep
- [ ] Sweep prompt/spec (standing question + explicit coverage reporting)
- [ ] `docs/audits/daily/YYYY-MM-DD.md` format
- [ ] Schedule after the afternoon run
- [ ] Retention/index so the files stay readable in bulk

## Known bugs found on 2026-08-19, not yet fixed
- [ ] 4 unexplained ghost positions: 02-13 (300373), 02-25 (600499), 02-26 (600096),
      03-11 (002497/600096/603191) — root cause never established
- [ ] `2026-03-11`: `ERROR OPEN 002497: unsupported operand type(s) for //: 'float'`
      — a TypeError in sizing; is it still reachable?
- [ ] 21 run dirs have no manifest at all
- [ ] `runs/*/manifest.json` is written *after* the commit, so it never lands in its
      own run's commit (cosmetic, but it is why failed runs' manifests go uncommitted)
