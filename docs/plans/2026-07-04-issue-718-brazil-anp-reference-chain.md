# Plan — worldenergydata #718: Brazil ANP Reference-Chain Slice

- **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/718
- **Date:** 2026-07-04
- **Status:** plan-review
- **Client:** N/A
- **Project:** N/A
- **Lane:** lane:codex
- **Complexity:** T2
- **Dependencies:** #714, #715
- **Closes:** #459
- **Execution mode:** single-lane implementation after approval; source probes,
  review, and validation may run in parallel.

## Resource Intelligence Summary

Brazil will be the next international country chain after Norway #716 and UKCS
#717. This plan will subsume #459 because the current Brazil scheduler failure
is the same stale endpoint/schema defect that must be fixed before the Brazil
reference chain can run against direct ANP sources.

Current repo state:

- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py`
  emits synthetic benchmark profiles for Lula, Búzios, Mero, and Marlim with
  `source="brazil_anp_mock"`.
- `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py`
  still builds
  `https://cdp.anp.gov.br/ords/r/cdp_apex/consulta-dados-publicos-cdp/consulta-producao-por-poco?year=YYYY&semester=S`.
- Reproduction proof for #459 on 2026-07-04:
  `curl -L -sS -o /tmp/anp-old-cdp.html -w '%{http_code} %{url_effective}\n' '<old-url>'`
  returns `404` with `Application "117" Page "consulta-producao-por-poco" not found`.
- `WellProductionLoader` currently expects old lowercase Sm3-style columns
  (`oleo_sm3`, `condensado_sm3`, `gas_mm3`, `agua_sm3`). The current official
  ANP production-by-well metadata exposes daily-rate columns such as
  `Óleo (bbl/dia)`, `Condensado (bbl/dia)`, `Gás Natural (Mm³/dia) Total`,
  `Água (bbl/dia)`, `Período`, `Campo`, and `Nome Poço ANP`.
- `FieldProductionAggregator` already provides the correct aggregation shape
  for well rows into field-month totals, but it will need the current ANP
  normalized columns.
- `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py`
  imports `ANPClient` and `WellProductionLoader`, calls the current semester
  API, and will be updated in this issue rather than left as a broken caller.
- `field_development.basin` already maps `region="brazil"` to a Brazil basin
  prior that favors FPSO and disfavors fixed jackets, spars, TLPs, and compliant
  towers.
- FDAS #714/#715 are on main. `to_fdas_production` requires unified rows with
  `region`, `field_name`, `year`, `month`, `oil_bbl`, `gas_mcf`, and `water_bbl`.

Official direct-source evidence:

- ANP "Produção de Petróleo e Gás Natural por Poço" says monthly production by
  well has been published since 2010, carries field/basin/state/operator/contract
  and production-period metadata, and is released with a two-month publication
  lag. It publishes separate files for `terra`, `mar`, and `pré-sal`.
- The ANP production-by-well metadata PDF identifies the file format as CSV,
  update frequency as monthly, and the source as ANP SDT/SIGEP.
- The official monthly archive URL
  `https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/arquivos-producao-de-petroleo-e-gas-natural-por-poco/2023/producao-01.zip`
  returns HTTP 200 `application/zip` and contains `2023_01_producao_Mar.csv`,
  `2023_01_producao_Presal.csv`, and `2023_01_producao_Terra.csv`.
- ANP "Fase de Desenvolvimento e Produção" exposes open CSVs for fields,
  returned fields, concessionaires, production-phase vertices, producing wells,
  rigs in operation, well interventions, offshore production units, forecast
  activity/investment/production, and realized activity/investment.
- Direct official CSV probes on 2026-07-04 returned HTTP 200 for:
  - fields:
    `.../informacoes-sobre-campos/extracao-campo.csv`
    with header fields including `CAMPO`, `BACIA`, `OPERADOR`, `AMBIENTE`,
    and `DATA_INICIO_PRODUCAO`;
  - well status:
    `.../informacoes-sobre-pocos/situacao-pocos-1939-2026.csv`
    with header fields including `Nome_poço_anp`, `Campo`, `Bacia`,
    `Data_início_perfuração`, `Data_início_produção_(mês/ano)`, and
    `Ambiente`;
  - offshore production units:
    `.../lpo/dados-abertos-plataformas-operacao.csv`
    with header fields including `[CAMPOS]`, `[BACIA]`,
    `[LÂMINA D'ÁGUA (m)]`, `[CLASSIFICAÇÃO]`, and production/gas capacity.

Runtime baseline:

- `PYTHONPATH=packages/worldenergydata-brazil_anp/src:packages/worldenergydata-production/src:packages/worldenergydata-common/src /mnt/local-analysis/worldenergydata/.venv/bin/python -m pytest tests/unit/brazil_anp tests/unit/production/unified/test_adapters.py --noconftest -o addopts=''`
  reports `155 passed`.

