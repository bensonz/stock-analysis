# iFinD integration — progress

**Status: complete** (2026-08-25). Seven stages, each committed separately.

| Doc | What it is |
|---|---|
| `FINDINGS.md` | The evaluation that justified the switch, plus the verified root cause of the `amount` gap |
| `IFIND_API_GUIDE.md` | Standalone, portable API reference — safe to hand to another project |
| `ifind_*.py` | Reproducible probe/eval harnesses (they authenticate via `scripts/ifind_client.py`) |

## What shipped

1. **`scripts/ifind_client.py`** — standalone client (imports nothing from this
   repo, so `pricedb` and `data_collector` can both use it without a cycle).
   Token cached at `data/ifind_token.json`, 0600, git-ignored, refreshed 6 h
   before expiry.
2. **iFinD as primary price provider** — chain is now iFinD → AkShare → Sina.
   Free chain deliberately retained: a single commercial dependency behind a
   `db_health` gate would otherwise hard-stop the pipeline on a token lapse.
3. **`pricedb.py backfill-amount`** — repaired 268,090 rows.
4. **Factors from `ths_af_stock`** — daily sync now uses iFinD's ratio
   (clist f18 fallback), plus a whole-series `factors rebuild`.
5. **Collector paths** — position prices, breadth, sectors, indices.
6. **`input/ifind_candidates.json`** — iwencai screens, display-only.
7. **Docs + tests** — 60 new tests; `CLAUDE.md` doctrine rewritten.

## Measured

| | Before | After |
|---|---|---|
| Universe daily pull | ~30 s (sina snapshot, 53 failed batches on 08-25) | **2.4 s**, 0 failures |
| Snapshot | ~30 s | **0.5 s**, 5207/5207, 0 rejected |
| Breadth | 65 paginated sina requests | one shared universe pull, 0.4 s |
| Sectors | regex scrape of `newSinaHy.php` | SW level-1 aggregation, 0.8 s |
| `amount` NULL | 268,096 / 2,212,886 | **6** (all non-trading rows) |
| Bar accuracy vs local DB | — | 1320/1320, 0 close/OHLC mismatches |

Backfill integrity vs a pre-run DB copy: 0 OHLCV rows changed, 0 rows
added/lost, 0 existing amounts overwritten, 0 close conflicts.

## `factors rebuild` — RUN on the live DB 2026-08-25

Executed at the user's instruction after the staged work landed. It turned out
to fix a real, undetected corruption; see `FINDINGS.md` § "The factor rebuild
found a live corruption" for the full evidence.

- 5568/5568 codes rebuilt, 2,216,878 factor rows, **0 failures, 0 no-data**.
- Coverage 96.11% → **100.00%** (all rows); codes without factors 332 → **0**.
- `factors verify` green; `rps_cache` invalidated and recomputed.
- **96.56% of codes are unchanged** in the today-scale ratio `f[t]/f[last]` that
  consumers actually use. 27 moved ≥1%.
- Those 27 were **wrong before, not now**: 18 codes carried physically
  impossible event counts (000002 had 216 "corporate actions" in 412 sessions).
  953 spurious event-days removed in total.

Rollback: `adj_factors_pre_ifind` inside the DB holds the pre-rebuild table
(2,127,587 rows). Drop it once you're satisfied — it accounts for most of the
503 MB → 624 MB growth.

## Deliberately NOT done

- **iwencai does not feed the RPS/MA gate**, and `ifind_candidates.json` is not
  injected into the LLM prompt. It follows `regime.json`'s posture: display
  first, graduate on evidence. Wiring it into the prompt is a one-line change
  once you want it.

## Known / open

- **`factors verify` cannot catch what the rebuild found.** It audits coverage
  and lag only, so 216 fabricated corporate actions on 000002 sat green for
  months. A plausibility guard (event count per code per year, ~1–4 normal,
  >12 impossible) would have caught it on day one. Not built — worth adding.
- **603558's factor step differs 3.12 bp** between iFinD and our derivation
  (5 of 6 names match exactly). Unresolved which is right; immaterial for
  momentum over 120–250 d, but it is why sources must not be mixed mid-series.
- **6 rows still have NULL `amount`** — all have NULL volume too (non-trading).
- **Quota is unmeasurable via API** (`data_statistics` 404s). `dataVol` is
  metered client-side on `IFindClient.data_vol`.
- `data_pool` `reportname` codes, `report_query` params, and `edb_service`
  indicator IDs are undetermined — see the guide's §13.
- **Pre-existing, unrelated test failures** (present before this work, verified
  against a clean worktree at HEAD): 6 in `scripts/test_hypothesis_manager.py`
  and `scripts/test_pipeline.py::test_entry_regime_throttles_strong_market`.
  Also `TestHistoricalReplay::test_replay_existing_runs` fails in any tree that
  has real `runs/*/response.json` files — one of them is a list where the test
  assumes a dict. Not touched here.
