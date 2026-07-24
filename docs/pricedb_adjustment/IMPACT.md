# Adjustment-factor impact report — "how wrong were we?"

Date: 2026-07-24. Comparison: RPS on 2026-07-22 (pre-image snapshot of the old
unadjusted cache, `rps_preimage.json`) vs the same date recomputed with sina
hfq adjustment factors. 4,996 stocks, factors covering 100% of the non-BJ
universe (300 BJ codes deliberately unfactored = unchanged).

## Headline numbers

| Metric | Value |
|---|---|
| Mean absolute RPS move | **3.83 percentile points** |
| Stock-metrics moved >1 pt | 11,664 |
| Stock-metrics moved >5 pt | **1,677** |
| RPS-gate passers (all three ≥80) | 601 → 621 |
| Stocks ENTERING the pool | **57** |
| Stocks LEAVING the pool | **37** |

**≈9% of the screened pool was wrong.** 57 stocks with genuine momentum were
being excluded because their dividends/送转 read as price crashes; 37 stocks
were passing only because *other* stocks were being unfairly penalized.

## The catastrophic tail (top movers)

| Stock | Metric | Old → New | Δ |
|---|---|---|---|
| 301550 | rps250 | 15.1 → 91.2 | **+76.1** |
| 301550 | rps120 | 19.4 → 88.6 | +69.1 |
| 001298 | rps250 | 11.7 → 77.6 | +65.9 |
| 301031 | rps250 | 17.6 → 83.2 | +65.5 |
| 688697 | rps250 | 8.4 → 73.3 | +64.9 |

These are 送转/large-dividend names: a 10送10 halves the raw price, so the old
data read them as −50% crashes and buried them at the bottom of the momentum
ranks — top-decile stocks ranked in the bottom quintile. This is the
missed-opportunity failure mode at its worst.

## Deep-report subjects re-checked (2026-07-22 values)

| Stock | rps60 | rps120 | rps250 | Verdict impact |
|---|---|---|---|---|
| 002832 比音勒芬 | 94.1→93.7 | 88.8→88.7 | 73.5→**74.6** | none — rps250 still <80; "长期动量未确认" stands |
| 301345 涛涛车业 | 89.1→88.2 | 85.7→84.7 | 97.9→97.7 | none — still passes the gate |
| 688378 奥来德 | 91.8→90.8 | 94.8→94.3 | 94.3→95.7 | none — still passes; "对但早" unaffected |

Honest correction to the morning's hypothesis: 002832's own series was indeed
distorted ~4–6% by its two ex-dividends, but RPS is *cross-sectional* — most
peers also paid dividends, so relative ranks moved only ~1 point. Individual
distortion ≠ rank distortion. The systematic victims were the *extreme*
corporate-action names above, not moderate dividend payers.

## Rollout record

- Factor source: sina `hfq.js` (direct factor series; 5,167 codes OK, 45 fails
  = BJ tail). Validated against 002832's ¥0.7 dividend: ex-day factor ratio
  1.03457 (4-decimal match).
- Eastmoney kline derivation retained as fallback; its WAF connection-kills
  bulk fetches from any IP (~60 codes/burst — home, VPS, and Aliyun all
  tripped) — unusable as a bulk source.
- 51 premature factor rows (from forming-bar derivations during the tunnel
  attempts) deleted; daily f18 sync recreates them properly.
- `factors verify`: 100% factored-universe coverage, dates aligned, OK.
- rps_cache fully invalidated and recomputed (2026-07-22 + 2026-07-23).
- First live screen on adjusted data: the 2026-07-24 15:35 afternoon run.

## Follow-ups

- Per-stock missing trading days discovered during validation (002832: 12 of
  19 days in a June window; the daily coverage cursor guarantees 90% of stocks
  per day but never repairs the residual per-stock holes). Needs a per-stock
  gap-repair sweep. Likely explains occasional RPS dropouts.
- BJ codes stay unfactored (sina unsupported) — acceptable: BJ names rarely
  clear the momentum gate; revisit if that changes.
