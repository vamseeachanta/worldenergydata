# Texas RRC Field Architecture Portfolio

The field architecture portfolio is the final onshore screening packet in the
Texas RRC pilot. It consumes the field-architecture dossier index and publishes a
portfolio-level action queue, rollups, quality metadata, and an HTML report under
`/mnt/ace/worldenergydata/data/modules/texas_rrc`.

The durable source of record is official Texas RRC data. LinkedIn posts,
PatchOps, and scraper examples are discovery or validation context only; they are
not persisted as authoritative source data.

## Lifecycle

The full onshore lifecycle is:

1. Official Texas RRC raw snapshots refresh into `/mnt/ace`.
2. Well lifecycle, production atlas, and GIS infrastructure metrics are curated.
3. Field-development metrics combine well, field, production, and infrastructure
   signals.
4. Field atlas reports produce field-level summaries and drill-down HTML pages.
5. Field opportunity rankings classify architecture signals and follow-up needs.
6. Field architecture dossiers create bounded per-field review packets.
7. The portfolio report turns the dossier index into a field-development action
   queue and portfolio rollups.

The portfolio builder consumes:

- `curated/analysis/field_architecture_dossiers/field_architecture_dossier_index.parquet`
  or `.csv`
- `curated/analysis/field_architecture_dossiers/manifest.json`
- `curated/analysis/field_architecture_dossiers/quality.json`
- `curated/analysis/field_architecture_dossiers/fields/*.html`

## Refresh Cadence

Refresh upstream artifacts first, then rebuild the portfolio:

```bash
worldenergydata texas-rrc build-field-architecture-portfolio --require-sources
```

Use dry-run mode to inspect source health without writing:

```bash
worldenergydata texas-rrc build-field-architecture-portfolio --dry-run
```

The portfolio should be rebuilt after any upstream raw, lifecycle, production,
infrastructure, field-atlas, opportunity, or dossier refresh. It inherits source
gaps from the dossier manifest and quality files rather than hiding missing or
partial source evidence.

## Outputs

The default output directory is:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_architecture_portfolio/
```

The packet contains:

- `field_architecture_action_queue.csv`
- `field_architecture_action_queue.parquet`
- `field_architecture_class_summary.csv`
- `field_architecture_class_summary.parquet`
- `field_architecture_followup_summary.csv`
- `field_architecture_followup_summary.parquet`
- `field_architecture_portfolio.html`
- `quality.json`
- `field_architecture_portfolio_quality.json`
- `manifest.json`

`quality.json` and `field_architecture_portfolio_quality.json` intentionally carry
the same payload.

## Action Queue

Each row preserves field identifiers, architecture signal class, opportunity
score/rank, field-development context, source caveats, quality flags, and a safe
relative link back to the source dossier when the dossier is inside the expected
`field_architecture_dossiers/fields/` directory.

Architecture classes map to deterministic screening actions:

- `low_data_confidence` -> `data_completion_review`
- `infrastructure_constrained_activity` -> `infrastructure_constraint_screen`
- `high_access_infill_redevelopment` -> `infill_redevelopment_screen`
- `emerging_growth` -> `growth_appraisal_screen`
- `mature_harvest` -> `mature_harvest_review`
- `monitor_only` -> `monitor_only`

Rows with unknown classes are routed to `data_completion_review` and receive an
`unknown_architecture_signal_class` caveat.

## Limitations

The portfolio is a screening and prioritization product. It does not estimate or
assert reserves, economics, tariffs, pipeline capacity, right-of-way status,
route feasibility, product compatibility, ownership, or engineered facility
design. It preserves upstream Texas RRC caveats such as lease-level production
allocation, no per-well production allocation, GIS screening-only distances,
dominant-county pipeline filtering, missing well GIS, and PDQ water or well-count
metric gaps.
