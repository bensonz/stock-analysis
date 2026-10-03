# Deep report: bear-case research — implementation plan

Trigger (2026-10-01): the 600150 中国船舶 deep report (评级 4/5, 78/78 numbers
verified) missed the dominant risk CheeseForTune led with — the USTR 301
port-fee suspension expires **2026-11-09**, plus US pressure to reinstate/extend
it. Our report had one clause, no date, bundled into an order-volume risk with
a "through 2027 mid-year" horizon. Root causes: the writer did 3 web searches,
all thesis-side; DATA carries no news/risk field; the risk-section format let two
generic base-rate risks eat 2 of 3 slots; the verifier cannot see omissions.

## Stage 1: Spec — mandatory bear search (A), dated-event table (B), risk slots (C)
**Goal**: `agents/DEEP_REPORT.md` requires ≥2 bear-side searches before the
verdict, a 关键日期 table of dated events ≤6 months out, ≥2 of 3 risks that are
stock/sector-specific (base-rate price-path line becomes mandatory-but-additional),
and judgment bets tied to a known date use that date as `expires`.
**Success**: spec reads coherently; prompt-only, no code.
**Status**: Complete — §3 关键日期 added (风险提示 renumbered to §4; no code parses section numbers)

## Stage 2: Independent bear-research pass (D)
**Goal**: `deep_report.py` runs a separate web-only tool loop (spec
`agents/DEEP_BEAR.md`) BEFORE the draft; its brief (every item with source URL,
dated events as a fenced ```events JSON block) is injected into the writer
prompt as its own block — NOT into `data` (would make web numbers pass as
〖内部数据〗). Brief saved as `<code>-<date>-deep-bear.md`. Degrades loudly
(exception / <500 chars → continue without brief). `--no-bear` flag.
**Success**: unit tests for prompt injection, degrade paths, events parsing;
full suite green.
**Status**: Complete — 21 new tests (prompt block/D1 split, events parsing, degrade paths, generate wiring, CLI); full suite 875 passed / 12 skipped

## Stage 3: Foundation test — re-run 600150
**Goal**: the re-run report covers the port-fee expiry properly.
**Pass criteria** (written before the run):
  (a) `2026-11-09` / `11月9日` appears in the report;
  (b) 301/港口费 is its own numbered risk in 风险提示, not a clause in another;
  (c) its judgment bet in predictions has `expires` on/near 2026-11-09, not 2027;
  (d) the bear brief contains the item (distinguishes "pass didn't find" from
      "writer ignored");
  (e) verification still holds (0 unverified remaining, no judge errors).
One run at TEMPERATURE 1.0 is a smoke test, not proof.
**Status**: Complete (smoke test passed 5/5, 2026-10-03 run) —
  (a) PASS 2026-11-10 (brief notes US media say 11-09) in 核心观点, §3 table, 风险三;
  (b) PASS own slot (风险三) — ranked 3rd, but the writer argued it explicitly as the
      spec allows: 9/26 中美八点共识 includes 延期吉隆坡经贸磋商成果 → 5–15%;
      核心观点 calls it 最大的破局变量;
  (c) PASS bet j1 expires 2026-12-15, p 0.05–0.15;
  (d) PASS brief item #1 (and in the ```events block);
  (e) PASS 79/79 verified (25 linked/54 internal), 0 judge errors.
  Bonus finds absent from the 10-01 report: 9·10 北海造船 fire (25 dead, State
  Council investigation) as 风险一; RMB appreciation vs ~60% USD revenue.
