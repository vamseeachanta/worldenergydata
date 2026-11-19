"""Regression cases use invented data only; no engineering inputs."""

import csv
import json
from hashlib import sha256

import pytest
from typer.testing import CliRunner

from . import test_scope_check as fixtures
from .test_scope_check import COLUMNS, ROOT, check, invented_row

scope = fixtures.scope
table = fixtures.table


@pytest.fixture(params=["duplicate", "stripped-duplicate", "csv-error"])
def corrupt_table(request, tmp_path):
    path = tmp_path / "invented-corrupt.csv"
    row = invented_row()
    columns = list(COLUMNS)
    values = [row[key] for key in columns]
    if request.param == "csv-error":
        values[columns.index("comparables")] = "x" * (csv.field_size_limit() + 1)
        message = "benchmark CSV"
    else:
        columns.append(" p50 " if request.param == "stripped-duplicate" else "p50")
        values.append(29)
        message = "duplicate benchmark columns"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(columns)
        writer.writerow(values)
    return path, message


def test_corrupt_csv_is_a_python_validation_error(corrupt_table, scope):
    path, message = corrupt_table
    with pytest.raises(ValueError, match=message):
        check(scope, path)


def test_corrupt_csv_is_a_cli_json_error(corrupt_table, scope, tmp_path):
    from worldenergydata.cli.main import app

    path, message = corrupt_table
    scope_file = tmp_path / "invented-scope.json"
    scope_file.write_text(json.dumps(scope), encoding="utf-8", newline="\n")
    result = CliRunner().invoke(
        app, ["cost-check", scope_file.as_posix(), "--benchmarks", path.as_posix()]
    )
    assert result.exit_code == 1
    assert message in json.loads(result.stdout)["error"]


def test_corrupt_csv_is_an_http_json_error(corrupt_table, scope):
    pytest.importorskip("flask")
    from worldenergydata.cost.scope_check_http import create_app

    path, message = corrupt_table
    response = create_app(path).test_client().post("/api/cost-check", json=scope)
    assert response.status_code == 400
    assert message in response.get_json()["error"]


