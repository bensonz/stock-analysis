"""Root pytest configuration — the ONE owner of the integration-test gate.

Before 2026-09-01 this logic lived twice with incompatible mechanisms:
tests/conftest.py gated on a --run-integration option, scripts/conftest.py on
`-m integration`. Both hooks ran globally over all collected items, so the
documented command (`pytest --run-integration`) skipped all 12 integration
tests anyway, only the undocumented combination of BOTH flags ran them, and
`pytest scripts/ --run-integration` hard-errored because the option was
defined in a conftest pytest never loaded for that path. The 12 tests were
silently dead from 2026-05-13 — long enough for two of them to still call a
provider that was retired in August.

pytest only honours pytest_addoption in the ROOTDIR conftest, which is why
this file must exist and why the split version could never work. The two
sub-conftests keep only their sys.path setup.
"""
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", action="store_true", default=False,
        help="Run integration tests that hit real external APIs",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: marks tests that hit real APIs (skipped without --run-integration)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        return
    skip = pytest.mark.skip(reason="integration test: pass --run-integration to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
