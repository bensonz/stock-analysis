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

# Integration-test gating lives in the ROOT conftest.py (pytest only honours
# pytest_addoption there). This file now owns sys.path setup only.
