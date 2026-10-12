"""Where the live state in tracking/ lives — the ONE place that says so.

tracking/ is split by kind (2026-10-12, docs/TRACKING_LAYOUT stage 2)::

    tracking/
      book/      config.json, positions.json,
                 active/{code}.json, closed/{code}_{exitDate}.json
      ledgers/   hypotheses.json, predictions.jsonl, rotation_ledger.json
      calendar/  events.json, event_inbox.md, event_inbox_ledger.json

Before, everything sat in one directory and every book reader globbed
``tracking/*.json``. Non-position files in that glob crashed the list
(rotation_ledger.json, 2026-08-11) and were deleted by ``--reset-to``
(2026-10-12). Now a book operation reads ``book/`` only, so it cannot reach a
ledger or the calendar by a glob.

Writers bind these names at import (``from tracking_paths import ACTIVE_DIR``);
tests repoint them per module. ``Layout(root)`` gives the same tree under any
root, for tools that take a ``tracking_dir`` argument and for tests.

The pre-move paths are not kept here: nothing reads tracking/ at old git
revisions. ``scripts/oneoff/migrate_tracking_layout.py`` holds the old → new
map for the one move.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TRACKING_DIR = PROJECT_ROOT / "tracking"


@dataclass(frozen=True)
class Layout:
    """The tracking/ tree under ``root``."""

    root: Path

    @property
    def book(self) -> Path:
        return self.root / "book"

    @property
    def active(self) -> Path:
        return self.book / "active"

    @property
    def closed(self) -> Path:
        return self.book / "closed"

    @property
    def positions(self) -> Path:
        return self.book / "positions.json"

    @property
    def config(self) -> Path:
        return self.book / "config.json"

    @property
    def ledgers(self) -> Path:
        return self.root / "ledgers"

    @property
    def hypotheses(self) -> Path:
        return self.ledgers / "hypotheses.json"

    @property
    def predictions(self) -> Path:
        return self.ledgers / "predictions.jsonl"

    @property
    def rotation_ledger(self) -> Path:
        return self.ledgers / "rotation_ledger.json"

    @property
    def calendar(self) -> Path:
        return self.root / "calendar"

    @property
    def events(self) -> Path:
        return self.calendar / "events.json"

    @property
    def event_inbox(self) -> Path:
        return self.calendar / "event_inbox.md"

    @property
    def event_inbox_ledger(self) -> Path:
        return self.calendar / "event_inbox_ledger.json"

    def dirs(self) -> tuple[Path, ...]:
        return (self.active, self.closed, self.ledgers, self.calendar)

    def files(self) -> tuple[Path, ...]:
        """Every fixed-name state file (not the per-trade files)."""
        return (self.positions, self.config, self.hypotheses, self.predictions,
                self.rotation_ledger, self.events, self.event_inbox,
                self.event_inbox_ledger)

    def make_dirs(self) -> "Layout":
        for d in self.dirs():
            d.mkdir(parents=True, exist_ok=True)
        return self


LIVE = Layout(TRACKING_DIR)

BOOK_DIR = LIVE.book
ACTIVE_DIR = LIVE.active
CLOSED_DIR = LIVE.closed
POSITIONS_FILE = LIVE.positions
PORTFOLIO_CONFIG_FILE = LIVE.config

LEDGERS_DIR = LIVE.ledgers
HYPOTHESES_FILE = LIVE.hypotheses
PREDICTIONS_FILE = LIVE.predictions
ROTATION_LEDGER_FILE = LIVE.rotation_ledger

CALENDAR_DIR = LIVE.calendar
EVENTS_FILE = LIVE.events
EVENT_INBOX_FILE = LIVE.event_inbox
EVENT_INBOX_LEDGER_FILE = LIVE.event_inbox_ledger
