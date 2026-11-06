"""Lookup qualification with an independently declared synthetic example.

Column/table names follow data/modules/bsee/atlas/2023/schema.json; these are
in-memory examples, not observations from the public Atlas. The hand-built
relationship is: field ZZ001 contains sands 101 and 102, both assigned to play
7001 (SYN_FAN) and chronozone SYN. CSV row identifiers 2 and 3 represent the
first and second data rows after a header. These numbers are arbitrary fixture
identifiers, not measured quantities or real field associations.

The synthetic public identity table's row alpha independently names the same
field. Its citation is carried in _source; no actual public crosswalk is claimed.
Missing lookup rows or a disagreement with either sand must keep the result
ambiguous despite this confirmed identity. A complete, consistent lookup permits
attribution. Expected evidence below is declared from these relationships,
without using the candidate builder to calculate expectations.
"""

import pytest

from worldenergydata.bsee.atlas import attribute_fields
from worldenergydata.common.fields_registry import load_fields


@pytest.fixture
def lookup_case(tmp_path):
    registry_path = tmp_path / "fields.yml"
    registry_path.write_text(
        "fields:\n"
        "  - canonical_id: synthetic_field\n"
        "    display_name: Synthetic field\n"
    )
    atlas = {
        "2023sands": [
            {
                "_csv_row": 2,
                "SN_FORMSAND": "101",
                "SAND_NAME": "Synthetic sand alpha",
                "BOEM_FIELD": "ZZ001",
                "PLAY_NUM": "7001",
                "PLAY_NAME": "SYN_FAN",
                "CHRONOZONE": "SYN",
            },
            {
                "_csv_row": 3,
                "SN_FORMSAND": "102",
                "SAND_NAME": "Synthetic sand beta",
                "BOEM_FIELD": "ZZ001",
                "PLAY_NUM": "7001",
                "PLAY_NAME": "SYN_FAN",
                "CHRONOZONE": "SYN",
            },
        ],
        "2023plays": [
            {
                "PLAY_NUMBER": "7001",
                "PLAY": "SYN_FAN",
                "PLAY_NAME_DESCRIPTION": "Synthetic fan play",
                "CHRONOZONE": "SYN",
            }
        ],
        "2023chronozones": [
            {
                "BOEM_CHRONOZONE": "SYN",
                "CHRONOZONE_DESCRIPTION": "Synthetic chronozone",
            }
        ],
    }
    return atlas, load_fields(registry_path)


def _attribute_confirmed(lookup_case):
    atlas, registry = lookup_case
    (result,) = attribute_fields(
        atlas,
        [{"name": "Synthetic field", "region": "US Gulf of Mexico", "play": None}],
        registry,
        {"synthetic_field": "ZZ001"},
        public_field_rows=[
            {
                "BOEM_FIELD": "ZZ001",
                "FIELD_NAME": "Synthetic field",
                "_source": "synthetic public identity table, row alpha",
            }
        ],
    )
    # Identity is confirmed in every case, isolating lookup qualification.
    assert result["field_id"] == "synthetic_field"
    assert result["join_basis"] == "confirmed_boem_field"
    assert result["evidence"]["code_match"] == {
        "value": True,
        "source_field": "2023sands.BOEM_FIELD",
    }
    assert result["evidence"]["name_match"] == {
        "value": True,
        "source_field": "synthetic public identity table, row alpha.FIELD_NAME",
    }
    assert result["sand_rows"] == [
        {
            "csv_row": 2,
            "sn_formsand": "101",
            "sand_name": "Synthetic sand alpha",
            "boem_field": "ZZ001",
            "play_number": "7001",
            "chronozone": "SYN",
        },
        {
            "csv_row": 3,
            "sn_formsand": "102",
            "sand_name": "Synthetic sand beta",
            "boem_field": "ZZ001",
            "play_number": "7001",
            "chronozone": "SYN",
        },
    ]
    return result


@pytest.mark.parametrize(
    "missing_tables",
    [
        ("2023plays",),
        ("2023chronozones",),
        ("2023plays", "2023chronozones"),
    ],
    ids=["absent-play", "absent-chronozone", "both-absent"],
)
def test_missing_lookup_cannot_be_attributed(lookup_case, missing_tables):
    atlas, _ = lookup_case
    for table in missing_tables:
        atlas[table].clear()

    result = _attribute_confirmed(lookup_case)

    assert result["status"] == "ambiguous"
    assert set(result["qualifiers"]) == {"missing_lookup"}


@pytest.mark.parametrize(
    ("lookup_column", "conflicting_value"),
    [("PLAY", "SYN_OTHER"), ("CHRONOZONE", "OTHER")],
    ids=["play-label-disagrees", "chronozone-disagrees"],
)
def test_conflicting_lookup_cannot_be_attributed(
    lookup_case, lookup_column, conflicting_value
):
    atlas, _ = lookup_case
    (play,) = atlas["2023plays"]
    play[lookup_column] = conflicting_value

    result = _attribute_confirmed(lookup_case)

    assert result["status"] == "ambiguous"
    assert set(result["qualifiers"]) == {"inconsistent_lookup"}


def test_consistent_lookup_retains_sand_evidence(lookup_case):
    result = _attribute_confirmed(lookup_case)

    assert result["status"] == "attributed"
    assert result["qualifiers"] == []
    assert result["plays"] == [
        {"number": "7001", "code": "SYN_FAN", "description": "Synthetic fan play"}
    ]
    assert result["chronozones"] == [
        {"code": "SYN", "description": "Synthetic chronozone"}
    ]
