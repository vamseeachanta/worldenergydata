# Canonical marine safety issue drafts

These texts are unfiled. Numbering preserves the canonical pack's open-item
register (revision 1, 2026-10-15, section 10) and compatibility references.
Counts and node causes are evidence in [BASELINE_RESULTS.md](BASELINE_RESULTS.md),
not acceptance limits or verified acquisition results. Refs #1351 and #1239.

## Draft 1: Qualify canonical contracts, database fixtures and method inventory

Responsible role: module maintainer.

The canonical pack sections 6 and 10 C1/U1–U5 identify reversed year ranges,
negative casualties, duplicate detection always returning false, failed batch
accounting, invalid dates, database schemas/fixtures, calibration and unresolved
source clauses. Skipped model tests do not measure persistence. The external
implementation map has no counted canonical families at its pinned revision.

Required resolution: inventory each public method and source unit contract;
reject or explicitly document invalid inputs; distinguish failed writes from
success; provide working database fixtures and independently sourced examples;
register implementation families and reconcile maturity/reference claims.
No numerical calibration value is proposed without a source.

## Draft 2: Check knowledge-pack inclusion in built distributions

Responsible role: package maintainer.

The package metadata recursively includes Markdown. The pack's C3/U4 does not
establish that assessment documents are excluded from wheels. Build an isolated
wheel, inspect its manifest and decide the intended documentation payload; add
a regression against that policy. No wheel was built for this audit.

## Draft 3: Reconcile scraper tests with the implemented API

Responsible role: scraper maintainer.

Fifteen tests call public names absent from `USCGMarineCasualtyScraper`, including
`fetch_page`, `parse_incident_html`, `scrape_incidents`, `download_pdf`,
`extract_pdf_text` and `parse_pdf_metadata`. The implementation exposes `scrape`
and private helpers instead. These are API-contract failures before acquisition,
not evidence of failed live downloads. See every node in BASELINE_RESULTS.md.

Required resolution: determine the supported API, correct contracts and tests,
retain mocked I/O and independent expected outcomes, then remove each strict
xfail as its test is corrected. Optional PDF test dependencies must skip with
a reason when absent. No live network test is requested here.

## Draft 4: Reconcile validator model construction and validation assertions

Responsible role: validation maintainer.

Thirteen tests construct `IncidentValidator()` or `VesselValidator()` without
required Pydantic fields, failing before the intended assertions. The class
schema in `utils/validators.py` declares required fields, while the tests expect
a separate service-style API. See BASELINE_RESULTS.md for the exact nodes.

Required resolution: establish the public model/service contract, supply valid
fixtures for that contract, exercise each invalid case independently and remove
the corresponding strict xfails. Do not replace validation with empty defaults.

## Draft 5: Replace the correlation test-local matching oracle

Responsible role: analysis maintainer.

`TestIncidentMatcherConfidence::test_find_matches_returns_above_threshold`
implements a test-local weighted formula rather than calling `IncidentMatcher`;
its fixture produces no qualifying pair. Canonical pack section 6 and the test
body establish this cause; the assertion is retained as a strict xfail.

Required resolution: specify independently justified matching inputs and expected
outcomes, exercise the actual implementation and retain a negative case. This
draft proposes no guessed confidence threshold or weight.

## Draft 6: Preserve per-source provenance and unknown-casualty semantics

Responsible role: data-pipeline maintainer.

Canonical pack C7 records that one successful importer labels mixed data `live`,
query output drops freshness, importer exceptions disappear and absent casualty
rows become zero. Required resolution: expose per-source provenance and rejected
record counts, distinguish unknown from zero and test each fallback independently.
No observed-source completeness is established by synthetic examples.

## Draft 7: Make classifier and integration tests reproducible offline

Responsible role: test maintainer.

The canonical pack records unavailable local model inputs and unconditional
integration skips. The first exposed run here shows setup failures when optional
`transformers` is absent; those now skip explicitly without excluding their file.
Installing the extra alone still does not provide a reviewed model fixture.

Required resolution: separate dependency-presence tests, mocked classifier tests
and opt-in tests requiring explicitly supplied model data; ensure the documented
flag enables the intended tests. No model download or classification-quality
claim is made. Historical 35 FAIL / 28 ERROR counts are not a portable oracle.

## Draft 8: Align statistical-report logging and output assertions

Responsible role: report maintainer.

`TestStatisticalSummary::test_print_report` checks `capsys` stdout, while
`StatisticalSummary.print_report()` writes through logging. The exact assertion
and implementation establish the mismatch. Required resolution: decide the
output contract, test that destination and remove the strict xfail. Retain the
report content assertions rather than silencing the test.

## Draft 9: Restore fixture imports and directory collection

Responsible role: test maintainer.

The historical hatch test and two lazy fixtures imported the removed fixture
namespace. The root hook also excluded all unit descendants (#1239; closed #327
is history). This change corrects those imports and removes the exclusion; the
committed collection test compares disk paths with file-level pytest reports,
including skipped modules. After restoration: 52/52 unit files, no collection
errors. Remaining baseline failures belong to drafts 3, 4, 5, 7 and 8 rather than
a renewed directory exclusion.
