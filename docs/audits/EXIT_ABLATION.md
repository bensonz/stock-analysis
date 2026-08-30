# Exit-rule ablation — 2026-08-17

Reproduce: `python3 scripts/research/exit_ablation.py --horizon {10,20,30,40} [--fill close] --human`

Replays every position we actually opened against the real price path and settles
it under each candidate exit policy. Entries are held fixed at what the pipeline
picked, so the only thing varying is the exit rule. 0.30% round-trip costs charged
to every policy. Stops trigger on the intraday low; gap-throughs fill at the open,
not at the stop level; T+1 enforced.

## Why this was run

The 08-16 weekly audit reported that the same 54 entries won 51.9% of the time at
a fixed 10-session horizon against 29.6% realized, with means of −0.12% vs −0.78%,
and inferred that the exit machinery was costing ~0.66pp/trade.

**That inference was wrong.** It compared fixed-horizon returns over *all* entries
against realized returns over *closed* entries only — two different populations,
differing by exactly the 8 open positions, all of which are winners. Apples to
oranges. Within one consistent sample the comparison reverses.

## Results (mean net return per trade)

| policy | h=20 (n=40) | h=30 (n=34) | h=40 (n=30) |
|---|---|---|---|
| 无止损 (no stops) | **−3.99%** | **−4.02%** | **−0.61%** |
| 仅硬止损 −5% | +1.68% | +2.35% | +3.16% |
| 仅硬止损 −8% (wider) | +0.32% | +0.07% | +0.51% |
| 硬止损 + 头3日−3% (no time stop) | +2.08% | +2.73% | +3.27% |
| └ + time stop **10d/<3% (current)** | **+0.26%** | **+1.60%** | **+2.70%** |
| └ + time stop 10d/<5% | +0.51% | +1.78% | +3.39% |
| └ + time stop 15d/<3% | +2.17% | **+4.04%** | +3.90% |
| └ + time stop 20d/<3% | +2.08% | +3.81% | +3.64% |
| └ + time stop 20d/<5% (the old rule) | +2.08% | +3.82% | **+4.17%** |

Worst single outcome: **−30% to −37%** with no stops, **−5.86%** with the full set.

## Findings

**1. Stops earn their keep, decisively.** No-stops is the worst policy at every
horizon and carries a 5-6x worse tail. The audit's "exits are the leak" hypothesis
is refuted. Stops make the *typical* trade worse (median −5.3% vs −6.9%…+0.4%) and
the *average* trade much better — they trade median for tail, which is the whole
point, and is also why the win rate is low. Low win rate remains a signature of
tight stops, not of bad selection; that conclusion from 08-16 survives, for the
opposite reason to the one given.

**2. −5% is the right hard stop.** Widening to −8% costs 1.4-2.6pp at every
horizon. Tighter beat looser.

**3. The −3% first-3-days rule earns its keep** (+0.11 to +0.40pp on top of the
hard stop, and it pulls the worst case from −11.26% to −5.86%). The 08-16 audit's
recommendation not to touch it holds.

**4. The 08-16 time-stop change (20d/<5% → 10d/<3%) is not supported and looks
harmful.** It is the worst of the five time-stop variants at every horizon, giving
up 1.1-1.8pp against leaving the time stop off entirely and 1.5-2.2pp against the
rule it replaced.

**It is the days, not the gain bar.** Holding days fixed, 3%→5% moves the result
by ≤0.7pp. Holding the bar fixed, 10d→15d moves it by 1.9-2.4pp. Ten sessions is
simply too impatient for this book's momentum to express; the 15-20d band is flat
and comfortably better.

The 08-16 counterfactual that motivated the change (12 trades, +8.73pp) was
conditioned on trades that had *already survived 10 sessions without being
stopped* — a sample selected for the very outcome being measured. This ablation
applies each policy to all entries uniformly.

## Execution slippage — the twice-a-day problem (added same day)

The table above fills hard stops *at the stop level*, which assumes a resting
stop order. There isn't one: the pipeline runs at ~11:35 and ~15:35, samples a
price, and sells at whatever it sees.

**Measured on 21 real stop exits: mean −2.56pp past the stop, median −1.56pp,
worst −15.97pp, and 14 of 21 filled below the stop.** (明阳智能 −15.97pp and
科陆电子 −10.59pp are the tail; both were flagged "hard stop already violated",
i.e. discovered late rather than executed badly.)

`--fill close` is the pessimistic bound: only a *close* below the stop is ever
seen, and it fills there. Truth sits between the two.

| policy | h=20 stop→close | h=30 stop→close |
|---|---|---|
| 无止损 | −3.99% → −3.99% | −4.02% → −4.02% |
| 仅硬止损 −5% | +1.68% → **+0.56%** | +2.35% → **+0.57%** |
| 仅硬止损 −8% | +0.32% → **−0.72%** | +0.07% → **−1.72%** |
| 硬止损 + 头3日−3% | +2.08% → **+1.22%** | +2.73% → **+1.72%** |
| └ 10d/<3% | +0.26% → −0.30% | +1.60% → +1.55% |
| └ **15d/<3%** | +2.17% → **+1.40%** | +4.04% → **+3.75%** |
| └ 20d/<5% | +2.08% → +1.22% | +3.82% → +3.41% |

**All four findings survive.** Slippage costs roughly 1–1.8pp on stop-heavy
policies and pushes the worst case from −5.86% to −12.47%, but no ranking flips:
no-stops is still worst by a wide margin, −5% still beats −8% (by more), 15d is
still the best time stop and 10d still the worst.

**One finding gets stronger.** The first-3-days rule's contribution *grows* under
realistic fills — +0.40→+0.66pp at h=20, +0.38→+1.15pp at h=30. It exits on a
close at −3% rather than waiting for a −5% level it cannot actually hit, so part
of its value is precisely that it compensates for the execution gap. That is an
argument for keeping it that the optimistic model could not see.

## Caveats

- n = 30-40 and shrinking with horizon; one broadly falling regime. This can
  reject a rule for this regime; it cannot validate one in general.
- **Price limits are not modelled**, so a limit-down day lets a stop exit here
  when reality would trap the position. This flatters every stop policy —
  i.e. it biases *toward* finding 1, the finding with the largest effect size.
- **Standalone, not portfolio-level.** Slots are scarce (10 max), so exiting early
  frees capital for the next candidate. That value is invisible here and it argues
  *for* the shorter time stop — the one thing that could rehabilitate 10 days.
  `rotation_ledger.py backtest` is the right instrument; it needs more samples.
- "No time stop" is partly an artifact: the horizon cap is itself a time stop.

## Outcome

**Time stop set to 15d/<3%** (owner decision, `7a88d0a`). `agents/ANALYST.md`
Rule 5 was changed to match — the spec moved to the evidence, not the reverse.
Best or near-best at h=20 and h=30 under *both* fill models. `check_time_decay.py`
and `backtest.py` are in sync with it.

Not recommended, and not done: any loosening of the −5% hard stop or the
first-3-days rule. Both are carrying the book, and both look *better* once
execution slippage is modelled honestly.

Open, not actioned:
- **Price limits still unmodelled.** Owner deferred. It is the one remaining
  assumption that flatters stops, and finding 1 has the biggest number riding
  on it — though also the biggest margin (~4-8pp), so it would take a large
  effect to overturn.
- **Portfolio-level effects.** Everything here is per-trade; slot scarcity means
  an earlier exit frees capital. That argues for shorter time stops and is
  invisible to this instrument. `rotation_ledger.py backtest` is the right tool
  and still has n=0.
