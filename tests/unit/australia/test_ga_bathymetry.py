"""Offline synthetic points; expected depths are independent sign calculations.

GA/DEA AusBathyTopo 2023 specifications, height_depth band and product information:
https://knowledge.dea.ga.gov.au/data/external-data/ga-ausbathytopo-250m/
The published band has metres relative to MSL, NoData -32767, EPSG:4326.
Test positions and elevations are synthetic, not observed well measurements.
"""

import copy

import pytest

from worldenergydata.australia.field_concept import build_australia_field_concept
from worldenergydata.australia.metadata import ga_bathymetry as ga
from worldenergydata.australia.metadata.well_enrichment import enrich_field_metadata


@pytest.fixture
def point():
    return {
        "product": "ga_ausbathytopo250m_2023",
        "height_depth": -125.5,
        "unit": "m",
        "vertical_datum": "MSL",
        "latitude": -20.0,
        "longitude": 130.0,
        "spatial_reference": {"wkid": 4326},
        "source_sha256": "a" * 64,
        "retrieved_at_utc": "2026-10-19T00:00:00Z",
        "marine_qualification": {
            "classification": "marine",
            "source": "synthetic point classification",
        },
    }


@pytest.fixture
def well(point):
    return {
        "well_identifier": "synthetic-well",
        "field_name": "Synthetic Field",
        "latitude": point["latitude"],
        "longitude": point["longitude"],
        "spatial_reference": copy.deepcopy(point["spatial_reference"]),
        "water_depth": None,
    }


def test_normalize_depth_and_provenance_without_mutation(point):
    """Depth = MSL - elevation = 0 - (-125.5) = 125.5 m by hand."""
    before = copy.deepcopy(point)
    result = ga.normalize_bathymetry_point(point)
    assert result["status"] == "EVALUATED"
    assert result["water_depth"] == 125.5
    assert result["water_depth_unit"] == "m"
    assert result["water_depth_datum"] == "MSL"
    assert result["water_depth_origin"] == "bathymetry"
    assert result["provenance"]["source_sha256"] == point["source_sha256"]
    assert result["provenance"]["product"] == point["product"]
    assert result["provenance"]["source_url"] == ga.SPECIFICATION_URL
    assert result["provenance"]["marine_qualification"] == point["marine_qualification"]
    result["provenance"]["marine_qualification"]["source"] = "changed copy"
    assert point == before


@pytest.mark.parametrize("elevation", [None, -32767, 0, 10])
def test_nonmarine_or_missing_depth_is_not_evaluated(point, elevation):
    """NoData is published; 0/10 m are synthetic shoreline/land elevations."""
    point["height_depth"] = elevation
    result = ga.normalize_bathymetry_point(point)
    assert result["status"] == "NOT_EVALUATED"
    assert result["water_depth"] is None
    assert result["reason"]


@pytest.mark.parametrize(
    "qualification",
    [
        None,
        True,
        "marine",
        [],
        {},
        {"classification": "land", "source": "synthetic point classification"},
        {"classification": "unknown", "source": "synthetic point classification"},
        {"classification": True, "source": "synthetic point classification"},
        {"classification": "marine"},
        {"classification": "marine", "source": None},
        {"classification": "marine", "source": ""},
        {"classification": "marine", "source": " \t"},
        {"classification": "marine", "source": 1},
    ],
)
def test_below_msl_requires_sourced_marine_qualification(point, qualification):
    """A synthetic -15 m elevation alone does not establish marine water depth."""
    point.update(height_depth=-15.0, marine_qualification=qualification)
    result = ga.normalize_bathymetry_point(point)
    assert result["status"] == "NOT_EVALUATED"
    assert result["water_depth"] is None
    assert result["reason"]
    assert result["provenance"]["marine_qualification"] == qualification


@pytest.mark.parametrize("classification", ["land", "unknown", None])
def test_below_msl_unqualified_point_preserves_field_fallback(
    point, well, classification
):
    """Synthetic dry land below MSL and unknown points cannot supply a depth."""
    point["height_depth"] = -15.0
    if classification is None:
        del point["marine_qualification"]
    else:
        point["marine_qualification"]["classification"] = classification
    normalized = ga.normalize_bathymetry_point(point)
    assert normalized["status"] == "NOT_EVALUATED"
    assert normalized["water_depth"] is None
    assert normalized["reason"]
    before = copy.deepcopy(well)
    result = ga.enrich_well_from_bathymetry(well, point)
    assert result == before
    assert well == before
    meta = {
        "field_name": "Synthetic Field",
        "well_identifier": "synthetic-well",
        "water_depth_m": 50,
    }
    enriched = enrich_field_metadata(meta, [result])
    assert enriched["water_depth_m"] == 50
    assert enriched["value_origins"]["water_depth_m"] == "default"
    assert "bathymetry_provenance" not in enriched
    concept = build_australia_field_concept(meta, wells=[result])
    assert concept.water_depth_m == 50
    assert "water_depth_m=bathymetry" not in concept.data_source


