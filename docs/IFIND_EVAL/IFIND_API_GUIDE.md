# iFinD (同花顺 quantapi) HTTP API — practical guide

Everything here was verified against the live API on **2026-08-25** with a paid
seat. Where something is unverified it says so explicitly — nothing below is
inferred from the vendor's docs alone.

This document is **self-contained and portable**. It has no dependency on the
repo it lives in; you can hand it to another project as-is.

> **Ignore the Windows PDFs.** 《同花顺数据接口用户手册-windows》 documents the
> Windows-only SuperCommand DLL (`THS_iFinDLogin`, `iFinDPy`, registry install).
> None of it applies to the HTTP API, and the function names don't map 1:1 to
> endpoint names. Use this guide instead.

---

## 1. Access model

Base URL: `https://quantapi.51ifind.com/api/v1/`

Two tokens:

| Token | Lifetime | Where it lives |
|---|---|---|
| **refresh token** | long-lived | your credential store (e.g. `.env`) |
| **access token** | ~7 days | derived; cache it, don't refetch per call |

Username/password are **not** used by the HTTP API. The refresh token alone is
sufficient.

### Get an access token

```bash
curl -s -X POST https://quantapi.51ifind.com/api/v1/get_access_token \
  -H "ContentType: application/json" \
  -H "refresh_token: $IFIND_REFRESH_TOKEN"
```

```json
{"errorcode":0,"errmsg":"success",
 "data":{"access_token":"deffb680a859…","expired_time":"2026-09-01 17:36:00"}}
```

Note the request header is `ContentType` (no hyphen) on this endpoint
specifically — that is what the vendor expects here. Every *other* endpoint uses
the normal `Content-Type: application/json`.

### Authenticate a data call

```bash
curl -s -X POST https://quantapi.51ifind.com/api/v1/cmd_history_quotation \
  -H "Content-Type: application/json" \
  -H "access_token: $AT" \
  -d '{"codes":"600519.SH","indicators":"open,close","startdate":"2026-08-25","enddate":"2026-08-25","functionpara":{"Fill":"Original"}}'
```

**Refresh before expiry, not on failure.** Give yourself a margin (we use 6 h) so
a long batch job can't straddle the boundary mid-flight.

---

## 2. Response envelope

Every data endpoint returns the same outer shape:

```json
{
  "errorcode": 0,
  "errmsg": "",
  "tables": [
    {"thscode": "600519.SH",
     "time":  ["2026-08-25"],
     "table": {"open": [1311.89], "close": [1304.0]}}
  ],
  "dataVol": 12,
  "perf": 63
}
```

- **`tables` is column-major.** `table` maps field name → array, parallel to
  `time`. Index `i` across all arrays is one bar.
- **One entry per code**, keyed by `thscode`.
- **`dataVol`** is the metered data volume for that call (≈ rows × indicators).
  There is no API endpoint that reports your remaining quota — `data_statistics`
  **404s** — so if you need to track consumption, sum `dataVol` yourself.
- **`perf`** is server-side processing time in ms.

### Codes

`600519.SH`, `000001.SZ`, `830799.BJ`. Board→suffix rules:

| Prefix | Suffix | |
|---|---|---|
| `60`, `68`, `90` | `.SH` | **`688` (STAR) is SH** — test `6` before `8` |
| `00`, `30`, `20` | `.SZ` | |
| `43`, `83`, `87`, `88`, `92` | `.BJ` | |

Indices use the same form: `000001.SH` (上证指数), `399001.SZ` (深证成指),
`399006.SZ` (创业板指), `000688.SH` (科创50). All four verified returning.

---

## 3. Endpoint status

Verified live (HTTP 200, real data):

| Endpoint | Purpose | Params verified |
|---|---|---|
| `get_access_token` | auth | ✅ |
| `cmd_history_quotation` | daily bars | ✅ |
| `real_time_quotation` | live/settled quotes | ✅ |
| `basic_data_service` | point-in-time indicators | ✅ |
| `date_sequence` | indicator time series | ✅ |
| `high_frequency` | intraday bars (1/5/15/60 min) | ✅ |
| `snap_shot` | tick-level intraday (~3 s) | ✅ |
| `smart_stock_picking` | iwencai NL screener | ✅ |
| `edb_service` | macro/EDB series | endpoint OK, indicator IDs not determined |
| `report_query` | announcements | endpoint OK, **params return -4210** |
| `data_pool` | 数据池 (板块成分, 涨停池…) | endpoint OK, **`reportname` codes not determined** |

