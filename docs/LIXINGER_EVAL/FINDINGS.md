# Lixinger (理杏仁) Open API — evaluation as iFinD replacement

_Evaluated 2026-09-28 with the `LIXINGER_TOKEN` in `.env`. Context: the iFinD
refresh token expired 2026-09-25 and will not be renewed._

## Verdict

Data quality and fit are good; **the token behaves like an unpurchased trial.**
After ~1000 successful calls `cn/company/candlestick` began returning
`403 "Exceed maximum access time, please purchase Open API."` while other
endpoints kept working — a per-API trial counter, exhausted by this evaluation's
bulk test. A daily full-universe pass needs ~5550 calls, so production use
requires a purchase.

| # | Use case | Verdict | Endpoint | Notes |
|---|---|---|---|---|
| 1 | Stock list | ⚠️ | `cn/company` | 5671 rows, pageSize 500 (12 calls, ~0.25s each). BJ = `920xxx` only; legacy 43/83/87 codes appear only as delisted, history lives under the 920 code. Documented `listingStatus` absent — ST only from name. Includes 79 B-shares, 21 never-listed (no `ipoDate`), 2 listing 09-29. |
| 2a | Per-stock OHLCV, 5y | ✅ | `cn/company/candlestick` | 1 code/call; 5y in one call (~0.5s); max span 10y. Universe × 5y ≈ 7 min at rate limit (once purchased). |
| 2b | Whole universe, one date | ⚠️ | `cn/company/fundamental/non_financial` | 100 codes/call → 56 calls, 4.3s, 5557 rows for 09-28. close/volume/amount matched all 5199 of our DB rows exactly. **No open/high/low.** |
| 2c | Same-evening availability | ✅ | both | 09-28 present at 21:25; exact publish time not measured. |
| 3 | Adj factors / ex-rights | ✅ | candlestick `complexFactor`, `dividend` | Ex-dates matched our factor steps 100% (10 codes × 1y sample), ratios within 0.05%. Resolves dividends down to 0.05%. |
| 4 | Index daily | ✅ | `cn/index/candlestick` | 000001 09-28 close = 3823.62. |
| 5 | Real-time / intraday | ❌ | — | No quote endpoint in the docs. Sina remains the noon source. |
| 6 | SW industry + sector change | ⚠️ | `cn/industry`, `constituents/sw_2021` | Full SW2021 membership in 1 call. No industry-index bars → sector change must be aggregated ourselves (as `_fetch_sectors_ifind` already does). |
| 7 | Trade calendar | ⚠️ | derive from 000001 bars | Historical only, no forward calendar (keep akshare's). |
| 8 | Extras | ✅ | fundamental | Turnover rate, market caps, PE/PB, margin, 陆股通 by date. No 量比. |
| 9 | Limits | ⚠️ | all | 1000 req/min, 36 req/s (HTTP 429), plus the per-API trial counter above. |

## Unit traps

- Volume is **股** → ÷100 to store 手.
- Amount is **元** (same as our DB).
- Stock `change` is a 4-decimal fraction and is the *adjusted* return on ex-dates.
- Index `change` is rounded to 2 decimals (−1.67% arrives as −0.02) — compute from closes.
- Empty result = `code: 1, "no data"`, not an error.
- The docs site returns `400 "you are robot"` to plain curl — needs a browser UA.

## Biggest gaps

1. **Must purchase** — trial counter (~1000 calls/API) is far below a ~5550-call universe pass. Check 我的接口 in a browser; re-probe candlestick on 09-29 to see if the counter resets daily.
2. No real-time quotes.
3. OHLC requires per-code calls (~6 min/day at rate limit); the cheap by-date path lacks open/high/low.
4. No industry-index bars.
5. Licence: personal, non-commercial use only.

## Side finding

pricedb has 5199 rows for 2026-09-28 (and 09-21) vs ~5537 normally — the 338
Beijing Exchange codes the sina real-time snapshot doesn't cover. Lixinger
returned 5557 for 09-28, so it could close that gap.

## Sources

- https://www.lixinger.com/api/open-api/url-doc
- https://www.lixinger.com/open/api/precaution
- Scratch scripts/captures (not in repo): `/private/tmp/lx*.py`, `/private/tmp/lx_*.json`
