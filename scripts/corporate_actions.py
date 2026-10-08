#!/usr/bin/env python3
"""Corporate actions in the simulated book — cash dividends and 送转.

Why this exists (2026-10-08): 普洛药业 000739 went ex-dividend (10派1.39). The
book marked the ex-date price drop (27.74 → 27.13) and credited no cash, so the
portfolio read a loss that a real holder never had. A 送转 (bonus shares) was
worse: a 10转4 would have read as −28%. See docs/corporate_actions/.

Owner decisions (DECISIONS.md):
- Scope: CURRENTLY OPEN positions only, events with entryDate < exDate <= run
  date. A missed event is back-credited by the same idempotent apply. Closed
  trades in tracking/closed/ are never restated.
- Tax on cash dividends, A-share holding-period rule judged at the ex-date:
  held ≤ 1 calendar month 20%, ≤ 1 year 10%, longer 0%. Net cash is credited.
- 送转: shares × (1 + ratio/10) floored, entryPrice ÷ the same factor (cost
  basis kept, allocatedCapital unchanged). Stops/targets are NOT adjusted —
  a loud warning says the stop is now likely to trip.

Source: eastmoney datacenter RPT_SHAREBONUS_DET (the host pricedb already uses
for ex-div dates). A fetch failure is a LOUD degradation, never a hard fail:
the book is untouched and the next run retries (apply is idempotent by exDate).

Path globals are read from position_manager AT CALL TIME (pm.TRACKING_DIR),
never `from position_manager import TRACKING_DIR`, so a test that rebinds the
position_manager globals also rebinds this module.
"""
from __future__ import annotations

import math
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import position_manager as pm

EXDIV_REPORT = "RPT_SHAREBONUS_DET"
IMPLEMENTED = "实施分配"          # the only ASSIGN_PROGRESS that is a real event
FETCH_TIMEOUT_SEC = 20
# eastmoney datacenter answers an empty filter with success=false + this code;
# that is "no events", not "could not ask".
_EMPTY_RESULT_CODE = 9201


# ── tax ──

def _add_months(d: _date, months: int) -> _date:
    """d + N calendar months, clamped to the target month's last day."""
    y, m = divmod(d.month - 1 + months, 12)
    y, m = d.year + y, m + 1
    nxt_y, nxt_m = (y + 1, 1) if m == 12 else (y, m + 1)
    last = (_date(nxt_y, nxt_m, 1) - _date(y, m, 1)).days
    return _date(y, m, min(d.day, last))


def tax_rate(entry_date: str, ex_date: str) -> float:
    """Dividend tax rate by holding period, judged at the ex-date.

    ex ≤ entry + 1 month → 20%; ex ≤ entry + 1 year → 10%; else 0%.
    """
    entry = _date.fromisoformat(entry_date)
    ex = _date.fromisoformat(ex_date)
    if ex <= _add_months(entry, 1):
        return 0.20
    if ex <= _add_months(entry, 12):
        return 0.10
    return 0.00


# ── source ──

