"""Offline synthetic examples for additive D&C provenance propagation."""

import csv
import importlib.util
import socket
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
LABELS = {"basis", "basis_v30", "basis_wed", "pnd_days", "days_status"}


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


def write_rows(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def synthetic_inputs(tmp_path):
    return make_synthetic_inputs(tmp_path)


def make_synthetic_inputs(tmp_path):
    row = dict(
        LEASE_NAME="Anchor",
        SURF_LEASE_NUM="G00001",
        WATER_DEPTH="100",
        API_WELL_NUMBER="100",
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
        BASIS="synthetic rule a",
    )
    second = dict(
        row,
        API_WELL_NUMBER="101",
        DRILLING_DAYS="3",
        COMPLETION_DAYS="2",
        PND_DAYS="1",
        DAYS_STATUS="war_covered",
        BASIS="synthetic rule b",
    )
    source = tmp_path / "synthetic_bores.csv"
    write_rows(source, [row, second])
    benchmark = tmp_path / "synthetic_benchmark.csv"
    benchmark.write_text("api12\n", encoding="utf-8")
    vintage = tmp_path / "synthetic_vintage.csv"
    vintage.write_text(
        "api12,dev,category,drill_v30,compl_v30,drill_wed,compl_wed,d_drill,d_compl,spud_wed\n"
        "100,Anchor,unchanged,0,0,0,0,0,0,\n"
        "101,Anchor,servicing_accrual,3,1,3,2,0,1,\n",
        encoding="utf-8",
    )
    return source, benchmark, vintage


def patch_inputs(monkeypatch, mod, inputs):
    for name, value in zip(("SOURCE_CSV", "BENCHMARK_CSV", "VINTAGE_CSV"), inputs):
        monkeypatch.setattr(mod, name, value)


def remove_source_labels(source):
    rows = list(csv.DictReader(source.open(encoding="utf-8")))
    write_rows(
        source,
        [
            {
                k: v
                for k, v in r.items()
                if k not in {"BASIS", "PND_DAYS", "DAYS_STATUS"}
            }
            for r in rows
        ],
    )


def strip_labels(value):
    if isinstance(value, dict):
        return {k: strip_labels(v) for k, v in value.items() if k not in LABELS}
    if isinstance(value, list):
        return [strip_labels(v) for v in value]
    return value


@pytest.mark.parametrize(
    "script,loader",
    [
        ("build_wo_per_well_dc.py", "load_bores"),
        ("build_dc_drilldown.py", "load_payload"),
    ],
)
def test_synthetic_labels_are_additive(monkeypatch, synthetic_inputs, script, loader):
    mod = load_script(REPO / "scripts/lower_tertiary" / script)
    patch_inputs(monkeypatch, mod, synthetic_inputs)
    labelled = getattr(mod, loader)()
    bores = labelled["bores"] if loader == "load_payload" else labelled["Anchor"]
    assert (bores[0]["drill"], bores[0]["compl"]) == (0, 0)
    assert bores[0]["pnd_days"] is None
    assert bores[0]["basis"] == "synthetic rule a"
    assert bores[1]["days_status"] == "war_covered"
    if loader == "load_payload":
        for surface in ("fields", "blocks"):
            group = labelled[surface][0]
            assert (group["drill"], group["compl"]) == (3, 2)
            assert group["basis"] == group["days_status"] == "mixed"
    remove_source_labels(synthetic_inputs[0])
    legacy = getattr(mod, loader)()
    assert strip_labels(labelled) == legacy
    if loader == "load_payload":
        html = mod.build_html(labelled)
        assert "<th>Basis</th>" in html
        assert "<th>Days status</th>" in html
        assert "{b.drill}</td>" in html  # Existing cell representation is retained.
    else:
        markdown = mod.build_markdown(labelled, mod.load_vintage_diff())
        assert "Basis | PND (days) | Days status" in markdown
        assert "| 0 | 0 | 0 |" in markdown
        assert "mixed" in markdown


@pytest.mark.parametrize(
    "script,loader",
    [
        ("build_wo_per_well_dc.py", "load_bores"),
        ("build_dc_drilldown.py", "load_payload"),
    ],
)
def test_synthetic_without_basis_has_no_new_fields(
    monkeypatch, synthetic_inputs, script, loader
):
    remove_source_labels(synthetic_inputs[0])
    mod = load_script(REPO / "scripts/lower_tertiary" / script)
    patch_inputs(monkeypatch, mod, synthetic_inputs)
    data = getattr(mod, loader)()
    assert strip_labels(data) == data
    if loader == "load_payload":
        assert data["bores"][0]["vin"] == "unchanged"
        html = mod.build_html(data)
        assert "<th>Basis</th>" not in html
    else:
        markdown = mod.build_markdown(data, mod.load_vintage_diff())
        assert "Basis | PND (days) | Days status" not in markdown


@pytest.mark.parametrize(
    "script,loader",
    [
        ("build_wo_per_well_dc.py", "load_bores"),
        ("build_dc_drilldown.py", "load_payload"),
    ],
)
def test_synthetic_invalid_basis_refused(monkeypatch, synthetic_inputs, script, loader):
    source = synthetic_inputs[0]
    rows = list(csv.DictReader(source.open(encoding="utf-8")))
    rows[0]["BASIS"] = " "
    write_rows(source, rows)
    mod = load_script(REPO / "scripts/lower_tertiary" / script)
    patch_inputs(monkeypatch, mod, synthetic_inputs)
    with pytest.raises(ValueError, match="provenance"):
        getattr(mod, loader)()


def synthetic_vintages():
    # Synthetic categories exercise the unchanged MB precedence and outer join.
    old = pd.DataFrame(
        {
            "API_WELL_NUMBER": [100, 101, 102, 103, 104],
            "LEASE_NAME": ["Anchor"] * 5,
            "DRILLING_DAYS": [0, 3, 4, 5, 6],
            "COMPLETION_DAYS": [0, 1, 2, 3, 4],
            "WELL_SPUD_DATE": [
                float("nan"),
                "2020-01-01",
                "2020-01-01",
                "2020-01-01",
                "2020-01-01",
            ],
        }
    )
    new = old.iloc[:4].copy()
    new["API_WELL_NUMBER"] = new["API_WELL_NUMBER"].astype(str)
    new.loc[0, "WELL_SPUD_DATE"] = "2020-01-01"
    new.loc[1, "COMPLETION_DAYS"] = 2
    new.loc[2, "DRILLING_DAYS"] = 7
    extra = new.iloc[[3]].copy()
    extra["API_WELL_NUMBER"] = "105"
    new = pd.concat([new, extra], ignore_index=True)
    return old, new


def add_source_labels(frame, basis):
    return frame.assign(BASIS=basis, PND_DAYS=1, DAYS_STATUS="war_covered")


def test_synthetic_vintage_labels_preserve_categories_and_dtypes():
    mod = load_script(REPO / "scripts/lower_tertiary/build_dc_vintage_diff.py")
    old, new = synthetic_vintages()
    legacy = mod.build_diff(old, new)
    labelled = mod.build_diff(
        add_source_labels(old, "synthetic rule a"),
        add_source_labels(new, "synthetic rule b"),
    )
    pd.testing.assert_frame_equal(labelled[legacy.columns], legacy)
    assert set(legacy["category"]) == {
        "late_data",
        "servicing_accrual",
        "drilling_changed",
        "unchanged",
        "v30_only",
        "wed_only",
    }
    assert labelled.loc[0, "basis"] == "mixed"
    assert str(labelled["pnd_days"].dtype) == "Int64"
    assert labelled.loc[0, "days_status"] == "war_covered"
    partial = mod.build_diff(old, add_source_labels(new, "synthetic rule b"))
    assert pd.isna(partial.loc[0, "basis_v30"])
    assert partial.loc[0, "basis"] == "synthetic rule b"
    assert "unavailable" not in partial.to_csv(index=False)


def test_synthetic_vintage_without_basis_has_mb_schema():
    mod = load_script(REPO / "scripts/lower_tertiary/build_dc_vintage_diff.py")
    old, new = synthetic_vintages()
    assert list(mod.build_diff(old, new)) == [
        "api12",
        "dev",
        "category",
        "drill_v30",
        "compl_v30",
        "drill_wed",
        "compl_wed",
        "d_drill",
        "d_compl",
        "spud_wed",
    ]


def test_synthetic_vintage_invalid_basis_refused():
    mod = load_script(REPO / "scripts/lower_tertiary/build_dc_vintage_diff.py")
    old, new = synthetic_vintages()
    with pytest.raises(ValueError, match="provenance"):
        mod.build_diff(old, add_source_labels(new, " "))


def publisher(monkeypatch, inputs):
    listing = load_script(REPO / "scripts/lower_tertiary/build_wo_per_well_dc.py")
    patch_inputs(monkeypatch, listing, inputs)
    mod = load_script(REPO / "scripts/hf_export/publish_dc_days_to_hf.py")
    monkeypatch.setattr(mod, "_load_listing_module", lambda: listing)
    monkeypatch.setattr(mod, "_drilldown_extras", lambda: {})
    return mod


def test_synthetic_publisher_labels_preserve_all_existing_columns(
    monkeypatch, synthetic_inputs, tmp_path
):
    mod = publisher(monkeypatch, synthetic_inputs)
    labelled = mod.build_tables()
    remove_source_labels(synthetic_inputs[0])
    legacy = mod.build_tables()
    for config in legacy:
        pd.testing.assert_frame_equal(
            labelled[config][legacy[config].columns], legacy[config]
        )
        target = tmp_path / f"synthetic_{config}.parquet"
        labelled[config].to_parquet(target, index=False)
        pd.testing.assert_frame_equal(pd.read_parquet(target), labelled[config])
    summary = labelled["dc_development_summary"].iloc[0]
    assert summary["dc_days_wed"] == 5
    assert (
        summary["delta_days"] == 5 - mod._load_listing_module().WO_ARTICLE["Anchor"][2]
    )
    assert summary["basis"] == summary["days_status"] == "mixed"
    assert pd.isna(summary["pnd_days"])
    assert labelled["dc_bores"].loc[0, "drilling_days"] == 0
    assert "basis" not in labelled["dc_vintage_diff"]  # Its own input is legacy.


def test_synthetic_publisher_without_basis_has_no_new_columns(
    monkeypatch, synthetic_inputs
):
    remove_source_labels(synthetic_inputs[0])
    tables = publisher(monkeypatch, synthetic_inputs).build_tables()
    for table in tables.values():
        assert not LABELS.intersection(table.columns)


def test_synthetic_publisher_invalid_basis_refused(monkeypatch, synthetic_inputs):
    source = synthetic_inputs[0]
    rows = list(csv.DictReader(source.open(encoding="utf-8")))
    rows[0]["BASIS"] = " "
    write_rows(source, rows)
    with pytest.raises(ValueError, match="provenance"):
        publisher(monkeypatch, synthetic_inputs).build_tables()


def test_basis_activation_and_day_schema_validation():
    mod = load_script(REPO / "scripts/lower_tertiary/dc_provenance.py")
    assert not mod.carries_basis(["DRILLING_DAYS", "PND_DAYS"])
    assert mod.carries_basis(["BASIS"])
    assert mod.carries_basis(["basis_v30"])
    with pytest.raises(ValueError, match="basis"):
        mod.validate_day_schema(["drilling_days", "pnd_days"])
    mod.validate_day_schema(["drilling_days", "basis"])


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
    result = subprocess.run(
        [sys.executable, "-c", "import runpy,sys; runpy.run_path(sys.argv[1])", script],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("builder", ["listing", "drilldown", "vintage", "publisher"])
@pytest.mark.parametrize("token", ["unavailable", "mixed"])
def test_synthetic_withdrawn_basis_token_refused(
    monkeypatch, synthetic_inputs, builder, token
):
    rows = list(csv.DictReader(synthetic_inputs[0].open(encoding="utf-8")))
    rows[0]["BASIS"] = token
    write_rows(synthetic_inputs[0], rows)
    with pytest.raises(ValueError, match="provenance"):
        if builder == "publisher":
            publisher(monkeypatch, synthetic_inputs).build_tables()
        elif builder == "vintage":
            mod = load_script(REPO / "scripts/lower_tertiary/build_dc_vintage_diff.py")
            old, new = synthetic_vintages()
            mod.build_diff(old, add_source_labels(new, token))
        else:
            name = (
                "build_wo_per_well_dc.py"
                if builder == "listing"
                else "build_dc_drilldown.py"
            )
            mod = load_script(REPO / "scripts/lower_tertiary" / name)
            patch_inputs(monkeypatch, mod, synthetic_inputs)
            getattr(mod, "load_bores" if builder == "listing" else "load_payload")()
