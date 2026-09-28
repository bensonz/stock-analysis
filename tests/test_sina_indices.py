"""data_collector._parse_sina_index_quotes — the sina index fallback.

Pinned because the short `s_` format carried no date, so every quote was
stamped datetime.now(): the 2026-09-25 (Mid-Autumn) holiday run recorded
09-24's close as a 09-25 bar. The full format carries the quote's own date.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import data_collector as dc

# Real response captured 2026-09-28 16:20 (post-close, -1.67% session).
_SH = ('var hq_str_sh000001="上证指数,3878.4088,3888.3738,3823.6206,3878.4088,'
       '3806.6708,0,0,452350675,804543704708,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,'
       '0,0,0,0,2026-09-28,16:19:58,00,";')
_CYB = ('var hq_str_sz399006="创业板指,3267.602,3288.948,3139.825,3270.810,'
        '3125.201,0.000,0.000,15016674360,430380130159.200,0,0.000,0,0.000,0,'
        '0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,'
        '2026-09-28,15:00:03,00";')


def test_quote_carries_its_own_date_not_the_clock():
    out = dc._parse_sina_index_quotes(_SH)
    assert out["上证指数"] == {"code": "sh000001", "close": 3823.621,
                              "change_pct": -1.67, "date": "2026-09-28"}


def test_parses_every_known_index_line():
    out = dc._parse_sina_index_quotes(_SH + "\n" + _CYB)
    assert out["创业板指"]["close"] == 3139.825
    assert out["创业板指"]["change_pct"] == -4.53


def test_skips_empty_or_truncated_lines():
    assert dc._parse_sina_index_quotes('var hq_str_sh000001="";') == {}
    assert dc._parse_sina_index_quotes('var hq_str_sh000001="上证指数,1,2,3";') == {}
    assert dc._parse_sina_index_quotes('var hq_str_sh600000="浦发银行,1,2";') == {}
