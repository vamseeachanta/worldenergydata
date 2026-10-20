"""Configurable, descriptive operator and well candidacy screen.

Method and sources: docs/data-sources/onshore/small-operator-screen.md.
Fractions use the mathematical identities zero (no deficit) and one (whole);
there are no embedded field thresholds, weights or engineering coefficients.
"""

from __future__ import annotations

import calendar
import math
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from itertools import pairwise
from statistics import mean, median, stdev

from .validation import validate_cases

SIGNALS = ("underperformance", "decline", "step_change", "idle", "erratic")
CAUSE_NOTE = (
    "Public production rates cannot distinguish reservoir depletion from "
    "mechanical failure, curtailment or reporting effects; mechanical "
    "addressability remains a hypothesis requiring operating evidence."
)


def _number(value: object, name: str, minimum: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} is outside its valid domain")
    return float(value)


def _integer(value: object, name: str, minimum: int = 1) -> int:
    _number(value, name, minimum)
    if int(value) != value:
        raise ValueError(f"{name} must be an integer")
    return int(value)


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


def _month(value: str) -> int:
    # Twelve is the calendar's months per year, not a screening parameter.
    try:
        parsed = date.fromisoformat(value + "-01")
        if parsed.strftime("%Y-%m") != value:
            raise ValueError
        return parsed.year * 12 + parsed.month - 1
    except (TypeError, ValueError) as exc:
        raise ValueError("month must use YYYY-MM") from exc


def _group_policy(policy: dict) -> None:
    _integer(policy["vintage_years"], "vintage_years")
    if policy["depth_band_ft"] is not None:
        width = _number(policy["depth_band_ft"], "depth_band_ft")
        if width == 0:
            raise ValueError("depth_band_ft must be positive")


def _check_policy(config: dict) -> None:
    try:
        _month(config["as_of"])
        # Two observations are the mathematical minimum for sample variance.
        _integer(config["history_months"], "history_months", 2)
        low = _integer(config["min_operator_wells"], "min_operator_wells")
        high = _integer(config["max_operator_wells"], "max_operator_wells")
        if high < low:
            raise ValueError("operator size band is reversed")
        _integer(config["min_peers"], "min_peers")
        _group_policy(config["peer_group"])
        _group_policy(config["sensitivity_peer_group"])
        for signal in SIGNALS:
            threshold = _number(config["thresholds"][signal], signal)
            _number(config["weights"][signal], signal)
            if (
                signal in ("underperformance", "decline", "step_change")
                and threshold > 1
            ):
                raise ValueError("fraction threshold exceeds one")
        _integer(config["thresholds"]["idle"], "idle months")
        _number(config["min_prior_rate_bopd"], "min_prior_rate_bopd")
        _number(config["concentration_weight"], "concentration_weight")
        _text(config["policy_source"], "policy_source")
        for name in ("min_recall", "max_false_positive_rate"):
            if _number(config["validation"][name], name) > 1:
                raise ValueError("validation proportion exceeds one")
    except (KeyError, TypeError) as exc:
        raise ValueError("missing or malformed required policy input") from exc


