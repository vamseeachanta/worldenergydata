"""Public readers must not silently consume the withheld historical catalog."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from worldenergydata.field_development import subseaiq
from worldenergydata.field_development.data_availability import DatasetUnavailableError
from worldenergydata.field_development.host_enrichment import load_host_registry
from worldenergydata.field_development.portfolio_matched import load_matched_crosswalk

ROOT = Path(__file__).resolve().parents[3]
CURATED = ROOT / "data/modules/offshore_assets/curated"
WITHHELD = (
    "country_centroids.csv",
    "coverage_summary.csv",
    "drilling_rigs.csv",
    "fields.csv",
    "host_facilities.csv",
    "jackups.csv",
    "production_facilities.csv",
    "bsee_field_crosswalk.csv",
    "subseaiq_hosts.csv",
    "subseaiq_bsee_block_crosswalk.csv",
)
REASON = "held privately pending redistribution-terms review"
FACILITY_WITHHELD = (
    "fpso_basic_info.csv",
    "fpso_riser_info.csv",
    "semisub_basic_info.csv",
    "semisub_riser_info.csv",
    "spar_basic_info.csv",
    "spar_riser_info.csv",
    "tlp_basic_info.csv",
)


@pytest.mark.parametrize(
    "relative_path",
    [f"data/modules/offshore_assets/curated/{name}" for name in WITHHELD]
    + [f"data/modules/facility_specs/curated/{name}" for name in FACILITY_WITHHELD]
    + [
        "reports/field-atlas/_roster.json",
        "reports/field-atlas/_atlas_feed.json",
        "reports/decommissioning/regional_liability.csv",
        "reports/field_development/bsee_matched/_summary.json",
        "data/modules/bsee/atlas/2023/field_attribution.json",
    ],
)
def test_guard_rejects_restored_withheld_paths(tmp_path, monkeypatch, relative_path):
    from worldenergydata.field_development import data_availability

    monkeypatch.setattr(data_availability, "ROOT", tmp_path)
    monkeypatch.setattr(
        data_availability, "CURATED", tmp_path / "data/modules/offshore_assets/curated"
    )
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic stale input", encoding="utf-8", newline="\n")
    with pytest.raises(DatasetUnavailableError, match=REASON):
        data_availability.require_available_source(path)


def test_guard_allows_independent_synthetic_source(tmp_path):
    from worldenergydata.field_development.data_availability import (
        require_available_source,
    )

    path = tmp_path / "independent.json"
    path.write_text("[]", encoding="utf-8", newline="\n")
    assert require_available_source(path) == path


def test_roster_derived_attribution_is_withheld():
    import json

    path = ROOT / "data/modules/bsee/atlas/2023/field_attribution.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "status": "withheld",
        "note": f"The data set is {REASON}.",
    }


@pytest.mark.parametrize("name", FACILITY_WITHHELD)
def test_related_facility_payload_is_replaced_by_notice(name):
    path = ROOT / "data/modules/facility_specs/curated" / name
    assert not path.exists(), f"Restricted payload remains: {name}"
    assert REASON in path.with_suffix(path.suffix + ".md").read_text(encoding="utf-8")


def test_facility_schema_and_metadata_only_offer_retained_matrix():
    import json

    import yaml

    data = ROOT / "data/modules/facility_specs"
    schema = yaml.safe_load((data / "schema.yaml").read_text(encoding="utf-8"))
    metadata = json.loads((data / "_metadata.json").read_text(encoding="utf-8"))
    assert [row["name"] for row in schema["datasets"]] == [
        "mooring_facility_matrix.csv"
    ]
    assert set(FACILITY_WITHHELD) == {
        row["name"] for row in metadata["withheld_datasets"]
    }
    assert metadata["record_count"] is None
    assert all(row["status"] == "withheld" for row in metadata["withheld_datasets"])
    for row in metadata["withheld_datasets"]:
        assert REASON in (data / row["notice"]).read_text(encoding="utf-8")


@pytest.mark.parametrize("module", ["facility_specs", "offshore_assets"])
def test_public_inventory_covers_all_retained_files(module):
    import json

    data = ROOT / "data/modules" / module
    metadata = json.loads((data / "_metadata.json").read_text(encoding="utf-8"))
    actual = {
        path.relative_to(data).as_posix(): path.stat().st_size
        for path in data.rglob("*")
        if path.is_file() and path.name != "_metadata.json"
    }
    listed = {row["path"]: row["size_bytes"] for row in metadata["files"]}
    assert listed == actual
    assert metadata["file_count"] == len(actual) == len(metadata["files"])
    assert metadata["total_size_bytes"] == sum(actual.values())
    if module == "offshore_assets":
        coverage = next(
            row for row in metadata["files"] if row["name"] == "COVERAGE_SUMMARY.md"
        )
        assert coverage["modified"] >= "2026-10-29"


def test_atlas_feed_raises_the_package_availability_exception():
    import importlib.util

    from worldenergydata.field_development.data_availability import (
        DatasetUnavailableError,
    )

    spec = importlib.util.spec_from_file_location(
        "atlas_availability", ROOT / "scripts/field_atlas/build_atlas_feed.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(DatasetUnavailableError, match=REASON):
        module.build()


@pytest.mark.parametrize("name", WITHHELD)
def test_public_payload_is_replaced_by_notice(name):
    path = CURATED / name
    assert not path.exists(), f"Restricted payload remains: {name}"
    assert REASON in path.with_suffix(path.suffix + ".md").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "reader",
    [
        subseaiq.load_subseaiq_fields,
        subseaiq._load_facility_picks,
        lambda: subseaiq.build_bsee_crosswalk([]),
        load_host_registry,
        load_matched_crosswalk,
    ],
)
def test_default_readers_explain_withholding(reader):
    with pytest.raises(RuntimeError, match=REASON):
        reader()


@pytest.mark.parametrize(
    "reader,name",
    [
        (subseaiq.load_subseaiq_fields, "fields.csv"),
        (load_host_registry, "subseaiq_hosts.csv"),
        (load_matched_crosswalk, "subseaiq_bsee_block_crosswalk.csv"),
    ],
)
def test_explicit_bundled_path_cannot_bypass_withholding(reader, name):
    with pytest.raises(RuntimeError, match=REASON):
        reader(CURATED / name)


def test_independent_synthetic_input_remains_supported(tmp_path):
    path = tmp_path / "fields.csv"
    path.write_text(
        "FIELD_NAME,COUNTRY,BLOCK,RESERVE_TYPE,WATER_DEPTH_M,US_GOM_FLAG\n"
        "Synthetic field,United States,MC1,Oil,100,Y\n",
        encoding="utf-8",
        newline="\n",
    )
    fields = subseaiq.load_subseaiq_fields(path)
    assert len(fields) == 1
    assert fields[0].name == "Synthetic field"
    assert fields[0].water_depth_m == 100
    crosswalk = subseaiq.build_bsee_crosswalk(["MC1"], csv_path=path)
    assert crosswalk[0].matched is True


@pytest.mark.parametrize("name", WITHHELD)
def test_loader_stub_names_each_withheld_dataset(name):
    from worldenergydata.field_development.data_availability import (
        load_withheld_dataset,
    )

    with pytest.raises(RuntimeError, match=REASON):
        load_withheld_dataset(name)


def test_withheld_reports_expose_no_embedded_tables():
    paths = list((ROOT / "reports/field_development/bsee_matched").glob("*.html"))
    paths += [
        ROOT / "reports/field_development/showcase/index.html",
        ROOT / "reports/field_development/all_regions_atlas.html",
        ROOT / "reports/field_development/region_devtype_comparison.html",
        ROOT / "reports/decommissioning/regional_liability.html",
        ROOT / "reports/field-atlas/index.html",
    ]
    assert paths
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert REASON in text, path.relative_to(ROOT).as_posix()
        assert "<table" not in text
        assert "<script" not in text


def test_metadata_does_not_advertise_withheld_payloads():
    import json

    import yaml

    data = ROOT / "data/modules/offshore_assets"
    schema = yaml.safe_load((data / "schema.yaml").read_text(encoding="utf-8"))
    metadata = json.loads((data / "_metadata.json").read_text(encoding="utf-8"))
    assert not set(WITHHELD) & {row["name"] for row in schema["datasets"]}
    assert not set(WITHHELD) & {row["name"] for row in metadata["files"]}
    assert set(WITHHELD) == {row["name"] for row in metadata["withheld_datasets"]}
    assert all(row["status"] == "withheld" for row in metadata["withheld_datasets"])


@pytest.mark.parametrize(
    "script,function",
    [
        ("field_atlas/build_atlas_feed.py", "build"),
        ("field_atlas/build_field_atlas.py", "build"),
        ("field_development/build_all_regions_atlas.py", "read_coverage"),
        ("field_development/build_subseaiq_bsee_crosswalk.py", "main"),
        ("field_development/build_region_devtype_comparison.py", "build_table"),
        ("decommissioning/build_regional_liability.py", "main"),
        ("hf_export/build_explorer_results_bundle.py", "build_bundle"),
        ("field_development/build_contractor_jackups.py", "main"),
        ("field_development/integrate_angola_catalog.py", "build_from_arguments"),
    ],
)
def test_default_generators_reject_withheld_input(script, function, tmp_path):
    import importlib.util
    from argparse import Namespace

    spec = importlib.util.spec_from_file_location(
        "withheld_generator", ROOT / "scripts" / script
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    arguments = ()
    if script.endswith("build_contractor_jackups.py"):
        arguments = (
            [
                str(tmp_path / "unread.csv"),
                str(CURATED / "jackups.csv"),
                "--source-sha256",
                "0" * 64,
            ],
        )
    elif script.endswith("integrate_angola_catalog.py"):
        arguments = (Namespace(legacy=CURATED / "fields.csv"),)
    with pytest.raises(DatasetUnavailableError, match=REASON):
        getattr(module, function)(*arguments)


def test_coverage_reader_retains_its_docstring():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "coverage_docstring",
        ROOT / "scripts/field_development/build_all_regions_atlas.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.read_coverage.__doc__ == (
        "Return (by_country list of dicts, by_region dict, totals dict)."
    )


@pytest.mark.parametrize(
    "script",
    [
        "field_development/build_region_devtype_comparison.py",
        "decommissioning/build_regional_liability.py",
        "field_development/build_all_regions_atlas.py",
    ],
)
def test_direct_command_reaches_withholding_without_pythonpath(script, tmp_path):
    env = dict(os.environ)
    for key in ("PYTHONPATH", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode != 0
    assert "DatasetUnavailableError" in result.stderr
    assert REASON in result.stderr
    assert "ModuleNotFoundError" not in result.stderr
