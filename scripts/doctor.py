"""Post-run audit: does a run's own record contradict itself?

Detection only. The doctor reads; it never writes to ``tracking/``, never
repairs anything, never touches the books. Its whole output is a verdict at
``runs/<date>/<slot>/audit-result.{md,json}``, written beside the manifest it
judges — a judgment *about* the run, not a product of it.

Two kinds of finding, and the distinction is the entire point:

**invariant** — internally inconsistent in a way no market condition can
produce. ``daily_summary.newPositions`` names a stock the position snapshot
does not hold. A gate reports failure while the manifest reports success. A
HOLD is issued on a code the portfolio does not own. There is no outside
explanation available for any of these, so the *first* occurrence is already a
code defect and is reported as one.

**env** — the outside world misbehaved: provider throttled, batch timed out,
price DB a day stale. One occurrence is weather. The doctor counts consecutive
occurrences across prior slots and promotes a finding to code-defect at
``PROMOTE_AFTER``, because a failure that reproduces on schedule is a design
gap, not bad luck. eastmoney's death is the worked example — occurrence 1 was
weather, occurrence 2 was the pattern, and the correct response was code
(``snapshot_bars.py``). Nothing was watching, so it took a third.

Recurrence is DERIVED by re-reading prior ``audit-result.json`` files rather
than kept in a ledger: one less piece of state to drift out of sync with the
runs it describes. The one thing not derivable from run artifacts is a human
deciding a finding is known and accepted — that lives in ``audit/ACCEPTED.md``,
which this module reads and never writes.

A check that cannot run is reported as **skipped, with its reason**. Silently
passing a check whose artifact is missing is how a health report starts lying,
which is the failure this whole file exists to catch.

Scope limit, stated plainly: this catches failure shapes someone already wrote
a check for. It cannot find a bug of a kind nobody imagined. That is the daily
agent sweep's job (Stage 5), and it is a different tool.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_paths import RUNS_DIR, list_runs_sorted, find_run_dir  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCEPTED_FILE = PROJECT_ROOT / "audit" / "ACCEPTED.md"
#: the standing "what is broken right now" view, refreshed after every audit.
#: A command you have to remember to run is a command nobody runs; the whole
#: point of the aggregate is that it is sitting there when you go looking.
OPEN_FILE = PROJECT_ROOT / "audit" / "OPEN.md"

#: consecutive occurrences after which an env finding is treated as a defect
PROMOTE_AFTER = 3

#: how many prior slots to scan when counting recurrence
RECURRENCE_WINDOW = 12

INVARIANT = "invariant"
ENV = "env"

# Artifacts a successful run must have produced — each from the date it began
# to exist. Judging a February run by August's output contract is the same
# error D9 names for gate statuses: reading old data through a new schema and
# calling the difference a defect. The first sweep did exactly that and flagged
# nine Feb–Mar runs for "missing" positions_snapshot.json, an artifact nothing
# wrote until 2026-03-05. Dates are first observed appearance in runs/.
ARTIFACT_EPOCHS = {
    "report.md": "2026-02-02",
    "daily_summary.json": "2026-02-03",
    "positions_snapshot.json": "2026-03-05",
}

# Actions that assert the portfolio already holds the code.
HOLDING_ACTIONS = {"HOLD", "RAISE_STOP", "SELL", "TRIM", "ADD"}


class CannotCheck(Exception):
    """A check lacks the artifact it needs. Recorded as skipped, never as pass."""


@dataclass
class Finding:
    id: str            # stable across occurrences — this is the recurrence key
    check: str
    kind: str          # INVARIANT | ENV
    title: str
    detail: str
    suspect: str = ""  # where a fix would go (invariant findings)
    fix_cmd: str = ""  # what a human would run (env findings)
    occurrences: int = 1
    first_seen: str = ""
    accepted: str = ""  # non-empty = the acceptance reason from ACCEPTED.md

    @property
    def needs_code_change(self) -> bool:
        if self.accepted:
            return False
        return self.kind == INVARIANT or self.occurrences >= PROMOTE_AFTER


@dataclass
class AuditResult:
    date: str
    slot: str
    findings: list[Finding] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    checks_run: int = 0

    @property
    def code_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.needs_code_change]

    @property
    def ops_findings(self) -> list[Finding]:
        return [f for f in self.findings
                if not f.needs_code_change and not f.accepted]

    @property
    def accepted_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.accepted]

    @property
    def verdict(self) -> str:
        if self.code_findings:
            return "code_change_needed"
        if self.ops_findings:
            return "action_needed"
        return "clean"


# ── the run under audit ──────────────────────────────────────────────────────

@dataclass
class RunView:
    """Everything a check may read, loaded once, missing-tolerant."""
    date: str
    slot: str
    path: Path
    manifest: dict | None = None
    summary: dict | None = None
    snapshot: dict | None = None
    report: str | None = None
    db_health: dict | None = None

    @classmethod
    def load(cls, date: str, slot: str, path: Path) -> "RunView":
        def js(p: Path):
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return None

        out = path / "output"
        try:
            report = (out / "report.md").read_text(encoding="utf-8")
        except Exception:
            report = None
        return cls(date=date, slot=slot, path=path,
                   manifest=js(path / "manifest.json"),
                   summary=js(out / "daily_summary.json"),
                   snapshot=js(out / "positions_snapshot.json"),
                   report=report,
                   # An INPUT artifact, unlike everything above it. db_health is
                   # the single implementation of "is the price data sound" —
                   # the phase-1 gate, the prompt and the report banner all read
                   # this same file. We consume its verdict rather than deriving
                   # our own, because two implementations that disagree leave
                   # nobody able to say which is right.
                   db_health=js(path / "input" / "db_health.json"))

    # -- accessors that fail loudly rather than defaulting to something plausible

    def need(self, name: str):
        val = getattr(self, name)
        if val is None:
            raise CannotCheck(f"{name} missing or unreadable")
        return val

    def held_codes(self) -> set[str]:
        snap = self.need("snapshot")
        pj = snap.get("positions_json") or {}
        active = pj.get("activePositions")
        if active is None:
            raise CannotCheck("snapshot has no positions_json.activePositions")
        return {str(p.get("code")) for p in active if p.get("code")}

    def status(self) -> str:
        return str(self.need("manifest").get("status") or "")

    def gates(self) -> dict:
        return self.need("manifest").get("gates") or {}


# ── invariant checks: no market condition produces these ─────────────────────

def check_new_positions_absent_from_snapshot(v: RunView) -> list[Finding]:
    """`newPositions` claims an open the snapshot does not hold.

    The 2026-08-17 688019 incident. The report prose was corrected but this
    machine-readable field was not, so the artifact still asserts a position
    that never existed. T+1 forbids the innocent explanation (opened and closed
    the same day), which is what makes this an invariant rather than a warning.
    """
    held = v.held_codes()
    claimed = [n for n in (v.need("summary").get("newPositions") or [])
               if n.get("code")]
    out = []
    for n in claimed:
        code = str(n["code"])
        if code not in held:
            out.append(Finding(
                id=f"new-position-not-held:{code}",
                check="new_positions_absent_from_snapshot",
                kind=INVARIANT,
                title=f"daily_summary 声称新开 {code}，持仓快照里没有",
                detail=(f"newPositions 含 {code} ({n.get('name', '')})，但 "
                        f"positions_snapshot.activePositions 不含该代码。"
                        f"T+1 排除了当日开平的解释——两份产物必然有一份在说谎。"),
                suspect="scripts/run_daily.py (newPositions written from intent, "
                        "not from applied outcome)"))
    return out


def check_action_on_code_not_held(v: RunView) -> list[Finding]:
    """HOLD/SELL/RAISE_STOP issued against a code the portfolio does not own.

    The ghost-position family: 12 historical runs carried these, and 02-13's
    ghost went on to cause 03-03's error with nobody noticing either.
    """
    held = v.held_codes()
    out = []
    for a in (v.need("summary").get("actions") or []):
        action = str(a.get("action") or "").upper()
        code = str(a.get("code") or "")
        if not code or action not in HOLDING_ACTIONS:
            continue
        if action == "SELL":
            continue          # sold today → legitimately absent from the snapshot
        if code not in held:
            out.append(Finding(
                id=f"action-on-unheld:{code}",
                check="action_on_code_not_held",
                kind=INVARIANT,
                title=f"{action} {code}，但持仓快照里没有这只票",
                detail=(f"daily_summary 对 {code} ({a.get('name', '')}) 下了 "
                        f"{action}，该动作断言我们持有它；快照显示未持有。"
                        f"幽灵持仓家族——历史上 12 次运行带过这种记录。"),
                suspect="scripts/position_manager.py / decisions applied vs logged"))
    return out


def check_sold_position_still_held(v: RunView) -> list[Finding]:
    """A SELL was recorded and the position is still in the snapshot."""
    held = v.held_codes()
    out = []
    for a in (v.need("summary").get("actions") or []):
        if str(a.get("action") or "").upper() != "SELL":
            continue
        code = str(a.get("code") or "")
        if code and code in held:
            out.append(Finding(
                id=f"sold-still-held:{code}",
                check="sold_position_still_held",
                kind=INVARIANT,
                title=f"SELL {code} 已记录，快照里仍持有",
                detail=(f"daily_summary 记录卖出 {code}，但 post-run 快照仍列为持仓。"
                        f"决策与执行有一边没落地。"),
                suspect="scripts/position_manager.py::apply_decisions"))
    return out


def check_gate_failure_reported_as_success(v: RunView) -> list[Finding]:
    """A gate says failed; the manifest says success."""
    status = v.status()
    failed = [name for name, g in v.gates().items()
              if isinstance(g, dict) and g.get("passed") is False]
    if failed and status == "success":
        return [Finding(
            id="gate-failure-as-success",
            check="gate_failure_reported_as_success",
            kind=INVARIANT,
            title=f"闸门 {', '.join(failed)} 未通过，manifest 却是 success",
            detail=("状态字段与它自己的闸门结果矛盾。任何按 status 过滤健康度的"
                    "工具（站点横幅、周报、这个 doctor）都会读到假信号。"),
            suspect="scripts/run_daily.py status derivation / contracts.RunManifest")]
    return []


def check_success_run_missing_artifacts(v: RunView) -> list[Finding]:
    """status == success but a required output is absent."""
    if v.status() != "success":
        return []
    expected = [n for n, epoch in ARTIFACT_EPOCHS.items() if v.date >= epoch]
    if not expected:
        raise CannotCheck(f"no artifact was mandatory yet on {v.date}")
    missing = [n for n in expected if not (v.path / "output" / n).exists()]
    if missing:
        return [Finding(
            id="success-missing-artifacts",
            check="success_run_missing_artifacts",
            kind=INVARIANT,
            title=f"success 运行缺少产物: {', '.join(missing)}",
            detail=("运行自称成功，但它应当产出的文件不在磁盘上。"
                    "validator 放行了一个不完整的运行。"),
            suspect="scripts/validator.py")]
    return []


def check_duplicate_active_positions(v: RunView) -> list[Finding]:
    snap = v.need("snapshot")
    active = (snap.get("positions_json") or {}).get("activePositions")
    if active is None:
        raise CannotCheck("snapshot has no positions_json.activePositions")
    seen, dupes = set(), set()
    for p in active:
        c = str(p.get("code"))
        if c in seen:
            dupes.add(c)
        seen.add(c)
    if dupes:
        return [Finding(
            id=f"duplicate-positions:{','.join(sorted(dupes))}",
            check="duplicate_active_positions",
            kind=INVARIANT,
            title=f"持仓快照里有重复代码: {', '.join(sorted(dupes))}",
            detail="同一代码出现多次，权益与权重合计都会被重复计入。",
            suspect="scripts/position_manager.py")]
    return []


def check_postrun_marks_are_from_run_day(v: RunView) -> list[Finding]:
    """A post_run snapshot whose marks predate the run day.

    post_run is written after prices are collected, so its marks must be that
    day's. Earlier means the marking step did not run — the failure the site
    provenance work surfaced, checked here at the source instead of the display.

    Marks *later* than the run date are deliberately NOT flagged. The 08-11 and
    08-12 afternoon runs were manual reruns finishing after midnight, so their
    marks are stamped the following day. The first draft of this check compared
    with ``!=`` and called both directions "stale", which was simply false about
    those two runs — the marking step had run, just late. A late rerun does put
    next-day marks on a past date's curve point, but that is the operator's
    deliberate trade against not marking at all, and inventing a severity for it
    would add noise to every evening heal.
    """
    snap = v.need("snapshot")
    if snap.get("snapshot_type") != "post_run":
        raise CannotCheck("not a post_run snapshot")
    if not v.held_codes():
        raise CannotCheck("no positions to mark")
    last = (snap.get("positions_json") or {}).get("lastUpdated")
    if not last:
        return [Finding(
            id="postrun-marks-undated",
            check="postrun_marks_are_from_run_day",
            kind=INVARIANT,
            title="post_run 快照没有 lastUpdated",
            detail="无法判断标记新鲜度；未知不能当作健康处理。",
            suspect="scripts/position_manager.py snapshot writer")]
    if str(last)[:10] < v.date:
        return [Finding(
            id="postrun-marks-stale",
            check="postrun_marks_are_from_run_day",
            kind=INVARIANT,
            title=f"post_run 标记停在 {str(last)[:10]}，运行日是 {v.date}",
            detail=("收盘后快照里的持仓价来自更早的日子，说明本次运行没有真正"
                    "重新标记持仓。权益曲线会照抄旧价。"),
            suspect="scripts/data_collector.py::fetch_position_prices → "
                    "position_manager mark step")]
    return []


# ── env checks: weather until they recur ─────────────────────────────────────

def check_phase_failed(v: RunView) -> list[Finding]:
    out = []
    for name, ph in (v.need("manifest").get("phases") or {}).items():
        if not isinstance(ph, dict) or ph.get("status") != "failed":
            continue
        out.append(Finding(
            id=f"phase-failed:{name}",
            check="phase_failed",
            kind=ENV,
            title=f"阶段 {name} 失败",
            detail="; ".join(str(e) for e in (ph.get("errors") or [])) or "无错误详情",
            fix_cmd=f"python3 scripts/run_daily.py --slot {v.slot} --run"))
    return out


def check_gate_hard_fail(v: RunView) -> list[Finding]:
    out = []
    for name, g in v.gates().items():
        if not isinstance(g, dict):
            continue
        for msg in (g.get("hard_fails") or []):
            # The id is the recurrence key, so two different hard fails from the
            # same gate must not collide — 08-12 noon produced 11 of them and the
            # first draft gave every one the same id, which would have counted a
            # single recurring failure as eleven.
            out.append(Finding(
                id=f"gate-hard-fail:{name}:{_digest(str(msg))}",
                check="gate_hard_fail",
                kind=ENV,
                title=f"{name} 硬闸门拦截",
                detail=str(msg),
                fix_cmd=_suggest_fix(str(msg))))
    return out


def check_source_unhealthy(v: RunView) -> list[Finding]:
    hc = (v.need("manifest").get("phases") or {}).get("health_check") or {}
    out = []
    for name, s in (hc.get("sources") or {}).items():
        if isinstance(s, dict) and s.get("status") not in ("ok", None):
            out.append(Finding(
                id=f"source-unhealthy:{name}",
                check="source_unhealthy",
                kind=ENV,
                title=f"数据源 {name} 状态 {s.get('status')}",
                detail=json.dumps(s, ensure_ascii=False)))
    return out


def check_pricedb_current(v: RunView) -> list[Finding]:
    """Price DB did not reach the run's own date."""
    phases = v.need("manifest").get("phases") or {}
    pre = phases.get("preflight_pricedb") or {}
    latest, target = pre.get("latest_date"), pre.get("target")
    if not latest or not target:
        raise CannotCheck("preflight_pricedb has no latest_date/target")
    if latest != target:
        return [Finding(
            id="pricedb-behind-target",
            check="pricedb_current",
            kind=ENV,
            title=f"价格库停在 {latest}，本次运行目标 {target}",
            detail="筛选与 RPS 都会用过期的收盘价计算。",
            fix_cmd=f"python3 scripts/pricedb.py snapshot --date {target} && "
                    f"python3 scripts/pricedb.py update")]
    return []


