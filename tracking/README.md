# Stock Tracking Directory

Each `.json` file represents an actively tracked stock position.

## File Naming
`{code}.json` — e.g., `002721.json` for 菜百股份

## Lifecycle
1. **Created** by `scripts/position_manager.py` when the LLM opens a position
2. **Updated** twice per trading day by the pipeline (`position_manager.py`)
3. **Archived** to `closed/` when position is closed

## State Fields
See `TRACKER_SCHEMA.md` for full schema.
