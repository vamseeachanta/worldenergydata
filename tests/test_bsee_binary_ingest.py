"""Regression coverage for the approved BSEE binary ingestion pipeline."""

import hashlib
import pickle
import subprocess
import sys

import pandas as pd
import pytest
import yaml

from tests.bsee_ingest_support import SCRIPT, entries, run_ingest, workspace, write_zip


def test_borehole_zip_roundtrip_preserves_ids_and_removes_current_overlap(workspace):
    source, project, current = workspace
    raw = write_zip(
        source,
        "bin/borehole/BoreholeRawData.zip",
        {
            "BoreholeRawData/": "",
            "BoreholeRawData/mv_boreholes_all.txt": "API_WELL_NUMBER\tWELL_NAME\n001234567890\tAlpha\n001234567891\tNA\n",
        },
    )
    (current / "wells.csv").write_text(
        "WELL_NAME,API_WELL_NUMBER\nAlpha,001234567890\n"
    )
    result = run_ingest(workspace, "--dataset", "borehole")
    assert result.returncode == 0, result.stderr
    target = project / "data/modules/bsee/borehole/20261113.csv"
    actual = pd.read_csv(target, dtype=str, keep_default_na=False)
    assert actual.to_dict("records") == [
        {"API_WELL_NUMBER": "001234567891", "WELL_NAME": "NA"}
    ]
    record = entries(project)[0]
    assert record["row_count"] == 1
    assert record["source_row_count"] == 2
    assert record["duplicate_rows"] == 1
    assert record["source_sha256"] == hashlib.sha256(raw.read_bytes()).hexdigest()
    assert record["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert record["source_id"] == "bsee-data-center"
    assert record["source_member"] == "BoreholeRawData/mv_boreholes_all.txt"
    assert record["deduplication"]["status"] == "checked"
    assert (
        "existing"
        in yaml.safe_load((project / "data/catalog.yaml").read_text())["modules"]
    )
    assert not any(str(source) in str(value) for value in record.values())


@pytest.mark.parametrize("extension,protocol", [("bin", 4), ("pkl", 5)])
@pytest.mark.parametrize("output_format", ["csv", "parquet"])
def test_pickle_dataframe_roundtrip_and_idempotence(
    workspace, extension, protocol, output_format
):
    source, project, _ = workspace
    folder = source / "bin/war"
    folder.mkdir(parents=True)
    with (folder / f"mv_war_main.{extension}").open("wb") as handle:
        pickle.dump(
            pd.DataFrame({"SN_WAR": ["01", "02"], "REMARK": ["NA", "a,b\nc"]}),
            handle,
            protocol=protocol,
        )
    args = ("--dataset", "war", "--trust-pickles", "--format", output_format)
    first = run_ingest(workspace, *args)
    assert first.returncode == 0, first.stderr
    record = entries(project)[0]
    target = project / record["path"]
    actual = (
        pd.read_csv(target, dtype=str, keep_default_na=False)
        if output_format == "csv"
        else pd.read_parquet(target)
    )
    assert actual.to_dict("records") == [
        {"SN_WAR": "01", "REMARK": "NA"},
        {"SN_WAR": "02", "REMARK": "a,b\nc"},
    ]
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    second = run_ingest(workspace, *args)
    assert second.returncode == 0, second.stderr
    assert len(entries(project)) == 1
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
    assert record["deduplication"]["status"] == "no_comparable_schema"
    assert record["source_id"] == "bsee-ewell-war"


def test_headerless_directional_surveys_keep_first_row(workspace):
    source, project, _ = workspace
    write_zip(
        source,
        "zip/directional_survey/dsptsdelimit.zip",
        {
            "dsptsdelimit.txt": "001234567890,16,15,9166,S,21,0,E,8915,.003,-.004,-93.59,29.64\n"
            "001234567891,0,0,0,N,0,0,E,0,0,0,-93.59,29.64\n",
        },
    )
    write_zip(
        source,
        "zip/directional_survey/directdelimit.zip",
        {
            "directdelimit.txt": "001234567890,9166,16.250,159.000,8915.29,29.64,-93.59,,,,01/08/2025\n",
        },
    )
    result = run_ingest(workspace, "--dataset", "directional_survey")
    assert result.returncode == 0, result.stderr
    records = {r["name"]: r for r in entries(project)}
    points = records["dsptsdelimit"]
    data = pd.read_csv(project / points["path"], dtype=str, keep_default_na=False)
    assert len(data) == 2
    assert data.iloc[0]["API_WELL_NUMBER"] == "001234567890"
    assert data.iloc[0]["SURVEY_POINT_MD"] == "9166"
    direct = records["directdelimit"]
    assert direct["row_count"] == 1
    assert len(direct["columns"]) == 11
    assert direct["schema_status"] == "positional_unverified"


def test_war_zip_reads_every_table_and_prefers_raw_zip_over_pickle(workspace):
    source, project, _ = workspace
    write_zip(
        source,
        "bin/war/eWellWARRawData.zip",
        {
            "eWellWARRawData/mv_war_main.txt": "SN_WAR,REMARK\n01,raw\n",
            "eWellWARRawData/mv_war_main_prop.txt": "SN_WAR|ACTIVITY\n01|DRL\n",
        },
    )
    pd.DataFrame({"SN_WAR": ["01"], "REMARK": ["stale"]}).to_pickle(
        source / "bin/war/mv_war_main.bin"
    )
    result = run_ingest(workspace, "--dataset", "war")
    assert result.returncode == 0, result.stderr
    assert sorted(r["name"] for r in entries(project)) == [
        "mv_war_main",
        "mv_war_main_prop",
    ]
    record = next(r for r in entries(project) if r["name"] == "mv_war_main")
    assert pd.read_csv(project / record["path"]).iloc[0]["REMARK"] == "raw"


@pytest.mark.parametrize(
    "member,body",
    [
        ("../escape.txt", "A,B\n1,2\n"),
        ("table.txt", "A,B\n1,2,3\n"),
        ("table.txt", ""),
        ("table.txt", "A,A\n1,2\n"),
    ],
)
def test_invalid_input_leaves_catalog_and_existing_output_unchanged(
    workspace, member, body
):
    source, project, _ = workspace
    write_zip(source, "bin/borehole/BoreholeRawData.zip", {member: body})
    catalog = project / "data/catalog.yaml"
    before = catalog.read_bytes()
    target = project / "data/modules/bsee/borehole/20261113.csv"
    target.parent.mkdir(parents=True)
    target.write_text("preserved\n")
    result = run_ingest(workspace, "--dataset", "borehole")
    assert result.returncode != 0
    assert catalog.read_bytes() == before
    assert target.read_text() == "preserved\n"
    assert not list(project.rglob("*.partial"))


def test_untrusted_pickle_is_rejected_before_loading(workspace):
    source, project, _ = workspace
    folder = source / "bin/rig_fleet"
    folder.mkdir(parents=True)
    pd.DataFrame({"RIG_NAME": ["Rig A"]}).to_pickle(folder / "rig_fleet.bin")
    result = run_ingest(workspace, "--dataset", "rig_fleet")
    assert result.returncode != 0
    assert "trust-pickles" in result.stderr
    assert not (project / "data/modules/bsee").exists()


def test_missing_dataset_fails_without_catalog_changes(workspace):
    _, project, _ = workspace
    catalog = project / "data/catalog.yaml"
    before = catalog.read_bytes()
    result = run_ingest(workspace, "--dataset", "war")
    assert result.returncode != 0
    assert catalog.read_bytes() == before


def test_lfs_pointer_is_not_treated_as_current_data(workspace):
    source, project, current = workspace
    write_zip(source, "bin/borehole/BoreholeRawData.zip", {"table.txt": "A,B\n1,2\n"})
    (current / "pointer.csv").write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 100\n"
    )
    result = run_ingest(workspace, "--dataset", "borehole")
    assert result.returncode != 0
    assert "LFS" in result.stderr
    assert not (project / "data/modules/bsee").exists()


