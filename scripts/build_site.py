#!/usr/bin/env python3
"""Static portfolio-overview site generator → site/index.html.

Single self-contained HTML file: inline data + inline SVG/JS, zero CDN or
network dependencies at view time (must render offline). Color convention
is A-share: red = gain, green = loss.

Data sources (数字纪律 — everything re-derivable):
  - runs/<date>[/<slot>]/{input,output}/positions_snapshot.json → daily equity
    curve + per-day holdings (per date the LATEST snapshot wins by
    snapshot_time — post_run output preferred over stale pre_run input;
    legacy no-slot layout supported)
  - runs/<date>[/<slot>]/output/daily_summary.json → per-day actions (from the
    winning snapshot's run dir; falls back to a sibling slot on the same date
    when that run produced none, e.g. it failed before Phase 3)
  - tracking/positions.json → current portfolio + active positions
  - tracking/closed/*.json  → trade history + win-rate stats
  - tracking/portfolio_config.json → inception anchor (created = 1M)
  - sina index kline (sh000001) → 上证指数 daily candles, rebased to starting
    capital at inception, plus per-day % (组合 / 上证 / 超额); closes cached in
    data/index_cache/sh000001.json, OHLC in sh000001_ohlc.json, so offline
    rebuilds still work (build degrades to cache, then to no overlay)
  - scripts/event_calendar.upcoming() → 未来事件窗口 section
  - latest run input/regime.json + input/gex.json → header badges

Regenerate: python3 scripts/build_site.py
Also runs automatically at the end of run_daily.py (non-fatal, pre-commit).
"""

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"
TRACKING_DIR = PROJECT_ROOT / "tracking"
SITE_DIR = PROJECT_ROOT / "site"
INDEX_CACHE = PROJECT_ROOT / "data" / "index_cache" / "sh000001.json"
INDEX_OHLC_CACHE = PROJECT_ROOT / "data" / "index_cache" / "sh000001_ohlc.json"
PRICE_DB = PROJECT_ROOT / "data" / "pricedb" / "ashare_prices.db"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NOTE_MAX = 170

SLOT_LABEL = {"noon": "午盘", "afternoon": "收盘", "legacy": "收盘"}


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- equity series

def _snapshot_point(path: Path):
    """Extract one equity point (+ holdings) from a positions_snapshot.json."""
    try:
        snap = _read_json(path)
        pj = snap.get("positions_json") or {}
        pf = pj.get("portfolio") or {}
        if not pf.get("startingCapital"):
            return None
        holdings = [
            {"c": p.get("code", ""), "n": p.get("name", ""), "p": p.get("pnl_pct"),
             "v": p.get("currentValue"), "w": p.get("weight_pct"),
             "px": p.get("currentPrice")}
            for p in (pj.get("activePositions") or [])
        ]
        return {
            "time": snap.get("snapshot_time", ""),
            "stype": snap.get("snapshot_type", ""),
            # When the MARKS in this snapshot were last refreshed. A pre_run
            # snapshot is written before Phase 1 fetches any price, so it
            # carries whatever the PREVIOUS run left in positions.json — which
            # may be the previous day (stale) or earlier the same day (fresh).
            # The snapshot_type alone cannot tell them apart. None = unknown.
            "marks_asof": pj.get("lastUpdated"),
            "equity": pf.get("totalEquity"),
            "cash": pf.get("cash"),
            "ret_pct": pf.get("totalReturnPct"),
            "positions": pf.get("positionsUsed"),
            "starting": pf.get("startingCapital"),
            "holdings": holdings,
        }
    except Exception:
        return None


def collect_equity_series(runs_dir: Path = RUNS_DIR) -> list[dict]:
    """One point per run date: the day's latest snapshot (by snapshot_time).
    Each point remembers its run dir (for the matching daily_summary) and slot."""
    series = []
    if not runs_dir.is_dir():
        return series
    for day_dir in sorted(runs_dir.iterdir()):
        if not day_dir.is_dir() or not DATE_RE.match(day_dir.name):
            continue
        # Both input/ (pre_run) and output/ (post_run) are candidates; the
        # LATEST snapshot_time wins, which keeps the truest end-of-day equity
        # (2026-08-07: input-only made today's equity == yesterday's, delta 0).
        #
        # Note this is time-only: a later run's pre_run CAN beat an earlier
        # run's post_run, including when that later run failed. That is
        # deliberate — on 2026-08-20 the failed afternoon run's 15:23 snapshot
        # held the real close while the successful noon run's held midday marks.
        # The number is right; provenance is carried separately via
        # marks_asof / _run_status_for rather than by distorting the curve.
        candidates = []  # (snapshot_path, run_dir, slot)
        for sub in ("input", "output"):
            legacy = day_dir / sub / "positions_snapshot.json"
            if legacy.exists():
                candidates.append((legacy, day_dir, "legacy"))
        for slot_dir in day_dir.iterdir():
            if not slot_dir.is_dir():
                continue
            for sub in ("input", "output"):
                slotted = slot_dir / sub / "positions_snapshot.json"
                if slotted.exists():
                    candidates.append((slotted, slot_dir, slot_dir.name))
        points = []
        for snap_path, run_dir, slot in candidates:
            p = _snapshot_point(snap_path)
            if p:
                p["run_dir"] = run_dir
                p["slot"] = slot
                points.append(p)
        if not points:
            continue
        best = max(points, key=lambda p: p["time"])
        best["date"] = day_dir.name
        series.append(best)
    return series


