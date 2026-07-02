# Plan: Issue #707 - Texas RRC field architecture portfolio report

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/707
**Status:** plan-review
**Tier:** T2 (new report package, portfolio action model, HTML and machine-readable outputs, CLI, tests, docs)
**Client:** N/A
**Project:** worldenergydata onshore field development
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Implementation will use single-lane development from `origin/main` after user
approval. The work will remain blocked until this plan is reviewed, pushed,
marked `status:plan-review`, and explicitly approved by the user.
Implementation will use TDD, with failing tests written before production code
for source loading, portfolio action classification, summary rollups, HTML
rendering, output persistence, quality reporting, and CLI behavior.

### Reproduction proofs

N/A. Issue #707 proposes a new portfolio report product and does not allege a
runtime failure, regression, missing method, or incorrect numeric output. The
implementation worker will still re-run the source-inventory probes below
before coding because portfolio output will depend on live `/mnt/ace`
artifacts.

### Direct-source artifact inventory

The portfolio builder will consume direct Texas RRC-derived curated artifacts
already published under `/mnt/ace/worldenergydata/data/modules/texas_rrc`. It
will not call PatchOps, scrape LinkedIn, use third-party scraper output, or
fetch new network data during portfolio publication.

Planning-time probes from 2026-07-02 report these current #702 dossier inputs:

| Input | Current rows | Current source gaps | Current generated_at | Expected path | Planned use |
|---|---:|---|---|---|---|
| Dossier index | 37 | none blocking; `water_bbl`, `well_count` informational | 2026-07-02T16:21:20Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_architecture_dossiers/field_architecture_dossier_index.csv` | Field action queue, architecture class rollups, source links, caveats |
| Dossier manifest | 37 | none blocking; `water_bbl`, `well_count` informational | 2026-07-02T16:21:20Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_architecture_dossiers/manifest.json` | Input provenance, upstream manifest list, source gaps, selection policy, code revision |
| Dossier quality JSON | 37 | none blocking; `water_bbl`, `well_count` informational | 2026-07-02T16:21:20Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_architecture_dossiers/quality.json` | Caveat and quality-flag counts, selection quality context |
| Dossier HTML pages | 37 pages | none blocking | 2026-07-02T16:21:20Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_architecture_dossiers/fields/` | Link targets for portfolio report rows |

Planning-time class distribution in the dossier index is:

| Architecture signal class | Current dossier count |
|---|---:|
| `high_access_infill_redevelopment` | 23 |
| `low_data_confidence` | 3 |
| `infrastructure_constrained_activity` | 3 |
| `monitor_only` | 3 |
| `mature_harvest` | 3 |
| `emerging_growth` | 2 |

The planning-time selection policy is `max_fields=25` and
`class_coverage_limit=3`. The implementation will not broaden the portfolio
input population in v1; it will summarize the bounded dossier packet produced
by #702. A later issue may add full-population portfolio rollups from the #695
ranking if the user wants statewide portfolio statistics.

### Current code shape

- `worldenergydata.texas_rrc.dossiers.io` defines the upstream dossier output
  directory and filenames through `FIELD_ARCHITECTURE_DOSSIER_DIR`,
  `INDEX_PARQUET_FILENAME`, `INDEX_CSV_FILENAME`, `QUALITY_FILENAME`,
  `COMPONENT_QUALITY_FILENAME`, and `MANIFEST_FILENAME`. The public
  `worldenergydata.texas_rrc.dossiers` namespace does not expose a dossier
  output loader, so this implementation will add an explicit
  `architecture_portfolio.sources` loader for the #702 output packet.
- `worldenergydata.texas_rrc.opportunities` will remain upstream provenance
  for opportunity score and architecture signal fields.
- `worldenergydata.texas_rrc.reports`, `field_development`,
  `infrastructure`, and `production_atlas` will remain upstream provenance
  through the dossier index and manifest.
- `src/worldenergydata/cli/commands/texas_rrc.py` already hosts Texas RRC Typer
  commands including `build-field-architecture-dossiers`.
- `tests/unit/texas_rrc/` already contains focused tests for source loading,
  staged writes, quality summaries, HTML rendering, and CLI support across the
  onshore modules.

