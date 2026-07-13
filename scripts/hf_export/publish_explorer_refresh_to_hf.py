#!/usr/bin/env python3
"""ABOUTME: Refresh the aceengineer/worldenergydata-explorer HF dataset from the
ABOUTME: committed Explorer bundle: corrected curated EUR (#979), surfaced
ABOUTME: life-to-date economics (#976/#981), and the parametric economics grid.

What it does
------------
1. Downloads the live ``fields.parquet`` from the HF dataset.
2. Patches ``eur_mmbbl`` from the committed bundle's curated reserves (#979 —
   the live values are the retired ~2-6.6x-inflated decline-fit numbers) and
   appends the economics columns (``npv_mm``, ``breakeven_wti``,
   ``sens_mm_per_dollar``, ``economics_status``, ``economics_basis``,
   ``eur_confidence``, ``eur_source``). All other columns are left untouched.
3. Publishes the parametric economics grid
   (``reports/lower_tertiary/parametric/lt_economics_parametric.csv``) as a new
   ``parametric_economics`` config — SURFACED fields only, per #971/#976.
4. Rewrites the dataset card (README) with the new configs, provenance shas,
   and a revision note.

Deps: pandas, pyarrow, huggingface_hub (token from ~/.cache/huggingface/token).

    <python-with-deps> scripts/hf_export/publish_explorer_refresh_to_hf.py [--dry-run]
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd
from huggingface_hub import HfApi, hf_hub_download

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = "aceengineer/worldenergydata-explorer"
BUNDLE = REPO_ROOT / "reports" / "field-atlas" / "results" / "explorer_results_bundle.json"
PERFORMANCE = REPO_ROOT / "reports" / "lower_tertiary" / "lifecycle" / "_performance.json"
PARAMETRIC_JSON = (
    REPO_ROOT / "reports" / "lower_tertiary" / "parametric" / "lt_economics_parametric.json"
)

ECON_COLS = [
    "npv_mm",
    "breakeven_wti",
    "sens_mm_per_dollar",
    "economics_status",
    "economics_basis",
    "eur_confidence",
    "eur_source",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_fields(live_parquet: Path) -> pd.DataFrame:
    fields = pd.read_parquet(live_parquet)
    perf_by_slug = json.loads(PERFORMANCE.read_text())["fields"]

    def col(slug: str, key: str):
        return perf_by_slug.get(slug, {}).get(key)

    fields["eur_mmbbl"] = fields["id"].map(lambda s: col(s, "eur_mmbbl")).astype("Float64")
    for c in ECON_COLS:
        if c == "economics_basis":
            fields[c] = fields["id"].map(
                lambda s: col(s, "economics_basis")
                if perf_by_slug.get(s)
                else None
            )
        else:
            fields[c] = fields["id"].map(lambda s, k=c: col(s, k))
    for c in ("npv_mm", "breakeven_wti", "sens_mm_per_dollar"):
        fields[c] = fields[c].astype("Float64")
    return fields


def build_parametric() -> pd.DataFrame:
    grid = json.loads(PARAMETRIC_JSON.read_text())
    rows = []
    for slug, f in grid["fields"].items():
        if f["economics_status"] != "surfaced":
            continue  # withheld per #971/#976 life-to-date gating
        for g in f["grid"]:
            rows.append(
                {
                    "field": slug,
                    "wti_price_multiplier": g["wti_price_multiplier"],
                    "discount_rate": g["discount_rate"],
                    "npv_musd": g["npv_musd"],
                    "breakeven_multiplier": f["breakeven_multiplier_by_rate"][
                        f"{g['discount_rate']:g}"
                    ],
                    "economics_basis": "life_to_date_pretax_npv",
                }
            )
    return pd.DataFrame(rows)


def build_readme(n_param_rows: int, param_fields: list[str]) -> str:
    grid = json.loads(PARAMETRIC_JSON.read_text())
    prov = grid["provenance"]
    return f"""---
license: cc-by-4.0
pretty_name: World Energy Field Explorer — analysis projection
tags:
- energy
- oil-and-gas
- offshore
- bsee
- gulf-of-mexico
configs:
- config_name: fields
  data_files: fields.parquet
