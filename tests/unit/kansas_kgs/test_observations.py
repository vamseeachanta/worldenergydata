"""Tests for Kansas KGS curated pressure observations."""

from __future__ import annotations

import csv
import zipfile
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest


def test_build_observations_converts_units_and_flags_earliest() -> None:
    from worldenergydata.kansas_kgs.observations import build_pressure_observations

    result = build_pressure_observations(_pressure_rows(), _well_rows())
    observations = result.observations.sort_values("test_year").reset_index(drop=True)

    assert observations.shape[0] == 2
    first = observations.iloc[0]
    assert first["pressure_psig_raw"] == 47.3
    assert first["pressure_psia"] == 62.0
    assert first["atmospheric_pressure_psi"] == 14.7
    assert first["pressure_kind"] == "WHP_shut_in"
    assert first["gradient_psi_ft"] == round(62.0 / 4470.0, 6)
    assert first["is_earliest_observation_for_well"] is True
    assert observations.iloc[1]["is_earliest_observation_for_well"] is False
    assert first["virgin_pressure_proxy_method"] == "earliest_available_proration_year"
    assert "not_initial_reservoir_pressure" in first["limitations"]
    assert "elevation_not_adjusted" in first["limitations"]


def test_build_observations_suppresses_ambiguous_api10_gradient() -> None:
    from worldenergydata.kansas_kgs.observations import build_pressure_observations

    wells = pd.concat([_well_rows(), _well_rows().assign(api14="15067200480001")])
    result = build_pressure_observations(_pressure_rows(), wells)
    row = result.observations.loc[result.observations["api10"].eq("1506720048")].iloc[0]

    assert pd.isna(row["api14"])
    assert pd.isna(row["reference_depth_ft"])
    assert pd.isna(row["gradient_psi_ft"])
    assert row["is_earliest_observation_for_well"] is None
    assert len(result.observations) == 2
    assert (
        result.observations[["api14", "reference_depth_ft", "gradient_psi_ft"]]
        .isna()
        .all()
        .all()
    )
    assert all(
        value is None
        for value in result.observations["is_earliest_observation_for_well"]
    )
    assert result.observations["virgin_pressure_proxy_method"].isna().all()
    assert "ambiguous_api10_join" in row["quality_flags"]
    assert "ambiguous_identity_for_virgin_proxy" in row["quality_flags"]


def test_kid_fallback_disambiguates_api10_join() -> None:
    from worldenergydata.kansas_kgs.observations import build_pressure_observations

    wells = pd.DataFrame(
        [
            _well(api14="15067200480000", well_kid="1001232609", depth=4470),
            _well(api14="15067200480001", well_kid="different", depth=4800),
        ]
    )
    result = build_pressure_observations(_pressure_rows(), wells)
    row = result.observations.loc[result.observations["test_year"].eq(1997)].iloc[0]

    assert row["api14"] == "15067200480000"
    assert row["reference_depth_ft"] == 4470.0
    assert "kid_fallback_join" in row["quality_flags"]


def test_coverage_reports_hugoton_county_dominance() -> None:
    from worldenergydata.kansas_kgs.observations import build_pressure_observations

    result = build_pressure_observations(
        _pressure_rows(include_stevens=True), _well_rows()
    )

    assert set(result.coverage["county_name"]) >= {"Grant", "Stevens"}
    assert result.quality["hugoton_panoma_county_observation_count"] == 3
    assert result.quality["observation_year_min"] == 1997
    assert result.quality["observation_year_max"] == 1998


def test_unknown_county_falls_back_to_matched_well_county() -> None:
    from worldenergydata.kansas_kgs.observations import build_pressure_observations

    pressure_rows = _pressure_rows()
    pressure_rows.loc[0, "county_name"] = pd.NA

    result = build_pressure_observations(pressure_rows, _well_rows())
    row = result.observations.loc[result.observations["source_row_id"].eq(1)].iloc[0]

    assert row["county_name"] == "Grant"


def test_no_positive_pressures_returns_empty_observations_and_quality() -> None:
    from worldenergydata.kansas_kgs.observations import (
        OBSERVATION_COLUMNS,
        build_pressure_observations,
    )

    pressure_rows = _pressure_rows()
    pressure_rows["pressure_psig_raw"] = 0.0

    result = build_pressure_observations(pressure_rows, _well_rows())

    assert result.observations.empty
    assert list(result.observations.columns) == OBSERVATION_COLUMNS
    assert result.quality == {
        "row_count": 0,
        "observation_year_min": None,
        "observation_year_max": None,
        "hugoton_panoma_county_observation_count": 0,
        "missing_well_join_count": 0,
        "ambiguous_api10_join_count": 0,
        "ambiguous_identity_for_virgin_proxy_count": 0,
        "missing_depth_count": 0,
        "missing_county_name_count": 0,
        "missing_test_year_count": 0,
    }


