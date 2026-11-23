"""Locations anchored to the test file rather than the process directory."""

from pathlib import Path

EXAMPLE_DIR = (
    Path(__file__).resolve().parents[3] / "examples/workflows/federal-acreage-evidence"
)
FIXTURE = EXAMPLE_DIR / "fixture_records.json"
