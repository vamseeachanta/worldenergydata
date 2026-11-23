# Codex adversarial code review - Issue #709

Implementation reviewed: Texas RRC pressure observations
Review time: 2026-07-03

## Verdict

MINOR after remediation - implementation is acceptable for the approved #709
scope.

No blocking defects remain after the live `/mnt/ace` smoke, parser/coverage
performance fixes, and the T2 adversarial review remediation pass.

## Findings

No unresolved blocking findings.

Resolved blocking findings from the T2 adversarial review:

1. `G-1 Field Data.WELLHEAD_PRESS` was initially curated as `WHP_shut_in`
   without requiring `source_row_no=SHUT-IN`. Fixed by requiring the SHUT-IN
   row context; added regression tests for SHUT-IN accepted and blank/FLOWING
   row numbers rejected.
2. Candidates with blank/invalid `api14` could initially become curated
   observations. Fixed by rejecting invalid API14 before curation and counting
   `missing_api`; added a regression test.
3. Source artifact hashing initially covered completion ZIPs only. Fixed by
   including Wellbore Query files in `input_artifacts`; added a regression
   assertion for completion and wellbore SHA256/byte-size payloads.

Minor residual caveats:

1. The command-line console script path imports the broader `worldenergydata`
   CLI and stalled in an unrelated `torch` import path from `safety_analysis`
   during smoke. The pressure build support layer itself completed and wrote
   `/mnt/ace` outputs. A separate CLI-startup issue should handle lazy-loading
   unrelated heavy modules.
2. The live run still reads the full Wellbore Query CSV before filtering to
   pressure-candidate API14s. The post-load filter prevents statewide groupby
   cost, but a future optimization could push candidate-API filtering into the
   wellbore read path.
3. WHP-derived rows remain screening-only and do not perform a static gas-column
   BHP correction in this slice. That matches the approved plan's downstream
   #710 policy gate, but consumers must not treat WHP gradients as measured BHP.

## Checks Performed

- Reviewed pressure classification, W-2 non-BHP handling, unit-basis fields,
  source warning propagation, depth priority, gradient gating, earliest-proxy
  selection, coverage aggregation, `/mnt/ace` output guard, staged writes, and
  manifest payloads.
- Ran focused tests:
  `PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync pytest --no-cov tests/unit/texas_rrc/test_pressure_observation*.py -q`
  -> 28 passed after the T2 review fixes.
- Ran remediation-focused tests:
  `PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync pytest --no-cov tests/unit/texas_rrc/test_pressure_observation_cli.py tests/unit/texas_rrc/test_pressure_observations.py tests/unit/texas_rrc/test_pressure_observation_sources.py -q`
  -> 15 passed after the T2 review fixes.
- Ran adjacent tests:
  `PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync pytest --no-cov tests/unit/texas_rrc/test_lifecycle_keys.py tests/unit/texas_rrc/test_lifecycle_sources.py tests/unit/texas_rrc/test_lifecycle_io.py tests/unit/texas_rrc/test_source_catalog.py -q`
  -> 31 passed after the final CLI helper split.
- Ran formatting/lint:
  `black --check --diff`, `isort --check-only --diff`, and `ruff check` on the
  touched pressure package, Texas RRC CLI command, and pressure tests -> clean.
- Ran `git diff --check` and `scripts/legal/legal-sanity-scan.sh` -> clean/PASS.
- Checked newly added pressure persistence and CLI helper function lengths
  against the local 50-line rule -> all pressure-related additions are <= 50
  lines per function.
- Ran live support-layer build against
  `/mnt/ace/worldenergydata/data/modules/texas_rrc` -> 360 candidates, 48
  curated observations, no source gaps, 2 hashed input artifacts, expected
  `raw_manifest_warning:completion_data:error:2026-07-01T00:36:55Z`.
- Wrote live `/mnt/ace` outputs:
  - `curated/pressure/well_pressure_observations/texas_rrc_well_pressure_observations.csv`
  - `curated/pressure/well_pressure_observations/texas_rrc_well_pressure_observations.parquet`
  - `normalized/pressure/texas_rrc_pressure_candidates.csv`
  - `normalized/pressure/texas_rrc_pressure_candidates.parquet`
  - `curated/pressure/well_pressure_observations/coverage_by_district_decade.csv`
  - `curated/pressure/well_pressure_observations/coverage_by_field_decade.csv`
  - `curated/pressure/well_pressure_observations/texas_rrc_pressure_observation_quality.json`
  - `curated/pressure/well_pressure_observations/manifest.json`
- Reloaded live CSV/JSON outputs and confirmed 48 observation rows, 360
  candidate rows, 6 district/decade coverage rows, 8 field/decade coverage
  rows, pressure/unit quality counts, no source gaps, 2 input artifacts, and
  the expected completion manifest warning.

## Required Changes Before Closeout

None for #709.
