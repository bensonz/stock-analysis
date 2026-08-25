# iFinD options-data evaluation — 2026-08-25

**Verdict: yes for SSE ETF options, no for CFFEX index options.**

Everything an options companion app needs on 50ETF/300ETF — chain enumeration,
bid/ask with 5-level depth, open interest, implied volatility, the full greek
set, and **per-contract daily history back to 2015-02-09** — is available and
internally consistent. That last item is the one AKShare cannot do at all.

CFFEX (IO/MO/HO index options) is blocked by seat entitlement, not by anything
technical. This is a purchasing question, not an engineering one.

Reproduce with `ifind_options_probe.py` in this directory (section names in
brackets below). Total cost of the whole evaluation: **~31,500 dataVol**.

Read `IFIND_API_GUIDE.md` first — the envelope shape, the `indipara` vs
`indicators` split, and the error-code semantics all carry over unchanged.

---

## 1. The code format — the key unlock  [`codes`, `scan`]

SSE ETF option contracts are addressed by a **plain 8-digit numeric code with a
`.SH` suffix**, e.g. `10011000.SH`. Nothing else works:

| Code tried | Result |
|---|---|
| `10011000.SH` | ✅ live quotes |
| `510300P2609M04500.SH` | `-4210` |
| `510300P2609M04500` | `-4210` |
| `IO2609-C-4000.CFE` | `-4216` — real code, no entitlement |
| `IO2609-C-4000.CFFEX` | `-4210` — wrong suffix |
| `90000001.SZ` | parses, never any data (see §7) |

The human-readable form (`510300P2609M04500`) is **output-only** — it comes back
from `ths_option_code_option` but is not accepted as input.

### Reading the error codes during discovery

This distinction is what makes discovery cheap, and it is worth internalising:

- **`-4210`** — the string is not a parseable instrument code. Nothing with that
  number exists or ever will.
- **empty `tables`** (`-4001` normalised by the client) — the code parses and
  names a real contract, but it is not currently quoting (expired, or not yet
  listed).
- **`-4216`** — the code is real, the seat lacks the exchange entitlement.

All three cost **0 dataVol**, so scanning a numeric range for the live block is
free. Only calls that return actual values are metered.

### Locating the live block

Codes are allocated in listing order, so the live block is contiguous and
**moves upward over time**. On 2026-08-25 it was `10010500` – `10012308`
(1,809 contracts). Rediscover it by scanning rather than hardcoding it:

```python
for start in range(10004000, 10013000, 500):
    codes = [f"{n}.SH" for n in range(start, start + 500)]
    tables = client.real_time(codes, "latest")   # -4210 => past the top
```

The 1,809 contracts break down as:

| Underlying | Name | Contracts |
|---|---|---|
| `510050` | 50ETF | 288 |
| `510300` | 300ETF | 308 |
| `510500` | 500ETF | 456 |
| `588000` | 科创50ETF | 383 |
| `588080` | 科创板50ETF | 374 |

---

## 2. Contract metadata — `basic_data_service`  [`meta`]

A `ths_*_option` indicator family exists and takes a date parameter. This is how
you enumerate a chain: strike, expiry, and call/put all come from here.

```json
{"codes": "10011000.SH",
 "indipara": [{"indicator": "ths_strike_price_option", "indiparams": ["2026-08-25"]}]}
```

Verified working, with the value returned for `10011000.SH`:

| Indicator | Returns |
|---|---|
| `ths_option_code_option` | `510300P2609M04500` |
| `ths_option_short_name_option` | `300ETF沽9月4500` |
| `ths_underlying_code_option` | `510300` (bare, no suffix) |
| `ths_contract_type_option` | `看跌期权` / `看涨期权` |
| `ths_strike_price_option` | `4.5` |
| `ths_maturity_date_option` | `20260923` |
| `ths_listed_date_option` | `20260129` |
| `ths_contract_multiplier_option` | `10000` |
| `ths_implied_volatility_option` | `0.1975` |
| `ths_delta_option` `ths_gamma_option` `ths_theta_option` `ths_vega_option` `ths_rho_option` | greeks |
| `ths_time_value_option` | `0.0582` |

