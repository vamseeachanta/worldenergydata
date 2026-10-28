# Offline UKCS metadata inventory example

`build_inventory(records)` inventories caller-supplied metadata without querying
or downloading datasets. This example uses synthetic metadata only. No live NDR
holdings or rights have been verified. The placeholder URLs are not NDR resources
and are never requested. Metadata availability does not grant redistribution
rights; any later use requires independent checks of the source and its terms.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-26 | Add a synthetic offline example to document the inventory contract. |

## Input and output contract

Import the function from `worldenergydata.ukcs.ndr_catalog`. It accepts an iterable
of metadata dictionaries with these fields:

| Field | Contract |
| --- | --- |
| `source_id` | Required non-empty stable identifier supplied by the caller; duplicates raise `ValueError`. |
| `name` | Required non-empty dataset name. |
| `data_type` | Required non-empty description of the data type. |
| `size_bytes` | Non-negative integer bytes, excluding booleans; missing or `None` means unknown. Floats, including non-finite values, strings and negative sizes raise `ValueError`. |
| `format` | Required non-empty format description. |
| `relevance` | Required non-empty caller-supplied relevance description; no ranking is inferred. |
| `source_url` | Required non-empty source locator, retained without fetching or verifying it. |
| `rights` | Non-empty caller-supplied text or `None`; missing or `None` means unknown. Text is retained without interpreting or verifying permission. |

Whitespace-only text is invalid. Valid text and identifiers are preserved exactly;
identifiers are compared and sorted case-sensitively. Other keys are omitted.
Inputs are unchanged, and output rows are new dictionaries. The returned
dictionary contains `records` sorted by `source_id` and a `summary` with
`dataset_count`, `known_size_bytes` and `unknown_size_count`. An empty input
returns empty rows and zero counts.

`known_size_bytes` is a subtotal, not the total size when unknown sizes remain.
A known zero-byte dataset retains its numeric size; an unknown size stays `None`.
Unknown rights stay unknown, without creating a redistribution permission flag.

## Runnable example

From the repository root, set
`PYTHONPATH=src:packages/worldenergydata-ukcs/src` and run the following Python
code using `uv run --no-project python`. Only the standard library and the local
module are needed. The same input appears in
`tests/unit/ukcs/test_ndr_catalog.py`.

```python
from worldenergydata.ukcs.ndr_catalog import build_inventory

records = [
    {
        "source_id": "gamma",
        "name": "Gamma sample",
        "data_type": "seismic metadata",
        "format": "JSON",
        "relevance": "Synthetic interpretation example",
        "source_url": "https://example.invalid/gamma",
    },
    {
        "source_id": "beta",
        "name": "Beta sample",
        "data_type": "well metadata",
        "size_bytes": 7,
        "format": "CSV",
        "relevance": "Synthetic well example",
        "source_url": "https://example.invalid/beta",
        "rights": None,
    },
    {
        "source_id": "zero",
        "name": "Empty sample",
        "data_type": "document metadata",
        "size_bytes": 0,
        "format": "TXT",
        "relevance": "Synthetic empty example",
        "source_url": "https://example.invalid/zero",
        "rights": "unknown",
    },
    {
        "source_id": "alpha",
        "name": "Alpha sample",
        "data_type": "production metadata",
        "size_bytes": 5,
        "format": "CSV",
        "relevance": "Synthetic time series example",
        "source_url": "https://example.invalid/alpha",
        "rights": "Synthetic terms; review required",
    },
]

inventory = build_inventory(records)
# Independently sorted lexical order of the synthetic identifiers.
assert [row["source_id"] for row in inventory["records"]] == [
    "alpha", "beta", "gamma", "zero"
]
# Hand calculation: four rows; known bytes = 5 + 7 + 0 = 12; one unknown size.
assert inventory["summary"] == {
    "dataset_count": 4,
    "known_size_bytes": 12,
    "unknown_size_count": 1,
}
by_id = {row["source_id"]: row for row in inventory["records"]}
assert by_id["gamma"]["size_bytes"] is None
assert by_id["gamma"]["rights"] is None
assert by_id["zero"]["size_bytes"] == 0
print(inventory["summary"])
```

The synthetic sizes are chosen example inputs, not measurements of any holdings.
The expected summary follows the hand calculation in the code and is independently
specified in the tests. Expected output:

```text
{'dataset_count': 4, 'known_size_bytes': 12, 'unknown_size_count': 1}
```

## Scope and next work

This primitive does not establish NDR catalogue coverage, authenticate sources,
validate rights, retrieve payloads or modify production and well loaders. Live
catalogue discovery, ranking datasets and integration planning remain work for
the parent issue. Supplied relevance and rights text remain unverified metadata.
