"""Date-schema regression checks for directional-survey preparation."""

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.well_api12 import WellAPI12

ROOT = Path(__file__).resolve().parents[4]


def test_held_borehole_date_schema():
    """The held public borehole row carries source date names."""
    source = pd.read_csv(
        ROOT / "data/modules/bsee/current/wells/well_data.csv", nrows=1
    )
    before = source.copy(deep=True)
    api = WellAPI12()
    api.prepare_well_paths(pd.DataFrame(), {"merged_api12_df": source})
    for display, raw in (
        ("Total Depth Date", "TOTAL_DEPTH_DATE"),
        ("Spud Date", "WELL_SPUD_DATE"),
    ):
        assert api.output_data_api12_df[display].iloc[0] == pd.to_datetime(
            source[raw].iloc[0]
        )
    pd.testing.assert_frame_equal(source, before)
    assert api.output_data_well_path == {}


@pytest.mark.parametrize(
    "dates",
    [
        {"Total Depth Date": "2023-06-15", "Spud Date": "2023-04-10"},
        {"TOTAL_DEPTH_DATE": "2023-06-15", "WELL_SPUD_DATE": "2023-04-10"},
        {},
    ],
)
def test_date_metadata_does_not_change_geometry(dates):
    """Optional metadata has no role in minimum-curvature positions."""
    source = pd.DataFrame([{"API12": 1, "SURF_x_rel": 0, "SURF_y_rel": 0, **dates}])
    survey = pd.DataFrame(
        {
            "API12": [1, 1],
            "SURVEY_POINT_MD": [0, 1000],
            "INCL_ANG_DEG_VAL": [0, 0],
            "INCL_ANG_MIN_VAL": [0, 0],
            "DIR_DEG_VAL": [0, 0],
            "DIR_MINS_VAL": [0, 0],
            "WELL_N_S_CODE": ["N", "N"],
            "WELL_E_W_CODE": ["E", "E"],
        }
    )
    api = WellAPI12()
    api.prepare_well_paths(survey, {"merged_api12_df": source})
    path = api.output_data_well_path[1]
    assert path["x_coor"].tolist() == [0, 0]
    assert path["y_coor"].tolist() == [0, 0]
    assert path["z_coor"].iloc[-1] == pytest.approx(1000)
    if not dates:
        assert api.output_data_api12_df["Total Depth Date"].isna().all()
        assert api.output_data_api12_df["Spud Date"].isna().all()


def test_legacy_date_columns_keep_precedence():
    source = pd.DataFrame(
        [
            {
                "Total Depth Date": "2023-06-15",
                "TOTAL_DEPTH_DATE": "2023-07-20",
                "Spud Date": "2023-04-10",
                "WELL_SPUD_DATE": "2023-05-01",
            }
        ]
    )
    api = WellAPI12()
    api.prepare_well_paths(pd.DataFrame(), {"merged_api12_df": source})
    assert api.output_data_api12_df["Total Depth Date"].iloc[0] == pd.Timestamp(
        "2023-06-15"
    )
    assert api.output_data_api12_df["Spud Date"].iloc[0] == pd.Timestamp("2023-04-10")


def test_public_record_reproducible_and_revision_bound():
    import hashlib
    import json

    from worldenergydata.bsee.analysis.directional_survey_validation import build_record

    inputs = ROOT / "data/modules/bsee/directional_survey_validation"
    first = build_record(inputs)
    assert first == build_record(inputs)
    assert first["revision_history"][-1]["revision"] == first["revision"]
    assert first["summary"]["record_count"] == len(first["stations"])
    assert first["summary"]["passes"]["relative_tvd_ft"]
    for name, digest in first["input_digests"].items():
        assert digest == hashlib.sha256((inputs / name).read_bytes()).hexdigest()
    saved = json.loads(
        (
            ROOT / "docs/data-sources/bsee/analysis/survey/one_well_validation.json"
        ).read_text()
    )
    regeneration = (
        "python -m worldenergydata.bsee.analysis.directional_survey_validation "
        "--input-dir data/modules/bsee/directional_survey_validation "
        "--output docs/data-sources/bsee/analysis/survey/one_well_validation.json"
    )
    assert first["method_digests"] == saved["method_digests"], (
        "Pinned method digests differ. Regenerate the saved record:\n" + regeneration
    )
    assert first == saved


def test_tampered_public_data_rejected(tmp_path):
    import hashlib
    import json
    import shutil

    from worldenergydata.bsee.analysis.directional_survey_validation import build_record

    inputs = ROOT / "data/modules/bsee/directional_survey_validation"
    original = hashlib.sha256((inputs / "stations.csv").read_bytes()).hexdigest()
    copied = tmp_path / "input"
    shutil.copytree(inputs, copied)
    raw = copied / "stations.csv"
    before = raw.read_bytes()
    raw.write_bytes(before + b"\n")
    tampered = hashlib.sha256(raw.read_bytes()).hexdigest()
    assert tampered != original
    with pytest.raises(ValueError, match="Survey input digest mismatch"):
        build_record(copied)
    raw.write_bytes(before)
    restored = hashlib.sha256(raw.read_bytes()).hexdigest()
    assert restored == original
    (tmp_path / "probe-evidence.json").write_text(
        json.dumps({"before": original, "tampered": tampered, "restored": restored})
        + "\n"
    )
    assert (
        original == hashlib.sha256((inputs / "stations.csv").read_bytes()).hexdigest()
    )