def test_missing_year_positive_pressure_is_flagged_not_fatal() -> None:
    from worldenergydata.kansas_kgs.observations import build_pressure_observations

    pressure_rows = _pressure_rows()
    pressure_rows.loc[0, "test_year"] = pd.NA

    result = build_pressure_observations(pressure_rows, _well_rows())
    row = result.observations.loc[result.observations["source_row_id"].eq(1)].iloc[0]

    assert pd.isna(row["test_year"])
    assert "missing_test_year" in row["quality_flags"]
    assert row["is_earliest_observation_for_well"] is not True
    assert result.quality["missing_test_year_count"] == 1


def test_observation_quality_counts_join_and_depth_flags() -> None:
    """Hand count for issue #1352, defect 1 (2026):

    The two pressure years for the zero-depth well each lack usable depth.
    The third pressure row has two API candidates and no matching KID, so
    neither candidate supplies depth. Missing-depth count = 2 + 1 = 3;
    ambiguous-API and ambiguous-identity counts each equal 1.
    """
    from worldenergydata.kansas_kgs.observations import build_pressure_observations

    wells = pd.DataFrame(
        [
            _well(
                api10="1506720048",
                api14="15067200480000",
                well_kid="1001232609",
                depth=0,
            ),
            _well(
                api10="1518920001",
                api14="15189200010000",
                well_kid="different",
                depth=3900,
                county_name="Stevens",
            ),
            _well(
                api10="1518920001",
                api14="15189200010001",
                well_kid="other",
                depth=3900,
                county_name="Stevens",
            ),
        ]
    )

    result = build_pressure_observations(_pressure_rows(include_stevens=True), wells)

    assert result.quality["missing_depth_count"] == 3
    assert result.quality["ambiguous_api10_join_count"] == 1
    assert result.quality["ambiguous_identity_for_virgin_proxy_count"] == 1
    # Hand enumeration above: every one of the three rows lacks a gradient.
    assert result.observations["gradient_psi_ft"].isna().sum() == 3
    assert result.observations["reference_depth_ft"].isna().sum() == 3


@pytest.mark.parametrize("join_case", ["missing", "ambiguous"])
def test_unresolved_join_counts_each_missing_depth_once(join_case: str) -> None:
    """Independent count for issue #1352, defect 1 (2026).

    Both rows in _pressure_rows share an API and KID. An empty well table
    gives no candidates; a duplicated well table gives two matching KIDs
    and cannot select either well. In either case, both pressure rows lack
    depth and gradient: missing-depth count = 1 + 1 = 2. Each row must carry
    exactly one missing-depth flag, alongside the appropriate join flags.
    """
    from worldenergydata.kansas_kgs.observations import build_pressure_observations

    wells = pd.DataFrame()
    expected_flags = {"missing_well_join", "missing_depth"}
    if join_case == "ambiguous":
        wells = pd.concat([_well_rows(), _well_rows()])
        expected_flags = {
            "ambiguous_api10_join",
            "ambiguous_identity_for_virgin_proxy",
            "missing_depth",
        }

    result = build_pressure_observations(_pressure_rows(), wells)

    # Expected counts follow the hand enumeration above, not the builder.
    assert len(result.observations) == 2
    assert result.quality["missing_depth_count"] == 2
    assert result.observations["reference_depth_ft"].isna().all()
    assert result.observations["gradient_psi_ft"].isna().all()
    for flags in result.observations["quality_flags"]:
        flag_list = flags.split("|")
        assert set(flag_list) == expected_flags
        assert flag_list.count("missing_depth") == 1


@pytest.mark.parametrize("blank", ["", "   ", pd.NA])
def test_blank_identity_rows_remain_independent(tmp_path, blank) -> None:
    """Issue #1352 (2026), blank-identity hand count.

    Two positive rows, one in each of two years, have neither API nor KID.
    No evidence links them: each source row is its own identity, so both
    are earliest, both carry a proxy, and both lack a well join and depth.
    The same expectations apply to CSV parsing and normalized callers.
    """
    from worldenergydata.kansas_kgs.observations import build_pressure_observations
    from worldenergydata.kansas_kgs.pressure import parse_proration_pressure

    path = tmp_path / "anonymous.csv"
    path.write_text(
        "WELL_KID,API_NUMBER,YEAR,SHUT_IN_PRESS\n" " , ,1997,10\n,,1998,20\n",
        encoding="utf-8",
        newline="\n",
    )
    parsed = parse_proration_pressure(path).normalized
    assert (
        parsed[["well_kid", "api10", "api_state_code", "api_county_code"]]
        .isna()
        .all()
        .all()
    )
    for rows in (parsed, _pressure_rows().assign(well_kid=blank, api10=blank)):
        result = build_pressure_observations(rows, pd.DataFrame())
        assert len(result.observations) == 2
        assert all(
            value is True
            for value in result.observations["is_earliest_observation_for_well"]
        )
        assert (
            result.observations["virgin_pressure_proxy_method"]
            .eq("earliest_available_proration_year")
            .all()
        )
        assert result.quality["missing_well_join_count"] == 2
        assert result.quality["missing_depth_count"] == 2


