"""Offline contract tests using small slices of published BSEE files."""

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from worldenergydata.bsee.lease_ingest import curate, load_table, registry_check
from worldenergydata.common.fields_registry import load_fields

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "tests/fixtures/bsee/leases"
SCHEMA = json.loads((ROOT / "data/modules/bsee/leases/source_schema.json").read_text())


def tables() -> dict[str, Any]:
    return {
        kind: load_table(
            FIXTURE / (spec["archive"] if kind == "lease" else spec["member"]), spec
        )
        for kind, spec in SCHEMA["tables"].items()
    }


def test_loader_validates_real_layout_and_types() -> None:
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
def test_loader_rejects_malformed(tmp_path: Path, content: str) -> None:
    path = tmp_path / "bad.txt"
    path.write_text(content)
    with pytest.raises(ValueError):
        load_table(path, SCHEMA["tables"]["owner"])


def test_curated_dates_owners_and_history() -> None:
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


def test_group_identity_and_no_owner_operator_multiplication() -> None:
    data = tables()
    extra = dict(data["owner"][0], SN_LSE_OWNER="999999", OWNER_GROUP_CODE="2")
    data["owner"].append(extra)
    data["operator"].append(dict(data["operator"][0]))
    result = curate(data, ["G16942"])
    assert len(result["owners"]) == 5
    assert result["leases"][0]["gwi_pct"] == [27.5, 12.5, 60.0, 27.5]
    assert result["panel_values"][0]["current_owners"][-1]["OWNER_GROUP_CODE"] == "2"


def test_missing_source_and_company_are_explicit() -> None:
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


def test_registry_round_trip_and_unknown_reason() -> None:
    registry = load_fields(ROOT / "config/fields.yml")
    result = registry_check(["G16942", "OCS-G 16942", "G99999"], registry)
    assert [row["field_id"] for row in result[:2]] == ["big_foot", "big_foot"]
    assert result[2] == {
        "lease_num": "G99999",
        "field_id": None,
        "reason": "Lease absent from canonical registry",
    }


def test_every_committed_lease_round_trips_through_by_lease() -> None:
    directory = ROOT / "data/modules/bsee/leases"
    leases = json.loads((directory / "leases.json").read_text())
    manifest = json.loads((directory / "extract_manifest.json").read_text())
    registry = load_fields(ROOT / "config/fields.yml")
    assert len(leases) == manifest["leases_ingested"]
    numbers = [row["lease_num"] for row in leases]
    result = registry_check(numbers, registry)
    assert all(registry.by_lease(number) is not None for number in numbers)
    assert all(row["field_id"] is not None and row["reason"] is None for row in result)
    assert result == json.loads((directory / "registry.json").read_text())


def test_committed_extract_integrity_and_complete_inventory() -> None:
    directory = ROOT / "data/modules/bsee/leases"
    manifest = json.loads((directory / "extract_manifest.json").read_text())
    for record in manifest["artifacts"]:
        content = (directory / record["file"]).read_bytes()
        assert len(content) == record["size_bytes"]
        assert hashlib.sha256(content).hexdigest() == record["sha256"]
    assert hashlib.sha256(
        (directory / "source_manifest.json").read_bytes()
    ).hexdigest() == (manifest["source_manifest_sha256"])
    exceptions = {"README.md", "source_manifest.json", "extract_manifest.json"}
    assert {path.name for path in directory.iterdir() if path.is_file()} == (
        {record["file"] for record in manifest["artifacts"]} | exceptions
    )


def test_company_history_selects_unique_unterminated_name() -> None:
    result = curate(tables(), ["G16942"])
    assert result["leases"][0]["operator"] == ["Chevron U.S.A. Inc."]
    assert result["owners"][0]["owner_name"] == "Equinor US Offshore EP LLC"


def test_csv_multiline_and_blank_assignment_status(tmp_path: Path) -> None:
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


def test_custom_output_contains_the_manifested_schema(tmp_path: Path) -> None:
    import runpy

    script = runpy.run_path(str(ROOT / "scripts/bsee/fetch_leases.py"))
    path, schema = script["prepare_schema"](tmp_path)
    assert path == tmp_path / "source_schema.json"
    assert schema == SCHEMA
    assert (
        path.read_bytes()
        == (ROOT / "data/modules/bsee/leases/source_schema.json").read_bytes()
    )


