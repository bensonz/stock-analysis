"""Engine tests for backtest.py — synthetic panels, no DB, no network.

Each test pins one microstructure rule from the plan (docs/backtest/
IMPLEMENTATION_PLAN.md D1-D3): T+1, limit-up entry skip, limit-down exit
deferral, cost arithmetic, suspended-day handling, accounting identities.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backtest as bt

DATES = [f"2026-01-{d:02d}" for d in range(1, 11)]

NO_COST = {"commission_pct": 0.0, "stamp_sell_pct": 0.0, "slippage_pct": 0.0}


def _panels(closes: dict, opens: dict | None = None):
    c = pd.DataFrame(closes, index=DATES[: len(next(iter(closes.values())))])
    o = pd.DataFrame(opens, index=c.index) if opens else c.copy()
    return {"closes": c, "opens": o}


def _buy_once(code, on_date=DATES[0]):
    return lambda d, p: [code] if d == on_date else []


def _sell_always(d, p, positions):
    return list(positions)


def _never(d, p, positions=None):
    return []


def test_t_plus_1_blocks_same_day_exit():
    # entry fills day2 open; exit demanded every day; T+1 defers day2's exit
    # to day3's close (drop kept within the 10% board limit — a bigger gap
    # would correctly trip the limit-down deferral instead)
    p = _panels({"600000": [10, 10, 9.5, 9.5, 9.5, 9.5, 9.5, 9.5, 9.5, 9.5]})
    res = bt.run(p, _buy_once("600000"), _sell_always, config=NO_COST)
    assert len(res["trades"]) == 1
    t = res["trades"][0]
    assert t["entry_date"] == DATES[1]
    assert t["exit_date"] == DATES[2]          # not DATES[1]
    assert t["days_held"] == 1


def test_limit_up_open_skips_entry_by_board():
    # main board: open exactly +10% over prev close → unfillable, order dies.
    # ChiNext (20% cap): same +10% open → fills fine.
    closes = {"600000": [10] * 10, "300001": [10] * 10}
    opens = {"600000": [10, 11.0] + [10] * 8, "300001": [10, 11.0] + [10] * 8}
    p = _panels(closes, opens)

    def buy_both(d, panels):
        return ["600000", "300001"] if d == DATES[0] else []

    res = bt.run(p, buy_both, _never, config=NO_COST)
    held = {x["code"] for x in res["open_positions"]}
    assert held == {"300001"}                  # main-board entry was skipped


def test_limit_down_close_defers_exit():
    # exit wanted on day3 whose close is -10% (sealed) → deferred to day4
    p = _panels({"600000": [10, 10, 10, 9.0, 9.5, 9.5, 9.5, 9.5, 9.5, 9.5]})

    def sell_from_day3(d, panels, positions):
        return list(positions) if d >= DATES[3] else []

    res = bt.run(p, _buy_once("600000"), sell_from_day3, config=NO_COST)
    assert len(res["trades"]) == 1
    assert res["trades"][0]["exit_date"] == DATES[4]


def test_suspended_close_defers_exit():
    p = _panels({"600000": [10, 10, 10, float("nan"), 10.2, 10, 10, 10, 10, 10]})

    def sell_from_day3(d, panels, positions):
        return list(positions) if d >= DATES[3] else []

    res = bt.run(p, _buy_once("600000"), sell_from_day3, config=NO_COST)
    assert res["trades"][0]["exit_date"] == DATES[4]


def test_cost_arithmetic_exact():
    # flat prices: net pnl is exactly the cost drag
    p = _panels({"600000": [10] * 10})
    cfg = {"commission_pct": 0.025, "stamp_sell_pct": 0.05, "slippage_pct": 0.10}

    def sell_day2(d, panels, positions):
        return list(positions) if d == DATES[2] else []

    res = bt.run(p, _buy_once("600000"), sell_day2, config=cfg)
    t = res["trades"][0]
    expected = (bt._exit_mult(cfg) / bt._entry_mult(cfg) - 1.0) * 100
    assert t["pnl_pct"] == round(expected, 4)   # engine stores 4dp
    assert expected < 0                         # costs always cost


def test_equity_accounting_hand_computed():
    # buy at 10 (day2 open), price runs to 12 → position gains 20% on a 3%
    # allocation → equity 1 + 0.03*0.2 = 1.006
    p = _panels({"600000": [10, 10, 10, 12, 12, 12, 12, 12, 12, 12]})
    res = bt.run(p, _buy_once("600000"), _never,
                 config={**NO_COST, "alloc_pct": 3.0})
    curve = dict(res["equity_curve"])
    assert abs(curve[DATES[3]] - 1.006) < 1e-9
    assert res["open_positions"][0]["pnl_pct"] == 20.0


def test_positions_max_and_dedupe():
    codes = [f"60000{i}" for i in range(5)]
    p = _panels({c: [10] * 10 for c in codes})

    def buy_all_every_day(d, panels):
        return codes + codes                    # dupes must not double-fill

    res = bt.run(p, buy_all_every_day, _never,
                 config={**NO_COST, "positions_max": 3})
    assert len(res["open_positions"]) == 3


def test_ex_div_gap_no_phantom_stop():
    # ADJUSTED closes are continuous across an ex-div date by construction;
    # a -5%-stop strategy over a flat adjusted series must never fire.
    p = _panels({"600000": [10.0] * 10})

    def stop5(d, panels, positions):
        return [c for c, v in positions.items()
                if v["pnl_pct"] is not None and v["pnl_pct"] <= -5]

    res = bt.run(p, _buy_once("600000"), stop5, config=NO_COST)
    assert res["trades"] == []
    assert len(res["open_positions"]) == 1


def test_out_of_cash_skips_entry():
    codes = [f"60000{i}" for i in range(4)]
    p = _panels({c: [10] * 10 for c in codes})

    def buy_all(d, panels):
        return codes if d == DATES[0] else []

    # 40% each → only 2 fit in 100% cash
    res = bt.run(p, buy_all, _never, config={**NO_COST, "alloc_pct": 40.0})
    assert len(res["open_positions"]) == 2


def test_metrics_max_drawdown():
    p = _panels({"600000": [10, 10, 12, 9, 9, 9, 9, 9, 9, 9]})
    res = bt.run(p, _buy_once("600000"), _never,
                 config={**NO_COST, "alloc_pct": 100.0})
    m = bt.metrics(res)
    # equity: 1.0, 1.0, 1.2, 0.9 → dd = 1 - 0.9/1.2 = 25%
    assert abs(m["max_drawdown_pct"] - 25.0) < 1e-6
    assert m["n_trades"] == 0 and m["open_positions"] == 1


def test_exit_reason_recorded():
    p = _panels({"600000": [10, 10, 10, 10, 10, 10, 10, 10, 10, 10]})

    def sell_with_reason(d, panels, positions):
        return [(c, "rule5") for c in positions] if d == DATES[3] else []

    res = bt.run(p, _buy_once("600000"), sell_with_reason, config=NO_COST)
    assert res["trades"][0]["reason"] == "rule5"


def test_board_limit_mapping():
    assert bt.board_limit("600519") == 0.10
    assert bt.board_limit("002245") == 0.10
    assert bt.board_limit("300037") == 0.20
    assert bt.board_limit("688378") == 0.20
    assert bt.board_limit("830001") == 0.30


# --------------------------------------------------------------------------- #
# Stage 1b — mechanical-ANALYST arm
# --------------------------------------------------------------------------- #
def _analyst_panels(**overrides):
    """Panels with every feature the baseline reads, pre-injected (so
    prepare_analyst_features computes nothing) — 3 codes, 2 days.
    A: passes everything. B: fails the RPS gate. C: overextended (Rule 2b).
    """
    days = ["2026-06-01", "2026-06-02"]

    def f(a, b, c):
        return pd.DataFrame({"A": [a] * 2, "B": [b] * 2, "C": [c] * 2}, index=days)

    panels = {
        "closes": f(10, 10, 10), "opens": f(10, 10, 10),
        "rps60": f(95, 60, 90), "rps120": f(90, 90, 90), "rps250": f(85, 85, 85),
        "dist_ma10_pct": f(2, 2, 2),
        "ma5": f(10, 10, 9.0),          # C: dist_ma5 = +11% > 6% → skip
        "ma20": f(9.8, 9.8, 9.8),
        "ma120": f(9.0, 9.0, 9.0),
        "ma250": f(8.0, 8.0, 8.0),
    }
    panels.update(overrides)
    return panels


def test_mechanical_entries_gate_extension_and_ranking():
    entries_fn, _ = bt.make_mechanical_analyst()
    p = _analyst_panels()
    assert entries_fn("2026-06-01", p) == ["A"]      # B gated out, C overextended

    # break A's MA alignment → nothing qualifies
    p2 = _analyst_panels(ma120=pd.DataFrame(
        {"A": [9.9] * 2, "B": [9.0] * 2, "C": [9.0] * 2},
        index=["2026-06-01", "2026-06-02"]))
    assert entries_fn("2026-06-01", p2) == []

    # two qualifiers rank by rps60 desc
    p3 = _analyst_panels(rps60=pd.DataFrame(
        {"A": [85] * 2, "B": [95] * 2, "C": [90] * 2},
        index=["2026-06-01", "2026-06-02"]),
        ma5=pd.DataFrame({"A": [10] * 2, "B": [10] * 2, "C": [9.0] * 2},
                         index=["2026-06-01", "2026-06-02"]))
    assert entries_fn("2026-06-01", p3) == ["B", "A"]


def test_mechanical_exits_rules():
    _, exits_fn = bt.make_mechanical_analyst()

    def pos(pnl, held):
        return {"X": {"entry_date": "d", "days_held": held, "pnl_pct": pnl}}

    assert exits_fn("d", {}, pos(-5.5, 10)) == [("X", "rule5_hard_stop")]
    assert exits_fn("d", {}, pos(-3.2, 2)) == [("X", "rule5_early")]
    assert exits_fn("d", {}, pos(-3.2, 10)) == []          # early rule expired
    assert exits_fn("d", {}, pos(3.0, 25)) == [("X", "time_decay")]
    assert exits_fn("d", {}, pos(8.0, 25)) == []           # winner rides
    assert exits_fn("d", {}, pos(None, 5)) == []           # suspended: no data


def test_mechanical_arm_end_to_end_stops_out():
    # A qualifies on day1, fills day2 open at 10, crashes -6% by day3 close
    days = [f"2026-06-{d:02d}" for d in range(1, 6)]

    def f(vals):
        return pd.DataFrame({"A": vals}, index=days)

    p = {
        "closes": f([10, 10, 9.4, 9.4, 9.4]), "opens": f([10, 10, 9.9, 9.4, 9.4]),
        "rps60": f([95] * 5), "rps120": f([90] * 5), "rps250": f([85] * 5),
        "dist_ma10_pct": f([2] * 5), "ma5": f([10] * 5), "ma20": f([9.8] * 5),
        "ma120": f([9.0] * 5), "ma250": f([8.0] * 5),
    }
    entries_fn, exits_fn = bt.make_mechanical_analyst()
    res = bt.run(p, entries_fn, exits_fn, config=NO_COST)
    assert len(res["trades"]) == 1
    t = res["trades"][0]
    assert t["reason"] in ("rule5_hard_stop", "rule5_early")
    assert t["entry_date"] == days[1] and t["exit_date"] == days[2]
    assert abs(t["pnl_pct"] - (-6.0)) < 1e-6


# --------------------------------------------------------------------------- #
# Stage 1b — replay arm
# --------------------------------------------------------------------------- #
def test_replay_closed_trades_reconciles(tmp_path):
    import json
    days = [f"2026-07-{d:02d}" for d in range(1, 6)]
    closes = pd.DataFrame({"600176": [38.0, 38.4, 36.1, 36.0, 36.0]}, index=days)
    opens = pd.DataFrame({"600176": [38.0, 38.39, 37.0, 36.0, 36.0]}, index=days)
    panels = {"closes": closes, "opens": opens}

    (tmp_path / "600176.json").write_text(json.dumps([{
        "code": "600176", "name": "中国巨石",
        "entryDate": days[1], "exitDate": days[2],
        "entryPrice": 38.39, "exitPrice": 36.12, "returnPct": -5.91,
    }, {
        "code": "600176", "name": "旧交易",
        "entryDate": "2025-01-01", "exitDate": "2025-01-05",   # pre-panel
        "returnPct": 3.0,
    }]), encoding="utf-8")

    rep = bt.replay_closed_trades(panels=panels, config=NO_COST, closed_dir=tmp_path)
    assert rep["summary"]["total"] == 2
    assert rep["summary"]["replayable"] == 1
    ok = [r for r in rep["trades"] if r["status"] == "ok"][0]
    # sim: 38.39 open → 36.1 close = -5.96% vs recorded -5.91 → within 1.5pp
    assert abs(ok["sim_pct"] - (-5.96)) < 0.02
    assert abs(ok["diff_pp"]) <= 1.5
    assert rep["summary"]["match_rate_pct"] == 100.0
    uncovered = [r for r in rep["trades"] if r["status"] == "date_uncovered"]
    assert len(uncovered) == 1
