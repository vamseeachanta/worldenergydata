"""Offline inventory checks using independently specified synthetic metadata.

The example has four records: sizes five, seven, zero and unknown bytes.
Hand calculation: known bytes = 5 + 7 + 0 = 12; unknown count = 1.
The literal lexical order is alpha, beta, gamma, zero. No live data is used.
"""

from copy import deepcopy
from itertools import permutations

import pytest

from worldenergydata.ukcs.ndr_catalog import build_inventory


@pytest.fixture
def records():
    """The same synthetic input as the documented offline example."""
    return [
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


def test_inventory_order_is_deterministic(records):
    for ordering in permutations(records):
        inventory = build_inventory(iter(ordering))
        assert [row["source_id"] for row in inventory["records"]] == [
            "alpha",
            "beta",
            "gamma",
            "zero",
        ]
        assert inventory["summary"] == {
            "dataset_count": 4,
            "known_size_bytes": 12,
            "unknown_size_count": 1,
        }


def test_metadata_and_unknown_size_preserved(records):
    original = deepcopy(records)
    inventory = build_inventory(records)
    assert inventory == {
        "records": [
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
                "source_id": "gamma",
                "name": "Gamma sample",
                "data_type": "seismic metadata",
                "size_bytes": None,
                "format": "JSON",
                "relevance": "Synthetic interpretation example",
                "source_url": "https://example.invalid/gamma",
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
        ],
        "summary": {
            "dataset_count": 4,
            "known_size_bytes": 12,
            "unknown_size_count": 1,
        },
    }
    assert records == original
    for row in inventory["records"]:
        row["name"] = "Changed output"
    assert records == original


def test_duplicate_source_id_rejected(records):
    # Matching ids must fail even when every other piece of metadata differs.
    duplicate = dict(records[-1], source_id="gamma")
    original = deepcopy(records)
    with pytest.raises(ValueError, match="duplicate source_id"):
        build_inventory([*records, duplicate])
    assert records == original


@pytest.mark.parametrize(
    "size",
    # Deliberate invalid inputs, including integral floats and non-finite values.
    [-1, True, False, 1.0, 1.5, float("nan"), float("inf"), float("-inf"), "5", [], {}],
)
def test_invalid_size_rejected(records, size):
    invalid = dict(records[-1], size_bytes=size)
    with pytest.raises(ValueError, match="size_bytes"):
        build_inventory([invalid])


def test_explicit_unknown_size_and_rights(records):
    row = dict(records[-1], size_bytes=None, rights=None)
    inventory = build_inventory([row])
    assert inventory["records"] == [row]
    # One unknown record contributes no known bytes, not a known zero-byte size.
    assert inventory["summary"] == {
        "dataset_count": 1,
        "known_size_bytes": 0,
        "unknown_size_count": 1,
    }


def test_empty_inventory():
    # With no records, both counts and the sum of known sizes are zero.
    assert build_inventory([]) == {
        "records": [],
        "summary": {
            "dataset_count": 0,
            "known_size_bytes": 0,
            "unknown_size_count": 0,
        },
    }


@pytest.mark.parametrize(
    "field", ["source_id", "name", "data_type", "format", "relevance", "source_url"]
)
def test_required_metadata_rejected_when_missing(records, field):
    row = dict(records[-1])
    del row[field]
    with pytest.raises(ValueError, match=field):
        build_inventory([row])


@pytest.mark.parametrize("source_id", [None, "", "  ", True])
def test_invalid_source_id_rejected(records, source_id):
    with pytest.raises(ValueError, match="source_id"):
        build_inventory([dict(records[-1], source_id=source_id)])


@pytest.mark.parametrize("rights", [True, "", "  ", []])
def test_invalid_rights_rejected(records, rights):
    with pytest.raises(ValueError, match="rights"):
        build_inventory([dict(records[-1], rights=rights)])


def test_non_mapping_record_rejected():
    with pytest.raises(ValueError, match="mapping"):
        build_inventory([None])
