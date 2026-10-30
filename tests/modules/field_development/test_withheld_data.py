"""Public readers must not silently consume the withheld historical catalog."""

from pathlib import Path

import pytest

from worldenergydata.field_development import subseaiq
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


@pytest.mark.parametrize("name", WITHHELD)
def test_public_payload_is_replaced_by_notice(name):
    path = CURATED / name
    assert not path.exists(), f"Restricted payload remains: {name}"
    assert REASON in path.with_suffix(path.suffix + ".md").read_text()


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
        "Synthetic field,United States,MC1,Oil,100,Y\n"
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
        text = path.read_text()
        assert REASON in text, path.relative_to(ROOT)
        assert "<table" not in text
        assert "<script" not in text


def test_metadata_does_not_advertise_withheld_payloads():
    import json

    import yaml

    data = ROOT / "data/modules/offshore_assets"
    schema = yaml.safe_load((data / "schema.yaml").read_text())
    metadata = json.loads((data / "_metadata.json").read_text())
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
    ],
)
def test_default_generators_reject_withheld_input(script, function):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "withheld_generator", ROOT / "scripts" / script
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(RuntimeError, match=REASON):
        getattr(module, function)()
