# Decisions
- Source: eastmoney datacenter RPT_SHAREBONUS_DET — already used by pricedb
  for ex-div dates, carries cash + 送转 ratios (verified on 000739).
- Back-credit = the same idempotent apply run once (entryDate < exDate <= today);
  no separate migration path.
- Tax at ex-date, not at sale: simpler, slightly conservative (owner choice).

## Implementation decisions (sub-agent, 2026-10-08)
- **Cash formula.** `cash = starting − Σ open(shares × entryPrice) + closed
  realized + Σ open dividend cash`. Dividend cash is its own explicit term,
  summed from each position's `corporateActions[].netCash` by
  `position_manager.dividend_cash` — the single source, no cached total field.
- **Which bucket.** Dividends are realized income: `portfolio.realizedPnl` =
  closed realized (incl. each closed trade's dividends) + open dividends.
  `portfolio.dividendCash` shows the open part alone. Chosen over a separate
  bucket so `totalEquity − starting == totalPnl` stays an identity with no
  new term in totalPnl (tested).
- **Closed history is untouched by construction.** `corporateActions` only
  exists on positions open on/after 2026-10-08; `dividend_cash` of any older
  closed record is 0. `apply_due` reads only active positions. No guard needed.
- **returnPct on close.** With dividends: `((exit − entry) × shares + div) /
  (entry × shares)`. Without: the old formula, byte-for-byte, so no historical
  rounding can shift.
- **送转 arithmetic.** shares floored with a 1e-6 epsilon (`1700 × 1.4` is
  2379.999… in float); entryPrice kept to 6 dp, not 2, because the snapshot
  recomputes cost as `shares × entryPrice` (it does not read the stored
  `allocatedCapital`). Test: cash before == cash after ±0.01.
- **Cash + 送转 in one event.** Cash is paid on the pre-bonus (record-date)
  holding.
- **BONUS_IT_RATIO** is the combined 送+转 (000739's 2007 row: 送3 转2 → 5);
  BONUS_RATIO / IT_RATIO are not used.
- **Not modelled:** the 1元-par tax on 送股 (bonus shares from profit, not
  转增) — owner rule covers cash dividends only; flagged for review.
- **Empty vs failed fetch.** eastmoney answers "no rows" with success=false,
  code 9201 → `[]`. Any other failure → `None` → loud degradation, book
  untouched, next run retries.
