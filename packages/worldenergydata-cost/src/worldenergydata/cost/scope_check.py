"""Compare fixed scopes with supplied project CAPEX intensities, without pooling."""

from __future__ import annotations

import csv
import io
import json
from hashlib import sha256
from itertools import combinations
from math import isfinite
from pathlib import Path

DEFAULT_BENCHMARKS = Path("reports/cost/unit_cost_benchmarks.csv")
GROUP_KEYS = ("water_depth_band", "region", "development_type", "host_type")
DEPTH_BANDS = {"shallow", "mid", "deep", "ultra_deep"}
# These denominators describe alternative whole-project estimates, not elements.
METRICS = {
    "capex_per_well": ("wells", "well"),
    "capex_per_tree": ("trees", "tree"),
    "capex_per_surf_km": ("surf_km", "km"),
    "capex_per_kboed": ("peak_production_kboed", "kboe/d"),
    "capex_per_boe": ("recoverable_resource_boe", "boe"),
}
UNSUPPORTED = ("manifolds", "umbilical_km", "risers")
COUNTS = ("wells", "trees", "manifolds", "risers")
QUANTITIES = tuple(value[0] for value in METRICS.values()) + UNSUPPORTED
METHOD = "per-metric alternative project CAPEX ranges; no aggregation"


def _number(value, name, *, integer=False):
    try:
        finite = isinstance(value, (int, float)) and isfinite(value)
    except OverflowError:
        finite = False
    if (
        isinstance(value, bool)
        or not finite
        or value < 0
        or (integer and value != int(value))
    ):
        raise ValueError(
            f"{name} must be a finite nonnegative number"
            + (" with no fractional part" if integer else "")
        )
    return value


def _scope_group(scope):
    if not isinstance(scope, dict):
        raise ValueError("scope must be a JSON object")
    allowed = set(GROUP_KEYS + QUANTITIES) | {
        "water_depth_m",
        "award_year",
        "fid_year",
        "quote",
        "quote_cost_basis",
        "invented",
    }
    if set(scope) - allowed:
        raise ValueError("scope contains unsupported keys; see the input schema")
    for key in GROUP_KEYS:
        if key in scope and (not isinstance(scope[key], str) or not scope[key].strip()):
            raise ValueError(f"{key} must be a nonempty string")
    if "host_type" not in scope:
        raise ValueError("host_type is required")
    group = {key: scope[key].strip() for key in GROUP_KEYS if key in scope}
    for key, label in group.items():
        if label.casefold() == "unknown":
            raise ValueError(f"{key} must match a known benchmark label")
    if "water_depth_m" in scope:
        depth = _number(scope["water_depth_m"], "water_depth_m")
        # Table convention: data_collection.calibration_schema.WaterDepthBand.
        # The consumer assigns each shared boundary to the shallower band.
        band = next(
            (
                band
                for ceiling, band in ((300, "shallow"), (1000, "mid"), (2000, "deep"))
                if depth <= ceiling
            ),
            "ultra_deep",
        )
        if "water_depth_band" in group and group["water_depth_band"] != band:
            raise ValueError("water_depth_band disagrees with water_depth_m")
        group["water_depth_band"] = band
    if group.get("water_depth_band") not in DEPTH_BANDS:
        raise ValueError("water_depth_m or a valid water_depth_band is required")
    for key in QUANTITIES:
        if key in scope:
            _number(scope[key], key, integer=key in COUNTS)
    if not any(scope.get(quantity, 0) > 0 for quantity, _unit in METRICS.values()):
        raise ValueError("at least one positive benchmarkable quantity is required")
    if "quote" in scope:
        _number(scope["quote"], "quote")
    if scope.get("quote_cost_basis", "USD_2026") not in ("USD_2026", "nominal"):
        raise ValueError("quote cost basis must be USD_2026 or nominal")
    for key in ("award_year", "fid_year"):
        if key in scope:
            year = _number(scope[key], key, integer=True)
            if not 1900 <= year <= 2200:
                raise ValueError(f"{key} must be between 1900 and 2200")
    if "invented" in scope and not isinstance(scope["invented"], bool):
        raise ValueError("invented must be boolean")
    return group


