# Texas RRC Field Architecture Dossiers

Field architecture dossiers are a screening packet built from direct Texas RRC
curated artifacts already stored under `/mnt/ace/worldenergydata/data/modules/texas_rrc`.
They extend the onshore field-development workflow from source inventory,
lifecycle, production, infrastructure access, field-atlas reporting, and
opportunity ranking into a bounded per-field dossier set.

## Lifecycle

The dossier builder does not scrape LinkedIn, PatchOps, or third-party scraper
output. It consumes three row-level curated inputs:

- `curated/analysis/field_opportunities/field_opportunity_rankings.csv`
- `curated/reports/field_atlas/field_atlas_summary.parquet` or `.csv`
- `curated/field_development/metrics/field_development_metrics.parquet` or `.csv`

The opportunity manifest is mandatory. Its upstream manifest list, source gaps,
and metric gaps are preserved in the dossier manifest and quality JSON.

## Refresh Cadence

Refresh upstream artifacts first, then rebuild dossiers:

```bash
worldenergydata texas-rrc build-field-architecture-dossiers --require-sources
```

Use dry-run mode to inspect source health without writing:

```bash
worldenergydata texas-rrc build-field-architecture-dossiers --dry-run
```

## Outputs

The default output directory is:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_architecture_dossiers/
```

The packet contains:

- `field_architecture_dossier_index.csv`
- `field_architecture_dossier_index.parquet`
- `field_architecture_dossier_summary.html`
- `fields/<district>-<field_number>-<field_slug>-dossier.html`
- `quality.json`
- `field_architecture_dossier_quality.json`
- `manifest.json`

`quality.json` and `field_architecture_dossier_quality.json` intentionally carry
the same payload.

## Selection

By default, the builder includes the top 25 opportunity-ranked fields and then
adds up to 3 rows for each architecture signal class absent from the top-ranked
set. Selection is deterministic by `opportunity_rank`, `district`,
`field_number`, and `field_name`.

Each index row includes a single `selection_reason` token:

- `top_ranked`
- `class_coverage:<architecture_signal_class>`

## Limitations

The dossier is a screening and decision-support product. It does not estimate or
assert reserves, economics, tariffs, pipeline capacity, right-of-way status,
route feasibility, or engineered facility design. It preserves upstream Texas
RRC caveats such as lease-level production allocation, no per-well production
allocation, GIS screening-only distances, dominant-county pipeline filtering,
missing well GIS, and PDQ water or well-count metric gaps.
