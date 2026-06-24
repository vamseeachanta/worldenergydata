# ABOUTME: Smoke gate for the carved worldenergydata-drilling member (#529).
# ABOUTME: Asserts the package imports and its public API is exposed.
"""Smoke test: worldenergydata.drilling resolves from its workspace member."""

import worldenergydata.drilling as drilling


def test_package_imports():
    assert drilling.__name__ == "worldenergydata.drilling"


def test_public_api_exported():
    for name in (
        "BatchDrillingEconomics",
        "BSEEBatchDetector",
        "DrillCampaign",
        "DrillingSite",
    ):
        assert hasattr(drilling, name), name
