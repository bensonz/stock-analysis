# Decisions

## D1 — brief goes in its own prompt block, not `data` (2026-10-03)
`flatten_data_numbers(data)` feeds the verifier's mechanical 〖内部数据〗 match.
Web-sourced numbers placed in `data` would verify without a link. Separate block,
modelled on the `focus` block in `build_prompt`.

## D2 — brief items carry source URLs; unlinked items are leads only
Otherwise the writer copies a brief number unlinked → naked claim → scrubbed
by the verifier to adjectives — the opposite of the goal.

## D3 — separate pass (D) on top of spec rules (A–C)
Spec rules depend on the writer obeying them in a long prompt; the separate pass
puts the bear facts in front of the writer regardless. Cost: one more tool loop
on the writer model (~+30–50% tokens vs 238k/36k for 600150).

## D4 — mechanical coverage check deferred
Dated events are emitted as a fenced JSON block so a later guard can check each
appears in the report. Not built now: measure whether the writer uses the brief first.

## D5 — base-rate price-path rule kept; only slot accounting changes
`build_auto_predictions` logs from base_rate tool calls; keeping the rule keeps
the Brier ledger intact. The generic momentum drawdown line becomes additional to
the 3 scenario slots.

## D6 — no test-case specifics in prompts
The spec must not mention 600150 / 301 port fees / 2026-11-09: the foundation
test asks whether the system FINDS the risk. Rationale and history live here in
docs/, which the writer never sees.
