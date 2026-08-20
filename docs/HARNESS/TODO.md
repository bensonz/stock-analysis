# Harness TODO

> Keep this honest. On 2026-08-20 three shipped items were still showing as
> unchecked — including one labelled FIRST, TIME-SENSITIVE — which makes the
> file exactly the kind of lying status signal Stage 1 existed to kill. Tick
> items in the same commit that ships them.

## Stage 1 — signal restoration ✅ (`6ab9377`)
- [x] Delete the dead V1 `watchlist` gate check (120x false alarm)
- [x] Add `gate.note()` severity; rule findings no longer set run status
- [x] A rule that fails to *run* still degrades
- [x] Tests pin all three severities
- [x] **Decided (D9)**: historical manifest statuses are MARKED, not recomputed.
      `contracts.GATE_SEVERITY_EPOCH = "2026-08-19"`; the 147 pre-epoch files
      (115 degraded / 8 failed / 23 success) stay untouched. Doctor and any
      health-over-time comparison MUST split on the epoch and say so — reading
      pre-epoch status as comparable is reading noise.

## Stage 2 — doctor.py
- [x] **2a-i schema widening — SHIPPED 2026-08-19 (`4bfacb6`)**. OPEN records
      shares/stop/allocatedCapital, SELL records shares, RAISE_STOP records
      old_stop → RESULTING stop (a refused lower is marked `stop_not_raised`,
      never recorded as applied). `HISTORY_SCHEMA_EPOCH = "2026-08-19"` is
      importable from position_manager — replay coverage starts there; earlier
      entries carry none of these fields and can never be replayed.
- [x] ~~Audit log/state independence~~ — resolved by review: separate call sites, both
      downstream of one decisions dict; reconciliation proves both writes happened,
      which is what the ghosts violated
- [ ] `replay_position()` — from the 2a-i epoch forward ONLY; checker must know the
      epoch (9 Feb–Mar positions have no history[] at all — zero spurious findings on
      pre-epoch data is part of the acceptance test)
