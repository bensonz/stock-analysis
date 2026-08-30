#!/usr/bin/env python3
"""Capture fresh Eastmoney clist JSON fixtures for unit tests.

Run manually when Eastmoney changes their response shape:

    python3 scripts/dev_capture_fixtures.py

Writes three fixture files under scripts/test_fixtures/:
  - eastmoney_clist_page1.json       (full first page, 50 rows)
  - eastmoney_clist_last_page.json   (partial trailing page)
  - eastmoney_clist_suspended.json   (synthetic — copy of page1 but trimmed
                                       to entries with '-' / null prices)

Hits real API, so the proxy bypass in _fetch_clist_page applies.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pricedb

OUT = Path(__file__).parent.parent / "test_fixtures"


def _trim(payload: dict, limit: int) -> dict:
    """Reduce diff size so fixtures stay small (<100KB)."""
    data = payload.get("data") or {}
    diff = data.get("diff")
    if isinstance(diff, list):
        data["diff"] = diff[:limit]
    elif isinstance(diff, dict):
        keys = list(diff.keys())[:limit]
        data["diff"] = {k: diff[k] for k in keys}
    return payload


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    print("Capturing page 1 ...")
    page1 = pricedb._fetch_clist_page(1)
    (OUT / "eastmoney_clist_page1.json").write_text(
        json.dumps(_trim(page1, 5), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total = int((page1.get("data") or {}).get("total") or 0)
    page_size = pricedb.EASTMONEY_CLIST_PAGE_SIZE
    last_page = (total + page_size - 1) // page_size if total else 1
    print(f"  total={total}, last_page={last_page}")

    print(f"Capturing last page ({last_page}) ...")
    last = pricedb._fetch_clist_page(last_page)
    (OUT / "eastmoney_clist_last_page.json").write_text(
        json.dumps(_trim(last, 5), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Synthesizing suspended-rows fixture ...")
    diff = (page1.get("data") or {}).get("diff") or []
    suspended_like = []
    for item in (diff if isinstance(diff, list) else list(diff.values())):
        if isinstance(item, dict) and (item.get("f2") in ("-", None) or item.get("f17") in ("-", None)):
            suspended_like.append(item)
        if len(suspended_like) >= 3:
            break
    if not suspended_like:
        # Synthesize one by copying the first item and blanking prices.
        copy = dict((diff[0] if isinstance(diff, list) else next(iter(diff.values()))))
        copy.update({"f2": "-", "f3": "-", "f5": "-", "f6": "-", "f15": "-", "f16": "-", "f17": "-"})
        suspended_like.append(copy)
    fixture = {
        "rc": page1.get("rc", 0),
        "rt": page1.get("rt", 6),
        "svr": page1.get("svr", 0),
        "lt": page1.get("lt", 1),
        "full": page1.get("full", 1),
        "data": {"total": len(suspended_like), "diff": suspended_like},
    }
    (OUT / "eastmoney_clist_suspended.json").write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for name in ("eastmoney_clist_page1", "eastmoney_clist_last_page", "eastmoney_clist_suspended"):
        size = (OUT / f"{name}.json").stat().st_size
        print(f"  {name}.json  ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