def _prepare(data: dict, config: dict) -> tuple[dict, list[dict], list[dict]]:
    registry = {}
    for record in data["registry"]:
        operator = _text(record["operator_no"], "operator_no")
        _text(record["source"], "registry source")
        _integer(record["well_count_total"], "well_count_total")
        if operator in registry:
            raise ValueError("duplicate registry operator")
        registry[operator] = dict(record)
    wells, excluded, seen = [], [], set()
    cutoff = _month(config["as_of"])
    for record in data["wells"]:
        key = _text(record["well_key"], "well_key")
        if key in seen:
            raise ValueError("duplicate well identity")
        seen.add(key)
        operator = _text(record["operator_no"], "operator_no")
        if operator not in registry:
            raise ValueError("well operator absent from registry")
        _text(record["source"], "well source")
        if record.get("production_basis") != "well":
            excluded.append(
                {"well_key": key, "reason": "production_not_attributed_to_well"}
            )
            continue
        if not record.get("field_key") or record.get("first_production_year") is None:
            excluded.append({"well_key": key, "reason": "missing_field_or_vintage"})
            continue
        _text(record["field_key"], "field_key")
        vintage = _integer(record["first_production_year"], "first_production_year")
        if vintage > cutoff // 12:
            raise ValueError("first production year is after cutoff")
        if record.get("depth_ft") is not None:
            _number(record["depth_ft"], "depth_ft", minimum=0)
        rates, months = {}, set()
        for observation in record["production"]:
            month = _month(observation["month"])
            if month in months:
                raise ValueError("duplicate production month")
            months.add(month)
            volume = observation["oil_bbl"]
            if volume is not None:
                volume = _number(volume, "oil_bbl")
                if month <= cutoff:
                    days = calendar.monthrange(month // 12, month % 12 + 1)[1]
                    rates[month] = volume / days
        wells.append({**record, "rates": rates})
    counts = Counter(well["operator_no"] for well in wells)
    for operator, count in counts.items():
        if count > registry[operator]["well_count_total"]:
            raise ValueError("supplied well count exceeds registry inventory")
    return (
        registry,
        sorted(wells, key=lambda well: well["well_key"]),
        sorted(excluded, key=lambda row: row["well_key"]),
    )


def _metrics(well: dict, config: dict) -> dict:
    end = _month(config["as_of"])
    start = end - config["history_months"] + 1
    rates = well["rates"]
    window = [rates.get(month) for month in range(start, end + 1)]
    complete = all(value is not None for value in window)
    metrics = {
        "current_rate_bopd": rates.get(end),
        "decline": None,
        "step_change": None,
        "erratic": None,
        "idle": None,
        "prior_rate_bopd": None,
        "history_complete": complete,
    }
    if complete:
        if window[0] > 0:
            # Endpoint fractional loss, not an Arps fit or forecast.
            metrics["decline"] = 1 - window[-1] / window[0]
        drops = [1 - b / a for a, b in pairwise(window) if a > 0]
        metrics["step_change"] = max([0, *drops])
        if mean(window) > 0:
            # NIST Dataplot, Coefficient of Variation (2017): sample s / mean.
            metrics["erratic"] = stdev(window) / mean(window)
    if rates.get(end) == 0:
        cursor = end
        while cursor in rates and rates[cursor] == 0:
            cursor -= 1
        if cursor in rates and rates[cursor] > 0:
            metrics["idle"] = end - cursor
            metrics["prior_rate_bopd"] = rates[cursor]
    return metrics


def _peer_key(well: dict, policy: dict) -> tuple | None:
    width = policy["depth_band_ft"]
    if width is not None and (well.get("depth_ft") is None or well["depth_ft"] <= 0):
        return None
    return (
        well["field_key"],
        well["first_production_year"] // policy["vintage_years"],
        math.floor(well["depth_ft"] / width) if width is not None else None,
    )


def _signal(
    value: float | None, threshold: float, weight: float, **evidence: object
) -> dict:
    evaluated = value is not None
    triggered = evaluated and value > 0 and value >= threshold
    return {
        "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
        "value": value,
        "threshold": threshold,
        "triggered": triggered,
        "weight": weight,
        "contribution": weight if triggered else 0,
        **evidence,
    }


def _rank_wells(wells: list[dict], config: dict, policy: dict) -> list[dict]:
    metrics = {well["well_key"]: _metrics(well, config) for well in wells}
    groups = defaultdict(list)
    for well in wells:
        key = _peer_key(well, policy)
        if key is not None:
            groups[key].append(well["well_key"])
    rows = []
    for well in wells:
        identity = well["well_key"]
        own = metrics[identity]
        key = _peer_key(well, policy)
        peers = [other for other in groups.get(key, []) if other != identity]
        signals = {}
        for signal in ("underperformance", "decline", "step_change", "erratic"):
            metric = "current_rate_bopd" if signal == "underperformance" else signal
            peer_values = [
                metrics[other][metric]
                for other in peers
                if metrics[other][metric] is not None
            ]
            enough = len(peer_values) >= config["min_peers"]
            # NIST/SEMATECH e-Handbook §1.3.5.1: ordered-sample median.
            comparator = median(peer_values) if enough else None
            value = None
            if comparator is not None and own[metric] is not None:
                if signal == "underperformance":
                    if comparator > 0:
                        value = max(0, 1 - own[metric] / comparator)
                else:
                    value = max(0, own[metric] - comparator)
            signals[signal] = _signal(
                value,
                config["thresholds"][signal],
                config["weights"][signal],
                observed=own[metric],
                peer_median=comparator,
                peer_count=len(peer_values),
                reason=(
                    "leave-one-out peer comparison"
                    if value is not None
                    else "missing history, insufficient peers or zero peer rate"
                ),
            )
        idle_value = own["idle"]
        if (
            own["prior_rate_bopd"] is not None
            and own["prior_rate_bopd"] < config["min_prior_rate_bopd"]
        ):
            idle_value = 0
        signals["idle"] = _signal(
            idle_value,
            config["thresholds"]["idle"],
            config["weights"]["idle"],
            prior_rate_bopd=own["prior_rate_bopd"],
            min_prior_rate_bopd=config["min_prior_rate_bopd"],
            reason="trailing observed zeros immediately following positive production",
        )
        evaluated = sum(item["status"] == "EVALUATED" for item in signals.values())
        score = sum(item["contribution"] for item in signals.values())
        rows.append(
            {
                "well_key": identity,
                "operator_no": well["operator_no"],
                "field_key": well["field_key"],
                "source": well["source"],
                "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
                "signals_evaluated": evaluated,
                "history_complete": own["history_complete"],
                "score": score,
                "candidate": any(
                    item["triggered"] and item["weight"] > 0
                    for item in signals.values()
                ),
                "peer_group": list(key) if key is not None else None,
                "signals": signals,
                "cause_status": "UNRESOLVED",
                "cause_note": CAUSE_NOTE,
            }
        )
    rows.sort(
        key=lambda row: (
            row["status"] != "EVALUATED",
            -row["score"],
            -(row["signals"]["idle"]["prior_rate_bopd"] or 0),
            row["signals"]["idle"]["value"] or 0,
            row["well_key"],
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def _pressure_context(well_key: str, observations: list[dict], as_of: str) -> dict:
    eligible = []
    for row in observations:
        if row.get("api14") != well_key:
            continue
        try:
            tested = date.fromisoformat(row["test_date"])
            if _month(tested.strftime("%Y-%m")) > _month(as_of):
                continue
            _number(row["pressure_psia"], "pressure_psia")
            _text(row["source_file"], "pressure source")
            _text(row["pressure_kind"], "pressure_kind")
            eligible.append(row)
        except (KeyError, ValueError, TypeError):
            continue
    if not eligible:
        return {"status": "NOT_EVALUATED", "reason": "no usable dated pressure context"}
    # Same-date ties are resolved by the full record, independent of input order.
    row = max(
        eligible,
        key=lambda item: (
            item["test_date"],
            item["pressure_kind"],
            item["source_file"],
            item["pressure_psia"],
            str(item.get("reference_depth_ft")),
        ),
    )
    depth = row.get("reference_depth_ft")
    bhp = row["pressure_kind"] in ("BHP_measured", "BHP_calc")
    usable_depth = (
        isinstance(depth, (int, float))
        and not isinstance(depth, bool)
        and math.isfinite(depth)
        and depth > 0
    )
    return {
        "status": "CONTEXT_ONLY",
        "test_date": row["test_date"],
        "pressure_psia": row["pressure_psia"],
        "pressure_kind": row["pressure_kind"],
        "reference_depth_ft": depth if usable_depth else None,
        "gradient_psi_ft": (
            row["pressure_psia"] / depth if bhp and usable_depth else None
        ),
        "source_file": row["source_file"],
        "note": "Dated context only; neither virgin pressure nor a mechanical diagnosis.",
    }


def _rank_operators(registry: dict, wells: list[dict], rows: list[dict], config: dict):
    operators = []
    for identity, registered in sorted(registry.items()):
        if not (
            config["min_operator_wells"]
            <= registered["well_count_total"]
            <= config["max_operator_wells"]
        ):
            continue
        inventory = [well for well in wells if well["operator_no"] == identity]
        ranked = [row for row in rows if row["operator_no"] == identity]
        evaluated = [row for row in ranked if row["status"] == "EVALUATED"]
        fields = Counter(well["field_key"] for well in inventory)
        # DOJ HHI definition (2024): sum of squared shares. Fractions here,
        # rather than percentage shares; no antitrust thresholds are imported.
        hhi = sum((count / len(inventory)) ** 2 for count in fields.values())
        average = mean(row["score"] for row in evaluated) if evaluated else None
        contribution = config["concentration_weight"] * hhi if inventory else None
        operators.append(
            {
                "operator_no": identity,
                "source": registered["source"],
                "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
                "well_count_total": registered["well_count_total"],
                "wells_supplied": len(inventory),
                "wells_evaluated": len(evaluated),
                "candidate_wells": sum(row["candidate"] for row in ranked),
                "inventory_coverage": len(inventory) / registered["well_count_total"],
                "mean_well_score": average,
                "concentration": {
                    "hhi": hhi if inventory else None,
                    "field_counts": dict(sorted(fields.items())),
                    "basis": "supplied_well_inventory",
                    "weight": config["concentration_weight"],
                    "contribution": contribution,
                },
                "score": average + contribution if average is not None else None,
                "why": "mean evaluated well score plus weighted field concentration",
                "well_evidence": [
                    {"well_key": row["well_key"], "score": row["score"]}
                    for row in evaluated
                ],
            }
        )
    operators.sort(
        key=lambda row: (
            row["score"] is None,
            -row["score"] if row["score"] is not None else 0,
            row["operator_no"],
        )
    )
    for rank, row in enumerate(operators, start=1):
        row["rank"] = rank
    return operators


def run_screen(data: dict, config: dict) -> dict:
    """Rank well-attributed inputs without changing them or inferring ownership.

    Operator identifiers must already be reconciled by the registry producer.
    Larger operators remain in the peer pool. Well scores are weighted signal
    flags, not production forecasts, probabilities or monetary estimates.
    """
    _check_policy(config)
    registry, wells, excluded = _prepare(data, config)
    base = _rank_wells(wells, config, config["peer_group"])
    alternate = _rank_wells(wells, config, config["sensitivity_peer_group"])
    selected = {
        identity
        for identity, row in registry.items()
        if config["min_operator_wells"]
        <= row["well_count_total"]
        <= config["max_operator_wells"]
    }
    rows = [row for row in base if row["operator_no"] in selected]
    alternate = [row for row in alternate if row["operator_no"] in selected]
    alternate_by_key = {row["well_key"]: row for row in alternate}
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        other = alternate_by_key[row["well_key"]]
        row["sensitivity"] = {
            "score": other["score"],
            "score_delta": other["score"] - row["score"],
            "rank": alternate.index(other) + 1,
            "rank_delta": alternate.index(other) + 1 - rank,
            "candidate_changed": other["candidate"] != row["candidate"],
            "signals": other["signals"],
            "peer_group": other["peer_group"],
        }
        row["pressure"] = _pressure_context(
            row["well_key"], data.get("pressure", []), config["as_of"]
        )
    operators = _rank_operators(registry, wells, rows, config)
    alternate_operators = _rank_operators(registry, wells, alternate, config)
    alternate_operator_map = {row["operator_no"]: row for row in alternate_operators}
    for row in operators:
        other = alternate_operator_map[row["operator_no"]]
        row["sensitivity"] = {
            "score": other["score"],
            "rank": other["rank"],
            "rank_delta": other["rank"] - row["rank"],
            "score_delta": (
                other["score"] - row["score"]
                if other["score"] is not None and row["score"] is not None
                else None
            ),
        }
    return {
        "config": deepcopy(config),
        "wells": rows,
        "operators": operators,
        "excluded": excluded,
        "coverage": {
            "registry_operators": len(registry),
            "peer_pool_wells": len(wells),
            "selected_wells": len(rows),
            "excluded_wells": len(excluded),
            "peer_definition_changed_candidates": sum(
                row["sensitivity"]["candidate_changed"] for row in rows
            ),
        },
        "validation": validate_cases(
            rows, data.get("validation_cases", []), config["validation"]
        ),
        "limitations": [
            CAUSE_NOTE,
            "Operator of record does not establish working interest or ownership.",
            "Calendar daily oil rates are not operating-day rates; no lease allocation.",
            "Correlated signal weights are policy inputs, not calibrated probabilities.",
            "Field grouping requires a jurisdiction-qualified stable identifier.",
        ],
    }
