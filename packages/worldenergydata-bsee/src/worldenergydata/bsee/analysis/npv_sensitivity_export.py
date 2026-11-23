"""Opt-in API12 sensitivity export with explicit economics and monthly timing."""

import csv
from copy import deepcopy
from math import isfinite
from pathlib import Path

from pandas import to_numeric

from worldenergydata.bsee.analysis.production_api12 import (
    ProductionAPI12Analysis,
    _currency_to_float,
)


def _finite_number(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be finite numeric input") from exc
    if not isfinite(number):
        raise ValueError(f"{label} must be finite numeric input")
    return number


def export_npv_sensitivity(cfg, revenue_df, destination, *, field_id, api12, rates):
    """Write one CSV row per rate, preserving caller order and input objects.

    CAPEX (USD) and OPEX (USD/bbl) must be explicit in economics.cost.
    Rates are annual effective fractions in (-1, 1]. Operating rows represent
    consecutive month ends in caller order; blank Month rows are summary rows.
    Revenue uses the API12 dollar/comma formatting convention, production bbl.
    Royalty is NOT_EVALUATED; values are after OPEX and before royalty.
    All validation and calculations finish before exclusive destination creation.
    The parent folder must exist. Returns the destination Path.
    """
    for label, value in (("field_id", field_id), ("api12", api12)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be a nonempty string")
    annual_rates = [_finite_number(rate, "rate") for rate in rates]
    if not annual_rates or any(not -1 < rate <= 1 for rate in annual_rates):
        raise ValueError("rates must be nonempty and greater than -1, at most 1")
    if len(set(annual_rates)) != len(annual_rates):
        raise ValueError("duplicate rates are not allowed")

    try:
        costs = cfg["economics"]["cost"]
        for key in ("CAPEX", "OPEX"):
            _finite_number(costs[key], key)
    except (KeyError, TypeError) as exc:
        raise ValueError("explicit economics.cost CAPEX and OPEX are required") from exc
    if "discount_rate_annual" in costs:
        _finite_number(costs["discount_rate_annual"], "discount_rate_annual")

    required = {"Month", "Revenue (USD)", "Monthly Oil Production"}
    if not required.issubset(revenue_df.columns):
        raise ValueError("Month, Revenue (USD) and Monthly Oil Production are required")
    if revenue_df["Month"].isna().any():
        raise ValueError("Month must not be missing")
    working = revenue_df[revenue_df["Month"].astype(str).str.strip() != ""].copy(
        deep=True
    )
    if working.empty:
        raise ValueError("at least one operating month is required")
    for column in ("Revenue (USD)", "Monthly Oil Production"):
        values = working[column]
        if values.isna().any() or values.astype(str).str.strip().eq("").any():
            raise ValueError(f"missing {column}")
        for value in values:
            if column == "Revenue (USD)":
                token = str(value).replace("$", "").replace(",", "").strip()
                _finite_number(token, column)
                _finite_number(_currency_to_float(value), column)
            else:
                _finite_number(to_numeric(value, errors="raise"), column)

    analyzer = ProductionAPI12Analysis()
    rows = []
    for rate in annual_rates:
        rate_cfg = deepcopy(cfg)
        rate_cfg["economics"]["cost"]["discount_rate_annual"] = rate
        result = analyzer.calculate_npv_with_citations(
            rate_cfg, working.copy(deep=True), period="monthly"
        )
        rows.append(
            {
                "field_id": field_id,
                "api12": api12,
                "discount_rate_annual": rate,
                "rate_basis": "annual effective",
                "cashflow_period": "monthly",
                "timing_basis": "CAPEX at period 0; receipts at month ends",
                "currency": "USD",
                "npv_basis": "after OPEX and before royalty",
                "royalty_status": result["royalty_status"],
                "npv": _finite_number(result["npv"], "calculated NPV"),
            }
        )

    path = Path(destination)
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path
