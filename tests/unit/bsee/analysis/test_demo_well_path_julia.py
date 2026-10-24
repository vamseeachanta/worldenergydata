"""Lease-selection regressions, independent of off-repository BSEE downloads.

Identifier evidence: reports/lower_tertiary/data/julia_wells.json, wells list,
and issue #493 (2026). Fixtures deliberately combine those identifiers with
synthetic names/coordinates; they are join examples, not measured geometry.
"""

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location(
    "demo_well_path_julia", REPO / "scripts/bsee/demo_well_path_julia.py"
)
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)

# Source: committed julia_wells.json, wells[well_name=DC101] and
# wells[well_name=JU102, producing=true]. No numerical calculation is involved.
DC_API = "608124009400"
JU_API = "608124003301"


@pytest.fixture
def records():
    """Hand join: lease rows {DC_API, JU_API}; the other lease contributes none.

    Repeated activity reports collapse to the same API/name pair. Coordinates
    are the arbitrary origin (zero latitude/longitude), not field positions.
    """
    war = pd.DataFrame(
        [
            (DC_API, ' "g20351" ', " DC101 "),
            (DC_API, "G20351", "DC101"),
            (JU_API, "G20351", "JU102"),
            ("unrelated", "OTHER", "JU999"),
        ],
        columns=["API_WELL_NUMBER", "SURF_LEASE_NUM", "WELL_NAME"],
    )
    boreholes = pd.DataFrame(
        {
            "API_WELL_NUMBER": [float(DC_API), JU_API, "unrelated"],
            "WELL_NAME": ["DC101", "JU102", "JU999"],
            "WELL_NAME_SUFFIX": ["ST00BP00", "ST01BP00", ""],
            "SURF_LATITUDE": ["0", "0", "0"],
            "SURF_LONGITUDE": ["0", "0", "0"],
        }
    )
    return war, boreholes


def test_selects_lease_including_non_prefix_name(records):
    """Hand result: G20351 yields DC101 and JU102; OTHER/JU999 is excluded."""
    war, boreholes = records
    original_war, original_boreholes = war.copy(), boreholes.copy()
    result = demo.julia_well_metadata(war, boreholes).set_index("API_WELL_NUMBER")
    assert result["WELL_NAME"].to_dict() == {DC_API: "DC101", JU_API: "JU102"}
    assert result.loc[JU_API, "WELL_NAME_SUFFIX"] == "ST01BP00"
    pd.testing.assert_frame_equal(war, original_war)
    pd.testing.assert_frame_equal(boreholes, original_boreholes)


def test_includes_every_report_bore_without_catalog_membership():
    """Hand set: every bore in the committed lease summary has the same lease.

    All reported bores, including non-producers and sidetracks, must survive;
    selection is not restricted to producers or APIs in the curated catalog.
    """
    report = json.loads(
        (REPO / "reports/lower_tertiary/data/julia_wells.json").read_text()
    )
    expected = {well["api"]: well["well_name"] for well in report["wells"]}
    war = pd.DataFrame(
        {
            "API_WELL_NUMBER": list(expected),
            "WELL_NAME": list(expected.values()),
            "SURF_LEASE_NUM": report["summary"]["lease"],
        }
    )
    boreholes = war.assign(SURF_LATITUDE="0", SURF_LONGITUDE="0")
    result = demo.julia_well_metadata(war, boreholes)
    assert dict(zip(result["API_WELL_NUMBER"], result["WELL_NAME"])) == expected


def test_sources_are_raw_tables_not_curated_catalog(records, monkeypatch):
    """Only the required WAR and borehole tables are read, before surveys."""
    war, boreholes = records
    sources = {"war.txt": war, "boreholes.txt": boreholes}
    reads = []

    def read_csv(path, *, dtype):
        assert dtype is str
        reads.append(path)
        return sources[path]

    def surveys_boundary():
        raise RuntimeError("validated metadata before surveys")

    monkeypatch.setattr(pd, "read_csv", read_csv)
    monkeypatch.setattr(demo, "load_surveys", surveys_boundary)
    with pytest.raises(RuntimeError, match="validated metadata before surveys"):
        demo.main(["--war-main-csv", "war.txt", "--boreholes-csv", "boreholes.txt"])
    assert reads == ["war.txt", "boreholes.txt"]


def test_missing_source_has_no_catalog_fallback(monkeypatch):
    def missing(path, **kwargs):
        raise FileNotFoundError("raw input absent")

    monkeypatch.setattr(pd, "read_csv", missing)
    with pytest.raises(FileNotFoundError, match="raw input absent"):
        demo.main(["--war-main-csv", "war.txt", "--boreholes-csv", "boreholes.txt"])