The implementation will create a new Texas RRC-local
`architecture_portfolio` package. It will consume the dossier packet rather
than moving portfolio responsibility into `dossiers` or overloading the
opportunity ranking publisher.

### Source-loading contract

The portfolio source loader will treat `root` as the Texas RRC module root,
normally `/mnt/ace/worldenergydata/data/modules/texas_rrc`, and will resolve the
input dossier directory as:

```text
root / FIELD_ARCHITECTURE_DOSSIER_DIR
```

The loader will import the dossier output constants from
`worldenergydata.texas_rrc.dossiers.io` and will load:

- `field_architecture_dossier_index.parquet` when present, otherwise
  `field_architecture_dossier_index.csv`
- `manifest.json`
- `quality.json`
- `fields/*.html` as linkable dossier page candidates

Missing index, manifest, or quality artifacts will be reported as blocking gaps:

- `missing_field_architecture_dossier_index`
- `missing_field_architecture_dossier_manifest`
- `missing_field_architecture_dossier_quality`

The loader will normalize inherited gap schema from the #702 manifest and
quality JSON. It will read blocking gaps from `manifest["blocking_source_gaps"]`
first, then `manifest["quality"]["blocking_source_gaps"]`, then
`quality["blocking_source_gaps"]`; it will read informational gaps from
`manifest["informational_source_gaps"]` first, then
`manifest["quality"]["informational_source_gaps"]`, then
`quality["informational_source_gaps"]`. It will not require or invent a
top-level `source_gaps` field for #702 artifacts. Informational gaps such as
`water_bbl` and `well_count` will remain visible in source-health output and
quality metadata without blocking publication.

The new loader will copy the #702 manifest `input_paths` into the portfolio
manifest and will separately derive `upstream_manifest_paths` from that list by
retaining paths whose filename is `manifest.json`.

### Interpretation policy

The portfolio output will remain a screening and decision-support product. It
will not claim reserves, economic value, NPV, tariffs, pipeline capacity,
product compatibility, right-of-way availability, route feasibility, or
engineered facility design. Every output artifact will preserve caveats from
the upstream RRC-derived artifacts, including lease-level production
allocation, no per-well production allocation, RRC GIS screening-only
distances, dominant county pipeline filtering, missing well GIS, and PDQ
water/well-count gaps.

### Out Of Scope

The implementation will not:

- refresh raw Texas RRC sources or rebuild upstream lifecycle, production,
  infrastructure, field-atlas, opportunity, or dossier artifacts
- scrape LinkedIn, PatchOps, or third-party datasets
- broaden the v1 portfolio beyond the bounded #702 dossier packet into statewide
  rollups from the full #695 ranking
- allocate lease-grain production to individual wells
- estimate reserves, economics, NPV, tariffs, pipeline capacity, product
  compatibility, ownership, right-of-way status, route feasibility, or
  engineered facility layout
- publish outside `/mnt/ace` except through the explicit non-ACE test/sandbox
  override described below

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-02-issue-707-texas-rrc-field-architecture-portfolio.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review - Codex initial | `scripts/review/results/2026-07-02-plan-707-codex.md` |
| Plan review - Codex focused | `scripts/review/results/2026-07-02-plan-707-codex-r2.md` |
| Plan review - Claude initial | `scripts/review/results/2026-07-02-plan-707-claude.md` |
| Plan review - Claude focused | `scripts/review/results/2026-07-02-plan-707-claude-r2.md` |
| Plan review - Gemini availability | `scripts/review/results/2026-07-02-plan-707-gemini-unavailable.md` |
| Plan review synthesis | `scripts/review/results/2026-07-02-plan-707-synthesis.md` |
| Code review - Codex | `scripts/review/results/2026-07-02-code-707-codex.md` |
| Code review - Claude | `scripts/review/results/2026-07-02-code-707-claude.md` |
| Code review - Gemini availability | `scripts/review/results/2026-07-02-code-707-gemini-unavailable.md` |
| Legal/security scan evidence | `scripts/review/results/2026-07-02-code-707-legal-sanity-scan.txt` plus issue closeout comment |
| Architecture portfolio package init | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/__init__.py` |
| Source loading | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/sources.py` |
| Portfolio models and rollups | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/models.py` |
| HTML rendering | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/html.py` |
| Quality reporting | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/quality.py` |
| Output persistence | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/io.py` |
| CLI support | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/cli_support.py` |
| CLI command | `src/worldenergydata/cli/commands/texas_rrc.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_architecture_portfolio_sources.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_architecture_portfolio_models.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_architecture_portfolio_html.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_architecture_portfolio_io.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_architecture_portfolio_quality.py` |
| CLI tests | `tests/unit/texas_rrc/test_field_architecture_portfolio_cli.py` |
| Docs | `docs/data-sources/onshore/texas-rrc/field-architecture-portfolio.md` |

## Deliverable

The deliverable will publish a Texas RRC field architecture portfolio packet
under:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_architecture_portfolio/
  field_architecture_action_queue.csv
  field_architecture_action_queue.parquet
  field_architecture_class_summary.csv
  field_architecture_class_summary.parquet
  field_architecture_followup_summary.csv
  field_architecture_followup_summary.parquet
  field_architecture_portfolio.html
  quality.json
  field_architecture_portfolio_quality.json
  manifest.json
```

