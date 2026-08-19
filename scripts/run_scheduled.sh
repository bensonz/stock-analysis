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
# Direct GitHub push hangs from this network; the owner's doctrine is the
# Privoxy proxy, applied inline for manual pushes. The scheduler has no shell
# to inherit it from, so export it as PUSH_PROXY — run_daily applies it ONLY
# to the git push subprocess, never to the LLM/data fetches (which must not
# inherit Privoxy's availability). Address lives here, not in run_daily.
export PUSH_PROXY="${PUSH_PROXY:-http://127.0.0.1:8118}"
cd "$(dirname "$0")/.."
echo "=== run_scheduled $(date '+%Y-%m-%d %H:%M:%S %z') args=${*:---run} ==="
source .venv/bin/activate
python3 scripts/run_daily.py "${@:---run}"
rc=$?
echo "=== exit=$rc $(date '+%Y-%m-%d %H:%M:%S %z') ==="
exit $rc
