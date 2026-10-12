"""Offline synthetic examples for D&C provenance propagation."""

import csv
import importlib.util
import socket
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def load_script(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("network disabled for synthetic fixtures")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
def synthetic_inputs(tmp_path):
    row = dict(
        LEASE_NAME="Anchor",
        SURF_LEASE_NUM="G00001",
        WATER_DEPTH="100",
        API_WELL_NUMBER="000000000100",
        WELL_NAME="synthetic",
        WELL_SPUD_DATE="",
        TOTAL_DEPTH_DATE="",
        DRILLING_DAYS="",
        COMPLETION_DAYS="",
        MAX_BH_TOTAL_MD="",
        MAX_WELL_BORE_TVD="",
        MAX_DRILL_FLUID_WGT="",
        PND_DAYS="",
        DAYS_STATUS="no_war_activity",
        BASIS="DRL_COM(drilling=DRL;completion=COM;days=inclusive)",
    )
    source = tmp_path / "synthetic_bores.csv"
    with source.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)
    benchmark = tmp_path / "synthetic_benchmark.csv"
    benchmark.write_text("api12\n", encoding="utf-8")
    vintage = tmp_path / "synthetic_vintage.csv"
    vintage.write_text("api12,category,basis,pnd_days,days_status\n", encoding="utf-8")
    return source, benchmark, vintage


def patch_inputs(monkeypatch, mod, inputs):
    for name, value in zip(("SOURCE_CSV", "BENCHMARK_CSV", "VINTAGE_CSV"), inputs):
        monkeypatch.setattr(mod, name, value)


@pytest.mark.parametrize(
    "script,loader",
    [
        ("build_wo_per_well_dc.py", "load_bores"),
        ("build_dc_drilldown.py", "load_payload"),
    ],
)
def test_missing_days_remain_null(monkeypatch, synthetic_inputs, script, loader):
    mod = load_script(REPO / "scripts/lower_tertiary" / script)
    patch_inputs(monkeypatch, mod, synthetic_inputs)
    data = getattr(mod, loader)()
    bore = data["bores"][0] if loader == "load_payload" else data["Anchor"][0]
    assert bore["drill"] is None
    assert bore["compl"] is None
    assert bore["pnd_days"] is None
    assert bore["days_status"] == "no_war_activity"
    assert bore["basis"] == "DRL_COM(drilling=DRL;completion=COM;days=inclusive)"
    if loader == "load_payload":
        for surface in ("fields", "blocks"):
            assert data[surface][0]["drill"] is None
            assert data[surface][0]["basis"] == bore["basis"]


def test_legacy_input_refused():
    mod = load_script(REPO / "scripts/lower_tertiary/build_wo_per_well_dc.py")
    with pytest.raises(ValueError, match="provenance"):
        mod.load_bores()


def test_mixed_aggregate_label():
    mod = load_script(REPO / "scripts/lower_tertiary/dc_provenance.py")
    assert mod.aggregate_basis([{"basis": "a"}, {"basis": "a"}]) == "a"
    assert mod.aggregate_basis([{"basis": "a"}, {"basis": "b"}]) == "mixed"
    assert mod.sum_days([None, None]) is None
    assert mod.sum_days([0, None]) is None
    assert mod.sum_days([0, 0]) == 0


def test_day_schema_requires_basis():
    mod = load_script(REPO / "scripts/lower_tertiary/dc_provenance.py")
    with pytest.raises(ValueError, match="basis"):
        mod.validate_day_schema(["drilling_days", "pnd_days"])
    mod.validate_day_schema(["drilling_days", "basis"])


