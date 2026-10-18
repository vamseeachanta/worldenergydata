# Energy mix module knowledge pack

| Header | Value |
| --- | --- |
| Module | `energy_mix` |
| Repository | `worldenergydata` |
| Package path | `src/worldenergydata/energy_mix` |
| Pack revision | 0, 2026-10-18 |
| Code revision | `dff1a33208ac2eb3771997cb6fffbf762cfd010d` |
| Analysis family | EC; Python calculations gate set for a data pipeline (AQG r0, section 10, Python calculations) |
| Quality role | Calculations quality manager (Module agent lifecycle, revision 0, section 6, data-pipeline coverage recommendation) |
| Status | DRAFT |

## 1. Purpose and scope

The package validates caller-normalized offshore-wind country/year CSV observations and emits normalized CSV and provenance JSON; it does not calculate national energy shares or retrieve live observations. [src/worldenergydata/energy_mix/irena.py:L1-L5] [src/worldenergydata/energy_mix/irena.py:L36-L41] [src/worldenergydata/energy_mix/irena.py:L80-L119] [src/worldenergydata/energy_mix/irena.py:L157-L206]

The supported technology is exactly `offshore wind`; capacity is MW and generation is GWh, and at least one measurement must be present in each row. [src/worldenergydata/energy_mix/irena.py:L68-L77] [src/worldenergydata/energy_mix/irena.py:L80-L85]

The normalized schema is a repository contract, not an established native source export format; format validation does not establish source accuracy, reuse rights or engineering readiness. [src/worldenergydata/energy_mix/irena.py:L1-L5] [src/worldenergydata/energy_mix/irena.py:L165-L168] [src/worldenergydata/energy_mix/irena.py:L195-L199] [docs/data/irena_offshore_wind.md:L94-L100]

## 2. Inputs and outputs

### Inputs

| Name | Unit | Range or convention | Default | Source and evidence |
| --- | --- | --- | --- | --- |
| `raw` | bytes | At most 5,000,000 bytes; UTF-8 with optional BOM; exactly ordered `COLUMNS` header | Required | Caller bytes; [src/worldenergydata/energy_mix/irena.py:L19-L29] [src/worldenergydata/energy_mix/irena.py:L80-L92] |
| `country`, `citation` | text | Nonempty; surrounding whitespace rejected for every field | Required | CSV fields; [src/worldenergydata/energy_mix/irena.py:L53-L59] |
| `iso_code` | text | Blank or three uppercase letters; no registry lookup | Blank accepted | CSV field; [src/worldenergydata/energy_mix/irena.py:L60-L62] [docs/data/irena_offshore_wind.md:L52-L56] |
| `year` | calendar year | Four ASCII digits; 1960 through current UTC year | Required | CSV field and UTC clock; [src/worldenergydata/energy_mix/irena.py:L63-L67] [src/worldenergydata/energy_mix/irena.py:L97-L99] |
| `technology` | text | Exact literal `offshore wind` | Required | CSV field; [src/worldenergydata/energy_mix/irena.py:L68-L69] |
| `capacity_mw` | MW | Blank or finite nonnegative Python float text | Blank becomes `None` | CSV field; [src/worldenergydata/energy_mix/irena.py:L44-L50] [src/worldenergydata/energy_mix/irena.py:L73-L77] |
| `generation_gwh` | GWh | Blank or finite nonnegative Python float text | Blank becomes `None` | CSV field; [src/worldenergydata/energy_mix/irena.py:L44-L50] [src/worldenergydata/energy_mix/irena.py:L73-L77] |
| `source_url` | URL | HTTPS, nonempty netloc, no embedded credentials; hostname caveat in section 6 | Required | CSV field; [src/worldenergydata/energy_mix/irena.py:L70-L72] |
| `synthetic` | boolean | Marks authored test data | `False` | `emit_manifest` keyword or CLI flag; [src/worldenergydata/energy_mix/irena.py:L157-L168] [src/worldenergydata/energy_mix/__main__.py:L17-L24] |
| `retrieved_at_utc`, `terms_quote`, `terms_url` | UTC timestamp; text; URL | Required for real exports; timestamp has zero UTC offset and is not future; terms URL has HTTPS hostname and no credentials | `None`; synthetic mode bypasses these checks | Caller provenance; [src/worldenergydata/energy_mix/irena.py:L133-L154] [src/worldenergydata/energy_mix/irena.py:L157-L164] |
| CLI paths | path | Input and manifest required for load; output optional; resolved paths distinct; destinations must not exist | No paths | Caller arguments; [src/worldenergydata/energy_mix/__main__.py:L17-L39] |

