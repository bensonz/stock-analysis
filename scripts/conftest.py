"""Pytest configuration for scripts/ tests.

Mirrors tests/conftest.py so that ``integration`` markers can be filtered
when running ``pytest scripts/`` directly.
"""
import sys
from pathlib import Path

# scripts/ holds a FLAT import namespace: modules import each other by bare name
# (`import pricedb`). On 2026-08-30 the leaf tools moved into scripts/research/
# and scripts/oneoff/ for navigability, so those directories go on the path too.
# Doing it here rather than in each test keeps every existing test file
# unmodified — which is the proof the move was transparent.
_SCRIPTS = Path(__file__).resolve().parent
for _d in (_SCRIPTS, _SCRIPTS / "research", _SCRIPTS / "oneoff"):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that hit real APIs (skipped unless explicitly selected)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("-m", default=None) is not None and "integration" in config.getoption("-m"):
        return
    skip_integration = pytest.mark.skip(reason="integration test: pass -m integration to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
