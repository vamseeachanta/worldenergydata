"""HSE query contract using synthetic inputs and independent hand calculations.

The fixture defines three incidents: BSEE A in 2023 (minor), BSEE B in 2024
(fatality), OSHA C in 2024 (fatality). Penalties linked to B are 10 and 30;
the penalty linked to A is 5. Thus the 2024 minimum-20 selection is [30].
Statistics for operator A in 2024 are 2 and 3, so the grouped total is 5.
TRI rows are chemical X/industry 111 in 2024 and Y/222 in 2023. These are
invented software examples, not observed records or regulatory limits.
"""

import asyncio
import json
import runpy
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from worldenergydata.hse import api
from worldenergydata.hse.database.models import (
    Base,
    HSEIncident,
    SafetyStatistic,
    ToxicRelease,
    ViolationIncident,
)


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "incidents.sqlite"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        first = HSEIncident(
            bsee_incident_id="BSEE-A",
            incident_date=datetime(2023, 12, 31),
            operator="Example A",
            incident_type="injury",
            severity="minor",
        )
        second = HSEIncident(
            bsee_incident_id="BSEE-B",
            incident_date=datetime(2024, 1, 1),
            operator="Example A",
            incident_type="injury",
            severity="fatality",
        )
        third = HSEIncident(
            bsee_incident_id="OSHA-INJ-C",
            incident_date=datetime(2024, 12, 31),
            operator="Example B",
            incident_type="injury",
            severity="fatality",
        )
        session.add_all([first, second, third])
        session.flush()
        session.add_all(
            [
                ViolationIncident(hse_incident_id=first.id, penalty_amount=5),
                ViolationIncident(hse_incident_id=second.id, penalty_amount=10),
                ViolationIncident(hse_incident_id=second.id, penalty_amount=30),
                SafetyStatistic(
                    report_date=datetime(2024, 3, 31),
                    operator="Example A",
                    total_incidents=2,
                ),
                SafetyStatistic(
                    report_date=datetime(2024, 6, 30),
                    operator="Example A",
                    total_incidents=3,
                ),
                ToxicRelease(
                    tri_facility_id="X",
                    facility_name="Example facility A",
                    chemical_name="X",
                    naics_code="111",
                    reporting_year=2024,
                ),
                ToxicRelease(
                    tri_facility_id="Y",
                    facility_name="Example facility B",
                    chemical_name="Y",
                    naics_code="222",
                    reporting_year=2023,
                ),
            ]
        )
        session.commit()
    yield path, engine
    engine.dispose()


@pytest.fixture
def client(database):
    path, _ = database
    with api.HSEApi(api.HSEQueryConfig(database_url=f"sqlite:///{path}")) as client:
        yield client


@pytest.mark.parametrize(
    "filters,expected",
    [
        ({"operator": "Example A"}, ["BSEE-A", "BSEE-B"]),
        ({"year": 2024, "severity": "fatality", "source": "bsee_inc"}, ["BSEE-B"]),
        ({"source": "osha", "year": 2023}, []),
    ],
)
def test_incidents(client, filters, expected):
    assert client.incidents.query(**filters).bsee_incident_id.tolist() == expected


@pytest.mark.parametrize(
    "filters,expected",
    [
        ({"operator": "Example A", "year": 2024, "min_amount": 20}, [30]),
        ({"year": 2023}, [5]),
        ({"min_amount": 31}, []),
    ],
)
def test_penalties(client, filters, expected):
    assert client.penalties.query(**filters).penalty_amount.tolist() == expected


@pytest.mark.parametrize(
    "filters,expected",
    [
        ({"year": 2024, "metric": "total_incidents", "grouping": "operator"}, [5]),
        ({"operator": "Example A", "metric": "total_incidents"}, [2, 3]),
        ({"year": 2023}, []),
    ],
)
def test_statistics(client, filters, expected):
    assert client.statistics.query(**filters).total_incidents.tolist() == expected


@pytest.mark.parametrize(
    "filters,expected",
    [
        ({"naics": "111", "year": 2024}, ["X"]),
        ({"chemical": "Y"}, ["Y"]),
        ({"year": 2024, "naics": "222"}, []),
    ],
)
def test_tri(client, filters, expected):
    assert client.epa_tri.query(**filters).chemical_name.tolist() == expected


@pytest.mark.parametrize(
    "filters,expected",
    [
        ({"year": 2024, "severity": "fatality"}, ["OSHA-INJ-C"]),
        ({"operator": "Example A"}, []),
        ({"year": 2023}, []),
    ],
)
def test_osha(client, filters, expected):
    assert client.osha.query(**filters).bsee_incident_id.tolist() == expected


@pytest.mark.parametrize(
    "surface,filters",
    [
        ("incidents", {"source": "unknown"}),
        ("incidents", {"operators": "Example A"}),
        ("incidents", {"year": True}),
        ("incidents", {"start_year": 2024, "end_year": 2023}),
        ("incidents", {"limit": -1}),
        ("incidents", {"operatr": "Example A"}),
        ("penalties", {"min_amount": float("nan")}),
        ("statistics", {"metric": "missing"}),
        ("statistics", {"grouping": "missing"}),
    ],
)
def test_invalid_filters_fail_before_sql(client, surface, filters):
    engine = client._backend.engine
    calls = []

    def record(*args):
        calls.append(args)

    event.listen(engine, "before_cursor_execute", record)
    try:
        with pytest.raises((ValueError, TypeError)):
            getattr(client, surface).query(**filters)
        assert calls == []
    finally:
        event.remove(engine, "before_cursor_execute", record)