## Artifact Map

- `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py`
  will add a monthly direct-source API (`download_month`) that resolves official
  gov.br production-by-well ZIP links and will replace the stale CDP APEX
  year/semester download path. Any retained legacy `download(year, semester)`
  wrapper will be tested as compatibility behavior over monthly files; otherwise
  all callers will be migrated in this issue.
- `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py`
  will parse the current ANP CSV schema, including decimal-comma numeric fields,
  daily-rate to monthly-volume conversion, and a `location_source` marker for
  `mar`, `terra`, and `presal`.
- `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py`
  will aggregate current well rows to field-month totals with gas converted to
  `gas_mcf`.
- `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py`
  will switch from semester refresh semantics to a monthly refresh contract and
  will write raw/normalized artifacts for one ANP production month.
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py`
  will gain an injectable loader-backed ANP path while retaining the no-loader
  synthetic compatibility fallback.
- New `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py`
  will map official ANP field/platform/well metadata into a sparse but useful
  `FieldConcept` and will provide `build_brazil_field_meta` plus
  `build_brazil_field_concept`.
- New `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py`
  will run one fixture Brazil field through production normalization, concept
  screening, and FDAS cashflow plumbing.
- Tests will pin the source resolver, current CSV schema bridge, unified adapter
  bridge, scheduler refresh behavior, Brazil FieldConcept mapping, and one-field
  reference-chain output.

## Deliverable

This slice will prove one Brazil field through:

1. Official ANP direct-source resolution for production-by-well monthly files.
2. Current ANP CSV normalization from well rows to field-month totals.
3. `BrazilAnpAdapter.fetch` using fixture-backed real ANP loader output.
4. `to_fdas_production` producing the FDAS monthly-production schema.
5. Brazil `FieldMetaMapping` producing a `FieldConcept` with `region="brazil"`.
6. `recommend()` returning a deterministic Brazil/FPSO-prior ranked list.
7. `CashflowEngine` returning finite metrics labeled `chain_plumbing_pre_tax`.

The implementation will not publish a Brazil investment NPV headline. Unified
production will preserve `condensate_bbl`, but `to_fdas_production` currently
maps only `oil_bbl` into `MONTHLY_OIL_BBL`; therefore the first FDAS cashflow
pass will be oil-only and will not claim full-liquids revenue for pre-salt
fields. Brazil fiscal terms are not yet representable by the current FDAS deck
schema because
`royalty.model="sliding_scale"` is reserved and rejected. The first economics
pass will therefore be explicitly pre-tax chain plumbing, while royalty/special
participation and PSC/concession after-tax semantics remain deferred to #737 or
a reviewed successor to #737.

## Pseudocode

```python
client = ANPClient(cache_dir=raw_cache)
raw = client.download_month(year=2023, month=1, force_refresh=False)

well_rows = WellProductionLoader().load(raw)
field_rows = FieldProductionAggregator().aggregate(well_rows)

adapter = BrazilAnpAdapter(loader=FakeBrazilProductionLoader(field_rows))
unified = adapter.fetch(ProductionQuery(regions=["brazil"], fields=["Marlim"]))
fdas_production = to_fdas_production(unified)

field_meta = build_brazil_field_meta(fields_csv, platforms_csv, wells_csv, "Marlim")
concept = build_brazil_field_concept(field_meta)
ranked = recommend(concept)

result = run_brazil_reference_chain(
    adapter=adapter,
    field_meta=field_meta,
    field_name="Marlim",
)
assert result["economics_label"] == "chain_plumbing_pre_tax"
```

## Files to Change

- `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py`
- `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py`
- `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py`
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py`
- `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py`
- `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py`
- `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py`
- `tests/unit/brazil_anp/test_anp_client.py`
- `tests/unit/brazil_anp/test_well_production.py`
- `tests/unit/brazil_anp/test_field_production.py`
- `tests/unit/scheduler/test_brazil_anp_refresh.py`
- `tests/unit/brazil_anp/test_brazil_field_concept.py`
- `tests/unit/brazil_anp/test_reference_chain.py`
- `tests/unit/production/unified/test_brazil_anp_adapter_loader.py`
- Existing compatibility tests in `tests/unit/production/unified/test_adapters.py`

## TDD Test List

- ANP client source resolver:
  - old CDP APEX URL is not used for downloads;
  - official gov.br monthly ZIP URL is accepted and cached by year/month;
  - a fixture ZIP with `Mar`, `Presal`, and `Terra` CSVs is parsed as mutually
    exclusive ANP partitions and concatenated with `location_source`;
  - duplicate `(field, well, date)` keys across partitions fail closed to protect
    against future upstream overlap.
- Current ANP well-production schema:
  - Portuguese columns with accents and decimal commas parse correctly;
  - `Período` becomes `year`, `month`, and `date`;
  - oil/condensate/water daily bbl rates become monthly bbl volumes;
  - gas daily `Mm³/dia` becomes monthly `gas_mcf`;
  - field/well/operator/basin/environment columns are preserved.
