"""Database contract tests; all records are invented fixtures, not field data.

Arithmetic oracle: monthly oil volumes 100, 80 and 64 bbl sum to 244 bbl.
Missing gas is unknown, whereas measured zero water remains zero. Calendar
indices for November, December and January are consecutive despite the year
boundary. These are hand calculations, independent of the database methods.
"""

import hashlib
import json
import math
import runpy
from dataclasses import replace
from pathlib import Path

import pytest

from worldenergydata.production.database import (
    REGULATOR_SOURCES,
    ProductionDatabase,
    SourceSnapshot,
)


def snapshot(snapshot_id="release-a", source_id="bsee-data-center", **kwargs):
    """Invented source metadata exercises the reported-data branch only."""
    return SourceSnapshot(
        snapshot_id=snapshot_id,
        source_id=source_id,
        version="fixture-v1",
        locator="https://example.org/production.csv",
        retrieved_at="2026-10-20T12:00:00Z",
        sha256="a" * 64,
        data_kind=kwargs.pop("data_kind", "reported"),
        **kwargs,
    )


UNITS = {
    "oil_bbl": "bbl",
    "gas_mcf": "Mcf",
    "water_bbl": "bbl",
    "condensate_bbl": "bbl",
}


def row(month=11, year=2024, oil=100.0, **changes):
    result = {
        "region": "fixture-region",
        "field_name": "external-01",
        "year": year,
        "month": month,
        "oil_bbl": oil,
        "gas_mcf": None,
        "water_bbl": 0.0,
        "condensate_bbl": None,
        "source": "fixture-reported",
    }
    result.update(changes)
    return result


@pytest.fixture
def database(tmp_path):
    with ProductionDatabase(tmp_path / "production.sqlite") as db:
        db.add_asset("field-01", "Example field", "field")
        db.add_snapshot(snapshot())
        db.map_field("bsee-data-center", "external-01", "field-01")
        yield db


def history_rows():
    return [row(), row(12, oil=80), row(1, year=2025, oil=64)]


def test_persistence_and_unknown_versus_zero(tmp_path):
    path = tmp_path / "catalog.sqlite"
    with ProductionDatabase(path) as db:
        db.add_asset("field-01", "Example field", "field")
        db.add_snapshot(snapshot())
        db.map_field("bsee-data-center", "external-01", "field-01")
        assert db.ingest("release-a", history_rows(), units=UNITS) == 3
    with ProductionDatabase(path) as db:
        records = db.production("release-a", "field-01")
        assert sum(item["oil_bbl"] for item in records) == 244
        assert records[0]["gas_mcf"] is None
        assert records[0]["water_bbl"] == 0
        assert [item["period"] for item in records] == ["2024-11", "2024-12", "2025-01"]
        assert records[0]["source_label"] == "fixture-reported"
        assert db.source_snapshot("release-a")["sha256"] == "a" * 64


@pytest.mark.parametrize("source_id", REGULATOR_SOURCES.values())
def test_all_seven_regulators_use_explicit_identity(database, source_id):
    database.add_snapshot(snapshot("other", source_id))
    database.map_field(source_id, "same-name", "field-01")
    database.ingest("other", [row(field_name="same-name")], units=UNITS)
    assert database.production("other", "field-01")[0]["oil_bbl"] == 100


def test_no_implicit_name_matching_or_cross_regulator_join(database):
    database.add_snapshot(snapshot("other", "eia-api-v2"))
    with pytest.raises(ValueError, match="mapping"):
        database.ingest("other", [row()], units=UNITS)
    assert database.production("other", "field-01") == []


def test_facility_and_reservoir_links_are_many_to_many(database):
    database.add_asset("field-02", "Second example field", "field")
    database.add_asset("facility-01", "Example facility", "facility")
    database.add_asset("reservoir-01", "Example reservoir", "reservoir")
    database.link_asset("field-01", "facility-01")
    database.link_asset("field-02", "facility-01")
    database.link_asset("field-01", "reservoir-01")
    assert {item["asset_id"] for item in database.linked_assets("field-01")} == {
        "facility-01",
        "reservoir-01",
    }
    with pytest.raises(ValueError):
        database.link_asset("facility-01", "reservoir-01")
    with pytest.raises(ValueError):
        database.map_field("bsee-data-center", "facility-code", "facility-01")