@pytest.mark.parametrize("kind", ["criteria", "revision", "chronology"])
def test_invalid_qualification_evidence_rejected(tmp_path, kind):
    import hashlib
    import json
    import shutil

    from worldenergydata.bsee.analysis.directional_survey_validation import build_record

    inputs = ROOT / "data/modules/bsee/directional_survey_validation"
    copied = tmp_path / "input"
    shutil.copytree(inputs, copied)
    if kind == "revision":
        path = copied / "revision.json"
        data = json.loads(path.read_text())
        data["revision"] = "2"
        message = "Newest history row"
    else:
        path = copied / "execution.json"
        data = json.loads(path.read_text())
        if kind == "criteria":
            data["criteria_sha256"] = "0" * 64
            message = "Criteria digest mismatch"
        else:
            data["first_computation_started_at"] = data["criteria_recorded_at"]
            message = "Criteria must precede"
    before = path.read_bytes()
    before_hash = hashlib.sha256(before).hexdigest()
    path.write_text(json.dumps(data) + "\n")
    tampered = hashlib.sha256(path.read_bytes()).hexdigest()
    assert tampered != before_hash
    with pytest.raises(ValueError, match=message):
        build_record(copied)
    path.write_bytes(before)
    restored = hashlib.sha256(path.read_bytes()).hexdigest()
    assert restored == before_hash
    (tmp_path / "probe-evidence.json").write_text(
        json.dumps({"before": before_hash, "tampered": tampered, "restored": restored})
        + "\n"
    )


def test_changed_method_pin_reports_regeneration(monkeypatch):
    import re

    from worldenergydata.bsee.analysis import directional_survey_validation as module

    original = module.build_record

    def changed_method(input_dir):
        record = original(input_dir)
        record["method_digests"]["well_api12.py"] = "0" * 64
        return record

    monkeypatch.setattr(module, "build_record", changed_method)
    command = (
        "python -m worldenergydata.bsee.analysis.directional_survey_validation "
        "--input-dir data/modules/bsee/directional_survey_validation "
        "--output docs/data-sources/bsee/analysis/survey/one_well_validation.json"
    )
    with pytest.raises(AssertionError, match=re.escape(command)):
        test_public_record_reproducible_and_revision_bound()
    assert command in module.__doc__


def test_digest_inputs_keep_checkout_bytes():
    import os
    import subprocess

    method_dir = "packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/"
    files = [
        "data/modules/bsee/directional_survey_validation/stations.csv",
        "data/modules/bsee/directional_survey_validation/source.json",
        method_dir + "well_api12.py",
        method_dir + "directional_survey_validation.py",
    ]
    env = os.environ.copy()
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(name, None)
    result = subprocess.run(
        ["git", "check-attr", "text", "eol", "--", *files],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    attributes = result.stdout.splitlines()
    for path in files[:2]:
        assert f"{path}: text: unset" in attributes
    for path in files[2:]:
        assert f"{path}: eol: lf" in attributes


@pytest.fixture
def extraction_fixture(tmp_path):
    """Artificial archive made from retained rows; no engineering qualification."""
    import csv
    import hashlib
    import itertools
    import json
    import zipfile

    inputs = ROOT / "data/modules/bsee/directional_survey_validation"
    source = json.loads((inputs / "source.json").read_text(encoding="utf-8"))
    with (ROOT / source["held_catalog"]).open(encoding="utf-8", newline="") as stream:
        catalog_rows = list(itertools.islice(csv.DictReader(stream), 2))
    catalog = tmp_path / "catalog.csv"
    catalog.write_text(
        "API_WELL_NUMBER\n"
        + catalog_rows[1]["API_WELL_NUMBER"]
        + "\n"
        + catalog_rows[0]["API_WELL_NUMBER"]
        + "\n",
        encoding="utf-8",
    )
    rows = (inputs / "stations.csv").read_bytes().splitlines(keepends=True)[:2]
    earlier_api = str(int(float(catalog_rows[1]["API_WELL_NUMBER"])))
    incomplete = rows[0].replace(source["api12"].encode(), earlier_api.encode())
    archive = tmp_path / "survey.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr(
            source["archive_member"],
            (incomplete + incomplete + b"".join(rows)).replace(b"\n", b"\r\n"),
        )
    source.update(
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        held_catalog_sha256=hashlib.sha256(catalog.read_bytes()).hexdigest(),
        record_count=2,
        data_sha256=hashlib.sha256(b"".join(rows)).hexdigest(),
    )
    manifest = tmp_path / "source.json"
    manifest.write_text(json.dumps(source) + "\n", encoding="utf-8")
    output = tmp_path / "retained.csv"
    return archive, catalog, manifest, output, b"".join(rows)


def _extractor():
    import runpy

    return runpy.run_path(
        str(ROOT / "scripts/bsee/extract_directional_survey_validation.py")
    )["extract"]


def test_extraction_selects_first_complete_unique_depth_survey(extraction_fixture):
    archive, catalog, manifest, output, expected = extraction_fixture
    extract = _extractor()
    extract(archive, catalog, manifest, output)
    assert output.read_bytes() == expected
    assert b"\r" not in output.read_bytes()
    extract(archive, catalog, manifest, output)
    assert output.read_bytes() == expected


@pytest.mark.parametrize(
    "field", ["archive_sha256", "held_catalog_sha256", "data_sha256"]
)
def test_extraction_rejects_digest_mismatch(extraction_fixture, field):
    import json

    archive, catalog, manifest, output, _ = extraction_fixture
    source = json.loads(manifest.read_text(encoding="utf-8"))
    source[field] = "0" * 64
    manifest.write_text(json.dumps(source) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        _extractor()(archive, catalog, manifest, output)
    assert not output.exists()