- Field aggregation:
  - field-month well rows sum oil, condensate, gas, and water;
  - `well_count` and `water_cut` remain deterministic.
- Scheduler refresh:
  - `BrazilAnpRefreshJob` uses the monthly direct-source API;
  - old semester configuration does not call the stale CDP APEX URL;
  - raw and normalized output paths carry year/month identifiers;
  - #459's configured 404 path is covered by a regression test.
- Brazil adapter bridge:
  - loader-backed `BrazilAnpAdapter.fetch` emits all `STANDARD_COLUMNS`;
  - `region="brazil"` and `source="anp_producao_poco"`;
  - field/date filters still work;
  - the no-loader synthetic fallback keeps existing adapter compatibility tests
    green.
- Brazil FieldConcept:
  - source CSV header fixtures cover the field/platform/well columns used by
    `build_brazil_field_meta`;
  - fields/platform/well metadata maps field name, operator, basin, environment,
    first production year, water depth, well count, and region;
  - `region="brazil"` triggers a deterministic FPSO-favored recommendation.
- Reference chain:
  - one fixture field runs `fetch -> to_fdas_production -> CashflowEngine`;
  - one fixture field runs `FieldConcept -> recommend`;
  - output metrics are finite and labeled `chain_plumbing_pre_tax`.

## Acceptance Criteria

- The #459 endpoint/schema failure is fixed by this implementation and the PR
  will close #459 together with #718.
- `ANPClient` uses official gov.br direct-source downloads, not the stale APEX
  year/semester endpoint.
- `BrazilAnpRefreshJob` uses the same direct-source API and no longer attempts
  the stale CDP APEX year/semester URL.
- Current ANP production-by-well CSVs normalize into field-month totals that can
  feed the unified production adapter.
- ANP `Mar`, `Presal`, and `Terra` monthly files are treated as disjoint
  partitions, with a duplicate-key guard to prevent double counting if upstream
  semantics change.
- Loader-backed `BrazilAnpAdapter.fetch` emits exactly the unified
  `STANDARD_COLUMNS` contract for supplied ANP loader data.
- Existing Brazil adapter compatibility tests stay green through the no-loader
  fallback.
- Brazil FieldConcept mapping ships with clear sparse metadata boundaries and
  `region="brazil"`.
- The reference-chain runner returns finite pre-tax plumbing metrics and a
  deterministic concept ranking.
- No Brazil after-tax economics, full-liquids revenue, or investor-value headline
  is claimed until the condensate FDAS seam plus sliding-scale royalty and
  special-participation fiscal seam are reviewed.
- Focused local tests, format/lint on touched Python files, whitespace/diff
  checks, legal scan, adversarial code review, PR CI, and issue closeout comment
  pass before merge.

## Risks

- ANP monthly direct-source links may change path conventions. The resolver will
  prefer scraping the official page for monthly links over hardcoding a single
  guessed URL pattern.
- The production-by-well ZIP separates `mar`, `terra`, and `pré-sal` files. The
  implementation will treat them as ANP's disjoint monthly partitions and will
  include a duplicate-key guard so any future upstream overlap fails closed
  before aggregation.
- The current loader column names are stale and use different units than current
  ANP metadata. Tests will pin current daily-rate columns and monthly conversion
  explicitly.
- Brazil fiscal modeling is materially more complex than Norway/UK royalty
  plumbing. This plan will fail closed as pre-tax plumbing until #737 or its
  successor extends FDAS to sliding-scale royalty and special participation.
- Sparse field metadata can still produce coarse concept rankings. Acceptance is
  deterministic screening output, not a final engineering concept-select report.

## Review Evidence

- r1 adversarial review:
  `scripts/review/results/2026-07-04-plan-718-claude-r1.md` returned MAJOR.
  Blockers folded into this revision:
  scheduler caller/test coverage, ANP partition semantics, concrete #459
  ownership, explicit new `download_month` API, condensate oil-only boundary,
  single `source="anp_producao_poco"` value, and Búzios spelling.
- r2 focused adversarial review:
  `scripts/review/results/2026-07-04-plan-718-claude.md` returned MINOR with no
  blockers. Minor findings folded after r2: r1 artifact citation,
  Norway/UKCS-style `run_brazil_reference_chain(adapter, field_meta, field_name)`
  contract, and explicit header evidence for field/platform/well metadata.
- Codex and Gemini provider artifacts were UNAVAILABLE in r1:
  `scripts/review/results/2026-07-04-plan-718-codex.md` and
  `scripts/review/results/2026-07-04-plan-718-gemini.md`.
- Implementation will remain blocked until final review artifacts report no
  unresolved MAJOR findings and the user applies the `status:plan-approved`
  gate.
