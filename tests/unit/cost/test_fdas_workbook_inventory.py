"""Workbook fixtures use independently specified cells and sums, never a solver."""

import hashlib
import json
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from worldenergydata.cost.workbook_reconciliation.workbook_reader import (
    inspect_workbook,
    read_frozen,
    validate_crosswalk,
)

ROOT = Path(__file__).resolve().parents[3]
FDAS = ROOT / "docs/modules/bsee/analysis/production/FDAS_V30"
CONTRACT = ROOT / "config/analysis/lower_tertiary/fdas_workbook_vintages.json"


@pytest.fixture
def workbook(tmp_path):
    path = tmp_path / "fixture.xlsx"
    w = Workbook()
    w.active.append(["period", "cost"])
    w.active.append(["2024-01", 10])
    w.active.append(["2024-02", "=B2+5"])
    w.save(path)
    w.close()
    return path


def test_formula_without_cached_value_is_never_zero(workbook):
    inventory = inspect_workbook(workbook)
    sheet = inventory["sheets"][0]
    assert sheet["formula_cells"] == ["B3"]
    assert sheet["uncached_formula_cells"] == ["B3"]


def test_schema_and_digest_drift(workbook):
    profile = inspect_workbook(workbook)
    assert read_frozen(workbook, profile) == profile
    w = load_workbook(workbook)
    w.active["B1"] = "changed"
    w.save(workbook)
    w.close()
    with pytest.raises(ValueError, match="digest drift"):
        read_frozen(workbook, profile)
    profile["sha256"] = hashlib.sha256(workbook.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="schema drift"):
        read_frozen(workbook, profile)


def test_inventory_excludes_core_properties_and_sheet_names(workbook):
    w = load_workbook(workbook)
    w.properties.creator = "PRIVATE_CREATOR"
    w.active.title = "PRIVATE_SHEET"
    w.save(workbook)
    w.close()
    serialized = json.dumps(inspect_workbook(workbook))
    assert "PRIVATE" not in serialized
    assert "creator" not in serialized


def test_frozen_reference_inventory_and_no_mutation():
    contract = json.loads(CONTRACT.read_text())
    for name, expected in contract["workbooks"].items():
        before = hashlib.sha256((FDAS / name).read_bytes()).hexdigest()
        assert read_frozen(FDAS / name, expected) == expected
        assert before == hashlib.sha256((FDAS / name).read_bytes()).hexdigest()


def test_every_used_cost_cell_has_one_disposition():
    """Set equality proves no missing cell and no duplicated accounting entry."""
    rows = [
        {"cell": "E2", "component": "host", "disposition": "included"},
        {"cell": "J2", "component": "facilities", "disposition": "aggregate"},
    ]
    validate_crosswalk({"E2", "J2"}, rows)
    for invalid in [
        rows[:1],
        rows + rows[:1],
        rows + [{"cell": "K2", "component": "other", "disposition": "excluded"}],
    ]:
        with pytest.raises(ValueError, match="crosswalk"):
            validate_crosswalk({"E2", "J2"}, invalid)
    with pytest.raises(ValueError, match="crosswalk"):
        validate_crosswalk(
            {"E2"}, [{"cell": "E2", "component": "host", "disposition": "guess"}]
        )