def test_source_root_can_share_bsee_parent_with_derived_tiers(workspace):
    _, project, current = workspace
    source = project / "data/modules/bsee"
    write_zip(
        source,
        "bin/borehole/BoreholeRawData.zip",
        {
            "mv_boreholes_all.txt": "API_WELL_NUMBER,WELL_NAME\n001234567890,Alpha\n",
        },
    )
    result = run_ingest((source, project, current), "--dataset", "borehole")
    assert result.returncode == 0, result.stderr
    assert (source / "borehole/20261113.csv").is_file()


def test_late_corrupt_table_preserves_all_previous_outputs(workspace):
    source, project, _ = workspace
    write_zip(
        source,
        "bin/war/eWellWARRawData.zip",
        {
            "a.txt": "A,B\n1,2\n",
            "z.txt": "A,B\n3,4,5\n",
        },
    )
    target = project / "data/modules/bsee/war/20261113_a.csv"
    target.parent.mkdir(parents=True)
    target.write_text("original\n")
    catalog = project / "data/catalog.yaml"
    before = catalog.read_bytes()
    result = run_ingest(workspace, "--dataset", "war")
    assert result.returncode != 0
    assert "Row width" in result.stderr
    assert target.read_text() == "original\n"
    assert catalog.read_bytes() == before
    assert list(target.parent.iterdir()) == [target]


def test_header_only_table_registers_zero_rows(workspace):
    source, project, _ = workspace
    write_zip(
        source,
        "bin/borehole/BoreholeRawData.zip",
        {
            "mv_boreholes_all.txt": "API_WELL_NUMBER,WELL_NAME\n",
        },
    )
    result = run_ingest(workspace, "--dataset", "borehole")
    assert result.returncode == 0, result.stderr
    assert entries(project)[0]["row_count"] == 0
    assert (
        project / "data/modules/bsee/borehole/20261113.csv"
    ).read_text() == "API_WELL_NUMBER,WELL_NAME\n"


