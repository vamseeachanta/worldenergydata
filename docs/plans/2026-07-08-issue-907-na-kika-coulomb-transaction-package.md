# Plan for #907: Na Kika / Coulomb transaction lifecycle and economics package

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-07-08
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/907
> **Client:** N/A
> **Project:**
> **Lane:** lane:codex
> **Review artifacts:** scripts/review/results/2026-07-08-plan-907-claude.md | scripts/review/results/2026-07-08-plan-907-codex-r1.md | scripts/review/results/2026-07-08-plan-907-codex-subagent.md | scripts/review/results/2026-07-08-plan-907-codex-followup.md | scripts/review/results/2026-07-08-plan-907-gemini.md

---

## Resource Intelligence Summary

### Existing Repo Code

- `reports/field_development/portfolio/_research.json` will supply the curated Coulomb field-development correction: Coulomb is a field-level `subsea_tieback` to the Na Kika semisub host, not a standalone semisub FPS.
- `reports/field_development/bsee_matched/_summary.json` will require correction or explicit override handling because Ariel, Kepler, Fourier, East Anstey, and Coulomb are currently recorded with `actual: semisub_fps`, which conflates host type with field concept for tieback fields.
- `reports/field_development/bsee_matched/` already carries per-field HTML outputs for `ariel`, `kepler`, `fourier`, `east-anstey`, and `coulomb`; no `herschel`, `isabela`, or `galapagos` page was observed in the targeted file check.
- `scripts/field_development/build_fdp_portfolio_matched.py` will be the nearest generator pattern for BSEE-matched field pages and index generation.
- `scripts/lower_tertiary/build_lifecycle_posters.py` will be the nearest lifecycle-poster generator pattern, but this issue should not add Na Kika to Lower Tertiary Wilcox reports because Na Kika/Coulomb are Miocene assets.
- `scripts/lower_tertiary/generate_field_economics_report.py` and `config/analysis/lower_tertiary/economic_assumptions.yml` will be reference patterns for economics reporting and price/fiscal assumptions, not the final home for Na Kika.

### Standards

Not applicable. This is a public-data/reporting feature, not an engineering-code standard implementation.

### LLM Wiki Pages Consulted

No relevant wiki page will be touched by this issue. `Client: N/A` applies.

### Documents Consulted

- Issue #907 — source request and acceptance sketch for a transaction/lifecycle/economics package.
- Shell release, 2026-06-30 — transaction scope, $1.7B total buyer consideration, Na Kika 50% non-operated working interest, 100% Coulomb tieback sale, Talos and Ridgewood buyer subsidiaries, BP preferential-right condition, ORRI/upside/decommissioning/offtake terms, 2025 Shell entitlement production, and Shell reserve figures.
- Talos release, 2026-06-30 — Talos $850M cash consideration net to Talos, expected final Talos net cash consideration of about $450-500M, Talos 50% Coulomb operated interest, Talos 25% BP-operated Na Kika interest, Ridgewood affiliate co-buyer context, named fields Kepler/Ariel/Fourier/Herschel, Q1 2026 production, oil mix, proved/probable reserve figures, upside sharing, financing, and closing conditions.
- BP Herschel Expansion release — Herschel Expansion location, Na Kika tieback context, three-well phase, and platform capacity context.
- `docs/domains/field-development/README.md` — field-development playbook architecture: field parameters -> `FieldConcept` -> recommendation engine -> deterministic diagrams.
- `docs/domains/field-development/calibration-v2.md` — host-enrichment warning that facility joins can mislabel tieback satellites with host concept and should be corrected to `subsea_tieback` where supported.
- `docs/plans/2026-05-03-issue-375-per-field-economics-10-lt-fields.md` — per-field economics plan pattern and citation concerns.
- `docs/plans/2026-05-03-issue-377-lt-comprehensive-report-assembly.md` — report assembly plan pattern for regenerable Markdown/HTML outputs.
- Drive index search via `/mnt/local-analysis/workspace-hub/scripts/data/drive-index-search/search.py` — exact filtered searches for `Na Kika`, `Coulomb`, `Talos`, `Ridgewood`, `Herschel`, `Kepler`, `Ariel`, `Fourier`, and `East Anstey` returned no directly relevant local drive document paths after filtering; broad raw search produced false positives such as Shell Prelude and unrelated "East" tokens.

