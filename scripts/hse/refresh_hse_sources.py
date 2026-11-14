# ABOUTME: Run the monthly public HSE collector from a repository checkout.
# ABOUTME: Add the root and namespace package source paths before CLI dispatch.

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
for source_path in [REPO / "src", *sorted((REPO / "packages").glob("*/src"))]:
    if str(source_path) not in sys.path:
        sys.path.insert(0, str(source_path))

from worldenergydata.hse.monthly_refresh import main

if __name__ == "__main__":
    raise SystemExit(main())
