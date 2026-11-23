"""Shared validation primitives and standalone sibling-module loading."""

import hashlib
import importlib.util
import json
import re
from pathlib import Path

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
HASH = re.compile(r"^[a-f0-9]{64}$")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def unique(rows, key):
    identifiers = [row[key] for row in rows]
    require(
        all(identifiers) and len(identifiers) == len(set(identifiers)),
        "blank or duplicate identity",
    )
    return set(identifiers)


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
