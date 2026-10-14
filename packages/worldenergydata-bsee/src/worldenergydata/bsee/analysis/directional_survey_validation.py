"""Build a reproducible comparison with one published BSEE survey.

Regenerate the saved record after a change to either pinned method file:
python -m worldenergydata.bsee.analysis.directional_survey_validation --input-dir data/modules/bsee/directional_survey_validation --output docs/data-sources/bsee/analysis/survey/one_well_validation.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from worldenergydata.bsee.analysis.well_api12 import WellAPI12

COLUMNS = [
    "API_WELL_NUMBER",
    "INCL_ANG_DEG_VAL",
    "INCL_ANG_MIN_VAL",
    "SURVEY_POINT_MD",
    "WELL_N_S_CODE",
    "DIR_DEG_VAL",
    "DIR_MINS_VAL",
    "WELL_E_W_CODE",
    "SURVEY_POINT_TVD",
    "DELTA_X",
    "DELTA_Y",
    "SURF_LONGITUDE",
    "SURF_LATITUDE",
]


def digest(path):
    """Return the digest of the retained bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_inputs(input_dir):
    """Verify retained input digests and the predeclared criterion."""
    root = Path(input_dir)
    source = json.loads((root / "source.json").read_text(encoding="utf-8"))
    criteria = json.loads((root / "criteria.json").read_text(encoding="utf-8"))
    revision = json.loads((root / "revision.json").read_text(encoding="utf-8"))
    execution = json.loads((root / "execution.json").read_text(encoding="utf-8"))
    raw_path = root / "stations.csv"
    if digest(raw_path) != source["data_sha256"]:
        raise ValueError("Survey input digest mismatch")
    if digest(root / "criteria.json") != execution["criteria_sha256"]:
        raise ValueError("Criteria digest mismatch")
    recorded = datetime.fromisoformat(execution["criteria_recorded_at"])
    started = datetime.fromisoformat(execution["first_computation_started_at"])
    if recorded.tzinfo is None or started.tzinfo is None or recorded >= started:
        raise ValueError("Criteria must precede the first computation")
    if revision["history"][-1]["revision"] != revision["revision"]:
        raise ValueError("Newest history row does not match the declared revision")
    return root, source, criteria, revision, execution


def _load_survey(root, source):
    """Read the published stations without changing their values."""
    survey = pd.read_csv(root / "stations.csv", header=None, names=COLUMNS)
    if len(survey) != source["record_count"] or len(survey) < 2:
        raise ValueError("Survey record count mismatch or insufficient stations")
    if not survey["API_WELL_NUMBER"].astype(str).eq(source["api12"]).all():
        raise ValueError("Survey must contain exactly the declared API12")
    for column in ("WELL_N_S_CODE", "WELL_E_W_CODE"):
        survey[column] = survey[column].str.strip()
    if (
        not survey["WELL_N_S_CODE"].isin(["N", "S"]).all()
        or not survey["WELL_E_W_CODE"].isin(["E", "W"]).all()
    ):
        raise ValueError("Unknown survey quadrant")
    numbers = [
        c
        for c in COLUMNS
        if c not in ("API_WELL_NUMBER", "WELL_N_S_CODE", "WELL_E_W_CODE")
    ]
    if not np.isfinite(survey[numbers].to_numpy(dtype=float)).all():
        raise ValueError("Survey contains missing or non-finite values")
    if survey["SURVEY_POINT_MD"].duplicated().any():
        raise ValueError("Repeated measured depths need separate qualification")
    survey["raw_row"] = np.arange(1, len(survey) + 1)
    survey = survey.sort_values("SURVEY_POINT_MD").reset_index(drop=True)
    return survey


