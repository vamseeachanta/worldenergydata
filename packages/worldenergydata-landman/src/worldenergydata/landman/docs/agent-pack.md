# Landman module knowledge pack

| Header | Value |
|---|---|
| Module | landman |
| Repository | worldenergydata |
| Package path | `packages/worldenergydata-landman/src/worldenergydata/landman` |
| Pack revision | 1, 2026-10-15 |
| Code revision | `13f3b70aa7a87045631b737406c881e4cb5bcfd0` |
| Analysis family | EC; data pipelines, Python calculations gate set |
| Quality manager role | Calculations quality manager; data-pipeline coverage interim |
| Status | DRAFT; independent clearance pending |

The header records this pack's scope and review disposition; code citations below resolve at the code revision.

## 1. Purpose and scope

`Landman` validates configuration and routes ownership, lease and title collection, while the directly exported providers expose county-reference, state-GIS and federal-land interfaces. [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L94-L150] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/__init__.py:L35-L55]

The automatic route selects `county_records`, then attempts an import of `providers.county_records`; other provider names enter the unimplemented branch. This pack treats the route as incomplete rather than evidence of acquisition readiness. [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L251-L288]

`CountyReferenceProvider` returns embedded reference information and search instructions; its health check only tests whether the embedded mapping is nonempty. [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L376-L428] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L430-L506] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L594-L601]

The two federal query branches and three state-GIS query branches suppress transport/parser errors into empty results (5 branches); the custom-GIS stub also returns an empty list. Empty results therefore do not establish absence of records. [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L208-L244] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L370-L406] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L195-L237] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L339-L365] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L478-L510] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L281-L295]

The manifest advertises `stable`; that is metadata, not a qualification of the provider route. [module-manifest.yaml:L236-L258]

## 2. Inputs and outputs

### Inputs

| Input | Unit and range | Default | Source and evidence |
|---|---|---|---|
| Router `cfg` | Mapping; nonempty; `data_types` and `provider` checked against constants | Provider `auto`; data types `all`; empty config, unknown data type/provider raise `TypeError`; default `auto` hits D1, caught and wrapped as `TypeError`; these failures do not raise the documented module error type; invalid-state/legal-description factories instead raise `LandmanValidationError` | [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L116-L129] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L152-L211] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L251-L272] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L302-L305] [packages/worldenergydata-landman/src/worldenergydata/landman/exceptions.py:L22-L28] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L22-L48] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L207-L223] |
| `state`, `county` | State code text checked against the code mapping; county text 2–100 characters and at least 2 alphabetic characters | Required in ownership search | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L161-L216] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L329-L363] |
| `legal_description` | Text; 5–1000 characters, then pattern checks; no geometric closure calculation | Optional search filter | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L70-L127] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L365-L388] |
| `mineral_interest_percent` | Percent; 0–100 inclusive; converted with `float` | Required for the scalar validator, optional in a record | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L218-L255] [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L475-L480] |
| `royalty_rate` | Decimal or percent; values above 1 divided by 100; normalized range 0–0.50 | Optional in lease records; percent-input regression: `tests/unit/landman/test_validators.py::TestValidateRoyaltyRate::test_percentage_format` | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L257-L289] [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L535-L540] [tests/unit/landman/test_validators.py:L250-L252] |
| `acreage` | Acres; greater than 0 and at most 1000000 | `None` accepted by scalar acreage validation | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L407-L431] |
| Lease terms | Years; primary 1–99, secondary 0–99 after integer conversion | Primary `None` accepted | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L363-L405] |
| Date text | Calendar date; five parse formats; year 1800 to current year plus 100 unless overridden | Empty accepted | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L316-L361] |
| Provider HTTP settings | Timeout 30 s; 3 retries; retry delay 1.0 s; rate delay 0.5 s; cache TTL 3600 s | Constructor defaults; no range enforcement in assignment | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/base.py:L152-L181] |
| Direct GIS and federal search `limit` | Record count; passed through to request parameters | 100 records | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L156-L174] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L224-L230] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L134-L160] |

### Outputs

