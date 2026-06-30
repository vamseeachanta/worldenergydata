"""Tests for official Texas RRC GoDrive directory listings."""

from __future__ import annotations

from io import BytesIO
from urllib.parse import parse_qs

import pytest

DIRECTORY_HTML = """
<html>
  <body>
    <form id="fileList">
      <input name="javax.faces.ViewState" value="old-state" />
      <input name="javax.faces.ViewState" value="fresh-state" />
      <tbody id="fileTable_data">
        <tr data-ri="0" data-rk="3832">
          <td class="ImageColumn"><img alt="zip" /></td>
          <td class="NameColumn">
            <a id="fileTable:0:j_id_2f" href="#">well001.zip</a>
          </td>
          <td class="ModifiedOnColumn">6/29/26 6:14:59 PM</td>
          <td class="SizeColumn">610.56 KB</td>
        </tr>
        <tr data-ri="1" data-rk="3833">
          <td class="ImageColumn"><img alt="zip" /></td>
          <td class="NameColumn">
            <a id="fileTable:1:j_id_2f" href="#">well003.zip</a>
          </td>
          <td class="ModifiedOnColumn">6/29/26 6:15:00 PM</td>
          <td class="SizeColumn">3.42 MB</td>
        </tr>
        <tr data-ri="2" data-rk="skip">
          <td class="NameColumn">
            <a id="fileTable:2:j_id_2f" href="#">readme.txt</a>
          </td>
        </tr>
      </tbody>
      <script>
        PrimeFaces.cw("DataTable","files",{id:"fileTable",
          paginator:{rows:250,rowCount:255,page:0}});
      </script>
    </form>
  </body>
</html>
"""


PARTIAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<partial-response>
  <changes>
    <update id="fileTable"><![CDATA[
      <tbody id="fileTable_data">
        <tr data-ri="250" data-rk="4082">
          <td class="NameColumn">
            <a id="fileTable:250:j_id_2f" href="#">well501.zip</a>
          </td>
          <td class="ModifiedOnColumn">6/29/26 6:16:29 PM</td>
          <td class="SizeColumn">1.03 MB</td>
        </tr>
        <tr data-ri="251" data-rk="FED">
          <td class="NameColumn">
            <a id="fileTable:251:j_id_2f" href="#">wellFED.zip</a>
          </td>
          <td class="ModifiedOnColumn">6/29/26 6:16:30 PM</td>
          <td class="SizeColumn">8.31 KB</td>
        </tr>
      </tbody>
    ]]></update>
    <update id="javax.faces.ViewState"><![CDATA[next-state]]></update>
  </changes>
</partial-response>
"""


EMPTY_PARTIAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<partial-response>
  <changes>
    <update id="fileTable"><![CDATA[
      <tbody id="fileTable_data">
        <tr data-ri="250" data-rk="nonzip">
          <td class="NameColumn">
            <a id="fileTable:250:j_id_2f" href="#">README.txt</a>
          </td>
        </tr>
      </tbody>
    ]]></update>
    <update id="javax.faces.ViewState"><![CDATA[next-state]]></update>
  </changes>
</partial-response>
"""


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        status: int = 200,
        url: str = "https://mft.rrc.texas.gov/webclient/godrive/PublicGoDrive.xhtml",
        headers: dict[str, str] | None = None,
    ):
        self._body = BytesIO(body)
        self.status = status
        self.headers = headers or {"Content-Type": "text/html;charset=UTF-8"}
        self._url = url

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


class RecordingOpener:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = responses
        self.requests = []

    def open(self, request, timeout=60):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("No fake response configured")
        return self.responses.pop(0)


def test_parse_godrive_directory_page_extracts_zip_rows_and_metadata():
    from worldenergydata.texas_rrc.godrive import parse_godrive_directory_page

    page = parse_godrive_directory_page(DIRECTORY_HTML, page_first=0, rows_per_page=250)

    assert page.view_state == "fresh-state"
    assert page.row_count == 255
    assert page.page_first == 0
    assert page.rows_per_page == 250
    assert [entry.filename for entry in page.entries] == [
        "well001.zip",
        "well003.zip",
    ]
    assert page.entries[0].command_id == "fileTable:0:j_id_2f"
    assert page.entries[0].modified_label == "6/29/26 6:14:59 PM"
    assert page.entries[0].size_label == "610.56 KB"
    assert page.entries[0].row_key == "3832"


