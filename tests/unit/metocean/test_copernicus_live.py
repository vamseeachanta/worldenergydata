"""Opt-in public metadata checks: no credentials and no data download."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

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

    def record(response):
        destination = os.environ.get("METOCEAN_EVIDENCE_DIR")
        if destination:
            folder = Path(destination)
            response.read()
            (folder / f"{source}.response").write_bytes(response.content)
            (folder / f"{source}.json").write_text(
                json.dumps(
                    {
                        "url": str(response.request.url),
                        "http_status": response.status_code,
                        "utc": datetime.now(timezone.utc).isoformat(),
                    },
                    indent=2,
                )
                + "\n"
            )

    with httpx.Client(
        timeout=timeout, trust_env=False, event_hooks={"response": [record]}
    ) as http:
        assert probe_catalogue(source, http=http)["id"]
