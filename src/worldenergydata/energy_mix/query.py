"""Select caller-normalized offshore wind observations without network access."""

import csv
import io
from collections.abc import Iterable
from decimal import (
    MAX_EMAX,
    MIN_EMIN,
    Context,
    Decimal,
    DecimalException,
    Inexact,
    localcontext,
)

from .irena import COLUMNS, load_export

# BIPM, SI Brochure, 9th ed. (2019), v4.01 (2026), section 3, table 7:
# giga / mega = 10**9 / 10**6 = 1000; the hour is unchanged.
# https://www.bipm.org/documents/20126/41483022/SI-Brochure-9.pdf
GWH_TO_MWH = Decimal(1000)


def query_export(
    raw: bytes,
    *,
    countries: Iterable[str] | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    generation_unit: str = "GWh",
) -> bytes:
    """Return CSV selected by case-insensitive country and inclusive year bounds.

    Validate the entire input before selecting rows. Preserve row order, source
    citations, capacity in MW and blank measurements. An empty selection yields
    a header only. MWh output uses ``generation_mwh`` instead of
    ``generation_gwh`` and is a query result, not the loader's input schema.
    No country totals, country-code inference or generation estimates are made.
    """
    if generation_unit not in ("GWh", "MWh"):
        raise ValueError("Generation unit must be GWh or MWh")
    for bound in (start_year, end_year):
        if bound is not None and type(bound) is not int:
            raise ValueError("Year bounds must be integers")
    if start_year is not None and end_year is not None and start_year > end_year:
        raise ValueError("Start year must not exceed end year")
    selected_countries = None
    if countries is not None:
        if isinstance(countries, str):
            raise ValueError("Countries must be an iterable of country names")
        selected_countries = set()
        for country in countries:
            if (
                not isinstance(country, str)
                or not country
                or country != country.strip()
            ):
                raise ValueError(
                    "Country names must be nonempty without outer whitespace"
                )
            selected_countries.add(country.casefold())

    load_export(raw)
    # Read validated text again to retain supplied decimal precision and keys.
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    generation_column = (
        "generation_mwh" if generation_unit == "MWh" else "generation_gwh"
    )
    columns = [
        generation_column if name == "generation_gwh" else name for name in COLUMNS
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in reader:
        year = int(row["year"])
        if (
            selected_countries is not None
            and row["country"].casefold() not in selected_countries
        ):
            continue
        if start_year is not None and year < start_year:
            continue
        if end_year is not None and year > end_year:
            continue
        if generation_unit == "MWh":
            value = row.pop("generation_gwh")
            if value:
                # Exact decimal multiplication: retain all supplied digits plus
                # the digits of the SI scale factor, independent of ambient context.
                context = Context(
                    prec=len(value) + len(str(GWH_TO_MWH)),
                    Emax=MAX_EMAX,
                    Emin=MIN_EMIN,
                )
                context.traps[Inexact] = True
                try:
                    with localcontext(context):
                        # Scientific notation avoids expanding tiny observations
                        # into arbitrarily large runs of leading zeroes.
                        value = str(Decimal(value) * GWH_TO_MWH)
                except DecimalException as error:
                    raise ValueError(
                        "Generation cannot be represented exactly in MWh"
                    ) from error
                if "." in value and "E" not in value:
                    value = value.rstrip("0").rstrip(".")
            row[generation_column] = value
        writer.writerow(row)
    return output.getvalue().encode("utf-8")
