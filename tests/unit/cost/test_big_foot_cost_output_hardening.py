"""Mutation and producer-provenance tests for the Big Foot evidence pack."""

from __future__ import annotations

import csv
import importlib.util
import locale
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HTML = Path("reports/cost/big_foot_cost_map.html")
CSV = Path("reports/cost/big_foot_cost_map_reconciliation.csv")
MANIFEST = Path("data/modules/cost/curated/cost_map_contract_manifest.v1.json")


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


@pytest.mark.parametrize(
    "relative",
    [
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/evidence_pack.py",
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/evidence_pack_render.py",
    ],
)
def test_producer_commit_pins_every_executable_helper(
    source_repo, tmp_path, relative
) -> None:
    root, commit = source_repo
    path = root / relative
    path.write_bytes(path.read_bytes() + b"\n# dirty mutation\n")
    with pytest.raises(ValueError, match="executable blob does not match"):
        _generate(root, tmp_path / "mismatch", commit)


def test_build_restores_process_locale_on_success_and_failure(
    source_repo, tmp_path
) -> None:
    root, commit = source_repo
    original = locale.setlocale(locale.LC_ALL)
    _generate(root, tmp_path / "ok", commit)
    assert locale.setlocale(locale.LC_ALL) == original

    source = root / "data/modules/cost/curated/project_asset_requirements.csv"

    def mutate() -> None:
        source.write_bytes(source.read_bytes() + b"\n")

    with pytest.raises(RuntimeError, match="input changed"):
        _generate(root, tmp_path / "bad-locale", commit, before_final_hash=mutate)
    assert locale.setlocale(locale.LC_ALL) == original
    assert "café".encode("utf-8").decode("utf-8") == "café"


def test_failed_staged_build_preserves_all_preexisting_outputs(
    source_repo, tmp_path
) -> None:
    root, commit = source_repo
    output = tmp_path / "published"
    sentinels = {HTML: b"old-html", CSV: b"old-csv", MANIFEST: b"old-manifest"}
    for relative, content in sentinels.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def corrupt(stage: Path) -> None:
        (stage / CSV).write_bytes(b"raced")

    with pytest.raises(RuntimeError, match="staged output changed"):
        _generate(root, output, commit, before_publish=corrupt)
    assert {
        relative: (output / relative).read_bytes() for relative in sentinels
    } == sentinels


def test_fdas_coverage_gap_is_source_derived_and_unique(source_repo, tmp_path) -> None:
    root, commit = source_repo
    output = tmp_path / "gap"
    _generate(root, output, commit)
    rows = list(csv.DictReader((output / CSV).open(encoding="utf-8", newline="")))
    gaps = [row for row in rows if row["row_kind"] == "fdas_gap"]
    assert len(gaps) == 1
    assert gaps[0] == {
        **{field: "" for field in gaps[0]},
        "accounting_view": "fdas_development_capex",
        "direction": "project_to_asset",
        "row_kind": "fdas_gap",
        "additive": "false",
        "project_id": "prj-000001",
        "requirement_id": "req-000007",
        "currency": "USD",
        "price_basis": "nominal",
        "ownership_basis": "gross",
        "scope_basis": "project",
        "capex_basis": "project_capex",
        "value_basis": "not_public",
        "evidence_derivation": "assumed",
        "source_provenance": "workbook_assumption",
        "counting_disposition": "excluded",
        "mapping_status": "unmapped",
        "source_identity": "FDAS_V30:installation/hookup",
        "source_locator": "financial_project_summary.xlsx:Project_Summary",
        "assumption_vintage": "FDAS_V30",
        "comparison_eligibility": "ineligible",
    }


def _sentinel_outputs(output: Path) -> dict[Path, bytes]:
    sentinels = {HTML: b"old-html", CSV: b"old-csv", MANIFEST: b"old-manifest"}
    for relative, content in sentinels.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return sentinels


def _assert_transaction_clean(output: Path, sentinels: dict[Path, bytes]) -> None:
    assert {
        relative: (output / relative).read_bytes() for relative in sentinels
    } == sentinels
    assert not list(output.rglob("*.tmp")) and not list(output.rglob("*.bak"))


