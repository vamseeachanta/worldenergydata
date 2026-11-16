"""Render explicit segment/component joins without inferring asset ownership."""

from __future__ import annotations

import html
import re
from collections import defaultdict
from typing import Any

import pandas as pd

_COMPONENT_COLUMNS = (
    "segment_number",
    "appurtenance_type",
    "asbuilt_sequence",
    "source_table",
    "join_key",
    "evidence_confidence",
)
_SEGMENT_COLUMNS = (
    "segment_number",
    "origin_name",
    "destination_name",
    "product_code",
    "pipeline_size_code",
    "source_table",
    "join_key",
    "evidence_confidence",
)


def _text(value: Any) -> str:
    """CSV cells are scalar; retain missing evidence as an explicit absence."""
    return "" if value is None or pd.isna(value) else str(value).strip()


def _key(value: Any) -> str:
    text = _text(value)
    if re.fullmatch(r"[0-9]+(?:\.0+)?", text):
        return text.split(".")[0].lstrip("0") or "0"
    return text


def _fields(row: dict[str, Any], columns: tuple[str, ...]) -> str:
    return (
        "<dl>"
        + "".join(
            f"<dt>{column}</dt>"
            f"<dd>{html.escape(_text(row.get(column)) or 'unavailable', quote=True)}</dd>"
            for column in columns
        )
        + "</dl>"
    )


def render_component_details(
    pipeline_segments: pd.DataFrame, appurtenances: pd.DataFrame
) -> str:
    """List every source row once; join only nonblank, unambiguous segment IDs.

    Integer CSV IDs and their zero-fraction forms share a key without float
    conversion. Conflicting nonblank endpoint/product/size values for a key
    make its membership ambiguous. Missing metadata does not establish conflict.
    Input order determines generated anchors, never source text.
    """
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unkeyed = []
    for row in pipeline_segments.to_dict("records"):
        key = _key(row.get("segment_number"))
        if key:
            groups[key].append(row)
        else:
            unkeyed.append(row)
    ambiguous = {
        key
        for key, rows in groups.items()
        if any(
            len({_text(row.get(column)) for row in rows} - {""}) > 1
            for column in _SEGMENT_COLUMNS[1:5]
        )
    }
    matched: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    unresolved = []
    for number, row in enumerate(appurtenances.to_dict("records"), start=1):
        key = _key(row.get("segment_number"))
        if key and key in groups and key not in ambiguous:
            matched[key].append((number, row))
        else:
            reason = (
                "Missing segment key"
                if not key
                else (
                    "Ambiguous segment inventory"
                    if key in ambiguous
                    else "No matching segment inventory"
                )
            )
            unresolved.append((number, row, reason))

    def component(number: int, row: dict[str, Any], reason: str = "") -> str:
        label = html.escape(_text(row.get("appurtenance_type")) or "unavailable")
        return (
            f'<details class="component" id="pipeline-component-{number}">'
            f"<summary>Component {number}: {label}</summary>"
            f"<p>{reason}</p>{_fields(row, _COMPONENT_COLUMNS)}</details>"
        )

    def inventory(rows: list[dict[str, Any]]) -> str:
        return "".join(
            f'<div class="segment-record">{_fields(row, _SEGMENT_COLUMNS)}</div>'
            for row in rows
        )

    parts = [
        '<section id="pipeline-components" class="panel">',
        "<h2>Pipeline Component Details</h2>",
        "<p>Membership uses explicit segment keys only; facility ownership is not inferred. "
        "Inferred evidence needs engineering review. Document-index rows are retrieval leads, "
        "not a design basis. Missing evidence is unavailable.</p>",
    ]
    for number, (key, rows) in enumerate(groups.items(), start=1):
        contents = "".join(component(n, row) for n, row in matched[key])
        parts.append(
            f'<details class="segment" id="pipeline-segment-{number}">'
            f"<summary>Segment {html.escape(key, quote=True)}</summary>"
            f"{inventory(rows)}{contents or '<p>No component records assigned.</p>'}</details>"
        )
    if unkeyed or unresolved:
        parts.append(
            '<details class="unresolved" id="pipeline-unresolved">'
            "<summary>Unresolved records</summary>"
            "<p>Missing, unmatched or ambiguous keys require source review.</p>"
            + inventory(unkeyed)
            + "".join(component(n, row, reason) for n, row, reason in unresolved)
            + "</details>"
        )
    if not groups and not unkeyed and not unresolved:
        parts.append("<p>No segment or component records in this bundle.</p>")
    return "\n".join(parts) + "\n</section>\n"
