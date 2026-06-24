# ABOUTME: Smoke gate for the carved worldenergydata-reservoir member (#529).
# ABOUTME: Asserts the package imports and a trivial public-API call works.
"""Smoke test: worldenergydata.reservoir resolves from its workspace member."""

import worldenergydata.reservoir as reservoir
from worldenergydata.reservoir.resource_estimation import compute_eur


def test_package_imports():
    assert reservoir.__name__ == "worldenergydata.reservoir"


def test_trivial_public_api():
    # EUR = OOIP * recovery_factor.
    assert compute_eur(1000.0, 0.3) == 300.0
