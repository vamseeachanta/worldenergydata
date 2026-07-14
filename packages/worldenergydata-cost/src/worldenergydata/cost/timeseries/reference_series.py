"""
ABOUTME: Pulls the CPI / PPI / oil-price reference series the cost-basis deck deflates against.
ABOUTME: Every series comes from a primary public endpoint (FRED), so no figure here is hand-entered.

Why fetch rather than vendor a CSV
----------------------------------
These series are the *yardsticks* for issue #844's scope addition #1 (inflation
normalization). A hand-typed CPI table is a fabrication risk for no benefit:
FRED publishes every one of these as a stable, public, no-key CSV endpoint. So
the deflators are pulled, not typed, and the refresh procedure re-pulls them.

Every series ID below was verified to return HTTP 200 with real observations
before being committed — see ``docs/modules/cost/REFRESH_PROCEDURE.md``. Series
that 404'd during research (``WPU1301``, ``CUSR0000SA0``, ``WPS1301``) were
dropped rather than guessed at.

Monthly → annual
----------------
We reduce to a calendar-year mean. For a *cost basis* that is the right
reduction: a project spending through a year pays something close to the year's
average rate, not its December print. Years with fewer than 12 monthly
observations (i.e. the current, incomplete year) are still emitted but flagged
in ``notes`` as partial, because silently averaging 5 months into an "annual"
figure and not saying so is how a deck starts lying to you.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Optional

from worldenergydata.cost.timeseries.schema import (
    CostComponent,
    CostObservation,
    DisclosureConfidence,
    FigureType,
    PriceBasis,
    Provenance,
    SourcePriority,
)

__all__ = [
    "ReferenceSeriesSpec",
    "REFERENCE_SERIES",
    "fetch_fred_series",
    "annualize",
    "build_reference_observations",
]

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
FRED_PAGE = "https://fred.stlouisfed.org/series/{series_id}"


@dataclass(frozen=True)
class ReferenceSeriesSpec:
    """One reference series we pull and the cost component it maps onto."""

    series_id: str
    component: CostComponent
    title: str
    unit: str
    publisher: str
    #: True for price levels (CPI/PPI indices); False for $/bbl oil prices.
    is_index: bool


# Verified live (HTTP 200 + real observations) on 2026-07-14. Four candidate
# IDs were checked and rejected as 404 — they are NOT in this list. Do not add
# a series here without fetching it first.
REFERENCE_SERIES: tuple[ReferenceSeriesSpec, ...] = (
    ReferenceSeriesSpec(
        series_id="CPIAUCSL",
        component=CostComponent.INDEX_CPI,
        title="CPI for All Urban Consumers: All Items in U.S. City Average",
        unit="index_1982_84_eq_100",
        publisher="U.S. Bureau of Labor Statistics via FRED",
        is_index=True,
    ),
    ReferenceSeriesSpec(
        series_id="PCU213111213111",
        component=CostComponent.INDEX_PPI_DRILLING,
        title="PPI by Industry: Drilling Oil and Gas Wells (NAICS 213111)",
        unit="index_dec_1985_eq_100",
        publisher="U.S. Bureau of Labor Statistics via FRED",
        is_index=True,
    ),
    ReferenceSeriesSpec(
        series_id="PCU213112213112",
        component=CostComponent.INDEX_PPI_SUPPORT,
        title="PPI by Industry: Support Activities for Oil and Gas Operations (NAICS 213112)",
        unit="index_dec_1985_eq_100",
        publisher="U.S. Bureau of Labor Statistics via FRED",
        is_index=True,
    ),
    ReferenceSeriesSpec(
        series_id="PCU333132333132",
        component=CostComponent.INDEX_PPI_MACHINERY,
        title="PPI by Industry: Oil and Gas Field Machinery and Equipment (NAICS 333132)",
        unit="index_1965_eq_100",
        publisher="U.S. Bureau of Labor Statistics via FRED",
        is_index=True,
    ),
    ReferenceSeriesSpec(
        series_id="MCOILBRENTEU",
        component=CostComponent.OIL_PRICE_BRENT,
        title="Crude Oil Prices: Brent — Europe",
        unit="usd_per_bbl",
        publisher="U.S. EIA via FRED",
        is_index=False,
    ),
    ReferenceSeriesSpec(
        series_id="MCOILWTICO",
        component=CostComponent.OIL_PRICE_WTI,
        title="Crude Oil Prices: West Texas Intermediate (WTI) — Cushing, Oklahoma",
        unit="usd_per_bbl",
        publisher="U.S. EIA via FRED",
        is_index=False,
    ),
)


def fetch_fred_series(series_id: str, timeout: int = 60) -> list[tuple[date, float]]:
    """Fetch one FRED series as ``(observation_date, value)`` pairs.

    FRED encodes a missing observation as ``"."`` — those are dropped, not
    zero-filled. A gap in the source stays a gap here.
    """
    url = FRED_CSV.format(series_id=series_id)
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
        if response.status != 200:
            raise RuntimeError(f"FRED returned HTTP {response.status} for {series_id}")
        payload = response.read().decode("utf-8")

    reader = csv.DictReader(io.StringIO(payload))
    if reader.fieldnames is None or len(reader.fieldnames) < 2:
        raise RuntimeError(f"unexpected FRED CSV shape for {series_id}")
    date_col, value_col = reader.fieldnames[0], reader.fieldnames[1]

    out: list[tuple[date, float]] = []
    for row in reader:
        raw = (row.get(value_col) or "").strip()
        if raw in ("", "."):  # FRED's missing-value sentinel
            continue
        out.append((date.fromisoformat(row[date_col]), float(raw)))
    if not out:
        raise RuntimeError(f"FRED series {series_id} returned no observations")
    return out


def annualize(
    observations: list[tuple[date, float]],
) -> dict[int, tuple[float, int]]:
    """Reduce monthly observations to ``{year: (mean_value, n_months)}``.

    ``n_months`` is returned alongside the mean so callers can flag partial
    years rather than passing an incomplete average off as an annual one.
    """
    buckets: dict[int, list[float]] = defaultdict(list)
    for observed_on, value in observations:
        buckets[observed_on.year].append(value)
    return {
        year: (sum(values) / len(values), len(values))
        for year, values in sorted(buckets.items())
    }


def build_reference_observations(
    accessed_date: date,
    start_year: int = 1990,
    end_year: Optional[int] = None,
    specs: tuple[ReferenceSeriesSpec, ...] = REFERENCE_SERIES,
) -> list[CostObservation]:
    """Fetch every reference series and emit them as ``CostObservation`` rows.

    These are all ``SOURCED`` with ``source_priority=REGULATOR_DOCUMENT``: BLS
    and EIA are statistical agencies, which is the strongest source class this
    dataset has. The ``quoted_text`` is the machine-readable equivalent of a
    quote — the series title plus the literal observation — since there is no
    prose sentence to quote from a CSV endpoint.
    """
    rows: list[CostObservation] = []
    for spec in specs:
        annual = annualize(fetch_fred_series(spec.series_id))
        for year, (mean_value, n_months) in annual.items():
            if year < start_year:
                continue
            if end_year is not None and year > end_year:
                continue

            partial = n_months < 12
            note = f"Calendar-year mean of {n_months} monthly observations."
            if partial:
                note += (
                    " PARTIAL YEAR — fewer than 12 months published; treat as"
                    " provisional and re-pull on next refresh."
                )

            rows.append(
                CostObservation(
                    year=year,
                    component=spec.component,
                    value=round(mean_value, 4),
                    unit=spec.unit,
                    currency="USD",
                    # An index has no price basis; an oil price is money-of-the-day.
                    price_basis=PriceBasis.NOMINAL,
                    figure_type=FigureType.INDEX if spec.is_index else FigureType.MARKET_AVERAGE,
                    region="US" if spec.is_index else "global",
                    provenance=Provenance.SOURCED,
                    source_title=f"{spec.title} ({spec.series_id})",
                    source_url=FRED_PAGE.format(series_id=spec.series_id),
                    page_reference=f"FRED series {spec.series_id}, annual mean of monthly observations",
                    quoted_text=(
                        f"{spec.title} — {spec.series_id}: "
                        f"{year} mean = {mean_value:.4f} ({n_months} monthly obs), "
                        f"published by {spec.publisher}."
                    ),
                    accessed_date=accessed_date,
                    confidence=DisclosureConfidence.HIGH,
                    source_priority=SourcePriority.REGULATOR_DOCUMENT,
                    notes=note,
                )
            )
    return rows
