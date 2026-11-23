"""Explicit opt-in publisher probes; default test runs never use the network."""

import os

import pytest

from worldenergydata.metocean.clients.archive_transport import ArchiveTransport
from worldenergydata.metocean.source_register import get_source


@pytest.mark.skipif(
    os.environ.get("METOCEAN_LIVE_TESTS") != "1",
    reason="Publisher requests require explicit METOCEAN_LIVE_TESTS=1; offline by default",
)
@pytest.mark.parametrize(
    "source_id", ["ndbc_archive", "coops", "met_norway", "irish_weather_buoys"]
)
def test_publisher_small_response(source_id):
    source = get_source(source_id)
    assert source["terms_rechecked"] and source["account_required"] is False
    with ArchiveTransport(
        max_file_bytes=1_000_000, max_total_bytes=1_000_000
    ) as transport:
        response = transport.download(source["example_url"])
    assert response.status_code == 200
    assert response.content
