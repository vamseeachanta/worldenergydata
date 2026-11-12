"""Scope checks against invented benchmarks; no values are engineering inputs."""

import csv
import importlib
import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from typer.testing import CliRunner
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[3]
COLUMNS = (
    "metric unit water_depth_band region development_type host_type n "
    "p10 p50 p90 indicative_only comparables cost_basis"
).split()


def invented_row(**changes):
    row = dict(
        metric="capex_per_well",
        unit="USD_MM_2026/well",
        water_depth_band="deep",
        region="invented_region",
        development_type="subsea",
        host_type="floating",
        n=5,
        p10=10,
        p50=20,
        p90=30,
        indicative_only="false",
        comparables="invented-a;invented-b;invented-c;invented-d;invented-e",
        cost_basis="USD_2026",
    )
    return row | changes


@pytest.fixture
def table(tmp_path):
    def write(*rows):
        path = tmp_path / "invented-benchmarks.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows or [invented_row()])
        return path

    return write


@pytest.fixture
def scope():
    return dict(
        wells=2,
        water_depth_m=1500,
        region="invented_region",
        development_type="subsea",
        host_type="floating",
        invented=True,
    )


def check(scope, path):
    module = importlib.import_module("worldenergydata.cost.scope_check")
    return module.check_scope(scope, path)


def test_exact_match_scales_whole_project_intensity_in_usd(table, scope):
    result = check(scope, table())
    interval = result["range"]["capex_per_well"]
    assert (interval["p10"], interval["p50"], interval["p90"]) == (
        20_000_000,
        40_000_000,
        60_000_000,
    )
    assert interval["unit"] == "USD"
    assert interval["benchmark_unit"] == "USD_MM_2026/well"
    assert interval["quantity"] == 2
    assert interval["n"] == 5
    assert (
        interval["comparables"]
        == result["comparables"]
        == ["invented-a", "invented-b", "invented-c", "invented-d", "invented-e"]
    )
    assert result["matched_group"]["capex_per_well"]["dropped_keys"] == []
    assert result["cost_basis"] == "USD_2026"
    assert result["indicative_only"] is False
    assert result["escalation_basis"]["conversion_applied"] is False
    assert result["escalation_basis"]["index"] is None
    assert "not supplied" in result["escalation_basis"]["limitation"]


@pytest.mark.parametrize("key", ["region", "development_type"])
def test_fallback_names_every_dropped_key(table, scope, key):
    result = check(scope | {key: "different"}, table())
    group = result["matched_group"]["capex_per_well"]
    assert group["dropped_keys"] == [key]
    assert group[key] == scope[key]
    assert result["indicative_only"] is True


def test_fallback_does_not_pool_ambiguous_group_percentiles(table, scope):
    path = table(invented_row(), invented_row(region="other_region", p50=25))
    result = check(scope | {"region": "unmatched"}, path)
    assert result["range"] is None
    assert result["reason"] == "no close comparables"
    assert "ambiguous" in " ".join(result["limitations"])


@pytest.mark.parametrize(
    "change",
    [{"water_depth_m": 20}, {"host_type": "fixed"}],
)
def test_depth_and_host_never_widen(table, scope, change):
    result = check(scope | change | {"quote": 25_000_000}, table())
    assert result["range"] is None
    assert result["reason"] == "no close comparables"
    assert result["comparables"] == []
    assert result["matched_group"] == {}
    assert result["cost_basis"] is None
    assert result["quote_position"] is None
    assert result["escalation_basis"]["conversion_applied"] is False


def test_zero_sample_rows_do_not_make_a_range(table, scope):
    result = check(scope, table(invented_row(n=0, comparables="")))
    assert result["range"] is None
    assert result["reason"] == "no close comparables"


@pytest.mark.parametrize(
    "quote,position",
    [
        (19_999_999, "below p10"),
        (20_000_000, "p10-p50"),
        (20_000_001, "p10-p50"),
        (39_999_999, "p10-p50"),
        (40_000_000, "p50-p90"),
        (40_000_001, "p50-p90"),
        (59_999_999, "p50-p90"),
        (60_000_000, "p50-p90"),
        (60_000_001, "above p90"),
    ],
)
def test_quote_boundaries(table, scope, quote, position):
    result = check(scope | {"quote": quote}, table())
    assert result["quote_position"] == {"capex_per_well": position}


def test_nominal_basis_is_retained_and_never_escalated(table, scope):
    path = table(invented_row(cost_basis="nominal", unit="USD_MM/well"))
    result = check(scope, path)
    assert result["cost_basis"] == "nominal"
    assert result["escalation_basis"]["conversion_applied"] is False
    assert "nominal" in result["escalation_basis"]["limitation"]
    with pytest.raises(ValueError, match="quote cost basis"):
        check(scope | {"quote": 40_000_000}, path)
    matched = check(scope | {"quote": 40_000_000, "quote_cost_basis": "nominal"}, path)
    assert matched["quote_position"] == {"capex_per_well": "p50-p90"}


def test_metrics_are_alternative_estimates_and_never_added(table, scope):
    path = table(
        invented_row(),
        invented_row(metric="capex_per_tree", unit="USD_MM_2026/tree"),
    )
    result = check(scope | {"trees": 3, "manifolds": 1}, path)
    assert set(result["range"]) == {"capex_per_well", "capex_per_tree"}
    assert result["range"]["capex_per_tree"]["p50"] == 60_000_000
    assert "total" not in result
    assert (
        result["method"]
        == "per-metric alternative project CAPEX ranges; no aggregation"
    )
    assert "manifolds" in result["unbenchmarked_elements"]