| Output | Unit and convention | Default or behavior | Evidence |
|---|---|---|---|
| Router result | Mapping with status and record count | Lists contribute length; nonlists contribute 1, including error strings | [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L136-L147] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L323-L327] |
| `OwnerSearchResult` | Counts in records; duration in ms; timestamp | Counts initialized as sum of three record lists; errors and warnings separate | [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L657-L736] |
| Direct search results | `total_count`, `returned_count`, page and page size in records; query time in ms | Page 1, page size 100, `has_more=False`; typed results serialized | [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L291-L358] |
| Ownership, lease, title dictionaries | Dates/timestamps serialized with `isoformat`; raw provider dictionaries not in these serializers | Optional values remain `None` | [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L443-L473] [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L527-L558] [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L626-L653] |
| GIS coordinates | Both `WellInfo` and `PermitInfo` copy `geometry.y` into latitude and `geometry.x` into longitude | Four geometry requests supply no `outSR`; frame and angular units not established | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L224-L230] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L346-L352] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L398-L403] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L491-L497] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L264-L265] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L539-L540] |
| Depth and monetary fields | `total_depth`, `proposed_depth`, `bonus_per_acre`, `consideration`, `rental_rate` | Unqualified numeric fields copied/stored without a unit declaration | [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L64-L86] [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L203-L221] [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L505-L525] [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L606-L624] |
| County instructions | Markdown string | General instructions returned on lookup failures | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L430-L506] |

UNVERIFIED: Coordinate reference system, coordinate units, depth units, currency basis and dimensional consistency of remote responses are not established by the copied numeric fields; no coordinate origin, sign or phase convention is qualified for engineering use; see section 10, issue pending (1). [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L224-L276] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L491-L550] [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L203-L221]

## 3. Method and governing standards

No governing engineering standard is assigned here: the implemented checks are string patterns, ranges, enum/status rules and transport logic, rather than a standards-qualified engineering calculation. [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L70-L127] [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L218-L289] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/base.py:L238-L334]

| Method | Implementation and limit | Evidence |
|---|---|---|
| Legal-description recognition | Case-insensitive regex searches for section/block, PLSS, lot/block and survey terms; recognition alone is not a title or spatial proof | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L98-L127] |
| Normalization | Strip whitespace; regex substitution of abbreviations; state-code/name lookup | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L569-L626] |
| Record validation | Checks only populated fields; empty ownership and lease mappings produce no errors | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L445-L493] [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L505-L567] |
| Lease classification | `is_active` checks four enum states; `is_expired` checks explicit expired status or past date except HBP | [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L560-L576] |
| Aggregation | `OwnerSearchResult.__post_init__` sums list lengths; append methods increment total | [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L697-L705] [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L738-L751] |
| Cache | MD5 key hash, expiration, expired-first then oldest-created eviction; no content-integrity guarantee follows from the key | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/base.py:L68-L122] |
| HTTP | Cache GET by URL and sorted JSON params; 429 handling, exponential retry, typed transport failures; JSON decode errors become `ParsingError` | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/base.py:L238-L334] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/base.py:L336-L363] |
| GIS parsing | Aliases selected with `or`, rows without API/permit identifiers skipped, unknown well status becomes UNKNOWN | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L246-L313] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L512-L550] |
| Federal parsing | Identifier aliases, missing-ID skip, unknown claim/fluid types default to LODE/OIL_AND_GAS | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L246-L294] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L408-L452] |
| County lookup | Uppercase, suffix removal, then first substring match; nearby means other entries in the same state, not distance | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L391-L407] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L575-L592] |

No standards-derived constant is qualified by this pack, and no new calculation or `Citation` sidecar is introduced; numeric ranges above describe code behavior only. [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L218-L289]

## 4. Validated worked examples

Validated examples: **0**; independent-source qualification remains open as issue pending (2). The following **5 regression examples** use test-defined expectations rather than an external benchmark. [tests/unit/landman/test_models.py:L183-L191] [tests/unit/landman/test_providers_base.py:L79-L96] [tests/unit/landman/test_validators.py:L210-L226]

