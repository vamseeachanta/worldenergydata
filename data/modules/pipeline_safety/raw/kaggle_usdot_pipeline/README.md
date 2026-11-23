# USDOT Oil Pipeline Accidents, 2010-Present (Kaggle curated)

**Downloaded:** 2026-05-05
**Source:** https://www.kaggle.com/datasets/usdot/pipeline-accidents
**License:** CC0-1.0 (public domain)
**Upstream:** US DOT / PHMSA, redistributed under Kaggle's `usdot` collaborator account
**Last upstream update:** 2019-09-20
**Physical location:** repo (committed) — `data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/`

## Contents

| File | Size | Records | SHA256 |
|------|------|---------|--------|
| `database.csv` | 908,056 B (~887 KB) | 2,795 | `1d4abf457565e2661b70f735c590a793204d59b3537c1995725d376dafc52c76` |

## Schema (2,795 rows × 47 cols)

Curated/renamed version of the PHMSA Form 7000-1 hazardous-liquid export with human-friendly column names:

- **Identity:** `Report Number`, `Supplemental Number`, `Accident Year`, `Operator ID`, `Operator Name`, `Pipeline/Facility Name`
- **Location:** `Pipeline Location` (onshore/offshore), `Accident State`, `Accident Latitude/Longitude`
- **Pipe asset:** `Pipeline Type`, `Liquid Type`, `Liquid Subtype`, `Liquid Name`
- **Release:** `Unintentional Release (Barrels)`, `Intentional Release (Barrels)`, `Liquid Recovery (Barrels)`, `Net Loss (Barrels)`
- **Cause:** `Cause Category`, `Cause Subcategory`
- **Consequence:** `Liquid Ignition`, `Liquid Explosion`, `Pipeline Shutdown`, `Public Evacuations`, `All Injuries`, `All Fatalities`
- **Cost:** `Property Damage Costs`, `Lost Commodity Costs`, `Public/Private Property Damage Costs`, `Emergency Response Costs`, `Environmental Remediation Costs`, `Other Costs`, `All Costs`

## Why this is in-repo (committed)

- 887 KB single CSV is well under the 100 MB threshold from `docs/data/LOCAL_DATA_PATTERN.md`
- `data/modules/pipeline_safety/raw/` is not symlinked or gitignored at the directory level
- CC0-1.0 license imposes no redistribution constraint
- Including in git gives test/CI deterministic access without a refresh step

## Relationship to other PHMSA data in the repo

| Path | Format | Coverage | Granularity |
|---|---|---|---|
| `data/modules/pipeline_safety/raw/phmsa/extracted/hl*.xlsx` | XLSX | 1986–present (3 files) | 100+ cols, manual download |
| `data/modules/pipeline_safety/raw/phmsa/extracted/gd*.xlsx` | XLSX | 1986–present (gas distribution) | 100+ cols |
| `data/modules/hse/raw/kaggle_oil_facility_accidents/...csv` | CSV | 2010–2023 (hazardous liquid only) | 81 cols (raw upstream) |
| **`data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/database.csv`** (this) | CSV | 2010–2019 (hazardous liquid only) | 47 cols (curated) |

Use this dataset when:
- You want a small, self-contained, in-repo CSV for examples / unit tests / docs
- Curated column names ("All Costs") are more ergonomic than raw PHMSA codes (`EST_COST_OTHER`)

For analysis covering 2019–present, prefer `kaggle_oil_facility_accidents` (more recent) or the in-repo PHMSA XLSX (currently maintained).

## Re-acquisition

```bash
export PATH="$HOME/.local/bin:$PATH"
kaggle datasets download -d usdot/pipeline-accidents \
  --unzip -p data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/
```

## Caveats

- **2019 snapshot** — does not include 2020+ incidents. For continuing coverage use one of the alternatives listed above.
- "Oil Pipeline" is the dataset's marketing name; upstream coverage is all hazardous liquid (oil, refined products, CO2, etc.).
