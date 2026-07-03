"""Tests for Kansas KGS curated pressure observations."""

from __future__ import annotations

import pandas as pd


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
    assert row["is_earliest_observation_for_well"] is not True
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

    assert result.quality["missing_depth_count"] == 2
    assert result.quality["ambiguous_api10_join_count"] == 1
    assert result.quality["ambiguous_identity_for_virgin_proxy_count"] == 1


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
