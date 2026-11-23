# Kansas KGS Pressure Observations

Issue: https://github.com/vamseeachanta/worldenergydata/issues/725

This source package builds a per-well pressure-observation table from official
Kansas Geological Survey bulk files:

- `https://www.kgs.ku.edu/PRS/Ora_Archive/kansas_proration_pressures.txt`
- `https://www.kgs.ku.edu/PRS/Ora_Archive/ks_wells.zip`

Raw, normalized, and curated outputs live under:

```text
/mnt/ace/worldenergydata/data/modules/kansas_kgs/
```

Build command:

```bash
worldenergydata kansas-kgs build-pressure-observations \
  --root /mnt/ace/worldenergydata/data/modules/kansas_kgs
```

Use `--refresh` to re-fetch the official KGS bulk files before building. Without
`--refresh`, the build hashes and manifests the raw files already present under
`raw/`. On 2026-07-03, KGS HEAD probes returned:

| Source | Last-Modified | Content-Length |
|---|---:|---:|
| `kansas_proration_pressures.txt` | Thu, 27 Mar 2025 17:32:01 GMT | 14,017,158 |
| `ks_wells.zip` | Fri, 05 Jun 2026 19:31:21 GMT | 43,773,721 |
| `ks_tops.zip` (optional, not parsed in v1) | Fri, 05 Jun 2026 19:31:33 GMT | 27,025,896 |

The curated table is written to:

```text
curated/pressure/well_pressure_observations/
  well_pressure_observations.csv
  well_pressure_observations.parquet
  coverage_by_county_year.csv
  coverage_by_county_year.parquet
  quality.json
  manifest.json
```

The 2026-07-03 build produced 39,134 curated pressure observations from 79,093
normalized pressure rows and 516,206 normalized well rows. The curated
observation window is 1996-2004. The raw source manifest records per-source URL,
path, byte size, SHA256, and `observed_at`; the curated manifest embeds that raw
manifest snapshot plus output file hashes.

Curated schema:

```text
api14, api10, api_state_code, api_county_code, county_name, state,
source_agency, field_name, test_date, test_year, test_type,
pressure_psig_raw, pressure_psia, atmospheric_pressure_psi, pressure_kind,
reference_depth_ft, reference_depth_method, gradient_psi_ft, gradient_method,
formation, is_earliest_observation_for_well, virgin_pressure_proxy_method,
source_file, source_row_id, quality_flags, limitations
```

Quality metrics include source/parser counts (`pressure_row_count`,
`bad_field_count_rows`, `nonpositive_pressure_rows`, `well_row_count`,
`wells_date_parse_failure_count`), join/depth counters
(`missing_well_join_count`, `ambiguous_api10_join_count`, `missing_depth_count`),
county/year counters, and Hugoton/Panoma coverage counts.

`SHUT_IN_PRESS` is treated as gauge wellhead pressure. The curated output
preserves `pressure_psig_raw` and also emits `pressure_psia` using a sea-level
14.7 psi atmospheric-pressure screening assumption. This is not corrected for
Hugoton-area elevation and is not bottom-hole pressure.

The `is_earliest_observation_for_well` flag means earliest available positive
KGS proration-year observation for a defensible well identity. It is not
measured initial reservoir pressure. Ambiguous API10/API14 identity suppresses
or qualifies that proxy flag.

This packet is the Kansas pressure-observation slice for parent
[#708](https://github.com/vamseeachanta/worldenergydata/issues/708). It follows
the pressure-observation contract planned for Texas RRC
[#709](https://github.com/vamseeachanta/worldenergydata/issues/709), but uses
Kansas KGS direct bulk files while Texas raw pressure extraction remains
separate. Downstream field ranking and under-pressure screening belong to
[#710](https://github.com/vamseeachanta/worldenergydata/issues/710).