| Case | Inputs and source | Expected value; tolerance | Existing test node ID | Offline result |
|---|---|---|---|---|
| R1 typed-result count | Two in-memory well objects; test fixture | `returned_count=2`, serialized length 2 records; exact | `tests/unit/landman/test_models.py::TestWellSearchResult::test_with_wells` | PASS at BASE and AFTER |
| R2 cache hit ratio | Two hits and one miss; test fixture | `hit_rate="66.7%"`; exact string, rounded one decimal | `tests/unit/landman/test_providers_base.py::TestMemoryCache::test_hit_rate` | PASS at BASE and AFTER |
| R3 mineral upper bound | 101.0 percent; test fixture | False, 0 accepted out-of-range values; exact | `tests/unit/landman/test_validators.py::TestValidateMineralInterest::test_over_100` | PASS at BASE and AFTER |
| R4 active-state membership | Four enum states; test fixture | 4 true results; exact | `tests/unit/landman/test_models.py::TestLeaseRecord::test_is_active` | PASS at BASE and AFTER |
| R5 validator statistics | One valid and one invalid state record; test fixture | 2 validations, 1 error, success rate 0.5 dimensionless; exact | `tests/unit/landman/test_validators.py::TestGetStatistics::test_after_validations` | PASS at BASE and AFTER |

R1 expectation is defined in the two-object fixture, R2 in the three cache lookups, R3 in the rejected scalar, R4 in enum membership and R5 in the two calls; these are regression criteria, not proof of live-source completeness. [tests/unit/landman/test_models.py:L183-L191] [tests/unit/landman/test_providers_base.py:L89-L96] [tests/unit/landman/test_validators.py:L210-L213] [tests/unit/landman/test_models.py:L254-L270] [tests/unit/landman/test_validators.py:L563-L569]

Test record: ordinary `uv run python -m pytest tests/unit/landman tests/unit/field_development/test_landman.py -q -rA -p no:cacheprovider --basetemp=<scratch>` with coverage reports directed to scratch; BASE `2a97a58d6e81060ee2f1738150c2b4171f644c41`: 279 run / 279 passed / 0 failed / 0 skipped / 0 NOT_RUN; AFTER 279 run / 279 passed / 0 failed / 0 skipped / 0 NOT_RUN on the uncommitted documentation tree above BASE. Tests use the unchanged module code at the header pin; no addopts override or extra installation. `uv run python -m pytest tests/contracts -q -rA -p no:cacheprovider --basetemp=<scratch>`: BASE 46 run / 46 passed / 0 failed / 0 skipped / 0 NOT_RUN; AFTER 46 run / 46 passed / 0 failed / 0 skipped / 0 NOT_RUN on the same uncommitted tree. The routing registry is absent, so no routing-registry contract test exists. AFTER runs add the documented `--allow-existing-tree-changes` mode, which hashes existing edits and rejects mutations; the first AFTER invocation passed 279 tests but exited 1 because the default tree guard reported the pre-existing pack edit. [tests/conftest.py:L412-L460] [docs/development/index.md:L56-L59]

## 5. QA gates

Gate selection: AQG r0, section 10, Python calculations row; G5 applies to all families. The following criteria are pack-specific checks, not claims of independent clearance.