`quality.json` will satisfy the generic artifact name. The component-specific
`field_architecture_portfolio_quality.json` will carry the same payload for
consistency with existing Texas RRC publishers. Tests will assert that both
files will be written with identical JSON.

### Action queue columns

`field_architecture_action_queue.csv` will be keyed by `district, field_number`
and will include:

- `portfolio_rank`
- `district`
- `field_number`
- `field_name`
- `field_slug`
- `architecture_signal_class`
- `portfolio_action`
- `followup_priority`
- `development_theme`
- `review_sequence`
- `opportunity_rank`
- `opportunity_score`
- `recommended_followup`
- `dossier_focus`
- `dossier_path`
- `source_dossier_href`
- `source_field_atlas_report_path`
- `production_maturity_class`
- `remaining_activity_score`
- `active_well_count`
- `well_count`
- `permit_count`
- `completion_count`
- `cumulative_boe`
- `production_per_well_boe`
- `infrastructure_access_class`
- `infrastructure_access_score`
- `nearest_pipeline_distance_miles`
- `top_operator_name`
- `top_operator_share`
- `source_caveats`
- `quality_flags`
- `portfolio_limitations`

### Portfolio action contract

The first implementation will map screening architecture signals to portfolio
actions as follows:

| Architecture signal class | Portfolio action | Priority sort | `followup_priority` | Development theme |
|---|---|---:|---|---|
| `low_data_confidence` | `data_completion_review` | 10 | `source_data_first` | Source/data completion before architecture interpretation |
| `infrastructure_constrained_activity` | `infrastructure_constraint_screen` | 20 | `high` | Infrastructure constraint and route/market-access evidence review |
| `high_access_infill_redevelopment` | `infill_redevelopment_screen` | 30 | `high` | Infill, recompletion, redevelopment candidate review |
| `emerging_growth` | `growth_appraisal_screen` | 40 | `medium` | Growth-field activity and infrastructure follow-up |
| `mature_harvest` | `mature_harvest_review` | 50 | `medium` | Late-life harvest, recompletion, abandonment, or surveillance review |
| `monitor_only` | `monitor_only` | 90 | `low` | Watchlist monitoring without active development recommendation |

The action labels will remain screening labels. They will not imply investment
approval, reserves, NPV, gathering system capacity, tariff access, right-of-way
availability, or engineered facility layout.

`portfolio_rank` will be assigned after sorting by priority sort, numeric
`opportunity_rank`, `district`, `field_number`, and `field_name`.
`review_sequence` will be the 1-based sequence within each `portfolio_action`
after the same secondary sort. Unknown architecture signal classes will map to
`data_completion_review`, priority sort `10`, and an
`unknown_architecture_signal_class` caveat.

### Summary tables

`field_architecture_class_summary.csv` will include one row per
`architecture_signal_class` with:

- `architecture_signal_class`
- `field_count`
- `portfolio_action`
- `development_theme`
- `mean_opportunity_score`
- `median_opportunity_score`
- `total_cumulative_boe`
- `total_active_well_count`
- `total_permit_count`
- `total_completion_count`
- `direct_or_near_access_count`
- `top_caveats`
- `top_quality_flags`