def attach_holding_day_pcts(series: list[dict], sessions=None) -> None:
    """Set each holding's `d` = its day % (price vs the quote's prev_close),
    from the prices.json of the run that produced the day's snapshot.

    Only when the quote is dated that day AND its price is the snapshot's own
    mark — a stale pre_run mark must not borrow today's quote %. Otherwise the
    holding gets no `d` and the UI shows "—". A noon snapshot gives an
    intraday %, matching its intraday equity.

    Also sets `xd` = the book's previous-point price when it differs from the
    quote's prev_close. That is an ex-dividend/ex-rights day (2026-10-08
    普洛药业: book 27.74, quote prev_close 27.61 after 10派1.39 — the book
    took the drop and credits no dividend) or a previous mark that was not
    the close. Either way the stock's quote % and its move in the book differ.

    `xd` is only judged when the previous point is a post-15:00 mark of the
    previous session (`sessions` = trading dates; a holiday snapshot counts as
    its last session). A gap day or a noon mark differs from prev_close for
    ordinary reasons and flagged 50+ days of noise before this guard.
    """
    sessions = sorted(sessions or [])

    def session_of(day):
        before = [x for x in sessions if x <= day]
        return before[-1] if before else None

    def prev_session(day):
        before = [x for x in sessions if x < day]
        return before[-1] if before else None

    prev_px, prev_pt = {}, None
    for p in series:
        run_dir, holdings = p.get("run_dir"), p.get("holdings") or []
        last_px, prev_px = prev_px, {str(h.get("c", "")).split(".")[0]: h.get("px")
                                     for h in holdings}
        last_pt, prev_pt = prev_pt, p
        judge_xd = bool(
            sessions and last_pt and not last_pt.get("synthetic")
            and str(last_pt.get("time", ""))[11:16] >= "15:00"
            and session_of(last_pt["date"]) == prev_session(p["date"]))
        if not run_dir or not holdings:
            continue
        try:
            quotes = _read_json(Path(run_dir) / "input" / "prices.json")
        except Exception:
            continue
        if not isinstance(quotes, dict):
            continue
        for h in holdings:
            q = quotes.get(str(h.get("c", "")).split(".")[0])
            try:
                px, prev = float(h["px"]), float(q["prev_close"])
                if q.get("date") != p.get("date") or prev <= 0:
                    continue
                if abs(float(q["price"]) - px) > 0.006:
                    continue
            except (KeyError, TypeError, ValueError):
                continue
            h["d"] = round((px / prev - 1) * 100, 2)
            book_prev = last_px.get(str(h.get("c", "")).split(".")[0])
            if judge_xd and isinstance(book_prev, (int, float)) and abs(book_prev - prev) > 0.006:
                h["xd"] = book_prev
                h["qp"] = prev


def inception_point(tracking_dir: Path = TRACKING_DIR) -> dict | None:
    """The one pre-snapshot fact we can state: at portfolio creation
    (portfolio_config.created) equity was exactly starting_capital."""
    try:
        cfg = _read_json(tracking_dir / "portfolio_config.json")
        created = cfg.get("created")
        starting = cfg.get("starting_capital")
        if created and starting:
            return {"date": created, "time": "", "equity": float(starting),
                    "ret_pct": 0.0, "positions": 0, "starting": starting,
                    "holdings": [], "synthetic": True}
    except Exception:
        pass
    return None


# ------------------------------------------------------------------ day details

def _trunc(text, limit=NOTE_MAX) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_open_lookup(active: dict, trades: list[dict]) -> dict:
    """(code, entryDate) → sizing facts, so OPEN actions can show how much
    was bought. Sources: current positions + closed position files (both
    carry shares/allocatedCapital written at open time)."""
    lookup = {}
    for p in list(active.get("activePositions") or []) + list(trades):
        code = str(p.get("code", "")).split(".")[0]
        if code and p.get("entryDate"):
            lookup[(code, p["entryDate"])] = {
                "sh": p.get("shares"), "amt": p.get("allocatedCapital"),
                "ap": p.get("allocation_pct"),
            }
    return lookup


OPEN_ACTIONS = {"OPEN", "BUY", "ADD"}


def _run_status_for(point: dict) -> str | None:
    """Status of the run that produced this point's snapshot, or None.

    The equity value can be correct while its provenance is not: on 2026-08-20
    the winning snapshot came from the run that died at Gate 1, and the page
    said nothing about it.
    """
    run_dir = point.get("run_dir")
    if not run_dir:
        return None
    try:
        return (_read_json(Path(run_dir) / "manifest.json") or {}).get("status")
    except Exception:
        return None


def booked_dividends(runs_dir: Path = RUNS_DIR) -> dict:
    """{date: net dividend cash booked by that day's runs}, from each run's
    log.json `corporate_actions.applied`. Not from positions.json
    `dividendCash`: that counts OPEN positions only, so a dividend booked and
    the stock sold the same day (000739 on 2026-10-09) vanished from it."""
    out = {}
    if not runs_dir.is_dir():
        return out
    for path in list(runs_dir.glob("*/*/log.json")) + list(runs_dir.glob("*/log.json")):
        try:
            log = _read_json(path)
        except Exception:
            continue
        for run in (log.get("runs") or []) if isinstance(log, dict) else []:
            corp = (run or {}).get("corporate_actions") or {}
            for a in corp.get("applied") or []:
                day = corp.get("date")
                if day and isinstance(a.get("netCash"), (int, float)):
                    out[day] = round(out.get(day, 0.0) + a["netCash"], 2)
    return out