| Gate | Applicability | Check IDs and numeric pass criterion | Evidence |
|---|---|---|---|
| G0 inputs, units, citations | Applicable | C0a: `validate_mineral_interest(101.0)` returns False: 0 accepted out-of-range inputs; C0b: completeness audit records 0 unacknowledged unit/CRS gaps, with unresolved fields retained in section 10 | R3; input/output tables and open item O1; [tests/unit/landman/test_validators.py:L210-L213] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L224-L276] |
| G1 imports and tests | Applicable; Python import route only | C1a: `Landman()` creates an empty provider cache: 0 cached providers; C1b: focused tests have 0 failures and 0 collection errors, with every nonpass accounted for | `tests/unit/landman/test_landman.py::TestLandmanInit::test_providers_empty`; full focused result record; [tests/unit/landman/test_landman.py:L63-L74] |
| G2 hand or published check | Applicable | C2a: `MemoryCache.stats()` after 2 hits and 1 miss agrees with hand ratio 100 × 2/3 within 0.05 percentage point when printed as 66.7 percent | R2; arithmetic check of the explicit lookup count, no engineering calibration; [tests/unit/landman/test_providers_base.py:L89-L96] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/base.py:L128-L137] |
| G3 short dynamics | NOT_APPLICABLE | No time-integration model is produced by the router; no dynamics quantity exists to check | [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L136-L150] |
| G4 diffraction | NOT_APPLICABLE | No diffraction mesh or hydrodynamic result is produced by the router | [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L136-L150] |
| G5 evidence appendix | Applicable | C5a: evidence audit resolves 100 percent of code citations, records 6 gate rows, 5 example node IDs and 0 unexplained test outcomes | This pack's sections 4–6 and citation self-check; regression anchors [tests/unit/landman/test_landman.py:L63-L74] [tests/unit/landman/test_models.py:L183-L191] |

Acceptance checks: G0 **2**, G1 **2**, G2 **1**, G3 **0**, G4 **0**, G5 **1**; **6** total. Six additional defect-detection checks feed G0 (D4, D5) and G1 (D1–D3, D6), giving **12** defined checks overall: G0 **4**, G1 **6**, G2 **1**, G5 **1**. C0b acknowledges missing qualification; it does not qualify remote coordinates or data readiness.

Before any data consumer relies on acquisition, the following detection checks shall be applied; a detected defect is not a readiness pass.

| Detection ID | Executable inspection | Defect criterion and unit | Disposition |
|---|---|---|---|
| D1 | Inspect `Landman._get_provider` and enumerate provider files at the pin | 1 missing `county_records.py`; `ProviderError` has 0 `unavailable` factory definitions in its hierarchy | Existing routing defect; [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L251-L272] [packages/worldenergydata-landman/src/worldenergydata/landman/exceptions.py:L16-L46] |
| D2 | Inspect `_collect_data` exception branch and router status/count assignment | 1 error string can count as 1 record while status is completed | Existing routing defect; [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L136-L143] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L323-L327] |
| D3 | Inspect federal query exception branches, `_search_esri_wells`, `search_by_operator`, `search_permits` and custom-GIS implementation | 5 query branches suppress errors into empty results (2 federal, 3 state-GIS); 1 custom-GIS stub always returns an empty list | No live-completeness inference; [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L208-L244] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L370-L406] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L195-L237] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L339-L365] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L478-L510] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L281-L295] |
| D4 | Inspect the well-location, operator, well-detail and permit geometry requests and both parsers | 0 `outSR` declarations across 4 geometry requests; 4 coordinate assignments (y/x in 2 parsers) copied without transformation | Unit/CRS qualification gap; [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L224-L230] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L346-L352] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L398-L403] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L491-L497] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L264-L265] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L539-L540] |
| D5 | Compare record-validation branches with the empty-record tests | 2 empty mappings accepted, 0 mandatory populated-field checks | Callers require a schema/completeness check; [tests/unit/landman/test_validators.py:L449-L451] [tests/unit/landman/test_validators.py:L491-L493] |
| D6 | Parse the pinned `LandmanError.__init__` parameter names with Python `ast`; count `LandmanError`/`LandmanValidationError` calls in `landman.py` having keywords outside that set | 6 incompatible call sites (count), at lines 159, 176, 193, 201, 230 and 360; readiness requires 0 | Exception-constructor defect; [packages/worldenergydata-landman/src/worldenergydata/landman/exceptions.py:L22-L28] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L159-L179] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L193-L205] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L230-L233] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L360-L363] |

## 6. Known failure modes and pitfalls

