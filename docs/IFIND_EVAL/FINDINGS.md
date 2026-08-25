# iFinD (同花顺 quantapi) data evaluation — 2026-08-25

**Verdict: the data is good.** Every accuracy check passed exactly. The open
question is commercial (quota), not technical.

Probe scripts in this directory are reproducible; they read `IFIND_*` from `.env`
and the local pricedb. Run order: `ifind_probe.py` (auth/endpoint surface) →
`ifind_eval_bars.py` → `ifind_throughput.py` → `ifind_final.py`.

## Access

- Auth is HTTP, **not** the Windows DLL. The two PDFs describe the Windows
  SuperCommand plugin (`THS_iFinDLogin`, `iFinDPy`), which is Windows-only and
  irrelevant to us. The usable surface is `https://quantapi.51ifind.com/api/v1/`.
- `POST /get_access_token` with header `refresh_token` → access token.
  Ours is valid to **2026-09-01** (~7 days), so a refresh-on-expiry helper is needed.
- `IFIND_USERNAME`/`IFIND_PASSWORD` are unused by the HTTP path — the refresh
  token alone is sufficient.
- Live endpoints (10): `basic_data_service`, `cmd_history_quotation`,
  `date_sequence`, `real_time_quotation`, `snap_shot`, `high_frequency`,
  `edb_service`, `data_pool`, `smart_stock_picking`, `report_query`.
  404: `date_query`, `date_offset`, `date_count`, `data_statistics`,
  `real_time_valuation`, `special_shape_predict`.

## Accuracy vs local pricedb

120-code stratified sample × 11 sessions (2026-08-11 → 08-25):

| metric | result |
|---|---|
| bars returned | 1320 / 1320 |
| close mismatches | **0** |
| OHLC mismatches | **0** |
| missing either side | 0 |

Real-time `latest` vs local settled close, 131 codes: **0 mismatches, 0 unusable.**

Unit note: iFinD `volume` is **shares**; our `daily_prices.volume` is **lots**
(÷100). Not a discrepancy, but a conversion any integration must apply.

## Adjustment factors

- `functionpara` default and `CPS:1` = 不复权 (raw) — matches our raw bars.
- `CPS:2` = 前复权.
- `ths_af_stock` exposes the factor directly (via `basic_data_service` point-in-time,
  or `date_sequence` with `indipara` shape for a series).

Step-ratio comparison on the six names that went ex-div 2026-08-25:

| code | local step | iFinD step | diff |
|---|---|---|---|
| 001231 | 1.007243 | 1.007243 | 0.00 bp |
| 300725 | 1.002067 | 1.002067 | 0.00 bp |
| 301391 | 1.002107 | 1.002107 | 0.00 bp |
| 301696 | 1.003920 | 1.003920 | 0.00 bp |
| 600620 | 1.002304 | 1.002304 | 0.00 bp |
| 603558 | 1.023510 | 1.023821 | **3.12 bp** |

Five of six agree exactly. The 603558 gap is one name, not a systematic offset —
but it means the two factor sets are **not interchangeable mid-series**. Adopt one
source wholesale or keep deriving our own; don't mix.

## Throughput

- Max codes per request: **≥800** tested clean (`perf` 111 ms at 800).
- **Full 5207-code universe, single day: 2.4 s, 0 chunk failures**
  (200/chunk, 6 threads, `dataVol` 41,656).

For comparison, today's `pricedb snapshot` path against sina takes ~30 s for the
same universe. History goes back to at least **2005-01-04**.

## Capabilities we don't currently have

- **`smart_stock_picking` (iwencai / 智能选股)** is the standout. It takes natural
  language and returns matching stocks *plus* auto-selected relevant columns:
  - `"今日涨停 非ST 非新股"` → 65 rows (code, name, 涨停 flag, 上市天数)
  - `"RPS120大于80 且 RPS250大于80 且 MA20大于MA120"` → 125 rows with the MA values
  - `"今日涨幅大于5% 换手率大于5% 量比大于2 流通市值小于200亿"` → 58 rows
  - `"所属同花顺行业 涨幅排名前10的行业"` → 861 rows with industry name, rank,
    and rank base (`1/55`) — i.e. sector-rotation data directly
  Cost is trivial (`dataVol` 260–6,888).
- Indices for breadth: `000001.SH`, `399001.SZ`, `399006.SZ`, `000688.SH` all return
  OHLC + `changeRatio`.
- Working `basic_data_service` indicators: `ths_market_value_stock`,
  `ths_pe_ttm_stock`, `ths_stock_short_name_stock`, `ths_listed_date_stock`,
  `ths_af_stock`.

## A gap this exposes in *our* data

`daily_prices.amount` is **almost entirely NULL** — 5172/5207 rows null on
2026-08-25, and >94% null on nearly every session in August. Only 08-21 and 08-24
are complete. iFinD returns `amount` with 100% coverage on the same bars.

**Verified mechanism** (traced 2026-08-25; an earlier guess blaming the snapshot
path plus `INSERT OR IGNORE` ordering was wrong and is corrected here):

- `snapshot_bars.parse_quote_line` **does** parse `amount` from sina's real-time
  feed (`snapshot_bars.py:109`), and `_akshare_hist_row_to_tuple` **does** carry
  `成交额` (`pricedb.py:1205`). Neither is the culprit.
- `_fetch_klines_sina` — the *kline* fallback provider — hardcodes `amount` to
  `None` (`pricedb.py:1998`), because sina's kline archive doesn't publish
  turnover. Its own docstring says so.
- So NULLs appear exactly on days where **both** better sources missed and the
  sina kline fallback did the filling. The manifests confirm it: 08-24 afternoon
  logged `0 → 5207 rows (5207 inserted)` from the snapshot and has 0 NULLs;
  08-25 afternoon logged `WARNING: 53 batch(es) failed` and has 5172 NULLs.

The read-through: `amount` coverage is a direct proxy for how often the free
chain has been degrading to its weakest provider — which in August was most
days. Independent of the iFinD decision, any turnover/liquidity screen reading
that column is silently degraded (today nothing does: `vcp_scanner.py:119`
selects it but never uses it).

## Unresolved

- **Quota is unknown and unmeasurable via API.** There is no `data_statistics`
  endpoint (404). Every response carries a `dataVol` field, so we can meter
  ourselves, but the account ceiling has to be read off the iFinD portal.
  Budget shape: universe daily bar update ≈ **42k dataVol/day** (×2 slots ≈ 83k);
  a full 250-session history backfill ≈ **10.4M** — that is the one call that
  could blow a trial allowance.
- Sector membership via `basic_data_service` — `ths_the_sw_industry_stock` returns
  empty and the ths-industry indicator names weren't found (`-4210`). Not blocking:
  iwencai returns `所属同花顺行业` reliably.
- Untested: `snap_shot`, `high_frequency`, `edb_service`, `report_query`,
  `data_pool` (needs correct `reportname` codes; guessed `p00868` returned no data).