def load_scope_json(payload):
    """Decode JSON without accepting duplicate keys or non-finite extensions."""

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(_value):
        raise ValueError("JSON numbers must be finite")

    try:
        return json.loads(
            payload, object_pairs_hook=pairs, parse_constant=invalid_constant
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("scope must contain valid JSON") from error


def _load_table(path):
    try:
        content = Path(path).read_bytes()
    except FileNotFoundError:
        raise FileNotFoundError(
            "benchmark table is absent; supply the benchmark table path"
        ) from None
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    required = set(GROUP_KEYS) | {
        "metric",
        "unit",
        "n",
        "p10",
        "p50",
        "p90",
        "indicative_only",
        "comparables",
        "cost_basis",
    }
    if not required <= set(reader.fieldnames or ()):
        raise ValueError("benchmark table is missing required columns")
    rows, seen = [], set()
    excluded_unknown = 0
    for raw in reader:
        if any(value is None for value in raw.values()) or None in raw:
            raise ValueError("benchmark row has an invalid column count")
        row = {key: value.strip() for key, value in raw.items()}
        if row["metric"] not in METRICS:
            raise ValueError("benchmark row has an unsupported metric")
        if any(not row[key] for key in GROUP_KEYS):
            raise ValueError("benchmark grouping keys must be nonempty")
        try:
            count = int(row["n"])
        except ValueError:
            raise ValueError("benchmark n must be an integer") from None
        if count < 0:
            raise ValueError("benchmark n must be nonnegative")
        if count == 0:
            continue
        if (
            row["water_depth_band"] not in DEPTH_BANDS
            and row["water_depth_band"].casefold() != "unknown"
        ):
            raise ValueError("benchmark water_depth_band must use a defined band")
        row["n"] = count
        basis = row["cost_basis"]
        if basis not in {"USD_2026", "nominal"}:
            raise ValueError("benchmark cost_basis must be USD_2026 or nominal")
        denominator = METRICS[row["metric"]][1]
        currency = "USD_2026" if basis == "USD_2026" else "USD"
        million_currency = "USD_MM_2026" if basis == "USD_2026" else "USD_MM"
        if row["unit"] not in {
            f"{currency}/{denominator}",
            f"{million_currency}/{denominator}",
        }:
            raise ValueError("benchmark unit disagrees with metric or cost basis")
        row["usd_multiplier"] = 1_000_000 if row["unit"].startswith("USD_MM") else 1
        try:
            for key in ("p10", "p50", "p90"):
                row[key] = _number(float(row[key]), f"benchmark {key}")
        except (ValueError, OverflowError):
            raise ValueError(
                "benchmark percentiles must be finite and nonnegative"
            ) from None
        if not row["p10"] <= row["p50"] <= row["p90"]:
            raise ValueError("benchmark percentiles must be ordered p10 <= p50 <= p90")
        if row["indicative_only"].lower() not in {"true", "false"}:
            raise ValueError("benchmark indicative_only must be true or false")
        row["indicative_only"] = row["indicative_only"].lower() == "true" or count < 5
        ids = [
            value.strip() for value in row["comparables"].split(";") if value.strip()
        ]
        if len(ids) != count or len(set(ids)) != count:
            raise ValueError("benchmark comparables must contain n unique project ids")
        row["comparables"] = sorted(ids)
        identity = (row["metric"], *(row[key] for key in GROUP_KEYS))
        if identity in seen:
            raise ValueError("duplicate benchmark group")
        seen.add(identity)
        if any(row[key].casefold() == "unknown" for key in GROUP_KEYS):
            excluded_unknown += 1
            continue
        rows.append(row)
    if not rows:
        raise ValueError("benchmark table has no usable benchmark rows with n >= 1")
    return rows, sha256(content).hexdigest(), excluded_unknown


def _select(rows, metric, group):
    candidates = [
        row
        for row in rows
        if row["metric"] == metric
        and all(row[key] == group[key] for key in ("water_depth_band", "host_type"))
    ]
    optional = ("region", "development_type")
    missing = [key for key in optional if key not in group]
    supplied = [key for key in optional if key in group]
    for size in range(len(supplied) + 1):
        stage = {}
        for relaxed in combinations(supplied, size):
            dropped = missing + list(relaxed)
            for row in candidates:
                if all(key in dropped or row[key] == group[key] for key in optional):
                    identity = tuple(row[key] for key in GROUP_KEYS)
                    stage[identity] = (row, sorted(dropped))
        if len(stage) == 1:
            row, dropped = next(iter(stage.values()))
            return row, dropped, None
        if len(stage) > 1:
            return (
                None,
                [],
                f"{len(stage)} groups at {len(missing) + size} dropped optional keys",
            )
    return None, [], None


def _position(quote, interval):
    if quote < interval["p10"]:
        return "below p10"
    if quote < interval["p50"]:
        return "p10-p50"
    if quote <= interval["p90"]:
        return "p50-p90"
    return "above p90"


def check_scope(scope: dict, benchmark_path=DEFAULT_BENCHMARKS) -> dict:
    """Return per-metric alternative project CAPEX ranges in USD, or no range.

    Fixed scope quantities scale the supplied intensity quantiles. These are
    screening proxies, not component estimates or a calibrated joint prediction.
    Nominal input stays nominal. Escalation is never reconstructed or invented.
    """
    group = _scope_group(scope)
    rows, digest, excluded_unknown = _load_table(benchmark_path)
    if group["host_type"] not in {row["host_type"] for row in rows}:
        raise ValueError("host_type must match a known benchmark label in the table")
    result = {
        "range": None,
        "comparables": [],
        "cost_basis": None,
        "indicative_only": True,
        "matched_group": {},
        "method": METHOD,
        "benchmark_sha256": digest,
        "unbenchmarked_elements": [],
        "limitations": [
            "Project CAPEX intensities are alternative screening proxies; "
            "metrics overlap and cannot be added.",
            "No joint scope distribution, component allocation or scale calibration "
            "is established.",
            "Award and FID years are not matching keys in the benchmark table contract.",
        ],
        "escalation_basis": {
            "conversion_applied": False,
            "index": None,
            "factor": None,
            "limitation": "Escalation index and factor are not supplied by the table "
            "contract; no conversion is applied.",
        },
    }
    if excluded_unknown:
        result["limitations"].append(
            "Excluded benchmark rows with unknown grouping labels: "
            f"{excluded_unknown}; these rows cannot qualify as comparables."
        )
    intervals, bases, ids = {}, set(), set()
    indicative = bool(excluded_unknown)
    for metric, (quantity_key, _unit) in METRICS.items():
        quantity = scope.get(quantity_key, 0)
        if not quantity:
            continue
        row, dropped, ambiguous = _select(rows, metric, group)
        if row is None:
            result["unbenchmarked_elements"].append(quantity_key)
            if ambiguous:
                result["limitations"].append(
                    f"{metric}: ambiguous comparable groups; {ambiguous}; "
                    "summary percentiles cannot be pooled."
                )
            continue
        interval = {
            key: row[key] * quantity * row["usd_multiplier"]
            for key in ("p10", "p50", "p90")
        }
        if not all(isfinite(value) for value in interval.values()):
            raise ValueError("scope scaling exceeds finite numerical range")
        interval.update(
            unit="USD",
            benchmark_unit=row["unit"],
            quantity=quantity,
            n=row["n"],
            comparables=row["comparables"],
        )
        intervals[metric] = interval
        result["matched_group"][metric] = {
            **{key: row[key] for key in GROUP_KEYS},
            "dropped_keys": dropped,
        }
        bases.add(row["cost_basis"])
        ids.update(row["comparables"])
        indicative |= row["indicative_only"] or bool(dropped)
    result["unbenchmarked_elements"].extend(
        key for key in UNSUPPORTED if scope.get(key, 0)
    )
    if len(bases) > 1:
        raise ValueError(
            "matched metrics have mixed cost bases; supply a homogeneous table"
        )
    if intervals:
        result.update(
            range=intervals,
            comparables=sorted(ids),
            cost_basis=bases.pop(),
            indicative_only=indicative or bool(result["unbenchmarked_elements"]),
        )
    else:
        result["reason"] = "no close comparables"
    if result["cost_basis"] == "nominal":
        result["escalation_basis"][
            "limitation"
        ] += " Values remain nominal; their price year is not supplied."
    if "quote" in scope:
        if (
            intervals
            and scope.get("quote_cost_basis", "USD_2026") != result["cost_basis"]
        ):
            raise ValueError("quote cost basis differs from benchmark cost basis")
        result["quote_position"] = (
            {
                metric: _position(scope["quote"], interval)
                for metric, interval in intervals.items()
            }
            if intervals
            else None
        )
    return result
