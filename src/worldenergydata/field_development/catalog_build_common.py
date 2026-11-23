"""Shared stdlib primitives and sibling loading for the catalog CLI."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path


def load_peer(name):
    if __package__:
        return importlib.import_module("." + name, __package__)
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TABLES = (
    "sources",
    "field_observations",
    "cost_observations",
    "milestone_observations",
    "inherited_cost_records",
)

PRECISIONS = {
    "day",
    "month",
    "year",
    "range",
    "unknown",
    "upper_bound_day",
    "half_year",
}

TYPES = {
    "field",
    "development",
    "phase",
    "block",
    "area",
    "host",
    "well",
    "contract_bundle",
}

TYPE_MAP = {
    "development_system": "development",
    "development_phase": "phase",
    "development_area": "area",
}


input_contract = load_peer("catalog_inputs")
validation = load_peer("catalog_validation")


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def row_fingerprint(values):
    return digest_bytes(canonical(values).encode("utf-8"))


def record_id(dataset, table, record):
    explicit = next(
        (
            record[k]
            for k in ("entity_id", "cost_id", "source_ref")
            if k in record and (k != "source_ref" or table == "sources")
        ),
        None,
    )
    return f"{dataset}:{table}:{explicit or row_fingerprint(record)}"


def read_csv(path):
    return input_contract.csv_input(Path(path).read_bytes())


def load_inputs(snapshot, legacy_csv, parent_csv):
    return input_contract.pinned_inputs(
        snapshot, legacy_csv, parent_csv, validate_evidence
    )


def validate_evidence(tables):
    validation.validate_evidence(tables)
