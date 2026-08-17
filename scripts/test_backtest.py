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
    assert exits_fn("d", {}, pos(-3.2, 5)) == []           # early rule expired
    # Rule 5 time stop = 15 sessions / <3% (ANALYST.md). 20/5 → 10/3 on 08-16,
    # then 10 measured worst of five variants → 15 on 08-17 (EXIT_ABLATION.md).
    assert exits_fn("d", {}, pos(2.9, 15)) == [("X", "time_decay")]   # fires ON day 15
    assert exits_fn("d", {}, pos(2.9, 14)) == []           # ...not before
    assert exits_fn("d", {}, pos(2.9, 10)) == []           # ...and not at the old 10
    assert exits_fn("d", {}, pos(3.0, 25)) == []           # >=3% rides, at any age
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
# --------------------------------------------------------------------------- #
# Stage 2 — engine knobs and strategy variants
# --------------------------------------------------------------------------- #
def test_entry_size_multiplier_scales_alloc():
    p = _panels({"600000": [10, 10, 12, 12, 12, 12, 12, 12, 12, 12]})

    def buy_half(d, panels):
        return [("600000", 0.5)] if d == DATES[0] else []

    res = bt.run(p, buy_half, _never, config={**NO_COST, "alloc_pct": 4.0})
    # 4% × 0.5 = 2% alloc; +20% move → equity 1 + 0.02*0.2 = 1.004
    assert abs(dict(res["equity_curve"])[DATES[3]] - 1.004) < 1e-9


def test_max_new_entries_per_day_caps_fills():
    codes = [f"60000{i}" for i in range(5)]
    p = _panels({c: [10] * 10 for c in codes})

    def buy_all_once(d, panels):
        return codes if d == DATES[0] else []

    res = bt.run(p, buy_all_once, _never,
                 config={**NO_COST, "max_new_entries_per_day": 2})
    assert len(res["open_positions"]) == 2


def test_min_cash_pct_floor_blocks_entry():
    codes = [f"60000{i}" for i in range(5)]
    p = _panels({c: [10] * 10 for c in codes})

    def buy_all(d, panels):
        return codes if d == DATES[0] else []

    # 10% each, floor 75% → only 2 fit (cash 100→90→80; a third would hit 70)
    res = bt.run(p, buy_all, _never,
                 config={**NO_COST, "alloc_pct": 10.0, "min_cash_pct": 75.0})
    assert len(res["open_positions"]) == 2


def test_pool_pain_throttle_blocks_and_halves():
    days = ["2026-06-01", "2026-06-02"]
    entries_fn, _ = bt.make_mechanical_analyst(
        {"pool_pain_halve": 30.0, "pool_pain_block": 60.0})
    base = _analyst_panels()

    p_block = dict(base)
    p_block["pool_pain"] = pd.Series([70.0, 70.0], index=days)
    assert entries_fn("2026-06-01", p_block) == []

    p_half = dict(base)
    p_half["pool_pain"] = pd.Series([45.0, 45.0], index=days)
    assert entries_fn("2026-06-01", p_half) == [("A", 0.5)]

    p_calm = dict(base)
    p_calm["pool_pain"] = pd.Series([10.0, 10.0], index=days)
    assert entries_fn("2026-06-01", p_calm) == ["A"]


def test_pool_pain_series_computation():
    days = [f"2026-06-{d:02d}" for d in range(1, 5)]
    # A drops 5% over 2 sessions (hurt); B flat; both pass the gate
    closes = pd.DataFrame({"A": [10, 9.8, 9.5, 9.5], "B": [10, 10, 10, 10]},
                          index=days)
    panels = {"closes": closes,
              "rps60": closes * 0 + 90, "rps120": closes * 0 + 90,
              "rps250": closes * 0 + 90}
    pain = bt._pool_pain(panels, 80.0)
    assert pain.loc[days[2]] == 50.0        # A hurt, B not → 1 of 2
    assert pain.loc[days[1]] == 0.0         # 2-session window incomplete → no hurt


def test_pullback_band_requires_dip():
    days = ["2026-06-01", "2026-06-02"]
    entries_fn, _ = bt.make_mechanical_analyst(
        {"dist_ma10_entry_min": -3.0, "dist_ma10_max": 3.0})
    # A at +2% from MA10 → inside band; strength name at +7% → excluded
    p = _analyst_panels(dist_ma10_pct=pd.DataFrame(
        {"A": [2.0] * 2, "B": [2.0] * 2, "C": [2.0] * 2}, index=days))
    assert entries_fn("2026-06-01", p) == ["A"]
    p2 = _analyst_panels(dist_ma10_pct=pd.DataFrame(
        {"A": [7.0] * 2, "B": [2.0] * 2, "C": [2.0] * 2}, index=days))
    assert entries_fn("2026-06-01", p2) == []


def test_wide_stop_disables_early_rule():
    _, exits_fn = bt.make_mechanical_analyst({"hard_stop_pct": -10.0, "early_days": 0})

    def pos(pnl, held):
        return {"X": {"entry_date": "d", "days_held": held, "pnl_pct": pnl}}

    assert exits_fn("d", {}, pos(-4.0, 1)) == []                       # survives
    assert exits_fn("d", {}, pos(-10.5, 1)) == [("X", "rule5_hard_stop")]


def test_experiments_registry_names_resolve():
    for name, spec in bt.EXPERIMENTS.items():
        assert set(spec) <= {"rules", "config"}
        # every rules/config key must exist in its target dict
        for k in spec.get("rules", {}):
            assert k in bt.ANALYST_RULES, f"{name}: unknown rule {k}"
        for k in spec.get("config", {}):
            assert k in bt.DEFAULT_CONFIG, f"{name}: unknown config {k}"


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
