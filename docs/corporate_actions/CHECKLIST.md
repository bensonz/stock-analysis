# Checklist
- [x] full pytest green (937 passed / 12 skipped)
- [x] tracking/ fingerprint guard — no conftest guard exists; the new test
      module carries its own and it held
- [ ] doctor --open no new invariant (only meaningful after the first live
      slot with this code; doctor has no cash check to break)
- [x] live tracking/ untouched by the sub-agent (hash before/after dry run)
- [x] tax brackets incl. boundaries, cash credit, 送转 shares/entryPrice,
      idempotent re-run, event ≤ entryDate ignored, non-实施分配 ignored,
      fetch failure leaves the book untouched, close carries dividends
