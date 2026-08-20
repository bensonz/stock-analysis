"""A-share exchange mechanics — one definition, shared by live and research.

These are the exchange's rules, not our strategy's. They belong in one place
because a divergence between the live pipeline and the backtest means the
research arm is measuring a market we don't trade in.

2026-08-20: `backtest.py` had `board_limit()` (correct: main 10 / ChiNext+STAR
20 / BJ 30) while `run_daily.py` hardcoded `change_pct >= 9.8` for every board.
成都先导 688222 rose 13.17% — comfortably inside STAR's 20% band and freely
tradable — and the live pipeline refused it as 涨停. Same shape as the time-stop
divergence: the correct number existed, in the wrong module.
"""


def _six(code) -> str:
    return str(code).split(".")[0].strip()


def is_star(code) -> bool:
    """科创板 — 688/689."""
    return _six(code).startswith("68")


def is_chinext(code) -> bool:
    """创业板 — 300/301."""
    return _six(code).startswith("30")


def is_bj(code) -> bool:
    """北交所 — 43x/83x/87x/88x/92x."""
    return _six(code).startswith(("4", "8", "92"))


def is_st(name) -> bool:
    """ST / *ST / S*ST — narrower band on the main board."""
    n = str(name or "").upper().replace(" ", "")
    return "ST" in n


def price_limit_pct(code, name=None) -> float:
    """Daily price-limit band in PERCENT (10.0 / 20.0 / 30.0 / 5.0).

    Boards: main 10%, ChiNext+STAR 20%, BJ 30%.
    ST names are capped at 5% — but only on the main board: the
    registration-system boards (ChiNext/STAR) keep their 20% band for ST
    issues, and BJ keeps 30%.

    `name` is optional. Omitting it returns the board limit, which is the
    permissive answer — callers that can supply a name should, or an ST stock
    at +6% reads as tradable when the exchange has already frozen it.
    """
    if is_bj(code):
        return 30.0
    if is_star(code) or is_chinext(code):
        return 20.0
    return 5.0 if is_st(name) else 10.0


# Prices print to 0.01, so a stock sitting at its cap can round a hair under
# the exact band. Treat "within this margin of the cap" as locked.
LIMIT_TOLERANCE_PCT = 0.2


def at_limit_up(change_pct, code, name=None) -> bool:
    """True if the stock is locked at its upper limit — cannot be bought."""
    if change_pct is None:
        return False
    return float(change_pct) >= price_limit_pct(code, name) - LIMIT_TOLERANCE_PCT


def at_limit_down(change_pct, code, name=None) -> bool:
    """True if the stock is locked at its lower limit — cannot be sold.

    Not yet enforced on the live sell path (2026-08-20); see docs/HARNESS TODO.
    Booking an exit at limit-down records a fill that reality would not have
    given us, which flatters every stop-loss statistic.
    """
    if change_pct is None:
        return False
    return float(change_pct) <= -(price_limit_pct(code, name) - LIMIT_TOLERANCE_PCT)
