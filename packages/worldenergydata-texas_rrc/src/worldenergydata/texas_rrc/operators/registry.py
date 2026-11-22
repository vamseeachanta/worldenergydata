"""Conservative operator roll-up of already-landed RRC production and wells.

Methods and sources: docs/data-sources/onshore/texas-rrc/operator-registry.md.
PDQ oil volumes are lease totals; no equal-share well allocation is performed.
"""

from __future__ import annotations

import calendar
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import median

import pandas as pd

# Issue #1126, Output: last-12-month production (inclusive calendar months).
WINDOW_MONTHS = 12
SUFFIXES = {
    "INC",
    "INCORPORATED",
    "LLC",
    "LTD",
    "LIMITED",
    "CO",
    "COMPANY",
    "CORP",
    "CORPORATION",
}
VOLUMES = ("oil_bbl", "gas_mcf", "water_bbl")
UNIT_KEY = ["district", "oil_gas_code", "lease_no"]
PRODUCTION_KEY = [*UNIT_KEY, "production_month"]
OUTPUT_COLUMNS = [
    "operator_no",
    "operator_name",
    "normalized_name",
    "operator_name_variants",
    "name_collision_operator_nos",
    "districts",
    "counties",
    "well_count_total",
    "well_count_producing",
    "well_count_inactive",
    "well_count_other",
    "oil_bbl_last12",
    "gas_mcf_last12",
    "water_bbl_last12",
    "usable_last12",
    "bopd_per_well_median",
    "water_cut_est",
    "first_production",
    "last_production",
    "field_count",
    "field_concentration",
    "stripper_share",
    "operator_size_band",
    "gas_rate_eligible_well_count",
    "gas_mcfd_per_well_median",
    "gas_per_well_metrics_status",
    "per_well_metrics_status",
    "ownership_basis",
    "quality_flags",
]


@dataclass(frozen=True)
class RegistryPolicy:
    """Caller-supplied screening criteria; no regulatory defaults are implied."""

    as_of: str
    size_bands: tuple[tuple[int, str], ...] = ()
    stripper_bopd: float | None = None

    def __post_init__(self):
        if not re.fullmatch(r"\d{4}-\d{2}", self.as_of):
            raise ValueError("as_of must be YYYY-MM")
        pd.Period(self.as_of, freq="M")
        previous = 0
        names = set()
        for upper, name in self.size_bands:
            if (
                isinstance(upper, bool)
                or not isinstance(upper, int)
                or upper <= previous
            ):
                raise ValueError(
                    "size band upper bounds must be increasing positive integers"
                )
            if (
                not name
                or name in names
                or name in {"ABOVE_CONFIGURED_BANDS", "NOT_EVALUATED"}
            ):
                raise ValueError("size band labels must be unique and nonempty")
            previous = upper
            names.add(name)
        if self.stripper_bopd is not None and (
            not math.isfinite(self.stripper_bopd) or self.stripper_bopd < 0
        ):
            raise ValueError("stripper_bopd must be finite and nonnegative")


@dataclass
class RegistryResult:
    """Registry and auditable coverage counts for the supplied snapshots."""

    registry: pd.DataFrame
    quality: dict


