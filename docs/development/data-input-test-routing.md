# Curated and staging input test routing

The inventory is derived from `git ls-tree -r --name-only origin/main` at
`e7f791dcdd6d0e41229c24ca2c0b12376d7655b6`. It contains eight tracked input
directories named `curated` or `staging` beneath `data/` and `packages/`.
`tests/unit/curated` contains validators, not input data.

The routes below are checked through `select`, `select_fast`, and both
`to_matrix` modes. Each data-only edit selects module scope, its listed targets,
and the always-on targets, without duplicates or nonexistent targets. Multiple
targets for a prefix are additive; mixed source/test edits retain their original
owning-domain shard. Trailing slashes keep near-prefix filenames and sibling
directories outside these routes. Cost and package-member routing are retained.

| Tracked input directory | Representative file | Selected targets | Route |
| --- | --- | --- | --- |
| `data/modules/cost/curated/` | `sanctioned_projects.csv` | `tests/unit/cost` | Existing prefix |
| `data/modules/cost/staging/` | `europe-2016-2026.csv` | `tests/unit/cost` | Existing prefix |
| `data/modules/facility_specs/curated/` | `mooring_facility_matrix.csv` | `tests/modules/field_development/test_withheld_data.py` | New prefix |
| `data/modules/frontier_basins/curated/` | `frontier_discoveries.csv` | `tests/unit/canada` | New prefix |
| `data/modules/offshore_assets/curated/` | `lt_reserves_discovery.csv` | `tests/unit/field_development`; `tests/modules/field_development/test_withheld_data.py` | New additive prefixes |
| `data/modules/subsea/curated/` | `rigid_jumper_specs.csv` | `tests/unit/subsea`; `tests/unit/curated` | New additive prefixes |
| `packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_data/curated/` | `terminals_seed.csv` | `tests/unit/lng_terminals` | Existing package-member pattern |
| `packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/_data/curated/` | `construction_evidence.json` | `tests/unit/vessel_fleet` | Existing package-member pattern |

Table 1. Tracked curated/staging input owners and their selected test targets.

The owning tests were inspected to establish the route associations:

- `tests/unit/cost/test_project_field_crosswalk.py` exercises recursive discovery
  of curated and staging project sources, including sanctioned projects.
- `tests/modules/field_development/test_withheld_data.py` checks retained-file
  inventory metadata, facility schema/metadata, withheld notices, and rejection
  of unavailable payloads for both facility specifications and offshore assets.
- `tests/unit/canada/emerging_basins/test_frontier_discoveries.py` exercises
  `FrontierDiscoveryLoader`, which reads the frontier-discovery CSV.
- `tests/unit/field_development/test_lt_reserves_discovery.py` exercises the
  reserves-table builder and its field-code bridge. The availability contract
  also checks the retained offshore-assets file inventory.
- `tests/unit/subsea/test_manifold_suppliers.py` exercises the supplier CSV
  loader; `tests/unit/curated/test_csv_validation.py` reads and validates the
  rigid-jumper and mooring CSVs. Both suites are required for the subsea owner.
- `tests/unit/lng_terminals/test_terminal_schema.py` resolves the package-local
  seed CSV and exercises terminal loading and schema validation.
- `tests/unit/vessel_fleet/test_construction_evidence.py` loads construction
  evidence and checks its provenance, manifest integrity, and query contracts.

## Limits and exclusions

The facility matrix route establishes availability and metadata coverage only.
An engineering validator for `mooring_facility_matrix.csv` contents is not
established by the inspected tests. Acceptance of those contents as engineering
input would require a separately established content validator.

Withheld payloads remain unavailable. Their notices are availability evidence,
not substitutes for private data or proof of its validity. Raw archives,
generated solver assets, external datasets, and unmaterialized withheld payload
contents are excluded from this curated/staging routing inventory.

The selector regressions check target membership without importing domain code,
running domain validators, downloading data, or executing solvers. A selected
suite is not a recorded runtime result for that suite. No data contents, domain
tests, thresholds, or CI gate policy are changed.

Implementation scope: [issue 1901](https://github.com/vamseeachanta/worldenergydata/issues/1901).