| Symptom, cause and limit | Detection | Tracking and observation date |
|---|---|---|
| Five query branches (2 federal, 3 state-GIS) suppress transport/parser errors into empty results; custom GIS adds 1 stub returning no records without a query | D3; no existing end-to-end detection test is established | #913, #1256, 2026-10-15; [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L208-L244] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L370-L406] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L195-L237] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L339-L365] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L478-L510] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L281-L295] |
| `_search_esri_wells`, `search_by_operator` and `search_permits` catch exceptions, log warnings and expose empty results with counts of 0; `get_well_detail` and `BLMProvider.get_case_detail` instead mask transport errors as `RecordNotFoundError` | D3 detects the 3 suppressed queries; no detection check exists for detail-error masking | #1256, 2026-10-15; [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L195-L237] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L339-L365] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L478-L510] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L405-L416] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L480-L490] |
| Six exception calls pass `code=` or `context=` although `LandmanError.__init__` accepts `message, error_code, details, cause`; these calls raise `TypeError`, including the router catch-all wrapper reached by default `auto` after D1 | D6; no executable regression test exists in the focused suite | #1255, 2026-10-15; [packages/worldenergydata-landman/src/worldenergydata/landman/exceptions.py:L22-L28] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L152-L179] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L193-L205] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L230-L233] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L360-L363] |
| A caught collection error is stored as text, status is completed and the nonlist contributes 1 to record count | D2; no existing detection test in the focused suite | #924, 2026-10-15; [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L136-L143] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L323-L327] |
| Automatic routing selects an absent provider import; failure handling calls an unavailable factory absent from the imported exception class | D1; constants/init tests do not exercise provider acquisition | #924, 2026-10-15; [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L251-L288] [packages/worldenergydata-landman/src/worldenergydata/landman/exceptions.py:L16-L46] [tests/unit/landman/test_landman.py:L36-L74] |
| Coordinate labels are assigned from geometry without CRS negotiation; dimensional interpretation is not established | D4; no detection test exists | issue pending (1), 2026-10-15; [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L224-L276] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L491-L550] |
| Empty records pass validators; scalar float checks do not explicitly reject nonfinite values; a validator pass does not establish record completeness | D5 for empty records; no nonfinite detection test exists | #924, 2026-10-15; [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L232-L255] [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L445-L493] [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L505-L567] |
| Embedded online availability and advertised supported states do not prove current portal access or complete county coverage | Compare `SUPPORTED_STATES` with `COUNTY_DATA`; no live verification check exists | #914, 2026-10-15; [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L33-L50] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L361-L374] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L508-L523] |
| Freshness/fixture readiness can differ from status metadata; issue discussion describes work beyond the code present at this pin | Compare manifest and scorecard; no detection check for a packaged fixture is established at this pin | #928, 2026-10-15; [module-manifest.yaml:L236-L258] [docs/reports/data-freshness-scorecard-2026-06-08.md:L1-L14] |
| Importing errors from different namespaces produces different class identities; public aliases refer to `exceptions`, while `errors` defines a separate hierarchy | Inspect exact exception import before catching; no cross-hierarchy compatibility check exists | #924, 2026-10-15; [packages/worldenergydata-landman/src/worldenergydata/landman/__init__.py:L48-L64] [packages/worldenergydata-landman/src/worldenergydata/landman/errors.py:L31-L58] [packages/worldenergydata-landman/src/worldenergydata/landman/exceptions.py:L16-L46] |

## 7. Lessons log

| Date | Change reference | Lesson | Evidence | Pack change | Shared-log entry |
|---|---|---|---|---|---|
| 2026-10-15 | Initial pack revision 0 | Import/init tests alone cannot qualify provider acquisition | [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L251-L288] [tests/unit/landman/test_landman.py:L63-L74] | Separate routing defects from regression results | Not assigned; issue pending (2) |
| 2026-10-15 | Pack revision 1 | Match exception keywords to the constructor and distinguish failed acquisition from no matching records | #1255, #1256; [packages/worldenergydata-landman/src/worldenergydata/landman/exceptions.py:L22-L28] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L159-L163] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L232-L237] | Add D6 and extend D3 to state-GIS failures | Not assigned; issue pending (2) |

## 8. Ownership

| Responsibility | Assigned role or disposition |
|---|---|
| Family quality manager | Calculations quality manager, interim data-pipeline coverage |
| Deputy | Maintainer-appointed deputy; appointment remains open, issue pending (2) |
| Production | Documentation and data-pipeline contributors |
| Escalation | Unresolved criteria or evidence gaps go to the family quality manager; cross-family decisions go to the maintainers |
| Clearance | DRAFT until independent review by a different provider |

