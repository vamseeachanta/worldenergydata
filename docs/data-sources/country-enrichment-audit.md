# Country enrichment identity and provenance audit

## Summary

This bounded audit follows issue #1164. Missing field links are excluded from
SODIR joins, existing observation columns retain their values and origins, and
an exhausted FeatureServer byte budget prevents another request. Australia
requires a non-blank textual well identifier and integer byte limits. Offline
regressions exercise repeated enrichment, changed access terms and remaining
budgets. Partial enrichment pairs imported values with their own origins and
rejects orphan evidence. These checks establish software behavior, not current
source permissions.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-21 | Record inspected coverage, correct observed identity and budget defects, and provide reproducible synthetic cases. |
| 1 | 2026-10-25 | Pair imported values with their own origins, reject orphan evidence, and define the shared-source limit for partial enrichment. |

## Scope and method

The inventory searched the Australia, Brazil ANP, Canada, Mexico CNH, SODIR,
Spain, UKCS and West Africa packages for field-concept adapters, enrichment,
field joins and source clients. Detailed inspection was limited to the paths
below. Existing Brazil missing-name protection is retained. Tests use synthetic
identities and distinguishable values; no regulator rows are downloaded.

| Country path | Inspection and exercised behavior | Limits |
| --- | --- | --- |
| Australia `metadata/well_enrichment.py` | Exact explicit field/well links; missing identifiers cannot select a well; measured depth and coordinate origins survive repetition, empty input and unusable new measurements. | Datum transformation and automatic field matching are outside scope. |
| Australia `metadata/nopta_wells.py` | Full terms-byte digest checked before queries; a retained licence sentence with an appended automation ban stops queries. Later requests receive the remaining data-byte budget; exhaustion stops requests. | Access preflight responses have separate existing response caps; the aggregate budget covers query responses only. Current terms and redistribution rights are NOT_EVALUATED. |
| Brazil ANP `field_concept.py` | Existing null-name guards and deterministic metadata reduction; supplied measured depth and source survive repeated concept conversion. | The reducer returns source metadata without an origin map. New provenance inference is outside scope. |
| SODIR `datasets.py` | Both wellbore and production joins exclude null/blank source identities, reject conflicting supplemental rows, and preserve existing observation columns. Repetition retains source evidence. | No unit conversion or physical eligibility is inferred by the join. |
| SODIR `feature_service.py` | Remaining-byte transport caps, exact-budget terminal pages, and no request after aggregate exhaustion. | There is no reviewed-terms digest preflight in this connector; changed-access-policy coverage is NOT_EVALUATED. |
| SODIR, Canada, Spain and UKCS `field_concept.py` | Repeated conversion of supplied metadata preserves depth and the source string without mutating input. | These are sparse converters, not re-enrichment functions. Arbitrary origin dictionaries are not mapped into FieldConcept. |
| Brazil ANP `production/anp_client.py`; UKCS `production/nsta_client.py` | Download paths inspected: response bodies are consumed without an aggregate byte cap or reviewed-terms comparison. | Policy-change and remaining-byte safeguards are NOT_EVALUATED; separate connector changes need reviewed policy evidence and explicit budgets. |
| Canada `production/cnloer_loader.py` | Inspected loader consumes local or injected content; runtime downloading is documented as a follow-on. | Network policy checks are not applicable to this loader. |
| Spain `production/cores_source.py` | Discovery and workbook-download boundaries inspected. | Workbook validation does not assess changed automation terms or remaining aggregate bytes; these checks are NOT_EVALUATED. |
| Mexico CNH and West Africa | No FieldConcept adapter or dedicated field-metadata enricher found in the inventory. | API clients and other normalization/lookup paths remain unexamined. |

BSEE, EIA, service-specific Canadian clients, legacy SODIR transport, Spain's
`production/cores_live.py` oil/gas merge, and non-country enrichment engines
remain unexamined. Discovery is not a claim of complete connector coverage.
A NOT_EVALUATED entry is not permission to fetch.

## Identity and observation policy

[pandas DataFrame.merge, API reference (2026), Warning and validate parameter](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html)
documents that two null keys match by default, and that a many-to-one merge
requires unique right-side keys. SODIR instead excludes null and blank source
keys, collapses equal supplemental rows, and rejects conflicting rows with
`pandas.errors.MergeError`. Numeric identities retain their type; literal text
such as `nan` remains a name. No coercion joins numeric and textual identities.

Existing observation columns are authoritative, including unknown values.
Only new columns are added. Filling an unknown observation from field metadata
would require a separate value/origin policy. This also prevents `_x`/`_y`
suffixes on repeated joins. The wellbore completeness denominator excludes its
own previously calculated indicator so repetition does not inflate it.

Supplemental origin entries are restricted to newly imported value columns.
Entries for retained values, including null observations, are discarded before
supplemental rows are compared. New entries extend the existing origin map
without changing its retained entries or mutating either input. Supplemental
origin maps are dictionaries or null; other forms raise `pandas.errors.MergeError`.
Null evidence establishes no origin. Output origin maps are copied recursively
per row, so changing one output's evidence cannot alter another row or an input.

An existing origin entry for an absent value cannot label an imported fallback.
A matched record with that ambiguity raises `pandas.errors.MergeError` and
requires correction of the observation/evidence pair before enrichment. A
non-null existing source without any observation columns also raises when
new values would be imported. These checks apply to every matched record;
unlinked records receive no supplemental evidence.

