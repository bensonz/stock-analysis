"""The evaluation epoch: the first day whose trades judge the CURRENT system.

Owner decision 2026-10-01: picks and trades before 2026-07-23 came from an
earlier, retired system and must not be used to evaluate this one — not in
win rates, drift research, base rates or weekly-audit totals. The complete
self-evolving agent dates from here, and the record agrees: the RPS gate and
Rule 2b were rewritten 2026-07-22 (5dffbb4, f65cd97), and adjustment factors
did not exist until 2026-07-24 (e1845cb) — RPS before that ran on unadjusted
prices, so an ex-dividend drop read as a loss.

Scope is EVALUATION only. Price history, RPS/MA250 windows, the portfolio book
in tracking/ and the doctor's audit trail all keep their full history.
"""

EVALUATION_EPOCH = "2026-07-23"