@pytest.mark.parametrize(
    "bad_row",
    [
        row(month=13),
        row(month=0),
        row(month=1.5),
        row(year=True),
        row(oil=-1),
        row(oil=float("inf")),
        row(oil=float("nan")),
        row(oil=True),
        row(source=""),
        row(field_name="unmapped"),
    ],
)
def test_bad_rows_roll_back_entire_batch(database, bad_row):
    with pytest.raises((TypeError, ValueError)):
        database.ingest("release-a", [row(), bad_row], units=UNITS)
    assert database.production("release-a", "field-01") == []
    assert database.ingest("release-a", [row()], units=UNITS) == 1


def test_duplicate_rows_roll_back_and_snapshot_is_immutable(database):
    with pytest.raises(ValueError, match="duplicate"):
        database.ingest("release-a", [row(), row()], units=UNITS)
    database.ingest("release-a", [row()], units=UNITS)
    with pytest.raises(ValueError, match="loaded"):
        database.ingest("release-a", [row(12)], units=UNITS)
    with pytest.raises(ValueError):
        database.add_snapshot(snapshot())
    with pytest.raises(ValueError):
        database.map_field("bsee-data-center", "external-01", "field-01")


@pytest.mark.parametrize("units", [{}, {**UNITS, "oil_bbl": "m3"}])
def test_explicit_units_are_required(database, units):
    with pytest.raises(ValueError, match="units"):
        database.ingest("release-a", [row()], units=units)


def test_snapshots_are_not_summed_together(database):
    database.ingest("release-a", [row()], units=UNITS)
    database.add_snapshot(snapshot("release-b"))
    database.ingest("release-b", [row(oil=90)], units=UNITS)
    assert database.production("release-a", "field-01")[0]["oil_bbl"] == 100
    assert database.production("release-b", "field-01")[0]["oil_bbl"] == 90


@pytest.mark.parametrize(
    "changes",
    [
        {"source_id": "unknown"},
        {"sha256": "bad"},
        {"retrieved_at": "2026-10-20"},
        {"data_kind": "ready"},
        {"version": " "},
        {"locator": ""},
    ],
)
def test_invalid_snapshot_metadata(changes):
    with pytest.raises(ValueError):
        replace(snapshot(), **changes)


def test_decline_history_and_stored_parameters(database):
    """Hand oracle: 100 * 0.8**t gives 100, 80, 64 at t=0,1,2.

    EIA, Production Decline Curve Analysis (2023), hyperbolic equation and
    exponential limiting form: Di=-ln(0.8) / month. Parameters here are supplied
    fixture inputs; the database does not estimate them or assert fit quality.
    """
    database.ingest("release-a", history_rows(), units=UNITS)
    history = database.decline_history("release-a", "field-01")
    assert history.points == ((1, 100.0), (2, 80.0), (3, 64.0))
    database.save_decline(
        "curve-a",
        history,
        model="exponential",
        qi=125.0,
        di=math.log(1.25),
        b=0.0,
        method_ref="Independent fixture calculation: -ln(0.8).",
    )
    curve = database.decline_curve("curve-a")
    assert curve["history_sha256"] == history.sha256
    assert curve["qualification"] == "NOT_EVALUATED"
    assert curve["rate_unit"] == "bbl/month"
    assert curve["source_version"] == "fixture-v1"
    with pytest.raises(ValueError, match="history"):
        database.save_decline(
            "forged",
            replace(history, points=((1, 200.0),)),
            model="exponential",
            qi=100,
            di=0.1,
            b=0,
            method_ref="Fixture calculation",
        )


@pytest.mark.parametrize(
    "records",
    [
        [row(), row(1, year=2025)],
        [row(oil=None)],
        [row(oil=0)],
        [],
    ],
)
def test_decline_rejects_incomplete_histories(database, records):
    if records:
        database.ingest("release-a", records, units=UNITS)
    with pytest.raises((TypeError, ValueError)):
        database.decline_history("release-a", "field-01")


