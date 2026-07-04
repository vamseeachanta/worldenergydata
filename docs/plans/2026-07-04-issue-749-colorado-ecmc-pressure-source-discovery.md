# Plan: Issue #749 - Colorado ECMC pressure-source discovery

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/749
**Status:** plan-review
**Tier:** T2 (official source discovery, bounded live scout, parser fixture, docs, follow-up decision)
**Client:** N/A
**Project:** worldenergydata onshore pressure screen
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Implementation will start from `origin/main` only after this plan is reviewed,
pushed, marked `status:plan-review`, and explicitly approved by the user. The
approved implementation will use TDD for any code path: HTML fixture parsing,
source-probe manifesting, API normalization, pressure-kind classification, and
`/mnt/ace` output contracts will receive failing tests before production code.

This issue will not implement a statewide Colorado pressure ingest. It will
identify and prove the official source path needed for a later ingest decision.

### Issue and dependency status

Planning-time issue probes on 2026-07-04 indicate:

| Issue | State | Current role |
|---|---|---|
| [#708](https://github.com/vamseeachanta/worldenergydata/issues/708) | open, `status:needs-plan` | Parent pressure-screen epic |
| [#709](https://github.com/vamseeachanta/worldenergydata/issues/709) | closed, `status:done` | Texas RRC pressure observations |
| [#725](https://github.com/vamseeachanta/worldenergydata/issues/725) | closed, `status:done` | Kansas KGS pressure observations |
| [#732](https://github.com/vamseeachanta/worldenergydata/issues/732) | closed, `status:done` | Multi-state pressure-screen foundation |
| [#740](https://github.com/vamseeachanta/worldenergydata/issues/740) | closed, `status:done` | Oklahoma OCC completion pressures |
| [#745](https://github.com/vamseeachanta/worldenergydata/issues/745) | closed, `status:done` | Colorado ECMC Form 7 bulk production and wells spine |
| [#749](https://github.com/vamseeachanta/worldenergydata/issues/749) | open, `status:needs-plan` | This official pressure-source discovery slice |

[#749](https://github.com/vamseeachanta/worldenergydata/issues/749) will build
on the [#745](https://github.com/vamseeachanta/worldenergydata/issues/745)
Colorado lifecycle spine. It will not reinterpret [#745](https://github.com/vamseeachanta/worldenergydata/issues/745)
empty Form 7 pressure columns as usable pressure evidence.

### Parallel work check

Planning-time worktree probes show other active worktrees for Texas RRC source
catalog, Texas RRC refresh, FDAS, corpus datasets, pages, field equipment, and
autorun lanes. This issue will avoid those scopes. It will stay inside:

- `docs/data-sources/onshore/state-well-databases/`
- `docs/plans/`
- `scripts/review/results/`
- `src/worldenergydata/modules/state_regulators/colorado_ecmc/` only if the
  approved implementation adds a bounded source-scout/parser
- focused unit tests under `tests/unit/modules/state_regulators/`

### Direct-source evidence

Official ECMC evidence checked on 2026-07-04:

| Source | Planning-time evidence | Role in this issue |
|---|---|---|
| Official download catalog | `https://ecmc.state.co.us/appAssets/data/downloadsExt.txt` lists bulk datasets, including wells, production, facilities, field inspections, MIT, and guidance | Source inventory baseline |
| ECMC data page | `https://ecmc.state.co.us/data2.html`; public download app redirects to the state data page, while the direct old catalog remains scriptable | Landing-page and catalog traceability |
| Production data dictionary | `https://ecmc.state.co.us/documents/data/downloads/production/production_record_data_dictionary.htm` defines `GasPressureTubing`, `GasPressureCasing`, `WaterPressureTubing`, and `WaterPressureCasing` | Explains why [#745](https://github.com/vamseeachanta/worldenergydata/issues/745) looked in Form 7 and why the live slice produced no rows |
| Download guide | `https://ecmc.state.co.us/documents/data/downloads/ECMC_Download_Guidance_v2_ada.pdf` describes ECMC SQL-backed data, forms, attachments, production summaries, wells, and GIS downloads | Source-system context and data-request lead |
| Wells GIS | `https://ecmc.state.co.us/documents/data/downloads/gis/WELLS_SHP.ZIP` remains the approved well/API/depth/field spine from [#745](https://github.com/vamseeachanta/worldenergydata/issues/745) | Join denominator |
| Facilities GIS | `https://ecmc.state.co.us/documents/data/downloads/gis/Facilities.ZIP`; HEAD 200, 169,504,664 bytes, last-modified 2026-07-03 | Candidate facility/well crosswalk and scout seed source |
| MIT data | `https://ecmc.state.co.us/documents/data/downloads/Engineering/MechIntegrityDownload.html` links `MIT.zip`; guide says the file is compiled from Form 21 submitted by operators | Separate mechanical-integrity lane, not a reservoir pressure source |
| Field inspections | `https://ecmc.state.co.us/documents/data/downloads/Field/FieldDownload.html`; updated monthly page | Compliance/operations context only unless a pressure-bearing table is proven |
| Imaged document search | `https://ecmc.state.co.us/cogisdb/ImagedDocToolMenu` renders the official document-search entry point and Laserfiche links | Fallback for forms/attachments; not preferred for automation |
| FacilityDetail scout card | `https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx?api=12339345` renders structured well data and an "Initial Test Data" block | Highest-priority direct endpoint to probe |
| COA page | `https://ecmc.state.co.us/cogisdb/Resources/COAs?facid=12339345` renders Form 5A/Form 17 conditions | Regulatory context; not a pressure-observation table |

The FacilityDetail sample for API fragment `12339345` renders a completed
interval/scout card with formation, depth, perforation, treatment, and initial
test sections. The "Initial Test Data" block includes test date, method, hours
tested, and test-type/measure pairs such as `CASING_PRESS` and `TUBING_PRESS`.
The same page also carries treatment pressure fields, which will be classified
separately so frac-treatment pressures cannot enter the underpressured screen.

### Source bounds

The approved implementation will treat FacilityDetail/Form 5A initial-test
content as a candidate official source, not as a confirmed statewide ingest.
The scout will be capped, polite, and reproducible. It will prove whether the
endpoint can support an automated direct-source lane or whether the project
should pursue an ECMC data request for the SQL-backed Form 5A/initial-test
tables.

This issue will not attempt:

- full COGIS FacilityDetail scraping;
- Laserfiche or imaged-form OCR;
- Form 17 bradenhead pressure interpretation;
- Form 21 MIT pressure interpretation as reservoir/wellhead production
  pressure;
- use of PatchOps, LinkedIn, commercial vendor output, or third-party scraper
  code as source of record;
- Colorado participation or analog gates in the multi-state pressure screen.

### Interpretation contract

The discovery output will classify pressure-bearing candidates before any
screen use:

| Candidate pressure | Source section | Proposed classification |
|---|---|---|
| `CASING_PRESS` in Initial Test Data | FacilityDetail / Form 5A completed interval | Candidate `WHP_casing_initial_test`; usable only after gas/formation/depth context is present |
| `TUBING_PRESS` in Initial Test Data | FacilityDetail / Form 5A completed interval | Candidate `WHP_flowing_tubing_initial_test`; usable only after gas/formation/depth context is present |
| Treatment maximum pressure | FacilityDetail treatment section | Engineering treatment pressure; excluded from underpressured screen |
| Bradenhead/Form 17 pressures | COA/document lanes | Annulus/compliance pressure; excluded until separate interpretation approval |
| MIT/Form 21 pressures | MIT bulk download | Mechanical-integrity pressure; excluded from reservoir and production-pressure screens |
| Form 7 production pressures | Bulk production CSV | Already implemented; remains empty for the approved [#745](https://github.com/vamseeachanta/worldenergydata/issues/745) live slice unless later source refreshes prove otherwise |

The approved implementation will preserve raw pressure units exactly as
reported. Any later conversion from psig to psia, depth correction, or gradient
screening will require a separate implementation decision after the source
path is proven.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-04-issue-749-colorado-ecmc-pressure-source-discovery.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review - Codex inline | `scripts/review/results/2026-07-04-plan-749-codex-inline.md` |
| Source discovery report | `docs/data-sources/onshore/state-well-databases/colorado-ecmc-pressure-source-discovery.md` |
| Source catalog update | `docs/data-sources/onshore/state-well-databases/source-catalog.md` |
| Optional scout module | `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py` |
| Optional FacilityDetail parser | `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py` |
| Optional scout config | `config/colorado_ecmc_source_discovery.yml` |
| Optional tests | `tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail.py`, `tests/unit/modules/state_regulators/test_colorado_ecmc_source_discovery.py` |

## Deliverable

The approved implementation will produce a source decision report and, if the
bounded scout is implemented, a small reproducible sample under:

```text
/mnt/ace/worldenergydata/data/modules/colorado_ecmc/source_discovery/
  raw/
    facility_detail/
      manifest.json
      *.html
  parsed/
    facility_detail_initial_tests.parquet
    facility_detail_initial_tests.json
  reports/
    colorado_ecmc_pressure_source_discovery.json
```

The sample will use a small configured API list and a hard cap. It will not
iterate the statewide well population.

## Implementation Plan

### Task 1: Write the official source inventory and decision matrix

**Files:**

- Create: `docs/data-sources/onshore/state-well-databases/colorado-ecmc-pressure-source-discovery.md`
- Modify: `docs/data-sources/onshore/state-well-databases/source-catalog.md`

**Work:**

1. Record official ECMC URLs, source ownership, refresh cadence, access
   constraints, and observed fields for production, wells, facilities, MIT,
   field inspections, FacilityDetail, COAs, document search, and the download
   guide.
2. Mark each source as one of:
   `approved_spine`, `candidate_pressure_observation`, `context_only`,
   `excluded_integrity_pressure`, or `requires_data_request`.
3. Document why Form 7 production pressure columns remain insufficient after
   [#745](https://github.com/vamseeachanta/worldenergydata/issues/745).
4. Document why MIT/Form 21, treatment pressure, and Form 17/bradenhead lanes
   will be excluded from the underpressured screen unless a later issue
   explicitly changes the interpretation contract.

**Verification:**

```bash
git diff --check -- docs/data-sources/onshore/state-well-databases
```

### Task 2: Add a FacilityDetail HTML parser behind fixture tests

**Files:**

- Create: `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py`
- Test: `tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail.py`
- Fixture: focused HTML fixture under the existing test-fixture convention

**Interfaces:**

- `parse_facility_detail_html(html: str, source_url: str | None = None) -> pd.DataFrame`
- `classify_facility_detail_pressures(frame: pd.DataFrame) -> pd.DataFrame`

**TDD steps:**

1. Write a failing fixture test using a saved official FacilityDetail sample
   that expects well/API identifiers, formation, test date, test method, hours
   tested, `CASING_PRESS`, `TUBING_PRESS`, oil/gas/water test rates, and source
   URL lineage.
2. Write a failing classification test that separates initial-test casing and
   tubing pressures from treatment pressure fields and MIT/bradenhead lanes.
3. Run:

   ```bash
   PYTHONPATH=src:packages/worldenergydata-core/src pytest \
     tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail.py -q
   ```

   Expected: fail before the parser exists.
4. Implement the smallest parser needed for the official fixture. The parser
   will use structured HTML parsing, not regex-only extraction.
5. Re-run the focused test and keep the parser output source-lineage rich
   enough to audit pressure-kind decisions.

### Task 3: Add a capped live source scout that writes `/mnt/ace` evidence

**Files:**

- Create: `config/colorado_ecmc_source_discovery.yml`
- Create: `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py`
- Test: `tests/unit/modules/state_regulators/test_colorado_ecmc_source_discovery.py`

**Interfaces:**

- `load_source_discovery_config(path: str | Path) -> dict`
- `build_facility_detail_url(api_fragment: str) -> str`
- `fetch_facility_detail(url: str, destination: str | Path, timeout: int = 60) -> dict`
- `write_source_discovery_manifest(base_dir: str | Path, downloads: list[dict]) -> dict`

**TDD steps:**

1. Write a failing config test that enforces a small `sample_apis` list, a hard
   `max_requests` cap, a `request_delay_seconds` throttle, direct ECMC URLs, and
   `/mnt/ace/worldenergydata/data/modules/colorado_ecmc/source_discovery` as the
   default output root.
2. Write a failing manifest test using mocked HTTP responses that expects
   `source_url`, `raw_path`, `sha256`, `size_bytes`, `status_code`,
   `last_modified`, `etag`, `downloaded_at`, and parser row counts.
3. Run:

   ```bash
   PYTHONPATH=src:packages/worldenergydata-core/src pytest \
     tests/unit/modules/state_regulators/test_colorado_ecmc_source_discovery.py -q
   ```

   Expected: fail before the source scout exists.
4. Implement the capped scout with no statewide iteration mode.
5. Run the focused tests, then run the live scout only if network access is
   available and write the sample/raw evidence under `/mnt/ace`.

### Task 4: Publish the source decision and next implementation issue

**Files:**

- Modify: `docs/data-sources/onshore/state-well-databases/colorado-ecmc-pressure-source-discovery.md`
- Modify: `docs/data-sources/onshore/state-well-databases/source-catalog.md`
- Optional: create a follow-up GitHub issue after the decision is known

**Work:**

1. Summarize whether FacilityDetail/Form 5A initial-test data is sufficiently
   stable for an automated direct-source ingest.
2. If it is viable, create a follow-up implementation issue for a production
   ingest that includes rate limits, retry policy, resume manifests, and
   statewide coverage accounting.
3. If it is not viable, create or update a data-request lane for ECMC's
   SQL-backed initial-test/Form 5A tables.
4. Preserve the decision boundary: Colorado will remain excluded from
   underpressured-screen participation gates until a pressure source with
   positive usable observations is implemented and reviewed.

## Acceptance Criteria

- Official ECMC source evidence will be documented with direct URLs, source
  roles, refresh cadence, access constraints, and pressure-field relevance.
- Form 7 production pressure insufficiency will remain documented with the
  [#745](https://github.com/vamseeachanta/worldenergydata/issues/745) live
  zero-positive result.
- MIT/Form 21, treatment pressure, Form 17/bradenhead, and imaged-form lanes
  will be excluded from underpressured-screen evidence unless a later approved
  issue changes that contract.
- A FacilityDetail/Form 5A initial-test parser will be fixture-tested before
  implementation if code is added.
- Any live FacilityDetail source scout will be capped, throttled, manifesting,
  and limited to the configured sample APIs.
- Any live source-scout data will be written under `/mnt/ace`, with raw HTML,
  parsed sample output, and a manifest/report.
- The implementation closeout will either create a follow-up automated-ingest
  issue or document why ECMC data request/manual acquisition is the correct
  path.
- `git diff --check`, focused unit tests for any new code, and
  `scripts/legal/legal-sanity-scan.sh` will pass before code closeout.

## Rollback / Safety

- The approved implementation will avoid any full-population scrape. The hard
  request cap and sample list will be required in config and tested.
- Raw live HTML samples will be stored only under `/mnt/ace`; the repository
  will carry fixtures that are small enough for tests and scrubbed of any
  machine-specific paths.
- The scout will use official ECMC endpoints only. Third-party source text will
  not be used as data of record.
- If ECMC endpoint behavior changes, the parser/scout will fail closed and the
  source report will recommend the data-request path instead of silent scraping.