### Outputs

| Name | Unit or encoding | Content and convention | Evidence |
| --- | --- | --- | --- |
| `load_export` result | List of dictionaries | Integer year, float-or-`None` measurements; supplied text retained; casefolded country/year uniqueness and country/code consistency | [src/worldenergydata/energy_mix/irena.py:L77-L119] |
| `write_table` result | UTF-8 CSV bytes; LF records | Same ordered header; revalidated before return; no conversion between MW, GWh or other units | [src/worldenergydata/energy_mix/irena.py:L122-L130] [docs/data/irena_offshore_wind.md:L55-L60] |
| `emit_manifest` result | UTF-8 JSON bytes; final LF | Schema version 1; dataset ID `irena-offshore-wind-normalized`; sorted unique source URLs and citations; raw-input SHA-256, bytes, rows, units and readiness | [src/worldenergydata/energy_mix/irena.py:L169-L206] |
| CLI files | CSV and JSON bytes | Optional normalized CSV and required manifest; manifest digest covers original input bytes, not normalized CSV bytes | [src/worldenergydata/energy_mix/__main__.py:L38-L52] [src/worldenergydata/energy_mix/irena.py:L191-L194] |

The contract has country/year keys and measurement columns rather than spatial coordinates, phases or force signs; measurements are constrained nonnegative and blank is distinct from reported zero. [src/worldenergydata/energy_mix/irena.py:L19-L28] [src/worldenergydata/energy_mix/irena.py:L44-L50] [tests/unit/energy_mix/test_irena.py:L43-L51]

## 3. Method and governing standards

| Method | Definition and implementation | Reference or limit |
| --- | --- | --- |
| Measurement parsing | `_measurement` maps empty text to `None`, otherwise calls `float`, then rejects nonfinite or negative numbers | Repository policy; separator caveat in section 6; [src/worldenergydata/energy_mix/irena.py:L44-L50] |
| Row validation | `_validate_row` rejects width/whitespace/key/year/technology/URL violations and converts the year and measurements | Repository policy, not a source specification; [src/worldenergydata/energy_mix/irena.py:L53-L77] |
| Table validation | `load_export` uses strict `csv.DictReader`, exact header comparison, casefolded country keys and sets for duplicates; empty tables raise | No aggregation, imputation or unit conversion in this algorithm; [src/worldenergydata/energy_mix/irena.py:L80-L119] |
| Serialization | `write_table` writes the contract header and rows, then invokes `load_export` on the result | Delegates validation; [src/worldenergydata/energy_mix/irena.py:L122-L130] |
| Provenance | `_validate_provenance` checks presence, UTC offset, future timestamps and terms-URL syntax; `emit_manifest` hashes original bytes and emits sorted JSON | Caller assertions remain unverified; [src/worldenergydata/energy_mix/irena.py:L133-L206] |
| CLI orchestration | `main` parses paths, rejects collisions/existing destinations, bounds the read and writes files in exclusive creation mode | CSV is written before manifest; [src/worldenergydata/energy_mix/__main__.py:L15-L52] |
| Live access | `fetch_irena` raises `AccessRefused` without a transport call | Historical access refusal is recorded in code, not a current source probe; [src/worldenergydata/energy_mix/irena.py:L32-L41] |

No standards-derived engineering formula is implemented in these validation and serialization paths; the capacity/generation units and year limits are repository policies, so no standards `Citation` sidecar is emitted by these paths. [src/worldenergydata/energy_mix/irena.py:L44-L119] [src/worldenergydata/energy_mix/irena.py:L122-L206]

## 4. Validated worked examples

Validated examples: 0; the observations are explicitly synthetic and the manifest is generated by this module, so these cases are regression evidence rather than independent source validation. [tests/unit/energy_mix/test_irena.py:L1-L1] [docs/data/irena_offshore_wind.md:L83-L92]

The following four regression cases ran PASS at the code pin both before and after the documentation change; the complete offline command collected 38 cases from 19 test functions, with 38 passed, 0 failed, 0 skipped and 0 NOT_RUN on each run. [tests/unit/energy_mix/test_irena.py:L43-L274]

