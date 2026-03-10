#!/usr/bin/env python3
"""
Hypothesis-based learning system for the stock analysis pipeline.

Replaces the append-only LEARNINGS.md with a structured system that tracks
observations → hypotheses → validated rules with evidence and hit rates.
"""

import json
import re
import sys
from datetime import datetime, date
from pathlib import Path
from difflib import SequenceMatcher

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HYPOTHESES_FILE = PROJECT_ROOT / "tracking" / "hypotheses.json"

# Status lifecycle thresholds
PROMOTE_TO_HYPOTHESIS_MIN_EVIDENCE = 2
PROMOTE_TO_VALIDATED_MIN_EVIDENCE = 5
PROMOTE_TO_VALIDATED_MIN_HITRATE = 0.65
PROMOTE_TO_RULE_MIN_EVIDENCE = 10
PROMOTE_TO_RULE_MIN_HITRATE = 0.75
RETIRE_MIN_EVIDENCE = 5
RETIRE_MAX_HITRATE = 0.40
RETIRE_STALE_DAYS = 30

VALID_TYPES = {"observation", "heuristic", "signal", "rule"}
VALID_STATUSES = {"observation", "hypothesis", "validated", "rule", "retired"}
STATUS_ORDER = ["observation", "hypothesis", "validated", "rule"]


def load_hypotheses() -> dict:
    """Load hypotheses from JSON file."""
    if HYPOTHESES_FILE.exists():
        return json.loads(HYPOTHESES_FILE.read_text(encoding="utf-8"))
    return {"version": 2, "lastUpdated": str(date.today()), "hypotheses": []}


def save_hypotheses(data: dict) -> None:
    """Save hypotheses to JSON file."""
    data["lastUpdated"] = str(date.today())
    HYPOTHESES_FILE.parent.mkdir(parents=True, exist_ok=True)
    HYPOTHESES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _next_id(data: dict) -> str:
    """Generate next hypothesis ID."""
    existing = [h["id"] for h in data.get("hypotheses", [])]
    if not existing:
        return "h001"
    max_num = max(int(h_id[1:]) for h_id in existing if h_id.startswith("h") and h_id[1:].isdigit())
    return f"h{max_num + 1:03d}"


def _normalize(s: str) -> str:
    """Normalize text for comparison."""
    s = s.lower()
    s = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _extract_keywords(text: str) -> set:
    """Extract meaningful keywords (skip stopwords, keep Chinese chars as individual tokens)."""
    norm = _normalize(text)
    # Split into words
    words = set(norm.split())
    # Also extract Chinese character bigrams for better matching
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', norm)
    for cc in chinese_chars:
        for i in range(len(cc) - 1):
            words.add(cc[i:i+2])
        words.add(cc)  # Full Chinese word too

    # Remove common English stopwords
    stopwords = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
        'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
        'neither', 'each', 'every', 'all', 'any', 'few', 'more', 'most',
        'other', 'some', 'such', 'no', 'only', 'own', 'same', 'than',
        'too', 'very', 'just', 'because', 'if', 'when', 'while', 'that',
        'this', 'these', 'those', 'it', 'its', 'i', 'me', 'my', 'we',
        'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her', 'they',
        'them', 'their', 'what', 'which', 'who', 'whom', 'how', 'where',
        'today', 'again', 'also', 'about', 'still', 'even',
    }
    return words - stopwords


def _similarity(a: str, b: str) -> float:
    """Compute text similarity between two strings (0-1).
    
    Uses a combination of:
    1. SequenceMatcher ratio (captures word order / phrasing similarity)
    2. Keyword Jaccard overlap (captures semantic/concept overlap)
    
    The max of both is returned, so either similar phrasing OR
    similar concepts will trigger a match.
    """
    na, nb = _normalize(a), _normalize(b)

    # Sequence similarity (word order matters)
    seq_sim = SequenceMatcher(None, na, nb).ratio()

    # Keyword overlap (order doesn't matter)
    kw_a = _extract_keywords(a)
    kw_b = _extract_keywords(b)
    if kw_a and kw_b:
        kw_sim = len(kw_a & kw_b) / len(kw_a | kw_b)
    else:
        kw_sim = 0.0

    return max(seq_sim, kw_sim)


def _tag_overlap(tags_a: list, tags_b: list) -> float:
    """Compute Jaccard similarity between two tag lists."""
    if not tags_a or not tags_b:
        return 0.0
    sa, sb = set(tags_a), set(tags_b)
    return len(sa & sb) / len(sa | sb)