- [ ] Both-direction action↔history reconciliation
- [ ] Conservation: equity identity, Δequity identity, realised identity
- [ ] Cross-artifact: positions.json ↔ tracking/*.json ↔ snapshot ↔ report claims
- [x] Manifest presence per run dir — 25 legacy manifests backfilled from their
      own log.json (`e512d98`, marked `backfilled`, gates explicitly empty ≠
      passed). Now 0 run dirs without one, pinned by
      tests/test_data_hygiene.py::test_every_run_dir_has_a_manifest
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

## Stage 5 — daily agent sweep  ← **NOTHING IS REVIEWING ANYTHING. This is the gap.**
> Verified 2026-08-20: `com.bz.stock-pipeline` is the only scheduled job;
> openclaw holds only two disabled jobs; no doctor.py, no sweep script, no
> docs/audits/daily/. Every bug found this week (ghost positions, limit band,
> dead-price screen) was caught by the owner's eye or by ad-hoc looking.
> Owner asked for this on 08-19 and it has not been built.
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

## 2026-08-20 morning — night recovery complete
- [x] DB healed for 08-19 (5,129 rows via sina, 0 failures; eastmoney dead)
- [x] factors verify OK (9 ex-div re-derived, 5,189 forward-filled)
- [x] Catch-up afternoon run: **success**, all gates passed, 4 HOLDs,
      committed + pushed (manual proxy push)
- [x] launchd push gap: run_daily now applies PUSH_PROXY (from
      run_scheduled.sh) ONLY to the git push subprocess; wrapper no longer
      exports proxy globally (would have routed LLM/data through Privoxy)

## 2026-08-20 — price-limit band was flat 10% for every board
- [x] Fixed: `market_rules.py` is now the single definition (main 10 / ChiNext+
      STAR 20 / BJ 30 / ST 5 on main board only); run_daily and backtest both
      import it. 成都先导 688222 at +13.17% had been refused as 涨停 while 7
      points inside STAR's 20% band.
- [ ] **Limit-down is still unenforced on the SELL path.** run_daily books an
      exit at whatever price it sees, so a 跌停 sale records a fill reality
      would not have given us — this flatters every stop-loss statistic and the
      exit ablation. `market_rules.at_limit_down()` exists and is unused.
      Behaviour change on live exits → needs an explicit decision, and the
      honest version also has to say what happens to the position afterwards
      (it stays open and keeps losing, which is what really happens).

## 2026-08-20 — screening measured extension against a DEAD price
- [x] **Fixed.** `fetch_ma_data` never attempted a live quote: it took the DB's
      newest *settled* close as the distance numerator, so during a session
      Rule 2b was tested against the PREVIOUS day's price. 688222 read
      dist_ma20 = +8.1% (compliant) while actually at +19.6% (a 7.6-point
      violation); the model wrote "MA距离全部合规" in good faith, and only the
      unrelated limit-band bug stopped the buy. Now: MAs from settled bars,
      distance from the live price, and on live-fetch failure the candidate is
      REJECTED with the reason logged (`screenable=False`, `screen_error`) —
      enforced at the open path, not just displayed.
- [x] Manifest is now written BEFORE the Phase-5 commit, so a run's manifest
      lands in its own commit ("manifest exists" and "commit exists" can no
      longer disagree — the signal D7 reads).
- [ ] Two artifacts disagreed and nothing reconciled them: candidates.md printed
      `❌ MA5` for 688222 while the model's thesis claimed all distances
      compliant. Worth a doctor check — display verdict vs decision rationale.
- [ ] Watch the first runs after this change: if live quotes are flaky the pool
      could shrink sharply. Rejections are logged as SKIP OPEN, so count them.

## 2026-08-20 night — snapshot writer built (BUILT, NOT WIRED)
- [x] `scripts/snapshot_bars.py` + `pricedb.py snapshot [--date --dry-run --force]`.
      Reads today's settled bar off Sina's REAL-TIME feed (hq.sinajs.cn) instead
      of the daily-kline archive (quotes.sina.cn), which is batch-built and did
      not finish publishing 08-20 until ~21:47. Batched ~100 codes/request:
      5,229 codes in ~30s vs ~1h of per-code kline calls, and no eastmoney.
      **Full-day validation vs the kline-sourced DB: 5,204 vs 5,204 rows,
      0 OHLC mismatches, volume off by exactly 1 lot on 4.2% (max 0.0164%),
      neither source held a stock the other missed.**
      Volume trap: feed reports 股, daily_prices stores 手 → floor(/100). An
      earlier 10-code check compared feed vs akshare kline (both shares) so it
      agreed — would have written every volume 100x too large.
      Refuses to run while the session is open (--force for testing only).
      17 tests incl. every reject guard.
- [x] **WIRED 2026-08-21**: run_daily preflight runs `pricedb.py snapshot`
      BEFORE `update`. Ordering matters — update can burn its whole 300s budget
      failing against dead akshare, and if it does, today's bar is already in.
      The command self-skips mid-session (exit 2), so the 11:35 slot naturally
      passes it by; only the close slot uses it. Outcome recorded on the
      preflight phase in the manifest, so a run says which path supplied the day.
- [x] Settle guard added: lines stamped before 15:00 are rejected. The closing
      auction runs 14:57-15:00 and the run fires at 15:05, so without this the
      "close" could be the last pre-auction print. Re-validated at full scale:
      still 5,204 bars, 0 OHLC mismatches, 0 stocks lost — every legitimate
      line was already stamped >= 15:00.
- [ ] Daily cross-check: once the archive publishes overnight, compare it
      against what the snapshot wrote. Agreement = daily proof the writer is
      honest; disagreement = a real finding. Costs nothing, both already exist.
      (This is the check that caught the volume-unit bug.)

## Known bugs found on 2026-08-19, not yet fixed
- [ ] 4 unexplained ghost positions: 02-13 (300373), 02-25 (600499), 02-26 (600096),
      03-11 (002497/600096/603191) — root cause never established. Review twist:
      closed/ HAS a 300373 file with entryDate 02-13, so ghosts eventually existed
      without apply ever logging the OPEN
- [ ] `2026-03-11`: `ERROR OPEN 002497: unsupported operand type(s) for //: 'float'`
      — a TypeError in sizing; is it still reachable?
- [ ] 21 run dirs have no manifest at all
- [x] ~~manifest written after the commit~~ — fixed 2026-08-20 (`886a0dd`),
      duplicate of the entry above; manifest now precedes Phase 5
