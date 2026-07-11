# ABOUTME: Unit test for the HF Explorer results-bundle exporter (#965) — asserts the
# ABOUTME: bundle parses, counts match the source JSON, no NaN leaks, schema_version set.

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "hf_export" / "build_explorer_results_bundle.py"

spec = importlib.util.spec_from_file_location("build_explorer_results_bundle", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_bundle_matches_sources_and_is_hf_safe():
    explorer = json.loads(mod.EXPLORER_JSON.read_text(encoding="utf-8"))
    expected_fields = len(explorer["fields"])
    expected_wells = len(explorer["wells"]["wells"])

    bundle = mod.build_bundle()

    # Serializes as strict JSON with no non-finite tokens.
    serialized = json.dumps(bundle, allow_nan=False)
    assert "NaN" not in serialized
    assert "Infinity" not in serialized

    # Round-trips back to a dict.
    assert isinstance(json.loads(serialized), dict)

    # schema_version present.
    assert bundle.get("schema_version") == mod.SCHEMA_VERSION

    # Counts match the source of truth.
    assert bundle["record_counts"]["fields"] == expected_fields
    assert bundle["record_counts"]["wells"] == expected_wells
    assert len(bundle["fields"]) == expected_fields
    assert len(bundle["wells"]["wells"]) == expected_wells

    # Dedicated (not combined) HF dataset per #927/#3427.
    assert bundle["hf_dataset"] == "worldenergydata"


def test_sanitize_nulls_non_finite_floats():
    dirty = {"a": float("nan"), "b": [float("inf"), 1.0], "c": {"d": float("-inf")}}
    clean = mod.sanitize(dirty)
    assert clean["a"] is None
    assert clean["b"] == [None, 1.0]
    assert clean["c"]["d"] is None
    assert "NaN" not in json.dumps(clean, allow_nan=False)
