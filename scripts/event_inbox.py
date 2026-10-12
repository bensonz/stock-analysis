#!/usr/bin/env python3
"""
event_inbox.py — automated candidates for the curated event calendar.

`tracking/events.json` is hand-curated, and by 2026-10 it had not been edited
for two months: it missed the US midterm election (2026-11-03). The owner does
not want the calendar limited to news they personally see, but also does not
want a noisy feed written straight into the LLM prompt. So:

    华尔街见闻 calendar (akshare.macro_info_ws, importance >= 4, 45 days)
        └─ refresh ─► tracking/event_inbox.md      (owner ticks a checklist)
                         └─ promote ─► tracking/events.json   ([x] keep)
                                   └─► tracking/event_inbox_ledger.json
                                       ([x] keep / [-] skip — never re-proposed)

event_calendar.py stays the only READER of events.json; this module only
proposes and appends. Every rule with a judgment call in it (Beijing time →
date/tz, the fuzzy dedupe, why "00:00" is a placeholder) is recorded with its
known limits in docs/EVENT_INBOX/DECISIONS.md.

CLI:
    python3 scripts/event_inbox.py refresh   # fetch + append new candidates
    python3 scripts/event_inbox.py promote   # [x] → events.json, [x]/[-] → ledger
    python3 scripts/event_inbox.py status    # counts + undecided items due soon
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import date as _date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import akshare as ak  # noqa: E402

import event_calendar  # noqa: E402
from pricedb.providers import _TimeoutError, _run_with_timeout  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INBOX_FILE = PROJECT_ROOT / "tracking" / "event_inbox.md"
LEDGER_FILE = PROJECT_ROOT / "tracking" / "event_inbox_ledger.json"
EVENTS_FILE = event_calendar.EVENTS_FILE

HORIZON_DAYS = 45
MIN_IMPORTANCE = 4   # owner 2026-10-12: >=3 gave 91 items/45d, mostly noise
#: akshare's macro_info_ws calls requests.get with no timeout at all
CALL_TIMEOUT_SEC = 20
#: whole-fetch budget; dates not reached count as fetch errors
FETCH_DEADLINE_SEC = 60
#: the doctor reminds about undecided items this close to their impact date
REMIND_WITHIN_DAYS = 7

IMPACTS = ("high", "medium", "low")
DIRECTIONS = ("risk", "two_sided", "supportive")  # event_calendar's vocabulary
TZS = ("US", "CN")
SOURCE_NAME = "华尔街见闻财经日历"


# ── the candidate ────────────────────────────────────────────────────────────

@dataclass
class Item:
    id: str
    name: str
    region: str
    date: str           # event_calendar `date` (US calendar date when tz=US)
    tz: str
    impact: str
    direction: str
    kind: str
    importance: int
    beijing_time: str   # as listed by wallstreetcn, "YYYY-MM-DD HH:MM"
    link: str = ""
    note: str = ""
    mark: str = " "     # " " undecided | "x" keep | "-" skip

    def impact_date(self) -> _date | None:
        try:
            return event_calendar.a_share_impact_date(
                _date.fromisoformat(self.date), self.tz)
        except (ValueError, TypeError):
            return None

    def problems(self) -> list[str]:
        """Why this item cannot be promoted as written (empty = fine)."""
        out = []
        if self.impact not in IMPACTS:
            out.append(f"impact '{self.impact}' not in {'/'.join(IMPACTS)}")
        if self.direction not in DIRECTIONS:
            out.append(f"direction '{self.direction}' not in {'/'.join(DIRECTIONS)}")
        if self.tz not in TZS:
            out.append(f"tz '{self.tz}' not in {'/'.join(TZS)}")
        if self.impact_date() is None:
            out.append(f"date '{self.date}' is not YYYY-MM-DD")
        if not self.name.strip():
            out.append("name is empty")
        return out

    def to_event(self) -> dict:
        """An events.json entry with the same fields hand-written ones have."""
        return {
            "date": self.date,
            "tz": self.tz,
            "name": self.name,
            "kind": self.kind,
            "certainty": "scheduled",
            "impact": self.impact,
            "direction": self.direction,
            "notes": self.note or f"北京时间 {self.beijing_time}（{SOURCE_NAME}）",
            "source": self.link or f"{SOURCE_NAME} imp={self.importance}",
            "inbox_id": self.id,
        }


def map_date_tz(region: str, beijing_date: _date, hms: str) -> tuple[str, _date]:
    """Beijing listing time → (tz, event_calendar date). See DECISIONS D3.

    US events use event_calendar's US rule (impact on the next weekday after
    the US date), so `date` must be the US calendar date: a 00:01–09:29
    Beijing time is the previous US evening (FOMC 02:00). Exactly 00:00:00 is
    wallstreetcn's date-only placeholder (the midterm), so the listed date
    stands. Every other region is taken as a same-day CN-session event.
    """
    if region == "美国":
        if "00:00:00" < hms < "09:30:00":
            return "US", beijing_date - timedelta(days=1)
        return "US", beijing_date
    return "CN", beijing_date


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v))


def candidate_from_row(row: dict) -> Item:
    ts = str(row["时间"]).strip()
    listed = _date.fromisoformat(ts[:10])
    hms = ts[11:19] or "00:00:00"
    region = str(row.get("地区") or "").strip()
    title = str(row.get("事件") or "").strip()
    link = str(row.get("链接") or "").strip()
    importance = int(row.get("重要性") or 0)
    m = re.search(r"/calendar/([^/?#]+)", link)
    key = m.group(1) if m else hashlib.sha1(
        f"{region}|{title}".encode("utf-8")).hexdigest()[:8]
    tz, stored = map_date_tz(region, listed, hms)
    has_data = _is_number(row.get("前值")) or _is_number(row.get("预期"))
    return Item(
        id=f"wscn-{listed:%Y%m%d}-{key}",
        name=title if region and region in title else f"{region}{title}",
        region=region or "?",
        date=stored.isoformat(),
        tz=tz,
        impact="high" if importance >= 4 else "medium",
        direction="two_sided",
        kind="macro_release" if has_data else "other",
        importance=importance,
        beijing_time=ts[:16],
        link=link,
    )


# ── fetching ─────────────────────────────────────────────────────────────────

def _akshare_fetch(day: str):
    return ak.macro_info_ws(date=day)


def _is_empty_day(e: BaseException) -> bool:
    """akshare indexes `public_date` on an empty item list → KeyError (D2)."""
    return isinstance(e, KeyError) and "public_date" in str(e)


def fetch_candidates(today: _date, days: int = HORIZON_DAYS, fetch_fn=None,
                     min_importance: int = MIN_IMPORTANCE,
                     call_timeout: float = CALL_TIMEOUT_SEC,
                     deadline_sec: float = FETCH_DEADLINE_SEC) -> tuple[list, dict]:
    """One call per date, today .. today+days. A failing date never stops the rest."""
    fetch_fn = fetch_fn or _akshare_fetch
    stats = {"dates": 0, "rows": 0, "candidates": 0,
             "empty_days": [], "errors": []}
    seen, out = set(), []
    started = time.monotonic()
    for i in range(days + 1):
        day = (today + timedelta(days=i)).strftime("%Y%m%d")
        stats["dates"] += 1
        if time.monotonic() - started > deadline_sec:
            stats["errors"].append({"date": day, "error": "fetch deadline exceeded"})
            continue
        try:
            df = _run_with_timeout(f"wscn:{day}",
                                   lambda d=day: fetch_fn(d), timeout=call_timeout)
        except _TimeoutError as e:
            stats["errors"].append({"date": day, "error": str(e)})
            continue
        except Exception as e:  # noqa: BLE001 — one bad date never fails the fetch
            if _is_empty_day(e):
                stats["empty_days"].append(day)
            else:
                stats["errors"].append({"date": day,
                                        "error": f"{type(e).__name__}: {e}"})
            continue
        rows = df.to_dict("records") if df is not None else []
        stats["rows"] += len(rows)
        for row in rows:
            try:
                if int(row.get("重要性") or 0) < min_importance:
                    continue
                it = candidate_from_row(row)
            except Exception as e:  # noqa: BLE001 — a malformed row is one error
                stats["errors"].append({"date": day,
                                        "error": f"bad row: {type(e).__name__}: {e}"})
                continue
            if it.id not in seen:
                seen.add(it.id)
                out.append(it)
    stats["candidates"] = len(out)
    return out, stats


# ── dedupe against events.json ───────────────────────────────────────────────

_NAME_NOISE = re.compile(r"\d{4}年|\d+\s*月|\d+\s*日|[\s\W_]+", re.UNICODE)
FUZZY_MIN_COMMON = 3
FUZZY_DAY_TOLERANCE = 1


def _norm_name(name: str, region: str = "") -> str:
    s = name.replace(region, "") if region else name
    return _NAME_NOISE.sub("", s).lower()


def _longest_common(a: str, b: str) -> int:
    best = 0
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0] * (len(b) + 1)
        for j, cb in enumerate(b, 1):
            if ca == cb:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


def match_event(item: Item, events: list) -> str | None:
    """"id" / "fuzzy" if events.json already carries this item, else None (D5).

    Fuzzy = same tz, A-share impact dates within ±1 day, and the normalized
    names share a run of >= FUZZY_MIN_COMMON characters.
    """
    if any(e.get("inbox_id") == item.id for e in events):
        return "id"
    mine = item.impact_date()
    if mine is None:
        return None
    a = _norm_name(item.name, item.region)
    for e in events:
        # same tz too: without it 中国9月CPI matched a hand-written 美国9月CPI
        # (the region word is stripped, leaving "CPI" on both sides)
        if not e.get("date") or e.get("tz", "CN") != item.tz:
            continue
        try:
            theirs = event_calendar.a_share_impact_date(
                _date.fromisoformat(e["date"]), e.get("tz", "CN"))
        except (ValueError, TypeError):
            continue
        if abs((theirs - mine).days) > FUZZY_DAY_TOLERANCE:
            continue
        if _longest_common(a, _norm_name(str(e.get("name", "")), item.region)) \
                >= FUZZY_MIN_COMMON:
            return "fuzzy"
    return None


# ── the markdown file ────────────────────────────────────────────────────────

_HEADER = """\
# 事件收件箱 (event inbox)

