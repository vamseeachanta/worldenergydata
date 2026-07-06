# Plan: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) - Spain CORES crude density/API table

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Status:** plan-review
**Tier:** T2 (parser, live-refresh metadata, report provenance)
**Client:** N/A
**Project:** worldenergydata Spain CORES production lifecycle
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Implementation will use a serialized TDD lane because the parser, live loader,
committed fixture metadata, and report caveat all depend on the same conversion
contract. Read-only research and adversarial review can run in parallel, but
file writes will stay serialized to avoid inconsistent conversion metadata.

Implementation will not begin until this plan is reviewed, pushed, moved to
`status:plan-review`, and explicitly approved by the user as
`status:plan-approved`.

### Issue and dependency status

| Issue | State | Role for this plan |
|---|---|---|
| [#713](https://github.com/vamseeachanta/worldenergydata/issues/713) | open, `status:needs-plan` | International source-to-field-development epic |
| [#763](https://github.com/vamseeachanta/worldenergydata/issues/763) | closed, `status:done` | Spain CORES parser, fixture, adapter, and reference chain |
| [#806](https://github.com/vamseeachanta/worldenergydata/issues/806) | closed, `status:done` | Direct-source live CORES XLSX download and normalized CSV lane |
| [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) | open | This crude-density/API conversion slice |
| [#808](https://github.com/vamseeachanta/worldenergydata/issues/808) | open | Gas revenue modeling, outside this slice |
| [#809](https://github.com/vamseeachanta/worldenergydata/issues/809) | closed, `status:done` | Scheduler job that refreshes the live CORES cache |
| [#810](https://github.com/vamseeachanta/worldenergydata/issues/810) | closed, `status:done` | Spain CORES field-development report |

Parallel work check:

- [PR #840](https://github.com/vamseeachanta/worldenergydata/pull/840) is open
  for GTM re-land work and does not touch the Spain CORES parser path.
- [PR #841](https://github.com/vamseeachanta/worldenergydata/pull/841) is open
  for completion reconciliation/report work and does not touch this plan's
  Spain CORES, scheduler, or production-adapter paths.

### Current code surfaces

- `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py`
  defines `TONNES_TO_BBL = 7.33`, `GWH_TO_MCF`, `parse_cores_frame(...)`,
  `CoresProductionLoader`, and `CoresFixtureProductionLoader`.
- `parse_cores_frame(raw, *, product)` currently accepts only `product`; for
  oil it applies the single `TONNES_TO_BBL` value to every field.
- `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py`
  calls `CoresProductionLoader(...).load()` and writes normalized CSVs under
  the configured cache root.
- `refresh_ayoluengo_fixture(...)` currently writes fixture metadata with
  `"oil_bbl = tonnes * 7.33"` and `oil_tonnes_to_bbl: 7.33`.
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py`
  passes through `oil_bbl`; it should not contain density conversion logic.
- `packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py`
  currently surfaces the limitation
  `oil_tonnes_to_bbl_conversion_deferred_to_issue_807`; this slice will replace
  that caveat with explicit conversion provenance only when strict conversion
  coverage is actually available.

### Live CORES oil-field scope

The current operational cache under `/mnt/ace/worldenergydata/data/spain/cores`
contains these oil-producing CORES field names in
`normalized/cores_oil_production.csv`:

```text
Albatros
Amposta
Ayoluengo
Boquerón
Casablanca
Dorada
Gaviota
Montanazo-Lubina
Rodaballo
Salmonete
Tarraco
Viura (1)
```

Implementation will treat this as the current source-coverage set. This issue
will close only if every oil-producing CORES field in the parsed oil workbook is
backed by a validated cited factor accepted for conversion. If source work cannot
support every current oil field, implementation will stop at a named source-gap
closeout and [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)
will remain incomplete rather than shipping a partial "real per-field" table.

### Source evidence boundary

CORES provides production volumes in metric tonnes for crude oil but does not
publish per-field API gravity or density in the production workbook. This slice
will therefore keep CORES as the production source and add a separate cited
conversion registry for density/API values.

Candidate density/API sources identified during planning:

- CORES statistics page and oil workbook:
  `https://www.cores.es/en/estadisticas`,
  `https://www.cores.es/sites/default/files/archivos/estadisticas/crude-oil-production.xlsx`
- AAPG Explorer, "Spain's Oldest and Only Onshore Oilfield":
  `https://www.aapg.org/news-and-media/explorer/spains-oldest-and-only-onshore-oilfield/`
  - The discovery well flowed 36-degree API oil.
  - Ayoluengo oils vary by well/sand, with gravities ranging from 20 to 39
    degrees API.
- EIA API gravity definition:
  `https://www.eia.gov/dnav/pet/TblDefs/pet_crd_api_tbldef2.asp`
  - Defines API gravity as `141.5 / specific_gravity - 131.5`.
- Chevron Marine Products fuel conversion chart:
  `https://www.chevronmarineproducts.com/content/dam/chevron-marine/fuels-conversion-chart/Fuels%20Conversion%20Charts.pdf`
  - Provides density/API/barrels-per-metric-ton conversion reference values.
- Additional candidate source leads will be verified during implementation for
  offshore Mediterranean fields. Planning source scouting found useful but not
  yet accepted secondary evidence for Ayoluengo, Boquerón, Casablanca,
  Rodaballo, Amposta, and Tarraco.

Planning source scouting did not find reliable density/API evidence for
`Albatros`, `Dorada`, `Gaviota`, `Montanazo-Lubina`, `Salmonete`, or
`Viura (1)`. Implementation will treat these as source gaps unless further
source work finds cited factors.

The implementation will not scrape third-party mirrors or uncited copies into
the repository. Numeric factors that affect `oil_bbl` will be accepted only from
regulator records, operator records, securities filings, crude assay data, or
technical literature with an explicit field-applicable measurement basis. A
secondary article, industry news article, or summary article can support an
evidence note or source lead, but it will not drive `bbl_per_tonne`. If a source
contains enough measurement detail to drive conversion, the registry must
classify it as one of the conversion-eligible source classes and record the
explicit representative produced stream, sales crude, blend, field average, or
other field-applicable conversion basis.
Each registry entry will carry `accepted_for_conversion`; entries with
`accepted_for_conversion: false` will be excluded from strict conversion.

### Boundary decisions

- Production data will remain direct CORES data; the density registry will only
  convert CORES metric tonnes to barrels.
- Durable live outputs will stay under `/mnt/ace`; repository changes will be
  code, tests, committed fixtures, and small cited metadata only.
- The parser will stay pure and fixture-testable. It will receive an optional
  `CoresOilConversionAudit` built from validated cited factors and will not
  perform network access. Raw float mappings will not be accepted at the public
  parser/live-loader boundary because they strip citation provenance.
- Citation/provenance validation will live outside the pure parser in a small
  registry loader module.
- The unified production adapter and FDAS cashflow code will remain unchanged
  unless tests prove they drop conversion metadata needed by the report.
- Missing density coverage will not silently masquerade as real per-field
  conversion. Strict conversion will raise on missing cited factors. Legacy
  default conversion will require an explicit `allow_default_density=True` opt-in
  and will always return/report exact defaulted fields.
- The implementation will not present Ayoluengo's 20-39 API range as a single
  accepted conversion factor. A single Ayoluengo factor will require a specific
  cited value for a representative produced stream, sales crude, blend, field
  average, or explicit current conversion basis; otherwise Ayoluengo will remain
  missing/defaulted and [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)
  will not close.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review artifacts | `scripts/review/results/2026-07-06-plan-807-*.md` |
| Parser | `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py` |
| Density registry module | `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py` |
| Density registry data | `packages/worldenergydata-spain/src/worldenergydata/spain/data/cores/crude_density_factors.json` |
| Live loader metadata | `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py` |
| Scheduler job wiring | `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/spain_cores_refresh.py` |
| Scheduler config | `config/scheduler/scheduler_config.yml` |
| Committed fixture metadata | `packages/worldenergydata-spain/src/worldenergydata/spain/data/cores/_metadata.json` |
| Committed fixture sample | `packages/worldenergydata-spain/src/worldenergydata/spain/data/cores/ayoluengo_oil_sample.csv` |
| Production adapter fallback | `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py` |
| Spain report builder | `packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py` |
| Parser tests | `tests/unit/spain/test_cores_loader.py` |
| Density registry tests | `tests/unit/spain/test_cores_density.py` |
| Live loader tests | `tests/unit/spain/test_cores_live.py` |
| Scheduler tests | `tests/unit/scheduler/test_spain_cores_refresh.py` |
| Scheduler config tests | `tests/unit/scheduler/test_config.py` |
| Adapter tests | `tests/unit/production/unified/test_spain_cores_adapter_loader.py` |
| Report tests | `tests/unit/spain/test_cores_field_development_report.py` |

## Deliverable

The implementation will add a cited Spain CORES crude density/API registry and
will wire it through the CORES oil parser so oil `tonnes` become `oil_bbl`
using field-specific conversion factors only where cited factors exist.

The registry will expose deterministic conversion metadata. Evidence that does
not support a representative field-level conversion factor will be retained only
as non-converting evidence, for example:

```json
{
  "field_name": "Ayoluengo",
  "aliases": ["ayoluengo"],
  "api_gravity_deg": null,
  "api_gravity_min_deg": 20.0,
  "api_gravity_max_deg": 39.0,
  "bbl_per_tonne": null,
  "source_title": "Spain's Oldest and Only Onshore Oilfield",
  "source_url": "https://www.aapg.org/news-and-media/explorer/spains-oldest-and-only-onshore-oilfield/",
  "source_class": "industry_technical_article",
  "measurement_basis": "non-representative discovery-test and field-range evidence only",
  "evidence_note": "Discovery-well oil tested at 36-degree API; field oil range also reported as 20-39 API by well/sand.",
  "confidence": "medium",
  "accepted_for_conversion": false
}
```

Final implementation will use a conversion factor for Ayoluengo only if source
research verifies a representative field-level API gravity, density, or
bbl/tonne basis. Any such value will be traceable in the registry and tests.

## Proposed Design

### Density registry API

`cores_density.py` will provide:

```python
@dataclass(frozen=True)
class CoresCrudeDensityFactor:
    field_name: str
    aliases: tuple[str, ...]
    api_gravity_deg: float | None
    api_gravity_min_deg: float | None
    api_gravity_max_deg: float | None
    bbl_per_tonne: float | None
    measurement_basis: str
    source_title: str
    source_url: str
    source_class: str
    evidence_note: str
    confidence: str
    accepted_for_conversion: bool

    def __post_init__(self) -> None:
        """Validate citation, source class, representative basis, and math."""


@dataclass(frozen=True)
class CoresOilConversionAudit:
    used_factors: tuple[CoresCrudeDensityFactor, ...]
    defaulted_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    _accepted_entries: tuple[tuple[str, CoresCrudeDensityFactor], ...]
    _defaulted_field_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        """Revalidate factors and immutable conversion entries."""

    def bbl_per_tonne_for_field(self, field_name: str) -> float:
        """Return cited/default factor for a parsed CORES field."""


def bbl_per_tonne_from_api(api_gravity_deg: float) -> float:
    specific_gravity = 141.5 / (api_gravity_deg + 131.5)
    return 1.0 / (specific_gravity * 0.158987294928)


def load_crude_density_factors(path: Path | None = None) -> dict[str, CoresCrudeDensityFactor]:
    """Load, normalize, and validate cited crude density factors."""


def validate_crude_density_factor(factor: CoresCrudeDensityFactor) -> None:
    """Validate one cited density factor regardless of construction path."""


def build_oil_conversion_audit(
    field_names: Iterable[str],
    factors: Mapping[str, CoresCrudeDensityFactor],
    *,
    allow_default_density: bool = False,
) -> CoresOilConversionAudit:
    """Resolve cited factors and exact missing/defaulted field lists."""


class CoresDensityCoverageError(ValueError):
    """Raised when strict oil conversion lacks accepted density coverage."""
```

The shared factor validator and registry loader will validate:

- `field_name` and each alias are non-empty strings.
- Accepted conversion entries have a positive `bbl_per_tonne` within a
  conservative crude-oil range.
- Evidence-only entries may carry `api_gravity_min_deg`/`api_gravity_max_deg`
  and `bbl_per_tonne: null`, but must have `accepted_for_conversion: false`.
- `measurement_basis`, `source_url`, `source_title`, `source_class`,
  `evidence_note`, `confidence`, and `accepted_for_conversion` are present for
  every factor.
- `source_class` is one of `regulator_record`, `operator_record`,
  `securities_filing`, `crude_assay`, `technical_literature`,
  `industry_technical_article`, or `secondary_article`.
- Only `regulator_record`, `operator_record`, `securities_filing`,
  `crude_assay`, and `technical_literature` may have
  `accepted_for_conversion: true`. `industry_technical_article` and
  `secondary_article` are evidence-only unless replaced by an underlying
  conversion-eligible source.
- If `api_gravity_deg` is present, `bbl_per_tonne` matches
  `bbl_per_tonne_from_api(...)` within a small tolerance.
- Ranged, discovery-test-only, or non-representative evidence can be stored only
  with `accepted_for_conversion: false`.
- Duplicate normalized names/aliases fail closed.
- `CoresCrudeDensityFactor.__post_init__` will call the same
  `validate_crude_density_factor(...)` helper used by the registry loader, so
  direct dataclass construction cannot bypass citation, source-class,
  representative-basis, range, or API-math validation.
- `build_oil_conversion_audit(...)` is the single helper used by the parser
  caller and sidecar writer so conversion math and provenance cannot drift.
- `CoresOilConversionAudit` will not expose a public mutable conversion map and
  will not accept raw numeric conversion maps. It will store immutable
  `_accepted_entries` tuples plus `_defaulted_field_keys`, and
  `__post_init__` will call `validate_crude_density_factor(...)` for every
  `used_factors` and `_accepted_entries` factor. It will then fail closed if any
  accepted entry is not backed by an `accepted_for_conversion: true`
  `CoresCrudeDensityFactor` in `used_factors`, if any accepted factor lacks
  `bbl_per_tonne`, if keys are duplicated, or if a default key is not
  represented in `defaulted_fields`.
- `build_oil_conversion_audit(...)` will be the normal construction path, but a
  direct `CoresOilConversionAudit(...)` call will still validate the invariant
  at runtime so tests cannot bypass provenance by constructing the dataclass
  manually.

### Parser API

`parse_cores_frame(...)` will become:

```python
def parse_cores_frame(
    raw: pd.DataFrame,
    *,
    product: str,
    oil_conversion_audit: CoresOilConversionAudit | None = None,
) -> pd.DataFrame:
    """Parse CORES production rows with optional audited oil conversion factors."""
```

For `product == "oil"`:

- field names will be normalized for lookup with case/space/punctuation
  tolerance but output field names will preserve CORES display spelling.
- fields resolved by `oil_conversion_audit.bbl_per_tonne_for_field(...)` will
  use cited values from accepted `CoresCrudeDensityFactor` objects or explicit
  audited defaults. The parser will not inspect public conversion maps or
  caller-supplied floats.
- fields defaulted by `build_oil_conversion_audit(..., allow_default_density=True)`
  will use `TONNES_TO_BBL` and will remain visible in the audit sidecar/report.
- fields missing from the audit will raise `CoresParseError`.
- the live/default code path will build the audit from validated
  `CoresCrudeDensityFactor` objects. Any raw float mapping will be limited to a
  private helper or test fixture derived from `CoresOilConversionAudit`, not a
  public parser or live-loader API.

For `product == "gas"`:

- `oil_conversion_audit` will have no effect.
- GWh to Mcf conversion will stay unchanged.

### Live loader and metadata

`CoresProductionLoader` will accept the parser's new `oil_conversion_audit`
argument and pass it through unchanged.

`CoresLiveProductionLoader` will accept a density registry path and an
`allow_default_density` flag. The default live refresh path will fail closed
when source gaps remain. Operators may set `allow_default_density=True` only for
legacy/diagnostic refreshes, and those refreshes will mark defaulted fields
explicitly.

The live loader will write a small normalized metadata sidecar under the
configured cache root, for example:

```text
normalized/cores_oil_density_factors.json
```

The sidecar will include cited factors, defaulted fields if any, and explicit
registry version/date fields. It will not add columns to the normalized
production CSV schemas.

Exact sidecar schema:

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-06T00:00:00+00:00",
  "registry_version": "2026-07-06",
  "registry_date": "2026-07-06",
  "conversion_basis": "cited_field_density_factors",
  "coverage_status": "complete",
  "oil_field_count": 1,
  "used_fields": ["Example CORES Field"],
  "defaulted_fields": [],
  "missing_fields": [],
  "factors": [
    {
      "field_name": "Example CORES Field",
      "aliases": ["example cores field"],
      "api_gravity_deg": 30.0,
      "api_gravity_min_deg": null,
      "api_gravity_max_deg": null,
      "bbl_per_tonne": 7.17883,
      "measurement_basis": "representative produced stream",
      "source_title": "source title",
      "source_url": "https://example.test/source",
      "source_class": "technical_literature",
      "evidence_note": "why this value is field-applicable",
      "confidence": "medium",
      "accepted_for_conversion": true
    }
  ]
}
```

`coverage_status` will be `complete`, `defaulted`, or `missing`. A `complete`
sidecar will require every current oil field to be represented in `factors` with
`accepted_for_conversion: true`; otherwise [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)
will remain incomplete.

`refresh_ayoluengo_fixture(...)` will include the relevant conversion factor and
citation metadata in the committed `_metadata.json` fixture. The sample CSV will
continue to contain normalized `oil_bbl` values and will not grow source
provenance columns.

### Scheduler wiring

`SpainCoresRefreshJob.run(...)` will pass optional scheduler config keys into
`CoresLiveProductionLoader`:

```yaml
spain_cores_refresh:
  output_dir: data/spain/cores
  density_registry_path: packages/worldenergydata-spain/src/worldenergydata/spain/data/cores/crude_density_factors.json
  allow_default_density: false
```

If strict density coverage fails, the scheduler job will classify the error as a
deterministic source/coverage failure, not a retryable network failure. The
strict live-loader path will raise the exported `CoresDensityCoverageError` for
missing accepted density factors; the scheduler will treat that exception as
non-retryable alongside the existing `CoresSourceError` contract. The scheduler
test will raise the real exported `CoresDensityCoverageError`, not an arbitrary
fake exception, so the live-loader gap cannot remain retryable by accident.
The job will still preserve the existing direct-source network/source failure
behavior from [#809](https://github.com/vamseeachanta/worldenergydata/issues/809).

`density_registry_path` will use the same `_scheduler_repo_root` resolution
contract as `output_dir` and `fixture_output_dir`: absolute paths pass through,
and relative paths from `config/scheduler/scheduler_config.yml` resolve against
the scheduler repo root before construction of `CoresLiveProductionLoader`.

`_metadata.json` will keep `format: "csv"` for the primary normalized
production tables. The implementation will add separate metadata fields such as
`data_files` and `sidecar_files` so JSON conversion sidecars are not misreported
as primary CSV outputs.

### Report provenance

The Spain CORES report builder will load and validate the normalized density
sidecar when it exists. It will include conversion provenance in the JSON/HTML
summary and will remove the issue-807 limitation only when the sidecar is
`coverage_status: "complete"` and has no defaulted or missing fields.

The report will emit:

- `oil_tonnes_to_bbl_uses_cited_field_density_factors`, when all oil fields
  have cited factors; or
- `oil_tonnes_to_bbl_has_defaulted_fields`, when any fields remain on the
  documented default; or
- `oil_tonnes_to_bbl_has_missing_fields`, when a density sidecar exists but any
  oil fields are missing accepted/defaulted conversion factors; or
- `oil_tonnes_to_bbl_conversion_deferred_to_issue_807`, when no density sidecar
  is available.

## Files to Change

### `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py`

This new module will own registry parsing, API-to-bbl/tonne math, alias
normalization, and validation.

### `packages/worldenergydata-spain/src/worldenergydata/spain/data/cores/crude_density_factors.json`

This new data file will store the cited per-field conversion registry. Each
entry will include the field name, aliases, value, source URL, source title,
source class, evidence note, and confidence.

### `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py`

The parser and `CoresProductionLoader` constructor will accept
`CoresOilConversionAudit` for oil conversion. Oil conversion will use a per-row
factor derived from the melted field name and
`oil_conversion_audit.bbl_per_tonne_for_field(...)`. Gas conversion will remain
unchanged.

### `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py`

The live loader will load/validate the density registry, build the oil
conversion audit, pass that audit into oil parsing, write the conversion
sidecar, and update fixture metadata conversion fields.

### `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/spain_cores_refresh.py`

The scheduler job will pass `density_registry_path` and `allow_default_density`
config values into `CoresLiveProductionLoader`. It will classify deterministic
density coverage errors as non-retryable.

### `config/scheduler/scheduler_config.yml`

The Spain CORES scheduler config will document the density registry path and
default strict behavior.

### `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py`

The production adapter fallback will be updated to avoid stale 7.33-based
Ayoluengo barrels. The preferred implementation will derive default data from
the committed Spain fixture; if an embedded fallback must remain, it will carry
updated values and explicit conversion provenance.

### `packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py`

The report builder will read the conversion sidecar when present and surface
conversion provenance/limitations in the report summary.

### Tests

The implementation will update existing parser/live/report tests and add a
focused density-registry test file.

## TDD Test List

1. `tests/unit/spain/test_cores_density.py::test_bbl_per_tonne_from_api_matches_reference_formula`
   - Assert API 36.0 converts to approximately `7.44554` bbl/tonne.
   - Assert API 20.0 converts to approximately `6.73432` bbl/tonne.

2. `tests/unit/spain/test_cores_density.py::test_density_registry_requires_citation_fields`
   - Build a temporary JSON entry missing `source_url`.
   - Expect the registry loader to raise `CoresParseError` or a density-specific
     `ValueError`.

3. `tests/unit/spain/test_cores_density.py::test_density_registry_rejects_duplicate_aliases`
   - Build two entries with aliases that normalize to the same key.
   - Expect validation failure before parser use.

4. `tests/unit/spain/test_cores_density.py::test_density_registry_rejects_non_representative_range_as_conversion_factor`
   - Build an entry with `api_gravity_min`, `api_gravity_max`, and no
     representative conversion basis.
   - Expect the entry to be retained only as evidence or rejected for
     `accepted_for_conversion`.

5. `tests/unit/spain/test_cores_density.py::test_density_registry_normalizes_accents_and_punctuation`
   - Include aliases for `Boquerón` and `Viura (1)`.
   - Expect lookup keys to resolve without losing display names.

6. `tests/unit/spain/test_cores_density.py::test_density_registry_rejects_invalid_source_class_and_confidence`
   - Use unsupported `source_class` and `confidence` values.
   - Expect validation failure.

7. `tests/unit/spain/test_cores_density.py::test_crude_density_factor_rejects_secondary_article_conversion_directly`
   - Directly construct `CoresCrudeDensityFactor` with
     `source_class="secondary_article"` and `accepted_for_conversion=True`.
   - Expect validation failure even if the factor contains a numeric API value.
   - Repeat with a direct accepted factor that contains only
     `api_gravity_min_deg`/`api_gravity_max_deg` non-representative range
     evidence and no representative `api_gravity_deg`/`bbl_per_tonne`.
   - Repeat through the JSON registry loader to prove both paths share the same
     validator.

8. `tests/unit/spain/test_cores_density.py::test_oil_conversion_audit_rejects_unbacked_conversion_entries`
   - Attempt to directly construct an audit with an accepted secondary-source
     factor, non-representative ranged factor, factor missing `bbl_per_tonne`,
     duplicate keys, or a default key not listed in `defaulted_fields`.
   - Expect validation failure before parser use.

9. `tests/unit/spain/test_cores_loader.py::test_parse_oil_frame_uses_conversion_audit_factor`
   - Parse a two-field oil frame with a `CoresOilConversionAudit` built by
     `build_oil_conversion_audit(...)` from an accepted Ayoluengo factor whose
     `bbl_per_tonne` is `6.95`.
   - Expect Ayoluengo to use `6.95`.

10. `tests/unit/spain/test_cores_loader.py::test_parse_oil_frame_requires_explicit_default_opt_in`
   - Build an audit for Ayoluengo and Casablanca while only Ayoluengo has an
     accepted factor and `allow_default_density=False`.
   - Parse a frame with that audit.
   - Expect `CoresParseError` naming Casablanca.

11. `tests/unit/spain/test_cores_loader.py::test_parse_oil_frame_allows_legacy_default_when_explicit`
   - Build an audit for Ayoluengo and Casablanca while only Ayoluengo has an
     accepted factor and `allow_default_density=True`.
   - Parse a frame with that audit.
   - Expect Casablanca to use `TONNES_TO_BBL`.

12. `tests/unit/spain/test_cores_density.py::test_oil_conversion_audit_names_defaulted_fields`
    - Build an audit for Ayoluengo and Casablanca while only Ayoluengo has an
      accepted factor and `allow_default_density=True`.
    - Expect Casablanca in `defaulted_fields`.

13. `tests/unit/spain/test_cores_loader.py::test_parse_gas_frame_ignores_oil_conversion_audit`
   - Parse a gas frame with a bogus oil conversion audit.
   - Expect GWh-to-Mcf behavior to match the current test exactly.

14. `tests/unit/spain/test_cores_loader.py::test_loader_passes_conversion_audit_to_parser`
   - Write a small XLSX and construct `CoresProductionLoader(product="oil",
     oil_conversion_audit=...)`.
   - Expect the parsed `oil_bbl` to use the override.

15. `tests/unit/spain/test_cores_live.py::test_live_loader_writes_oil_density_sidecar`
   - Run `CoresLiveProductionLoader` against fake oil/gas workbooks.
   - Expect `normalized/cores_oil_density_factors.json` to exist and include
     used/defaulted field lists.

16. `tests/unit/spain/test_cores_live.py::test_live_loader_strict_density_fails_on_source_gaps`
   - Run the live loader against fake oil workbooks containing one unmapped oil
     field and `allow_default_density=False`.
   - Expect `CoresDensityCoverageError` naming the missing field.

17. `tests/unit/spain/test_cores_live.py::test_refresh_ayoluengo_fixture_records_density_provenance`
    - Refresh the Ayoluengo fixture from a fake oil frame and metadata.
    - Expect `_metadata.json` to include the selected Ayoluengo
      `bbl_per_tonne`, `source_url`, and evidence note.

18. `tests/unit/scheduler/test_spain_cores_refresh.py::test_spain_cores_refresh_passes_density_config_to_loader`
    - Run the scheduler job with `density_registry_path` and
      `allow_default_density`.
    - Expect the fake loader constructor to receive both values, with a
      repo-relative `density_registry_path` resolved against
      `_scheduler_repo_root`.

19. `tests/unit/scheduler/test_spain_cores_refresh.py::test_spain_cores_density_coverage_failure_is_non_retryable`
    - Make the fake loader raise the real exported
      `CoresDensityCoverageError`.
    - Expect job status `failure` and `retryable is False`.

20. `tests/unit/scheduler/test_spain_cores_refresh.py::test_spain_cores_refresh_metadata_lists_sidecars_separately`
    - Run a fake successful refresh with a conversion sidecar.
    - Expect `_metadata.json` to keep `format: "csv"` and list the sidecar under
      `sidecar_files`.

21. `tests/unit/scheduler/test_config.py::test_repo_scheduler_config_includes_spain_density_options`
    - Load `config/scheduler/scheduler_config.yml` through the real scheduler
      config loader.
    - Expect `spain_cores_refresh` to expose `density_registry_path` and
      `allow_default_density: false`.

22. `tests/unit/production/unified/test_spain_cores_adapter_loader.py::test_adapter_accepts_live_cores_loader`
    - Update expected oil barrels if the default live loader applies a cited
      Ayoluengo factor.

23. `tests/unit/production/unified/test_spain_cores_adapter_loader.py::test_default_adapter_uses_density_adjusted_fixture_or_marked_fallback`
    - Construct `SpainCoresAdapter()` without injecting a loader.
    - Expect default Ayoluengo data to match the committed fixture or an
      explicitly updated fallback with conversion provenance.

24. `tests/unit/production/unified/test_spain_cores_adapter_loader.py::test_embedded_adapter_fallback_does_not_use_stale_733_barrels`
    - Force the production adapter onto `_EmbeddedCoresFixtureLoader` by
      monkeypatching the Spain fixture import path to raise `ModuleNotFoundError`
      or by removing the embedded fallback entirely.
    - Expect embedded fallback oil barrels to match the density-adjusted fixture
      or expect the fallback-removal path to raise a clear missing-fixture error.

25. `tests/unit/spain/test_cores_field_development_report.py::test_build_report_includes_density_conversion_provenance`
    - Write a report cache with the density sidecar.
    - Expect the summary to include the factor source and no longer include
      `oil_tonnes_to_bbl_conversion_deferred_to_issue_807` only when coverage is
      complete.

26. `tests/unit/spain/test_cores_field_development_report.py::test_report_preserves_defaulted_density_limitations`
    - Write a report cache whose sidecar lists a defaulted field.
    - Expect the summary and HTML to include
      `oil_tonnes_to_bbl_has_defaulted_fields`.

27. `tests/unit/spain/test_cores_field_development_report.py::test_report_preserves_missing_density_limitations`
    - Write a report cache whose sidecar has `coverage_status: "missing"` and a
      non-empty `missing_fields` list.
    - Expect the summary and HTML to include
      `oil_tonnes_to_bbl_has_missing_fields` and the exact missing field names.

28. `tests/unit/spain/test_cores_field_development_report.py::test_report_rejects_malformed_density_sidecar`
    - Write a sidecar missing `coverage_status` or `factors`.
    - Expect `CoresReportError`.

29. `tests/unit/spain/test_cores_field_development_report.py::test_render_html_keeps_density_provenance_self_contained`
    - Render HTML with complete density provenance.
    - Expect no `/mnt/ace`, no `src=`, strict JSON, and visible conversion
      source metadata.

## Acceptance Criteria

- `parse_cores_frame(..., product="oil", oil_conversion_audit=...)` will support
  per-field oil conversion while preserving current output columns and keeping
  conversion provenance attached at the parser boundary.
- `parse_cores_frame(..., product="gas")` will remain unchanged.
- A cited crude density/API registry will live in the Spain package data tree.
- Registry entries will fail validation if they lack citation/provenance fields.
- Registry entries will fail validation as conversion factors when they are
  based only on ranges, discovery-test-only values, or non-representative notes.
- Registry entries will fail validation as conversion factors when they use
  `industry_technical_article` or `secondary_article` source classes.
- Direct `CoresCrudeDensityFactor(...)` construction will run the same
  validation as registry loading, so tests cannot bypass provenance by manually
  creating accepted invalid factors.
- Conversion audits will fail validation if a parsed field conversion value is
  not backed by an accepted cited factor or an explicit defaulted-field entry.
- Strict oil conversion will fail closed when any oil field lacks an accepted
  cited factor.
- Legacy/default oil conversion will remain possible only through explicit
  `allow_default_density=True` opt-in and will identify defaulted fields in
  conversion metadata.
- [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) will be
  closed only when every current CORES oil field has an accepted cited factor.
  If source gaps remain, the implementation will stop with a source-gap comment
  and leave the issue open.
- Live CORES refresh will write normalized production CSVs plus a density
  conversion sidecar under the configured cache root.
- Scheduler config will pass density registry options to the live loader and
  classify strict density coverage gaps as non-retryable deterministic failures.
- Scheduler wiring will resolve repo-relative `density_registry_path` values
  through `_scheduler_repo_root` before passing them to the live loader.
- Scheduler retry classification will use the real exported
  `CoresDensityCoverageError` for strict density gaps.
- The committed Ayoluengo fixture metadata will record the oil conversion factor
  and citation used to produce its `oil_bbl` values.
- The Spain CORES report will surface conversion provenance and will not remove
  the [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)
  caveat unless the density sidecar is complete and has no
  defaulted or missing fields.
- Missing density coverage will be visible in metadata/report limitations and
  will not be described as real per-field conversion.
- Present sidecars with `coverage_status: "missing"` will surface
  `oil_tonnes_to_bbl_has_missing_fields` and exact missing field names in the
  report.
- The production adapter fallback will not retain stale 7.33-based embedded
  Ayoluengo barrels.
- The embedded production adapter fallback path will be directly exercised or
  removed, so production-only installs cannot keep stale 7.33-based rows hidden
  behind the package fixture loader path.
- Targeted tests will pass:

```bash
uv run python -m pytest \
  tests/unit/spain/test_cores_density.py \
  tests/unit/spain/test_cores_loader.py \
  tests/unit/spain/test_cores_live.py \
  tests/unit/scheduler/test_spain_cores_refresh.py \
  tests/unit/scheduler/test_config.py \
  tests/unit/production/unified/test_spain_cores_adapter_loader.py \
  tests/unit/spain/test_cores_field_development_report.py \
  -q
```

- Formatting and scan gates will pass:

```bash
uv run black --check packages/worldenergydata-spain packages/worldenergydata-scheduler/src packages/worldenergydata-production/src tests/unit/spain tests/unit/scheduler tests/unit/production/unified
uv run isort --check-only packages/worldenergydata-spain packages/worldenergydata-scheduler/src packages/worldenergydata-production/src tests/unit/spain tests/unit/scheduler tests/unit/production/unified
scripts/legal/legal-sanity-scan.sh
uv run pre-commit run check-yaml --files config/scheduler/scheduler_config.yml
uv run pre-commit run yamllint --files config/scheduler/scheduler_config.yml
```

## Risks

| Risk | Mitigation |
|---|---|
| CORES does not publish density/API in the production workbook. | Keep CORES as production source and require separate cited density sources with explicit source class/confidence. |
| A field-level source gives a range rather than a single representative factor. | Store range/evidence note and use a single factor only when the source supports one; otherwise mark the field defaulted/missing. |
| Parser defaults could hide missing density coverage. | Require explicit `allow_default_density=True` tests and conversion sidecar/report limitations for defaulted fields. |
| Updating normalized CSV schemas could break downstream adapters. | Keep production CSV columns unchanged; put conversion provenance in a sidecar and report metadata. |
| Ayoluengo API evidence conflicts across sources. | Prefer conversion-eligible sources in order: regulator/operator/filing records, crude assays, then peer-reviewed or technical literature; keep industry articles and surveys as evidence-only leads unless backed by an underlying conversion-eligible source. |
| Generated fixture values may change when the density factor changes. | Update fixture metadata and tests in the same TDD cycle as parser wiring. |
| Scheduler config may not propagate density settings. | Add scheduler config keys, resolve repo-relative `density_registry_path` through `_scheduler_repo_root`, pass the resolved path into `CoresLiveProductionLoader`, and test the fake loader constructor receives it. |
| `_metadata.json` may misclassify JSON sidecars as CSV outputs. | Keep `format: "csv"` for production tables and list conversion sidecars separately in metadata. |
| Parser conversion and sidecar provenance may drift. | Use one conversion-audit helper for parser inputs and sidecar generation. |
| Production adapter fallback may keep stale embedded barrels. | Directly force the embedded fallback path in tests, or remove it and test the clear missing-fixture error. |

## Review Plan

Plan-stage adversarial review will inspect this plan for:

- source-evidence overclaiming;
- silent fallback to the global default;
- downstream breakage from metadata/schema changes;
- missing tests for strict density coverage; and
- failure to update the [#810](https://github.com/vamseeachanta/worldenergydata/issues/810)
  report caveat.

Review artifacts will be written under:

```text
scripts/review/results/2026-07-06-plan-807-*.md
```

The issue will stay unapproved until the review findings are addressed and the
user explicitly approves implementation.