def test_vintage_requires_comparable_basis(synthetic_inputs):
    import pandas as pd

    mod = load_script(REPO / "scripts/lower_tertiary/build_dc_vintage_diff.py")
    candidate = pd.read_csv(synthetic_inputs[0], keep_default_na=False)
    frozen = candidate.drop(columns=["BASIS", "PND_DAYS", "DAYS_STATUS"])
    diff = mod.build_diff(frozen, candidate)
    assert diff.loc[0, "basis"] == "mixed"
    assert diff.loc[0, "basis_v30"] == "unavailable"
    assert diff.loc[0, "category"] == "basis_unavailable"
    assert pd.isna(diff.loc[0, "d_drill"])
    assert pd.isna(diff.loc[0, "drill_wed"])
    assert str(diff["pnd_days"].dtype) == "Int64"
    candidate["DRILLING_DAYS"] = "0"
    candidate["COMPLETION_DAYS"] = "2"
    same = mod.build_diff(candidate.copy(), candidate)
    assert same.loc[0, "d_drill"] == 0
    assert same.loc[0, "category"] == "unchanged"
    other = candidate.copy()
    other["BASIS"] = "a different full rule"
    changed = mod.build_diff(other, candidate)
    assert changed.loc[0, "category"] == "basis_changed"
    assert pd.isna(changed.loc[0, "d_compl"])


def test_exported_tables_preserve_nulls_and_schema(monkeypatch, synthetic_inputs):
    import pandas as pd

    listing = load_script(REPO / "scripts/lower_tertiary/build_wo_per_well_dc.py")
    patch_inputs(monkeypatch, listing, synthetic_inputs)
    monkeypatch.setattr(
        listing,
        "load_vintage_diff",
        lambda: {
            "basis_unavailable": [
                {
                    "dev": "Anchor",
                    "api12": "000000000100",
                    "category": "basis_unavailable",
                    "drill_v30": None,
                    "compl_v30": None,
                    "drill_wed": None,
                    "compl_wed": None,
                    "d_drill": None,
                    "d_compl": None,
                    "spud_wed": "",
                    "basis": "mixed",
                    "basis_v30": "unavailable",
                    "basis_wed": "DRL_COM(drilling=DRL;completion=COM;days=inclusive)",
                    "pnd_days": None,
                    "days_status": "no_war_activity",
                }
            ],
        },
    )
    mod = load_script(REPO / "scripts/hf_export/publish_dc_days_to_hf.py")
    monkeypatch.setattr(mod, "_load_listing_module", lambda: listing)
    monkeypatch.setattr(mod, "_drilldown_extras", lambda: {})
    tables = mod.build_tables()
    for table in tables.values():
        assert "basis" in table
        assert "pnd_days" in table
        assert "days_status" in table
        assert str(table["pnd_days"].dtype) == "Int64"
        assert str(table["basis"].dtype) == "string"
    bore = tables["dc_bores"].iloc[0]
    assert pd.isna(bore["dc_days"])
    assert pd.isna(bore["pnd_days"])
    summary = tables["dc_development_summary"].iloc[0]
    assert pd.isna(summary["dc_days_wed"])
    assert summary["basis_article"] == "unavailable"
    assert pd.isna(summary["delta_days"])


def test_field_and_block_aggregates_are_mixed_and_incomplete(
    monkeypatch, synthetic_inputs
):
    mod = load_script(REPO / "scripts/lower_tertiary/build_dc_drilldown.py")
    source = synthetic_inputs[0]
    rows = list(csv.DictReader(source.open()))
    second = dict(
        rows[0],
        API_WELL_NUMBER="000000000101",
        DRILLING_DAYS="0",
        COMPLETION_DAYS="2",
        PND_DAYS="0",
        DAYS_STATUS="war_covered",
        BASIS="a different full rule",
    )
    with source.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=second)
        writer.writeheader()
        writer.writerows([rows[0], second])
    patch_inputs(monkeypatch, mod, synthetic_inputs)
    payload = mod.load_payload()
    for surface in ("fields", "blocks"):
        aggregate = payload[surface][0]
        assert aggregate["basis"] == "mixed"
        assert aggregate["drill"] is None
        assert aggregate["compl"] is None
        assert aggregate["pnd_days"] is None
    html = mod.build_html(payload)
    assert "Basis: mixed" in html
    assert "<th>Basis</th><th>PND days</th><th>Days status</th>" in html
    assert "None drilling" not in html
    assert "const add=(d,c)=>d==null||c==null?null:d+c" in html
    assert "Day counts follow the recorded basis" in html
    assert "'basis':" not in html  # Never render Python mapping repr.


def test_existing_dataset_card_gets_column_documentation():
    mod = load_script(REPO / "scripts/hf_export/publish_dc_days_to_hf.py")
    old = "config_name: dc_bores\n\n## D&C days QA/QC tables\nOld description\n"
    patched = mod.patch_readme(old)
    assert "`pnd_days` (nullable integer" in patched
    assert "Old description" not in patched
    assert mod.patch_readme(patched) == patched