def collect_day_details(series: list[dict], trades: list[dict],
                        open_lookup: dict | None = None,
                        booked_divs: dict | None = None) -> dict:
    """Per-date payload for the hover side panel. day_pnl is the delta vs the
    PREVIOUS REAL snapshot (labeled 较上一快照 in the UI — gaps happen).
    NOTE: snapshots are taken at run START, so a day's OPEN actions only show
    up in holdings from the next snapshot — the UI labels this."""
    open_lookup = open_lookup or {}
    booked_divs = booked_divs or {}
    closed_by_date = {}
    for t in trades:
        closed_by_date.setdefault(t.get("exitDate"), []).append(
            {"c": t.get("code", ""), "n": t.get("name", ""),
             "r": t.get("returnPct"), "why": str(t.get("exitReason") or "")})

    details = {}
    prev_equity = None
    for p in series:
        d = p["date"]
        det = {
            "slot": SLOT_LABEL.get(p.get("slot", ""), p.get("slot", "")),
            "equity": p.get("equity"),
            "ret": p.get("ret_pct"),
            "day_pnl": None,
            "holdings": p.get("holdings", []),
            "actions": [],
            "closed": closed_by_date.get(d, []),
        }
        # Stale iff the marks predate the day being shown. Replaces the old
        # `det["pre"]`, which asked "is this a pre_run snapshot?" — a different
        # question that gave a false answer on 2026-08-20, where a 15:23
        # pre_run snapshot held that day's real closing marks and was
        # nonetheless badged 未含当日行情. Unknown freshness counts as stale:
        # absence of evidence must not render as health.
        asof = p.get("marks_asof")
        if p.get("synthetic"):
            pass                                   # inception anchor, not a run
        elif not asof:
            det["stale_marks"] = 1
        elif str(asof)[:10] < d:
            det["stale_marks"] = 1
        if p.get("synthetic"):
            det["slot"] = "起始"
        elif prev_equity is not None and isinstance(p.get("equity"), (int, float)):
            det["day_pnl"] = round(p["equity"] - prev_equity, 2)
        # Dividend cash booked that day moves equity with no price move, so the
        # holdings check must not call it a gap. Kept OUT of the if/elif above:
        # on 2026-10-09 it sat there as an elif and blanked the day's P&L.
        if not p.get("synthetic") and booked_divs.get(d):
            det["div_in"] = booked_divs[d]
        # Decisions come from the winning snapshot's run dir; if that run
        # produced none (it failed before Phase 3), fall back to a sibling slot
        # on the same date rather than discarding real decisions. 2026-08-20:
        # the afternoon run died at Gate 1 and the noon run's 4 decisions were
        # thrown away purely because the afternoon snapshot won on timestamp.
        run_dir = p.get("run_dir")
        summary_path, borrowed_from = None, None
        if run_dir:
            own = Path(run_dir) / "output" / "daily_summary.json"
            if own.exists():
                summary_path = own
            else:
                day_dir = Path(run_dir).parent if p.get("slot") != "legacy" else Path(run_dir)
                for sib in sorted(day_dir.glob("*/output/daily_summary.json")):
                    summary_path, borrowed_from = sib, sib.parent.parent.name
                    break
        if summary_path:
            if borrowed_from:
                det["actions_from_slot"] = borrowed_from
            try:
                summary = _read_json(summary_path)
                for a in summary.get("actions", []) or []:
                    code = str(a.get("code", "") or "").split(".")[0]
                    act = {
                        "c": code, "n": a.get("name", ""),
                        "a": str(a.get("action", "") or "").upper(),
                        "p": a.get("price"), "r": a.get("pnl_pct"),
                        "note": _trunc(a.get("note")),
                    }
                    if act["a"] in OPEN_ACTIONS:
                        act.update(open_lookup.get((code, d), {}))
                    det["actions"].append(act)
            except Exception:
                pass

        # Why are there no per-position notes? Four different answers, and
        # until 2026-08-21 all four rendered as "早于决策日志上线" — which is
        # true for exactly ONE date in all history (2026-02-13). Everywhere
        # else it appeared it was a fabricated explanation for a failure.
        if any(a.get("note") for a in det["actions"]):
            det["notes_absent_reason"] = None
        elif det["actions"]:
            det["notes_absent_reason"] = "predates_note_log"   # ran, logged, no notes
        else:
            status = _run_status_for(p)
            det["notes_absent_reason"] = ("run_failed" if status == "failed"
                                          else "unknown")
        if _run_status_for(p) == "failed":
            det["from_failed_run"] = True

        details[d] = det
        if not p.get("synthetic") and isinstance(p.get("equity"), (int, float)):
            prev_equity = p["equity"]
    return details


# ---------------------------------------------------------------- index overlay

def fetch_index_kline() -> list[dict] | None:
    """Sina daily kline for 上证指数 (sh000001): [{day, open, high, low, close}].
    None on any failure — callers fall back to their caches. One call feeds
    both the close cache and the OHLC cache."""
    try:
        import requests
        resp = requests.get(
            "https://quotes.sina.cn/cn/api/jsonp_v2.php/x/CN_MarketDataService.getKLineData",
            params={"symbol": "sh000001", "scale": "240", "ma": "no", "datalen": "1023"},
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0",
                     "Referer": "https://finance.sina.com.cn"})
        text = resp.text
        return json.loads(text[text.index("(") + 1: text.rindex(")")])
    except Exception as e:
        print(f"[site] index fetch failed ({e}); using caches", file=sys.stderr)
        return None


def _merge_into_cache(cache_path: Path, fresh: dict, parse) -> dict:
    """Cache ∪ fresh (fresh wins), written back so coverage only grows."""
    cached = {}
    if cache_path.exists():
        try:
            cached = {k: parse(v) for k, v in _read_json(cache_path).items()}
        except Exception:
            cached = {}
    if not fresh:
        return cached
    merged = {**cached, **fresh}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(dict(sorted(merged.items())), ensure_ascii=False, indent=0) + "\n",
        encoding="utf-8")
    return merged


def load_index_closes(kline: list[dict] | None,
                      cache_path: Path = INDEX_CACHE) -> dict:
    """{iso_date: close} for 上证指数: kline merged into the cache, cache alone
    when the fetch failed, {} when neither exists."""
    fresh = {d["day"]: float(d["close"]) for d in (kline or [])}
    return _merge_into_cache(cache_path, fresh, float)


def load_index_bars(kline: list[dict] | None,
                    cache_path: Path = INDEX_OHLC_CACHE) -> dict:
    """{iso_date: [open, high, low, close]} for 上证指数, same merge rules as
    the close cache. Kept in its own file: settled market.json quotes only
    give a close, so close coverage and bar coverage differ by design."""
    fresh = {}
    for d in kline or []:
        try:
            fresh[d["day"]] = [float(d[k]) for k in ("open", "high", "low", "close")]
        except (KeyError, TypeError, ValueError):
            continue
    return _merge_into_cache(cache_path, fresh, lambda v: [float(x) for x in v])


def settled_index_closes(runs_dir: Path = RUNS_DIR) -> dict:
    """{iso_date: close} for 上证指数 from each run's real-time market.json quote,
    kept only when the quote is for the run's own day and taken at/after 15:00.

    Sina's daily kline is batch-built and can lag the close by hours: on
    2026-09-28 the 15:13 build had no bar for the day and forward-filled 09-24
    through a -1.67% session. Noon quotes are intraday and never qualify; a
    holiday run carries the previous session's date and is dropped too.
    """
    closes = {}
    if not runs_dir.is_dir():
        return closes
    for path in runs_dir.rglob("input/market.json"):
        try:
            data = _read_json(path)
            quote = data["indices"]["上证指数"]
            taken = datetime.fromisoformat(data["timestamp"])
            close = float(quote["close"])
        except Exception:
            continue
        if quote.get("date") == taken.date().isoformat() and taken.hour >= 15:
            closes[quote["date"]] = close
    return closes


