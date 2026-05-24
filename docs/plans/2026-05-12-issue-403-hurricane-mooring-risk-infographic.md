# Plan for #403: feat(marketing): hurricane mooring risk-avoidance infographic from incident data

> **Status:** plan-review
> **Complexity:** T2
> **Date:** 2026-05-12
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/403
> **Review artifacts:** scripts/review/results/2026-05-12-plan-403-codex.md | scripts/review/results/2026-05-12-plan-403-gemini.md | scripts/review/results/2026-05-12-plan-403-synthesis.md

---

## Resource Intelligence Summary

### Existing repo code and artifacts
- Found: `src/worldenergydata/cli/commands/marine_safety.py` — marine safety CLI command surface exists, but the hurricane/mooring infographic is currently report-artifact work rather than a reusable report generator.
- Found: `reports/modules/marketing/marketing_brochure_marine_safety_incident_analysis.md` — existing marine-safety marketing copy; not the hurricane/mooring decision-tree infographic.
- Found: `reports/modules/marketing/hurricane_mooring_safety_infographic.html` and `reports/modules/marketing/hurricane_mooring_safety_infographic_stats.json` — current prior draft artifacts. Adversarial review correctly noted these are not purely generic; they already contain partial hurricane-readiness positioning. Implementation must preserve them as **prior/reference draft artifacts**, then create a revised artifact only for concrete deltas: metric contract, interactive evidence sections, clearer caveats, and stronger decision-tree positioning.
- Found: `reports/modules/marketing/assets/hurricane_mooring_safety_infographic.png` and `.pdf` — prior static exports. These are binary artifacts and must not be duplicated in git without explicit size/policy gate.
- Gap: no committed deterministic generator/validator currently owns the hurricane mooring infographic statistics/artifact contract.

### Standards
- Repo visualization/reporting rules from `worldenergydata/CLAUDE.md`: use interactive HTML for visualizations, include data attribution, and include timestamp. This plan now treats those as acceptance-tested requirements.

### LLM Wiki pages consulted
- Not consulted for this plan. The source-of-truth content is the user-provided DOCX plus `worldenergydata` incident CSVs. Implementation must not add domain claims beyond these inputs unless it adds source-backed citations in a follow-up plan.

### Documents and data consulted
- Issue #403 — created in response to the user request; this is the implementation tracking issue.
- `/home/vamsee/Downloads/Hurricane Planning and Mooring R0-4revisions.docx` — reviewed source document. Key themes: hurricane preparation planning, mooring analysis, port/refuge decision trees, dock geometry, bollard/fender loads, storm surge, changing wind/wave/current directions, crew readiness, and survivability by storm category.
- `data/modules/marine_safety/input/fatality_incidents.csv` — 20 fatality incident rows.
- `data/modules/marine_safety/input/foundering_incidents.csv` — 15 foundering/loss-of-vessel pathway rows.
- `data/modules/marine_safety/input/hatch_incidents.csv` — 30 hatch/watertight integrity rows, including 20 event rows and 10 explicit `None`/non-incident controls.
- `reports/modules/marketing/hurricane_mooring_safety_infographic_stats.json` — prior draft stats: 65 total incidents, 60 fatalities, 24 weather/water-related records, 40 weather/water-related fatalities, 12 critical/high hatch records, 38 foundering fatalities. These prior numbers are reference-only until recomputed by the hardened metric contract below.

### Gaps identified
- Need to preserve current prior draft artifacts with clear reference naming before writing revised artifacts.
- Need deterministic stats builder that recomputes counts from CSV source files and includes matched incident IDs for each headline bucket.
- Need revised self-contained interactive HTML that positions the message as "avoidable risk pathways via pre-storm mooring analysis and decision timing" rather than a generic incident dashboard.
- Need validator/tests proving required HTML sections, timestamp, source provenance, caveats, matched-ID traceability, and stats consistency.

### Evidence

**Issue status** (verified 2026-05-12T09:26:18Z via `gh issue view`):
- `#403` — OPEN — `feat(marketing): hurricane mooring risk-avoidance infographic from incident data` — https://github.com/vamseeachanta/worldenergydata/issues/403 — labels: `enhancement`, `priority:medium`, `cat:data`, `cat:business`

