# Corporate actions in the simulated book (dividends + 送转)

Owner ask 2026-10-08 after the site's P&L check exposed 普洛药业 ex-div
(10派1.39, ex-date 2026-10-08): the book took the price drop and credited no
cash (~¥236). position_manager.py has no corporate-action handling at all;
送转 is unhandled too (a 10转4 would read as −28%).

## Owner decisions (2026-10-08)
- Scope: forward from now + back-credit missed events on CURRENTLY OPEN
  positions only. Closed trades are never restated.
- Tax: A-share holding-period rule judged at ex-date — held ≤1 month 20%,
  >1 month ≤1 year 10%, >1 year 0%.
- Stops/targets: NOT adjusted. A 送转 event must log a loud warning (stop will
  likely trip). entryPrice IS rescaled on 送转 so cost basis is preserved.

## Stage 1: event source
**Goal**: per-code ex-div events from eastmoney datacenter RPT_SHAREBONUS_DET
(PRETAX_BONUS_RMB = cash per 10 sh, BONUS_IT_RATIO = 送转 per 10 sh,
EX_DIVIDEND_DATE, ASSIGN_PROGRESS == 实施分配). Fetch failure → None (loud),
never a hard fail.
**Tests**: parse fixture rows; failure returns None; non-implemented plans skipped.
**Status**: Complete

## Stage 2: apply to the book (idempotent)
**Goal**: for each active position, events with entryDate < exDate <= run date
not already in the position's `corporateActions` list are applied: net cash
credited (tax by holding period), 送转 → shares × (1+r/10) floored, entryPrice
÷ same factor, allocatedCapital unchanged. Cash/equity/realized P&L include
dividend cash; a later close's returnPct includes dividends received.
**Tests**: cash credit + tax brackets; 送转 shares/entry; idempotent re-run;
event before entryDate ignored; fetch failure leaves book untouched.
**Status**: Complete

## Stage 3: pipeline wiring
**Goal**: applied at the start of Phase 3 every slot, recorded in the run log /
manifest; doctor stays green.
**Status**: Complete
