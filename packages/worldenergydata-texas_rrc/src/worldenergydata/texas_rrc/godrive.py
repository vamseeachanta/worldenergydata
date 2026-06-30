"""Helpers for official Texas RRC GoDrive public download pages."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass(frozen=True)
class GoDriveFileForm:
    """JSF form values required to request one public GoDrive file."""

    command_id: str
    view_state: str


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


__all__ = ["GoDriveFileForm", "GoDrivePublicPageParser", "parse_godrive_file_form"]