**File existence** (`stat` 2026-05-12T09:26:18Z):
- EXISTS: `/home/vamsee/Downloads/Hurricane Planning and Mooring R0-4revisions.docx` — 20,011 bytes
- EXISTS: `data/modules/marine_safety/input/fatality_incidents.csv` — 3,324 bytes
- EXISTS: `data/modules/marine_safety/input/foundering_incidents.csv` — 2,464 bytes
- EXISTS: `data/modules/marine_safety/input/hatch_incidents.csv` — 4,577 bytes
- EXISTS: `reports/modules/marketing/hurricane_mooring_safety_infographic.html` — 14,553 bytes
- EXISTS: `reports/modules/marketing/hurricane_mooring_safety_infographic_stats.json` — 743 bytes
- EXISTS: `reports/modules/marketing/assets/hurricane_mooring_safety_infographic.png` — 1,041,150 bytes
- EXISTS: `reports/modules/marketing/assets/hurricane_mooring_safety_infographic.pdf` — 504,631 bytes
- EXISTS: `reports/modules/marketing/marketing_brochure_marine_safety_incident_analysis.md` — 3,344 bytes
- EXISTS: `src/worldenergydata/cli/commands/marine_safety.py` — 32,109 bytes

**CSV shape proof** (`uv run python` 2026-05-12T09:26:18Z):
```json
{
  "fatality_incidents.csv": {"rows": 20, "columns": ["incident_id", "date", "vessel_name", "description", "fatalities", "cause_of_death", "location"]},
  "foundering_incidents.csv": {"rows": 15, "columns": ["incident_id", "date", "vessel_name", "description", "fatalities", "location"]},
  "hatch_incidents.csv": {"rows": 30, "columns": ["incident_id", "date", "vessel_name", "description", "severity", "location"]}
}
```

**Verified baseline counts** (`uv run python` 2026-05-12T09:31Z):
- Total rows across source CSVs: 65.
- Total fatalities from `fatalities` fields in fatality + foundering CSVs: 60.
- Foundering/loss-of-vessel pathway rows: 15.
- Foundering fatalities: 38.
- Hatch severity counts: `Critical=6`, `High=6`, `Medium=7`, `Low=1`, `None=10`.
- Hatch event rows excluding `severity=None` controls: 20.
- Critical/high hatch event rows: 12 (`12/20 = 60%` of hatch event rows; `12/30 = 40%` of all hatch CSV records including controls).

**Document excerpt proof** (`docx` XML text extraction 2026-05-12T09:20:20Z):
```text
Planning ahead should include a proper mooring analysis considering dock side geometry (bollards and bulkhead configuration), exposure to waves and currents under hurricane surge conditions, and varying wind speeds from all directions. ... A decision tree can then be prepared to enable decisions to be made to move the vessel to alternative sites depending on the predicted severity of the hurricane and the proximity of its path.
```

**Reproduction proofs**:
- N/A — artifact refresh/data-backed infographic issue, not an alleged runtime bug. Implementation must still start with failing validator/tests for the stats/artifact contract before changing artifacts.

---

## Metric Contract

Implementation must use these exact metric definitions unless tests and review artifacts are updated first:

| Metric | Definition | Required traceability |
|---|---|---|
| `dataset_total_records` | Count of rows across the three source CSVs. | Source file row counts. |
| `dataset_total_fatalities` | Sum of numeric `fatalities` fields from `fatality_incidents.csv` and `foundering_incidents.csv`; hatch CSV has no fatalities field. | Source file sums. |
| `foundering_pathway_records` | All rows in `foundering_incidents.csv`, described as foundering/loss-of-vessel pathway evidence, not hurricane-only evidence. | `matched_incident_ids.foundering_pathway`. |
| `foundering_pathway_fatalities` | Sum of `fatalities` in `foundering_incidents.csv`. | Matched IDs + sum. |
| `hatch_watertight_event_records` | Rows in `hatch_incidents.csv` where `severity != "None"`. | `matched_incident_ids.hatch_watertight_events`. |
| `hatch_control_records` | Rows in `hatch_incidents.csv` where `severity == "None"`; these are controls/non-incidents and must not be counted as risk events. | `excluded_incident_ids.hatch_controls`, including `NI002` and `NI010`. |
| `critical_high_hatch_events` | Hatch event rows with severity `Critical` or `High`; report denominator explicitly as both event-row denominator and all-hatch-record denominator if both are shown. | Matched IDs + denominator labels. |
| `direct_weather_or_water_exposure_events` | Rows from fatality/foundering/hatch event rows whose **description/cause text** directly indicates exposure, flooding, sinking/capsizing/foundering, rough/heavy/severe weather, storm, typhoon, rogue wave, water ingress, or overboard/drowning. Exclude `severity=None` controls and explicitly successful/preventive rows. | Matched IDs, keyword group, excluded IDs, and caveat. |