| Case | Input and expected result | Tolerance and basis | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| CSV round trip | Synthetic CSV; first record 10.5 MW and 20.25 GWh; explicit 0 MW retained and blanks remain `None`; serialized records equal loaded records | 0 MW and 0 GWh absolute difference; exact fixture assertions | `tests/unit/energy_mix/test_irena.py::test_load_and_round_trip` | PASS / PASS; [tests/unit/energy_mix/test_irena.py:L43-L51] [tests/fixtures/energy_mix/irena_offshore_synthetic.csv:L1-L4] |
| Manifest reproduction | Same CSV; manifest equals the committed synthetic JSON byte for byte | 0 differing bytes; snapshot basis | `tests/unit/energy_mix/test_irena.py::test_manifest_reproduction` | PASS / PASS; [tests/unit/energy_mix/test_irena.py:L111-L114] [tests/fixtures/energy_mix/irena_offshore_synthetic.manifest.json:L1-L28] |
| CLI preservation | Same CSV, two fresh temporary destinations; manifest matches emitter, CSV matches loaded input, input unchanged, repeat invocation raises | 0 changed input bytes; 0 record differences | `tests/unit/energy_mix/test_irena.py::test_cli_manifest_and_input_preservation` | PASS / PASS; [tests/unit/energy_mix/test_irena.py:L166-L195] |
| Offline fetch refusal | No input data; `fetch_irena` raises `AccessRefused` while network transports are blocked | 1 expected exception, 0 network connections | `tests/unit/energy_mix/test_irena.py::test_fetch_refuses_without_network` | PASS / PASS; [tests/unit/energy_mix/test_irena.py:L23-L30] [tests/unit/energy_mix/test_irena.py:L122-L124] |

Execution form: `uv run python -m pytest tests/unit/energy_mix -q -rA -p no:cacheprovider --noconftest --basetemp=<scratch>` with `PYTHONPATH` containing repository source and the dependency source checkout; coverage data and all coverage reports were directed to scratch, with repository `addopts` retained and no source-resolution fallback. [AGENTS.md:L3-L6] [tests/unit/energy_mix/test_irena.py:L23-L30]

## 5. QA gates

The gate set below applies the Python calculations row, including G5; criteria are maintenance checks for this pipeline, not a claim that source observations or rights have been verified (AQG r0, sections 9–10). [docs/data/irena_offshore_wind.md:L75-L81]

| Gate | Applicability and reason | Check IDs |
| --- | --- | --- |
| G0 | Applicable: exact schema, declared units, keys and provenance inputs | `input-schema`, `input-keys`, `input-provenance` |
| G1 | Applicable: import and exercise the Python loader, emitter and CLI offline | `load-offline`, `output-safety` |
| G2 | Applicable: compare parsed measurements with explicit fixture literals; independent engineering-value evidence remains open under #1326 | `reference-fixture` |
| G3 | NOT_APPLICABLE: no dynamics simulation in the processing path | [src/worldenergydata/energy_mix/irena.py:L80-L130] [src/worldenergydata/energy_mix/__main__.py:L38-L52] |
| G4 | NOT_APPLICABLE: no mesh or diffraction body in the input/output contract | [src/worldenergydata/energy_mix/irena.py:L19-L28] [src/worldenergydata/energy_mix/irena.py:L171-L203] |
| G5 | Applicable: retain manifest integrity, provenance and test evidence with outputs | `evidence-manifest` |

