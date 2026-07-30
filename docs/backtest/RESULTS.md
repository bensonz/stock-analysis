# Backtest Stage-1 Results — Mechanical ANALYST.md, 2024-12 → 2026-07-29

Run: `python3 scripts/backtest.py baseline` @ `80df134`, adjusted prices,
costs on (0.30% round trip), T+1 + price-limit constraints modeled.
**Framing reminder: one market regime, ~130 tradeable sessions. This run can
reject the ruleset for this regime; it cannot validate any ruleset in general.**

## The verdict

**Mechanically executed, ANALYST.md's rules lost -29.0% (net) over Jan–Jul
2026, while an equal-weight market proxy lost -14.9% over the same span.**
The rules did twice as badly as the falling market they traded in. The live
portfolio's actual -5.9% over the same period beat the mechanical baseline by
23 points — the LLM/pipeline's *selectivity and cash discipline* (few entries,
high cash, weak-market blocks) has been worth a lot; the entry/exit rules
themselves, run at full permitted deployment, are the bleed.

| Metric | Value |
|---|---|
| Total return (net) | **-28.98%** |
| Max drawdown | 29.14% |
| Trades closed | 148 (median hold: 2 sessions) |
| Win rate | **8.1%** |
| Avg win / avg loss | +2.67% / **-8.44%** |
| Exit reasons | 100 hard-stop, 40 early-stop, 8 time-decay |
| EW market proxy, same span | -14.89% |
| Open at window end | 8 positions (marked in equity) |

Equity (monthly closes): 1.000 through 2025 (gate warm-up needs 250 sessions —
no signals), then 0.963 (Jan) → 0.942 (Feb) → 0.900 (Mar) → 0.864 (May) →
0.880 (Jun) → **0.710 (Jul 29)**. July alone cost ~17 points — consistent with
the pool-wide 97%/97%/80% stopout days measured mid-July.

## Why it bleeds (mechanics, not mystery)

1. **A -5% stop realizes ≈ -8.4% on average.** Stops evaluate at the close
   that breaches, gaps blow through the level, and limit-down closes defer the
   fill a day (all also true live: 中国巨石 recorded -5.91%). The stop
   controls *when* you lose, not *how much*.
2. **8% win rate with wins capped small.** Buying RPS leaders in a falling
   tape mean-reverts against the entry almost immediately; median hold 2 days
   means most positions never saw a chance.
3. **The revolving door.** Slots refill the day after a stop — the ruleset
   re-buys the same falling class relentlessly (148 trades in ~130 sessions).
   The live pipeline's cadence (few entries/day, regime blocks) is an implicit
   throttle the written rules don't contain.

## Fidelity (is the simulator believable?)

Replay of the 41 actual closed trades through the same fill+cost model
(`python3 scripts/backtest.py replay`):

- 20 replayable; **mean |model residual| = 0.30pp** after fill-timing
  attribution — and that residual ≈ the cost load recorded gross returns
  omit. The cost/adjustment model is sound.
- Headline per-trade diff 2.23pp is intraday fill timing: live entries sit on
  average **2.53%** away from the day's open (chasing both directions);
  exits only 0.86pp (both near close).
- **21 of 41 trades unreplayable** — dates fall on dropped partial-coverage
  days. The pricedb gap-repair backlog now has a measured cost.

## What Stage 2 should test first (each = one config diff now)

1. **Entry cooldown / pool-pain throttle** — halve or zero new entries when
   >30–60% of the gate pool fell ≥3% in 2 sessions (measured 55% forward stop
   rate in that state). Directly attacks the revolving door.
2. **Wider stop × smaller size** — same risk per trade, fewer whipsaws;
   the -5%-close stop realizing -8.4% is the worst of both.
3. **Pullback entries vs strength entries** — the 15–30% pool-pain bucket was
   the only state with positive forward expectancy (+1.7% med 5d).
4. **Deployment discipline as a rule** — the live system's outperformance of
   its own ruleset suggests encoding "few entries, high cash floor" explicitly
   rather than leaving it to LLM mood.

## Caveats

Single regime (2026 downtrend/chop); no intraday data (close-based stops);
no liquidity/impact model; EW proxy ≠ investable benchmark; 100-share lots
and ST 5% limits unmodeled. All conclusions are rejections, not validations.
