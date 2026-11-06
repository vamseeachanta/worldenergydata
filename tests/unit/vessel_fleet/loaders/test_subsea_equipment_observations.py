"""Published observations, not interchangeable design inputs.

Expected values are direct transcriptions from the cited sheets; no value is
computed by production code. Removing provenance, filling a gap with zero, or
merging conflicting source revisions must fail these dataset contract tests.
"""

import csv
import re
from datetime import date, timedelta
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
        assert urlparse(row["source_url"]).scheme == "https", (
            row["observation_id"],
            "invalid source_url",
        )
        assert urlparse(row["source_url"]).netloc, (
            row["observation_id"],
            "invalid source_url",
        )
        assert date.fromisoformat(row["retrieved_on"]) <= date.today(), (
            row["observation_id"],
            "invalid retrieved_on",
        )
        assert row["unit"] in {"in", "ft", "ft_in", "kg", "lb", "NOT_TRANSCRIBED"}, (
            row["observation_id"],
            "invalid unit",
        )
        if row["unit"] == "NOT_TRANSCRIBED":
            assert row["status"] == "NOT_TRANSCRIBED", (
                row["observation_id"],
                "invalid unit",
            )
        assert row["status"] in {"REPORTED", "NOT_FOUND", "NOT_TRANSCRIBED"}, (
            row["observation_id"],
            "invalid status",
        )
        if row["status"] in {"NOT_FOUND", "NOT_TRANSCRIBED"}:
            assert row["value"] == row["status"], (
                row["observation_id"],
                "invalid value",
            )
            assert row["confidence"] == "NOT_EVALUATED", (
                row["observation_id"],
                "invalid confidence",
            )
        else:
            assert row["confidence"] == "A", (
                row["observation_id"],
                "invalid confidence",
            )
            if row["unit"] == "ft_in":
                assert re.fullmatch(r"\d+ ft \d+ in", row["value"]), (
                    row["observation_id"],
                    "invalid value",
                )
            else:
                assert Decimal(row["value"]).is_finite(), (
                    row["observation_id"],
                    "invalid value",
                )
                assert Decimal(row["value"]) > 0, (
                    row["observation_id"],
                    "invalid value",
                )
        assert row["range"] == "NOT_REPORTED", (
            row["observation_id"],
            "invalid range",
        )


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
def test_component_weight_provenance(rows, identifier, entry, includes_connector):
    row = next(row for row in rows if row["observation_id"] == identifier)
    assert row["source_locator"] == f"p.2 Equipment Specifications; {entry}"
    assert ("H4 connector" in row["notes"]) is includes_connector
    if identifier == "OVS-EDP-WEIGHT":
        assert "LRP" not in row["notes"]
        assert "H4" not in row["notes"]
    else:
        assert "LRP includes H4 connector" in row["notes"]


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
    assert "EDP / LRP as labelled; combined or per-module not stated" in row["notes"]
    if identifier == "MODULAR-WEIGHT":
        assert "basis unspecified" in row["notes"]
    else:
        assert "basis" not in row["notes"].lower()
        assert "dry" not in row["notes"].lower()
        assert "submerged" not in row["notes"].lower()


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
    elif identifier == "BOP-HEIGHT-GAP":
        assert "assembly boundaries" in row["notes"]
    else:
        assert "in air" in row["notes"]
        assert "ton type" in row["notes"]


def test_known_research_is_untranscribed_not_missing(rows):
    pending = {
        row["observation_id"]: row for row in rows if row["status"] == "NOT_TRANSCRIBED"
    }
    assert set(pending) == {"BOP-HEIGHT-GAP", "BOP-MASS-GAP", "LMRP-MASS-GAP"}
    assert all(row["range"] == "NOT_REPORTED" for row in pending.values())


def test_published_weight_parameters_preserve_the_source_labels(rows):
    parameters = {
        row["observation_id"]: row["parameter"]
        for row in rows
        if row["status"] == "REPORTED" and "WEIGHT" in row["observation_id"]
    }
    assert parameters == {
        "OVS-EDP-WEIGHT": "deployed_weight_as_published",
        "OVS-LRP-WEIGHT": "deployed_weight_as_published",
        "MODULAR-WEIGHT": "weight_as_published",
    }


def test_unspecified_weight_basis_is_not_promoted_to_mass(rows):
    for row in rows:
        if re.search(r"basis.*(?:unspecified|unstated)", row["notes"], re.IGNORECASE):
            assert row["parameter"] not in {"dry_mass", "submerged_mass"}, row[
                "observation_id"
            ]
    bop = next(row for row in rows if row["observation_id"] == "BOP-MASS-GAP")
    assert bop["parameter"] == "weight_as_published"


@pytest.mark.parametrize("identifier", ["BOP-MASS-GAP", "LMRP-MASS-GAP"])
def test_unconfirmed_weight_units_are_not_assigned_a_mass_unit(rows, identifier):
    row = next(row for row in rows if row["observation_id"] == identifier)
    assert row["status"] == "NOT_TRANSCRIBED"
    assert row["unit"] == "NOT_TRANSCRIBED"
    assert row["parameter"] == "weight_as_published"
    if identifier == "BOP-MASS-GAP":
        assert "source units require confirmation" in row["notes"]
        assert "no force-to-mass conversion" in row["notes"]
    else:
        assert "ton type" in row["notes"]
        assert "no ton-to-kilogram conversion" in row["notes"]


@pytest.mark.parametrize(
    "identifier,field,value",
    [
        ("MODULAR-LENGTH", "unit", "kgs"),
        ("MODULAR-LENGTH", "unit", "NOT_TRANSCRIBED"),
        ("MODULAR-LENGTH", "value", "10ft 10in"),
        (
            "MODULAR-LENGTH",
            "retrieved_on",
            (date.today() + timedelta(days=1)).isoformat(),
        ),
        ("MODULAR-LENGTH", "status", "UNKNOWN"),
        ("MODULAR-WEIGHT", "value", "NaN"),
        ("MODULAR-WEIGHT", "value", "Infinity"),
        ("MODULAR-WEIGHT", "value", "0"),
        ("MODULAR-WEIGHT", "value", "-1"),
        ("MODULAR-LENGTH", "source_url", "http://example.org/source"),
        ("MODULAR-LENGTH", "source_url", "https:/source"),
        ("LMRP-HEIGHT-GAP", "value", "1"),
        ("BOP-HEIGHT-GAP", "value", "1"),
        ("MODULAR-LENGTH", "confidence", "B"),
        ("LMRP-HEIGHT-GAP", "confidence", "A"),
        ("BOP-HEIGHT-GAP", "confidence", "A"),
        ("MODULAR-LENGTH", "range", "0"),
        ("LMRP-HEIGHT-GAP", "range", "0"),
        ("BOP-HEIGHT-GAP", "range", "0"),
    ],
)
def test_provenance_and_shape_rejects_invalid_metadata(rows, identifier, field, value):
    row = next(row for row in rows if row["observation_id"] == identifier)
    with pytest.raises(AssertionError, match=f"invalid {field}"):
        test_provenance_and_shape([{**row, field: value}])
