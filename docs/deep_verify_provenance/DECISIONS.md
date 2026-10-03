# Decisions

## V1 — anchor = decimal with nonzero fraction, or ≥3 significant digits (not a year)
Measured: 135/961 verified internal claims had none. "All tokens distinctive"
would have hit 578/961, mostly date fragments and genuine small figures — too blunt.

## V2 — no-anchor claims go to the judge, not to the scrubber
Scrubbing true data is the 300037/601168 failure direction. The judge reads
context + DATA; requires the judge to see the same DATA the matcher walks.

## V3 — bare thresholds stay claims
"同比增长>20%" is a real claim; only spec-defined judgment bands are exempt.

## V4 — two commits
Allowlist (low risk, removes the visible bad labels) separate from the anchor
rule (changes verification routing; revertable on its own).

## V5 — judge sees the full DATA, not a slim subset
Was: technicals, rps_gate, margin, fundamentals, peer_fundamentals, base_rates.
flatten_data_numbers walks everything (summary, intro, peers, valuation_history),
so routing weak claims to a judge that sees less would scrub true numbers.
Full DATA for 600150 is ~16k chars — no reason to slim (owner: accuracy > cost).

## V6 — false tags are removed, not just ignored
A writer- or guard-placed 〖内部数据〗 over only exempt text (band, 9·10, 第N条)
makes no claim AND is stripped from the published text: leaving it would still
tell the reader a probability came from our database.
