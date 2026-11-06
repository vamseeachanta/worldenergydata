"""Compare observed costs with explicitly supplied, like-for-like proxies.

This is an observed-data benchmark, independent of CostPredictor's fitted
values and escalation assumptions. Each cell has one cost type, sanction
year, region, depth bands, rig, activity and completion basis. No currency,
year, total-capital-to-well-cost, or cost-to-day-rate conversion is inferred.
Amounts follow CostDataPoint: USD millions for costs, USD millions per day
for day-rate observations. A proxy must use the same basis as its cell.

The caller supplies the minimum record count; it is a coverage policy, not
a statistical confidence criterion. Selecting an observed mean does not
qualify its source data or establish prediction accuracy. Sources are carried
through as references, without claiming that their contents were verified.
No confidence interval is calculated. Sparse cells retain their proxy;
observations without a matching proxy are NOT_EVALUATED.

Metric source: Forecasting: Principles and Practice, third edition (2021),
section 5.8, scale-dependent errors and percentage errors:
https://otexts.com/fpp3/toolbox.html#sec-accuracy
The signed bias here uses the proxy as denominator (an explicit benchmark
convention), rather than the observation denominator of forecast MAPE.
RMSE measures proxy errors against observations, not fitted-model residuals.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from math import hypot, isfinite, sqrt
from statistics import fmean

from worldenergydata.cost.data_collection.calibration_schema import (
    ActivityType,
    CostDataPoint,
    CostType,
    RigType,
    SubseaType,
    WaterDepthBand,
    WellDepthBand,
)


@dataclass(frozen=True)
class BenchmarkCell:
    """Exact comparison key; obtain it with ``from_record`` for schema alignment.

    Unknown well-depth bands remain separate from known bands. Exact numeric
    depths may vary within a band. Year means nominal sanction-year USD,
    matching the existing sanctioned-project schema; no deflation is applied.
    """

    region: str
    water_depth_band: WaterDepthBand
    well_depth_band: WellDepthBand | None
    rig_type: RigType
    activity_type: ActivityType
    cost_type: CostType
    year_sanction: int
    hpht: bool
    subsea: SubseaType

    @classmethod
    def from_record(cls, record: CostDataPoint) -> BenchmarkCell:
        """Extract the cell without aliasing regions or inferring missing bands."""
        return cls(**{name: getattr(record, name) for name in cls.__dataclass_fields__})


@dataclass(frozen=True)
class BenchmarkProxy:
    """A positive comparator in the cell's units, with a required source reference."""

    cost_usd_mm: float
    source: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.cost_usd_mm, bool)
            or not isinstance(self.cost_usd_mm, (int, float))
            or not isfinite(self.cost_usd_mm)
            or self.cost_usd_mm <= 0
        ):
            raise ValueError("Proxy cost must be positive and finite.")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Proxy source must be a nonblank reference.")


class BenchmarkStatus(str, Enum):
    """Selection disposition, independent of source quality or confidence."""

    OBSERVED_MEAN = "observed_mean"
    PROXY_FALLBACK = "proxy_fallback"
    NOT_EVALUATED = "not_evaluated"


@dataclass(frozen=True)
class ObservedBenchmark:
    """Per-cell metrics; missing metrics are None, never substituted with zero."""

    cell: BenchmarkCell
    status: BenchmarkStatus
    reason: str | None
    n_records: int
    observed_mean_usd_mm: float | None
    proxy_cost_usd_mm: float | None
    selected_cost_usd_mm: float | None
    bias_pct: float | None
    rmse_usd_mm: float | None
    observation_sources: tuple[str, ...]
    proxy_source: str | None


