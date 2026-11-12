# Drilling riser CSV validation

The component loader rejects records whose field count differs from the header,
ambiguous column labels, missing provenance, blank, padded or repeated IDs,
and IDs containing Unicode control or format characters. Canonically equivalent
IDs also count as duplicates; stored IDs and lookups remain literal.
Validation completes before a DataFrame is cached. This protects field alignment
and identity lookup; it does not establish engineering suitability of the data.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-19 | Document header and identity rejection, with a reproducible example to prevent ambiguous catalog lookups. |
| 2 | 2026-10-20 | Preserve literal ID strings, locate blank IDs by physical CSV line, and remove temporary example files automatically. |
| 3 | 2026-10-21 | Reject padded IDs and locate missing provenance by physical CSV line so ambiguous or incomplete records can be corrected. |
| 4 | 2026-10-21 | Reject Unicode format characters in IDs to prevent invisible or directional formatting from creating ambiguous lookups. |
| 5 | 2026-11-05 | Reject canonically equivalent duplicates and Unicode controls, bound physical-line diagnostics, and consolidate overlapping tests. |
| 6 | 2026-11-12 | Reject parser row-count disagreement, assign literal IDs by position, and clarify version-dependent NUL rejection. |

## Input contract and method

The packaged `drilling_riser_components.csv` is the canonical catalog.
Issue #1046 requires consistent row widths, stable unique component IDs, semantic anchors
for each component type, and populated `DATA_SOURCE` and `NOTES`.
The delimiter repair was merged in PR #1157.
This change retains that catalog byte for byte.

The [loader](../src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py)
reads a single UTF-8 snapshot (a byte-order mark is accepted), then:

1. Parses the header with the strict CSV reader and rejects duplicate or blank
   column names before pandas can rename them.
2. Counts logical CSV fields, respecting quoted commas and newlines. Each record
   must have the header's field count. Width errors give the physical start line,
   expected count and actual count. Only empty physical lines are skipped.
3. Parses the same snapshot with pandas and checks the required query columns.
   Rejects a row-count mismatch with the strict CSV reader before assigning
   literal ID strings by position, then checks populated `DATA_SOURCE` and `NOTES`.
   On Python 3.11 and later, the strict reader preserves NUL for identity rejection
   rather than truncation; Python 3.10 rejects it earlier as malformed CSV.
   Missing provenance errors give each affected record's physical start line.
4. Checks `COMPONENT_ID` strings for blank or padded values, Unicode control
   and format characters (categories `Cc` and `Cf`), and duplicates using NFC
   comparison keys. Blank, padded, control-character, format-character and
   duplicate errors identify the affected records' physical start lines,
   including after quoted newlines or empty physical lines. Diagnostics show at
   most 20 starts and include the total when truncated. IDs with leading or
   trailing whitespace are rejected rather than trimmed. Canonically equivalent
   IDs are rejected together before `get_by_id` can choose a first match.
5. Caches the frame only after all checks pass. A failed load can be retried after
   the input is corrected.

Column names and `get_by_id` lookups are compared exactly. NFC keys are used
only to detect duplicates; validation does not trim or rewrite stored IDs. A
single decomposed ID is accepted and requires the same literal lookup string.
Compatibility variants, case differences and other visual confusables are not
merged by NFC. Non-control, non-format invisible characters are not rejected
as a class. Optional engineering cells may remain empty.
IDs `1` and `01` remain distinct strings; `NA` is a populated ID. Other columns
retain pandas' default numeric and missing-value parsing.
Pandas missing-value tokens such as `NA` in `DATA_SOURCE` or `NOTES` are
therefore treated as missing provenance.
A missing file retains the existing behavior of returning an empty frame.

## Worked example: repeated identity, correction and short row

The following inputs are synthetic. No engineering constants or acceptance limits
are assigned. The field count is obtained by counting the explicitly listed
header names. Independent hand checks are:

- `[A, A]` contains two records but one distinct ID, so lookup is ambiguous.
- `[A, B]` contains two records with two distinct IDs and is accepted.
- Removing the last cell leaves eight fields under a nine-field header; the
  first data record begins on physical line two and must be rejected.

Run this example in an environment where the component package is importable.
Temporary CSV files use the configured temporary directory and are removed when
the example exits its context manager.

```python
import csv
import tempfile
from pathlib import Path

from worldenergydata.vessel_fleet.loaders.drilling_riser_loader import (
    DrillingRiserLoader,
)

header = [
    "COMPONENT_ID", "DATA_SOURCE", "NOTES", "COMPONENT_TYPE", "OD_IN",
    "PRESSURE_RATING_PSI", "BORE_SIZE_IN", "BOP_TYPE", "MANUFACTURER",
]
# Synthetic cells; empty numeric fields do not claim design properties.
row = ["A", "Synthetic CSV example", "Identity validation only", "riser_joint",
       "", "", "", "", ""]
with tempfile.TemporaryDirectory(prefix="riser-csv-example-") as temporary_dir:
    data_dir = Path(temporary_dir)
    catalog = data_dir / "drilling_riser_components.csv"

    def write_rows(records):
        with catalog.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(records)

    loader = DrillingRiserLoader(data_dir)
    write_rows([row, row])
    try:
        loader.get_by_id("A")
    except ValueError as error:
        print(error)

    write_rows([row, ["B", *row[1:]]])
    print(loader.load()["COMPONENT_ID"].tolist())

    # A new loader observes the changed file; a successful load is cached.
    write_rows([row[:-1]])
    try:
        DrillingRiserLoader(data_dir).load()
    except ValueError as error:
        print(error)
```

Expected output, derived from the hand checks above:

```text
Duplicate COMPONENT_ID values: ['A'] at CSV lines 2, 3
['A', 'B']
CSV line 2: expected 9 fields, actual 8
```

## Evidence and limits

[Identity tests](../../../tests/unit/vessel_fleet/loaders/test_drilling_riser_identity.py)
exercise ambiguous headers, blank IDs with physical line numbers, literal numeric
and missing-value-like ID strings, padding and control/format-character rejection,
canonical duplicate rejection, exact Unicode lookups, bounded line diagnostics, correction
and retry, missing provenance with physical line numbers, and quoted provenance
round trips. Existing
[alignment tests](../../../tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py)
retain the catalog's ID list, delimiter-independent text digest, width checks,
component-type anchors and provenance assertions.

These are catalog integrity checks. They do not authenticate source documents,
validate numerical engineering limits, or certify a component for analysis.
Catalog expansion and downstream fixture refresh remain separate work under
issue #698 and the linked consuming program. No downstream fixture is modified.
`DATA_SOURCE` text is retained as supplied; a citation label alone does not
establish that its source has been independently checked.
