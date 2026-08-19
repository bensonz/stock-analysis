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