| Check ID | Gate | Executable check and numeric pass criterion | Evidence and current coverage |
| --- | --- | --- | --- |
| `input-schema` | G0 | Run `test_invalid_values`, `test_changed_header`, `test_empty_table`, `test_extra_cell`, `test_missing_measurements`; 20 invalid cases rejected, 0 accepted invalid rows, unit: cases | Covers negative/nonfinite measurements, year syntax/range and exact headers; [tests/unit/energy_mix/test_irena.py:L54-L108] |
| `input-keys` | G0 | Run `test_duplicate_country_year`, `test_country_key_consistency`, `test_iso_code_collision`, `test_country_key_case_consistency`; 4 invalid tables rejected, 0 inconsistent keys, unit: tables | Casefold and ISO collision checks; [tests/unit/energy_mix/test_irena.py:L83-L91] [tests/unit/energy_mix/test_irena.py:L127-L131] [tests/unit/energy_mix/test_irena.py:L222-L227] |
| `input-provenance` | G0 | Run `test_manifest_requires_synthetic_or_provenance`, `test_manifest_rejects_non_utc_or_future`, `test_manifest_rejects_unusable_terms`; 7 invalid submissions rejected, 0 accepted, unit: submissions | Presence, timestamp and terms syntax, not source truth; [tests/unit/energy_mix/test_irena.py:L117-L119] [tests/unit/energy_mix/test_irena.py:L153-L163] [tests/unit/energy_mix/test_irena.py:L230-L245] |
| `load-offline` | G1 | Run all module tests with their autouse transport guard; 38 passed, 0 failed, 0 skipped, 0 network calls, unit: cases/calls | Includes imports, CSV serialization, provenance and CLI; [tests/unit/energy_mix/test_irena.py:L11-L30] [tests/unit/energy_mix/test_irena.py:L43-L274] |
| `output-safety` | G1 | Run `test_cli_manifest_and_input_preservation`, `test_cli_rejects_input_overwrite`, `test_cli_existing_manifest_creates_no_output`; 3 passed and 0 changed input/existing-manifest bytes, unit: cases/bytes | Does not exercise failure between the two destination writes; [tests/unit/energy_mix/test_irena.py:L166-L219] [tests/unit/energy_mix/test_irena.py:L248-L274] |
| `reference-fixture` | G2 | Read the CSV literal independently of the loader; compare `test_load_and_round_trip` assertions with 10.5 MW, 20.25 GWh, 0 MW and unavailable cells; 0 MW/GWh absolute error and 0 missingness mismatches | Regression check only; no GWh-to-MWh calculation or independent real-source example; [tests/fixtures/energy_mix/irena_offshore_synthetic.csv:L1-L4] [tests/unit/energy_mix/test_irena.py:L43-L51] |
| `evidence-manifest` | G5 | Run `test_manifest_reproduction` and `test_manifest_real_provenance`; 0 snapshot byte differences, 0 digest mismatches, 0 byte-count differences; independently hash the 438-byte, 3-row fixture and compare manifest | Retains source citations, original-input digest, units and synthetic limitation; [tests/unit/energy_mix/test_irena.py:L111-L114] [tests/unit/energy_mix/test_irena.py:L134-L150] [tests/fixtures/energy_mix/irena_offshore_synthetic.manifest.json:L1-L28] |

Short test names in this table refer to definitions in `tests/unit/energy_mix/test_irena.py`; section 10 enumerates all full node IDs. [tests/unit/energy_mix/test_irena.py:L43-L274]

## 6. Known failure modes and pitfalls

sweep: 14 found

Sweep command: `rg -n 'except|continue|return None|return \[\]|return \{\}|= 0(\.0)?\b|1970|0\.05|int\(|float\(|MW|GWh|cache' src/worldenergydata/energy_mix --glob '*.py'`; all three Python files were also read for indirect record skipping, provenance defaults and output-write ordering. [src/worldenergydata/energy_mix/__init__.py:L1-L1] [src/worldenergydata/energy_mix/irena.py:L1-L206] [src/worldenergydata/energy_mix/__main__.py:L1-L56]

The fourteen rows include intentional sentinel/default policies as pitfalls; there are no package `except` handlers, explicit `continue` statements, error-path empty-container returns, fallback zero/epoch/percentage defaults or cache writers; the zero-offset comparison is a UTC check, not a fallback. [src/worldenergydata/energy_mix/irena.py:L44-L206] [src/worldenergydata/energy_mix/__main__.py:L15-L56]

