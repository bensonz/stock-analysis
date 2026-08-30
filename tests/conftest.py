"""Pytest configuration for stock-analysis tests."""
import sys
from pathlib import Path

# scripts/ holds a FLAT import namespace: modules import each other by bare name
# (`import pricedb`). On 2026-08-30 the leaf tools moved into scripts/research/
# and scripts/oneoff/ for navigability, so those directories go on the path too.
# Doing it here rather than in each test keeps every existing test file
# unmodified — which is the proof the move was transparent.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
for _d in (_SCRIPTS, _SCRIPTS / "research", _SCRIPTS / "oneoff"):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", action="store_true", default=False,
        help="Run integration tests that hit real APIs"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: marks tests that hit real APIs")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
