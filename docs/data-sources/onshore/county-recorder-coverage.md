# County recorder access and title-chain feasibility

The offline catalog identifies recorder access constraints for a bounded set of
candidate counties. It provides source feasibility, not a title opinion or a
complete chain of ownership. All title-chain checks remain `NOT_EVALUATED`.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-20 | Added sourced county access metadata and conservative classifications to prevent online availability being mistaken for automation permission. |

## Scope and priority selection

Refs #914; parent #909; readiness dependency #911. The existing county reference
provider contains contact details and historical guidance. This catalog adds
dated access evidence without changing that provider or enabling acquisition.

The initial selection pairs existing county references in Texas, Oklahoma and
Colorado with their implemented state sources. Stevens is an explicit discovery
candidate alongside the implemented Kansas source. This is a bounded editorial
selection, not a claim that these are the highest-producing counties or a
national completeness claim. The basis is recorded on every row:

- Texas: [RRC source catalog](texas-rrc/source-catalog.md), Midland reference.
- Oklahoma: [state source catalog](state-well-databases/source-catalog.md),
  implemented OCC completion-pressure source, Canadian reference.
- Colorado: the same state catalog, implemented ECMC bulk spine, Weld reference.
- Kansas: [KGS pressure observations](kansas-kgs/pressure-observations.md),
  Stevens recorder discovery candidate; no county-volume assumption.

`regulator_readiness` describes state evidence reported by #911 and the linked
repository documents. It does not assert that files were inspected locally, that
county records were downloaded, or that regulator evidence establishes title.
Selection sorts `downloaded`, `partial`, `configured-only`, then `missing`, with
alphabetical state/county ties. This categorical priority policy follows #911;
there are no scoring equations, numerical thresholds, assumed fees or weights.
Callers can filter states; an uncovered county raises `KeyError` rather than
falling back to a nearby name. No alternate materialization registry is created.

## Slices delivered

- Slice 1: typed county/source metadata and all requested access categories.
- Slice 2: dated official-source catalog, explicit priority basis, exact lookup
  and deterministic readiness selection.
- Slice 3: JSON export, reload validation, offline worked example and tests.

Every row records recorder/search locators, search capabilities, document types,
cost constraints, historical limits, bulk availability, legal caveats, evidence
and the next human action. Null means a factual question was not established;
`NOT_EVALUATED` explains an unresolved assessment. No fee amount is inferred from
a filing schedule. There is no numerical title feasibility score.

## Classification method

Apply the following rules in order (issue #914 access categories):

| Evidence | Access classification |
| --- | --- |
| Explicit automation prohibition, or no opened evidence | `do-not-automate` |
| Attendance explicitly required | `in-person-only` |
| Online search not established | `do-not-automate` |
| Online search with payment or account required | `paid-gated` |
| Account/payment conditions unknown | `do-not-automate` |
| Online search, no account/payment, free images established | `public-online` |
| Online index established without established free images | `manual-download` |

`paid-gated` includes account gates; it does not assert a registration fee.
`manual-download` identifies manual follow-up and does not authorize downloading.
`do-not-automate` can reflect unknown evidence as well as an explicit prohibition;
consult the row's sources and caveats. Missing online evidence does not establish
that attendance is required. All categories have synthetic truth-table tests;
the initial counties need not populate every category.

Automation is a separate assessment: excluded, attendance-only and gated sources
are `blocked`. Other sources remain `NOT_EVALUATED` unless terms explicitly
permit automation and bulk availability is established, in which case the result
is only `candidate-for-review`. This is not approval or a downloader. Public/free
search never establishes title completeness, mineral ownership or reusable rights.

## Official source observations

All pages below were opened read-only on 2026-10-20. These pages have no stated
edition; observations can become stale. Access and terms require rechecking before
use. Only metadata summaries are shipped; no document images or personal records
were acquired. Search controls were not used, disclaimers were not accepted and
no account was requested. Bulk availability remains unknown for all entries.

| County | Official source and observed finding | Answer and action |
| --- | --- | --- |
| Midland, TX | [Official Public Records](https://www.co.midland.tx.us/184/Official-Public-Records), recorded instruments and requirements sections: deeds, leases, mineral deeds and releases are listed; online search conditions are not established by this page. | `do-not-automate`; confirm search URL, image access, history and terms. |
| Canadian, OK | [Land Record Searches](https://www.canadiancounty.org/885/Land-Record-Searches): office-issued login required for images. The page specifies name indexing from 1987, name/legal indexing from 1989, and most images from 1890; earlier book/page coverage ends in 1986. | `paid-gated`; login cost remains unknown. Obtain approval before requesting access. |
| Weld, CO | [Recording Department](https://www.weld.gov/Government/Departments/Clerk-and-Recorder/Recording-Department) describes search and copy purchases, with records from 1865. Its search link redirects to the [portal disclaimer](https://recording.weld.gov/web/user/disclaimer), which prohibits automated searches and copying and warns against relying on the index to decide the underlying document. | `do-not-automate`; explicit prohibition takes precedence over online or paid access. |
| Stevens, KS | [Register of Deeds](https://stevenscoks.org/departments/register_of_deeds.php), department function: deeds, mortgages, oil/gas leases, plats and liens are recorded. Online search and bulk rights were not established. | `do-not-automate`; request access guidance through an approved follow-up. Do not infer in-person-only access. |

The source-stated year ranges above describe index/image availability, not an
acceptance criterion or title root date. Each range is also attributed in its
catalog row. Initial discovery addresses that redirected to an unrelated page or
returned unavailable responses were not used as evidence of access.

## Worked example: inputs, method and answer

Input: bundled `recorder_coverage.json`, filtered to TX, OK, CO and KS. Method:
apply the categorical rules above, assess automation separately, then order by
reported readiness and identity. No physical equations apply to this catalog.

With the landman package installed:

```bash
python examples/landman/recorder_coverage.py
python -m worldenergydata.landman.recorder_coverage --state OK
```

The example's hand-evaluated expected answer is:

```text
CO/WELD: do-not-automate; automation=blocked; title=NOT_EVALUATED
KS/STEVENS: do-not-automate; automation=blocked; title=NOT_EVALUATED
OK/CANADIAN: paid-gated; automation=blocked; title=NOT_EVALUATED
TX/MIDLAND: do-not-automate; automation=blocked; title=NOT_EVALUATED
```

Weld's ban wins; Canadian needs a login; the other pages do not establish the
necessary online conditions. `--catalog` accepts an explicit local JSON file;
`--state` is repeatable. Exported computed answers are recalculated when loaded.
No network fallback occurs if a local file is missing.

## Separation and later slices

State regulator wells/production and BLM federal lease evidence remain separate
source families. They may identify candidate counties but cannot establish
recorded mineral ownership, reservations, assignments or title-chain completeness.
The federal acreage workflow's existing title-chain gap remains unevaluated.

Follow-up requires human selection and reviewed county-specific access evidence:
expand county coverage and the #911 readiness matrix, establish historical
completeness, review terms and sanctioned bulk paths, and define a qualified
title-review workflow. No paid access, registration, scraping beyond terms or
private data ingestion is authorized by a catalog entry or this example.
