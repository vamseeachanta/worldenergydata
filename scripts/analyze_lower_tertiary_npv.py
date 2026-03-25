#!/usr/bin/env python3
"""
ABOUTME: Lower Tertiary NPV analysis using actual production data through Dec 2024
ABOUTME: Generates NPV comparison tables against World Oil report benchmarks

This script extracts BSEE production data for Lower Tertiary fields and calculates
NPV using actual historical performance through December 2024.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import warnings

warnings.filterwarnings("ignore")


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from worldenergydata.analysis.lower_tertiary.npv import (  # noqa: E402
    calculate_monthly_financials,
    load_field_inputs,
    load_lease_mapping,
    summarize_field_financials,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lower Tertiary field-level NPV analysis")
    parser.add_argument(
        "--fields",
        nargs="+",
        help="Field identifiers or display names to analyze (default: all producing fields)",
    )
    parser.add_argument(
        "--status",
        default="producing",
        help="Status filter for field configurations (producing, under_development, pre_fid, all)",
    )
    return parser.parse_args(argv)


def load_yaml(path: Path) -> dict:
    import yaml

    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


import zipfile


def load_production_data(zip_paths: list[Path]) -> pd.DataFrame:
    column_names = [
        "LEASE_NUMBER",
        "COMPLETION_NAME",
        "PRODUCTION_DATE",
        "DAYS_ON_PROD",
        "PRODUCT_CODE",
        "MON_O_PROD_VOL",
        "MON_G_PROD_VOL",
        "MON_WTR_PROD_VOL",
        "API_WELL_NUMBER",
        "WELL_STAT_CD",
        "AREA_CODE_BLOCK_NUM",
        "OPERATOR_NUM",
        "SORT_NAME",
        "BOEM_FIELD",
        "INJECTION_VOLUME",
        "PROD_INTERVAL_CD",
        "FIRST_PROD_DATE",
        "UNIT_AGT_NUMBER",
        "UNIT_ALOC_SUFFIX",
    ]

    frames: list[pd.DataFrame] = []

    for path in zip_paths:
        with zipfile.ZipFile(path, "r") as archive:
            inner_name = f"{path.stem}.txt"
            if inner_name not in archive.namelist():
                inner_name = "ogoradelimit.txt"
            with archive.open(inner_name) as handle:
                frame = pd.read_csv(handle, sep=",", names=column_names, low_memory=False, quotechar='"')
                frame["source_file"] = path.name
                frames.append(frame)

    if not frames:
        raise FileNotFoundError("No production files loaded")

    df = pd.concat(frames, ignore_index=True)
    df["LEASE_NUMBER"] = (
        df["LEASE_NUMBER"].astype(str).str.strip().str.replace('"', "").str.replace(" ", "")
    )
    df["date"] = pd.to_datetime(df["PRODUCTION_DATE"], format="%Y%m", errors="coerce")
    return df


def normalize_identifier(value: str) -> str:
    return value.lower().replace("/", "_").replace(" ", "_")


def resolve_target_fields(
    field_inputs: dict[str, dict[str, object]],
    requested: list[str] | None,
) -> dict[str, dict[str, object]]:
    if not requested:
        return field_inputs

    lookup = {}
    for field_id, payload in field_inputs.items():
        lookup[normalize_identifier(field_id)] = field_id
        lookup[normalize_identifier(payload.get("display_name", field_id))] = field_id

    selected: dict[str, dict[str, object]] = {}
    missing: list[str] = []
    for item in requested:
        normalized = normalize_identifier(item)
        field_id = lookup.get(normalized)
        if field_id:
            selected[field_id] = field_inputs[field_id]
        else:
            missing.append(item)

    if missing:
        print(f"⚠️  Requested fields not found: {', '.join(missing)}")
    if not selected:
        raise ValueError("No valid fields resolved for analysis")
    return selected


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    print("=" * 80)
    print("Lower Tertiary NPV Analysis - Using Actual Production Through Dec 2024")
    print("=" * 80)

    econ_path = project_root / "config/analysis/lower_tertiary/economic_assumptions.yml"
    econ_config = load_yaml(econ_path)

    lease_mapping_path = project_root / "config/analysis/lower_tertiary/lease_mapping_fdas.yml"
    lease_mapping = load_lease_mapping(lease_mapping_path)

    fields_dir = project_root / "config/analysis/lower_tertiary/fields"
    status_filter = None if args.status.lower() == "all" else args.status.lower()
    field_inputs = load_field_inputs(fields_dir, lease_mapping, status_filter=status_filter)
    target_fields = resolve_target_fields(field_inputs, args.fields)

    print(f"\n1. Field configurations loaded: {len(target_fields)} selected")

    oil_price = econ_config["commodity_prices"]["oil"]["base_case"]["wti_usd_per_bbl"]
    gas_price = econ_config["commodity_prices"]["gas"]["base_case"]["henry_hub_usd_per_mcf"]
    royalty_rate = econ_config["fiscal_terms"]["royalty"]["rate"]
    tax_rate = econ_config["fiscal_terms"]["taxes"]["federal_income_tax"]["rate"]
    discount_rate = econ_config["financial_metrics"]["discount_rates"]["primary_discount_rate"]

    print("\n2. Economic Parameters:")
    print(f"   Oil price: ${oil_price:.2f}/bbl")
    print(f"   Gas price: ${gas_price:.2f}/mcf")
    print(f"   Royalty rate: {royalty_rate * 100:.2f}%")
    print(f"   Tax rate: {tax_rate * 100:.0f}%")
    print(f"   Discount rate: {discount_rate * 100:.0f}%")

    zip_dir = project_root / "data/modules/bsee/zip/historical_production_yearly"
    first_oil_years = [int(profile["first_oil"].year) for profile in target_fields.values()]
    start_year = max(1996, min(first_oil_years))
    end_year = 2024
    zip_paths = []
    for year in range(start_year, end_year + 1):
        candidate = zip_dir / f"ogora{year}delimit.zip"
        if candidate.exists():
            zip_paths.append(candidate)

    if not zip_paths:
        raise FileNotFoundError("No OGOR production files found for selected timeframe")

    print("\n3. Loading BSEE production data...")
    print("   Using files:")
    for path in zip_paths:
        print(f"     - {path.name}")

    df_prod = load_production_data(zip_paths)
    print(f"   ✓ Loaded {len(df_prod):,} production records")
    print(
        f"   Date range: {df_prod['date'].min().date()} to {df_prod['date'].max().date()}"
    )

    lease_to_field = {
        lease: field_id
        for field_id, payload in target_fields.items()
        for lease in payload.get("leases", [])
    }

    target_leases = set(lease_to_field.keys())
    df_subset = df_prod[df_prod["LEASE_NUMBER"].isin(target_leases)].copy()

    if df_subset.empty:
        raise RuntimeError("No production records found for selected fields")

    for column in ["MON_O_PROD_VOL", "MON_G_PROD_VOL"]:
        df_subset[column] = (
            df_subset[column].astype(str).str.replace('"', "").str.strip()
        )
        df_subset[column] = pd.to_numeric(df_subset[column], errors="coerce").fillna(0.0)

    df_subset["field_id"] = df_subset["LEASE_NUMBER"].map(lease_to_field)
    df_subset = df_subset.dropna(subset=["field_id", "date"])

    monthly_prod = (
        df_subset.groupby(["field_id", "date"], as_index=False)[
            ["MON_O_PROD_VOL", "MON_G_PROD_VOL"]
        ]
        .sum()
        .rename(columns={"MON_O_PROD_VOL": "oil_bbl", "MON_G_PROD_VOL": "gas_mcf"})
    )

    monthly_prod = monthly_prod[monthly_prod["date"] <= "2024-12-31"]

    print(f"\n4. Aggregated to {len(monthly_prod):,} field-month records")

    all_field_results: list[dict[str, object]] = []
    monthly_outputs: dict[str, pd.DataFrame] = {}

    for field_id, profile in target_fields.items():
        field_monthly = monthly_prod[monthly_prod["field_id"] == field_id].copy()
        display_name = profile.get("display_name", field_id)

        first_oil = profile.get("first_oil")
        if isinstance(first_oil, pd.Timestamp):
            field_monthly = field_monthly[field_monthly["date"] >= first_oil]

        if field_monthly.empty:
            print(f"   ⚠️  No production data for {display_name}; skipping")
            continue

        field_monthly["field"] = display_name
        opex_per_boe = profile.get("raw", {}).get("opex_per_boe") or profile.get("opex_per_boe") or 15.0

        field_financials = calculate_monthly_financials(
            field_monthly, econ_config, float(opex_per_boe)
        )
        summary = summarize_field_financials(field_financials, profile, econ_config)
        all_field_results.append(summary)
        monthly_outputs[field_id] = field_financials

        total_oil = field_financials["oil_bbl"].sum() / 1e6
        total_gas = field_financials["gas_mcf"].sum() / 1e9
        first_date = field_financials["date"].min().date()
        last_date = field_financials["date"].max().date()
        print(
            f"   - {display_name}: {total_oil:.1f} MMBO, {total_gas:.1f} BCF"
            f" ({len(field_financials)} months, {first_date} to {last_date})"
        )

    if not all_field_results:
        raise RuntimeError("No field results computed; exiting")

    df_results = pd.DataFrame(all_field_results).sort_values(
        "NPV Project ($MM)", ascending=False
    )

    print("\n" + "=" * 80)
    print("NPV ANALYSIS RESULTS - LOWER TERTIARY FIELDS")
    print("=" * 80)
    print("\nProduction Summary (Through December 2024):")
    print("-" * 80)
    print(
        df_results[
            ["Field", "First Oil", "Months", "Oil (MMBO)", "Gas (BCF)", "BOE (MMBOE)"]
        ].to_string(index=False)
    )

    print("\n\nFinancial Summary:")
    print("-" * 80)
    print(
        df_results[["Field", "Revenue ($MM)", "Opex ($MM)", "Op Cash Flow ($MM)"]].to_string(
            index=False
        )
    )

    print("\n\nNPV Analysis (10% Discount Rate):")
    print("-" * 80)
    print(
        df_results[
            ["Field", "CAPEX ($MM)", "NPV Operations ($MM)", "NPV Project ($MM)", "PI"]
        ].to_string(index=False)
    )

    benchmarks = {
        "Jack/St. Malo": {"prod_mmboe": 150, "revenue_mm": 8000, "npv_mm": 3500},
        "Stones": {"prod_mmboe": 80, "revenue_mm": 4500, "npv_mm": 2000},
        "Julia": {"prod_mmboe": 50, "revenue_mm": 2800, "npv_mm": 1200},
    }

    comparison_rows: list[dict[str, object]] = []
    for field_name, bench in benchmarks.items():
        actual = df_results[df_results["Field"] == field_name]
        if actual.empty:
            continue
        actual_prod = actual["BOE (MMBOE)"].iloc[0]
        actual_revenue = actual["Revenue ($MM)"].iloc[0]
        actual_npv = actual["NPV Project ($MM)"].iloc[0]

        prod_var = (
            ((actual_prod - bench["prod_mmboe"]) / bench["prod_mmboe"]) * 100 if bench["prod_mmboe"] else 0
        )
        rev_var = (
            ((actual_revenue - bench["revenue_mm"]) / bench["revenue_mm"]) * 100
            if bench["revenue_mm"]
            else 0
        )
        npv_var = (
            ((actual_npv - bench["npv_mm"]) / bench["npv_mm"]) * 100 if bench["npv_mm"] else 0
        )

        comparison_rows.extend(
            [
                {
                    "Field": field_name,
                    "Metric": "Production (MMBOE)",
                    "Paper": f"{bench['prod_mmboe']:.0f}",
                    "Actual": f"{actual_prod:.0f}",
                    "Variance": f"{prod_var:+.1f}%",
                },
                {
                    "Field": field_name,
                    "Metric": "Revenue ($MM)",
                    "Paper": f"{bench['revenue_mm']:,.0f}",
                    "Actual": f"{actual_revenue:,.0f}",
                    "Variance": f"{rev_var:+.1f}%",
                },
                {
                    "Field": field_name,
                    "Metric": "NPV10 ($MM)",
                    "Paper": f"{bench['npv_mm']:,.0f}",
                    "Actual": f"{actual_npv:,.0f}",
                    "Variance": f"{npv_var:+.1f}%",
                },
            ]
        )

    if comparison_rows:
        df_comparison = pd.DataFrame(comparison_rows)
        print("\n" + "=" * 80)
        print("COMPARISON WITH WORLD OIL REPORT BENCHMARKS")
        print("=" * 80)
        print("\n" + df_comparison.to_string(index=False))
    else:
        df_comparison = pd.DataFrame()

    output_dir = project_root / "results/lower_tertiary"
    output_dir.mkdir(parents=True, exist_ok=True)

    excel_path = output_dir / "npv_analysis_results.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_results.to_excel(writer, sheet_name="NPV Analysis", index=False)
        for field_id, frame in monthly_outputs.items():
            sheet_name = field_id[:31]
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
        if not df_comparison.empty:
            df_comparison.to_excel(writer, sheet_name="Paper Comparison", index=False)

    csv_path = output_dir / "npv_summary.csv"
    df_results.to_csv(csv_path, index=False)

    print(f"\n✓ Results saved to: {excel_path}")
    print(f"✓ CSV summary saved to: {csv_path}")
    print("\n" + "=" * 80)
    print("Analysis Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