`direct_or_near_access_count` will count rows where
`infrastructure_access_class` is exactly `direct_access` or `near_access`.
`top_caveats` and `top_quality_flags` will each contain up to five non-empty
semicolon-separated tokens sorted by descending count and then ascending token
for tie breaks.

`field_architecture_followup_summary.csv` will group by
`recommended_followup`, `portfolio_action`, and `development_theme`, preserving
counts and score ranges so a user can route follow-up work without inspecting
every dossier page.

### HTML report

`field_architecture_portfolio.html` will be a self-contained portfolio report
with:

1. Source health and limitations.
2. Architecture class distribution.
3. Portfolio action queue.
4. Follow-up summary.
5. Links to the #702 dossier pages when the input and output roots are
   compatible.

If source dossier links cannot be expressed safely relative to the portfolio
output root, the report will render source paths as text and add a visible
`source_dossier_link_not_relative_to_output_root` caveat.

The relative link algorithm will be explicit and fail closed:

1. Resolve `input_dossier_dir` as `root / FIELD_ARCHITECTURE_DOSSIER_DIR`.
2. Resolve `output_analysis_root` as `output_root / "curated" / "analysis"`.
3. Resolve `portfolio_dir` as
   `output_analysis_root / "field_architecture_portfolio"`.
4. Resolve allowed dossier pages under `input_dossier_dir / "fields"`.
5. Require `input_dossier_dir.parent` and `output_analysis_root` to resolve to
   the same directory before emitting links.
6. Reject a row `dossier_path` before path construction if it contains a NUL
   byte. When `dossier_path` is relative, resolve it as
   `input_dossier_dir / row["dossier_path"]`; when it is absolute, resolve it
   directly. Never resolve relative dossier paths against the process working
   directory or the portfolio output directory.
7. Emit a link only when the resolved dossier path is under the allowed dossier
   pages directory and has an `.html` suffix.
8. Compute the href from `portfolio_dir` to the dossier page. The expected
   default shape for live #702 rows will be
   `../field_architecture_dossiers/fields/<page-name>.html`.
9. Reject hrefs that are absolute paths, contain a URL scheme, contain NUL
   bytes, or re-resolve outside the allowed dossier pages directory. Rejected
   links will be rendered as escaped text with the visible caveat above.

### Manifest

`manifest.json` will include:

- generated timestamp
- code revision
- command
- output paths
- input dossier index path
- input dossier manifest path
- input quality path
- dossier manifest `input_paths`
- upstream manifest paths derived from dossier manifest `input_paths`
- row counts for action queue, class summary, and follow-up summary
- blocking source gaps
- informational source gaps
- portfolio action vocabulary
- caveat and quality summaries
- limitations

## Pseudocode

```text
run_build_field_architecture_portfolio(
  root,
  output_root,
  dry_run,
  require_sources,
  allow_non_ace_output,
):
  inputs = load portfolio inputs from root using dossier IO constants
  blocking_gaps = validate index, manifest, quality, and inherited blocking gaps
  informational_gaps = inherit dossier manifest/quality informational gaps

  if blocking_gaps and (require_sources or not dry_run):
    raise ValueError with blocking gap names

  action_queue = build action queue from dossier index
  class_summary = summarize action queue by architecture signal class
  followup_summary = summarize action queue by recommendation/action/theme
  quality = assess row counts, actions, caveats, flags, inherited gaps

  if dry_run:
    return source health and planned row counts without writing

  if action_queue is empty:
    raise ValueError no_portfolio_candidates before writing

  write staged outputs to field_architecture_portfolio directory
  return manifest and quality
```

### CLI and output-root contract

The CLI support layer will follow existing Texas RRC publisher naming:

```text
run_build_field_architecture_portfolio(
  root: Path | str,
  output_root: Path | str,
  dry_run: bool = False,
  require_sources: bool = False,
  allow_non_ace_output: bool = False,
)
```

The IO writer will use `allow_non_ace_root: bool = False`. The Typer command
will expose `--root`, `--output-root`, `--dry-run`, `--require-sources`, and
`--allow-non-ace-output`, matching the existing dossier command convention.
Publication writes to non-`/mnt/ace` output roots will raise unless
`allow_non_ace_output` reaches the IO writer as `allow_non_ace_root=True`.
Dry-run mode will not write outputs.