Returns **HTTP 404** (do not exist on this API): `data_statistics`,
`date_query`, `date_offset`, `date_count`, `real_time_valuation`,
`special_shape_predict`, `user_info`.

---

## 4. The traps

These cost the most time because **they fail silently or misleadingly**.

### 4.1 `date_sequence` takes `indipara`, not `indicators`

Same concept, different key. Using `indicators` returns `-4210`.

```jsonc
// cmd_history_quotation — flat string
{"codes":"600519.SH", "indicators":"open,close", "startdate":"…","enddate":"…"}

// date_sequence / basic_data_service — list of dicts
{"codes":"600519.SH",
 "indipara":[{"indicator":"ths_af_stock","indiparams":[""]}],
 "startdate":"…","enddate":"…"}
```

### 4.2 Indicator param ORDER matters, and the wrong order returns `""`

`ths_the_sw_industry_stock` takes `[level, date]`:

```jsonc
{"indicator":"ths_the_sw_industry_stock","indiparams":["1","2026-08-25"]}  // → "食品饮料"
{"indicator":"ths_the_sw_industry_stock","indiparams":["2026-08-25","1"]}  // → ""   ← no error!
```

The reversed form returns `errorcode: 0` with an empty string. If you aggregate
by industry, you silently get zero sectors instead of a failure.

### 4.3 Volume units differ **between endpoints**

| Endpoint | `volume` unit |
|---|---|
| `cmd_history_quotation` | **shares (股)** |
| `high_frequency` | **shares (股)** |
| `real_time_quotation` | **lots (手)** — already ÷100 |

Verified on 600519 for 2026-08-25: history `2111118` shares vs real-time
`21111` lots. Getting this wrong is a silent 100× error. `amount` is 元
everywhere.

### 4.4 One bad indicator fails the WHOLE request

`basic_data_service` with five good indicators and one typo returns `-4210`
for all six. Validate indicator names individually before batching.

### 4.5 `errorcode: -4001` is not an error

It means "no data" — a query that legitimately matched nothing. Treat it as an
empty result, not a fault, or you'll fail runs over empty screens.

---

## 5. Daily bars — `cmd_history_quotation`

```json
{"codes": "600519.SH,000001.SZ",
 "indicators": "open,high,low,close,volume,amount,changeRatio,turnoverRatio",
 "startdate": "2026-08-18", "enddate": "2026-08-25",
 "functionpara": {"Fill": "Original"}}
```

**Adjustment** via `functionpara.CPS`:

| Value | Meaning |
|---|---|
| absent or `"1"` | 不复权 (raw) — the default |
| `"2"` | 前复权 (forward-adjusted) |

Verified on 603558 across its 2026-08-25 ex-dividend:
raw `[12.07, 11.85, 12.19, 11.78]` vs `CPS:2`
`[11.789…, 11.574…, 11.906…, 11.78]`.

`Fill`: `"Original"` leaves non-trading days out; `"Previous"` forward-fills.
For anything computing returns, use `Original` — filled bars fake flat sessions.

**History depth:** verified back to at least **2005-01-04**.

**Throughput:** ≥800 codes per request (server `perf` 111 ms at 800). The full
5207-code A-share universe for one session: **2.4 s** using 200-code chunks and
6 threads, 0 failures. 31,215 bars across 6 sessions: 2.8 s.

---

## 6. Real-time — `real_time_quotation`

```json
{"codes": "600519.SH", "indicators": "latest,open,high,low,preClose,volume,amount"}
```

```json
{"thscode":"600519.SH","time":["2026-08-25 16:01:08"],
 "table":{"latest":[1304.0],"preClose":[1304.66],"volume":[21111.0], …}}
```

After the close this carries the **settled** bar — verified matching the
official close on 131/131 sampled codes. The `time` field is the feed's own
timestamp; use it to reject stale lines (a suspended name keeps returning its
last session) and pre-close prints. Full universe: **0.5 s**.

---

## 7. Intraday — `high_frequency` and `snap_shot`

```json
{"codes": "600519.SH", "indicators": "open,high,low,close,volume,amount",
 "starttime": "2026-08-25 09:30:00", "endtime": "2026-08-25 15:00:00",
 "functionpara": {"Fill": "Original", "Interval": "1"}}
```

`Interval` is in minutes. Verified for one full session on 600519:

