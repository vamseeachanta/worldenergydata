"""Offline contract tests using small slices of published BSEE files."""

import json
from pathlib import Path

import pytest

from worldenergydata.bsee.lease_ingest import curate, load_table, registry_check
from worldenergydata.common.fields_registry import load_fields

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "tests/fixtures/bsee/leases"
SCHEMA = json.loads((ROOT / "data/modules/bsee/leases/source_schema.json").read_text())


def tables():
    return {
        kind: load_table(
            FIXTURE / (spec["archive"] if kind == "lease" else spec["member"]), spec
        )
        for kind, spec in SCHEMA["tables"].items()
    }


def test_loader_validates_real_layout_and_types():
    data = tables()
    assert data["owner"][0]["ASSIGNMENT_PCT"] == 27.5
    assert data["owner"][0]["ASGN_APRV_DATE"] == "2026-07-28"
    assert data["lease"][0]["Lease Number"] == "G16942"


@pytest.mark.parametrize(
    "content",
    [
        '"G16942","bad"\n',
        '"1","312242","20260230","20040727","02748","G16942","C","","","27.5","20250701"\n',
        '"1","312242","20260728","20040727","02748","G16942","C","","","NaN","20250701"\n',
        '"1","312242","20260728","20040727","02748","G16942","C","","","101","20250701"\n',
    ],
)
def test_loader_rejects_malformed(tmp_path, content):
    path = tmp_path / "bad.txt"
    path.write_text(content)
    with pytest.raises(ValueError):
        load_table(path, SCHEMA["tables"]["owner"])


def test_curated_dates_owners_and_history():
    result = curate(tables(), ["G16942"])
    lease = result["leases"][0]
    assert lease["lease_num"] == "G16942"
    assert lease["status"] == "PROD"
    assert lease["effective_date"] == "1996-09-01"
    assert lease["approval_date"] == ["2026-07-28"] * 3
    assert lease["gwi_pct"] == [27.5, 12.5, 60.0]
    assert len(result["owners"]) == 4
    assert result["owners"][3]["ASGN_STATUS_CODE"] == "T"
    assert len(result["panel_values"][0]["current_owners"]) == 3
    assert lease["operator"] == ["Chevron U.S.A. Inc."]
    assert result["panel_values"][0]["current_owners"][0]["owner_name"]


def test_group_identity_and_no_owner_operator_multiplication():
    data = tables()
    extra = dict(data["owner"][0], SN_LSE_OWNER="999999", OWNER_GROUP_CODE="2")
    data["owner"].append(extra)
    data["operator"].append(dict(data["operator"][0]))
    result = curate(data, ["G16942"])
    assert len(result["owners"]) == 5
    assert result["leases"][0]["gwi_pct"] == [27.5, 12.5, 60.0, 27.5]
    assert result["panel_values"][0]["current_owners"][-1]["OWNER_GROUP_CODE"] == "2"


def test_missing_source_and_company_are_explicit():
    data = tables()
    data["company"] = []
    result = curate(data, ["G16942", "G99999"])
    assert result["missing"] == [
        {"lease_num": "G99999", "reason": "Lease absent from Lease Data package"}
    ]
    assert result["owners"][0]["owner_name"] is None
    assert (
        result["owners"][0]["owner_name_reason"]
        == "Company number absent from Company (All)"
    )


def test_registry_round_trip_and_unknown_reason():
    registry = load_fields(ROOT / "config/fields.yml")
    result = registry_check(["G16942", "OCS-G 16942", "G99999"], registry)
    assert [row["field_id"] for row in result[:2]] == ["big_foot", "big_foot"]
    assert result[2] == {
        "lease_num": "G99999",
        "field_id": None,
        "reason": "Lease absent from canonical registry",
    }


def test_company_history_selects_unique_unterminated_name():
    result = curate(tables(), ["G16942"])
    assert result["leases"][0]["operator"] == ["Chevron U.S.A. Inc."]
    assert result["owners"][0]["owner_name"] == "Equinor US Offshore EP LLC"


def test_csv_multiline_and_blank_assignment_status(tmp_path):
    path = tmp_path / "company.txt"
    text = (FIXTURE / "compalldelimit.txt").read_text()
    text = text.replace("California Oil Company", "California\nOil Company")
    path.write_text(text)
    assert (
        load_table(path, SCHEMA["tables"]["company"])[0]["BUS_ASC_NAME"]
        == "California\nOil Company"
    )
    data = tables()
    data["owner"][0]["ASGN_STATUS_CODE"] = None
    assert len(curate(data, ["G16942"])["panel_values"][0]["current_owners"]) == 2


def test_custom_output_contains_the_manifested_schema(tmp_path):
    import runpy

    script = runpy.run_path(str(ROOT / "scripts/bsee/fetch_leases.py"))
    path, schema = script["prepare_schema"](tmp_path)
    assert path == tmp_path / "source_schema.json"
    assert schema == SCHEMA
    assert (
        path.read_bytes()
        == (ROOT / "data/modules/bsee/leases/source_schema.json").read_bytes()
    )