> 由 `python3 scripts/event_inbox.py refresh` 生成，每次流水线运行自动刷新
> （来源: 华尔街见闻财经日历，重要性>=4，未来45天）。你只需要打勾：
>
> - `[x]` 保留 → 下次运行（或 `python3 scripts/event_inbox.py promote`）写入 `tracking/events.json`
> - `[-]` 跳过 → 记入台账，不再出现
> - `[ ]` 待定 → 留在这里
>
> 可直接改: 标题里 `—` 后的名称、`impact` (high/medium/low)、`direction` (risk/two_sided/supportive)、
> `date`、`tz` (US=影响其后第一个A股交易日 / CN=当日)、`kind`、`note`。不要改 `src:` 和 `id:` 两行。
> 标题日期 = A股影响日，由 date+tz 推算，重写时刷新。规则与局限: docs/EVENT_INBOX/DECISIONS.md
"""

_KV = re.compile(r"(\w+):\s*(\S+)")


def render_inbox(items: list, today: _date) -> str:
    items = sorted(items, key=lambda i: (str(i.impact_date() or i.date), i.id))
    pending = sum(1 for i in items if i.mark == " ")
    L = [_HEADER, f"_更新: {today.isoformat()} · 共 {len(items)} 条 · 待定 {pending} 条_", ""]
    if not items:
        L.append("（暂无候选）")
    for it in items:
        d = it.impact_date()
        when = f"{d.isoformat()} (T-{(d - today).days})" if d else f"{it.date} (T-?)"
        L += [f"## {when} {it.region} — {it.name}",
              f"- [{it.mark}] keep   impact: {it.impact}   direction: {it.direction}",
              f"  date: {it.date}   tz: {it.tz}   kind: {it.kind}",
              f"  note: {it.note}".rstrip(),
              f"  src: wallstreetcn imp={it.importance} 北京 {it.beijing_time} | {it.link}".rstrip(),
              f"  id: {it.id}",
              ""]
    return "\n".join(L).rstrip() + "\n"


def parse_inbox(text: str) -> tuple[list, list]:
    """Owner-edited markdown → (items, warnings). Tolerant of hand edits."""
    blocks, cur = [], None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = [line]
            blocks.append(cur)
        elif cur is not None:
            cur.append(line)
    items, warnings = [], []
    for b in blocks:
        heading = b[0][3:].strip()
        f = {"region": "?", "name": heading.split("—", 1)[-1].strip(),
             "mark": " ", "note": "", "link": "", "importance": 0,
             "beijing_time": "", "date": "", "tz": "", "impact": "",
             "direction": "", "kind": "other", "id": ""}
        hm = re.match(r"\S+\s+\(T-?[-\d?]+\)\s+(\S+)\s+—\s+(.+)$", heading)
        if hm:
            f["region"], f["name"] = hm.group(1), hm.group(2).strip()
        for line in b[1:]:
            s = line.strip()
            cb = re.match(r"-\s*\[(.?)\]\s*(.*)$", s)
            if cb:
                mark = cb.group(1).lower()
                f["mark"] = "x" if mark == "x" else "-" if mark == "-" else " "
                rest = cb.group(2)
            elif s.startswith("note:"):
                f["note"] = s[5:].strip()
                continue
            elif s.startswith("src:"):
                sm = re.match(r"src:\s*\S+\s+imp=(\d+)\s+北京\s+(\S+\s+\S+)\s*\|?\s*(.*)$", s)
                if sm:
                    f["importance"] = int(sm.group(1))
                    f["beijing_time"] = sm.group(2)
                    f["link"] = sm.group(3).strip()
                continue
            elif s.startswith("id:"):
                f["id"] = s[3:].strip()
                continue
            else:
                rest = s
            for k, v in _KV.findall(rest):
                if k in ("impact", "direction", "date", "tz", "kind"):
                    f[k] = v.upper() if k == "tz" else v
            f["impact"] = f["impact"].lower()
            f["direction"] = f["direction"].lower().replace("-", "_")
        if not f["id"]:
            warnings.append(f"block without an `id:` line dropped: {heading}")
            continue
        items.append(Item(**f))
    return items, warnings


# ── state files ──────────────────────────────────────────────────────────────

def _atomic_write(path: Path, text: str) -> None:
    """Temp file beside the target, fsync, os.replace — same as position_manager."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _write_json(path: Path, data: dict) -> None:
    _atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_inbox(path: Path) -> tuple[list, list]:
    if not path.exists():
        return [], []
    return parse_inbox(path.read_text(encoding="utf-8"))