@pytest.mark.parametrize(
    "quantity,metric,unit,value,expected",
    [
        ("surf_km", "capex_per_surf_km", "USD_MM_2026/km", 3, 60_000_000),
        (
            "peak_production_kboed",
            "capex_per_kboed",
            "USD_MM_2026/kboe/d",
            4,
            80_000_000,
        ),
        ("recoverable_resource_boe", "capex_per_boe", "USD_2026/boe", 100, 2_000),
    ],
)
def test_denominators_and_million_scaling(
    table, scope, quantity, metric, unit, value, expected
):
    result = check(
        scope | {quantity: value}, table(invented_row(metric=metric, unit=unit))
    )
    assert result["range"][metric]["p50"] == expected
    assert "wells" in result["unbenchmarked_elements"]


@pytest.mark.parametrize(
    "depth,band",
    [
        (0, "shallow"),
        (300, "shallow"),
        (301, "mid"),
        (1000, "mid"),
        (1001, "deep"),
        (2000, "deep"),
        (2001, "ultra_deep"),
    ],
)
def test_depth_bands_follow_benchmark_contract(table, scope, depth, band):
    result = check(
        scope | {"water_depth_m": depth}, table(invented_row(water_depth_band=band))
    )
    assert result["matched_group"]["capex_per_well"]["water_depth_band"] == band


@pytest.mark.parametrize(
    "change",
    [
        {"wells": -1},
        {"wells": True},
        {"wells": 1.5},
        {"water_depth_m": float("nan")},
        {"quote": float("inf")},
        {"quote": -1},
        {"host_type": ""},
        {"typo": 1},
        {"water_depth_band": "shallow"},
        {"award_year": "2020"},
    ],
)
def test_invalid_scope_is_rejected(table, scope, change):
    with pytest.raises(ValueError):
        check(scope | change, table())


@pytest.mark.parametrize(
    "change",
    [
        {"p10": -1},
        {"p50": "NaN"},
        {"p90": 15},
        {"n": "1.5"},
        {"cost_basis": "EUR_2026"},
        {"unit": "USD_2026/boe"},
        {"indicative_only": "perhaps"},
        {"comparables": ""},
    ],
)
def test_invalid_benchmark_is_rejected(table, scope, change):
    with pytest.raises(ValueError):
        check(scope, table(invented_row(**change)))


def test_duplicate_groups_are_rejected_instead_of_chosen_by_row_order(table, scope):
    with pytest.raises(ValueError, match="duplicate"):
        check(scope, table(invented_row(), invented_row(p50=21)))


def test_missing_table_is_explicit_and_no_fixture_is_used(scope, tmp_path):
    with pytest.raises(FileNotFoundError, match="benchmark table is absent"):
        check(scope, tmp_path / "absent.csv")


def test_schema_and_invented_demo_are_shipped(table):
    demo = json.loads((ROOT / "examples/cost_check_invented_scope.json").read_text())
    assert demo["invented"] is True
    schema = json.loads(
        (ROOT / "docs/modules/cost/scope_check_input.schema.json").read_text()
    )
    assert schema["additionalProperties"] is False
    assert "host_type" in schema["required"]
    output_schema = json.loads(
        (ROOT / "docs/modules/cost/scope_check_output.schema.json").read_text()
    )
    result = check(demo, table())
    assert set(output_schema["required"]) <= result.keys()


def test_cli_prints_only_result_json(table, scope, tmp_path):
    from worldenergydata.cli.main import app

    scope_file = tmp_path / "invented-scope.json"
    scope_file.write_text(json.dumps(scope))
    result = CliRunner().invoke(
        app, ["cost-check", str(scope_file), "--benchmarks", str(table())]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["range"]["capex_per_well"]["p50"] == 40_000_000


def test_cli_missing_table_and_malformed_scope_are_json_errors(scope, tmp_path):
    from worldenergydata.cli.main import app

    scope_file = tmp_path / "invented-scope.json"
    scope_file.write_text(json.dumps(scope))
    result = CliRunner().invoke(
        app,
        ["cost-check", str(scope_file), "--benchmarks", str(tmp_path / "absent.csv")],
    )
    assert result.exit_code != 0
    assert "benchmark table is absent" in json.loads(result.stdout)["error"]
    scope_file.write_text("{")
    result = CliRunner().invoke(app, ["cost-check", str(scope_file)])
    assert result.exit_code != 0
    assert "JSON" in json.loads(result.stdout)["error"]


@pytest.mark.parametrize(
    "payload,status",
    [(None, 200), (b"{", 400), (b"[]", 400), (b"x" * 65537, 413)],
    ids=["success", "malformed", "non-object", "too-large"],
)
def test_http_round_trip_uses_ephemeral_loopback_port(table, scope, payload, status):
    from worldenergydata.cost.scope_check_http import create_app

    server = make_server("127.0.0.1", 0, create_app(table()))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        body = json.dumps(scope).encode() if payload is None else payload
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/cost-check",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            assert response.code == status
            result = json.load(response)
        if status == 200:
            assert result["range"]["capex_per_well"]["p50"] == 40_000_000
        else:
            assert result["error"]
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()
