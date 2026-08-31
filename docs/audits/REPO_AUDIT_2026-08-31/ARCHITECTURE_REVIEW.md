# Architecture Review — 2026-08-31

*Verbatim report from the read-only architecture survey agent. Five parallel
audits (import graph, silent degradation, write-ownership, spec/code drift,
testing architecture). Every claim verified with file:line.*

**Headline:** the module structure is sound — layering is nearly clean, the
doctrine docs are unusually good, the pricedb split worked. The risk is NOT
structural. It is that `agents/ANALYST.md` and the Python gates have drifted
apart with nothing able to detect it, and the drift runs toward taking more
risk.

## 1. Layer diagram (as it IS today)

```
L6  OFFLINE TOOLS    research/{deep_report, backtest, vcp_backtest, candidate_alpha, ...}
                     oneoff/{migrate_*, dev_capture_fixtures, backfill_history_slots}
    ══ one-way boundary: VERIFIED CLEAN (zero edges upward, no dynamic imports) ══
L5  ORCHESTRATION    run_daily.py (2788)  data_collector.py (1963)  doctor.py (900)
                          │ fan-out 22 (9 declared, 13 deferred)
L4  PRESENTATION     report_generator  build_site  llm_client
L3  DOMAIN           position_manager contracts validator rps_calculator vcp_scanner
                     hypothesis_manager rotation_ledger regime_detector base_rates
                     fundamentals event_calendar prediction_log pit_archive
                     run_rules ─subprocess→ rules/check_*.py
L2  PRICE STORE      pricedb/{__init__ (facade+CLI), providers, factors, health, storage}
                          ↑↓ 22 deferred imports = the one real cycle
L1  EXTERNAL CLIENTS ifind_client cheesefortune_client snapshot_bars
                     fetch_gex fetch_iv_sentiment margin_flow
L0  PURE LEAVES      market_rules  run_paths  price_adjust  pricedb.bars
```

**Violations — only four, three minor:**

- **V1 (L2→L3):** pricedb imports rps_calculator at `__init__.py:1271`
  (cmd_rps), `:1421` (cmd_query) — confined to CLI handlers. Real defect is
  a ~400-line CLI inside the package `__init__`; `pricedb/cli.py` erases both.
- **V2 (cycle):** pricedb ↔ {factors, health, providers}, 22 deferred sites.
  Deliberate + documented; also preserves the monkeypatch seam. Not a free fix.
- **V3:** `contracts.py:641` does live HTTP through a private client method
  inside check_source_health — validation layer untestable offline.
- **V4:** llm_client + report_generator import fmt_dist/fmt_flip from L1
  fetch_gex. Right instinct (one owner for null rendering), wrong home.

**Structural fact bigger than any violation: 44 top-level import edges vs 59
deferred-only.** run_daily declares 9 deps, has 22. Most deferral is
legitimate error-containment (10 of 13 sit inside `try:`) — the "never
hard-fail" doctrine as an import pattern — but the structure is invisible.

## 2. Top 10 findings (risk-to-money × likelihood)

### 1. ANALYST.md's entry gates are not the code's gates; code is looser in every direction — design-decision
`agents/ANALYST.md:38-42` states three MANDATORY conditions.
`run_daily.py:443-446`:
```python
panic_tape = has_breadth and (ratio < 0.35 or limit_downs >= 30)
weak_tape  = has_breadth and ratio < 1.0
strong_tape = has_breadth and ratio >= 1.5 and broad_index_support
allow_new_positions = has_breadth and not panic_tape
```
Panic floor 0.35 vs spec 1.0. The 1.5:1 gate and 2-of-3-green-indices gate
are sizing labels, not gates: a 1.1:1 tape with one green index → `balanced,
1.0×`, full-size entries. Spec says weak tape → `new_positions: []`; code
gives 0.5× sizing. Fires every run.

### 2. phase3_apply writes any path the LLM names, chmod 0755, then git add -A + push — quick-fix
`run_daily.py:1988-1991`. No allowlist, no `..` rejection.
`{"path": "agents/ANALYST.md"}` overwrites the strategy spec;
`{"path": "../../.ssh/authorized_keys"}` escapes the repo. Phase 5 sweeps
(`:2527`) and pushes (`:2563`). One-line `resolve().is_relative_to(...)`.

### 3. db_health failure silently deletes all three data-quality hard gates — quick-fix
`run_daily.py:1272-1273` catches + prints; `data["db_health"]` never set.
`contracts.py:212-214`: `if health:` → staleness, latest_partial, spot-audit
ALL skipped; absent is indistinguishable from fixture. Same gap at
`:781-782`: preflight's outer handler returns without adding a phase — the
check disappears, leaving the doctor nothing to judge.

