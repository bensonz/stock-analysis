# tracking/ schema — v2.1 (rewritten 2026-09-01 against the code; layout 2026-10-12)

**Authority: `scripts/position_manager.py` is the schema.** This document
describes what that code writes, generated from the live files on
2026-09-01. If this page and the code disagree, the code is right and this
page has rotted — fix it in the same commit that changed the writer.
(The previous version of this file described a v1.0 that no code had written
since February; it sat here stale for six months while CLAUDE.md called it
canonical. Rewritten per repo audit decision B5.)

## Files

Layout since 2026-10-12 (docs/TRACKING_LAYOUT stage 2). Every path is named
once, in `scripts/tracking_paths.py`.

```
tracking/
  book/                    the portfolio — position_manager.py is the only writer
    positions.json         aggregate view (portfolio + activePositions) — REGENERATED,
                           never hand-edited; rebuilt from the per-code files
    active/{code}.json     one file per active position (the source of truth);
                           NOTHING else lives in active/
    closed/{code}_{exitDate}.json    moved here on close — date suffix REQUIRED
                           (naming without the date silently erased 9 round-trips
                           pre-2026-08-06; see docs/tracking_fixes/). The 42
                           pre-2026-08-06 files keep their undated {code}.json name.
    config.json            hard limits (see below); was portfolio_config.json
  ledgers/
    hypotheses.json        the learning loop's state (separate schema, owned by
                           hypothesis_manager.py)
    predictions.jsonl      prediction_log.py
    rotation_ledger.json   rotation_ledger.py
  calendar/
    events.json            curated event calendar (event_calendar.py reads it)
    event_inbox.md         candidates for the owner (event_inbox.py)
    event_inbox_ledger.json  keep/skip decisions (event_inbox.py)
  README.md
```

Before 2026-10-12 all of this sat flat in `tracking/` (`tracking/{code}.json`,
`tracking/closed/`, `tracking/portfolio_config.json`, …). Run snapshots
(`runs/*/positions_snapshot.json`) do not store paths, so they are the same
before and after the move.

## config.json — the hard limits

```json
{"starting_capital": 1000000, "max_position_pct": 10, "max_positions": 10,
 "min_cash_pct": 0, "created": "2026-02-03", "currency": "CNY"}
```

These are the authoritative limits (owner decision 2026-09-01, audit B2):
**max 10 positions, no minimum-cash floor.** ANALYST.md mirrors these numbers;
if they differ, this file wins and the prompt is stale.

## book/active/{code}.json — a position

Live keys (all present on an active position):

| key | meaning |
|---|---|
| `code`, `name`, `sector` | identity; `code` is the bare 6-digit form |
| `status` | `active` → `closed` (no other values in 64 opens to date) |
| `thesis` | LLM's entry reasoning, free text |
| `entryDate`, `entrySlot` | date + `noon`/`afternoon` |
| `entryPrice`, `shares`, `allocation_pct`, `allocatedCapital` | entry sizing |
| `stopLoss` | the ORIGINAL stop (never moves) |
| `currentStop` | the trailing stop (RAISE_STOP moves this one only) |
| `targetPrice` | soft reference — momentum doctrine treats the trailing stop as the hard constraint, not the target (see h174) |
| `rating`, `rps120`, `catalysts`, `sourceWatchlist` | entry-time context |
| `trackerVersion` | `"2.1"` |
| `createdAt`, `updatedAt` | ISO timestamps |
| `history` | append-only event list, below |
| `corporateActions` | only once a dividend/送转 was booked (2026-10-08+), below |

**On close, added:** `exitDate`, `exitPrice`, `exitReason`, `holdingDays`,
`returnPct`, `lessonLearned`. When the position carries `corporateActions`,
`returnPct` = ((exit − entry) × shares + dividend cash) / (entry × shares) —
dividends received are part of the trade's return; otherwise the plain
(exit − entry) / entry.

### corporateActions[] — dividends and 送转 (2026-10-08)

Written by `corporate_actions.apply_due` (persisted through
`position_manager.save_corporate_actions`) at the start of phase 3, every
slot, for OPEN positions only, for events with entryDate < exDate <= run
date. Idempotent by `exDate`. Closed trades are never restated.

```json
{"exDate": "2026-10-08", "cashPer10": 1.39, "bonusPer10": 0.0,
 "plan": "10派1.39元(含税,扣税后1.251元)",
 "sharesBefore": 1700, "sharesAfter": 1700,
 "entryPriceBefore": 24.21, "entryPriceAfter": 24.21,
 "grossCash": 236.3, "taxRate": 0.2, "tax": 47.26, "netCash": 189.04,
 "appliedAt": "<ISO>"}
```