def merge_index_closes(kline: dict, quotes: dict) -> dict:
    """Kline closes win; quotes only fill dates AFTER the kline's last bar.

    The kline only lags at its tail. A quote for a date inside its coverage
    that it has no bar for is a non-trading day: 2026-09-25 (中秋) carried a
    quote stamped 09-25 with 09-24's close — the holiday-stamping bug fixed
    09-29 — and drew a fake close-only tick on the chart."""
    last = max(kline) if kline else ""
    return {**{d: c for d, c in quotes.items() if d > last}, **kline}


def rebase_index(closes: dict, dates: list[str], starting: float) -> dict:
    """Map each series date → index rebased to `starting` at the first date.
    Uses the last close <= date (holiday forward-fill). {} if no coverage."""
    if not closes or not dates:
        return {}
    sorted_days = sorted(closes)

    def last_close_leq(d):
        prior = [x for x in sorted_days if x <= d]
        return closes[prior[-1]] if prior else None

    base = last_close_leq(dates[0])
    if not base:
        return {}
    out = {}
    for d in dates:
        c = last_close_leq(d)
        if c:
            out[d] = round(starting * c / base, 0)
    return out


def index_base(closes: dict, first_date: str) -> float | None:
    """The index close the rebase is anchored to — last close <= first_date.

    Exposed separately so the chart can label a right-hand axis in real index
    points. Kept out of `rebase_index`'s return value on purpose: that function's
    contract (date → rebased value) is asserted directly by tests and read by the
    template, and widening it to a tuple would buy nothing here.
    """
    if not closes or not first_date:
        return None
    prior = [d for d in sorted(closes) if d <= first_date]
    return closes[prior[-1]] if prior else None


def index_day_change(closes: dict, date: str) -> tuple[float, str] | None:
    """(上证 % change, previous index date) for `date` vs the previous index
    close — the number a quote app shows. None unless `date` has its own close
    (no forward-fill: a holiday has no day change)."""
    if date not in closes:
        return None
    prior = [d for d in closes if d < date]
    if not prior:
        return None
    prev = max(prior)
    return round((closes[date] / closes[prev] - 1) * 100, 2), prev


def intraday_index_pcts(series: list[dict]) -> dict:
    """{date: 上证 change_pct seen by the run} for days whose chart point is a
    snapshot taken before 15:00.

    Such a point's equity is an intraday mark, while the day's candle is the
    15:00 close — on 2026-10-08 the noon run saw 上证 −0.27%, the close was
    −0.79%. Showing both keeps the two from being read as the same moment.
    """
    out = {}
    for p in series:
        if p.get("synthetic") or not p.get("run_dir") or not p.get("time"):
            continue
        try:
            if datetime.fromisoformat(p["time"]).hour >= 15:
                continue
            quote = _read_json(Path(p["run_dir"]) / "input" / "market.json")["indices"]["上证指数"]
            if quote.get("date") == p["date"]:
                out[p["date"]] = float(quote["change_pct"])
        except Exception:
            continue
    return out


# ------------------------------------------------------------- events + badges

def load_events() -> dict | None:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import event_calendar
        return event_calendar.upcoming()
    except Exception as e:
        print(f"[site] events unavailable: {e}", file=sys.stderr)
        return None


def load_latest_run_status() -> dict | None:
    """Status of the most recent run, for the header banner.

    The site is rebuilt right after every manifest write (2026-08-14), so a
    run that fails downstream of apply still refreshes the page — the data
    stays true and this says so out loud. Sorted by run_started_at, never by
    slot name ("afternoon" < "noon" alphabetically)."""
    newest = None
    for mf in RUNS_DIR.glob("*/*/manifest.json"):
        try:
            m = _read_json(mf)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(m, dict) or not m.get("run_started_at"):
            continue
        if newest is None or m["run_started_at"] > newest["run_started_at"]:
            newest = m
    if not newest:
        return None
    gates = newest.get("gates") or {}
    failed_gates = [g for g, v in gates.items() if isinstance(v, dict) and v.get("passed") is False]
    if newest.get("status") != "failed" and not failed_gates:
        return None
    reasons = []
    for g in failed_gates:
        reasons.extend(gates[g].get("hard_fails") or [])
    return {
        "date": newest.get("date", "?"),
        "slot": newest.get("slot", "?"),
        "reasons": reasons[:3],
        # Apply ran ⇒ the numbers below are real, just uncommitted.
        "applied": (newest.get("phases") or {}).get("apply") is not None,
    }


def load_badges(series: list[dict]) -> list[dict]:
    """Header badges from the latest real run's input artifacts."""
    badges = []
    run_dir = next((p.get("run_dir") for p in reversed(series) if p.get("run_dir")), None)
    if not run_dir:
        return badges
    try:
        r = _read_json(Path(run_dir) / "input" / "regime.json")
        if r.get("label"):
            badges.append({
                "k": "市场机制(只读)",
                "v": r["label"],
                "sub": f"IC20 {r.get('rolling_ic20', '?')} · 止损率10日 {r.get('pool_stop_rate10', '?')}",
            })
    except Exception:
        pass
    try:
        g = _read_json(Path(run_dir) / "input" / "gex.json")
        overall = g.get("overall") or {}
        sig = overall.get("signal") or overall.get("summary")
        if not sig:
            data = g.get("etf_gex_data") or []
            neg = sum(1 for u in data if "净负" in str(u.get("regime", "")))
            sig = f"净负gamma {neg}/{len(data)}" if data else None
        if sig:
            badges.append({"k": "GEX", "v": str(sig), "sub": "期权实验室"})
    except Exception:
        pass
    return badges


# ----------------------------------------------------------------------- misc