def find_matching(data: dict, text: str, tags: list | None = None, threshold: float = 0.45) -> dict | None:
    """Find an existing hypothesis that matches the given text/tags.
    
    Uses text similarity + tag overlap + evidence text similarity.
    Returns the best match above threshold, or None.
    """
    best = None
    best_score = 0.0

    for h in data.get("hypotheses", []):
        if h.get("status") == "retired":
            continue

        text_sim = _similarity(text, h["text"])

        # Also check similarity against existing evidence (the hypothesis may have
        # evolved from its original text through accumulated evidence)
        ev_texts = [e["detail"] for e in h["evidence"]["supporting"]] + \
                   [e["detail"] for e in h["evidence"]["contradicting"]]
        ev_max_sim = max((_similarity(text, et) for et in ev_texts), default=0.0)

        # Use whichever text comparison is better
        best_text_sim = max(text_sim, ev_max_sim * 0.9)  # Slight discount for evidence vs title match

        tag_sim = _tag_overlap(tags or [], h.get("tags", []))
        # Weighted: text matters more than tags
        score = best_text_sim * 0.7 + tag_sim * 0.3

        if score > best_score and score >= threshold:
            best_score = score
            best = h

    return best


def create_hypothesis(
    data: dict,
    text: str,
    h_type: str = "observation",
    tags: list | None = None,
    mechanism: str | None = None,
    initial_evidence: dict | None = None,
    status: str | None = None,
) -> dict:
    """Create a new hypothesis entry.
    
    Returns the created hypothesis dict.
    """
    if h_type not in VALID_TYPES:
        raise ValueError(f"Invalid type: {h_type}. Must be one of {VALID_TYPES}")

    today = str(date.today())
    h_id = _next_id(data)

    hypothesis = {
        "id": h_id,
        "text": text,
        "type": h_type,
        "status": status or "observation",
        "created": today,
        "lastTested": today,
        "mechanism": mechanism,
        "evidence": {"supporting": [], "contradicting": []},
        "sampleSize": 0,
        "hitRate": 0.5,  # Prior: 50/50
        "confidence": 0.5,
        "tags": tags or [],
        "parentRule": None,
        "retiredDate": None,
        "retiredReason": None,
    }

    if initial_evidence:
        ev_type = initial_evidence.get("type", "supporting")
        ev_entry = {
            "date": initial_evidence.get("date", today),
            "detail": initial_evidence.get("detail", text),
        }
        hypothesis["evidence"][ev_type].append(ev_entry)
        hypothesis["sampleSize"] = 1
        hypothesis["hitRate"] = 1.0 if ev_type == "supporting" else 0.0
        hypothesis["confidence"] = 0.6 if ev_type == "supporting" else 0.4

    data["hypotheses"].append(hypothesis)
    return hypothesis


def add_evidence(
    data: dict,
    hypothesis_id: str,
    evidence_type: str,
    detail: str,
    ev_date: str | None = None,
) -> dict:
    """Add evidence to an existing hypothesis.
    
    evidence_type: 'supporting' or 'contradicting'
    Returns the updated hypothesis.
    """
    if evidence_type not in ("supporting", "contradicting"):
        raise ValueError("evidence_type must be 'supporting' or 'contradicting'")

    today = ev_date or str(date.today())

    for h in data["hypotheses"]:
        if h["id"] == hypothesis_id:
            # Check for duplicate (same date + similar detail)
            existing = h["evidence"][evidence_type]
            for e in existing:
                if e["date"] == today and _similarity(e["detail"], detail) > 0.85:
                    return h  # Duplicate, skip

            h["evidence"][evidence_type].append({"date": today, "detail": detail})
            h["lastTested"] = today

            # Recalculate stats
            n_support = len(h["evidence"]["supporting"])
            n_contra = len(h["evidence"]["contradicting"])
            h["sampleSize"] = n_support + n_contra

            if h["sampleSize"] > 0:
                h["hitRate"] = round(n_support / h["sampleSize"], 3)
            else:
                h["hitRate"] = 0.5

            # Bayesian-ish confidence update
            # confidence = smoothed hitRate biased toward 0.5 for small samples
            # As sample size grows, confidence converges to hitRate
            prior_weight = 2  # equivalent to 2 prior observations at 50%
            h["confidence"] = round(
                (n_support + prior_weight * 0.5) / (h["sampleSize"] + prior_weight),
                3,
            )

            # Check for auto-promote/demote
            _auto_lifecycle(h)
            return h

    raise ValueError(f"Hypothesis {hypothesis_id} not found")


