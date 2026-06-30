"""Helpers for official Texas RRC GoDrive public download pages."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
from xml.etree import ElementTree


@dataclass(frozen=True)
class GoDriveFileForm:
    """JSF form values required to request one public GoDrive file."""

    command_id: str
    view_state: str


@dataclass(frozen=True)
class GoDriveDirectoryEntry:
    """One downloadable file row from a public GoDrive directory listing."""

    filename: str
    command_id: str
    modified_label: str
    size_label: str
    row_key: str | None
    page_first: int


@dataclass(frozen=True)
class GoDriveDirectoryPage:
    """Parsed page from a public GoDrive directory listing."""

    entries: tuple[GoDriveDirectoryEntry, ...]
    view_state: str
    row_count: int
    page_first: int
    rows_per_page: int


class GoDrivePublicPageParser(HTMLParser):
    """Extract the file command id and JSF view state from a GoDrive page."""

    def __init__(self, expected_filename: str):
        super().__init__()
        self.expected_filename = expected_filename
        self.view_states: list[str] = []
        self.command_id: str | None = None
        self._active_link_id: str | None = None
        self._active_link_text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attr_map = dict(attrs)
        if tag == "input" and attr_map.get("name") == "javax.faces.ViewState":
            value = attr_map.get("value")
            if value:
                self.view_states.append(value)
        if tag == "a" and attr_map.get("id", "").startswith("fileTable:"):
            self._active_link_id = attr_map["id"]
            self._active_link_text = []

    def handle_data(self, data: str) -> None:
        if self._active_link_id:
            self._active_link_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._active_link_id:
            return

        link_text = "".join(self._active_link_text).strip()
        if link_text == self.expected_filename:
            self.command_id = self._active_link_id
        self._active_link_id = None
        self._active_link_text = []


class GoDriveDirectoryParser(HTMLParser):
    """Extract zip file rows from a GoDrive directory table."""

    def __init__(self, page_first: int):
        super().__init__()
        self.page_first = page_first
        self.view_states: list[str] = []
        self.entries: list[GoDriveDirectoryEntry] = []
        self._row: dict[str, str | None] | None = None
        self._cell: str | None = None
        self._active_link_id: str | None = None
        self._active_link_text: list[str] = []
        self._cell_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "input" and attr_map.get("name") == "javax.faces.ViewState":
            value = attr_map.get("value")
            if value:
                self.view_states.append(value)
        if tag == "tr" and attr_map.get("data-ri") is not None:
            self._row = {"row_key": attr_map.get("data-rk")}
        if tag == "td" and self._row is not None:
            self._cell = self._cell_kind(attr_map.get("class", ""))
            self._cell_text = []
        if tag == "a" and self._row is not None:
            if attr_map.get("id", "").startswith("fileTable:"):
                self._active_link_id = attr_map["id"]
                self._active_link_text = []

    def handle_data(self, data: str) -> None:
        if self._active_link_id:
            self._active_link_text.append(data)
        elif self._cell:
            self._cell_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active_link_id and self._row is not None:
            self._capture_link()
        if tag == "td" and self._row is not None and self._cell:
            self._row[self._cell] = " ".join("".join(self._cell_text).split())
            self._cell = None
            self._cell_text = []
        if tag == "tr" and self._row is not None:
            self._append_row()
            self._row = None

    def _capture_link(self) -> None:
        filename = "".join(self._active_link_text).strip()
        if filename.lower().endswith(".zip"):
            self._row["filename"] = filename
            self._row["command_id"] = self._active_link_id
        self._active_link_id = None
        self._active_link_text = []

    def _append_row(self) -> None:
        filename = self._row.get("filename")
        command_id = self._row.get("command_id")
        if not filename or not command_id:
            return
        self.entries.append(
            GoDriveDirectoryEntry(
                filename=filename,
                command_id=command_id,
                modified_label=self._row.get("modified_label") or "",
                size_label=self._row.get("size_label") or "",
                row_key=self._row.get("row_key"),
                page_first=self.page_first,
            )
        )

    @staticmethod
    def _cell_kind(class_name: str) -> str | None:
        if "ModifiedOnColumn" in class_name:
            return "modified_label"
        if "SizeColumn" in class_name:
            return "size_label"
        return None


def parse_godrive_file_form(
    html_text: str,
    expected_filename: str,
) -> GoDriveFileForm:
    """Return the JSF form values for a named public GoDrive file."""
    parser = GoDrivePublicPageParser(expected_filename)
    parser.feed(html_text)
    if not parser.view_states:
        raise ValueError("Official GoDrive page did not include a JSF view state")
    if not parser.command_id:
        raise ValueError(
            f"Official GoDrive page did not list expected file {expected_filename!r}"
        )
    return GoDriveFileForm(
        command_id=parser.command_id,
        view_state=parser.view_states[-1],
    )


def parse_godrive_directory_page(
    html_text: str,
    page_first: int,
    rows_per_page: int,
) -> GoDriveDirectoryPage:
    """Return zip rows and pagination metadata from a GoDrive directory page."""
    row_count = _extract_row_count(html_text)
    effective_rows_per_page = _extract_rows_per_page(html_text) or rows_per_page
    return _parse_directory_fragment(
        html_text,
        page_first=page_first,
        rows_per_page=effective_rows_per_page,
        row_count=row_count,
    )


def parse_godrive_partial_directory_page(
    xml_text: str,
    page_first: int,
    rows_per_page: int,
    row_count: int,
    require_zip_rows: bool = True,
) -> GoDriveDirectoryPage:
    """Return zip rows from a JSF partial-response DataTable update."""
    root = ElementTree.fromstring(xml_text)
    fragment = ""
    view_state = None
    for update in root.iter("update"):
        update_id = update.attrib.get("id", "")
        if update_id == "fileTable":
            fragment = update.text or ""
        if "ViewState" in update_id:
            view_state = (update.text or "").strip()
    return _parse_directory_fragment(
        fragment,
        page_first=page_first,
        rows_per_page=rows_per_page,
        row_count=row_count,
        view_state=view_state,
        require_zip_rows=require_zip_rows,
    )


def _parse_directory_fragment(
    html_text: str,
    page_first: int,
    rows_per_page: int,
    row_count: int,
    view_state: str | None = None,
    require_zip_rows: bool = True,
) -> GoDriveDirectoryPage:
    parser = GoDriveDirectoryParser(page_first)
    parser.feed(html_text)
    page_view_state = view_state or _last_view_state(parser.view_states, html_text)
    if require_zip_rows and not parser.entries:
        raise ValueError("Official GoDrive directory page did not list zip files")
    return GoDriveDirectoryPage(
        entries=tuple(parser.entries),
        view_state=page_view_state,
        row_count=row_count,
        page_first=page_first,
        rows_per_page=rows_per_page,
    )


def _last_view_state(view_states: list[str], text: str) -> str:
    matches = re.findall(
        r'<update[^>]+id="[^"]*ViewState"[^>]*><!\[CDATA\[(.*?)\]\]>',
        text,
    )
    states = [*view_states, *(match.strip() for match in matches if match.strip())]
    if not states:
        raise ValueError("Official GoDrive page did not include a JSF view state")
    return states[-1]


def _extract_row_count(html_text: str) -> int:
    for pattern in (r"rowCount:(\d+)", r"Showing\s+[\d\s-]+of\s+(\d+)"):
        match = re.search(pattern, html_text)
        if match:
            return int(match.group(1))
    raise ValueError("Official GoDrive directory page did not include row count")


def _extract_rows_per_page(html_text: str) -> int | None:
    match = re.search(r"rows:(\d+)", html_text)
    if not match:
        return None
    return int(match.group(1))


__all__ = [
    "GoDriveDirectoryEntry",
    "GoDriveDirectoryPage",
    "GoDriveFileForm",
    "GoDrivePublicPageParser",
    "parse_godrive_directory_page",
    "parse_godrive_file_form",
    "parse_godrive_partial_directory_page",
]