@pytest.mark.parametrize("blank", ["", "   ", pd.NA])
def test_missing_kid_cannot_disambiguate_candidates(blank) -> None:
    """Hand count: two API candidates and no source KID select zero wells.

    One candidate also lacks KID. Missing values supply no identity evidence;
    both pressure rows remain ambiguous, with missing depth and earliest flag.
    """
    from worldenergydata.kansas_kgs.observations import build_pressure_observations

    rows = _pressure_rows().assign(well_kid=blank)
    wells = pd.DataFrame(
        [
            _well(api14="15067200480000", well_kid=blank, depth=1000),
            _well(api14="15067200480001", well_kid="populated", depth=2000),
        ]
    )
    result = build_pressure_observations(rows, wells)
    assert result.quality["ambiguous_api10_join_count"] == 2
    assert result.quality["missing_depth_count"] == 2
    assert result.observations["api14"].isna().all()
    assert all(
        value is None
        for value in result.observations["is_earliest_observation_for_well"]
    )


@pytest.mark.parametrize(
    ("well_kid", "pressure_kids", "earliest"),
    [
        ("matched", ("", ""), [True, False]),
        ("matched", ("   ", pd.NA), [True, False]),
        ("matched", ("source-a", "source-b"), [True, False]),
        ("", ("source", "source"), [True, False]),
        ("", ("source-a", "source-b"), [True, True]),
        ("", ("", ""), [True, True]),
    ],
)
def test_matched_well_kid_groups_observations_without_api14(
    tmp_path: Path, well_kid: str, pressure_kids: tuple, earliest: list[bool]
) -> None:
    """Hand count for #1352: two years joined to one identified well.

    A twelve-digit API14 is suppressed by parsing. A populated matched-well
    KID still identifies one well, so exactly one of its two rows is earliest.
    Without that KID, equal pressure KIDs group the rows; distinct pressure
    KIDs or independent unidentified source rows each receive two flags.
    """
    from worldenergydata.kansas_kgs.observations import build_pressure_observations
    from worldenergydata.kansas_kgs.wells import REQUIRED_COLUMNS, parse_wells_master

    contents = StringIO()
    writer = csv.DictWriter(contents, fieldnames=sorted(REQUIRED_COLUMNS))
    writer.writeheader()
    writer.writerow(
        {
            "KID": well_kid,
            "API_NUMBER": "15-067-20048",
            "API_NUM_NODASH": "150672004800",
            "DEPTH": "1000",
        }
    )
    path = tmp_path / "wells.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ks_wells.txt", contents.getvalue())
    wells = parse_wells_master(path)
    rows = _pressure_rows().assign(well_kid=list(pressure_kids))

    result = build_pressure_observations(rows, wells)
    observations = result.observations.sort_values("test_year")

    assert len(observations) == 2
    assert observations["api14"].isna().all()
    assert observations["quality_flags"].eq("invalid_api14").all()
    assert result.quality["missing_well_join_count"] == 0
    assert result.quality["missing_depth_count"] == 0
    assert observations["is_earliest_observation_for_well"].tolist() == earliest
    assert observations["virgin_pressure_proxy_method"].notna().tolist() == earliest


def _pressure_rows(include_stevens: bool = False) -> pd.DataFrame:
    rows = [
        {
            "well_kid": "1001232609",
            "api10": "1506720048",
            "api_state_code": "15",
            "api_county_code": "067",
            "county_name": "Grant",
            "field_name": "HUGOTON GAS AREA",
            "test_year": 1997,
            "test_date": None,
            "test_type": "KS_PRORATION",
            "pressure_psig_raw": 47.3,
            "source_file": "kansas_proration_pressures.txt",
            "source_row_id": 1,
        },
        {
            "well_kid": "1001232609",
            "api10": "1506720048",
            "api_state_code": "15",
            "api_county_code": "067",
            "county_name": "Grant",
            "field_name": "HUGOTON GAS AREA",
            "test_year": 1998,
            "test_date": None,
            "test_type": "KS_PRORATION",
            "pressure_psig_raw": 80.0,
            "source_file": "kansas_proration_pressures.txt",
            "source_row_id": 2,
        },
    ]
    if include_stevens:
        rows.append(
            {
                "well_kid": "2000000000",
                "api10": "1518920001",
                "api_state_code": "15",
                "api_county_code": "189",
                "county_name": "Stevens",
                "field_name": "HUGOTON GAS AREA",
                "test_year": 1998,
                "test_date": None,
                "test_type": "KS_PRORATION",
                "pressure_psig_raw": 90.0,
                "source_file": "kansas_proration_pressures.txt",
                "source_row_id": 3,
            }
        )
    return pd.DataFrame(rows)


def _well_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _well(api14="15067200480000", well_kid="1001232609", depth=4470),
            _well(
                api10="1518920001",
                api14="15189200010000",
                well_kid="2000000000",
                depth=3900,
                county_name="Stevens",
            ),
        ]
    )


def _well(
    api14: str,
    well_kid: str,
    depth: float,
    api10: str = "1506720048",
    county_name: str = "Grant",
) -> dict[str, object]:
    return {
        "well_kid": well_kid,
        "api10": api10,
        "api14": api14,
        "field_name": "HUGOTON GAS AREA",
        "reference_depth_ft": depth,
        "formation": "CHASE GROUP",
        "latitude": 37.4789,
        "longitude": -101.4114,
        "county_name": county_name,
    }
