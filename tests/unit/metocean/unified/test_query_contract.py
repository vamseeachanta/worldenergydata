"""Unified contract tests using synthetic observations, with no network access.

Numbers are test inputs, not environmental design values. Locations reuse the
Gulf of Mexico and North Sea examples in test_unified_query.py. Expected UTC
times use hand subtraction of the supplied offset; expected rows use inclusive
interval membership and parameter equality, without the implementation.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest
from typer.testing import CliRunner

from worldenergydata.metocean.clients.base_client import FetchResult
from worldenergydata.metocean.constants import DataSource
from worldenergydata.metocean.unified import (
    MetoceanDashboard,
    MetoceanHarmonizer,
    MetoceanQuery,
    UnifiedMetoceanClient,
)


def query(lat=28.5, lon=-88.5, **kwargs):
    return MetoceanQuery(lat, lon, datetime(2023, 1, 1), datetime(2023, 1, 2), **kwargs)


def rows(source):
    return pd.DataFrame(
        [
            ["2023-01-01T01:00:00+01:00", "Hs", 2.0, source, "m"],
            ["2023-01-01T00:30:00Z", "Hs", 4.0, source, "m"],
            ["2023-01-02T00:00:00Z", "Hs", 6.0, source, "m"],
            ["2023-01-03T00:00:00Z", "Hs", 8.0, source, "m"],
            ["2023-01-01T00:00:00Z", "Tp", 9.0, source, "s"],
        ],
        columns=["timestamp", "parameter", "value", "source", "unit"],
    )


@pytest.mark.parametrize("lat,lon", [(28.5, -88.5), (57.0, 3.5)])
def test_locations_filter_time_and_parameter_without_fabricating_samples(lat, lon):
    """01:00+01 = 00:00 UTC; 00:30 stays; both interval ends stay.

    The third day and Tp are excluded. Each contributing source has precisely
    the three input Hs rows, values 2, 4, 6; no hourly samples are invented.
    """
    client = UnifiedMetoceanClient()
    with patch.object(client, "_fetch_from_source", side_effect=lambda s, q: rows(s)):
        result = client.query(query(lat, lon, parameters=("Hs",)))
    for _, group in result.data.groupby("source"):
        assert group.value.tolist() == [2.0, 4.0, 6.0]
        assert group.timestamp.dt.strftime("%H:%M").tolist() == [
            "00:00",
            "00:30",
            "00:00",
        ]
    assert set(result.data.parameter) == {"Hs"}
    assert result.sources_used == sorted(result.data.source.unique())


@pytest.mark.parametrize("lat,lon", [(91, 0), (0, 181), (float("nan"), 0)])
def test_invalid_coordinates_rejected_before_fetch(lat, lon):
    """RFC 5870 (2010), section 3.4.2 supplies angular bounds."""
    with pytest.raises(ValueError):
        query(lat, lon)


def test_invalid_time_and_parameters():
    with pytest.raises(ValueError):
        MetoceanQuery(0, 0, datetime(2023, 2, 1), datetime(2023, 1, 1))
    with pytest.raises(ValueError):
        query(parameters=())
    with pytest.raises(ValueError):
        query(parameters=("unknown",))


def test_failure_is_distinct_from_empty_and_unused():
    client = UnifiedMetoceanClient()

    def fetch(source, q):
        if source == "ndbc":
            raise RuntimeError("private diagnostic must not escape")
        return rows(source).iloc[:0]

    with patch.object(client, "_fetch_from_source", side_effect=fetch):
        result = client.query(query())
    assert result.sources_used == []
    assert result.source_status["ndbc"] == "FAILED"
    assert result.source_status["coops"] == "EMPTY"
    assert result.coverage_gaps


def test_optional_sources_not_evaluated_without_configuration():
    client = UnifiedMetoceanClient()
    with (
        patch.object(client, "_fetch_ndbc", return_value=rows("ndbc")),
        patch.object(client, "_fetch_coops", return_value=rows("coops")),
        patch.object(client, "_fetch_open_meteo", return_value=rows("open_meteo")),
    ):
        result = client.query(query())
    assert result.source_status["era5"] == "NOT_EVALUATED"
    assert result.source_status["cmems"] == "NOT_EVALUATED"
    assert result.source_status["erddap"] == "NOT_EVALUATED"


@pytest.mark.parametrize("source", ["era5", "cmems"])
def test_configured_copernicus_adapter(source):
    client = UnifiedMetoceanClient(source_fetchers={source: lambda q: rows(source)})
    with patch.object(client._coverage, "get_clients", return_value=[source]):
        result = client.query(query(parameters=("Hs",)))
    assert result.sources_used == [source]
    assert result.source_status[source] == "OK"
    assert result.data.value.tolist() == [2.0, 4.0, 6.0]


def test_erddap_uses_configured_dataset_and_bounds():
    bbox = (-89.0, -88.0, 28.0, 29.0)  # caller-specified synthetic selection
    client = UnifiedMetoceanClient(erddap_dataset="fixture", erddap_bbox=bbox)
    with patch(
        "worldenergydata.metocean.clients.erddap_client.ERDDAPClient"
    ) as factory:
        api = factory.return_value.__enter__.return_value
        api.fetch_tabledap.return_value = SimpleNamespace(data=[])
        client._fetch_from_source("erddap", query())
    assert api.fetch_tabledap.call_args.kwargs["dataset_id"] == "fixture"
    assert api.fetch_tabledap.call_args.kwargs["bbox"] == bbox


def test_harmonizer_converts_offset_and_drops_nonfinite():
    """01:00+01:00 minus one hour is 00:00 UTC; infinity is not data."""
    data = MetoceanHarmonizer().harmonize_ndbc(
        [
            {"observation_time": "2023-01-01T01:00:00+01:00", "wave_height_m": 2},
            {"observation_time": "2023-01-01", "wave_height_m": float("inf")},
        ]
    )
    assert data.timestamp.tolist() == [pd.Timestamp("2023-01-01")]
    assert data.value.tolist() == [2.0]


def test_cli_exports_combined_csv_and_plotly(tmp_path):
    """Two sources times three retained rows = six CSV rows; mean=(2+4+6)/3=4."""
    from worldenergydata.metocean.cli import app

    client = UnifiedMetoceanClient()
    with (
        patch.object(
            client._coverage, "get_clients", return_value=["ndbc", "open_meteo"]
        ),
        patch.object(client, "_fetch_from_source", side_effect=lambda s, q: rows(s)),
    ):
        result = client.query(query(parameters=("Hs",)))
    assert MetoceanDashboard().build_summary_stats(result)["mean"].tolist() == [4, 4]
    with patch.object(UnifiedMetoceanClient, "query", return_value=result):
        invocation = CliRunner().invoke(
            app,
            [
                "unified",
                "--lat",
                "28.5",
                "--lon",
                "-88.5",
                "--start",
                "2023-01-01",
                "--end",
                "2023-01-02",
                "--parameters",
                "Hs",
                "--output",
                str(tmp_path / "combined.csv"),
                "--dashboard",
                str(tmp_path / "combined.html"),
            ],
        )
    assert invocation.exit_code == 0, invocation.output
    assert len(pd.read_csv(tmp_path / "combined.csv")) == 6
    assert "Plotly.newPlot" in (tmp_path / "combined.html").read_text(encoding="utf-8")


def test_cli_invalid_location_is_reported():
    from worldenergydata.metocean.cli import app

    result = CliRunner().invoke(
        app,
        [
            "unified",
            "--lat",
            "91",
            "--lon",
            "0",
            "--start",
            "2023-01-01",
            "--end",
            "2023-01-02",
        ],
    )
    assert result.exit_code != 0
    assert "latitude" in result.output.lower()


@pytest.mark.parametrize("bbox", [(), (1, 2, 3), (2, 1, 3, 4), (1, 2, 3, 91)])
def test_invalid_erddap_bounds_rejected(bbox):
    """Bounds are ordered caller inputs, with RFC 5870 angular limits."""
    with pytest.raises(ValueError):
        UnifiedMetoceanClient(erddap_dataset="fixture", erddap_bbox=bbox)


def test_wrong_adapter_units_fail_source_without_relabelling():
    data = rows("era5")
    data["unit"] = "cm"
    client = UnifiedMetoceanClient(source_fetchers={"era5": lambda q: data})
    with patch.object(client._coverage, "get_clients", return_value=["era5"]):
        result = client.query(query())
    assert result.source_status == {"era5": "FAILED"}
    assert result.sources_used == []


@pytest.mark.parametrize("source", ["era5", "cmems"])
@pytest.mark.parametrize(
    "units,status,values",
    [
        pytest.param(["m"], "OK", [2.0], id="matching"),
        pytest.param([pd.NA], "FAILED", [], id="missing"),
        pytest.param(["m", pd.NA], "FAILED", [], id="missing-last"),
        pytest.param([pd.NA, "m"], "FAILED", [], id="missing-first"),
        pytest.param(["m", "cm"], "FAILED", [], id="mixed-mismatch"),
        pytest.param(["m", "m"], "OK", [2.0, 4.0], id="matching-multiple"),
    ],
)
def test_nullable_adapter_units_require_every_row_to_match(
    source, units, status, values
):
    """Missing or mismatched units reject the source, including partial results."""
    data = rows(source).iloc[: len(units)].copy()
    data["unit"] = pd.Series(units, dtype="string")
    client = UnifiedMetoceanClient(source_fetchers={source: lambda q: data})
    with patch.object(client._coverage, "get_clients", return_value=[source]):
        result = client.query(query(parameters=("Hs",)))
    assert result.source_status == {source: status}
    assert result.sources_used == ([source] if status == "OK" else [])
    assert result.data.value.tolist() == values


@pytest.mark.parametrize(
    "source,method",
    [
        ("ndbc", "fetch_historical"),
        ("open_meteo", "fetch_historical"),
        ("met_norway", "fetch_combined_forecast"),
    ],
)
def test_native_client_dispatch_uses_real_observation_contract(source, method):
    """Each synthetic native observation supplies Hs=2 m at the interval start."""
    classes = {
        "ndbc": "NDBCClient",
        "open_meteo": "OpenMeteoClient",
        "met_norway": "MetNorwayClient",
    }
    client = UnifiedMetoceanClient()
    with patch(
        f"worldenergydata.metocean.clients.{source}_client.{classes[source]}"
    ) as factory:
        api = factory.return_value.__enter__.return_value
        api.fetch_stations.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(
                    station_id="fixture",
                    latitude=28.5,
                    longitude=-88.5,
                )
            ]
        )
        getattr(api, method).return_value = SimpleNamespace(
            data=[
                SimpleNamespace(
                    observation_time=datetime(2023, 1, 1),
                    forecast_time=datetime(2023, 1, 1),
                    wave_height_m=2.0,
                )
            ]
        )
        result = client._fetch_from_source(source, query())
    assert result.source.tolist() == [source]
    assert result.value.tolist() == [2.0]


def test_coops_fetches_each_requested_product():
    """Independent input rows: current=2 m/s and level=4 m; both must remain."""
    client = UnifiedMetoceanClient()
    with patch("worldenergydata.metocean.clients.coops_client.COOPSClient") as factory:
        api = factory.return_value.__enter__.return_value
        api.fetch_stations.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(
                    station_id="fixture",
                    latitude=28.5,
                    longitude=-88.5,
                )
            ]
        )
        api.fetch_currents.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(
                    observation_time=datetime(2023, 1, 1),
                    speed_ms=2.0,
                )
            ]
        )
        api.fetch_water_level.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(
                    observation_time=datetime(2023, 1, 1),
                    water_level_m=4.0,
                )
            ]
        )
        result = client._fetch_from_source(
            "coops", query(parameters=("current_speed", "water_level"))
        )
    assert dict(zip(result.parameter, result.value)) == {
        "current_speed": 2.0,
        "water_level": 4.0,
    }


def test_offline_worked_example(tmp_path):
    """Six sources times three rows=18; five times three=15; (2+4+6)/3=4."""
    from worldenergydata.metocean.unified.example import run_example

    assert run_example(tmp_path) == {
        "gulf": {"rows": 18, "mean_Hs_m": 4.0},
        "north_sea": {"rows": 15, "mean_Hs_m": 4.0},
    }
    assert "Plotly.newPlot" in (tmp_path / "north_sea.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("command", ["unified", "historical", "update"])
def test_cli_help_preserves_option_registration(command):
    from worldenergydata.metocean.cli import app

    result = CliRunner().invoke(app, [command, "--help"])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    "source,method",
    [
        ("ndbc", "fetch_historical"),
        ("coops", "fetch_currents"),
        ("coops", "fetch_water_level"),
        ("open_meteo", "fetch_historical"),
        ("met_norway", "fetch_combined_forecast"),
        ("erddap", "fetch_tabledap"),
        ("ndbc", "fetch_stations"),
        ("coops", "fetch_stations"),
    ],
)
@pytest.mark.parametrize("has_rows", [False, True], ids=["empty", "partial"])
@pytest.mark.parametrize(
    "had_errors,error_messages",
    [
        (True, ["upstream diagnostic withheld"]),
        (True, []),
        (False, ["upstream diagnostic withheld"]),
        (False, []),
    ],
    ids=["both-errors", "flag-only", "messages-only", "clean"],
)
def test_native_fetch_outcomes(
    source, method, has_rows, had_errors, error_messages, caplog
):
    """Native errors fail the whole source, before consuming partial records.

    Clean empty results remain EMPTY and clean rows remain OK. A healthy
    adapter still contributes its three Hs rows when another source fails.
    """
    from worldenergydata.metocean.unified.unified_query import _nearest_station

    classes = {
        "ndbc": "NDBCClient",
        "coops": "COOPSClient",
        "open_meteo": "OpenMeteoClient",
        "met_norway": "MetNorwayClient",
        "erddap": "ERDDAPClient",
    }

    def native_result(data, **kwargs):
        return FetchResult(
            data=data,
            source=DataSource(source),
            fetch_time=datetime(2023, 1, 1),
            records_count=len(data),
            **kwargs,
        )

    stations = [SimpleNamespace(station_id="fixture", latitude=28.5, longitude=-88.5)]
    observations = [
        SimpleNamespace(
            observation_time=datetime(2023, 1, 1),
            forecast_time=datetime(2023, 1, 1),
            wave_height_m=2.0,
            speed_ms=2.0,
            water_level_m=4.0,
        )
    ]
    discovery = method == "fetch_stations"
    payload = stations if discovery else observations
    client = UnifiedMetoceanClient(
        source_fetchers={"era5": lambda q: rows("era5")},
        erddap_dataset="fixture",
        erddap_bbox=(-89.0, -88.0, 28.0, 29.0),
    )
    with patch(
        f"worldenergydata.metocean.clients.{source}_client.{classes[source]}"
    ) as factory:
        api = factory.return_value.__enter__.return_value
        api.fetch_stations.return_value = native_result(stations)
        api.fetch_historical.return_value = native_result(observations)
        api.fetch_currents.return_value = native_result(observations)
        getattr(api, method).return_value = native_result(
            payload if has_rows else [],
            had_errors=had_errors,
            error_messages=error_messages,
        )
        with (
            patch.object(
                client._coverage, "get_clients", return_value=[source, "era5"]
            ),
            patch(
                "worldenergydata.metocean.unified.unified_query._nearest_station",
                wraps=_nearest_station,
            ) as nearest,
        ):
            product = (
                "water_level" if method == "fetch_water_level" else "current_speed"
            )
            result = client.query(query(parameters=("Hs", product)))
        getattr(api, method).assert_called_once()
        if discovery and (had_errors or error_messages):
            nearest.assert_not_called()
            api.fetch_historical.assert_not_called()
            api.fetch_currents.assert_not_called()

    expected = (
        "FAILED" if had_errors or error_messages else "OK" if has_rows else "EMPTY"
    )
    assert result.source_status == {source: expected, "era5": "OK"}
    native_rows = result.data[result.data.source == source]
    assert native_rows.empty == (expected != "OK")
    assert result.sources_used == sorted(
        ["era5", source] if expected == "OK" else ["era5"]
    )
    assert result.data[result.data.source == "era5"].value.tolist() == [2.0, 4.0, 6.0]
    if expected == "FAILED":
        assert f"Source {source} failed" in caplog.messages
    assert "upstream diagnostic withheld" not in caplog.text
    assert "upstream diagnostic withheld" not in repr(result)


def test_historical_cli_retains_delegation_and_defaults():
    from worldenergydata.metocean.cli import app
    from worldenergydata.metocean.cli_utils import SourceChoice

    with patch("worldenergydata.metocean.cli.historical_command") as command:
        result = CliRunner().invoke(
            app, ["historical", "fixture", "2023-01-01", "2023-01-02"]
        )
    assert result.exit_code == 0, result.output
    command.assert_called_once_with(
        "fixture", "2023-01-01", "2023-01-02", SourceChoice.ndbc, None, False
    )
