#!/bin/bash
# launchd entrypoint for the post-run audit (docs/HARNESS Stage 2).
#
# A SEPARATE job from the pipeline, deliberately. If the doctor were the last
# line of run_scheduled.sh, then a pipeline that died hard — segfault, OOM,
# machine asleep through the slot — would take the audit down with it, and the
# audit's most valuable single output is precisely "the run that should have
# happened left nothing behind". The auditor cannot share a fate with the thing
# it audits.
#
# Runs 20 minutes after each pipeline slot: 11:55 and 15:25 CST. That is past
# the observed p95 duration (~5 min) with room for a slow LLM pass, and still
# well before the close-slot report is read.
set -uo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"
cd "$(dirname "$0")/.."
echo "=== run_doctor $(date '+%Y-%m-%d %H:%M:%S %z') args=$* ==="
source .venv/bin/activate
python3 scripts/doctor.py "$@"
rc=$?
# Exit 1 means "findings need a code change" — real information, not a crash.
# Report it verbatim rather than letting launchd's retry logic read it as one.
echo "=== exit=$rc $(date '+%Y-%m-%d %H:%M:%S %z') ==="
exit 0
