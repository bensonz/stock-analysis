"""A missing profile field must not delete an underlying's regime — or invert the signal.

2026-08-31 noon shipped **全面净正gamma (净负gamma: 0/2)** — "net positive across
the board" — to the prompt. The backend had returned all five underlyings. Three
were thrown away by `read_state`, which bailed on `if not spot or not flip`, and
all three carried a perfectly good `total_net_gex`:

    510050 50ETF    flip 3.108   net  +95.1M   kept
    510300 300ETF   flip 4.899   net  +61.2M   kept
    510500 500ETF   flip None    net  -74.8M   DROPPED
    588000 科创50    flip None    net   -2.8M   DROPPED
    159915 创业板    flip None    net  -18.8M   DROPPED

With all five the reading is **偏净负gamma, 3/5 negative** — volatility
amplifying, the opposite of what the model was told.

The bias is not random, which is what makes it dangerous. `flip_point` is a
zero-crossing of the gamma profile; the backend cannot locate one when the
profile does not cross zero inside the strike range, and that is far likelier
under strongly negative net gamma. **The absent field correlates with the
signal**, so the parser systematically discarded the amplifying half and
reported the suppressive remainder as unanimous.

Design rules these tests pin:

1. `total_net_gex` alone determines the regime. `flip_point` is descriptive —
   it feeds dist_to_flip_pct and spot_vs_flip, nothing else.
2. Ratios are reported over the population that could actually be measured;
   `below_flip` must not silently borrow `net_negative`'s denominator.
3. Partial coverage is stated. 2 of 5 must never render as 全面 anything.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_gex


def raw(net, spot=3.0, flip=3.1, code="510050"):
    return {"underlying": code, "spot": spot, "flip_point": flip,
            "total_net_gex": net, "call_wall": 3.0, "put_wall": 3.0,
            "expiry_month": "2609", "captured_at": "2026-08-31T03:30:00+00:00"}


# --- 1. a missing flip_point must not delete the row ------------------------

def test_a_row_without_a_flip_point_is_still_read():
    """The exact 500ETF payload: no flip point, real net GEX of -74.8M."""
    st = fetch_gex.read_state(raw(-74761216.15, spot=7.828, flip=None, code="510500"))
    assert st is not None, "row discarded despite carrying a usable net GEX"
    assert st["total_net_gex"] == -74761216.15
    assert st["regime"].startswith("净负")


def test_the_profile_fields_go_null_rather_than_being_invented():
    """Absent is absent. A fabricated flip point would put a stock on the wrong
    side of a boundary the report draws conclusions from."""
    st = fetch_gex.read_state(raw(-1.0, spot=7.828, flip=None))
    assert st["flip_point"] is None
    assert st["dist_to_flip_pct"] is None
    assert st["spot_vs_flip"] is None


def test_a_row_with_no_net_gex_is_still_rejected():
    """Regime is the one thing that cannot be inferred; without it the row says
    nothing and must not pad the denominator."""
    assert fetch_gex.read_state(raw(None)) is None


def test_a_complete_row_is_unchanged():
    st = fetch_gex.read_state(raw(95111874.46, spot=3.017, flip=3.1081458))
    assert st["flip_point"] == 3.108
    assert st["dist_to_flip_pct"] == -2.93
    assert "下方" in st["spot_vs_flip"]


# --- 2. the signal must reflect everything measurable -----------------------

def _states(*nets):
    out = []
    for i, n in enumerate(nets):
        s = fetch_gex.read_state(raw(n, flip=None, code=f"5105{i:02d}"))
        s["name"] = f"etf{i}"
        out.append(s)
    return out


def test_the_real_2026_08_31_case_reads_net_negative():
    """The regression, in one assertion: +95.1M, +61.2M, -74.8M, -2.8M, -18.8M."""
    o = fetch_gex.overall_reading(
        _states(95111874.46, 61169388.35, -74761216.15, -2795018.65, -18804398.16))
    assert o["net_negative"] == "3/5"
    assert o["signal"] == "偏净负gamma"


def test_all_positive_is_still_reported_as_such():
    o = fetch_gex.overall_reading(_states(1.0, 2.0, 3.0))
    assert o["signal"] == "全面净正gamma" and o["net_negative"] == "0/3"


def test_below_flip_is_counted_over_rows_that_have_a_flip_point():
    """Two rows have a profile, one does not. The ratio must be 1/2, not 1/3 —
    borrowing the wrong denominator understates a real concentration."""
    a = fetch_gex.read_state(raw(1.0, spot=3.0, flip=3.1))    # below
    b = fetch_gex.read_state(raw(1.0, spot=3.2, flip=3.1))    # above
    c = fetch_gex.read_state(raw(1.0, spot=3.0, flip=None))   # unmeasurable
    for i, s in enumerate((a, b, c)):
        s["name"] = f"e{i}"
    assert fetch_gex.overall_reading([a, b, c])["below_flip"] == "1/2"


def test_the_pinning_caveat_needs_a_full_profile_not_a_lucky_subset():
    """That caveat fires on `below == n and neg == 0`. If n silently meant
    'rows that happened to parse', a partial fetch could trigger a confident
    structural claim about a board it never saw."""
    a = fetch_gex.read_state(raw(1.0, spot=3.0, flip=3.1))
    b = fetch_gex.read_state(raw(1.0, spot=3.0, flip=None))
    for i, s in enumerate((a, b)):
        s["name"] = f"e{i}"
    assert "注意" not in fetch_gex.overall_reading([a, b])["implication"]


# --- 3. partial coverage must be visible ------------------------------------

def test_fetch_all_records_which_underlyings_were_dropped(monkeypatch):
    """Silence is what let 2-of-5 render as 全面 for who knows how long."""
    def fake(code):
        return raw(1.0, code=code) if code in ("510050", "510300") else None
    monkeypatch.setattr(fetch_gex, "fetch_gex", fake)

    out = fetch_gex.fetch_all()
    cov = out["coverage"]
    assert cov["fetched"] == 2 and cov["expected"] == 5
    assert set(cov["missing"]) == {"510500", "588000", "159915"}
    assert cov["partial"] is True


def test_full_coverage_is_marked_not_partial(monkeypatch):
    monkeypatch.setattr(fetch_gex, "fetch_gex", lambda code: raw(1.0, code=code))
    cov = fetch_gex.fetch_all()["coverage"]
    assert cov["partial"] is False and cov["fetched"] == cov["expected"] == 5


# --- 4. the degraded path has to be printable -------------------------------

def test_the_human_report_survives_a_row_with_no_profile(monkeypatch, capsys):
    """The moment the parser stopped discarding profile-less rows, the --human
    printer died on `f"{None:+.2f}"` — the same NoneType.__format__ break that
    took candidates.md down on 2026-08-25. A fix that surfaces hidden data is
    worthless if surfacing it crashes the report."""
    monkeypatch.setattr(fetch_gex, "fetch_gex",
                        lambda code: raw(-1.0, spot=7.8, flip=None, code=code))
    monkeypatch.setattr(sys, "argv", ["fetch_gex.py", "--human"])

    fetch_gex.main()

    out = capsys.readouterr().out
    assert "净负gamma" in out
    assert "None" not in out, "a null leaked into the human report"
