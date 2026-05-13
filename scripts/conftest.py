"""Pytest configuration for scripts/ tests.

Mirrors tests/conftest.py so that ``integration`` markers can be filtered
when running ``pytest scripts/`` directly.
"""
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