def load_active(tracking_dir: Path = TRACKING_DIR) -> dict:
    try:
        return _read_json(tracking_dir / "positions.json")
    except Exception:
        return {"portfolio": {}, "activePositions": []}


def load_closed_trades(tracking_dir: Path = TRACKING_DIR) -> list[dict]:
    trades = []
    closed = tracking_dir / "closed"
    if not closed.is_dir():
        return trades
    for f in sorted(closed.glob("*.json")):
        try:
            p = _read_json(f)
            if p.get("exitDate") and p.get("returnPct") is not None:
                trades.append(p)
        except Exception:
            pass
    trades.sort(key=lambda t: t.get("exitDate", ""), reverse=True)
    return trades


# ------------------------------------------------------------ position history

HIST_BARS_BEFORE = 20   # sessions of context before entry
HIST_BARS_AFTER = 5     # and after exit
HIST_NOTE_MAX = 400


def trade_key(code: str, entry_date: str) -> str:
    """One round trip = code + entry date (a code can be traded many times)."""
    return f"{str(code).split('.')[0]}|{entry_date}"


def load_active_trade_files(tracking_dir: Path = TRACKING_DIR) -> list[dict]:
    """tracking/<code>.json for open positions — positions.json has no history."""
    out = []
    for f in sorted(tracking_dir.glob("*.json")):
        try:
            p = _read_json(f)
        except Exception:
            continue
        if isinstance(p, dict) and p.get("status") == "active" and p.get("entryDate"):
            out.append(p)
    return out


def _stock_bars(conn, code: str, start: str, end: str | None) -> list[list]:
    """Raw (unadjusted, as the book prices them) daily bars around a trade:
    HIST_BARS_BEFORE sessions before `start`, through `end` (None = latest),
    plus HIST_BARS_AFTER sessions after it."""
    q = "SELECT date, open, high, low, close FROM daily_prices WHERE code = ? AND "
    before = conn.execute(q + "date < ? ORDER BY date DESC LIMIT ?",
                          (code, start, HIST_BARS_BEFORE)).fetchall()[::-1]
    if end:
        during = conn.execute(q + "date >= ? AND date <= ? ORDER BY date",
                              (code, start, end)).fetchall()
        after = conn.execute(q + "date > ? ORDER BY date LIMIT ?",
                             (code, end, HIST_BARS_AFTER)).fetchall()
    else:
        during = conn.execute(q + "date >= ? ORDER BY date", (code, start)).fetchall()
        after = []
    return [[d, o, h, l, c] for d, o, h, l, c in before + during + after
            if None not in (o, h, l, c)]


def collect_trade_histories(trades: list[dict], db_path: Path = PRICE_DB) -> dict:
    """{trade_key: payload} for the click-a-position view.

    Bars come from the local price DB; when it is missing or unreadable each
    trade still gets its timeline, with `bars_missing` set so the UI says why
    there is no chart instead of drawing an empty one.
    """
    conn = None
    if db_path and Path(db_path).exists():
        try:
            import sqlite3
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        except Exception as e:
            print(f"[site] price DB unreadable ({e}); position charts off", file=sys.stderr)
    out = {}
    for t in trades:
        code = str(t.get("code", "")).split(".")[0]
        ed = t.get("entryDate")
        if not code or not ed:
            continue
        events = []
        # Stop levels over time: [date, level] from that date on; level None =
        # unknown from that date (a RAISE_STOP that recorded no value — true of
        # every raise before the run log started writing new_stop). Never carry
        # an old level past a raise: 603259 drew its 120.18 opening stop to
        # 10-08 while the real stop had been 139.15 since 08-07.
        stops = []
        if isinstance(t.get("stopLoss"), (int, float)):
            stops.append([ed, t["stopLoss"]])
        last_raise = None
        for h in t.get("history") or []:
            ev = {"d": h.get("date"), "s": SLOT_LABEL.get(h.get("slot"), h.get("slot") or ""),
                  "a": h.get("action"), "px": h.get("price"), "r": h.get("change_pct"),
                  "note": _trunc(h.get("note"), HIST_NOTE_MAX)}
            new_stop = h.get("new_stop", h.get("stop"))
            if isinstance(new_stop, (int, float)):
                ev["st"] = new_stop
                if not stops or stops[-1][1] != new_stop:
                    stops.append([h.get("date"), new_stop])
            elif h.get("action") == "RAISE_STOP":
                # one entry per raise, so the last one can take currentStop
                stops.append([h.get("date"), None])
            if h.get("action") == "RAISE_STOP":
                last_raise = len(stops) - 1
            events.append(ev)
        # currentStop is the result of the LAST raise, so it is known from
        # that raise on even when the raise itself recorded no value.
        cs = t.get("currentStop")
        if (last_raise is not None and isinstance(cs, (int, float))
                and stops[last_raise][1] is None):
            stops[last_raise][1] = cs
        rec = {"c": code, "n": t.get("name", ""), "ed": ed, "xd": t.get("exitDate"),
               "ep": t.get("entryPrice"), "xp": t.get("exitPrice"),
               "r": t.get("returnPct") if t.get("exitDate") else t.get("pnl_pct"),
               "tp": t.get("targetPrice"), "cs": t.get("currentStop"),
               "sec": t.get("sector") or "", "why": _trunc(t.get("exitReason"), HIST_NOTE_MAX),
               "th": _trunc(t.get("thesis"), HIST_NOTE_MAX), "sh": t.get("shares"),
               "stops": stops, "ev": events, "bars": []}
        if conn is None:
            rec["bars_missing"] = "本地价格库不可用"
        else:
            try:
                rec["bars"] = _stock_bars(conn, code, ed, t.get("exitDate"))
            except Exception as e:
                rec["bars_missing"] = f"价格库读取失败: {e}"
        out[trade_key(code, ed)] = rec
    if conn is not None:
        conn.close()
    return out


