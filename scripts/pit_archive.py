#!/usr/bin/env python3
"""
pit_archive.py — point-in-time raw-data archive ("store raw, derive later").

Quant-standard PIT discipline: archive RAW upstream data immutably, one JSON
file per source per trading day, so any future signal can be recomputed from
history — you can derive from raw archives, but you can never reconstruct what
you didn't capture. Files are append-only (never overwritten) and git-tracked.

Backfill-first: every run first heals gaps (all sources here are retroactively
fetchable), then captures the newest day — so a powered-off day costs nothing.

Layout: archive/<source>/<YYYY-MM-DD>.json
    {"source", "date", "fetched_at", "rows": [...]}

Sources (v1):
    margin_sse   — SSE margin balance (exchange site; cycle thermometer)
    margin_szse  — SZSE margin summary (exchange site)
    lhb          — 龙虎榜 detail (eastmoney via akshare)
    jiejin       — restricted-share release summary (eastmoney via akshare)

Usage:
    python3 scripts/pit_archive.py run [--source NAME] [--beg YYYYMMDD]
    python3 scripts/pit_archive.py status
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pricedb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = PROJECT_ROOT / "archive"

# Earliest date worth backfilling (pricedb history starts here).
DEFAULT_BEG = "2024-12-17"
# Politeness: pace requests, stop the sweep on failure bursts (resumable).
SLEEP_SEC = 0.5
MAX_CONSECUTIVE_FAILURES = 5


def _df_rows(frame) -> list:
    """DataFrame → list of JSON-safe row dicts."""
    if frame is None or getattr(frame, "empty", True):
        return []
    return json.loads(frame.to_json(orient="records", force_ascii=False, date_format="iso"))


def _yyyymmdd(date_iso: str) -> str:
    return date_iso.replace("-", "")


# --------------------------------------------------------------------------- #
# Source fetchers — each takes an ISO date, returns a list of row dicts.
# All are retro-fetchable, so the backfill-first cursor heals any gap.
# --------------------------------------------------------------------------- #
def _fetch_margin_sse(date_iso: str) -> list:
    import akshare as ak
    d = _yyyymmdd(date_iso)
    return _df_rows(ak.stock_margin_sse(start_date=d, end_date=d))


def _fetch_margin_szse(date_iso: str) -> list:
    import akshare as ak
    return _df_rows(ak.stock_margin_szse(date=_yyyymmdd(date_iso)))


def _fetch_lhb(date_iso: str) -> list:
    import akshare as ak
    d = _yyyymmdd(date_iso)
    return _df_rows(ak.stock_lhb_detail_em(start_date=d, end_date=d))


def _fetch_jiejin(date_iso: str) -> list:
    import akshare as ak
    d = _yyyymmdd(date_iso)
    return _df_rows(ak.stock_restricted_release_summary_em(
        symbol="全部股票", start_date=d, end_date=d))


SOURCES = {
    "margin_sse": _fetch_margin_sse,
    "margin_szse": _fetch_margin_szse,
    "lhb": _fetch_lhb,
    "jiejin": _fetch_jiejin,
}


# --------------------------------------------------------------------------- #
# Archive mechanics
# --------------------------------------------------------------------------- #
def archived_dates(source: str, archive_dir: Path = None) -> set:
    d = (archive_dir or ARCHIVE_DIR) / source
    if not d.exists():
        return set()
    return {p.stem for p in d.glob("????-??-??.json")}


def write_day(source: str, date_iso: str, rows: list, archive_dir: Path = None) -> Path:
    """Write one immutable day file. Existing files are NEVER overwritten."""
    d = (archive_dir or ARCHIVE_DIR) / source
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{date_iso}.json"
    if out.exists():
        return out
    payload = {
        "source": source,
        "date": date_iso,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "rows": rows,
    }
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.rename(out)
    return out


def trading_days(beg_iso: str, end_iso: str = None) -> list:
    """Trading days from the local price DB (no network)."""
    import sqlite3
    conn = sqlite3.connect(str(pricedb.DB_PATH))
    try:
        q = "SELECT DISTINCT date FROM daily_prices WHERE date >= ?"
        params = [beg_iso]
        if end_iso:
            q += " AND date <= ?"
            params.append(end_iso)
        return sorted(r[0] for r in conn.execute(q, params))
    finally:
        conn.close()


def run_source(source: str, fetch, days: list, archive_dir: Path = None,
               sleep_sec: float = None) -> dict:
    """Backfill-first sweep of one source over `days`. Returns stats."""
    sleep_sec = SLEEP_SEC if sleep_sec is None else sleep_sec
    have = archived_dates(source, archive_dir)
    missing = [d for d in days if d not in have]
    stats = {"source": source, "wanted": len(missing), "written": 0,
             "empty": 0, "failed": 0, "aborted": False}
    consecutive = 0
    for date_iso in missing:
        try:
            with pricedb._no_proxy_env():
                rows = fetch(date_iso)
            # empty results are archived too: "nothing happened that day" is
            # itself point-in-time information (e.g. no 龙虎榜 entries)
            write_day(source, date_iso, rows, archive_dir)
            stats["written"] += 1
            if not rows:
                stats["empty"] += 1
            consecutive = 0
        except Exception as e:
            stats["failed"] += 1
            consecutive += 1
            print(f"  {source} {date_iso}: FAILED ({str(e)[:80]})", file=sys.stderr)
            if consecutive >= MAX_CONSECUTIVE_FAILURES:
                stats["aborted"] = True
                print(f"  {source}: circuit breaker — aborting sweep "
                      f"(resumable; rerun later)", file=sys.stderr)
                break
        if sleep_sec:
            time.sleep(sleep_sec)
    return stats


def cmd_run(args: list):
    only = args[args.index("--source") + 1] if "--source" in args else None
    beg = args[args.index("--beg") + 1] if "--beg" in args else _yyyymmdd(DEFAULT_BEG)
    beg_iso = f"{beg[:4]}-{beg[4:6]}-{beg[6:8]}"
    days = trading_days(beg_iso)
    if not days:
        print("No trading days known (pricedb empty?)", file=sys.stderr)
        sys.exit(1)
    print(f"PIT archive run: {len(days)} trading days from {beg_iso}", file=sys.stderr)
    any_failed = False
    for name, fetch in SOURCES.items():
        if only and name != only:
            continue
        s = run_source(name, fetch, days)
        print(f"  {name}: +{s['written']} days "
              f"({s['empty']} empty, {s['failed']} failed"
              f"{', ABORTED' if s['aborted'] else ''})", file=sys.stderr)
        any_failed = any_failed or s["aborted"]
    sys.exit(2 if any_failed else 0)


def cmd_status():
    days = trading_days(DEFAULT_BEG)
    total = len(days)
    print(f"Trading days in range: {total} (from {DEFAULT_BEG})")
    for name in SOURCES:
        have = archived_dates(name)
        missing = sum(1 for d in days if d not in have)
        newest = max(have) if have else "—"
        print(f"  {name:12s}: {len(have):4d} days archived, {missing:4d} missing, newest {newest}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("run", "status"):
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "run":
        cmd_run(sys.argv[2:])
    else:
        cmd_status()
