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

## Deliberately NOT done

- **`factors rebuild` was not run on the live DB.** It is implemented, tested,
  and verified correct on a copy (all six 2026-08-25 ex-div names reproduce, five
  at 0.00 bp; series re-anchor at 1.0). Running it swaps every factor to iFinD's
  basis and invalidates `rps_cache` — a deliberate decision, not a side effect.
  Current factors are at 100% coverage with `verify` green, so there is no
  pressure to run it.
- **iwencai does not feed the RPS/MA gate**, and `ifind_candidates.json` is not
  injected into the LLM prompt. It follows `regime.json`'s posture: display
  first, graduate on evidence. Wiring it into the prompt is a one-line change
  once you want it.

## Known / open

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