@pytest.mark.parametrize(
    "change",
    [
        {"product": "unknown"},
        {"unit": "ft"},
        {"vertical_datum": "unknown"},
        {"spatial_reference": {"wkid": 4283}},
        {"spatial_reference": None},
        {"height_depth": True},
        {"height_depth": "-125.5"},
        {"height_depth": float("nan")},
        {"height_depth": float("inf")},
        {"latitude": True},
        {"latitude": -91},
        {"longitude": 181},
        {"longitude": float("nan")},
        {"source_sha256": "unverified"},
        {"retrieved_at_utc": "2026-10-19"},
        {"retrieved_at_utc": "invalid"},
    ],
)
def test_unqualified_evidence_is_rejected(point, change):
    point.update(change)
    with pytest.raises(ValueError):
        ga.normalize_bathymetry_point(point)


@pytest.mark.parametrize("key", ["product", "height_depth", "source_sha256"])
def test_missing_required_evidence_rejected(point, key):
    del point[key]
    with pytest.raises(ValueError):
        ga.normalize_bathymetry_point(point)


def test_join_and_field_concept_keep_estimated_origin(point, well):
    """Hand calculation: 0 - (-125.5) = 125.5 m; no unit conversion."""
    before = copy.deepcopy(well)
    result = ga.enrich_well_from_bathymetry(well, point)
    assert well == before
    assert result["water_depth"] == 125.5
    assert result["bathymetry_provenance"]["source_sha256"] == point["source_sha256"]
    meta = {
        "field_name": "Synthetic Field",
        "well_identifier": "synthetic-well",
        "water_depth_m": 50,
    }
    enriched = enrich_field_metadata(meta, [result])
    assert enriched["water_depth_m"] == 125.5
    assert enriched["value_origins"]["water_depth_m"] == "bathymetry"
    assert enriched["bathymetry_provenance"] == result["bathymetry_provenance"]
    repeated = enrich_field_metadata(enriched, [])
    assert repeated["value_origins"]["water_depth_m"] == "bathymetry"
    concept = build_australia_field_concept(meta, wells=[result])
    assert concept.water_depth_m == 125.5
    assert "water_depth_m=bathymetry" in concept.data_source


@pytest.mark.parametrize(
    "change",
    [
        {"latitude": -21},
        {"longitude": 131},
        {"latitude": None},
        {"spatial_reference": {"wkid": 4283}},
        {"spatial_reference": None},
    ],
)
def test_join_does_not_guess_coordinate_transformation(point, well, change):
    well.update(change)
    with pytest.raises(ValueError, match="position"):
        ga.enrich_well_from_bathymetry(well, point)


def test_measured_well_depth_has_priority(point, well):
    """Synthetic measured 80 m is retained unchanged over a grid estimate."""
    well.update(water_depth=80, water_depth_unit="m", water_depth_datum="MSL")
    assert ga.enrich_well_from_bathymetry(well, point) == well


def test_nodata_preserves_existing_well(point, well):
    point["height_depth"] = -32767  # GA/DEA 2023 height_depth band NoData.
    assert ga.enrich_well_from_bathymetry(well, point) == well


def test_grid_does_not_replace_measured_field_depth(point, well):
    """A synthetic measured field depth of 80 m outranks a grid estimate."""
    grid_well = ga.enrich_well_from_bathymetry(well, point)
    meta = {
        "field_name": "Synthetic Field",
        "well_identifier": "synthetic-well",
        "water_depth_m": 80,
        "water_depth_datum": "MSL",
        "value_origins": {"water_depth_m": "measured"},
    }
    result = enrich_field_metadata(meta, [grid_well])
    assert result["water_depth_m"] == 80
    assert result["value_origins"]["water_depth_m"] == "measured"
    assert "bathymetry_provenance" not in result


def test_grid_source_reaches_concept_and_wgs84_coordinates(point, well):
    grid_well = ga.enrich_well_from_bathymetry(well, point)
    meta = {"field_name": "Synthetic Field", "well_identifier": "synthetic-well"}
    result = enrich_field_metadata(meta, [grid_well])
    assert result["latitude"] == point["latitude"]
    assert result["spatial_reference"] == {"wkid": 4326}
    concept = build_australia_field_concept(meta, wells=[grid_well])
    assert point["product"] in concept.data_source
    assert point["source_sha256"] in concept.data_source