- config_name: wells
  data_files: wells.parquet
- config_name: countries
  data_files: countries.parquet
- config_name: parametric_economics
  data_files: parametric_economics.parquet
---

# World Energy Field Explorer — analysis projection

Tabular projection of the **World Energy Field Explorer** analysis results, published so the
Hugging Face dataset viewer and the **datasets-server API** can render visualizations directly.

Live Explorer: https://vamseeachanta.github.io/worldenergydata/field-atlas/

## Tables (viewer configs)

| Config | Rows | What |
|---|---|---|
| `fields` | 10 | Lower-Tertiary fields — economics, reservoir, HPHT/decommission risk, concept, landman |
| `wells` | 56 | Producing wells — spud/TD/first-oil, rig-days, cumulative oil, uptime |
| `countries` | 84 | Global offshore funnel — per-country field counts + data-density badge |
| `parametric_economics` | {n_param_rows} | WTI price-multiplier x discount-rate NPV grid ({", ".join(param_fields)}) |

## Economics basis

- `npv_mm` / `breakeven_wti` are **life-to-date**, pre-tax, 10%-discounted: full sunk capex
  charged against oil produced to date, not full-cycle EUR. Fields early in life are withheld
  (`economics_status = early_life`, values null) rather than surfaced as absurd numbers.
- `eur_mmbbl` is **curated published/booked recoverable reserves** with `eur_source` +
  `eur_confidence` — NOT a decline-fit extrapolation. Null where no credible public figure
  exists.
- `parametric_economics` sweeps a uniform multiplier on the historical monthly WTI deck and
  the annual discount rate over the same sanctioned cashflow model. NPV is exact (affine) in
  the price multiplier. Fields with withheld economics are excluded from the grid.

## Provenance

Schema version `1.0.0`. Derived from the committed Explorer results bundle
(`reports/field-atlas/results/explorer_results_bundle.json`), itself a projection of
`_explorer.json` + `_atlas_feed.json`. Source snapshots (sha256):

- `reports/field-atlas/results/explorer_results_bundle.json` — sha256 `{_sha(BUNDLE)[:16]}…`
- `reports/lower_tertiary/lifecycle/_performance.json` — sha256 `{_sha(PERFORMANCE)[:16]}…`
- parametric grid: code revision `{prov["code_revision"][:12]}`, config
  `{prov["config_path"]}` (sha256 `{prov["config_sha256"][:16]}…`), data window through
  `{prov["end_date"]}`, model `{prov["model"]}`

## Revision notes

- **Economics refresh**: `eur_mmbbl` corrected to curated published reserves (the previous
  revision carried inflated decline-fit values, since retired); life-to-date NPV / break-even
  columns added for fields whose economics are surfaced; `parametric_economics` grid added.
"""


def main() -> int:
    dry = "--dry-run" in sys.argv
    api = HfApi()

    with tempfile.TemporaryDirectory() as td:
        live = hf_hub_download(
            DATASET, "fields.parquet", repo_type="dataset", local_dir=td
        )
        fields = build_fields(Path(live))
        param = build_parametric()
        readme = build_readme(len(param), sorted(param["field"].unique()))

        out = Path(td) / "upload"
        out.mkdir()
        fields.to_parquet(out / "fields.parquet", index=False)
        param.to_parquet(out / "parametric_economics.parquet", index=False)
        (out / "README.md").write_text(readme)

        print(f"fields: {fields.shape}, parametric: {param.shape}")
        print(fields[["id", "eur_mmbbl", "npv_mm", "breakeven_wti", "economics_status"]])
        if dry:
            print("DRY RUN — nothing uploaded")
            return 0

        api.upload_folder(
            repo_id=DATASET,
            repo_type="dataset",
            folder_path=str(out),
            commit_message=(
                "economics refresh: curated EUR (#979), life-to-date NPV/breakeven "
                "(#976/#981), parametric_economics grid"
            ),
        )
        print(f"uploaded -> https://huggingface.co/datasets/{DATASET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