### Gaps Identified

- No structured transaction facts dataset exists for Na Kika/Coulomb.
- No explicit buyer-allocation model exists for the Shell seller leg, Talos buyer leg, and Ridgewood buyer leg.
- No transaction-package renderer exists for acquisition metrics, source provenance, and lifecycle/economics readiness.
- No standalone Na Kika / Coulomb lifecycle page exists for this transaction package.
- No economics-readiness artifact exists that states which BSEE production inputs are present, absent, stale, or blocked before field economics can be calculated.
- No report output exists under a transaction-specific `reports/field_development/transactions/` namespace.
- Current BSEE-matched field concept outputs will need an explicit host-vs-field concept boundary so Coulomb/tiebacks do not inherit Na Kika host type as their field concept.
- Herschel / Herschel Expansion coverage is not present in the targeted BSEE-matched HTML output set and will need either a new field row or a documented "not yet generated" status.
- Shell and Talos source scopes are not identical: Shell says "associated fields"; Talos names Kepler, Ariel, Fourier, and Herschel. East Anstey should remain a source-discrepancy/legacy-field item until BSEE/public evidence resolves its current transaction treatment.

### Evidence

**Issue statuses** (verified 2026-07-08T18:53:05Z via `gh issue view`):

```json
{"number":907,"state":"OPEN","title":"feat(insights): Na Kika / Coulomb transaction lifecycle and economics package","url":"https://github.com/vamseeachanta/worldenergydata/issues/907","labels":["enhancement","priority:medium","cat:data","domain:reports","lane:codex","status:needs-plan"]}
```

**File existence** (`ls -la` 2026-07-08T18:53:05Z):

```text
EXISTS: config/analysis/lower_tertiary/economic_assumptions.yml
EXISTS: reports/field_development/bsee_matched/_summary.json
EXISTS: reports/field_development/portfolio/_research.json
EXISTS: reports/lower_tertiary/lifecycle/_facts.json
EXISTS: scripts/field_development/build_fdp_portfolio_matched.py
EXISTS: scripts/lower_tertiary/build_lifecycle_posters.py
EXISTS: scripts/lower_tertiary/generate_field_economics_report.py
```

**Line excerpts / command output**:

```text
$ jq '.fields[] | select(.name|test("Coulomb|Kepler|Ariel|Fourier|Herschel|East Anstey|Isabela|Galapagos"; "i"))' reports/field_development/bsee_matched/_summary.json
{"name":"Ariel","block":"MC429","actual":"semisub_fps","recommended":"semisub_fps","match":true}
{"name":"Coulomb","block":"MC657","actual":"semisub_fps","recommended":"semisub_fps","match":true}
{"name":"East Anstey","block":"MC607","actual":"semisub_fps","recommended":"semisub_fps","match":true}
{"name":"Fourier","block":"MC522","actual":"semisub_fps","recommended":"semisub_fps","match":true}
{"name":"Kepler","block":"MC383","actual":"semisub_fps","recommended":"semisub_fps","match":true}
```

```text
$ jq '.[] | select(.name=="Coulomb")' reports/field_development/portfolio/_research.json
"concept_type": "subsea_tieback"
"host_facility": "Na Kika semi (semisubmersible FPS, MC474)"
"narrative": "Coulomb is ... an all-subsea wet-tree tieback ... to the existing BP/Shell Na Kika semisubmersible FPS ..."
```

```text
$ find reports/field_development/bsee_matched -maxdepth 1 -type f | rg '/(coulomb|kepler|ariel|fourier|east-anstey|herschel|isabela|galapagos)\.html$'
reports/field_development/bsee_matched/ariel.html
reports/field_development/bsee_matched/coulomb.html
reports/field_development/bsee_matched/east-anstey.html
reports/field_development/bsee_matched/fourier.html
reports/field_development/bsee_matched/kepler.html
```

