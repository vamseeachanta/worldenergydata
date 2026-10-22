"""Compose the existing tied-boundary and short-page pagination regressions.

EIA APIv2 documentation (accessed 2026-10-22), Sort Results and length/offset:
https://www.eia.gov/opendata/documentation.php#SortResults
All rows, page lengths and dates are synthetic protocol fixtures.
"""

from unittest.mock import Mock

import pytest

from worldenergydata.eia.client import EIAFeedClient


@pytest.mark.parametrize(
    "method", ["fetch_petroleum_weekly", "fetch_gas_storage_weekly"]
)
def test_ties_cross_several_short_pages(monkeypatch, method):
    """Hand ordering: A/B/C/D share Jan 5; E is Jan 12.

    Server returns at most two of three requested rows: AB, CD, E.
    Offsets must be 0, 0+2=2, 2+2=4. The secondary series sort must
    preserve ABCDE exactly once, even as ties cross two page boundaries.
    """
    monkeypatch.setattr("worldenergydata.eia.client.DEFAULT_PAGE_SIZE", 3)
    rows = [{"period": "2024-01-05", "series": letter} for letter in "ABCD"] + [
        {"period": "2024-01-12", "series": "E"}
    ]
    offsets = []

    def page(url, *, params, timeout):
        assert params["sort[0][column]"] == "period"
        assert params["sort[1][column]"] == "series"
        assert params["sort[0][direction]"] == params["sort[1][direction]"] == "asc"
        offsets.append(params["offset"])
        offset = params["offset"]
        return Mock(
            status_code=200,
            json=lambda: {
                "response": {"total": "5", "data": rows[offset : offset + 2]}
            },
        )

    monkeypatch.setattr("worldenergydata.eia.client.requests.get", page)
    records = getattr(EIAFeedClient(api_key="synthetic-test-key"), method)()
    assert [record["series"] for record in records] == list("ABCDE")
    assert len({(record["period"], record["series"]) for record in records}) == len(
        rows
    )
    assert offsets == [0, 2, 4]