def normalize_name(value: str) -> str:
    """Candidate key only: uppercase, punctuation, terminal legal suffixes.

    No fuzzy spelling correction or cross-number entity merge is justified by
    production data. Different cores under one number remain an ambiguity.
    """
    tokens = re.sub(r"[^\w\s]", " ", value.upper()).split()
    # Recognize dotted L.L.C. without conflating other word boundaries.
    if tokens[-3:] == ["L", "L", "C"]:
        tokens = tokens[:-3]
    while tokens and tokens[-1] in SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def _text(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy().reset_index(drop=True)
    for column in columns:
        if column not in result:
            if result.empty:
                result[column] = pd.Series(dtype="string")
            else:
                raise ValueError(f"Missing required column: {column}")
        result[column] = result[column].fillna("").astype(str).str.strip()
    return result


def validate_operator_inputs(production: pd.DataFrame, wells: pd.DataFrame):
    """Return canonical validated copies, rejecting conflicting snapshot rows.

    No outlier thresholds are imposed: volumes must be finite and nonnegative;
    identifiers and calendar months must be explicit. Unknown volumes stay null.
    """
    p = _text(
        production, ["operator_no", "operator_name", *UNIT_KEY, "production_month"]
    )
    w = _text(
        wells, ["operator_no", "operator_name", *UNIT_KEY, "well_id", "well_status"]
    )
    for frame in (p, w):
        for column in ("operator_no", *UNIT_KEY):
            if frame[column].eq("").any():
                raise ValueError(f"Empty required identifier: {column}")
        frame["oil_gas_code"] = frame.oil_gas_code.str.upper()
        if not frame.oil_gas_code.isin(["O", "G"]).all():
            raise ValueError("oil_gas_code must be O or G")
        for column in ("field_no", "county"):
            frame[column] = (
                frame.get(column, pd.Series("", index=frame.index))
                .fillna("")
                .astype(str)
                .str.strip()
            )
    for column in VOLUMES:
        raw = p.get(column, pd.Series(float("nan"), index=p.index))
        values = pd.to_numeric(raw.replace("", float("nan")), errors="coerce")
        malformed = raw.notna() & raw.ne("") & values.isna()
        if (
            malformed.any()
            or ((values < 0) | (values.notna() & ~values.map(math.isfinite))).any()
        ):
            raise ValueError(f"Invalid nonnegative finite volume: {column}")
        p[column] = values.astype(float)
    if not p.production_month.str.fullmatch(r"\d{4}-\d{2}").all():
        raise ValueError("production_month must be YYYY-MM")
    p["production_month"] = p.production_month.map(
        lambda value: str(pd.Period(value, freq="M"))
    )
    if w.well_id.eq("").any():
        raise ValueError("well_id must be nonempty")
    w["well_status"] = w.well_status.str.lower()
    # Exact duplicates collapse. Revised/conflicting snapshots need explicit selection.
    p = p.drop_duplicates()
    w = w.drop_duplicates()
    if p.duplicated(PRODUCTION_KEY).any():
        raise ValueError("Conflicting production unit-month rows; select one snapshot")
    if w.duplicated("well_id").any():
        raise ValueError("Conflicting well rows; select one current inventory snapshot")
    return p, w


def _names(production, wells):
    by_number = defaultdict(set)
    by_core = defaultdict(set)
    for frame in (production, wells):
        for number, name in frame[["operator_no", "operator_name"]].itertuples(
            index=False, name=None
        ):
            if name:
                by_number[number].add(name)
                core = normalize_name(name)
                if core:
                    by_core[core].add(number)
    return by_number, by_core


def _complete(group: pd.DataFrame, months: set[str]) -> bool:
    return (
        set(group.production_month) == months
        and group[["oil_bbl", "gas_mcf"]].notna().all().all()
    )


def _total(frame, column):
    values = frame[column]
    return float(values.sum()) if len(values) and values.notna().all() else None


def _size_band(count, policy):
    if count is None or not policy.size_bands:
        return "NOT_EVALUATED"
    return next(
        (name for upper, name in policy.size_bands if count <= upper),
        "ABOVE_CONFIGURED_BANDS",
    )


def _well_metrics(wells, production, months, days):
    """Gas leases are single-well only when inventory uniquely confirms the link.

    Source: RRC PDQ FAQ, 'How is production reported?', accessed 2026-10-19.
    Oil lease rows are never assigned to a well, even a single current match.
    """
    rates = []
    by_unit = {key: group for key, group in wells.groupby(UNIT_KEY)}
    for key, group in production.groupby(UNIT_KEY):
        matches = by_unit.get(key)
        if key[1] != "G" or matches is None or len(matches) != 1:
            continue
        if (
            matches.iloc[0].well_status != "producing"
            or set(group.production_month) != months
            or group.gas_mcf.isna().any()
        ):
            continue
        # Calendar-day gas rate: volume / actual days, no assumed operating uptime.
        rates.append(float(group.gas_mcf.sum()) / days)
    producing = int(wells.well_status.eq("producing").sum())
    status = (
        "NOT_EVALUATED"
        if not rates
        else ("COMPLETE" if len(rates) == producing else "PARTIAL")
    )
    return {
        "gas_rate_eligible_well_count": len(rates),
        "gas_per_well_metrics_status": status,
        "gas_mcfd_per_well_median": median(rates) if rates else None,
        # RRC PDQ FAQ, oil vs condensate (accessed 2026-10-19): gas-well
        # condensate is not crude oil. PDQ oil leases lack well allocation.
        # A threshold cannot supply the missing oil-well production evidence.
        "per_well_metrics_status": "NOT_EVALUATED",
        "bopd_per_well_median": None,
        "stripper_share": None,
    }


def _operator_row(number, p, w, names, by_core, months, days, policy):
    recent = p[p.production_month.isin(months)]
    flags = []
    variants = sorted(names.get(number, ()))
    cores = sorted({normalize_name(name) for name in variants} - {""})
    collisions = (
        sorted(set().union(*(by_core[core] for core in cores)) - {number})
        if cores
        else []
    )
    if len(cores) > 1:
        flags.append("operator_name_ambiguous")
    if collisions:
        flags.append("operator_name_collision")
    if not cores:
        flags.append("operator_name_missing")
    if policy.stripper_bopd is None:
        flags.append("stripper_threshold_missing")
    count = len(w) if len(w) else None
    if count is None:
        flags.append("well_inventory_missing")
    usable = bool(len(recent)) and all(
        _complete(group, months) for _, group in recent.groupby(UNIT_KEY)
    )
    # Every current inventory unit must also have observed reports in the window.
    # Historical-only units do not establish a current reporting obligation.
    usable = usable and set(map(tuple, w[UNIT_KEY].to_numpy())).issubset(
        set(map(tuple, recent[UNIT_KEY].to_numpy()))
    )
    if not usable:
        flags.append("last12_incomplete")
    positive = p[(p.oil_bbl.fillna(0) > 0) | (p.gas_mcf.fillna(0) > 0)]
    fields = w.loc[w.field_no.ne(""), ["district", "field_no"]]
    hhi = None
    if count and len(fields) == count:
        # DOJ, Herfindahl-Hirschman Index (updated 2024), sum of squared shares.
        # Here shares are fractions of inventory wells per district/field, not markets.
        hhi = float((fields.value_counts().div(count) ** 2).sum())
    oil, gas, water = (_total(recent, col) for col in VOLUMES)
    per_well = _well_metrics(w, recent, months, days)
    if per_well["per_well_metrics_status"] != "COMPLETE":
        flags.extend(
            ["per_well_oil_allocation_unavailable", "stripper_allocation_unavailable"]
        )
    if water is None:
        flags.append("water_unavailable")
    if hhi is None:
        flags.append("field_concentration_unavailable")
    row = {
        "operator_no": number,
        "operator_name": variants[0] if variants else "",
        "normalized_name": cores[0] if len(cores) == 1 else "",
        "operator_name_variants": variants,
        "name_collision_operator_nos": collisions,
        "districts": sorted(set(p.district) | set(w.district)),
        "counties": sorted((set(p.county) | set(w.county)) - {""}),
        "well_count_total": count,
        "well_count_producing": (
            int(w.well_status.eq("producing").sum()) if count else None
        ),
        "well_count_inactive": (
            int(w.well_status.eq("inactive").sum()) if count else None
        ),
        "well_count_other": (
            int((~w.well_status.isin(["producing", "inactive"])).sum())
            if count
            else None
        ),
        "oil_bbl_last12": oil,
        "gas_mcf_last12": gas,
        "water_bbl_last12": water,
        "usable_last12": bool(usable),
        # Volume ratio, not an inferred water cut when water measurements are absent.
        "water_cut_est": (
            water / (oil + water)
            if oil is not None and water is not None and oil + water > 0
            else None
        ),
        "first_production": positive.production_month.min() if len(positive) else None,
        "last_production": positive.production_month.max() if len(positive) else None,
        "field_count": len(fields.drop_duplicates()) if count else None,
        "field_concentration": hhi,
        "operator_size_band": _size_band(count, policy),
        "ownership_basis": "operator_of_record_only",
        "quality_flags": sorted(flags),
    }
    row.update(per_well)
    return row


def build_operator_registry(
    production: pd.DataFrame, wells: pd.DataFrame, policy: RegistryPolicy
) -> RegistryResult:
    """Aggregate validated canonical rows, keeping every operator number separate.

    Wells are one selected current snapshot; production remains attributed to
    the operator reported in each month. Future months cannot leak into output.
    Coverage refers only to supplied data, never to the statewide population.
    """
    p, w = validate_operator_inputs(production, wells)
    end = pd.Period(policy.as_of, freq="M")
    p = p[p.production_month <= str(end)]
    periods = [end - offset for offset in range(WINDOW_MONTHS)]
    months = {str(period) for period in periods}
    days = sum(calendar.monthrange(period.year, period.month)[1] for period in periods)
    names, cores = _names(p, w)
    numbers = sorted(set(p.operator_no) | set(w.operator_no))
    p_groups = dict(tuple(p.groupby("operator_no")))
    w_groups = dict(tuple(w.groupby("operator_no")))
    rows = [
        _operator_row(
            number,
            p_groups.get(number, p.iloc[:0]),
            w_groups.get(number, w.iloc[:0]),
            names,
            cores,
            months,
            days,
            policy,
        )
        for number in numbers
    ]
    registry = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    for column in (
        "well_count_total",
        "well_count_producing",
        "well_count_inactive",
        "well_count_other",
        "field_count",
        "gas_rate_eligible_well_count",
    ):
        registry[column] = registry[column].astype("Int64")
    well_units = set(map(tuple, w[["operator_no", *UNIT_KEY]].to_numpy()))
    prod_units = set(map(tuple, p[["operator_no", *UNIT_KEY]].to_numpy()))
    quality = {
        "operator_count": len(registry),
        "operators_usable_last12": sum(row["usable_last12"] for row in rows),
        "operators_by_size_band": dict(
            sorted(Counter(row["operator_size_band"] for row in rows).items())
        ),
        "operators_by_district": dict(
            sorted(Counter(d for row in rows for d in row["districts"]).items())
        ),
        "production_rows_by_basis": dict(
            sorted(
                Counter(p.oil_gas_code.map({"O": "oil_lease", "G": "gas_well"})).items()
            )
        ),
        "production_units_by_basis": {
            kind: len(p[p.oil_gas_code == code][UNIT_KEY].drop_duplicates())
            for code, kind in (("O", "oil_lease"), ("G", "gas_well"))
        },
        "unmatched_production_units": len(prod_units - well_units),
        "unmatched_well_units": len(well_units - prod_units),
        "name_collision_count": sum(len(numbers) > 1 for numbers in cores.values()),
        "name_ambiguity_count": sum(
            "operator_name_ambiguous" in row["quality_flags"] for row in rows
        ),
        "name_variant_operator_count": sum(
            len(row["operator_name_variants"]) > 1 for row in rows
        ),
        "source_ids": ["production_pdq", "wellbore_query"],
        "ownership_basis": "operator_of_record_only",
        "coverage_scope": "supplied_snapshots_only",
        "window_start": str(min(periods)),
        "window_end": str(end),
        "window_calendar_days": days,
        "gas_rate_eligible_well_count": sum(
            row["gas_rate_eligible_well_count"] for row in rows
        ),
        "producing_wells_without_gas_rates": sum(
            (row["well_count_producing"] or 0) - row["gas_rate_eligible_well_count"]
            for row in rows
        ),
        "last12_production_rows_by_basis": dict(
            sorted(
                Counter(
                    p.loc[p.production_month.isin(months), "oil_gas_code"].map(
                        {"O": "oil_lease", "G": "gas_well"}
                    )
                ).items()
            )
        ),
    }
    return RegistryResult(registry, quality)
