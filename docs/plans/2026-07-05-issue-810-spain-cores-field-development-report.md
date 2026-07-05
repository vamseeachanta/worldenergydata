# Plan: Issue #810 - Spain CORES field-development HTML report

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/810
**Status:** plan-review
**Tier:** T2 (interactive HTML report over existing live Spain CORES chain)
**Client:** N/A
**Project:** worldenergydata Spain CORES production lifecycle
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Implementation will use a single-lane TDD workflow because this slice will
touch the Spain package, report-generation scripts, tracked report artifacts,
the public-pages copy hook, and repo-structure allowlist metadata. Read-only
review and verification can run independently, but code writes will remain
serialized to avoid report/index conflicts.

Implementation will not begin until this plan is reviewed, pushed, moved to
`status:plan-review`, and explicitly approved by the user as
`status:plan-approved`.

### Issue and dependency status

| Issue | State | Role for this plan |
|---|---|---|
| [#713](https://github.com/vamseeachanta/worldenergydata/issues/713) | open, `status:needs-plan` | International source-to-field-development epic |
| [#763](https://github.com/vamseeachanta/worldenergydata/issues/763) | closed, `status:done` | Spain CORES parser, fixture, adapter, and reference chain |
| [#806](https://github.com/vamseeachanta/worldenergydata/issues/806) | closed, `status:done` | Direct-source live CORES XLSX download and normalized CSV lane |
| [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) | open | Per-field crude density/API refinement, outside this slice |
| [#808](https://github.com/vamseeachanta/worldenergydata/issues/808) | open | Gas revenue modeling, outside this slice |
| [#809](https://github.com/vamseeachanta/worldenergydata/issues/809) | closed, `status:done` | Scheduler job that refreshes the live CORES cache |
| [#810](https://github.com/vamseeachanta/worldenergydata/issues/810) | open, `status:needs-plan` | This Spain CORES field-development report |

### Reproduction proofs

N/A - [#810](https://github.com/vamseeachanta/worldenergydata/issues/810)
requests a new report surface rather than alleging a failing test or runtime
regression.

Input-shape proof against the live scheduler cache:

```bash
python - <<'PY'
from pathlib import Path
import json
import pandas as pd
root = Path('/mnt/ace/worldenergydata/data/spain/cores')
all_df = pd.read_csv(root / 'normalized' / 'cores_all_production.csv')
oil_df = pd.read_csv(root / 'normalized' / 'cores_oil_production.csv')
gas_df = pd.read_csv(root / 'normalized' / 'cores_gas_production.csv')
meta = json.loads((root / '_metadata.json').read_text())
manifest = json.loads((root / 'manifest.json').read_text())
fields = sorted(all_df['field_name'].dropna().unique().tolist())
ay = all_df[all_df['field_name'].str.lower() == 'ayoluengo']
print(json.dumps({
    'root_exists': root.exists(),
    'all_rows': len(all_df),
    'oil_rows': len(oil_df),
    'gas_rows': len(gas_df),
    'field_count': len(fields),
    'first_fields': fields[:8],
    'ayoluengo_rows': len(ay),
    'ayoluengo_oil_rows': int((ay.get('oil_bbl', 0).fillna(0) > 0).sum()),
    'metadata_format': meta.get('format'),
    'metadata_record_count': meta.get('record_count'),
    'metadata_last_refresh': meta.get('last_refresh'),
    'metadata_source_url': meta.get('source_url'),
    'manifest_status': manifest.get('status'),
    'manifest_records_updated': manifest.get('records_updated'),
}, indent=2))
PY
```

Output:

```json
{
  "root_exists": true,
  "all_rows": 4375,
  "oil_rows": 2865,
  "gas_rows": 1520,
  "field_count": 20,
  "first_fields": [
    "Albatros",
    "Amposta",
    "Ayoluengo",
    "Biogas",
    "Boquer\u00f3n",
    "Casablanca",
    "Castillo",
    "Dorada"
  ],
  "ayoluengo_rows": 688,
  "ayoluengo_oil_rows": 577,
  "metadata_format": "csv",
  "metadata_record_count": 4375,
  "metadata_last_refresh": "2026-07-05T18:37:12.102722+00:00",
  "metadata_source_url": "https://www.cores.es/en/estadisticas",
  "manifest_status": "success",
  "manifest_records_updated": 4375
}
```

Direct import proof through the unmanaged system Python showed an environment
risk rather than a data failure:

```text
ModuleNotFoundError: No module named 'plotly'
```

`plotly` is declared by `packages/worldenergydata-production/pyproject.toml`,
so implementation verification will use the repo-managed environment. The
report code will keep routine data-shape tests fixture-backed and will not
require `/mnt/ace` or a live dependency sync in CI.

### Resource-intel commands

- `gh pr list --repo vamseeachanta/worldenergydata --state open` returned an
  empty list, so no active PR is competing with this report slice.
- The clean planning worktree is
  `/mnt/local-analysis/wt-wed-810-spain-report-plan` at `0906342b`
  (`docs: add #809 Spain CORES scheduler exit handoff`) on branch
  `plan/spain-810-report`.
- `docs/plans/_template-issue-plan.md` is absent in this repo snapshot, so this
  plan follows the existing [#806](https://github.com/vamseeachanta/worldenergydata/issues/806)
  and [#809](https://github.com/vamseeachanta/worldenergydata/issues/809)
  plan shape.
- `scripts/data/drive-index-search/search.py` is absent in this repo snapshot,
  so drive-file resource intel could not run; the plan treats this as
  `drive-search-missing` rather than claiming no relevant drive files.

### Current code surfaces this implementation will reuse

- `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py`
  exposes `CoresLiveProductionLoader`, normalized CSV writes, and source
  metadata access.
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py`
  exposes `SpainCoresAdapter(loader=...)`, `fetch(...)`, `available_fields()`,
  and `date_range()`.
- `packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py`
  exposes `run_spain_reference_chain(...)`, which returns unified production,
  FDAS production, ranked concepts, `dev_system`, and `pre_tax_metrics`.
- `tests/unit/spain/test_reference_chain.py` already proves the sparse
  Ayoluengo onshore chain, `dev_system == "dry"`, and
  `onshore_model_mismatch is True` through a fixture loader.
- `scripts/build_pages.py` publishes field-development report artifacts from
  `reports/field_development/` to `public/field-development/` and indexes only
  pages copied there.
- `docs/HTML_REPORTING_STANDARDS.md` requires HTML reports with interactive
  plots, source/provenance information, and relative browser data paths.
  Existing field-development reports are self-contained generated HTML. This
  slice will follow the self-contained field-development publishing pattern and
  will explicitly test that the public HTML has no runtime dependency on
  `/mnt/ace` or an uncopied JSON file.
- `config/repo_structure.yml` explicitly allowlists tracked report and script
  artifacts, so new tracked report/script/test paths must be added there if the
  structure check requires exact paths.

### Boundary decisions

- The implementation will use direct CORES data refreshed by [#806](https://github.com/vamseeachanta/worldenergydata/issues/806)
  and [#809](https://github.com/vamseeachanta/worldenergydata/issues/809);
  it will not scrape or copy third-party data.
- Durable raw and normalized source outputs will stay under `/mnt/ace`.
  Tracked repo artifacts will be generated report HTML/JSON summaries only.
- The report will read `normalized/cores_*_production.csv` directly through a
  report-specific normalized-CSV loader. It will not instantiate
  `CoresLiveProductionLoader` for the report read path because that loader reads
  raw XLSX, can download missing workbooks, and writes normalized CSVs as a side
  effect.
- The report will cover all 20 live CORES fields for monthly production
  visibility, with oil and gas volumes plotted separately when present.
- Pre-tax economics will run through `run_spain_reference_chain(...)` only for
  fields with explicit report metadata for both product suitability and
  environment classification. The initial approved set will be Ayoluengo:
  `environment="onshore"`, oil-producing, sparse metadata. Other fields will
  remain production-only until field-environment metadata is curated.
- Gas-only economics will be marked as deferred to [#808](https://github.com/vamseeachanta/worldenergydata/issues/808)
  instead of showing false zero-revenue conclusions.
- The report will prominently show the `onshore_model_mismatch` caveat for
  Ayoluengo and for any future field whose explicit report metadata classifies
  it as onshore. Unknown-environment fields will not be passed through the
  reference-chain economics path.
- The report will cite CORES source URL, refresh timestamp, record counts,
  workbook/source metadata from `metadata/cores_refresh_metadata.json`, and the
  open limitations from [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)
  and [#808](https://github.com/vamseeachanta/worldenergydata/issues/808).
- The tracked HTML will not embed `/mnt/ace` absolute paths and will not require
  a runtime fetch of `spain_cores.json`. The HTML will embed the compact browser
  payload inline; `spain_cores.json` will be an audit/provenance sidecar only.
- `manifest.json` will be a hard prerequisite. The report command will be
  documented as a post-scheduler consumer, not as a consumer of direct
  `CoresLiveProductionLoader.refresh()` output alone.
- The report renderer will use inline SVG/JavaScript interactions rather than
  Python Plotly APIs or externally loaded Plotly JavaScript. This keeps the
  tracked field-development HTML self-contained and aligned with
  `scripts/build_pages.py` comments that field-development surfaces have no
  external assets.
- The report/reference-chain import path depends on `worldenergydata-production`
  and `worldenergydata-fdas`. The implementation will declare those dependencies
  explicitly in `packages/worldenergydata-spain/pyproject.toml` and refresh
  `uv.lock` because `worldenergydata.spain.reference_chain` already imports
  those packages. The Python process may still import Plotly transitively through
  the current production package initialization; this plan removes Plotly from
  the report renderer/runtime contract, not from the broader production import
  graph.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-05-issue-810-spain-cores-field-development-report.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review artifacts | `scripts/review/results/2026-07-05-plan-810-*.md` |
| Report package | `packages/worldenergydata-spain/src/worldenergydata/spain/reports/` |
| Report data assembly | `packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py` |
| HTML renderer | `packages/worldenergydata-spain/src/worldenergydata/spain/reports/html.py` |
| Operator script | `scripts/spain/build_cores_field_development_report.py` |
| Tracked report HTML | `reports/field_development/spain_cores.html` |
| Tracked report summary/provenance | `reports/field_development/spain_cores.json` |
| Public-pages publisher | `scripts/build_pages.py` |
| Spain package dependencies | `packages/worldenergydata-spain/pyproject.toml`, `uv.lock` |
| Package README | `packages/worldenergydata-spain/README.md` |
| Repo-structure allowlist | `config/repo_structure.yml` |
| Unit tests | `tests/unit/spain/test_cores_field_development_report.py` |
| Public-pages tests | `tests/test_build_pages.py` |

Operational input root for report generation:

```text
/mnt/ace/worldenergydata/data/spain/cores/
  normalized/
    cores_oil_production.csv
    cores_gas_production.csv
    cores_all_production.csv
  metadata/
    cores_refresh_metadata.json
  _metadata.json
  manifest.json
```

Tracked output:

```text
reports/field_development/
  spain_cores.html
  spain_cores.json
```

## Deliverable

The implementation will add a Spain CORES field-development report generator
that operators can run after the live scheduler refresh has written normalized
CSV files, detailed workbook metadata, `_metadata.json`, and scheduler
`manifest.json`:

```bash
uv run python scripts/spain/build_cores_field_development_report.py \
  --cache-root /mnt/ace/worldenergydata/data/spain/cores \
  --output-html reports/field_development/spain_cores.html \
  --output-json reports/field_development/spain_cores.json
```

The report will:

1. Load normalized live CORES CSVs and metadata from the supplied cache root
   without reading raw XLSX and without network access.
2. Validate that `_metadata.json` records `source_url`, `last_refresh`, and
   `format == "csv"`, that `metadata/cores_refresh_metadata.json` records
   workbook source URLs, `status_code`, hashes, byte counts, and last-modified
   values, and that `manifest.json` reports scheduler success.
3. Build all-field monthly production series for oil and gas.
4. Build a duck-typed normalized-CSV loader for `SpainCoresAdapter` so
   `run_spain_reference_chain(...)` consumes in-memory/CSV production rows and
   never triggers raw workbook parsing or downloads.
5. Run `run_spain_reference_chain(...)` for Ayoluengo as the initial explicit
   economics field and mark all other fields production-only until product and
   environment metadata are curated.
6. Render interactive production and economics views with inline SVG and
   JavaScript controls, hover detail, field filtering, and legend toggles. The
   report renderer will not call Python Plotly APIs and will not load Plotly
   JavaScript from a CDN.
7. Render a field selector/table that makes gas-only and unknown-environment
   economics deferred rather than misleading.
8. Render a prominent onshore-model caveat and sparse-metadata caveat for the
   Ayoluengo economics slice.
9. Write a deterministic JSON summary with record counts, source provenance,
   field coverage, selected economics fields, and limitation flags.
10. Publish the self-contained HTML through `scripts/build_pages.py` to
   `public/field-development/spain-cores.html`.

## Pseudocode

```python
def build_report(cache_root: Path, output_html: Path, output_json: Path) -> ReportSummary:
    source = load_cores_report_source(cache_root)
    validate_source(source.metadata, source.manifest)
    fields = summarize_fields(source.all_production)
    report_loader = NormalizedCoresReportLoader(source.all_production)
    adapter = SpainCoresAdapter(loader=report_loader)
    economics = []
    for field in select_explicit_oil_economics_fields(fields, FIELD_METADATA):
        economics.append(
            summarize_reference_chain(
                run_spain_reference_chain(
                    adapter=adapter,
                    field_meta=FIELD_METADATA[field.name],
                    field_name=field.name,
                )
            )
        )
    summary = ReportSummary(source=source.provenance, fields=fields, economics=economics)
    output_json.write_text(summary.to_json())
    output_html.write_text(render_spain_cores_html(summary))
    return summary
```

```python
def render_spain_cores_html(summary: ReportSummary) -> str:
    payload = json.dumps(summary.to_browser_payload(), ensure_ascii=False)
    return (
        HTML_TEMPLATE
        .replace("__TITLE__", html.escape("Spain CORES field-development report"))
        .replace("__SOURCE_URL__", html.escape(summary.source_url))
        .replace("__LAST_REFRESH__", html.escape(summary.last_refresh))
        .replace("__CAVEATS__", render_caveats(summary))
        .replace("__PAYLOAD__", payload.replace("</", "<\\/"))
    )
```

## Files to Change

- `packages/worldenergydata-spain/src/worldenergydata/spain/reports/__init__.py`
  will export the report-generation API.
- `packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py`
  will load/validate live-cache CSV inputs, define
  `NormalizedCoresReportLoader`, define the explicit initial
  `FIELD_METADATA = {"Ayoluengo": {"field_name": "Ayoluengo", "environment": "onshore", "source": "CORES"}}`,
  assemble field summaries, run the selected reference-chain economics, and
  return deterministic report data.
- `packages/worldenergydata-spain/src/worldenergydata/spain/reports/html.py`
  will render the interactive HTML shell with escaped inline JSON payloads,
  inline SVG/JavaScript interactions, and visible source/caveat sections.
- `scripts/spain/build_cores_field_development_report.py` will provide the
  operator CLI and default paths without hardcoding `/mnt/ace` inside library
  code.
- `reports/field_development/spain_cores.html` will be the tracked report.
- `reports/field_development/spain_cores.json` will be the tracked summary and
  provenance payload.
- `scripts/build_pages.py` will add an explicit
  `("spain_cores.html", "spain-cores.html")` copy entry to
  `build_field_development(...)` and add a `_field_development_section()` card
  guarded by `if (fd / "spain-cores.html").exists():`. The section heading and
  copy will be broadened from offshore-only wording to field-development
  surfaces that include offshore playbooks and the Spain CORES country chain,
  without implying Spain CORES is BSEE/SubseaIQ-derived.
- `packages/worldenergydata-spain/pyproject.toml` will declare
  `worldenergydata-production` and `worldenergydata-fdas`; `uv.lock` will be
  refreshed with the dependency metadata change.
- `packages/worldenergydata-spain/README.md` will document the report-generation
  command and source caveats.
- `config/repo_structure.yml` will allowlist new tracked artifacts when the
  structure check requires exact paths.
- `tests/unit/spain/test_cores_field_development_report.py` will cover source
  validation, report assembly, HTML rendering, and CLI writes.
- `tests/test_build_pages.py` will cover the field-development publishing hook.

## TDD Test List

- Source validation:
  - a fixture cache with normalized oil/gas/all CSVs plus `_metadata.json` and
    `metadata/cores_refresh_metadata.json` and `manifest.json` will load into a
    report source model;
  - missing `_metadata.json`, missing `source_url`, missing `last_refresh`,
    non-`csv` format, missing detailed workbook metadata, workbook
    `status_code != 200`, or non-success manifest will fail closed with a clear
    exception;
  - loaded CSV row count will match `_metadata.record_count` and
    `manifest.records_updated`;
  - the source model will report row counts, field counts, date range, and
    product coverage.
- Normalized report loader:
  - `NormalizedCoresReportLoader.load_all_production()` will return the
    normalized CSV frame without writing files;
  - `load_field_production("Ayoluengo")` will filter the normalized frame
    case-insensitively;
  - tests will use a sentinel object or monkeypatch to prove report generation
    does not instantiate `CoresLiveProductionLoader`, read raw XLSX, or call
    any network/downloader path.
- Field summaries:
  - all fixture fields will appear in the field coverage table;
  - oil and gas monthly series will stay separate and sorted by
    `(field_name, year, month)`;
  - Ayoluengo will be selected as the default highlighted field when present.
- Economics summaries:
  - `run_spain_reference_chain(...)` will be called through an injected
    `SpainCoresAdapter` and normalized CSV loader for Ayoluengo;
  - economics selection will require both `field_name in FIELD_METADATA` and
    positive oil production, so metadata-backed gas-only fields cannot render a
    zero-revenue economics block;
  - the economics summary will include months, gross revenue, royalty, host
    capex, net cashflow, `dev_system`, and ranked concept labels;
  - `onshore_model_mismatch` will be carried through as a required caveat;
  - gas-only fields and fields lacking explicit `FIELD_METADATA` will emit
    limitation flags instead of showing zero-revenue or misclassified economics.
- HTML rendering:
  - the HTML will include inline interactive chart containers, hover detail,
    legend toggles, and a field selector/table with no external JavaScript;
  - source URL, refresh timestamp, `format=csv`, record counts, and scheduler
    status will be visible;
  - caveats for onshore model mismatch, sparse Spain metadata, [#807](https://github.com/vamseeachanta/worldenergydata/issues/807),
    and [#808](https://github.com/vamseeachanta/worldenergydata/issues/808)
    will be visible;
  - embedded JSON will escape `</script>`-style content and browser-visible text
    will escape field names;
  - the tracked HTML will not contain `/mnt/ace`, local user paths, secrets, or
    client identifiers.
  - the tracked HTML will not fetch `spain_cores.json`; it will be
    self-contained with inline CSS/JS;
  - template rendering will avoid `str.format` brace collisions by using a
    sentinel replacement or `string.Template`, and a test with realistic inline
    CSS/JS braces will prove rendering does not raise `KeyError` or
    `ValueError`.
- Dependency/import boundary:
  - an import smoke test will prove the report generator and
    `run_spain_reference_chain(...)` import under the supported repo-managed
    environment;
  - the focused dependency test will prove `worldenergydata-spain` declares the
    reference-chain dependencies it imports.
- CLI/report writes:
  - the script will write HTML and JSON to `tmp_path` from a fixture cache;
  - repeated runs from the same fixture cache will produce deterministic JSON;
  - invalid cache roots will exit non-zero with a clear message.
- Public-pages publishing:
  - `build_field_development(...)` will copy `spain_cores.html` to
    `public/field-development/spain-cores.html`;
  - the landing section will include a Spain CORES card only when the copied
    page exists;
  - the test around the Spain card/section will assert that Spain CORES is not
    described as BSEE/SubseaIQ-derived or offshore-only.

## Acceptance Criteria

- `reports/field_development/spain_cores.html` exists and provides an
  interactive Spain CORES field-development report.
- `reports/field_development/spain_cores.json` records source URL, refresh
  timestamp, scheduler status, row counts, field coverage, economics fields,
  workbook metadata, and caveat flags.
- The report uses direct CORES normalized CSV data from the live cache and does
  not use scraped third-party copies.
- The report covers all live CORES fields for monthly production and presents
  oil/gas product coverage clearly.
- The report presents pre-tax economics from `run_spain_reference_chain(...)`
  for the explicitly metadata-backed Ayoluengo field and does not misrepresent
  gas-only or unknown-environment fields before [#808](https://github.com/vamseeachanta/worldenergydata/issues/808)
  and a future field-environment metadata slice.
- The `onshore_model_mismatch` caveat is prominent for the Ayoluengo economics
  slice.
- The tracked HTML/JSON does not contain `/mnt/ace` absolute paths, secrets, or
  client identifiers.
- `scripts/build_pages.py` publishes the report to
  `public/field-development/spain-cores.html` without labeling Spain CORES as a
  BSEE/SubseaIQ or offshore-only report.
- The report HTML is self-contained with no external JavaScript runtime and no
  browser fetch of the JSON sidecar.
- Focused tests pass for report assembly, rendering, CLI writes, and publishing.
- `scripts/legal/legal-sanity-scan.sh --diff-only` passes.
- CI or the repo's targeted equivalent passes after implementation.

## Risks

| Risk | Mitigation |
|---|---|
| Gas-only fields show false economics before [#808](https://github.com/vamseeachanta/worldenergydata/issues/808) | Mark gas economics as deferred and test that gas-only fields do not render zero-revenue conclusions. |
| Per-field oil conversion remains approximate before [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) | Cite the limitation in the report and JSON summary; do not introduce density assumptions in this slice. |
| Sparse Spain metadata weakens concept screening | Keep concept output labeled as sparse/wiring-oriented and show the `onshore_model_mismatch` caveat prominently. |
| No live environment field exists for most CORES fields | Run economics only for fields in explicit `FIELD_METADATA`; render all others as production-only until metadata is curated. |
| Report build re-downloads or rewrites CORES cache | Use `NormalizedCoresReportLoader` over normalized CSVs; test that report generation does not instantiate the live/raw loader or touch downloader paths. |
| `/mnt/ace` leaks into tracked report artifacts | Accept `/mnt/ace` only as an operator CLI argument; test tracked output for absence of absolute local paths. |
| Report misses workbook-level provenance | Require `metadata/cores_refresh_metadata.json`, surface workbook URLs/status/hashes/last-modified values, and test failure when detailed metadata is missing. |
| Inline template braces break rendering | Use sentinel replacement or `string.Template`; include a test with CSS/JS braces. |
| Spain reference-chain dependencies stay implicit | Declare `worldenergydata-production` and `worldenergydata-fdas` in the Spain package and test the declaration. |
| Report generator becomes hard to review | Split source assembly, economics summary, HTML rendering, and CLI into focused files under the repo line-size guardrails. |
| First-run dependency setup is slow | Keep CI tests fixture-backed and reserve live `/mnt/ace` report generation for the operator command. |
| Public page index drifts | Add a build-pages test that proves the Spain report is copied and linked only when present. |

## Adversarial Review Summary

Plan review completed with final no-MAJOR available-provider verdicts:

| Provider | Artifact | Verdict | Blocking findings |
|---|---|---|---|
| Claude | `scripts/review/results/2026-07-05-plan-810-claude.md` | MAJOR | Normalize-vs-raw loader gap; missing field environment metadata for onshore caveat |
| Codex | `scripts/review/results/2026-07-05-plan-810-codex.md` | MAJOR | Missing field environment metadata; ambiguous JSON runtime contract |
| Gemini | `scripts/review/results/2026-07-05-plan-810-gemini.md` | UNAVAILABLE | CLI/auth tier rejected review (`UNSUPPORTED_CLIENT`) |
| Claude r2 | `scripts/review/results/2026-07-05-plan-810-claude-r2.md` | MINOR | R1 blockers resolved; remaining brace-safety, Plotly delivery, and oil-presence filter concerns |
| Codex r2 | `scripts/review/results/2026-07-05-plan-810-codex-r2.md` | MAJOR | Production adapter import still implied Plotly dependency; workbook metadata and landing-copy concerns |
| Codex r3 | `scripts/review/results/2026-07-05-plan-810-codex-r3.md` | MINOR | Renderer-vs-transitive Plotly wording, `status_code`, and landing-copy negative assertion |

This revision adds a normalized-CSV report loader, scopes economics to the
explicitly metadata-backed Ayoluengo field, makes the HTML self-contained with
inline SVG/JavaScript rather than Plotly charting APIs, adds detailed workbook
metadata to the input contract, declares the Spain package dependency boundary,
and documents Gemini unavailability. Codex r3 returned MINOR only; final local
patches clarified renderer-vs-transitive Plotly imports, `status_code`, and the
landing-copy negative assertion.
