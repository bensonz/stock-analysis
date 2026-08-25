"""iFinD options-data probe — reproducible checks behind OPTIONS_FINDINGS.md.

Run a single section by name, or `all`:

    python3 docs/IFIND_EVAL/ifind_options_probe.py codes     # code-format discovery
    python3 docs/IFIND_EVAL/ifind_options_probe.py scan      # live contract range
    python3 docs/IFIND_EVAL/ifind_options_probe.py meta      # ths_*_option indicators
    python3 docs/IFIND_EVAL/ifind_options_probe.py chain     # build a 510050 chain
    python3 docs/IFIND_EVAL/ifind_options_probe.py history   # per-contract daily bars
    python3 docs/IFIND_EVAL/ifind_options_probe.py parity    # put-call parity audit
    python3 docs/IFIND_EVAL/ifind_options_probe.py iv        # real_time vs basic_data IV
    python3 docs/IFIND_EVAL/ifind_options_probe.py cffex     # CFFEX index options

Every section prints the dataVol it consumed. `scan` and `chain` are the
expensive ones (~3k and ~7k respectively); the rest are under 500 each.

Read-only: this script touches no project DB, config, or pipeline.
"""

from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import ifind_client  # noqa: E402

# The session these findings were recorded against.
TRADE_DATE = "2026-08-25"

# SSE ETF options occupy a contiguous 8-digit numeric range. Codes are allocated
# in listing order, so the live block moves upward over time — rediscover it with
# `scan` rather than hardcoding these in anything durable.
SSE_OPTION_LO = 10010500
SSE_OPTION_HI = 10012309

UNDERLYINGS = {"510050": "50ETF", "510300": "300ETF", "510500": "500ETF",
               "588000": "科创50ETF", "588080": "科创板50ETF"}

# real_time_quotation fields verified present on option contracts.
RT_QUOTE = ("latest,open,high,low,preClose,volume,amount,"
            "bid1,ask1,bidSize1,askSize1,openInterest,"
            "preSettlement,settlement,changeRatio")
RT_GREEKS = "impliedVolatility,delta,gamma,theta,vega,rho"

# cmd_history_quotation fields verified present on option contracts.
HIST_FIELDS = ("open,high,low,close,volume,amount,openInterest,"
               "settlement,preSettlement,changeRatio")

# basic_data_service / date_sequence indicators verified for options.
META_INDICATORS = ("ths_option_code_option", "ths_option_short_name_option",
                   "ths_underlying_code_option", "ths_contract_type_option",
                   "ths_strike_price_option", "ths_maturity_date_option",
                   "ths_listed_date_option", "ths_contract_multiplier_option")
ANALYTIC_INDICATORS = ("ths_implied_volatility_option", "ths_delta_option",
                       "ths_gamma_option", "ths_theta_option",
                       "ths_vega_option", "ths_rho_option",
                       "ths_time_value_option")

# Enumerating the chain costs ~7.3k dataVol, so cache it outside the repo tree
# rather than re-spending quota on every run.
CHAIN_CACHE = PROJECT_ROOT / "data" / "ifind_option_chain.json"


def _first(table: dict, key: str):
    values = table.get(key)
    return values[0] if values else None


def _rows(tables: list) -> dict:
    """thscode -> {field: first value}."""
    return {t["thscode"]: {k: _first(t.get("table") or {}, k)
                           for k in (t.get("table") or {})}
            for t in tables}


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def probe_codes(client):
    """Which option code formats does the API recognise?

    The distinction that matters: -4210 means the string is not a parseable
    instrument code, while an empty result means the code parses but names
    nothing currently quoting. -4216 means the code is real but the seat lacks
    the exchange entitlement.
    """
    candidates = [
        "10011000.SH",              # SSE ETF option, numeric  -> WORKS
        "510300P2609M04500.SH",     # SSE readable form        -> -4210
        "510300P2609M04500",        # readable, no suffix      -> -4210
        "90000001.SZ",              # SZSE numeric guess       -> parses, no data
        "IO2609-C-4000.CFE",        # CFFEX index option       -> -4216 (no entitlement)
        "IO2609-C-4000.CFFEX",      # wrong suffix             -> -4210
        "IO2609C4000.CFE",          # no separators            -> -4210
    ]
    for code in candidates:
        try:
            tables = client.real_time([code], "latest,openInterest")
            if not tables:
                print(f"  parses, no data   {code}")
            else:
                print(f"  LIVE              {code}: "
                      f"{json.dumps(_rows(tables)[code], ensure_ascii=False)}")
        except ifind_client.IFindError as exc:
            print(f"  errorcode={exc.errorcode:<6}    {code}: {exc.errmsg}")


