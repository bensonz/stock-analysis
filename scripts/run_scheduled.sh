#!/bin/bash
# launchd entrypoint for the daily pipeline (docs/HARNESS Stage 4).
#
# Why this exists instead of launchd calling python directly: the venv must be
# the interpreter, the working directory must be the repo (run_daily resolves
# everything relative to it), and launchd agents inherit a minimal PATH with no
# shell profile — git and curl must be findable explicitly.
#
# The scheduler is NOT the source of truth for success (DECISIONS.md D2): that
# is the run's manifest on disk. This wrapper only executes and timestamps.
set -uo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"
cd "$(dirname "$0")/.."
echo "=== run_scheduled $(date '+%Y-%m-%d %H:%M:%S %z') args=${*:---run} ==="
source .venv/bin/activate
python3 scripts/run_daily.py "${@:---run}"
rc=$?
echo "=== exit=$rc $(date '+%Y-%m-%d %H:%M:%S %z') ==="
exit $rc
