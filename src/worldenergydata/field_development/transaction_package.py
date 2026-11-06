"""Basis-separated transaction screening; missing evidence never becomes zero.

Ratios are dimensional definitions, not an economic model: consideration in USD
divided by reserves in boe or production in boe/day. No conversion factor,
working-interest adjustment, discount rate, or acceptance threshold is supplied.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit


def _number(fact: dict, unit: str) -> Decimal | None:
    if fact.get("unit") != unit:
        raise ValueError(f"Expected unit {unit}")
    if fact.get("value") is None:
        if not fact.get("reason"):
            raise ValueError("Missing values require a reason")
        return None
    citation = fact.get("citation", {})
    required = ("basis", "subject", "as_of")
    if not all(fact.get(key) for key in required) or not all(
        citation.get(key) for key in ("source_id", "locator")
    ):
        raise ValueError("Known values require basis, subject, date and citation")
    try:
        value = Decimal(str(fact["value"]))
    except InvalidOperation as exc:
        raise ValueError("Numeric value required") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("Values must be finite and nonnegative")
    return value


def _consideration_values(fact: dict) -> list[Decimal] | None:
    if "range" not in fact:
        value = _number(fact, "USD")
        return [value] if value is not None else None
    bounds = fact["range"]
    if (
        fact.get("value") is not None
        or not isinstance(bounds, list)
        or len(bounds) != 2
    ):
        raise ValueError(
            "Consideration range requires exactly two bounds and no point value"
        )
    values = [_number({**fact, "value": bound}, "USD") for bound in bounds]
    if any(value is None for value in values) or values[0] > values[1]:
        raise ValueError("Consideration range requires ordered numeric bounds")
    return values


def _finite_ratio(amount: Decimal, quantity: Decimal) -> float:
    ratio = amount / quantity
    value = float(ratio)
    if not math.isfinite(value) or (ratio != 0 and value == 0):
        raise ValueError(
            "Ratio cannot be represented as a finite non-underflowing number"
        )
    return value


def valuation_metrics(consideration: dict, reserves: dict, production: dict) -> dict:
    """Calculate two independent ratios with their input evidence echoed.

    The equations are unit-price definitions, derived explicitly in the worked
    example in docs/field-development-transactions.html (2026), Method section.
    Denominators must already represent the same acquired-interest asset scope
    and consideration basis. Zero reserves or production is unevaluable.
    """
    amounts = _consideration_values(consideration)
    results = {}
    for key, denominator, unit in (
        ("usd_per_boe", reserves, "boe"),
        ("usd_per_flowing_boe_day", production, "boe/d"),
    ):
        quantity = _number(denominator, unit)
        if amounts is not None and quantity is not None:
            for identity in ("basis", "subject"):
                if consideration[identity] != denominator[identity]:
                    raise ValueError(f"Mixed {identity}: ratio refused")
        evaluated = amounts is not None and quantity is not None and quantity > 0
        reasons = [
            fact["reason"]
            for fact in (consideration, denominator)
            if fact.get("value") is None and "range" not in fact
        ]
        if quantity == 0:
            reasons.append("Denominator is zero")
        results[key] = {
            "status": (
                ("EVALUATED_RANGE" if len(amounts) == 2 else "EVALUATED")
                if evaluated
                else "NOT_EVALUATED"
            ),
            "value": (
                _finite_ratio(amounts[0], quantity)
                if evaluated and len(amounts) == 1
                else None
            ),
            "unit": f"USD/({unit})",
            "reason": "; ".join(reasons),
            "inputs": {"consideration": consideration, "denominator": denominator},
        }
        if evaluated and len(amounts) == 2:
            results[key]["range"] = [
                _finite_ratio(amount, quantity) for amount in amounts
            ]
    return results


def _verify_sources(sources: dict, root: Path) -> None:
    for source in sources.values():
        if "url" in source:
            url = urlsplit(source["url"])
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username
                or url.password
            ):
                raise ValueError("Public source URLs require credential-free HTTPS")
        digest = source.get("sha256", "")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Source digest must be SHA-256")
        if "path" in source:
            path = (root / source["path"]).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("Source path must stay inside the repository")
            content = path.read_bytes()
            domain = source.get("digest_domain", "source-bytes")
            if domain == "UTF-8 text; CRLF normalized to LF":
                content = content.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
            elif domain != "source-bytes":
                raise ValueError("Unsupported source digest domain")
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError("Source digest mismatch; refresh evidence explicitly")


def _verify_citation(citation: dict, sources: dict) -> None:
    if not citation.get("locator") or citation.get("source_id") not in sources:
        raise ValueError("Citation requires a known source and claim locator")
    if sources[citation["source_id"]]["access"] != "available":
        raise ValueError("Known facts cannot cite unavailable sources")


def _catalog(source: dict, root: Path) -> list[dict]:
    with (root / source["path"]).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _verify_host_concept(asset: dict, sources: dict, root: Path) -> None:
    if asset["host_concept"] is None:
        return
    citation = asset["host_concept_citation"]
    if citation["source_id"] != "catalog_host":
        raise ValueError("Host concept requires the host catalog")
    rows = [
        row
        for row in _catalog(sources["catalog_host"], root)
        if row["VESSEL_NAME"] == citation.get("row_name")
    ]
    concepts = {"SemiSub": "semisub_fps", "FPSO": "fpso", "TLP": "tlp", "Spar": "spar"}
    if (
        len(rows) != 1
        or concepts.get(rows[0]["FACILITY_TYPE"]) != asset["host_concept"]
    ):
        raise ValueError("Host concept differs from the cited catalog row")


def _lifecycle(data: dict, root: Path) -> list[dict]:
    fields = {
        r["FIELD_NAME"]: r for r in _catalog(data["sources"]["catalog_fields"], root)
    }
    crosswalk = {
        r["og_field_name"]: r
        for r in _catalog(data["sources"]["catalog_crosswalk"], root)
    }
    assets = []
    for asset in data["assets"]:
        name = asset["name"]
        field = fields.get(name, {})
        cross = crosswalk.get(name, {})
        slug = name.lower().replace(" ", "-")
        relative_page = f"reports/field_development/bsee_matched/{slug}.html"
        page_exists = (root / relative_page).is_file()
        assets.append(
            {
                **asset,
                "catalog_host_concept": cross.get("host_concept"),
                "catalog_discovery": field.get("DISCOVERY_DATE"),
                "catalog_first_production": field.get("PRODUCTION_START"),
                "catalog_citation": (
                    {"source_id": "catalog_fields", "locator": f"FIELD_NAME={name}"}
                    if field
                    else None
                ),
                "block": cross.get("bsee_block_code"),
                "block_match": cross.get("matched") == "1",
                "block_citation": (
                    {
                        "source_id": "catalog_crosswalk",
                        "locator": f"og_field_name={name}",
                    }
                    if cross
                    else None
                ),
                "lifecycle_status": "CATALOG_ONLY" if field else "NOT_EVALUATED",
                "generated_page_status": "present" if page_exists else "missing",
                "report_path": relative_page if page_exists else None,
            }
        )
    for asset in assets:
        for claim in ("host", "host_concept", "field_concept"):
            if asset[claim] is not None:
                _verify_citation(asset.get(f"{claim}_citation") or {}, data["sources"])
        status = asset["transaction_membership_status"]
        if status == "SOURCE_SUPPORTED":
            _verify_citation(
                asset.get("transaction_membership_citation") or {}, data["sources"]
            )
        elif status != "NOT_EVALUATED" or not asset.get(
            "transaction_membership_reason"
        ):
            raise ValueError(
                "Membership requires supported evidence or an unevaluated reason"
            )
        elif asset.get("transaction_membership_citation") is not None:
            raise ValueError(
                "Unevaluated membership cannot carry a supporting citation"
            )
        for key, citation in asset.items():
            if key.endswith("_citation") and citation is not None:
                _verify_citation(citation, data["sources"])
        _verify_host_concept(asset, data["sources"], root)
    return assets


def build_package(data: dict, root: Path) -> dict:
    """Build an offline snapshot from cited input and digest-pinned catalogs.

    Block matches expose candidate join keys only. They are never interpreted
    as verified field production, field reserves, or economic qualification.
    """
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported transaction input schema")
    sources = data["sources"]
    _verify_sources(sources, root)
    _verify_citation(data["transaction"]["buyer_group_citation"], sources)
    for fact in data["transaction"]["working_interests"]:
        value = _number(fact, "fraction")
        if value is None or value > 1:
            raise ValueError("Working interest must be between zero and one")
        _verify_citation(fact["citation"], sources)
    metrics = {}
    for basis, facts in data["bases"].items():
        for fact in facts.values():
            if fact.get("value") is not None or "range" in fact:
                _verify_citation(fact.get("citation", {}), sources)
                if "range" not in fact:
                    _number(fact, fact["unit"])
                if fact.get("basis") != basis:
                    raise ValueError("Observation basis differs from its container")
        metrics[basis] = valuation_metrics(
            facts["consideration"], facts["reserves"], facts["production"]
        )
    assets = _lifecycle(data, root)
    missing_inputs = [
        "verified_field_production",
        "public_reserves_and_interest_basis",
        "price_forecast",
        "opex",
        "capex",
        "fiscal_terms",
        "discount_rate",
        "decommissioning_cost_and_timing",
    ]
    readiness = [
        {
            "name": asset["name"],
            "block": asset["block"],
            "block_match": asset["block_match"],
            "status": "NOT_EVALUATED",
            "npv_usd": None,
            "missing_inputs": missing_inputs.copy(),
            "refresh_method": (
                "Resolve field-to-lease/API membership, retain dated BSEE monthly production, "
                "reconcile units and acquired interest, then supply cited economics assumptions."
            ),
        }
        for asset in assets
        if asset["kind"] == "field"
    ]
    canonical = json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return {
        "title": data["title"],
        "revision_history": data["revision_history"],
        "evidence_as_of": data["evidence_as_of"],
        "transaction": data["transaction"],
        "input_echo": data,
        "metrics": {
            "screening_status": "NOT_EVALUATED",
            "criterion": (
                "Field economics require qualified production, reserves and explicit assumptions; "
                "transaction ratios alone are not a valuation opinion."
            ),
            "bases": metrics,
        },
        "lifecycle": {
            "title": data["lifecycle_title"],
            "limitation": data["lifecycle_limitation"],
            "assets": assets,
            "coverage_note": data["coverage_note"],
        },
        "economics_readiness": {"status": "NOT_EVALUATED", "fields": readiness},
        "provenance": {
            "input_sha256": hashlib.sha256(canonical).hexdigest(),
            "digest_domain": (
                "UTF-8 JSON, sorted keys, compact separators, "
                "ensure_ascii=False, allow_nan=False"
            ),
            "sources": sources,
        },
    }