def test_raw_csv_round_trip(records, tmp_path, monkeypatch):
    """Hand set after real CSV decoding remains {DC_API, JU_API}, with WAR names.

    Pandas writes and reads the quoted text and floating API spellings used by
    the fixture. Expected membership is the explicit lease intersection, not
    a result calculated by the selector.
    """
    war, boreholes = records
    war_path, bore_path = tmp_path / "war.txt", tmp_path / "boreholes.txt"
    war.to_csv(war_path, index=False)
    boreholes.to_csv(bore_path, index=False)
    select = demo.julia_well_metadata
    captured = {}

    def capture(war_frame, bore_frame):
        result = select(war_frame, bore_frame)
        captured.update(zip(result["API_WELL_NUMBER"], result["WELL_NAME"]))
        return result

    def surveys_boundary():
        raise RuntimeError("survey boundary")

    monkeypatch.setattr(demo, "julia_well_metadata", capture)
    monkeypatch.setattr(demo, "load_surveys", surveys_boundary)
    with pytest.raises(RuntimeError, match="survey boundary"):
        demo.main(["--war-main-csv", str(war_path), "--boreholes-csv", str(bore_path)])
    assert captured == {DC_API: "DC101", JU_API: "JU102"}


def test_empty_lease_fails(records):
    war, boreholes = records
    war["SURF_LEASE_NUM"] = "OTHER"
    with pytest.raises(ValueError, match="No WAR wells"):
        demo.julia_well_metadata(war, boreholes)


@pytest.mark.parametrize("lease", ["G20351", ' "g20351" ', "G 20351"])
def test_lease_normalization_matches_economics(records, lease):
    """All spellings denote the same lease, using ops_timeline._norm_lease rules."""
    war, boreholes = records
    war.loc[war["SURF_LEASE_NUM"] != "OTHER", "SURF_LEASE_NUM"] = lease
    result = demo.julia_well_metadata(war, boreholes)
    assert set(result["API_WELL_NUMBER"]) == {DC_API, JU_API}


@pytest.mark.parametrize("table", ["war", "boreholes"])
def test_missing_required_columns_fail(records, table):
    war, boreholes = records
    if table == "war":
        war = war.drop(columns="SURF_LEASE_NUM")
    else:
        boreholes = boreholes.drop(columns="SURF_LONGITUDE")
    with pytest.raises(ValueError, match="Missing.*columns"):
        demo.julia_well_metadata(war, boreholes)


@pytest.mark.parametrize("bad_api", [None, "", "not-an-api", "60812400940001"])
def test_invalid_selected_api_fails(records, bad_api):
    """Full bore API keys are required; longer keys must not be truncated."""
    war, boreholes = records
    war.loc[war["WELL_NAME"].str.strip() == "DC101", "API_WELL_NUMBER"] = bad_api
    with pytest.raises(ValueError, match="Invalid WAR API"):
        demo.julia_well_metadata(war, boreholes)


def test_missing_borehole_fails_instead_of_dropping_well(records):
    war, boreholes = records
    boreholes = boreholes[boreholes["WELL_NAME"] != "JU102"]
    with pytest.raises(ValueError, match=f"Missing borehole metadata.*{JU_API}"):
        demo.julia_well_metadata(war, boreholes)


def test_identity_collision_fails(records):
    """Issue #493 collision: WAR DC101 must not acquire catalog-like JU101 data."""
    war, boreholes = records
    boreholes.loc[boreholes["WELL_NAME"] == "DC101", "WELL_NAME"] = "JU101"
    with pytest.raises(ValueError, match=f"Conflicting well names.*{DC_API}"):
        demo.julia_well_metadata(war, boreholes)


def test_conflicting_war_names_fail(records):
    war, boreholes = records
    war = pd.concat([war, war.iloc[[0]].assign(WELL_NAME="JU101")], ignore_index=True)
    with pytest.raises(ValueError, match="Conflicting WAR names"):
        demo.julia_well_metadata(war, boreholes)


def test_conflicting_borehole_rows_fail(records):
    war, boreholes = records
    boreholes = pd.concat(
        [boreholes, boreholes.iloc[[0]].assign(SURF_LATITUDE="unknown")],
        ignore_index=True,
    )
    with pytest.raises(ValueError, match="Conflicting borehole metadata"):
        demo.julia_well_metadata(war, boreholes)


def test_identical_borehole_rows_are_deduplicated(records):
    war, boreholes = records
    boreholes = pd.concat([boreholes, boreholes], ignore_index=True)
    result = demo.julia_well_metadata(war, boreholes)
    assert set(result["API_WELL_NUMBER"]) == {DC_API, JU_API}
    assert result["API_WELL_NUMBER"].is_unique


@pytest.mark.parametrize("bad_name", [None, "", ' " " '])
def test_missing_war_name_fails(records, bad_name):
    war, boreholes = records
    war["WELL_NAME"] = bad_name
    with pytest.raises(ValueError, match="Missing WAR well name"):
        demo.julia_well_metadata(war, boreholes)


@pytest.mark.parametrize("column", ["SURF_LATITUDE", "SURF_LONGITUDE"])
@pytest.mark.parametrize("bad_coordinate", [None, "unknown", "inf", "-inf"])
def test_missing_or_nonfinite_surface_position_fails(records, column, bad_coordinate):
    war, boreholes = records
    boreholes[column] = bad_coordinate
    with pytest.raises(ValueError, match="Invalid borehole surface coordinates"):
        demo.julia_well_metadata(war, boreholes)


