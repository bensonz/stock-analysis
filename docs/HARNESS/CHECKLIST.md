# Harness pre-flight checklist

Nothing in this harness counts as "done" until it can demonstrate it detects
something. The point is not to have checks; it is to not be lied to.

## Per detector
- [ ] Has a **known-bad fixture** that makes it fire (D4). No fixture, no merge.
- [ ] Has a **known-good fixture** that keeps it silent — false alarms are the failure
      mode that killed the last two layers (94% degraded, 100% phantom cron timeouts)
- [ ] Failure message names the **binding constraint with numbers**, not a category.
      (The 08-17 bug hid for months behind "Insufficient deployable cash" while cash
      was 13x what was needed.)
- [ ] Says what it did NOT check when it cannot check something
- [ ] Reads raw artifacts, not the pipeline's own summary of itself

## Per stage
- [ ] Full suite green (7 known pre-existing failures only)
- [ ] Run against **full history**, not just today — every incident so far was found late
- [ ] Spurious-finding count is zero on known-good history; if not, the check is noise
      and must be fixed or dropped before it ships
- [ ] Documented in PROGRESS.md with the actual numbers

## Before declaring the harness "working"
- [ ] doctor.py reproduces all 12 known incidents from history
- [ ] Deliberately break something live (a stale manifest, a hand-edited position) and
      confirm it surfaces in the report within one run
- [ ] Kill a scheduled run and confirm the heartbeat notices the absence
- [ ] Confirm `degraded` is now rare enough that a single one draws attention
