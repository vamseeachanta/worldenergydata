"""
ABOUTME: The one way to reduce raw cost rows to an annual series — with the filters that keep it honest.
ABOUTME: Every consumer (normalization, trend fitting, the report) goes through here, so none can forget a filter.

Why this module exists
----------------------
Two mistakes are very easy to make with this dataset, and both silently produce
a number that looks fine and is wrong. They are not hypothetical: the first
draft of the analysis made both, and the AHTS series came out claiming day rates
had beaten CPI by 8.2 percentage points a year — an artifact, not a finding.

**1. Currency mixing.** The Seabrokers North Sea spot rates are quoted in GBP and
are stored as GBP (converting them would inject an FX rate no source states). If
an aggregation does not filter on currency, £47,017 is silently averaged in as
$47,017 and the series is nonsense.

**2. Figure-type mixing.** A contractor's ``fleet_average`` is a backlog-weighted
average of rigs *already under contract* — it lags the market and is
survivorship-biased upward, because stacked rigs are excluded and expensive
legacy contracts persist for years. A ``single_fixture`` is the market-clearing
price. Transocean's ultra-deepwater fleet average read **$484k in Q1-2016 while
its own new fixtures were signing at $170k**. Average those together and you
produce a cost history that never happened.

So there is exactly one function that turns rows into a series, it filters on
both by default, and everything downstream calls it. A filter you cannot forget
is worth more than a warning in a docstring.
"""

from __future__ import annotations

from typing import Optional

from worldenergydata.cost.timeseries.schema import (
    CostComponent,
    CostObservation,
    FigureType,
    Provenance,
)

__all__ = [
    "MARKET_RATE_LENS",
    "FIXTURE_LENS",
    "annual_means",
]

#: The "what did the market charge, on average, that year" lens: contractor
#: backlog-weighted averages plus third-party averages of awards. This is the
#: default lens for the cost basis, because a field-development deck wants the
#: rate a project would actually have paid across a campaign, not the single
#: highest print of the year.
MARKET_RATE_LENS: frozenset[FigureType] = frozenset(
    {FigureType.FLEET_AVERAGE, FigureType.MARKET_AVERAGE, FigureType.SPOT_RATE}
)

#: The "what did someone actually sign, at the margin" lens. Leading-edge.
FIXTURE_LENS: frozenset[FigureType] = frozenset({FigureType.SINGLE_FIXTURE})


def annual_means(
    rows: list[CostObservation],
    component: CostComponent,
    *,
    currency: str = "USD",
    figure_types: Optional[frozenset[FigureType]] = MARKET_RATE_LENS,
    region: Optional[str] = "global",
    sourced_only: bool = True,
) -> dict[int, float]:
    """Collapse rows for one component to one value per year.

    Filters, in order:

    * ``sourced_only`` — a fitted value must never become an input to a fit, nor
      an endpoint of an inflation verdict. That would be circular.
    * ``currency`` — see the module docstring. Never aggregate across currencies.
    * ``figure_types`` — see the module docstring. Never aggregate across lenses.
    * ``region`` — the third mixing hazard, and the subtlest. The AHTS series has
      exactly one Gulf-of-Mexico row (a point-in-time March-2000 figure, taken at
      a regional trough) sitting in an otherwise global series. Left unfiltered it
      becomes the *first* point of the window and anchors a 26-year growth rate to
      a number that is not comparable to its endpoint — inflating the apparent
      real growth by several points a year. Regional and global series are
      different series. ``None`` disables the filter.

    Pass ``None`` to any filter to disable it — but only after thinking about
    which of the above you are re-admitting.

    Years with multiple observations are averaged, so a heavily-reported year
    does not dominate purely by having been written about more often.
    """
    buckets: dict[int, list[float]] = {}
    for obs in rows:
        if obs.component is not component or obs.value is None:
            continue
        if sourced_only and obs.provenance is not Provenance.SOURCED:
            continue
        if obs.currency != currency:
            continue
        if figure_types is not None and obs.figure_type not in figure_types:
            continue
        if region is not None and obs.region != region:
            continue
        buckets.setdefault(obs.year, []).append(obs.value)
    return {year: sum(v) / len(v) for year, v in sorted(buckets.items())}