@pytest.mark.parametrize(
    "column, value",
    [
        ("SURF_LATITUDE", "91"),
        ("SURF_LATITUDE", "-91"),
        ("SURF_LONGITUDE", "181"),
        ("SURF_LONGITUDE", "-181"),
    ],
)
def test_out_of_domain_surface_position_fails(records, column, value):
    """Reject impossible positions before they can shift the field origin."""
    war, boreholes = records
    boreholes.loc[0, column] = value
    with pytest.raises(
        ValueError, match=f"Invalid borehole surface coordinates: {column}"
    ):
        demo.julia_well_metadata(war, boreholes)


@pytest.mark.parametrize(
    "column, value",
    [
        ("SURF_LATITUDE", "90"),
        ("SURF_LATITUDE", "-90"),
        ("SURF_LONGITUDE", "180"),
        ("SURF_LONGITUDE", "-180"),
    ],
)
def test_geographic_domain_endpoints_are_valid(records, column, value):
    war, boreholes = records
    boreholes.loc[0, column] = value
    result = demo.julia_well_metadata(war, boreholes).set_index("API_WELL_NUMBER")
    assert result.loc[DC_API, column] == float(value)


def test_missing_survey_for_any_selected_bore_fails(records):
    """Hand difference: selected {DC_API, JU_API} minus surveyed {DC_API}=JU_API.

    Failure must precede geometry processing, so a partial field cannot render.
    """
    metadata = demo.julia_well_metadata(*records)
    surveys = pd.DataFrame({"API_WELL_NUMBER": [DC_API]})
    with pytest.raises(ValueError, match=f"Missing survey rows.*{JU_API}"):
        demo.build_inputs(surveys, metadata)


def test_build_inputs_preserves_the_complete_lease_set(records):
    """Hand join: only DC_API/JU_API reach the pipeline, with their WAR names.

    Both wellheads are at the arbitrary origin, so each surface offset is
    (zero minus the mean of zeros) times any finite scale = zero. Every angle
    and station depth is also zero; no physical trajectory is asserted here.
    A malformed station for an unrelated API must be excluded before coercion.
    """
    metadata = demo.julia_well_metadata(*records)
    surveys = pd.DataFrame(
        {
            "API_WELL_NUMBER": [float(DC_API), f" {JU_API}.0 ", "unrelated"],
            "SURVEY_POINT_MD": ["0", "0", "invalid"],
            "INCL_ANG_DEG_VAL": "0",
            "INCL_ANG_MIN_VAL": "0",
            "DIR_DEG_VAL": "0",
            "DIR_MINS_VAL": "0",
            "SURF_LATITUDE": "0",
            "SURF_LONGITUDE": "0",
        }
    )
    original = surveys.copy()
    directions, well_data = demo.build_inputs(surveys, metadata)
    merged = well_data["merged_api12_df"].set_index("API12")
    expected_names = {int(DC_API): "DC101", int(JU_API): "JU102"}
    assert set(directions["API12"]) == set(expected_names)
    assert merged["Well Name"].to_dict() == expected_names
    assert merged.loc[int(JU_API), "Sidetrack and Bypass"] == "ST01BP00"
    assert merged["SURF_x_rel"].eq(0).all()
    assert merged["SURF_y_rel"].eq(0).all()
    pd.testing.assert_frame_equal(surveys, original)


def test_quoted_borehole_names_match(records):
    war, boreholes = records
    boreholes["WELL_NAME"] = (
        boreholes["WELL_NAME"].str.lower().map(lambda name: f' "{name}" ')
    )
    result = demo.julia_well_metadata(war, boreholes)
    assert set(result["WELL_NAME"]) == {"DC101", "JU102"}


def test_missing_borehole_name_cannot_confirm_identity(records):
    war, boreholes = records
    boreholes["WELL_NAME"] = None
    with pytest.raises(ValueError, match="Conflicting well names"):
        demo.julia_well_metadata(war, boreholes)


def test_main_checks_metadata_before_downloading_surveys(records, monkeypatch):
    war, boreholes = records
    war["SURF_LEASE_NUM"] = "OTHER"
    sources = {"war.txt": war, "boreholes.txt": boreholes}

    def unexpected_surveys():
        pytest.fail("Survey download must wait for lease metadata validation")

    monkeypatch.setattr(pd, "read_csv", lambda path, **kwargs: sources[path])
    monkeypatch.setattr(demo, "load_surveys", unexpected_surveys)
    with pytest.raises(ValueError, match="No WAR wells"):
        demo.main(["--war-main-csv", "war.txt", "--boreholes-csv", "boreholes.txt"])


def test_main_requires_both_raw_inputs():
    with pytest.raises(SystemExit) as error:
        demo.main([])
    assert error.value.code == 2  # argparse's missing-required-argument exit code.
