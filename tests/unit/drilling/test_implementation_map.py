"""Evidence checks for the package-local mobilization allocation enrollment."""

import ast
import hashlib
import json
import re
from pathlib import Path

import pytest

from worldenergydata.drilling import BatchDrillingEconomics

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path("packages/worldenergydata-drilling/src/worldenergydata/drilling")
MAP = ROOT / PACKAGE / "docs/implementation-map.json"


def test_mobilization_enrollment_pin():
    """Enrollment identifies the actual definition and its recorded current bytes."""
    inventory = json.loads(MAP.read_text())
    assert inventory["repository"] == "worldenergydata"
    (family,) = inventory["families"]
    assert family["id"] == "mobilization-allocation"
    assert family["counted"] is False
    assert family["status"] == "pending_review"
    (entry,) = family["implementations"]
    current = (ROOT / entry["path"]).read_bytes()
    assert re.fullmatch(r"[0-9a-f]{40}", inventory["revision"])
    assert hashlib.sha256(current).hexdigest() == entry["file_sha256"]
    tree = ast.parse(current)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    method = next(
        node
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == "mobilization_savings"
    )
    assert entry["symbol"] == f"{cls.name}.{method.name}"
    assert entry["line"] == method.lineno
    assert entry["end_line"] == method.end_lineno
    for evidence in family["tests"]:
        path, node = evidence.split("::")
        definitions = ast.parse((ROOT / path).read_text()).body
        assert any(
            isinstance(n, ast.FunctionDef) and n.name == node for n in definitions
        )
    assert family["equation"] == "allocated_cost_usd_per_well = mob_cost_usd / n_wells"
    assert family["source"]["section"] == "2.2, Average fixed cost"


def test_mobilization_discovery_evidence():
    """Check retained search evidence without requiring historical Git objects.

    The recorded command replays the search in a full checkout. File digests
    and AST classifications also work in shallow CI checkouts.
    """
    inventory = json.loads(MAP.read_text())
    discovery = inventory["families"][0]["duplicate_discovery"]
    for item in discovery["results"]:
        content = (ROOT / item["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == item["file_sha256"]
        assert re.search(discovery["pattern"], content.decode())
        tree = ast.parse(content)
        definitions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "mobilization_savings"
        ]
        if item["classification"] == "implementation":
            assert item["path"].endswith("/batch_economics/economics.py")
            assert len(definitions) == 1
        else:
            assert item["classification"] == "test_consumer"
            assert item["path"].startswith("tests/")
            assert not definitions
            assert any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "mobilization_savings"
                for node in ast.walk(tree)
            )


@pytest.mark.parametrize(
    "cost,wells,expected", [(1200, 1, 1200), (1200, 3, 400), (0, 3, 0)]
)
def test_mobilization_hand_calculation(cost, wells, expected):
    """OpenStax, Principles of Accounting Vol. 2 (2019), section 2.2, AFC.

    Equal fixed-cost allocation: total fixed cost divided by unit count.
    Synthetic inputs in USD and wells: 1200/1 = 1200; 1200/3 = 400;
    0/3 = 0 USD/well. These are arithmetic examples, not field calibration.
    All quotients are exactly representable, so equality needs no tolerance.
    """
    assert BatchDrillingEconomics().mobilization_savings(cost, wells) == expected


@pytest.mark.parametrize("wells", [0, -1])
def test_mobilization_nonpositive_count(wells):
    """economics.py, mobilization_savings guard at the enrolled pin rejects N<=0.

    Zero and minus one exercise the boundary and a representative invalid count;
    1200 USD is the synthetic fixed cost from the hand calculation above.
    """
    with pytest.raises(ValueError, match="n_wells_batch"):
        BatchDrillingEconomics().mobilization_savings(1200, wells)