def test_extract_renders_and_manifests_panel_from_same_rows(tmp_path: Path) -> None:
    import runpy

    script = runpy.run_path(str(ROOT / "scripts/bsee/fetch_leases.py"))
    schema_path, _ = script["prepare_schema"](tmp_path)
    (tmp_path / "source_manifest.json").write_text("{}\n")
    data = tables()
    result = curate(data, ["G16942"])
    result["registry"] = registry_check(
        ["G16942"], load_fields(ROOT / "config/fields.yml")
    )
    script["save_extract"](tmp_path, schema_path, data, ["G16942"], result)
    html = (tmp_path / "panel_values.html").read_text()
    assert "WR029" in html and "PROD" in html
    assert "2006-08-31" in html and "1996-09-01" in html
    assert "Equinor US Offshore EP LLC" in html and "27.5" in html
    manifest = json.loads((tmp_path / "extract_manifest.json").read_text())
    record = next(
        row for row in manifest["artifacts"] if row["file"] == "panel_values.html"
    )
    content = (tmp_path / record["file"]).read_bytes()
    assert record["size_bytes"] == len(content)
    assert record["sha256"] == hashlib.sha256(content).hexdigest()


PANEL_HEADERS = [
    "Lease",
    "Area/block",
    "Status",
    "Lease effective date",
    "Actual expiration date",
    "Expected expiration date",
    "Current owner assignment interest (%)",
]


class PanelParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[list[str]]] = []
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag == "tr":
            self.rows.append([])
        elif tag in {"th", "td"}:
            self.cell = [""]
            self.rows[-1].append(self.cell)
        elif tag == "br" and self.cell is not None:
            self.cell.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"}:
            self.cell = None

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell[-1] += data


def parse_panel(path: Path) -> PanelParser:
    page = PanelParser()
    page.feed(path.read_text())
    assert [cell[0] for cell in page.rows[0]] == PANEL_HEADERS
    for row in page.rows:
        for cell in row:
            for line in cell:
                assert not any(
                    token in line
                    for token in (
                        "[{",
                        '{"',
                        '"}',
                        "OWNER_ALIQUOT_CD",
                        "SN_LSE_OWNER",
                        "ASSIGNMENT_PCT",
                        "owner_name_basis",
                        "current_owners",
                        "lease_num",
                        "OWNER_GROUP_CODE",
                        "owner_name_reason",
                    )
                )
    return page


def test_panel_owner_lines_escape_names_and_expose_missing_reason(
    tmp_path: Path,
) -> None:
    import runpy

    script = runpy.run_path(str(ROOT / "scripts/bsee/fetch_leases.py"))
    rows = curate(tables(), ["G16942"])["panel_values"]
    rows[0]["current_owners"][0]["OWNER_GROUP_CODE"] = "2"
    rows[0]["current_owners"].append(
        {
            "SN_LSE_OWNER": "999",
            "OWNER_GROUP_CODE": None,
            "owner_name": "BP Exploration & Production Inc.",
            "ASSIGNMENT_PCT": 0.0,
        }
    )
    rows.append({"lease_num": "G99999", "current_owners": []})
    rows.append(
        {
            "lease_num": "G99998",
            "current_owners": [
                {
                    "SN_LSE_OWNER": "998",
                    "OWNER_GROUP_CODE": None,
                    "owner_name": None,
                    "owner_name_reason": "Company number absent from Company (All)",
                    "ASSIGNMENT_PCT": 100.0,
                }
            ],
        }
    )
    script["save_panel_html"](tmp_path, rows)
    page = parse_panel(tmp_path / "panel_values.html")
    assert page.rows[1][-1] == [
        "312242 / group 2 / Equinor US Offshore EP LLC: 27.5%",
        "312241 / ME Bigfoot, LLC: 12.5%",
        "312240 / Chevron U.S.A. Inc.: 60.0%",
        "999 / BP Exploration & Production Inc.: 0.0%",
    ]
    assert page.rows[2][-1] == ["Not reported"]
    assert page.rows[3][-1] == [
        "998 / Company number absent from Company (All): 100.0%"
    ]


def test_committed_panel_has_twenty_readable_lease_rows() -> None:
    page = parse_panel(ROOT / "data/modules/bsee/leases/panel_values.html")
    assert len(page.rows) == 21
    assert page.rows[1][-1] == [
        "312242 / Equinor US Offshore EP LLC: 27.5%",
        "312241 / ME Bigfoot, LLC: 12.5%",
        "312240 / Chevron U.S.A. Inc.: 60.0%",
    ]