def load_ledger(path: Path) -> dict:
    if not path.exists():
        return {"note": "event_inbox.py 决策台账: 已保留(keep)/跳过(skip)/过期未决(expired) "
                        "的候选，按 inbox_id 永不再提议。只追加。", "decisions": []}
    return json.loads(path.read_text(encoding="utf-8"))


def load_events_doc(path: Path) -> dict:
    """events.json as a whole document. Unreadable → raise, never overwrite it."""
    if not path.exists():
        return {"events": []}
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc.get("events"), list):
        raise ValueError(f"{path} has no `events` list — refusing to write it")
    return doc


def _record(ledger: dict, it: Item, decision: str, today: _date) -> None:
    ledger["decisions"].append({
        "inbox_id": it.id, "decision": decision, "decided": today.isoformat(),
        "name": it.name, "date": it.date, "tz": it.tz})


# ── operations ───────────────────────────────────────────────────────────────

def refresh(today: _date | None = None, inbox_path: Path = INBOX_FILE,
            ledger_path: Path = LEDGER_FILE, events_path: Path = EVENTS_FILE,
            fetch_fn=None, days: int = HORIZON_DAYS,
            min_importance: int = MIN_IMPORTANCE) -> dict:
    """Append NEW candidates; keep every owner mark/edit already in the file.

    Undecided items below `min_importance` (left from a lower threshold) are
    dropped without a ledger entry, so lowering the threshold brings them back.
    """
    today = today or _date.today()
    items, warnings = read_inbox(inbox_path)
    ledger = load_ledger(ledger_path)
    decided = {d.get("inbox_id") for d in ledger["decisions"]}
    events = load_events_doc(events_path)["events"]

    kept, expired, dup_existing, below = [], [], 0, 0
    for it in items:
        d = it.impact_date()
        if it.mark == " " and d is not None and d < today:
            expired.append(it)
            _record(ledger, it, "expired", today)
        elif it.mark == " " and match_event(it, events):
            dup_existing += 1   # the owner hand-added it to events.json meanwhile
        elif it.mark == " " and it.importance < min_importance:
            below += 1
        else:
            kept.append(it)

    candidates, stats = fetch_candidates(today, days=days, fetch_fn=fetch_fn,
                                        min_importance=min_importance)
    listed = {it.id for it in kept}
    new = []
    counts = {"already_listed": 0, "decided": 0, "past": 0,
              "dup_id": 0, "dup_fuzzy": 0}
    for c in candidates:
        if c.id in listed:
            counts["already_listed"] += 1
            continue
        if c.id in decided:
            counts["decided"] += 1
            continue
        d = c.impact_date()
        if d is None or d < today:
            counts["past"] += 1
            continue
        how = match_event(c, events)
        if how:
            counts[f"dup_{how}"] += 1
            continue
        new.append(c)
        listed.add(c.id)

    final = kept + new
    _atomic_write(inbox_path, render_inbox(final, today))
    if expired:
        _write_json(ledger_path, ledger)
    return {
        "fetched": stats["candidates"], "new": len(new),
        "pending": sum(1 for i in final if i.mark == " "),
        "expired": len(expired), "dup_existing": dup_existing,
        "below_threshold": below, **counts,
        "fetch_errors": len(stats["errors"]), "empty_days": len(stats["empty_days"]),
        "errors": stats["errors"], "warnings": warnings,
    }


