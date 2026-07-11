"""HTML renderer for the Jack St Malo D&C diagnostic report."""

from __future__ import annotations

import html
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def write_html(
    diff: pd.DataFrame,
    activity: pd.DataFrame,
    sensitivity: pd.DataFrame,
    summary: dict[str, int],
    html_report: Path,
    extractor: Path,
    leases: Path,
    war_main: Path,
    war_boreholes: Path,
    war_remarks: Path,
) -> None:
    body = _html_document(
        chart=_delta_chart(diff),
        status_rows=_status_rows(diff),
        sens_rows=_sensitivity_rows(sensitivity),
        summary=summary,
        provenance=_provenance(war_main, war_boreholes, war_remarks),
        extractor_cmd=_extractor_cmd(
            extractor, leases, war_main, war_boreholes, war_remarks
        ),
        activity_rows=len(activity),
        citation=f"{extractor}:212-267 derive_completion_days()",
    )
    html_report.write_text(body, encoding="utf-8")


def _delta_chart(diff: pd.DataFrame) -> str:
    import plotly.graph_objects as go
    import plotly.io as pio

    changed = diff[diff["screening_status"] != "MATCH"].sort_values("api_well_number")
    fig = go.Figure(
        [
            go.Bar(
                name="Drilling delta",
                x=changed["api_well_number"],
                y=changed["drill_delta"],
                marker_color="#1d4ed8",
            ),
            go.Bar(
                name="Completion delta",
                x=changed["api_well_number"],
                y=changed["compl_delta"],
                marker_color="#b42318",
                hovertext=changed["screening_status"],
            ),
        ]
    )
    fig.update_layout(
        barmode="stack",
        title="JSM D&C day delta by bore",
        xaxis_title="API",
        yaxis_title="Candidate minus frozen days",
    )
    chart = pio.to_html(fig, include_plotlyjs="inline", full_html=False)
    # Plotly's inline bundle includes a default topojson URL for geo charts.
    # This report uses only a local bar chart; remove the inert CDN default so
    # the self-contained gate can grep fail-closed on any cdn.plot reference.
    return chart.replace("https://cdn.plot.ly/", "about:blank/")


def _status_rows(diff: pd.DataFrame) -> str:
    return "".join(
        f"<tr><td>{html.escape(r.api_well_number)}</td><td>{r.drill_delta}</td>"
        f"<td>{r.compl_delta}</td><td>{html.escape(r.screening_status)}</td></tr>"
        for r in diff.itertuples()
    )


def _sensitivity_rows(sensitivity: pd.DataFrame) -> str:
    return "".join(
        f"<tr><td>{html.escape(str(r.rule))}</td>"
        f"<td>{html.escape(str(r.development))}</td>"
        f"<td>{r.drilling_days}</td><td>{r.completion_days}</td>"
        f"<td>{r.d_and_c_days}</td><td>{r.qualified_rule}</td>"
        f"<td>{html.escape(str(r.disqualifier))}</td></tr>"
        for r in sensitivity.itertuples()
    )


def _provenance(
    war_main: Path, war_boreholes: Path, war_remarks: Path
) -> dict[str, str]:
    return {
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        "war_main_mtime": datetime.fromtimestamp(
            war_main.stat().st_mtime, timezone.utc
        ).isoformat(),
        "war_boreholes_mtime": datetime.fromtimestamp(
            war_boreholes.stat().st_mtime, timezone.utc
        ).isoformat(),
        "war_remarks_mtime": datetime.fromtimestamp(
            war_remarks.stat().st_mtime, timezone.utc
        ).isoformat(),
    }


def _extractor_cmd(
    extractor: Path,
    leases: Path,
    war_main: Path,
    war_boreholes: Path,
    war_remarks: Path,
) -> str:
    return (
        f"python {extractor} --leases {leases} --war-main {war_main} "
        f"--war-boreholes {war_boreholes} --war-remarks {war_remarks} "
        "--out <tempdir>/dc_days_candidate.xlsx"
    )


def _style() -> str:
    return """
body {
  color: #1f2937;
  font-family: Arial, sans-serif;
  line-height: 1.45;
  margin: 32px;
}
table {
  border-collapse: collapse;
  font-size: 13px;
  width: 100%;
}
td, th {
  border: 1px solid #d0d7de;
  padding: 6px;
}
th {
  background: #f6f8fa;
  text-align: left;
}
.metric {
  border: 1px solid #d0d7de;
  display: inline-block;
  margin: 0 16px 12px 0;
  padding: 10px 12px;
}
"""


def _html_document(
    *,
    chart: str,
    status_rows: str,
    sens_rows: str,
    summary: dict[str, int],
    provenance: dict[str, str],
    extractor_cmd: str,
    activity_rows: int,
    citation: str,
) -> str:
    screening_header = (
        "<tr><th>API</th><th>Drill delta</th><th>Completion delta</th>"
        "<th>Status</th></tr>"
    )
    sensitivity_header = (
        "<tr><th>Rule</th><th>Development</th><th>Drill</th>"
        "<th>Completion</th><th>D&amp;C</th><th>Qualified</th>"
        "<th>Disqualifier</th></tr>"
    )
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Jack St Malo D&amp;C Diff</title>
<style>{_style()}</style></head>
<body><h1>Jack St Malo D&amp;C Over-count Diagnostic</h1>
<p>Diagnostic-only PR for issue #846. No extractor behavior changes are applied here.</p>
<div class="metric">Frozen D&amp;C: <strong>{summary['frozen_dc_days']}</strong></div>
<div class="metric">Candidate D&amp;C: <strong>{summary['candidate_dc_days']}</strong></div>
<div class="metric">Delta: <strong>{summary['dc_delta']:+d}</strong></div>
{chart}
<h2>Screening Status</h2><table>{screening_header}{status_rows}</table>
<h2>Rule Sensitivity</h2><table>{sensitivity_header}{sens_rows}</table>
<h2>Provenance</h2><pre>{html.escape(str(provenance))}</pre>
<h2>Input Echo</h2><pre>{html.escape(extractor_cmd)}</pre>
<p>WAR vintage 2026-02-19. Activity rows: {activity_rows}.
Code citation: {html.escape(citation)}.</p>
</body></html>"""
    return body


def _git_sha() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
