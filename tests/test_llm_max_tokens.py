"""The completion budget must leave room for BOTH reasoning and the answer.

2026-08-26 noon died here. DeepSeek V4 Pro is a reasoning model, and its
reasoning tokens are billed against `max_tokens` — a probe against the live
endpoint returned `completion_tokens=12` of which `reasoning_tokens=10` for a
two-character reply. With the cap at 16384 both passes reported *exactly*
16384 output tokens and 0 chars of content: the model spent the entire budget
thinking and had nothing left to emit. Phase 2 then failed to parse an empty
string, the run exited 1 before writing a manifest, and no decisions were made.

The squeeze had been building. On 2026-08-20 Pass 1 also hit 16384, but the
refine pass came in at 11645 and the run succeeded — the difference was input
size, 63333 tokens then against 73225 on 08-26, with prompt.md growing from
208KB to 244KB as LEARNINGS.md accumulates after every run. A fixed output
ceiling under a growing prompt is a deadline, not a limit.

64K is the endpoint's accepted ceiling (probed 2026-08-26: max_tokens=65536
ACCEPTED). We take it whole rather than picking a comfortable-looking middle
number, because there is no benefit to leaving headroom unused — the cap
truncates, it does not reserve, and billing follows tokens actually generated.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import llm_client as lc


def test_the_constant_is_the_probed_endpoint_ceiling():
    assert lc.MAX_OUTPUT_TOKENS == 65536


def test_every_entry_point_defaults_to_the_constant():
    """Five call paths shared the literal 16384. A per-function default is how
    one of them silently keeps the old cap after the next bump."""
    import inspect

    entry_points = [
        lc._call_anthropic_only,
        lc._call_openai_only,
        lc._call_hybrid,
        lc.call_llm,
        lc.call_llm_v1,
    ]
    for fn in entry_points:
        default = inspect.signature(fn).parameters["max_tokens"].default
        assert default == lc.MAX_OUTPUT_TOKENS, (
            f"{fn.__name__} defaults to {default}, not MAX_OUTPUT_TOKENS"
        )


def test_the_budget_clears_the_observed_failure():
    """73225 in / 16384 out produced nothing. The new cap must be comfortably
    clear of the burn that failed, not merely larger than it."""
    observed_exhausted_budget = 16384
    assert lc.MAX_OUTPUT_TOKENS >= 4 * observed_exhausted_budget
