"""Mutation and producer-provenance tests for the Big Foot evidence pack."""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[3]
HTML = Path("reports/cost/big_foot_cost_map.html")
CSV = Path("reports/cost/big_foot_cost_map_reconciliation.csv")


def _builder():
    path = ROOT / "scripts/cost/build_big_foot_cost_map.py"
    spec = importlib.util.spec_from_file_location("hardening_builder", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def source_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    for relative in _builder().INPUT_PATHS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return root, commit


def _rewrite(path: Path, mutate) -> None:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    mutate(rows)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _generate(root: Path, output: Path, commit: str, **options) -> None:
    _builder().build_outputs(
        repo_root=root,
        output_root=output,
        source_date_epoch=1,
        producer_commit=commit,
        **options,
    )


def test_financial_values_derive_from_unique_curated_evidence(
    source_repo, tmp_path
) -> None:
    root, commit = source_repo
    awards = root / "data/modules/cost/curated/contract_awards.csv"

    def ge(rows):
        return next(row for row in rows if row.get("CONTRACTOR") == "GE Oil & Gas")

    _rewrite(
        awards,
        lambda rows: ge(rows).update({"VALUE_LOW_MM": "46", "VALUE_HIGH_MM": "46"}),
    )
    output = tmp_path / "output"
    _generate(root, output, commit)
    text = (output / HTML).read_text(encoding="utf-8")
    rows = list(csv.DictReader((output / CSV).open(encoding="utf-8", newline="")))
    assert "46 USD MM" in text and "45 USD MM" not in text
    assert {
        row["value_low_mm"]
        for row in rows
        if row["award_id"] == "awd-000001" and row["row_kind"] == "observed_component"
    } == {"46"}
    assert {
        row["value_low_mm"]
        for row in rows
        if row["row_kind"] == "implied_project_total"
    } == {"766.66", "920.00", "657.14"}
    crosswalk = root / "data/modules/cost/curated/fdas_project_cost_crosswalk.csv"
    _rewrite(
        crosswalk,
        lambda rows: next(row for row in rows if row["WORKBOOK_CELL"] == "J3").update(
            {"WORKBOOK_VALUE": "2730000001"}
        ),
    )
    with pytest.raises(ValueError, match="crosswalk value"):
        _generate(root, tmp_path / "drift", commit)


def test_input_fingerprints_fail_closed_on_workbook_and_toctou(
    source_repo, tmp_path
) -> None:
    root, commit = source_repo
    workbook = (
        root / "docs/modules/bsee/analysis/production/FDAS_V30/lease_assumptions.xlsx"
    )
    workbook.write_bytes(workbook.read_bytes() + b"appended")
    with pytest.raises(ValueError, match="workbook fingerprint"):
        _generate(root, tmp_path / "bad", commit)
    workbook.write_bytes(
        (
            ROOT
            / "docs/modules/bsee/analysis/production/FDAS_V30/lease_assumptions.xlsx"
        ).read_bytes()
    )
    source = root / "data/modules/cost/curated/project_asset_requirements.csv"

    def mutate():
        source.write_bytes(source.read_bytes() + b"\n")

    with pytest.raises(RuntimeError, match="input changed"):
        _generate(root, tmp_path / "race", commit, before_final_hash=mutate)


def test_producer_commit_must_contain_exact_builder(source_repo, tmp_path) -> None:
    root, commit = source_repo
    with pytest.raises(ValueError, match="40-hex"):
        _generate(root, tmp_path / "short", commit[:8])
    builder = root / _builder().BUILDER_REL
    builder.write_bytes(builder.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="blob does not match"):
        _generate(root, tmp_path / "mismatch", commit)
