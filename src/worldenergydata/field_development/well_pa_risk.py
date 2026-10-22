"""Per-field TA/COM borehole screen with explicit, optional scenario prices.

Consumes the existing bottom-lease attribution snapshot; does not infer legal
obligations, independent well counts, current ownership or reservoir targeting.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

# BSEE Data Center, Borehole Status Code enumeration (retrieved 2026-10-20).
# COM = Borehole Completed; TA = Temporarily Abandoned; PA is excluded.
STATUS_URL = "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields"
CANDIDATE_STATUSES = ("TA", "COM")


def _count(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("Borehole count must be a nonnegative integer")
    return value


def _price(value: Any) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError("Invalid unit cost: expected finite nonnegative USD")
    try:
        number = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("Invalid unit cost: expected numerical USD") from error
    if not number.is_finite() or number < 0:
        raise ValueError("Invalid unit cost: expected finite nonnegative USD")
    return number


def _cost(counts: dict, basis: dict | None, borehole_count: int) -> dict:
    prices = {}
    if basis is not None:
        prices = {
            code: _price(value)
            for code, value in basis.get("unit_cost_usd", {}).items()
        }
        if set(prices) - set(CANDIDATE_STATUSES):
            raise ValueError("Unknown unit cost status; only TA and COM are supported")
    reason = None
    if not borehole_count:
        reason = "no_boreholes_on_registered_leases"
    elif not sum(counts.values()):
        reason = "no_ta_com_boreholes"
    elif (
        basis is None
        or set(prices) != set(CANDIDATE_STATUSES)
        or not isinstance(basis.get("source"), str)
        or not basis["source"].strip()
        or not isinstance(basis.get("price_basis"), str)
        or not basis["price_basis"].strip()
    ):
        reason = "missing_unit_cost_basis"
    if reason:
        return {"status": "NOT_EVALUATED", "reason": reason, "total_usd": None}

    # Accounting identity C = sum(n_status * c_status), no fitted coefficient.
    # OpenStax, Principles of Accounting, Volume 2: Managerial Accounting (2019),
    # section 2.2, Variable Costs: total variable cost scales with units.
    # https://openstax.org/books/principles-managerial-accounting/pages/2-2-identify-and-apply-basic-cost-behavior-patterns
    # Both per-borehole prices and their source are required scenario inputs.
    # Size decimal precision from the inputs so multiplication and addition are
    # exact even when price exponents differ. Output strings retain USD precision.
    low = min(price.as_tuple().exponent for price in prices.values())
    high = max(
        price.adjusted() + len(str(counts[code])) for code, price in prices.items()
    )
    with localcontext() as context:
        context.prec = max(context.prec, high - low + len(str(len(prices))))
        parts = {code: prices[code] * counts[code] for code in CANDIDATE_STATUSES}
        total = sum(parts.values(), Decimal(0))
    return {
        "status": "SCENARIO",
        "reason": None,
        "total_usd": format(total, "f"),
        "by_status_usd": {code: format(value, "f") for code, value in parts.items()},
        "unit_cost_usd": {code: format(value, "f") for code, value in prices.items()},
        "source": basis["source"],
        "price_basis": basis["price_basis"],
    }


def build_well_pa_signals(
    snapshot: dict, cost_inputs: dict[str, dict] | None = None
) -> dict[str, dict]:
    """Build canonical-field signals from ``borehole_status/summary.json``.

    ``cost_inputs`` maps field ids to ``unit_cost_usd: {TA: ..., COM: ...}``,
    ``source`` and ``price_basis``. Missing inputs yield NOT_EVALUATED; supplied
    invalid prices raise ValueError. Costs are undiscounted TA/COM scenarios,
    excluding all other statuses and all facility-removal costs.
    """
    cost_inputs = cost_inputs or {}
    signals = {}
    for field in snapshot["fields"]:
        field_id = field["field_id"]
        if not isinstance(field_id, str) or not field_id:
            raise ValueError("Missing canonical field id")
        if field_id in signals:
            raise ValueError("Duplicate field in borehole snapshot")
        statuses = {code: _count(n) for code, n in field["status_counts"].items()}
        borehole_count = _count(field["borehole_count"])
        if sum(statuses.values()) != borehole_count:
            raise ValueError("Field borehole count differs from status counts")
        counts = {code: statuses.get(code, 0) for code in CANDIDATE_STATUSES}
        cost = _cost(counts, cost_inputs.get(field_id), borehole_count)
        note = (
            "API12 boreholes on registered bottom leases; not independent wells "
            "or outstanding liability. Other statuses and facility removal excluded. "
            + (
                f"Cost NOT_EVALUATED: {cost['reason']}."
                if cost["status"] == "NOT_EVALUATED"
                else f"Undiscounted cost scenario: {cost['total_usd']} USD "
                f"({cost['price_basis']}); source: {cost['source']}."
            )
        )
        signals[field_id] = {
            "field_id": field_id,
            "basis": snapshot["basis"],
            "registered_leases": list(field["registered_leases"]),
            "borehole_count": borehole_count,
            "ta_count": counts["TA"],
            "com_count": counts["COM"],
            "candidate_boreholes": sum(counts.values()),
            "other_status_counts": {
                code: n for code, n in statuses.items() if code not in counts
            },
            "availability": (
                "boreholes_present"
                if borehole_count
                else "no_boreholes_on_registered_leases"
            ),
            "cost": cost,
            "label": f"P&A screen · TA {counts['TA']} / COM {counts['COM']} boreholes",
            "note": note,
            "provenance": deepcopy(
                {
                    key: snapshot[key]
                    for key in (
                        "source_sha256",
                        "registry_sha256",
                        "source_retrieved_at_utc",
                        "status_definitions_url",
                        "source_boreholes",
                        "joined_boreholes",
                        "unmatched_counts",
                    )
                }
            ),
        }
    unknown = set(cost_inputs) - set(signals)
    if unknown:
        raise ValueError("Unknown cost field in scenario inputs")
    joined = sum(item["borehole_count"] for item in signals.values())
    unmatched = sum(_count(n) for n in snapshot["unmatched_counts"].values())
    if joined != _count(snapshot["joined_boreholes"]) or joined + unmatched != _count(
        snapshot["source_boreholes"]
    ):
        raise ValueError("Snapshot borehole counts do not reconcile")
    return signals
