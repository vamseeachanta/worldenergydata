"""Remaining-byte regressions for issue 1164; synthetic payloads only.

Independent arithmetic: if a first page uses L bytes and the aggregate budget
is L + R, the next transport cap is R. For R = 0 no request is permitted.
No engineering constant or source access permission is inferred by these tests.
"""

import json

import pytest
import requests

from worldenergydata.sodir import feature_service as fs
from worldenergydata.sodir.api_client import SodirAPIClient


@pytest.fixture
def client(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("network forbidden in offline tests")

    monkeypatch.setattr(requests.sessions.Session, "request", deny)
    monkeypatch.setattr(fs.time, "sleep", lambda _: None)
    return SodirAPIClient("https://factmaps.sodir.no/api/rest", max_retries=0)


@pytest.mark.parametrize("remaining", [0, 1])
def test_continuation_cap_and_exhaustion(client, monkeypatch, remaining):
    """The first payload is L bytes; second budget is exactly R, when positive."""
    page = {
        "features": [{"attributes": {"OBJECTID": 1}}],
        "exceededTransferLimit": True,
    }
    raw = json.dumps(page).encode()
    budgets = []
    original = fs._read_response

    def read(client, url, params, budget):
        budgets.append(budget)
        if len(budgets) == 1:
            return page, raw, url
        # Real transport must refuse a zero budget before session.get starts.
        return original(client, url, params, budget)

    calls = []

    def get(*args, **kwargs):
        calls.append(kwargs)
        raise ValueError("response byte cap exceeded")

    monkeypatch.setattr(fs, "_read_response", read)
    monkeypatch.setattr(client.session, "get", get)
    with pytest.raises(ValueError, match="byte cap"):
        client.query_entity("fields", max_pages=2, max_bytes=len(raw) + remaining)
    assert len(calls) == remaining
    assert budgets == [len(raw) + remaining, remaining]


def test_exact_budget_completes_without_continuation(client, monkeypatch):
    """Exactly L bytes is sufficient when the terminal page is L bytes long."""
    raw = b'{"features": []}'

    class Response:
        status_code = requests.codes.ok
        url = "https://factmaps.sodir.no/api/rest"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def iter_content(self, chunk_size):
            yield raw

    monkeypatch.setattr(client.session, "get", lambda *a, **k: Response())
    assert client.query_entity("fields", max_bytes=len(raw)) == []
    assert client.feature_observations[0]["size_bytes"] == len(raw)
