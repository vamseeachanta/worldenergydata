# Predictive Maintenance — Pipe Thickness Loss Dataset (API 579 toy corpus)

**Downloaded:** 2026-05-05
**Source:** https://www.kaggle.com/datasets/muhammadwaqas023/predictive-maintenance-oil-and-gas-pipeline-data
**License:** MIT — see `LICENSE` in this directory
**Author / attribution:** Muhammad Waqas (Kaggle: `muhammadwaqas023`)
**Last upstream update:** 2025-06-04
**Physical location:** repo (committed) — `data/modules/pipeline/raw/kaggle_pipe_thickness_loss/`

## Contents

| File | Size | Records | SHA256 |
|------|------|---------|--------|
| `market_pipe_thickness_loss_dataset.csv` | 70,728 B (~70 KB) | 1,000 | `28711e39dcef463db8cb6ff967356dc17cb67e2a289e431af8d4ccaee6a44938` |

## Schema (1,000 rows × 11 cols)

| Column | Units | Description |
|---|---|---|
| `Pipe_Size_mm` | mm | Outside diameter |
| `Thickness_mm` | mm | Original wall thickness |
| `Material` | — | Material category (e.g. "Carbon Steel", "PVC") |
| `Grade` | — | Material grade (e.g. "API 5L X52", "ASTM A333 Grade 6") |
| `Max_Pressure_psi` | psi | Maximum operating pressure |
| `Temperature_C` | °C | Operating temperature |
| `Corrosion_Impact_Percent` | % | Corrosion severity proxy |
| `Thickness_Loss_mm` | mm | Wall loss |
| `Material_Loss_Percent` | % | Fraction of original material lost |
| `Time_Years` | years | Time in service |
| `Condition` | label | Categorical target — `Moderate`, `Critical`, etc. |

## Use cases — and the boundary of usefulness

### ✅ Appropriate

- **API 579 / ASME FFS-1 workflow demonstration** — schema maps directly to Part 4 (general metal loss) and Part 5 (local metal loss) inputs: `Pipe_Size_mm` + `Thickness_mm` for `t_min`/`MAWP` calcs, `Thickness_Loss_mm` + `Time_Years` for corrosion-rate (CR) and remaining-life (RL) computation.
- **ML / classifier teaching corpus** — predicting `Condition` from sensor + asset features.
- **Pipeline plumbing tests** for FFS code paths (1000 rows is enough to exercise edge cases without slowness).

### ⚠️ NOT appropriate

This dataset is **synthetic / educational, not real field data**. Quality red flags:

- **Nonsensical material/grade pairings**: row 2 of the CSV has `Material=PVC` paired with `Grade=ASTM A106 Grade B`. A106 Grade B is a **carbon steel seamless-pipe spec** — PVC cannot be A106 Grade B. The dataset's material × grade matrix is not physically valid.
- **Suspect corrosion rates**: a record with `Time_Years=2` and `Material_Loss_Percent=31.72` would imply ~5 mm/year wall loss, which is uncharacteristically severe for almost any real service environment.

→ **Do not** train production-grade predictive-maintenance models on this corpus. **Do** use it for code-correctness validation of FFS workflows that will later run on real plant inspection data (UT thickness surveys, MFL pig data, etc.).

## Relationship to other repo data

- **Sibling**: `data/modules/pipeline/api_5l_pipe_schedule.csv` — API 5L pipe schedule lookup. Useful for joining standard `Pipe_Size_mm` against expected wall thicknesses.
- **No overlap** with `pipeline_safety` (incident records) or `kaggle_oil_facility_accidents` (PHMSA Form 7000-1 incident data) — those are post-failure forensic data; this is pre-failure integrity data.

## Re-acquisition

```bash
export PATH="$HOME/.local/bin:$PATH"
kaggle datasets download -d muhammadwaqas023/predictive-maintenance-oil-and-gas-pipeline-data \
  --unzip -p data/modules/pipeline/raw/kaggle_pipe_thickness_loss/
```
