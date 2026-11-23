"""Tests for Texas RRC field-development metric construction."""

from __future__ import annotations

import warnings
from time import perf_counter

import pandas as pd

from worldenergydata.texas_rrc.field_development.sources import (
    FieldDevelopmentInputs,
)


def _inputs(
    lifecycle: list[dict[str, object]],
    production: list[dict[str, object]],
    *,
    source_gaps: tuple[str, ...] = (),
    production_quality: dict[str, object] | None = None,
) -> FieldDevelopmentInputs:
    return FieldDevelopmentInputs(
        lifecycle=pd.DataFrame(lifecycle),
        production=pd.DataFrame(production),
        lifecycle_quality={"row_count": len(lifecycle)},
        production_quality=production_quality or {"metric_gaps": []},
        source_gaps=source_gaps,
    )


def test_build_field_development_metrics_joins_sources_and_ranks_fields():
    from worldenergydata.texas_rrc.field_development.metrics import (
        build_field_development_metrics,
    )

    inputs = _inputs(
        lifecycle=[
            {
                "api14": "42001000010000",
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
                "lease_number": "02001",
                "operator_number": "300001",
                "operator_name": "ALPHA ENERGY",
                "well_status": "PRODUCING",
                "well_type": "O",
                "wellbore_profile": "HORIZONTAL",
                "permit_number": "100",
                "permit_issued_date": "2020-01-01",
                "completion_date": "2020-01-11",
            },
            {
                "api14": "42001000020000",
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
                "lease_number": "02002",
                "operator_number": "300002",
                "operator_name": "BETA ENERGY",
                "well_status": "PLUGGED",
                "well_type": "O",
                "wellbore_profile": "DIRECTIONAL",
                "permit_number": "101",
                "permit_issued_date": "2020-01-01",
                "completion_date": "2020-01-21",
            },
        ],
        production=[
            {
                "aggregation_level": "field",
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
                "first_production_month": "2020-02",
                "last_production_month": "2023-01",
                "still_producing": True,
                "production_span_months": 36,
                "cumulative_oil_bbl": 100.0,
                "cumulative_gas_mcf": 600.0,
                "cumulative_condensate_bbl": 10.0,
                "cumulative_boe": 210.0,
                "lease_count": 2,
                "operator_count": 2,
                "top_operator_number": "300001",
                "top_operator_name": "ALPHA ENERGY",
                "top_operator_share": 0.75,
            }
        ],
        production_quality={"metric_gaps": ["water_bbl", "well_count"]},
    )

    metrics = build_field_development_metrics(inputs)
    row = metrics.set_index(["district", "field_number"]).loc[("08", "00010001")]

    assert row["field_name"] == "SPRABERRY"
    assert row["well_count"] == 2
    assert row["active_well_count"] == 1
    assert row["plugged_well_count"] == 1
    assert row["permit_count"] == 2
    assert row["completion_count"] == 2
    assert row["horizontal_well_count"] == 1
    assert row["directional_well_count"] == 1
    assert row["horizontal_directional_share"] == 1.0
    assert row["median_permit_to_completion_days"] == 15.0
    assert row["median_completion_to_first_production_days"] == 16.0
    assert row["production_maturity_class"] == "growth"
    assert row["production_per_well_boe"] == 105.0
    assert row["well_density_proxy"] == 1.0
    assert row["well_density_basis"] == "wells_per_lease"
    assert row["remaining_activity_score"] == 0.75
    assert row["rank_cumulative_boe"] == 1
    assert row["rank_remaining_activity"] == 1
    assert row["rank_well_density_proxy"] == 1
    assert row["top_operator_number"] == "300001"
    assert row["top_operator_share"] == 0.75
    assert row["source_caveats"] == (
        "lease_level_production|no_per_well_allocation|"
        "water_and_well_count_unavailable_from_pdq"
    )
    assert row["quality_flags"] == ""