def check_snapshot_wrote_rows(v: RunView) -> list[Finding]:
    """Preflight snapshot ran but inserted nothing on a session day."""
    phases = v.need("manifest").get("phases") or {}
    note = (phases.get("preflight_pricedb") or {}).get("snapshot")
    if note is None:
        raise CannotCheck("no snapshot note in preflight (run predates the writer)")
    m = re.search(r"(\d+)\s+inserted", str(note))
    if m and int(m.group(1)) == 0 and "0 rows" not in str(note):
        return [Finding(
            id="snapshot-inserted-nothing",
            check="snapshot_wrote_rows",
            kind=ENV,
            title="快照写入 0 行",
            detail=f"preflight snapshot: {note}",
            fix_cmd=f"python3 scripts/pricedb.py snapshot --date {v.date} --dry-run")]
    return []


def check_db_health_warnings(v: RunView) -> list[Finding]:
    """Phase 1 recorded a data-quality warning that no one downstream acted on.

    db_health rides into the prompt and the report banner, but until 2026-08-27
    nothing compared it against later runs — so an adj-factor lag announced
    itself for days while every audit read ✅ 无发现. The lag is what corrupts
    rps_cache.ma10 into hfq units, so "just a warning" is how a wrong number
    reaches a report.

    Ids strip digits (via _digest) so the same warning on consecutive sessions
    shares an id and can actually accumulate a streak. Per-date ids would reset
    the count every day and never promote.
    """
    health = v.need("db_health")
    warnings = health.get("warnings")
    if warnings is None:
        raise CannotCheck("db_health has no warnings list")
    return [Finding(
        id=f"db-health-warning:{_digest(str(w))}",
        check="db_health_warnings",
        kind=ENV,
        title=f"数据健康告警: {str(w)[:70]}",
        detail=str(w),
        suspect="scripts/pricedb.py db_health",
        fix_cmd="python3 scripts/pricedb.py factors verify")
        for w in warnings]


