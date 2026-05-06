# Kaggle Dataset Acquisition Log

> Single index of Kaggle-sourced datasets ingested into worldenergydata. Each row links to a per-dataset README with full schema, fields, and re-acquisition commands.

## 2026-05-05 — Initial five-dataset ingest

| # | Kaggle slug | Module | Files | Total size | License | Stored in git? |
|---|---|---|---|---|---|---|
| 1 | [ihmstefanini/industrial-safety-and-health-analytics-database](https://www.kaggle.com/datasets/ihmstefanini/industrial-safety-and-health-analytics-database) | hse | 3 (1 PNG + 2 CSV) | ~338 KB | CC0-1.0 | No (`/mnt/ace` via symlink) |
| 2 | [jaimeshaker/osha-work-related-fatalities](https://www.kaggle.com/datasets/jaimeshaker/osha-work-related-fatalities) | hse | 1 CSV | ~1.7 MB | CC0-1.0 | No (`/mnt/ace` via symlink) |
| 3 | [energysafetystat/oil-facility-accidents-2010-present](https://www.kaggle.com/datasets/energysafetystat/oil-facility-accidents-2010-present) | hse | 1 CSV | ~3.2 MB | CC0-1.0 | No (`/mnt/ace` via symlink) |
| 4 | [usdot/pipeline-accidents](https://www.kaggle.com/datasets/usdot/pipeline-accidents) | pipeline_safety | 1 CSV | ~887 KB | CC0-1.0 | **Yes** (committed) |
| 5 | [muhammadwaqas023/predictive-maintenance-oil-and-gas-pipeline-data](https://www.kaggle.com/datasets/muhammadwaqas023/predictive-maintenance-oil-and-gas-pipeline-data) | pipeline | 1 CSV | ~70 KB | **MIT** (attribution) | **Yes** (committed) |

Per-dataset details:
- [`data/modules/hse/raw/kaggle_ihm_stefanini/README.md`](modules/hse/raw/kaggle_ihm_stefanini/README.md)
- [`data/modules/hse/raw/kaggle_osha_fatalities/README.md`](modules/hse/raw/kaggle_osha_fatalities/README.md)
- [`data/modules/hse/raw/kaggle_oil_facility_accidents/README.md`](modules/hse/raw/kaggle_oil_facility_accidents/README.md)
- [`data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/README.md`](modules/pipeline_safety/raw/kaggle_usdot_pipeline/README.md)
- [`data/modules/pipeline/raw/kaggle_pipe_thickness_loss/README.md`](modules/pipeline/raw/kaggle_pipe_thickness_loss/README.md) — **API 579 toy corpus, synthetic data; see README caveats**

## Placement rule

Driven by repo plumbing, not raw size:
- `data/modules/hse/raw/` is a **symlink to `/mnt/ace/...`** and gitignored — anything written under it auto-routes to `/mnt/ace` and stays out of git
- `data/modules/pipeline_safety/raw/` is a real directory, only `phmsa/extracted/*.{xlsx,pdf}` are gitignored — small CSVs land in-repo and are committed

For datasets >100 MB the `LOCAL_DATA_PATTERN.md` deterministic-refresh-script pattern applies; none of the 2026-05-05 batch hit that threshold.

## Auth setup (one-time per machine)

```bash
# 1. Install Kaggle CLI (uv-managed tool)
uv tool install kaggle

# 2. Drop your Kaggle Access Token (KGAT...) at:
#    ~/.kaggle/access_token   (chmod 600)
# Generate at: https://www.kaggle.com/settings → API → "Create New Token"

# 3. Verify
export PATH="$HOME/.local/bin:$PATH"
kaggle datasets list -s "industrial safety" --max-size 1
```

The Kaggle CLI 2.x natively reads `~/.kaggle/access_token` (KGAT format) — no `kaggle.json` wrapper needed.

## Discovery surface — Kaggle "oil and gas" search backlog

The Kaggle search [`?search=oil+and+gas`](https://www.kaggle.com/datasets?search=oil+and+gas) returns roughly **250+ datasets across ~12+ pages** (verified 2026-05-05). Relevance density is highest on pages 1–3 (engineering / operational corpora) and falls off toward pages 5–12 (stock prices, trade macro, country-level reports).

**To re-survey from CLI:**
```bash
export PATH="$HOME/.local/bin:$PATH"
kaggle datasets list -s "oil and gas" --sort-by votes -p 1 --csv | head -40
# pages 2-12 with -p 2 ... -p 12
```

**Top backlog candidates** worth evaluating before next ingest pass (slug, size, why):

| Slug | Size | Module fit | Why it's interesting |
|---|---|---|---|
| `afrniomelo/3w-dataset` | **1.8 GB** | new (drilling/operational) | Petrobras-released *3W* — real-world undesirable events in oil wells; ML/anomaly-detection corpus. Needs `/mnt/ace` per `LOCAL_DATA_PATTERN.md`. |
| `garystafford/environmental-sensor-data-132k` | 7 MB | hse / iot | IoT sensor telemetry, 132k rows; predictive-maintenance training. |
| `mabusalah/brent-oil-prices` | 40 KB | oil_price | Brent crude historical price series. |
| `mruanova/us-gasoline-and-diesel-retail-prices-19952021` | 39 KB | oil_price | US retail gasoline/diesel prices 1995–2021. |
| `caesarmario/oecd-data-crude-oil-production` | 44 KB | eia_us / world energy | OECD crude production; updated 2026-01. |
| `toriqulstu/global-crude-petroleum-trade-1995-2021` | 72 KB | trade / world energy | Worldwide crude import/export volumes. |
| `jordancarlen/100-years-oil-production` | 5 KB | eia_us | Historical US oil production, 100+ years. |
| `ahmedelbashir99/drilling-log-dataset` | 6 KB | drilling | Drilling logs (small, demo-scale). |
| `sobhanmohammadids/drilling-well-production-data` | 328 KB | drilling | Well production data, useful for type-curve work. |
| `cathetorres/geospatial-environmental-and-socioeconomic-data` | **2.4 GB** | new (geospatial) | Cross-domain environmental/socioeconomic geospatial layer. Needs `/mnt/ace`. |
| `mauriciy/daily-spanish-gas-prices` | **1.7 GB** | oil_price | Daily prices across Spanish gas stations 2007–2023. Needs `/mnt/ace`. |
| `umerhaddii/exxon-mobil-stock-price-data` | 421 KB | financial / cost | Exxon stock 2025; useful for E&P-cost benchmarking. |

**Triage rule** before ingesting any of the above:
1. Confirm a downstream consumer exists (a module, a notebook, a planned analysis). Don't ingest "because it's there".
2. Check license — CC0/MIT/Apache → fine; CC-BY → preserves attribution; CC-BY-NC / "Other" / unspecified → review per `.claude/rules/calc-citation-contract.md` deny-list.
3. Apply the size routing rule: `<100 MB` + non-symlinked module dir → repo; `>100 MB` or symlinked module → `/mnt/ace` with refresh-script + `.gitkeep`.

## License notes

Datasets 1–4 are CC0-1.0 (public domain) — no attribution constraint, freely redistributable.

Dataset 5 (predictive-maintenance pipe thickness loss) is **MIT** — requires attribution to the upstream author (Muhammad Waqas). The `LICENSE` file in `data/modules/pipeline/raw/kaggle_pipe_thickness_loss/` carries the copyright line; downstream tooling that includes this dataset in derivative outputs should preserve the attribution.

Future Kaggle ingests with restrictive licenses (CC-BY-NC, CC-BY-SA, "Other", or unspecified) must be reviewed against the workspace-hub vendor-derivative deny-list (`.claude/rules/calc-citation-contract.md`) before any in-repo placement.
