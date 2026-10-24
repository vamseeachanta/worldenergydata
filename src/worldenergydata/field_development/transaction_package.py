"""Basis-separated transaction screening; missing evidence never becomes zero.

Ratios are dimensional definitions, not an economic model: consideration in USD
divided by reserves in boe or production in boe/day. No conversion factor,
working-interest adjustment, discount rate, or acceptance threshold is supplied.
"""

from __future__ import annotations

import csv
import hashlib
import json
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


def valuation_metrics(consideration: dict, reserves: dict, production: dict) -> dict:
    """Calculate two independent ratios with their input evidence echoed.

    The equations are unit-price definitions, derived explicitly in the worked
    example in docs/field-development-transactions.html (2026), Method section.
    Denominators must already represent the same acquired-interest asset scope
    and consideration basis. Zero reserves or production is unevaluable.
    """
    amount = _number(consideration, "USD")
    results = {}
    for key, denominator, unit in (
        ("usd_per_boe", reserves, "boe"),
        ("usd_per_flowing_boe_day", production, "boe/d"),
    ):
        quantity = _number(denominator, unit)
        if amount is not None and quantity is not None:
            for identity in ("basis", "subject"):
                if consideration[identity] != denominator[identity]:
                    raise ValueError(f"Mixed {identity}: ratio refused")
        evaluated = amount is not None and quantity is not None and quantity > 0
        reasons = [
            fact["reason"]
            for fact in (consideration, denominator)
            if fact.get("value") is None
        ]
        if quantity == 0:
            reasons.append("Denominator is zero")
        results[key] = {
            "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
            "value": float(amount / quantity) if evaluated else None,
            "unit": f"USD/({unit})",
            "reason": "; ".join(reasons),
            "inputs": {"consideration": consideration, "denominator": denominator},
        }
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
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("Source digest mismatch; refresh evidence explicitly")


def _verify_citation(citation: dict, sources: dict) -> None:
    if not citation.get("locator") or citation.get("source_id") not in sources:
        raise ValueError("Citation requires a known source and claim locator")
    if sources[citation["source_id"]]["access"] != "available":
        raise ValueError("Known facts cannot cite unavailable sources")


def _catalog(source: dict, root: Path) -> list[dict]:
    with (root / source["path"]).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


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
                "host": "Na Kika" if name == "Coulomb" else None,
                "host_concept": "semisub_fps" if asset["kind"] == "hub" else None,
                "host_concept_citation": (
                    {
                        "source_id": "catalog_host",
                        "locator": "NA KIKA row; SemiSub classification",
                    }
                    if asset["kind"] == "hub"
                    else None
                ),
                "field_concept": "subsea_tieback" if name == "Coulomb" else None,
                "field_concept_citation": (
                    {
                        "source_id": "shell_release",
                        "locator": "meta[name=description]: Coulomb tieback",
                    }
                    if name == "Coulomb"
                    else None
                ),
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
                "transaction_membership_status": (
                    "SOURCE_SUPPORTED"
                    if name in {"Na Kika", "Coulomb"}
                    else "NOT_EVALUATED"
                ),
                "lifecycle_status": "CATALOG_ONLY" if field else "NOT_EVALUATED",
                "generated_page_status": "present" if page_exists else "missing",
                "report_path": relative_page if page_exists else None,
                "limitation": (
                    "Host concept is not a field concept. Satellite association and "
                    "sale membership require source confirmation; expansion timing is unverified."
                ),
            }
        )
    for asset in assets:
        asset["transaction_membership_citation"] = (
            {
                "source_id": "shell_release",
                "locator": "meta[name=description]: interests included in the sale",
            }
            if asset["transaction_membership_status"] == "SOURCE_SUPPORTED"
            else None
        )
        for key, citation in asset.items():
            if key.endswith("_citation") and citation is not None:
                _verify_citation(citation, data["sources"])
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
            if fact.get("value") is not None:
                _verify_citation(fact.get("citation", {}), sources)
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
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return {
        "title": data["title"],
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
        "lifecycle": {"assets": assets, "coverage_note": data["coverage_note"]},
        "economics_readiness": {"status": "NOT_EVALUATED", "fields": readiness},
        "provenance": {
            "input_sha256": hashlib.sha256(canonical).hexdigest(),
            "digest_domain": "UTF-8 JSON, sorted keys, compact separators",
            "sources": sources,
        },
    }