def check_db_health_spot_check(v: RunView) -> list[Finding]:
    """The spot audit sampled rows but confirmed none of them.

    `sampled: 20, checked: 0, fetch_failures: 20` shipped under `ok: true` on
    2026-08-27. Zero mismatches out of zero comparisons is not a clean bill of
    health; it is the absence of one, and reporting it as a pass is the exact
    lie this layer exists to catch.
    """
    spot = (v.need("db_health") or {}).get("spot_check")
    if not spot:
        raise CannotCheck("db_health has no spot_check block")
    sampled, checked = spot.get("sampled"), spot.get("checked")
    if sampled is None or checked is None:
        raise CannotCheck("spot_check has no sampled/checked counts")
    if sampled > 0 and checked == 0:
        return [Finding(
            id="db-health-spot-check-verified-nothing",
            check="db_health_spot_check",
            kind=ENV,
            title=f"抽查 {sampled} 只、实际核对 0 只",
            detail=f"spot_check: {json.dumps(spot, ensure_ascii=False)}。"
                   f"0 处不一致来自 0 次比对，不能读作数据无误。",
            fix_cmd="python3 scripts/pricedb.py status")]
    return []


CHECKS = [
    # invariant
    check_new_positions_absent_from_snapshot,
    check_action_on_code_not_held,
    check_sold_position_still_held,
    check_gate_failure_reported_as_success,
    check_success_run_missing_artifacts,
    check_duplicate_active_positions,
    check_postrun_marks_are_from_run_day,
    # env
    check_phase_failed,
    check_gate_hard_fail,
    check_source_unhealthy,
    check_pricedb_current,
    check_snapshot_wrote_rows,
    check_db_health_warnings,
    check_db_health_spot_check,
]


