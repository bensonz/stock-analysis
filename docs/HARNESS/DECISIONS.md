# Harness decisions

## D1 — Flag at the report; never block the commit (owner, 2026-08-19)

By the time doctor runs, the trades are already applied and irreversible. Blocking a
commit protects nothing and risks halting the book on a *doctor* bug. Findings surface
in `report.md` — the artifact the owner actually reads — and in the site banner.

Corollary: this settles the Gate-3 severity question open since 08-14. Post-apply
problems in non-trade steps degrade and shout; they do not block.

## D2 — Split execution from judgement: launchd for the pipeline, agent cron for the sweep

**Evidence.** The openclaw cron job `Stock Analysis Pipeline` (`35 11,15 * * 1-5`,
Asia/Shanghai) has reported **64 errors in 203 runs**, 60 of them
`cron: job execution timed out` — including *every* run from 08-14 through 08-19, all
of which actually succeeded and committed.

The 600s timeout is not measuring the pipeline. Pipeline wall-clock is p50 **207s**,
p90 392s, p99 720s; only **4% of 136 runs exceed 600s**. The timeout is bounding the
*LLM agent session wrapped around* the pipeline. So the scheduler has been reporting
failure on success for months — the same saturation disease as the 94% `degraded`, one
layer up, and equally guaranteed to hide a real failure.

**Options considered**

| | verdict |
|---|---|
| Keep openclaw cron, raise the timeout | Cheapest, but leaves an LLM agent in the path of a deterministic script — cost, latency, nondeterminism, and a success signal that reports on the agent rather than the work |
| **launchd (chosen)** | Native to macOS, survives reboot, `RunAtLoad`, direct `python3 scripts/run_daily.py --run`, exit code means what it says, stdout/stderr to a file |
| Write our own scheduler daemon | Most control, most maintenance, no benefit over launchd for a fixed twice-daily schedule |

**Chosen**: launchd runs the pipeline. The openclaw agent cron keeps the **daily
sweep**, which is genuine judgement work and the right use of an agent. This also
matches how the owner asked for it: deterministic run, then an agent sweeping results.

**Non-negotiable regardless of scheduler**: the invoker is never the source of truth
for success. The authoritative answer is "did a manifest with a good status land on
disk for the expected slot", checked by something that is not the invoker. Had that
existed, the 60 phantom timeouts would have been visibly phantom, and the 18 dark
sessions visibly dark.

## D3 — Three severities, not two (`6ab9377`)

`hard` (stop) / `soft` (defect → degraded) / `note` (recorded, status untouched).

Risk-engine WATCH/WARNING output is the engine working, not the pipeline degrading;
counting it as degradation made it indistinguishable from a real defect. A rule that
*failed to execute* is still `soft` — that is a genuine defect.

## D4 — Detectors must ship with a fixture proving they fire

A check that has never fired is not evidence of health; it is untested code. "missing
watchlist" fired 120 times and meant nothing. A check firing zero times can be equally
meaningless, and there is no way to tell the two apart without feeding it a known-bad
input. Applies to every check in doctor.py.

## D5 — Replay over enumeration

Prefer invariants closed over a space ("state must reproduce from its own event log")
to checks aimed at a case ("does the report mention a position that isn't held"). The
second only catches what we already suffered; the first catches causes nobody listed.

Accepted cost: replay is more work to build and depends on the log and state being
written independently — a precondition to verify, not assume.

## D6 — The daily sweep must publish what it could NOT verify

An empty findings list otherwise reads as proof of health. It usually means the check
did not run, the data was missing, or nobody looked. Each daily file states coverage
explicitly.

## D7 — The absence watcher must be partly off-machine (review, 2026-08-19)

Every same-machine watcher shares the machine's fate: a Mac that is off runs neither
the pipeline nor the thing meant to notice the pipeline didn't run. The most expensive
incident (03-13→03-26, −33pp) is plausibly exactly this. Fix: a dead-man's switch
outside the machine — scheduled GitHub Action checking that a run commit landed for
the expected slot (runs are already committed and pushed; infra exists). Local
heartbeat still worth having for fast, rich diagnostics; the Action is the backstop.

## D8 — Sweep findings persist until acknowledged (review, 2026-08-19)

A dated file nobody is forced to revisit is a write-only alarm stream — the failure
this plan documents twice (94% degraded, 100% phantom timeouts). An unacknowledged
finding therefore reappears in every subsequent daily file and run report until a
resolution line is written next to it. Acknowledgment is a written act, not a read.

## D9 — Historical manifest statuses are marked, not recomputed (2026-08-19 epoch)

`degraded` before 2026-08-19 was produced by retired rules (dead V1 watchlist
check + risk findings counted as degradation), so 115 of 147 historical runs
carry a status that means nothing. Two options: recompute them under today's
rules, or mark the boundary.

**Chosen: mark.** `contracts.GATE_SEVERITY_EPOCH = "2026-08-19"`. The files are
not touched. A run's manifest is the record of what that run reported;
recomputing it would make history claim something it never said. This is the
third time the same call has been made — pre-epoch history events stay
unreplayable rather than back-filled with invented values (HISTORY_SCHEMA_EPOCH),
and the impossible 奥来德 T+1 trade stayed on the books with a `dataQuality`
marker rather than being deleted.

Binding on doctor and on any health-over-time comparison: **split on the epoch
and say so in the output.** Reading pre-epoch status as comparable to
post-epoch status is reading noise — and a sweep that floods on 115 phantom
`degraded` runs would train exactly the blindness Stage 1 removed.

## D10 — audit output lives with the run, recurrence is derived

**2026-08-22.** Owner rejected `docs/audits/daily/YYYY-MM-DD.md` in favour of
`runs/<date>/<slot>/audit-result.{md,json}`, beside the manifest it judges.

Reasons it is better than what I proposed: same lifecycle and same git tracking
as the artifacts it describes; no separate index needed to answer "how did that
run go"; and — the part I had not seen — because the doctor runs on its own
schedule rather than as a pipeline phase, it can create the file even when the
run left nothing, which turns the audit file's own presence into the signal that
distinguishes *failed* from *never fired*.

Recurrence counting is **derived** by re-reading the previous 12 slots'
`audit-result.json` rather than kept in a ledger. A ledger is state that can
drift out of agreement with the runs it summarises; derivation cannot. The one
fact not derivable from run artifacts is a human deciding a finding is known and
accepted, so that — and only that — lives in `audit/ACCEPTED.md`.

Rejected: a third severity for "known". Acceptance already expresses it, and a
third level invites the same saturation that made 94%-degraded meaningless.

## D11 — the auditor does not share a fate with the audited

**2026-08-22.** `com.bz.stock-doctor` is a separate launchd job, not the last
line of `run_scheduled.sh`.

If the doctor ran inside the pipeline wrapper, a pipeline that died hard —
segfault, OOM, machine asleep through the slot — would take the audit down with
it. The single most valuable thing the audit can say is "the run that should
have happened left nothing behind", and that sentence is unwriteable by a
process the dead run was hosting.

Cost: two jobs to keep in sync instead of one. Accepted — the 20-minute offset
(11:55 / 15:25) is the only coupling, and it is one integer in each plist.

## D12 — detection only; the books are never repaired

**2026-08-22.** Owner chose detection over detection+auto-heal.

The boundary I would have held either way, now pinned by a test: the doctor may
never write `tracking/` or `tracking/closed/`. A system that silently repairs
its own trade records produces numbers nobody can audit — including us. Every
finding needs a human to act, which is slower and is the point.

