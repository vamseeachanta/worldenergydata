# IEA Methane Tracker integration evaluation

## Summary

Conditionally adopt the IEA Methane Tracker as a country-level methane reference
for the prospective ESG module. Defer ingestion until published files can be
inspected and their rights confirmed. Country estimates cannot supply individual
facility or operator emissions. Defer the abatement model to a separate review.

The evaluation is a dated publication assessment, not an emissions dataset or a
live source monitor. The implementation runs offline and introduces no emissions
constants, conversion factors, acceptance limits or numerical equations.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Separate report evidence from unopened database files so integration decisions retain their evidence limits. |

## Opened sources

All sources were requested without login, credentials, cookies or forms. The
responses and retrieval metadata were retained outside the repository. No data
from the explorer's undocumented backing service was used.

| Key | Publication and relevant sections | Retrieved (UTC) | HTTP status |
| --- | --- | --- | --- |
| report_2025 | [IEA (2025), Global Methane Tracker 2025](https://www.iea.org/reports/global-methane-tracker-2025), About this report, Published and Licence | 2026-10-19 17:28:45 | 200 |
| documentation_2025 | [IEA (2025), Global Methane Tracker Documentation, 2025 version](https://iea.blob.core.windows.net/assets/451af9a0-8736-40dc-b843-69275d6fdb07/GlobalMethaneTracker2025Documentation.pdf), Methane emission estimates and Upstream and downstream oil and gas, pp. 5-8 | 2026-10-19 17:29:29 | 200 |
| product_2026 | [IEA, Methane Tracker Database and Methane Abatement Model](https://www.iea.org/data-and-statistics/data-product/methane-tracker-database-and-methane-abatement-model), Overview, Data sets, Schedule, Licence and Download notice; current release May 2026 | 2026-10-19 17:29:03 | 200 |

The documentation is identified by its cover and download link as the 2025
version. Some preliminary running headers retain an older year; the cited
methane-estimation section is headed 2025. Neither that document nor the report
establishes the actual schema of the current download files.

## Findings and decision basis

| Question | Finding | Evidence and limit |
| --- | --- | --- |
| Geographic grain | CONFIRMED | Product Overview describes country and regional estimates. Suitable as a national reference; facility or operator attribution would require a different source. |
| Historical data | CONFIRMED announcement; NOT_EVALUATED file coverage | The 2025 report announces country-level history. No country list, year range, completeness or revision policy has been verified in published files. |
| Estimation method | CONFIRMED publication description | Documentation pp. 5-8 describes activity data and country-specific emission intensities, informed by measurement studies and satellite observations. These are modelled estimates. |
| Published formats | CONFIRMED listing only | The current product lists Global methane emissions 2025 and Oil and gas methane emissions 2025 as CSV files in its database section. CSV contents were not inspected. Release edition and emissions year must remain distinct. |
| Access | NOT_EVALUATED download | The product displays a sign-in requirement. No account was used, so anonymous download availability and reproducible refresh are unestablished. |
| Report rights | CONFIRMED page statement | The 2025 report page identifies CC BY 4.0 for that report. This does not establish rights for database files or model code. |
| Database rights | NOT_EVALUATED file-specific terms | The combined product advertises GPL v3.0 for code and CC BY SA 4.0 for datasets, while its Licence paragraph refers to model datasets. Confirm the applicable terms and attribution on each emissions download before reuse. |
| Schema and units | NOT_EVALUATED | No file was inspected. Column names, country identifiers, missing-value conventions, methane mass units and conversion factors are not inferred. |
| Abatement model | Deferred | The product describes a separate model with code and datasets. Its rights, inputs, reproducibility and validation require separate review; no model was imported or run. |

This supports conditional adoption for country reference use, an unsuitable
recommendation for facility emissions, and a deferred recommendation for
abatement modelling. These are integration-scope judgments from the publications,
not legal clearance or validation of any emissions values.

## Implemented slices

Slice 1 records dated source evidence and the integration recommendation in
`worldenergydata.esg_carbon`. Every finding links to an opened publication and
explicitly separates publication statements from unresolved data properties.

Slice 2 exposes intended-use decisions through
`evaluate_iea_methane_tracker`. Its immutable result includes all unresolved
checks even when facility use is rejected or abatement use is deferred. Unknown
intended-use values raise `ValueError`. A maintainer can serialize the result
with standard-library dataclass and JSON functions:

```python
import json
from dataclasses import asdict

from worldenergydata.esg_carbon import evaluate_iea_methane_tracker

assessment = evaluate_iea_methane_tracker("country_reference")
print(json.dumps(asdict(assessment), indent=2))
```

The snapshot does not update itself when source pages change. Re-evaluation
requires opening the source material again and updating the dated evidence and
tests. Callers cannot pass unchecked assertions to clear the unresolved findings.

## Verification

The focused suite has 24 offline tests. Expected statuses come from the sources
and the independent decision table above, as recorded in test docstrings. Tests
cover country, facility and abatement decisions, invalid uses, citation links,
retention of all unresolved checks, separation of report and database rights,
immutability and exportable structure. No expected emissions values are derived
from the implementation because this slice performs no emissions calculations.

## Later slices

Slice 3, ingestion, is deferred. First obtain the official published files through
permitted access and retain their edition, attribution, rights evidence and
content digests. Inspect schema, units, country identifiers, aggregates, segment
labels, missing values, historical coverage and revisions. Design fixtures and
an adapter only after those properties are established; avoid silently summing
regional totals with their constituent countries.

For comparisons with other inventories, verify the other source's own terms,
years, units, sector boundaries and identifiers before joining. This evaluation
does not establish compatibility with any other inventory. A separate review
must address the abatement model; no model code or datasets are redistributed.
