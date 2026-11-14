"""HTTP retry contracts for the in-memory BSEE downloader.

Status meanings: RFC 9110 (2022), sections 15.5.5 and 15.6.3-15.6.4.
Budgets and delays are synthetic inputs, not operational recommendations.
"""

from http import HTTPStatus
from unittest.mock import Mock, call, patch

import pytest
import requests


@pytest.fixture
def scraper():
    from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper

    scraper = BSEEWebScraper()
    yield scraper
    scraper.close()


def _response(status):
    response = requests.Response()
    response.status_code = status
    response.url = "https://example.invalid/archive.zip"
    return response


def test_opted_in_not_found_raises_without_retry(scraper):
    """Hand trace: first Not Found raises; one request, zero sleeps.

    The synthetic budget allows three attempts, but no second attempt
    can repair a configured endpoint during this run (#460 policy).
    """
    response = _response(HTTPStatus.NOT_FOUND)
    with (
        patch.object(scraper.session, "get", return_value=response) as get,
        patch("worldenergydata.bsee.data.scrapers.bsee_web.time.sleep") as sleep,
        pytest.raises(requests.HTTPError) as caught,
    ):
        scraper.download_zip_to_memory(
            response.url, max_retries=3, raise_on_not_found=True
        )
    assert caught.value.response is response
    get.assert_called_once()
    sleep.assert_not_called()


def test_default_not_found_behavior_remains_compatible(scraper):
    """Hand trace: two failed requests, one intervening configured delay.

    Legacy callers still receive None after their explicit attempt budget.
    """
    response = _response(HTTPStatus.NOT_FOUND)
    with (
        patch.object(scraper.session, "get", return_value=response) as get,
        patch("worldenergydata.bsee.data.scrapers.bsee_web.time.sleep") as sleep,
    ):
        result = scraper.download_zip_to_memory(response.url, max_retries=2)
    assert result is None
    assert get.call_count == 2
    sleep.assert_called_once_with(scraper.RETRY_DELAY)


@pytest.mark.parametrize(
    "error",
    [
        requests.HTTPError(response=_response(HTTPStatus.SERVICE_UNAVAILABLE)),
        requests.HTTPError(response=_response(HTTPStatus.BAD_GATEWAY)),
        requests.HTTPError("no response"),
        requests.Timeout("temporary timeout"),
        requests.ConnectionError("temporary connection failure"),
        RuntimeError("404 in text is not an HTTP status"),
    ],
)
def test_opted_in_transient_failure_can_recover(error, scraper):
    """Hand trace: failure then success uses two requests and one delay.

    The successful synthetic body is returned unchanged. HTTP server errors
    and errors without a typed Not Found response retain the retry policy.
    """
    response = Mock(headers={"Content-Type": "application/zip"})
    response.iter_content.return_value = [b"synthetic archive bytes"]
    with (
        patch.object(scraper.session, "get", side_effect=[error, response]) as get,
        patch("worldenergydata.bsee.data.scrapers.bsee_web.time.sleep") as sleep,
    ):
        result = scraper.download_zip_to_memory(
            "https://example.invalid/archive.zip",
            max_retries=3,
            raise_on_not_found=True,
        )
    assert result == b"synthetic archive bytes"
    assert get.call_count == 2
    assert sleep.call_args_list == [call(scraper.RETRY_DELAY)]
