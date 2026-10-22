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
        assert row["status"] in {"REPORTED", "NOT_FOUND", "NOT_TRANSCRIBED"}
        if row["status"] in {"NOT_FOUND", "NOT_TRANSCRIBED"}:
            assert row["value"] == row["status"]
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
    if "WEIGHT" in identifier:
        assert "basis unspecified" in row["notes"]


@pytest.mark.parametrize(
    "identifier,entry,includes_connector",
    [
        ("OVS-EDP-WEIGHT", "EDP Deployed Weight", False),
        ("OVS-LRP-WEIGHT", "LRP Deployed Weight with H4 Connector", True),
    ],
)
def test_ovs_weights_identify_the_component_entry(
    rows, identifier, entry, includes_connector
):
    row = next(row for row in rows if row["observation_id"] == identifier)
    assert row["source_locator"] == f"p.2 Equipment Specifications; {entry}"
    assert ("H4 connector" in row["notes"]) is includes_connector


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
        "LMRP-HEIGHT-GAP",
        "SSTT-HEIGHT-GAP",
        "RETAINER-HEIGHT-GAP",
        "THRT-HEIGHT-GAP",
        "SPOOL-HEIGHT-GAP",
        "ADAPTER-HEIGHT-GAP",
    }


@pytest.mark.parametrize(
    "identifier,research_rows",
    [
        ("BOP-HEIGHT-GAP", "row 19"),
        ("BOP-MASS-GAP", "rows 1; 4; 19"),
        ("LMRP-MASS-GAP", "row 20"),
    ],
)
def test_known_research_findings_are_untranscribed_not_absent(
    rows, identifier, research_rows
):
    """The #1140 research record distinguishes published leads from gaps."""
    row = next(row for row in rows if row["observation_id"] == identifier)
    assert (row["status"], row["value"]) == ("NOT_TRANSCRIBED", "NOT_TRANSCRIBED")
    assert row["source_url"] == (
        "https://api.github.com/repositories/574746314/issues/comments/6111983634"
    )
    assert row["source_document"] == "Research record #1140; 2026-10-11"
    assert row["source_locator"] == f"2026-10-11 research record; {research_rows}"
    assert "#1140" in row["notes"]
    assert "NOT_EVALUATED" in row["notes"]
    if identifier == "BOP-MASS-GAP":
        assert "Restricted" in row["notes"]


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
