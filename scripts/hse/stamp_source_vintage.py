#!/usr/bin/env python3
# ABOUTME: Stamp the HSE source-data vintage into the refresh acceptance contract (#489).
# ABOUTME: Proves freshness from the BSEE DATE_OCCURRED field (basis dataset_field), not mtime.

"""Stamp the proven HSE source-data vintage into the refresh contract.

Closes the provenance gap (#489): the HSE row in
``data/source-refresh-acceptance-contract.json`` carried
``source_data_latest_date: null`` / basis ``unknown`` even though the BSEE
incident corpus runs to a recent business date. This reads the newest
``DATE_OCCURRED`` from the corpus (``worldenergydata.hse.grounding.corpus_vintage``)
and writes it back with basis ``dataset_field`` — a provable, repeatable source
vintage, never a file-mtime / refresh-timestamp proxy (which the contract
prohibits).

Operator tool: run where the BSEE corpus is reachable (the ace-linux-1 share or a
local ``data/modules`` copy). Re-run as the corpus advances.

Usage::

    python scripts/hse/stamp_source_vintage.py            # update the contract
    python scripts/hse/stamp_source_vintage.py --check     # report, do not write

Then verify with ``python scripts/audit/validate_source_refresh_contract.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "data" / "source-refresh-acceptance-contract.json"
SRC = REPO / "src"


def _vintage() -> str | None:
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    from worldenergydata.hse.grounding import corpus_vintage

    return corpus_vintage()


def _hse_row_span(text: str) -> tuple[int, int]:
    """Byte span of the compact ``hse`` row object in the raw contract text."""
    i = text.find('"module_id":"hse"')
    if i < 0:
        raise SystemExit("hse row not found in contract")
    start = text.rfind("{", 0, i)
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return start, j + 1
    raise SystemExit("unbalanced braces around hse row")


def stamp(
    contract_path: Path = CONTRACT, *, vintage: str | None = None, write: bool = True
) -> dict:
    """Update only the HSE row's source vintage, preserving file formatting.

    Surgically rewrites the single compact ``hse`` row object (same
    ``separators`` style) and splices it back — every other row stays byte-for-
    byte unchanged.
    """
    vintage = vintage or _vintage()
    if not vintage:
        raise SystemExit(
            "BSEE corpus unavailable — run where data/modules or the share is mounted"
        )

    text = contract_path.read_text(encoding="utf-8")
    start, end = _hse_row_span(text)
    row = json.loads(text[start:end])

    old = {
        "source_data_latest_date": row.get("source_data_latest_date"),
        "source_data_latest_date_basis": row.get("source_data_latest_date_basis"),
    }
    row["source_data_latest_date"] = vintage
    row["source_data_latest_date_basis"] = "dataset_field"
    row["source_data_latest_date_unknown_reason"] = ""  # proven now
    new = {
        "source_data_latest_date": vintage,
        "source_data_latest_date_basis": "dataset_field",
    }
    changed = old != new
    if write and changed:
        rewritten = json.dumps(row, separators=(",", ":"))  # match compact row style
        contract_path.write_text(
            text[:start] + rewritten + text[end:], encoding="utf-8"
        )
    return {"old": old, "new": new, "changed": changed}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="report only, do not write")
    a = ap.parse_args(argv)
    result = stamp(write=not a.check)
    print(
        f"HSE source vintage: {result['new']['source_data_latest_date']} "
        f"(basis {result['new']['source_data_latest_date_basis']})"
    )
    print(f"  was: {result['old']}")
    print(
        f"  {'updated contract' if (result['changed'] and not a.check) else 'no write'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