These are pack review assignments, not assertions of completed review.

## 9. Dependencies and implementation inventory

The package declares `worldenergydata-core`, `httpx`, `loguru` and `pydantic`; the direct provider classes use the common HTTP/cache base, and the exception hierarchies inherit `ModuleError`. [packages/worldenergydata-landman/pyproject.toml:L30-L35] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/base.py:L140-L181] [packages/worldenergydata-landman/src/worldenergydata/landman/exceptions.py:L13-L20]

The CLI calls the ownership and title routes and the direct county-reference provider; it is a consumer outside this pack's package boundary. [src/worldenergydata/cli/commands/landman.py:L144-L174] [src/worldenergydata/cli/commands/landman.py:L304-L323] [src/worldenergydata/cli/commands/landman.py:L395-L421]

The similarly named `field_development.landman.build_landman` assembles a lease-panel mapping and normalizes join keys; it is a separate implementation outside this package, rather than a provider wrapper. No dependency on this package is established by that implementation. [src/worldenergydata/field_development/landman.py:L23-L81]

### Map inventory

Map inspected: `digitalmodel`, `docs/registry/implementation-map.yaml` at map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, declared data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`.

Inventory observation: the pinned map declares `repository: digitalmodel` and covers digitalmodel only; all 13 map families were enumerated, and 0 implementation rows have a path inside the header package. The section-9 inventory is therefore empty, with 0 counted families. A8(c) is **NOT_APPLICABLE**, because no map family has an in-package implementation row; no regex signals are selected, dropped or counted. This is a map observation, not a claim that the package has no algorithms.

### Repository-wide supplementary search and map follow-up

A supplementary definition search covered tracked Python under the entire repository, including `scripts/`, for `validate_legal_description`, `validate_mineral_interest`, `validate_royalty_rate`, `_parse_esri_wells`, `_parse_mining_claims`, `build_landman`, `_make_request`, `is_expired`, `MemoryCache` and `Landman`. Supplementary hits do not change the empty counted-family inventory.

| Candidate | Classification and relationship | Evidence |
|---|---|---|
| `LandmanDataValidator` scalar/record methods | In-package implementation: legal-description recognition, normalization, numeric and date checks | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L70-L127] [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L218-L431] |
| Validator convenience functions | Delegating helpers, not additional implementations | [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L645-L664] |
| `CacheEntry`, `MemoryCache`, `BaseProvider` | In-package implementations: TTL cache, eviction, HTTP retry and JSON parsing | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/base.py:L31-L137] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/base.py:L238-L363] |
| `StateGISProvider` | In-package implementation: request construction, well/permit parsing and status/API-prefix mappings | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L202-L313] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L418-L448] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L512-L550] |
| `BLMProvider` | In-package implementation: claim/fluid parsing and enum mapping | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L246-L294] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L408-L452] |
| `CountyReferenceProvider` | In-package implementation: reference lookup, filtering and instruction generation | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L361-L506] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L525-L592] |
| `LeaseRecord`, `OwnerSearchResult` | In-package implementation: active/expired predicates and aggregation; serialization is a helper | [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L560-L576] [packages/worldenergydata-landman/src/worldenergydata/landman/models.py:L697-L759] |
| Router and search facades | Delegation and orchestration, with independent config checks and result counting documented in section 3 | [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L115-L150] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L165-L235] |
| Separate lease-panel builder | Out-of-package method/map gap, not an A8 miss | [src/worldenergydata/field_development/landman.py:L38-L81] |
| `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc` | Related out-of-package API-number handling: well, permit and GIS identifier normalizers compute their own comparison keys; landman queries Texas RRC ArcGIS well/permit services and derives states from API prefixes; map follow-up, not an A8 miss | [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L41-L47] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L418-L448] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/well_processor.py:L300-L314] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/permit_processor.py:L324-L338] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/gis_sources.py:L119-L139] |

Map follow-up, issue pending (2): add legal-description recognition/normalization, scalar and record validation, lease-state classification, result aggregation, cache/expiry/eviction, HTTP retry/cache/JSON handling, GIS/federal parsing and county-reference lookup families from section 3, then assign their in-package rows before a future counted-family audit; include related `texas_rrc` API-number handling in that follow-up. Shared HTTP/cache implementations in other domains require family-level reconciliation rather than automatic deduplication; no equivalence is established here.

## 10. Coverage and open items

### Reading inventory

All 11 Python source files in the package were read: `__init__.py`, `errors.py`, `exceptions.py`, `landman.py`, `models.py`, `validators.py`, and provider `__init__.py`, `base.py`, `blm.py`, `county_reference.py`, `state_gis.py`. Source scope is evidenced by the implementation and interface citations above.

The configuration `config/landman.yml` was also read. [config/landman.yml:L1-L7]

The package README and packaging metadata were read; no package-local tests folder was found. The focused test inventory comprises eight nonempty files: `tests/unit/landman/test_errors.py`, `test_exceptions.py`, `test_landman.py`, `test_models.py`, `test_providers_base.py`, `test_validators.py`, `providers/test_base.py` and `providers/test_county_reference.py`; the two empty test initializers were also read. The separate `tests/unit/field_development/test_landman.py` was read and run without copying identifying fixture values.

Documentation discovery under `docs/` found and inspected Landman passages in the following files; historical status/count claims are not promoted to current qualification:

- `docs/CLI.md`
- `docs/adr/0001-domain-package-split.md`
- `docs/ci/flake8-inventory-2026-04-23.md`
- `docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md`
- `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md`
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml`
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md`
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml`
- `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md`
- `docs/reports/cli-smoke-report-2026-05-11.json`
- `docs/reports/cli-smoke-report-2026-05-11.md`
- `docs/reports/data-freshness-scorecard-2026-06-08.md`