def test_parse_godrive_directory_page_uses_server_page_size_when_capped():
    from worldenergydata.texas_rrc.godrive import parse_godrive_directory_page

    page = parse_godrive_directory_page(
        DIRECTORY_HTML,
        page_first=0,
        rows_per_page=1000,
    )

    assert page.rows_per_page == 250


def test_parse_godrive_partial_directory_page_extracts_next_view_state():
    from worldenergydata.texas_rrc.godrive import parse_godrive_partial_directory_page

    page = parse_godrive_partial_directory_page(
        PARTIAL_XML,
        page_first=250,
        rows_per_page=250,
        row_count=255,
    )

    assert page.view_state == "next-state"
    assert page.row_count == 255
    assert page.page_first == 250
    assert [entry.filename for entry in page.entries] == [
        "well501.zip",
        "wellFED.zip",
    ]
    assert page.entries[1].row_key == "FED"


def test_parse_godrive_directory_page_requires_view_state():
    from worldenergydata.texas_rrc.godrive import parse_godrive_directory_page

    with pytest.raises(ValueError, match="view state"):
        parse_godrive_directory_page(
            DIRECTORY_HTML.replace("javax.faces.ViewState", "notViewState"),
            page_first=0,
            rows_per_page=250,
        )


def test_url_transport_lists_directory_pages_with_primefaces_pagination():
    from worldenergydata.texas_rrc.raw_transport import UrlLibTransport

    opener = RecordingOpener(
        [
            FakeResponse(DIRECTORY_HTML.encode("utf-8")),
            FakeResponse(
                PARTIAL_XML.encode("utf-8"),
                headers={"Content-Type": "text/xml;charset=UTF-8"},
            ),
        ]
    )
    transport = UrlLibTransport(opener_factory=lambda: opener)

    pages = transport.list_godrive_directory(
        "https://mft.rrc.texas.gov/link/d551fb20-442e-4b67-84fa-ac3f23ecabb4",
        rows_per_page=1000,
    )

    assert [entry.filename for page in pages for entry in page.entries] == [
        "well001.zip",
        "well003.zip",
        "well501.zip",
        "wellFED.zip",
    ]
    assert len(opener.requests) == 2
    page_request = opener.requests[1]
    post = parse_qs(page_request.data.decode("utf-8"))
    assert post["javax.faces.partial.ajax"] == ["true"]
    assert post["javax.faces.source"] == ["fileTable"]
    assert post["fileTable_first"] == ["250"]
    assert post["fileTable_rows"] == ["1000"]
    assert post["javax.faces.ViewState"] == ["fresh-state"]


def test_url_transport_allows_final_directory_page_without_zip_rows():
    from worldenergydata.texas_rrc.raw_transport import UrlLibTransport

    opener = RecordingOpener(
        [
            FakeResponse(DIRECTORY_HTML.encode("utf-8")),
            FakeResponse(
                EMPTY_PARTIAL_XML.encode("utf-8"),
                headers={"Content-Type": "text/xml;charset=UTF-8"},
            ),
        ]
    )
    transport = UrlLibTransport(opener_factory=lambda: opener)

    pages = transport.list_godrive_directory(
        "https://mft.rrc.texas.gov/link/d551fb20-442e-4b67-84fa-ac3f23ecabb4",
        rows_per_page=1000,
    )

    assert [entry.filename for page in pages for entry in page.entries] == [
        "well001.zip",
        "well003.zip",
    ]
    assert len(opener.requests) == 2


def test_url_transport_rejects_non_rrc_godrive_directory_url():
    from worldenergydata.texas_rrc.raw_transport import UrlLibTransport

    with pytest.raises(ValueError, match="official RRC GoDrive"):
        UrlLibTransport().list_godrive_directory("https://example.com/link/not-rrc")


def test_url_transport_allows_missing_content_disposition_for_expected_filename():
    from worldenergydata.texas_rrc.raw_transport import UrlLibTransport

    UrlLibTransport._validate_artifact_response(
        200,
        {"content-type": "application/zip"},
        expected_filename="well001.zip",
    )
