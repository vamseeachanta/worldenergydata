# Reporting module knowledge pack

| Header | Value |
| --- | --- |
| Module | `reporting` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-reporting/src/worldenergydata/reporting` |
| Pack revision | 1, 2026-10-16 |
| Code revision | `02d6b17c5757852649b27a3191d1d9e736492ba2` |
| Analysis family | Data pipeline; QA family EC; AQG r0 Python calculations gate set |
| Quality role | Calculations quality manager, pending a dedicated data quality role |
| Status | DRAFT; independent clearance pending |

Header roles and gate applicability are the review assignments adopted for this pack; they do not record completed clearance.

## 1. Purpose and scope

The public API exposes `export_report` and `ExportManifest`; the implementation serializes a result object's data and summary into selected formats and records each format's outcome. [packages/worldenergydata-reporting/src/worldenergydata/reporting/__init__.py:L5-L7] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L168-L248]

`PlotlyReportGenerator` accumulates figures and summary labels, then writes an HTML document containing figure JSON and JavaScript plot calls. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L24-L48] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L348-L398]

The utility layer constructs data/report paths and relative links; it is separate from export dispatch and the template's output-path handling. [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L18-L138] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L210-L239] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L393-L396]

Scope includes both subpackages, `templates` and `utils`, and all export writers; the example under the template's main guard is random sample generation, not an independent benchmark. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L44-L158] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L401-L434]

Distribution metadata declares Alpha and Python 3.10 or later; this is a metadata declaration rather than evidence of engineering validation. [packages/worldenergydata-reporting/pyproject.toml:L5-L23]

UNVERIFIED: numerical validation across arbitrary caller datasets and browser compatibility are not established by this pack; open item O4.

### Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-16 | Initial source-pinned export, plotting and path knowledge pack. |
| 1 | 2026-10-16 | Record the package sweep, seven missing output risks and their coverage gaps; retain separate correction drafts. |

## 2. Inputs and outputs

### Inputs

| Name | Unit | Allowed range or type | Default | Source and evidence |
| --- | --- | --- | --- | --- |
| `result.data` | Caller-defined column units; no conversion | pandas DataFrame; other types become empty frames | Empty DataFrame when absent | `export_report` normalization. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L204-L208] |
| `result.summary` | Caller-defined values and units | Mapping expected by writers; no explicit schema check | Empty dict when absent or false-like | Summary normalization and serialization. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L51-L54] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L74-L80] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L204-L208] |
| `formats` | Format tokens, dimensionless | `xlsx`, `parquet`, `csv`, `json`, `pdf`; unknown tokens recorded as failures | `xlsx`, `parquet` | Dispatch and format filter. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L19-L19] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L165-L165] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L220-L239] |
| `output_dir`, `filename_prefix` | Filesystem paths and filename stem | Joined without confinement validation; directory created before per-format exception handling | `DEFAULT_OUTPUT_DIR`; lowercase result class name | Explicit output directories should be supplied; the literal default is intentionally omitted here. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L197-L212] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L227-L239] |
| Plot DataFrame, `x`, `y`, `color`, `size` | Caller-defined axis/column units | Column names passed to Plotly Express | `color=None`, `size=None` where supported | Plot methods. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L50-L147] |
| Histogram `column`, `nbins` | Column units; bin count | Passed to Plotly; no module range validation | 30 bins | Histogram method. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L149-L168] |
| Heatmap DataFrame | Correlation dimensionless | Numeric columns selected; pandas correlation used | No input default | Heatmap method. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L170-L202] |
| `title`, `module_name`, `repository_name`; stat label/value/unit | Text; stat unit is display text | Stored as supplied and interpolated into HTML | Empty stat unit | Constructor and summary rendering. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L24-L48] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L339-L355] |
| `filename`, `data_type`, `subfolder` | Filesystem components | `raw`, `processed`, `results` for data type; other components not validated | `processed`; empty subfolder | Path helpers. [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L31-L89] |

### Outputs

| Name | Unit or representation | Contents and limits | Evidence |
| --- | --- | --- | --- |
| `ExportManifest` | Strings, lists, mappings | Output directory, files, requested/succeeded/failed formats, UTC ISO timestamp | Fields and construction. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L27-L36] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L214-L248] |
| XLSX | Caller column units | `data` sheet without index; `summary` sheet with key/value columns | `_write_xlsx`. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L44-L56] |
| Parquet | Caller column units | DataFrame without index; pyarrow first, then pandas default engine after an exception | `_write_parquet`. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L59-L65] |
| CSV | Caller column units | DataFrame without index; writer defaults otherwise retained | `_write_csv`. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L68-L71] |
| JSON | Records and summary object | `data` is records; summary retained; otherwise unsupported JSON values stringify | `_write_json`. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L74-L81] |
| Requested `pdf` | HTML, not a PDF document | `.html` file and `html_report` manifest key; table shows at most 200 rows while heading reports full row count | HTML writer and format maps. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L84-L121] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L128-L138] |
| Template HTML | UTF-8 | Figure JSON embedded; external Plotly JavaScript reference; output parent created | Template writer. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L221-L227] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L377-L396] |
| Data/report paths and relative links | Path objects / string | Fixed ancestor root; relative-link fallback builds upward components and target suffix | Utility implementations. [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L18-L74] [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L115-L138] |

No geometry frame, origin, sign or phase transform is defined by these serializer and plotting operations; physical conventions remain the caller's responsibility. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L44-L81] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L50-L202]

## 3. Method and governing standards

| Method | Implementation | Governing reference and limits |
| --- | --- | --- |
| Independent format dispatch | `_dispatch`, `export_report` | Each supported writer is tried separately; failures are captured rather than raised by the writer loop. Directory creation occurs outside that loop. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L141-L158] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L210-L248] |
| Numeric-column correlation heatmap | `PlotlyReportGenerator.add_heatmap` | pandas `.corr()` result becomes heatmap `z`; displayed text is rounded to two decimals while `z` retains the correlation values. No engineering standard is cited by this method. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L170-L202] |
| Line, scatter, bar, histogram and custom figures | `add_line_plot`, `add_scatter_plot`, `add_bar_chart`, `add_histogram`, `add_custom_figure` | Plotly Express constructs the first four; a supplied custom figure is appended directly. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L50-L168] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L204-L211] |
| HTML assembly | `generate_html`, `_write_html_report` | Local reporting guidance requires interactive HTML and relative CSV access, but these implementations accept already-loaded DataFrames; the template embeds figures and does not read CSV itself. [docs/HTML_REPORTING_STANDARDS.md:L13-L47] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L50-L71] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L377-L396] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L84-L121] |
| Path construction | `get_project_root`, `get_data_path`, `get_report_path`, `ensure_report_dir`, `relative_path_from_report` | Ancestor counting and path concatenation, not data discovery or engineering calculations; the root and directory defects in section 6 preclude treating these helpers as a reference for correct repository-root discovery. [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L18-L138] |

No standards-derived numerical coefficient or formula is introduced by this pack; the reviewed methods use serialization, plotting and path construction rather than a licensed-code calculation. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L44-L158] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L50-L211] [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L18-L138]

AQG r0, sections 9–11, supplies the review gate set adopted in section 5; it is not a claim that the module already generates a signed QA appendix.

## 4. Validated worked examples

Validated engineering examples: **0**; the following **4 regression examples** check synthetic fixtures and structure, not an external engineering benchmark, and the heatmap test checks figure count rather than correlation accuracy. [tests/unit/reporting/test_export.py:L27-L68] [tests/unit/reporting/test_export.py:L184-L193] [tests/unit/reporting/test_export.py:L275-L278] [tests/unit/reporting/test_plotly_report_template.py:L82-L86] [tests/unit/reporting/test_plotly_report_template.py:L122-L131]

All node IDs below are relative to the repository root; fixture inputs live in the cited tests rather than a separate input dataset.

| Case | Source and input | Expected value, unit and tolerance basis | Existing test node ID | Last offline result |
| --- | --- | --- | --- | --- |
| Workbook round trip | Synthetic `simple_result` | 3 rows and identical column names; exact structural equality, not full cell comparison. [tests/unit/reporting/test_export.py:L27-L34] [tests/unit/reporting/test_export.py:L184-L188] | `tests/unit/reporting/test_export.py::TestXlsxExport::test_xlsx_readable_back_as_dataframe` | PASS at BASE and AFTER |
| JSON summary | Synthetic summary | `fields_analysed` = 3 records, exact integer equality. [tests/unit/reporting/test_export.py:L37-L42] [tests/unit/reporting/test_export.py:L275-L278] | `tests/unit/reporting/test_export.py::TestJsonExport::test_json_summary_preserved` | PASS at BASE and AFTER |
| Heatmap construction | Three affine numeric columns, 3 rows | 1 figure, exact count; matrix values are not asserted by this node. [tests/unit/reporting/test_plotly_report_template.py:L82-L86] | `tests/unit/reporting/test_plotly_report_template.py::TestAddPlots::test_add_heatmap` | PASS at BASE and AFTER |
| Multiple HTML plots | Two-row synthetic DataFrame | 2 plot identifiers, exact presence assertions; no browser execution. [tests/unit/reporting/test_plotly_report_template.py:L122-L131] | `tests/unit/reporting/test_plotly_report_template.py::TestGenerateHtml::test_generate_html_multiple_plots` | PASS at BASE and AFTER |

Original execution record at the header code pin: BASE has 66 passing test calls, 0 failed calls, 0 skipped, 0 NOT_RUN and 1 teardown error in `tests/unit/reporting/test_export.py::TestXlsxExport::test_xlsx_has_summary_sheet`; AFTER also has 66 passing calls, 0 failed calls, 0 skipped, 0 NOT_RUN and the same 1 teardown error; both commands return status 1. The four listed nodes passed in both runs. The unclosed workbook reader and temporary-directory fixture are recorded in open item O8 rather than silently counted as a clean run. [tests/unit/reporting/test_export.py:L60-L63] [tests/unit/reporting/test_export.py:L190-L193]

## 5. QA gates

Applicability follows AQG r0, section 10, Python calculations, with G5 from section 9; the checks below are module-specific acceptance instructions, not a claim of automated gate signing.

| Gate | Applicability | Module-specific execution and numeric criterion | Evidence / disposition |
| --- | --- | --- | --- |
| G0 | Applicable | C0.1: `get_data_path("test.csv", "invalid")` raises exactly 1 `ValueError` (exception count); C0.2: `export_report` with one valid and one unsupported token records exactly 1 success and 1 failure (format counts). [tests/unit/reporting/utils/test_path_utils.py:L38-L40] [tests/unit/reporting/test_export.py:L309-L315] | Run both named tests; keep manifests, supplied column units and input digests with the consumer's evidence record. No unit-conversion claim is made. |
| G1 | Applicable | C1.1: run `python -m pytest tests/unit/reporting -q -rA -p no:cacheprovider` in the installed workspace; expected 66 collected, 66 passed, 0 failed, 0 errors and 0 skipped (test counts). Package import is exercised directly. [tests/unit/reporting/test_export.py:L378-L382] [tests/unit/reporting/test_plotly_report_template.py:L7-L9] [tests/unit/reporting/utils/test_path_utils.py:L7-L12] | Offline Python route; no target solver program is written or loaded by these methods. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L141-L158] |
| G2 | Applicable | C2.1: use the three affine columns from the heatmap fixture; independently center the arrays, compute normalized dot products, then compare all 9 `add_heatmap` matrix entries with maximum absolute difference ≤ 1e-12 (dimensionless correlation). This tolerance is a pack-defined floating-point check, not a licensed standard value. [tests/unit/reporting/test_plotly_report_template.py:L82-L86] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L178-L191] | Retain the input arrays, independent matrix and maximum difference. This supplementary hand check does not promote the existing count-only test to a validated example. |
| G3 | NOT_APPLICABLE | No dynamic simulation state or time integration is produced by export dispatch or plot assembly. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L141-L158] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L377-L396] | Reason: data reporting rather than dynamics. |
| G4 | NOT_APPLICABLE | The reviewed operations serialize data and figures rather than compute diffraction meshes or hydrostatics. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L44-L121] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L50-L202] | Reason: no diffraction model. |
| G5 | Applicable | C5.1: `export_report` with `csv`, `json` and one unsupported token shall yield 2 successes + 1 failure = 3 requested formats, and 0 failed formats in `files` (format counts). [tests/unit/reporting/test_export.py:L317-L338] C5.2: delivery evidence shall contain all 4 applicable gate records, with 0 missing fingerprints, 0 missing dispositions and 0 missing independent signatures (record counts), per AQG r0 sections 9, 11 and 13. | C5.1 is executable by manifest inspection; C5.2 is an external delivery checklist. The manifest fields contain no QA signature or fingerprint field, so automatic signed appendix generation is an open item, issue pending (5). [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L27-L36] |

Check inventory: C0.1 and C0.2 feed G0, C1.1 feeds G1 (the original run missed its zero-error criterion; the revision-1 run below meets it, with resource-closure follow-up still issue pending (7)), C2.1 feeds G2, and C5.1 and C5.2 feed G5; G3 and G4 have no checks because they are not applicable.

Original self-check execution record at the header code pin: C0.1 PASS (1 expected exception), C0.2 PASS (1 successful and 1 failed format), C2.1 PASS (9 correlation entries, maximum absolute difference 0.0 dimensionless against the independent centered-array calculation), and C5.1 PASS (3 requested formats accounted for, 0 failed formats in `files`). Four imported module files match the pinned source digests. C1.1 remains FAIL against its zero-error criterion because of the repeated baseline teardown error, issue pending (7); C5.2 is NOT_RUN because independent delivery signatures and the QA appendix remain outside this production step, issue pending (5). These records do not constitute independent clearance.

Supplementary contract execution: `uv run --extra test python -m pytest tests/contracts -q -rA -p no:cacheprovider`, with scratch basetemp/coverage destinations and the documented preservation mode, records 46 passed, 0 failed, 0 errors, 0 skipped and 0 NOT_RUN at the same code pin. Both module runs retain the repository's pytest addopts; AFTER and the contract run use `--allow-existing-tree-changes` to compare the initial documentation bytes rather than disable the preservation check.

Revision-1 execution record: the unchanged package source matches the header pin in all six files. Local BASE and AFTER each collect 66 tests and finish with **66 passed, 0 failed, 0 errors, 0 skipped and 0 NOT_RUN**, exit status 0. C1.1 therefore passes in this environment; the historical teardown error did not reproduce. The four section-4 examples pass in both runs. The supplementary contract run finishes with **46 passed, 0 failed, 0 errors and 0 skipped**, exit status 0. Initial attempts lacked dependencies; after supplying the required dependencies, both suites ran without exclusions. All runs retain the repository pytest addopts, direct coverage and basetemp outputs outside the repository, and use the documented preservation mode after the pack edit.

Revision-1 self-checks: C0.1, C0.2, C2.1 and C5.1 pass with the same criteria as above; all 9 correlation entries have maximum absolute difference 0.0 from the independent centered-array calculation. Source-digest comparisons match all six package files to the pin. Separate inspection probes reproduce SF1 (integer JSON dates) and SF2 (3 emitted linter comments with one statistic card); these probes are diagnostic evidence, not permanent regression coverage. C5.2 remains NOT_RUN because independent signatures and a signed QA appendix are not available.

## 6. Known failure modes and pitfalls

The following are inspection findings at the code pin; they do not attribute an incident to a feature request.

sweep: 14 found (14 package risk rows below: seven retained and seven added, SF1–SF2 and F1–F5; the separate guidance row is outside the package).

The first grep returned 37 hit lines; the expanded grep returned 53, with overlapping hits counted separately. All six package `.py` files were read at the header pin and match the current source bytes. These exact commands searched the entire package, including both subpackages:

```sh
find packages/worldenergydata-reporting/src/worldenergydata/reporting -name '*.py' -type f -print0 | xargs -0 grep -nE 'except|continue|return None|return *$|\[\]|\{\}|\b0(\.0)?\b|1970|1900|percent|\bint\(|\bfloat\(|to_numeric|to_datetime|errors=|timeout|delay|offset|head\(|write_text|write_bytes|to_parquet|to_json|\.get\('
find packages/worldenergydata-reporting/src/worldenergydata/reporting -name '*.py' -type f -print0 | xargs -0 grep -nE 'getattr|select_dtypes|corr\(|datetime|strftime|isoformat|unit|noqa|cache|read_|return |default|random|= *[0-9]'
```

Classification: four exception handlers comprise one loud dependency error, the Parquet fallback (F1), manifest failures and the link fallback (F5). The single `continue` records an unsupported format, covered by C0.2. Six empty-container hits comprise two normalization defaults and four accumulators; accumulators are not error fallbacks. Eighteen zero hits are presentation constants or the correlation colour midpoint, with no numerical fallback. No bare return, `return None`, error-path empty-container return, external-text `int()`/`float()` conversion, percentage default, paging or cache write exists. Successful path returns and dispatch delegates are helpers. Plot sizes, bin count and the guarded random example are presentation/sample choices, not engineering defaults. Caller units are unconverted display metadata; numeric selection and local-time assumptions are F2 and F4. Full-string inspection adds SF2 beyond the first grep's candidates. Direct writers and truncation are classified in their rows rather than counted per write call.

| Symptom | Cause and evidence | Detection check / missing coverage | Tracking |
| --- | --- | --- | --- |
| SF1: JSON dates silently become epoch milliseconds | `to_json(orient="records")` uses pandas' epoch-millisecond datetime representation; a zoned column loses its offset representation. Unsupported summary values also stringify via `default=str`. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L74-L81] | No detection check exists for dated JSON/CSV agreement or preservation of offset representation; current JSON tests use undated fixtures. | issue pending (8), 2026-10-16 |
| SF2: Linter text appears in every generated report | `# noqa: E501` is inside HTML f-strings at the body style, statistic card and footer; it is emitted as CSS/text, including interference with the following CSS declaration. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L235-L236] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L354-L354] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L370-L370] | No detection check exists for zero emitted `noqa` occurrences; HTML tests assert selected strings without CSS or browser parsing. | issue pending (8), 2026-10-16 |
| F1: Parquet fallback loses the first error and engine provenance | The pyarrow exception is discarded before retrying pandas' default engine; a successful alternative engine can use different type mappings. The manifest has no engine field. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L59-L65] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L27-L36] | No detection check exists for the engine used, initial fallback cause or cross-engine type agreement; success alone is insufficient. | issue pending (9), 2026-10-16 |
| F2: Heatmap silently drops columns or yields empty/NaN cells | Numeric selection drops text columns, including numbers stored as text; `.corr()` uses pairwise-complete observations, constant columns give NaNs and no numeric columns gives an empty matrix. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L178-L191] | No detection check exists for dropped-column count, empty matrices, constant columns or pairwise row counts. C2.1 checks only the nine finite entries of its complete numeric fixture. | issue pending (9), 2026-10-16 |
| F3: Failed writes leave partial or stale files beside the manifest | Writers use destination paths directly, without atomic replacement or cleanup; an interrupted write can leave a partial file, or an older file can remain for a format now marked failed. Template output is also written in place. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L227-L239] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L393-L396] | C5.1 accounts for manifest outcomes only; no detection check exists for directory/manifest agreement after a partial write or a failed repeat export. | issue pending (9), 2026-10-16 |
| F4: Report and manifest times use different zone conventions | Template time is local with no zone while manifest time is UTC ISO text. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L339-L344] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L214-L214] | No detection check exists for a zone-bearing HTML timestamp or report/manifest instant agreement. | issue pending (9), 2026-10-16 |
| F5: HTML link separators depend on platform and branch | Direct relative paths stringify with native separators; the `ValueError` fallback explicitly joins with `/`, so Windows results differ by branch. [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L123-L138] | No detection check exists for portable separators across direct and fallback Windows paths. | issue pending (9), 2026-10-16 |
| Invalid data silently becomes an empty export | Missing or non-DataFrame input becomes an empty DataFrame; an absent or false-like summary becomes an empty dict. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L204-L208] | Inspect row count and type before C0.2; no detection check exists in the current tests for non-DataFrame rejection or unintended false-like summary loss. | issue pending (3), 2026-10-16 |
| Requested PDF is HTML; rows beyond the preview are absent | Dispatch maps `pdf` to `.html` and `html_report`; writer uses `head(200)` but prints full frame length. The docstring mentions PDF tools that are not called by this writer. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L84-L121] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L128-L158] | Existing PDF tests detect the HTML mapping; no detection check exists for disclosure of row truncation. [tests/unit/reporting/test_export.py:L286-L301] | issue pending (3), 2026-10-16 |
| Paths resolve below the member rather than the repository root | Five `.parent` operations from the current source layout reach the member package directory. [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L18-L28] | Count ancestors from the header path and compare with the workspace root; existing root tests assert only type and absoluteness, so no detection check exists for root identity. [tests/unit/reporting/utils/test_path_utils.py:L15-L22] | issue pending (1), 2026-10-16 |
| Requested report directory is not created | `ensure_report_dir` takes the parent of `get_report_path("", subfolder)`. [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L77-L89] | Compare returned path with requested report directory; no detection check exists in the path test file for this helper. [tests/unit/reporting/utils/test_path_utils.py:L7-L12] [tests/unit/reporting/utils/test_path_utils.py:L47-L69] | issue pending (1), 2026-10-16 |
| Caller text becomes markup or a path outside the chosen directory | Summary/title strings are interpolated without escaping; filename stems are joined without confinement validation. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L90-L118] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L227-L232] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L339-L355] | Use only trusted inputs pending escaping and confinement tests; no detection check exists for adversarial text or filename components in the reviewed tests. [tests/unit/reporting/test_export.py:L149-L162] [tests/unit/reporting/test_plotly_report_template.py:L95-L131] | issue pending (2), 2026-10-16 |
| Export may partially succeed or fail before a manifest exists | Writer exceptions populate `formats_failed`; directory creation precedes the exception handler. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L210-L239] | C0.2 and C5.1 require inspecting failures rather than treating return as full success. [tests/unit/reporting/test_export.py:L309-L338] | Existing feature context: issue 201; not an incident record. |
| Offline plots may not load; emitted markup is not browser-tested | HTML references external JavaScript while existing tests read strings only. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L221-L227] [tests/unit/reporting/test_plotly_report_template.py:L95-L131] | No detection check exists for offline browser rendering; the source guidance's offline checklist is not evidence of a pass. [docs/HTML_REPORTING_STANDARDS.md:L782-L795] | issue pending (5), 2026-10-16 |
| Guidance examples are not current API evidence | Reporting guidance contains unresolved conflict text, and a separate example calls `field_analysis_report` whereas the public exports name `export_report` and `ExportManifest`. [docs/HTML_REPORTING_STANDARDS.md:L248-L287] [docs/examples/index.md:L91-L97] [packages/worldenergydata-reporting/src/worldenergydata/reporting/__init__.py:L5-L7] | Search guidance for conflict delimiters and resolve documented callables against exports; no detection check exists in the reviewed module tests. | Existing issue 349 covers stale capability documentation. |

