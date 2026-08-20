"""A-share price-limit bands — the rule the live pipeline didn't have.

2026-08-20: run_daily hardcoded `change_pct >= 9.8` for every board, so
成都先导 688222 at +13.17% was refused as 涨停 while sitting 7 points inside
STAR's 20% band. backtest.py had `board_limit()` right the whole time; the
correct number existed in the wrong module. Both now share market_rules.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import backtest
import market_rules as m


def test_bands_by_board():
    assert m.price_limit_pct("600000") == 10.0     # 主板 SH
    assert m.price_limit_pct("000001") == 10.0     # 主板 SZ
    assert m.price_limit_pct("002415") == 10.0     # 中小板 → 主板
    assert m.price_limit_pct("300750") == 20.0     # 创业板
    assert m.price_limit_pct("301707") == 20.0     # 创业板 (301)
    assert m.price_limit_pct("688222") == 20.0     # 科创板
    assert m.price_limit_pct("689009") == 20.0     # 科创板 CDR
    assert m.price_limit_pct("830799") == 30.0     # 北交所
    assert m.price_limit_pct("430047") == 30.0     # 北交所
    assert m.price_limit_pct("920059") == 30.0     # 北交所 (920)


def test_st_narrows_only_on_the_main_board():
    assert m.price_limit_pct("600000", "*ST国华") == 5.0
    assert m.price_limit_pct("000004", "ST某某") == 5.0
    # registration-system boards keep their band for ST issues
    assert m.price_limit_pct("300750", "ST测试") == 20.0
    assert m.price_limit_pct("688222", "*ST测试") == 20.0
    assert m.price_limit_pct("830799", "ST测试") == 30.0
    # a name that merely contains no ST marker is untouched
    assert m.price_limit_pct("600000", "浦发银行") == 10.0


def test_the_688222_regression():
    """The exact trade the old `>= 9.8` rule refused."""
    assert m.at_limit_up(13.17, "688222") is False
    assert m.at_limit_up(19.9, "688222") is True       # actually locked
    assert m.at_limit_up(9.9, "600000") is True        # main board still caught


def test_limit_down_mirrors_the_band():
    assert m.at_limit_down(-9.9, "600000") is True
    assert m.at_limit_down(-13.17, "688222") is False  # inside STAR's band
    assert m.at_limit_down(-19.9, "688222") is True
    assert m.at_limit_down(-29.9, "830799") is True


def test_missing_change_is_not_a_limit():
    # unknown must never read as "locked" — that would silently block trades
    assert m.at_limit_up(None, "600000") is False
    assert m.at_limit_down(None, "600000") is False


def test_suffixed_codes_are_handled():
    assert m.price_limit_pct("688222.SH") == 20.0
    assert m.price_limit_pct("830799.BJ") == 30.0


def test_backtest_shares_the_same_definition():
    """The research arm must measure the market we actually trade."""
    for code in ("600000", "300750", "688222", "830799", "920059"):
        assert backtest.board_limit(code) == m.price_limit_pct(code) / 100.0