def compute_stats(series: list[dict], trades: list[dict]) -> dict:
    stats = {}
    if series:
        equities = [p["equity"] for p in series if p["equity"]]
        peak, max_dd = float("-inf"), 0.0
        for e in equities:
            peak = max(peak, e)
            if peak > 0:
                max_dd = max(max_dd, (peak - e) / peak * 100)
        stats["max_drawdown_pct"] = round(max_dd, 2)
    wins = [t for t in trades if t["returnPct"] > 0]
    losses = [t for t in trades if t["returnPct"] <= 0]
    stats["n_trades"] = len(trades)
    stats["n_wins"] = len(wins)
    stats["win_rate"] = round(len(wins) / len(trades) * 100, 1) if trades else None
    stats["avg_win"] = round(sum(t["returnPct"] for t in wins) / len(wins), 2) if wins else None
    stats["avg_loss"] = round(sum(t["returnPct"] for t in losses) / len(losses), 2) if losses else None
    gross_win = sum(t["returnPct"] for t in wins)
    gross_loss = abs(sum(t["returnPct"] for t in losses))
    stats["profit_factor"] = round(gross_win / gross_loss, 2) if gross_loss else None
    return stats


def _fmt_money(v) -> str:
    return f"{v:,.0f}" if isinstance(v, (int, float)) else "—"


def _pnl_cls(v) -> str:
    if not isinstance(v, (int, float)) or v == 0:
        return "flat"
    return "up" if v > 0 else "down"  # up=red, down=green (A-share)


def _slot_tag(slot) -> str:
    """Which run filled it — noon vs afternoon (blank when unknown: the
    pre-2026-08-11 history has no slot recorded, and a guess would lie)."""
    label = SLOT_LABEL.get(slot or "")
    return f" <span class='slot'>{html.escape(label)}</span>" if label else ""


def _pct(v, signed=True) -> str:
    if not isinstance(v, (int, float)):
        return "—"
    return f"{v:+.2f}%" if signed else f"{v:.2f}%"


# -------------------------------------------------------------------- rendering

EVENT_ICON = {"risk": "🔴", "two_sided": "🔶", "supportive": "🟢"}
IMPACT_CN = {"high": "高", "medium": "中", "low": "低"}


def _event_item(ev: dict, dated: bool) -> str:
    icon = EVENT_ICON.get(ev.get("direction", ""), "🔶")
    impact = IMPACT_CN.get(ev.get("impact", ""), ev.get("impact", "?"))
    name = html.escape(ev.get("name", ""))
    notes = html.escape(_trunc(ev.get("notes", ""), 140))
    src = str(ev.get("source", "") or "")
    if src.startswith("http"):
        src_html = f'<a href="{html.escape(src)}" target="_blank" rel="noopener">来源</a>'
    else:
        src_html = f'<span title="{html.escape(src)}">来源: 内部</span>' if src else "来源: 未标注"
    if dated:
        when = (f"<b>{html.escape(ev.get('a_share_impact_date') or ev.get('date', ''))}</b>"
                f" <span class='tminus'>T-{ev.get('days_until_impact', '?')}</span>")
    else:
        when = "<b>持续中</b>"
    return (f'<div class="ev"><div class="ev-when">{icon} {when}'
            f' <span class="chip">冲击:{html.escape(str(impact))}</span></div>'
            f'<div class="ev-name">{name}</div>'
            f'<div class="ev-note">{notes} <span class="ev-src">〔{src_html}〕</span></div></div>')


ASSETS_DIR = Path(__file__).parent / "site_assets"
# The page's JS and CSS live in real files (2026-10-08) so editors and
# linters can see them; build inlines them, so the output is still one
# offline HTML file. JS data arrives by token replacement:
# __DATA__ __DETAILS__ __STARTING__ __IDXBASE__ __TRADES__
CHART_JS = (ASSETS_DIR / "app.js").read_text(encoding="utf-8").rstrip("\n")
SITE_CSS = (ASSETS_DIR / "app.css").read_text(encoding="utf-8").rstrip("\n")