def _compute_comparisons(survey, source):
    """Use the production pipeline and align the published depth datum."""
    survey["API12"] = int(source["api12"])
    well = pd.DataFrame(
        [
            {
                "API12": int(source["api12"]),
                "SURF_x_rel": 0.0,
                "SURF_y_rel": 0.0,
                **source["well_dates"],
            }
        ]
    )
    api = WellAPI12()
    api.prepare_well_paths(survey, {"merged_api12_df": well})
    path = api.output_data_well_path[int(source["api12"])]
    reference_inc = survey.INCL_ANG_DEG_VAL + survey.INCL_ANG_MIN_VAL / 60
    direction = survey.DIR_DEG_VAL + survey.DIR_MINS_VAL / 60
    reference_az = direction.copy()
    for i, row in survey.iterrows():
        reference_az.iloc[i] = {
            "NE": direction.iloc[i],
            "NW": 360 - direction.iloc[i],
            "SE": 180 - direction.iloc[i],
            "SW": 180 + direction.iloc[i],
        }[row.WELL_N_S_CODE + row.WELL_E_W_CODE]
    # process_survey_xyz integrates from its first station, not from the KB.
    source_tvd = survey.SURVEY_POINT_TVD - survey.SURVEY_POINT_TVD.iloc[0]
    comparisons = {
        "measured_depth_ft": (path.md, survey.SURVEY_POINT_MD),
        "inclination_deg": (path.inc, reference_inc),
        "azimuth_deg": (path.az, reference_az),
        "relative_tvd_ft": (path.z_coor, source_tvd),
    }
    return path, comparisons


def _compare_stations(path, survey, comparisons, criteria):
    """Judge unrounded differences before formatting the station record."""
    rows = []
    differences = {k: (a - b).abs() for k, (a, b) in comparisons.items()}
    for i in range(len(path)):
        row = {"station": i + 1, "raw_row": int(survey.raw_row.iloc[i])}
        row["computed_position_ft"] = {
            "north_from_first_station": round(float(path.x_coor.iloc[i]), 1),
            "east_from_first_station": round(float(path.y_coor.iloc[i]), 1),
            "down_from_first_station": round(float(path.z_coor.iloc[i]), 1),
        }
        row["comparison"] = {}
        for name, (computed, reference) in comparisons.items():
            tolerance = criteria["tolerances"][name]
            difference = float(differences[name].iloc[i])
            row["comparison"][name] = {
                "computed": round(float(computed.iloc[i]), 1),
                "published_or_decoded": round(float(reference.iloc[i]), 1),
                "absolute_difference": round(difference, 1),
                "tolerance": tolerance,
                "passes": difference <= tolerance,
            }
        rows.append(row)
    passed = {
        name: bool((delta <= criteria["tolerances"][name]).all())
        for name, delta in differences.items()
    }
    return rows, passed, differences


def build_record(input_dir):
    """Build one limited-purpose public-survey validation record."""
    root, source, criteria, revision, execution = _read_inputs(input_dir)
    survey = _load_survey(root, source)
    path, comparisons = _compute_comparisons(survey, source)
    rows, passed, differences = _compare_stations(path, survey, comparisons, criteria)
    return {
        "revision": revision["revision"],
        "summary": {
            "api12": source["api12"],
            "record_count": len(rows),
            "passes": passed,
            "maximum_absolute_differences": {
                name: round(float(delta.max()), 1)
                for name, delta in differences.items()
            },
            "qualification": "Relative depth comparison; angular decoding consistency only",
        },
        "revision_history": revision["history"],
        "source": source,
        "criteria": criteria,
        "execution": execution,
        "input_digests": {
            name: digest(root / name)
            for name in (
                "stations.csv",
                "source.json",
                "criteria.json",
                "revision.json",
                "execution.json",
            )
        },
        "method_digests": {
            "well_api12.py": digest(Path(__file__).with_name("well_api12.py")),
            "directional_survey_validation.py": digest(__file__),
        },
        "datum": {
            "first_measured_depth_ft": round(float(survey.SURVEY_POINT_MD.iloc[0]), 1),
            "first_published_tvd_ft": round(float(survey.SURVEY_POINT_TVD.iloc[0]), 1),
            "horizontal_origin": "First published station; no geographic transform applied",
        },
        "known_limits": [
            "Depth units follow the repository's feet convention; the opened layout does not state units.",
            "Published DELTA_X and DELTA_Y are longitude and latitude differences, not linear offsets.",
            "Geographic coordinates are retained in stations.csv but are not qualified against computed linear positions.",
            "Inclination and azimuth comparisons test decoding of the same input, not independent measurements.",
            "One public survey does not qualify other wells, absolute wellhead placement or plotting labels.",
        ],
        "stations": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = build_record(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
