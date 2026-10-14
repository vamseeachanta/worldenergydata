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