## Files To Change

The implementation will add:

- `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/__init__.py`
- `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/sources.py`
- `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/models.py`
- `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/html.py`
- `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/quality.py`
- `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/io.py`
- `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio/cli_support.py`
- `tests/unit/texas_rrc/test_field_architecture_portfolio_sources.py`
- `tests/unit/texas_rrc/test_field_architecture_portfolio_models.py`
- `tests/unit/texas_rrc/test_field_architecture_portfolio_html.py`
- `tests/unit/texas_rrc/test_field_architecture_portfolio_io.py`
- `tests/unit/texas_rrc/test_field_architecture_portfolio_quality.py`
- `tests/unit/texas_rrc/test_field_architecture_portfolio_cli.py`
- `docs/data-sources/onshore/texas-rrc/field-architecture-portfolio.md`

The implementation will modify:

- `src/worldenergydata/cli/commands/texas_rrc.py`

## Task Breakdown

1. Source-loading tests will be written first, then the loader will resolve #702
   dossier outputs, normalize manifest/quality schema, and report source health.
2. Portfolio-model tests will be written next, then the action queue, priority
   mapping, review sequencing, class summary, and follow-up summary will be
   implemented.
3. HTML tests will be written next, then self-contained report rendering and
   fail-closed dossier links will be implemented.
4. IO and CLI tests will be written next, then staged writes, `/mnt/ace`
   guardrails, dry-run behavior, and the Typer command will be implemented.
5. Documentation, live `/mnt/ace` smoke output, legal/security scan, and
   code-stage adversarial review will complete the closeout sequence.

## TDD Test List

The implementation will add tests before production code for:

1. Source loading prefers dossier index Parquet when present and falls back to
   CSV.
2. Source loading reports `missing_field_architecture_dossier_index`,
   `missing_field_architecture_dossier_manifest`, and
   `missing_field_architecture_dossier_quality` as blocking gaps.
3. Source loading fixture coverage pins the #702 manifest/quality schema with
   nested `quality.blocking_source_gaps` and `quality.informational_source_gaps`
   and no required top-level `source_gaps`.
4. Source loading inherits dossier manifest blocking and informational gaps
   without treating informational gaps as blocking.
5. Action classification maps each architecture signal class to the expected
   `portfolio_action`, priority sort, `followup_priority`, and
   `development_theme`.
6. Unknown architecture signal classes map to `data_completion_review` with a
   visible `unknown_architecture_signal_class` caveat.
7. Action queue ranking is deterministic by the enumerated priority sort,
   opportunity rank, district, field number, and field name.
8. Action queue assigns `portfolio_rank` globally and `review_sequence` within
   each portfolio action.
9. Action queue preserves source caveats, quality flags, dossier paths, field
   atlas source paths, and screening limitations.
10. Class summary counts fields and aggregates scores, activity, production,
   and infrastructure metrics.
11. Class summary counts `direct_or_near_access_count` only from `direct_access`
    and `near_access`, and computes top caveat/flag tokens by the stated count
    rule.
12. Follow-up summary groups by recommendation/action/theme and preserves score
   ranges.
13. Quality reporting counts portfolio actions, development themes, caveats,
    flags, inherited blocking gaps, inherited informational gaps, and
    limitations.
14. HTML report renders source health, class distribution, action queue,
    follow-up summary, and limitations without external network assets.
15. HTML report links to dossier pages with the expected
    `../field_architecture_dossiers/fields/<page-name>.html` href when source
    paths use live-shaped `fields/<page-name>.html` values and resolve under
    the same analysis root.
16. HTML report renders dossier paths as escaped text, not links, when source
    and output roots diverge, when hrefs carry a URL scheme or absolute path,
    when path traversal would resolve outside the allowed dossier pages
    directory, or when the source path contains a NUL byte.
17. Output writer stages CSV, Parquet, HTML, quality, component quality, and
    manifest atomically under `curated/analysis/field_architecture_portfolio`.
18. Output writer records row counts, input paths, upstream manifests, command,
    code revision, action vocabulary, gaps, and limitations in `manifest.json`.
19. CLI dry-run reports source health and does not write files.
20. CLI dry-run raises on blocking source gaps when `--require-sources` is set.
21. CLI publication raises on blocking source gaps even when `--require-sources`
    is not set.
