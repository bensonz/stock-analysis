"""Slot-aware run-directory path helpers.

A "run" writes its artifacts to::

    runs/<YYYY-MM-DD>/<slot>/input/...
    runs/<YYYY-MM-DD>/<slot>/output/...

where ``slot`` is derived from the wall-clock hour at run start:

    hour < 13   -> "noon"       (intraday, market open, data UNSETTLED)
    hour >= 13  -> "afternoon"  (post-close, settled data)

The daily pipeline runs twice per trading day (11:35 and 15:35 CST); the slot
subdir keeps both runs from overwriting each other.

Legacy runs (written before slots existed) live directly at
``runs/<date>/input`` and ``runs/<date>/output`` with no slot subdir. Readers
here treat a legacy run as an implicit ``afternoon`` (settled) run so discovery
keeps working without moving any folders.

Sorting note: "afternoon" < "noon" alphabetically, so NEVER sort runs by slot
name. Sort by ``run_started_at`` from each run's manifest.json instead.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"

SLOTS = ("noon", "afternoon")
# Runs started before this local hour are "noon"; at/after it, "afternoon".
NOON_HOUR_CUTOFF = 13


def resolve_slot(explicit: str | None = None, now: datetime | None = None) -> str:
    """Resolve the slot for a run.

    An explicit slot (from ``--slot``) always wins. Otherwise the slot is
    derived from the local clock: before 13:00 -> "noon", else "afternoon".
    """
    if explicit:
        if explicit not in SLOTS:
            raise ValueError(f"Invalid slot {explicit!r}; expected one of {SLOTS}")
        return explicit
    now = now or datetime.now()
    return "noon" if now.hour < NOON_HOUR_CUTOFF else "afternoon"


def get_run_dir(date: str, slot: str) -> Path:
    """Return ``runs/<date>/<slot>/``, creating its input/ and output/ subdirs."""
    if slot not in SLOTS:
        raise ValueError(f"Invalid slot {slot!r}; expected one of {SLOTS}")
    run_dir = RUNS_DIR / date / slot
    (run_dir / "input").mkdir(parents=True, exist_ok=True)
    (run_dir / "output").mkdir(parents=True, exist_ok=True)
    return run_dir


def run_started_at(run_dir: Path) -> str:
    """Return a sortable ISO timestamp for a run directory.

    Prefers ``manifest.json``'s ``run_started_at`` stamp; falls back to the
    directory mtime when the manifest is missing or unstamped (e.g. legacy or
    partial runs). Always returns a string so results can be sorted directly.
    """
    manifest = run_dir / "manifest.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            stamp = data.get("run_started_at")
            if stamp:
                return str(stamp)
        except (json.JSONDecodeError, OSError):
            pass
    try:
        return datetime.fromtimestamp(run_dir.stat().st_mtime).astimezone().isoformat()
    except OSError:
        return ""


def iter_run_dirs(runs_dir: Path | None = None) -> list[tuple[str, str, Path]]:
    """Enumerate every run as ``(date, slot, run_dir)`` tuples.

    Covers both the slot layout (``runs/<date>/<slot>/``) and the legacy layout
    (``runs/<date>/`` with a direct ``output/``). Legacy runs are reported with
    slot ``"afternoon"`` and ``run_dir`` pointing at the date directory itself.
    Results are unsorted; use :func:`list_runs_sorted` for ordering.
    """
    base = runs_dir or RUNS_DIR
    result: list[tuple[str, str, Path]] = []
    if not base.exists():
        return result
    for date_dir in base.iterdir():
        if not date_dir.is_dir():
            continue
        date = date_dir.name
        found_slot = False
        for slot in SLOTS:
            slot_dir = date_dir / slot
            if slot_dir.is_dir():
                result.append((date, slot, slot_dir))
                found_slot = True
        # Legacy layout: runs/<date>/output with no slot subdir -> implicit afternoon.
        if not found_slot and (date_dir / "output").exists():
            result.append((date, "afternoon", date_dir))
    return result


def list_runs_sorted(runs_dir: Path | None = None, reverse: bool = True) -> list[tuple[str, str, Path]]:
    """All runs sorted by ``run_started_at`` (newest first when ``reverse``).

    The date is used as a tiebreaker so ordering stays deterministic when two
    runs share (or lack) a start stamp.
    """
    runs = iter_run_dirs(runs_dir)
    runs.sort(key=lambda t: (run_started_at(t[2]), t[0]), reverse=reverse)
    return runs


def find_run_dir(date: str, slot: str | None = None, runs_dir: Path | None = None) -> Path | None:
    """Resolve an existing run directory for reading.

    - When ``slot`` is given, return that slot's run dir if it exists (a legacy
      layout counts as an existing ``afternoon``), else ``None``.
    - When ``slot`` is ``None``, return the canonical run for the date: the
      ``afternoon`` run is preferred as the "latest settled state"; ties break
      on ``run_started_at``. Returns ``None`` when no run exists for the date.
    """
    date_runs = [(s, d) for (dt, s, d) in iter_run_dirs(runs_dir) if dt == date]
    if not date_runs:
        return None
    if slot is not None:
        if slot not in SLOTS:
            raise ValueError(f"Invalid slot {slot!r}; expected one of {SLOTS}")
        for s, d in date_runs:
            if s == slot:
                return d
        return None
    # Prefer afternoon (settled); among the rest, newest by run_started_at.
    date_runs.sort(key=lambda item: (item[0] == "afternoon", run_started_at(item[1])), reverse=True)
    return date_runs[0][1]
