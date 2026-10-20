"""Credential-free catalogue checks; opt in explicitly for network access."""

import os

import pytest

from worldenergydata.metocean.clients.copernicus_clients import check_endpoint

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(
        os.environ.get("METOCEAN_LIVE_TESTS") != "1",
        reason="Offline by default; set METOCEAN_LIVE_TESTS=1 to opt in",
    ),
]


@pytest.mark.parametrize("source", ["era5", "cmems"])
def test_current_copernicus_catalogue(source):
    """Catalogue identity must match the publisher, independent of download access."""
    timeout = os.environ.get("METOCEAN_LIVE_TIMEOUT_SECONDS")
    assert timeout, "Set METOCEAN_LIVE_TIMEOUT_SECONDS to a positive finite timeout"
    assert check_endpoint(source, timeout=float(timeout))
