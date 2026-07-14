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

__all__ = [
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

    @property
    def min_year(self) -> int:
        return min(self.values)

    @property
    def max_year(self) -> int:
        return max(self.values)

    def covers(self, year: int) -> bool:
        return year in self.values


def _interpolate_gaps(anchors: dict[int, float]) -> tuple[dict[int, float], set[int]]:
    """Linearly interpolate between anchor years. Never extrapolates.

    Returns ``(values, interpolated_years)``. Years outside ``[min, max]`` of
    the anchors are simply absent — that is the "we don't know" answer, and it
    is deliberate.
    """
    if not anchors:
        return {}, set()
    known = sorted(anchors)
    values: dict[int, float] = dict(anchors)
    interpolated: set[int] = set()

    for left, right in zip(known, known[1:]):
        span = right - left
        if span <= 1:
            continue
        rise = anchors[right] - anchors[left]
        for offset in range(1, span):
            year = left + offset
            values[year] = anchors[left] + rise * (offset / span)
            interpolated.add(year)

    return values, interpolated


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
    anchors = {
        obs.year: obs.value
        for obs in observations
        if obs.component is component and obs.value is not None
    }
    if not anchors:
        raise ValueError(
            f"no {component.value} rows available — cannot build the {basis.value} "
            "deflator. Refusing to substitute a different index silently."
        )

    values, interpolated = _interpolate_gaps(anchors)

    if basis is DeflatorBasis.CPI:
        note = (
            "U.S. CPI-U all items (FRED CPIAUCSL), calendar-year mean of monthly "
            "observations. Complete measured series; no interpolation."
        )
    else:
        note = (
            f"IHS/S&P Upstream Capital Costs Index. Proprietary — built from "
            f"{len(anchors)} publicly sourced anchor year(s) "
            f"({min(anchors)}–{max(anchors)}) with linear interpolation across "
            f"{len(interpolated)} gap year(s). NOT extrapolated beyond the anchor "
            "range: outside it, UCCI-real is not published."
        )

    return Deflator(
        basis=basis,
        values=values,
        interpolated_years=frozenset(interpolated),
        source_note=note,
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
) -> Optional[InflationVerdict]:
    """Answer #844's headline question for one component.

    *"Did deepwater rig day-rates outpace or lag CPI over 2000–2026?"*

    Uses the component's first and last **sourced** years as the window, so the
    verdict is anchored on real data at both ends rather than on a fitted value.
    Returns ``None`` when there are fewer than two sourced points — one point
    cannot have a trend, and asserting one from a single observation would be
    exactly the kind of invention this dataset exists to avoid.
    """
    series = sorted(
        (
            obs
            for obs in observations
            if obs.component is component
            and obs.value is not None
            and obs.provenance.value == "sourced"
        ),
        key=lambda o: o.year,
    )
    # Collapse duplicate years (multiple fixtures in one year) to their mean, so
    # a year with 5 quotes does not outvote a year with 1 when we pick endpoints.
    by_year: dict[int, list[float]] = {}
    for obs in series:
        by_year.setdefault(obs.year, []).append(obs.value)  # type: ignore[arg-type]
    annual = {year: sum(v) / len(v) for year, v in by_year.items()}

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
