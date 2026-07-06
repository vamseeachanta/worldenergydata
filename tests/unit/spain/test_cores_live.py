"""Spain CORES live workbook source tests (#806)."""

import hashlib
import json

import pandas as pd
import pytest

from worldenergydata.spain.production.cores_live import (
    DEFAULT_WORKBOOKS,
    STATISTICS_PAGE_URL,
    CoresHttpResponse,
    CoresSourceError,
    CoresWorkbookSource,
    refresh_ayoluengo_fixture,
)
from worldenergydata.spain.production.cores_loader import TONNES_TO_BBL


def test_discover_resolves_official_workbook_links_from_statistics_page_html(tmp_path):
    html = """
    <html>
      <body>
        <a href="/sites/default/files/archivos/estadisticas/crude-oil-production.xlsx">
          Indigenous Crude Oil Production
        </a>
        <a href="https://www.cores.es/sites/default/files/archivos/estadisticas/gas-production.xlsx">
          Indigenous Natural Gas Production
        </a>
      </body>
    </html>
    """
    source = CoresWorkbookSource(cache_root=tmp_path)

    inventory = source.discover(page_html=html)

    assert inventory["oil"].source_url == DEFAULT_WORKBOOKS["oil"].source_url
    assert inventory["gas"].source_url == DEFAULT_WORKBOOKS["gas"].source_url


def test_discover_fails_closed_when_a_workbook_link_is_missing(tmp_path):
    source = CoresWorkbookSource(cache_root=tmp_path)

    with pytest.raises(CoresSourceError, match="gas-production.xlsx"):
        source.discover(
            page_html="""
            <a href="/sites/default/files/archivos/estadisticas/crude-oil-production.xlsx">
              Indigenous Crude Oil Production
            </a>
            """
        )


def test_download_all_writes_raw_files_atomically_and_records_metadata(tmp_path):
    oil_bytes = b"oil workbook bytes"
    gas_bytes = b"gas workbook bytes"
    responses = _fake_workbook_responses(oil_bytes, gas_bytes)

    def fake_http_get(url, *, method="GET"):
        assert method == "GET"
        return responses[url]

    source = CoresWorkbookSource(
        cache_root=tmp_path,
        http_get=fake_http_get,
        clock=lambda: "2026-07-04T00:00:00Z",
    )

    paths = source.download_all(force_refresh=True)

    assert paths["oil"].read_bytes() == oil_bytes
    assert paths["gas"].read_bytes() == gas_bytes
    assert not list((tmp_path / "raw").glob("*.tmp"))

    metadata = json.loads(
        (tmp_path / "metadata" / "cores_refresh_metadata.json").read_text()
    )
    assert metadata["statistics_page"] == STATISTICS_PAGE_URL
    assert metadata["refreshed_at_utc"] == "2026-07-04T00:00:00Z"
    assert (
        metadata["workbooks"]["oil"]["sha256"] == hashlib.sha256(oil_bytes).hexdigest()
    )
    assert metadata["workbooks"]["gas"]["byte_count"] == len(gas_bytes)
    assert (
        metadata["workbooks"]["oil"]["last_modified"] == "Fri, 12 Jun 2026 07:51:41 GMT"
    )


def test_refresh_ayoluengo_fixture_writes_stable_sample_and_metadata(tmp_path):
    oil = pd.DataFrame(
        [
            {"field_name": "Other", "year": 2026, "month": 1, "oil_bbl": 1.0},
            {"field_name": "Ayoluengo", "year": 2026, "month": 2, "oil_bbl": 20.0},
            {"field_name": "Ayoluengo", "year": 2026, "month": 1, "oil_bbl": 10.0},
        ]
    )
    source_metadata = {
        "statistics_page": STATISTICS_PAGE_URL,
        "workbooks": {
            "oil": {
                "source_url": DEFAULT_WORKBOOKS["oil"].source_url,
                "last_modified": "Fri, 12 Jun 2026 07:51:41 GMT",
                "sha256": "abc123",
                "byte_count": 123,
            }
        },
    }

    result = refresh_ayoluengo_fixture(
        oil_frame=oil,
        metadata=source_metadata,
        output_dir=tmp_path,
        refreshed_at_utc="2026-07-04T00:00:00Z",
    )

    sample = pd.read_csv(result.sample_path)
    assert sample.to_dict("records") == [
        {
            "field_name": "Ayoluengo",
            "year": 2026,
            "month": 1,
            "oil_bbl": 10.0,
            "gas_mcf": 0.0,
        },
        {
            "field_name": "Ayoluengo",
            "year": 2026,
            "month": 2,
            "oil_bbl": 20.0,
            "gas_mcf": 0.0,
        },
    ]
    written_metadata = json.loads(result.metadata_path.read_text())
    assert written_metadata["source_url"] == DEFAULT_WORKBOOKS["oil"].source_url
    assert written_metadata["statistics_page"] == STATISTICS_PAGE_URL
    assert written_metadata["sample_row_count"] == 2
    assert "oil_tonnes_to_bbl" not in written_metadata["conversion_factors"]
    assert written_metadata["conversion_factors"]["oil_tonnes_to_bbl_default"] == (
        TONNES_TO_BBL
    )
    audit = written_metadata["oil_conversion_audit"]
    assert audit["coverage_status"] == "defaulted"
    assert audit["defaulted_fields"] == ["Ayoluengo"]
    assert audit["default_bbl_per_tonne"] == TONNES_TO_BBL
    assert written_metadata["workbooks"]["oil"]["sha256"] == "abc123"


def _fake_workbook_responses(oil_bytes, gas_bytes):
    statistics_page = f"""
            <a href="{DEFAULT_WORKBOOKS["oil"].source_url}">oil</a>
            <a href="{DEFAULT_WORKBOOKS["gas"].source_url}">gas</a>
            """
    return {
        STATISTICS_PAGE_URL: CoresHttpResponse(
            content=statistics_page.encode("utf-8"),
            headers={"Content-Type": "text/html"},
        ),
        DEFAULT_WORKBOOKS["oil"].source_url: _fake_xlsx_response(
            oil_bytes,
            "Fri, 12 Jun 2026 07:51:41 GMT",
        ),
        DEFAULT_WORKBOOKS["gas"].source_url: _fake_xlsx_response(
            gas_bytes,
            "Fri, 12 Jun 2026 07:52:01 GMT",
        ),
    }


def _fake_xlsx_response(content, last_modified):
    return CoresHttpResponse(
        content=content,
        headers={
            "Content-Type": (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            "Last-Modified": last_modified,
        },
    )
