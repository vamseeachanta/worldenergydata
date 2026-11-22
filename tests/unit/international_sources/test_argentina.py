"""CKAN discovery tests using synthetic catalogue metadata, never production.

Wire fields follow the CKAN package_show response cited in issue 722's research
note: the country-source readiness note in docs/data-sources/.
"""

import pytest

from worldenergydata.international_sources.argentina import discover_resources


def test_catalogue_preserves_rights_frequency_and_smallest_resource():
    """Hand calculation: CSV sizes 30 and 10 bytes; ascending order is 10, 30.

    These are synthetic byte counts, not measured dataset sizes. Missing size
    cannot win the size comparison. No production values or units are inferred.
    """
    package = {
        "success": True,
        "result": {
            "id": "production-fixture",
            "license_id": "cc-by-4.0",
            "metadata_modified": "2026-01-02T00:00:00",
            "extras": [{"key": "accrualPeriodicity", "value": "R/P1M"}],
            "resources": [
                {
                    "id": "large",
                    "format": "CSV",
                    "size": 30,
                    "url": "https://datos.energia.gob.ar/large.csv",
                },
                {
                    "id": "unknown",
                    "format": "CSV",
                    "size": None,
                    "url": "https://datos.energia.gob.ar/unknown.csv",
                },
                {
                    "id": "small",
                    "format": "csv",
                    "size": 10,
                    "url": "https://datos.energia.gob.ar/small.csv",
                },
            ],
        },
    }
    discovery = discover_resources(package)
    assert discovery.dataset_id == "production-fixture"
    assert discovery.license == "cc-by-4.0"
    assert discovery.update_frequency == "R/P1M"
    assert discovery.source_modified == "2026-01-02T00:00:00"
    assert [resource.resource_id for resource in discovery.resources] == [
        "small",
        "large",
        "unknown",
    ]
    assert discovery.production_status == "NOT_EVALUATED"


# Local catalogue validation policy: discovery rejects failed responses and
# unsafe locators without treating malformed metadata as production evidence.


@pytest.mark.parametrize(
    "payload",
    [
        {"success": False, "result": {}},
        {"success": True, "result": {}},
        {"success": True, "result": []},
    ],
)
def test_missing_or_failed_package_is_rejected(payload):
    with pytest.raises(ValueError):
        discover_resources(payload)


def test_non_csv_and_unmeasured_sizes_do_not_become_download_candidates():
    discovery = discover_resources(
        {
            "success": True,
            "result": {
                "id": "example",
                "resources": [
                    {
                        "id": "not-csv",
                        "format": "XLSX",
                        "url": "https://example.org/file",
                    },
                    {
                        "id": "invalid-size",
                        "format": "CSV",
                        "size": True,
                        "url": "https://example.org/file.csv",
                    },
                ],
            },
        }
    )
    assert len(discovery.resources) == 1
    assert discovery.resources[0].size_bytes is None
    assert discovery.license is None
    assert discovery.update_frequency is None


@pytest.mark.parametrize("url", ["file:example.csv", "https://", "javascript:invalid"])
def test_non_http_resource_locators_are_rejected(url):
    with pytest.raises(ValueError, match="URL"):
        discover_resources(
            {
                "success": True,
                "result": {
                    "id": "example",
                    "resources": [{"id": "csv", "format": "CSV", "url": url}],
                },
            }
        )
