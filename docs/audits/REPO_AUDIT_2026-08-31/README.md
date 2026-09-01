# Repo Audit — 2026-08-31 (synthesis)

Three read-only survey agents ran in parallel over the whole repo; their full
reports sit beside this file. Every headline claim below was independently
re-verified at `file:line` before being written down — the four most severe
(arbitrary-path write, entry gates, price-0 fabrication, rules-engine
swallow) by reading the live code directly.

| report                   | scope                                                      |
| ------------------------ | ---------------------------------------------------------- |
| `DOCS_AUDIT.md`          | all 79 hand-written markdown files: CURRENT / STALE / DEAD |
| `DEADCODE_AUDIT.md`      | unused modules/functions, the 7 red tests, test-layer rot  |
| `ARCHITECTURE_REVIEW.md` | layering, top-10 risk findings, run_daily split proposal   |

**State in one sentence:** the structure is sound and the recent refactors
held; the real risk is that `agents/ANALYST.md` and the Python gates have
drifted apart with nothing able to detect it — and the drift consistently
runs toward taking MORE risk.

---

## A. Safety-critical code fixes (small, high-stakes)

1. **`phase3_apply` writes any path the LLM names, chmod 0755, then commits
   and pushes it** — `run_daily.py:1990-1993`. No allowlist, no traversal
   check. Containment is one line (`resolve().is_relative_to(...)`).
2. **A failed price fetch fabricates a −100% day** — `price_data.get("price", 0)`
   at `run_daily.py:1664`; sibling default renders a missing price exactly
   flat, blinding all six sell rules. `close_position` accepts price 0 while
   `open_position` rejects it.
3. **The sell-discipline layer can go dark with a clean log** —
   `except Exception: pass` around `run_all_rules()` (`run_daily.py:2072`);
   a crashed rule script reads as 0 violations.
4. **db_health failure silently deletes all three data-quality hard gates**
   (`run_daily.py:1272`, `contracts.py:212`).
5. **`f10>=30` panic clause depends solely on CheeseForTune** — no fallback
   emits `distribution`; absence prints as "0 limit-downs" as if measured.
   Same husk-shape live in `fetch_iv_sentiment.fetch_all:256` (feeds sizing).
6. **No locking, non-atomic writes** — both launchd jobs have fired
   simultaneously once (2026-08-26). Cheapest big win:
   `position_manager._write_json` → temp+`os.replace`.

## B. Decisions only the owner can make

1. Entry gates: spec says breadth ≥1.5:1 and 2-of-3 indices are MANDATORY;
   code blocks only below 0.35:1 and treats both as sizing labels. Which is
   the strategy?
   code is right, only sizing on a bad day.
2. Position limits: prompt 8 / 20% cash vs config 10 / 0% — the model sees both.
   config is right, udpate the prompt one
3. Time stop: 15d (code + one spec line) vs 10d (three other lines the model
   reads every run); TRACKER.md has a third variant.
   15d is correct
4. The four orphaned agent specs (ORCHESTRATOR / RESEARCHER / TRACKER /
   DAILY_AUDIT): archive, delete, or rewrite? TRACKER.md as written would
   destroy the portfolio block.
   delete
5. TRACKER_SCHEMA.md: rewrite against code, or delete and point at code?
   rewrite
6. Hypothesis staleness is dead in production (retire check only fires when
   evidence arrives): wire `stale-check` into the pipeline, or drop it?
   delete it.
7. `pit_archive.py`: revive or delete?
   revive and come back later
8. requirements: `baostock` / `tushare` imported by nothing — keep as forensic
   conveniences or drop?
   remove

## C. Approved-convention work (mechanical)

- Doc fixes ~15 files: 15:35→15:05, missing `<slot>` in audit-spec paths
  (WEEKLY_AUDIT's runs section silently empty since July), pre-move
  `scripts/*.py` paths incl. one rendered into every report via
  `event_calendar.py:121`, shipped-work still marked Not Started, `.gitignore:14`.
- Deletions (0 inbound refs each, per repo convention): 10 fully-closed plan
  files, `test_eastmoney.py` (4 live HTTP calls at every pytest collection),
  `fetch_price.py` + `fetch_and_save.py` (+ agent-doc mentions),
  `vcp_backtest.py`, 2 foreign options-learn work orders, the eastmoney codex
  plan that instructs what the provider doctrine forbids.
- Test repairs: 5 wall-clock-bombed hypothesis tests, the stale sizing test
  (rename too — it asserts the opposite of its name), delete the local-state
  replay test, real asserts for the 7 assert-free `test_full_pipeline` tests,
  unify the two conftests so `--run-integration` works (dead since May), fix
  2 confirmed-inert monkeypatches.
- One guard test converting the "pipeline never imports research/" convention
  into an invariant.

## D. Scheduled refactors (proposals)

- `run_daily.py` split into `scripts/pipeline/` — four stages, façade
  discipline as with pricedb; Stage 2 (state-mutating boundary with explicit
  dirs) kills the class where `--phase1` mutates the live book. Details in
  `ARCHITECTURE_REVIEW.md` §3.
- Spec↔code drift detection (the missing layer behind B1–B3).
- `--reset-to` bypasses position_manager and re-introduces the pre-08-06
  closed-file naming; fold into the split.

## Deliberately NOT changing

The 22 deferred imports in pricedb (they ARE the test seam), the free
provider chain behind iFinD, doctor-as-separate-job, the three frozen epochs,
per-rule thresholds beside their track records, dated records never rewritten.

---

_Reports generated 2026-08-31 by read-only survey agents; synthesis and
spot-verification by the coordinating session. Nothing was modified during
the survey._