def promote(today: _date | None = None, inbox_path: Path = INBOX_FILE,
            ledger_path: Path = LEDGER_FILE, events_path: Path = EVENTS_FILE) -> dict:
    """[x] → events.json (+ledger keep); [-] → ledger skip; both leave the inbox.

    Write order is events → ledger → inbox, and the events append is
    idempotent on inbox_id, so a crash between writes can only leave an item
    to be promoted again harmlessly — never a duplicate event.
    """
    today = today or _date.today()
    items, warnings = read_inbox(inbox_path)
    keep = [i for i in items if i.mark == "x"]
    skip = [i for i in items if i.mark == "-"]
    invalid = [{"id": i.id, "name": i.name, "problems": i.problems()}
               for i in keep if i.problems()]
    bad = {x["id"] for x in invalid}
    good = [i for i in keep if i.id not in bad]
    if not good and not skip:
        return {"promoted": 0, "skipped": 0, "invalid": invalid,
                "pending": sum(1 for i in items if i.mark == " "),
                "warnings": warnings}

    if good:
        doc = load_events_doc(events_path)
        have = {e.get("inbox_id") for e in doc["events"]}
        doc["events"].extend(i.to_event() for i in good if i.id not in have)
        doc["updated"] = today.isoformat()
        _write_json(events_path, doc)
    ledger = load_ledger(ledger_path)
    for i in good:
        _record(ledger, i, "keep", today)
    for i in skip:
        _record(ledger, i, "skip", today)
    _write_json(ledger_path, ledger)
    gone = {i.id for i in good} | {i.id for i in skip}
    rest = [i for i in items if i.id not in gone]
    _atomic_write(inbox_path, render_inbox(rest, today))
    return {"promoted": len(good), "skipped": len(skip), "invalid": invalid,
            "pending": sum(1 for i in rest if i.mark == " "), "warnings": warnings}


