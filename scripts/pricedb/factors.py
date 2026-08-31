#!/usr/bin/env python3
"""
pricedb_factors.py — adjustment-factor derivation, sync and repair.

Extracted from pricedb.py on 2026-08-30, immediately after this code produced a
real bug that ran for months.

`cmd_snapshot` writes the close-slot price bars and never touches adj_factors.
That write makes `latest` equal today, so `cmd_update` hit its "Already up to
date" early return — fifty lines ABOVE the factor reconciliation it owned. The
snapshot succeeding is what made update skip the sync. Factors then lagged
prices by one session on every afternoon run, `get_factors_on_date` (exact-date
match) returned {}, `f_ref.get(code, 1.0)` read that absence as "no adjustment
needed", and rps_cache.ma10 shipped hfq-scale numbers as prices — 603259 read
168.28 against a true 162.23, and a deep report quoted a figure 9x off.

Nobody could see the gap because no module owned factors. Both commands lived in
the same 3,649-line file, both wrote the same tables, and neither one's contract
about who advances adj_factors was visible from the other. **That is what this
file is for: an explicit owner.** Anything that advances daily_prices without
advancing adj_factors is now visibly someone else's code calling in here.

I/O deliberately stayed in pricedb.py. The network fetches this module needs
(`_fetch_ex_div_codes_datacenter`, `fetch_adj_factor_events_sina`,
`_ifind_af_series`, `_fetch_clist_prev_close_map`, `_kline_closes_eastmoney`)
are imported INSIDE the functions that call them, not at module load. Two
reasons: it avoids a circular import, and — more importantly — the deferred
lookup resolves against pricedb's module globals at call time, so the nine
existing `monkeypatch.setattr(pricedb, "_fetch_...")` sites in
tests/test_factor_heal.py and tests/test_ifind_factors.py keep working. Binding
them at import time would have left those patches silently inert, including a
`_must_not_call` assertion that would then pass while hitting the live API.
"""

import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

import price_adjust
import bisect

import ifind_client
from pricedb.bars import _eastmoney_secid, _frame_close_series, _return_ratio_factors

ADJ_BACKFILL_SLEEP_SEC = float(os.getenv("ADJ_BACKFILL_SLEEP_SEC", "0.4"))
ADJ_EVENT_THRESHOLD = 0.005
IFIND_ADJ_EVENT_EPSILON = 1e-9
from pricedb.bars import _safe_float, _yyyymmdd_to_iso
from pricedb.storage import invalidate_rps_cache

def _expand_events_to_code_dates(conn: sqlite3.Connection, code: str,
                                 events: list) -> list[tuple]:
    """Map sparse factor events onto a code's actual traded dates (dense rows).

    Applicable factor for date d = factor of the latest event <= d, else 1.0
    (the pre-first-event hfq base). Guarantees the table is dense for the code
    so COALESCE never mixes scales inside one window (hazard F1).
    """
    event_dates = [d for d, _ in events]
    rows = []
    for (d,) in conn.execute(
        "SELECT date FROM daily_prices WHERE code = ? ORDER BY date", (code,)
    ):
        i = bisect.bisect_right(event_dates, d) - 1
        factor = events[i][1] if i >= 0 else 1.0
        rows.append((code, d, round(factor, 8)))
    return rows

def derive_factors_from_akshare(ak, code: str, beg: str, end: str) -> list[tuple]:
    """Return-ratio factors via akshare raw + hfq histories (fallback path)."""
    # Deferred so the lookup resolves against pricedb's globals at CALL time —
    # that is what keeps monkeypatch.setattr(pricedb, ...) working, and it
    # avoids a circular import at load.
    from pricedb import _no_proxy_env, _run_with_timeout
    with _no_proxy_env():
        raw = _run_with_timeout(
            f"AkShare raw {code}",
            lambda: ak.stock_zh_a_hist(symbol=code, period="daily",
                                       start_date=beg, end_date=end, adjust=""),
        )
        hfq = _run_with_timeout(
            f"AkShare hfq {code}",
            lambda: ak.stock_zh_a_hist(symbol=code, period="daily",
                                       start_date=beg, end_date=end, adjust="hfq"),
        )
    return _return_ratio_factors(_frame_close_series(raw), _frame_close_series(hfq))