| ID | Symptom and cause at the pin | Detection check or gap | Incident or follow-up; date |
| --- | --- | --- | --- |
| s01 | Blank measurement silently becomes `None`, while zero remains a numeric value; intentional missingness policy. [src/worldenergydata/energy_mix/irena.py:L44-L50] | `reference-fixture` checks both sentinel and zero | Policy evidence; [tests/unit/energy_mix/test_irena.py:L43-L51]; 2026-10-18 |
| s02 | `float(value)` accepts Python underscore numeric spelling but rejects comma grouping/decimal commas; locale normalization is absent. [src/worldenergydata/energy_mix/irena.py:L44-L50] | No detection check exists for separator/underscore grammar | issue pending (1); 2026-10-18 |
| s03 | `int(row["year"])` follows a four-ASCII-digit check; range uses a current-UTC-year ceiling rather than a pinned dataset vintage. [src/worldenergydata/energy_mix/irena.py:L63-L67] [src/worldenergydata/energy_mix/irena.py:L97-L99] | `input-schema` rejects fractional, old and future year examples | Policy evidence; [tests/unit/energy_mix/test_irena.py:L60-L62]; 2026-10-18 |
| s04 | Capacity is assumed MW from header spelling; there is no physical unit inference or conversion. [src/worldenergydata/energy_mix/irena.py:L73-L84] | `input-schema` rejects changed capacity-unit headers; `reference-fixture` checks supplied MW | Conversion coverage: #1326; [tests/unit/energy_mix/test_irena.py:L77-L80]; 2026-10-18 |
| s05 | Generation is assumed GWh and manifest repeats GWh; falsely labelled source values cannot be detected by syntax validation. [src/worldenergydata/energy_mix/irena.py:L73-L84] [src/worldenergydata/energy_mix/irena.py:L194-L199] | `reference-fixture` checks supplied GWh; no detection check exists for external unit truth | #1095, #1326; 2026-10-18 |
| s06 | `csv.DictReader` can omit wholly blank lines before record validation; no rejected-line counter is emitted by `load_export`. [src/worldenergydata/energy_mix/irena.py:L88-L99] [src/worldenergydata/energy_mix/irena.py:L115-L119] | No detection check exists for blank-line accounting | issue pending (1); 2026-10-18 |
| s07 | Empty ISO text is retained and skips the reverse-code map; alpha-3 syntax does not prove registry membership. [src/worldenergydata/energy_mix/irena.py:L60-L62] [src/worldenergydata/energy_mix/irena.py:L100-L111] | `reference-fixture` checks blank retention; `input-keys` checks collisions; no membership check exists | Intended policy; [docs/data/irena_offshore_wind.md:L43-L56]; 2026-10-18 |
| s08 | Default `synthetic=False` and absent provenance keywords require rejection; no retrieval time or terms are inferred for real data. [src/worldenergydata/energy_mix/irena.py:L139-L154] [src/worldenergydata/energy_mix/irena.py:L157-L170] | `input-provenance` checks missing/invalid real provenance | Policy evidence; [tests/unit/energy_mix/test_irena.py:L117-L119]; 2026-10-18 |
| s09 | Synthetic mode bypasses provenance validation and replaces retrieval time/terms URL with `None` and terms quote with fixture text, even if supplied. [src/worldenergydata/energy_mix/irena.py:L139-L143] [src/worldenergydata/energy_mix/irena.py:L174-L189] | `evidence-manifest` checks default synthetic output; no detection check exists for supplied provenance discarded in synthetic mode | issue pending (1); 2026-10-18 |
| s10 | Source URL validation checks netloc rather than hostname; a hostname-free authority with a port passes. [src/worldenergydata/energy_mix/irena.py:L70-L72] | No detection check exists for malformed HTTPS authority | issue pending (2); 2026-10-18 |
| s11 | Nonempty citations and provenance quotes are caller assertions; source authenticity and permissions are not checked. [src/worldenergydata/energy_mix/irena.py:L58-L59] [src/worldenergydata/energy_mix/irena.py:L165-L168] [src/worldenergydata/energy_mix/irena.py:L195-L199] | `input-provenance` covers shape only; no detection check exists for truth or rights | #1095; 2026-10-18 |
| s12 | Manifest `live_access` contains a historical refusal for every export, including synthetic data; it is not a fresh network observation. [src/worldenergydata/energy_mix/irena.py:L200-L202] | `evidence-manifest` snapshots the string; `load-offline` checks refusal; no current-access check exists | #1095; [tests/unit/energy_mix/test_irena.py:L111-L124]; 2026-10-18 |
| s13 | Manifest SHA-256 describes original input bytes; normalization can change CSV bytes, so hashing the output CSV against it is the wrong comparison. [src/worldenergydata/energy_mix/__main__.py:L38-L52] [src/worldenergydata/energy_mix/irena.py:L191-L194] | `evidence-manifest` compares with input hash; `output-safety` compares records | Policy evidence; [tests/unit/energy_mix/test_irena.py:L146-L150] [tests/unit/energy_mix/test_irena.py:L189-L195]; 2026-10-18 |
| s14 | CLI creates optional CSV before manifest; a later manifest write failure can leave CSV without provenance, despite prechecking existing paths. [src/worldenergydata/energy_mix/__main__.py:L35-L52] | No detection check exists for a failure between writes; `output-safety` covers only preexisting destinations | issue pending (3); 2026-10-18 |