**Reproduction proofs**:

N/A — #907 is an insight/report-generation feature request and does not allege a runtime failure. The implementation will still use TDD before code changes.

Minimum distinct sources consulted: 12.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-07-08-issue-907-na-kika-coulomb-transaction-package.md` |
| Structured facts | `data/modules/offshore_assets/transactions/na_kika_coulomb_2026.yml` |
| Source/provenance sidecar | `data/modules/offshore_assets/transactions/na_kika_coulomb_2026_sources.yml` |
| Transaction package module | `src/worldenergydata/field_development/transaction_package.py` |
| Generator script | `scripts/field_development/build_na_kika_coulomb_transaction.py` |
| HTML output | `reports/field_development/transactions/na_kika_coulomb_2026/index.html` |
| Machine-readable output | `reports/field_development/transactions/na_kika_coulomb_2026/metrics.json` |
| Lifecycle page | `reports/field_development/lifecycle/na_kika_coulomb_2026.html` |
| Lifecycle facts | `reports/field_development/transactions/na_kika_coulomb_2026/lifecycle.json` |
| Economics readiness | `reports/field_development/transactions/na_kika_coulomb_2026/economics_readiness.json` |
| Transaction index | `reports/field_development/transactions/index.html` |
| Tests | `tests/modules/field_development/test_transaction_package.py` |
| Plan review - Claude | `scripts/review/results/2026-07-08-plan-907-claude.md` |
| Plan review - Codex r1 | `scripts/review/results/2026-07-08-plan-907-codex-r1.md` |
| Plan review - Codex subagent | `scripts/review/results/2026-07-08-plan-907-codex-subagent.md` |
| Plan review - Codex follow-up | `scripts/review/results/2026-07-08-plan-907-codex-followup.md` |
| Plan review - Gemini | `scripts/review/results/2026-07-08-plan-907-gemini.md` |

---

## Deliverable

A regenerable Na Kika / Coulomb transaction insight package will preserve public source facts, compute transparent acquisition metrics, distinguish Na Kika host type from field-level tieback concepts, and render a lifecycle/economics-readiness HTML report with machine-readable metrics and provenance sidecars.

---

## Pseudocode

```text
load_transaction_facts(path):
    parse YAML into typed TransactionPackageFacts
    validate source sidecar schema:
        source_id, publisher, title, url, publication_date, accessed_date,
        claim_ids, and claim-to-subject mapping are required for public facts
    require source_id for every public numeric value, date, commercial term,
        named party, named field, interest, operator, and branch condition
    require derivation_id for inferred residuals such as Ridgewood allocation
        if the public sources do not directly state the allocation
    validate named fields, interests, and buyer legs have explicit basis/source_status
    return facts
```

```text
calculate_transaction_metrics(facts):
    compute Shell-side headline consideration screens using the $1.7B total buyer consideration only with Shell-basis production/reserve figures
    compute Talos announced consideration metrics using the $850M net-to-Talos consideration only with Talos-basis reserves/production
    compute Talos estimated final net cash metrics using the $450-500M range only with Talos-basis reserves/production
    keep Ridgewood buyer participation explicit and avoid Talos metrics absorbing Ridgewood interests
    compute production/reserve duration screens without reserve-overclaim
    preserve separate Shell seller, Talos buyer, Ridgewood buyer, base-case, and "if BP exercises preferential right" cases
    return metrics with source references
```

```text
build_lifecycle_assessment(facts, existing_pages, curated_research):
    create lifecycle rows for Na Kika host, Coulomb, Kepler, Ariel, Fourier, and Herschel/Herschel Expansion
    require Herschel minimum facts: named field, Na Kika tieback/host relationship, source scope,
        generated-page status, and whether expansion facts are source-backed or missing
    write lifecycle.json and lifecycle HTML page with stable anchors for host, fields, gaps, and source scope
    return lifecycle assessment with explicit missing-data flags