def pending_items(today: _date | None = None, inbox_path: Path = INBOX_FILE) -> list:
    today = today or _date.today()
    items, _ = read_inbox(inbox_path)
    out = []
    for i in items:
        if i.mark != " ":
            continue
        d = i.impact_date()
        out.append({"id": i.id, "name": i.name,
                    "a_share_impact_date": d.isoformat() if d else None,
                    "days_until_impact": (d - today).days if d else None})
    return sorted(out, key=lambda x: x["a_share_impact_date"] or "")


def status(today: _date | None = None, inbox_path: Path = INBOX_FILE,
           ledger_path: Path = LEDGER_FILE) -> dict:
    today = today or _date.today()
    items, warnings = read_inbox(inbox_path)
    ledger = load_ledger(ledger_path)
    pend = pending_items(today, inbox_path)
    return {
        "pending": len(pend),
        "marked_keep": sum(1 for i in items if i.mark == "x"),
        "marked_skip": sum(1 for i in items if i.mark == "-"),
        "invalid": [{"id": i.id, "problems": i.problems()}
                    for i in items if i.mark == "x" and i.problems()],
        "due_soon": [p for p in pend if p["days_until_impact"] is not None
                     and p["days_until_impact"] <= REMIND_WITHIN_DAYS],
        "ledger": {k: sum(1 for d in ledger["decisions"] if d.get("decision") == k)
                   for k in ("keep", "skip", "expired")},
        "warnings": warnings,
    }


