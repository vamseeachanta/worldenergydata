# Plan for #334: annual operator disclosures dataset for year-over-year project cost tracking

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-04-21
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/334
> **Review artifacts:** scripts/review/results/2026-04-21-plan-334-codex.md | scripts/review/results/2026-04-21-plan-334-gemini.md

---

## Resource Intelligence Summary

### Existing repo code
- Found: `src/worldenergydata/cost/data_collection/public_dataset.py` — current cost dataset is a curated list of sanctioned-project cost points sourced from annual reports, SEC filings, press releases, NPD/NSTA filings, and BOEM studies; records are keyed to one project cost datapoint at sanction/FID time.
- Found: `src/worldenergydata/cost/data_collection/calibration_schema.py` — `CostDataPoint` models one project cost datapoint with sanction/drilling year, source string, and confidence, but no recurring annual disclosure structure.
- Found: `src/worldenergydata/cost/calibration/cost_predictor.py` — current model consumes `CostDataPoint` records and extracts features from sanction-oriented fields (`water_depth_m`, `well_depth_m`, `year_sanction`, `hpht`, `subsea`, `region`, `rig_type`, `water_depth_band`).
- Found: `src/worldenergydata/cost/__init__.py` and `src/worldenergydata/cost/data_collection/__init__.py` — current public exports only expose `CostDataPoint` and `load_public_dataset()` for the data-collection layer.
- Found: `tests/unit/cost/test_cost_predictor.py` and `tests/unit/cost/test_proxy_comparison.py` — existing cost tests assume the sanction-point dataset and predictor workflow.
- Gap: no annual disclosure schema, no annual operator/project time-series dataset, and no dedicated tests for disclosure-style cost tracking.

### Standards
- Not applicable — this is a repository data-modeling issue rather than an engineering standards-transfer issue.

### LLM Wiki pages consulted
- No relevant wiki pages in this repo were found for cost disclosure schema design; the implementation surface is localized to the `worldenergydata.cost` package.

### Documents consulted
- Issue `#334` — defines the requested outcome: annual-statement-driven year-over-year operator/project cost tracking.
- Issue `#143` (`WRK-261: BSEE field economics case study — rebuild on calibrated cost data`) — confirms there is already downstream demand for richer cost/calibration inputs.
- `README.md` — confirms WorldEnergyData positions economics/reporting as core capabilities and already exposes BSEE/FDAS economic workflows.
- `module-manifest.yaml` — confirms economics-relevant modules already exist in `bsee`, `fdas`, `lower_tertiary`, `sodir`, `ukcs`, and `brazil_anp`, so the new disclosure layer should be designed as reusable data infrastructure rather than a one-off BSEE-only feature.

### Gaps identified
- No schema exists for annual operator disclosures with `fiscal_year`, filing/report type, page references, quoted text, or metric-level provenance.
- No curated dataset exists for project cost revisions across multiple years for the same project.
- No curated dataset exists for operator-level annual capex series adjacent to the current sanctioned project dataset.
- No tests currently prove a project can be represented as a true time series rather than a single sanction datapoint.
- No public module exports currently expose a disclosure-layer loader or schema.

### Evidence (embedded verification)

**Issue statuses** (verified 2026-04-21T19:37:19-05:00 via `gh issue view`):
- `#334` — OPEN — `feat(cost): annual operator disclosures dataset for year-over-year project cost tracking`
- `#143` — OPEN — `WRK-261: BSEE field economics case study — rebuild on calibrated cost data (WRK-019 + WRK-171)`

**File existence** (verified 2026-04-21T19:37:19-05:00):
- EXISTS: `src/worldenergydata/cost/data_collection/public_dataset.py`
- EXISTS: `src/worldenergydata/cost/data_collection/calibration_schema.py`
- EXISTS: `src/worldenergydata/cost/calibration/cost_predictor.py`
- EXISTS: `tests/unit/cost/test_cost_predictor.py`
- MISSING (new — this plan creates): `src/worldenergydata/cost/data_collection/operator_disclosures_schema.py`
- MISSING (new — this plan creates): `src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py`
- MISSING (new — this plan creates): `tests/unit/cost/test_operator_disclosures.py`

