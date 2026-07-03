# Prompt: Make the long-entry gate breadth-aware (stop auto-blocking on narrow megacap-flush days)

> **Repo:** `stock-analysis` (`/Users/bz/Work/Personal/stock-analysis`)
> **Files:** `agents/ANALYST.md` (primary), `scripts/run_daily.py` (`evaluate_new_entry_regime`, verify alignment only)
> **Do not touch position-management, sizing multipliers, or stop rules.** This is purely the *new-entry gate*.

## Problem (verified 2026-07-02)

On 2026-07-02 the market was a **narrow megacap/large-index flush, not a broad selloff**:
- Indices deep red: 科创50 −4.61%, 创业板 −3.47%, 深证 −2.09%, 上证 −0.90% (0/3 gate indices green)
- **But breadth was POSITIVE:** ~3057 up / 2337 down (≈1.31:1), 135 limit-ups vs only 6 limit-downs
- i.e. the *median* stock was fine/up; only index-heavy tech (semis) was getting destroyed, plus a clear rotation INTO 贵金属 +6.39%, 林业 +7.98%, 工程机械 +2.81%.

The analyst returned `new_positions: []` and narrated "0/3 indices green blocks new entries."

**Root cause is in `agents/ANALYST.md`, not the Python.** The Python `evaluate_new_entry_regime` only hard-blocks on a *panic tape* (ratio < 0.35 OR limit_downs ≥ 30) — today was neither, so the code would have allowed entries. But `ANALYST.md` instructs a **stricter AND gate**:

- Line ~115: *"Minimum long-entry gate: Up/Down ratio must be at least 1.5:1 **AND at least 2 major indices must be green**, otherwise default to `new_positions: []`"*
- Line ~23: "Minimum buy gate for any new long"
- Line ~233: "Default to `[]` when breadth/regime is weak."

The hard "AND ≥2 indices green" requirement is a **blunt instrument**: it cannot distinguish a *broad market collapse* from a *narrow megacap flush with healthy breadth*, and it blocks exactly the rotation-capture entries we'd want on days like today.

## The change

Rewrite the minimum long-entry gate in `ANALYST.md` so it is **breadth-aware with a narrow-flush exception**, while still hard-blocking genuine broad routs. Replace the strict "breadth ≥1.5:1 AND ≥2 indices green" rule with:

**Allow new long entries when EITHER:**
- **(A) Broad-strength path:** Up/Down ratio ≥ 1.5:1 **AND** ≥2 of 3 major indices green (the existing strong-tape case — keep as-is), **OR**
- **(B) Narrow-flush path (NEW):** Up/Down ratio ≥ 1.3:1 **AND** limit_downs < 15 **AND** the *candidate's own sector* is in today's **top 30% of sectors (green/leading)** and NOT in the bottom-5 / crashing sectors — even if indices are red.
  - Rationale: when breadth is healthy but indices are red, capital is *rotating*, not fleeing. Buy the strength (the leading sectors) rather than sitting out the whole day. This is a selective, sector-aligned entry, not a blanket green light.

**Still HARD-BLOCK all new entries (return `new_positions: []`) when ANY:**
- Panic tape: Up/Down ratio < 0.35 **OR** limit_downs ≥ 30 (matches Python `panic_tape`)
- Breadth ratio < 1.0 (weak tape — median stock declining; keep cash)
- Candidate's sector is in the bottom-5 / crashing sectors (existing Rule 1 — never override this)
- Candidate is overextended per MA-distance rules (existing Rule 2b — never override this)

**Sizing on the narrow-flush path (B):** cap fresh size conservatively — treat it like `STRONG_TAPE_SIZE_MULTIPLIER` (the existing "cap at X% to avoid chasing" throttle) or smaller. This is a higher-risk regime (indices red), so entries should be *smaller and more selective*, never full-size. Do NOT allow multiple new positions on a path-B day — cap at 1 new starter.

## Also: align the Python (verify, light touch)

`scripts/run_daily.py::evaluate_new_entry_regime` currently sets `allow_new_positions = has_breadth and not panic_tape` and only classifies regime by breadth+index. It does NOT itself enforce the strict "≥2 indices green" AND-gate — so the primary fix is `ANALYST.md`. **Confirm** the Python still permits path-B (it should, since today isn't panic). If any downstream code (e.g. the apply step around line ~1216 `if entry_regime.get("allow_new_positions")`) would suppress a valid path-B entry, adjust only enough to let a sector-aligned narrow-flush entry through at throttled sizing. Keep the panic/weak hard-blocks intact.

## Acceptance criteria

- On a **2026-07-02-type tape** (indices red, breadth ≥1.3:1, few limit-downs, clear sector rotation), the analyst MAY open **1 small sector-aligned starter** in a leading (top-30%) non-crashing sector — instead of auto-returning `[]`.
- On a **genuine panic/broad selloff** (ratio < 1.0, or limit_downs ≥ 30, or ratio < 0.35), entries are still **fully blocked**.
- Bottom-5 sector skip (Rule 1) and MA-overextension skip (Rule 2b) still override everything — path B never buys a crashing-sector or overextended stock.
- Path-B entries are throttled (≤ strong-tape sizing, max 1 new position).
- Update the example JSON / narration in `ANALYST.md` so the analyst *explains* which path (A broad-strength vs B narrow-flush) it used and why, and logs breadth vs index divergence explicitly.

## Test

Add a unit test (or extend `test_pipeline.py`) with a synthetic market dict matching 2026-07-02 (indices all negative, up=3057/down=2337, limit_downs=6) + one candidate in a top-30% green sector → assert the gate would ALLOW a throttled entry. And a panic dict (ratio 0.2 / limit_downs 40) → assert BLOCK.
