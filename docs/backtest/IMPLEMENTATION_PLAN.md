# Backtest Harness — Stage-1 Implementation Plan

## Why (one paragraph)

We can measure "how often did stocks fall after condition X" (`base_rates`) but
not "would strategy X have made money" — with sizing, stops, T+1, and costs.
Every strategy debate this month (pool-pain throttle, 0.75× strong-tape sizing,
wider stops) ended in a frequency table instead of a verdict. The harness turns
each into an equity-curve comparison, and answers the scariest question first:
does ANALYST.md's strategy, executed perfectly mechanically over our data,
make money at all? (The 2026 breadth study suggests possibly not — negative
forward medians almost everywhere. That needs a real P&L answer.)

**Honest scope limit:** ~390 trading days, one market regime. This harness can
*reject* strategies quickly and cheaply; it cannot *confirm* edge. Frame every
result accordingly.

## Design decisions (locked before code)

- **D1 — Signals in adjusted space, P&L in percent space.** Indicator math
  (RPS, MA, stops-as-returns) uses adjusted closes from the `base_rates` panel,
  same as production. Position P&L = adjusted-return from entry × allocation;
  no integer share lots in Stage 1 (100-share lot rounding is a Stage-2 realism
  knob, noted, not modeled). This sidesteps raw-price gaps across ex-div dates
  corrupting stop math.
- **D2 — Fill model (T+1 exists or the results are fiction).**
  - Signals computed at close of day *t* → entries fill at **t+1 open**
    (open/close from `daily_prices`, adjusted via factor ratio).
  - A-share T+1: a position entered at t+1 open cannot exit before t+2.
  - Exits (stop hit, rule sell) evaluated on closes → fill at the **trigger
    day's close** (live system sells intraday at noon/afternoon; close is the
    conservative approximation), except never on the entry day itself.
  - **Limit constraints:** skip an entry if t+1 open is at/above the limit-up
    cap vs t close (10% main board / 20% ChiNext+STAR, by code prefix); defer
    an exit by one day if the trigger day's close is at limit-down (can't fill
    a sell into a sealed limit-down).
- **D3 — Costs, parameterized, defaults on:** commission 0.025% per side,
  stamp duty 0.05% on sells, slippage 0.10% per side ⇒ ~0.30% round trip.
  Every result reports gross AND net.
- **D4 — The mechanical-ANALYST arm needs a selection rule** (the LLM's seat):
  among gate passers (rps60/120/250 ≥ 80, MA20>MA120>MA250) not blocked by the
  extension guard (Rule 2b MA-distance), rank by rps60 desc, fill up to
  `positions_max` (10) at `alloc_pct` (3%) each. Deliberately dumb — it is the
  *baseline*, not the strategy. Exits: Rule 5 (−5% hard stop; −3% within first
  3 sessions), time-decay per rules-engine spec. Parameters read from one
  config dict so variants are one-line diffs.
- **D5 — Fidelity is a deliverable, not an afterthought.** The engine must
  replay our 41 actual closed trades (entryDate/entryPrice → exitDate) through
  the fill+cost model and reconcile per-trade returns vs the recorded
  `returnPct`. Deviations are expected (live fills are intraday); the check is
  direction + magnitude (tolerance band), and the reconciliation table ships
  with the results. If the simulator can't approximately reproduce July, its
  verdicts on hypotheticals are worthless.
- **D6 — Location & reuse:** `scripts/backtest.py` (engine + CLI), building on
  `base_rates.get_panel()` (adjusted closes, RPS features, coverage-floor
  dates) — no second data path. Results → `docs/backtest/RESULTS.md`.

## Stage 1a — Portfolio engine

**Goal**: Day-loop simulator: signals→orders→fills→positions→equity, with T+1,
limit constraints, stops, costs. Strategy passed in as two callables
(`entries(day, panel, portfolio) -> [orders]`, `exits(day, panel, positions) ->
[orders]`).
**Success criteria**: Deterministic; equity curve + per-trade ledger out;
synthetic-price unit tests prove each microstructure rule fires.
**Tests**: T+1 blocks same-day exit; entry skipped at limit-up open (both 10%
and 20% boards); exit deferred at limit-down close; stop on close not low;
costs reduce net exactly as configured; ex-div day produces no phantom stop
(adjusted-space P&L).
**Status**: Not Started

## Stage 1b — The two arms

**Goal**: (a) mechanical-ANALYST baseline per D4; (b) replay arm that feeds the
actual `tracking/closed/*.json` + open-position trades as forced orders.
**Success criteria**: Baseline runs 2025-01→today in <60s; replay arm
reconciles ≥80% of the 41 closed trades within ±1.5pp of recorded `returnPct`
(and documents every miss).
**Tests**: Selection respects gate + extension guard + max positions; replay
of a hand-picked trade (e.g. 600176 entry 7/29 → stop 7/30) matches its file.
**Status**: Not Started

## Stage 1c — Results & the verdict

**Goal**: Run the baseline over the full window; write `docs/backtest/RESULTS.md`:
equity curve (plus benchmark: CSI300-proxy buy&hold and cash), max drawdown,
win rate, avg win/loss, exposure, turnover, cost drag; the July fidelity table;
and the one-line verdict on "does mechanical ANALYST.md make money here".
**Success criteria**: A reader can answer "did the strategy beat sitting in
cash, net of costs, and where did it bleed" from the doc alone.
**Tests**: Full pytest suite green (7 known pre-existing failures only).
**Status**: Not Started

## Stage 2 (sketch only — NOT in scope now)

Experiment CLI (`backtest.py compare configA configB`) for: pool-pain throttle,
stop width × size trade-off, pullback-vs-strength entries, 0.75× sizing
question. Each becomes an equity-curve diff with the same engine. Later: LLM
overlay evaluation by replaying historical LLM decisions vs the mechanical arm.

## Risks / known limits

- One regime of data → rejection-only conclusions (stated in every output).
- Close-based stop evaluation understates intraday whipsaw both ways.
- No volume/liquidity model: assumes our 3% notional fills without impact
  (fine at sim scale, stated).
- Selection stand-in ≠ LLM behavior: baseline measures the *rules*, replay arm
  measures *what we actually did*; the gap between them is itself a finding.
