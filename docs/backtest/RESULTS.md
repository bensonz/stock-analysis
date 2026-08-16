# Backtest Stage-1 Results — Mechanical ANALYST.md, 2024-12 → 2026-07-29

> **Stale as of 2026-08-16.** Every number below was produced with
> `time_decay_days=20, time_decay_min_gain=5.0` — V1's time stop, which the
> mechanical arm still carried long after ANALYST.md Rule 5 moved to 10d/<3%.
> The defaults are now 10/3.0, so this run no longer describes the ruleset the
> code implements. Re-run `backtest.py baseline` before citing these figures;
> the time stop was the arm's most-fired exit, so the effect is unlikely to be
> small. The qualitative finding (mechanical execution badly underperforms the
> live pipeline's selectivity) is not in doubt, only the magnitudes.

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

## Stage 2 — experiment matrix (run 2026-07-30, `backtest.py compare`)

| experiment | return% | maxDD% | trades | win% | avg win/loss | med hold |
|---|---|---|---|---|---|---|
| baseline | -28.98 | 29.14 | 148 | 8.1 | +2.67 / -8.44 | 2 |
| pool_pain (halve@30, block@60) | -20.64 | 20.82 | 142 | 7.8 | +2.10 / -8.27 | 2 |
| wide_stop (-10% @ 1.5% size) | -12.09 | 12.19 | 89 | 12.4 | +2.25 / -11.57 | 3 |
| pullback (dist_ma10 ∈ [-3,+3]) | **-8.92** | 23.64 | 81 | 7.4 | +3.90 / -7.95 | 2 |
| disciplined (≤2/day, 70% cash) | -24.74 | 24.79 | 126 | 10.3 | +2.99 / -8.64 | 2 |
| combo (all of the above) | **-2.48** | **10.60** | 51 | 11.8 | +3.44 / -12.00 | 4 |

(EW market proxy over the same tradeable span: -14.89%. Cash: 0%.)

**Readings:**

1. **Every single lever helps; the two biggest are the ones that fight the
   whipsaw directly.** Wider-stop-smaller-size (+17pp vs baseline) stops the
   -5%-close stop from being pure churn; pullback entries (+20pp) stop buying
   the tops of intraday strength. The entry-budget/cash-floor alone barely
   helps (-24.7) — *when* you buy matters more than *how much*.
2. **Combo is near-flat (-2.5%, maxDD 10.6%) in a tape where the market lost
   14.9%** — a 26.5pp improvement over the written rules. Note what combo
   actually is: half-size, wide stops, only on pullbacks, only when the pool
   isn't bleeding, max 2/day, 70% cash floor. In other words: *mostly don't
   trade.* 51 trades in 7 months.
3. **Nothing beat cash.** No tested configuration had positive absolute
   return in this regime. The honest summary of 2026 so far: the best
   momentum strategy was standing aside, and the best tested variant is the
   one that most closely approximates that.

**⚠️ In-sample warning — do not ship these numbers into ANALYST.md as
"proven".** The knob values (pain 30/60, band ±3%, -10% stop) were chosen
FROM studies on this same sample, and combo compounds five tuned choices.
These are *hypotheses that survived their first test*, ranked for out-of-
sample validation — the forward test is the live pipeline watching these
signals in read-only mode for a few weeks, or new data as the DB grows.

## Selection audit — rank-IC of the picker (run 2026-07-31)

Question: within the ~500 gate-passing stocks each day, does sorting by RPS60
(our picker) predict which do better? Daily Spearman rank-IC vs forward
returns, 86 pool-days:

| signal | horizon | mean IC | %days IC>0 | top-vs-bottom decile |
|---|---|---|---|---|
| rps60 | 5d | **-0.063** | 36% | **-1.10pp** |
| rps60 | 10d | -0.068 | 35% | -1.55pp |
| rps120 | 5d | -0.035 | 45% | -1.06pp |
| rps20 | 5d | -0.045 | 42% | -0.59pp |
| dist_ma10 | 5d | +0.005 | 54% | +2.20pp (nonlinear: deep-below-MA10 worst) |

**The picker is not weak — it is inverted.** |IC| 0.06 is a genuinely strong
cross-sectional signal (funds trade +0.03); ours points backwards in this
regime: the hottest names in an already-hot pool were systematically the
worst buys. Harness confirmation (one line changed — rank ascending):

| run | return | maxDD | trades | win% |
|---|---|---|---|---|
| baseline | -28.98% | 29.1% | 148 | 8.1 |
| baseline, inverted rank | **-3.47%** | 18.2% | 60 | 8.3 |
| combo | -2.48% | 10.6% | 51 | 11.8 |
| combo, inverted rank | **-1.87%** | **5.1%** | 44 | 15.9 |

Selection was the dominant failure: ranking flipped alone recovers 25.5 of
the 29 points. **Do NOT ship the inversion** — cross-sectional momentum
classically flips sign between trending and choppy regimes, and flipping a
sign in-sample is the canonical overfit. The durable finding is narrower:
*within a pool that already passed the momentum gate, chasing the very
hottest names was the toxic component in this regime* (rhymes with the
pullback result). The actionable bar for any candidate picker (e.g. Kronos):
positive mean rank-IC with a stable sign on our window, out-of-sample.

## Kronos audition — zero-shot picker (run 2026-07-31)

Setup: Kronos-small (24.7M, AAAI'26 k-line foundation model), zero-shot, 250
adjusted daily bars per stock, 10-session forecast, full gate pool every 3rd
day (27 days × ~550 stocks, ~15k forecasts, 53min on MPS). Scores archived
at `docs/backtest/kronos_scores_2026-07-31.csv`. Window postdates the
model's 2025-08 release → genuinely out-of-sample. (Spike artifacts — repo
clone, venv, weights, `scripts/kronos_spike.py` — deleted 2026-07-31 after
the verdict; the script survives in git history at `897cb0f` if ever needed.)

| ranking signal | mean rank-IC (10d) | days IC>0 |
|---|---|---|
| RPS60 (incumbent) | -0.071 | 8/27 |
| **inverted RPS60** | **+0.071** | 19/27 |
| Kronos zero-shot | +0.056 | 16/27 |
| Kronos orthogonalized to inverted-RPS60 | **+0.008** | 13/27 |

**Verdict: audition failed — not because Kronos is bad, but because it is
our own signal in disguise.** Its cross-sectional ranking correlates 0.70
with inverted RPS60; the day-level IC series correlate -0.89 with RPS60
(near-mirror). Orthogonalized to the inversion, its residual IC is +0.008 ≈
nothing on average, and the residual is itself regime-flipping (+0.15 in the
reversal regimes, -0.13 in the Apr–Jun momentum stretch). Zero-shot Kronos ≈
a 70%-strength mean-reversion tilt, and the plain inversion of our existing
signal scores higher (+0.071 vs +0.056) for free.

What the spike DID establish: (1) an external model trained on 45 exchanges
independently reads this pool's dominant structure as short-horizon reversal
— corroborates the selection audit, so the inversion finding is not an
artifact of our RPS math; (2) the regime question is the actual alpha
question: with IC-series correlation -0.89, one binary switch between
"rank by RPS60" and "rank by -RPS60" captures nearly everything either
signal offers — IF the regime (momentum vs reversal, the Apr–Jun flip) can
be predicted. Fitting that switch on 27 days would be pure overfit; it needs
either much more data (gap repair → longer history) or an ex-ante regime
proxy tested out-of-sample. (3) Fine-tuning Kronos on A-shares remains
untried and is the only path by which it could still add value; parked.

## Caveats

Single regime (2026 downtrend/chop); no intraday data (close-based stops);
no liquidity/impact model; EW proxy ≠ investable benchmark; 100-share lots
and ST 5% limits unmodeled. All conclusions are rejections, not validations.
Stage-2 knob values are in-sample-tuned (see warning above).
