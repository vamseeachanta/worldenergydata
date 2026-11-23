# ABOUTME: Smoke gate for the carved worldenergydata-baker_hughes member (#529).
# ABOUTME: Asserts the package imports and its public API is exposed.
"""Smoke test: worldenergydata.baker_hughes resolves from its workspace member."""

import worldenergydata.baker_hughes as baker_hughes


def test_package_imports():
    assert baker_hughes.__name__ == "worldenergydata.baker_hughes"


def test_public_api_exported():
    assert hasattr(baker_hughes, "load_pivot_table")
    assert hasattr(baker_hughes, "load_summary")
