"""Mechanical evidence checks for the drilling pack's current source pin.

Historical Git blobs are verified separately when issuing the pack; these
checks also work in shallow source checkouts by checking retained SHA-256 and
reference ranges against the shipped sources.
"""

import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "packages/worldenergydata-drilling/src/worldenergydata/drilling"
PACK = PACKAGE / "docs/agent-pack.md"


def test_pack_source_pin_and_digests():
    """All five package source digests must match the documented code pin."""
    text = PACK.read_text()
    inventory = json.loads((PACKAGE / "docs/implementation-map.json").read_text())
    assert f'| Code revision | `{inventory["revision"]}` |' in text
    assert inventory["detector_revision"] in text
    table = text.split("### C1 pinned source digests\n", 1)[1].split("### ", 1)[0]
    digests = re.findall(r"\| `([^`]+\.py)` \| `([0-9a-f]{64})` \|", table)
    assert len(digests) == 5  # Package source manifest: two exports plus three modules.
    for path, digest in digests:
        assert hashlib.sha256((PACKAGE / path).read_bytes()).hexdigest() == digest


def test_pack_source_ranges_and_regression_nodes_resolve():
    """Every source citation is within a real file; each test node exists."""
    text = PACK.read_text()
    ranges = re.findall(r"\[([^\s\[\]]+):L(\d+)-L(\d+)\]", text)
    assert ranges
    for path, first, last in ranges:
        lines = (ROOT / path).read_text().splitlines()
        assert 1 <= int(first) <= int(last) <= len(lines), (path, first, last)
    nodes = re.findall(r"(tests/[\w./-]+\.py)::([\w:]+)", text)
    assert nodes
    for path, name in nodes:
        definitions = ast.parse((ROOT / path).read_text()).body
        for component in name.split("::"):
            definition = next(
                n
                for n in definitions
                if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                and n.name == component
            )
            if isinstance(definition, ast.ClassDef):
                definitions = definition.body


def test_pack_inventory_and_detector_failure_rows():
    """Six proposed families are distinct from the unchanged external inventory."""
    text = PACK.read_text()
    assert "6 families; 10 implementation/API rows; 0 counted families" in text
    assert "0 external in-package rows" in text
    failures = text.split("## 6. Known failure modes and pitfalls", 1)[1].split(
        "## 7.", 1
    )[0]
    covered = set(range(1, 17)) | {44, 45}
    for line in failures.splitlines():
        match = re.match(r"\| (\d+) \|", line)
        if match and int(match.group(1)) in covered:
            assert "tests/unit/drilling/test_" in line
            assert "no detection check exists" not in line
    assert (
        "Independent physical duration-law qualification remains outside scope" in text
    )


def test_revision_history_keeps_three_columns_and_issue_dates():
    """A failure-row update must not overwrite numbered revision-history rows."""
    from datetime import date

    history = PACK.read_text().split("### Revision history", 1)[1].split("## 1.", 1)[0]
    rows = [line for line in history.splitlines() if re.match(r"\| [0-9]", line)]
    assert rows
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        assert len(cells) == 3
        date.fromisoformat(cells[1])