| Interval | Bars | dataVol |
|---|---|---|
| `1` | 241 | 1,446 |
| `5` | 48 | 288 |
| `15` | 16 | 96 |
| `60` | 4 | 24 |

`snap_shot` returns **tick-level** data (~3 s granularity, timestamps like
`09:15:05`, including the pre-auction). It is expensive: **dataVol 26,015 for
one stock for one day** — roughly 18× a full day of 1-minute bars. Use
`high_frequency` unless you genuinely need ticks.

---

## 8. Point-in-time indicators — `basic_data_service`

```json
{"codes": "600519.SH",
 "indipara": [{"indicator": "ths_stock_short_name_stock", "indiparams": ["2026-08-25"]}]}
```

Verified working (with the exact `indiparams` shown):

| Indicator | Params | Returns (600519) |
|---|---|---|
| `ths_stock_short_name_stock` | `["2026-08-25"]` | `贵州茅台` |
| `ths_listed_date_stock` | `["2026-08-25"]` | `20010827` |
| `ths_market_value_stock` | `["2026-08-25"]` | `1630106407704.0` |
| `ths_pe_ttm_stock` | `["2026-08-25"]` | `20.017519751628` |
| `ths_af_stock` | `["2026-08-25"]` | `5.1505939764` (adjustment factor) |
| `ths_the_sw_industry_stock` | `["1","2026-08-25"]` | `食品饮料` — **[level, date]** |

Confirmed **not** valid (all return `-4210`): `ths_adjust_factor_stock`,
`ths_total_market_value_stock`, `ths_free_float_market_value_stock`,
`ths_industry_stock`, `ths_sw_level1_stock`, `ths_st_stock`,
`ths_belong_industry_stock`. Indicator naming is not guessable — verify each one
individually against a known stock before relying on it.

### Adjustment factors

`ths_af_stock` is iFinD's cumulative factor, available as a series via
`date_sequence`. Compared against 20 months of independently-derived factors,
the **step ratios** across 2026-08-25's six ex-dividend names matched to
0.00 bp on five, and differed 3.12 bp on one (603558).

> **Its base is anchored at listing.** If you already maintain factors anchored
> elsewhere, do not splice iFinD's absolute values into an existing series —
> that fabricates a return on the splice date. Either import the **ratio**
> (`af[t]/af[t-1]`) or rebuild a code's whole series and renormalize.

Because it's an *exact published* factor rather than an inference, don't apply a
noise threshold to it. A 0.5% floor (reasonable for factors reverse-engineered
from prev-close) would have discarded 4 of those 6 real dividends, whose steps
were 1.0021–1.0039.

---

## 9. Indicator time series — `date_sequence`

```json
{"codes": "603558.SH",
 "indipara": [{"indicator": "ths_af_stock", "indiparams": [""]}],
 "startdate": "2026-08-14", "enddate": "2026-08-25",
 "functionpara": {"Fill": "Original"}}
```

Any `basic_data_service` indicator can generally be pulled as a series this way.
Remember `indipara`, not `indicators` (§4.1).

---

## 10. Natural-language screening — `smart_stock_picking` (iwencai)

The most distinctive capability. It parses Chinese natural language and returns
matching stocks **plus automatically-chosen relevant columns**.

```json
{"searchstring": "RPS120大于80 且 RPS250大于80 且 MA20大于MA120", "searchtype": "stock"}
```

Verified results (2026-08-25):

| Query | Rows | Columns returned |
|---|---|---|
| `今日涨停 非ST 非新股` | 65 | 代码, 简称, 涨停, 上市交易日天数 |
| `RPS120大于80 且 RPS250大于80 且 MA20大于MA120` | 125 | + 收盘价, 20日均线, 120日均线, 差值 |
| `今日涨幅大于5% 换手率大于5% 量比大于2 流通市值小于200亿` | 58 | + 涨跌幅, 换手率, 量比, 流通市值 |
| `所属同花顺行业 涨幅排名前10的行业` | 861 | + 行业, 行业排名 (`1/55`), 排名基数 |

Cheap: `dataVol` 260–6,888 per query.

### iwencai gotchas

- **`searchtype` is ignored.** `stock`, `zhishu`, `block`, `industry` all return
  byte-identical stock-level rows. There is no sector-level mode — aggregate
  client-side by grouping on `所属同花顺行业`.
- **Column names embed the query date**: `涨跌幅:前复权[20260825]`. Strip
  `\[\d{8}\]` if you want stable keys across days.