`ths_stock_short_name_stock` and `ths_listed_date_stock` also work on option
codes, returning the same values as their `_option` counterparts.

Plausible names that return **`-4210`** — the naming is not guessable, so verify
each one before relying on it: `ths_iv_option`, `ths_expire_date_option`,
`ths_expiry_date_option`, `ths_last_trade_date_option`, `ths_option_type_option`,
`ths_call_or_put_option`, `ths_exercise_price_option`, `ths_strike_option`,
`ths_contract_unit_option`, `ths_theoretical_price_option`,
`ths_intrinsic_value_option`, `ths_leverage_option`, `ths_exercise_type_option`,
`ths_underlying_security_code_option`, `ths_option_name_option`.

Enumerating all 1,809 contracts with four metadata indicators costs **7,260
dataVol** and takes a few seconds. The contract set only changes when a new
expiry lists, so cache it.

---

## 3. Real-time quotes  [`chain`]

`real_time_quotation` works on option codes with the ordinary equity indicator
names, plus options-specific ones:

```json
{"codes": "10011000.SH",
 "indicators": "latest,bid1,ask1,bidSize1,askSize1,volume,openInterest,settlement,impliedVolatility,delta,gamma,theta,vega,rho"}
```

Verified fields: `latest`, `open`, `high`, `low`, `preClose`, `volume`, `amount`,
`bid1`–`bid5`, `ask1`–`ask5`, `bidSize1`, `askSize1`, **`openInterest`**,
`preSettlement`, `settlement`, `changeRatio`, `impliedVolatility`, `delta`,
`gamma`, `theta`, `vega`, `rho`.

A full front-month 50ETF chain (28 contracts × 14 indicators) costs **392
dataVol** and returns in well under a second. A snapshot of the entire 1,809-
contract universe with 10 indicators costs **18,090 dataVol**.

> ⚠️ **Unknown indicator names are silently dropped here, not rejected.**
> `open_interest` and `positionChange` produce no error and no column — unlike
> `basic_data_service`, where one bad name `-4210`s the whole request. Assert on
> the columns you got back rather than trusting the request to fail loudly.

Real-time calls on an expired contract return an empty `tables` list, cleanly.

---

## 4. History — the decisive capability  [`history`]

`cmd_history_quotation` serves per-contract daily bars **including settlement
price and open interest**, which is exactly the shape a companion app needs:

```json
{"codes": "10011000.SH",
 "indicators": "open,high,low,close,volume,amount,openInterest,settlement,preSettlement,changeRatio",
 "startdate": "2026-08-18", "enddate": "2026-08-25",
 "functionpara": {"Fill": "Original"}}
```

```json
{"thscode": "10011000.SH",
 "time": ["2026-08-18", …, "2026-08-25"],
 "table": {"close": [0.0251, 0.057, 0.05, 0.0418, 0.0595, 0.0582],
           "openInterest": [27880, 35078, 36359, 37120, 40151, 42242],
           "settlement": [0.0251, 0.057, 0.05, 0.0418, 0.0595, 0.0582],
           "volume": [17432, 38010, 12936, 14984, 36895, 22601], …}}
```

Three things make this usable where AKShare is not:

1. **Expired contracts keep their full history.** Contracts that expired in
   December 2025, February 2026 and July 2026 all returned complete bars for
   their trading life — 6/6 codes in each sample.
2. **Depth reaches the first day of the market.** `10000001.SH` returns
   `2015-02-09` close `0.1826`, open interest `674` — day one of 50ETF options.
3. **IV and greeks are available as a historical series** through
   `date_sequence`, on expired contracts too. This is what lets you rebuild a
   historical volatility surface:

```json
{"codes": "10011000.SH",
 "indipara": [{"indicator": "ths_implied_volatility_option", "indiparams": [""]},
              {"indicator": "ths_delta_option", "indiparams": [""]}],
 "startdate": "2026-08-18", "enddate": "2026-08-25",
 "functionpara": {"Fill": "Original"}}
```

Remember `indipara`, not `indicators` (guide §4.1).

**Intraday** works too: `high_frequency` returns 1/5/15/60-minute bars for an
option contract with the same payload shape as for equities.