22. CLI publication rejects an empty action queue before writing outputs.
23. CLI publication writes outputs under `/mnt/ace` by default and supports
    non-ACE roots only through the `--allow-non-ace-output` flag,
    `allow_non_ace_output` support parameter, and `allow_non_ace_root` IO
    parameter chain.

## Validation Gates

Before moving #707 from implementation to closeout, the implementation worker
will verify the uv workspace environment is synced, then run and record:

```bash
uv sync --all-packages --all-extras
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync python -m pytest \
  tests/unit/texas_rrc/test_field_architecture_portfolio_sources.py \
  tests/unit/texas_rrc/test_field_architecture_portfolio_models.py \
  tests/unit/texas_rrc/test_field_architecture_portfolio_html.py \
  tests/unit/texas_rrc/test_field_architecture_portfolio_io.py \
  tests/unit/texas_rrc/test_field_architecture_portfolio_quality.py \
  tests/unit/texas_rrc/test_field_architecture_portfolio_cli.py \
  -q
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync black --check --diff \
  src/ tests/ packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync isort --check-only --diff \
  src/ tests/ packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync flake8 src/ \
  --max-line-length=100 \
  --extend-ignore=E203,W503 \
  --exclude=__pycache__,*.egg-info,.git,.venv
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync ruff check \
  packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/architecture_portfolio \
  src/worldenergydata/cli/commands/texas_rrc.py \
  tests/unit/texas_rrc/test_field_architecture_portfolio_*.py
scripts/legal/legal-sanity-scan.sh | tee scripts/review/results/2026-07-02-code-707-legal-sanity-scan.txt
```

The implementation will also receive code-stage adversarial review. Codex will
review the diff against the approved plan. Claude will serve as the second
actual reviewer when Gemini is unavailable. Gemini will still be attempted; if
the current Gemini CLI remains unavailable, the implementation worker will
write an `UNAVAILABLE` artifact with the exact authentication/client error and
will not represent the missing provider as an approval.

Implementation closeout will use a feature branch and PR. The branch will be
pushed, a PR will be opened, review and validation evidence will be posted on
the issue, and the PR will be merged before #707 can be closed. Any MAJOR
verdict from Codex or Claude will block closeout until patched or explicitly
waived by the user.

## Acceptance Criteria

- A new `worldenergydata texas-rrc build-field-architecture-portfolio` command
  will publish portfolio outputs under `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_architecture_portfolio/`.
- The command will consume direct curated #702 dossier artifacts only.
- Dry-run mode will report source health without writing outputs.
- The action queue, class summary, follow-up summary, HTML report, quality
  JSON, component quality JSON, and manifest will be written.
- The output will preserve upstream caveats, quality flags, source gaps, and
  limitations.
- The HTML report will be self-contained and will not use external network
  assets.
- Safe links to #702 dossier pages will be emitted only when the relative path
  is valid.
- Unit tests will cover source loading, action models, rollups, HTML, output
  persistence, quality reporting, and CLI behavior.
- The live `/mnt/ace` command will be run after implementation and its row
  counts, class counts, source gaps, and output paths will be reported.
- `scripts/legal/legal-sanity-scan.sh`, Black, isort, flake8, ruff, targeted
  tests, and PR CI will pass before closeout.
- Code-stage review artifacts and legal/security scan evidence will be posted on
  issue #707 before closeout.

## Risks

- The dossier packet is intentionally bounded to 37 fields. The portfolio
  report will summarize that dossier packet, not statewide Texas RRC field
  inventory.
- RRC production remains field/lease-grain and may not allocate production per
  well.
- Infrastructure access is GIS screening-grade and does not prove tie-in
  feasibility, product compatibility, tariff access, capacity, ownership, or
  right-of-way availability.
- Action labels may be mistaken for engineered architecture recommendations.
  The report will mitigate this with explicit screening language and repeated
  limitations.
- Relative links to dossier pages may become unsafe if users publish portfolio
  outputs outside the same `/mnt/ace` Texas RRC root. The implementation will
  fail closed to escaped text and visible caveats.

## Implementation Stop

Implementation will not start until this plan is reviewed, pushed, marked
`status:plan-review`, and explicitly approved by the user.