- **Column names follow your phrasing.** Asking `上市天数大于60` yields a column
  called `上市天数`; other phrasings yield `上市交易日天数`. Match loosely.
- **Results exceed the tradeable universe** (5548 rows vs 5207 with bars) —
  suspended and other listings are included.
- **Debut-day outliers**: one row printed `+282.98%` on its first session.
  Filter on listed-days.
- Output is column-major like every other endpoint, but has **no `thscode`** —
  the code is a column (`股票代码`) instead.

---

## 11. Error codes

| Code | Meaning | What to do |
|---|---|---|
| `0` | success | — |
| `-4001` | `no data.` | **Not an error** — empty result |
| `-4210` | bad input parameters | Wrong indicator name, wrong param order/count, or `indicators` where `indipara` was required. A programming error — surface it, don't retry |
| HTTP 404 | endpoint doesn't exist | See §3 |

Auth-expiry codes weren't reproduced during testing (the token stayed valid), so
treat refresh-on-auth-failure as a belt-and-braces path, not a verified one.

---

## 12. Minimal client

Copy-pasteable, no dependencies beyond `requests`:

```python
import json, time, requests

BASE = "https://quantapi.51ifind.com/api/v1/"

class IFind:
    def __init__(self, refresh_token):
        self.rt = refresh_token
        self.at = None
        self.expires = 0
        self.data_vol = 0

    def token(self):
        if self.at and time.time() < self.expires - 6 * 3600:
            return self.at
        r = requests.post(BASE + "get_access_token",
                          headers={"ContentType": "application/json",
                                   "refresh_token": self.rt}, timeout=60).json()
        if r.get("errorcode"):
            raise RuntimeError(f"auth failed: {r}")
        self.at = r["data"]["access_token"]
        self.expires = time.mktime(time.strptime(r["data"]["expired_time"],
                                                 "%Y-%m-%d %H:%M:%S"))
        return self.at

    def post(self, endpoint, payload):
        r = requests.post(BASE + endpoint, json=payload, timeout=60,
                          headers={"Content-Type": "application/json",
                                   "access_token": self.token()})
        if r.status_code == 404:
            raise RuntimeError(f"{endpoint}: no such endpoint")
        body = r.json()
        code = body.get("errorcode", body.get("errcode"))
        if code == -4001:                      # "no data" is an empty result
            return {"tables": [], "dataVol": 0}
        if code:
            raise RuntimeError(f"{endpoint}: errorcode={code} {body.get('errmsg')}")
        self.data_vol += body.get("dataVol") or 0
        return body

    def bars(self, codes, beg, end, indicators="open,high,low,close,volume,amount",
             cps=None):
        """Daily bars. NOTE: volume is in SHARES here."""
        fp = {"Fill": "Original"}
        if cps:
            fp["CPS"] = str(cps)
        return self.post("cmd_history_quotation",
                         {"codes": ",".join(codes), "indicators": indicators,
                          "startdate": beg, "enddate": end,
                          "functionpara": fp})["tables"]

    def iwencai(self, query):
        tables = self.post("smart_stock_picking",
                           {"searchstring": query, "searchtype": "stock"})["tables"]
        return tables[0]["table"] if tables else {}


def rows(table):
    """Column-major iFinD table → list of row dicts."""
    cols = table.get("table", {})
    n = len(table.get("time", []))
    return [{"time": table["time"][i],
             **{k: v[i] for k, v in cols.items() if i < len(v)}}
            for i in range(n)]
```

Usage:

```python
api = IFind(os.environ["IFIND_REFRESH_TOKEN"])
for bar in rows(api.bars(["600519.SH"], "2026-08-21", "2026-08-25")[0]):
    print(bar)
print("dataVol used:", api.data_vol)
```

Batch large universes at ~500 codes/request across ~6 threads; that
comfortably pulls all 5207 A-shares in about 2.4 s.

---

## 13. Open questions

Worth resolving if you need these:

- **`data_pool` `reportname` codes.** The endpoint is live but the report
  identifiers (for 涨停池, 板块成分, etc.) aren't published anywhere we found;
  guessed values return empty. Likely obtainable from the SuperCommand client's
  command generator or vendor support.
- **`report_query` parameters** — returns `-4210` for every shape tried.
- **`edb_service` indicator IDs** — endpoint responds, but the ID tried returned
  an empty series.
- **Quota.** No API surface reports it. If the seat has a ceiling, it must be
  read from the vendor portal; meter `dataVol` locally in the meantime.