def _digest(msg: str) -> str:
    """Short stable key for a message, so ids survive number churn.

    Digits are stripped first: "454 rows vs ~5210" and "1102 rows vs ~5210" are
    the same failure on two days, and must share an id or recurrence can never
    promote them.
    """
    import hashlib
    norm = re.sub(r"\d+", "#", msg).strip().lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:8]


def _suggest_fix(msg: str) -> str:
    if "partial" in msg:
        return "python3 scripts/pricedb.py repair"
    if "stale" in msg or "staleness" in msg:
        return "python3 scripts/pricedb.py update"
    return ""


# ── recurrence, acceptance, reporting ────────────────────────────────────────

def load_accepted(path: Path | None = None) -> dict[str, str]:
    """Parse `audit/ACCEPTED.md`. Lines: `- <finding-id> — <reason>`."""
    path = path or ACCEPTED_FILE
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return out
    for line in text.splitlines():
        m = re.match(r"\s*[-*]\s+`?([^\s`]+)`?\s*[—:-]\s*(.+)", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


#: noon precedes afternoon; legacy runs are an implicit afternoon.
SLOT_RANK = {"noon": 0, "afternoon": 1}


def calendar_order(runs_dir: Path) -> list[tuple[str, str, Path]]:
    """Runs in CALENDAR order — deliberately not `list_runs_sorted`.

    The house rule is to sort runs by `run_started_at`, because slot *names*
    sort wrong ("afternoon" < "noon"). That rule is right for the equity curve,
    which wants the true chronology of execution. It is wrong here, because
    "the slot before this one" is a calendar question, and `run_started_at`
    answers a different one:

    - backfilled legacy manifests carry timestamps that do not track their own
      dates, which put 2026-04-30 between 04-09 and 04-10 and scrambled the
      whole April neighbour chain;
    - the 08-11 afternoon rerun finished at 00:18 on 08-12, so by start time it
      lands *after* 08-12 noon.

    Either one silently breaks a recurrence streak — the counter would read
    three consecutive eastmoney failures as three unrelated weather events,
    which is precisely the promotion this tool exists to make. Sorting by
    (date, slot rank) is immune to both, since it never consults a timestamp a
    backfill or a late rerun could have written.
    """
    rows = list_runs_sorted(runs_dir, reverse=False)
    return sorted(rows, key=lambda r: (r[0], SLOT_RANK.get(r[1], 1)))


def prior_audits(runs_dir: Path, date: str, slot: str,
                 window: int = RECURRENCE_WINDOW) -> list[dict]:
    """Previous slots' audit-result.json, most recent first."""
    ordered = list(reversed(calendar_order(runs_dir)))
    out, started = [], False
    for d, s, p in ordered:
        if not started:
            if (d, s) == (date, slot):
                started = True
            continue
        try:
            out.append(json.loads((p / "audit-result.json").read_text(encoding="utf-8")))
        except Exception:
            out.append({})       # audited-but-unreadable and never-audited both
        if len(out) >= window:    # break the streak the same way: no match
            break
    return out


def apply_recurrence(findings: list[Finding], history: list[dict]) -> None:
    """Count *consecutive* prior occurrences, and record when it started.

    Consecutive, not total: a finding that appeared twice last month and once
    today is three separate weather events. A finding present in every run
    since Tuesday is a defect.
    """
    for f in findings:
        streak, first = 0, ""
        for audit in history:
            ids = {x.get("id"): x for x in (audit.get("findings") or [])}
            if f.id not in ids:
                break
            streak += 1
            first = audit.get("date") or first
        f.occurrences = streak + 1
        f.first_seen = first or ""


def audit_run(date: str, slot: str, path: Path,
              runs_dir: Path | None = None,
              accepted: dict[str, str] | None = None) -> AuditResult:
    runs_dir = runs_dir or RUNS_DIR
    accepted = load_accepted() if accepted is None else accepted
    view = RunView.load(date, slot, path)
    res = AuditResult(date=date, slot=slot)

    if view.manifest is None:
        res.findings.append(Finding(
            id="manifest-absent",
            check="manifest_present",
            kind=INVARIANT,
            title="该时段没有 manifest",
            detail=("运行目录存在但没有 manifest.json——无法区分'跑了但死在写清单前'"
                    "与'根本没跑'。预检失败零留痕就是这个洞。"),
            suspect="scripts/run_daily.py (write the manifest before preflight)"))
    else:
        for fn in CHECKS:
            try:
                res.findings.extend(fn(view))
                res.checks_run += 1
            except CannotCheck as e:
                res.skipped.append({"check": fn.__name__, "reason": str(e)})
            except Exception as e:                     # a broken check is a finding
                res.skipped.append({"check": fn.__name__,
                                    "reason": f"检查本身出错: {type(e).__name__}: {e}"})

    apply_recurrence(res.findings, prior_audits(runs_dir, date, slot))
    for f in res.findings:
        f.accepted = accepted.get(f.id, "")
    return res


def render_md(res: AuditResult) -> str:
    L = [f"# 运行审计 {res.date} {res.slot}", ""]
    badge = {"clean": "✅ 无发现",
             "action_needed": "🟡 需要人工操作",
             "code_change_needed": "🔴 需要改代码"}[res.verdict]
    L += [f"**结论: {badge}**", "",
          f"_生成于 {datetime.now().astimezone().isoformat(timespec='seconds')}_", ""]

    def block(f: Finding) -> list[str]:
        head = f"### [{f.kind}] {f.title}"
        out = [head, "", f"- `{f.id}`", f"- {f.detail}"]
        if f.occurrences > 1:
            out.append(f"- **连续第 {f.occurrences} 次**"
                       + (f"（始于 {f.first_seen}）" if f.first_seen else "")
                       + (f" — 超过 {PROMOTE_AFTER} 次阈值，按缺陷处理，不再当天气。"
                          if f.occurrences >= PROMOTE_AFTER and f.kind == ENV else ""))
        if f.suspect:
            out.append(f"- 可疑位置: `{f.suspect}`")
        if f.fix_cmd:
            out.append(f"- 处理: `{f.fix_cmd}`")
        return out + [""]

    if res.code_findings:
        L += [f"## 需要改代码 ({len(res.code_findings)})", ""]
        for f in res.code_findings:
            L += block(f)
    if res.ops_findings:
        L += [f"## 需要人工操作 ({len(res.ops_findings)})", ""]
        for f in res.ops_findings:
            L += block(f)
    if res.accepted_findings:
        L += [f"## 已知并接受 ({len(res.accepted_findings)})", ""]
        for f in res.accepted_findings:
            L.append(f"- `{f.id}` — {f.accepted}")
        L.append("")

    L += ["## 检查覆盖", "",
          f"- 已执行: {res.checks_run}/{len(CHECKS)}"]
    if res.skipped:
        L.append(f"- 跳过: {len(res.skipped)}")
        for s in res.skipped:
            L.append(f"  - `{s['check']}` — {s['reason']}")
    L += ["",
          "> 本审计只发现，不修复；从不写入 tracking/。",
          "> 它只能抓住已经写了检查的失败形状——没人想过的新 bug 不在覆盖内。"]
    return "\n".join(L) + "\n"


def write_result(res: AuditResult, path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    payload = {"date": res.date, "slot": res.slot, "verdict": res.verdict,
               "checks_run": res.checks_run, "checks_total": len(CHECKS),
               "skipped": res.skipped,
               "findings": [asdict(f) for f in res.findings]}
    (path / "audit-result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (path / "audit-result.md").write_text(render_md(res), encoding="utf-8")


def open_findings(runs_dir: Path, since: str = "") -> list[dict]:
    """Everything outstanding, folded by PROBLEM rather than by instance.

    The per-run files answer "did THAT run go OK". They cannot answer "what is
    broken right now", because one defect living on eight dates is one problem
    in eight files, and the newest file says nothing about it.

    Folding by finding id was the obvious first cut and it was wrong: ids carry
    the stock code, so a single bug in how newPositions is written showed up as
    eleven separate rows demanding eleven separate fixes. The unit of "a thing
    to go fix" is the CHECK. Instances become evidence underneath it.
    """
    groups: dict[str, dict] = {}
    for date, slot, p in calendar_order(runs_dir):
        if since and date < since:
            continue
        try:
            audit = json.loads((p / "audit-result.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        for f in (audit.get("findings") or []):
            g = groups.setdefault(f["check"], {
                "check": f["check"], "kind": f["kind"], "suspect": f.get("suspect", ""),
                "fix_cmd": f.get("fix_cmd", ""), "instances": [], "dates": set(),
                "max_streak": 1, "accepted": "", "titles": []})
            g["instances"].append({"date": date, "slot": slot, "id": f["id"],
                                   "title": f["title"]})
            g["dates"].add(date)
            g["max_streak"] = max(g["max_streak"], f.get("occurrences", 1))
            g["kind"] = f["kind"]
            g["suspect"] = g["suspect"] or f.get("suspect", "")
            g["fix_cmd"] = g["fix_cmd"] or f.get("fix_cmd", "")
            if f.get("accepted"):
                g["accepted"] = f["accepted"]
    out = []
    for g in groups.values():
        g["dates"] = sorted(g["dates"])
        g["last_seen"] = g["dates"][-1]
        g["needs_code"] = bool(not g["accepted"] and (
            g["kind"] == INVARIANT or g["max_streak"] >= PROMOTE_AFTER))
        out.append(g)
    out.sort(key=lambda g: (g["accepted"] != "", not g["needs_code"],
                            g["last_seen"]), reverse=False)
    out.sort(key=lambda g: (g["accepted"] != "", not g["needs_code"]))
    return out


def render_open(groups: list[dict]) -> str:
    L = ["未结审计发现  (按问题归并, 不按实例)", "=" * 62, ""]
    buckets = [("需要改代码", lambda g: g["needs_code"]),
               ("需要人工操作", lambda g: not g["needs_code"] and not g["accepted"]),
               ("已知并接受", lambda g: bool(g["accepted"]))]
    for label, pick in buckets:
        sel = [g for g in groups if pick(g)]
        if not sel:
            continue
        L.append(f"## {label} ({len(sel)})")
        L.append("")
        for g in sel:
            span = (f"{g['dates'][0]} … {g['last_seen']}"
                    if len(g["dates"]) > 1 else g["last_seen"])
            L.append(f"  ▸ {g['check']}  [{g['kind']}]")
            L.append(f"      {len(g['instances'])} 次 / {len(g['dates'])} 天   {span}"
                     + (f"   最长连续 {g['max_streak']}" if g["max_streak"] > 1 else ""))
            if g["suspect"]:
                L.append(f"      改这里: {g['suspect']}")
            if g["fix_cmd"]:
                L.append(f"      执行:   {g['fix_cmd']}")
            if g["accepted"]:
                L.append(f"      已接受: {g['accepted']}")
            recent = g["instances"][-4:]
            for i in recent:
                L.append(f"        · {i['date']} {i['slot']:<9} {i['title']}")
            if len(g["instances"]) > len(recent):
                L.append(f"        · … 另有 {len(g['instances']) - len(recent)} 次更早的")
            L.append("")
        L.append("")
    if len(L) == 3:
        L.append("  （无）")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Post-run audit (detection only).")
    ap.add_argument("--date")
    ap.add_argument("--slot", choices=("noon", "afternoon"))
    ap.add_argument("--since", help="sweep every run from this date forward")
    ap.add_argument("--open", action="store_true", dest="open_",
                    help="what is outstanding across all runs, folded by problem")
    ap.add_argument("--dry-run", action="store_true", help="print, do not write")
    ap.add_argument("--runs-dir", default=None)
    args = ap.parse_args(argv)

    runs_dir = Path(args.runs_dir) if args.runs_dir else RUNS_DIR

    if args.open_:
        groups = open_findings(runs_dir, since=args.since or "")
        text = render_open(groups)
        print(text)
        if not args.dry_run:
            # Follow --runs-dir. A module-level constant here would mean any
            # test passing a tmp runs dir still writes the REAL audit/OPEN.md —
            # the same import-bound-path leak that put two synthetic trades in
            # tracking/closed/ on 08-19.
            out_file = (OPEN_FILE if runs_dir == RUNS_DIR
                        else runs_dir.parent / "audit" / "OPEN.md")
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(
                "<!-- 由 scripts/doctor.py --open 生成, 不要手改. -->\n"
                "<!-- 要接受某条发现, 编辑同目录的 ACCEPTED.md. -->\n\n"
                "```\n" + text + "\n```\n", encoding="utf-8")
            print(f"→ {out_file}", file=sys.stderr)
        return 1 if any(g["needs_code"] for g in groups) else 0

    if args.since:
        # Calendar order matters twice over here: each audit reads the ones
        # already written behind it, so processing out of order also means
        # computing recurrence against files that do not exist yet.
        rows = [(d, s, p) for d, s, p in calendar_order(runs_dir)
                if d >= args.since]
        worst = 0
        for d, s, p in rows:
            res = audit_run(d, s, p, runs_dir=runs_dir)
            if not args.dry_run:
                write_result(res, p)
            mark = {"clean": "  ", "action_needed": "🟡", "code_change_needed": "🔴"}
            print(f"{mark[res.verdict]} {d} {s:<9} "
                  f"{len(res.code_findings)}码 {len(res.ops_findings)}操作 "
                  f"{res.checks_run}/{len(CHECKS)}查"
                  + ("  " + "; ".join(f.id for f in res.findings[:3])
                     if res.findings else ""))
            worst = max(worst, 2 if res.code_findings else 1 if res.ops_findings else 0)
        return 1 if worst == 2 else 0

    if args.date and args.slot:
        path = runs_dir / args.date / args.slot
        date, slot = args.date, args.slot
        if not path.exists():
            found = find_run_dir(args.date, args.slot, runs_dir)
            if not found:
                print(f"no run dir for {args.date} {args.slot}", file=sys.stderr)
                return 2
            path = found
    else:
        latest = list_runs_sorted(runs_dir, reverse=True)
        if not latest:
            print("no runs found", file=sys.stderr)
            return 2
        date, slot, path = latest[0]

    res = audit_run(date, slot, path, runs_dir=runs_dir)
    print(render_md(res))
    if not args.dry_run:
        write_result(res, path)
        print(f"→ {path / 'audit-result.md'}", file=sys.stderr)
    return 1 if res.code_findings else 0


if __name__ == "__main__":
    sys.exit(main())
