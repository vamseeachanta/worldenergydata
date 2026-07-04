# Texas RRC Pressure Observations

Texas RRC pressure observations extract structured pressure-like fields from
official completion packet data and join them to Wellbore Query depth context.
The output supports the under-pressured well and field screen in
[#708](https://github.com/vamseeachanta/worldenergydata/issues/708) and feeds
downstream ranking work in
[#710](https://github.com/vamseeachanta/worldenergydata/issues/710).

## Source Of Record

The command uses local snapshots of official Texas RRC bulk data only.
PatchOps, Collide, EWA web-form flows, and historical scraper repositories are
validation or endpoint-intelligence surfaces; they are not durable inputs for
this product.

| Input | Official source | Refresh cycle | Local path |
| --- | --- | --- | --- |
| `completion_data` | `https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/#completion-data-table` | Nightly | `/mnt/ace/worldenergydata/data/modules/texas_rrc/raw/completions/` |
| `wellbore_query` | `https://www.rrc.texas.gov/media/kywh5qsj/wellboredump.zip` | Monthly, beginning of month | `/mnt/ace/worldenergydata/data/modules/texas_rrc/raw/wellbore/query/` |

The loader also reads raw refresh manifests under
`/mnt/ace/worldenergydata/data/modules/texas_rrc/manifests/`. If a completion
ZIP exists but the newest `completion_data-*` manifest has `status=error`, the
run proceeds and records a `raw_manifest_warning` in quality and manifest JSON.

## Command

Refresh source snapshots first when needed:

```bash
uv run worldenergydata texas-rrc refresh --source completion_data
uv run worldenergydata texas-rrc refresh --source wellbore_query
```

Build the pressure outputs:

```bash
uv run worldenergydata texas-rrc build-pressure-observations \
  --raw-root /mnt/ace/worldenergydata/data/modules/texas_rrc \
  --output-root /mnt/ace/worldenergydata/data/modules/texas_rrc \
  --require-sources
```

Use `--dry-run` to inspect counts and source warnings without writing outputs:

```bash
uv run worldenergydata texas-rrc build-pressure-observations --dry-run
```

Sandbox runs must opt into non-ACE outputs:

```bash
uv run worldenergydata texas-rrc build-pressure-observations \
  --raw-root /tmp/texas_rrc \
  --output-root /tmp/texas_rrc_out \
  --allow-non-ace-output
```

## Output Contract

The command writes normalized candidates and curated pressure observations:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/
+-- normalized/pressure/
|   +-- texas_rrc_pressure_candidates.csv
|   +-- texas_rrc_pressure_candidates.parquet
+-- curated/pressure/well_pressure_observations/
    +-- texas_rrc_well_pressure_observations.csv
    +-- texas_rrc_well_pressure_observations.parquet
    +-- coverage_by_district_decade.csv
    +-- coverage_by_district_decade.parquet
    +-- coverage_by_field_decade.csv
    +-- coverage_by_field_decade.parquet
    +-- texas_rrc_pressure_observation_quality.json
    +-- manifest.json
```

Writes are staged under `.staging-pressure-*` directories before promotion. By
default, writes outside `/mnt/ace/worldenergydata/data/modules/texas_rrc` are
rejected.

## Curated Schema

Curated observation columns include:

```text
api14, api10, district, field_no, field_name, test_date, test_year,
source_record_type, source_pressure_field, pressure_raw_psi,
pressure_unit_basis, pressure_psia, atmospheric_pressure_psi,
pressure_kind, pressure_method, reference_depth_ft, reference_depth_method,
gradient_psi_ft, gradient_method, source_file, source_tracking_no,
source_packet_id, source_form_id, source_row_no, source_row_id,
usable_for_virgin_pressure_proxy, is_earliest_observation_for_well,
virgin_pressure_proxy_method, quality_flags, limitations
```

Normalized candidates retain source pressure fields that are not yet defensible
as curated observations. This is deliberate: W-2 casing, flowing, and fracturing
pressures are preserved as candidates but are not silently represented as BHP.

## Pressure Semantics

- `G-1.BOTTOM_HOLE_PRESS` becomes `pressure_kind=BHP_measured` with
  `pressure_method=source_reported_bottom_hole_pressure`.
- `G-1 Field Data.WELLHEAD_PRESS` and `G-10.SIWH_PRESSURE` become
  `pressure_kind=WHP_shut_in`.
- Surface wellhead pressure uses `pressure_raw_psi + 14.7` for
  `pressure_psia`, with `pressure_unit_basis=psig_assumed` and a screening
  limitation.
- Unclassified G-1 measurement, G-10 flowing, and W-2 pressure-like fields
  remain normalized candidates until source semantics justify a curated kind.

Reference depth priority is linked production interval midpoint, G-1
bottom-hole depth, G-1 vertical depth, G-1 measured depth, G-1 plug-back depth,
then unique Wellbore Query total depth. Gradients are only emitted for positive
pressure, positive depth, and unambiguous linkage.

`is_earliest_observation_for_well` marks the earliest usable pressure row by
API14 and test date. WHP-derived gradients remain screening-only until #710
performs or explicitly declines a gas-column correction.

## Coverage And Quality

Coverage tables report how many distinct wells have at least one curated
pressure observation by:

- district and decade
- district, field, and decade

Quality JSON includes parser counts, candidate and curated row counts, W-2
candidate counts not curated, uncurated candidate counts, ambiguous depth
counts, source gaps, and raw manifest warnings.

## Known Caveats

- The structured completion ZIP available in `/mnt/ace` is a daily packet, not
  a full historical pressure archive.
- Some G-10/W-10 status and historical pressure evidence lives only in PDFs or
  imaged records; that extraction is outside this structured bulk-data scope.
- Source pressure units are not always explicit in packet data. Raw values,
  unit basis, and limitations are preserved so downstream ranking does not
  confuse source-reported psi, assumed psig, and screening psia.
- This product does not classify hydrostatic tiers, make reserves claims, or
  produce field architecture recommendations; those remain downstream analysis
  tasks.
