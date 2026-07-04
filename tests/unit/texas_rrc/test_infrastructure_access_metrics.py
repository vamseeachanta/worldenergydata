"""Tests for Texas RRC field-level infrastructure access metrics."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.infrastructure.gis_sources import (
    PipelineGisRecord,
    WellGisRecord,
)


def _field_development() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
                "well_count": 2,
            },
            {
                "district": "08",
                "field_number": "00020001",
                "field_name": "REMOTE FIELD",
                "well_count": 1,
            },
            {
                "district": "09",
                "field_number": "00030001",
                "field_name": "NO GIS FIELD",
                "well_count": 1,
            },
        ]
    )


def _lifecycle() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "api14": "42001000010000",
                "api10": "4200100001",
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
            },
            {
                "api14": "42001000020000",
                "api10": "4200100002",
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
            },
            {
                "api14": "42003000010000",
                "api10": "4200300001",
                "district": "08",
                "field_number": "00020001",
                "field_name": "REMOTE FIELD",
            },
            {
                "api14": "42005000010000",
                "api10": "4200500001",
                "district": "08",
                "field_number": "00040001",
                "field_name": "GIS ONLY FIELD",
            },
        ]
    )


def _well_gis() -> tuple[WellGisRecord, ...]:
    return (
        WellGisRecord("42001000010000", "001", 31.0, -102.0, "well001.zip"),
        WellGisRecord("42001000020000", "001", 31.02, -102.02, "well001.zip"),
        WellGisRecord("42003000010000", "003", 32.0, -103.0, "well003.zip"),
        WellGisRecord("42005000010000", "005", 30.0, -101.0, "well005.zip"),
    )


def _pipeline_gis() -> tuple[PipelineGisRecord, ...]:
    return (
        PipelineGisRecord(
            "near-001",
            "001",
            ((-102.0, 30.95), (-102.0, 31.1)),
            "pipeline001.zip",
        ),
        PipelineGisRecord(
            "regional-003",
            "003",
            ((-103.12, 31.95), (-103.12, 32.05)),
            "pipeline003.zip",
        ),
    )


def test_build_infrastructure_access_metrics_scores_pipeline_access():
    from worldenergydata.texas_rrc.infrastructure.access_metrics import (
        InfrastructureAccessInputs,
        build_infrastructure_access_metrics,
    )

    metrics = build_infrastructure_access_metrics(
        InfrastructureAccessInputs(
            field_development=_field_development(),
            lifecycle=_lifecycle(),
            well_gis=_well_gis(),
            pipeline_gis=_pipeline_gis(),
            source_gaps=(),
        )
    ).set_index(["district", "field_number"])

    spraberry = metrics.loc[("08", "00010001")]
    assert spraberry["field_well_count_with_location"] == 2
    assert spraberry["nearest_pipeline_identifier"] == "near-001"
    assert spraberry["nearest_pipeline_distance_miles"] <= 1.0
    assert spraberry["nearby_pipeline_count_1mi"] == 1
    assert spraberry["nearby_pipeline_count_5mi"] == 1
    assert spraberry["infrastructure_access_class"] == "direct_access"
    assert spraberry["infrastructure_access_score"] == 1.0
    assert "rrc_gis_screening_only" in spraberry["source_caveats"]

    remote = metrics.loc[("08", "00020001")]
    assert 5.0 < remote["nearest_pipeline_distance_miles"] <= 10.0
    assert remote["infrastructure_access_class"] == "regional_access"
    assert remote["infrastructure_access_score"] == 0.5

    missing = metrics.loc[("09", "00030001")]
    assert missing["field_well_count_with_location"] == 0
    assert pd.isna(missing["nearest_pipeline_distance_miles"])
    assert missing["infrastructure_access_class"] == "isolated_or_unknown"
    assert "missing_well_gis" in missing["source_caveats"]


def test_build_infrastructure_access_metrics_screens_from_field_centroid(monkeypatch):
    import worldenergydata.texas_rrc.infrastructure.access_metrics as access_metrics
    import worldenergydata.texas_rrc.infrastructure.spatial as spatial

    def fake_distance(latitude, longitude, coordinates):
        raise AssertionError("field screening should use pipeline envelope distance")

    monkeypatch.setattr(
        spatial,
        "point_to_polyline_distance_miles",
        fake_distance,
    )

    metrics = access_metrics.build_infrastructure_access_metrics(
        access_metrics.InfrastructureAccessInputs(
            field_development=pd.DataFrame(
                [
                    {
                        "district": "08",
                        "field_number": "00010001",
                        "field_name": "SPRABERRY",
                    }
                ]
            ),
            lifecycle=pd.DataFrame(
                [
                    {
                        "api14": "42001000010000",
                        "district": "08",
                        "field_number": "00010001",
                    },
                    {
                        "api14": "42001000020000",
                        "district": "08",
                        "field_number": "00010001",
                    },
                ]
            ),
            well_gis=(
                WellGisRecord("42001000010000", "001", 31.0, -102.0, "well001.zip"),
                WellGisRecord("42001000020000", "001", 31.1, -102.1, "well001.zip"),
            ),
            pipeline_gis=(
                PipelineGisRecord(
                    "pipe-1", "001", ((-102.0, 31.0), (-102.0, 31.2)), "pipe.zip"
                ),
                PipelineGisRecord(
                    "pipe-2", "001", ((-102.1, 31.0), (-102.1, 31.2)), "pipe.zip"
                ),
                PipelineGisRecord(
                    "pipe-3", "001", ((-102.2, 31.0), (-102.2, 31.2)), "pipe.zip"
                ),
            ),
            source_gaps=(),
        )
    )

    row = metrics.iloc[0]
    assert row["nearby_pipeline_count_1mi"] == 0
    assert row["nearby_pipeline_count_5mi"] == 2
    assert row["nearby_pipeline_count_10mi"] == 3
    assert 2.0 < row["nearest_pipeline_distance_miles"] < 3.5


def test_build_infrastructure_access_metrics_uses_pipeline_envelope_distance(
    monkeypatch,
):
    import worldenergydata.texas_rrc.infrastructure.access_metrics as access_metrics
    import worldenergydata.texas_rrc.infrastructure.spatial as spatial

    def fake_distance(latitude, longitude, coordinates):
        raise AssertionError("field screening should use pipeline envelope distance")

    monkeypatch.setattr(
        spatial,
        "point_to_polyline_distance_miles",
        fake_distance,
    )

    metrics = access_metrics.build_infrastructure_access_metrics(
        access_metrics.InfrastructureAccessInputs(
            field_development=pd.DataFrame(
                [
                    {
                        "district": "08",
                        "field_number": "00010001",
                        "field_name": "SPRABERRY",
                    }
                ]
            ),
            lifecycle=pd.DataFrame(
                [
                    {
                        "api14": "42001000010000",
                        "district": "08",
                        "field_number": "00010001",
                    },
                ]
            ),
            well_gis=(
                WellGisRecord("42001000010000", "001", 31.0, -102.0, "well001.zip"),
            ),
            pipeline_gis=(
                PipelineGisRecord(
                    "near", "001", ((-102.0, 31.0), (-102.0, 31.2)), "pipe.zip"
                ),
                PipelineGisRecord(
                    "far-envelope",
                    "001",
                    ((-101.7, 31.0), (-101.7, 31.2)),
                    "pipe.zip",
                ),
            ),
            source_gaps=(),
        )
    )

    row = metrics.iloc[0]
    assert row["nearest_pipeline_identifier"] == "near"
    assert row["nearest_pipeline_distance_miles"] == 0.0
    assert row["nearby_pipeline_count_10mi"] == 1


def test_build_infrastructure_access_metrics_filters_by_dominant_field_county():
    from worldenergydata.texas_rrc.infrastructure.access_metrics import (
        InfrastructureAccessInputs,
        build_infrastructure_access_metrics,
    )

    metrics = build_infrastructure_access_metrics(
        InfrastructureAccessInputs(
            field_development=pd.DataFrame(
                [
                    {
                        "district": "08",
                        "field_number": "00010001",
                        "field_name": "SPRABERRY",
                    }
                ]
            ),
            lifecycle=pd.DataFrame(
                [
                    {
                        "api14": "42001000010000",
                        "district": "08",
                        "field_number": "00010001",
                    },
                    {
                        "api14": "42001000020000",
                        "district": "08",
                        "field_number": "00010001",
                    },
                    {
                        "api14": "42003000010000",
                        "district": "08",
                        "field_number": "00010001",
                    },
                ]
            ),
            well_gis=(
                WellGisRecord("42001000010000", "001", 31.0, -102.0, "well001.zip"),
                WellGisRecord("42001000020000", "001", 31.0, -102.1, "well001.zip"),
                WellGisRecord("42003000010000", "003", 31.0, -102.2, "well003.zip"),
            ),
            pipeline_gis=(
                PipelineGisRecord(
                    "dominant-county",
                    "001",
                    ((-102.0, 30.9), (-102.0, 31.1)),
                    "pipe001.zip",
                ),
                PipelineGisRecord(
                    "other-county",
                    "003",
                    ((-102.1, 30.9), (-102.1, 31.1)),
                    "pipe003.zip",
                ),
            ),
            source_gaps=(),
        )
    )

    row = metrics.iloc[0]
    assert row["nearest_pipeline_identifier"] == "dominant-county"
    assert "dominant_county_pipeline_filter" in row["source_caveats"]


def test_build_infrastructure_access_metrics_preserves_gis_only_fields():
    from worldenergydata.texas_rrc.infrastructure.access_metrics import (
        InfrastructureAccessInputs,
        build_infrastructure_access_metrics,
    )

    metrics = build_infrastructure_access_metrics(
        InfrastructureAccessInputs(
            field_development=_field_development(),
            lifecycle=_lifecycle(),
            well_gis=_well_gis(),
            pipeline_gis=_pipeline_gis(),
            source_gaps=("pipeline_gis_layers",),
        )
    )

    gis_only = metrics.set_index(["district", "field_number"]).loc[("08", "00040001")]

    assert gis_only["field_name"] == "GIS ONLY FIELD"
    assert gis_only["field_well_count_with_location"] == 1
    assert gis_only["infrastructure_access_class"] == "isolated_or_unknown"
    assert "missing_field_development_metrics" in gis_only["source_caveats"]
    assert "missing_pipeline_gis" in gis_only["source_caveats"]
    assert tuple(
        metrics[["district", "field_number"]].itertuples(index=False, name=None)
    ) == (
        ("08", "00010001"),
        ("08", "00020001"),
        ("08", "00040001"),
        ("09", "00030001"),
    )