def derive_factors_eastmoney(code: str, exchange: str, beg: str, end: str) -> list[tuple]:
    """Return-ratio factors from eastmoney's own raw (fqt=0) + hfq (fqt=2)
    klines. Preferred over the akshare path: two curl fetches, no pandas, and
    immune to python-TLS fingerprint blocks."""
    # Deferred so the lookup resolves against pricedb's globals at CALL time —
    # that is what keeps monkeypatch.setattr(pricedb, ...) working, and it
    # avoids a circular import at load.
    from pricedb import _kline_closes_eastmoney, _no_proxy_env
    secid = _eastmoney_secid({"code": code, "exchange": exchange})
    if not secid:
        return []
    with _no_proxy_env():
        raw_s = _kline_closes_eastmoney(secid, beg, end, fqt=0)
        hfq_s = _kline_closes_eastmoney(secid, beg, end, fqt=2)
    return _return_ratio_factors(raw_s, hfq_s)

def upsert_adj_factors(conn: sqlite3.Connection, rows: list) -> str | None:
    """INSERT OR REPLACE (code, date, factor) rows with diff detection.

    Returns the earliest date whose *effective* value changed, so the caller
    can invalidate rps_cache from there. A fresh insert counts as a change
    only when factor != 1.0 (a missing row already read as 1.0 via COALESCE).
    """
    earliest_changed: str | None = None
    cur = conn.cursor()
    for code, date_iso, factor in rows:
        old = cur.execute(
            "SELECT factor FROM adj_factors WHERE code = ? AND date = ?",
            (code, date_iso),
        ).fetchone()
        effective_old = old[0] if old is not None else 1.0
        if abs(effective_old - factor) < 1e-9:
            if old is None and abs(factor - 1.0) < 1e-9:
                # still write the 1.0 row: presence marks the code as processed
                cur.execute("INSERT OR REPLACE INTO adj_factors VALUES (?, ?, ?)",
                            (code, date_iso, factor))
            continue
        cur.execute("INSERT OR REPLACE INTO adj_factors VALUES (?, ?, ?)",
                    (code, date_iso, factor))
        if earliest_changed is None or date_iso < earliest_changed:
            earliest_changed = date_iso
    conn.commit()
    return earliest_changed

def _forward_fill_factors(conn: sqlite3.Connection) -> int:
    """Densify: any (code, date) in daily_prices missing a factor gets the
    code's most recent PRIOR factor. Dates before a code's first factor row
    stay absent (COALESCE 1.0 == the pre-event base, which is correct).
    Codes with no factor rows at all are untouched (unprocessed => raw)."""
    filled = 0
    codes = [r[0] for r in conn.execute("SELECT DISTINCT code FROM adj_factors")]
    for code in codes:
        factors = conn.execute(
            "SELECT date, factor FROM adj_factors WHERE code = ? ORDER BY date",
            (code,),
        ).fetchall()
        fdates = [f[0] for f in factors]
        fset = set(fdates)
        missing = [
            r[0] for r in conn.execute(
                "SELECT date FROM daily_prices WHERE code = ? ORDER BY date", (code,)
            ) if r[0] not in fset
        ]
        rows = []
        for d in missing:
            i = bisect.bisect_right(fdates, d) - 1
            if i < 0:
                continue  # before first factor: leave absent (reads as 1.0)
            rows.append((code, d, factors[i][1]))
        if rows:
            conn.executemany("INSERT OR REPLACE INTO adj_factors VALUES (?, ?, ?)", rows)
            filled += len(rows)
    conn.commit()
    return filled

