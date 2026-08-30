# Candidate-list alpha — 2026-08-28

Reproduce: `python3 scripts/research/candidate_alpha.py --human` (or `--json`)

Asks one question: **do the LLM's picks beat picking at random from the same
candidate list?** Every row of every `output/candidates.md` ever written is
treated as a hypothetical blind purchase and measured against the entries the
LLM actually made.

Sample: 7,266 candidate rows, 294 distinct codes, 104 run dates (2026-04-03 →
2026-08-26), against 64 real LLM entries (61 closed + 3 open).

## Method, and why each choice matters

- **Excess over 上证指数 across the identical window.** The market was roughly
  flat over the sample (+0.84%) while the screen was not. Raw returns would let
  a bad tape and a bad screen look the same.
- **Fixed horizons (5/10/20 sessions), never "to exit."** Measuring to exit
  folds our own sell rule into the answer and reports on the exit machinery
  instead of the pick. An earlier pass of this analysis made exactly that
  mistake and read as "forward returns are reliably negative" — which reversed
  once the exit rule was taken out.
- **Adjusted closes** (`daily_prices ⋈ adj_factors`), the same basis RPS
  computes on, so a dividend does not read as a drawdown.
- **Clustered by code for every confidence claim.** A name sits on the list a
  median of **16 sessions** (max 117), so 7,266 rows are ~294 stocks counted
  over and over. Row-level n describes "what a random pick on a random day
  got"; it is the wrong denominator for "how sure are we," and quoting it as
  one overstates certainty by more than an order of magnitude. Both are
  reported below.

## Result 1 — the picks are indistinguishable from random

Excess return vs index, clustered one-observation-per-code:

| horizon | LLM picks | blind ✅PASS | diff | t | verdict |
|---|---|---|---|---|---|
| 5d | −1.32% (n=52) | −0.76% (n=127) | −0.56pt | −0.32 | indistinguishable |
| 10d | −1.10% (n=51) | −1.41% (n=122) | +0.32pt | +0.14 | indistinguishable |
| 20d | −1.93% (n=42) | −3.34% (n=105) | +1.41pt | +0.45 | indistinguishable |

Row-level gives the same verdict (t = −0.44, +0.38, +0.58). The LLM is
nominally ahead at 10d and 20d and behind at 5d, all far inside noise.

This is **absence of evidence, not evidence of absence.** A single pick's 20d
excess has a ~15.6pt standard deviation; at n=42 the 95% CI on the LLM's mean is
about ±4.3pt. An edge smaller than roughly 4 points could not be detected with
the data we have.

## Result 2 — the list itself has no edge

Excess vs index, by the screen's own Status (row-level):

| bucket | 5d | 10d | 20d | 20d beat-index |
|---|---|---|---|---|
| ✅ PASS | −0.74% | −1.37% | −3.76% | 36.3% |
| ⏳ RPS>95 | −1.54% | −3.53% | **−9.39%** | **23.4%** |
| ❌ MA-rejected | −0.72% | −0.24% | −0.08% | 45.6% |
| all rows | −0.83% | −0.74% | −1.42% | 42.4% |

Every bucket is negative at every horizon. **The names the screen most approves
of are the ones that do worst.** That reframes the whole exercise: the LLM is
choosing skilfully from a list with no edge in it, so there is nothing for skill
to extract. The candidate generator — not the prompt or the decision logic — is
where the problem lives.

## Result 3 — the RPS>95 ceiling is strongly vindicated

`⏳ RPS>95` is the worst bucket in the dataset by a wide margin: −9.39% at 20d
row-level, **−12.14% clustered**, beating the index only **22.1%** of the time.
Buying the very strongest RPS names is a reliable way to lose money, and
`ANALYST.md`'s 75–95 sweet spot already says so. This is the clearest signal
here and it confirms an existing rule rather than challenging one.

## Result 4 — the MA-alignment gate does not survive contact

`❌ MA-rejected` outperforming `✅ PASS` could be an artifact: PASS is capped at
RPS 95 while REJECT spans every RPS level, so the raw comparison confounds two
gates. Holding RPS fixed at the 75–95 sweet spot and varying only MA:

| horizon | RPS 75–95, MA ok | RPS 75–95, MA fail | gap |
|---|---|---|---|
| 5d | −0.83% (n=905) | −0.47% (n=1935) | +0.36pt |
| 10d | −1.81% (n=803) | +0.31% (n=1886) | +2.12pt |
| 20d | **−4.12%** (n=635) | **+4.63%** (n=1667) | **+8.75pt** |

Beat-index at 20d: 34.2% for MA-aligned against **53.6%** for MA-rejected. The
confound is removed and the result gets *stronger*. In this sample the MA gate
is not neutral — it is actively selecting the worse half.