def _auto_lifecycle(h: dict) -> None:
    """Auto-promote or demote hypothesis based on thresholds."""
    status = h["status"]
    n = h["sampleSize"]
    hr = h["hitRate"]

    if status == "retired":
        return

    # Auto-retire: low hit rate with enough samples
    if n >= RETIRE_MIN_EVIDENCE and hr < RETIRE_MAX_HITRATE:
        h["status"] = "retired"
        h["retiredDate"] = str(date.today())
        h["retiredReason"] = f"hitRate {hr:.0%} < {RETIRE_MAX_HITRATE:.0%} after {n} samples"
        return

    # Stale check
    if h.get("lastTested"):
        last = datetime.strptime(h["lastTested"], "%Y-%m-%d").date()
        days_stale = (date.today() - last).days
        if days_stale > RETIRE_STALE_DAYS and status in ("observation", "hypothesis"):
            h["status"] = "retired"
            h["retiredDate"] = str(date.today())
            h["retiredReason"] = f"No new evidence in {days_stale} days"
            return

    # Promotion chain
    if status == "observation" and n >= PROMOTE_TO_HYPOTHESIS_MIN_EVIDENCE:
        h["status"] = "hypothesis"
    if status == "hypothesis" and n >= PROMOTE_TO_VALIDATED_MIN_EVIDENCE and hr >= PROMOTE_TO_VALIDATED_MIN_HITRATE:
        h["status"] = "validated"
    if status == "validated" and n >= PROMOTE_TO_RULE_MIN_EVIDENCE and hr >= PROMOTE_TO_RULE_MIN_HITRATE:
        h["status"] = "rule"

    # Demotion: rule can drop back to validated if hitRate falls
    if status == "rule" and hr < PROMOTE_TO_RULE_MIN_HITRATE:
        h["status"] = "validated"
    if status == "validated" and hr < PROMOTE_TO_VALIDATED_MIN_HITRATE:
        h["status"] = "hypothesis"


def retire_hypothesis(data: dict, hypothesis_id: str, reason: str) -> dict:
    """Manually retire a hypothesis."""
    for h in data["hypotheses"]:
        if h["id"] == hypothesis_id:
            h["status"] = "retired"
            h["retiredDate"] = str(date.today())
            h["retiredReason"] = reason
            return h
    raise ValueError(f"Hypothesis {hypothesis_id} not found")


def get_active_for_prompt(data: dict) -> str:
    """Format active hypotheses for inclusion in the analyst prompt.
    
    Only includes 'validated' and 'rule' status hypotheses.
    Returns a compact markdown string.
    """
    rules = []
    validated = []

    for h in data.get("hypotheses", []):
        status = h.get("status")
        if status == "rule":
            rules.append(h)
        elif status == "validated":
            validated.append(h)

    # Sort by confidence descending
    rules.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    validated.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    lines = []

    if rules:
        lines.append("## Active Rules (proven, hitRate ≥ 75%)")
        for h in rules:
            lines.append(
                f"- [{h['id']}] {h['text']} "
                f"(hitRate: {h['hitRate']:.0%}, n={h['sampleSize']}, confidence: {h['confidence']:.0%})"
            )
        lines.append("")

    if validated:
        lines.append("## Working Hypotheses (testing, hitRate ≥ 65%)")
        for h in validated:
            lines.append(
                f"- [{h['id']}] {h['text']} "
                f"(hitRate: {h['hitRate']:.0%}, n={h['sampleSize']}, confidence: {h['confidence']:.0%})"
            )
        lines.append("")

    if not rules and not validated:
        lines.append("## No validated learnings yet — system is bootstrapping.\n")

    return "\n".join(lines)


def get_all_summary(data: dict) -> str:
    """Full summary of all hypotheses for human review."""
    lines = ["# Hypothesis Dashboard", ""]

    by_status = {}
    for h in data.get("hypotheses", []):
        status = h.get("status", "unknown")
        by_status.setdefault(status, []).append(h)

    for status in ["rule", "validated", "hypothesis", "observation", "retired"]:
        group = by_status.get(status, [])
        if not group:
            continue

        emoji = {"rule": "✅", "validated": "🔬", "hypothesis": "🧪", "observation": "👁️", "retired": "🪦"}.get(status, "")
        lines.append(f"## {emoji} {status.upper()} ({len(group)})")
        lines.append("")

        for h in sorted(group, key=lambda x: x.get("confidence", 0), reverse=True):
            lines.append(
                f"- **[{h['id']}]** {h['text']}\n"
                f"  Type: {h['type']} | HitRate: {h['hitRate']:.0%} | "
                f"Samples: {h['sampleSize']} | Confidence: {h['confidence']:.0%} | "
                f"Tags: {', '.join(h.get('tags', []))}"
            )
            if h.get("mechanism"):
                lines.append(f"  Mechanism: {h['mechanism']}")
            if h.get("retiredReason"):
                lines.append(f"  Retired: {h['retiredReason']}")
        lines.append("")

    # Stats
    total = len(data.get("hypotheses", []))
    active = sum(1 for h in data.get("hypotheses", []) if h.get("status") not in ("retired",))
    lines.append(f"**Total: {total} | Active: {active} | Retired: {total - active}**")

    return "\n".join(lines)


