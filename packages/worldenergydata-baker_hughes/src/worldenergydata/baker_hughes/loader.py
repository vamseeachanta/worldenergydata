# ABOUTME: Excel parser for Baker Hughes rig count data (WRK-1190).
# ABOUTME: Handles pivot table (detailed metadata) and summary (state counts) formats.

"""Baker Hughes rig count Excel loaders.

Two formats:
  - Pivot table: per-rig-record with full metadata (basin, county, trajectory, depth)
  - Summary: wide-format state x date counts, melted to long format
"""

import logging
import math
import re
from decimal import Decimal, DecimalException, InvalidOperation
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Column mapping: Baker Hughes Excel → standardized output
_PIVOT_COLUMN_MAP = {
    "PublishDate": "date",
    "Country": "country",
    "StateProvince": "state",
    "County": "county",
    "BasinName": "basin",
    "DrillFor": "drill_for",
    "Location": "location",
    "Trajectory": "trajectory",
    "WellType": "well_type",
    "WellDepth": "well_depth_ft",
    "WaterDepth": "water_depth_ft",
    "RigCount": "rig_count",
}


# Issue #1334: accept decimal/scientific notation with no locale/grouping
# inference. Decimal alone would silently accept underscore grouping.
_NUMERIC_TOKEN = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
)


def _decimal_number(value: object) -> Decimal:
    text = str(value).strip()
    if isinstance(value, bool) or not _NUMERIC_TOKEN.fullmatch(text):
        raise InvalidOperation
    return Decimal(text)


def _validated_counts(values: pd.Series) -> pd.Series:
    """Reject rather than repair counts (issue #1334, F1/F2/F11/F12).

    The count domain is the nonnegative integers; zero is a true count,
    never an imputed missing value. Decimal avoids a float round trip.
    """
    counts = []
    for row, value in values.items():
        try:
            number = _decimal_number(value)
        except InvalidOperation:
            number = Decimal("NaN")
        if (
            isinstance(value, bool)
            or not number.is_finite()
            or number < 0
            or number != number.to_integral_value()
        ):
            raise ValueError(
                f"rig_count row {row}: expected a nonnegative integer; rejected"
            )
        counts.append(int(number))
    return pd.Series(counts, index=values.index, name=values.name)


# NIST SP 811 (2008), Appendix B.6: international foot, defined by the
# 1959 agreement. https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf
_METRES_PER_FOOT = Decimal("0.3048")


def _validated_depths(df: pd.DataFrame, depth_unit: str | None) -> dict[str, str]:
    """Validate source units and values before assigning feet-labelled columns.

    Empty cells are absent depths; all other cells must be numeric, finite
    and nonnegative (issue #1334, F3--F6 input contract). Unit suffixes are
    declarations, not an inference from numeric magnitude.
    """
    if depth_unit is not None and depth_unit not in {"ft", "m"}:
        raise ValueError("depth_unit must be 'ft' or 'm'")
    units = {}
    for source in ("WellDepth", "WaterDepth"):
        columns = [c for c in (source, source + "_ft", source + "_m") if c in df]
        if len(columns) != 1:
            raise ValueError(f"{source}: exactly one source column is required")
        column = columns[0]
        tagged_unit = column.removeprefix(source + "_") if column != source else None
        if tagged_unit and depth_unit and tagged_unit != depth_unit:
            raise ValueError(f"{source}: source/declaration unit mismatch")
        unit = tagged_unit or depth_unit
        if unit is None:
            raise ValueError(f"depth_unit is required for ambiguous {source} header")
        output = _PIVOT_COLUMN_MAP[source]
        values = []
        for row, value in df[column].items():
            if value is None or (isinstance(value, str) and not value.strip()):
                values.append(float("nan"))
                continue
            try:
                number = _decimal_number(value)
                if not number.is_finite() or number < 0 or isinstance(value, bool):
                    raise ValueError
                # Output remains international feet; convert before labelling.
                converted = float(number / _METRES_PER_FOOT if unit == "m" else number)
                # A nonzero input must not silently underflow to zero.
                if not math.isfinite(converted) or (number != 0 and converted == 0):
                    raise ValueError
            except (DecimalException, ValueError, OverflowError):
                raise ValueError(
                    f"{output} row {row}: expected finite nonnegative depth; rejected"
                ) from None
            values.append(converted)
        df[output] = pd.Series(values, index=df.index, dtype=float)
        df.drop(columns=[column], inplace=True)
        units[output] = unit
    return units


