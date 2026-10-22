"""BH-map-1 independent membership check for #1337.

Three in-package entry points form three families; the independent collector
and export caller form one outside-package family. Counts enumerate the
explicit sets below, not the historical external registry.
"""

import ast
import json
from pathlib import Path


def test_map_covers_entry_points():
    root = Path(__file__).resolve().parents[3]
    mapping = json.loads(
        (root / "docs/modules/baker_hughes-implementation-map.json").read_text()
    )
    assert mapping["revision"] == "BH-map-1"
    inside = [f for f in mapping["families"] if f["scope"] == "in-package"]
    outside = [f for f in mapping["families"] if f["scope"] == "outside-package"]
    assert {f["id"] for f in inside} == {
        "pivot-ingestion",
        "summary-ingestion",
        "ingestion-report",
    }
    assert {f["id"] for f in outside} == {"independent-workbook-export"}
    assert {s["symbol"] for f in inside for s in f["implementations"]} == {
        "load_pivot_table",
        "load_summary",
        "generate_report",
    }
    assert {s["symbol"] for f in outside for s in f["implementations"]} == {
        "BakerHughesCollector.download_na_rig_count",
        "BakerHughesCollector.download_international_rig_count",
        "export_baker_hughes",
        "main",
    }
    for family in mapping["families"]:
        for item in family["implementations"]:
            tree = ast.parse((root / item["path"]).read_text())
            nodes = tree.body
            for part in item["symbol"].split("."):
                node = next(n for n in nodes if getattr(n, "name", None) == part)
                nodes = getattr(node, "body", [])
        for node_id in family["tests"]:
            path, function = node_id.split("::")
            tree = ast.parse((root / path).read_text())
            assert function in {
                n.name for n in tree.body if isinstance(n, ast.FunctionDef)
            }