def _ifind_event_multipliers(conn: sqlite3.Connection, codes: list,
                             prev_date: str, date_iso: str) -> dict:
    """{code: multiplier} for `date_iso`, from the RATIO of iFinD's factors.

    Deliberately a ratio, not an absolute value. Our stored chains are anchored
    at 1.0 on each code's first date; iFinD anchors at listing. Writing their
    absolute af into our table would jump the base mid-series and fabricate a
    return on the splice date. Taking af[today]/af[prev] imports only the
    corporate-action event, which is the part iFinD detects more reliably than
    the retired eastmoney clist f18 probe.
    """
    # Deferred so the lookup resolves against pricedb's globals at CALL time —
    # that is what keeps monkeypatch.setattr(pricedb, ...) working, and it
    # avoids a circular import at load.
    from pricedb import _ifind_af_series
    ex_map = {c: e for c, e in conn.execute("SELECT code, exchange FROM stocks")}
    series = _ifind_af_series(codes, ex_map, prev_date, date_iso)
    out = {}
    for code, by_date in series.items():
        prev_af, today_af = by_date.get(prev_date), by_date.get(date_iso)
        if prev_af and today_af and prev_af > 0:
            out[code] = today_af / prev_af
    return out

def rebuild_factors_from_ifind(conn: sqlite3.Connection, codes: list | None = None,
                               dry_run: bool = False, chunk: int = 300,
                               dry_run_sample: int = 20) -> dict:
    """Rebuild adj_factors for whole codes from iFinD's ths_af_stock.

    Rebuilds a code's ENTIRE series or none of it. Partial rebuilds are the one
    thing that must not happen here: our chains are anchored at 1.0 on each
    code's first date while iFinD anchors at listing, so splicing their absolute
    values into the middle of one of our series would fabricate a return on the
    splice date. Each series is renormalized to 1.0 at the code's first date,
    which reproduces our existing convention exactly.

    **Quota**: this is the most expensive call in the project. It bills to
    `date_sequence`, which shares the 5,000,000-point 基本面数据 bucket (NOT the
    150,000,000 行情数据 bucket that bars use). A full universe rebuild is
    ~2.2M points — 44% of that bucket in one command. On 2026-08-25 a dry run
    plus a real run consumed 89% of the month's fundamental allowance.

    `dry_run` therefore **samples** rather than fetching the universe: it sizes
    the job and proves the fetch works on `dry_run_sample` codes. A dry run that
    costs as much as the real thing is not a safety net, it is double billing.
    """
    # Deferred so the lookup resolves against pricedb's globals at CALL time —
    # that is what keeps monkeypatch.setattr(pricedb, ...) working, and it
    # avoids a circular import at load.
    from pricedb import _ifind_af_series
    ex_map = {c: e for c, e in conn.execute("SELECT code, exchange FROM stocks")}
    bounds = {}
    for code, first, last in conn.execute(
            "SELECT code, MIN(date), MAX(date) FROM daily_prices GROUP BY code"):
        bounds[code] = (first, last)
    targets = [c for c in (codes or bounds) if c in bounds]

    stats = {"codes": len(targets), "rebuilt": 0, "rows": 0,
             "no_data": 0, "failed": 0, "sampled": False,
             "estimated_rows": 0}
    if not targets:
        return stats

    if dry_run and len(targets) > dry_run_sample:
        sessions = conn.execute(
            "SELECT COUNT(DISTINCT date) FROM daily_prices").fetchone()[0]
        stats["sampled"] = True
        stats["estimated_rows"] = conn.execute(
            "SELECT COUNT(*) FROM daily_prices").fetchone()[0]
        print(f"  dry run: sampling {dry_run_sample} of {len(targets)} codes "
              f"(a full fetch would cost ~{stats['estimated_rows']:,} points "
              f"against the 5M 基本面 bucket)", file=sys.stderr)
        targets = targets[::max(1, len(targets) // dry_run_sample)][:dry_run_sample]
        stats["codes"] = len(targets)

    for i in range(0, len(targets), chunk):
        batch = targets[i:i + chunk]
        beg = min(bounds[c][0] for c in batch)
        end = max(bounds[c][1] for c in batch)
        try:
            series = _ifind_af_series(batch, ex_map, beg, end)
        except Exception as e:
            stats["failed"] += len(batch)
            print(f"    ⚠ batch {batch[0]}..{batch[-1]} failed: {str(e)[:70]}",
                  file=sys.stderr)
            continue

        rows = []
        for code in batch:
            by_date = series.get(code)
            if not by_date:
                stats["no_data"] += 1
                continue
            dates = sorted(d for d in by_date
                           if bounds[code][0] <= d <= bounds[code][1])
            if not dates:
                stats["no_data"] += 1
                continue
            base = by_date[dates[0]]
            if not base or base <= 0:
                stats["no_data"] += 1
                continue
            for d in dates:
                rows.append((code, d, round(by_date[d] / base, 8)))
            stats["rebuilt"] += 1

        if rows and not dry_run:
            # Replace the whole code's series atomically.
            done = {c for c, _, _ in rows}
            conn.executemany("DELETE FROM adj_factors WHERE code = ?",
                             [(c,) for c in done])
            conn.executemany(
                "INSERT OR REPLACE INTO adj_factors(code,date,factor) "
                "VALUES (?,?,?)", rows)
            conn.commit()
        stats["rows"] += len(rows)
        print(f"    [{min(i + chunk, len(targets))}/{len(targets)}] "
              f"{stats['rebuilt']} codes, {stats['rows']:,} rows", file=sys.stderr)

    if not dry_run:
        _forward_fill_factors(conn)
    return stats

def sync_adj_factors_for_today(conn: sqlite3.Connection, date_iso: str) -> str | None:
    """Incremental daily factor sync using the clist f18 detector.

    For each stock: stored_prev_raw_close / f18 == the event multiplier for
    `date_iso` (1.0 when no corporate action). New factor = prior factor × m.
    Finishes with a forward-fill so the table stays dense. Returns earliest
    changed date (for cache invalidation), or None.

    Limitation (documented): this only detects events whose ex-date is TODAY.
    After multi-day downtime, gap-day events are missed until a
    `pricedb.py factors backfill` re-derivation — same self-heal philosophy
    as the price cursor.
    """
    # Deferred so the lookup resolves against pricedb's globals at CALL time —
    # that is what keeps monkeypatch.setattr(pricedb, ...) working, and it
    # avoids a circular import at load.
    from pricedb import _fetch_clist_prev_close_map
    prev_row = conn.execute(
        "SELECT MAX(date) FROM daily_prices WHERE date < ?", (date_iso,)
    ).fetchone()
    prev_date = prev_row[0] if prev_row else None
    if not prev_date:
        return None
    prev_closes = dict(conn.execute(
        "SELECT code, close FROM daily_prices WHERE date = ?", (prev_date,)
    ))
    prev_factors = dict(conn.execute(
        "SELECT code, factor FROM adj_factors WHERE date = ?", (prev_date,)
    ))
    if prev_closes and not prev_factors:
        # Multi-day factor gap: every chain would restart at base 1.0 and
        # silently destroy the cumulative factors. Refuse; heal instead.
        raise RuntimeError(
            f"adj_factors has no rows for {prev_date} — multi-day gap; "
            f"run 'pricedb.py factors heal'"
        )

    # Primary: iFinD's own factor ratio. Fallback: the eastmoney clist f18
    # probe, which is a RETIRED provider surviving only as this helper — it
    # infers the event from prev_close/f18 and dies whenever eastmoney throttles.
    source = "ifind"
    mult_map: dict = {}
    if ifind_client.is_available():
        try:
            mult_map = _ifind_event_multipliers(
                conn, list(prev_closes), prev_date, date_iso)
        except Exception as e:
            print(f"  factors: iFinD multipliers failed ({str(e)[:80]}) — "
                  f"falling back to clist f18", file=sys.stderr)
    if not mult_map:
        source = "clist-f18"
        f18_map = _fetch_clist_prev_close_map()
        if not f18_map:
            raise RuntimeError("clist f18 snapshot returned no rows")
        for code, prev_close in prev_closes.items():
            f18 = f18_map.get(code)
            if f18 and prev_close and prev_close > 0:
                mult_map[code] = prev_close / f18

    # The noise threshold is a property of the SOURCE, not of the market.
    # clist f18 INFERS the event from prev_close/f18, so ratios within 0.5% are
    # indistinguishable from rounding noise and get snapped to 1.0. iFinD's
    # ths_af_stock is an exact published factor — applying the same 0.5% floor
    # to it discarded 4 of the 6 real dividends on 2026-08-25 (steps of
    # 1.0021–1.0039), so exact sources get only a float-noise epsilon.
    threshold = (IFIND_ADJ_EVENT_EPSILON if source == "ifind"
                 else ADJ_EVENT_THRESHOLD)

    rows = []
    events = 0
    for code, prev_close in prev_closes.items():
        m = mult_map.get(code)
        if not m or m <= 0:
            continue
        if abs(m - 1.0) <= threshold:
            m = 1.0
        else:
            events += 1
        base = prev_factors.get(code, 1.0)
        rows.append((code, date_iso, round(base * m, 8)))
    earliest = upsert_adj_factors(conn, rows)
    _forward_fill_factors(conn)
    print(f"  factors: {date_iso} synced via {source} "
          f"({events} corporate actions detected)", file=sys.stderr)
    return earliest

def heal_adj_factor_gap(conn: sqlite3.Connection, beg_iso: str, end_iso: str) -> str | None:
    """Repair a multi-session factor gap [beg_iso, end_iso] inclusive.

    Factors only change on corporate actions, so the gap splits cleanly:
    the datacenter ex-div calendar names the codes with an event inside the
    gap — those get a full re-derivation (sina events primary, eastmoney
    return-ratio fallback), anchor-rescaled so pre-gap rows are unchanged
    (keeps rps_cache invalidation shallow); every other code is an exact
    plain forward-fill. Returns earliest changed date for cache invalidation.
    """
    # Deferred so the lookup resolves against pricedb's globals at CALL time —
    # that is what keeps monkeypatch.setattr(pricedb, ...) working, and it
    # avoids a circular import at load.
    from pricedb import _fetch_ex_div_codes_datacenter, fetch_adj_factor_events_sina
    dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM daily_prices WHERE date >= ? AND date <= ? "
        "ORDER BY date", (beg_iso, end_iso))]
    exchanges = dict(conn.execute("SELECT code, exchange FROM stocks"))
    known = {r[0] for r in conn.execute("SELECT DISTINCT code FROM daily_prices")}

    event_codes: set = set()
    calendar_failures = 0
    for d in dates:
        codes = _fetch_ex_div_codes_datacenter(d)
        if codes is None:
            calendar_failures += 1
            print(f"  factors heal: ex-div calendar FAILED for {d} — event "
                  f"codes that day keep forward-filled factors until the next "
                  f"heal", file=sys.stderr)
            continue
        hits = set()
        for code in codes & known:
            # Skip codes whose stored factor already jumps on the event date —
            # they were derived event-aware; re-deriving is pure waste. A
            # missing row, or a factor flat across its own ex-date, is damage.
            row = conn.execute(
                "SELECT factor FROM adj_factors WHERE code = ? AND date = ?",
                (code, d)).fetchone()
            prev = conn.execute(
                "SELECT factor FROM adj_factors WHERE code = ? AND date < ? "
                "ORDER BY date DESC LIMIT 1", (code, d)).fetchone()
            prev_val = prev[0] if prev else 1.0
            if row is None or abs(row[0] - prev_val) < 1e-12:
                hits.add(code)
        print(f"  factors heal: {d} — {len(hits)} ex-div codes needing "
              f"re-derivation", file=sys.stderr)
        event_codes |= hits

    earliest: str | None = None
    failed = 0
    stale = []
    for code in sorted(event_codes):
        try:
            events = fetch_adj_factor_events_sina(code, exchanges.get(code, ""))
            if events:
                rows = _expand_events_to_code_dates(conn, code, events)
            else:
                first = conn.execute(
                    "SELECT MIN(date) FROM daily_prices WHERE code = ?", (code,)
                ).fetchone()[0]
                series = derive_factors_eastmoney(
                    code, exchanges.get(code, ""),
                    first.replace("-", ""), end_iso.replace("-", ""))
                rows = [(code, d, f) for d, f in series]
            if not rows:
                failed += 1
                continue
            # Anchor-rescale: sources use absolute (since-listing) factor
            # scale; existing rows use whatever scale backfill stored. Pin the
            # new series to the stored factor on the last pre-gap date so
            # pre-gap rows diff as unchanged and only the gap invalidates.
            anchor = conn.execute(
                "SELECT date, factor FROM adj_factors WHERE code = ? AND date < ? "
                "ORDER BY date DESC LIMIT 1", (code, beg_iso)).fetchone()
            if anchor:
                new_at_anchor = next((f for _c, d, f in reversed(rows) if d <= anchor[0]), None)
                if new_at_anchor:
                    scale = anchor[1] / new_at_anchor
                    rows = [(c, d, round(f * scale, 8)) for c, d, f in rows]
            in_gap = [f for _, d, f in rows if beg_iso <= d <= end_iso]
            pre_gap = anchor[1] if anchor else 1.0
            if in_gap and all(abs(f - pre_gap) < 1e-9 for f in in_gap):
                stale.append(code)  # calendar says event, source shows none yet
            changed = upsert_adj_factors(conn, rows)
            if changed and (earliest is None or changed < earliest):
                earliest = changed
        except Exception as e:
            failed += 1
            print(f"  factors heal: {code} FAILED ({str(e)[:80]})", file=sys.stderr)
        time.sleep(ADJ_BACKFILL_SLEEP_SEC)

    filled = _forward_fill_factors(conn)
    print(f"  factors heal: {len(event_codes)} event codes re-derived "
          f"({failed} failed), forward-filled {filled} rows", file=sys.stderr)
    if stale:
        print(f"  factors heal: WARNING — source has not yet published the "
              f"event for: {','.join(stale[:10])}"
              f"{' …' if len(stale) > 10 else ''} (re-run heal later)",
              file=sys.stderr)
    if calendar_failures == len(dates) and dates:
        print("  factors heal: WARNING — ex-div calendar unreachable for the "
              "entire gap; only forward-fill applied", file=sys.stderr)
    return earliest

def _sync_or_heal_factors(conn: sqlite3.Connection) -> str | None:
    """Keep adj_factors caught up with daily_prices, whatever the lag.

    Lag of exactly one session on today's date → fast same-day f18 sync
    (falls back to heal when clist is down). Anything more → gap heal.
    Returns earliest changed date, or None.
    """
    cov = price_adjust.factor_coverage(conn)
    mpd, mfd = cov["max_price_date"], cov["max_factor_date"]
    if not mpd or not mfd or mfd >= mpd:
        filled = _forward_fill_factors(conn)
        if filled:
            print(f"  factors: forward-filled {filled} rows", file=sys.stderr)
        return None
    prev_date = conn.execute(
        "SELECT MAX(date) FROM daily_prices WHERE date < ?", (mpd,)
    ).fetchone()[0]
    if mfd == prev_date and mpd == datetime.now().strftime("%Y-%m-%d"):
        try:
            return sync_adj_factors_for_today(conn, mpd)
        except Exception as e:
            print(f"  factors: same-day f18 sync failed ({str(e)[:80]}); "
                  f"falling back to gap heal", file=sys.stderr)
    beg = (datetime.strptime(mfd, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    return heal_adj_factor_gap(conn, beg, mpd)