def render_html(series, active, trades, stats, details=None, index_rebased=None,
                events=None, badges=None, generated_at=None, run_status=None,
                idx_base=None, index_bars=None, index_closes=None,
                intraday_idx=None, trade_hist=None) -> str:
    pf = active.get("portfolio", {})
    positions = active.get("activePositions", [])
    details = details or {}
    index_rebased = index_rebased or {}
    index_bars = index_bars or {}
    index_closes = index_closes or {}
    intraday_idx = intraday_idx or {}
    trade_hist = trade_hist or {}
    badges = badges or []
    generated_at = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")

    run_banner = ""
    if run_status:
        why = "".join(f"<li>{html.escape(str(r))}</li>" for r in run_status.get("reasons") or [])
        tail = ("下方数据已落盘，但该次运行未提交" if run_status.get("applied")
                else "该次运行未写入新数据，下方为上一次成功运行的结果")
        run_banner = (
            f'<div class="runfail"><b>⚠ 最新一次运行未通过校验</b>'
            f'（{html.escape(run_status.get("date", "?"))} '
            f'{html.escape(run_status.get("slot", "?"))}）'
            f'{f"<ul>{why}</ul>" if why else ""}'
            f'<div class="rf-tail">{tail}</div></div>'
        )

    # Per-point keys: d date · e equity · r cum ret% · n positions · s synthetic
    # · t snapshot HH:MM · p day pnl · pr day % · pd prev snapshot date · i rebased 上证 close
    # (forward-filled, sets the y-range) · k real [o,h,l,c] (exact date only)
    # · kc real close when only a settled quote exists · ic 上证 day % ·
    # ipd prev index date · pdi pd mapped to its last session (holiday) · iq 上证 % at a pre-15:00 snapshot.
    chart_data = []
    prev_real = None
    prev_real_date = None
    for p in series:
        if not isinstance(p.get("equity"), (int, float)):
            continue
        d = p["date"]
        pt = {"d": d, "e": round(p["equity"], 0), "r": p.get("ret_pct"),
              "n": p.get("positions")}
        if p.get("synthetic"):
            pt["s"] = 1
        elif p.get("time"):
            pt["t"] = str(p["time"])[11:16]
        if not p.get("synthetic") and prev_real is not None:
            pt["p"] = round(p["equity"] - prev_real, 2)
            if prev_real:
                pt["pr"] = round((p["equity"] / prev_real - 1) * 100, 2)
            pt["pd"] = prev_real_date
        if d in index_rebased:
            pt["i"] = index_rebased[d]
        if d in index_bars:
            pt["k"] = index_bars[d]
        elif d in index_closes:
            pt["kc"] = index_closes[d]
        chg = index_day_change(index_closes, d)
        if chg:
            pt["ic"], pt["ipd"] = chg
            # A previous snapshot on a non-trading day (a holiday run) holds
            # the last session's values: compare spans by that session.
            pd = pt.get("pd")
            if pd and pd not in index_closes:
                before = [x for x in index_closes if x <= pd]
                if before:
                    pt["pdi"] = max(before)
        if d in intraday_idx:
            pt["iq"] = intraday_idx[d]
        if not p.get("synthetic"):
            prev_real = p["equity"]
            prev_real_date = d
        chart_data.append(pt)
    starting = (series[0].get("starting") if series else None) or pf.get("startingCapital") or 1000000

    cards = [
        ("总资产", _fmt_money(pf.get("totalEquity")), _pnl_cls(pf.get("totalPnl"))),
        ("总收益率", _pct(pf.get("totalReturnPct")), _pnl_cls(pf.get("totalReturnPct"))),
        ("今日盈亏", _fmt_money(pf.get("dayPnl")), _pnl_cls(pf.get("dayPnl"))),
        ("已实现盈亏", _fmt_money(pf.get("realizedPnl")), _pnl_cls(pf.get("realizedPnl"))),
        ("未实现盈亏", _fmt_money(pf.get("unrealizedPnl")), _pnl_cls(pf.get("unrealizedPnl"))),
        ("现金占比", _pct(pf.get("cashPct"), signed=False), "flat"),
        ("最大回撤", _pct(stats.get("max_drawdown_pct"), signed=False), "down" if stats.get("max_drawdown_pct") else "flat"),
        ("持仓", f"{pf.get('positionsUsed', '—')}/{pf.get('positionsMax', '—')}", "flat"),
    ]
    cards_html = "\n".join(
        f'<div class="card"><div class="label">{html.escape(k)}</div>'
        f'<div class="value {cls}">{html.escape(str(v))}</div></div>'
        for k, v, cls in cards
    )
    badges_html = "\n".join(
        f'<span class="hbadge" title="{html.escape(b.get("sub", ""))}">'
        f'{html.escape(b["k"])}: <b>{html.escape(str(b["v"]))}</b></span>'
        for b in badges
    )

    def _tk_attr(t):
        k = trade_key(t.get("code", ""), t.get("entryDate", ""))
        return f" class='tk' data-tk='{html.escape(k)}' title='点击查看该笔交易走势'" if k in trade_hist else ""

    pos_rows = "\n".join(
        f"<tr{_tk_attr(p)}>"
        f"<td>{html.escape(p.get('code', ''))}</td>"
        f"<td>{html.escape(p.get('name', ''))}</td>"
        f"<td>{html.escape(p.get('entryDate', ''))}"
        f"{_slot_tag(p.get('entrySlot'))}</td>"
        f"<td class='num'>{p.get('entryPrice', '—')}</td>"
        f"<td class='num'>{p.get('currentPrice', '—')}</td>"
        f"<td class='num {_pnl_cls(p.get('pnl_pct'))}'>{_pct(p.get('pnl_pct'))}</td>"
        f"<td class='num'>{p.get('currentStop', '—')}</td>"
        f"<td class='num'>{_pct(p.get('weight_pct'), signed=False)}</td>"
        f"<td>{html.escape(p.get('sector', '') or '')}</td>"
        "</tr>"
        for p in sorted(positions, key=lambda x: -(x.get("pnl_pct") or 0))
    ) or "<tr><td colspan='9' class='empty'>当前空仓</td></tr>"

    trade_rows = "\n".join(
        f"<tr{_tk_attr(t)}>"
        f"<td>{html.escape(t.get('code', ''))}</td>"
        f"<td>{html.escape(t.get('name', ''))}</td>"
        f"<td>{html.escape(t.get('entryDate', ''))}{_slot_tag(t.get('entrySlot'))}</td>"
        f"<td>{html.escape(t.get('exitDate', ''))}{_slot_tag(t.get('exitSlot'))}</td>"
        f"<td class='num'>{t.get('holdingDays', '—')}</td>"
        f"<td class='num {_pnl_cls(t.get('returnPct'))}'>{_pct(t.get('returnPct'))}</td>"
        f"<td class='why'><div>{html.escape(str(t.get('exitReason', '') or ''))}</div></td>"
        "</tr>"
        for t in trades
    ) or "<tr><td colspan='7' class='empty'>暂无已平仓交易</td></tr>"

    win_summary = (
        f"共 {stats['n_trades']} 笔 · 胜率 {stats['win_rate']}% ({stats['n_wins']}胜) · "
        f"平均盈利 {_pct(stats['avg_win'])} · 平均亏损 {_pct(stats['avg_loss'])} · "
        f"盈亏比 {stats['profit_factor'] if stats['profit_factor'] is not None else '—'}"
        if stats.get("n_trades") else "暂无已平仓交易"
    )

    events_html = ""
    if events and (events.get("dated") or events.get("ongoing")):
        items = [_event_item(ev, dated=True) for ev in events.get("dated", [])]
        items += [_event_item(ev, dated=False) for ev in events.get("ongoing", [])]
        events_html = (
            f"<h2>未来事件窗口 <span class='muted-h'>{html.escape(str(events.get('as_of', '')))} 起 "
            f"{events.get('window_days', '?')} 天 · 🔴风险 🔶双向 🟢支撑</span></h2>"
            f"<div class='events'>{''.join(items)}</div>"
        )

    idx_note = ("上证指数取自新浪财经日K(sh000001)，等额起点=起始日按初始资金折算，缓存于 "
                "<code>data/index_cache/sh000001{,_ohlc}.json</code>。" if index_rebased else
                "（上证指数数据不可用——离线且无缓存）")

    js = (CHART_JS
          .replace("__DATA__", json.dumps(chart_data, ensure_ascii=False))
          .replace("__DETAILS__", json.dumps(details, ensure_ascii=False))
          .replace("__STARTING__", json.dumps(starting))
          .replace("__IDXBASE__", json.dumps(idx_base))
          .replace("__TRADES__", json.dumps(trade_hist, ensure_ascii=False)))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>组合总览 · 模拟盘</title>