**A rule/implementation mismatch sits underneath this.** `ANALYST.md` Rule 2b is
one-sided — *"dist_ma5_pct > 6% → SKIP. Stock is overextended short-term,"*
with prose that names the target: *"buying a stock that just spiked far above
its moving averages is chasing."* But `report_generator.py:528` implements it
as `abs(ma5) > 6`. A stock **25% below** its MA5 is marked ❌ under a rule
written to catch stocks far *above*.

Splitting the rejection by side (corrected parser, see Data-quality note):

| bucket | 10d mean / beat | 20d mean / beat | n (20d) |
|---|---|---|---|
| >6% **above** MA5 (rule as written) | +1.60% / 47.7% | −1.89% / 41.0% | 991 |
| >6% **below** MA5 (`abs()` only) | **−5.84% / 33.5%** | −2.51% / 43.9% | 1247 |
| inside the band | +0.46% / 48.6% | −0.77% / 42.2% | 2842 |

This does **not** show the `abs()` is costing money — names far below MA5 are
the worst bucket at 10d, so excluding them may well be right. The mismatch is
that the code enforces something the spec never authorised, and nobody decided
it. Distance from **MA20** points the other way at 20d (>20% below: **+8.55%**,
**73.6%** beat-index, n=552), so "far below" is bad short-term and good
longer-term. Different horizons, different MAs, different answers — which is
why this needs replication before anything changes.

## Result 5 — the system as a whole trails the market

2026-04-03 → 2026-08-26: **上证指数 +0.84%, portfolio −3.16%, excess −4.00pt**,
carrying ~89% cash. Realized −47,347, unrealized +15,792.

The shortfall is not beta and not over-exposure — roughly a tenth of capital was
deployed. With 61 closed trades at a 31% win rate, it looks like churn. Note the
other side of the same coin: since the candidate universe underperforms at every
horizon, holding 89% cash has been *protective*, not timid.

## Data-quality note (a correction to the first version of this doc)

`candidates.md` has had two column layouts:

```
≤2026-05 : | Code | Name | RPS120 | RPS60 | Trend | Co | MA5% | MA10% | MA20% | Status |
current  : | Code | Name | RPS120 | RPS60 | MA5% | MA10% | MA20% | Status |
```

The first version of `candidate_alpha.py` read columns by position, so for the
~80% of the archive in the older layout it read **MA5% where it meant MA20%**.
Status (last column) and RPS120 (index 2) are in the same place in both, so
Results 1–4's headline tables were unaffected — but the MA-distance breakdown
was wrong, and the published version of it understated the deep-below bucket by
10× on n (55 vs 552). The parser now resolves columns from each file's own
header; `tests/test_candidate_alpha.py` pins that both layouts yield identical
values for the same row.

The lesson generalises: the run archive spans schema changes, and any analysis
reaching back through it has to read the schema rather than assume one.

## Label split (2026-08-28, after this audit)

Acting on Result 4, `report_generator.py` now splits the two-sided `❌` into
`❌` (extended far **above** — the actual Rule 2b breach) and `🔻 BELOW` (far
below — broken trend). Two consequences for the tables above:

- Every `❌` figure here was computed on the **merged** two-sided label, so it
  mixes both sides. Runs from 2026-08-28 onward separate them.
- Historical `candidates.md` files are **not** back-filled. Rewriting a past
  run's artifact to match today's labelling would destroy the record of what the
  screen actually said that day. `candidate_alpha.py` therefore groups `❌` and
  `🔻` together for the `blind_ma_rejected` series so it stays continuous across
  the change, and reports `blind_below_band_only` separately for post-split runs.

Nothing about what gets *admitted* changed — the label moved, the tradeable set
did not.

## What this does not measure

Entry selection only. Exits, position sizing, and the choice to stay in cash are
out of scope — see `docs/audits/EXIT_ABLATION.md` for the exit side. One market
regime, five months. 上证指数 is an imperfect benchmark for a momentum,
small-cap-tilted book; a matched-size index would be fairer and we do not have
one cached.

## What follows

1. **Do not build an "add to winners" feature on a P&L trigger.** Related work
   in this sample found forward returns conditional on being up X% are
   indistinguishable from noise at 5/10/20d, and weakest at +20% — exactly where
   the temptation is greatest.
2. **Re-examine the MA-alignment gate.** It is the one live rule with evidence
   against it. Before changing it, replicate on a longer window — the sample is
   one regime, and `⏳ >95` shows this dataset *can* produce a strong true
   signal, which makes the MA result harder to dismiss as noise.
3. **Work on the screen, not the prompt.** No amount of decision-logic tuning
   extracts alpha from a universe that has none.