> A contract only has bars inside its own listing window. Querying a code
> outside that window returns `time: []` with null columns — which looks
> identical to "no such contract". Pull `ths_listed_date_option` and
> `ths_maturity_date_option` first and clamp your date range to them, or you
> will misread live gaps as missing data. This cost real time during the probe.

---

## 5. Data quality — put-call parity holds  [`parity`]

The strongest available internal check: `C - P - (S - K)` must be the *same
constant* at every strike, because it is just the discount/carry term. A
residual that wandered strike to strike would mean mismatched strikes, types, or
prices.

50ETF, expiry 2026-09-23, 14 strikes, settled closes on 2026-08-25, S = 2.982:

| | value |
|---|---|
| residual mean | **−0.00764** |
| residual stdev | **0.00156** |
| residual range | −0.0109 … −0.0052 |

Flat to within a sixth of a cent across strikes spanning 2.65–3.60. The strikes,
call/put flags, and prices line up. Bid/ask spreads, open-interest profile
(peaking at the 3.00–3.10 strikes) and the delta ladder all read like a real
chain.

---

## 6. The one real data trap: real-time greeks collapse on deep ITM  [`iv`]

`real_time_quotation`'s `impliedVolatility` and greeks **degenerate on deep
in-the-money calls**, while the `basic_data_service` indicators stay correct for
the same contract, same instant:

| Contract | K | IV (real_time) | IV (basic_data) | delta (real_time) | delta (basic_data) |
|---|---|---|---|---|---|
| `10011255.SH` | 2.65 | **0.0001** | 0.2286 | **1.0** | 0.9658 |
| `10011256.SH` | 2.70 | **0.0001** | 0.1975 | **1.0** | 0.9616 |
| `10011233.SH` | 2.75 | **0.0001** | 0.1711 | **1.0** | 0.9515 |
| `10011215.SH` | 2.80 | **0.0001** | 0.1441 | **1.0** | 0.9365 |
| `10010971.SH` | 2.85 | 0.0956 | 0.1338 | 0.9556 | 0.8808 |
| `10010974.SH` | 3.00 | 0.1311 | 0.1381 | 0.4542 | 0.4395 |
| `10010976.SH` | 3.20 | 0.1627 | 0.1659 | 0.0711 | 0.0699 |

4 of 28 contracts affected on this chain. The signature is unmistakable: IV
pinned at exactly `0.0001`, delta at exactly `1.0`, gamma and vega at `0.0`.

It is **not** caused by requesting too many indicators — asking for
`impliedVolatility` alone reproduces it exactly. It is a property of the
real-time analytics feed.

Two traps to guard against:

- `0.0001` is **truthy**, so a `if not iv:` guard will not catch it. Test
  `iv < 0.01` against a contract you know is deep ITM. A naive zero-check gave a
  false all-clear during this probe before the values were inspected directly.
- Near expiry the degeneracy spreads. On the 1-day-to-expiry 2026-08-26 chain,
  IV came back as `0.000`, `1.061`, and `0.661` on adjacent strikes. Treat
  same-week IV as unusable regardless of source.

**Recommendation:** take prices, sizes, volume and open interest from
`real_time_quotation`, but take IV and greeks from
`basic_data_service`/`date_sequence` (`ths_*_option`). That also keeps the live
and historical analytics on one consistent model, which matters if you plot
today's smile against last month's.

---

## 7. Gaps

### CFFEX index options — blocked by entitlement  [`cffex`]

Every CFFEX instrument returns **`-4216 Permission denied for CFFEX security`**,
across `real_time_quotation`, `cmd_history_quotation` *and*
`basic_data_service`. The `IF2609.CFE` **futures** control fails identically, so
this is a blanket exchange entitlement on the seat, not an options-specific or
format-specific problem.

The code format is confirmed correct by the error itself: `IO2609-C-4000.CFE`
returns `-4216` (real instrument, denied) while `IO2609-C-4000.CFFEX` and
`IO2609C4000.CFE` return `-4210` (unparseable). So **`{SERIES}{YYMM}-{C|P}-{STRIKE}.CFE`**
is the shape to use if the entitlement is ever purchased. `MO2609-C-6000.CFE`
returned `-4210` — that strike simply doesn't exist on that series, which is a
further confirmation the parser is real.

