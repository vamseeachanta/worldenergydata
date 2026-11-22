# Onshore underwriting join contract

The existing Texas RRC, Kansas KGS, Oklahoma OCC, Colorado ECMC and derived
pressure-screen outputs can be inspected with a bounded local audit. This
contract supports the first diligence pack under issue #915 and parent #909.
It supplies explicit identifiers, grains and unresolved evidence requirements;
it does not establish statewide coverage or title ownership.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Define local inventory and structural join checks so ingestion evidence can be consumed without implicit identity or coverage assumptions. |

## Evidence basis and existing work

The source map below is based on repository code, checked-in reports and the
linked issue descriptions. Downloaded production files were not available for
inspection during this implementation. Historical run results in the linked
reports are evidence of those runs only. Materialization, source vintage,
rights, freshness and dataset digests require the inventory from blocker #910
and a local audit of the selected snapshots. The shared source-catalog and
domain-database indexes were unavailable; their absence establishes no source
absence. Caller dataset IDs are local audit aliases, not newly issued catalog IDs.

| Work | Existing implementation or report | Reuse |
| --- | --- | --- |
| Pressure program #708 | [Multi-state screen report](state-well-databases/underpressured-gas-fields.md) | Pressure/depletion coverage and interpretation limits |
| Texas #709 | [Pressure observations](texas-rrc/pressure-observations.md); `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/` | API14 observations, source forms, quality sidecars |
| Kansas #725 | [KGS ingest](state-well-databases/kansas-kgs-ingest.md); [package report](kansas-kgs/pressure-observations.md) | Two output variants; inspect schema before choosing key |
| Mixed-source screen #732 | `src/worldenergydata/analysis/underpressured_screen/observations.py` | Existing source/era normalization; no new pressure model |
| Oklahoma #740 | `src/worldenergydata/modules/state_regulators/oklahoma_occ/{pipeline,parsers}.py` | Structured completion observations; production acquisition remains deferred |
| Colorado #745 | `src/worldenergydata/modules/state_regulators/colorado_ecmc/{pipeline,parsers,schema}.py` | Wells and production spine; no usable pressure rows in the reported run |
| Colorado #751 | [Pressure source discovery](state-well-databases/colorado-ecmc-pressure-source-discovery.md); `colorado_ecmc/facility_detail_candidates.py` beside the modules above | FacilityDetail/Form 5A remains candidate-only and sample-limited |
| Texas atlas #659, #660, #661 | [Source catalog](texas-rrc/source-catalog.md), [storage contract](texas-rrc/storage-contract.md), [raw refresh](texas-rrc/raw-refresh.md) | Existing source identities, snapshots and manifests |
| Texas #662, #663, #664 | [Lifecycle](texas-rrc/well-lifecycle-spine.md), [production](texas-rrc/production-field-atlas.md), [development metrics](texas-rrc/field-development-metrics.md) | Well, district, lease, field and operator grains |
| Texas #665, #666 | [Infrastructure](texas-rrc/infrastructure-access-metrics.md), [atlas reports](texas-rrc/field-atlas-reports.md) | Spatial context and documented output artifacts |

Issue references are traceable by number in this repository. These existing
modules are extended by consumption, without changing their ingestion behavior.

## Coverage and join readiness

All entries describe available code or documented runs, not a new live inventory.
Missing evidence means `NOT_EVALUATED`, never an empty-but-ready dataset.

