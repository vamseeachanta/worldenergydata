from __future__ import annotations

import csv
import hashlib
import importlib.util
import inspect
import json
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from tests.unit.cost import test_big_foot_cost_output_hardening as hardening

ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = ROOT / "scripts/cost/build_big_foot_cost_map.py"
HTML_REL = Path("reports/cost/big_foot_cost_map.html")
CSV_REL = Path("reports/cost/big_foot_cost_map_reconciliation.csv")
MANIFEST_REL = Path("data/modules/cost/curated/cost_map_contract_manifest.v1.json")
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


def _run(command: list[str], cwd: Path) -> str:
    return subprocess.run(
        command, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture(scope="module")
def source_repo(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    root = tmp_path_factory.mktemp("big-foot-source")
    builder = _builder()
    for relative in builder.INPUT_PATHS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    _run(["git", "init", "-q"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    _run(["git", "add", "."], root)
    _run(["git", "commit", "-qm", "fixture"], root)
    return root, _run(["git", "rev-parse", "HEAD"], root)


def _clone(source: tuple[Path, str], tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    shutil.copytree(source[0], root)
    return root, source[1]


def _build(source: tuple[Path, str], tmp_path: Path) -> tuple[Path, Path, str]:
    root, commit = _clone(source, tmp_path)
    output = tmp_path / "output"
    _builder().build_outputs(
        repo_root=root,
        output_root=output,
        source_date_epoch=1_700_000_000,
        producer_commit=commit,
    )
    return output, root, commit


def _rows(output: Path) -> list[dict[str, str]]:
    return list(csv.DictReader((output / CSV_REL).open(encoding="utf-8", newline="")))


def _manifest(output: Path) -> dict:
    return json.loads((output / MANIFEST_REL).read_text(encoding="utf-8"))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _generate(root: Path, output: Path, commit: str, **options) -> None:
    _builder().build_outputs(
        repo_root=root,
        output_root=output,
        source_date_epoch=1,
        producer_commit=commit,
        **options,
    )


def _rewrite(path: Path, mutate) -> None:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    mutate(rows)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _ge_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return next(
        row
        for row in rows
        if row.get("CONTRACTOR") == "GE Oil & Gas"
        or row.get("AWARD_ID") == "awd-000001"
    )


def test_big_foot_output_contains_all_required_accounting_lanes(
    source_repo, tmp_path
) -> None:
    output, _, _ = _build(source_repo, tmp_path)
    text, rows = (output / HTML_REL).read_text(encoding="utf-8"), _rows(output)
    assert all(f"req-{number:06d}" in text for number in range(1, 9))
    assert {row["direction"] for row in rows} == {
        "project_to_asset",
        "asset_to_project",
    }
    kinds = {row["row_kind"] for row in rows}
    assert {
        "observed_component",
        "aggregate_reconciliation",
        "scenario_allocation",
        "implied_project_total",
        "fdas_total",
        "trace_event",
    } <= kinds
    assert all(
        term in text
        for term in (
            "eligible",
            "excluded",
            "overlap",
            "residual",
            "unallocated",
            "unreconciled variance",
        )
    )


def test_observed_and_allocated_values_are_visually_and_semantically_distinct(
    source_repo, tmp_path
) -> None:
    output, _, _ = _build(source_repo, tmp_path)
    text, rows = (output / HTML_REL).read_text(encoding="utf-8"), _rows(output)
    assert 'class="observed"' in text and 'class="allocated"' in text
    assert all(
        row["accounting_view"].startswith("scenario:")
        for row in rows
        if row["row_kind"] == "scenario_allocation"
    )
    assert all(
        row["accounting_view"].startswith("bottom_up:")
        for row in rows
        if row["row_kind"] == "observed_component"
    )
    for view in {
        row["accounting_view"]
        for row in rows
        if row["accounting_view"].startswith("scenario:")
    }:
        selected = [
            Decimal(row["value_low_mm"])
            for row in rows
            if row["accounting_view"] == view
        ]
        event = view.split(":")[1]
        assert (
            sum(selected)
            == {"evt-000003": Decimal("4000"), "evt-000004": Decimal("5100")}[event]
        )
    ge = [
        row
        for row in rows
        if row["award_id"] == "awd-000001" and row["row_kind"] == "observed_component"
    ]
    assert len(ge) == 2 and {row["value_low_mm"] for row in ge} == {"45"}


def test_output_preserves_unknown_and_unmapped_findings(source_repo, tmp_path) -> None:
    output, _, _ = _build(source_repo, tmp_path)
    text, rows = (output / HTML_REL).read_text(encoding="utf-8"), _rows(output)
    assert text.count("unknown") >= 8 and "installation/hookup" in text
    assert any(
        row["value_basis"] == "not_public" and row["mapping_status"] == "unmapped"
        for row in rows
    )


def test_report_trace_has_no_interpolated_years(source_repo, tmp_path) -> None:
    output, _, _ = _build(source_repo, tmp_path)
    text = (output / HTML_REL).read_text(encoding="utf-8")
    trace = [r for r in _rows(output) if r["row_kind"] == "trace_event"]
    assert [row["total_event_id"] for row in trace] == [
        f"evt-{n:06d}" for n in (2, 3, 1, 5, 4)
    ]
    assert all(label in text for label in ("2009", "2010", "2011", "2015-05", "2018"))
    assert "no interpolation" in text and all(
        f">{year}<" not in text for year in (2012, 2013, 2014, 2016, 2017)
    )
    assert all(row["source_locator"] for row in trace)


def test_fdas_bridge_and_opex_separation_render_exactly(source_repo, tmp_path) -> None:
    output, _, _ = _build(source_repo, tmp_path)
    text, rows = (output / HTML_REL).read_text(encoding="utf-8"), _rows(output)
    assert "2,730.0 + 965.6 + 821.7 = 4,517.3 USD MM" in text
    assert "267,482,624 USD" in text and "790,000,000 USD" in text
    total = [row for row in rows if row["row_kind"] == "fdas_total"]
    assert len(total) == 1 and total[0]["total_mm"] == "4517.3"
    fdas = [row for row in rows if row["row_kind"] == "fdas_assumption"]
    assert {row["source_locator"] for row in fdas} == {
        "Project_Summary!J3",
        "Project_Summary!K3",
        "Project_Summary!L3",
    }
    assert {row["assumption_vintage"] for row in fdas} == {"FDAS_V30"}
    assert {row["comparison_eligibility"] for row in fdas} == {"ineligible"}
    assert all(
        row["rounding_policy"] == "native_USD_divided_by_1000000" for row in fdas
    )


def test_manifest_pins_schema_inputs_ids_scenarios_and_workbook_fields(
    source_repo, tmp_path
) -> None:
    output, root, commit = _build(source_repo, tmp_path)
    manifest = _manifest(output)
    assert manifest["producer"]["commit"] == commit and len(commit) == 40
    assert manifest["producer"]["builder_sha256"] == _digest(
        root / _builder().BUILDER_REL
    )
    assert manifest["schema"]["sha256"] == _digest(root / manifest["schema"]["path"])
    assert {r["path"]: r["sha256"] for r in manifest["inputs"]} == {
        p: _digest(root / p) for p in _builder().INPUT_PATHS
    }
    expected = {
        key: {rid: str(value) for rid, value in scenario.shares.items()}
        for key, scenario in _builder().BIG_FOOT_JOINT_SCENARIOS.items()
    }
    assert {
        row["scenario_id"]: row["shares"] for row in manifest["scenarios"]
    } == expected
    assert all(row["reuse_allowed"] is False for row in manifest["scenarios"])
    assert manifest["decimal_policy"] == {
        "arithmetic": "Decimal",
        "source_scale": "native",
        "output_quantum": "0.01 USD MM",
        "allocation_rounding": "largest_remainder",
        "inverse_rounding": "outward",
        "rounding_boundary": "output_only",
    }
    allowlists = {
        row["file"]: row["allowlisted_cells"] for row in manifest["workbooks"]
    }
    assert "Project_Summary!J3" in allowlists["financial_project_summary.xlsx"]
    assert "Sheet1!A17:L54" in allowlists["drilling_and_completion_days.xlsx"]
    assert {
        row["file"]: row["sha256"] for row in manifest["workbooks"]
    } == WORKBOOK_HASHES


def test_manifest_avoids_self_referential_hash(source_repo, tmp_path) -> None:
    output, _, _ = _build(source_repo, tmp_path)
    manifest = _manifest(output)
    assert [row["path"] for row in manifest["outputs"]] == [str(HTML_REL), str(CSV_REL)]
    assert all(
        row["sha256"] == _digest(output / row["path"]) for row in manifest["outputs"]
    )
    assert all("manifest" not in row["path"] for row in manifest["outputs"])


def test_report_rejects_unsafe_urls_and_escapes_source_text(
    source_repo, tmp_path
) -> None:
    builder = _builder()
    for value in (
        " javascript:alert(1)",
        "https:///x",
        "https://u:p@example.com",
        "https://example.com/x\n",
        "https://example.com:bad",
    ):
        assert builder.safe_url(value) is None
    root, commit = _clone(source_repo, tmp_path / "unsafe")
    for filename in ("award_asset_links.csv", "contract_awards.csv"):
        path = root / "data/modules/cost/curated" / filename
        _rewrite(
            path,
            lambda rows: _ge_row(rows).update({"SOURCE_URL": " https://example.com"}),
        )
    with pytest.raises(ValueError, match="unsafe award URL"):
        _generate(root, tmp_path / "bad-output", commit)
    root, commit = _clone(source_repo, tmp_path / "escaped")
    path = root / "data/modules/cost/curated/award_asset_links.csv"
    _rewrite(
        path,
        lambda rows: _ge_row(rows).update({"COUNTING_REASON": '<script data-x="1">'}),
    )
    output = tmp_path / "escaped-output"
    _generate(root, output, commit)
    text = (output / HTML_REL).read_text(encoding="utf-8")
    assert (
        "<script data-x" not in text and "&lt;script data-x=&quot;1&quot;&gt;" in text
    )


def test_workbook_metadata_and_absolute_paths_are_not_published(
    source_repo, tmp_path
) -> None:
    output, _, _ = _build(source_repo, tmp_path)
    published = "\n".join(
        path.read_text(encoding="utf-8") for path in output.rglob("*") if path.is_file()
    )
    assert all(
        value not in published
        for value in ("lastModifiedBy", '"creator"', "/home/", "/mnt/")
    )


def test_big_foot_outputs_are_byte_deterministic(source_repo, tmp_path) -> None:
    first, _, _ = _build(source_repo, tmp_path / "first")
    second, _, _ = _build(source_repo, tmp_path / "second")
    assert {_digest(first / p) for p in (HTML_REL, CSV_REL, MANIFEST_REL)} == {
        _digest(second / p) for p in (HTML_REL, CSV_REL, MANIFEST_REL)
    }


def test_source_workbooks_are_byte_unchanged_after_build(source_repo, tmp_path) -> None:
    output, root, _ = _build(source_repo, tmp_path)
    assert output.exists()
    prefix = root / "docs/modules/bsee/analysis/production/FDAS_V30"
    assert {name: _digest(prefix / name) for name in WORKBOOK_HASHES} == WORKBOOK_HASHES


def test_owner_decision_and_external_send_remain_pending(source_repo, tmp_path) -> None:
    output, _, _ = _build(source_repo, tmp_path)
    manifest, text = _manifest(output), (output / HTML_REL).read_text(encoding="utf-8")
    assert manifest["owner_decision"]["status"] == "pending"
    assert (
        manifest["policies"]["email"] == "not_sent"
        and manifest["policies"]["external_send"] == "pending_owner_authorization"
    )
    assert all(
        item in text
        for item in ("taxonomy", "accounting", "scenarios", "portfolio reuse")
    )


def test_production_has_no_attestation_bypass_and_normalizes_git_errors(
    monkeypatch,
) -> None:
    builder = _builder()
    parameters = inspect.signature(builder.build_outputs).parameters
    assert "producer_executable_attestation" not in parameters
    module = importlib.import_module("worldenergydata.cost.timeseries.evidence_pack")
    monkeypatch.setattr(module.subprocess, "run", Mock(side_effect=OSError))
    with pytest.raises(ValueError, match="producer commit must exist"):
        builder.validate_producer(ROOT, "0" * 40, {})


def test_producer_commit_must_contain_exact_builder(source_repo, tmp_path) -> None:
    root, commit = _clone(source_repo, tmp_path)
    with pytest.raises(ValueError, match="40-hex"):
        _generate(root, tmp_path / "short", commit[:8])
    builder = root / _builder().BUILDER_REL
    builder.write_bytes(builder.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="blob does not match"):
        _generate(root, tmp_path / "mismatch", commit)


def test_checked_in_outputs_regenerate_from_manifest_producer() -> None:
    manifest = json.loads((ROOT / MANIFEST_REL).read_text(encoding="utf-8"))
    hardening.hydrate_trusted_producer_history(ROOT, manifest["producer"]["commit"])
    output = ROOT / ".superpowers/sdd/checked-output"
    if output.exists():
        shutil.rmtree(output)
    try:
        _builder().build_outputs(
            repo_root=ROOT,
            output_root=output,
            source_date_epoch=manifest["generated_at"]["epoch"],
            producer_commit=manifest["producer"]["commit"],
        )
        assert all(
            (output / path).read_bytes() == (ROOT / path).read_bytes()
            for path in (HTML_REL, CSV_REL, MANIFEST_REL)
        )
    finally:
        shutil.rmtree(output, ignore_errors=True)