def pipeline_step(today: _date | None = None, inbox_path: Path = INBOX_FILE,
                  ledger_path: Path = LEDGER_FILE, events_path: Path = EVENTS_FILE,
                  fetch_fn=None) -> dict:
    """promote then refresh, for run_daily phase 1. Each half fails alone.

    Promote first so items ticked since the last run reach this run's
    event_calendar read; refresh second so they are already in the ledger.
    The return value is the run's record (`input/event_inbox.json`), which is
    what the doctor reads — not the live inbox.
    """
    today = today or _date.today()
    out = {"as_of": today.isoformat(), "step_errors": []}
    try:
        out["promote"] = promote(today, inbox_path, ledger_path, events_path)
    except Exception as e:  # noqa: BLE001 — refresh still runs
        out["step_errors"].append(f"promote: {type(e).__name__}: {e}")
    try:
        out["refresh"] = refresh(today, inbox_path, ledger_path, events_path,
                                 fetch_fn=fetch_fn)
    except Exception as e:  # noqa: BLE001
        out["step_errors"].append(f"refresh: {type(e).__name__}: {e}")
    try:
        out["pending_items"] = pending_items(today, inbox_path)
    except Exception as e:  # noqa: BLE001
        out["step_errors"].append(f"pending: {type(e).__name__}: {e}")
    return out


def summary_line(rec: dict) -> str:
    p, r = rec.get("promote") or {}, rec.get("refresh") or {}
    line = (f"[event-inbox] new {r.get('new', '?')}, "
            f"pending {len(rec['pending_items']) if 'pending_items' in rec else '?'}, "
            f"promoted {p.get('promoted', '?')}, skipped {p.get('skipped', '?')}, "
            f"fetch errors {r.get('fetch_errors', '?')} "
            f"(+{r.get('empty_days', '?')} empty days)")
    if p.get("invalid"):
        line += f", INVALID [x] {len(p['invalid'])} (kept in inbox)"
    if rec.get("step_errors"):
        line += " — FAILED: " + "; ".join(rec["step_errors"])
    return line


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Event inbox: candidates → events.json.")
    ap.add_argument("cmd", choices=("refresh", "promote", "status"))
    args = ap.parse_args(argv)
    if args.cmd == "refresh":
        res = refresh()
        print(f"fetched {res['fetched']} candidates (imp>={MIN_IMPORTANCE}), "
              f"new {res['new']}, pending {res['pending']}, expired {res['expired']}, "
              f"dup id/fuzzy {res['dup_id']}/{res['dup_fuzzy']}, decided {res['decided']}, "
              f"fetch errors {res['fetch_errors']} (+{res['empty_days']} empty days)")
        for e in res["errors"]:
            print(f"  ! {e['date']}: {e['error']}", file=sys.stderr)
    elif args.cmd == "promote":
        res = promote()
        print(f"promoted {res['promoted']}, skipped {res['skipped']}, "
              f"pending {res['pending']}")
        for x in res["invalid"]:
            print(f"  ! NOT promoted {x['id']} ({x['name']}): "
                  + "; ".join(x["problems"]), file=sys.stderr)
    else:
        res = status()
        print(f"pending {res['pending']}, marked keep {res['marked_keep']}, "
              f"marked skip {res['marked_skip']}, ledger {res['ledger']}")
        for p in res["due_soon"]:
            print(f"  ⏰ {p['a_share_impact_date']} (T-{p['days_until_impact']}) "
                  f"{p['name']}  [{p['id']}]")
        for x in res["invalid"]:
            print(f"  ! invalid [x] {x['id']}: " + "; ".join(x["problems"]))
    for w in res.get("warnings", []):
        print(f"  ! {w}", file=sys.stderr)
    return 1 if res.get("invalid") else 0


if __name__ == "__main__":
    sys.exit(main())
