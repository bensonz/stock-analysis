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
  - sina index kline (sh000001) → 上证指数 overlay, rebased to starting
    capital at inception; cached in data/index_cache/sh000001.json so
    offline rebuilds still work (build degrades to cache, then to no overlay)
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
             "v": p.get("currentValue"), "w": p.get("weight_pct")}
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


def collect_day_details(series: list[dict], trades: list[dict],
                        open_lookup: dict | None = None) -> dict:
    """Per-date payload for the hover side panel. day_pnl is the delta vs the
    PREVIOUS REAL snapshot (labeled 较上一快照 in the UI — gaps happen).
    NOTE: snapshots are taken at run START, so a day's OPEN actions only show
    up in holdings from the next snapshot — the UI labels this."""
    open_lookup = open_lookup or {}
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

def load_index_closes(cache_path: Path = INDEX_CACHE) -> dict:
    """{iso_date: close} for 上证指数. Network first (merged into cache so
    coverage only grows), cache fallback, {} when neither works."""
    closes = {}
    if cache_path.exists():
        try:
            closes = {k: float(v) for k, v in _read_json(cache_path).items()}
        except Exception:
            closes = {}
    try:
        import requests
        resp = requests.get(
            "https://quotes.sina.cn/cn/api/jsonp_v2.php/x/CN_MarketDataService.getKLineData",
            params={"symbol": "sh000001", "scale": "240", "ma": "no", "datalen": "1023"},
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0",
                     "Referer": "https://finance.sina.com.cn"})
        text = resp.text
        data = json.loads(text[text.index("(") + 1: text.rindex(")")])
        closes.update({d["day"]: float(d["close"]) for d in data})
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(dict(sorted(closes.items())), ensure_ascii=False, indent=0) + "\n",
            encoding="utf-8")
    except Exception as e:
        print(f"[site] index fetch failed ({e}); using cache "
              f"({len(closes)} closes)", file=sys.stderr)
    return closes


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