@pytest.mark.parametrize(
    "surface,filters",
    [
        ("epa_tri", {"chemical_carcinogen": True}),
        ("epa_tri", {"chemical_carcinogen": False}),
        ("osha", {"naics": "111"}),
    ],
)
def test_missing_schema_evidence_is_explicit(client, surface, filters):
    with pytest.raises(NotImplementedError, match="NOT_EVALUATED"):
        getattr(client, surface).query(**filters)


def test_pagination_and_plural_precedence(client):
    frame = client.incidents.query(
        operator="Example B",
        operators=["Example A"],
        start_year=2023,
        end_year=2024,
        limit=1,
        offset=1,
    )
    assert frame.bsee_incident_id.tolist() == ["BSEE-B"]
    assert client.incidents.query(operator="' OR 1=1 --").empty


def test_filters_are_pushed_to_sql(database):
    _, engine = database
    statements = []

    def record(connection, cursor, statement, parameters, context, many):
        statements.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", record)
    try:
        with Session(engine) as session:
            api.IncidentsQuery(session=session).query(operator="Example A", limit=1)
        assert len(statements) == 1
        sql, parameters = statements[0]
        assert "WHERE" in sql and "LIMIT" in sql
        assert "Example A" not in sql
        assert "Example A" in parameters
    finally:
        event.remove(engine, "before_cursor_execute", record)


def test_unknown_statistics_remain_missing(database):
    _, engine = database
    with Session(engine) as session:
        frame = api.StatisticsQuery(session).query(grouping="operator")
    assert frame.fatality_count.isna().all()


def test_default_sample_is_labeled():
    query = api.IncidentsQuery()
    try:
        frame = query.query()
        assert frame.attrs["data_kind"] == "synthetic"
    finally:
        query.close()


def test_configuration_and_missing_database(tmp_path):
    with pytest.raises(ValidationError):
        api.HSEQueryConfig(database_url="not-a-url")
    path = tmp_path / "absent.sqlite"
    with pytest.raises(FileNotFoundError):
        api.HSEApi(api.HSEQueryConfig(database_url=f"sqlite:///{path}"))
    assert not path.exists()


@pytest.mark.parametrize(
    "surface,filters,column,expected",
    [
        ("incidents", {"year": 2024}, "bsee_incident_id", ["BSEE-B", "OSHA-INJ-C"]),
        ("penalties", {"min_amount": 20}, "penalty_amount", [30]),
        (
            "statistics",
            {"grouping": "operator", "metric": "total_incidents"},
            "total_incidents",
            [5],
        ),
        ("epa_tri", {"year": 2024}, "chemical_name", ["X"]),
        ("osha", {"severity": "fatality"}, "bsee_incident_id", ["OSHA-INJ-C"]),
    ],
)
def test_async_queries(database, surface, filters, column, expected):
    path, _ = database

    async def run():
        config = api.HSEQueryConfig(database_url=f"sqlite:///{path}")
        async with api.HSEApi(config) as client:
            return await getattr(client, surface).aquery(**filters)

    frame = asyncio.run(run())
    assert frame[column].tolist() == expected
    assert frame.attrs["data_kind"] == "database"


def test_concurrent_async_queries(database):
    path, _ = database

    async def run():
        async with api.HSEApi(
            api.HSEQueryConfig(database_url=f"sqlite:///{path}")
        ) as c:
            return await asyncio.gather(
                c.incidents.aquery(year=2023), c.incidents.aquery(year=2024)
            )

    first, second = asyncio.run(run())
    assert len(first) == 1 and len(second) == 2


def test_cli_query_and_error(database):
    from worldenergydata.cli.commands.hse import app

    path, _ = database
    runner = CliRunner()
    args = [
        "incidents",
        "query",
        "--database-url",
        f"sqlite:///{path}",
        "--operator",
        "Example A",
        "--year",
        "2024",
        "--output",
        "json",
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert [row["bsee_incident_id"] for row in json.loads(result.stdout)] == ["BSEE-B"]
    result = runner.invoke(app, args + ["--source", "unknown"])
    assert result.exit_code != 0


def test_quickstart_runs(capsys):
    path = Path(__file__).resolve().parents[2] / "notebooks" / "quickstart_hse.py"
    runpy.run_path(str(path), run_name="__main__")
    output = capsys.readouterr().out
    assert "synthetic" in output
    assert "65000" in output


def test_missing_tables_do_not_return_sample(tmp_path):
    path = tmp_path / "empty.sqlite"
    path.touch()
    with (
        api.HSEApi(api.HSEQueryConfig(database_url=f"sqlite:///{path}")) as client,
        pytest.raises(OperationalError, match="no such table"),
    ):
        client.incidents.query()


def test_cli_demo_and_environment(database, monkeypatch):
    from worldenergydata.cli.commands.hse import app

    path, _ = database
    runner = CliRunner()
    monkeypatch.setenv("HSE_DATABASE_URL", f"sqlite:///{path}")
    result = runner.invoke(app, ["incidents", "query", "--year", "2023"])
    assert result.exit_code == 0, result.output
    assert len(json.loads(result.stdout)) == 1
    monkeypatch.delenv("HSE_DATABASE_URL")
    result = runner.invoke(app, ["incidents", "query", "--demo", "--output", "csv"])
    assert result.exit_code == 0, result.output
    assert "Synthetic" in result.stderr
    assert result.stdout.startswith("bsee_incident_id,")
    assert runner.invoke(app, ["incidents", "query"]).exit_code != 0


def test_hse_is_reachable_from_main_cli(database):
    from worldenergydata.cli.main import app

    path, _ = database
    result = CliRunner().invoke(
        app,
        [
            "hse",
            "incidents",
            "query",
            "--database-url",
            f"sqlite:///{path}",
            "--year",
            "2023",
        ],
    )
    assert result.exit_code == 0, result.output
    assert len(json.loads(result.stdout)) == 1
