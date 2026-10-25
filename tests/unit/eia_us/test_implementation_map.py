"""Contracts for the EIA US enrollment proposal and synthetic boundary."""

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path("packages/worldenergydata-eia_us/src/worldenergydata/eia_us")
MAP = ROOT / PACKAGE / "docs/implementation-map.json"


def definitions(content):
    """Resolve qualified symbols without importing the enrolled implementation."""
    tree = ast.parse(content)
    found = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            found[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    found[f"{node.name}.{child.name}"] = child
    return found


def test_enrollment_covers_every_method_and_preserves_pin():
    inventory = json.loads(MAP.read_text())
    assert inventory["status"] == "pending_review"
    assert re.fullmatch(r"[0-9a-f]{40}", inventory["revision"])
    assert {f["id"] for f in inventory["families"]} == {
        "retrieval-cache",
        "normalisation-aggregation",
        "decline",
        "fiscal",
        "production-crosscheck",
    }
    expected = {
        (str(path.relative_to(ROOT)), symbol)
        for path in (ROOT / PACKAGE).rglob("*.py")
        for symbol in definitions(path.read_bytes())
    }
    entries = [row for f in inventory["families"] for row in f["implementations"]]
    assert {(row["path"], row["symbol"]) for row in entries} == expected
    assert len(entries) == len(expected)
    for family in inventory["families"]:
        assert family["counted"] is False
        assert family["qualification"] == "NOT_EVALUATED"
    for row in entries + inventory["overlaps"]:
        content = (ROOT / row["path"]).read_bytes()
        node = definitions(content)[row["symbol"]]
        assert row["line"] == node.lineno
        assert row["end_line"] == node.end_lineno
        assert hashlib.sha256(content).hexdigest() == row["file_sha256"]
        assert row["relation"] in {"independent", "delegates", "helper"}
        assert row["basis"]
        assert row["targets"] or row["relation"] != "delegates"


def test_discovery_evidence_matches_tracked_sources():
    """Compare pinned hit sets with maintained sources, also in shallow CI.

    The new contract test is excluded because it consumes all family names.
    Historical replay uses search.command separately; Git objects at the source
    pin need not be available in a shallow checkout of the resulting change.
    """
    inventory = json.loads(MAP.read_text())
    for family in inventory["families"]:
        search = family["search"]
        result = subprocess.run(
            [
                "git",
                "grep",
                "-l",
                "-E",
                search["pattern"],
                "--",
                "*.py",
                ":(exclude)tests/unit/eia_us/test_implementation_map.py",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode in (0, 1)
        paths = set(result.stdout.splitlines())
        assert paths == {row["path"] for row in search["results"]}
        assert all(row["classification"] for row in search["results"])


def test_dpr_independent_arithmetic_and_delegation(monkeypatch):
    """Synthetic addition, not a measured or calibrated DPR example.

    basin_production.py, BasinRecord.net_change_bopd, and
    drilling_productivity.py, net_change_summary, at the inventory pin:
    new contribution 120 bbl/day plus legacy change -45 bbl/day = 75 bbl/day.
    Both operands and the expected sum are explicit hand-calculation inputs.
    No numerical acceptance tolerance is needed for these exact integers.
    """
    from worldenergydata.eia_us.production.basin_production import BasinRecord
    from worldenergydata.eia_us.production.drilling_productivity import (
        DrillingProductivityReport,
    )

    record = BasinRecord("2024-01", "synthetic-region", 1, 120, -45, 900)
    report = DrillingProductivityReport()
    supplied = [{"sentinel": "caller-supplied"}]
    sentinel = pd.DataFrame({"sentinel": ["loader-result"]})

    def loader(records):
        assert records is supplied
        return sentinel

    monkeypatch.setattr(report._loader, "load", loader)
    assert report.load_all_basins(supplied) is sentinel
    df = pd.DataFrame([record.__dict__])
    assert record.net_change_bopd == 75
    assert report.net_change_summary(df)["net_change_bopd"].tolist() == [75]


def test_adapter_provenance_without_loader_calls(monkeypatch):
    """An adapter success must survive loaders that reject every call.

    The synthetic table is replaced with neutral inputs. Only source labels and
    routing/filter behavior are checked; no production magnitude is qualified.
    """
    from worldenergydata.eia_us.client.eia_api import EIAApiClient
    from worldenergydata.eia_us.international.country_production import (
        CountryProductionLoader,
    )
    from worldenergydata.eia_us.production.alaska_production import (
        AlaskaProductionLoader,
    )
    from worldenergydata.eia_us.production.basin_production import BasinProductionLoader
    from worldenergydata.eia_us.production.drilling_productivity import (
        DrillingProductivityReport,
    )
    from worldenergydata.eia_us.production.state_production import StateProductionLoader
    from worldenergydata.production.unified.adapters.eia_us_adapter import EiaUsAdapter
    from worldenergydata.production.unified.query import ProductionQuery

    def forbidden(*args, **kwargs):
        pytest.fail("Synthetic adapter called an EIA US loader or series client")

    for cls in (
        CountryProductionLoader,
        AlaskaProductionLoader,
        BasinProductionLoader,
        StateProductionLoader,
    ):
        monkeypatch.setattr(cls, "load", forbidden)
    monkeypatch.setattr(DrillingProductivityReport, "load_all_basins", forbidden)
    monkeypatch.setattr(EIAApiClient, "fetch_series", forbidden)
    # Magnitudes and calendar are arbitrary synthetic fixture inputs.
    monkeypatch.setattr(
        EiaUsAdapter,
        "_FIELDS",
        [
            ("synthetic-region", 48, 48, 48, 48, 2024, 1, 2),
        ],
    )
    df = EiaUsAdapter().fetch(
        ProductionQuery(
            regions=["eia_us"],
            fields=["SYNTHETIC-REGION"],
            start="2024-02",
            end="2024-02",
        )
    )
    assert df["source"].tolist() == ["eia_us_mock"]
    assert df["region"].tolist() == ["eia_us"]
    assert df["field_name"].tolist() == ["synthetic-region"]
    assert df["month"].tolist() == [2]