def probe_scan(client):
    """Locate the live SSE option code block by scanning the numeric range.

    Cheap because codes outside the block cost nothing: non-existent codes raise
    -4210 (dataVol 0) and delisted ones return an empty table (dataVol 0).
    """
    found = []
    for start in range(10004000, 10013000, 500):
        codes = [f"{n}.SH" for n in range(start, start + 500)]
        try:
            tables = client.real_time(codes, "latest")
        except ifind_client.IFindError as exc:
            print(f"  {start}: errorcode={exc.errorcode} (past the top of the range)")
            break
        if tables:
            found += [t["thscode"] for t in tables]
            print(f"  {start}: {len(tables):4d} quoting")
    if found:
        print(f"\n  live block: {found[0]} .. {found[-1]}  ({len(found)} contracts)")
    return found


def probe_meta(client):
    """Verify the ths_*_option indicator family on one contract."""
    code = "10011000.SH"
    for name in META_INDICATORS + ANALYTIC_INDICATORS:
        try:
            tables = client.basic_data([code], [{"indicator": name,
                                                 "indiparams": [TRADE_DATE]}])
            table = tables[0].get("table") if tables else {}
            print(f"  OK   {name:34s} {json.dumps(table, ensure_ascii=False)}")
        except ifind_client.IFindError as exc:
            print(f"  bad  {name:34s} errorcode={exc.errorcode}")

    print("\n  Names that look plausible but return -4210:")
    for name in ("ths_iv_option", "ths_expire_date_option", "ths_option_type_option",
                 "ths_exercise_price_option", "ths_theoretical_price_option",
                 "ths_intrinsic_value_option", "ths_contract_unit_option"):
        try:
            client.basic_data([code], [{"indicator": name, "indiparams": [TRADE_DATE]}])
            print(f"    (unexpectedly OK) {name}")
        except ifind_client.IFindError as exc:
            print(f"    {name:34s} errorcode={exc.errorcode}")


def load_chain(client, refresh=False) -> list:
    """Enumerate every live contract with its strike/expiry/type/underlying.

    ~1 dataVol per code per indicator, so a full 1809-contract enumeration with
    four indicators costs ~7.3k. Cached on disk — the contract set only changes
    when a new expiry lists.
    """
    if CHAIN_CACHE.exists() and not refresh:
        return json.loads(CHAIN_CACHE.read_text(encoding="utf-8"))

    codes = [f"{n}.SH" for n in range(SSE_OPTION_LO, SSE_OPTION_HI)]
    indipara = [{"indicator": name, "indiparams": [TRADE_DATE]} for name in
                ("ths_underlying_code_option", "ths_contract_type_option",
                 "ths_strike_price_option", "ths_maturity_date_option")]
    chain = []
    for table in client.basic_data(codes, indipara):
        fields = table.get("table") or {}
        underlying = _first(fields, "ths_underlying_code_option")
        if not underlying:
            continue
        chain.append({
            "code": table["thscode"],
            "underlying": underlying,
            "type": _first(fields, "ths_contract_type_option"),
            "strike": _first(fields, "ths_strike_price_option"),
            "expiry": _first(fields, "ths_maturity_date_option"),
        })
    CHAIN_CACHE.write_text(json.dumps(chain, ensure_ascii=False), encoding="utf-8")
    return chain


def probe_chain(client, underlying="510050", expiry=None):
    """Build a real option chain and print it as a trader would read it."""
    chain = load_chain(client)
    by_underlying = collections.Counter(r["underlying"] for r in chain)
    print("  contracts by underlying: " + ", ".join(
        f"{UNDERLYINGS.get(k, k)}({k})={v}" for k, v in sorted(by_underlying.items())))

    subset = [r for r in chain if r["underlying"] == underlying]
    expiries = sorted({r["expiry"] for r in subset})
    print(f"  {underlying} expiries: {expiries}")
    expiry = expiry or next((e for e in expiries if e >= TRADE_DATE.replace("-", "")),
                            expiries[-1])
    subset = [r for r in subset if r["expiry"] == expiry]
    codes = [r["code"] for r in subset]

    before = client.data_vol
    quotes = _rows(client.real_time(codes, RT_QUOTE + "," + RT_GREEKS))
    spot = _first(client.real_time([f"{underlying}.SH"], "latest")[0]["table"], "latest")
    cost = client.data_vol - before

    print(f"\n  {underlying} expiry {expiry} — {len(codes)} contracts, "
          f"spot={spot}, snapshot dataVol={cost}\n")
    header = (f"{'strike':>7} | {'C bid':>7} {'C ask':>7} {'C IV':>6} {'C dlt':>6} "
              f"{'C OI':>7} | {'P bid':>7} {'P ask':>7} {'P IV':>6} {'P dlt':>6} {'P OI':>7}")
    print(header)
    print("  " + "-" * (len(header) - 2))
    for strike in sorted({r["strike"] for r in subset}):
        call = next((quotes.get(r["code"], {}) for r in subset
                     if r["strike"] == strike and "看涨" in r["type"]), {})
        put = next((quotes.get(r["code"], {}) for r in subset
                    if r["strike"] == strike and "看跌" in r["type"]), {})

        def cell(side, key, width=7, prec=4):
            value = side.get(key)
            return f"{value:{width}.{prec}f}" if value is not None else " " * width

        print(f"{strike:7.2f} | {cell(call,'bid1')} {cell(call,'ask1')} "
              f"{cell(call,'impliedVolatility',6,3)} {cell(call,'delta',6,3)} "
              f"{cell(call,'openInterest',7,0)} | {cell(put,'bid1')} {cell(put,'ask1')} "
              f"{cell(put,'impliedVolatility',6,3)} {cell(put,'delta',6,3)} "
              f"{cell(put,'openInterest',7,0)}")