Mandatory caveat in stats JSON and HTML:
> These marine-safety records show incident pathways relevant to hurricane mooring readiness. They are not a hurricane-only or hurricane-caused incident sample.

Mandatory adversarial examples:
- `NI002` (`all hatches and doors verified secure`) is a non-incident control and must be excluded from weather/water risk-event counts.
- `NI010` (`Weather routing system helped avoid severe storm, voyage successful`) is a preventive/control row and must be excluded from loss-event counts, though it may be referenced as a positive control if explicitly labeled.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-05-12-issue-403-hurricane-mooring-risk-infographic.md` |
| Issue body | https://github.com/vamseeachanta/worldenergydata/issues/403 |
| Plan review — Codex-style | `scripts/review/results/2026-05-12-plan-403-codex.md` |
| Plan review — Gemini-style | `scripts/review/results/2026-05-12-plan-403-gemini.md` |
| Plan review synthesis | `scripts/review/results/2026-05-12-plan-403-synthesis.md` |
| Preserve prior draft HTML | `reports/modules/marketing/reference_hurricane_mooring_safety_infographic_prior_draft.html` |
| Preserve prior draft stats | `reports/modules/marketing/reference_hurricane_mooring_safety_infographic_prior_draft_stats.json` |
| Preserve prior draft PNG, if committed/approved | `reports/modules/marketing/assets/reference_hurricane_mooring_safety_infographic_prior_draft.png` |
| Preserve prior draft PDF, if committed/approved | `reports/modules/marketing/assets/reference_hurricane_mooring_safety_infographic_prior_draft.pdf` |
| Revised HTML infographic | `reports/modules/marketing/hurricane_mooring_risk_avoidance_infographic.html` |
| Revised stats/provenance JSON | `reports/modules/marketing/hurricane_mooring_risk_avoidance_infographic_stats.json` |
| Revised static exports, optional/policy-gated | `reports/modules/marketing/assets/hurricane_mooring_risk_avoidance_infographic.{png,pdf}` |
| Generator script | `scripts/marketing/generate_hurricane_mooring_risk_infographic.py` |
| Validator/test | `tests/modules/marketing/test_hurricane_mooring_risk_infographic.py` |
| Plans index update | `docs/plans/README.md` |

---

## Deliverable

A preserved reference copy of the current prior draft infographic plus a revised, self-contained interactive HTML hurricane mooring risk-avoidance infographic with deterministic statistics/provenance JSON and validation coverage.

---

## Recommended positioning

Primary headline:
> Hurricane mooring analysis turns marine incident pathways into avoidable planning decisions.

Core message hierarchy:
1. **Risk pathway:** foundering, flooding/water ingress, severe-weather exposure, overboard/drowning, and hatch/watertight failures are incident pathways relevant to hurricane mooring readiness.
2. **Decision lever:** pre-storm analysis of mooring layout, bollard/fender capacity, storm surge, wind/current directions, and relocation timing reduces exposure before the storm track locks in.
3. **Operational proof:** incident data provides pathway counts/fatality/severity context; the DOCX provides the mitigation framework; the artifact must not imply the incidents were all hurricane-caused.
4. **Call to action:** convert site/vessel constraints into a storm-category survivability plot and port/refuge decision tree before hurricane season.

Concrete delta versus prior draft:
- use explicit metric contract and matched incident IDs;
- add visible timestamp and machine-readable `generated_utc`;
- add interactive HTML details/tooltips/expandable evidence sections for source rows;
- strengthen caveat language and denominator labeling;
- preserve prior draft under reference naming instead of overwriting it.

Avoid:
- claiming all 65 records are hurricane incidents;
- implying causation not present in the CSVs;
- burying the hurricane-planning decision tree behind generic incident-dashboard styling;
- committing duplicate binary exports without approval.

---

## Pseudocode

```text
function load_incident_sources(input_dir):
    read fatality, foundering, hatch CSVs with csv.DictReader
    normalize date fields and numeric fatalities
    tag each row with source_file and dataset
    return row lists plus relative source paths

