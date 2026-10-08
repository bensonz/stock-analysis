# Decisions
- Source: eastmoney datacenter RPT_SHAREBONUS_DET — already used by pricedb
  for ex-div dates, carries cash + 送转 ratios (verified on 000739).
- Back-credit = the same idempotent apply run once (entryDate < exDate <= today);
  no separate migration path.
- Tax at ex-date, not at sale: simpler, slightly conservative (owner choice).