def probe_history(client):
    """Per-contract daily bars, including for contracts that have already expired."""
    print("  live contract, recent bars:")
    tables = client.history_quotation(["10011000.SH"], HIST_FIELDS,
                                      "2026-08-18", TRADE_DATE)
    print("   ", json.dumps(tables[0], ensure_ascii=False)[:520])

    print("\n  expired contracts still serve their full life:")
    chain = load_chain(client)
    for expiry, window in (("20251224", ("2025-12-15", "2025-12-17")),
                           ("20260225", ("2026-02-10", "2026-02-12")),
                           ("20260722", ("2026-07-10", "2026-07-14"))):
        codes = [r["code"] for r in chain
                 if r["expiry"] == expiry and r["underlying"] == "510050"][:6]
        if not codes:
            continue
        tables = client.history_quotation(codes, "close,openInterest,settlement",
                                          window[0], window[1])
        with_bars = [t for t in tables if t.get("time")]
        print(f"    expiry {expiry}: {len(with_bars)}/{len(codes)} returned bars "
              f"— {json.dumps(with_bars[0], ensure_ascii=False)[:170]}")

    print("\n  history depth — the first day of the market (2015-02-09):")
    tables = client.history_quotation([f"{n}.SH" for n in range(10000001, 10000009)],
                                      "close,openInterest", "2015-02-09", "2015-02-11")
    for table in [t for t in tables if t.get("time")][:3]:
        print("   ", json.dumps(table, ensure_ascii=False)[:180])

    print("\n  historical IV/greeks series via date_sequence (works on expired too):")
    tables = client.date_sequence(
        ["10011000.SH"],
        [{"indicator": "ths_implied_volatility_option", "indiparams": [""]},
         {"indicator": "ths_delta_option", "indiparams": [""]}],
        "2026-08-18", TRADE_DATE)
    print("   ", json.dumps(tables[0], ensure_ascii=False)[:420])

    print("\n  intraday 5-minute bars via high_frequency:")
    body = client.post("high_frequency", {
        "codes": "10011000.SH", "indicators": "open,high,low,close,volume,amount",
        "starttime": f"{TRADE_DATE} 09:30:00", "endtime": f"{TRADE_DATE} 10:00:00",
        "functionpara": {"Fill": "Original", "Interval": "5"}})
    print("   ", json.dumps(body.get("tables", [{}])[0], ensure_ascii=False)[:400])


def probe_parity(client, underlying="510050", expiry="20260923"):
    """Put-call parity audit — the strongest internal consistency check available.

    C - P - (S - K) must be the same constant at every strike (it is the
    discount/carry term). A residual that wanders strike to strike would mean
    the strikes, types, or prices are mismatched.
    """
    chain = load_chain(client)
    subset = [r for r in chain if r["underlying"] == underlying and r["expiry"] == expiry]
    codes = [r["code"] for r in subset]
    tables = client.history_quotation(codes + [f"{underlying}.SH"], "close",
                                      TRADE_DATE, TRADE_DATE)
    close = {t["thscode"]: t["table"]["close"][0] for t in tables if t.get("time")}
    spot = close[f"{underlying}.SH"]

    print(f"  S={spot}  expiry={expiry}\n")
    print(f"{'K':>6} {'C':>8} {'P':>8} {'C-P':>9} {'S-K':>9} {'resid':>9}")
    residuals = []
    for strike in sorted({r["strike"] for r in subset}):
        call = next((close.get(r["code"]) for r in subset
                     if r["strike"] == strike and "看涨" in r["type"]), None)
        put = next((close.get(r["code"]) for r in subset
                    if r["strike"] == strike and "看跌" in r["type"]), None)
        if call is None or put is None:
            continue
        residual = (call - put) - (spot - strike)
        residuals.append(residual)
        print(f"{strike:6.2f} {call:8.4f} {put:8.4f} {call - put:+9.4f} "
              f"{spot - strike:+9.4f} {residual:+9.4f}")
    print(f"\n  residual mean={statistics.mean(residuals):+.5f} "
          f"stdev={statistics.pstdev(residuals):.5f} "
          f"range=[{min(residuals):+.4f}, {max(residuals):+.4f}]")