# JS kept as a plain (non-f) string — data injected via token replacement, so
# no brace-escaping games. Tokens: __DATA__ __DETAILS__ __STARTING__
CHART_JS = r"""
const DATA = __DATA__;
const DETAILS = __DETAILS__;
const STARTING = __STARTING__;
const fmtM = v => (v == null ? "—" : Math.round(v).toLocaleString());
const pnlCls = v => (typeof v !== "number" || v === 0) ? "flat" : (v > 0 ? "up" : "down");
const sign = v => (v > 0 ? "+" : "");
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

// ---------------- side panel
const dayEl = document.getElementById("day");
let pinned = null;
let latestDay = null;
const ACTION_CN = {OPEN:"开", BUY:"开", SELL:"平", ADD:"加", TRIM:"减", HOLD:"持"};
const OPENS = {OPEN:1, BUY:1, ADD:1};
function unpin() { pinned = null; if (latestDay) renderDay(latestDay); }
function renderDay(d) {
  const det = DETAILS[d];
  if (!det) { dayEl.innerHTML = `<div class='d-date'>${esc(d)}</div><div class='note'>无记录</div>`; return; }
  const pinBtn = pinned ? ` <button id="unpin" title="取消固定 (Esc)">📌 ✕</button>` : "";
  let h = `<div class="d-date">${esc(d)} <span class="chip">${esc(det.slot)}</span>`
        + (det.stale_marks ? ` <span class="chip warn" title="该日快照里的持仓市值早于当日，或无法确定其时点">持仓市值非当日</span>` : "")
        + (det.from_failed_run ? ` <span class="chip warn" title="该数值取自当日一次失败的运行所留下的快照——数值本身可用，但该次运行未走完">来自失败运行</span>` : "")
        + `${pinBtn}</div>`;
  h += `<div class="d-equity">${fmtM(det.equity)}</div>`;
  const dp = det.day_pnl;
  h += `<div class="d-sub"><span class="${pnlCls(dp)}">${dp == null ? "—" : sign(dp) + fmtM(dp)}</span> 较上一快照`
     + ` · 累计 <span class="${pnlCls(det.ret)}">${det.ret == null ? "—" : sign(det.ret) + det.ret + "%"}</span></div>`;
  const trades = (det.actions || []).filter(a => a.a !== "HOLD");
  const hasOpens = trades.some(a => OPENS[a.a]);
  if (trades.length) {
    h += `<h4>当日交易</h4>`;
    for (const a of trades) {
      let size = "";
      if (a.sh) {
        size = `<div class="d-size">${a.sh.toLocaleString()}股`
             + (a.amt ? ` ≈ ${fmtM(a.amt)}` : "")
             + (a.ap ? ` · ${a.ap}%仓位` : "") + `</div>`;
      }
      h += `<div class="d-act"><span class="badge b-${a.a === "SELL" ? "sell" : "open"}">${ACTION_CN[a.a] || esc(a.a)}</span>`
         + ` <b>${esc(a.n)}</b> <span class="muted">${a.p ?? ""}</span>`
         + ` <span class="${pnlCls(a.r)}">${a.r == null ? "" : sign(a.r) + a.r + "%"}</span>`
         + size
         + `<div class="d-note">${esc(a.note)}</div></div>`;
    }
  }
  if (det.closed && det.closed.length) {
    h += `<h4>当日平仓结果</h4>`;
    for (const t of det.closed) {
      h += `<div class="d-row"><b>${esc(t.n)}</b><span class="${pnlCls(t.r)}">${sign(t.r)}${t.r}%</span></div>`
         + `<div class="d-note">${esc(t.why)}</div>`;
    }
  }
  if (det.holdings && det.holdings.length) {
    h += `<h4>持仓 (${det.holdings.length}) <span class="mini">当日最后快照${det.stale_marks ? "(市值非当日)" : ""}</span></h4>`;
    // Every action carries the model's reasoning — not just HOLD. Filtering
    // to HOLD hid 91 of 255 notes (SELL/OPEN/RAISE_STOP), which read as
    // "this row has nothing to say" when it had the most to say.
    const rowNotes = {};
    for (const a of (det.actions || [])) if (a.note) rowNotes[a.c] = {a: a.a, note: a.note};
    let noted = 0;
    for (const p of det.holdings) {
      const size = p.v != null ? `<span class="muted">${fmtM(p.v)}${p.w != null ? ` (${p.w}%)` : ""}</span> ` : "";
      const rn = rowNotes[p.c];
      if (rn) noted++;
      // Glyph, not the word: the full action name is in the tooltip badge,
      // and "RAISE_STOP" inline pushed the stock code out of the row.
      const glyph = {RAISE_STOP: "⬆", OPEN: "＋", SELL: "✕"}[rn && rn.a] || "";
      const tag = glyph ? ` <span class="act-tag">${glyph}</span>` : "";
      h += `<div class="d-row${rn ? " has-note" : ""}"${rn ? ` data-note="${esc(rn.note)}" data-act="${esc(rn.a)}"` : ""}>`
         + `<span>${esc(p.n)}${tag} <span class="muted">${esc(p.c)}</span></span>`
         + `<span>${size}<span class="${pnlCls(p.p)}">${p.p == null ? "—" : sign(p.p) + p.p + "%"}</span></span></div>`;
    }
    // Absence must be visible, not mysterious: 39 of 108 days predate action
    // logging, so no row on them has reasoning to show.
    if (!noted) {
      // Four causes, four sentences. Until 2026-08-21 all of them rendered as
      // "早于决策日志上线", which is true for exactly one date in all history
      // (2026-02-13) and was a fabricated excuse everywhere else.
      const why = {
        run_failed: "该日该时段运行失败，未产生决策记录",
        predates_note_log: "该日有决策但无逐仓理由（早于决策日志上线）",
        unknown: "该日无逐仓决策记录（原因不明）",
      }[det.notes_absent_reason] || "该日无逐仓决策记录";
      h += `<div class="note mini-note">${esc(why)}</div>`;
    }
    else h += `<div class="note mini-note">悬停持仓行查看当日决策理由</div>`;
  } else {
    h += `<div class="note" style="margin-top:8px">空仓 · 100%现金`
       + (hasOpens ? " — 当日开仓于下一快照计入持仓" : "") + `</div>`;
  }
  dayEl.innerHTML = h;
  const btn = document.getElementById("unpin");
  if (btn) btn.addEventListener("click", unpin);
}
document.addEventListener("keydown", ev => { if (ev.key === "Escape" && pinned) unpin(); });

// Hover reasoning for holding rows. Delegated so it survives every re-render
// of the side panel; native title= was unstyled, ~1s delayed, and clipped the
// 200-char Chinese notes these actually are.
(function() {
  const rt = document.getElementById("rowtip");
  function place(ev) {
    const pad = 14, w = rt.offsetWidth, hgt = rt.offsetHeight;
    let x = ev.clientX - w - pad, y = ev.clientY + pad;
    if (x < 8) x = ev.clientX + pad;                       // flip near left edge
    if (y + hgt > window.innerHeight - 8) y = ev.clientY - hgt - pad;
    rt.style.left = Math.max(8, x) + "px";
    rt.style.top = Math.max(8, y) + "px";
  }
  document.addEventListener("mouseover", ev => {
    const row = ev.target.closest && ev.target.closest(".d-row.has-note");
    if (!row) return;
    // textContent, not innerHTML: dataset gives back the DECODED note, so
    // re-parsing it as HTML would undo the escaping done at render time.
    rt.textContent = "";
    const badge = document.createElement("span");
    badge.className = "rt-act";
    badge.textContent = row.dataset.act || "";
    rt.appendChild(badge);
    rt.appendChild(document.createElement("br"));
    rt.appendChild(document.createTextNode(row.dataset.note || ""));
    rt.style.display = "block";
    place(ev);
  });
  document.addEventListener("mousemove", ev => {
    if (rt.style.display === "block" && ev.target.closest && ev.target.closest(".d-row.has-note")) place(ev);
  });
  document.addEventListener("mouseout", ev => {
    if (ev.target.closest && ev.target.closest(".d-row.has-note")) rt.style.display = "none";
  });
})();

// ---------------- charts
(function() {
  const svg = document.getElementById("chart"), tip = document.getElementById("tip");
  const bars = document.getElementById("bars");
  if (!DATA.length) { svg.outerHTML = "<div class='empty'>暂无快照数据</div>"; return; }
  const IDXBASE = __IDXBASE__;
  const hasIdx = DATA.some(p => p.i != null);
  // Right gutter only widens when there is a second axis to put in it.
  const W = 960, H = 340, L = 74, R = (hasIdx && IDXBASE) ? 56 : 16, T = 18, B = 30;
  const iw = W - L - R, ih = H - T - B;
  const es = DATA.map(p => p.e).concat(hasIdx ? DATA.filter(p => p.i != null).map(p => p.i) : []);
  let lo = Math.min(...es, STARTING), hi = Math.max(...es, STARTING);
  const pad = (hi - lo) * 0.06 || 1; lo -= pad; hi += pad;
  const x = i => L + (DATA.length === 1 ? iw / 2 : i * iw / (DATA.length - 1));
  const y = v => T + (hi - v) / (hi - lo) * ih;
  const S = [];
  // Right axis = the SAME gridlines relabelled in index points. The overlay is
  // rebased (index_t / index_base x STARTING), so equity value v corresponds to
  // index level v / STARTING x IDXBASE exactly. Deliberately NOT an independent
  // scale: the whole point of the overlay is "did we beat 上证", and giving each
  // series its own range lets any pair of lines be made to look correlated or
  // divergent by choosing limits. One scale, two readings.
  const showIdxAxis = hasIdx && IDXBASE;
  const toIdx = v => v / STARTING * IDXBASE;
  for (let g = 0; g <= 4; g++) {
    const v = lo + (hi - lo) * g / 4, yy = y(v);
    S.push(`<line x1="${L}" y1="${yy}" x2="${W - R}" y2="${yy}" stroke="#eef1f5"/>`);
    S.push(`<text x="${L - 8}" y="${yy + 4}" text-anchor="end" font-size="11" fill="#8a93a2">${Math.round(v).toLocaleString()}</text>`);
    if (showIdxAxis)
      S.push(`<text x="${W - R + 8}" y="${yy + 4}" font-size="11" fill="#c08a2e">${toIdx(v).toFixed(0)}</text>`);
  }
  if (showIdxAxis) {
    S.push(`<text x="${W - R + 8}" y="${T - 6}" font-size="10" fill="#c08a2e">上证</text>`);
    S.push(`<text x="${L - 8}" y="${T - 6}" text-anchor="end" font-size="10" fill="#8a93a2">净值</text>`);
  }
  const step = Math.max(1, Math.round(DATA.length / 8));
  for (let i = 0; i < DATA.length; i += step)
    S.push(`<text x="${x(i)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="#8a93a2">${DATA[i].d.slice(5)}</text>`);
  S.push(`<line x1="${L}" y1="${y(STARTING)}" x2="${W - R}" y2="${y(STARTING)}" stroke="#9aa3b2" stroke-dasharray="5 4"/>`);
  const pts = DATA.map((p, i) => `${x(i).toFixed(1)},${y(p.e).toFixed(1)}`).join(" ");
  const tone = DATA[DATA.length - 1].e >= STARTING ? "212,58,58" : "26,156,98";
  S.push(`<polygon points="${L},${y(STARTING)} ${pts} ${x(DATA.length - 1)},${y(STARTING)}" fill="rgba(${tone},0.07)"/>`);
  if (hasIdx) {
    const ipts = DATA.map((p, i) => p.i == null ? null : `${x(i).toFixed(1)},${y(p.i).toFixed(1)}`).filter(Boolean).join(" ");
    S.push(`<polyline id="idxline" points="${ipts}" fill="none" stroke="#c08a2e" stroke-width="1.6" opacity="0.85"/>`);
  }
  const solidFrom = (DATA[0].s && DATA.length > 1) ? 1 : 0;
  if (solidFrom)
    S.push(`<line x1="${x(0)}" y1="${y(DATA[0].e)}" x2="${x(1)}" y2="${y(DATA[1].e)}" stroke="#3b6ea5" stroke-width="2" stroke-dasharray="6 5"/>`);
  const solidPts = DATA.slice(solidFrom).map((p, i) => `${x(i + solidFrom).toFixed(1)},${y(p.e).toFixed(1)}`).join(" ");
  S.push(`<polyline points="${solidPts}" fill="none" stroke="#3b6ea5" stroke-width="2"/>`);
  S.push(`<circle id="dot" r="4" fill="#3b6ea5" stroke="#fff" stroke-width="1.5" style="display:none"/>`);
  S.push(`<line id="guide" y1="${T}" y2="${T + ih}" stroke="#c3cad4" stroke-dasharray="3 3" style="display:none"/>`);
  svg.innerHTML = S.join("");

  // daily pnl bars (shared x)
  if (bars) {
    const BH = 96, BT = 6, BB = 4, bih = BH - BT - BB;
    const ps = DATA.map(p => p.p).filter(v => typeof v === "number");
    const mx = Math.max(1, ...ps.map(Math.abs));
    const by = v => BT + (mx - v) / (2 * mx) * bih;
    const bw = Math.max(1.5, Math.min(7, iw / DATA.length * 0.62));
    const BS = [`<line x1="${L}" y1="${by(0)}" x2="${W - R}" y2="${by(0)}" stroke="#e4e8ee"/>`,
                `<text x="${L - 8}" y="${by(mx) + 8}" text-anchor="end" font-size="10" fill="#8a93a2">+${fmtM(mx)}</text>`,
                `<text x="${L - 8}" y="${by(-mx)}" text-anchor="end" font-size="10" fill="#8a93a2">-${fmtM(mx)}</text>`];
    DATA.forEach((p, i) => {
      if (typeof p.p !== "number") return;
      const yy = by(Math.max(p.p, 0)), hh = Math.abs(by(p.p) - by(0)) || 0.5;
      BS.push(`<rect x="${(x(i) - bw / 2).toFixed(1)}" y="${yy.toFixed(1)}" width="${bw.toFixed(1)}" height="${hh.toFixed(1)}" fill="${p.p >= 0 ? "#d43a3a" : "#1a9c62"}" opacity="0.8"/>`);
    });
    bars.innerHTML = BS.join("");
  }

  // legend toggle
  const lg = document.getElementById("lg-idx");
  if (lg && hasIdx) lg.addEventListener("click", () => {
    const el = svg.querySelector("#idxline");
    const off = el.style.display === "none";
    el.style.display = off ? "" : "none";
    lg.classList.toggle("off", !off);
  });

  // hover + pin
  const dot = svg.querySelector("#dot"), guide = svg.querySelector("#guide");
  function idxFromEvent(ev) {
    const r = svg.getBoundingClientRect();
    const mx = (ev.clientX - r.left) * W / r.width;
    let i = Math.round((mx - L) / (iw / Math.max(DATA.length - 1, 1)));
    return Math.max(0, Math.min(DATA.length - 1, i));
  }
  svg.addEventListener("mousemove", ev => {
    const i = idxFromEvent(ev), p = DATA[i];
    dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(p.e)); dot.style.display = "";
    guide.setAttribute("x1", x(i)); guide.setAttribute("x2", x(i)); guide.style.display = "";
    tip.style.display = "block";
    tip.style.left = (ev.clientX + 14) + "px"; tip.style.top = (ev.clientY - 12) + "px";
    const idxTxt = p.i != null ? ` · 上证(等额) ${fmtM(p.i)}` : "";
    tip.textContent = p.s ? `${p.d} · ${fmtM(p.e)} · 组合起始(初始资金)`
      : `${p.d} · ${fmtM(p.e)}${p.r != null ? ` · ${sign(p.r)}${p.r}%` : ""}${idxTxt}`;
    if (!pinned) renderDay(p.d);
  });
  svg.addEventListener("click", ev => {
    const d = DATA[idxFromEvent(ev)].d;
    pinned = (pinned === d) ? null : d;
    renderDay(pinned || d);
  });
  svg.addEventListener("mouseleave", () => {
    dot.style.display = "none"; guide.style.display = "none"; tip.style.display = "none";
    if (!pinned) renderDay(DATA[DATA.length - 1].d);
  });
  latestDay = DATA[DATA.length - 1].d;
  renderDay(latestDay);
})();
"""