def test_synthetic_history_requires_explicit_opt_in(database):
    database.add_snapshot(snapshot("synthetic", data_kind="synthetic"))
    database.ingest("synthetic", history_rows(), units=UNITS)
    with pytest.raises(ValueError, match="synthetic"):
        database.decline_history("synthetic", "field-01")
    history = database.decline_history("synthetic", "field-01", allow_synthetic=True)
    assert history.data_kind == "synthetic"


def test_reported_snapshot_cannot_promote_mock_adapter_rows(database):
    with pytest.raises(ValueError, match="synthetic"):
        database.ingest("release-a", [row(source="bsee_mock")], units=UNITS)


def test_aggregate_is_not_a_reservoir_field(database):
    database.add_asset("basin-01", "Example basin", "aggregate")
    database.map_field("bsee-data-center", "basin-code", "basin-01")
    database.ingest("release-a", [row(field_name="basin-code")], units=UNITS)
    with pytest.raises(ValueError, match="field"):
        database.decline_history("release-a", "basin-01")


def test_parameterized_identifiers_do_not_execute_sql(database):
    identifier = "field'); DROP TABLE assets; --"
    database.add_asset(identifier, "Literal identifier", "field")
    database.map_field("bsee-data-center", identifier, identifier)
    database.ingest("release-a", [row(field_name=identifier)], units=UNITS)
    assert database.production("release-a", identifier)[0]["oil_bbl"] == 100


def test_worked_example_uses_existing_fitter_and_retains_raw_bytes(tmp_path):
    """Hand oracle: total=100+80+64=244; qi=100/0.8=125 at t=0.

    The example rounds qi to one decimal, so equality checks its reported value
    without introducing a numerical acceptance limit for field data.
    """
    root = Path(__file__).resolve().parents[4]
    example = runpy.run_path(str(root / "examples" / "production_database.py"))
    result = example["run_example"](tmp_path)
    assert result["oil_total_bbl"] == 244.0
    assert result["fitted_qi_bbl_per_month"] == 125.0
    assert result["qualification"] == "NOT_EVALUATED"
    assert result["data_kind"] == "synthetic"
    assert (
        hashlib.sha256((tmp_path / result["raw_file"]).read_bytes()).hexdigest()
        == result["raw_sha256"]
    )
    assert json.loads((tmp_path / "manifest.json").read_text()) == result
    with pytest.raises(FileExistsError):
        example["run_example"](tmp_path)


def test_calendar_periods_have_fixed_width(database):
    """ISO calendar representation pads years to four digits, independently of locale."""
    database.ingest("release-a", [row(month=1, year=999)], units=UNITS)
    assert database.production("release-a", "field-01")[0]["period"] == "0999-01"


def test_generator_failure_rolls_back_prior_records(database):
    def broken_records():
        yield row()
        raise RuntimeError("source iteration failed")

    with pytest.raises(RuntimeError, match="source iteration"):
        database.ingest("release-a", broken_records(), units=UNITS)
    assert database.production("release-a", "field-01") == []
    database.ingest("release-a", [row()], units=UNITS)


@pytest.mark.parametrize(
    "changes",
    [
        {"model": "unknown"},
        {"b": 1},
        {"qi": 0},
        {"di": float("inf")},
        {"method_ref": ""},
    ],
)
def test_decline_rejects_invalid_parameters(database, changes):
    database.ingest("release-a", history_rows(), units=UNITS)
    history = database.decline_history("release-a", "field-01")
    parameters = {
        "model": "exponential",
        "qi": 125,
        "di": math.log(1.25),
        "b": 0,
        "method_ref": "Hand calculation",
    }
    parameters.update(changes)
    with pytest.raises(ValueError):
        database.save_decline("bad-curve", history, **parameters)


def test_two_regulators_can_map_one_field_without_combining_snapshots(database):
    database.add_snapshot(snapshot("second-regulator", "uk-nsta-opendata"))
    database.map_field("uk-nsta-opendata", "different-code", "field-01")
    database.ingest("release-a", [row()], units=UNITS)
    database.ingest(
        "second-regulator", [row(field_name="different-code", oil=90)], units=UNITS
    )
    assert database.production("release-a", "field-01")[0]["oil_bbl"] == 100
    assert database.production("second-regulator", "field-01")[0]["oil_bbl"] == 90
