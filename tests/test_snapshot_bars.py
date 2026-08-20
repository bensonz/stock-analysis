"""Sina real-time quote feed → today's settled daily bar.

Validated 2026-08-20 against the full kline-sourced day already in the DB:
5,204 bars vs 5,204 rows, **0 OHLC mismatches**, volume off by one lot on 4.2%
(max relative error 0.0164%), and neither source held a stock the other missed.

The trap these tests exist for: the feed reports 股 (shares) while
`daily_prices` stores 手 (100-share lots). An earlier spot-check compared the
feed against *akshare klines* — also shares — so it agreed, and would have
shipped a writer that wrote every volume 100x too large, quietly wrecking
mavol30 and check_volume_below_mavol30 while prices looked perfect.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import snapshot_bars as sb

DAY = "2026-08-20"


def line(code="600000", name="浦发银行", o="9.03", price="9.11", high="9.14",
         low="8.98", vol="45729665", amount="4.1e8", date=DAY, time="15:34:59",
         pad_to=33):
    f = [""] * 33
    f[sb.F_NAME], f[sb.F_OPEN], f[sb.F_PREV_CLOSE] = name, o, "9.05"
    f[sb.F_PRICE], f[sb.F_HIGH], f[sb.F_LOW] = price, high, low
    f[sb.F_VOLUME], f[sb.F_AMOUNT] = vol, amount
    f[sb.F_DATE], f[sb.F_TIME] = date, time
    f = f[:pad_to]                       # pad_to<32 simulates a truncated line
    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    return f'var hq_str_{prefix}{code}="{",".join(f)}";'


# ── symbol mapping ──

def test_symbol_prefixes_by_exchange():
    assert sb.sina_symbol("600000") == "sh600000"
    assert sb.sina_symbol("688222") == "sh688222"
    assert sb.sina_symbol("000001") == "sz000001"
    assert sb.sina_symbol("300750") == "sz300750"
    assert sb.sina_symbol("688222.SH") == "sh688222"      # suffix tolerated


def test_bj_codes_are_unsupported_not_broken():
    """BJ isn't on this feed. Already read as factor 1.0 — absence is status quo."""
    for code in ("430047", "830799", "920059"):
        assert sb.sina_symbol(code) is None


def test_malformed_codes_are_rejected():
    for code in ("", "60000", "6000000", "ABCDEF", None):
        assert sb.sina_symbol(code) is None


# ── the volume unit, i.e. the bug this nearly shipped ──

def test_volume_is_converted_shares_to_lots():
    row = sb.parse_quote_line(line(vol="45729665"), DAY)
    assert row[6] == 457296, "feed gives 股; daily_prices stores 手 — must floor(/100)"


def test_volume_floors_rather_than_rounds():
    # 382/400 of the archive's values matched floor, not round
    assert sb.parse_quote_line(line(vol="1531876"), DAY)[6] == 15318


def test_ohlc_passes_through_untouched():
    row = sb.parse_quote_line(line(o="9.03", high="9.14", low="8.98", price="9.11"), DAY)
    code, date, o, h, low, c, vol, amt = row
    assert (code, date) == ("600000", DAY)
    assert (o, h, low, c) == (9.03, 9.14, 8.98, 9.11)


# ── guards: reject, never guess ──

def test_stale_date_is_rejected():
    """A suspended stock keeps serving its last session's line."""
    assert sb.parse_quote_line(line(date="2026-08-19"), DAY) is None


def test_zero_volume_is_rejected():
    assert sb.parse_quote_line(line(vol="0"), DAY) is None


def test_zero_price_is_rejected():
    assert sb.parse_quote_line(line(price="0.000"), DAY) is None
    assert sb.parse_quote_line(line(o="0.000"), DAY) is None


def test_sub_lot_volume_is_rejected_not_written_as_zero():
    """99 shares floors to 0 lots — must not land as a zero-volume bar."""
    assert sb.parse_quote_line(line(vol="99"), DAY) is None


def test_incoherent_bar_is_rejected():
    # close above the high / low above the open — do not trust the line
    assert sb.parse_quote_line(line(price="99.0"), DAY) is None
    assert sb.parse_quote_line(line(low="9.99"), DAY) is None


def test_truncated_or_unparseable_lines_are_rejected():
    assert sb.parse_quote_line(line(pad_to=10), DAY) is None
    assert sb.parse_quote_line('var hq_str_sh600000="";', DAY) is None
    assert sb.parse_quote_line("garbage", DAY) is None
    assert sb.parse_quote_line("", DAY) is None


def test_non_numeric_fields_are_rejected():
    assert sb.parse_quote_line(line(price="N/A"), DAY) is None


# ── batching + failure isolation ──

class _Resp:
    def __init__(self, text):
        self.text, self.encoding = text, "gbk"


class _Session:
    def __init__(self, behaviour):
        self.behaviour, self.calls = behaviour, []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        out = self.behaviour(len(self.calls) - 1)
        if isinstance(out, Exception):
            raise out
        return _Resp(out)


def test_codes_are_batched_not_fetched_one_by_one():
    codes = [f"60{i:04d}" for i in range(250)]
    sess = _Session(lambda i: line())
    _rows, stats = sb.fetch_snapshot_bars(codes, DAY, session=sess, batch_size=100)
    assert len(sess.calls) == 3          # 250 codes → 3 requests, not 250
    assert stats["supported"] == 250


def test_a_failed_batch_costs_its_codes_not_the_run():
    sess = _Session(lambda i: RuntimeError("timeout") if i == 0 else line())
    rows, stats = sb.fetch_snapshot_bars(
        [f"60{i:04d}" for i in range(200)], DAY, session=sess, batch_size=100)
    assert stats["failed_batches"] == 1
    assert rows, "the surviving batch must still produce rows"


def test_stats_report_rejections_rather_than_swallowing_them():
    sess = _Session(lambda i: line() + "\n" + line(code="600001", date="2026-08-19"))
    _rows, stats = sb.fetch_snapshot_bars(["600000", "600001"], DAY, session=sess)
    assert stats["rejected"] == 1        # the stale line, counted not hidden


def test_unsupported_codes_are_counted_separately():
    sess = _Session(lambda i: line())
    _rows, stats = sb.fetch_snapshot_bars(["600000", "830799", "920059"], DAY, session=sess)
    assert stats["skipped_unsupported"] == 2
