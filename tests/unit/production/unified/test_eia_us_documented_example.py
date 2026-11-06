"""Execute the documented synthetic query without network transport access."""

import re
from pathlib import Path

import pytest

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file()
)
DOCUMENT = (
    ROOT
    / "packages/worldenergydata-production/src/worldenergydata/production"
    / "docs/eia-us-synthetic-example.md"
)


@pytest.fixture
def documented_example(monkeypatch, capsys):
    """Run the unique named fence; even a swallowed network attempt fails."""
    document = DOCUMENT.read_text(encoding="utf-8")
    [code] = re.findall(
        r"^<!-- example: eia-us-synthetic-query -->\n\n```python\n(.*?)^```$",
        document,
        flags=re.MULTILINE | re.DOTALL,
    )
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Network transport used by the documented example")

    for transport in (
        "socket.create_connection",
        "socket.getaddrinfo",
        "socket.socket.connect",
        "socket.socket.connect_ex",
        "socket.socket.sendto",
        "http.client.HTTPConnection.connect",
        "http.client.HTTPSConnection.connect",
        "urllib.request.urlopen",
        "requests.sessions.Session.request",
    ):
        monkeypatch.setattr(transport, forbidden)

    namespace = {"__name__": "__main__"}
    exec(compile(code, str(DOCUMENT), "exec"), namespace)
    assert not attempts, "The example attempted network access"
    return namespace["rows"], capsys.readouterr(), document


def test_documented_synthetic_adapter_example_is_offline(documented_example):
    rows, output, _ = documented_example
    assert not rows.empty
    assert set(rows["region"]) == {"eia_us"}
    assert output.out.splitlines() == [
        "routing-region: eia_us",
        "source: eia_us_mock",
    ]
    assert not output.err


def test_documented_source_labels_are_explicit(documented_example):
    rows, _, document = documented_example
    assert set(rows["source"]) == {"eia_us_mock"}
    assert "`eia_us` is a routing label" in document
    assert "`eia_us_mock` is the provenance label" in document