def render_html(series, active, trades, stats, details=None, index_rebased=None,
                events=None, badges=None, generated_at=None, run_status=None,
                idx_base=None) -> str:
    pf = active.get("portfolio", {})
    positions = active.get("activePositions", [])
    details = details or {}
    index_rebased = index_rebased or {}
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

    chart_data = []
    prev_real = None
    for p in series:
        if not isinstance(p.get("equity"), (int, float)):
            continue
        pt = {"d": p["date"], "e": round(p["equity"], 0), "r": p.get("ret_pct"),
              "n": p.get("positions")}
        if p.get("synthetic"):
            pt["s"] = 1
        elif prev_real is not None:
            pt["p"] = round(p["equity"] - prev_real, 2)
        if p["date"] in index_rebased:
            pt["i"] = index_rebased[p["date"]]
        if not p.get("synthetic"):
            prev_real = p["equity"]
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

    pos_rows = "\n".join(
        "<tr>"
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
        "<tr>"
        f"<td>{html.escape(t.get('code', ''))}</td>"
        f"<td>{html.escape(t.get('name', ''))}</td>"
        f"<td>{html.escape(t.get('entryDate', ''))}{_slot_tag(t.get('entrySlot'))}</td>"
        f"<td>{html.escape(t.get('exitDate', ''))}{_slot_tag(t.get('exitSlot'))}</td>"
        f"<td class='num'>{t.get('holdingDays', '—')}</td>"
        f"<td class='num {_pnl_cls(t.get('returnPct'))}'>{_pct(t.get('returnPct'))}</td>"
        f"<td>{html.escape(str(t.get('exitReason', '') or ''))}</td>"
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
                "<code>data/index_cache/sh000001.json</code>。" if index_rebased else
                "（上证指数数据不可用——离线且无缓存）")

    js = (CHART_JS
          .replace("__DATA__", json.dumps(chart_data, ensure_ascii=False))
          .replace("__DETAILS__", json.dumps(details, ensure_ascii=False))
          .replace("__STARTING__", json.dumps(starting))
          .replace("__IDXBASE__", json.dumps(idx_base)))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>组合总览 · 模拟盘</title>
