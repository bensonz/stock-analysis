"""db_health FAILING must not silently delete the data-quality gates.

Audit A4 / top-10 #3. The old shape: the health check raising left
data["db_health"] absent; contracts' gate does `if health:` and skips ALL
THREE hard gates (staleness, partial-day, spot-audit) — and absent-because-
crashed was indistinguishable from absent-because-old-fixture. The very gates
that saved the DNS-outage days (2026-08-25/26) evaporated exactly when the
checker itself broke.

Contract: a crash writes a SENTINEL {"ok": False, "check_failed": ...}, and
the gate hard-fails on it. Genuinely absent (legacy replay / minimal fixture)
still skips — backward compatibility is preserved by distinguishing "never
ran" from "ran and died".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import contracts


def _gate(data):
    return contracts.validate_phase1_gate(data)


def _minimal(**extra):
    d = {"date": "2026-09-01",
         "market": {"breadth": {"up": 3000, "down": 2000},
                    "indices": {"上证指数": {"change_pct": 0.5, "close": 3900},
                                "深证成指": {"change_pct": 0.5, "close": 14000},
                                "创业板指": {"change_pct": 0.5, "close": 3400}}},
         "positions": [], "position_prices": {},
         "strategy_pool": {"stocks": [{"code": "600000"}]}}
    d.update(extra)
    return d


def test_absent_health_still_skips_for_legacy_fixtures():
    g = _gate(_minimal())
    assert not any("db_health" in f or "health check" in f for f in g.hard_fails)


def test_a_crash_sentinel_hard_fails_the_gate():
    g = _gate(_minimal(db_health={"ok": False,
                                  "check_failed": "sqlite3.OperationalError: locked"}))
    assert any("health check itself failed" in f for f in g.hard_fails), g.hard_fails


def test_a_healthy_block_passes():
    g = _gate(_minimal(db_health={"ok": True, "lag_sessions": 0, "warnings": []}))
    assert not any("health" in f.lower() for f in g.hard_fails)


def test_stale_data_still_hard_fails_as_before():
    g = _gate(_minimal(db_health={"ok": False, "lag_sessions": 3,
                                  "latest_price_date": "2026-08-26",
                                  "expected_latest": "2026-09-01"}))
    assert any("sessions stale" in f for f in g.hard_fails)