No incident issue number was specified for this module; issue 201 records export integration intent and issue 529 records package decomposition intent, rather than proof of a defect or completed numerical validation.

Historical baseline finding, repeated at the original BASE and AFTER: temporary-directory teardown reports `OSError: [Errno 39] Directory not empty` after `test_xlsx_has_summary_sheet`; that test creates an `ExcelFile` without an explicit close. The filesystem mechanism is not established. No detection check exists for resource closure; issue pending (7). The second-provider review at `a84eda6a` reports that the hosted `Domain unit-reporting` job passed; that hosted result does not establish the local teardown cause. [tests/unit/reporting/test_export.py:L60-L63] [tests/unit/reporting/test_export.py:L190-L193]

## 7. Lessons log

| Date | Entry | Lesson | Evidence | Pack change | Shared entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-16 | reporting-pack-0 | A success return does not mean every requested format succeeded; inspect both outcome lists. | [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L220-L248] | Sections 2, 5 and 6 distinguish partial success. | Not registered; issue pending (5). |
| 2026-10-16 | reporting-path-0 | Type-only path assertions do not establish the intended root after package extraction. | [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L18-L28] [tests/unit/reporting/utils/test_path_utils.py:L15-L22] | Sections 3 and 6 exclude this helper as a root-discovery reference. | Not registered; issue pending (1). |