No incident issue was supplied for this package; repository issue discovery found the source-integration gap #1095 and the independent-value coverage gap #1326, associated here with `load-offline` and `reference-fixture` respectively; neither check establishes live-source correctness. [docs/data/irena_offshore_wind.md:L3-L6] [docs/data/irena_offshore_wind.md:L94-L100] [tests/unit/energy_mix/test_irena.py:L43-L51] [tests/unit/energy_mix/test_irena.py:L122-L124]

## 7. Lessons log

| Date | Entry | Lesson and evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-18 | Initial documentation | Format preservation and snapshot equality establish regression behavior; they do not establish source truth or reuse permission. [tests/unit/energy_mix/test_irena.py:L43-L51] [tests/unit/energy_mix/test_irena.py:L111-L114] [docs/data/irena_offshore_wind.md:L75-L81] | Separate regression examples from independent validation in sections 4–5 | Not assigned; issue pending (5) |

## 8. Ownership

Review route: calculations quality manager for this data pipeline, with independent-provider review before clearance; maintenance and unresolved coverage questions go to the maintainer (Module agent lifecycle, revision 0, sections 3–4 and 6; AQG r0, section 11).

UNVERIFIED: a deputy quality manager and shared-log entry have not been established in the inspected module evidence; maintainer assignment and review completion remain issue pending (5).

## 9. Dependencies and implementation inventory

The runtime processing paths use Python standard-library CSV, hashing, JSON, time, URL, argument and filesystem utilities; the CLI delegates to the loader/emitter and writes caller-selected destinations. [src/worldenergydata/energy_mix/irena.py:L7-L15] [src/worldenergydata/energy_mix/irena.py:L80-L119] [src/worldenergydata/energy_mix/irena.py:L169-L206] [src/worldenergydata/energy_mix/__main__.py:L3-L12] [src/worldenergydata/energy_mix/__main__.py:L38-L52]

The only dataset demonstrated by the tests is the authored synthetic fixture for dataset ID `irena-offshore-wind-normalized`; its committed manifest records 3 rows and 438 original bytes, MW/GWh units and synthetic-only readiness. [tests/unit/energy_mix/test_irena.py:L19-L20] [tests/unit/energy_mix/test_irena.py:L111-L114] [tests/fixtures/energy_mix/irena_offshore_synthetic.manifest.json:L5-L26]

The implementation map was read at map commit `3256bab95f84da3d9fadce8d5dcf8458d66d1eb4`, data revision `270c8759c374b67a7f032953e7fcdb14e0224461`; none of its 13 families has an implementation row whose path is inside this package (digitalmodel, Implementation map, schema version 1, named map commit, `families[].implementations[].path`).

| Inventory | In-package families | Listed implementations | Counted-family grep |
| --- | --- | --- | --- |
| Empty | 0 | 0 | NOT_APPLICABLE: no map family has a row inside the package (digitalmodel, Implementation map, schema version 1, named map commit, `families[].implementations[].path`) |

Map follow-up: add the section-3 normalized CSV/schema/key-validation, provenance-manifest and fail-closed access method families; these are uncounted until the map holds in-package rows, issue pending (4). [src/worldenergydata/energy_mix/irena.py:L36-L119] [src/worldenergydata/energy_mix/irena.py:L133-L206]

Whole-repository discovery, including `scripts/`, used `git grep -n -I -E 'energy_mix|irena|energy-mix' dff1a33208ac2eb3771997cb6fffbf762cfd010d --` across all tracked files; the CLI and tests delegate to the listed definitions, while a dashboard document contains a placeholder fetch method and a separate illustrative data-frame harmonizer rather than a second implementation of this normalized CSV contract. [src/worldenergydata/energy_mix/__main__.py:L38-L52] [tests/unit/energy_mix/test_irena.py:L11-L17] [docs/modules/dashboard/implementation-guides/full-stack-guide.md:L408-L422]

No downstream computational consumer is asserted by this pack; the documented workflow consumes user-supplied normalized CSV and writes a table/manifest pair. [docs/data/irena_offshore_wind.md:L58-L88]

