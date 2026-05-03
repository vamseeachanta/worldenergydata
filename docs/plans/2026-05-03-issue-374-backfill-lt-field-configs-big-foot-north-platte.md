# Plan for #374: backfill LT field configs for Big Foot + North Platte

> **Status:** draft
> **Complexity:** T1
> **Date:** 2026-05-03
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/374
> **Parent epic:** https://github.com/vamseeachanta/worldenergydata/issues/373

---

## Resource Intelligence Summary

### Existing repo code
- `config/analysis/lower_tertiary/fields/` contains 8 yaml configs (anchor, cascade_chinook, jack_st_malo, julia, kaskida, shenandoah, stones, tiber). Big Foot and North Platte are absent.
- `config/analysis/lower_tertiary/fields/anchor.yml` is the canonical schema reference: top-level `field` with `field_id`, `display_name`, `status`, `leases_key`, `first_oil`, `data_through`, `operator`, `partners` (list of `name` + `working_interest`), `capex` (totals + `fpu_mm_usd`/`subsea_mm_usd`/`wells_mm_usd`), `production_profile` (`plateau_rate_mbopd`, `gor_scf_per_bbl`), `opex_per_boe`.
- `src/worldenergydata/lower_tertiary/npv.py` consumes these configs via `load_field_inputs()`. A field absent from the configs is silently skipped — no fail-loud guard on portfolio completeness.
- `tests/unit/lower_tertiary/test_field_inputs.py` exists; need to confirm whether it asserts the full 10-field roster.

### Documents and issues consulted
- Issue #374 body
- Parent epic #373 (10-field portfolio definition)
- `reports/lower_tertiary_field_summary.md` (canonical field roster + cum production / lease counts)
- Reference schema: `config/analysis/lower_tertiary/fields/anchor.yml`

### Gaps identified
- **Big Foot:** no yaml. Public data: Chevron operator, dry-tree TLP, first oil 2018, Walker Ridge 29/82, ~$5.2B CAPEX (Chevron annual reports). Working interests: Chevron 60%, Equinor 27.5%, Marubeni 12.5%.
- **North Platte:** no yaml. Status Pre-FID. TotalEnergies operator after Equinor handover (2022); Garden Banks 957/958. CAPEX TBD (only conceptual estimates public).
- No portfolio-completeness test exists; `test_field_inputs.py` should be extended to assert the 10-field roster matches the report.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-05-03-issue-374-backfill-lt-field-configs-big-foot-north-platte.md` |
| Schema reference | `config/analysis/lower_tertiary/fields/anchor.yml` |
| New config (Big Foot) | `config/analysis/lower_tertiary/fields/big_foot.yml` |
| New config (North Platte) | `config/analysis/lower_tertiary/fields/north_platte.yml` |
| Roster test | `tests/unit/lower_tertiary/test_field_inputs.py` |
| Roster source | `reports/lower_tertiary_field_summary.md` |

---

## Deliverable

Two yaml field configs (`big_foot.yml`, `north_platte.yml`) that match the existing schema, plus a portfolio-completeness test that fails loudly if any of the 10 expected LT fields lacks a config.

---

## Scope Boundaries

### In scope now
- Add `big_foot.yml` with operator/partners/capex/production sourced from Chevron public disclosures.
- Add `north_platte.yml` with the Pre-FID equivalent: operator, planned dev system, capex range with `confidence: preliminary` flag, no `first_oil` (or "TBD" sentinel), no production profile.
- Extend `tests/unit/lower_tertiary/test_field_inputs.py` to assert the 10-field roster matches `LT_FIELDS_2026 = ["anchor", "big_foot", "cascade_chinook", "jack_st_malo", "julia", "kaskida", "north_platte", "shenandoah", "stones", "tiber"]`.
- Run `lower_tertiary.npv` against the new configs to confirm they parse without errors (no economics calculation needed yet — that's Phase 2 / #375).

### Out of scope (deferred)
- Production grounding (real BSEE OGOR aggregation per field) — Phase 2 / #375.
- Citations adoption (Citation schema sidecar per yaml entry) — #361 follow-up.
- North Platte operator-handover history narrative — Phase 4 / #377 report assembly.

---

## Steps

1. **Read** the canonical schema from `anchor.yml` and `kaskida.yml` (Pre-FID example) to identify the exact field set used by the loader.
2. **Discover sources** for Big Foot capex/partnerships (Chevron 10-K, project announcements, BSEE lease records under Walker Ridge 29/82).
3. **Discover sources** for North Platte (TotalEnergies disclosures post-2022, prior Equinor/Cobalt era press releases). Capex remains preliminary.
4. **Author `big_foot.yml`** with values + a `provenance` block listing each non-trivial number's source URL + retrieval date.
5. **Author `north_platte.yml`** similarly; add a `confidence: preliminary` field and `first_oil: null` or `TBD` per the loader's convention (verify what the loader accepts).
6. **Extend test_field_inputs.py** with a parametrized test asserting all 10 yamls load without error and produce non-null `field_id`.
7. **Add roster constant** in `lower_tertiary/__init__.py` or a new `lower_tertiary/portfolio.py`: `LT_FIELDS_2026 = (...)` so the report (#377) and tests share a single source.
8. **Run tests locally** — `uv run pytest tests/unit/lower_tertiary/ -v` — confirm 10 fields × loader = pass.
9. **Black + ruff** clean before push.
10. **PR through gates** per the repo's branch protection.

---

## Adversarial review checklist

- [ ] Are the operator/partner working interests in `big_foot.yml` consistent with **publicly disclosed** numbers (no internal estimates)? Cite the source for each.
- [ ] Does North Platte's `confidence: preliminary` flag survive Phase 4's report assembly so buyers see the uncertainty marker?
- [ ] Does the loader silently accept missing fields (e.g., `first_oil: null` for Pre-FID), or does it crash? If it crashes, the loader needs a small accommodation here, not a workaround in the yaml.
- [ ] Does the new completeness test fail loudly when a yaml is removed, or does it just count? Verify by deleting one yaml temporarily.
- [ ] Are there other LT-class fields (e.g., Buckskin, Whale, Sparta) that should be in the 10 but aren't? Cross-check against `reports/lower_tertiary_field_summary.md` — that document is the **roster of record** for this epic; deviations need an explicit decision in the parent epic before deviating here.

---

## Verification

After implementation:
- `uv run pytest tests/unit/lower_tertiary/test_field_inputs.py -v` → all 10 fields load
- `ls config/analysis/lower_tertiary/fields/*.yml | wc -l` → 10
- Roster constant resolves to all 10 ids when imported
- `lower_tertiary.npv.load_field_inputs("big_foot")` returns a non-null FieldInputs object
- `lower_tertiary.npv.load_field_inputs("north_platte")` returns a non-null FieldInputs object with the preliminary flag preserved
