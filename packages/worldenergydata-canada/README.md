# worldenergydata-canada

`canada` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.canada` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Collection and well-search results

Canada collection summaries distinguish failed collection from collected records.
AER well searches apply every supplied predicate or raise a validation error.
The behavioural source is issue #1270 and the collection/search implementation
in `canada.py` and `aer/api_client.py`; these are software contracts, with no
engineering coefficients or numerical acceptance limits.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-21 | Document collection error accounting and explicit search predicates to distinguish failures from empty results. |

## Search contract

- `field_name` and `operator` are case-insensitive **literal substrings**;
  punctuation has no regular-expression meaning.
- `well_status` is a case-insensitive exact text match. Missing cells never
  match, including searches for the literal text `none`, `nan` or `<NA>`.
- Only `None` omits a filter. A supplied blank or non-string filter raises
  `CanadaValidationError` with code `AER_INVALID_FILTER` before retrieval.
- Each supplied filter must identify exactly one source column: a name
  containing `field`, `operator`/`licensee`, or `status`, respectively.
  Missing or multiple candidate columns raise `CanadaValidationError` with
  code `AER_UNSUPPORTED_FILTER`. Ambiguity includes duplicate column names;
  it is checked even when the table is empty or another predicate has no match.
  The exception context identifies the filter and, for ambiguity, its columns.
- Predicates combine with AND and preserve the source index and row order.
  A successful search with no matching rows returns `[]`.
- Download, parsing and filtering exceptions propagate to the caller.

Previously, punctuation could change the requested match through regex
interpretation, and multiple candidate columns silently selected the first.
Callers using regex patterns must supply literal text instead. Callers with
ambiguous source schemas must select and rename the intended source columns
before searching; the client does not infer their meaning from row contents.

## Worked example

Inputs below are synthetic, not regulator data. The first table has rows a,
b and c. By independent hand enumeration, only row a contains the literal
`[` in its field name, has operator `Example`, and status `ACTIVE`.
Thus the answer is `['a']`, independent of the nonsequential source index.
The fixture is injected at the download boundary; no network request occurs.

```pycon
>>> from pathlib import Path
>>> from tempfile import TemporaryDirectory
>>> from unittest.mock import patch
>>> import pandas as pd
>>> from worldenergydata.canada.aer.api_client import AERClient
>>> table = pd.DataFrame({
...     "id": ["a", "b", "c"],
...     "Field": ["North[Upper]", "NorthUpper", "South"],
...     "Operator": ["Example", "Example", "Other"],
...     "Status": ["ACTIVE", "ACTIVE", "CLOSED"],
... }, index=["third", "first", "second"])
>>> with TemporaryDirectory() as scratch, AERClient(cache_dir=Path(scratch)) as client:
...     with patch.object(client, "download_well_infrastructure", return_value=table):
...         rows = client.search_wells(field_name="[", operator="example", well_status="active")
>>> [row["id"] for row in rows]
['a']

```

The second example injects an AER collection failure while BCER returns one
synthetic well. The method is to route both provincial collectors through the
Canada summary. Hand count: the error envelope contains zero acquired wells;
the BCER list contains one well. The answer is an error status with counts
`aer_wells=0` and `bcer_wells=1`, plus a diagnostic for `aer_wells`.

```pycon
>>> from worldenergydata.canada.aer.aer import AER
>>> from worldenergydata.canada.bcer.bcer import BCER
>>> from worldenergydata.canada.canada import Canada
>>> with patch.object(AER, "_collect_wells", side_effect=RuntimeError("synthetic failure")), patch.object(BCER, "_collect_wells", return_value=[{"id": "synthetic"}]):
...     summary = Canada().router({"provinces": ["ab", "bc"], "data_types": ["wells"]})["canada"]
>>> summary["status"]
'error'
>>> summary["data_collected"]
{'aer_wells': 0, 'bcer_wells': 1}
>>> summary["errors"]
{'aer_wells': 'synthetic failure'}

```

`tests/unit/canada/test_canada.py` also connects the real client search to the
provincial and Canada routers for missing/ambiguous columns and download/parse
failures. Those tests demonstrate that search errors reach collection status
without becoming collected records.

## Known limits

These examples and tests establish synthetic control-flow behaviour only;
they do not establish live endpoint availability or regulator schema support.
Provincial collector implementations still contain placeholders. The basic
zero-count/error-status and missing-column/exception propagation fixes predate
this revision. Licence lookup failure classification, result-limit validation
and query/cache semantics remain separate follow-up work.
