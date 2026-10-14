#!/usr/bin/env python3
"""Retain verbatim Julia lease rows and publisher archive provenance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path

import yaml


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def select_member(archive, member, lease_columns, header, output):
    blob = archive.read(member)
    lines = blob.splitlines(keepends=True)
    selected, row_numbers = [], []
    if header:
        selected.append(lines[0].rstrip(b"\r\n") + b"\n")
    for number, line in enumerate(lines, 1):
        if header and number == 1:
            continue
        row = next(csv.reader([line.decode("latin-1")]))
        if any(row[column].strip() == "G20351" for column in lease_columns):
            selected.append(line.rstrip(b"\r\n") + b"\n")
            row_numbers.append(number)
    raw = b"".join(selected)
    output.write_bytes(raw)
    return {
        "path": "raw/" + output.name,
        "sha256": digest(raw),
        "bytes": len(raw),
        "record_count": len(row_numbers),
        "header_lines": int(header),
        "source_member": member,
        "source_member_sha256": digest(blob),
        "source_member_bytes": len(blob),
        "source_record_count": len(lines) - int(header),
        "source_row_numbers": row_numbers,
        "transformation": "Lease selection only; line endings normalized to LF; all columns retained.",
    }


def collect_one(source_dir, output_dir, name, request, selections):
    path = source_dir / name
    if not zipfile.is_zipfile(path):
        raise ValueError(f"Publisher response is not a ZIP: {name}")
    receipt = (source_dir / request).read_text().splitlines()
    if receipt[2] != "HTTP_STATUS: 200":
        raise ValueError(f"Publisher retrieval failed: {name}")
    files = []
    with zipfile.ZipFile(path) as archive:
        for member, columns, header, destination in selections:
            item = select_member(archive, member, columns, header, output_dir / destination)
            item.update({
                "source_url": receipt[0],
                "retrieved_at": receipt[1],
                "http_status": 200,
                "archive_sha256": digest(path.read_bytes()),
                "archive_bytes": path.stat().st_size,
                "archive_reproduce_command": f"curl --location --output {name} {receipt[0]}",
                "receipt_name": request,
                "source_id": "bsee-data-center",
            })
            files.append(item)
    return files


def assumptions(root):
    econ_path = "config/analysis/lower_tertiary/economic_assumptions.yml"
    field_path = "config/analysis/lower_tertiary/fields/julia.yml"
    econ = yaml.safe_load((root / econ_path).read_text())
    field = yaml.safe_load((root / field_path).read_text())["field"]
    selections = {
        "oil_price": (econ["commodity_prices"]["oil"]["base_case"]["wti_usd_per_bbl"], "USD/bbl", econ_path, "Constant scenario price; realized sales prices are not established."),
        "gas_price": (econ["commodity_prices"]["gas"]["base_case"]["henry_hub_usd_per_mcf"], "USD/Mcf", econ_path, "Constant scenario price; realized sales prices are not established."),
        "royalty_rate": (econ["fiscal_terms"]["royalty"]["rate"], "1", econ_path, "Lease-specific royalty payments and relief are not established; the recorded publisher reference returned HTTP 404."),
        "income_tax_rate": (0, "1", "Pre-tax analysis scope", "Tax is excluded; zero is a model exclusion, not an actual tax rate."),
        "opex_per_boe": (field["opex_per_boe"], "USD/boe", field_path, "Observed field operating expenditure is unavailable."),
        "capex_usd_mm": (field["capex"]["total_mm_usd"], "USD million", field_path, "Recorded capital assumption is charged at first observed production; actual expenditure and timing are unavailable."),
        "discount_rate": (econ["financial_metrics"]["discount_rates"]["primary_discount_rate"], "1", econ_path, "Scenario discount rate; financing terms are unavailable."),
        "gas_boe_conversion": (6, "Mcf/boe", "packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py", "The existing module's energy-equivalence convention is retained; sales energy content is unavailable."),
    }
    return {key: {"value": value, "unit": unit, "basis": basis, "reason": ("assumed, based on previous experience; " + reason) if key not in {"income_tax_rate", "gas_boe_conversion"} else reason, "status": "ASSUMED"}
            for key, (value, unit, basis, reason) in selections.items()}


def collect(source_dir, output_dir, source_revision):
    raw = output_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    files = []
    for year in range(2015, 2026):
        files += collect_one(source_dir, raw, f"ogora{year}delimit.zip", f"ogora{year}.request.txt",
                             [(f"ogora{year}delimit.txt", [0], False, f"ogora{year}.csv")])
    files += collect_one(source_dir, raw, "ogoradelimit.zip", "ogora-current.request.txt",
                         [("ogoradelimit.txt", [0], False, "ogora2026.csv")])
    files += collect_one(source_dir, raw, "APIRawData.zip", "api.request.txt", [
        ("APIRawData/mv_api_list_all.txt", [10, 13], True, "wells.csv"),
        ("APIRawData/mv_api_wellcomps_all.txt", [5], True, "completions.csv"),
    ])
    files += collect_one(source_dir, raw, "DeepQualRawData.zip", "deepqual.request.txt",
                         [("DeepQualRawData/mv_deep_water_field_leases.txt", [1], True, "field.csv")])
    root = Path(__file__).resolve().parents[2]
    save_json(output_dir / "basis.json", {
        "field": "Julia", "lease": "G20351", "field_code": "WR627", "block": "WR 584",
        "source_revision": source_revision, "production_years": list(range(2015, 2027)),
        "selection_basis": "reports/lower_tertiary/2026-06-17-julia-granular-economics-summary.md",
        "assumptions": assumptions(root),
    })
    save_json(output_dir / "sources.json", {
        "owner_repo": "worldenergydata", "dataset_id": "julia_life_to_date",
        "files": files, "units": {"oil": "bbl", "gas": "Mcf", "water": "bbl"},
        "retention": "Raw lease rows are retained. Bulk publisher archives are identified by address and digest and reproduced by curl followed by this collector.",
        "reproduce": "python scripts/lower_tertiary/collect_life_to_date.py --archives-dir ARCHIVES --output-dir DATA --source-revision REVISION",
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    collect(args.archives_dir, args.output_dir, args.source_revision)


if __name__ == "__main__":
    main()