def test_listing_renders_metadata_and_nulls(monkeypatch, synthetic_inputs):
    mod = load_script(REPO / "scripts/lower_tertiary/build_wo_per_well_dc.py")
    patch_inputs(monkeypatch, mod, synthetic_inputs)
    text = mod.build_markdown(mod.load_bores(), {})
    assert "Basis | PND (days) | Days status" in text
    assert "no_war_activity" in text
    assert "None" not in text
    assert "spud to total depth" not in text


def test_vintage_csv_to_dataset_roundtrip(monkeypatch, synthetic_inputs, tmp_path):
    import pandas as pd

    builder = load_script(REPO / "scripts/lower_tertiary/build_dc_vintage_diff.py")
    candidate = pd.read_csv(
        synthetic_inputs[0], keep_default_na=False, dtype={"API_WELL_NUMBER": str}
    )
    builder.build_diff(candidate.drop(columns=["BASIS"]), candidate).to_csv(
        synthetic_inputs[2],
        index=False,
    )
    listing = load_script(REPO / "scripts/lower_tertiary/build_wo_per_well_dc.py")
    patch_inputs(monkeypatch, listing, synthetic_inputs)
    exporter = load_script(REPO / "scripts/hf_export/publish_dc_days_to_hf.py")
    monkeypatch.setattr(exporter, "_load_listing_module", lambda: listing)
    monkeypatch.setattr(exporter, "_drilldown_extras", lambda: {})
    for name, table in exporter.build_tables().items():
        target = tmp_path / f"synthetic_{name}.parquet"
        table.to_parquet(target, index=False)
        restored = pd.read_parquet(target)
        assert restored.equals(table)
        assert pd.isna(restored.loc[0, "pnd_days"])


@pytest.mark.parametrize(
    "script",
    [
        "scripts/lower_tertiary/build_wo_per_well_dc.py",
        "scripts/lower_tertiary/build_dc_drilldown.py",
        "scripts/lower_tertiary/build_dc_vintage_diff.py",
        "scripts/hf_export/publish_dc_days_to_hf.py",
    ],
)
def test_direct_cli_imports_without_pythonpath(script):
    import os
    import subprocess
    import sys

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for name in ("PYTHONPATH", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(name, None)
    # Import only: no production generation, publication, or source requests.
    command = [
        sys.executable,
        "-c",
        "import runpy,sys; runpy.run_path(sys.argv[1])",
        script,
    ]
    result = subprocess.run(command, cwd=REPO, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "missing", ["basis_v30", "basis_wed", "pnd_days", "days_status"]
)
def test_incomplete_vintage_schema_refused(monkeypatch, synthetic_inputs, missing):
    mod = load_script(REPO / "scripts/lower_tertiary/build_wo_per_well_dc.py")
    patch_inputs(monkeypatch, mod, synthetic_inputs)
    row = dict(
        api12="000000000100",
        category="unchanged",
        basis="a",
        basis_v30="a",
        basis_wed="a",
        pnd_days="0",
        days_status="war_covered",
    )
    row.pop(missing)
    with synthetic_inputs[2].open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)
    with pytest.raises(ValueError, match="provenance"):
        mod.load_vintage_diff()


@pytest.mark.parametrize("column", ["basis", "basis_v30", "basis_wed"])
def test_blank_vintage_basis_refused(column):
    mod = load_script(REPO / "scripts/lower_tertiary/dc_provenance.py")
    row = dict(
        basis="a",
        basis_v30="a",
        basis_wed="a",
        pnd_days=None,
        days_status="no_war_activity",
    )
    row[column] = " "
    with pytest.raises(ValueError, match="provenance"):
        mod.validate_vintage_row(row)


def test_drilldown_refuses_legacy_vintage_claim(monkeypatch, synthetic_inputs):
    mod = load_script(REPO / "scripts/lower_tertiary/build_dc_drilldown.py")
    patch_inputs(monkeypatch, mod, synthetic_inputs)
    synthetic_inputs[2].write_text(
        "api12,category\n000000000100,unchanged\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="provenance"):
        mod.load_payload()
