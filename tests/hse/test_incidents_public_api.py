"""Regression coverage for the incident entry point named in the approved plan."""

import asyncio
from datetime import datetime

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from worldenergydata.hse.database.models import Base, HSEIncident


@pytest.fixture
def incident_database(tmp_path):
    """Invented records: one OSHA row followed by 101 BSEE rows in key order."""
    path = tmp_path / "incidents.sqlite"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            HSEIncident(
                bsee_incident_id="OSHA-INJ-1",
                incident_date=datetime(2022, 6, 1),
                operator="Example B",
                incident_type="injury",
                severity="fatality",
            )
        )
        for number in range(101):
            session.add(
                HSEIncident(
                    bsee_incident_id=f"BSEE-{number:03}",
                    incident_date=datetime(2022 if number < 100 else 2023, 6, 1),
                    operator="Example A" if number < 100 else "Example B",
                    incident_type="injury",
                    severity="minor" if number < 100 else "fatality",
                )
            )
        session.commit()
    yield path, engine
    engine.dispose()


def test_planned_incidents_entry_point_is_exported():
    from worldenergydata.hse import HSEIncidentsQuery
    from worldenergydata.hse.api import HSEIncidentsQuery as ApiQuery

    assert HSEIncidentsQuery is ApiQuery
    query = HSEIncidentsQuery()
    try:
        frame = query.query(source="bsee_inc", year=2022)
        assert frame.bsee_incident_id.tolist() == ["INC-2022-002", "INC-2022-003"]
    finally:
        query.close()


def test_planned_defaults_select_first_100_bsee_records(incident_database):
    from worldenergydata.hse import HSEIncidentsQuery

    _, engine = incident_database
    with Session(engine) as session:
        frame = HSEIncidentsQuery(session).query()
    assert frame.bsee_incident_id.tolist() == [f"BSEE-{n:03}" for n in range(100)]


@pytest.mark.parametrize(
    "filters,expected",
    [
        ({"source": "osha", "year": 2022}, ["OSHA-INJ-1"]),
        (
            {"year": 2023, "operator": "Example B", "incident_type": "injury"},
            ["BSEE-100"],
        ),
        ({"year": 2022, "severity": "fatality"}, []),
        (
            {"sources": ["osha", "bsee_inc"], "operator": "Example B"},
            ["OSHA-INJ-1", "BSEE-100"],
        ),
        ({"source": None, "operator": "Example B"}, ["OSHA-INJ-1", "BSEE-100"]),
        ({"limit": 1, "offset": 100}, ["BSEE-100"]),
        ({"operator": "unknown"}, []),
    ],
)
def test_explicit_filters_override_planned_defaults(incident_database, filters, expected):
    from worldenergydata.hse import HSEIncidentsQuery

    _, engine = incident_database
    with Session(engine) as session:
        frame = HSEIncidentsQuery(session).query(**filters)
    assert isinstance(frame, pd.DataFrame)
    assert frame.bsee_incident_id.tolist() == expected
    assert frame.attrs["data_kind"] == "database"


def test_unlimited_selection_and_existing_entry_point(incident_database):
    from worldenergydata.hse.api import HSEIncidentsQuery, IncidentsQuery

    _, engine = incident_database
    with Session(engine) as session:
        assert len(HSEIncidentsQuery(session).query(limit=None)) == 101
        assert len(IncidentsQuery(session).query()) == 102


@pytest.mark.parametrize("filters", [{}, {"source": "osha"}, {"year": 2023}])
def test_planned_async_defaults_match_sync(incident_database, filters):
    from worldenergydata.hse import HSEIncidentsQuery
    from worldenergydata.hse.query_config import HSEBackend, HSEQueryConfig

    path, engine = incident_database
    with Session(engine) as session:
        expected = HSEIncidentsQuery(session).query(**filters)

    async def run():
        backend = HSEBackend(HSEQueryConfig(database_url=f"sqlite:///{path}"))
        try:
            return await HSEIncidentsQuery(backend=backend).aquery(**filters)
        finally:
            await backend.aclose()

    pd.testing.assert_frame_equal(asyncio.run(run()), expected)


def test_planned_envelope_uses_same_defaults(incident_database):
    from worldenergydata.hse import HSEIncidentsQuery

    _, engine = incident_database
    with Session(engine) as session:
        envelope = HSEIncidentsQuery(session).query_envelope()
    assert envelope.workflow_id == "hse.incidents"
    assert envelope.result["records"] == 100
