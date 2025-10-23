# ABOUTME: Implements Lower Tertiary field-level financial calculations and NPV metrics
# ABOUTME: Loads modular field configurations and FDAS lease mappings for analysis workflows

"""Lower Tertiary NPV analysis utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml


def _read_yaml(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def _normalize_lease(value: str) -> str:
    return value.strip().upper()


def load_lease_mapping(path: Path | str) -> Dict[str, Dict[str, object]]:
    """Load FDAS lease mapping details with normalized lease numbers."""

    mapping_path = Path(path)
    data = _read_yaml(mapping_path)

    fields_section = data.get("fields", {})
    normalized_fields: Dict[str, Dict[str, object]] = {}
    for key, payload in fields_section.items():
        leases = [_normalize_lease(item) for item in payload.get("leases", [])]
        normalized_fields[key] = {
            **{k: v for k, v in payload.items() if k != "leases"},
            "leases": leases,
        }

    lease_lookup = {
        _normalize_lease(lease): name for lease, name in (data.get("lease_to_field", {}) or {}).items()
    }

    return {
        "fields": normalized_fields,
        "lease_to_field": lease_lookup,
        "raw": data,
    }


def _resolve_first_oil(value: object) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        return value
    if value is None:
        return pd.Timestamp("1970-01-01")
    return pd.to_datetime(value)


def load_field_inputs(
    fields_dir: Path | str,
    lease_mapping: Dict[str, Dict[str, object]],
    status_filter: Optional[str] = None,
) -> Dict[str, Dict[str, object]]:
    """Load modular field configurations and attach verified lease numbers."""

    directory = Path(fields_dir)
    if not directory.exists():
        raise FileNotFoundError(f"Field configuration directory not found: {directory}")

    status_filter_normalized = status_filter.lower() if status_filter else None
    normalized_fields = lease_mapping.get("fields", {})

    profiles: Dict[str, Dict[str, object]] = {}
    for file_path in sorted(directory.glob("*.yml")):
        contents = _read_yaml(file_path)
        field_payload = contents.get("field", contents)

        field_id = field_payload.get("field_id") or file_path.stem
        field_id = str(field_id).strip()
        status = str(field_payload.get("status", "unknown")).lower()
        if status_filter_normalized and status != status_filter_normalized:
            continue

        display_name = field_payload.get("display_name") or field_payload.get("name") or field_payload.get("field_name") or field_id
        leases_key = field_payload.get("leases_key", field_id)
        leases = field_payload.get("leases")
        if leases is None:
            leases = normalized_fields.get(leases_key, {}).get("leases", [])
        leases = [_normalize_lease(item) for item in leases]

        capex = field_payload.get("capex") or {}
        first_oil = _resolve_first_oil(field_payload.get("first_oil") or field_payload.get("key_dates", {}).get("first_oil"))
        data_through_value = field_payload.get("data_through") or field_payload.get("key_dates", {}).get("data_through")
        data_through = pd.to_datetime(data_through_value) if data_through_value else None

        profiles[field_id] = {
            "field_id": field_id,
            "display_name": display_name,
            "status": status,
            "first_oil": first_oil,
            "data_through": data_through,
            "capex": capex,
            "leases": leases,
            "opex_per_boe": field_payload.get("opex_per_boe"),
            "raw": field_payload,
        }

    return profiles


def calculate_monthly_financials(
    monthly: pd.DataFrame,
    econ_config: Dict[str, object],
    opex_per_boe: float,
) -> pd.DataFrame:
    """Calculate monthly financial metrics for a field-level production frame."""

    df = monthly.copy()
    if df.empty:
        return df

    oil_price = float(
        econ_config["commodity_prices"]["oil"]["base_case"]["wti_usd_per_bbl"]
    )
    gas_price = float(
        econ_config["commodity_prices"]["gas"]["base_case"]["henry_hub_usd_per_mcf"]
    )
    royalty_rate = float(econ_config["fiscal_terms"]["royalty"]["rate"])
    tax_rate = float(econ_config["fiscal_terms"]["taxes"]["federal_income_tax"]["rate"])

    df["oil_revenue"] = df.get("oil_bbl", 0.0) * oil_price
    df["gas_revenue"] = df.get("gas_mcf", 0.0) * gas_price
    df["total_revenue"] = df["oil_revenue"] + df["gas_revenue"]
    df["boe"] = df.get("oil_bbl", 0.0) + df.get("gas_mcf", 0.0) / 6.0
    df["royalty"] = df["total_revenue"] * royalty_rate
    df["net_revenue"] = df["total_revenue"] - df["royalty"]
    df["opex"] = df["boe"] * opex_per_boe
    df["operating_income"] = df["net_revenue"] - df["opex"]
    df["tax"] = df["operating_income"].clip(lower=0) * tax_rate
    df["operating_cash_flow"] = df["operating_income"] - df["tax"]

    return df


def summarize_field_financials(
    monthly: pd.DataFrame,
    field_profile: Dict[str, object],
    econ_config: Dict[str, object],
) -> Dict[str, float | str | int]:
    """Summarize key production and financial metrics for a field."""

    if monthly.empty:
        raise ValueError("Monthly dataframe must contain at least one record")

    first_oil = _resolve_first_oil(field_profile.get("first_oil"))
    discount_rate = float(
        econ_config["financial_metrics"]["discount_rates"]["primary_discount_rate"]
    )
    monthly_discount = (1 + discount_rate) ** (1 / 12) - 1

    df = monthly.copy()
    df = df.sort_values("date")
    df["months_from_first_oil"] = (
        (df["date"].dt.year - first_oil.year) * 12
        + (df["date"].dt.month - first_oil.month)
    )
    df["discount_factor"] = 1 / ((1 + monthly_discount) ** df["months_from_first_oil"])

    if "operating_cash_flow" in df.columns:
        df["operating_cash_flow"] = df["operating_cash_flow"].fillna(0.0)
    else:
        df["operating_cash_flow"] = 0.0
    df["pv_cash_flow"] = df["operating_cash_flow"] * df["discount_factor"]

    total_oil = df.get("oil_bbl", pd.Series(0.0)).sum()
    total_gas = df.get("gas_mcf", pd.Series(0.0)).sum()
    total_revenue = df.get("total_revenue", pd.Series(0.0)).sum()
    total_royalty = df.get("royalty", pd.Series(0.0)).sum()
    total_opex = df.get("opex", pd.Series(0.0)).sum()
    total_ocf = df.get("operating_cash_flow", pd.Series(0.0)).sum()
    npv_operations = df["pv_cash_flow"].sum()

    boe = total_oil + total_gas / 6.0
    capex_total = float(field_profile.get("capex", {}).get("total_mm_usd", 0.0))

    npv_operations_mm = npv_operations / 1_000_000.0
    npv_project_mm = npv_operations_mm - capex_total
    profitability_index = (npv_project_mm / capex_total) if capex_total else 0.0

    return {
        "Field": field_profile.get("display_name", field_profile.get("field_id", "Unknown")),
        "First Oil": first_oil.strftime("%Y-%m"),
        "Months": int(len(df)),
        "Oil (MMBO)": total_oil / 1_000_000.0,
        "Gas (BCF)": total_gas / 1_000_000_000.0,
        "BOE (MMBOE)": boe / 1_000_000.0,
        "Revenue ($MM)": total_revenue / 1_000_000.0,
        "Royalty ($MM)": total_royalty / 1_000_000.0,
        "Opex ($MM)": total_opex / 1_000_000.0,
        "Op Cash Flow ($MM)": total_ocf / 1_000_000.0,
        "CAPEX ($MM)": capex_total,
        "NPV Operations ($MM)": npv_operations_mm,
        "NPV Project ($MM)": npv_project_mm,
        "PI": profitability_index,
    }