**Line excerpts**
```text
public_dataset.py:1-23
ABOUTME: Curated public dataset of sanctioned project cost data points.
ABOUTME: All entries sourced from publicly disclosed operator reports and announcements.
Every entry cites a specific public source (operator annual report, SEC filing,
press release, NPD/NSTA filing, or BOEM study).
...
- Company 10-K / 20-F filings (SEC EDGAR, publicly accessible)
```

```text
public_dataset.py:42-67
# Each entry is a dict ready to unpack into CostDataPoint(**entry).
# Costs are as-reported USD MM at time of FID announcement.
...
"year_sanction": 2017,
...
"source": (
    "BP FID press release Jan 2017; BP Annual Report 2017 p.38 — "
    "'Mad Dog Phase 2 sanctioned at ~$9B revised down from ~$20B'"
),
```

```text
calibration_schema.py:85-153
class CostDataPoint(BaseModel):
    project_name: str
    region: str
    water_depth_m: float
    water_depth_band: WaterDepthBand
    well_depth_m: Optional[float]
    well_depth_band: Optional[WellDepthBand]
    operator: str
    year_sanction: int
    year_drilling: Optional[int]
    rig_type: RigType
    activity_type: ActivityType
    hpht: bool
    subsea: SubseaType
    cost_usd_mm: float
    cost_type: CostType
    source: str
    confidence: Confidence
```

```text
cost_predictor.py:96-126
_extract_features(records: list[CostDataPoint])
    rows.append({
        "water_depth_m": rec.water_depth_m,
        "well_depth_m": ...,
        "year_sanction": float(rec.year_sanction),
        "hpht": 1.0 if rec.hpht else 0.0,
        "subsea": rec.subsea.value,
        "region": rec.region,
        "rig_type": rec.rig_type.value,
        "water_depth_band": rec.water_depth_band.value,
    })
```

**Gap proofs**
- `test -f tests/unit/cost/test_operator_disclosures.py || echo missing` → `missing`
- `test -f src/worldenergydata/cost/data_collection/operator_disclosures_schema.py || echo missing` → `missing`
- `test -f src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py || echo missing` → `missing`

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md` |
| Tests | `tests/unit/cost/test_operator_disclosures.py` |
| Implementation | `src/worldenergydata/cost/data_collection/operator_disclosures_schema.py` |
| Implementation | `src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py` |
| Implementation | `src/worldenergydata/cost/data_collection/__init__.py` |
| Implementation | `src/worldenergydata/cost/__init__.py` |
| Plan review — Codex | `scripts/review/results/2026-04-21-plan-334-codex.md` |
| Plan review — Gemini | `scripts/review/results/2026-04-21-plan-334-gemini.md` |

---

## Deliverable

A disclosure-oriented cost data layer that models annual operator/project cost disclosures as provenance-rich time-series records, ships with a curated seed dataset, and is publicly loadable beside the existing sanction-point calibration dataset.

---

## Pseudocode

```text
class FilingType(Enum):
    define annual_report, ten_k, twenty_f, investor_presentation, regulator_pdo, regulator_fdp, press_release, media_confirmed

class DisclosureMetricName(Enum):
    define sanctioned_capex, revised_capex, remaining_capex, upstream_capex, offshore_capex, exploration_spend, decommissioning_provision, first_oil_target, plateau_target, subsea_count, well_count

class OperatorDisclosureRecord(BaseModel):
    validate operator, fiscal_year, filing_type, metric_name, metric_value, currency, unit, source_title_or_url, page_reference, quoted_text, confidence
    allow optional project_name / basin / country / project_phase

function load_operator_disclosures_dataset():
    iterate curated raw records
    instantiate OperatorDisclosureRecord for each record
    return validated list