def process_learnings(data: dict, learnings: list[dict | str], run_date: str | None = None) -> list[str]:
    """Process new learnings from the LLM response.
    
    Accepts both:
    - Old format: list of strings (backward compatible)
    - New format: list of dicts with {text, type, tags, evidence_type, related_hypothesis, mechanism}
    
    Returns list of action descriptions (for logging).
    """
    today = run_date or str(date.today())
    actions = []

    for learning in learnings:
        # Normalize to dict
        if isinstance(learning, str):
            learning = {"text": learning, "type": "observation", "tags": []}

        text = learning.get("text", "")
        if not text:
            continue

        h_type = learning.get("type", "observation")
        tags = learning.get("tags", [])
        mechanism = learning.get("mechanism")
        evidence_type = learning.get("evidence_type", "supporting")
        related_id = learning.get("related_hypothesis")

        # Try to match existing hypothesis
        match = None
        if related_id:
            # Explicit reference
            for h in data["hypotheses"]:
                if h["id"] == related_id:
                    match = h
                    break

        if not match:
            # Fuzzy match
            match = find_matching(data, text, tags)

        if match:
            # Add evidence to existing hypothesis
            add_evidence(data, match["id"], evidence_type, text, ev_date=today)
            actions.append(
                f"Updated {match['id']} ({match['status']}): "
                f"+1 {evidence_type} evidence → hitRate={match['hitRate']:.0%}, n={match['sampleSize']}"
            )
        else:
            # Create new observation
            h = create_hypothesis(
                data,
                text=text,
                h_type=h_type if h_type in VALID_TYPES else "observation",
                tags=tags,
                mechanism=mechanism,
                initial_evidence={"type": evidence_type, "detail": text, "date": today},
            )
            actions.append(f"Created {h['id']} ({h['status']}): {text[:80]}...")

    return actions


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    """CLI interface for hypothesis management."""
    args = sys.argv[1:]

    if not args or args[0] == "help":
        print("Usage:")
        print("  hypothesis_manager.py summary        — Full dashboard")
        print("  hypothesis_manager.py prompt          — Prompt-ready active rules")
        print("  hypothesis_manager.py stats           — Quick stats")
        print("  hypothesis_manager.py get <id>        — Show single hypothesis")
        print("  hypothesis_manager.py retire <id> <reason>  — Retire a hypothesis")
        print("  hypothesis_manager.py stale-check     — Retire stale hypotheses")
        return

    data = load_hypotheses()
    cmd = args[0]

    if cmd == "summary":
        print(get_all_summary(data))

    elif cmd == "prompt":
        print(get_active_for_prompt(data))

    elif cmd == "stats":
        total = len(data.get("hypotheses", []))
        by_status = {}
        for h in data.get("hypotheses", []):
            by_status[h["status"]] = by_status.get(h["status"], 0) + 1
        print(f"Total hypotheses: {total}")
        for s in ["rule", "validated", "hypothesis", "observation", "retired"]:
            if s in by_status:
                print(f"  {s}: {by_status[s]}")

    elif cmd == "get" and len(args) > 1:
        h_id = args[1]
        for h in data["hypotheses"]:
            if h["id"] == h_id:
                print(json.dumps(h, ensure_ascii=False, indent=2))
                return
        print(f"Not found: {h_id}")

    elif cmd == "retire" and len(args) > 2:
        h_id = args[1]
        reason = " ".join(args[2:])
        retire_hypothesis(data, h_id, reason)
        save_hypotheses(data)
        print(f"Retired {h_id}: {reason}")

    elif cmd == "stale-check":
        count = 0
        for h in data["hypotheses"]:
            if h["status"] in ("observation", "hypothesis") and h.get("lastTested"):
                last = datetime.strptime(h["lastTested"], "%Y-%m-%d").date()
                days = (date.today() - last).days
                if days > RETIRE_STALE_DAYS:
                    h["status"] = "retired"
                    h["retiredDate"] = str(date.today())
                    h["retiredReason"] = f"Stale: no evidence in {days} days"
                    count += 1
                    print(f"  Retired {h['id']}: stale ({days} days)")
        if count:
            save_hypotheses(data)
        print(f"Retired {count} stale hypotheses")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
