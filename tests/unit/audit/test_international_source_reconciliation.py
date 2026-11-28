"""Offline reconciliation cases derived from issue #917 (2026) acceptance criteria."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "audit"))

from reconcile_international_sources import main, reconcile
from test_source_refresh_contract import _write_project
from validate_source_refresh_contract import validate_contract

REPO_ROOT = Path(__file__).resolve().parents[3]


def _project(root: Path) -> None:
    """Synthetic inputs: closed repair, completed code, no downloaded data.

    Hand derivation: CLOSED repair intersect active blocker = one stale blocker;
    a package file plus an enabled job cannot imply a materialized directory.
    No physical constants or numerical acceptance limits are used.
    """
    (root / "data").mkdir()
    (root / "config" / "scheduler").mkdir(parents=True)
    (root / "packages").mkdir()
    (root / "packages" / "chain.py").write_text('"""Fixture chain."""\n')
    (root / "data" / "international-source-reconciliation.json").write_text(
        json.dumps(
            {
                "observed_on": "2026-10-20",
                "issue_states": {"#459": "CLOSED", "#718": "CLOSED"},
                "sources": [
                    {
                        "module_id": "brazil_anp",
                        "capability_evidence": ["packages/chain.py"],
                        "scheduler_job": "brazil_anp_refresh",
                        "data_path": "modules/brazil_anp",
                        "implementation_issues": ["#718"],
                    }
                ],
            }
        )
    )
    (root / "data" / "source-refresh-acceptance-contract.json").write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "module_id": "brazil_anp",
                        "scheduler_job": "brazil_anp_refresh",
                        "scheduler_output_dir": "data/modules/brazil_anp",
                        "data_location": "data/modules/brazil_anp",
                        "freshness_status": "blocked",
                        "blocker_issue": "#459",
                    }
                ]
            }
        )
    )
    (root / "config" / "scheduler" / "scheduler_config.yml").write_text(
        yaml.safe_dump(
            {
                "jobs": [
                    {
                        "name": "brazil_anp_refresh",
                        "output_dir": "data/modules/brazil_anp",
                        "enabled": True,
                    }
                ]
            }
        )
    )


def test_closed_repair_is_reported_without_promoting_freshness(tmp_path):
    _project(tmp_path)
    row = reconcile(tmp_path)["sources"][0]
    assert row["findings"] == ["closed_blocker:#459"]
    assert row["freshness_status"] == "blocked"
    assert row["materialization_status"] == "NOT_EVALUATED"
    assert row["capability_evidence_present"] is True


@pytest.mark.parametrize(
    ("layout", "expected"),
    [
        ("absent", "not_observed"),
        ("directory", "directory_only"),
        ("manifest", "manifest_present"),
        ("file", "unavailable"),
    ],
)
def test_explicit_data_root_is_observed_without_accepting_data(
    tmp_path, layout, expected
):
    """Hand truth table: absent < directory < manifest presence; no freshness proof.

    Even a failure manifest counts only as present, never as accepted production.
    """
    _project(tmp_path)
    data_root = tmp_path / "external-data"
    data_root.mkdir()
    target = data_root / "modules" / "brazil_anp"
    target.parent.mkdir()
    if layout in {"directory", "manifest"}:
        target.mkdir()
    if layout == "manifest":
        (target / "manifest.json").write_text('{"status": "failure"}')
    if layout == "file":
        target.write_text("not a directory")
    row = reconcile(tmp_path, data_root=data_root)["sources"][0]
    assert row["materialization_status"] == expected
    assert row["freshness_status"] == "blocked"
    assert str(tmp_path) not in json.dumps(row)


def test_missing_root_is_not_evidence_of_missing_country_data(tmp_path):
    _project(tmp_path)
    row = reconcile(tmp_path, data_root=tmp_path / "unavailable")["sources"][0]
    assert row["materialization_status"] == "NOT_EVALUATED"


def test_symlink_does_not_escape_observation_root(tmp_path):
    _project(tmp_path)
    data_root = tmp_path / "external-data"
    data_root.mkdir()
    (data_root / "modules").symlink_to(tmp_path / "packages", target_is_directory=True)
    row = reconcile(tmp_path, data_root=data_root)["sources"][0]
    assert row["materialization_status"] == "unavailable"


@pytest.mark.parametrize("link_target", ["root", "manifest"])
def test_symlinked_root_or_manifest_is_not_accepted(tmp_path, link_target):
    _project(tmp_path)
    data_root = tmp_path / "external-data"
    if link_target == "root":
        data_root.symlink_to(tmp_path / "data", target_is_directory=True)
        expected = "NOT_EVALUATED"
    else:
        target = data_root / "modules/brazil_anp"
        target.mkdir(parents=True)
        (target / "manifest.json").symlink_to(tmp_path / "absent.json")
        expected = "unavailable"
    assert (
        reconcile(tmp_path, data_root)["sources"][0]["materialization_status"]
        == expected
    )


@pytest.mark.parametrize(
    ("field", "value", "finding"),
    [
        ("scheduler_job", "none", "contract_scheduler_mismatch"),
        ("scheduler_output_dir", "data/other", "contract_output_mismatch"),
        ("data_location", "data/other", "contract_data_location_mismatch"),
    ],
)
def test_contract_drift_is_reported(tmp_path, field, value, finding):
    _project(tmp_path)
    path = tmp_path / "data/source-refresh-acceptance-contract.json"
    contract = json.loads(path.read_text())
    contract["sources"][0][field] = value
    path.write_text(json.dumps(contract))
    assert finding in reconcile(tmp_path)["sources"][0]["findings"]


def test_scheduler_output_drift_and_missing_contract_source(tmp_path):
    _project(tmp_path)
    path = tmp_path / "data/source-refresh-acceptance-contract.json"
    path.write_text('{"sources": []}')
    config = tmp_path / "config/scheduler/scheduler_config.yml"
    config.write_text(
        yaml.safe_dump(
            {"jobs": [{"name": "brazil_anp_refresh", "output_dir": "data/other"}]}
        )
    )
    assert reconcile(tmp_path)["sources"][0]["findings"] == [
        "scheduler_output_mismatch",
        "missing_contract_source",
    ]


def test_cli_reports_findings_and_invalid_input_without_disclosing_paths(
    tmp_path, capsys
):
    _project(tmp_path)
    assert main(["--project-root", str(tmp_path)]) == 1
    assert "closed_blocker:#459" in capsys.readouterr().out
    path = tmp_path / "data/international-source-reconciliation.json"
    path.write_text("not JSON")
    with pytest.raises(SystemExit) as exc:
        main(["--project-root", str(tmp_path)])
    assert exc.value.code == 1
    error = capsys.readouterr().err
    assert "inputs are unavailable or invalid" in error
    assert str(tmp_path) not in error


def test_scheduler_drift_and_missing_capability_are_reported(tmp_path):
    _project(tmp_path)
    config = tmp_path / "config" / "scheduler" / "scheduler_config.yml"
    config.write_text(yaml.safe_dump({"jobs": []}))
    # Model missing implementation evidence without deleting any source fixture.
    register_path = tmp_path / "data" / "international-source-reconciliation.json"
    register = json.loads(register_path.read_text())
    register["sources"][0]["capability_evidence"] = ["packages/absent.py"]
    register_path.write_text(json.dumps(register))
    row = reconcile(tmp_path)["sources"][0]
    assert "missing_scheduler_job" in row["findings"]
    assert "missing_capability_evidence" in row["findings"]


@pytest.mark.parametrize("data_path", ["../escape", "/absolute"])
def test_unbounded_observation_paths_are_rejected(tmp_path, data_path):
    _project(tmp_path)
    path = tmp_path / "data" / "international-source-reconciliation.json"
    register = json.loads(path.read_text())
    register["sources"][0]["data_path"] = data_path
    path.write_text(json.dumps(register))
    with pytest.raises(ValueError, match="relative"):
        reconcile(tmp_path, data_root=tmp_path / "data")


def test_repository_reconciliation_matches_code_and_preserves_issue_references():
    """Expected states: issue closeouts read on 2026-10-20; see the register basis.

    #459 is CLOSED, so Brazil has no active endpoint blocker. #809 is CLOSED,
    so Spain names its registered job. No inspection can establish source dates.
    """
    report = reconcile(REPO_ROOT)
    assert all(not row["findings"] for row in report["sources"])
    assert all(
        row["materialization_status"] == "NOT_EVALUATED" for row in report["sources"]
    )
    register = json.loads(
        (REPO_ROOT / "data" / "international-source-reconciliation.json").read_text()
    )
    assert set(register["issue_states"]) >= {
        "#713",
        "#716",
        "#717",
        "#718",
        "#719",
        "#720",
        "#721",
        "#722",
        "#753",
        "#763",
        "#806",
        "#807",
        "#809",
        "#810",
        "#831",
        "#459",
    }
    rows = {row["module_id"]: row for row in report["sources"]}
    assert rows["brazil_anp"]["freshness_status"] == "missing"
    assert rows["spain_cores"]["scheduler_job"] == "spain_cores_refresh"
    assert rows["canada"]["contract_status"] == "not_listed"


def test_worked_example(tmp_path):
    """Hand calculation in docs/data/international-source-reconciliation.md.

    Empty directory + no manifest = directory_only. A closed repaired blocker
    removed from the contract = no findings. No accepted data = missing freshness.
    """
    (tmp_path / "modules/brazil_anp").mkdir(parents=True)
    rows = reconcile(REPO_ROOT, data_root=tmp_path)["sources"]
    brazil = next(row for row in rows if row["module_id"] == "brazil_anp")
    assert brazil["findings"] == []
    assert brazil["materialization_status"] == "directory_only"
    assert brazil["freshness_status"] == "missing"


def test_repository_contract_in_isolated_metadata_project(tmp_path):
    """Validate real metadata independently of unavailable local datasets.

    Only empty directories are supplied, as allowed by the contract validator
    for non-fresh rows. No manifest or source-vintage evidence is fabricated.
    A fresh Spain row would require a real accepted manifest and fail here.
    """
    contract = json.loads(
        (REPO_ROOT / "data/source-refresh-acceptance-contract.json").read_text()
    )
    _write_project(tmp_path, contract)
    (tmp_path / "config/scheduler/scheduler_config.yml").write_bytes(
        (REPO_ROOT / "config/scheduler/scheduler_config.yml").read_bytes()
    )
    validate_contract(tmp_path)
    by_id = {row["module_id"]: row for row in contract["sources"]}
    for module_id in ("sodir", "ukcs", "brazil_anp", "spain_cores"):
        assert by_id[module_id]["source_data_latest_date"] is None
        assert by_id[module_id]["last_successful_refresh"] is None
    assert by_id["spain_cores"]["refresh_blocker_reason"]
    assert by_id["spain_cores"]["freshness_grace_days"] is None


def test_repository_cli_success(capsys):
    assert main(["--project-root", str(REPO_ROOT)]) == 0
    assert all(
        row["materialization_status"] == "NOT_EVALUATED"
        for row in json.loads(capsys.readouterr().out)["sources"]
    )


def test_reconciliation_is_read_only(tmp_path):
    _project(tmp_path)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    reconcile(tmp_path, data_root=tmp_path / "data")
    after = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before