def test_missing_current_tier_is_not_silently_accepted(workspace):
    source, project, current = workspace
    write_zip(source, "bin/borehole/BoreholeRawData.zip", {"table.txt": "A,B\n1,2\n"})
    current.rmdir()
    result = run_ingest(workspace, "--dataset", "borehole")
    assert result.returncode != 0
    assert "Current CSV tier is unavailable" in result.stderr
    assert not (project / "data/modules/bsee").exists()


def test_pickle_payload_must_be_dataframe(workspace):
    source, project, _ = workspace
    path = source / "bin/war/invalid.pkl"
    path.parent.mkdir(parents=True)
    path.write_bytes(pickle.dumps({"not": "a table"}))
    result = run_ingest(workspace, "--dataset", "war", "--trust-pickles")
    assert result.returncode != 0
    assert "not a DataFrame" in result.stderr
    assert not (project / "data/modules/bsee").exists()


def test_make_unpack_bsee_runs_configured_interpreter(workspace):
    source, project, current = workspace
    write_zip(
        source,
        "bin/borehole/BoreholeRawData.zip",
        {
            "mv_boreholes_all.txt": "API_WELL_NUMBER,WELL_NAME\n001234567890,Alpha\n",
        },
    )
    result = subprocess.run(
        [
            "make",
            "unpack-bsee",
            f"BSEE_INGEST_PYTHON={sys.executable}",
            f"BSEE_SOURCE_ROOT={source}",
            f"BSEE_INGEST_ARGS=--project-root {project} --current-root {current} --dataset borehole --date 2026-11-13",
        ],
        cwd=SCRIPT.parents[2],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert (project / "data/modules/bsee/borehole/20261113.csv").is_file()


def test_single_column_current_table_does_not_prevent_other_schema_ingest(workspace):
    source, project, current = workspace
    (current / "blocks.csv").write_text("BLOCK_CODE\nGC807\n")
    write_zip(
        source,
        "bin/borehole/BoreholeRawData.zip",
        {
            "mv_boreholes_all.txt": "API_WELL_NUMBER,WELL_NAME\n001234567890,Alpha\n",
        },
    )
    result = run_ingest(workspace, "--dataset", "borehole")
    assert result.returncode == 0, result.stderr
    assert entries(project)[0]["row_count"] == 1


def test_symbolic_output_directory_cannot_redirect_writes_outside_project(workspace):
    source, project, _ = workspace
    write_zip(
        source,
        "bin/borehole/BoreholeRawData.zip",
        {
            "mv_boreholes_all.txt": "API_WELL_NUMBER,WELL_NAME\n001234567890,Alpha\n",
        },
    )
    output = project / "data/modules/bsee/borehole"
    output.parent.mkdir(parents=True)
    output.symlink_to(source, target_is_directory=True)
    result = run_ingest(workspace, "--dataset", "borehole")
    assert result.returncode != 0
    assert "Output cannot overwrite" in result.stderr
    assert not (source / "20261113.csv").exists()


def test_content_detection_is_independent_of_file_extension(workspace):
    source, project, _ = workspace
    path = source / "bin/war/table.bin"
    path.parent.mkdir(parents=True)
    path.write_text("SN_WAR,REMARK\n001,delimited\n")
    result = run_ingest(workspace, "--dataset", "war")
    assert result.returncode == 0, result.stderr
    assert entries(project)[0]["source_format"] == "delimited"
    assert entries(project)[0]["row_count"] == 1


def test_quoted_multiline_current_values_with_escaped_quotes_match_exactly(workspace):
    source, project, current = workspace
    body = 'SN_WAR,TEXT_REMARK\n01,"He said ""NA, Inc"".\nSecond line"\n'
    (current / "remarks.csv").write_text(body)
    write_zip(source, "bin/war/eWellWARRawData.zip", {"mv_war_main.txt": body})
    result = run_ingest(workspace, "--dataset", "war")
    assert result.returncode == 0, result.stderr
    record = entries(project)[0]
    assert record["source_row_count"] == 1
    assert record["duplicate_rows"] == 1
    assert record["row_count"] == 0
    assert (
        record["deduplication"]["compared_sources"][0]["sha256"]
        == hashlib.sha256(body.encode()).hexdigest()
    )


def test_colliding_archive_table_names_fail_instead_of_dropping_data(workspace):
    source, project, _ = workspace
    write_zip(
        source,
        "bin/war/eWellWARRawData.zip",
        {
            "first/table.txt": "SN_WAR,REMARK\n001,first\n",
            "second/table.txt": "SN_WAR,REMARK\n002,second\n",
        },
    )
    catalog = project / "data/catalog.yaml"
    before = catalog.read_bytes()
    result = run_ingest(workspace, "--dataset", "war")
    assert result.returncode != 0
    assert "Ambiguous table name" in result.stderr
    assert catalog.read_bytes() == before
    assert not (project / "data/modules/bsee").exists()
