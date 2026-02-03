# Stock Tracking Directory

Each `.json` file represents an actively tracked stock position.

## File Naming
`{code}.json` — e.g., `002721.json` for 菜百股份

## Lifecycle
1. **Created** by daily scanner when a stock is added to watchlist
2. **Updated** daily by tracker subagent
3. **Archived** to `closed/` when position is closed

## State Fields
See `TRACKER_SCHEMA.md` for full schema.