<style>
{SITE_CSS}
</style>
</head>
<body>
<div class="wrap">
  <h1>组合总览 <span style="font-weight:400;color:var(--muted);font-size:14px">模拟盘 · A股动量策略</span></h1>
  <div class="sub">生成于 {html.escape(generated_at)} · 红涨绿跌</div>
  {run_banner}
  <div class="hbadges">{badges_html}</div>

  <div class="cards">{cards_html}</div>

  <h2>每日总资产 <span class="muted-h">悬停查看当日详情 · 点击固定</span>
    <span class="range" id="range"><button data-n="20">近20日</button><button data-n="60">近60日</button><button data-n="0">全部</button></span></h2>
  <div class="main">
    <div>
      <div class="panel">
        <svg id="chart" viewBox="0 0 960 340" preserveAspectRatio="xMidYMid meet"></svg>
        <div class="legend">
          <span><span class="sw" style="background:#3b6ea5"></span>组合总资产</span>&nbsp;&nbsp;
          <span id="lg-idx"><span class="sw sw-k"></span>上证指数日K（等额起点，红涨绿跌，点击隐藏）</span>&nbsp;&nbsp;
          <span><span class="sw" style="background:#9aa3b2;height:1px;border-top:2px dashed #9aa3b2"></span>初始资金 {_fmt_money(starting)}</span>
        </div>
        <svg id="cmp" viewBox="0 0 960 58" preserveAspectRatio="xMidYMid meet" style="margin-top:6px"></svg>
        <div class="legend">逐日涨跌 %：组合较上一快照 · 上证较前一交易日收盘 · 超额 = 组合 − 上证（区间不同不算；* = 午盘快照：组合为盘中值，超额按运行时上证计算，无运行时行情则不算）</div>
        <svg id="bars" viewBox="0 0 960 96" preserveAspectRatio="xMidYMid meet" style="margin-top:8px"></svg>
        <div class="legend">每日盈亏（较上一快照）</div>
        <div class="note">每个交易日取当日最后一次流水线快照的 totalEquity；曲线首点为组合起始日（portfolio_config.created，等于初始资金），起始日至首个每日快照间无逐日数据（斜虚线段示意）。{idx_note}</div>
      </div>
    </div>
    <div class="panel side"><div id="day"></div></div>
  </div>
  <div id="tip"></div>
  <div id="rowtip"></div>
  <div id="posmodal" hidden><div class="pm-box" role="dialog" aria-modal="true">
    <button class="pm-x" id="pm-x" title="关闭 (Esc)">✕</button><div id="pm-body"></div></div></div>

  {events_html}

  <h2>当前持仓</h2>
  <table>
    <thead><tr><th>代码</th><th>名称</th><th>建仓日</th><th style="text-align:right">成本</th>
    <th style="text-align:right">现价</th><th style="text-align:right">盈亏</th>
    <th style="text-align:right">止损</th><th style="text-align:right">权重</th><th>板块</th></tr></thead>
    <tbody>{pos_rows}</tbody>
  </table>

  <h2>已平仓交易</h2>
  <div class="note" style="margin:0 0 8px">{html.escape(win_summary)}</div>
  <table>
    <thead><tr><th>代码</th><th>名称</th><th>建仓日</th><th>平仓日</th>
    <th style="text-align:right">持有天数</th><th style="text-align:right">收益</th><th>平仓原因</th></tr></thead>
    <tbody>{trade_rows}</tbody>
  </table>

  <footer>
    数据来源〔内部数据〕: <code>runs/*/input/positions_snapshot.json</code>（资产曲线/每日持仓）·
    <code>runs/*/output/daily_summary.json</code>（每日操作）·
    <code>tracking/</code>（持仓/历史交易/起始配置）·
    <code>scripts/event_calendar.py</code>（事件窗口）· 新浪财经 sh000001 日K（上证对比）。
    重新生成: <code>python3 scripts/build_site.py</code>
  </footer>
</div>

<script>
{js}
</script>
</body>
</html>
"""


def build(site_dir: Path = SITE_DIR) -> Path:
    series = collect_equity_series()
    anchor = inception_point()
    if anchor and (not series or anchor["date"] < series[0]["date"]):
        series.insert(0, anchor)
    active = load_active()
    trades = load_closed_trades()
    stats = compute_stats(series, trades)
    kline = fetch_index_kline()
    index_closes = merge_index_closes(load_index_closes(kline), settled_index_closes())
    index_bars = load_index_bars(kline)
    attach_holding_day_pcts(series, sessions=index_closes)   # before details copies holdings
    details = collect_day_details(series, trades, build_open_lookup(active, trades),
                                  booked_divs=booked_dividends())
    starting = (series[0].get("starting") if series else None) or 1000000
    dates = [p["date"] for p in series]
    index_rebased = rebase_index(index_closes, dates, float(starting))
    idx_base = index_base(index_closes, dates[0]) if dates else None
    open_files = load_active_trade_files()
    live_pnl = {str(p.get("code", "")).split(".")[0]: p.get("pnl_pct")
                for p in active.get("activePositions", [])}
    for t in open_files:
        t.setdefault("pnl_pct", live_pnl.get(str(t.get("code", "")).split(".")[0]))
    trade_hist = collect_trade_histories(trades + open_files)
    events = load_events()
    badges = load_badges(series)
    site_dir.mkdir(parents=True, exist_ok=True)
    out = site_dir / "index.html"
    out.write_text(render_html(series, active, trades, stats, details=details,
                               index_rebased=index_rebased, events=events,
                               badges=badges, run_status=load_latest_run_status(),
                               idx_base=idx_base, index_bars=index_bars,
                               index_closes=index_closes,
                               intraday_idx=intraday_index_pcts(series),
                               trade_hist=trade_hist),
                   encoding="utf-8")
    print(f"[site] {out} — {len(series)} equity points "
          f"({len(index_rebased)} with index overlay), "
          f"{len(active.get('activePositions', []))} positions, "
          f"{len(trades)} closed trades, "
          f"{len((events or {}).get('dated', []))} dated events",
          file=sys.stderr)
    return out


if __name__ == "__main__":
    build()
