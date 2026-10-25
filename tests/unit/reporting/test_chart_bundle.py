"""Chart-bundle contract tests using an independent, synthetic table.

All data below are hand-specified test inputs, not engineering observations.
The oracle is: period | primary | secondary
                 first  | 1.25    | 0
                 second | missing | 3.75
                 third  | -2.5    | 5
The optional marker cites the secondary value in the second row; it is not
a regulatory limit. The digest is SHA-256 of ASCII 'abc' (RFC 6234, B.1).
"""

from __future__ import annotations

import csv
import importlib
import json
from dataclasses import asdict, replace

import pytest


@pytest.fixture
def api():
    # A missing module fails each test during the initial test-first run.
    return importlib.import_module("worldenergydata.reporting.chart_bundle")


@pytest.fixture
def payload():
    return {
        "chart_id": "synthetic-energy",
        "headline": "Synthetic energy by period",
        "quantity": "Energy",
        "unit": "MWh",
        "x_variable": "period",
        "x_values": ["first", "second", "third"],
        "series": [
            {"name": "primary", "values": [1.25, None, -2.5]},
            {"name": "secondary", "values": [0, 3.75, 5]},
        ],
        "source": {
            "name": "Synthetic table in test_chart_bundle.py",
            "url": "https://example.org/synthetic-chart",
            "date": "2026-01-01",
        },
        "retrieved_at": "2026-01-02T12:00:00Z",
        "input_sha256": (
            "ba7816bf8f01cfea414140de5dae2223" "b00361a396177a9cb410ff61f20015ad"
        ),
        "limits": [],
        "csv_name": "synthetic-energy.csv",
        "missing_values": "null",
    }