def test_build_field_development_metrics_preserves_missing_source_fields():
    from worldenergydata.texas_rrc.field_development.metrics import (
        build_field_development_metrics,
    )

    inputs = _inputs(
        lifecycle=[
            {
                "api14": "42003000010000",
                "district": "08",
                "field_number": "00020001",
                "field_name": "LIFECYCLE ONLY",
                "lease_number": "02010",
                "well_status": "SHUT IN",
                "permit_number": "200",
            }
        ],
        production=[
            {
                "aggregation_level": "field",
                "district": "09",
                "field_number": "00030001",
                "field_name": "PRODUCTION ONLY",
                "first_production_month": "1990-01",
                "last_production_month": "2010-01",
                "still_producing": False,
                "production_span_months": 240,
                "cumulative_boe": 500.0,
                "lease_count": 4,
                "operator_count": 1,
            }
        ],
    )

    metrics = build_field_development_metrics(inputs)
    by_field = metrics.set_index(["district", "field_number"])
    lifecycle_only = by_field.loc[("08", "00020001")]
    production_only = by_field.loc[("09", "00030001")]

    assert lifecycle_only["well_count"] == 1
    assert lifecycle_only["active_well_count"] == 1
    assert pd.isna(lifecycle_only["cumulative_boe"])
    assert lifecycle_only["production_maturity_class"] == "pre_production"
    assert "missing_production" in lifecycle_only["source_caveats"]
    assert "missing_lifecycle_dates" in lifecycle_only["source_caveats"]

    assert production_only["well_count"] == 0
    assert production_only["production_maturity_class"] == "late_life"
    assert pd.isna(production_only["production_per_well_boe"])
    assert pd.isna(production_only["well_density_proxy"])
    assert "missing_lifecycle" in production_only["source_caveats"]


def test_build_field_development_metrics_classifies_maturity_and_dates():
    from worldenergydata.texas_rrc.field_development.metrics import (
        build_field_development_metrics,
    )

    inputs = _inputs(
        lifecycle=[
            {
                "api14": "42001000010000",
                "district": "01",
                "field_number": "00000001",
                "field_name": "EARLY",
                "permit_issued_date": "2021-03-01",
                "completion_date": "2021-02-01",
            },
            {
                "api14": "42001000020000",
                "district": "01",
                "field_number": "00000002",
                "field_name": "MATURE",
                "completion_date": "2010-01-01",
            },
            {
                "api14": "42001000030000",
                "district": "01",
                "field_number": "00000003",
                "field_name": "UNKNOWN",
            },
        ],
        production=[
            {
                "aggregation_level": "field",
                "district": "01",
                "field_number": "00000001",
                "field_name": "EARLY",
                "first_production_month": "2021-02",
                "last_production_month": "2022-01",
                "still_producing": True,
                "production_span_months": 12,
                "cumulative_boe": 10.0,
                "lease_count": 1,
            },
            {
                "aggregation_level": "field",
                "district": "01",
                "field_number": "00000002",
                "field_name": "MATURE",
                "first_production_month": "2010-01",
                "last_production_month": "2025-01",
                "still_producing": True,
                "production_span_months": 180,
                "cumulative_boe": 20.0,
                "lease_count": 1,
            },
        ],
    )

    metrics = build_field_development_metrics(inputs).set_index("field_number")

    assert metrics.loc["00000001", "production_maturity_class"] == "early_development"
    assert pd.isna(metrics.loc["00000001", "median_permit_to_completion_days"])
    assert metrics.loc["00000002", "production_maturity_class"] == "mature_active"
    assert metrics.loc["00000003", "production_maturity_class"] == "pre_production"
    assert metrics.loc["00000002", "rank_development_maturity"] == 1


def test_lifecycle_aggregation_scales_beyond_row_wise_group_processing():
    from worldenergydata.texas_rrc.field_development.metrics import (
        _aggregate_lifecycle,
    )

    row_count = 5_000
    lifecycle = pd.DataFrame(
        {
            "district": ["08"] * row_count,
            "field_number": [f"{index % 100:08d}" for index in range(row_count)],
            "field_name": ["SPRABERRY"] * row_count,
            "lease_number": [f"{index % 300:05d}" for index in range(row_count)],
            "operator_number": [f"{index % 25:06d}" for index in range(row_count)],
            "well_status": [
                "PRODUCING" if index % 2 else "PLUGGED" for index in range(row_count)
            ],
            "well_type": ["O"] * row_count,
            "wellbore_profile": [
                "HORIZONTAL" if index % 3 else "DIRECTIONAL"
                for index in range(row_count)
            ],
            "permit_number": [str(index) for index in range(row_count)],
            "permit_issued_date": ["2020-01-01"] * row_count,
            "completion_date": ["2020-01-11"] * row_count,
        }
    )

    started = perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        metrics = _aggregate_lifecycle(lifecycle)
    elapsed = perf_counter() - started

    assert len(metrics) == 100
    assert metrics["well_count"].sum() == row_count
    assert metrics["permit_count"].sum() == row_count
    assert not [warning for warning in caught if warning.category is UserWarning]
    assert elapsed < 4.0
