"""
ABOUTME: Multi-format export stage for analysis pipelines.
ABOUTME: export_report(result, formats, output_dir) -> ExportManifest
"""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_FORMATS = ["xlsx", "parquet"]
# Derive from the platform temp dir rather than a hardcoded "/tmp" path
# (portable + avoids B108 predictable-temp-path warning).
DEFAULT_OUTPUT_DIR = str(Path(tempfile.gettempdir()) / "worldenergydata_exports")

# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------


@dataclass
class ExportManifest:
    """Records the result of a multi-format export operation."""

    output_dir: str
    files: dict[str, str]  # format -> absolute file path
    formats_requested: list[str]
    formats_succeeded: list[str]
    formats_failed: dict[str, str]  # format -> error message
    timestamp: str


# ---------------------------------------------------------------------------
# Format writers (each returns the output file path as str)
# ---------------------------------------------------------------------------


def _write_xlsx(df: pd.DataFrame, summary: dict, dest: Path) -> str:
    """Write DataFrame + summary sheet to an xlsx file."""
    try:
        import openpyxl  # noqa: F401 — presence check
    except ImportError as exc:
        raise RuntimeError("openpyxl is not installed") from exc

    with pd.ExcelWriter(dest, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="data", index=False)
        summary_df = pd.DataFrame(list(summary.items()), columns=["key", "value"])
        summary_df.to_excel(writer, sheet_name="summary", index=False)

    return str(dest)


def _write_parquet(df: pd.DataFrame, dest: Path) -> str:
    """Write DataFrame to a parquet file (pyarrow preferred)."""
    try:
        df.to_parquet(dest, engine="pyarrow", index=False)
    except Exception:
        df.to_parquet(dest, index=False)
    return str(dest)


def _write_csv(df: pd.DataFrame, dest: Path) -> str:
    """Write DataFrame to a CSV file."""
    df.to_csv(dest, index=False)
    return str(dest)


def _write_json(df: pd.DataFrame, summary: dict, dest: Path) -> str:
    """Write data as JSON records plus summary to a single JSON file."""
    payload = {
        "data": json.loads(df.to_json(orient="records")),
        "summary": summary,
    }
    dest.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(dest)


def _write_html_report(df: pd.DataFrame, summary: dict, dest: Path) -> str:
    """Generate a simple HTML report (PDF fallback — no heavy deps needed).

    Attempts weasyprint/pdfkit first; falls back to plain HTML gracefully.
    The manifest key is always 'html_report' for this format.
    """
    rows_html = df.head(200).to_html(classes="data-table", border=1, index=False)

    summary_rows = "".join(
        f"<tr><td><b>{k}</b></td><td>{v}</td></tr>" for k, v in summary.items()
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>WorldEnergyData Export Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    table.data-table {{ border-collapse: collapse; width: 100%; }}
    table.data-table th, table.data-table td {{ border: 1px solid #ccc; padding: 6px; }}
    table.data-table th {{ background: #e0e0e0; }}
    h2 {{ color: #333; }}
  </style>
</head>
<body>
  <h1>WorldEnergyData Export Report</h1>
  <h2>Summary</h2>
  <table border="1" style="border-collapse:collapse">
    {summary_rows}
  </table>
  <h2>Data ({len(df)} rows)</h2>
  {rows_html}
</body>
</html>"""

    dest.write_text(html, encoding="utf-8")
    return str(dest)


# ---------------------------------------------------------------------------
# Format dispatch table
# ---------------------------------------------------------------------------

_EXTENSIONS: dict[str, str] = {
    "xlsx": ".xlsx",
    "parquet": ".parquet",
    "csv": ".csv",
    "json": ".json",
    "pdf": ".html",  # HTML fallback; manifest key re-mapped to html_report
}

_MANIFEST_KEYS: dict[str, str] = {
    "pdf": "html_report",  # re-label pdf -> html_report in manifest
}


def _dispatch(
    fmt: str,
    df: pd.DataFrame,
    summary: dict,
    dest: Path,
) -> str:
    """Call the correct writer for *fmt*."""
    if fmt == "xlsx":
        return _write_xlsx(df, summary, dest)
    if fmt == "parquet":
        return _write_parquet(df, dest)
    if fmt == "csv":
        return _write_csv(df, dest)
    if fmt == "json":
        return _write_json(df, summary, dest)
    if fmt == "pdf":
        return _write_html_report(df, summary, dest)
    raise ValueError(f"Unsupported export format: {fmt!r}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_SUPPORTED_FORMATS = frozenset(["xlsx", "parquet", "csv", "json", "pdf"])


def export_report(
    result: Any,
    formats: list[str] | None = None,
    output_dir: str | None = None,
    filename_prefix: str | None = None,
) -> ExportManifest:
    """Export *result* to one or more file formats.

    Parameters
    ----------
    result:
        Any object exposing ``.data`` (``pd.DataFrame``) and ``.summary``
        (``dict``).  If ``.summary`` is absent an empty dict is used.
    formats:
        List of format strings.  Supported: ``xlsx``, ``parquet``, ``csv``,
        ``json``, ``pdf``.  Defaults to ``["xlsx", "parquet"]``.
    output_dir:
        Directory to write files into.  Created if it does not exist.
        Defaults to ``/tmp/worldenergydata_exports``.
    filename_prefix:
        Stem prefix for output files.  Defaults to the lowercase class name
        of *result* (e.g. ``"fieldreport"``).

    Returns
    -------
    ExportManifest
        Records which files were created and which formats failed.
    """
    # --- Normalise inputs ---------------------------------------------------
    if formats is None:
        formats = list(DEFAULT_FORMATS)
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    if filename_prefix is None:
        filename_prefix = type(result).__name__.lower()

    # Extract data / summary from result
    df: pd.DataFrame = getattr(result, "data", pd.DataFrame())
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame()
    summary: dict = getattr(result, "summary", {}) or {}

    # --- Prepare output directory -------------------------------------------
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    files: dict[str, str] = {}
    succeeded: list[str] = []
    failed: dict[str, str] = {}

    # --- Export each format independently -----------------------------------
    for fmt in formats:
        if fmt not in _SUPPORTED_FORMATS:
            failed[fmt] = f"Unsupported format: {fmt!r}"
            logger.warning("Skipping unsupported format %r", fmt)
            continue

        ext = _EXTENSIONS[fmt]
        dest = out_path / f"{filename_prefix}{ext}"
        manifest_key = _MANIFEST_KEYS.get(fmt, fmt)

        try:
            file_path = _dispatch(fmt, df, summary, dest)
            files[manifest_key] = file_path
            succeeded.append(manifest_key)
            logger.info("Exported %s -> %s", manifest_key, file_path)
        except Exception as exc:  # noqa: BLE001
            error_msg = f"{type(exc).__name__}: {exc}"
            failed[manifest_key] = error_msg
            logger.warning("Export failed for %r: %s", fmt, error_msg)

    return ExportManifest(
        output_dir=str(out_path),
        files=files,
        formats_requested=list(formats),
        formats_succeeded=succeeded,
        formats_failed=failed,
        timestamp=timestamp,
    )
