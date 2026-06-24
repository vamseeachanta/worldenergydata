# ABOUTME: Smoke gate for the carved worldenergydata-marine member (#529).
# ABOUTME: Asserts the package imports and a trivial public-API call works.
"""Smoke test: worldenergydata.marine resolves from its workspace member."""

import worldenergydata.marine as marine
from worldenergydata.marine import haversine_nm


def test_package_imports():
    assert marine.__name__ == "worldenergydata.marine"


def test_trivial_public_api():
    # Zero distance between identical coordinates.
    assert haversine_nm(0.0, 0.0, 0.0, 0.0) == 0.0