function get_project_timeseries(records, project_name):
    filter records by project_name
    sort by fiscal_year then metric_name
    return filtered list

function get_operator_annual_metrics(records, operator, metric_name):
    filter by operator and metric
    sort by fiscal_year
    return filtered list

update package exports:
    expose OperatorDisclosureRecord, FilingType, DisclosureMetricName, load_operator_disclosures_dataset
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `src/worldenergydata/cost/data_collection/operator_disclosures_schema.py` | schema for annual operator/project disclosure records |
| Create | `src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py` | curated disclosure-oriented seed dataset + loader |
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export new schema/loader alongside current sanction-point dataset |
| Modify | `src/worldenergydata/cost/__init__.py` | expose disclosure-layer API at package entry point |
| Create | `tests/unit/cost/test_operator_disclosures.py` | TDD coverage for schema, loader, provenance, and time-series behavior |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_operator_disclosure_record_requires_core_fields` | schema rejects missing required provenance/value fields | record missing `fiscal_year` or `metric_value` | validation error |
| `test_load_operator_disclosures_dataset_returns_validated_records` | loader returns validated disclosure records | seed dataset | non-empty `list[OperatorDisclosureRecord]` |
| `test_dataset_contains_multiple_filing_types` | dataset is not reduced to one source style | seed dataset | includes annual report / SEC or regulator filing types |
| `test_dataset_contains_year_over_year_project_series` | at least one project has >1 fiscal year record | records filtered for one project | two or more years represented |
| `test_dataset_contains_operator_level_annual_series` | operator-level annual metrics are modeled separately from project rows | records filtered by operator-level metric | non-empty ordered series |
| `test_records_capture_page_reference_or_quote_support` | provenance quality exceeds current free-text source-only pattern | seed dataset | page reference or quoted text present where expected |
| `test_public_exports_include_disclosure_loader` | public package API exposes new disclosure layer | import from `worldenergydata.cost` and `.data_collection` | names resolve |

---

## Acceptance Criteria

- [ ] `tests/unit/cost/test_operator_disclosures.py` passes under the repo test command
- [ ] New schema exists for annual operator/project disclosure records with explicit provenance fields
- [ ] Curated seed dataset exists and loads successfully via public loader
- [ ] At least one project is represented as a true multi-year time series rather than a single sanction datapoint
- [ ] At least one operator-level annual metric series is represented in the seed dataset
- [ ] New disclosure layer is exported without breaking the existing `CostDataPoint` / `load_public_dataset()` interface
- [ ] Review artifacts for this plan exist under `scripts/review/results/`

---

## Adversarial Review Summary

| Provider | Verdict | Key findings |
|---|---|---|
| Codex | MAJOR | Schema type model is underspecified; linkage/integration deliverables are not planned strongly enough; current v1 scope is still too broad for the stated acceptance surface |
| Gemini | MINOR | Add explicit operator-vs-project scope typing, make helper API decision explicit, and cap v1 seed dataset size |

**Overall result:** FAIL (revision required before approval stage)

Revisions made based on review:
- None yet — cross-review completed, but the plan remains blocked on the Codex MAJOR findings and is not approval-ready.

---

## Risks and Open Questions

- **Risk:** annual reports are not uniform across operators; the first dataset may need a narrower v1 metric vocabulary than the issue body implies.
- **Risk:** mixed currency disclosures and region-specific reporting conventions can cause misleading comparability if normalization rules are over-scoped in v1.
- **Risk:** if the plan tries to wire predictor/training consumers immediately, scope could expand beyond the requested data-layer foundation.
- **Open:** should v1 include helper query functions (`get_project_timeseries`, `get_operator_annual_metrics`) as public API, or should it ship only schema + loader + dataset?
- **Open:** should the seed dataset be intentionally small and hand-curated (for provenance quality) before any scraper/import automation is planned as a follow-up issue?

---

## Complexity: T2

**T2** — this is a bounded multi-file data-model addition with new tests and package exports, but it does not require immediate cross-module integration or new external automation in v1.
