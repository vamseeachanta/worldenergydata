"""Grain-preserving operator roll-up and descriptive peer screen.

Source definitions: RRC, Production Data Query Dump Manual, tables
OG_LEASE_CYCLE and OG_WELL_COMPLETION, pp. 12–13 and 19 (current public copy).
Statistics: NIST/SEMATECH e-Handbook (online edition, accessed 2026), §1.3.5.1, median definition.
All acceptance thresholds are required policy inputs, not physical constants.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from statistics import median, pstdev
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Policy:
    """Caller decisions; no implicit industry cutoffs or calibrated weights."""

    min_wells: int
    max_wells: int
    stripper_bopd: float
    min_stripper_share: float
    min_peers: int
    window_months: int
    vintage_years: int
    deficit_fraction: float
    decline_excess_fraction: float
    erratic_cv: float
    top_candidates: int

    def __post_init__(self):
        for key in (
            "min_wells",
            "max_wells",
            "min_peers",
            "window_months",
            "vintage_years",
            "top_candidates",
        ):
            value = getattr(self, key)
            if type(value) is not int or value <= 0:
                raise ValueError(f"policy {key} must be a positive integer")
        # Two observations are the mathematical minimum for a change.
        if self.window_months < 2 or self.max_wells < self.min_wells:
            raise ValueError("invalid window or size band")
        for key in (
            "stripper_bopd",
            "min_stripper_share",
            "deficit_fraction",
            "decline_excess_fraction",
            "erratic_cv",
        ):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"policy {key} must be numeric")
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"policy {key} must be finite and nonnegative")
        for key in (
            "min_stripper_share",
            "deficit_fraction",
            "decline_excess_fraction",
        ):
            if getattr(self, key) > 1:
                raise ValueError(f"policy {key} must be a fraction")


def normalize_name(value: str) -> str:
    """Diagnostic matching only; never an identity or transfer join.

    Method is an explicit local convention: punctuation, AND/& and terminal
    legal suffixes are ignored. IDs remain the sole operator identity.
    """
    words = re.sub(r"[^A-Z0-9]+", " ", value.upper().replace("&", " AND ")).split()
    while words and words[-1] in {"INC", "LLC", "CO", "CORP", "LTD"}:
        words.pop()
    return " ".join(words)


def _text(row, key):
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing string field: {key}")
    return value.strip()


def _month(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}", value):
        raise ValueError("month must be YYYY-MM")
    parsed = date.fromisoformat(value + "-01")
    return parsed


def _months(as_of, count):
    last = _month(as_of)
    result = []
    year, month = last.year, last.month
    for _ in range(count):
        result.append(f"{year:04}-{month:02}")
        if month == 1:
            year, month = year - 1, 12  # Gregorian months in a year.
        else:
            month -= 1
    return sorted(result)


def _volume(row, key, *, optional=False):
    value = row.get(key)
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{key} must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{key} must be finite and nonnegative")
    return float(value)


def _lease(row):
    return tuple(_text(row, k) for k in ("district", "oil_gas_code", "lease_no"))


def _source(bundle):
    source = bundle.get("source", {})
    for key in ("dataset", "url", "snapshot_date", "inventory_date"):
        if not source.get(key):
            raise ValueError(f"source requires {key}")
        _text(source, key)
    url = urlsplit(source["url"])
    if url.scheme != "https" or not url.netloc or url.username or url.password:
        raise ValueError("source url must be public HTTPS without credentials")
    for key in ("snapshot_date", "inventory_date"):
        date.fromisoformat(source[key])
    return dict(source)


def _inventory(bundle):
    wells = bundle.get("wells", [])
    if not wells:
        raise ValueError("nonempty well inventory required")
    groups = defaultdict(list)
    apis = set()
    for original in wells:
        well = dict(original)
        for key in ("operator_no", "operator_name", "api_number", "county", "status"):
            well[key] = _text(well, key)
        well["district"], well["oil_gas_code"], well["lease_no"] = _lease(well)
        # Operator numbers become report basenames, so only regulator digits are allowed.
        if not well["operator_no"].isascii() or not well["operator_no"].isdigit():
            raise ValueError("operator_no must contain ASCII digits")
        if well["api_number"] in apis:
            raise ValueError(
                "duplicate API inventory; resolve completions before screening"
            )
        apis.add(well["api_number"])
        if well["oil_gas_code"] not in {"O", "G"}:
            raise ValueError("oil_gas_code must be O or G")
        if well["status"] not in {"producing", "inactive", "plugged", "unknown"}:
            raise ValueError("status requires explicit normalized classification")
        year = well.get("completion_year")
        if year is not None and (type(year) is not int or year <= 0):
            raise ValueError("completion_year must be a positive integer or null")
        groups[_lease(well)].append(well)
    return groups


def _production(bundle, inventory, months):
    grouped = defaultdict(dict)
    grains = Counter()
    observed = set()
    for original in bundle.get("production", []):
        row = dict(original)
        lease = _lease(row)
        month = _text(row, "month")
        _month(month)
        operator = _text(row, "operator_no")
        grain = _text(row, "granularity")
        if grain not in {"lease", "well"}:
            raise ValueError("granularity must be lease or well")
        if lease not in inventory:
            raise ValueError("production has no inventory lease")
        members = inventory[lease]
        if grain == "well":
            api = _text(row, "api_number")
            members = [w for w in members if w["api_number"] == api]
            if not members:
                raise ValueError("production API has no matching inventory")
        else:
            api = ""
        if {w["operator_no"] for w in members} != {operator}:
            raise ValueError(
                "operator history differs from inventory; dated join required"
            )
        for key in ("oil_bbl", "gas_mcf", "water_bbl"):
            row[key] = _volume(row, key, optional=key == "water_bbl")
        identity = (lease, month, api)
        if identity in observed:
            raise ValueError("duplicate production period; select one snapshot first")
        observed.add(identity)
        unit = (lease, grain, api)
        grouped[unit][month] = row
        if month in months:
            grains[grain] += 1
    for lease, month, api in observed:
        if api and (lease, month, "") in observed:
            raise ValueError("mixed lease and well totals would double count")
    # A changing grain cannot establish comparable histories even in different months.
    lease_grains = defaultdict(set)
    for lease, grain, api in grouped:
        lease_grains[lease].add(grain)
    if any(len(grains) > 1 for grains in lease_grains.values()):
        raise ValueError("production grain changes within a lease")
    return grouped, dict(sorted(grains.items()))


def _unit(lease, grain, api, members, history, months, policy):
    history = {m: r for m, r in history.items() if m <= months[-1]}
    if grain == "well":
        members = [w for w in members if w["api_number"] == api]
    years = [w.get("completion_year") for w in members]
    vintages = {y // policy.vintage_years for y in years if y is not None}
    fields = {w.get("field_no") for w in members}
    peer_key = None
    # Match district, field, fluid, vintage bucket AND inventory well count.
    # Lease rates are never compared to a different-sized lease or allocated to wells.
    if (
        len(fields) == 1
        and None not in fields
        and "" not in fields
        and all(y is not None for y in years)
        and len(vintages) == 1
    ):
        peer_key = (
            lease[0],
            next(iter(fields)),
            lease[1],
            next(iter(vintages)),
            grain,
            len(members),
        )
    complete = all(m in history for m in months)
    rates = []
    for month in months:
        if month in history:
            d = _month(month)
            # Calendar-day average; not days-on-production or an uplift prediction.
            rates.append(
                history[month]["oil_bbl"] / calendar.monthrange(d.year, d.month)[1]
            )
    latest = history.get(months[-1])
    rate = None
    if latest is not None:
        d = _month(months[-1])
        rate = latest["oil_bbl"] / calendar.monthrange(d.year, d.month)[1]
    decline = None
    if complete and rates[0] > 0:
        # Local descriptive definition, docs method M2: endpoint fractional loss.
        decline = (rates[0] - rates[-1]) / rates[0]
    cv = None
    if complete and sum(rates) > 0:
        # NIST Dataplot, Coefficient of Variation (online edition, accessed 2026):
        # CV = standard deviation / mean; see docs method M3 for population convention.
        # Population convention: this is the observed window, not a sample estimator.
        cv = pstdev(rates) / (sum(rates) / len(rates))
    positive_months = sorted(m for m, r in history.items() if r["oil_bbl"] > 0)
    last_positive = positive_months[-1] if positive_months else None
    last_positive_rate = None
    idle_months = None
    if last_positive is not None:
        previous = _month(last_positive)
        current = _month(months[-1])
        last_positive_rate = (
            history[last_positive]["oil_bbl"]
            / calendar.monthrange(previous.year, previous.month)[1]
        )
        # Calendar month subtraction; a reporting interval, not measured downtime.
        idle_months = (
            (current.year - previous.year) * 12 + current.month - previous.month
        )
    return {
        "operator_no": members[0]["operator_no"],
        "unit_id": ":".join((*lease, grain, api)),
        "granularity": grain,
        "api_number": api or None,
        "district": lease[0],
        "lease_no": lease[2],
        "oil_gas_code": lease[1],
        "field_no": next(iter(fields)) if len(fields) == 1 else None,
        "inventory_well_count": len(members),
        "rate_bopd": rate,
        "decline_fraction": decline,
        "rate_cv": cv,
        "last_positive_oil_month": last_positive,
        "last_positive_oil_bopd": last_positive_rate,
        "months_since_positive_oil": idle_months,
        "observed_window_months": sum(m in history for m in months),
        "vintage_bucket_start": (
            min(vintages) * policy.vintage_years if peer_key else None
        ),
        "history_status": "EVALUATED" if complete else "NOT_EVALUATED",
        "mechanism": "NOT_EVALUATED",
        "pressure_context": "NOT_EVALUATED",
        "peer_status": "NOT_EVALUATED",
        "peer_count": 0,
        "peer_median_bopd": None,
        "deficit_fraction": None,
        "decline_excess_fraction": None,
        "signals": [],
        "signal_count": 0,
        "_peer_key": peer_key,
        "_history": history,
        "_inactive": all(w["status"] == "inactive" for w in members),
    }


def _rank_units(units, policy):
    peer_groups = defaultdict(list)
    for unit in units:
        if unit["_peer_key"] is not None and unit["history_status"] == "EVALUATED":
            peer_groups[unit["_peer_key"]].append(unit)
    for unit in units:
        if unit["history_status"] != "EVALUATED" or unit["oil_gas_code"] != "O":
            continue
        peers = [
            p
            for p in peer_groups[unit["_peer_key"]]
            if p["operator_no"] != unit["operator_no"]
        ]
        unit["peer_count"] = len(peers)
        if len(peers) >= policy.min_peers:
            unit["peer_status"] = "EVALUATED"
            center = median(p["rate_bopd"] for p in peers)
            unit["peer_median_bopd"] = center
            if center > 0:
                # Method M1 in the report: max(0, median - observed) / median.
                unit["deficit_fraction"] = max(0, center - unit["rate_bopd"]) / center
                if unit["deficit_fraction"] > policy.deficit_fraction:
                    unit["signals"].append("below_peer_median")
            declines = [
                p["decline_fraction"]
                for p in peers
                if p["decline_fraction"] is not None
            ]
            if (
                len(declines) >= policy.min_peers
                and unit["decline_fraction"] is not None
            ):
                excess = unit["decline_fraction"] - median(declines)
                unit["decline_excess_fraction"] = excess
                if excess > policy.decline_excess_fraction:
                    unit["signals"].append("steeper_than_peer_decline")
        if (
            unit["_inactive"]
            and unit["rate_bopd"] == 0
            and any(r["oil_bbl"] > 0 for r in unit["_history"].values())
        ):
            unit["signals"].append("idle_with_prior_oil")
        if unit["rate_cv"] is not None and unit["rate_cv"] > policy.erratic_cv:
            unit["signals"].append("erratic_oil_rate")
        # Unweighted evidence count is a transparent sorting convention, not a model.
        unit["signal_count"] = len(unit["signals"])
    return sorted(
        units, key=lambda u: (-u["signal_count"], u["operator_no"], u["unit_id"])
    )


def _registry(inventory, units, months, policy):
    operators = defaultdict(list)
    name_ids = defaultdict(set)
    for members in inventory.values():
        for well in members:
            operators[well["operator_no"]].append(well)
            name_ids[normalize_name(well["operator_name"])].add(well["operator_no"])
    units_by_operator = defaultdict(list)
    for unit in units:
        units_by_operator[unit["operator_no"]].append(unit)
    rows = []
    for operator, wells in sorted(operators.items()):
        names = sorted({w["operator_name"] for w in wells})
        owned = units_by_operator[operator]
        # Complete coverage requires every API (well grain) or every lease (lease grain).
        covered = set()
        for u in owned:
            if u["history_status"] == "EVALUATED":
                if u["granularity"] == "well":
                    covered.add(u["api_number"])
                else:
                    covered.update(
                        w["api_number"]
                        for w in wells
                        if _lease(w) == tuple(u["unit_id"].split(":")[:3])
                    )
        complete = covered == {w["api_number"] for w in wells}
        totals = {}
        for column in ("oil_bbl", "gas_mcf", "water_bbl"):
            values = [
                u["_history"][m][column]
                for u in owned
                for m in months
                if m in u["_history"]
            ]
            totals[column] = (
                sum(values)
                if complete and values and all(v is not None for v in values)
                else None
            )
        well_rates = [
            u["rate_bopd"]
            for u in owned
            if u["granularity"] == "well" and u["rate_bopd"] is not None
        ]
        share = None
        if len(well_rates) == len(wells) and all(
            w["oil_gas_code"] == "O" for w in wells
        ):
            share = sum(0 < r <= policy.stripper_bopd for r in well_rates) / len(
                well_rates
            )
        fields = Counter((w["district"], w.get("field_no")) for w in wells)
        hhi = None
        if all(key[1] for key in fields):
            # DOJ, Herfindahl-Hirschman Index (2024), definition: sum squared shares.
            # Fractions are used here; no antitrust thresholds are applied.
            hhi = sum((n / len(wells)) ** 2 for n in fields.values())
        in_band = policy.min_wells <= len(wells) <= policy.max_wells
        selection = (
            "OUTSIDE_SIZE_BAND"
            if not in_band
            else (
                "NOT_EVALUATED"
                if share is None
                else (
                    "SELECTED"
                    if share >= policy.min_stripper_share
                    else "BELOW_STRIPPER_SHARE"
                )
            )
        )
        dates = sorted(
            {
                m
                for u in owned
                for m, r in u["_history"].items()
                if m <= months[-1] and (r["oil_bbl"] > 0 or r["gas_mcf"] > 0)
            }
        )
        oil, water = totals["oil_bbl"], totals["water_bbl"]
        water_cut = None
        if oil is not None and water is not None and oil + water > 0:
            water_cut = water / (oil + water)  # Method M4: oil + water only; no gas.
        rows.append(
            {
                "operator_no": operator,
                "operator_name": names[0],
                "operator_names": names,
                "name_variant_count": len(names),
                "name_collision_count": len(
                    set().union(*(name_ids[normalize_name(n)] for n in names))
                    - {operator}
                ),
                "districts": sorted({w["district"] for w in wells}),
                "counties": sorted({w["county"] for w in wells}),
                "well_count_total": len(wells),
                "well_count_producing": sum(w["status"] == "producing" for w in wells),
                "well_count_inactive": sum(w["status"] == "inactive" for w in wells),
                "oil_bbl_window": oil,
                "gas_mcf_window": totals["gas_mcf"],
                "water_bbl_window": water,
                "water_cut_est": water_cut,
                "bopd_per_well_median": (
                    median(well_rates) if len(well_rates) == len(wells) else None
                ),
                "stripper_share": share,
                "field_count": len(fields) if hhi is not None else None,
                "field_concentration": hhi,
                "first_observed_production": dates[0] if dates else None,
                "last_observed_production": dates[-1] if dates else None,
                "window_complete": complete,
                "operator_size_band": "in_band" if in_band else "outside",
                "selection_status": selection,
                "signal_count": sum(u["signal_count"] for u in owned),
            }
        )
    return rows


def build_screen(bundle: dict, policy: Policy, *, as_of: str) -> dict:
    """Validate a local normalized snapshot, aggregate and rank reproducibly.

    Missing months are unknown. Duplicate snapshots, mixed grains and inventory
    transfers are rejected rather than silently allocated or deduplicated.
    """
    source = _source(bundle)
    months = _months(as_of, policy.window_months)
    if source["snapshot_date"] < as_of + "-01":
        raise ValueError("source snapshot predates analysis month")
    if source["inventory_date"][:7] != as_of:
        raise ValueError(
            "inventory date must fall in the analysis month; a dated join is required"
        )
    if source["inventory_date"] > source["snapshot_date"]:
        raise ValueError("inventory date is later than the source snapshot")
    inventory = _inventory(bundle)
    grouped, grains = _production(bundle, inventory, months)
    units = [
        _unit(lease, grain, api, inventory[lease], history, months, policy)
        for (lease, grain, api), history in sorted(grouped.items())
    ]
    units = _rank_units(units, policy)
    operators = _registry(inventory, units, months, policy)
    ranked = sorted(
        (o for o in operators if o["operator_size_band"] == "in_band"),
        key=lambda o: (-o["signal_count"], o["operator_no"]),
    )
    canonical_bundle = dict(bundle)
    for key in ("wells", "production"):
        canonical_bundle[key] = sorted(
            bundle.get(key, []), key=lambda r: json.dumps(r, sort_keys=True)
        )
    canonical = json.dumps(
        canonical_bundle, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return {
        "method_version": "operator_screen_v1",
        "as_of": as_of,
        "window": months,
        "policy": asdict(policy),
        "source": source,
        "input_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "validation_gate": "NOT_EVALUATED",
        "operators": operators,
        "ranked_operators": ranked,
        "candidates": [
            {k: v for k, v in u.items() if not k.startswith("_")} for u in units
        ],
        "coverage": {
            "production_rows_by_granularity": grains,
            "operators_with_complete_window": sum(
                o["window_complete"] for o in operators
            ),
            "operators_by_size_band": dict(
                sorted(Counter(o["operator_size_band"] for o in operators).items())
            ),
            "operators_by_district": dict(
                sorted(Counter(d for o in operators for d in o["districts"]).items())
            ),
        },
        "sensitivity": {
            "peer_eligible_candidates": sum(
                u["peer_status"] == "EVALUATED" for u in units
            ),
            "peer_definition": "district + field + fluid + vintage bucket + grain + well count",
            "validation_false_positive_rate": "NOT_EVALUATED",
        },
    }
