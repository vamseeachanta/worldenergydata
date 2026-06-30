"""Build deterministic Texas RRC production atlas aggregations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

import pandas as pd

from worldenergydata.texas_rrc.data.loaders.pdq_loader import PDQLoader
from worldenergydata.texas_rrc.processors.production_processor import (
    ProductionProcessor,
)
from worldenergydata.texas_rrc.validators import TexasDataValidator

GAS_MCF_TO_BOE = ProductionProcessor.UNIT_CONVERSIONS["mcf_to_boe"]
VALID_DISTRICTS = set(TexasDataValidator.VALID_DISTRICTS)
AGGREGATION_LEVELS = ("field", "lease", "district", "operator", "statewide")
ATLAS_COLUMNS = [
    "aggregation_level",
    "district",
    "field_number",
    "field_name",
    "lease_number",
    "lease_name",
    "operator_number",
    "operator_name",
    "cumulative_oil_bbl",
    "cumulative_gas_mcf",
    "cumulative_condensate_bbl",
    "cumulative_water_bbl",
    "cumulative_boe",
    "first_production_month",
    "last_production_month",
    "still_producing",
    "production_month_count",
    "production_span_months",
    "peak_oil_bbl",
    "peak_gas_mcf",
    "peak_boe",
    "lease_count",
    "operator_count",
    "well_count_peak",
    "top_operator_number",
    "top_operator_name",
    "top_operator_boe",
    "top_operator_share",
]
IDENTIFIER_COLUMNS = (
    "district",
    "field_number",
    "field_name",
    "lease_number",
    "lease_name",
    "operator_number",
    "operator_name",
)
NUMERIC_COLUMNS = ("oil_bbl", "gas_mcf", "condensate_bbl", "water_bbl", "well_count")
METRIC_COLUMNS = (*NUMERIC_COLUMNS, "boe")
OPTIONAL_METRIC_COLUMNS = ("water_bbl", "well_count")
OPTIONAL_METRIC_AVAILABILITY = {
    "water_bbl": "water_available",
    "well_count": "well_count_available",
}
BOUNDARY_MONTH_COLUMNS = (
    "district",
    "field_number",
    "lease_number",
    "production_month",
)
GROUP_KEYS = {
    "field": ("district", "field_number"),
    "lease": (
        "district",
        "field_number",
        "lease_number",
    ),
    "district": ("district",),
    "operator": ("operator_number",),
    "statewide": (),
}
DISPLAY_COLUMNS_BY_LEVEL = {
    "field": ("field_name",),
    "lease": ("field_name", "lease_name"),
    "district": (),
    "operator": ("operator_name",),
    "statewide": (),
}
OUTPUT_KEY_COLUMNS = (
    "district",
    "field_number",
    "field_name",
    "lease_number",
    "lease_name",
    "operator_number",
    "operator_name",
)


def normalize_production_frame(
    frame: pd.DataFrame,
    sort_rows: bool = True,
) -> pd.DataFrame:
    """Normalize official PDQ production columns into atlas-ready rows."""
    if frame.empty:
        return _empty_normalized_frame()
    renamed = frame.rename(columns=_rename_map(frame))
    processor = ProductionProcessor()
    normalized = pd.DataFrame(index=renamed.index)
    for column in IDENTIFIER_COLUMNS:
        normalized[column] = (
            renamed[column].map(_text_value) if column in renamed else ""
        )
    normalized["district"] = _normalize_districts(normalized["district"])
    normalized["production_month"] = _production_months(renamed, processor)
    for source, target in (
        ("oil_production", "oil_bbl"),
        ("gas_production", "gas_mcf"),
        ("condensate", "condensate_bbl"),
        ("water_production", "water_bbl"),
        ("well_count", "well_count"),
    ):
        values, available = _numeric_values_with_availability(renamed, source)
        normalized[target] = values
        availability_column = OPTIONAL_METRIC_AVAILABILITY.get(target)
        if availability_column:
            normalized[availability_column] = available
    normalized["gas_mcf"] = normalized["gas_mcf"] + _numeric_values(
        renamed, "casinghead_gas"
    )
    normalized["boe"] = (
        normalized["oil_bbl"]
        + normalized["condensate_bbl"]
        + normalized["gas_mcf"] * GAS_MCF_TO_BOE
    )
    normalized["report_filed"] = _report_filed_values(renamed)
    normalized["source_id"] = "production_pdq"
    if not sort_rows:
        return normalized.reset_index(drop=True)
    return normalized.sort_values(
        [
            "district",
            "field_number",
            "lease_number",
            "operator_number",
            "production_month",
        ],
        kind="mergesort",
    ).reset_index(drop=True)


def is_usable_production_frame(frame: pd.DataFrame) -> bool:
    """Return True when a raw frame has the minimum recognizable PDQ columns."""
    if frame.empty:
        return False
    columns = set(frame.rename(columns=_rename_map(frame)).columns)
    has_date = "production_date" in columns or {"year", "month"}.issubset(columns)
    has_key = any(
        column in columns
        for column in ("district", "field_number", "lease_number", "operator_number")
    )
    has_volume = any(
        column in columns
        for column in (
            "oil_production",
            "gas_production",
            "casinghead_gas",
            "condensate",
            "water_production",
        )
    )
    return has_date and has_key and has_volume


def build_production_atlas(frame: pd.DataFrame) -> pd.DataFrame:
    """Build field, lease, district, operator, and statewide production summaries."""
    if frame.empty:
        return pd.DataFrame(columns=ATLAS_COLUMNS)
    production = (
        frame
        if "production_month" in frame.columns
        else normalize_production_frame(frame)
    )
    max_month = _max_month(production)
    rows: list[dict[str, object]] = []
    for level in AGGREGATION_LEVELS:
        rows.extend(_aggregate_level(production, level, max_month))
    if not rows:
        return pd.DataFrame(columns=ATLAS_COLUMNS)
    atlas = pd.DataFrame(rows, columns=ATLAS_COLUMNS)
    atlas["_level_order"] = atlas["aggregation_level"].map(
        {level: index for index, level in enumerate(AGGREGATION_LEVELS)}
    )
    sort_columns = [
        "_level_order",
        "district",
        "field_number",
        "lease_number",
        "operator_number",
    ]
    atlas = atlas.assign(
        district=atlas["district"].fillna(""),
        field_number=atlas["field_number"].fillna(""),
        lease_number=atlas["lease_number"].fillna(""),
        operator_number=atlas["operator_number"].fillna(""),
    )
    return (
        atlas.sort_values(sort_columns, kind="mergesort")
        .drop(columns="_level_order")
        .reset_index(drop=True)
    )


def build_production_atlas_from_chunks(
    chunks: Iterable[pd.DataFrame],
) -> pd.DataFrame:
    """Build the production atlas from bounded raw or normalized chunks."""
    accumulator = _ProductionAtlasAccumulator()
    for chunk in chunks:
        if chunk.empty:
            continue
        production = (
            chunk
            if "production_month" in chunk.columns
            else normalize_production_frame(chunk, sort_rows=False)
        )
        accumulator.add(production)
    return accumulator.to_frame()


@dataclass
class _LevelAccumulator:
    level: str
    keys: tuple[str, ...]
    cumulative: dict[tuple[str, ...], dict[str, float]] = field(default_factory=dict)
    lease_values: dict[tuple[str, ...], set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    operator_values: dict[tuple[str, ...], set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    operator_boe: dict[tuple[str, ...], dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float))
    )
    operator_names: dict[tuple[tuple[str, ...], str], tuple[str, str]] = field(
        default_factory=dict
    )
    display_values: dict[tuple[tuple[str, ...], str], tuple[str, str]] = field(
        default_factory=dict
    )
    monthly_totals: dict[tuple[tuple[str, ...], str], dict[str, float]] = field(
        default_factory=dict
    )
    lease_first_month: dict[tuple[str, ...], str] = field(default_factory=dict)
    lease_last_month: dict[tuple[str, ...], str] = field(default_factory=dict)
    lease_month_count: dict[tuple[str, ...], int] = field(
        default_factory=lambda: defaultdict(int)
    )
    lease_peaks: dict[tuple[str, ...], dict[str, float]] = field(default_factory=dict)
    metric_availability: dict[tuple[str, ...], dict[str, bool]] = field(
        default_factory=dict
    )
    last_filed_month: dict[tuple[str, ...], str] = field(default_factory=dict)

    def add(self, production: pd.DataFrame) -> None:
        self._add_monthly(production)
        self._add_unique(production, "lease_number", self.lease_values)
        self._add_unique(production, "operator_number", self.operator_values)
        self._add_operator_boe(production)
        self._add_display_values(production)

    def to_rows(self, max_month: str | None) -> list[dict[str, object]]:
        rows = []
        finalized = self._finalized_monthly()
        for key in sorted(self.cumulative):
            rows.append(self._row(key, max_month, finalized))
        return rows

    def _add_monthly(self, production: pd.DataFrame) -> None:
        columns = [*self.keys, "production_month"]
        aggregation: dict[str, str] = {column: "sum" for column in METRIC_COLUMNS}
        for column in OPTIONAL_METRIC_AVAILABILITY.values():
            if column in production:
                aggregation[column] = "any"
        if "report_filed" in production:
            aggregation["report_filed"] = "any"
        monthly = (
            production.groupby(columns or ["production_month"], as_index=False)
            .agg(aggregation)
            .reset_index(drop=True)
        )
        for row in monthly.itertuples(index=False):
            data = row._asdict()
            key = self._key(data)
            month = _text_value(data.get("production_month"))
            metrics = _metrics_from_row(data)
            _add_availability(
                self.metric_availability.setdefault(key, _empty_availability()),
                _availability_from_row(data),
            )
            self._add_filed_month(key, month, data)
            _add_metrics(self.cumulative.setdefault(key, _empty_metrics()), metrics)
            if self.level == "lease":
                self._add_lease_month(key, month, metrics)
            else:
                _add_metrics(
                    self.monthly_totals.setdefault((key, month), _empty_metrics()),
                    metrics,
                )

    def _add_filed_month(
        self,
        key: tuple[str, ...],
        month: str,
        data: dict[str, object],
    ) -> None:
        if not month or not bool(data.get("report_filed", True)):
            return
        self.last_filed_month[key] = max(month, self.last_filed_month.get(key, month))

    def _add_lease_month(
        self,
        key: tuple[str, ...],
        month: str,
        metrics: dict[str, float],
    ) -> None:
        peaks = self.lease_peaks.setdefault(key, _empty_metrics())
        _max_metrics(peaks, metrics)
        if not month or metrics["boe"] <= 0:
            return
        self.lease_month_count[key] += 1
        self.lease_first_month[key] = min(month, self.lease_first_month.get(key, month))
        self.lease_last_month[key] = max(month, self.lease_last_month.get(key, month))

    def _add_unique(
        self,
        production: pd.DataFrame,
        column: str,
        target: dict[tuple[str, ...], set[str]],
    ) -> None:
        if column not in production:
            return
        if self.level == "lease" and column == "lease_number":
            return
        columns = [*self.keys, column]
        values = production[columns or [column]].drop_duplicates()
        for row in values.itertuples(index=False):
            data = row._asdict()
            value = _text_value(data.get(column))
            if value:
                target[self._key(data)].add(value)

    def _add_operator_boe(self, production: pd.DataFrame) -> None:
        columns = [*self.keys, "operator_number"]
        columns = list(dict.fromkeys(columns))
        operator = production.groupby(columns, as_index=False)["boe"].sum()
        for row in operator.itertuples(index=False):
            data = row._asdict()
            key = self._key(data)
            operator_number = _text_value(data.get("operator_number"))
            self.operator_boe[key][operator_number] += float(data["boe"])
        self._add_operator_names(production)

    def _add_operator_names(self, production: pd.DataFrame) -> None:
        columns = [*self.keys, "operator_number", "production_month", "operator_name"]
        values = production[columns]
        for row in values.drop_duplicates().itertuples(index=False):
            data = row._asdict()
            key = self._key(data)
            operator_number = _text_value(data.get("operator_number"))
            operator_name = _text_value(data.get("operator_name"))
            if operator_number and operator_name:
                self._set_operator_name(
                    key,
                    operator_number,
                    _text_value(data.get("production_month")),
                    operator_name,
                )

    def _set_operator_name(
        self,
        key: tuple[str, ...],
        operator_number: str,
        month: str,
        value: str,
    ) -> None:
        current = self.operator_names.get((key, operator_number))
        if (
            current is None
            or month > current[0]
            or (month == current[0] and value < current[1])
        ):
            self.operator_names[(key, operator_number)] = (month, value)

    def _add_display_values(self, production: pd.DataFrame) -> None:
        for column in DISPLAY_COLUMNS_BY_LEVEL[self.level]:
            if column not in production:
                continue
            values = production[[*self.keys, "production_month", column]]
            for row in values.drop_duplicates().itertuples(index=False):
                data = row._asdict()
                value = _text_value(data.get(column))
                if value:
                    self._set_display(
                        self._key(data),
                        column,
                        _text_value(data.get("production_month")),
                        value,
                    )

    def _set_display(
        self,
        key: tuple[str, ...],
        column: str,
        month: str,
        value: str,
    ) -> None:
        current = self.display_values.get((key, column))
        if (
            current is None
            or month > current[0]
            or (month == current[0] and value < current[1])
        ):
            self.display_values[(key, column)] = (month, value)

    def _finalized_monthly(self) -> dict[tuple[str, ...], dict[str, object]]:
        if self.level == "lease":
            return {}
        finalized: dict[tuple[str, ...], dict[str, object]] = {}
        for (key, month), metrics in self.monthly_totals.items():
            data = finalized.setdefault(
                key,
                {"months": set(), "peaks": _empty_metrics()},
            )
            if month and metrics["boe"] > 0:
                data["months"].add(month)
            _max_metrics(data["peaks"], metrics)
        return finalized

    def _row(
        self,
        key: tuple[str, ...],
        max_month: str | None,
        finalized: dict[tuple[str, ...], dict[str, object]],
    ) -> dict[str, object]:
        cumulative = self.cumulative[key]
        months, peaks = self._months_and_peaks(key, finalized)
        top_operator = self._top_operator(key)
        availability = self.metric_availability.get(key, _available_metrics())
        row = {column: "" for column in OUTPUT_KEY_COLUMNS}
        row.update(dict(zip(self.keys, key)))
        row.update(self._display_columns(key))
        row.update(_metric_columns(cumulative, availability))
        row.update(
            {
                "aggregation_level": self.level,
                "first_production_month": months[0] if months else "",
                "last_production_month": months[-1] if months else "",
                "still_producing": bool(
                    months
                    and months[-1] == max_month
                    and self.last_filed_month.get(key, "") == months[-1]
                    and cumulative["boe"] > 0
                ),
                "production_month_count": len(months),
                "production_span_months": (
                    _month_span(months[0], months[-1]) if months else 0
                ),
                "peak_oil_bbl": peaks["oil_bbl"],
                "peak_gas_mcf": peaks["gas_mcf"],
                "peak_boe": peaks["boe"],
                "lease_count": self._lease_count(key),
                "operator_count": len(self.operator_values.get(key, set())),
                "well_count_peak": _available_value(
                    int(peaks["well_count"]), availability["well_count"]
                ),
                "top_operator_number": top_operator["operator_number"],
                "top_operator_name": top_operator["operator_name"],
                "top_operator_boe": top_operator["boe"],
                "top_operator_share": _share(top_operator["boe"], cumulative["boe"]),
            }
        )
        return row

    def _months_and_peaks(
        self,
        key: tuple[str, ...],
        finalized: dict[tuple[str, ...], dict[str, object]],
    ) -> tuple[list[str], dict[str, float]]:
        if self.level == "lease":
            first = self.lease_first_month.get(key, "")
            last = self.lease_last_month.get(key, "")
            months = _contiguous_months(first, last, self.lease_month_count.get(key, 0))
            return months, self.lease_peaks.get(key, _empty_metrics())
        data = finalized.get(key, {"months": set(), "peaks": _empty_metrics()})
        return sorted(data["months"]), data["peaks"]

    def _top_operator(self, key: tuple[str, ...]) -> dict[str, object]:
        operators = self.operator_boe.get(key, {})
        if not operators:
            return {"operator_number": "", "operator_name": "", "boe": 0.0}
        operator_number, boe = sorted(
            operators.items(),
            key=lambda item: (-item[1], item[0]),
        )[0]
        return {
            "operator_number": operator_number,
            "operator_name": self.operator_names.get((key, operator_number), ("", ""))[
                1
            ],
            "boe": float(boe),
        }

    def _display_columns(self, key: tuple[str, ...]) -> dict[str, str]:
        return {
            column: self.display_values.get((key, column), ("", ""))[1]
            for column in DISPLAY_COLUMNS_BY_LEVEL[self.level]
        }

    def _lease_count(self, key: tuple[str, ...]) -> int:
        if self.level == "lease":
            return 1 if key and _text_value(key[-1]) else 0
        return len(self.lease_values.get(key, set()))

    def _key(self, data: dict[str, object]) -> tuple[str, ...]:
        return tuple(_text_value(data.get(column)) for column in self.keys)


class _ProductionAtlasAccumulator:
    def __init__(self) -> None:
        self.levels = {
            level: _LevelAccumulator(level, GROUP_KEYS[level])
            for level in AGGREGATION_LEVELS
        }
        self.max_month: str | None = None
        self._pending = pd.DataFrame()

    def add(self, production: pd.DataFrame) -> None:
        if production.empty:
            return
        ready = self._ready_production(production)
        if ready.empty:
            return
        self._add_ready(ready)

    def _ready_production(self, production: pd.DataFrame) -> pd.DataFrame:
        if not self._pending.empty:
            production = pd.concat([self._pending, production], ignore_index=True)
        if production.empty or not set(BOUNDARY_MONTH_COLUMNS).issubset(production):
            self._pending = pd.DataFrame()
            return production
        last = production.iloc[-1]
        pending_mask = pd.Series(True, index=production.index)
        for column in BOUNDARY_MONTH_COLUMNS:
            pending_mask &= production[column].eq(last[column])
        self._pending = production.loc[pending_mask].copy()
        return production.loc[~pending_mask].copy()

    def _add_ready(self, production: pd.DataFrame) -> None:
        self.max_month = _max_text(self.max_month, _max_month(production))
        for accumulator in self.levels.values():
            accumulator.add(production)

    def to_frame(self) -> pd.DataFrame:
        self._flush_pending()
        rows = []
        for level in AGGREGATION_LEVELS:
            rows.extend(self.levels[level].to_rows(self.max_month))
        if not rows:
            return pd.DataFrame(columns=ATLAS_COLUMNS)
        return _sort_atlas(pd.DataFrame(rows, columns=ATLAS_COLUMNS))

    def _flush_pending(self) -> None:
        if self._pending.empty:
            return
        pending = self._pending
        self._pending = pd.DataFrame()
        self._add_ready(pending)


def _metrics_from_row(data: dict[str, object]) -> dict[str, float]:
    return {
        "oil_bbl": float(data.get("oil_bbl", 0.0) or 0.0),
        "gas_mcf": float(data.get("gas_mcf", 0.0) or 0.0),
        "condensate_bbl": float(data.get("condensate_bbl", 0.0) or 0.0),
        "water_bbl": float(data.get("water_bbl", 0.0) or 0.0),
        "well_count": float(data.get("well_count", 0.0) or 0.0),
        "boe": float(data.get("boe", 0.0) or 0.0),
    }


def _empty_metrics() -> dict[str, float]:
    return {
        "oil_bbl": 0.0,
        "gas_mcf": 0.0,
        "condensate_bbl": 0.0,
        "water_bbl": 0.0,
        "well_count": 0.0,
        "boe": 0.0,
    }


def _empty_availability() -> dict[str, bool]:
    return {column: False for column in OPTIONAL_METRIC_COLUMNS}


def _available_metrics() -> dict[str, bool]:
    return {column: True for column in OPTIONAL_METRIC_COLUMNS}


def _add_metrics(target: dict[str, float], values: dict[str, float]) -> None:
    for column, value in values.items():
        target[column] += value


def _add_availability(target: dict[str, bool], values: dict[str, bool]) -> None:
    for column, value in values.items():
        target[column] = target.get(column, False) or value


def _max_metrics(target: dict[str, float], values: dict[str, float]) -> None:
    for column, value in values.items():
        target[column] = max(target[column], value)


def _metric_columns(
    metrics: dict[str, float],
    availability: dict[str, bool],
) -> dict[str, object]:
    return {
        "cumulative_oil_bbl": metrics["oil_bbl"],
        "cumulative_gas_mcf": metrics["gas_mcf"],
        "cumulative_condensate_bbl": metrics["condensate_bbl"],
        "cumulative_water_bbl": _available_value(
            metrics["water_bbl"], availability["water_bbl"]
        ),
        "cumulative_boe": metrics["boe"],
    }


def _available_value(value: object, available: bool) -> object:
    return value if available else pd.NA


def _share(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return min(1.0, max(0.0, float(numerator) / float(denominator)))


def _contiguous_months(first: str, last: str, count: int) -> list[str]:
    if not first or count <= 0:
        return []
    if count == 1 or first == last:
        return [first]
    return [first, *([first] * max(count - 2, 0)), last]


def _max_text(left: str | None, right: str | None) -> str | None:
    if not left:
        return right
    if not right:
        return left
    return max(left, right)


def _sort_atlas(atlas: pd.DataFrame) -> pd.DataFrame:
    ordered = atlas.assign(
        _level_order=atlas["aggregation_level"].map(
            {level: index for index, level in enumerate(AGGREGATION_LEVELS)}
        ),
        district=atlas["district"].fillna(""),
        field_number=atlas["field_number"].fillna(""),
        lease_number=atlas["lease_number"].fillna(""),
        operator_number=atlas["operator_number"].fillna(""),
    )
    return (
        ordered.sort_values(
            [
                "_level_order",
                "district",
                "field_number",
                "lease_number",
                "operator_number",
            ],
            kind="mergesort",
        )
        .drop(columns="_level_order")
        .reset_index(drop=True)
    )


def _aggregate_level(
    production: pd.DataFrame,
    level: str,
    max_month: str | None,
) -> list[dict[str, object]]:
    keys = GROUP_KEYS[level]
    if not keys:
        return [_summary_row(production, level, {}, max_month)]
    rows = []
    for key_values, group in production.groupby(list(keys), dropna=False, sort=True):
        values = key_values if isinstance(key_values, tuple) else (key_values,)
        key_map = dict(zip(keys, values))
        rows.append(_summary_row(group, level, key_map, max_month))
    return rows


def _summary_row(
    group: pd.DataFrame,
    level: str,
    key_map: dict[str, object],
    max_month: str | None,
) -> dict[str, object]:
    monthly = _monthly_totals(group)
    months = _positive_months(monthly)
    top_operator = _top_operator(group)
    cumulative_boe = float(group["boe"].sum())
    availability = _metric_availability(group)
    last_filed_month = _max_filed_month(group)
    row = {column: "" for column in OUTPUT_KEY_COLUMNS}
    row.update({key: _text_value(value) for key, value in key_map.items()})
    row.update(
        {
            column: _display_value(group, column)
            for column in DISPLAY_COLUMNS_BY_LEVEL[level]
        }
    )
    row.update(
        {
            "aggregation_level": level,
            "first_production_month": months[0] if months else "",
            "last_production_month": months[-1] if months else "",
            "still_producing": bool(
                months
                and months[-1] == max_month
                and last_filed_month == months[-1]
                and cumulative_boe > 0
            ),
            "production_month_count": len(months),
            "production_span_months": (
                _month_span(months[0], months[-1]) if months else 0
            ),
            "peak_oil_bbl": _peak(monthly, "oil_bbl"),
            "peak_gas_mcf": _peak(monthly, "gas_mcf"),
            "peak_boe": _peak(monthly, "boe"),
            "lease_count": _nunique_text(group, "lease_number"),
            "operator_count": _nunique_text(group, "operator_number"),
            "well_count_peak": _available_value(
                int(_peak(monthly, "well_count")), availability["well_count"]
            ),
            "top_operator_number": top_operator["operator_number"],
            "top_operator_name": top_operator["operator_name"],
            "top_operator_boe": top_operator["boe"],
            "top_operator_share": _share(top_operator["boe"], cumulative_boe),
        }
    )
    row.update(
        _metric_columns(
            {
                "oil_bbl": float(group["oil_bbl"].sum()),
                "gas_mcf": float(group["gas_mcf"].sum()),
                "condensate_bbl": float(group["condensate_bbl"].sum()),
                "water_bbl": float(group["water_bbl"].sum()),
                "well_count": float(group["well_count"].sum()),
                "boe": cumulative_boe,
            },
            availability,
        )
    )
    return row


def _monthly_totals(group: pd.DataFrame) -> pd.DataFrame:
    if group.empty or "production_month" not in group:
        return pd.DataFrame(columns=["production_month", *NUMERIC_COLUMNS, "boe"])
    return (
        group.groupby("production_month", as_index=False, dropna=False)[
            ["oil_bbl", "gas_mcf", "condensate_bbl", "water_bbl", "well_count", "boe"]
        ]
        .sum()
        .sort_values("production_month", kind="mergesort")
    )


def _positive_months(monthly: pd.DataFrame) -> list[str]:
    if monthly.empty or "boe" not in monthly or "production_month" not in monthly:
        return []
    positive = monthly[monthly["boe"] > 0]
    return sorted(
        month for month in positive["production_month"].dropna().unique() if month
    )


def _top_operator(group: pd.DataFrame) -> dict[str, object]:
    operator = (
        group.groupby(["operator_number"], dropna=False, as_index=False)["boe"]
        .sum()
        .sort_values(
            ["boe", "operator_number"], ascending=[False, True], kind="mergesort"
        )
    )
    if operator.empty:
        return {"operator_number": "", "operator_name": "", "boe": 0.0}
    row = operator.iloc[0]
    operator_number = _text_value(row["operator_number"])
    operator_rows = group[group["operator_number"].map(_text_value) == operator_number]
    return {
        "operator_number": operator_number,
        "operator_name": _display_value(operator_rows, "operator_name"),
        "boe": float(row["boe"]),
    }


def _rename_map(frame: pd.DataFrame) -> dict[str, str]:
    mappings = {
        **ProductionProcessor.COLUMN_MAPPINGS,
        **PDQLoader.PRODUCTION_FIELD_MAPPING,
        "OG_COND_PROD": "condensate",
        "OIL_PRODUCTION": "oil_production",
        "GAS_PRODUCTION": "gas_production",
        "WATER_PRODUCTION": "water_production",
        "PRODUCTION_MONTH": "production_date",
        "FIELD_OIL_PROD_VOL": "oil_production",
        "FIELD_GAS_PROD_VOL": "gas_production",
        "FIELD_COND_PROD_VOL": "condensate",
        "FIELD_CSGD_PROD_VOL": "casinghead_gas",
        "LEASE_OIL_PROD_VOL": "oil_production",
        "LEASE_GAS_PROD_VOL": "gas_production",
        "LEASE_COND_PROD_VOL": "condensate",
        "LEASE_CSGD_PROD_VOL": "casinghead_gas",
        "OPER_OIL_PROD_VOL": "oil_production",
        "OPER_GAS_PROD_VOL": "gas_production",
        "OPER_COND_PROD_VOL": "condensate",
        "OPER_CSGD_PROD_VOL": "casinghead_gas",
        "DIST_OIL_PROD_VOL": "oil_production",
        "DIST_GAS_PROD_VOL": "gas_production",
        "DIST_COND_PROD_VOL": "condensate",
        "DIST_CSGD_PROD_VOL": "casinghead_gas",
        "PROD_REPORT_FILED_FLAG": "report_filed",
    }
    rename = {}
    for column in frame.columns:
        key = str(column).strip().upper().replace(" ", "_").replace("-", "_")
        rename[column] = mappings.get(key, key.lower())
    return rename


def _numeric_values(frame: pd.DataFrame, column: str) -> pd.Series:
    values = frame[column] if column in frame else pd.Series(0.0, index=frame.index)
    return pd.to_numeric(values, errors="coerce").fillna(0.0)


def _numeric_values_with_availability(
    frame: pd.DataFrame,
    column: str,
) -> tuple[pd.Series, pd.Series]:
    if column not in frame:
        return (
            pd.Series(0.0, index=frame.index),
            pd.Series([False] * len(frame.index), index=frame.index, dtype=object),
        )
    values = frame[column]
    available = values.map(_text_value).ne("")
    return (
        pd.to_numeric(values, errors="coerce").fillna(0.0),
        available.astype(object),
    )


def _report_filed_values(frame: pd.DataFrame) -> pd.Series:
    if "report_filed" not in frame:
        return pd.Series([True] * len(frame.index), index=frame.index, dtype=object)
    values = frame["report_filed"].map(_text_value).str.upper()
    return values.eq("Y").astype(object)


def _availability_from_row(data: dict[str, object]) -> dict[str, bool]:
    return {
        metric: bool(data.get(column, True))
        for metric, column in OPTIONAL_METRIC_AVAILABILITY.items()
    }


def _metric_availability(frame: pd.DataFrame) -> dict[str, bool]:
    availability = {}
    for metric, column in OPTIONAL_METRIC_AVAILABILITY.items():
        if column not in frame:
            availability[metric] = True
        else:
            availability[metric] = bool(frame[column].any())
    return availability


def _normalize_districts(values: pd.Series) -> pd.Series:
    districts = values.map(_text_value).str.upper()
    single_digit = districts.str.fullmatch(r"\d", na=False)
    districts.loc[single_digit] = districts.loc[single_digit].str.zfill(2)
    return districts.where(districts.isin(VALID_DISTRICTS), "")


def _production_months(
    renamed: pd.DataFrame,
    processor: ProductionProcessor,
) -> pd.Series:
    if "production_date" in renamed:
        return _production_date_values(renamed["production_date"], processor)
    if {"year", "month"}.issubset(renamed.columns):
        return _year_month_values(renamed["year"], renamed["month"])
    return pd.Series(None, index=renamed.index)


def _production_date_values(
    values: pd.Series,
    processor: ProductionProcessor,
) -> pd.Series:
    text = values.map(_text_value)
    result = pd.Series(None, index=values.index, dtype=object)
    yyyymm = text.str.fullmatch(r"\d{6}", na=False)
    month = pd.to_numeric(text.str.slice(4, 6), errors="coerce")
    yyyymm = yyyymm & month.between(1, 12)
    if yyyymm.any():
        result.loc[yyyymm] = (
            text.loc[yyyymm].str.slice(0, 4) + "-" + text.loc[yyyymm].str.slice(4, 6)
        )
    fallback = ~yyyymm & text.ne("")
    if fallback.any():
        result.loc[fallback] = text.loc[fallback].map(processor._parse_production_date)
    return result


def _year_month_values(years: pd.Series, months: pd.Series) -> pd.Series:
    year = pd.to_numeric(years, errors="coerce")
    month = pd.to_numeric(months, errors="coerce")
    valid = year.notna() & month.notna() & month.between(1, 12)
    result = pd.Series(None, index=years.index, dtype=object)
    if valid.any():
        result.loc[valid] = (
            year.loc[valid].astype(int).astype(str).str.zfill(4)
            + "-"
            + month.loc[valid].astype(int).astype(str).str.zfill(2)
        )
    return result


def _year_month_value(year: object, month: object) -> str | None:
    year_text = _text_value(year)
    month_text = _text_value(month)
    if not year_text or not month_text:
        return None
    try:
        return f"{int(float(year_text)):04d}-{int(float(month_text)):02d}"
    except ValueError:
        return None


def _text_value(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        return text[:-2]
    return text


def _display_value(frame: pd.DataFrame, column: str) -> str:
    if column not in frame:
        return ""
    candidates = frame[[column, "production_month"]].copy()
    candidates[column] = candidates[column].map(_text_value)
    candidates = candidates[candidates[column] != ""]
    if candidates.empty:
        return ""

    dated = candidates[candidates["production_month"].map(lambda value: bool(value))]
    if not dated.empty:
        latest_month = max(dated["production_month"])
        candidates = dated[dated["production_month"] == latest_month]

    counts = candidates[column].value_counts()
    max_count = counts.max()
    return sorted(counts[counts == max_count].index)[0]


def _peak(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return 0.0
    return float(frame[column].max())


def _nunique_text(frame: pd.DataFrame, column: str) -> int:
    if column not in frame:
        return 0
    values = {_text_value(value) for value in frame[column]}
    values.discard("")
    return len(values)


def _max_month(frame: pd.DataFrame) -> str | None:
    if "production_month" not in frame:
        return None
    months = frame["production_month"].map(_text_value)
    mask = months.ne("")
    if "report_filed" in frame:
        filed = frame["report_filed"].map(
            lambda value: False if value is None or pd.isna(value) else bool(value)
        )
        mask &= filed
    if "boe" in frame:
        mask &= pd.to_numeric(frame["boe"], errors="coerce").fillna(0.0) > 0
    months = [month for month in months[mask] if month]
    return max(months) if months else None


def _max_filed_month(frame: pd.DataFrame) -> str | None:
    if "production_month" not in frame:
        return None
    months = frame["production_month"].map(_text_value)
    mask = months.ne("")
    if "report_filed" in frame:
        mask &= frame["report_filed"].map(
            lambda value: False if value is None or pd.isna(value) else bool(value)
        )
    months = [month for month in months[mask] if month]
    return max(months) if months else None


def _month_span(start: str, end: str) -> int:
    start_date = datetime.strptime(start, "%Y-%m")
    end_date = datetime.strptime(end, "%Y-%m")
    return (
        (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
    )


def _empty_normalized_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            *IDENTIFIER_COLUMNS,
            "production_month",
            "oil_bbl",
            "gas_mcf",
            "condensate_bbl",
            "water_bbl",
            "well_count",
            "water_available",
            "well_count_available",
            "report_filed",
            "boe",
            "source_id",
        ]
    )
