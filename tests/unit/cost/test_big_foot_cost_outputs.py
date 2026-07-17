"""Deterministic Big Foot cost-map evidence-pack contract."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = ROOT / "scripts/cost/build_big_foot_cost_map.py"
HTML_PATH = ROOT / "reports/cost/big_foot_cost_map.html"
CSV_PATH = ROOT / "reports/cost/big_foot_cost_map_reconciliation.csv"
MANIFEST_PATH = ROOT / "data/modules/cost/curated/cost_map_contract_manifest.v1.json"
FDAS = ROOT / "docs/modules/bsee/analysis/production/FDAS_V30"
WORKBOOK_HASHES = {
    "lease_assumptions.xlsx": "a1193f669db49ac33b87481733fb13af409844fed890e763b4e8726e329a1407",
    "financial_project_summary.xlsx": "00f200def283d307293bb93033f070718722618b9a8ace2bbbe11bfbffeddf04",
    "drilling_and_completion_days.xlsx": "3ecfa1128b33edf73db3a793f8839c98c50bc27184487a8af579c5ef22795e7f",
}


def _builder():
    spec = importlib.util.spec_from_file_location("big_foot_builder", BUILDER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build(tmp_path: Path):
    output = tmp_path / "output"
    output.mkdir(parents=True)
    _builder().build_outputs(
        repo_root=ROOT,
        output_root=output,
        source_date_epoch=1_700_000_000,
        producer_commit="1a74d78",
    )
    return output


def _text(output: Path) -> str:
    return (output / "reports/cost/big_foot_cost_map.html").read_text()


def _manifest(output: Path) -> dict:
    return json.loads(
        (
            output / "data/modules/cost/curated/cost_map_contract_manifest.v1.json"
        ).read_text()
    )


def _csv_rows(output: Path) -> list[dict[str, str]]:
    path = output / "reports/cost/big_foot_cost_map_reconciliation.csv"
    return list(csv.DictReader(path.open(encoding="utf-8", newline="")))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_big_foot_output_contains_all_required_accounting_lanes(tmp_path: Path) -> None:
    output = _build(tmp_path)
    text = _text(output)
    rows = _csv_rows(output)

    for requirement_id in (f"req-{number:06d}" for number in range(1, 9)):
        assert requirement_id in text
    assert {row["direction"] for row in rows} == {
        "project_to_asset",
        "asset_to_project",
    }
    assert {
        row["total_event_id"]
        for row in rows
        if row["row_kind"] in {"observed_component", "scenario_allocation"}
    } == {
        "evt-000003",
        "evt-000004",
    }
    assert "eligible" in text and "excluded" in text and "overlap" in text
    assert "residual" in text and "unallocated" in text and "variance" in text


def test_observed_and_allocated_values_are_visually_and_semantically_distinct(
    tmp_path: Path,
) -> None:
    output = _build(tmp_path)
    text = _text(output)
    rows = _csv_rows(output)

    assert 'class="observed"' in text and 'class="allocated"' in text
    assert "assumed" in text and "proposed" in text and "low confidence" in text
    assert "reuse_allowed=false" in text
    assert {row["evidence_derivation"] for row in rows} >= {"disclosed", "allocated"}
    proposed = [row for row in rows if row["scenario_status"] == "proposed"]
    assert proposed and {row["reuse_allowed"] for row in proposed} == {"false"}
    assert {
        (row["scenario_id"], row["value_low_mm"], row["value_high_mm"])
        for row in rows
        if row["row_kind"] == "implied_project_total"
    } == {
        ("reference", "750.00", "750.00"),
        ("host_heavy", "900.00", "900.00"),
        ("well_heavy", "642.85", "642.86"),
    }
    assert not any(
        row["direction"] == "asset_to_project" and row["award_id"] == "awd-000002"
        for row in rows
    )


def test_output_preserves_unknown_and_unmapped_findings(tmp_path: Path) -> None:
    output = _build(tmp_path)
    text = _text(output)
    rows = _csv_rows(output)

    assert text.count("unknown") >= 8
    assert "installation/hookup" in text and "unmapped" in text
    assert any(row["mapping_status"] == "unmapped" for row in rows)
    assert any(row["value_basis"] == "not_public" for row in rows)


def test_report_trace_has_no_interpolated_years(tmp_path: Path) -> None:
    text = _text(_build(tmp_path))

    assert all(label in text for label in ("2009", "2010", "2011", "2015-05", "2018"))
    assert all(f">{year}<" not in text for year in (2012, 2013, 2014, 2016, 2017))
    assert "no interpolation" in text


def test_fdas_bridge_and_opex_separation_render_exactly(tmp_path: Path) -> None:
    text = _text(_build(tmp_path))

    assert "2,730.0 + 965.6 + 821.7 = 4,517.3 USD MM" in text
    assert "267,482,624 USD" in text and "790,000,000 USD" in text
    assert "OPEX — excluded from development CAPEX" in text
    assert "5,200 USD MM" in text and "stale configuration estimate" in text


def test_manifest_pins_schema_inputs_ids_scenarios_and_workbook_fields(
    tmp_path: Path,
) -> None:
    manifest = _manifest(_build(tmp_path))

    assert manifest["contract_version"] == "1.0.0"
    assert len(manifest["schema"]["sha256"]) == 64
    assert manifest["controlled_ids"] == {
        "awards": ["awd-000001", "awd-000002"],
        "events": [f"evt-{number:06d}" for number in range(1, 6)],
        "projects": ["prj-000001"],
        "requirements": [f"req-{number:06d}" for number in range(1, 9)],
    }
    assert [row["scenario_id"] for row in manifest["scenarios"]] == [
        "reference",
        "host_heavy",
        "well_heavy",
    ]
    assert {
        row["file"]: row["sha256"] for row in manifest["workbooks"]
    } == WORKBOOK_HASHES
    assert all(row["allowlisted_cells"] for row in manifest["workbooks"])
    assert all(
        row["extraction"]["library"] == "openpyxl" for row in manifest["workbooks"]
    )
    paths = [row["path"] for row in manifest["inputs"]]
    assert (
        paths == sorted(paths)
        and "data/modules/cost/curated/fdas_project_cost_crosswalk.csv" in paths
    )


def test_manifest_avoids_self_referential_hash(tmp_path: Path) -> None:
    output = _build(tmp_path)
    manifest = _manifest(output)

    assert [row["path"] for row in manifest["outputs"]] == [
        "reports/cost/big_foot_cost_map.html",
        "reports/cost/big_foot_cost_map_reconciliation.csv",
    ]
    assert all("manifest" not in row["path"] for row in manifest["outputs"])
    for row in manifest["outputs"]:
        assert row["sha256"] == _digest(output / row["path"])


def test_report_rejects_unsafe_urls_and_escapes_source_text() -> None:
    builder = _builder()

    assert builder.safe_url("javascript:alert(1)") is None
    assert builder.safe_url("https:///missing-host") is None
    assert builder.safe_url("https://user:password@example.com/source") is None
    assert builder.safe_url("https://example.com/bad\nheader") is None
    assert (
        builder.safe_url("https://example.com/source") == "https://example.com/source"
    )
    assert (
        builder.escape_text('<source data-x="bad">')
        == "&lt;source data-x=&quot;bad&quot;&gt;"
    )


def test_workbook_metadata_and_absolute_paths_are_not_published(tmp_path: Path) -> None:
    output = _build(tmp_path)
    published = "\n".join(
        path.read_text(encoding="utf-8") for path in output.rglob("*") if path.is_file()
    )

    assert "lastModifiedBy" not in published and "creator" not in published
    assert "/home/" not in published and "/mnt/" not in published
    assert "Project_Summary!" not in published


def test_big_foot_outputs_are_byte_deterministic(tmp_path: Path) -> None:
    first = _build(tmp_path / "first")
    second = _build(tmp_path / "second")

    relative_paths = (
        "reports/cost/big_foot_cost_map.html",
        "reports/cost/big_foot_cost_map_reconciliation.csv",
        "data/modules/cost/curated/cost_map_contract_manifest.v1.json",
    )
    assert {path: _digest(first / path) for path in relative_paths} == {
        path: _digest(second / path) for path in relative_paths
    }


def test_source_workbooks_are_byte_unchanged_after_build(tmp_path: Path) -> None:
    before = {name: _digest(FDAS / name) for name in WORKBOOK_HASHES}
    _build(tmp_path)
    after = {name: _digest(FDAS / name) for name in WORKBOOK_HASHES}

    assert before == after == WORKBOOK_HASHES


def test_owner_decision_and_external_send_remain_pending(tmp_path: Path) -> None:
    output = _build(tmp_path)
    manifest = _manifest(output)
    text = _text(output)

    assert manifest["owner_decision"]["status"] == "pending"
    assert manifest["policies"] == {
        "email": "not_sent",
        "external_send": "pending_owner_authorization",
        "workbooks": "read_only",
    }
    for item in ("taxonomy", "accounting", "scenarios", "portfolio reuse"):
        assert item in text
