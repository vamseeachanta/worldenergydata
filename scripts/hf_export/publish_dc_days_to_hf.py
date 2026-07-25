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

Deps: pandas, pyarrow, huggingface_hub (token from ~/.cache/huggingface/token).

    <python-with-deps> scripts/hf_export/publish_dc_days_to_hf.py [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import tempfile
from pathlib import Path

import pandas as pd

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
| `dc_development_summary` | 11 | Per-development rollup vs the article (7 exact, 3 explained) |
| `dc_bores` | 253 | Per-bore spud/TD, drill vs completion split, producer/sidetrack |
| `dc_vintage_diff` | 253 | Frozen-V30 vs wed — drilling changed on 0 of 253 bores |

Basis: canonical extractor output, BSEE WAR vintage 2026-02-19. Drilling days =
spud to TD; completion days = all post-TD rig time including later servicing
(the open #846 boundary question). Known caveat: DRILLING_DAYS mixes calendar
days (spans <=250 d) with WAR-union rig-days (longer spans), so batch-drilled
wells undercount — tracked in the QA/QC hub.
"""


def _load_listing_module():
    spec = importlib.util.spec_from_file_location(
        "build_wo_per_well_dc", LISTING_SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_tables() -> dict[str, pd.DataFrame]:
    mod = _load_listing_module()
    devs = mod.load_bores()
    vintage = mod.load_vintage_diff()

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
                    "dc_days": b["drill"] + b["compl"],
                    "sidetrack": b["sidetrack"],
                    "producer": b["producer"],
                    "note": b["note"] or None,
                }
            )
        wo = mod.WO_ARTICLE.get(dev)
        drill = sum(b["drill"] for b in bores)
        compl = sum(b["compl"] for b in bores)
        summary_rows.append(
            {
                "development": dev,
                "bores_wed": len(bores),
                "bores_article": wo[0] if wo else None,
                "producers_wed": sum(1 for b in bores if b["producer"]) or None,
                "producers_article": wo[1] if wo else None,
                "drilling_days": drill,
                "completion_days": compl,
                "dc_days_wed": drill + compl,
                "dc_days_article": wo[2] if wo else None,
                "delta_days": (drill + compl - wo[2]) if wo else None,
                "status": mod.STATUS[dev],
            }
        )

    diff_rows = [row for rows in vintage.values() for row in rows]
    diff = pd.DataFrame(diff_rows)
    for col in (
        "drill_v30",
        "compl_v30",
        "drill_wed",
        "compl_wed",
        "d_drill",
        "d_compl",
    ):
        diff[col] = diff[col].astype("int64")
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

    return {
        "dc_development_summary": summary,
        "dc_bores": pd.DataFrame(bore_rows),
        "dc_vintage_diff": diff,
    }


def patch_readme(readme: str) -> str:
    if "config_name: dc_bores" in readme:
        return readme
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
    return readme.replace(anchor, addition) + CARD_SECTION


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tables = build_tables()
    assert len(tables["dc_bores"]) == 253
    assert len(tables["dc_vintage_diff"]) == 253
    assert int(tables["dc_development_summary"]["dc_days_wed"].sum()) == 25404
    assert int(tables["dc_development_summary"]["delta_days"].sum()) == 195  # 119+52+24

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
