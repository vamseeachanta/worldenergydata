"""Explicit opt-in requests; offline CI makes no connections.

Sample requests and schema evidence are in source_register.json. Timeouts and
identifying User-Agent are operator inputs, not availability acceptance limits.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from worldenergydata.metocean.clients.endpoint_checks import probe_sample

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(
        os.environ.get("METOCEAN_LIVE_TESTS") != "1",
        reason="Offline by default; opt in with METOCEAN_LIVE_TESTS=1",
    ),
]


@pytest.mark.parametrize(
    "source", ["ndbc_realtime", "coops", "irish_weather_buoys", "met_norway"]
)
def test_publisher_data_schema(source):
    timeout = float(os.environ["METOCEAN_ENDPOINT_TIMEOUT"])
    user_agent = os.environ["METOCEAN_USER_AGENT"]

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
        samples = probe_sample(source, http=http, user_agent=user_agent)
    assert samples
    assert samples[0].unit == "m"
    assert samples[0].timestamp.tzinfo is not None
