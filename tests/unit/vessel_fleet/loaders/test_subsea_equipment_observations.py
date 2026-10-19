"""Published observations, not interchangeable design inputs.

Expected values are direct transcriptions from the cited sheets; no value is
computed by production code. Removing provenance, filling a gap with zero, or
merging conflicting source revisions must fail these dataset contract tests.
"""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import pytest

DATA = (
    Path(__file__).resolve().parents[4]
    / "packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet"
    / "_data/curated/subsea_equipment_observations.csv"
)
COLUMNS = [
    "observation_id",
    "equipment_class",
    "parameter",
    "value",
    "unit",
    "range",
    "status",
    "source_url",
    "source_document",
    "source_locator",
    "retrieved_on",
    "confidence",
    "notes",
]


@pytest.fixture(scope="module")
def rows():
    with DATA.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == COLUMNS
        return list(reader)


def test_provenance_and_shape(rows):
    assert rows
    assert len({row["observation_id"] for row in rows}) == len(rows)
    for row in rows:
        assert None not in row and None not in row.values()
        for field in COLUMNS:
            assert row[field].strip(), (row["observation_id"], field)
        assert urlparse(row["source_url"]).scheme == "https"
        assert urlparse(row["source_url"]).netloc
        date.fromisoformat(row["retrieved_on"])
        assert row["status"] in {"REPORTED", "NOT_FOUND"}
        if row["status"] == "NOT_FOUND":
            assert row["value"] == "NOT_FOUND"
            assert row["confidence"] == "NOT_EVALUATED"
        else:
            assert row["confidence"] == "A"
            assert row["range"] == "NOT_REPORTED"
            if row["unit"] != "ft_in":
                assert Decimal(row["value"]).is_finite()
                assert Decimal(row["value"]) > 0


@pytest.mark.parametrize(
    "identifier,value,unit",
    [
        ("OVS-EDP-OD", "50", "in"),
        ("OVS-EDP-WEIGHT", "19960", "kg"),
        ("OVS-LRP-WEIGHT", "49895", "kg"),
    ],
)
def test_ovs_published_values(rows, identifier, value, unit):
    """H013638, June 2022, p.2 Equipment Specifications, files/864.

    OD = 50 in; EDP deployed weight = 19,960 kg; LRP deployed weight
    with H4 connector = 49,895 kg. No conversion of the ambiguous 'T' unit.
    """
    row = next(row for row in rows if row["observation_id"] == identifier)
    assert (row["value"], row["unit"]) == (value, unit)
    assert row["source_url"] == "https://www.trendsetterengineering.com/files/864/"
    assert "basis unspecified" in row["notes"] if "WEIGHT" in identifier else True


@pytest.mark.parametrize(
    "identifier,value,unit",
    [
        ("MODULAR-LENGTH", "10 ft 10 in", "ft_in"),
        ("MODULAR-WIDTH", "8 ft 3 in", "ft_in"),
        ("MODULAR-HEIGHT", "15 ft 9 in", "ft_in"),
        ("MODULAR-WEIGHT", "34476", "lb"),
    ],
)
def test_modular_published_values(rows, identifier, value, unit):
    """Trident Modular Intervention System, undated sheet, p.2, files/862.

    The EDP/LRP L x W x H / Weight row is transcribed without conversion.
    Its weight is not silently substituted for either files/864 component.
    """
    row = next(row for row in rows if row["observation_id"] == identifier)
    assert (row["value"], row["unit"]) == (value, unit)
    assert row["source_url"] == "https://www.trendsetterengineering.com/files/862/"
    assert row["equipment_class"] == "EDP_LRP-6_3_8in-15000psi-generation_unstated"
    assert "unresolved" in row["notes"]


def test_gaps_remain_explicit(rows):
    gaps = {row["observation_id"] for row in rows if row["status"] == "NOT_FOUND"}
    assert gaps == {
        "BOP-HEIGHT-GAP",
        "BOP-MASS-GAP",
        "LMRP-HEIGHT-GAP",
        "LMRP-MASS-GAP",
        "SSTT-HEIGHT-GAP",
        "RETAINER-HEIGHT-GAP",
        "THRT-HEIGHT-GAP",
        "SPOOL-HEIGHT-GAP",
        "ADAPTER-HEIGHT-GAP",
    }


def test_weight_basis_is_not_promoted_to_dry_or_submerged_mass(rows):
    weights = [
        row for row in rows if row["parameter"] == "deployed_weight_as_published"
    ]
    assert {row["observation_id"] for row in weights} == {
        "OVS-EDP-WEIGHT",
        "OVS-LRP-WEIGHT",
        "MODULAR-WEIGHT",
    }
    assert all("basis unspecified" in row["notes"] for row in weights)
