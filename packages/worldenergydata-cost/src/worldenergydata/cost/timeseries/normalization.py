"""
ABOUTME: Inflation normalization — nominal→real on a dual deflator basis (CPI and UCCI).
ABOUTME: Implements issue #844 scope addition #1, including the "did it beat inflation?" comparison.

The deflator policy (this is the part to argue with)
----------------------------------------------------
Issue #844 addition #1 requires each component published in **nominal and real**
terms against **both** a general deflator and a sector deflator. We implement
exactly two deflator bases and refuse to silently pick one:

* ``CPI``  — U.S. CPI-U, all items (FRED ``CPIAUCSL``). The general-purchasing-
  power question: *did this cost outrun the broad price level?* This is the
  deflator a CFO means by "real".
* ``UCCI`` — IHS/S&P Upstream Capital Costs Index. The sector question: *did
  this component outrun the upstream capital-goods bundle it sits inside?* A
  rig day rate can beat CPI handily and still be cheap relative to the rest of
  the upstream supply chain; only the sector deflator shows that.

Deflating by CPI answers a different question than deflating by UCCI, and the
two routinely disagree in sign over a given window. That disagreement is a
finding, not an error — so we publish both and never average them.

The UCCI honesty problem
------------------------
UCCI is a **proprietary S&P Global product**. There is no public endpoint; only
scattered values quoted in press releases, presentations and papers are
sourceable. So the UCCI deflator is inherently an *anchor-and-interpolate*
series, not a measured one.

We handle that by construction, not by pretending:

* Sourced anchor years carry ``Provenance.SOURCED`` with their citation.
* Gap years are linearly interpolated between anchors and carry
  ``Provenance.FITTED``, and every value deflated through an interpolated year
  is reported with ``deflator_is_interpolated=True``.
* We never extrapolate UCCI beyond the sourced anchor range. Outside it, the
  UCCI-real series is simply **not published** — ``to_real`` returns ``None``
  rather than inventing a deflator. A missing real series is a correct answer.

CPI has no such problem: it is a complete monthly public series.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from worldenergydata.cost.timeseries.schema import CostComponent, CostObservation
from worldenergydata.cost.timeseries.series import MARKET_RATE_LENS, annual_means

__all__ = [
    "MAX_INTERPOLATION_SPAN",
    "DeflatorBasis",
    "Deflator",
    "build_deflator",
    "to_real",
    "RealSeriesPoint",
    "deflate_series",
    "InflationVerdict",
    "compare_against_inflation",
]


class DeflatorBasis(str, Enum):
    """Which yardstick a real figure was deflated against."""

    CPI = "cpi"
    UCCI = "ucci"


@dataclass(frozen=True)
class Deflator:
    """A deflator series: index value by year, plus which years were inferred.

    ``interpolated_years`` is carried explicitly so that every downstream real
    figure can declare whether the deflator it used was measured or inferred.
    """

    basis: DeflatorBasis
    values: dict[int, float]
    interpolated_years: frozenset[int]
    source_note: str
    #: (left_anchor, right_anchor) pairs whose gap was too wide to bridge. The
    #: years strictly between them are NOT in `values` and cannot be deflated.
    unbridged_gaps: tuple[tuple[int, int], ...] = ()

    @property
    def min_year(self) -> int:
        return min(self.values)

    @property
    def max_year(self) -> int:
        return max(self.values)

    def covers(self, year: int) -> bool:
        return year in self.values


#: The longest gap we will bridge by linear interpolation, in years.
#:
#: This constant is doing real work. The sourced UCCI record has an anchor at
#: 2013 (229) and its next at 2019 (182.6) — and *nothing in between*, because
#: IHS stopped publishing free index levels after 2013 and OGJ only resumed
#: printing them in 2019. A naive straight line across that gap would glide
#: smoothly from 229 to 183 and, in doing so, would erase the 2014 peak and the
#: 2016 crash — the two most important events in the entire series. It would
#: also look completely plausible.
#:
#: A five-year interpolation across a known structural break is not a estimate;
#: it is a fabrication with a trend line drawn through it. So we cap the span.
#: Gaps longer than this are left UNCOVERED, and the UCCI-real series is simply
#: not published for those years. "We don't know what happened to sector costs
#: in 2016" is the true answer, and the dataset is allowed to say it.
MAX_INTERPOLATION_SPAN = 3


def _interpolate_gaps(
    anchors: dict[int, float],
    max_span: int = MAX_INTERPOLATION_SPAN,
) -> tuple[dict[int, float], set[int], list[tuple[int, int]]]:
    """Linearly interpolate between anchor years. Never extrapolates.

    Returns ``(values, interpolated_years, unbridged_gaps)``.

    * Years outside ``[min, max]`` of the anchors are absent — we do not
      extrapolate a deflator.
    * Gaps wider than ``max_span`` are **left unbridged** and reported in
      ``unbridged_gaps`` as ``(left_anchor, right_anchor)`` pairs, so the caller
      can say out loud which years it cannot deflate. See ``MAX_INTERPOLATION_SPAN``.
    """
    if not anchors:
        return {}, set(), []
    known = sorted(anchors)
    values: dict[int, float] = dict(anchors)
    interpolated: set[int] = set()
    unbridged: list[tuple[int, int]] = []

    for left, right in zip(known, known[1:]):
        span = right - left
        if span <= 1:
            continue
        if span - 1 > max_span:
            # Too wide to bridge honestly. Leave the years out entirely.
            unbridged.append((left, right))
            continue
        rise = anchors[right] - anchors[left]
        for offset in range(1, span):
            year = left + offset
            values[year] = anchors[left] + rise * (offset / span)
            interpolated.add(year)

    return values, interpolated, unbridged


def build_deflator(
    observations: list[CostObservation],
    basis: DeflatorBasis,
) -> Deflator:
    """Build a deflator from the reference/index rows in the dataset.

    CPI comes back as a complete measured series. UCCI comes back as
    anchor-and-interpolate, with the inferred years flagged — see the module
    docstring.
    """
    component = (
        CostComponent.INDEX_CPI
        if basis is DeflatorBasis.CPI
        else CostComponent.INDEX_UCCI
    )
    # Average within a year. UCCI anchors arrive as *quarterly* prints (e.g. both
    # Q1-2012 = 227 and Q3-2012 = 230 are separately sourced), so a dict
    # comprehension keyed on year would silently keep whichever row happened to
    # come last in file order — a value that depends on sort order is not a value.
    buckets: dict[int, list[float]] = {}
    for obs in observations:
        if obs.component is component and obs.value is not None:
            buckets.setdefault(obs.year, []).append(obs.value)
    anchors = {year: sum(v) / len(v) for year, v in buckets.items()}

    if not anchors:
        raise ValueError(
            f"no {component.value} rows available — cannot build the {basis.value} "
            "deflator. Refusing to substitute a different index silently."
        )

    values, interpolated, unbridged = _interpolate_gaps(anchors)

    if basis is DeflatorBasis.CPI:
        note = (
            "U.S. CPI-U all items (FRED CPIAUCSL), calendar-year mean of monthly "
            "observations. Complete measured series; no interpolation."
        )
    else:
        note = (
            f"IHS/S&P Upstream Capital Costs Index (2000=100). Proprietary, with no "
            f"public endpoint — built from {len(anchors)} publicly sourced anchor "
            f"year(s) spanning {min(anchors)}–{max(anchors)}, with linear "
            f"interpolation across {len(interpolated)} gap year(s). Quarterly prints "
            f"within a year are averaged. NOT extrapolated beyond the anchor range."
        )
        if unbridged:
            gaps_txt = "; ".join(
                f"{left + 1}–{right - 1} (between anchors {left} and {right})"
                for left, right in unbridged
            )
            note += (
                f" NOT BRIDGED — gaps wider than {MAX_INTERPOLATION_SPAN} years are "
                f"left uncovered rather than interpolated, because a straight line "
                f"across them would erase real structural breaks: {gaps_txt}. "
                f"UCCI-real is not published for those years."
            )

    return Deflator(
        basis=basis,
        values=values,
        interpolated_years=frozenset(interpolated),
        source_note=note,
        unbridged_gaps=tuple(unbridged),
    )


def to_real(
    nominal_value: float,
    from_year: int,
    basis_year: int,
    deflator: Deflator,
) -> Optional[float]:
    """Convert a money-of-the-day figure into ``basis_year`` dollars.

        real = nominal x (deflator[basis_year] / deflator[from_year])

    Returns ``None`` — not a guess — when the deflator does not cover either
    year. A caller that needs a number must widen the deflator's sourced range,
    not paper over the gap.
    """
    if not (deflator.covers(from_year) and deflator.covers(basis_year)):
        return None
    from_index = deflator.values[from_year]
    if from_index == 0:
        return None
    return nominal_value * (deflator.values[basis_year] / from_index)


@dataclass(frozen=True)
class RealSeriesPoint:
    """One nominal figure alongside its real counterpart on a stated basis."""

    year: int
    component: CostComponent
    band: str
    nominal: float
    real: Optional[float]
    basis: DeflatorBasis
    basis_year: int
    deflator_is_interpolated: bool
    unit: str


def deflate_series(
    observations: list[CostObservation],
    deflator: Deflator,
    basis_year: int,
    components: Optional[set[CostComponent]] = None,
) -> list[RealSeriesPoint]:
    """Produce the paired nominal/real view for the requested components.

    Rows whose deflator year is uncovered still come back, with ``real=None``.
    Dropping them would quietly shrink the series and hide the coverage gap.
    """
    points: list[RealSeriesPoint] = []
    for obs in observations:
        if obs.value is None:
            continue
        if components is not None and obs.component not in components:
            continue
        points.append(
            RealSeriesPoint(
                year=obs.year,
                component=obs.component,
                band=obs.band.value,
                nominal=obs.value,
                real=to_real(obs.value, obs.year, basis_year, deflator),
                basis=deflator.basis,
                basis_year=basis_year,
                deflator_is_interpolated=(
                    obs.year in deflator.interpolated_years
                    or basis_year in deflator.interpolated_years
                ),
                unit=obs.unit,
            )
        )
    return points


@dataclass(frozen=True)
class InflationVerdict:
    """Did this component beat the yardstick, or lag it?

    ``excess_cagr_pct`` is the headline number issue #844 asks for: the annual
    percentage-point spread between the component's nominal growth and the
    deflator's own growth over the same window. Positive = the component
    outpaced inflation; negative = it lagged.
    """

    component: CostComponent
    basis: DeflatorBasis
    start_year: int
    end_year: int
    start_nominal: float
    end_nominal: float
    nominal_cagr_pct: Optional[float]
    deflator_cagr_pct: Optional[float]
    real_cagr_pct: Optional[float]
    excess_cagr_pct: Optional[float]
    verdict: str
    n_points: int


def _cagr_pct(start: float, end: float, years: int) -> Optional[float]:
    """Compound annual growth rate, in percent. ``None`` if undefined."""
    if years <= 0 or start <= 0 or end <= 0:
        return None
    return ((end / start) ** (1.0 / years) - 1.0) * 100.0


def compare_against_inflation(
    observations: list[CostObservation],
    deflator: Deflator,
    component: CostComponent,
    basis_year: int,
    currency: str = "USD",
    figure_types: Optional[frozenset] = MARKET_RATE_LENS,
    region: Optional[str] = "global",
) -> Optional[InflationVerdict]:
    """Answer #844's headline question for one component.

    *"Did deepwater rig day-rates outpace or lag CPI over 2000–2026?"*

    Uses the component's first and last **sourced** years as the window, so the
    verdict is anchored on real data at both ends rather than on a fitted value.
    Returns ``None`` when there are fewer than two sourced points — one point
    cannot have a trend, and asserting one from a single observation would be
    exactly the kind of invention this dataset exists to avoid.

    The default lens is ``MARKET_RATE_LENS`` (contractor/market averages), and
    the default currency is USD. Both defaults exist to stop the two silent
    corruptions described in ``series.py``. A caller who wants the leading-edge
    story passes ``figure_types=FIXTURE_LENS`` and gets a *separate* verdict —
    never a blended one.
    """
    # Goes through `annual_means`, which filters on currency AND figure type.
    # Both matter: without the currency filter the GBP North Sea spot rates get
    # averaged in as dollars, and without the figure-type filter a contractor's
    # lagging backlog average gets averaged with a leading-edge fixture. Either
    # one produces a confident, plausible, wrong verdict. See series.py.
    annual = annual_means(
        observations,
        component,
        currency=currency,
        figure_types=figure_types,
        region=region,
    )

    if len(annual) < 2:
        return None

    start_year, end_year = min(annual), max(annual)
    span = end_year - start_year
    start_nominal, end_nominal = annual[start_year], annual[end_year]

    nominal_cagr = _cagr_pct(start_nominal, end_nominal, span)

    deflator_cagr = None
    if deflator.covers(start_year) and deflator.covers(end_year):
        deflator_cagr = _cagr_pct(
            deflator.values[start_year], deflator.values[end_year], span
        )

    start_real = to_real(start_nominal, start_year, basis_year, deflator)
    end_real = to_real(end_nominal, end_year, basis_year, deflator)
    real_cagr = (
        _cagr_pct(start_real, end_real, span)
        if start_real is not None and end_real is not None
        else None
    )

    excess = (
        nominal_cagr - deflator_cagr
        if nominal_cagr is not None and deflator_cagr is not None
        else None
    )

    if excess is None:
        verdict = f"indeterminate — {deflator.basis.value.upper()} does not cover {start_year}–{end_year}"
    elif excess > 0.5:
        verdict = f"OUTPACED {deflator.basis.value.upper()} by {excess:.1f} pp/yr"
    elif excess < -0.5:
        verdict = f"LAGGED {deflator.basis.value.upper()} by {abs(excess):.1f} pp/yr"
    else:
        verdict = f"TRACKED {deflator.basis.value.upper()} (within +/-0.5 pp/yr)"

    return InflationVerdict(
        component=component,
        basis=deflator.basis,
        start_year=start_year,
        end_year=end_year,
        start_nominal=start_nominal,
        end_nominal=end_nominal,
        nominal_cagr_pct=nominal_cagr,
        deflator_cagr_pct=deflator_cagr,
        real_cagr_pct=real_cagr,
        excess_cagr_pct=excess,
        verdict=verdict,
        n_points=len(annual),
    )
