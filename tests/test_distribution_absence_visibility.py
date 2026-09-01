"""An absent limit-up/down distribution must never print as "0 / 0 measured".

Audit A5 / top-10 #8. Only CheeseForTune's breadth emits `distribution`; all
three fallback providers return bare {up,down,flat,total}. The old code did
`int(distribution.get("f10") or 0)` and then printed "<n> limit-ups /
<n> limit-downs" into the prompt AND the report — so on any CF outage the
`f10>=30` panic clause silently could never fire, and absence rendered as the
most bullish possible reading, AS IF MEASURED. All 40 August runs were
checked: 38 had distribution — the hole is real but latent, and CF sits in a
chain designed to degrade.

Contract: distribution present → numbers as before. Absent → the panic clause
runs on ratio alone, and the reason string SAYS the distribution was
unavailable instead of claiming zeros.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import run_daily


GREEN = {"上证指数": {"change_pct": 1.0}, "深证成指": {"change_pct": 1.0},
         "创业板指": {"change_pct": 1.0}}


def test_present_distribution_reports_real_numbers():
    r = run_daily.evaluate_new_entry_regime({
        "breadth": {"up": 3000, "down": 1000, "distribution": {"f10": 4, "r10": 78}},
        "indices": GREEN})
    assert "78 limit-ups / 4 limit-downs" in r["reason"]


def test_absent_distribution_is_named_not_zeroed():
    r = run_daily.evaluate_new_entry_regime({
        "breadth": {"up": 3000, "down": 1000},   # fallback-provider shape
        "indices": GREEN})
    assert "0 limit-ups" not in r["reason"], "absence rendered as a measurement"
    assert "distribution unavailable" in r["reason"]


def test_panic_still_fires_on_ratio_alone_without_distribution():
    r = run_daily.evaluate_new_entry_regime({
        "breadth": {"up": 500, "down": 4000},    # 0.125:1 — panic by ratio
        "indices": {}})
    assert r["allow_new_positions"] is False
    assert r["regime"] == "panic"


def test_panic_by_limit_downs_still_works_when_measured():
    r = run_daily.evaluate_new_entry_regime({
        "breadth": {"up": 2000, "down": 1900, "distribution": {"f10": 31, "r10": 5}},
        "indices": GREEN})
    assert r["allow_new_positions"] is False


# --- the same husk-shape in IV sentiment (feeds SIZING) ----------------------

def test_partial_iv_coverage_is_stamped_into_the_signal(monkeypatch):
    import fetch_iv_sentiment as iv

    def fake_rank(code, lookback=252):
        return ({"underlying": code, "iv_rank": 0.5, "iv_percentile": 0.5}
                if code in ("510050", "510300") else None)
    monkeypatch.setattr(iv, "fetch_iv_rank", fake_rank)
    out = iv.fetch_all()
    assert out["coverage"]["partial"] is True
    assert out["coverage"]["fetched"] == 2
    assert "覆盖不全" in out["overall_sentiment"]["signal"], (
        "a sizing input averaged over survivors without saying so")


def test_full_iv_coverage_keeps_the_clean_label(monkeypatch):
    import fetch_iv_sentiment as iv
    monkeypatch.setattr(iv, "fetch_iv_rank",
                        lambda code, lookback=252: {"underlying": code, "iv_rank": 0.5, "iv_percentile": 0.5})
    out = iv.fetch_all()
    assert out["coverage"]["partial"] is False
    assert "覆盖不全" not in out["overall_sentiment"]["signal"]
