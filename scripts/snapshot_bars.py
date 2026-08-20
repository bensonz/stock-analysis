"""Today's settled daily bar, from Sina's real-time quote feed.

Sina runs two independent systems and they publish on very different schedules:

- ``quotes.sina.cn`` — the daily-kline **archive**, built by a batch job that
  runs after the close. On 2026-08-20 it still had not published most stocks at
  16:37; it was complete by ~21:47.
- ``hq.sinajs.cn`` — the real-time **quote feed**. It streams ticks during the
  session and simply stops updating when trading ends, so the day's final
  values are readable minutes after the close. No batch job involved.

With eastmoney (which akshare fronts) connection-dead, the archive was the only
path to today's bar, and it arrives ~6 hours too late for a 15:05 run. Two
afternoon runs died on this in two days, each needing a manual evening heal.

This module reads the day off the quote feed instead. Validated 2026-08-20
against 400 kline-sourced rows already in the DB:

    OHLC identical ......................... 400/400
    volume == floor(shares/100) ............ 382/400
    the other 18 ........................... off by exactly one lot,
                                             max relative error 0.0065%

**The volume unit is the trap.** The feed reports 股 (shares); ``daily_prices``
stores 手 (100-share lots). An earlier 10-code check compared the feed against
*akshare klines* — both in shares — so it agreed, and would have shipped a
writer that wrote every volume 100x too large. That feeds ``mavol30`` and
``check_volume_below_mavol30``, so the volume rule would have gone quietly
insane while prices looked perfect. Compare against what you STORE, not against
another copy of the same source.

Scope: this writes today's bar only. It is not a replacement for the kline
archive, which remains the source for history, backfill of missed days, new
listings, factor derivation (raw + hfq series), and — deliberately — the
independent cross-check on what this writer produced.
"""
import re
import sys
from datetime import datetime

SINA_QUOTE_URL = "http://hq.sinajs.cn/list="
SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}
BATCH_SIZE = 100          # codes per request; the feed accepts many
SHARES_PER_LOT = 100      # 股 → 手

# The feed stamps each line with the last time it updated (field 31). The
# closing auction runs 14:57–15:00, so a line stamped before 15:00 does NOT
# carry the settled close — it is the last intraday print. The afternoon run
# fires at 15:05, minutes after the auction, so this is the difference between
# writing the close and writing whatever traded just before it.
# A stock halted mid-session keeps an early stamp; rejecting it costs one bar
# and is the honest outcome (reject, never guess).
SETTLE_AFTER = "15:00:00"

# Field offsets in the comma-separated quote line.
F_NAME, F_OPEN, F_PREV_CLOSE, F_PRICE = 0, 1, 2, 3
F_HIGH, F_LOW, F_VOLUME, F_AMOUNT = 4, 5, 8, 9
F_DATE, F_TIME = 30, 31
MIN_FIELDS = 32

_LINE_RE = re.compile(r'var hq_str_[a-z]{2}(\d+)="(.*)";')


def sina_symbol(code: str) -> str | None:
    """Prefixed symbol for the quote feed, or None if unsupported.

    BJ codes (43x/83x/87x/92x) are not carried by this feed. They are already
    the permanently-unfactored set the adjustment layer reads as 1.0, so a
    missing bar here is the status quo, not a regression.
    """
    c = str(code).split(".")[0].strip()
    if not c.isdigit() or len(c) != 6:
        return None
    if c.startswith(("4", "8", "92")):
        return None
    return ("sh" if c.startswith(("6", "9")) else "sz") + c


def parse_quote_line(line: str, expect_date: str) -> tuple | None:
    """One quote line → a daily_prices row, or None if it must not be written.

    Rejects rather than guesses. A suspended stock keeps returning its last
    session's line with zero volume; writing that stamped as today would be
    worse than a missing row, because it looks like real trading.
    """
    m = _LINE_RE.match(line.strip())
    if not m:
        return None
    code, fields = m.group(1), m.group(2).split(",")
    if len(fields) < MIN_FIELDS:
        return None

    # The feed's own date must be the session we asked for. This is the guard
    # against stale lines for suspended names.
    if fields[F_DATE].strip() != expect_date:
        return None

    # ...and its own timestamp must be at/after the close, or the "close" we
    # would store is really a pre-auction intraday print.
    if fields[F_TIME].strip() < SETTLE_AFTER:
        return None

    try:
        o = float(fields[F_OPEN])
        h = float(fields[F_HIGH])
        low = float(fields[F_LOW])
        c = float(fields[F_PRICE])
        vol_shares = float(fields[F_VOLUME])
        amount = float(fields[F_AMOUNT]) if fields[F_AMOUNT] else None
    except (ValueError, IndexError):
        return None

    if min(o, h, low, c) <= 0 or vol_shares <= 0:
        return None                      # suspended / no trade
    if not (low <= min(o, c) and max(o, c) <= h):
        return None                      # incoherent bar, do not trust it

    # 股 → 手. floor, matching what the kline archive stores (382/400 exact;
    # the rest differ by one lot from sub-lot rounding at source).
    volume = int(vol_shares // SHARES_PER_LOT)
    if volume <= 0:
        return None
    return (code, expect_date, o, h, low, c, volume, amount)


def fetch_snapshot_bars(codes, expect_date: str, session=None,
                        batch_size: int = BATCH_SIZE, progress=None):
    """Fetch today's bar for `codes`. Returns (rows, stats).

    Network failures are per-batch and non-fatal: a batch that fails costs its
    codes, not the run, and the count is reported rather than swallowed.
    """
    import requests
    session = session or requests
    symbols = [(c, sina_symbol(c)) for c in codes]
    supported = [(c, s) for c, s in symbols if s]
    rows, failed_batches, unparsed = [], 0, 0

    for i in range(0, len(supported), batch_size):
        chunk = supported[i:i + batch_size]
        try:
            resp = session.get(SINA_QUOTE_URL + ",".join(s for _c, s in chunk),
                               headers=SINA_HEADERS, timeout=20)
            resp.encoding = "gbk"
            text = resp.text
        except Exception as e:
            failed_batches += 1
            print(f"  [snapshot] batch {i // batch_size + 1} failed: "
                  f"{type(e).__name__}: {str(e)[:80]}", file=sys.stderr)
            continue
        for line in text.strip().split("\n"):
            row = parse_quote_line(line, expect_date)
            if row:
                rows.append(row)
            elif line.strip():
                unparsed += 1
        if progress:
            progress(min(i + batch_size, len(supported)), len(supported), len(rows))

    return rows, {
        "requested": len(codes),
        "supported": len(supported),
        "skipped_unsupported": len(codes) - len(supported),   # BJ etc.
        "rows": len(rows),
        "rejected": unparsed,          # suspended, stale date, incoherent
        "failed_batches": failed_batches,
    }