### 4. restore_snapshot is a 2nd validation-free writer for tracking/ and reintroduces a FIXED bug — refactor-stage
`run_daily.py:346-387` (--reset-to) bypasses position_manager entirely.
`snapshot_positions:308-310` keys closed_summary by bare code;
`restore_snapshot:371` writes `closed/{code}.json` — the exact pre-2026-08-06
naming that silently erased 9 round-trips (documented at
position_manager.py:388-394). compute_realized_pnl globs closed/*.json →
--reset-to silently changes realized P&L. Latent today. Same shape as the
newPositions bug: two components with independent write authority.

### 5. Failed price fetch writes a fabricated −100% day into the book — quick-fix
`run_daily.py:1664-1673`: `price = price_data.get("price", 0)` → pnl −100.0
into permanent history. Sibling `position_manager.py:118-119` renders a
missing price exactly FLAT — and that positions.json feeds the prompt,
report, and all six rules, so a real drawdown becomes invisible to
check_stop_proximity. `validator.py:59-64` only catches an explicit error
key. close_position has no exit_price>0 guard while open_position hard-fails
— the asymmetry is the defect.

### 6. No locking anywhere, non-atomic writes everywhere; both launchd jobs have already fired simultaneously — refactor-stage
Zero hits for fcntl/flock/filelock/PID. Exactly ONE atomic write in the repo
(pit_archive.py:116-118), on the least critical state. Ranked exposure:
1. tracking/{code}.json — truncation swallowed by load_active_positions'
   `except (JSONDecodeError, KeyError): pass` (position_manager.py:255) →
   position silently vanishes, cash recomputed as if never held.
2. positions.json — 8+ writes/run; at least caught loudly by validator.
3. LEARNINGS.md — read-modify-write of ~250KB.
Doctor reads manifest mid-write with `except Exception: continue`
(doctor.py:756) → torn read = silently skipped check.
**Cheapest big win: position_manager._write_json (:79-83) is a single choke
point — temp+os.replace fixes 4 of the 6 worst artifacts.**

### 7. The mechanical sell-discipline layer can go fully dark with a clean log — quick-fix
`run_daily.py:2066-2073`: bare `except Exception: pass`. Compounds with
run_rules.py:52-75: a crashed check exits 1 like "violations found", error is
nulled, non-JSON stdout → `violations=[]`. A crashed stop-proximity check
reports status "violations" with an empty list.

### 8. The f10>=30 panic clause is one CheeseForTune outage from permanently off — quick-fix
Only _fetch_market_cheesefortune emits `distribution`
(data_collector.py:1194); all three fallbacks return breadth without it.
`run_daily.py:427-428` `int(distribution.get("f10") or 0)` → clause can
never fire, and `:459-463` prints "0 limit-ups / 0 limit-downs" AS IF
MEASURED. All 40 August runs checked: 38 had distribution, 2 had no breadth
(correctly unknown). Same shape ALREADY FIRING: fetch_iv_sentiment
fetch_all:256-260 silently drops failed underlyings and averages the
survivors — and IV feeds sizing while GEX is advisory. fetch_gex had this
exact bug fixed; the IV module never got the fix.

### 9. Test suite is RED on master and no documented command runs an integration test — quick-fix
7 failures on clean master (5 wall-clock fixtures, 1 local-state replay, 1
genuine drift). `pytest --run-integration` skips the 12 integration tests
anyway (conftest conflict; only both-flags works; `pytest scripts/
--run-integration` hard-errors). test_eastmoney.py fires 4 live requests at
collection. test_full_pipeline.py's 7 tests can never go red and read live
tracking/. Two inert monkeypatches: test_local_pricedb.py:561 patches
pricedb._run_with_timeout (caller uses providers' local name);
test_factor_heal.py:61/84/104 patches pricedb.ADJ_BACKFILL_SLEEP_SEC which
is defined TWICE independently (__init__.py:712, factors.py:47) and can
drift at runtime.

### 10. ANALYST.md contradicts itself, TRACKER.md is stale, nothing detects drift — design-decision
Time stop appears 4× with 2 values (15 at :111; 10 at :112/:197/:271);
TRACKER.md:39 is a third variant, and its :89/:208 price-limit table is
factually wrong (创业板 10%→ actually 20%, BJ 20%→ actually 30%) —
market_rules.py:52-54 has it right, and run_daily.py:1834-1837 documents
this bug class already costing a real trade (688222 refused at +13.17%).
ANALYST.md:102 max-8/20%-cash vs code+config 10/0% — and
test_full_pipeline.py:83-84 asserts the DRIFTED values. Zero drift detection
exists: no test reads any agents/*.md; doctor can't see this class by
construction.

**Honourable mentions:** `run_daily.py:984` `nearest_ma_dist or 99` — a
candidate at exactly 0.0 (best reading) becomes 99 and is demoted out of
PREMIUM. Rule 2b abs() fix half-landed: glyphs split, but
report_generator.py:547 `fails = above + below` still gates Sweet Spot on
both sides.

## 3. run_daily.py split proposal

The pricedb split worked because it moved code while keeping names
resolvable through the facade. Same constraint, harder: ~14 test patch sites
bind names into run_daily's namespace via `from data_collector import (...)`
(:51-67). Any extraction that moves a name silently un-fakes a test leg.

Current shape (2,788 lines): constants+strategy pool 174 · book
snapshot/restore 133 · evaluate_new_entry_regime 85 · reset/list 136 ·
preflight 146 · **phase1_collect 543** · prompt building 181 · hard-sells
100 · **phase3_apply 417** · manifest/site/learnings 87 · auto-heal 36 ·
**main() 566**.

**Stage 1 — pure functions (~350 lines, near-zero risk)** → `scripts/pipeline/`:
- `strategy_pool.py` ← flag_over_extended, fetch_strategy_pool_with_fallback,
  _build_strategy_intersection, INTERSECT_MIN_RPS
- `regime.py` ← evaluate_new_entry_regime + the sizing constants — **where
  finding #1 gets fixed**; 90 lines in one file makes asserting it against
  ANALYST.md tractable
- `decisions.py` ← _parse_llm_response, _bare_code, opened/blocked_new_positions,
  _clean_events, _slim_*
run_daily re-exports every name.

**Stage 2 — the state-mutating boundary (~450 lines, medium risk, highest payoff):**
- `book_snapshot.py` ← snapshot/restore/check_snapshot_consistency/reset_to_date
- `preflight.py` ← preflight_pricedb_or_exit, attempt_partial_day_autoheal
Every function takes tracking_dir/closed_dir/runs_dir AS PARAMETERS
(doctor.py's --runs-dir pattern). Makes #4 and #6 testable; collapses the 12
coordinated patches a test needs to 1.

**Stage 3 — phases vs CLI (~700 lines, mechanical):**
- `phases.py` ← phase1_collect, phase2_build_prompt, phase3_apply, phase4,
  enforce_hard_sells, _append_learnings
- `finalize.py` ← refresh_site, write_manifest
- `vcs.py` ← the inline git block (:2521-2576) as commit_and_push(...) →
  Phase 5 is currently the ONLY phase with no test at all.

**Stage 4 — arg parsing:** main()'s 566 lines of hand-rolled `if "--x" in
args` (with copy-paste twin write blocks at :2300/:2711 and :2370/:2637) →
`cli.py` returning a config object; main() becomes ~120-line dispatch.

**Facade keeps:** main(), the --run sequence, path constants, re-export
block. Target ~400 lines.

**Two hazards to plan around:** (a) phase functions have side effects their
names deny — phase2_build_prompt rewrites tracking/positions.json (:1396)
and writes prompt.md into a run dir resolved from TODAY'S CLOCK not
data["date"]; phase1_collect also rewrites positions.json (:1289) — so
"data collection only" --phase1 mutates the live book. Do NOT preserve while
moving; hoist regenerate_positions_json() to the caller, take explicit
run_dir. Third offenders: build_site.load_index_closes:312 writes a
git-tracked cache; data_collector._load_sw_industry_map:1061 writes from a
thread-pool worker. (b) `:995`'s intersect.json existence guard is a
stale-artifact TOCTOU on the Gate-1 retry — attempt 2 can skip the save and
leave intersect.json disagreeing with the in-memory pool. The newPositions
shape again. Fix during Stage 3 by keying off in-memory state.

## 4. What NOT to change

- **The 22 deferred imports in pricedb** — documented; they break a real
  load-time cycle AND preserve the monkeypatch seam. Hoisting shared state
  to a config leaf breaks the seam. Not free.
- **The free provider chain behind iFinD** — 08-25 doctrine; insurance, not
  redundancy.
- **The doctor as a separate launchd job** — a hard pipeline death must not
  take its own audit down. Fix the simultaneous-fire with a lock or
  wait-for-manifest, NOT by merging jobs.
- **doctor.py never writing tracking/** — verified exhaustively (3 write
  sites, all audit artifacts). Its --runs-dir re-derivation (:842-847) is
  the reference pattern; propagate, don't dilute.
- **The three frozen epochs** (doctor ARTIFACT_EPOCHS, GATE_SEVERITY_EPOCH,
  HISTORY_SCHEMA_EPOCH) — do NOT pool into config; that invites "updating
  together", which re-judges history.
- **Thresholds inside rules/check_*.py** — each sits beside its track record
  and LEARNINGS lineage per CLAUDE.md. (Docstrings need fixing IN PLACE:
  check_stop_proximity title says 3% while :34 fires at 5%;
  check_overextended_entry's headline metric is never computed.)
- **ifind_client importing nothing from the project** — stated design; the
  duplicated .env parser is the price.
- **The research/ one-way boundary** — verified clean but enforced by
  nothing. One guard test converts convention → invariant; probably the
  highest value-per-line test available.

**Genuinely dead + safe:** fetch_price.py, fetch_and_save.py (with their
agent-doc mentions), pit_archive.py behaving like a research/ tool missed by
the 08-30 move.
