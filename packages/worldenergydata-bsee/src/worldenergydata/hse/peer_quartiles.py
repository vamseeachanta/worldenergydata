"""Quartiles of anonymous, already-qualified rates for one activity/peer group."""

from collections.abc import Iterable
from math import isfinite
from numbers import Real

# Issue #425, acceptance criteria: minimum peer-group cell size n >= 10.
_MIN_CELL_SIZE = 10


def peer_quartiles(rates: Iterable[Real]) -> dict[str, float] | None:
    """Return only q1/median/q3, or None for a group below the #425 minimum.

    The caller supplies anonymous finite, nonnegative real rates for a single
    activity and peer group, using consistent units and reporting periods.
    Rates are normalized to built-in floats; booleans and non-real values
    are rejected. Every member is validated before suppression, so missing or
    invalid rates raise ValueError rather than silently shrinking the group.
    Errors never include member values or their positions.

    Inclusive linear interpolation uses zero-based rank r = (n - 1) * p
    in the sorted rates, interpolating between the adjacent ranks. Quartiles
    use p = 0.25, 0.5, 0.75. The independent derivation in
    test_inclusive_quartiles_match_hand_case uses sorted rates 0..9:
    ranks and values are respectively 2.25, 4.5, 6.75.

    The result contains no identifiers, member rates or exact sample size,
    following the #425 plan's sample-size omission requirement. This primitive
    does not qualify sources or exposure, infer rates from incident rows, or
    perform cross-cell disclosure review. Synthetic tests do not establish
    publication clearance; those controls remain the caller's responsibility.

    Raises:
        ValueError: The group is not iterable, or a member is missing, invalid,
            negative, or cannot be represented as a finite float.
    """
    message = "rates must contain only finite nonnegative real values"
    try:
        members = iter(rates)
    except TypeError as exc:
        raise ValueError("rates must be an iterable of real values") from exc

    values = []
    for rate in members:
        if isinstance(rate, bool) or not isinstance(rate, Real) or rate < 0:
            raise ValueError(message)
        try:
            value = float(rate)
        except (OverflowError, ValueError) as exc:
            raise ValueError(message) from exc
        if not isfinite(value):
            raise ValueError(message)
        values.append(value)

    if len(values) < _MIN_CELL_SIZE:
        return None
    values.sort()

    def quantile(probability: float) -> float:
        # Inclusive convention and independent hand case are documented above.
        rank = (len(values) - 1) * probability
        lower = int(rank)
        fraction = rank - lower
        # Nonnegative sorted endpoints keep the difference finite, avoiding
        # overflow from summing large weighted endpoints before division.
        return values[lower] + fraction * (values[lower + 1] - values[lower])

    return {"q1": quantile(0.25), "median": quantile(0.5), "q3": quantile(0.75)}
