# Harness: catching failures we haven't imagined yet

**Problem**: on 2026-08-19 a sweep of six months of runs found **12 runs** where the
report claimed a position that never opened, or apply threw an error. Four vanished
with no SKIP and no ERROR. One (02-13, ghost 300373) caused a downstream
`ERROR HOLD 300373: Position file not found` on 03-03 — and *that* wasn't noticed
either. Separately, **18 trading sessions** had no run at all.

None of this surfaced, for one reason: **94% of runs were marked `degraded`** (120 of
them by a single dead check), and the scheduler reported `timed out` on 100% of recent
runs while succeeding. Both layers were saturated with false alarms, so there was no
"normal" for anything to stand out against.

**Design premise**: a checklist of detectors for bugs we already found is fighting the
last war. What generalises are checks *closed over a space* rather than aimed at a
case — invariants that fail for reasons nobody enumerated in advance.

---

## Stage 1: Restore signal — **Complete** (`6ab9377`)

**Goal**: make `degraded` mean something before adding anything that reports into it.
**Done**: removed the dead V1 `watchlist` check; added a third severity `gate.note()`
so risk-engine WATCH/WARNING output is recorded without setting run status; a rule that
*failed to run* still degrades.
**Result**: 14 of the last 15 runs go `degraded → success`; the one still flagged has a
real cause (price DB one session stale).

---

## Stage 2: Reconciliation — `scripts/doctor.py`

**Goal**: one independent command that re-derives truth from raw artifacts and exits
non-zero on any divergence. Covers mechanisms **1 (replay)** and **2 (conservation)**.

Two rules that come straight from the failures:
- **Never trust the pipeline's own bookkeeping.** A broken pipeline cannot audit
  itself — that is exactly how 07-20 stayed hidden for 3.5 weeks.
- **Sweep history, not just now.** Every incident was found late; a present-tense check
  would have missed all twelve.

### 2a. Replay invariant (the strongest single check)
Each `tracking/<code>.json` carries an append-only `history[]` of
`{date, slot, action, price}`. Therefore `shares`, `currentStop`, `allocatedCapital`
are *pure functions of that history*. Check both directions:
- every position's fields reproduce from replaying its own history
- every run action has a matching history entry, and vice versa

Would have caught: 02-13 ghost, 03-11 crash, 07-20 orphan, 08-17 report lie — none
anticipated.

**Precondition (must verify first)**: the log and the state must be written
*independently*. If Phase 3 serialises both from one in-memory object they will agree
while both are wrong, and this check is decorative. **Audit before building.**

### 2b. Conservation identities
- `equity == cash + Σ(shares × price)`, derived two independent ways
- `Δequity` between snapshots == mark-to-market + realised − costs
- realised from `closed/*.json` == running `realizedPnl`

Any residual beyond rounding is a defect that nobody had to predict.

### 2c. Cross-artifact consistency
`positions.json` ↔ `tracking/*.json` ↔ latest snapshot ↔ report claims. Every run dir
has a manifest. No future-dated entries. Every open position has a stop.

**Success criteria**: running it over the full history reproduces the 12 known
incidents and finds nothing spurious.
**Tests**: every check ships with a deliberately-broken fixture proving it fires (see
CHECKLIST.md — this is non-negotiable).
**Status**: Not Started

---

## Stage 3: Drift + fail-loud posture

**Goal**: mechanisms **3** and **4** — catch "something changed shape" and stop new
holes from being born silent.

- **3a. Structural drift**: compare each run against the trailing 20 — sections
  present, candidate count, decision count, artifact sizes, phase durations. Flags a
  half-dead data source or an LLM that quietly stopped emitting a field, with no rule
  written in advance.
- **3b. Fail-loud audit**: sweep for bare `except:`, `except Exception: pass`, and
  `.get(k, <plausible default>)` on load-bearing paths. Missing/unknown must render as
  an explicit marker, never a plausible value. The null-visibility rule exists as
  doctrine but is enforced nowhere.

**Status**: Not Started

---

## Stage 4: Scheduling + heartbeat

**Goal**: execution we control, and detection of **absence** — the one class no
in-pipeline check can ever catch, because a pipeline that isn't running can't report
that it isn't running.

Split by nature of the work (rationale in DECISIONS.md):
- **Pipeline execution → launchd.** Deterministic script, native to macOS, survives
  reboot, authoritative exit code, no LLM in the loop.
- **Daily sweep → agent cron.** Judgement work; an agent is the right tool.
- **Heartbeat → independent of both.** Reads `runs/*/manifest.json` and asks "did a
  good run land for every expected slot". The invoker must never be the source of
  truth for success.

**Status**: Not Started

---

## Stage 5: Daily agent sweep → `docs/audits/daily/YYYY-MM-DD.md`

**Goal**: the residual — failures no invariant models. Today's sweep found 12
incidents in an hour and happened *by accident*. Make it a scheduled ritual with a
standing question: *"what does the system claim that I can independently verify?"*

Runs after the afternoon pipeline. Reads doctor output, the day's manifests/reports,
and the diff of `tracking/`. Writes one dated file: what it checked, what it found,
what it could not verify. **Explicitly lists what it could NOT check** — absence of
findings must never read as proof of health.

**Status**: Not Started

---

## What this still won't catch

Stated plainly so the harness isn't oversold:
- **Wrong-but-consistent.** Consistently bad decisions reconcile perfectly. No
  invariant detects "the strategy is losing money" — that is the weekly audit and
  ablation axis, not this one.
- **Plausible bad upstream data.** Wrong-but-reasonable prices pass every internal
  check. Only cross-source comparison catches it; `db_health` does a little today.
- **Correlated errors.** Log and state wrong in the same way — see the Stage 2a
  precondition.
