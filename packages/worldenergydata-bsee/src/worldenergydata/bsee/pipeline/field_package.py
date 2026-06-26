"""Engineering-facing package renderer for BSEE field infrastructure bundles."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import pandas as pd

FIELD_PACKAGE_CONTRACT_VERSION = "field-infrastructure-package-v1"
BSEE_SCANNED_DOCUMENTS = {
    "pipeline_map": {
        "pdf_dir": "PIPEMAPS",
        "query_url": "https://www.data.bsee.gov/Other/FileRequestSystem/ScanPipelineMaps.aspx",
    },
    "row": {
        "pdf_dir": "ROW",
        "query_url": "https://www.data.bsee.gov/Other/FileRequestSystem/ScanROW.aspx",
    },
    "plan": {
        "pdf_dir": "PLANS",
        "query_url": "https://www.data.bsee.gov/Other/FileRequestSystem/ScanPlans.aspx",
    },
}


class FieldPackageError(ValueError):
    """Raised when a field infrastructure package cannot be built."""


def build_field_package(
    bundle_dir: Path | str,
    output_dir: Path | str,
) -> dict[str, Path]:
    """Write an engineering-facing package from a field infrastructure bundle.

    Args:
        bundle_dir: Directory containing the field infrastructure bundle contract.
        output_dir: Directory where `index.html` and `document_queue.csv` are written.
    """
    bundle = _load_bundle(Path(bundle_dir))
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    document_queue = _build_document_queue(bundle["documents"])
    html_report = render_field_package_html(bundle, document_queue)

    paths = {
        "html_report": out / "index.html",
        "document_queue": out / "document_queue.csv",
    }
    paths["html_report"].write_text(html_report, encoding="utf-8")
    document_queue.to_csv(paths["document_queue"], index=False)
    return paths


def render_field_package_html(
    bundle: dict[str, Any],
    document_queue: pd.DataFrame | None = None,
) -> str:
    """Render a static HTML field package from loaded bundle data."""
    document_queue = (
        _build_document_queue(bundle["documents"])
        if document_queue is None
        else document_queue
    )
    context = bundle["context"]
    summary = bundle["summary"]
    field_name = _text(context.get("field_name") or summary.get("field_name"))
    field_code = _text(context.get("field_code") or summary.get("field_code"))

    sections = [
        _hero_section(context, summary),
        _summary_section(context, summary),
        _asset_inventory_section(bundle["structures"]),
        _pipeline_section(bundle["pipeline_segments"], bundle["appurtenances"]),
        _document_queue_section(document_queue),
        _evidence_section(),
    ]

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>BSEE Field Infrastructure Package - {_esc(field_name)}</title>\n"
        f"<style>\n{_css()}\n</style>\n"
        "</head>\n"
        "<body>\n"
        '<main class="page">\n'
        f'  <p class="contract">{FIELD_PACKAGE_CONTRACT_VERSION}</p>\n'
        f"  <h1>{_esc(field_name)}</h1>\n"
        f'  <p class="subtitle">BSEE field code {_esc(field_code)}</p>\n'
        f"{''.join(sections)}\n"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )


def _load_bundle(bundle_dir: Path) -> dict[str, Any]:
    required = {
        "context": bundle_dir / "field_context.json",
        "summary": bundle_dir / "engineering_summary.json",
        "structures": bundle_dir / "structures.csv",
        "pipeline_segments": bundle_dir / "pipeline_segments.csv",
        "appurtenances": bundle_dir / "appurtenances.csv",
        "documents": bundle_dir / "documents.csv",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise FieldPackageError(f"Bundle is missing required files: {missing}")
    return {
        "context": _read_json(required["context"]),
        "summary": _read_json(required["summary"]),
        "structures": pd.read_csv(required["structures"]),
        "pipeline_segments": pd.read_csv(required["pipeline_segments"]),
        "appurtenances": pd.read_csv(required["appurtenances"]),
        "documents": pd.read_csv(required["documents"]),
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FieldPackageError(f"Cannot parse JSON file {path}: {exc}") from exc


def _build_document_queue(documents: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "priority_rank",
        "document_family",
        "document_id",
        "segment_number",
        "lease_number",
        "row_number",
        "control_number",
        "document_type",
        "document_date",
        "retrieval_reason",
        "retrieval_url",
        "retrieval_status",
        "query_url",
        "evidence_confidence",
        "source_table",
    ]
    if documents.empty:
        return pd.DataFrame(columns=columns)

    queue = documents.copy()
    for column in columns:
        if column not in queue.columns and column != "priority_rank":
            queue[column] = ""

    queue["retrieval_reason"] = (
        queue["document_family"]
        .map(_retrieval_reason)
        .fillna("Review indexed document before engineering use")
    )
    queue["retrieval_url"] = queue.apply(_candidate_pdf_url, axis=1)
    queue["retrieval_status"] = queue["retrieval_url"].map(
        lambda value: "candidate_pdf_url" if _text(value) else "query_page_only"
    )
    queue["query_url"] = queue["document_family"].map(_query_url).fillna("")
    family_priority = {"pipeline_map": 1, "row": 2, "plan": 3}
    queue["_family_priority"] = queue["document_family"].map(family_priority).fillna(99)
    queue = queue.sort_values(
        ["_family_priority", "segment_number", "document_id", "lease_number"],
        kind="stable",
    ).reset_index(drop=True)
    queue.insert(0, "priority_rank", range(1, len(queue) + 1))
    return queue[columns]


def _retrieval_reason(document_family: Any) -> str:
    family = _text(document_family)
    if family == "pipeline_map":
        return "Review pipeline map for segment geometry and appurtenance context"
    if family == "row":
        return "Review ROW document for right-of-way and segment authorization context"
    if family == "plan":
        return (
            "Review plan document for lease-level development and installation context"
        )
    return "Review indexed document before engineering use"


def _candidate_pdf_url(row: pd.Series) -> str:
    family = _text(row.get("document_family"))
    doc_id = _text(row.get("document_id"))
    if not doc_id or family not in BSEE_SCANNED_DOCUMENTS:
        return ""
    try:
        doc_id_int = int(float(doc_id))
    except ValueError:
        return ""
    directory = BSEE_SCANNED_DOCUMENTS[family]["pdf_dir"]
    bucket = doc_id_int // 1000
    return (
        f"https://www.data.bsee.gov/PDFDocs/Scan/{directory}/"
        f"{bucket}/{doc_id_int}.pdf"
    )


def _query_url(document_family: Any) -> str:
    family = _text(document_family)
    if family not in BSEE_SCANNED_DOCUMENTS:
        return ""
    return BSEE_SCANNED_DOCUMENTS[family]["query_url"]


def _hero_section(context: dict[str, Any], summary: dict[str, Any]) -> str:
    leases = _format_list(context.get("leases", []))
    area_blocks = _format_list(context.get("area_blocks", []))
    operators = _format_list(context.get("operator_names", []))
    water_depth = _text(context.get("average_water_depth_ft"))
    return (
        '<section class="panel">\n'
        "  <h2>Field Context</h2>\n"
        '  <div class="facts">\n'
        f"    {_fact('Leases', leases)}\n"
        f"    {_fact('Area Blocks', area_blocks)}\n"
        f"    {_fact('Operators', operators)}\n"
        f"    {_fact('Average Water Depth ft', water_depth or 'N/A')}\n"
        f"    {_fact('Route Bounds', _route_bounds(summary.get('route_bounds')))}\n"
        "  </div>\n"
        "</section>\n"
    )


def _summary_section(context: dict[str, Any], summary: dict[str, Any]) -> str:
    del context
    cards = [
        ("Infrastructure Records", summary.get("infrastructure_record_count")),
        ("Platform Structures", summary.get("structure_count")),
        ("Pipeline Segments", summary.get("pipeline_segment_count")),
        ("Pipeline Location Rows", summary.get("pipeline_location_row_count")),
        ("Appurtenances", summary.get("appurtenance_count")),
        ("Documents", summary.get("document_count")),
    ]
    card_html = "\n".join(_metric(label, value) for label, value in cards)
    app_types = _format_list(summary.get("appurtenance_types", []))
    return (
        '<section class="panel">\n'
        "  <h2>Engineering Summary</h2>\n"
        f'  <div class="metrics">{card_html}</div>\n'
        f"  <p><strong>Appurtenance types:</strong> {_esc(app_types or 'None')}</p>\n"
        "</section>\n"
    )


def _asset_inventory_section(structures: pd.DataFrame) -> str:
    if structures.empty:
        table = '<p class="empty">No direct infrastructure rows in this bundle.</p>'
    else:
        counts = _counts_table(structures, "asset_type", "Records")
        detail = _html_table(
            structures,
            [
                "asset_type",
                "structure_name",
                "structure_type",
                "area_code",
                "block_number",
                "water_depth_ft",
                "evidence_confidence",
            ],
            max_rows=20,
        )
        table = f"{counts}\n<h3>Key Infrastructure Rows</h3>\n{detail}"
    return (
        '<section class="panel">\n'
        "  <h2>Asset Inventory</h2>\n"
        f"{table}\n"
        "</section>\n"
    )


def _pipeline_section(
    pipeline_segments: pd.DataFrame, appurtenances: pd.DataFrame
) -> str:
    segment_table = (
        '<p class="empty">No pipeline segments matched this bundle.</p>'
        if pipeline_segments.empty
        else _html_table(
            pipeline_segments,
            [
                "segment_number",
                "origin_name",
                "destination_name",
                "product_code",
                "pipeline_size_code",
                "status",
                "evidence_confidence",
            ],
            max_rows=20,
        )
    )
    appurtenance_table = (
        '<p class="empty">No appurtenance rows matched this bundle.</p>'
        if appurtenances.empty
        else _html_table(
            _high_value_appurtenances(appurtenances),
            [
                "segment_number",
                "asbuilt_sequence",
                "appurtenance_type",
                "latitude",
                "longitude",
                "evidence_confidence",
            ],
            max_rows=30,
        )
    )
    return (
        '<section class="panel">\n'
        "  <h2>Pipeline Segments</h2>\n"
        f"{segment_table}\n"
        "  <h3>Riser, Tie-In, Manifold, and Sled Highlights</h3>\n"
        f"{appurtenance_table}\n"
        "</section>\n"
    )


def _document_queue_section(document_queue: pd.DataFrame) -> str:
    if document_queue.empty:
        content = '<p class="empty">No document-index rows matched this bundle.</p>'
    else:
        content = _html_table(
            document_queue,
            [
                "priority_rank",
                "document_family",
                "document_id",
                "segment_number",
                "lease_number",
                "row_number",
                "control_number",
                "retrieval_reason",
                "retrieval_url",
                "retrieval_status",
            ],
            max_rows=40,
        )
    return (
        '<section class="panel">\n'
        "  <h2>Document Retrieval Queue</h2>\n"
        "  <p>Retrieve indexed BSEE documents before detailed design.</p>\n"
        f"{content}\n"
        "</section>\n"
    )


def _evidence_section() -> str:
    return (
        '<section class="panel evidence">\n'
        "  <h2>Engineering Caveats</h2>\n"
        "  <ul>\n"
        "    <li>Direct rows can support screening, but still require source review.</li>\n"
        "    <li>Inferred rows are linked by lease, area/block, segment, or complex.</li>\n"
        "    <li>Document-index rows are retrieval leads, not final engineering basis.</li>\n"
        "    <li>Risers, jumpers, and umbilicals are not complete unless present in source evidence.</li>\n"
        "  </ul>\n"
        "</section>\n"
    )


def _high_value_appurtenances(appurtenances: pd.DataFrame) -> pd.DataFrame:
    if "appurtenance_type" not in appurtenances.columns:
        return appurtenances
    pattern = "RISER|TIE|MANIFOLD|SLED|UMB|WELL|BLOCK"
    mask = (
        appurtenances["appurtenance_type"]
        .astype("string")
        .fillna("")
        .str.contains(pattern, case=False, regex=True)
    )
    highlighted = appurtenances[mask]
    return highlighted if not highlighted.empty else appurtenances


def _counts_table(df: pd.DataFrame, column: str, count_label: str) -> str:
    if column not in df.columns:
        return ""
    counts = (
        df[column]
        .astype("string")
        .fillna("")
        .replace("", "Unknown")
        .value_counts()
        .rename_axis(column)
        .reset_index(name=count_label)
    )
    return _html_table(counts, [column, count_label], max_rows=20)


def _html_table(
    df: pd.DataFrame,
    columns: list[str],
    *,
    max_rows: int,
) -> str:
    available = [column for column in columns if column in df.columns]
    if not available:
        return '<p class="empty">No display columns available.</p>'
    rows = df[available].head(max_rows)
    header = "".join(
        f"<th>{_esc(column.replace('_', ' ').title())}</th>" for column in available
    )
    body = []
    for _, row in rows.iterrows():
        cells = "".join(_html_cell(column, row[column]) for column in available)
        body.append(f"<tr>{cells}</tr>")
    more = ""
    if len(df) > max_rows:
        more = f'<p class="note">Showing {max_rows} of {len(df)} rows.</p>'
    return (
        '<div class="table-wrap">\n'
        "<table>\n"
        f"<thead><tr>{header}</tr></thead>\n"
        f"<tbody>{''.join(body)}</tbody>\n"
        "</table>\n"
        "</div>\n"
        f"{more}"
    )


def _html_cell(column: str, value: Any) -> str:
    text = _text(value)
    if column == "retrieval_url" and text.startswith("https://"):
        safe_url = _esc(text)
        return (
            '<td><a href="'
            f'{safe_url}" target="_blank" rel="noopener noreferrer">Open PDF</a></td>'
        )
    if column == "query_url" and text.startswith("https://"):
        safe_url = _esc(text)
        return (
            '<td><a href="'
            f'{safe_url}" target="_blank" rel="noopener noreferrer">Open Query</a></td>'
        )
    return f"<td>{_esc(text)}</td>"


def _fact(label: str, value: str) -> str:
    return (
        '<div class="fact">'
        f'<span class="label">{_esc(label)}</span>'
        f'<span class="value">{_esc(value or "N/A")}</span>'
        "</div>"
    )


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f'<span class="metric-value">{_esc(_text(value) or "0")}</span>'
        f'<span class="metric-label">{_esc(label)}</span>'
        "</div>"
    )


def _route_bounds(bounds: Any) -> str:
    if not isinstance(bounds, dict):
        return "N/A"
    return (
        f"lat {_text(bounds.get('latitude_min'))} to {_text(bounds.get('latitude_max'))}, "
        f"lon {_text(bounds.get('longitude_min'))} to {_text(bounds.get('longitude_max'))}"
    )


def _format_list(values: Any) -> str:
    if values is None:
        return ""
    if isinstance(values, str):
        return values
    try:
        return ", ".join(_text(value) for value in values if _text(value))
    except TypeError:
        return _text(values)


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _esc(value: Any) -> str:
    return html.escape(_text(value), quote=True)


def _css() -> str:
    return """
