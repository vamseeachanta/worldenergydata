"""Import filled reviewer inputs into BSEE field-structure decision products."""

from __future__ import annotations

import hashlib
import html
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_GATE_FIELDS = [
    "basis_page_accepted",
    "promote_to_verified_register",
    "basis_evidence_type",
    "verified_structure_class",
    "verified_quantity",
    "verified_segment_or_asset_id",
    "basis_reviewer",
    "basis_review_date",
]

MATCH_ONLY_FIELDS = [
    "asset_register_id",
    "review_sequence",
]

OPTIONAL_UPDATE_FIELDS = [
    "basis_decision",
    "observed_structure_class",
    "observed_quantity",
    "observed_segment_or_asset_id",
    "verified_asset_name",
    "verified_asset_role",
    "design_basis_reference",
    "basis_review_notes",
    "follow_up_required",
    "follow_up_owner",
]

ACCEPTED_VALUES = {"1", "accepted", "true", "yes", "y"}
PROMOTE_VALUES = {"1", "promote", "promoted", "true", "yes", "y"}


class ReviewerInputImportError(ValueError):
    """Raised when reviewer input products cannot be imported."""


def import_reviewer_ready_inputs(
    ready_input_path: Path | str,
    decision_log_path: Path | str,
    output_dir_path: Path | str,
    *,
    sqlite_product_path: Path | str | None = None,
) -> dict[str, Path | int]:
    """Validate filled reviewer rows and write updated decision products."""
    ready_input = _read_csv(Path(ready_input_path), "ready input")
    decision_log = _read_csv(Path(decision_log_path), "decision log")
    _validate_columns(ready_input, {"basis_review_decision_id", *REQUIRED_GATE_FIELDS})
    _validate_columns(decision_log, {"basis_review_decision_id"})

    output_dir = Path(output_dir_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    staging = _build_staging_audit(ready_input, decision_log)
    updated = _updated_decision_log(decision_log, ready_input, staging)
    gate = _build_promotion_gate(updated)
    verified = _build_verified_register(gate)

    staging_path = output_dir / "reviewer_ready_input_staging_audit.csv"
    updated_path = output_dir / "basis_review_decision_log_updated.csv"
    gate_path = output_dir / "promotion_gate_audit.csv"
    verified_path = output_dir / "verified_field_structure_register.csv"
    manifest_path = output_dir / "import_run_manifest.json"
    html_path = output_dir / "index.html"
    staging.to_csv(staging_path, index=False)
    updated.to_csv(updated_path, index=False)
    gate.to_csv(gate_path, index=False)
    verified.to_csv(verified_path, index=False)
    counts = {
        "import_ready": int((staging["import_ready"] == 1).sum()),
        "import_blocked": int((staging["import_ready"] != 1).sum()),
        "verified_rows": int(len(verified)),
    }
    output_files = {
        "staging_audit": _file_entry(staging_path, staging),
        "updated_decision_log": _file_entry(updated_path, updated),
        "promotion_gate_audit": _file_entry(gate_path, gate),
        "verified_register": _file_entry(verified_path, verified),
    }
    manifest = {
        "product": "bsee_reviewer_input_import",
        "generated_at": datetime.now(UTC).isoformat(),
        "inputs": {
            "ready_input": str(Path(ready_input_path)),
            "decision_log": str(Path(decision_log_path)),
        },
        "counts": counts,
        "required_gate_fields": REQUIRED_GATE_FIELDS,
        "match_only_fields": ["basis_review_decision_id", *MATCH_ONLY_FIELDS],
        "output_files": output_files,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    html_path.write_text(_render_import_html(manifest), encoding="utf-8")

    result = {
        "updated_decision_log": updated_path,
        "staging_audit": staging_path,
        "promotion_gate_audit": gate_path,
        "verified_register": verified_path,
        "import_manifest": manifest_path,
        "html_report": html_path,
        **counts,
    }
    if sqlite_product_path is not None:
        sqlite_path = Path(sqlite_product_path)
        _publish_latest_import_to_sqlite(
            sqlite_path,
            manifest,
            staging,
            updated,
            gate,
            verified,
            manifest_path,
            html_path,
        )
        result["sqlite_product"] = sqlite_path
    return result


def _read_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.is_file():
        raise ReviewerInputImportError(f"{label} CSV does not exist: {path}")
    return pd.read_csv(path, dtype=str).fillna("")


def _validate_columns(frame: pd.DataFrame, required: set[str]) -> None:
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ReviewerInputImportError(f"CSV missing columns: {missing}")


def _build_staging_audit(
    ready_input: pd.DataFrame,
    decision_log: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    decision_counts = decision_log["basis_review_decision_id"].value_counts()
    decisions = decision_log.set_index("basis_review_decision_id", drop=False)
    for _, source in ready_input.iterrows():
        missing = _missing_required(source)
        invalid = _identity_invalid(source, decisions, decision_counts)
        invalid.extend(_invalid_required(source))
        import_ready = 0 if missing or invalid else 1
        rows.append(
            {
                **_staging_context(source),
                "missing_required_fields": "|".join(missing),
                "invalid_required_fields": "|".join(invalid),
                "import_ready": import_ready,
                "staging_status": (
                    "import_ready"
                    if import_ready
                    else "blocked_missing_or_invalid_required_fields"
                ),
                "import_instruction": (
                    "Import only when import_ready=1; then rerun validation and gate."
                ),
            }
        )
    return pd.DataFrame(rows)


def _identity_invalid(
    source: pd.Series,
    decisions: pd.DataFrame,
    decision_counts: pd.Series,
) -> list[str]:
    decision_id = _text(source.get("basis_review_decision_id"))
    if not decision_id:
        return []
    if int(decision_counts.get(decision_id, 0)) != 1:
        return ["basis_review_decision_id"]
    target = decisions.loc[decision_id]
    invalid = []
    for field in MATCH_ONLY_FIELDS:
        if _text(source.get(field)) != _text(target.get(field)):
            invalid.append(field)
    return invalid


def _staging_context(source: pd.Series) -> dict[str, Any]:
    fields = [
        "ready_input_id",
        "basis_review_decision_id",
        "review_sequence",
        "field",
        "proposed_structure_class",
        "asset_register_id",
        "selected_basis_document_family",
        "selected_basis_document_id",
        "selected_basis_page_number",
        "source_pdf_path",
        "thumbnail_path",
    ]
    return {field: _text(source.get(field)) for field in fields}


def _updated_decision_log(
    decision_log: pd.DataFrame,
    ready_input: pd.DataFrame,
    staging: pd.DataFrame,
) -> pd.DataFrame:
    updated = decision_log.copy()
    _ensure_columns(updated, REQUIRED_GATE_FIELDS + OPTIONAL_UPDATE_FIELDS)
    ready_ids = set(staging.loc[staging["import_ready"] == 1, "basis_review_decision_id"])
    updates = ready_input.set_index("basis_review_decision_id", drop=False)
    for row_index, target in updated.iterrows():
        decision_id = _text(target.get("basis_review_decision_id"))
        if decision_id not in ready_ids:
            continue
        source = updates.loc[decision_id]
        for column in REQUIRED_GATE_FIELDS + OPTIONAL_UPDATE_FIELDS:
            value = _text(source.get(column))
            if value or column in REQUIRED_GATE_FIELDS:
                updated.at[row_index, column] = value
    return updated


def _build_promotion_gate(decision_log: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in decision_log.iterrows():
        missing = _missing_required(row)
        invalid = _invalid_required(row)
        ready = not missing and not invalid
        rows.append(
            {
                **{column: _text(row.get(column)) for column in decision_log.columns},
                "promotion_gate_audit_id": _audit_id(row),
                "promotion_ready": "1" if ready else "0",
                "promotion_gate_status": (
                    "ready_for_verified_register"
                    if ready
                    else "blocked_pending_review_fields"
                ),
                "missing_required_fields": "|".join(missing),
                "invalid_required_fields": "|".join(invalid),
            }
        )
    return pd.DataFrame(rows)


def _build_verified_register(gate: pd.DataFrame) -> pd.DataFrame:
    rows = []
    promoted = gate["promotion_gate_status"] == "ready_for_verified_register"
    for _, row in gate[promoted].iterrows():
        rows.append(
            {
                "verified_field_structure_id": _verified_id(row),
                "asset_register_id": _text(row.get("asset_register_id")),
                "basis_review_decision_id": _text(row.get("basis_review_decision_id")),
                "verified_register_delta_id": _text(row.get("verified_register_delta_id")),
                "review_sequence": _text(row.get("review_sequence")),
                "field": _text(row.get("field")),
                "field_join_key": _text(row.get("field_join_key")),
                "verified_structure_class": _text(row.get("verified_structure_class")),
                "verified_quantity": _text(row.get("verified_quantity")),
                "verified_segment_or_asset_id": _text(row.get("verified_segment_or_asset_id")),
                "verified_asset_name": _text(row.get("verified_asset_name")),
                "verified_asset_role": _text(row.get("verified_asset_role")),
                "basis_evidence_type": _text(row.get("basis_evidence_type")),
                "basis_document_family": _text(row.get("selected_basis_document_family")),
                "basis_document_id": _text(row.get("selected_basis_document_id")),
                "basis_page_number": _text(row.get("selected_basis_page_number")),
                "basis_source": _text(row.get("selected_basis_source")),
                "source_pdf_path": _text(row.get("source_pdf_path")),
                "thumbnail_path": _text(row.get("thumbnail_path")),
                "ocr_text_path": _text(row.get("ocr_text_path")),
                "evidence_packet_path": _text(row.get("evidence_packet_path")),
                "design_basis_reference": _text(row.get("design_basis_reference")),
                "basis_reviewer": _text(row.get("basis_reviewer")),
                "basis_review_date": _text(row.get("basis_review_date")),
                "basis_review_notes": _text(row.get("basis_review_notes")),
                "follow_up_required": _text(row.get("follow_up_required")),
                "follow_up_owner": _text(row.get("follow_up_owner")),
                "created_from": "basis_review_decision_log",
            }
        )
    return pd.DataFrame(rows, columns=VERIFIED_REGISTER_COLUMNS)


VERIFIED_REGISTER_COLUMNS = [
    "verified_field_structure_id",
    "asset_register_id",
    "basis_review_decision_id",
    "verified_register_delta_id",
    "review_sequence",
    "field",
    "field_join_key",
    "verified_structure_class",
    "verified_quantity",
    "verified_segment_or_asset_id",
    "verified_asset_name",
    "verified_asset_role",
    "basis_evidence_type",
    "basis_document_family",
    "basis_document_id",
    "basis_page_number",
    "basis_source",
    "source_pdf_path",
    "thumbnail_path",
    "ocr_text_path",
    "evidence_packet_path",
    "design_basis_reference",
    "basis_reviewer",
    "basis_review_date",
    "basis_review_notes",
    "follow_up_required",
    "follow_up_owner",
    "created_from",
]


def _missing_required(row: pd.Series) -> list[str]:
    return [field for field in REQUIRED_GATE_FIELDS if not _text(row.get(field))]


def _invalid_required(row: pd.Series) -> list[str]:
    invalid = []
    if (
        _text(row.get("basis_page_accepted"))
        and _norm(row.get("basis_page_accepted")) not in ACCEPTED_VALUES
    ):
        invalid.append("basis_page_accepted")
    if (
        _text(row.get("promote_to_verified_register"))
        and _norm(row.get("promote_to_verified_register")) not in PROMOTE_VALUES
    ):
        invalid.append("promote_to_verified_register")
    if _text(row.get("verified_quantity")) and not _positive_number(
        row.get("verified_quantity")
    ):
        invalid.append("verified_quantity")
    return invalid


def _ensure_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""


def _file_entry(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "path": str(path),
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "sha256": _sha256(path),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _publish_latest_import_to_sqlite(
    sqlite_path: Path,
    manifest: dict[str, Any],
    staging: pd.DataFrame,
    updated: pd.DataFrame,
    gate: pd.DataFrame,
    verified: pd.DataFrame,
    manifest_path: Path,
    html_path: Path,
) -> None:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    counts = manifest["counts"]
    run = pd.DataFrame(
        [
            {
                "product": manifest["product"],
                "generated_at": manifest["generated_at"],
                "ready_input": manifest["inputs"]["ready_input"],
                "decision_log": manifest["inputs"]["decision_log"],
                "import_ready": counts["import_ready"],
                "import_blocked": counts["import_blocked"],
                "verified_rows": counts["verified_rows"],
                "import_manifest_path": str(manifest_path),
                "html_report_path": str(html_path),
            }
        ]
    )
    tables = {
        "latest_reviewer_import_run": run,
        "latest_reviewer_import_staging_audit": staging,
        "latest_reviewer_import_decision_log": updated,
        "latest_reviewer_import_promotion_gate": gate,
        "latest_reviewer_import_verified_register": verified,
    }
    with sqlite3.connect(sqlite_path) as conn:
        for table in tables:
            conn.execute(f"DROP VIEW IF EXISTS v_{table}")
        for table, frame in tables.items():
            frame.to_sql(table, conn, if_exists="replace", index=False)
            conn.execute(f"CREATE VIEW v_{table} AS SELECT * FROM {table}")
        conn.commit()


def _render_import_html(manifest: dict[str, Any]) -> str:
    counts = manifest["counts"]
    output_rows = "\n".join(
        "<tr>"
        f"<td>{_esc(name)}</td>"
        f"<td>{_esc(details['path'])}</td>"
        f"<td>{details['rows']}</td>"
        f"<td>{details['columns']}</td>"
        f"<td><code>{_esc(details['sha256'])}</code></td>"
        "</tr>"
        for name, details in manifest["output_files"].items()
    )
    required = ", ".join(_esc(field) for field in manifest["required_gate_fields"])
    match_only = ", ".join(_esc(field) for field in manifest["match_only_fields"])
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        "  <title>BSEE Reviewer Input Import</title>\n"
        "  <style>\n"
        "    body { font-family: Arial, sans-serif; margin: 32px; color: #1f2933; }\n"
        "    table { border-collapse: collapse; width: 100%; margin: 16px 0; }\n"
        "    th, td { border: 1px solid #d8dde3; padding: 8px; text-align: left; }\n"
        "    th { background: #edf2f7; }\n"
        "    .metrics { display: flex; gap: 12px; flex-wrap: wrap; }\n"
        "    .metric { border: 1px solid #d8dde3; padding: 12px; min-width: 140px; }\n"
        "    .value { font-size: 1.7rem; font-weight: 700; }\n"
        "    code { font-size: 0.85rem; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>BSEE Reviewer Input Import</h1>\n"
        f"  <p>Generated at {_esc(manifest['generated_at'])}</p>\n"
        '  <div class="metrics">\n'
        f"    {_metric('Import Ready', counts['import_ready'])}\n"
        f"    {_metric('Import Blocked', counts['import_blocked'])}\n"
        f"    {_metric('Verified Rows', counts['verified_rows'])}\n"
        "  </div>\n"
        "  <h2>Inputs</h2>\n"
        "  <table><tbody>\n"
        f"    <tr><th>Ready input</th><td>{_esc(manifest['inputs']['ready_input'])}</td></tr>\n"
        f"    <tr><th>Decision log</th><td>{_esc(manifest['inputs']['decision_log'])}</td></tr>\n"
        "  </tbody></table>\n"
        "  <h2>Validation Contract</h2>\n"
        f"  <p><strong>Match-only fields:</strong> {match_only}</p>\n"
        f"  <p><strong>Required gate fields:</strong> {required}</p>\n"
        "  <h2>Outputs</h2>\n"
        "  <table>\n"
        "    <thead><tr><th>Key</th><th>Path</th><th>Rows</th>"
        "<th>Columns</th><th>SHA-256</th></tr></thead>\n"
        f"    <tbody>{output_rows}</tbody>\n"
        "  </table>\n"
        "</body>\n"
        "</html>\n"
    )


def _metric(label: str, value: int) -> str:
    return (
        '<div class="metric">'
        f"<div>{_esc(label)}</div>"
        f'<div class="value">{value}</div>'
        "</div>"
    )


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _audit_id(row: pd.Series) -> str:
    return f"PGA-{int(_text(row.get('review_sequence'))):02d}-{_field_token(row)}"


def _verified_id(row: pd.Series) -> str:
    return f"VFS-{int(_text(row.get('review_sequence'))):02d}-{_field_token(row)}"


def _field_token(row: pd.Series) -> str:
    return "-".join(
        [
            _text(row.get("field")).upper(),
            _text(row.get("verified_structure_class") or row.get("proposed_structure_class")).upper(),
            _text(row.get("verified_segment_or_asset_id") or row.get("segment_number")),
        ]
    )


def _positive_number(value: Any) -> bool:
    try:
        return float(_text(value)) > 0
    except ValueError:
        return False


def _norm(value: Any) -> str:
    return _text(value).strip().lower()


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value)
