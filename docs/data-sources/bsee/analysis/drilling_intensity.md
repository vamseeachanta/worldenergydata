# Days/10K drilling intensity previews

The existing calculation and drill-down preview are extended to the per-well
listing and dataset tables. The generic `days_per_10k_ft` column requires an
explicit `md` or `tvd` denominator; neither is selected automatically. These
previews do not establish that a supplied basis is ratified or that the wider
well population has been validated. Current unlabelled source rows yield null
ratios with `missing_basis`.

## Revision history

| Revision | Date | Change and reason |
|---|---|---|
| 1 | 2026-10-21 | Document listing and dataset previews with a worked example so the calculation and publication limits can be checked. |

## Method and sources

Issue #1080 specifies:

```text
Days/10K = drilling_days / depth_ft * 10000
```

The scale of 10,000 feet and the reference range of 20–23 days per 10,000 feet
are supported by SPE-87117-MS (2004), *Deepwater Success Through Predictable
and Distinctive Drilling and Completion Performance*, publisher-deposited
[public abstract, paragraph 4](https://api.crossref.org/works/10.2118/87117-MS).
The reference denominator and comparability to a supplied basis are not
established. The range is a context reference, not an acceptance limit; no
pass/fail classification is made against it.

`MAX_BH_TOTAL_MD` supplies measured depth (MD) in feet and
`MAX_WELL_BORE_TVD` supplies true vertical depth (TVD) in feet, following the
repository's existing `DEPTH_COLUMNS` contract in
`packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/drilling_intensity.py`.
Completion days never enter the numerator. The adapter preserves raw nullable
source cells before the legacy day-count display parser fills gaps.

For field and block rollups, valid drilling-day/depth pairs are selected
independently for each denominator. The calculation is the ratio of their
summed days to their summed depths, multiplied by the same scale. This follows
algebraically from depth weighting each bore's ratio. A mean of bore ratios
would give each bore equal weight regardless of depth.

Missing, negative or nonfinite days, and missing, nonpositive or nonfinite
depths, exclude a bore from both totals for that denominator. A measured zero
remains zero. Missing or conflicting basis labels refuse group ratios even
when the conflicting bore has invalid depth. Matched-pair totals, statuses and
included/excluded counts accompany both MD and TVD results.

## Worked example

The following inputs are synthetic arithmetic examples, not measured wells.
All rows carry the same explicit `synthetic-rule` basis and field/block labels.
The completion values demonstrate exclusion and have no physical significance.

| Bore | Drilling (days) | Completion (days) | MD (ft) | TVD (ft) |
|---|---:|---:|---:|---:|
| A | 10 | 900 | 10000 | 10000 |
| B | 90 | 900 | 30000 | 10000 |
| C | 40 | 900 | null | 10000 |

Table 1. Synthetic inputs; depth and day units are explicit.

- Bore A: MD and TVD both give `10 / 10000 * 10000 = 10.0` Days/10K.
- Bore B: MD gives `90 / 30000 * 10000 = 30.0`; TVD gives `90.0`.
- Bore C: MD is null; TVD gives `40.0`.
- Field/block MD: `(10 + 90) / (10000 + 30000) * 10000 = 25.0`.
  Two bores are included and one excluded; status is `computed_partial`.
- Field/block TVD: `(10 + 90 + 40) / 30000 * 10000 = 46.7` to one decimal.
  Three bores are included and none excluded; status is `computed`.
- The mean of the valid MD ratios is `(10 + 30) / 2 = 20.0`, which is not
  the depth-weighted result. Completion days do not change any ratio.

These calculations are written independently in the test docstrings in
`tests/unit/lower_tertiary/test_dc_listing_intensity.py` and
`tests/unit/lower_tertiary/test_dc_drilldown_intensity.py`.

## Preview interfaces

Set the namespace import path before running the builders:

```bash
export PYTHONPATH=src:packages/worldenergydata-core/src:packages/worldenergydata-bsee/src:scripts
```

Use an existing writable scratch directory as `OUTPUT_DIR`. With the established
Python environment, the interfaces are:

```bash
python scripts/lower_tertiary/build_wo_per_well_dc.py \
  --intensity-denominator md --output "$OUTPUT_DIR/listing-preview.md"
python scripts/lower_tertiary/build_dc_drilldown.py \
  --intensity-denominator md --output "$OUTPUT_DIR/drilldown-preview.html"
python scripts/hf_export/publish_dc_days_to_hf.py \
  --intensity-denominator md --dry-run
```

The listing and drill-down require a separate output destination for previews.
The dataset option requires `--dry-run` and writes only local Parquet previews
under the configured temporary directory. It adds intensity columns to
`dc_bores` and `dc_development_summary`; `dc_vintage_diff` retains its existing
schema. Nullable floating columns preserve an all-null population through a
Parquet round trip. Reference bounds, citation, URL and qualification accompany
each bore and development row. The shared legacy columns retain their values.

Python callers may pass `intensity_denominator="md"` or `"tvd"` to
`load_bores()`, `load_payload()` and `build_tables()`. The listing's private
`_intensity_input` member retains raw matched-pair inputs and is not exported
as a dataset column.

## Remaining publication work

The basis decision in issue #1064 requires wider population validation before
published figures are replaced. Basis-labelled input is required; an opaque
label alone is not evidence of validation. This change does not derive days,
choose a day rule, regenerate committed reports, upload datasets, or update an
external capability. The external capability can consume the preview column
schema after its separate validation and release work. Legacy independently
computed `days_per_10k` variants remain follow-up convergence work.