def _num(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def parse_events(rows: list[dict]) -> list[dict]:
    """eastmoney RPT_SHAREBONUS_DET rows → events, oldest first.

    BONUS_IT_RATIO is the combined 送+转 per 10 shares (2007 row of 000739:
    送3 转2 → 5), so it is used rather than BONUS_RATIO / IT_RATIO.
    """
    events = []
    for r in rows or []:
        if not isinstance(r, dict) or r.get("ASSIGN_PROGRESS") != IMPLEMENTED:
            continue
        ex = str(r.get("EX_DIVIDEND_DATE") or "")[:10]
        if len(ex) != 10:
            continue
        cash = _num(r.get("PRETAX_BONUS_RMB"))
        bonus = _num(r.get("BONUS_IT_RATIO"))
        if cash <= 0 and bonus <= 0:
            continue
        events.append({"exDate": ex, "cashPer10": cash, "bonusPer10": bonus,
                       "plan": r.get("IMPL_PLAN_PROFILE") or ""})
    return sorted(events, key=lambda e: e["exDate"])


def fetch_events(code: str) -> list[dict] | None:
    """Implemented dividend/送转 events for one code; None when we could not ask.

    None (fetch failed) and [] (asked, nothing there) are different answers and
    the caller treats them differently — the first is a loud degradation.
    """
    import requests
    from pricedb.providers import DATACENTER_EXDIV_URL, _no_proxy_env

    code6 = str(code).split(".")[0]
    try:
        with _no_proxy_env():
            resp = requests.get(
                DATACENTER_EXDIV_URL,
                params={
                    "reportName": EXDIV_REPORT,
                    "columns": "ALL",
                    "filter": f'(SECURITY_CODE="{code6}")',
                    "pageSize": "100",
                    "pageNumber": "1",
                    "sortColumns": "EX_DIVIDEND_DATE",
                    "sortTypes": "-1",
                },
                headers={"User-Agent": "Mozilla/5.0 pricedb"},
                timeout=FETCH_TIMEOUT_SEC,
            )
        payload = resp.json()
    except Exception as e:
        print(f"  [corporate-actions] fetch {code6} failed: {e}", file=sys.stderr)
        return None
    if not isinstance(payload, dict):
        return None
    if not payload.get("success"):
        if payload.get("code") == _EMPTY_RESULT_CODE:
            return []
        print(f"  [corporate-actions] fetch {code6} unsuccessful: "
              f"{payload.get('message')}", file=sys.stderr)
        return None
    rows = (payload.get("result") or {}).get("data") or []
    return parse_events(rows)


# ── apply ──

def _apply_event(pos: dict, ev: dict, applied_at: str) -> tuple[dict, list[str]]:
    """Mutate `pos` for one event. Returns (corporateActions record, warnings)."""
    warnings = []
    ex = ev["exDate"]
    shares_before = int(pos["shares"])
    entry_before = float(pos["entryPrice"])

    # Cash is paid on the record-date holding, i.e. BEFORE any bonus shares.
    gross = round(shares_before * ev["cashPer10"] / 10, 2)
    rate = tax_rate(pos["entryDate"], ex) if gross > 0 else 0.0
    tax = round(gross * rate, 2)
    net = round(gross - tax, 2)

    shares_after, entry_after = shares_before, entry_before
    if ev["bonusPer10"] > 0:
        factor = 1 + ev["bonusPer10"] / 10
        # epsilon: 1700 × 1.4 is 2379.9999… in float
        shares_after = int(math.floor(shares_before * factor + 1e-6))
        # unrounded (6 dp) so shares × entryPrice keeps the cost basis
        entry_after = round(entry_before / factor, 6)
        pos["shares"] = shares_after
        pos["entryPrice"] = entry_after
        stop = pos.get("currentStop", pos.get("stopLoss"))
        warnings.append(
            f"⚠ 送转 {pos['code']} {pos.get('name', '')} ex {ex}: "
            f"10转{ev['bonusPer10']:g} → shares {shares_before}→{shares_after}, "
            f"entryPrice {entry_before}→{entry_after}. Stop {stop} / target "
            f"{pos.get('targetPrice')} were NOT adjusted (owner decision) — the "
            f"ex-rights price is ~{1 / factor:.0%} of before, so the stop will "
            f"very likely trip this session.")

    rec = {
        "exDate": ex,
        "cashPer10": ev["cashPer10"],
        "bonusPer10": ev["bonusPer10"],
        "plan": ev.get("plan", ""),
        "sharesBefore": shares_before,
        "sharesAfter": shares_after,
        "entryPriceBefore": entry_before,
        "entryPriceAfter": entry_after,
        "grossCash": gross,
        "taxRate": rate,
        "tax": tax,
        "netCash": net,
        "appliedAt": applied_at,
    }
    pos.setdefault("corporateActions", []).append(rec)

    history = pos.setdefault("history", [])
    if gross > 0:
        history.append({
            "date": ex, "action": "DIVIDEND", "shares": shares_before,
            "cashPer10": ev["cashPer10"], "grossCash": gross,
            "taxRate": rate, "tax": tax, "netCash": net,
            "note": f"除息 10派{ev['cashPer10']:g}: 税前{gross} 税{tax} "
                    f"({rate:.0%}) 到账{net}",
        })
    if shares_after != shares_before:
        history.append({
            "date": ex, "action": "BONUS_SHARES",
            "shares": shares_after,                 # 2a-i replay field
            "sharesBefore": shares_before, "bonusPer10": ev["bonusPer10"],
            "entryPriceBefore": entry_before, "entryPriceAfter": entry_after,
            "note": f"送转 10转{ev['bonusPer10']:g}: {shares_before}→{shares_after}股, "
                    f"成本价 {entry_before}→{entry_after}; 止损/目标未调整",
        })
    return rec, warnings


def apply_due(date: str, fetcher=None) -> dict:
    """Apply every due, not-yet-applied event to every OPEN position.

    Due = entryDate < exDate <= date. Idempotent by exDate per position, so it
    is safe to call every slot; a missed event is back-credited by the next
    call. Never raises for a source problem: a failed fetch leaves that
    position untouched and is reported in `fetch_failed` + `warnings`.

    Returns {"date", "status": "ok"|"degraded", "checked", "applied":
    [record + code/name], "fetch_failed": [codes], "warnings": [str]}.
    """
    fetcher = fetcher or fetch_events
    result = {"date": date, "status": "ok", "checked": 0, "applied": [],
              "fetch_failed": [], "warnings": []}
    applied_at = pm._now_iso()

    for pos in pm.load_active_positions():
        code = str(pos.get("code", "")).split(".")[0]
        entry_date = pos.get("entryDate")
        if not code or not entry_date or not pos.get("shares") or not pos.get("entryPrice"):
            result["warnings"].append(
                f"corporate actions: {code or '?'} skipped — missing "
                f"code/entryDate/shares/entryPrice")
            continue
        result["checked"] += 1
        try:
            events = fetcher(code)
        except Exception as e:
            print(f"  [corporate-actions] fetcher raised for {code}: {e}", file=sys.stderr)
            events = None
        if events is None:
            result["fetch_failed"].append(code)
            result["warnings"].append(
                f"WARN corporate actions: could not fetch ex-div events for "
                f"{code} {pos.get('name', '')} — dividends/送转 NOT checked this "
                f"run; the next run retries")
            continue

        done = {a.get("exDate") for a in (pos.get("corporateActions") or [])}
        due = [e for e in events
               if entry_date < e["exDate"] <= date and e["exDate"] not in done]
        if not due:
            continue
        for ev in sorted(due, key=lambda e: e["exDate"]):
            rec, warns = _apply_event(pos, ev, applied_at)
            result["applied"].append({"code": code, "name": pos.get("name", ""), **rec})
            result["warnings"].extend(warns)
        pos["updatedAt"] = applied_at
        pm._write_json(pm.TRACKING_DIR / f"{code}.json", pos)

    if result["fetch_failed"]:
        result["status"] = "degraded"
    if result["applied"]:
        pm.regenerate_positions_json()
    for w in result["warnings"]:
        print(f"  {w}", file=sys.stderr)
    return result


if __name__ == "__main__":
    # Read-only preview: what WOULD be applied. Never writes the book.
    import json
    run_date = sys.argv[1] if len(sys.argv) > 1 else _date.today().isoformat()
    out = []
    for p in pm.load_active_positions():
        code = str(p.get("code", "")).split(".")[0]
        evs = fetch_events(code)
        done = {a.get("exDate") for a in (p.get("corporateActions") or [])}
        due = None if evs is None else [
            e for e in evs if p["entryDate"] < e["exDate"] <= run_date
            and e["exDate"] not in done]
        out.append({"code": code, "name": p.get("name"), "entryDate": p.get("entryDate"),
                    "due": due})
    print(json.dumps(out, ensure_ascii=False, indent=2))