def _group_records(
    records: Sequence[CostDataPoint],
) -> dict[BenchmarkCell, list[CostDataPoint]]:
    groups: dict[BenchmarkCell, list[CostDataPoint]] = {}
    identities: set[tuple[str, str, BenchmarkCell]] = set()
    for record in records:
        # Revalidate a snapshot: the existing schema permits post-creation mutation.
        snapshot = CostDataPoint.model_validate(record.model_dump())
        if not isfinite(snapshot.cost_usd_mm):
            raise ValueError("Observed cost must be positive and finite.")
        for name in ("source", "region", "operator", "project_name"):
            if not getattr(snapshot, name).strip():
                raise ValueError(f"Observation {name} must not be blank.")
        cell = BenchmarkCell.from_record(snapshot)
        identity = (snapshot.operator, snapshot.project_name, cell)
        if identity in identities:
            raise ValueError("Duplicate project observation within a benchmark cell.")
        identities.add(identity)
        groups.setdefault(cell, []).append(snapshot)
    return groups


def _compare_cell(
    cell: BenchmarkCell,
    records: list[CostDataPoint],
    proxy: BenchmarkProxy | None,
    minimum_records: int,
) -> ObservedBenchmark:
    costs = [record.cost_usd_mm for record in records]
    # Arithmetic mean definition; each distinct project contributes equal weight.
    scale = max(costs) if costs else None
    # Scaling preserves the mean while avoiding overflow of its intermediate sum.
    mean = scale * fmean(cost / scale for cost in costs) if costs else None
    bias = rmse = selected = None
    if proxy is None:
        status, reason = BenchmarkStatus.NOT_EVALUATED, "missing_proxy"
    elif not costs:
        status, reason = BenchmarkStatus.PROXY_FALLBACK, "no_observations"
        selected = proxy.cost_usd_mm
    else:
        # FPP, third ed. (2021), section 5.8: sqrt(mean(error**2)).
        # Normalize before hypot to avoid both squared and summed overflow.
        denominator = sqrt(len(costs))
        rmse = hypot(*((cost - proxy.cost_usd_mm) / denominator for cost in costs))
        # 100 is the percent conversion, not an empirical calibration coefficient.
        # Proxy-denominator convention: positive means proxy < observed mean.
        bias = (mean / proxy.cost_usd_mm - 1) * 100
        if not isfinite(bias) or not isfinite(rmse):
            raise ValueError("Benchmark metrics exceed finite numeric range.")
        if len(costs) < minimum_records:
            status, reason = BenchmarkStatus.PROXY_FALLBACK, "insufficient_records"
            selected = proxy.cost_usd_mm
        else:
            status, reason = BenchmarkStatus.OBSERVED_MEAN, None
            selected = mean
    return ObservedBenchmark(
        cell=cell,
        status=status,
        reason=reason,
        n_records=len(records),
        observed_mean_usd_mm=mean,
        proxy_cost_usd_mm=proxy.cost_usd_mm if proxy else None,
        selected_cost_usd_mm=selected,
        bias_pct=bias,
        rmse_usd_mm=rmse,
        observation_sources=tuple(sorted({record.source for record in records})),
        proxy_source=proxy.source if proxy else None,
    )


def benchmark_observed_costs(
    records: Sequence[CostDataPoint],
    proxies: Mapping[BenchmarkCell, BenchmarkProxy],
    *,
    minimum_records: int,
) -> list[ObservedBenchmark]:
    """Benchmark exact cells, retaining proxies below caller-specified coverage.

    All observed cells and all supplied proxy cells appear in the result, in
    first-observed order followed by unobserved proxy cells in mapping order.
    Duplicated (operator, project, cell) identities raise ValueError rather
    than inflating coverage; multiple source citations are not independent
    observations. Inputs remain unchanged. Resolve duplicate records and verify
    the comparability and rights of source data before calling this function.
    """
    if type(minimum_records) is not int or minimum_records <= 0:
        raise ValueError("minimum_records must be a positive integer.")
    if any(
        not isinstance(cell, BenchmarkCell) or not isinstance(proxy, BenchmarkProxy)
        for cell, proxy in proxies.items()
    ):
        raise ValueError(
            "Proxies must map BenchmarkCell keys to BenchmarkProxy values."
        )
    groups = _group_records(records)
    cells = dict.fromkeys([*groups, *proxies])
    return [
        _compare_cell(cell, groups.get(cell, []), proxies.get(cell), minimum_records)
        for cell in cells
    ]
