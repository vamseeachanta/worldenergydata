#!/usr/bin/env python3
"""Publish the WO April 2026 D&C QA/QC tables to the Explorer HF dataset.

Adds three configs to ``aceengineer/worldenergydata-explorer`` so the website
can render the D&C days QA/QC directly from the datasets-server API (the
report-hub design rule: data belongs on Hugging Face):

- ``dc_development_summary`` (11 rows) — per-development rollup with the
  article comparison columns (the reconciliation matrix, machine-readable).
- ``dc_bores`` (253 rows) — one row per wellbore: spud, TD, drilling /
  completion split, sidetrack + producer markers, #846 flags.
- ``dc_vintage_diff`` (253 rows) — frozen-V30 vs wed per-bore diff proving
  drilling-day stability (categories: unchanged / late_data /
  servicing_accrual / wed_only).

All rows come from the committed listing pipeline
(``scripts/lower_tertiary/build_wo_per_well_dc.py`` + its two committed CSV
inputs) — this script re-projects, it does not recompute.

Deps: pandas, pyarrow; publication additionally requires huggingface_hub.

    <python-with-deps> scripts/hf_export/publish_dc_days_to_hf.py [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lower_tertiary.dc_provenance import (
    add_days,
    aggregate_basis,
    sum_days,
    validate_day_schema,
    validate_vintage_row,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = "aceengineer/worldenergydata-explorer"
LISTING_SCRIPT = REPO_ROOT / "scripts" / "lower_tertiary" / "build_wo_per_well_dc.py"

NEW_CONFIGS = ["dc_development_summary", "dc_bores", "dc_vintage_diff"]

CARD_SECTION = """
## D&C days QA/QC tables