Discovery also found shared CLI, audit and site-link tests naming the module; these are not provider-validation evidence. The focused results in section 4 cover the package's unit-test directory and the separate lease-panel tests, not the whole repository.

### Open-item register

Each row assigns follow-up to the maintainers; draft numbers identify unpublished issue drafts awaiting issue creation.

| ID | Item and qualification boundary | Tracking |
|---|---|---|
| O1 | UNVERIFIED claim from section 2: CRS, coordinate/depth units and currency basis; engineering interpretation requires source-specific metadata and parser tests | issue pending (1) |
| O2 | Independent benchmark examples, map family registration, deputy appointment and shared-log/index registration remain open; no independent clearance is asserted | issue pending (2) |
| O3 | Existing package-data `**/*.md` glob includes nested Markdown; exclusion of this pack from a wheel is not established and requires a packaging change outside the documentation scope | issue pending (3); [packages/worldenergydata-landman/pyproject.toml:L50-L56] |
| O4 | Default-provider routing, truthful partial-failure status, exception-constructor keywords and complete/finite validation need executable regression coverage | #924, #1255; [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L251-L288] [packages/worldenergydata-landman/src/worldenergydata/landman/exceptions.py:L22-L28] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L159-L179] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L193-L205] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L230-L233] [packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:L360-L363] |
| O5 | Federal acquisition, source qualification and the federal/state-GIS error/empty distinction remain incomplete; detail lookups mask transport errors as missing records | #913, #1256; [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L235-L244] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L232-L237] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L354-L365] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L499-L510] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/state_gis.py:L405-L416] [packages/worldenergydata-landman/src/worldenergydata/landman/providers/blm.py:L480-L490] |
| O6 | County coverage and current portal access remain reference claims requiring source confirmation | #914; [packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_reference.py:L361-L374] |
| O7 | Fixture/freshness metadata and older documentation claims require reconciliation against their actual code revision, not issue-update assertions | #928; [module-manifest.yaml:L236-L258] |

Routing-registry disposition: `docs/registry/module-routing.yaml` is absent at the code pin; no registry file is created. The shared calculation-citation contract was available for reading; no licensed standard or private repository was read. No raw source records are included in this pack.