def test_partial_temp_copy_failure_preserves_all_finals(
    source_repo, tmp_path, monkeypatch
) -> None:
    root, commit = source_repo
    output, sentinels = (
        tmp_path / "partial-copy",
        _sentinel_outputs(tmp_path / "partial-copy"),
    )
    module = importlib.import_module("worldenergydata.cost.timeseries.evidence_pack")
    original = module.shutil.copyfile

    def partial_then_raise(source, target):
        Path(target).write_bytes(b"partial")
        raise OSError("simulated partial temp copy")

    monkeypatch.setattr(module.shutil, "copyfile", partial_then_raise)
    with pytest.raises(OSError, match="partial temp copy"):
        _generate(root, output, commit)
    monkeypatch.setattr(module.shutil, "copyfile", original)
    _assert_transaction_clean(output, sentinels)


def test_replace_failure_rolls_back_every_final(
    source_repo, tmp_path, monkeypatch
) -> None:
    root, commit = source_repo
    output, sentinels = tmp_path / "replace", _sentinel_outputs(tmp_path / "replace")
    module = importlib.import_module("worldenergydata.cost.timeseries.evidence_pack")
    original = module.os.replace
    calls = 0

    def fail_second_replace(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated replace failure")
        return original(source, target)

    monkeypatch.setattr(module.os, "replace", fail_second_replace)
    with pytest.raises(OSError, match="replace failure"):
        _generate(root, output, commit)
    monkeypatch.setattr(module.os, "replace", original)
    _assert_transaction_clean(output, sentinels)


def test_csv_trace_preserves_dates_bases_and_controlled_vocabularies(
    source_repo, tmp_path
) -> None:
    root, commit = source_repo
    output = tmp_path / "trace"
    _generate(root, output, commit)
    rows = list(csv.DictReader((output / CSV).open(encoding="utf-8", newline="")))
    trace = [row for row in rows if row["row_kind"] == "trace_event"]
    assert [(row["effective_date"], row["date_precision"]) for row in trace] == [
        ("2009", "year"),
        ("2010", "year"),
        ("2011", "year"),
        ("2015-05", "month"),
        ("2018", "year"),
    ]
    assert {row["price_basis"] for row in trace if row["value_low_mm"]} == {"nominal"}
    monetary_totals = [
        row for row in trace if row["lane"] == "total" and row["value_low_mm"]
    ]
    assert {row["ownership_basis"] for row in monetary_totals} == {"gross"}
    assert {row["scope_basis"] for row in monetary_totals} == {"project"}
    assert {row["capex_basis"] for row in monetary_totals} == {"project_capex"}
    assert {row["date_precision"] for row in trace} <= {"year", "month", "day"}
    assert {row["price_basis"] for row in rows if row["price_basis"]} <= {
        "nominal",
        "real",
    }


def test_whitespace_urls_and_csv_formula_prefixes_fail_closed(
    source_repo, tmp_path
) -> None:
    builder = _builder()
    for value in (
        "https://example.com/a b",
        "https://example.com/a\tb",
        "https://example.com/a\u00a0b",
    ):
        assert builder.safe_url(value) is None
    root, commit = source_repo
    links = root / "data/modules/cost/curated/award_asset_links.csv"
    _rewrite(
        links,
        lambda rows: next(
            row for row in rows if row["AWARD_ID"] == "awd-000001"
        ).update({"SOURCE_LOCATOR": '=WEBSERVICE("https://example.com")'}),
    )
    with pytest.raises(ValueError, match="CSV formula prefix"):
        _generate(root, tmp_path / "formula", commit)


def test_controlled_identity_cardinality_drift_fails_closed(
    source_repo, tmp_path
) -> None:
    root, commit = source_repo
    requirements = root / "data/modules/cost/curated/project_asset_requirements.csv"
    _rewrite(requirements, lambda rows: rows.pop())
    with pytest.raises(ValueError, match="controlled requirement IDs"):
        _generate(root, tmp_path / "missing", commit)