**IO/MO/HO index options are unavailable today, and only a commercial change
unlocks them.**

### SZSE ETF options — not found

SZSE-listed ETF options (300ETF on `159919`, ChiNext on `159915`) were not
located. `9000xxxx.SZ` parses without `-4210` but never returns data across
`90000000`–`90005200` on either `real_time_quotation` or
`cmd_history_quotation`. Either the seat lacks SZSE option data or the code
range is different. **Unresolved** — it did not block the SSE evaluation, and
50ETF/300ETF (the companion project's targets) are both SSE.

### Discovery has no catalogue endpoint

There is no "list the chain for this underlying" call.

- **`smart_stock_picking` (iwencai) is useless here.** `50ETF期权` returns 50
  *stocks* — index constituents. As the guide notes, `searchtype` is ignored;
  it is a stock screener and there is no options mode.
- **`data_pool`** returned nothing for every `reportname` guessed
  (`p00868`, `option`, `optionchain`, `p03291`, `p00500`, `期权`), consistent
  with the guide's §13 open question.

The numeric range scan in §1 is the working substitute. It is cheap and
reliable, but it is a scan — budget for rediscovering the block boundaries
periodically rather than assuming today's constants hold.

### Not found

- **iVIX / a China volatility index.** `000188.SH` and `IVIX.SH` both `-4210`.
  Not located; would have to be computed from the chain.
- **Exercise/assignment and settlement-calendar data.** No indicator found.
  `ths_maturity_date_option` gives the expiry date, which covers the common need.

---

## 8. Cost

| Operation | dataVol |
|---|---|
| Range scan for the live code block | **0** (errors and empties are free) |
| Enumerate all 1,809 contracts, 4 metadata indicators | 7,260 |
| One 28-contract chain snapshot, 14 indicators | 392 |
| Full 1,809-contract snapshot, 10 indicators | 18,090 |
| 6 days of daily bars, one contract, 10 fields | ~60 |
| Whole evaluation in this document | **~31,500** |

Sizing a companion app: snapshotting **only 50ETF + 300ETF** (596 contracts ×
~10 indicators ≈ 6,000 dataVol) every 5 minutes over a 4-hour session is roughly
**290k dataVol/day** — an order of magnitude above the ~42k/day the equity
universe update costs in `FINDINGS.md`. Polling only the front two expiries, or
every 15 minutes instead of 5, brings it back into the same range. **The account
ceiling is still unknown and unreadable via API** (`data_statistics` 404s), so
meter `IFindClient.data_vol` and check the vendor portal before committing to a
polling cadence.

---

## 9. Bottom line for the companion project

| Requirement | iFinD | AKShare |
|---|---|---|
| Chain enumeration (strike/expiry/type) | ✅ via `ths_*_option` | ✅ |
| Bid/ask + depth | ✅ 5 levels | partial |
| Open interest | ✅ live and historical | current day |
| IV + greeks | ✅ (use `basic_data`, not real-time) | ✅ current day |
| **Per-contract daily history** | ✅ **back to 2015-02-09** | ❌ |
| **Historical IV / greeks series** | ✅ via `date_sequence` | ❌ |
| Intraday bars per contract | ✅ 1/5/15/60 min | ❌ |
| CFFEX index options (IO/MO/HO) | ❌ entitlement | ✅ |
| SZSE ETF options | ❌ not located | ✅ |

**iFinD should replace AKShare for 50ETF and 300ETF**, which is where the
companion project's course content and examples live. It removes the single
hardest constraint in the current design — that AKShare only serves current-day
data, which is why the project needs a 5-minute snapshot scheduler purely to
accumulate history it can never backfill. With iFinD that history already exists
and can be pulled on demand.

**Keep AKShare** for CFFEX index options and SZSE ETF options until the
entitlement question is settled. A source-per-market split is the honest shape
here; do not present it as a full migration.

One integration note carried over from `FINDINGS.md` §Accuracy: `volume` is in
**shares** on `cmd_history_quotation`/`high_frequency` but **lots** on
`real_time_quotation`. For options the natural unit is contracts (张) — verify
which one you are getting before wiring it to a position size.
