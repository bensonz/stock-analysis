#!/usr/bin/env python3
"""Path-preserving shim for the pricedb package.

`python3 scripts/pricedb.py <cmd>` is baked into run_daily's subprocess calls,
CLAUDE.md, and years of muscle memory. When pricedb became a package
(scripts/pricedb/, 2026-08-31) those call sites did not have to move, because
of one deliberate property: **Python resolves a package before a same-named
module on the same path entry** — verified empirically before relying on it.

So `import pricedb` anywhere in the codebase finds the PACKAGE, never this
file. This file is only ever *executed by path*, at which point it puts
scripts/ on sys.path and delegates to the package CLI.

Do not add logic here. Anything beyond delegation belongs in
pricedb/__init__.py (or a submodule), where imports can reach it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pricedb import main  # the package, not this shim — see docstring

if __name__ == "__main__":
    main()
