"""Pagination regressions using synthetic rows and hand-calculated page slices.

Protocol source: EIA, APIv2 documentation (accessed 2026-10-19), "Sort
Results" and the following length/offset section:
https://www.eia.gov/opendata/documentation.php#SortResults
Sort precedence starts at zero; offset skips that many eligible rows.
The series column is present in both feed fixtures in test_client.py.
All dates, series letters and page lengths below are synthetic test inputs,
not measured energy data or acceptance tolerances.
"""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def client():
    from worldenergydata.eia.client import EIAFeedClient

    return EIAFeedClient(api_key="synthetic-test-key")


@pytest.mark.parametrize(
    "feed_method", ["fetch_petroleum_weekly", "fetch_gas_storage_weekly"]
)
def test_tied_periods_across_page_boundary(client, feed_method, monkeypatch):
    """Hand calculation: ordered keys are (Jan 05,A/B/C), (Jan 12,A).

    Two-row pages must be [A05,B05] then [C05,A12]; offsets are 0 and
    0 + 2 = 2. Without a secondary sort, the second request may put C05
    before A05/B05: [C05,A05,B05,A12][2:4] repeats B05 and loses C05.
    Expected output is enumerated independently of the mock's sort.
    """
    # Synthetic page length from the hand calculation above.
    monkeypatch.setattr("worldenergydata.eia.client.DEFAULT_PAGE_SIZE", 2)
    rows = [
        {"period": "2024-01-05", "series": "A"},
        {"period": "2024-01-05", "series": "B"},
        {"period": "2024-01-05", "series": "C"},
        {"period": "2024-01-12", "series": "A"},
    ]
    requests = []

    def get_page(url, *, params, timeout):
        requests.append(dict(params))
        offset = params["offset"]
        ordered = list(rows)
        # Simulate a legal reshuffling of ties if only period is requested.
        if params.get("sort[1][column]") != "series" and offset:
            ordered = [rows[2], rows[0], rows[1], rows[3]]
        response = Mock(status_code=200)
        response.json.return_value = {
            "response": {"total": len(rows), "data": ordered[offset : offset + 2]}
        }
        return response

    with patch("worldenergydata.eia.client.requests.get", side_effect=get_page):
        records = getattr(client, feed_method)(start_date="2024-01-01")

    expected = [
        ("2024-01-05", "A"),
        ("2024-01-05", "B"),
        ("2024-01-05", "C"),
        ("2024-01-12", "A"),
    ]
    keys = [(row["period"], row["series"]) for row in records]
    assert keys == expected
    assert len(set(keys)) == len(expected)
    assert [request["offset"] for request in requests] == [0, 2]
    for request in requests:
        assert request["sort[0][column]"] == "period"
        assert request["sort[0][direction]"] == "asc"
        assert request["sort[1][column]"] == "series"
        assert request["sort[1][direction]"] == "asc"
        assert request["start"] == "2024-01-01"
    expected_feed = feed_method.removeprefix("fetch_")
    assert all(row["_feed"] == expected_feed for row in records)


@pytest.mark.parametrize("total", [4, "4"])
@pytest.mark.parametrize("extra_params", [None, {"length": 2}])
def test_short_nonfinal_pages_advance_by_received_rows(client, total, extra_params):
    """Hand calculation: four rows A/B/C/D, batches [A], [B,C], [D].

    Cumulative offsets are 0, 0+1=1, 1+2=3; after D, 3+1=4 ends the
    fetch. Requested length cannot replace these actual batch lengths.
    The protocol source above shows total as a decimal string.
    """
    batches = {
        0: [{"series": "A"}],
        1: [{"series": "B"}, {"series": "C"}],
        3: [{"series": "D"}],
    }
    offsets = []

    def get_page(url, *, params, timeout):
        offsets.append(params["offset"])
        response = Mock(status_code=200)
        response.json.return_value = {
            "response": {"total": total, "data": batches.get(params["offset"], [])}
        }
        return response

    with patch("worldenergydata.eia.client.requests.get", side_effect=get_page):
        records = client._get("petroleum/sum/snd/w", extra_params=extra_params)

    assert [record["series"] for record in records] == ["A", "B", "C", "D"]
    assert offsets == [0, 1, 3]


def test_empty_page_stops_without_advancing(client):
    """Hand calculation: no rows received at offset zero means no progress.

    Even with four declared rows, a second identical request cannot add
    records. Preserve the existing empty-page stop (not completeness proof).
    """
    response = Mock(status_code=200)
    response.json.return_value = {"response": {"total": 4, "data": []}}
    with patch(
        "worldenergydata.eia.client.requests.get", return_value=response
    ) as get_page:
        assert client.fetch_petroleum_weekly() == []
    get_page.assert_called_once()
