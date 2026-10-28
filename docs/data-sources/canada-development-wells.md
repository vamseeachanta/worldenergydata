# Canada development-well enrichment

Supplied ArcGIS feature attributes can enrich Canada FieldConcept inputs with
well-inventory counts and a representative water depth. The implementation is
offline: it accepts authorized input and makes no service requests. Real source
records and derived field depths are not committed.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Add an offline contract so enrichment can be tested while live access remains deferred. |

## Input contract

Import `DevelopmentWellMapping`, `parse_development_wells` and
`summarize_field_wells` from `worldenergydata.canada.development_wells`.
The parser requires a complete ArcGIS JSON feature response and these explicit
attribute mappings:

| Normalized attribute | Required caller evidence |
| --- | --- |
| `uwi` | Non-empty textual well identity; preserved without onshore UWI parsing. |
| `field_name` | Non-empty explicit field linkage, supplied or verified by the caller. |
| `water_depth_m` | Source depth is in metres; no unit conversion is inferred. |
| `latitude`, `longitude` | Coordinate columns and their reference system are verified by the caller; no reprojection is performed. |
| `source` argument | Non-empty provenance identifier for the authorized input. |

Mapped columns must exist. Null and blank numeric cells remain unknown; other
malformed or non-finite numbers raise. Depth must be non-negative, following
`field_development.models.FieldConcept.must_be_non_negative`. Coordinates come
from mapped attributes, not an assumed interpretation of ArcGIS geometry.

The parser rejects ArcGIS error responses and `exceededTransferLimit` responses.
It performs no pagination. A caller must assemble a complete result before
parsing; an omitted transfer-limit flag alone cannot prove completeness.
Exact duplicate UWI records collapse. Conflicting records with the same UWI
raise, including conflicts between fields or coordinate values. Separate pages
can be combined before summarization only after completeness has been verified.

## Reduction and precedence

Field matching strips surrounding whitespace and ignores case. It never guesses
linkage from a well name or uses fuzzy field matching. Within each linked field,
the reduction uses each unique UWI once, excludes null depths, and calculates
the median. For sorted depths, the odd-count median is the middle depth; the
even-count median is the arithmetic mean of the middle pair. This follows the
[NIST/SEMATECH e-Handbook, section 1.3.5.1, Measures of Location](https://www.itl.nist.gov/div898/handbook/eda/section3/eda351.htm#MEDIAN)
(online edition retrieved 2026-10-19), implemented by
[Python statistics.median](https://docs.python.org/3/library/statistics.html#statistics.median)
(documentation retrieved 2026-10-19). No engineering coefficients or acceptance
tolerances are introduced.

Pass parsed records as `development_wells=` to `canada_field_to_concept`,
`build_canada_field_concept` or `run_canada_reference_chain`. The precedence is:

1. Explicit `water_depth_m` and `num_wells` metadata.
2. Median non-null linked well depth and unique linked UWI inventory count.
3. Existing depth defaults, where available; otherwise depth remains unknown.

Legacy depths are **assumed, based on previous experience**; this change does not
validate those defaults. `FieldConcept.data_source` retains the input source and
adds `water_depth=provided`, `water_depth=development_wells_median`,
`water_depth=legacy_default` or `water_depth=unknown`. Linked inventory sources
are also recorded. `summarize_field_wells` returns sorted UWI and source tuples
for deterministic inspection. A representative median is not a design envelope.

The inventory count includes supplied wells with unknown depth. It does not
establish a producing-well count, planned-well count or drilling timeline.
Explicit well counts therefore take precedence. FieldConcept has no coordinate
or UWI fields; those attributes remain on the individual `DevelopmentWell`
records. No canonical schema or downstream depth classifier is changed.

## Verification and limits

Offline synthetic tests cover explicit mapping, identity and coordinate
retention, null preservation, malformed/partial responses, duplicate integrity,
odd/even medians, field linkage, precedence, provenance and reference-chain
integration. Expected medians use Python's published example or hand
calculations written in the test docstrings.

The ArcGIS response structure follows
[Esri Query (Feature Service/Layer), JSON response syntax](https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/)
(documentation retrieved 2026-10-19). This generic protocol reference does not
verify the regulator's layer schema, coverage, units, linkage or licensing.

Live endpoint discovery, source column names, source units, coordinate reference,
coverage and reuse permission are **NOT_EVALUATED**. The access hold recorded on
issue #818 remains applicable; no further regulator access is needed by this
offline implementation. A later slice can add bounded runtime fetching,
external caching and a reproducible retrieval manifest after access permission
and source metadata have been confirmed. Drilling dates, active-well status and
development-system overrides remain later work.
