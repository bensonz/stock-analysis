"""Tests for the static portfolio site generator (2026-08-06).

Pins the equity-series extraction rules: legacy + slotted run layouts,
latest-snapshot-of-the-day wins, broken/empty snapshots skipped.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_site as bs


def _snap(tmp, rel, time, equity, ret=None):
    path = tmp / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "snapshot_time": time,
        "positions_json": {
            "portfolio": {
                "startingCapital": 1000000,
                "totalEquity": equity,
                "totalReturnPct": ret,
                "positionsUsed": 2,
            }
        },
    }), encoding="utf-8")


def test_series_legacy_and_slotted_latest_wins(tmp_path):
    runs = tmp_path / "runs"
    # legacy layout day
    _snap(runs, "2026-03-05/input/positions_snapshot.json",
          "2026-03-05T15:35:00+08:00", 968982.0, -3.1)
    # slotted day: afternoon must beat noon
    _snap(runs, "2026-08-06/noon/input/positions_snapshot.json",
          "2026-08-06T11:35:00+08:00", 960000.0)
    _snap(runs, "2026-08-06/afternoon/input/positions_snapshot.json",
          "2026-08-06T15:35:00+08:00", 964319.0)
    series = bs.collect_equity_series(runs)
    assert [p["date"] for p in series] == ["2026-03-05", "2026-08-06"]
    assert series[1]["equity"] == 964319.0  # afternoon snapshot won


def test_output_postrun_snapshot_beats_input_prerun(tmp_path):
    # 2026-08-07: input/ (pre_run) carries the PREVIOUS close's marks — using
    # it made today's equity equal yesterday's (delta 0). output/ must win.
    runs = tmp_path / "runs"
    _snap(runs, "2026-08-07/noon/input/positions_snapshot.json",
          "2026-08-07T11:35:00+08:00", 972360.0)
    out = runs / "2026-08-07/noon/output/positions_snapshot.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "snapshot_time": "2026-08-07T11:45:02+08:00",
        "snapshot_type": "post_run",
        "positions_json": {"portfolio": {
            "startingCapital": 1000000, "totalEquity": 979412.0,
            "totalReturnPct": -2.06, "positionsUsed": 9}},
    }), encoding="utf-8")
    series = bs.collect_equity_series(runs)
    assert series[0]["equity"] == 979412.0
    assert series[0]["stype"] == "post_run"
    details = bs.collect_day_details(series, [])
    assert "pre" not in details["2026-08-07"]

    # a day with ONLY a pre_run snapshot gets the visible stale marker
    pre = runs / "2026-08-08/noon/input/positions_snapshot.json"
    pre.parent.mkdir(parents=True)
    pre.write_text(json.dumps({
        "snapshot_time": "2026-08-08T11:35:00+08:00",
        "snapshot_type": "pre_run",
        "positions_json": {"portfolio": {
            "startingCapital": 1000000, "totalEquity": 979412.0,
            "positionsUsed": 9}},
    }), encoding="utf-8")
    details = bs.collect_day_details(bs.collect_equity_series(runs), [])
    # field renamed 2026-08-21: `pre` asked "is this a pre_run snapshot?",
    # `stale_marks` asks "are the marks older than the day shown?" — the
    # question the badge was always trying to answer. This fixture has no
    # lastUpdated at all, which counts as stale (unknown must stay visible).
    assert details["2026-08-08"]["stale_marks"] == 1


def test_series_skips_broken_and_empty_snapshots(tmp_path):
    runs = tmp_path / "runs"
    bad = runs / "2026-04-01/input/positions_snapshot.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not json", encoding="utf-8")
    empty = runs / "2026-04-02/input/positions_snapshot.json"
    empty.parent.mkdir(parents=True)
    empty.write_text(json.dumps({"snapshot_time": "t", "positions_json": {}}),
                     encoding="utf-8")
    _snap(runs, "2026-04-03/input/positions_snapshot.json",
          "2026-04-03T15:35:00+08:00", 1000500.0)
    series = bs.collect_equity_series(runs)
    assert [p["date"] for p in series] == ["2026-04-03"]


def test_inception_anchor_from_config(tmp_path):
    (tmp_path / "portfolio_config.json").write_text(json.dumps({
        "starting_capital": 1000000, "created": "2026-02-03"}), encoding="utf-8")
    p = bs.inception_point(tmp_path)
    assert p == {"date": "2026-02-03", "time": "", "equity": 1000000.0,
                 "ret_pct": 0.0, "positions": 0, "starting": 1000000,
                 "holdings": [], "synthetic": True}
    assert bs.inception_point(tmp_path / "nope") is None


def test_max_drawdown():
    series = [{"equity": e} for e in [100.0, 110.0, 99.0, 105.0]]
    stats = bs.compute_stats(series, [])
    assert stats["max_drawdown_pct"] == 10.0  # 110 → 99


def test_render_html_contains_data_and_no_external_resources(tmp_path):
    series = [{"date": "2026-08-06", "equity": 964319.0, "ret_pct": -3.57,
               "positions": 9, "starting": 1000000}]
    trades = [{"code": "600988", "name": "赤峰黄金", "entryDate": "2026-07-01",
               "exitDate": "2026-07-10", "holdingDays": 9, "returnPct": 5.5,
               "exitReason": "target_hit"}]
    html_out = bs.render_html(series, {"portfolio": {"totalEquity": 964319.0},
                                       "activePositions": []},
                              trades, bs.compute_stats(series, trades))
    assert "964319" in html_out
    assert "赤峰黄金" in html_out
    # self-contained: nothing loaded from the network at view time
    assert "<script src" not in html_out
    assert "<link" not in html_out
    assert "@import" not in html_out
    assert "胜率 100.0%" in html_out


def _manifest(runs, date, slot, started, status, gate_passed=True, hard=(), applied=True):
    d = runs / date / slot
    d.mkdir(parents=True, exist_ok=True)
    m = {"date": date, "slot": slot, "run_started_at": started, "status": status,
         "gates": {"phase3_to_phase4": {"passed": gate_passed, "hard_fails": list(hard)}}}
    if applied:
        m["phases"] = {"apply": {"status": "ok"}}
    (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")


def test_run_status_banner_only_on_failure(tmp_path, monkeypatch):
    # 7/20 and 8/14 both failed AFTER apply: books moved, commit and site
    # rebuild both skipped, page silently disagreed with reality.
    runs = tmp_path / "runs"
    monkeypatch.setattr(bs, "RUNS_DIR", runs)

    _manifest(runs, "2026-08-13", "afternoon", "2026-08-13T15:35:00+08:00", "degraded")
    assert bs.load_latest_run_status() is None          # healthy → silent

    # newest run failed — picked by run_started_at, never by slot name
    _manifest(runs, "2026-08-14", "afternoon", "2026-08-14T15:35:00+08:00", "failed",
              gate_passed=False, hard=["apply phase had errors: ERROR learnings"])
    st = bs.load_latest_run_status()
    assert st["date"] == "2026-08-14" and st["slot"] == "afternoon"
    assert st["applied"] is True
    assert "ERROR learnings" in st["reasons"][0]

    series = [{"date": "2026-08-14", "equity": 985708.0, "ret_pct": -1.43,
               "positions": 8, "starting": 1000000}]
    html_out = bs.render_html(series, {"portfolio": {"totalEquity": 985708.0},
                                       "activePositions": []},
                              [], bs.compute_stats(series, []), run_status=st)
    assert "最新一次运行未通过校验" in html_out
    assert "ERROR learnings" in html_out
    assert "下方数据已落盘，但该次运行未提交" in html_out

    # and no banner at all when the caller passes nothing
    clean = bs.render_html(series, {"portfolio": {"totalEquity": 985708.0},
                                    "activePositions": []},
                           [], bs.compute_stats(series, []))
    assert "最新一次运行未通过校验" not in clean


def test_holding_row_notes_cover_every_action_type(tmp_path):
    # Until 2026-08-14 the row tooltip read `if (a.a === "HOLD")`, so the
    # 91 SELL/OPEN/RAISE_STOP notes (of 255) silently had no hover — a row
    # that had just been acted on looked like it had nothing to say.
    series = [{"date": "2026-08-14", "equity": 985708.0, "ret_pct": -1.43,
               "positions": 8, "starting": 1000000}]
    html_out = bs.render_html(series, {"portfolio": {"totalEquity": 985708.0},
                                       "activePositions": []},
                              [], bs.compute_stats(series, []))
    assert 'if (a.note) rowNotes[a.c]' in html_out      # every action, not just HOLD
    assert '=== "HOLD"' not in html_out.split("rowNotes")[1][:200]
    assert 'id="rowtip"' in html_out                     # styled tooltip container
    assert "无逐仓决策记录" in html_out                    # missing notes stay explicit


def test_day_details_join(tmp_path):
    runs = tmp_path / "runs"
    _snap(runs, "2026-08-05/noon/input/positions_snapshot.json",
          "2026-08-05T11:35:00+08:00", 960000.0)
    _snap(runs, "2026-08-06/noon/input/positions_snapshot.json",
          "2026-08-06T11:35:00+08:00", 964319.0)
    summary = runs / "2026-08-06/noon/output/daily_summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text(json.dumps({"actions": [
        {"code": "002138", "name": "顺络电子", "action": "HOLD",
         "price": 48.2, "pnl_pct": 10.78, "note": "x" * 500},
        {"code": "603259", "name": "药明康德", "action": "OPEN",
         "price": 126.5, "pnl_pct": 0, "note": "开仓"},
    ]}), encoding="utf-8")
    series = bs.collect_equity_series(runs)
    trades = [{"code": "600988", "name": "赤峰黄金", "exitDate": "2026-08-06",
               "returnPct": -5.2, "exitReason": "stop_hit"}]
    lookup = {("603259", "2026-08-06"): {"sh": 800, "amt": 101200.0, "ap": 10}}
    details = bs.collect_day_details(series, trades, lookup)
    d = details["2026-08-06"]
    assert d["day_pnl"] == 4319.0            # vs previous real snapshot
    assert d["slot"] == "午盘"
    assert len(d["actions"]) == 2
    assert len(d["actions"][0]["note"]) == bs.NOTE_MAX  # truncated
    open_act = d["actions"][1]
    assert (open_act["sh"], open_act["amt"]) == (800, 101200.0)  # sizing joined
    assert "sh" not in d["actions"][0]       # HOLD rows untouched
    assert d["closed"][0]["c"] == "600988"
    assert details["2026-08-05"]["day_pnl"] is None  # no prior snapshot


def test_open_lookup_from_active_and_closed():
    active = {"activePositions": [
        {"code": "603259", "entryDate": "2026-07-31", "shares": 800,
         "allocatedCapital": 101200.0, "allocation_pct": 10}]}
    trades = [{"code": "600988.SH", "entryDate": "2026-07-01", "shares": 5000,
               "allocatedCapital": 99500.0}]
    lk = bs.build_open_lookup(active, trades)
    assert lk[("603259", "2026-07-31")]["sh"] == 800
    assert lk[("600988", "2026-07-01")]["amt"] == 99500.0  # suffix stripped


def test_rebase_index_forward_fills_holidays():
    closes = {"2026-02-02": 3000.0, "2026-02-04": 3300.0}
    out = bs.rebase_index(closes, ["2026-02-03", "2026-02-05"], 1000000.0)
    # base = last close <= 02-03 → 3000; 02-05 forward-fills 02-04's close
    assert out == {"2026-02-03": 1000000.0, "2026-02-05": 1100000.0}
    assert bs.rebase_index({}, ["2026-02-03"], 1e6) == {}
    assert bs.rebase_index(closes, ["2026-01-01"], 1e6) == {}  # no base yet


def test_index_base_is_the_rebase_anchor():
    closes = {"2026-02-02": 3000.0, "2026-02-04": 3300.0}
    assert bs.index_base(closes, "2026-02-03") == 3000.0   # last close <= start
    assert bs.index_base(closes, "2026-02-02") == 3000.0
    assert bs.index_base(closes, "2026-01-01") is None     # no base yet
    assert bs.index_base({}, "2026-02-03") is None
    assert bs.index_base(closes, "") is None


def test_right_axis_labels_index_points_on_the_shared_scale():
    """Second Y axis (2026-08-17): the SAME gridlines, relabelled in 上证 points.

    Not an independent scale on purpose — the overlay exists to answer "did we
    beat 上证", and separate ranges would let the two lines be made to look
    correlated or divergent by choosing limits.
    """
    series = [{"date": "2026-02-03", "equity": 1000000.0, "ret_pct": 0.0,
               "positions": 0, "starting": 1000000},
              {"date": "2026-08-14", "equity": 985708.0, "ret_pct": -1.43,
               "positions": 8, "starting": 1000000}]
    active = {"portfolio": {"totalEquity": 985708.0}, "activePositions": []}
    stats = bs.compute_stats(series, [])
    idx = {"2026-02-03": 1000000.0, "2026-08-14": 965000.0}

    html_out = bs.render_html(series, active, [], stats, index_rebased=idx,
                              idx_base=4067.738)
    assert "const IDXBASE = 4067.738" in html_out
    assert "v / STARTING * IDXBASE" in html_out          # exact, not a second fit
    assert ">上证</text>" in html_out and ">净值</text>" in html_out
    assert "(hasIdx && IDXBASE) ? 56 : 16" in html_out   # gutter only when used

    # no index → no right axis, and the gutter stays narrow
    plain = bs.render_html(series, active, [], stats)
    assert "const IDXBASE = null" in plain


def _market(tmp, rel, timestamp, close, date):
    path = tmp / rel / "input" / "market.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"timestamp": timestamp, "indices": {
        "上证指数": {"code": "sh000001", "close": close, "date": date}}}),
        encoding="utf-8")


def test_settled_index_closes_keeps_only_post_close_quotes(tmp_path):
    # 2026-09-28: the site built at 15:13 before sina's daily kline carried the
    # day, so the chart forward-filled 09-24 through a -1.67% session.
    _market(tmp_path, "2026-09-28/noon", "2026-09-28T11:35:17", 3820.819, "2026-09-28")
    _market(tmp_path, "2026-09-28/afternoon", "2026-09-28T15:05:40", 3823.621, "2026-09-28")
    assert bs.settled_index_closes(tmp_path) == {"2026-09-28": 3823.621}


def test_settled_index_closes_rejects_quote_dated_another_day(tmp_path):
    # A post-close run on a holiday sees the previous session's quote.
    _market(tmp_path, "2026-09-25/afternoon", "2026-09-25T15:05:00", 3888.374, "2026-09-24")
    assert bs.settled_index_closes(tmp_path) == {}


def test_settled_index_closes_skips_missing_or_broken(tmp_path):
    _market(tmp_path, "2026-09-22/afternoon", "2026-09-22T15:05:00", None, "2026-09-22")
    (tmp_path / "2026-09-23/afternoon/input").mkdir(parents=True)
    (tmp_path / "2026-09-23/afternoon/input/market.json").write_text("{", encoding="utf-8")
    assert bs.settled_index_closes(tmp_path) == {}
    assert bs.settled_index_closes(tmp_path / "nope") == {}


def test_merge_index_closes_kline_wins_over_quote():
    kline = {"2026-09-24": 3888.374, "2026-09-28": 3823.62}
    quotes = {"2026-09-28": 3823.9, "2026-09-29": 3850.0}
    assert bs.merge_index_closes(kline, quotes) == {
        "2026-09-24": 3888.374, "2026-09-28": 3823.62, "2026-09-29": 3850.0}


def test_merge_index_closes_drops_quotes_inside_kline_coverage():
    # 2026-09-25 (中秋) had a quote stamped 09-25 carrying 09-24's close. The
    # kline covers past it with no bar, so it was not a trading day.
    kline = {"2026-09-24": 3888.374, "2026-09-28": 3823.621}
    quotes = {"2026-09-25": 3888.374, "2026-09-29": 3830.0}
    assert bs.merge_index_closes(kline, quotes) == {
        "2026-09-24": 3888.374, "2026-09-28": 3823.621, "2026-09-29": 3830.0}
    assert bs.merge_index_closes({}, quotes) == quotes


_KLINE = [{"day": "2026-09-29", "open": "3816.154", "high": "3843.838",
           "low": "3810.812", "close": "3830.451", "volume": "1"},
          {"day": "2026-09-30", "open": "3839.253", "high": "3851.217",
           "low": "3833.086", "close": "3842.195", "volume": "1"}]


def test_load_index_bars_merges_kline_into_cache(tmp_path):
    cache = tmp_path / "ohlc.json"
    cache.write_text(json.dumps({"2026-09-28": [1, 2, 0.5, 1.5]}), encoding="utf-8")
    bars = bs.load_index_bars(_KLINE, cache)
    assert bars["2026-09-30"] == [3839.253, 3851.217, 3833.086, 3842.195]
    assert bars["2026-09-28"] == [1.0, 2.0, 0.5, 1.5]          # cache kept
    assert json.loads(cache.read_text())["2026-09-29"][3] == 3830.451


def test_index_loaders_fall_back_to_cache_when_fetch_failed(tmp_path):
    bs.load_index_bars(_KLINE, tmp_path / "ohlc.json")
    bs.load_index_closes(_KLINE, tmp_path / "close.json")
    assert set(bs.load_index_bars(None, tmp_path / "ohlc.json")) == {"2026-09-29", "2026-09-30"}
    assert bs.load_index_closes(None, tmp_path / "close.json")["2026-09-30"] == 3842.195
    assert bs.load_index_bars(None, tmp_path / "missing.json") == {}


def test_index_day_change_is_vs_previous_index_close_without_forward_fill():
    closes = {"2026-09-30": 3842.195, "2026-10-08": 3811.904}
    assert bs.index_day_change(closes, "2026-10-08") == (-0.79, "2026-09-30")
    assert bs.index_day_change(closes, "2026-10-01") is None    # holiday
    assert bs.index_day_change(closes, "2026-09-30") is None    # no prior close


def _chart_data(html_out):
    import re
    return json.loads(re.search(r"const DATA = (\[.*?\]);\n", html_out).group(1))


def test_chart_points_carry_candle_only_on_exact_bar_dates():
    series = [{"date": "2026-09-29", "equity": 1000000.0, "time": "2026-09-29T15:10:00+08:00"},
              {"date": "2026-09-30", "equity": 1010000.0, "time": "2026-09-30T15:10:00+08:00"},
              {"date": "2026-10-01", "equity": 1010000.0, "time": "2026-10-01T15:10:00+08:00"},
              {"date": "2026-10-08", "equity": 1005000.0, "time": "2026-10-08T11:41:00+08:00"}]
    closes = {"2026-09-29": 3830.451, "2026-09-30": 3842.195, "2026-10-08": 3811.904}
    bars = {"2026-09-29": [3816.154, 3843.838, 3810.812, 3830.451],
            "2026-09-30": [3839.253, 3851.217, 3833.086, 3842.195]}
    active = {"portfolio": {}, "activePositions": []}
    out = _chart_data(bs.render_html(
        series, active, [], bs.compute_stats(series, []),
        index_rebased=bs.rebase_index(closes, [p["date"] for p in series], 1e6),
        idx_base=3830.451, index_bars=bars, index_closes=closes,
        intraday_idx={"2026-10-08": -0.27}))
    by = {p["d"]: p for p in out}
    assert by["2026-09-30"]["k"] == bars["2026-09-30"]
    assert by["2026-09-30"]["pr"] == 1.0 and by["2026-09-30"]["ic"] == 0.31
    assert "k" not in by["2026-10-01"] and "kc" not in by["2026-10-01"]   # holiday
    assert "ic" not in by["2026-10-01"]
    assert by["2026-10-08"]["kc"] == 3811.904 and "k" not in by["2026-10-08"]
    assert by["2026-10-08"]["iq"] == -0.27 and by["2026-10-08"]["t"] == "11:41"
    assert by["2026-10-08"]["pd"] == "2026-10-01" and by["2026-10-08"]["ipd"] == "2026-09-30"
    assert by["2026-10-08"]["pdi"] == "2026-09-30"   # holiday snapshot → its session
    assert "pdi" not in by["2026-09-30"]


def test_intraday_index_pcts_only_for_pre_close_snapshots(tmp_path):
    _market(tmp_path, "2026-10-08/noon", "2026-10-08T11:35:30", 3831.8, "2026-10-08")
    json_path = tmp_path / "2026-10-08/noon/input/market.json"
    data = json.loads(json_path.read_text()); data["indices"]["上证指数"]["change_pct"] = -0.27
    json_path.write_text(json.dumps(data), encoding="utf-8")
    _market(tmp_path, "2026-09-30/afternoon", "2026-09-30T15:05:00", 3842.2, "2026-09-30")
    series = [{"date": "2026-09-30", "time": "2026-09-30T15:10:00+08:00",
               "run_dir": tmp_path / "2026-09-30/afternoon"},
              {"date": "2026-10-08", "time": "2026-10-08T11:41:28+08:00",
               "run_dir": tmp_path / "2026-10-08/noon"},
              {"date": "2026-09-08", "time": "2026-09-08T12:20:00+08:00",
               "run_dir": tmp_path / "nope"}]
    assert bs.intraday_index_pcts(series) == {"2026-10-08": -0.27}


def test_starting_capital_baseline_is_always_in_range():
    # Zoomed ranges once scaled to visible data only, so a 20-day window
    # entirely below 1M dropped the 0% dashed line off the chart.
    js = bs.CHART_JS
    assert "es.push(STARTING);" in js
    assert "if (full) es.push(STARTING)" not in js


def _prices(tmp, rel, quotes):
    path = tmp / rel / "input" / "prices.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(quotes), encoding="utf-8")
    return tmp / rel


def test_holding_day_pct_from_own_runs_quote(tmp_path):
    run = _prices(tmp_path, "2026-10-08/noon", {
        "603259": {"date": "2026-10-08", "price": 165.95, "prev_close": 167.34},
        "601872": {"date": "2026-10-08", "price": 22.20, "prev_close": 20.15},   # not the mark
        "603127": {"date": "2026-09-30", "price": 52.88, "prev_close": 49.30}})  # other day
    series = [{"date": "2026-10-08", "run_dir": run, "holdings": [
        {"c": "603259", "px": 165.95}, {"c": "601872", "px": 22.17},
        {"c": "603127", "px": 52.88}, {"c": "000001", "px": 10.0}]}]
    bs.attach_holding_day_pcts(series)
    hs = series[0]["holdings"]
    assert hs[0]["d"] == -0.83
    assert [("d" in h) for h in hs[1:]] == [False, False, False]


def test_holding_flags_book_prev_price_that_is_not_the_quote_prev_close(tmp_path):
    # 2026-10-08 普洛药业 ex-dividend 10派1.39: book 27.74, quote prev_close 27.61.
    run = _prices(tmp_path, "2026-10-08/noon", {
        "000739": {"date": "2026-10-08", "price": 27.13, "prev_close": 27.61},
        "603259": {"date": "2026-10-08", "price": 165.95, "prev_close": 167.34}})
    def series(prev_date, prev_time):
        return [{"date": prev_date, "time": f"{prev_date}T{prev_time}+08:00", "holdings": [
                    {"c": "000739", "px": 27.74}, {"c": "603259", "px": 167.34}]},
                {"date": "2026-10-08", "run_dir": run, "holdings": [
                    {"c": "000739", "px": 27.13}, {"c": "603259", "px": 165.95}]}]
    sessions = {"2026-09-29": 1, "2026-09-30": 1, "2026-10-08": 1}

    s = series("2026-09-30", "15:10:22")
    bs.attach_holding_day_pcts(s, sessions)
    pulo, wuxi = s[1]["holdings"]
    assert pulo["d"] == -1.74 and pulo["xd"] == 27.74 and pulo["qp"] == 27.61
    assert "xd" not in wuxi

    # Not judged when yesterday's mark was a noon mark or not the prior session:
    # those differ from prev_close for ordinary reasons.
    for prev_date, prev_time in [("2026-09-30", "11:41:00"), ("2026-09-29", "15:10:00")]:
        s = series(prev_date, prev_time)
        bs.attach_holding_day_pcts(s, sessions)
        assert "xd" not in s[1]["holdings"][0] and s[1]["holdings"][0]["d"] == -1.74