@pytest.mark.parametrize("key", ["region", "development_type"])
@pytest.mark.parametrize("omitted", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_excluded_sampled_row_still_competes_at_selected_stage(
    table, scope, key, omitted, reverse
):
    rows = [
        invented_row(**{key: "other"}),
        invented_row(**{key: "unknown"}, p50=200, p90=300),
    ]
    if omitted:
        scope = {name: value for name, value in scope.items() if name != key}
    result = check(scope, table(*reversed(rows) if reverse else rows))
    assert result["range"] is None
    assert result["reason"] == "ambiguous comparable groups"
    assert result["comparables"] == []
    assert result["matched_group"] == {}
    assert any(
        "capex_per_well: ambiguous comparable groups; 2 groups at 1 dropped" in item
        for item in result["limitations"]
    )
    validate_output(result)


def validate_output(result):
    from jsonschema import Draft202012Validator

    schema = json.loads(
        (ROOT / "docs/modules/cost/scope_check_output.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)


def test_ambiguity_reason_is_distinct_from_no_matching_group(table, scope):
    path = table(invented_row(region="other"), invented_row(region="another"))
    ambiguous = check(scope, path)
    missing = check(scope | {"water_depth_m": 20}, path)
    assert ambiguous["reason"] == "ambiguous comparable groups"
    assert missing["reason"] == "no close comparables"
    validate_output(ambiguous)
    validate_output(missing)


@pytest.mark.parametrize("key", ["region", "development_type"])
@pytest.mark.parametrize("reverse", [False, True])
def test_excluded_row_competes_across_equal_distance_relaxations(
    table, scope, key, reverse
):
    other_key = "development_type" if key == "region" else "region"
    rows = [invented_row(**{key: "other"}), invented_row(**{other_key: "unknown"})]
    result = check(scope, table(*reversed(rows) if reverse else rows))
    assert result["range"] is None
    assert result["reason"] == "ambiguous comparable groups"
    validate_output(result)


@pytest.mark.parametrize("with_wider_group", [False, True])
def test_excluded_singleton_never_supplies_a_range(table, scope, with_wider_group):
    rows = [
        invented_row(region="unknown"),
        invented_row(metric="capex_per_tree", unit="USD_MM_2026/tree"),
    ]
    if with_wider_group:
        rows.append(invented_row(region="other", development_type="other"))
    path = table(*rows)
    result = check(scope, path)
    assert result["range"] is None
    assert result["reason"] == "no close comparables"
    assert result["comparables"] == []
    assert result["unbenchmarked_elements"] == ["wells"]
    assert (
        "capex_per_well: nearest group has an unknown grouping label; "
        "wider stages were not considered." in result["limitations"]
    )
    assert result["benchmark_sha256"] == sha256(path.read_bytes()).hexdigest()
    validate_output(result)


def test_placeholder_ambiguity_preserves_a_unique_alternative(table, scope):
    result = check(
        scope | {"trees": 3},
        table(
            invented_row(region="other"),
            invented_row(region="unknown"),
            invented_row(metric="capex_per_tree", unit="USD_MM_2026/tree"),
        ),
    )
    assert set(result["range"]) == {"capex_per_tree"}
    assert result["unbenchmarked_elements"] == ["wells"]
    assert result["indicative_only"] is True
    assert any("capex_per_well: ambiguous" in item for item in result["limitations"])
    validate_output(result)


def test_unrelated_excluded_row_does_not_make_exact_match_indicative(table, scope):
    result = check(
        scope,
        table(
            invented_row(),
            invented_row(
                region="unknown",
                host_type="fixed",
                metric="capex_per_tree",
                unit="USD_MM_2026/tree",
            ),
        ),
    )
    assert result["indicative_only"] is False
    assert result["range"]["capex_per_well"]["p50"] == 40_000_000


@pytest.mark.parametrize(
    "change,message",
    [
        ({"water_depth_band": "abyssal"}, "water_depth_band"),
        ({"cost_basis": "EUR"}, "cost_basis"),
        ({"unit": "x"}, "unit"),
        ({"indicative_only": "perhaps"}, "indicative_only"),
        ({"comparables": "invented-a"}, "comparables"),
        ({"p10": -1}, "percentiles"),
        ({"p50": "NaN"}, "percentiles"),
        ({"p90": 15}, "percentiles"),
    ],
)
def test_zero_sample_row_metadata_is_validated(table, scope, change, message):
    empty = invented_row(n=0, comparables="", region="other") | change
    with pytest.raises(ValueError, match=message):
        check(scope, table(invented_row(), empty))


def test_zero_sample_duplicates_are_rejected(table, scope):
    empty = invented_row(n=0, comparables="", region="other")
    with pytest.raises(ValueError, match="duplicate benchmark group"):
        check(scope, table(invented_row(), empty, empty))


def test_zero_sample_row_may_omit_the_entire_percentile_triplet(table, scope):
    empty = invented_row(n=0, comparables="", region="other", p10="", p50="", p90="")
    result = check(scope, table(invented_row(), empty))
    assert result["range"]["capex_per_well"]["p50"] == 40_000_000
    assert result["indicative_only"] is False


def test_zero_sample_row_cannot_supply_a_partial_percentile_triplet(table, scope):
    empty = invented_row(n=0, comparables="", region="other", p50="")
    with pytest.raises(ValueError, match="percentiles"):
        check(scope, table(invented_row(), empty))


@pytest.mark.parametrize("count", ["5_0", "+50", "5\u0660"])
def test_sample_count_requires_ascii_decimal_digits(table, scope, count):
    ids = ";".join(f"invented-{index}" for index in range(50))
    with pytest.raises(ValueError, match="benchmark n"):
        check(scope, table(invented_row(n=count, comparables=ids)))


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"])
def test_recorded_digest_matches_binary_table_bytes(table, scope, newline, bom):
    path = table()
    path.write_bytes(bom + path.read_bytes().replace(b"\n", newline))
    result = check(scope, path)
    with path.open("rb") as stream:
        assert result["benchmark_sha256"] == sha256(stream.read()).hexdigest()