| Domain | Texas | Kansas | Oklahoma | Colorado |
| --- | --- | --- | --- | --- |
| Wells | Lifecycle API14 anchor; API10 is a coarser grouping | Wells master API10/API14, with KID disambiguation | Completion-derived identity; not a full wells census | Wells API12/API10 and facility ID; API10 can collapse sidetracks |
| Production | PDQ lease/district/field/month; no implicit well allocation | Proration flow/rate observations do not establish monthly production coverage | Tax Commission production acquisition deferred | Form 7 production reports: facility/API/report year/month; inspect amendments |
| Permits/completions | Lifecycle permit and completion milestones; preserve event grain | Wells-master dates; no demonstrated full permit history | Form 1002A completion/test rows; pre-2010/OCR deferred per #740 | Wells context and Form 5A samples; not statewide permit/completion coverage |
| Pressure/depletion | Completion API14/test date/type; proxy flags required | KID or API variant plus year/test; earliest available is not virgin pressure | API/completion/test date and pressure kind; formation is not a verified field | Form 7 path yielded no curated pressure rows; Form 5A casing/tubing candidates excluded from screen promotion |
| Fields | District plus field number; names are labels | Field label needs reviewed crosswalk for stable identity | `field` may be formation name; no automatic field equivalence | Field code/name from wells; qualify by source and state |
| Operators | Operator number plus source vintage; names can change | Legacy pressure has operator labels; authoritative mapping unverified | Operator number/name from completions; qualify by snapshot | Operator number/name from Form 7; preserve report time |
| GIS/infrastructure | Well/pipeline geometry and field metrics; CRS and geometry revision required | Wells coordinates available; infrastructure coverage unverified | No infrastructure overlay demonstrated by completion ingest | Wells GIS available; pipeline coverage unverified |
| HSE/environmental | No qualified HSE join in this contract | No qualified HSE join | No qualified HSE join | No qualified HSE join; bradenhead/MIT tests are not reservoir pressure |

HSE overlays require a separate source inventory, location/CRS check, temporal
intersection and identity crosswalk. Lack of an overlay does not imply lack of
incidents. No row in this matrix establishes mineral, lease or title rights.

## Stable identity rules

- All joins are state-qualified. Identifiers remain strings, including leading
  zeros. Canonical key names map explicitly to physical column names in the
  audit configuration. No fuzzy matching or name-only field joins are performed.
  If a `state` column is present, every row must match the declared state.
  Mixed-state pressure-screen outputs require selected per-state views; source
  rows are never silently relabelled using configuration.
- API10, API12 and API14 are distinct grains. Only spaces and hyphens are removed
  from complete APIs; numeric/scientific notation, wrong-state prefixes and
  incomplete IDs are rejected. No completion suffix is invented or truncated.
  Texas's ingestion normalizer has broader padding behavior; audit that result,
  rather than applying that behavior to another state's source.
- Kansas has two maintained outputs: the state-regulator pipeline's `well_key`
  is the source `WELL_KID`; the package output carries API columns and resolves
  ambiguous API10 using `well_kid`. Never equate KID with API based on string
  length. Require a reviewed KID-to-API crosswalk for joins between those variants.
- Texas lease production requires the district/field/lease keys appropriate to
  the selected atlas table. Preserve product/lease type where the selected source
  requires it. A well-to-lease bridge can multiply production; allocation requires
  a separate reviewed rule. Pressure-screen field rankings grouped by display
  names are derived screening artifacts, not stable multi-state field entities.
- Use event keys (completion number, test date/year, pressure kind) for observation
  uniqueness. A repeated well key is expected on an observation table. For a
  well lookup declare `unique: true`; for observations use `unique: false` and
  audit the event grain separately when needed.

The API shape sources are the existing Texas `lifecycle/keys.py`, Kansas
`tests/unit/state_regulators/test_kansas_kgs.py` source sample, Oklahoma
`tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py` compatibility
fixtures, and Colorado `normalization.py`/`parsers.py`. These are compatibility
rules for existing outputs, not certification of a regulator's entire API registry.

## Audit interface and method

Run `python -m worldenergydata.analysis.onshore_join_readiness` with `--config`,
`--root` and `--output`. The root is the supplied local data directory; every
configured input and manifest is a relative path contained within it, including
after symlink resolution. There is no crawl, download, archive extraction or
source mutation. Reports contain metadata and counts, not row values.

The [example configuration](../../../examples/onshore-joins/input.json) defines
the required dataset fields: `id`, existing `source_id`, `source_version`,
`state`, `domain`, `path`, `status`, ordered `keys` and boolean `unique`.
Record the actual source version/snapshot identifier, not filesystem mtime.
The supported inventory vocabulary is `downloaded`, `derived`, `configured-only`,
`partial/error`, `missing` and `private/legacy`. Only explicitly declared
downloaded/derived files are read. Private/legacy entries remain quarantined.
CSV and Parquet are supported; Parquet requires PyArrow. There is no implicit
conversion of numeric identifiers. Relative paths and SHA-256 identify the
observed bytes; source and rights assertions still need independent evidence.

