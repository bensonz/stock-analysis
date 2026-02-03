# Stock Tracker State Schema

## Portfolio Config

- **Total Capital**: 1,000,000 RMB
- **Max Position Size**: 20% (200k per stock)
- **Default Position**: 10% (100k per stock)
- **Max Open Positions**: 5-8

Position sizing rules:
- **High confidence (BUY)**: 15-20% of capital
- **Medium confidence (WATCH→BUY)**: 10-15% of capital
- **Speculative**: 5-10% of capital

## tracking/{code}.json

```json
{
  "code": "002721",
  "name": "菜百股份",
  "status": "active",           // active | closed | stopped
  
  // Position Info
  "thesis": "Gold jewelry retail leader, RPS in ideal range, breakout pattern",
  "entryDate": "2026-02-03",
  "entryPrice": 23.93,
  "shares": 4000,               // Number of shares (must be 100s for A-stock)
  "capital": 95720,             // Capital allocated (shares × entryPrice)
  "capitalPct": 9.57,           // % of total portfolio capital
  "targetPrice": 28.00,         // +17% target
  "stopLoss": 22.00,            // -8% stop
  "currentStop": 22.00,         // May be raised as position profits (trailing stop)
  "rating": 2,                  // 1-3 stars from initial recommendation
  
  // Technical Context (at entry)
  "rps120": 85.2,
  "sector": "黄金珠宝",
  "catalysts": ["黄金涨价周期", "春节消费旺季"],
  
  // Tracking History
  "history": [
    {
      "date": "2026-02-03",
      "price": 23.93,
      "change_pct": 0,
      "action": "OPEN",
      "note": "Initial position, watching for breakout confirmation"
    },
    {
      "date": "2026-02-04", 
      "price": 24.50,
      "change_pct": 2.38,
      "action": "HOLD",
      "note": "Strength confirmed, thesis intact"
    },
    {
      "date": "2026-02-05",
      "price": 25.20,
      "change_pct": 5.31,
      "action": "RAISE_STOP",
      "note": "Raising stop to 23.50 (breakeven+), momentum strong"
    }
  ],
  
  // Exit Info (populated when closed)
  "exitDate": null,
  "exitPrice": null,
  "exitReason": null,           // "target_hit" | "stop_hit" | "thesis_invalid" | "manual"
  "returnPct": null,
  "holdingDays": null,
  
  // Learnings (populated on exit)
  "lessonLearned": null,
  
  // Metadata
  "createdAt": "2026-02-03T14:00:00+08:00",
  "updatedAt": "2026-02-05T14:00:00+08:00",
  "trackerVersion": "1.0"
}
```

## Actions

| Action | Description |
|--------|-------------|
| `OPEN` | Initial position opened |
| `HOLD` | Continue holding, thesis intact |
| `ADD` | Adding to position (rare) |
| `RAISE_STOP` | Trailing stop raised |
| `PARTIAL_EXIT` | Partial profit taking |
| `EXIT` | Full exit |

## Status Transitions

```
[new stock] → OPEN → active
                ↓
        HOLD/RAISE_STOP (daily updates)
                ↓
           EXIT → closed
```

## Exit Reasons

| Reason | Description |
|--------|-------------|
| `target_hit` | Price reached target |
| `stop_hit` | Price hit stop loss |
| `thesis_invalid` | Original thesis no longer valid |
| `time_decay` | Held too long without progress |
| `better_opportunity` | Capital reallocation |
| `manual` | Manual override |