def _write_unchecked(tmp_path, payload, rows=None):
    """Create independent files, so validator tests cannot trust the writer."""
    json_path = tmp_path / "chart.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    if rows is None:
        rows = [
            ["period", "primary", "secondary"],
            ["first", "1.25", "0"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
        ]
    with (tmp_path / "synthetic-energy.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        csv.writer(stream).writerows(rows)
    return json_path


def test_chart_bundle_round_trip(api, payload, tmp_path):
    chart = api.ChartBundle.from_dict(payload)
    assert isinstance(chart.source, api.ChartSource)
    assert all(isinstance(series, api.ChartSeries) for series in chart.series)
    json_path, csv_path = api.write_chart_bundle(chart, tmp_path / "chart.json")

    # Literal expectations are independent of the serialization implementation.
    result = json.loads(json_path.read_text(encoding="utf-8"))
    assert result == payload
    assert result["series"] == [
        {"name": "primary", "values": [1.25, None, -2.5]},
        {"name": "secondary", "values": [0, 3.75, 5]},
    ]
    assert result["missing_values"] == "null"
    with csv_path.open(encoding="utf-8", newline="") as stream:
        assert list(csv.reader(stream)) == [
            ["period", "primary", "secondary"],
            ["first", "1.25", "0"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
        ]
    validated = api.validate_chart_bundle(json_path)
    assert asdict(validated) == asdict(chart)


@pytest.mark.parametrize(
    "field,value",
    [
        ("chart_id", ""),
        ("headline", " \t"),
        ("quantity", None),
        ("unit", ""),
        ("x_variable", " "),
        ("source", None),
        ("source.name", " "),
        ("source.url", ""),
        ("source.url", "not a URL"),
        ("source.date", ""),
        ("source.date", "2026"),
        ("source.date", "2026-02-30"),
        ("source.date", "20260101"),
        ("retrieved_at", "2026-01-02T12:00:00"),
        ("retrieved_at", "2026-01-02T12:00:00+01:00"),
        ("retrieved_at", "2026-01-02"),
        ("retrieved_at", "2026-02-30T12:00:00Z"),
        ("input_sha256", ""),
        ("input_sha256", "abc"),
        ("input_sha256", "g" * 64),  # SHA-256: 64 hexadecimal digits.
        ("input_sha256", "a" * 63),
        ("input_sha256", "a" * 65),
        ("csv_name", ""),
        ("csv_name", "../outside.csv"),
        ("csv_name", "folder\\outside.csv"),
        ("csv_name", "/outside.csv"),
        ("csv_name", "chart.json"),
        ("missing_values", "NaN"),
    ],
)
def test_chart_bundle_rejects_missing_provenance(api, payload, tmp_path, field, value):
    if "." in field:
        parent, child = field.split(".")
        payload[parent][child] = value
    else:
        payload[field] = value
    # Both public entry points must reject the same metadata.
    with pytest.raises(ValueError):
        api.ChartBundle.from_dict(payload)
    path = _write_unchecked(tmp_path, payload)
    with pytest.raises(ValueError):
        api.validate_chart_bundle(path)


@pytest.mark.parametrize("field", ["unit", "source", "retrieved_at", "missing_values"])
def test_chart_bundle_requires_declared_fields(api, payload, field):
    del payload[field]
    with pytest.raises(ValueError):
        api.ChartBundle.from_dict(payload)


@pytest.mark.parametrize(
    "rows",
    [
        [
            ["period", "primary", "secondary"],
            ["first", "9", "0"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
        ],
        [
            ["period", "primary", "secondary"],
            ["wrong", "1.25", "0"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
        ],
        [
            ["period", "primary", "secondary"],
            ["first", "1.25", "0"],
            ["second", "0", "3.75"],
            ["third", "-2.5", "5"],
        ],
        [
            ["period", "primary", "secondary"],
            ["first", "", "0"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
        ],
        [
            ["period", "primary", "secondary"],
            ["first", "1.25", "0"],
            ["second", "", "3.75"],
        ],
        [
            ["period", "primary", "secondary"],
            ["first", "1.25", "0"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
            ["extra", "1", "1"],
        ],
        [
            ["period", "primary", "primary"],
            ["first", "1.25", "0"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
        ],
        [
            ["period", "primary", "secondary"],
            ["first", "1.25"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
        ],
        [
            ["period", "primary", "secondary"],
            ["first", "1.25", "0", "extra"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
        ],
        [
            ["period", "primary", "secondary"],
            ["first", "NaN", "0"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
        ],
        [
            ["period", "primary", "secondary"],
            ["first", "inf", "0"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
        ],
        [],
    ],
)
def test_chart_bundle_rejects_csv_mismatch(api, payload, tmp_path, rows):
    path = _write_unchecked(tmp_path, payload, rows)
    with pytest.raises(ValueError):
        api.validate_chart_bundle(path)
    # Replacing corrupted CSV with the independent oracle restores validity.
    _write_unchecked(tmp_path, payload)
    assert api.validate_chart_bundle(path).chart_id == "synthetic-energy"


@pytest.mark.parametrize("values", [[1.25], [], [1.25, None, -2.5, 0]])
def test_chart_bundle_rejects_series_length(api, payload, values):
    payload["series"][0]["values"] = values
    with pytest.raises(ValueError):
        api.ChartBundle.from_dict(payload)


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), -float("inf"), True, "1"]
)
@pytest.mark.parametrize("location", ["series", "x", "limit"])
def test_chart_bundle_rejects_invalid_numbers(api, payload, value, location):
    if location == "series":
        payload["series"][0]["values"][0] = value
    elif location == "x":
        # Strings are legitimate categorical x values; blank strings are not.
        payload["x_values"][0] = " " if isinstance(value, str) else value
    else:
        payload["limits"] = [
            {
                "label": "Fixture marker",
                "value": value,
                "citation": "Synthetic oracle table, secondary, second row",
            }
        ]
    with pytest.raises(ValueError):
        api.ChartBundle.from_dict(payload)


@pytest.mark.parametrize("citation", [None, "", " \t"])
def test_chart_bundle_rejects_uncited_limit(api, payload, citation):
    payload["limits"] = [
        {
            "label": "Fixture marker",
            "value": 3.75,
            "citation": "Synthetic oracle table, secondary, second row",
        },
        {"label": "Uncited marker", "value": 0, "citation": citation},
    ]
    with pytest.raises(ValueError):
        api.ChartBundle.from_dict(payload)


def test_chart_bundle_retains_each_limit_citation(api, payload, tmp_path):
    payload["limits"] = [
        {
            "label": "Fixture marker",
            "value": 3.75,
            "citation": "Synthetic oracle table, secondary, second row",
        }
    ]
    chart = api.ChartBundle.from_dict(payload)
    path, _ = api.write_chart_bundle(chart, tmp_path / "chart.json")
    assert api.validate_chart_bundle(path).limits == (
        api.DrawnLimit(
            "Fixture marker", 3.75, "Synthetic oracle table, secondary, second row"
        ),
    )


def test_chart_bundle_validates_before_touching_outputs(api, payload, tmp_path):
    chart = api.ChartBundle.from_dict(payload)
    path, csv_path = api.write_chart_bundle(chart, tmp_path / "chart.json")
    original = (path.read_bytes(), csv_path.read_bytes())
    # Direct dataclass construction must not bypass writer validation.
    invalid = replace(chart, unit="")
    with pytest.raises(ValueError):
        api.write_chart_bundle(invalid, path)
    assert (path.read_bytes(), csv_path.read_bytes()) == original
    new_path = tmp_path / "new" / "chart.json"
    with pytest.raises(ValueError):
        api.write_chart_bundle(invalid, new_path)
    assert not new_path.parent.exists()


@pytest.mark.parametrize("mutation", ["duplicate", "collision", "empty", "unknown"])
def test_chart_bundle_rejects_ambiguous_schema(api, payload, mutation):
    if mutation == "duplicate":
        payload["series"][1]["name"] = "primary"
    elif mutation == "collision":
        payload["series"][0]["name"] = "period"
    elif mutation == "empty":
        payload["series"] = []
    else:
        payload["unexpected"] = "not part of the schema"
    with pytest.raises(ValueError):
        api.ChartBundle.from_dict(payload)


def test_chart_bundle_numeric_x_and_missing_x(api, payload, tmp_path):
    # Hand-specified x values exercise numeric comparison and missing x cells.
    payload["x_values"] = [0, None, 1.25]
    path, csv_path = api.write_chart_bundle(
        api.ChartBundle.from_dict(payload), tmp_path / "chart.json"
    )
    assert csv_path.read_text(encoding="utf-8").splitlines() == [
        "period,primary,secondary",
        "0,1.25,0",
        ",,3.75",
        "1.25,-2.5,5",
    ]
    assert api.validate_chart_bundle(path).x_values == (0, None, 1.25)


def test_chart_bundle_compares_numbers_without_float_rounding(api, payload, tmp_path):
    # Hand calculation: 2**53 + 1 and 2**53 differ by exactly one.
    payload["series"][0]["values"][0] = 9007199254740993
    path = _write_unchecked(
        tmp_path,
        payload,
        [
            ["period", "primary", "secondary"],
            ["first", "9007199254740992", "0"],
            ["second", "", "3.75"],
            ["third", "-2.5", "5"],
        ],
    )
    with pytest.raises(ValueError):
        api.validate_chart_bundle(path)


def test_chart_bundle_accepts_explicit_utc_offset(api, payload, tmp_path):
    payload["retrieved_at"] = "2026-01-02T12:00:00+00:00"
    path = _write_unchecked(tmp_path, payload)
    assert api.validate_chart_bundle(path).retrieved_at.endswith("+00:00")


def test_chart_bundle_requires_csv_file(api, payload, tmp_path):
    path = tmp_path / "chart.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="CSV"):
        api.validate_chart_bundle(path)


def test_chart_bundle_rejects_json_precision_mismatch(api, payload, tmp_path):
    path = _write_unchecked(tmp_path, payload)
    # Hand calculation: 1.25000000000000001 differs from 1.25 by 0.00000000000000001.
    path.write_text(
        path.read_text(encoding="utf-8").replace("1.25", "1.25000000000000001"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        api.validate_chart_bundle(path)


def test_chart_bundle_rejects_duplicate_json_fields(api, payload, tmp_path):
    path = _write_unchecked(tmp_path, payload)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            '"unit": "MWh"', '"unit": "wrong", "unit": "MWh"'
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate"):
        api.validate_chart_bundle(path)


def test_chart_bundle_rejects_numeric_x_mismatch(api, payload, tmp_path):
    payload["x_values"] = [0, None, 1.25]
    path = _write_unchecked(
        tmp_path,
        payload,
        [
            ["period", "primary", "secondary"],
            ["0", "1.25", "0"],
            ["", "", "3.75"],
            ["3.75", "-2.5", "5"],
        ],
    )
    with pytest.raises(ValueError):
        api.validate_chart_bundle(path)


def test_chart_bundle_validates_last_limit_before_writing(api, payload, tmp_path):
    chart = api.ChartBundle.from_dict(payload)
    invalid = replace(
        chart,
        limits=(
            api.DrawnLimit(
                "Fixture marker", 3.75, "Synthetic oracle table, secondary, second row"
            ),
            api.DrawnLimit("Missing citation", 0, ""),
        ),
    )
    with pytest.raises(ValueError):
        api.write_chart_bundle(invalid, tmp_path / "chart.json")
    assert list(tmp_path.iterdir()) == []


def test_chart_bundle_accepts_equivalent_numeric_csv_spelling(api, payload, tmp_path):
    path = _write_unchecked(
        tmp_path,
        payload,
        [
            ["period", "primary", "secondary"],
            ["first", "1.250", "0.0"],
            ["second", "", "3.75e0"],
            ["third", "-2.50", "5.0"],
        ],
    )
    assert api.validate_chart_bundle(path).chart_id == "synthetic-energy"