def probe_iv(client, underlying="510050", expiry="20260923"):
    """real_time_quotation greeks vs basic_data_service greeks.

    They agree closely except on deep in-the-money calls, where the real-time
    feed degenerates (IV pinned at 0.0001, delta at exactly 1.0, gamma and vega
    at 0) while the ths_*_option indicators stay sane.
    """
    chain = load_chain(client)
    subset = sorted([r for r in chain if r["underlying"] == underlying
                     and r["expiry"] == expiry],
                    key=lambda r: (r["type"], r["strike"]))
    codes = [r["code"] for r in subset]

    live = _rows(client.real_time(codes, "impliedVolatility,delta"))
    stored = _rows(client.basic_data(
        codes, [{"indicator": "ths_implied_volatility_option", "indiparams": [TRADE_DATE]},
                {"indicator": "ths_delta_option", "indiparams": [TRADE_DATE]}]))

    print(f"{'code':>12} {'type':>6} {'K':>6} | {'IV rt':>8} {'IV bd':>8} | "
          f"{'dlt rt':>8} {'dlt bd':>8}")
    collapsed = 0
    for row in subset:
        code = row["code"]
        iv_rt = live[code].get("impliedVolatility")
        iv_bd = stored[code].get("ths_implied_volatility_option")
        d_rt = live[code].get("delta")
        d_bd = stored[code].get("ths_delta_option")
        flag = ""
        if iv_rt is not None and iv_rt < 0.01 and (iv_bd or 0) > 0.05:
            flag = "  <-- real_time IV collapsed"
            collapsed += 1
        print(f"{code:>12} {row['type']:>6} {row['strike']:6.2f} | "
              f"{iv_rt!s:>8} {iv_bd!s:>8} | {d_rt!s:>8} {d_bd!s:>8}{flag}")
    print(f"\n  real_time IV collapsed on {collapsed}/{len(subset)} contracts")


def probe_cffex(client):
    """CFFEX index options (IO/MO/HO) — entitlement check, not a format check."""
    checks = [
        ("real_time IO option", lambda: client.real_time(["IO2609-C-4000.CFE"], "latest")),
        ("history IO option", lambda: client.history_quotation(
            ["IO2609-C-4000.CFE"], "close", "2026-08-24", TRADE_DATE)),
        ("basic_data IO option", lambda: client.basic_data(
            ["IO2609-C-4000.CFE"],
            [{"indicator": "ths_strike_price_option", "indiparams": [TRADE_DATE]}])),
        ("HO option", lambda: client.real_time(["HO2609-C-3000.CFE"], "latest")),
        ("IF future (control)", lambda: client.real_time(["IF2609.CFE"], "latest")),
    ]
    for label, call in checks:
        try:
            print(f"  OK   {label}: {json.dumps(call(), ensure_ascii=False)[:200]}")
        except ifind_client.IFindError as exc:
            print(f"  bad  {label}: errorcode={exc.errorcode} {exc.errmsg}")


SECTIONS = {
    "codes": probe_codes,
    "scan": probe_scan,
    "meta": probe_meta,
    "chain": probe_chain,
    "history": probe_history,
    "parity": probe_parity,
    "iv": probe_iv,
    "cffex": probe_cffex,
}


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = list(SECTIONS) if which == "all" else [which]
    unknown = [n for n in names if n not in SECTIONS]
    if unknown:
        print(f"unknown section(s): {unknown}. choose from: {list(SECTIONS)}",
              file=sys.stderr)
        return 2

    client = ifind_client.get_client()
    if not client.configured:
        print("IFIND_REFRESH_TOKEN not set (checked env and .env)", file=sys.stderr)
        return 1

    for name in names:
        print(f"\n{'=' * 72}\n== {name}\n{'=' * 72}")
        before = client.data_vol
        try:
            SECTIONS[name](client)
        except ifind_client.IFindError as exc:
            print(f"  section failed: {exc}")
        print(f"\n  [{name} dataVol: {client.data_vol - before}]")

    print(f"\nTOTAL dataVol this run: {client.data_vol}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