```

```text
build_economics_readiness(facts, bsee_inputs):
    inspect local BSEE production inputs without requiring a live external refresh
    report production-data status by asset/field as present, absent, stale, or not-yet-mapped
    list the minimum economics inputs needed before NPV or field economics are claimed:
        production volumes, price deck, opex/capex/decommissioning assumptions, working interest, and fiscal basis
    write economics_readiness.json and render the readiness table in the HTML report
    fail if the package emits NPV or full economics values before readiness gates pass
```

```text
build_field_roster(facts, existing_bsee_summary, curated_research):
    create rows for Na Kika host, Kepler, Ariel, Fourier, Herschel, Coulomb
    attach legacy/source-discrepancy rows for East Anstey, Isabela, Galapagos if supported
    set host_type and field_concept separately
    preserve Shell source scope, Talos named-field scope, and local legacy field-page scope separately
    mark missing generated pages such as Herschel as report gaps
    return roster
```

```text
render_transaction_report(facts, metrics, roster):
    render HTML with transaction card, valuation table, lifecycle section, roster table
    include public source links and explicit uncertainty flags
    write index.html and metrics.json
    fail if any metric, commercial term, party assertion, branch condition, or roster assertion lacks source or derivation provenance
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `data/modules/offshore_assets/transactions/na_kika_coulomb_2026.yml` | structured public transaction facts |
| Create | `data/modules/offshore_assets/transactions/na_kika_coulomb_2026_sources.yml` | source/provenance sidecar |
| Create | `src/worldenergydata/field_development/transaction_package.py` | typed loader, validation, metrics, and rendering data model |
| Create | `scripts/field_development/build_na_kika_coulomb_transaction.py` | deterministic generator for report artifacts |
| Create | `tests/modules/field_development/test_transaction_package.py` | TDD coverage for loader, metrics, roster, and provenance gates |
| Create | `reports/field_development/transactions/na_kika_coulomb_2026/index.html` | human-facing transaction package |
| Create | `reports/field_development/transactions/na_kika_coulomb_2026/metrics.json` | machine-readable metrics output |
| Create | `reports/field_development/lifecycle/na_kika_coulomb_2026.html` | standalone lifecycle assessment page |
| Create | `reports/field_development/transactions/na_kika_coulomb_2026/lifecycle.json` | machine-readable lifecycle and field-roster status |
| Create | `reports/field_development/transactions/na_kika_coulomb_2026/economics_readiness.json` | BSEE/economics input readiness status |
| Create/Update | `reports/field_development/transactions/index.html` | transaction report index |
| Update | `reports/field_development/portfolio/README.md` | link the transaction package if the report namespace is built |
| Update | `docs/plans/README.md` | add this plan to the index |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_load_transaction_facts_requires_sources` | every public transaction assertion carries a source id or derivation id | fact YAML missing provenance for a commercial term, party, field, numeric, or date | `ValueError` |
| `test_source_sidecar_schema_requires_claim_mapping` | dummy source ids cannot satisfy provenance | sidecar with `source_id` but missing URL/date/publisher/claim mapping | `ValueError` |
| `test_transaction_parties_include_ridgewood_leg` | Talos and Ridgewood are modeled as separate buyer legs | Shell/Talos source facts | transaction party table has Shell seller, Talos buyer, Ridgewood buyer, and source/derivation status |
| `test_consideration_bases_do_not_mix` | Shell $1.7B, Talos $850M, and Talos $450-500M bases remain separate | source facts containing all three consideration bases | metrics are grouped by basis and reject cross-basis denominator mixing |
| `test_calculate_shell_headline_metric_golden_values` | Shell-side metrics use only Shell-basis consideration/reserve/production facts | $1.7B, 11.5 MMboe Shell proved reserves, 37 Mboe/d Shell entitlement production | about $147.83/boe and $45,945.95/flowing boe/d, flagged as Shell-basis screen |
| `test_calculate_talos_announced_metric_golden_values` | Talos announced metrics use only Talos-basis facts | $850M, 23 MMboe proved, 16 Mboe/d | about $36.96/boe and $53,125/flowing boe/d, flagged as Talos-announced screen |
| `test_calculate_talos_final_net_metric_golden_values` | Talos final net cash range metrics are deterministic | $450-500M, 23 MMboe proved, 16 Mboe/d | about $19.57-21.74/boe and $28,125-31,250/flowing boe/d, flagged as Talos-final-net screen |
| `test_ridgewood_residual_is_unknown_or_derived_not_talos` | Ridgewood allocation is not folded into Talos economics | source facts without directly stated Ridgewood allocation | Ridgewood row has `allocation_status=unknown` or sourced derivation, and Talos metrics exclude it |
| `test_preserves_bp_preferential_right_case` | BP exercise branch is modeled separately, including buyer-leg impact | facts with preferential-right flag | scenario table includes base and BP-exercise cases with affected Na Kika interests explicit and no final-mix assumption |
| `test_provenance_covers_commercial_terms_and_roster` | nonnumeric terms and roster assertions cannot render uncited | valid metrics with missing source for offtake/upside/field roster term | render/validation fails |
| `test_field_roster_separates_host_and_field_concept` | Na Kika host and Coulomb field concept do not collapse | Coulomb facts plus current summary | Na Kika `host_type=semisub_fps`, Coulomb `field_concept=subsea_tieback` |
| `test_lifecycle_requires_herschel_minimum_facts` | Herschel/Herschel Expansion is not optional even if the generated field page is missing | current `bsee_matched` directory plus BP/Talos facts | lifecycle row includes named field, Na Kika tieback/host relationship, source scope, and `generated_page_status=missing` |
| `test_economics_readiness_reports_bsee_input_status` | economics readiness is explicit and does not imply full economics | local BSEE input paths present or absent | JSON lists production-data status by field and blocks NPV/full-economics claims until required inputs exist |
| `test_render_report_contains_required_sections` | HTML contains transaction, roster, lifecycle, economics-readiness, provenance sections | valid facts | HTML contains stable section anchors and links to lifecycle/economics JSON artifacts |
| `test_metrics_json_is_reproducible` | JSON output is stable and source-linked | valid facts | sorted JSON with metrics and source ids |

---

## Acceptance Criteria

- [ ] Tests are written before implementation.
- [ ] `uv run pytest tests/modules/field_development/test_transaction_package.py -v` passes.
- [ ] `uv run python scripts/field_development/build_na_kika_coulomb_transaction.py` writes transaction HTML, metrics JSON, lifecycle HTML, lifecycle JSON, and economics-readiness JSON outputs.
- [ ] The source sidecar validates each public claim with `source_id`, publisher, title, URL, publication date, accessed date, and claim-to-subject mapping; a dummy source id alone fails tests.
- [ ] The report includes Shell-side, Talos-side, and Ridgewood buyer-leg transaction context without mixing total $1.7B, Talos $850M, and Talos final net cash consideration.
- [ ] Golden metric tests cover Shell headline, Talos announced, Talos final-net, Ridgewood unknown/residual, and BP preferential-right scenarios.
- [ ] Ridgewood allocation is either directly sourced or explicitly marked as a derived/unknown residual; it is not silently folded into Talos economics.
- [ ] The report explicitly models the BP preferential-right branch, including affected Na Kika interests, rather than assuming the final asset mix.
- [ ] Na Kika host type and field-level concepts are separate fields in the facts/model.
- [ ] Coulomb is represented as a field-level subsea tieback when supported by the curated research/source record.
- [ ] Herschel / Herschel Expansion receives minimum lifecycle coverage even if the generated field page is missing: named field, Na Kika tieback/host relationship, source scope, generated-page status, and expansion fact status.
- [ ] Economics-readiness output reports BSEE production-data status by asset/field and blocks NPV/full field-economics claims until required inputs are available.
- [ ] Every public numeric/date/source-derived constant, commercial term, named party, named field, operator, interest, and branch condition has a source id or derivation id in the sidecar.
- [ ] `scripts/legal/legal-sanity-scan.sh` passes, or any failure is documented as pre-existing and unrelated.

---

## Adversarial Review Summary

This draft is not ready for `status:plan-review` yet. Codex-family follow-up review found no remaining MAJOR content defects, but external Claude/Gemini reviews were unavailable in the current noninteractive session. The T2 cross-provider review gate still requires a real second-provider review before label transition and user approval.

| Provider | Verdict | Key findings |
|---|---|---|
| Claude | UNAVAILABLE | CLI installed, but noninteractive run returned `Not logged in · Please run /login`. |
| Codex r1 | MAJOR | Ridgewood buyer leg was omitted; Shell/Talos consideration bases were not test-backed; provenance covered only numeric/date facts. |
| Codex subagent | MAJOR | Lifecycle/economics artifacts were under-specified; source sidecar schema was too weak; golden metric tests and Herschel minimum coverage were missing. |
| Codex follow-up | MINOR | No remaining MAJOR defects; requested broader `claim-to-subject` wording, now patched. |
| Gemini | UNAVAILABLE | CLI installed, but noninteractive run failed with `FatalAuthenticationError` / exit code 41. |

**Overall result:** WAITING ON SECOND-PROVIDER REVIEW — revised draft exists with no known MAJOR content defects, but clean T2 review coverage is still required before `status:plan-review`.

Revisions made based on review:
- Added Ridgewood as an explicit buyer leg and required unknown/derived allocation handling instead of folding Ridgewood economics into Talos metrics.
- Split Shell $1.7B total buyer consideration, Talos $850M net-to-Talos consideration, and Talos $450-500M final net cash consideration into separate metric bases with golden-value tests.
- Expanded provenance requirements from numeric/date facts to public commercial terms, named parties, named fields, operators, interests, branch conditions, and claim-level source-sidecar schema.
- Reworded source-sidecar validation from `claim-to-field` to `claim-to-subject` so transaction-, party-, scenario-, field-, and commercial-term claims are all covered.
- Added standalone lifecycle HTML, lifecycle JSON, and economics-readiness JSON artifacts.
- Required minimum Herschel/Herschel Expansion lifecycle coverage even when a generated field page is missing.
- Added economics-readiness checks that report BSEE production-input status and block NPV/full field-economics claims until required inputs are present.

---

## Risks and Open Questions

- **Risk:** The current BSEE-matched portfolio may overstate model accuracy by treating host concept as field concept for Na Kika satellites. The implementation should use an explicit override/source-status layer rather than silently editing generated summaries without tests.
- **Risk:** Shell and Talos source scopes differ: Talos names Kepler, Ariel, Fourier, and Herschel; Shell uses broader "associated fields" wording. East Anstey should remain a flagged source discrepancy until resolved.
- **Risk:** Ridgewood's explicit acquired-interest allocation may not be stated in the same public detail as Talos's allocation. The implementation should preserve Ridgewood as a buyer leg and label any residual allocation as derived or unknown rather than treating it as Talos economics.
- **Risk:** Decommissioning obligations, ORRI, upside sharing, and offtake terms affect valuation but may not be computable from public releases. The report should preserve terms and avoid false precision.
- **Risk:** BSEE production data may be stale or unavailable in a checkout. The generator should render the public transaction report from source facts and mark BSEE-backed production refresh as readiness if local data is absent.
- **Open:** Should the final public artifact use "Gulf of America" as source wording and "Gulf of Mexico" as historical/BSEE dataset wording, with both terms explicitly reconciled?

---

## Complexity: T2

**T2** — one repo, multi-file report/data/model/test change with source-provenance and domain-model risk. Implementation should run in `single-lane` mode after approval; resource intelligence and review may run in `parallel-readonly` mode.