<style>
  :root {{ --up:#d43a3a; --down:#1a9c62; --fg:#1c2330; --muted:#6b7482;
           --line:#e4e8ee; --bg:#f6f7f9; --card:#fff; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:14px/1.55 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
          color:var(--fg); background:var(--bg); }}
  .wrap {{ max-width:1200px; margin:0 auto; padding:28px 20px 48px; }}
  h1 {{ font-size:21px; margin:0 0 2px; }}
  .sub {{ color:var(--muted); font-size:12.5px; margin-bottom:10px; }}
  h2 {{ font-size:15.5px; margin:30px 0 10px; }}
  .muted-h {{ font-weight:400; color:var(--muted); font-size:12px; }}
  .hbadges {{ margin:0 0 16px; }}
  .hbadge {{ display:inline-block; background:#eef1f6; border:1px solid var(--line);
             border-radius:20px; padding:3px 12px; font-size:12.5px; margin-right:8px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(122px,1fr)); gap:10px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 13px; }}
  .card .label {{ font-size:12px; color:var(--muted); }}
  .card .value {{ font-size:17px; font-weight:600; margin-top:2px; font-variant-numeric:tabular-nums; }}
  .up {{ color:var(--up); }} .down {{ color:var(--down); }} .flat {{ color:var(--fg); }}
  .main {{ display:grid; grid-template-columns:minmax(0,1fr) 320px; gap:14px; align-items:start; }}
  @media (max-width: 900px) {{ .main {{ grid-template-columns:1fr; }} }}
  .panel {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }}
  #chart, #bars {{ width:100%; height:auto; display:block; }}
  .legend {{ font-size:12px; color:var(--muted); margin:4px 2px 0; user-select:none; }}
  .legend .sw {{ display:inline-block; width:16px; height:3px; vertical-align:middle; margin-right:4px; border-radius:2px; }}
  #lg-idx {{ cursor:pointer; }} #lg-idx.off {{ opacity:0.35; }}
  #tip {{ position:fixed; display:none; pointer-events:none; background:#1c2330; color:#fff;
          padding:6px 9px; border-radius:6px; font-size:12px; white-space:nowrap; z-index:9; }}
  .side {{ position:sticky; top:14px; max-height:calc(100vh - 28px); overflow-y:auto; }}
  .side h4 {{ margin:13px 0 5px; font-size:12.5px; color:var(--muted); font-weight:600;
              border-top:1px solid var(--line); padding-top:10px; }}
  .d-date {{ font-weight:600; font-size:15px; }}
  .d-equity {{ font-size:22px; font-weight:700; font-variant-numeric:tabular-nums; margin-top:2px; }}
  .d-sub {{ font-size:12.5px; color:var(--muted); }}
  .d-row {{ display:flex; justify-content:space-between; align-items:baseline; gap:8px;
            padding:3px 0; font-size:13px; }}
  .d-row > span:first-child {{ min-width:0; overflow:hidden; text-overflow:ellipsis;
                               white-space:nowrap; }}
  .d-row > span:last-child {{ flex:none; white-space:nowrap; }}
  .d-act {{ margin:7px 0; font-size:13px; }}
  .d-size {{ font-size:12px; color:var(--fg); margin:1px 0 0 2px; font-variant-numeric:tabular-nums; }}
  .d-note {{ color:var(--muted); font-size:12px; margin:2px 0 0 2px; }}
  .d-row.has-note {{ cursor:help; border-bottom:1px dotted var(--line); }}
  .d-row.has-note:hover {{ background:#f6f8fa; }}
  .act-tag {{ font-size:9.5px; font-weight:700; letter-spacing:.03em; color:#8a5a00;
              background:#fdf1d6; border-radius:3px; padding:0 3px; vertical-align:1px; }}
  .mini-note {{ font-size:11px; color:var(--muted); margin-top:6px; }}
  #rowtip {{ position:fixed; display:none; pointer-events:none; z-index:20;
             background:#1c2330; color:#fff; padding:8px 10px; border-radius:7px;
             font-size:12px; line-height:1.55; max-width:340px; white-space:normal;
             box-shadow:0 6px 22px rgba(0,0,0,.28); }}
  #rowtip .rt-act {{ display:inline-block; font-size:10px; font-weight:700;
                     background:rgba(255,255,255,.16); border-radius:3px;
                     padding:0 4px; margin-bottom:4px; }}
  .mini {{ font-weight:400; font-size:10.5px; color:var(--muted); }}
  .slot {{ font-size:10.5px; color:var(--muted); background:#f0f2f5;
           border-radius:3px; padding:0 4px; margin-left:3px; }}
  #unpin {{ border:1px solid var(--line); background:#fff; border-radius:6px; padding:1px 8px;
            font-size:11.5px; cursor:pointer; color:var(--muted); }}
  #unpin:hover {{ background:#f2f4f7; }}
  .badge {{ display:inline-block; border-radius:4px; padding:0 6px; font-size:11.5px; color:#fff; }}
  .b-open {{ background:var(--up); }} .b-sell {{ background:#4a5568; }}
  .muted {{ color:var(--muted); }}
  .chip {{ display:inline-block; background:#eef1f6; border-radius:4px; padding:0 6px;
           font-size:11px; color:var(--muted); }}
  .chip.warn {{ background:#fdf1e3; color:#9a6b1f; }}
  .events {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:10px; }}
  .ev {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:11px 13px; }}
  .ev-when {{ font-size:12.5px; }} .tminus {{ color:var(--muted); font-size:11.5px; }}
  .ev-name {{ font-weight:600; margin:3px 0 2px; font-size:13.5px; }}
  .ev-note {{ font-size:12px; color:var(--muted); }}
  .ev-src a {{ color:#3b6ea5; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card);
           border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
  th,td {{ padding:7px 10px; text-align:left; border-bottom:1px solid var(--line); font-size:13px; }}
  th {{ background:#fafbfc; color:var(--muted); font-weight:500; }}
  tr:last-child td {{ border-bottom:none; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  td.empty {{ text-align:center; color:var(--muted); padding:18px; }}
  .note {{ color:var(--muted); font-size:12px; margin-top:6px; }}
  footer {{ margin-top:34px; color:var(--muted); font-size:12px; border-top:1px solid var(--line); padding-top:12px; }}
  code {{ background:#eef0f3; padding:1px 5px; border-radius:4px; font-size:11.5px; }}
  .runfail {{ margin:10px 0 2px; padding:10px 13px; border-radius:8px; font-size:13px;
              background:#fdf3f3; border:1px solid #f0cfcf; color:#8a2a2a; }}
  .runfail ul {{ margin:5px 0 0; padding-left:19px; }}
  .runfail li {{ font-size:12px; line-height:1.55; }}
  .rf-tail {{ margin-top:5px; font-size:12px; color:#a2564f; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>组合总览 <span style="font-weight:400;color:var(--muted);font-size:14px">模拟盘 · A股动量策略</span></h1>
  <div class="sub">生成于 {html.escape(generated_at)} · 红涨绿跌</div>
  {run_banner}
  <div class="hbadges">{badges_html}</div>

  <div class="cards">{cards_html}</div>

  <h2>每日总资产 <span class="muted-h">悬停查看当日详情 · 点击固定</span></h2>
  <div class="main">
    <div>
      <div class="panel">
        <svg id="chart" viewBox="0 0 960 340" preserveAspectRatio="xMidYMid meet"></svg>
        <div class="legend">
          <span><span class="sw" style="background:#3b6ea5"></span>组合总资产</span>&nbsp;&nbsp;
          <span id="lg-idx"><span class="sw" style="background:#c08a2e"></span>上证指数（等额起点，点击隐藏）</span>&nbsp;&nbsp;
          <span><span class="sw" style="background:#9aa3b2;height:1px;border-top:2px dashed #9aa3b2"></span>初始资金 {_fmt_money(starting)}</span>
        </div>
        <svg id="bars" viewBox="0 0 960 96" preserveAspectRatio="xMidYMid meet" style="margin-top:8px"></svg>
        <div class="legend">每日盈亏（较上一快照）</div>
        <div class="note">每个交易日取当日最后一次流水线快照的 totalEquity；曲线首点为组合起始日（portfolio_config.created，等于初始资金），起始日至首个每日快照间无逐日数据（斜虚线段示意）。{idx_note}</div>
      </div>
    </div>
    <div class="panel side"><div id="day"></div></div>
  </div>
  <div id="tip"></div>
  <div id="rowtip"></div>

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
    details = collect_day_details(series, trades, build_open_lookup(active, trades))
    starting = (series[0].get("starting") if series else None) or 1000000
    index_closes = load_index_closes()
    dates = [p["date"] for p in series]
    index_rebased = rebase_index(index_closes, dates, float(starting))
    idx_base = index_base(index_closes, dates[0]) if dates else None
    events = load_events()
    badges = load_badges(series)
    site_dir.mkdir(parents=True, exist_ok=True)
    out = site_dir / "index.html"
    out.write_text(render_html(series, active, trades, stats, details=details,
                               index_rebased=index_rebased, events=events,
                               badges=badges, run_status=load_latest_run_status(),
                               idx_base=idx_base),
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