Each table reports byte size, digest, rows, invalid keys, distinct valid keys and
duplicate excess. Missing columns, malformed CSV rows, invalid keys or duplicates
on a declared unique grain fail the structural check. Empty/unreadable/missing
tables are `NOT_EVALUATED`. There is no empirical tolerance or engineering
coefficient: acceptance follows the declared relational constraint exactly.

For valid keys k with left multiplicity L(k) and right multiplicity R(k):

- Duplicate excess = total valid rows minus distinct valid keys.
- Matched left rows = sum of L(k) where R(k) is positive.
- Inner join rows = sum of L(k) multiplied by R(k).
- Left join rows = inner join rows plus unmatched left rows.

These equations follow directly by enumerating pairs in a relational join; this
is their derivation, with independent enumerations in the test docstrings.
The public reference is the [PostgreSQL 18 manual, section 7.2.1.1,
Joined Tables](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-JOIN)
(accessed 2026-10-20): a cross product enumerates all pairs, an inner join retains
matching pairs, and a left join adds each unmatched left row once. Grouping those
pairs by key yields the multiplicity equations above. Duplicate excess is the
definition of row count minus distinct key count, rather than an empirical model.
Each declared join expects many-to-one cardinality, complete left coverage and
passing input tables. Duplicate projected right keys or any unmatched left key
fail. No materialized join or allocation is written. `PASS` means only that
the selected keys satisfy these structural conditions. It does not validate
pressure, units, vintage, rights, spatial accuracy or financial suitability.

Memory grows with distinct key tuples; select bounded snapshots. Parquet is read
in batches using only key columns; hashing reads the complete selected file.
Inputs must be immutable while audited. The CLI's successful exit means report
creation; consumers inspect every `join_status`. The output is created
exclusively, so an existing file cannot be overwritten.

## Completion-manifest drift

Issue #915 records Texas completion status `error` alongside an existing raw ZIP.
This has not been resolved by inspecting that external snapshot. Supply an
`artifacts` entry with `source_id: completion_data`, the relative ZIP `path` and
relative `manifest` path. The existing single-snapshot manifest shape is defined
in `texas_rrc/raw_manifest.py`: `source_id`, `status`, `raw_path`, checksum and
retrieval metadata. An aggregate status index must first be resolved to that
individual snapshot record; it is not silently interpreted as one.

The audit emits `manifest_error_with_raw_zip` when a ZIP marker exists beside an
error record. This remains `NOT_EVALUATED`: ZIP presence is not proof of complete
contents, checksum agreement, source/version identity or successful normalization.
Other artifact outcomes remain `NOT_EVALUATED` as well. Preserve both originals;
the next reviewer compares manifest checksum/path/retrieval metadata against
the specific archive, validates members and inspects parser/quality reports.
Neither record is repaired or automatically promoted by this audit.

## Worked example and diligence-pack handoff

The bundled files are synthetic structural fixtures, not downloaded observations.
From the repository root, with the source directory on the Python import path:

```bash
PYTHONPATH=src python -m worldenergydata.analysis.onshore_join_readiness \
  --config examples/onshore-joins/input.json \
  --root examples/onshore-joins --output "$TMPDIR/onshore-audit.json"
```

Inputs: wells A and B; observations A, A and B. The well lookup is unique;
observation well keys may repeat. Independent enumeration gives two matches for
A and one for B: three inner rows, three left rows, no unmatched rows and no
right duplicates. Both table checks and the join return `PASS`. The example
contains no pressure magnitude, physical coefficient or underwriting threshold.

For the first diligence pack, retain the audit report alongside the source
inventory, immutable snapshot references, source manifests, quality sidecars,
units/pressure-kind/era definitions and reviewed crosswalks. Keep raw and heavy
derived files on the existing data disk; only code, this contract and small
synthetic fixtures belong in Git. An absent audit or any `NOT_EVALUATED` result
blocks claims for that domain; unrelated structural passes do not clear it.
Colorado pressure remains excluded pending interpretation and coverage evidence.

## Follow-up

Run against the inventory from #910, reconcile the actual completion ZIP and
manifest, qualify rights/freshness and implement any required identity crosswalks.
Statewide Form 5A promotion, production allocation, HSE spatial joins and title
search are later work; this contract does not represent them as completed.