## 10. Coverage and open items

### Evidence read

All three package Python files, the complete test file, both synthetic fixtures and the module-specific document were read; the broader dashboard document was inspected at its source-integration example. [src/worldenergydata/energy_mix/__init__.py:L1-L1] [src/worldenergydata/energy_mix/__main__.py:L1-L56] [src/worldenergydata/energy_mix/irena.py:L1-L206] [tests/unit/energy_mix/test_irena.py:L1-L274] [tests/fixtures/energy_mix/irena_offshore_synthetic.csv:L1-L4] [tests/fixtures/energy_mix/irena_offshore_synthetic.manifest.json:L1-L28] [docs/data/irena_offshore_wind.md:L1-L100] [docs/modules/dashboard/implementation-guides/full-stack-guide.md:L383-L422]

Module-name discovery under `docs/` found `docs/data/irena_offshore_wind.md`; package documentation is this initial pack, and the package has no nested implementation subpackages at the pin. [docs/data/irena_offshore_wind.md:L4-L6] [src/worldenergydata/energy_mix/__init__.py:L1-L1] [src/worldenergydata/energy_mix/irena.py:L1-L206] [src/worldenergydata/energy_mix/__main__.py:L1-L56]

### Complete test inventory

Each row below ran offline at the code pin before and after this documentation change; parameter groups report collected-case counts. [tests/unit/energy_mix/test_irena.py:L43-L274]

| Test node ID | Cases | BASE / after |
| --- | --- | --- |
| `tests/unit/energy_mix/test_irena.py::test_load_and_round_trip` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_invalid_values` | 13 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_changed_header` | 3 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_duplicate_country_year` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_country_key_consistency` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_empty_table` | 2 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_extra_cell` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_missing_measurements` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_manifest_reproduction` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_manifest_requires_synthetic_or_provenance` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_fetch_refuses_without_network` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_iso_code_collision` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_manifest_real_provenance` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_manifest_rejects_non_utc_or_future` | 3 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_cli_manifest_and_input_preservation` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_cli_rejects_input_overwrite` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_country_key_case_consistency` | 1 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_manifest_rejects_unusable_terms` | 3 | PASS / PASS |
| `tests/unit/energy_mix/test_irena.py::test_cli_existing_manifest_creates_no_output` | 1 | PASS / PASS |

### Open items

UNVERIFIED: native export headers, observation accuracy, current permitted access and source reuse rights are not established by the offline evidence; the existing document records those limits and the historical refusal rather than a successful extraction, #1095. [docs/data/irena_offshore_wind.md:L8-L30] [docs/data/irena_offshore_wind.md:L94-L100]

| Item | Coverage limit or next action | Maintainer tracking |
| --- | --- | --- |
| Source evidence | Obtain a permitted export, verify native schema, source units, country keys and reuse rights; no current source probe was made. [docs/data/irena_offshore_wind.md:L94-L100] | #1095 |
| Independent validation | No independently sourced engineering-value example; the current check preserves literals and does not calculate GWh-to-MWh conversion. [tests/unit/energy_mix/test_irena.py:L43-L51] | #1326 |
| Parser policies | Add separator, underscore, blank-line and supplied-synthetic-provenance assertions for s02, s06 and s09. [src/worldenergydata/energy_mix/irena.py:L44-L50] [src/worldenergydata/energy_mix/irena.py:L88-L99] [src/worldenergydata/energy_mix/irena.py:L174-L189] | issue pending (1) |
| Source URL validity | Add hostname/authority validation and rejection tests for s10. [src/worldenergydata/energy_mix/irena.py:L70-L72] | issue pending (2) |
| Paired output failure | Specify and test the failure contract between CSV and manifest writes for s14. [src/worldenergydata/energy_mix/__main__.py:L48-L52] | issue pending (3) |
| Map follow-up | Add the section-3 method families and rerun the counted-family audit after they have in-package rows. [src/worldenergydata/energy_mix/irena.py:L36-L206] | issue pending (4) |
| Review coverage | Establish deputy/shared-log coverage, open numbered drafts, replace draft references and complete independent review (Module agent lifecycle, revision 0, sections 3–4; AQG r0, section 11). | issue pending (5) |

The pack remains DRAFT; test success and citation resolution are production evidence for this documentation, not independent quality clearance (AQG r0, section 11).