function compute_metric_contract(rows):
    total rows = all rows
    total fatalities = fatality fatalities + foundering fatalities
    foundering pathway = all foundering rows
    hatch events = hatch rows where severity != None
    hatch controls = hatch rows where severity == None
    direct weather/water exposure events = fatality + foundering + hatch-event rows matching exact keyword groups, excluding preventive/control language
    for every headline bucket, include matched_incident_ids and denominator labels
    include caveat and generated_utc timestamp

function render_interactive_html(stats, document_themes):
    produce self-contained HTML with stat tiles, pathway bars, hatch severity grid, decision-tree section, mitigation checklist, provenance footer
    include <details> evidence panels or lightweight JS toggles/tooltips listing matched IDs and source paths
    include visible generated timestamp and caveat

function preserve_prior_draft_once(paths):
    if reference file exists, do not overwrite it
    if prior draft file exists and reference missing, move/copy preserving byte content
    binary PNG/PDF preservation requires policy gate; otherwise leave existing binaries untouched and document them in JSON

function validate_artifacts(stats_path, html_path):
    assert stats counts match recomputation from CSVs
    assert matched/excluded ID lists include required adversarial examples
    assert HTML includes headline, decision lever sections, caveat, timestamp, source file names, DOCX filename, and interactive evidence element(s)
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `scripts/marketing/generate_hurricane_mooring_risk_infographic.py` | lightweight deterministic report generator/validator owner |
| Create | `tests/modules/marketing/test_hurricane_mooring_risk_infographic.py` | TDD tests for stats/provenance/HTML contract |
| Preserve | `reports/modules/marketing/hurricane_mooring_safety_infographic.html` → `reports/modules/marketing/reference_hurricane_mooring_safety_infographic_prior_draft.html` | keep prior draft as requested |
| Preserve | `reports/modules/marketing/hurricane_mooring_safety_infographic_stats.json` → `reports/modules/marketing/reference_hurricane_mooring_safety_infographic_prior_draft_stats.json` | keep prior draft stats for reference |
| Preserve only if approved | `reports/modules/marketing/assets/hurricane_mooring_safety_infographic.png` → `reports/modules/marketing/assets/reference_hurricane_mooring_safety_infographic_prior_draft.png` | binary reference; avoid duplicate commit unless approved |
| Preserve only if approved | `reports/modules/marketing/assets/hurricane_mooring_safety_infographic.pdf` → `reports/modules/marketing/assets/reference_hurricane_mooring_safety_infographic_prior_draft.pdf` | binary reference; avoid duplicate commit unless approved |
| Create | `reports/modules/marketing/hurricane_mooring_risk_avoidance_infographic.html` | revised positioned interactive infographic |
| Create | `reports/modules/marketing/hurricane_mooring_risk_avoidance_infographic_stats.json` | deterministic source-backed stats/provenance |
| Optional/policy-gated | `reports/modules/marketing/assets/hurricane_mooring_risk_avoidance_infographic.{png,pdf}` | static exports only if approved and size-safe |
| Update | `docs/plans/README.md` | add plan index row |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_stats_recomputed_from_source_csvs` | source CSV row/fatality counts | source CSV directory | total records 65; source rows 20/15/30; fatalities 60 |
| `test_metric_contract_separates_pathways` | foundering, hatch event, hatch control, and direct weather/water buckets are distinct | source rows | foundering IDs separate from hatch IDs; hatch controls excluded from event counts |
| `test_weather_water_false_positive_controls_excluded` | `NI002` and `NI010` do not inflate loss-event counts | `hatch_incidents.csv` | IDs appear in `excluded_incident_ids.hatch_controls`, not matched risk events |
| `test_hatch_severity_counts_are_exact` | hatch severity grid reflects source values | `hatch_incidents.csv` | Critical=6, High=6, Medium=7, Low=1, None=10; critical/high event denominator clear |
| `test_stats_json_has_traceability_and_timestamp` | JSON includes `generated_utc`, source paths, caveat, matched IDs | generated stats | UTC timestamp pattern, relative source paths, caveat, matched/excluded ID arrays |
| `test_rendered_html_contains_required_positioning` | revised HTML includes decision-tree and mooring-analysis risk-avoidance narrative | generated stats | headline, decision lever sections, call to action, caveat |
| `test_rendered_html_is_interactive_and_provenanced` | HTML includes interactive evidence element(s), visible timestamp, and provenance | generated HTML | `<details>` or JS toggle/tooltips, CSV paths, DOCX filename, generated timestamp |
| `test_reference_artifact_preservation_is_idempotent` | prior reference preservation does not repeatedly rename or mutate references | reports path | reference files are preserved; second run is a no-op |
| `test_binary_exports_are_policy_gated` | PNG/PDF generation/preservation is optional and skips cleanly without approval/tools | default generator args | HTML+JSON generated; binary writes skipped unless flag enabled |
| `test_html_avoids_hurricane_causation_claims` | copy does not imply hurricane-only dataset or unsupported causation | generated HTML | required caveat present; banned phrases absent |

---

## Acceptance Criteria

- [ ] User approval received after plan-review before implementation starts; issue label moved to `status:plan-approved` only after approval.
- [ ] Previous prior-draft HTML/JSON infographic artifacts are retained under `reference_hurricane_mooring_safety_infographic_prior_draft*` names.
- [ ] PNG/PDF prior/new static exports are not duplicated into git unless explicitly approved and size-safe; default implementation produces HTML+JSON.
- [ ] Revised interactive HTML exists at `reports/modules/marketing/hurricane_mooring_risk_avoidance_infographic.html`.
- [ ] Revised stats/provenance JSON exists and is recomputed from the three source CSVs.
- [ ] Stats JSON includes `generated_utc`, relative source paths, caveat text, matched incident IDs, excluded control IDs, and denominator labels.
- [ ] The artifact displays verified incident counts/statistics from source files, including total records, total fatalities, foundering pathway records/fatalities, hatch/watertight severity counts, and direct weather/water exposure pathway counts where supported by the metric contract.
- [ ] The narrative explicitly states the CSVs show marine incident pathways relevant to hurricane readiness, not a hurricane-only or hurricane-caused incident sample.
- [ ] The artifact includes visible data provenance, DOCX filename provenance, and visible generated timestamp.
- [ ] Targeted validation passes: `uv run pytest tests/modules/marketing/test_hurricane_mooring_risk_infographic.py -v`.
- [ ] Generator smoke passes: `uv run python scripts/marketing/generate_hurricane_mooring_risk_infographic.py --output-dir reports/modules/marketing`.
- [ ] Plan review artifacts are committed under `scripts/review/results/`.

---

## Adversarial Review Summary

| Provider | Verdict | Key findings |
|---|---|---|
| Codex-style | MAJOR | Loose weather/water classifier would inflate stats; timestamp/provenance not tested; static HTML ambiguity; binary bloat risk. |
| Gemini-style | MAJOR | Current artifact already has partial positioning; plan needed issue-traceability correction; classification contract underspecified; scope contradiction around generator/tests. |

**Overall result:** MAJOR findings addressed in this revised plan; now parked at `plan-review` for user approval before implementation.

Revisions made based on review:
- Reclassified current artifact as prior positioned draft/reference rather than purely generic.
- Added explicit metric contract, matched-ID traceability, negative controls, denominators, and caveat.
- Promoted timestamp/provenance/interactivity into acceptance criteria and tests.
- Added binary artifact gating; default deliverables are HTML+JSON.
- Clarified issue #403 is the new implementation tracking issue.
- Clarified this is a lightweight report-generator/validator implementation, not broad domain-code expansion.

---

## Risks and Open Questions

- **Risk:** incident CSVs appear to be small sample/demo data. Infographic must label dataset scope and avoid implying comprehensive industry-wide hurricane statistics.
- **Risk:** external DOCX path is outside repo and not durable. Implementation may cite filename and extracted themes, but must not commit the original DOCX unless explicitly approved.
- **Risk:** static PNG/PDF assets can add binary weight. Default is no new binary commit without explicit approval.
- **Open for approval:** Is HTML+JSON sufficient for this pass, with PNG/PDF deferred or generated outside git if needed?

---

## Complexity: T2

**T2** — one lightweight deterministic generator script, one targeted test module, artifact preservation, generated interactive HTML/JSON outputs, and marketing-data positioning with provenance constraints.
