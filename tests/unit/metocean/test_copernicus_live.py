"""Opt-in public metadata checks: no credentials and no data download."""

import os

import httpx
import pytest

from worldenergydata.metocean.clients.copernicus_clients import probe_catalogue

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(
        os.environ.get("METOCEAN_LIVE_TESTS") != "1",
        reason="Offline by default; opt in with METOCEAN_LIVE_TESTS=1",
    ),
]


@pytest.mark.parametrize("source", ["era5", "cmems"])
def test_current_copernicus_catalogue(source):
    # Timeout is an operator input, not a publisher availability criterion.
    timeout = float(os.environ["METOCEAN_ENDPOINT_TIMEOUT"])
    with httpx.Client(timeout=timeout, trust_env=False) as http:
        assert probe_catalogue(source, http=http)["id"]
