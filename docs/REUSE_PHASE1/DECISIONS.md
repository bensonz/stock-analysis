# Decisions

**D1 — flag on `--run`, not a new mode.** Everything after Gate 1 (LLM, Gate 2/3, apply, manifest, commit) must be the same code as a scheduled run. A separate mode would copy it and drift.

**D2 — refuse when the book moved.** Compare `active_positions` + `closed_positions` of `input/positions_snapshot.json` against a fresh snapshot. A Gate 2/3 failure fails closed so they match; anything else means the prompt would describe positions that no longer exist. `positions_json` is not compared — phase 1 and prompt building regenerate it (prices, `lastUpdated`).

**D3 — carry the prior manifest's `health_check` and `preflight_pricedb`.** They are the conditions the reused data was collected under; the doctor's `pricedb_current` / `snapshot_wrote_rows` keep auditing something true. `collect` is written fresh with `reused_phase1: true`, `collected_at`, `reused_duration_sec`; its `duration_sec` is 0. Status stays `"ok"`/`"failed"` — no new status string for the site to colour.

**D4 — Gate 1 re-runs, auto-heal does not.** The gate is cheap and honest on reloaded data; auto-heal re-collects, which the flag exists to avoid. A Gate 1 failure says "run without --reuse-phase1".

**D5 — age is a warning, not a gate.** Afternoon reuse is always the settled close. Noon reuse hours later is an operator choice; the run prints the age loudly.

**Rejected — hand-edit `response.json` + `--apply`.** Puts a human-written decision in the trade record.