:root {
  color-scheme: light;
  --ink: #16202a;
  --muted: #5d6875;
  --line: #d8dee6;
  --panel: #ffffff;
  --bg: #f5f7fa;
  --accent: #0f6b78;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: Arial, Helvetica, sans-serif;
  line-height: 1.45;
}
.page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 32px 20px 48px;
}
.contract {
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .08em;
  margin: 0 0 8px;
  text-transform: uppercase;
}
h1 {
  font-size: 38px;
  line-height: 1.1;
  margin: 0;
}
.subtitle {
  color: var(--muted);
  margin: 8px 0 24px;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  margin: 16px 0;
  padding: 20px;
}
h2 {
  font-size: 22px;
  margin: 0 0 14px;
}
h3 {
  font-size: 16px;
  margin: 18px 0 10px;
}
.facts, .metrics {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}
.fact, .metric {
  border-left: 3px solid var(--accent);
  padding-left: 10px;
}
.label, .metric-label {
  color: var(--muted);
  display: block;
  font-size: 12px;
  text-transform: uppercase;
}
.value, .metric-value {
  display: block;
  font-size: 18px;
  font-weight: 700;
  margin-top: 2px;
}
.table-wrap {
  overflow-x: auto;
}
table {
  border-collapse: collapse;
  font-size: 13px;
  min-width: 720px;
  width: 100%;
}
th, td {
  border-bottom: 1px solid var(--line);
  padding: 8px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #edf3f5;
  color: #24313d;
  font-size: 12px;
  text-transform: uppercase;
}
.empty, .note {
  color: var(--muted);
}
.evidence ul {
  margin-bottom: 0;
}
""".strip()
