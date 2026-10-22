"""Production measurement contracts; no missing-to-zero substitutions.

Sources: NIST SP 811 (2008), section 4/Table 5 and section 7.11;
https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf
Python calendar documentation (2026), monthrange/isleap:
https://docs.python.org/3/library/calendar.html
Rate * duration = volume follows the definition of an average daily rate,
using the quantity-equation approach in NIST section 7.11.
"""

import calendar
import math
import re
from datetime import date

import pandas as pd

RATE = "rate_per_day"
VOLUME = "volume_per_period"

# NIST SP 811 (2008), section 4, Table 5: kilo = 10**3.
KILO = 1_000.0
# Exact spellings form the supported contract; ambiguous Mbbl is not an alias.
UNITS = {
    "Barrels": (1.0, VOLUME),
    "bbl": (1.0, VOLUME),
    "Thousand Barrels": (KILO, VOLUME),
    "kbbl": (KILO, VOLUME),
    "Barrels per Day": (1.0, RATE),
    "bbl/day": (1.0, RATE),
    "bopd": (1.0, RATE),
    "Thousand Barrels per Day": (KILO, RATE),
    "kbd": (KILO, RATE),
}


def declared_unit(record, *, schema_unit=None):
    """Read an explicit unit, or the unit declared by a typed field schema.

    A generic value has no schema unit. For typed fields, a row declaration
    must agree with the schema scale and basis; it cannot reinterpret values.
    """
    unit = record.get("unit", schema_unit)
    if not isinstance(unit, str) or unit not in UNITS:
        raise ValueError("Unknown or absent production unit")
    scale, basis = UNITS[unit]
    if schema_unit is not None and (scale, basis) != UNITS[schema_unit]:
        raise ValueError("Production unit conflicts with named field schema")
    if "basis" in record and record["basis"] != basis:
        raise ValueError("Production basis conflicts with unit")
    return unit, scale, basis


def monthly_period(period):
    """Validate YYYY-MM and return Gregorian year, month and duration."""
    if not isinstance(period, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", period):
        raise ValueError("Monthly period must be YYYY-MM")
    year, month = map(int, period.split("-"))
    try:
        date(year, month, 1)
    except ValueError as exc:
        raise ValueError("Invalid calendar period") from exc
    return year, month, calendar.monthrange(year, month)[1]


def number_or_missing(value, *, signed=False):
    """Absent/NaN is missing; malformed, infinite and negative output fail.

    Signed quantities (DPR net-change components) explicitly opt in. Zero is
    the physical lower bound for an unsigned production volume/rate or count,
    not an acceptance tolerance or an imputed measurement.
    """
    if value is None or pd.isna(value):
        return math.nan
    if isinstance(value, bool):
        raise TypeError("Boolean is not a production number")
    number = float(value)
    if not math.isfinite(number) or (not signed and number < 0):
        raise ValueError("Production number must be finite and nonnegative")
    return number


def annual_volumes(frame, entity, columns):
    """Aggregate monthly bbl columns; incomplete years have unknown totals.

    ``columns`` names volume columns, never rates. The caller must normalize
    units first. A separate reported subtotal preserves partial information;
    missing-month tuples distinguish absent rows, null values and true zeros.
    Duplicate months fail rather than double count. No input frame is mutated.
    """
    output = [entity, "year", "unit", "basis", "status"]
    for column in columns:
        output.extend(
            [column, f"reported_{column}", column.replace("_bbl", "_missing_months")]
        )
    if frame.empty:
        return pd.DataFrame(columns=output)
    df = frame.copy()
    # Revalidate calendar coordinates even for a directly supplied frame.
    for year, month in zip(df["year"], df["month"]):
        monthly_period(f"{year:04d}-{month:02d}")
    if df.duplicated([entity, "year", "month"]).any():
        raise ValueError("Duplicate entity/month production records")
    rows = []
    # Python calendar (2026), month_name: January through December, indices 1..12.
    expected_months = set(range(1, len(calendar.month_name)))
    for (name, year), group in df.groupby([entity, "year"], dropna=False):
        row = {
            entity: name,
            "year": year,
            "unit": "bbl",
            "basis": VOLUME,
            "status": "COMPLETE",
        }
        for column in columns:
            values = group[column].map(number_or_missing)
            reported_months = set(group.loc[values.notna(), "month"])
            missing = tuple(sorted(expected_months - reported_months))
            subtotal = values.sum(min_count=1)
            row[column] = math.nan if missing else subtotal
            row[f"reported_{column}"] = subtotal
            row[column.replace("_bbl", "_missing_months")] = missing
            if missing:
                row["status"] = "MISSING"
        rows.append(row)
    return pd.DataFrame(rows, columns=output)
