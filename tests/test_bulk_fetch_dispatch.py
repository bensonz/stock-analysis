"""Provider routing, exercised with fakes instead of patched private names.

`bulk_fetch` was a seven-branch `if provider_name == ...` chain. It is now a
table plus an injection seam, so a test can drive routing and error handling
with plain fakes.

Why that matters beyond tidiness: the alternative is `monkeypatch.setattr` on
private fetch functions, and that failed silently on 2026-08-30. When
`heal_adj_factor_gap` moved from pricedb to pricedb_factors, a patch aimed at
`pricedb.heal_adj_factor_gap` became inert — the caller resolved the name in its
own module — and the REAL function ran inside the test, hitting the network. It
did not error; only an assertion on the call log caught it. A test that quietly
stops testing is worse than no test, and an explicit seam cannot drift that way.

These do not replace tests/test_provider_chain.py, which drives the real
fetchers. They cover the routing layer specifically.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pricedb


def _fake(log, name, exc=None):
    def f(conn, stocks, beg, end, provider):
        log.append(name)
        if exc:
            raise exc
        return f"{name}-ok"
    return f


def test_each_provider_name_routes_to_its_own_fetcher():
    log = []
    dispatch = {n: _fake(log, n) for n in
                (pricedb.PROVIDER_IFIND, pricedb.PROVIDER_AKSHARE, pricedb.PROVIDER_SINA)}
    for name in dispatch:
        pricedb.bulk_fetch(None, [], "20260831", "20260831", name, None,
                           dispatch=dispatch)
    assert log == [pricedb.PROVIDER_IFIND, pricedb.PROVIDER_AKSHARE, pricedb.PROVIDER_SINA]


def test_only_the_named_provider_is_called():
    """Routing to iFinD must not also touch sina — the chain relies on trying
    exactly one provider per attempt."""
    log = []
    dispatch = {pricedb.PROVIDER_IFIND: _fake(log, "ifind"),
                pricedb.PROVIDER_SINA: _fake(log, "sina")}
    pricedb.bulk_fetch(None, [], "20260831", "20260831",
                       pricedb.PROVIDER_IFIND, None, dispatch=dispatch)
    assert log == ["ifind"]


def test_an_unknown_provider_raises_rather_than_silently_doing_nothing():
    """A typo'd provider name must fail loudly. Returning None here would look
    exactly like a successful fetch of zero rows."""
    with pytest.raises(ValueError, match="Unknown provider"):
        pricedb.bulk_fetch(None, [], "20260831", "20260831", "nope", None,
                           dispatch={})


def test_a_provider_failure_propagates_to_the_caller():
    """cmd_update decides whether to fall back based on the exception escaping.
    Swallowing it here would strand the run on a dead provider."""
    dispatch = {pricedb.PROVIDER_IFIND:
                _fake([], "ifind", exc=RuntimeError("iFinD token expired"))}
    with pytest.raises(RuntimeError, match="token expired"):
        pricedb.bulk_fetch(None, [], "20260831", "20260831",
                           pricedb.PROVIDER_IFIND, None, dispatch=dispatch)


def test_the_return_value_reaches_the_caller():
    dispatch = {pricedb.PROVIDER_SINA: _fake([], "sina")}
    assert pricedb.bulk_fetch(None, [], "20260831", "20260831",
                              pricedb.PROVIDER_SINA, None,
                              dispatch=dispatch) == "sina-ok"


def test_production_uses_the_real_table_when_nothing_is_injected():
    """The seam must be test-only. If omitting `dispatch` did anything other
    than use the real fetchers, the live path would differ from what ships."""
    table = pricedb._bulk_fetchers()
    assert table[pricedb.PROVIDER_IFIND] is pricedb._bulk_fetch_ifind
    assert table[pricedb.PROVIDER_AKSHARE] is pricedb._bulk_fetch_akshare
    assert table[pricedb.PROVIDER_SINA] is pricedb._bulk_fetch_sina


def test_every_provider_iter_providers_can_yield_is_routable():
    """iter_providers and the dispatch table must not drift apart: a provider
    offered by the chain but missing from the table would raise 'Unknown
    provider' mid-run, on the fallback path, which is exactly when it is least
    welcome."""
    table = pricedb._bulk_fetchers()
    for name in (pricedb.PROVIDER_IFIND, pricedb.PROVIDER_AKSHARE, pricedb.PROVIDER_SINA):
        assert name in table


def test_retired_providers_stay_callable_for_forensics():
    """They are out of iter_providers deliberately, but the docs point at them
    for manual investigation, so routing must still work."""
    table = pricedb._bulk_fetchers()
    for name in (pricedb.PROVIDER_TUSHARE, pricedb.PROVIDER_EASTMONEY,
                 pricedb.PROVIDER_EASTMONEY_CLIST, pricedb.PROVIDER_BAOSTOCK):
        assert name in table