## 8. Ownership

The adopted review assignment is the calculations quality manager until a data quality role is appointed; the deputy role remains to be assigned by the maintainer, with review coverage tracked by issue pending (5).

Producing role: reporting package contributors. Review disagreements on method classification will go to the family quality manager; unresolved scope or missing review coverage will go to the maintainer. Neither this role assignment nor DRAFT status records a completed second-provider review.

## 9. Dependencies and other implementations

### Runtime and consumer dependencies

Inventory correspondence uses the supplied snapshot entries `core:common` and `bsee`; runtime relationships are traced to the pinned code below. (Module inventory, revision 0, entries `core:common` and `bsee`.)

| Relationship | Inventory row or dependency identity | Evidence |
| --- | --- | --- |
| Upstream package | Inventory row `core:common`; distribution `worldenergydata-core` | Reporting declares core, NumPy, openpyxl, pandas and Plotly dependencies. [packages/worldenergydata-reporting/pyproject.toml:L26-L36] |
| Upstream data | Caller-supplied DataFrame and summary | No dataset identity or physical-unit metadata is required by normalization. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L204-L208] |
| Format engine | openpyxl; optional Parquet engine | XLSX checks openpyxl availability; Parquet tries pyarrow then pandas' default engine. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L44-L65] |
| Downstream caller | Inventory row `bsee`; consumer `bsee/pipeline` | The pipeline adapter passes production and activity data to the export stage and logs failures. [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/pipeline_runner.py:L167-L200] |
| HTML consumer | Browser with compatible Plotly JavaScript | Generated markup references Plotly JavaScript version 2.26.0 and invokes `Plotly.newPlot`; compatibility is open item O4. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L221-L227] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L377-L385] |

