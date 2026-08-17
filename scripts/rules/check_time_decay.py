#!/usr/bin/env python3
"""
Rule: Time decay — flag positions held >=15 trading days with <3% gain.
Created: 2026-03-03
Source: agents/ANALYST.md Rule 5 (the spec of record), LEARNINGS #1 (time_decay),
        #18 (catalyst exception), #19 (commodity 30d — RETIRED, see below),
        #20 (rebound-day delay)
Last modified: 2026-08-16
Track record: 3 fires, 2 correct, 1 incorrect
  - 600988 赤峰黄金: fired 02-27 (24d, +0.50%) → SOLD → 03-02 涨停+10% ❌ (missed +9.89pp)
  - 688002 睿创微纳: fired 03-04 (21d, -4.76%) → SOLD correctly ✅ (突破失败+动能逆转)
  - 300684 中石科技: approaching threshold (18d on 03-06, -4.37%) → pending

Evolution notes (2026-03-06):
  - Added commodity/event-driven 30-day threshold (LEARNINGS #19)
  - Added momentum-reversal check: if PnL was recently positive and turned negative
    in last 3 days (like 睿创微纳 120→109), that's a STRONGER sell signal
  - Added rebound-day exception (LEARNINGS #20): if trigger day the stock is up >2%
    AND PnL just turned positive, delay 2 days
  - Removed: no longer just a binary fire/not-fire. Now provides severity levels:
    SELL (strong), REVIEW (catalyst exception may apply), INFO (approaching threshold)

Evolution notes (2026-08-16) — reconciled with the spec after the first weekly audit:
  - 20d/<5% → **10d/<3%**. ANALYST.md Rule 5 has mandated 10d/<3% for months
    ("V1 used 20 days — too slow"); this file was never updated, so the tightening
    lived in the spec with no mechanical backstop. In 54 closed trades the engine
    never once flagged time decay inside the spec's window — the only 4 time-stop
    exits were the LLM's own discretionary calls at 9-16 days.
  - Replay of all 12 trades ever held >=10 sessions: the spec threshold fires on 9
    for **+8.73pp net (+0.97pp/trade)** and touches NONE of the three big winners
    (新宙邦 +11.8%, 上海新阳 +29.8%, 路维光电 +30.9% — all were >+3% at day 10, so
    they never qualify). Catastrophes caught: 科陆电子 +2.36pp, 中石科技 +3.97pp,
    睿创微纳 +5.07pp. Costs: 赤峰黄金 -1.96pp, 恒铭达 -1.70pp.
  - **Commodity 30d grace REMOVED.** ANALYST.md Rule 5 is explicit: "No
    'event-driven exceptions' to time stops. If the event hasn't moved the stock
    in 10 days, your timing is wrong. You can always re-enter." LEARNINGS #19
    (黄金股事件驱动型分类) is superseded by that line. Evidence is thin but points
    the same way: over the two affected trades the carve-out was worth -0.51pp
    (赤峰黄金 -1.96pp saved vs 云天化 +2.47pp lost). `is_commodity` is still
    reported in the payload for post-hoc analysis; it no longer changes behaviour.
  - Fires AT the threshold, not one day past it. The old `> threshold` test meant a
    "20-day" rule actually fired on day 21, and the INFO branch's `<=` swallowed the
    boundary day entirely. At a 10-day threshold that off-by-one is 10% of the window.
  - Trading days are now counted as actual weekdays rather than `calendar * 5 // 7`.
    (Threshold below was 10 for one day; see the 08-17 note.)
    The ratio drifts by up to a day depending on which weekday you entered on —
    tolerable against 20, not against 10. Public holidays still inflate the count
    slightly (no exchange calendar here, and every other rule in this directory is
    pure stdin/stdout with no DB access — keeping that contract), so the rule can
    fire up to ~1 session early around 春节/国庆. It errs toward exiting sooner,
    which is the direction Rule 5 wants.

Evolution notes (2026-08-17) — 10d lasted one day; measured, then corrected to 15d:
  - docs/audits/EXIT_ABLATION.md replayed every real entry under five time-stop
    variants at horizons 20/30/40. 10d/<3% was the WORST at all three: 1.1-1.8pp
    behind having no time stop, 1.5-2.2pp behind the 20d/<5% it had replaced.
  - The damage is in the days, not the gain bar. Holding days fixed, 3%→5% moves
    the result by <=0.7pp; holding the bar fixed, 10d→15d moves it by 1.9-2.4pp.
    Ten sessions does not give this book's momentum time to express.
  - The 08-16 counterfactual that justified 10d was conditioned on trades that had
    already survived 10 sessions without being stopped — a sample selected for the
    outcome it measured. The ablation applies each policy to every entry uniformly.
  - 15d/<3% chosen (owner decision): best or near-best at h=20 and h=30, and keeps
    the spec's intent that 20 sessions is too patient. ANALYST.md Rule 5 updated to
    match — the spec moved to the evidence, not the other way round.
  - Unaffected by the twice-daily execution problem: this rule triggers on a DATE,
    not a price, so it needs no intraday precision. The price-triggered rules
    (-5% hard, -3%/3d) do — see docs/audits/EXIT_ABLATION.md caveats.
"""
import json
import sys
from datetime import datetime, date, timedelta

