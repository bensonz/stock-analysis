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