The shared `source` column describes retained observations when it already
exists. It does not establish the source of supplemental additions. A new
supplemental `source` is copied only when the input has no observation columns,
so all non-key values come from the supplemental row. If any observation column
is retained, including an unknown value, a supplemental source is omitted.
Sources for new values in such mixed records remain unestablished; the join
does not invent a per-value source schema.

The wellbore entry point intentionally imports only field identity, name,
operator and discovery year. Supplemental depths, sources and origin maps
are excluded by that projection. Existing observation values and evidence
remain intact; provenance-bearing supplemental values are handled by the
production entry point.

Australia's normalized well schema declares `well_identifier` as string or
null (`packages/worldenergydata-australia/src/worldenergydata/australia/data/nopta_well.schema.json`).
Nontext and blank identifiers are therefore ineligible for explicit linkage.
The spatial-reference identifier used by the tests comes from the existing
synthetic layer fixture, not a newly assumed datum code.

## Worked example: explicit links and preserved measurements

The inputs below are synthetic software sentinels, not engineering data. The
depths distinguish an observation from a fallback; no acceptance threshold is
applied. The calculation is an explicit left join: only the `linked` identity
selects metadata; the missing identity selects nothing. The observation depth
and origin already exist, so they remain authoritative.

```python
import pandas as pd
from worldenergydata.sodir.datasets import DatasetGenerator

records = pd.DataFrame({
    "field_id": ["linked", None],
    "water_depth": [12, None],
    "source": ["synthetic measurement", None],
    "value_origins": [{"water_depth": "measured"}, None],
})
fields = pd.DataFrame({
    "field_id": ["linked", None],
    "field_name": ["synthetic", "unlinked"],
    "water_depth": [99, 99],
    "source": ["synthetic fallback", "synthetic fallback"],
})
generator = DatasetGenerator()
result = generator.create_production_dataset(records, fields)
assert result["field_name"].fillna("missing").tolist() == ["synthetic", "missing"]
assert result.loc[0, "water_depth"] == 12
assert result.loc[0, "source"] == "synthetic measurement"
assert result.loc[0, "value_origins"] == {"water_depth": "measured"}
pd.testing.assert_frame_equal(
    result, generator.create_production_dataset(result, fields)
)
```

Hand answer: two input rows produce two output rows, one linked field name,
and the retained measured depth of 12 m. No depth is inferred for the unlinked
record. This combines the missing-link and repetition cases exercised by the
offline regression tests.

## Worked example: policy changes and byte budgets

For synthetic reviewed terms `Synthetic licence sentence.`, the test supplies
their SHA-256 digest as the reviewed evidence. Appending
`Automated access forbidden.` changes the full digest while retaining the
licence sentence. Expected data-query count is zero. Unchanged terms allow the
synthetic terminal query. This exercises the existing preflight through the
fetch entry point; it does not replace the production reviewed digest.

The byte-budget rule in issue #1164 is pure accounting:
`remaining = aggregate_limit - sum(length_of_previous_query_responses)`.
In the tests, a first page has length L and the caller provides L + R bytes.
For R = 1 the second transport cap is exactly one byte; for R = 0 no subsequent
request starts. A terminal response of exactly L bytes succeeds with budget L.
These caller-selected software counts are not source rate limits or engineering
acceptance values. Policy requests are separate from the data-query budget.

## Verification and remaining coverage

The regression files are `tests/unit/sodir/test_enrichment_links.py`,
`tests/unit/sodir/test_feature_budget_audit.py`,
`tests/unit/australia/test_enrichment_audit.py`, and
`tests/unit/audit/test_country_enrichment.py`. Expected rows, source strings,
depth sentinels and budget arithmetic are specified independently in their
docstrings. Network boundaries are blocked in transport tests. Existing Brazil
link tests and the tests of all changed modules are included in validation.

Initial validation recorded 58 passing new regression cases. Its combined module run produced 284 passes
and three existing snapshot failures at
`tests/unit/australia/test_field_concept_opt_in.py:27`: the recorded outputs
omit `flowline_liquid_rate_bpd`, already present in
`src/worldenergydata/field_development/models.py:80` on `origin/main`.
Reading the unchanged test, model and snapshots on that reference establishes
the baseline mismatch. Ruff reported 54 diagnostics on unchanged source spans;
the new tests passed with first-party import classification matching the
repository's isort configuration. Black, isort, the repository structure check,
the engineering-register check and the documented example passed.

Partial-enrichment validation ran all SODIR, Australia and audit unit tests:
the unchanged head produced 1,081 passes and three baseline snapshot failures;
the revised code produced 1,096 passes and the same three failures with
`PYTHONUTF8` unset. The SODIR enrichment file now contains 51 cases, including
15 additional cases. Eleven new cases failed before their corresponding fixes;
four positive cases exercise complete imports, a later-row guard and the
wellbore projection with and without existing observations. The three
baseline failures remain at the unchanged assertion described above. Broader
repository suites and live-source access were not run for this revision.

No engineering coefficients, datum conversions or classification thresholds
are added. Existing conversion constants and classifications are outside this
audit. Remaining work is source-specific policy evidence for the connectors
marked NOT_EVALUATED, plus audit of the unexamined clients. Independent review
is required before maintainer merge; issue #1164 remains open for that coverage.