- `taxRate` by holding period at the ex-date: ≤ 1 calendar month 0.20,
  ≤ 1 year 0.10, longer 0. Cash is paid on `sharesBefore`.
- 送转 (`bonusPer10` > 0): `shares` → floor(shares × (1 + bonusPer10/10)),
  `entryPrice` ÷ the same factor (6 dp), `allocatedCapital` unchanged.
  `stopLoss` / `currentStop` / `targetPrice` are NOT adjusted (owner
  decision) — Gate 3 soft-warns that the stop will likely trip.
- Σ `netCash` is the position's dividend cash (`position_manager.dividend_cash`)
  — the single source; no cached total field.

**`exitReason` is free-text LLM prose, NOT an enum** — measured: 0 of 61
closed positions match the old enum. That is the accepted design (audit B5):
narrative goes here; anything queryable must be derived from `history` actions
and prices, not parsed out of this field.

## history[] — one entry per run that touched the position

```json
{"date": "2026-08-27", "slot": "afternoon", "price": 59.01,
 "change_pct": 0, "action": "OPEN", "note": "LLM开仓 奥士康"}
```

- **Action vocabulary (measured over 432 entries): `OPEN` / `HOLD` /
  `RAISE_STOP` / `SELL`.** No ADD, no PARTIAL_EXIT (adding to positions was
  evaluated 2026-08-27 and rejected: no edge at any P&L threshold).
  Since 2026-10-08 also `DIVIDEND` (carries `shares`, `cashPer10`,
  `grossCash`, `taxRate`, `tax`, `netCash`) and `BONUS_SHARES` (carries
  `shares` = after, `sharesBefore`, `bonusPer10`, `entryPriceBefore`,
  `entryPriceAfter`), dated at the ex-date, with no `price`.
- `slot` present since the 2026-07 noon/afternoon split (legacy entries lack it).
- OPEN entries may additionally carry `shares` / `stop` / `allocatedCapital`
  (the 2a-i widening, so the doctor can audit sizing from the history alone).
- `synthetic: true` marks backfilled entries from the 2026-08 history repair —
  they are reconstructions, not live marks.

## positions.json — the regenerated aggregate

```
lastUpdated            ISO timestamp of last regeneration
activePositions[]      per-code snapshot + live-mark fields:
                       currentPrice, pnl_pct, currentValue, unrealizedPnl,
                       volume, mavol30, volumeBelowMavol30, weight_pct,
                       dividendCash (only when non-zero)
portfolio{}            startingCapital, totalEquity, cash, investedValue,
                       unrealizedPnl, realizedPnl, dividendCash, totalPnl,
                       totalReturnPct, positionsUsed, positionsMax, cashPct,
                       dayPnl, minCashPct, minCashValue, deployableCash
```

Cash is derived, never stored:

```
cash        = starting − Σ open (shares × entryPrice)
                       + Σ closed ((exit − entry) × shares + dividend cash)
                       + Σ open dividend cash
realizedPnl = Σ closed (… incl. their dividends) + Σ open dividend cash
dividendCash = Σ open dividend cash (the open share of realizedPnl)
totalPnl    = unrealizedPnl + realizedPnl = totalEquity − starting
```

Regenerated by `position_manager.regenerate_positions_json()` on every run
(and, note well, by `--phase1` too — there is no read-only pipeline mode).
Because it is derived, hand-edits are lost on the next run; edit the per-code
files (or better, don't — the pipeline owns them, `--reset-to` for rollbacks).

## Rules for anything that touches these files

1. **`position_manager.py` is the only writer of `book/`.** The audit found
   two violations (`--reset-to`, and phase functions with side effects). The
   reset is fixed: since 2026-10-12 `plan_book_restore` / `apply_book_restore`
   live in position_manager (docs/TRACKING_LAYOUT D9). The phase-function side
   effects remain scheduled refactor work, not precedent.
2. **The doctor never writes here** (D12) — detection only.
3. `closed/` filenames MUST carry the exit date.
4. History is append-only; repairs add `synthetic` entries rather than
   rewriting real ones.
5. `book/active/` holds position records only. A reader still checks each
   file with `position_manager.is_position_record`; `--reset-to` aborts on a
   file there that is not one.