data = json.load(sys.stdin)
today = date.today()
violations = []

# agents/ANALYST.md Rule 5. Keep these in sync with the spec and with
# scripts/backtest.py's time_decay_days / time_decay_min_gain.
THRESHOLD_DAYS = 15
MIN_GAIN_PCT = 3.0
WARN_WINDOW = 3          # INFO from day 12 through day 14

# Retained for reporting only — no longer alters the threshold (see 08-16 notes).
COMMODITY_KEYWORDS = ["化工", "黄金", "有色", "煤炭", "石油", "磷", "钾", "稀土", "矿"]


def trading_days_between(entry: date, today: date) -> int:
    """Weekdays elapsed since entry, entry day excluded (day 1 = next session).

    Exchange holidays are not modelled — see the 2026-08-16 note in the module
    docstring for why, and which way it biases.
    """
    days = 0
    d = entry
    while d < today:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


for p in data.get("activePositions", []):
    entry = datetime.strptime(p["entryDate"], "%Y-%m-%d").date()
    trading_days = trading_days_between(entry, today)

    pnl = p.get("pnl_pct", 0)
    sector = p.get("sector", "").lower()

    is_commodity = any(k in sector for k in COMMODITY_KEYWORDS)
    threshold = THRESHOLD_DAYS

    # Pre-threshold warning (the WARN_WINDOW days before the threshold)
    if threshold - WARN_WINDOW <= trading_days < threshold and pnl < MIN_GAIN_PCT:
        violations.append({
            "code": p["code"],
            "name": p["name"],
            "rule": "time_decay",
            "severity": "INFO",
            "trading_days": trading_days,
            "threshold": threshold,
            "pnl_pct": pnl,
            "is_commodity": is_commodity,
            "suggestion": (
                f"APPROACHING threshold — {trading_days}/{threshold} trading days, "
                f"PnL={pnl:.1f}%. Will trigger in {threshold - trading_days} days "
                f"unless PnL reaches {MIN_GAIN_PCT:.0f}%. Prepare exit plan — note that "
                f"Rule 5 allows no event-driven exception, so plan the exit, not a case for it."
            ),
        })
        continue

    if trading_days < threshold:
        continue

    if pnl >= MIN_GAIN_PCT:
        continue

    # At/beyond threshold with <MIN_GAIN_PCT gain — determine severity
    severity = "SELL"
    suggestion_extra = ""

    # Check for momentum reversal (stronger sell signal)
    # If PnL was recently positive but now negative, trend is worsening
    if pnl < 0:
        severity = "SELL"
        suggestion_extra = " PnL is negative — momentum has reversed, prioritize exit."

    # Note about rebound-day exception (LEARNINGS #20)
    # We can't check today's intraday change from positions.json alone,
    # but we flag the rule so the human/tracker can check
    if 0 < pnl < 2:
        severity = "REVIEW"
        suggestion_extra = (
            " PnL slightly positive — check if today's stock is rebounding (>2% intraday gain). "
            "If yes AND PnL just turned positive from negative, delay 2 trading days (LEARNINGS #20)."
        )

    violations.append({
        "code": p["code"],
        "name": p["name"],
        "rule": "time_decay",
        "severity": severity,
        "trading_days": trading_days,
        "threshold": threshold,
        "pnl_pct": pnl,
        "is_commodity": is_commodity,
        "suggestion": (
            f"{severity} — held {trading_days} trading days (threshold: {threshold}d) "
            f"with PnL={pnl:.1f}% (<{MIN_GAIN_PCT:.0f}%).{suggestion_extra}"
        ),
    })

result = {
    "rule": "time_decay",
    "status": "ok" if not violations else "violations",
    "violations": violations,
}
json.dump(result, sys.stdout, ensure_ascii=False)
sys.exit(1 if violations else 0)