Bore-level drilling & completion days behind the World Oil April 2026
reconciliation (hub: https://vamseeachanta.github.io/worldenergydata/wo-april-2026-qaqc-hub.html).

| Config | Rows | What |
|---|---|---|
| `dc_development_summary` | 11 | Per-development rollup with explicit article provenance gap |
| `dc_bores` | 253 | Per-bore spud/TD, drill vs completion split, producer/sidetrack |
| `dc_vintage_diff` | 253 | Per-bore vintage values, separate bases and comparable deltas |

`basis` preserves the complete extractor rule; `pnd_days` (nullable integer,
units: days) counts the opaque PND activity code separately. `days_status`
(nullable string) preserves WAR coverage vocabulary: `war_covered`,
`war_covered_no_activity_code`, `no_war_activity`. These describe coded,
unattributed and absent coverage, respectively; activity day values may be
null even with coverage. Day columns use nullable integers. A null contributor
makes its field/block total null. Multiple full rules are labelled `mixed`.
Vintage tables carry `basis_v30` and `basis_wed`; deltas are null unless rules
are known and equal. Article counts carry `basis_article=unavailable`; no
article delta is asserted. Production refresh and publication remain pending.
"""


def _load_listing_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "build_wo_per_well_dc", LISTING_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _drilldown_extras() -> dict[str, dict]:
    """Well-geometry columns the listing does not carry, keyed by API12.

    The HF table is the data home for the drill-down surface, so it must hold
    every column that surface renders — water depth, MD, TVD, mud weight —
    plus the vintage category, rather than making consumers re-join CSVs.
    """
    import csv as _csv

    src = (
        REPO_ROOT
        / "docs/modules/bsee/analysis/production/FDAS_V30"
        / "drilling_and_completion_days_v21_kc.csv"
    )
    vin_path = REPO_ROOT / "reports/lower_tertiary/data/dc_vintage_diff.csv"
    vintage = {
        r["api12"]: r["category"]
        for r in _csv.DictReader(vin_path.open(encoding="utf-8"))
    }

    def _num(raw: str | None) -> float | None:
        raw = (raw or "").strip()
        return float(raw) if raw else None

    extras = {}
    for r in _csv.DictReader(src.open(encoding="utf-8")):
        api = r["API_WELL_NUMBER"].strip()
        extras[api] = {
            "water_depth_ft": _num(r["WATER_DEPTH"]),
            "max_md_ft": _num(r["MAX_BH_TOTAL_MD"]),
            "max_tvd_ft": _num(r["MAX_WELL_BORE_TVD"]),
            "max_mud_ppg": _num(r["MAX_DRILL_FLUID_WGT"]),
            "vintage_category": vintage.get(api),
        }
    return extras


def build_tables() -> dict[str, pd.DataFrame]:
    mod = _load_listing_module()
    devs = mod.load_bores()
    vintage = mod.load_vintage_diff()
    extras = _drilldown_extras()

    bore_rows = []
    summary_rows = []
    for dev in sorted(devs, key=lambda d: (d == "Big Foot", d)):
        bores = devs[dev]
        for b in bores:
            bore_rows.append(
                {
                    "development": dev,
                    "api12": b["api12"],
                    "bore": b["bore"],
                    "lease_name": b["lease_name"],
                    "lease_num": b["lease_num"],
                    "spud": None if b["spud"] == "—" else b["spud"],
                    "td_date": None if b["td"] == "—" else b["td"],
                    "drilling_days": b["drill"],
                    "completion_days": b["compl"],
                    "dc_days": add_days(b["drill"], b["compl"]),
                    "basis": b["basis"],
                    "pnd_days": b["pnd_days"],
                    "days_status": b["days_status"],
                    "sidetrack": b["sidetrack"],
                    "producer": b["producer"],
                    "note": b["note"] or None,
                    **extras.get(b["api12"], {}),
                }
            )
        wo = mod.WO_ARTICLE.get(dev)
        drill = sum_days(b["drill"] for b in bores)
        compl = sum_days(b["compl"] for b in bores)
        summary_rows.append(
            {
                "development": dev,
                "bores_wed": len(bores),
                "bores_article": wo[0] if wo else None,
                "producers_wed": sum(1 for b in bores if b["producer"]) or None,
                "producers_article": wo[1] if wo else None,
                "drilling_days": drill,
                "completion_days": compl,
                "dc_days_wed": add_days(drill, compl),
                "basis": aggregate_basis(bores),
                "basis_article": "unavailable",
                "pnd_days": sum_days(b["pnd_days"] for b in bores),
                "days_status": aggregate_basis(
                    {"basis": b["days_status"]} for b in bores
                ),
                "dc_days_article": wo[2] if wo else None,
                "delta_days": None,  # Article basis is unavailable.
                "status": "historical: " + mod.STATUS[dev],
            }
        )

    diff_rows = [row for rows in vintage.values() for row in rows]
    for row in diff_rows:
        validate_vintage_row(row)
    diff = pd.DataFrame(diff_rows)
    for col in (
        "drill_v30",
        "compl_v30",
        "drill_wed",
        "compl_wed",
        "d_drill",
        "d_compl",
    ):
        diff[col] = pd.to_numeric(diff[col].replace("", pd.NA), errors="raise").astype(
            "Int64"
        )
    diff["spud_wed"] = diff["spud_wed"].replace("", None)
    diff = diff.sort_values(["dev", "api12"]).reset_index(drop=True)

    summary = pd.DataFrame(summary_rows)
    for col in (
        "bores_article",
        "producers_wed",
        "producers_article",
        "dc_days_article",
        "delta_days",
    ):
        summary[col] = summary[col].astype("Int64")

    tables = {
        "dc_development_summary": summary,
        "dc_bores": pd.DataFrame(bore_rows),
        "dc_vintage_diff": diff,
    }
    for table in tables.values():
        validate_day_schema(table.columns)
        for column in table.columns:
            if column in {
                "pnd_days",
                "drilling_days",
                "completion_days",
                "dc_days",
                "dc_days_wed",
                "dc_days_article",
                "delta_days",
            }:
                table[column] = pd.to_numeric(
                    table[column].replace("", pd.NA), errors="raise"
                ).astype("Int64")
            if column.startswith("basis") or column == "days_status":
                table[column] = table[column].astype("string")
    return tables


def patch_readme(readme: str) -> str:
    if "config_name: dc_bores" in readme:
        heading = "\n## D&C days QA/QC tables"
        if heading in readme:
            start = readme.index(heading)
            end = readme.find("\n## ", start + len(heading))
            tail = readme[end:] if end != -1 else ""
            return readme[:start].rstrip() + CARD_SECTION + tail
        return readme.rstrip() + CARD_SECTION
    anchor = "- config_name: parametric_economics\n  data_files: parametric_economics.parquet\n"
    addition = (
        anchor
        + "- config_name: dc_development_summary\n  data_files: dc_development_summary.parquet\n"
        + "- config_name: dc_bores\n  data_files: dc_bores.parquet\n"
        + "- config_name: dc_vintage_diff\n  data_files: dc_vintage_diff.parquet\n"
    )
    if anchor not in readme:
        raise SystemExit(
            "README anchor not found — dataset card layout changed; patch manually"
        )
    return readme.replace(anchor, addition).rstrip() + CARD_SECTION


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tables = build_tables()
    assert len(tables["dc_bores"]) == 253
    assert len(tables["dc_vintage_diff"]) == 253

    out = Path(tempfile.mkdtemp(prefix="dc-days-hf-"))
    for name, df in tables.items():
        df.to_parquet(out / f"{name}.parquet", index=False)
        print(f"{name}: {len(df)} rows -> {out / (name + '.parquet')}")

    if args.dry_run:
        print("dry-run: nothing uploaded")
        return

    from huggingface_hub import HfApi, hf_hub_download

    api = HfApi()
    readme_path = hf_hub_download(DATASET, "README.md", repo_type="dataset")
    patched = patch_readme(Path(readme_path).read_text(encoding="utf-8"))
    (out / "README.md").write_text(patched, encoding="utf-8")

    src_sha = hashlib.sha256(
        (
            REPO_ROOT
            / "docs/modules/bsee/analysis/production/FDAS_V30"
            / "drilling_and_completion_days_v21_kc.csv"
        ).read_bytes()
    ).hexdigest()
    api.upload_folder(
        repo_id=DATASET,
        repo_type="dataset",
        folder_path=str(out),
        commit_message=(
            "Add D&C QA/QC configs (dc_development_summary/dc_bores/dc_vintage_diff); "
            f"source v21_kc sha256={src_sha[:12]}"
        ),
    )
    print(f"uploaded 3 configs + README to {DATASET}")


if __name__ == "__main__":
    main()