No solver-version dependency is exercised by the reviewed format dispatch or HTML assembly. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L141-L158] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L377-L396]

### Implementation-map inventory and counted-family search

Map source: `digitalmodel`, `docs/registry/implementation-map.yaml`, map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, declared data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`; family records inspected read-only. This external map is separate from the code revision in the header.

A8 inspection record: **0 in-package implementation rows, 0 module map families, empty inventory** across the map's **13 families**; counted-family grep **NOT_APPLICABLE**, because no family has an implementation path inside the header package. No method-family signal ranking or additional-implementation count is substituted for this empty-inventory rule. (Source: `digitalmodel`, Implementation map, map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, family implementation records.)

Map follow-up shall cover all section-3 methods: multi-format dispatch/serialization, numeric correlation heatmaps, figure construction, HTML assembly, and data/report path resolution; issue pending (6).

### Repository-wide discovery, including scripts

Search scope is the owning repository, including `scripts/`, using the symbols `export_report`, `PlotlyReportGenerator`, `get_project_root`, `get_data_path`, `get_report_path`, `ensure_report_dir`, `generate_html`, and the expression `corr\(`. The entries below are related implementations or callers, rather than counted-family A8 misses.

| Definition | Classification and evidence |
| --- | --- |
| `common.data_resolver._get_project_root` | Separate root-discovery implementation; prefers a workspace declaration rather than a fixed ancestor count. [packages/worldenergydata-core/src/worldenergydata/common/data_resolver.py:L26-L52] |
| `scripts/fdas/generate_production_report.py::generate_html_report` | Separate report assembly with its own aggregations, outside this package; candidate map gap. [scripts/fdas/generate_production_report.py:L67-L87] |
| `bsee.pipeline.pipeline_runner._export_report` | Adapter and delegate to the listed `export_report`, not a further implementation of its writers. [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/pipeline_runner.py:L174-L191] |

This discovery table is a bounded map follow-up rather than an exhaustive claim that all reporting implementations have been reconciled; issue pending (6).

## 10. Coverage and open items

### Files read

| Group | Files and evidence at the code pin |
| --- | --- |
| Package API | `__init__.py`. [packages/worldenergydata-reporting/src/worldenergydata/reporting/__init__.py:L1-L7] |
| Export implementation | `export.py`, including all writers, dispatch and manifest. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L1-L248] |
| Templates subpackage | `templates/__init__.py` and the entire template implementation, including its guarded example. [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/__init__.py:L1-L3] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L1-L434] |
| Utilities subpackage | `utils/__init__.py` and the entire path utility implementation. [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/__init__.py:L1-L3] [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L1-L145] |
| Distribution documentation | Package README and build metadata. [packages/worldenergydata-reporting/README.md:L1-L8] [packages/worldenergydata-reporting/pyproject.toml:L1-L57] |
| Direct module tests | Export, template and path test files. [tests/unit/reporting/test_export.py:L1-L382] [tests/unit/reporting/test_plotly_report_template.py:L1-L131] [tests/unit/reporting/utils/test_path_utils.py:L1-L69] |
| Discovery exclusions | The integration reporting tests import the separate Lower Tertiary comprehensive-report module; they are outside the direct reporting package test census. [tests/integration/reporting/test_comprehensive_delivery.py:L11-L11] [tests/integration/reporting/test_lt_comprehensive.py:L24-L32] |
| Reporting guidance found by module-qualified references | `docs/HTML_REPORTING_STANDARDS.md`; interactive plots and relative CSV guidance, with unresolved conflict text. [docs/HTML_REPORTING_STANDARDS.md:L1-L821] |
| Related module documentation found by explicit module references | `docs/adr/0001-domain-package-split.md`, `docs/examples/index.md`, `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`; historical design and capability statements are not current validation evidence. [docs/adr/0001-domain-package-split.md:L26-L43] [docs/examples/index.md:L91-L97] [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L176-L176] |

Test source recount: **39 export + 16 template + 11 path = 66 test definitions**, without parametrized cases; the assertions cover synthetic data, file structure, plotting construction and path shape rather than licensed-solver results. [tests/unit/reporting/test_export.py:L76-L382] [tests/unit/reporting/test_plotly_report_template.py:L12-L131] [tests/unit/reporting/utils/test_path_utils.py:L15-L69]

### Open items

All items below are assigned to the reporting maintainer for triage; unresolved review classification will go to the calculations quality manager.

| ID | Gap or limitation | Tracking and acceptance checkpoint |
| --- | --- | --- |
| O1 | Root identity and report-directory creation are incorrect for the extracted layout; existing path assertions do not detect either. [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L18-L28] [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L77-L89] [tests/unit/reporting/utils/test_path_utils.py:L15-L22] | issue pending (1); add exact root/directory tests before changing helpers. |
| O2 | HTML text escaping and filename confinement are not implemented at the interpolation/join sites. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L90-L118] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L227-L232] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L339-L355] | issue pending (2); adversarial text shall remain text and output paths shall remain inside the requested directory. |
| O3 | PDF naming, undisclosed preview truncation, invalid-data fallback and writer docstring do not provide a complete export contract. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L84-L121] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L128-L138] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L204-L208] | issue pending (3); explicit format/content and row-count tests shall cover the limits. |
| O4 | UNVERIFIED claim from section 1: general numerical/browser validation is not established; a permanent matrix-value test, offline rendering check and signed QA appendix are missing from the reviewed examples and manifest. [tests/unit/reporting/test_plotly_report_template.py:L82-L131] [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L27-L36] | issue pending (5); retain independent numerical references, browser evidence and all applicable QA records. |
| O5 | Recursive Markdown package-data patterns match a pack under `docs/`; this change does not establish wheel exclusion. [packages/worldenergydata-reporting/pyproject.toml:L51-L57] | issue pending (4); resolve packaging policy and inspect a built wheel in a dedicated change; package configuration is not changed here. |
| O6 | Map follow-up for every section-3 method and remaining related implementations is pending. [packages/worldenergydata-reporting/src/worldenergydata/reporting/export.py:L44-L158] [packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py:L50-L211] [packages/worldenergydata-reporting/src/worldenergydata/reporting/utils/path_utils.py:L18-L138] | issue pending (6); add family rows to the map before those families count under A8. |
| O7 | Reporting guidance has conflict text, example API drift and historical readiness figures; these are not adopted as current capabilities. [docs/HTML_REPORTING_STANDARDS.md:L248-L287] [docs/examples/index.md:L91-L97] [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L176-L176] | Existing issue 349; update documentation against exported callables and the test census. |
| O8 | Original BASE and AFTER have a temporary-directory teardown error after workbook sheet inspection; the test does not explicitly close `ExcelFile`. [tests/unit/reporting/test_export.py:L60-L63] [tests/unit/reporting/test_export.py:L190-L193] | issue pending (7); the review at `a84eda6a` reports the hosted `Domain unit-reporting` job passed. Reproduce and check reader closure without weakening test assertions or warning policy. |
| O9 | JSON date representation changes silently and linter text is emitted into HTML (SF1–SF2 in section 6). | issue pending (8); preserve dated-fixture instants and required offset representation across JSON/CSV, and assert zero emitted linter comments. |
| O10 | Parquet engine provenance, heatmap input loss, partial/stale files, zoneless times and platform-dependent links are unreported (F1–F5 in section 6). | issue pending (9); record engine/fallback cause and dropped-column count, test incomplete/constant heatmaps, reconcile files after failures, and assert zoned times and portable separators. |

Issue references are read-only context: issue 201 (multi-format integration), issue 529 (package split), issue 349 (capability-documentation audit), and issue 361 (upstream calculation citation sidecars). No engineering output from those issues is adopted as independently verified reference data.
