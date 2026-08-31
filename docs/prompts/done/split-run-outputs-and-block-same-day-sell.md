# Two changes: (1) split run outputs by time-slot, (2) block same-day sell of a just-opened position

Context: the daily pipeline runs twice per trading day — **11:35 (midday)** and **15:35 (post-close)** — both writing into `runs/<YYYY-MM-DD>/`. Two problems to fix.

---

## Change 1 — Split output files by run slot (don't clobber the midday report)

**Problem:** Both runs write to `runs/<date>/output/` with the same filenames (`daily_summary.json`, `report.md`, `watchlist.json`, etc.), so the **15:35 run overwrites the 11:35 run's reports**. We lose the intraday-vs-close audit trail.

**Requirement:** Tag run outputs with a **slot** derived from wall-clock time at run start:
- `midday` if the run starts before 14:00 local (Asia/Shanghai)
- `close` if the run starts at/after 14:00 local
- (Keep it a simple 14:00 cutoff — the two crons are 11:35 and 15:35, so this cleanly separates them. Make the cutoff a module constant for easy tuning.)

**Implement:**
1. In `scripts/run_daily.py`, compute `slot` once at run start from `datetime.now()` in Asia/Shanghai (the repo already uses `datetime.now().astimezone()`; use the local tz).
2. Write **slot-suffixed copies** of the human/report artifacts so both runs are preserved:
   - `report-<slot>.md`, `daily_summary-<slot>.json`, `watchlist-<slot>.json`
   - **Keep** the existing un-suffixed filenames (`report.md`, `daily_summary.json`, `watchlist.json`) as the "latest" pointer for backward compatibility (the most recent run wins, as today). So we ADD slot copies, we don't remove the canonical names.
3. The functions that write these are `generate_report_md`, `generate_watchlist_json`, and the daily-summary writer in `phase3_apply` (around lines 1381–1421). Thread the `slot` value through `phase3_apply(date, decisions, data, slot=...)` and have each writer emit both the canonical file and the slot-suffixed file.
4. Do NOT slot-suffix the persistent state (`tracking/`, `hypotheses.json`, `LEARNINGS.md`, `positions.json`) — those are cumulative, not per-run. Only the per-run report artifacts get slot copies.

**Acceptance:** After a midday + a close run on the same date, `runs/<date>/output/` contains `report-midday.md` AND `report-close.md` (plus canonical `report.md` = the close copy). Same for `daily_summary-*` and `watchlist-*`.

---

## Change 2 — Block same-day sell of a position opened the same day

**Problem / rule (from Benson):** The afternoon (close) run **must not sell a position that was opened earlier the same day** (e.g. the midday run opens a name, the close run must not immediately stop it out / flip it). This prevents same-day round-trips (A-shares are T+1 anyway — you can't actually sell stock bought the same day until the next session, so selling it in the model is unrealistic and creates phantom round-trips). Hold at minimum until the next trading day.

**Implement in `phase3_apply` (`scripts/run_daily.py`, SELL branch ~lines 1161–1175):**
1. Before calling `close_position(...)` for a SELL decision, look up the position's `entryDate` (positions store `entryDate` as `YYYY-MM-DD`; see `scripts/position_manager.py`). The position dict is available via the tracking store / `positions.json` — read it (or have a small helper `get_position(code)` if one isn't already imported).
2. If `position.entryDate == date` (the current run date), **skip the SELL**:
   - Do NOT call `close_position`.
   - Append a clear log action: `f"SKIP SELL {code}: opened today ({entryDate}) — T+1, cannot sell same day"`.
   - Leave the position open (it effectively becomes a HOLD for this run).
3. This guard applies regardless of slot, but in practice only bites the close run (since the midday run is what opens). Keep it slot-independent for safety.

**Edge cases:**
- A position opened on a PRIOR day selling today → allowed (normal stop/exit).
- If `entryDate` is missing/malformed → fail safe by allowing the sell (don't crash), but log a warning.

**Acceptance:**
- Simulate: midday run opens 300037 with `entryDate = <today>`; close run issues a SELL 300037 decision → pipeline logs `SKIP SELL 300037: opened today...`, position remains open, no `close_position` call, no entry in closed/.
- A position with `entryDate` = yesterday still sells normally on a SELL decision today.

---

## Tests
Add/extend tests under `scripts/` (e.g. `test_run_daily.py` or a new `test_phase3_apply.py`):
- Slot derivation: 11:35 → `midday`, 15:35 → `close` (mock `datetime.now`).
- Slot-suffixed files are written alongside canonical ones.
- Same-day-sell guard: SELL on a same-day-entry position is skipped + logged; SELL on a prior-day position proceeds.

## Acceptance (overall)
- `.venv/bin/python -m pytest scripts/ -q` passes (existing + new).
- A real `--run` produces `report-<slot>.md` and preserves both midday/close artifacts.
- No regression to persistent state handling, gates, or git-commit phase.

## When done
Append a Done section (summary, files changed, test counts) and move this file to `docs/prompts/done/`.