def load_pivot_table(
    path: str | Path,
    *,
    country: str | None = None,
    basin: str | None = None,
    sheet_name: str = "Pivot Table",
    depth_unit: str | None = None,
) -> pd.DataFrame:
    """Load Baker Hughes NA pivot table Excel into a standardized DataFrame.

    Args:
        path: Path to the pivot table Excel file.
        country: Filter to a specific country (e.g. 'UNITED STATES').
        basin: Filter to a specific basin (e.g. 'PERMIAN').
        sheet_name: Excel sheet name to read.
        depth_unit: Source depth unit, 'ft' (international feet) or 'm'.
            Required for WellDepth/WaterDepth without a unit suffix. Headers
            WellDepth_ft/WellDepth_m and WaterDepth_ft/WaterDepth_m declare
            units per field; a conflicting explicit declaration is rejected.

    Returns:
        DataFrame with standardized columns: date, country, state, county,
        basin, drill_for, location, trajectory, well_type, well_depth_ft,
        water_depth_ft, rig_count. Depth outputs are international feet after
        conversion. DataFrame attrs['numeric_validation'] records the source
        and output units and count policy. Invalid counts/depths raise
        ValueError with field and row; empty depth cells remain NaN. Values
        outside finite/nonzero float representation are rejected.
    """
    df = pd.read_excel(path, sheet_name=sheet_name, keep_default_na=False, dtype=object)
    source_units = _validated_depths(df, depth_unit)
    df = df.rename(columns=_PIVOT_COLUMN_MAP)

    df["date"] = pd.to_datetime(df["date"])
    df["rig_count"] = _validated_counts(df["rig_count"])
    df.attrs["numeric_validation"] = {
        "rig_count": "nonnegative_integer_reject",
        "source_depth_units": source_units,
        "output_depth_unit": "ft",
        "depth_policy": "empty_cell_missing_otherwise_finite_nonnegative_reject",
    }

    if country is not None:
        df = df[df["country"] == country].copy()
    if basin is not None:
        df = df[df["basin"] == basin].copy()

    logger.info("Loaded pivot table: %d records from %s", len(df), path)
    return df.reset_index(drop=True)


def load_summary(
    path: str | Path,
    *,
    sheet_name: str = "Rigs by State",
) -> pd.DataFrame:
    """Load Baker Hughes summary (rigs by state) Excel into long format.

    The summary Excel has states as rows and dates as columns. This function
    melts the wide format into long format with columns: state, date, rig_count.

    Args:
        path: Path to the summary Excel file.
        sheet_name: Excel sheet name to read.

    Returns:
        DataFrame with columns: state, date, rig_count. Counts must be
        nonnegative integers; invalid/missing/fractional inputs raise ValueError
        with field and melted row index. No locale separators are inferred.
        DataFrame attrs['numeric_validation'] records the rejection policy.
    """
    df = pd.read_excel(path, sheet_name=sheet_name, keep_default_na=False, dtype=object)

    state_col = df.columns[0]
    date_cols = [c for c in df.columns if c != state_col]

    melted = df.melt(
        id_vars=[state_col],
        value_vars=date_cols,
        var_name="date",
        value_name="rig_count",
    )
    melted = melted.rename(columns={state_col: "state"})
    melted["date"] = pd.to_datetime(melted["date"])
    melted["rig_count"] = _validated_counts(melted["rig_count"])
    melted.attrs["numeric_validation"] = {"rig_count": "nonnegative_integer_reject"}

    logger.info("Loaded summary: %d records from %s", len(melted), path)
    return melted.reset_index(drop=True)
