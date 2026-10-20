"""Mexico production-chain readiness report with explicit qualification gaps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape

from worldenergydata.fdas.adapters.contract import FdasInputs

from .bulk import LISTING_URL, ProductionWorkbook
from .production import SenerProductionAdapter


@dataclass(frozen=True)
class ChainResult:
    checks: dict[str, str]
    fdas: FdasInputs | None
    html: str


def run_chain(
    observed: ProductionWorkbook,
    *,
    water_bbl: dict | None = None,
    basin: str | None = None,
    location: str | None = None,
) -> ChainResult:
    """Normalize observations, qualify FDAS inputs and render the remaining gaps.

    PASS qualifies only the named stage. Fiscal economics, forecasts and concept
    screening cannot be established from historical production alone.
    """
    bundle = None
    try:
        adapter = SenerProductionAdapter(observed, basin=basin, location=location)
        bundle = adapter.fdas_inputs(water_bbl=water_bbl)
        production_reason = "Complete oil, gas and caller-supplied water volumes."
    except ValueError as exc:
        production_reason = str(exc)
    checks = {
        "production": "PASS",
        "fdas_inputs": "PASS" if bundle else "NOT_EVALUATED",
        "freshness": "NOT_EVALUATED",
        "concept_screening": "NOT_EVALUATED",
        "economics": "NOT_EVALUATED",
    }
    reasons = {
        "production": "Workbook schema and units are validated; missing values are retained.",
        "fdas_inputs": production_reason,
        "freshness": "Source vintage is retained; no current-use freshness criterion is supplied.",
        "concept_screening": "Water depth, reserves and development metadata are required.",
        "economics": "A sourced Mexico contract fiscal deck, forecast, prices and costs are required."
        " The shared fiscal engine does not establish complete Mexico taxation.",
    }
    return ChainResult(checks, bundle, _render_report(observed, checks, reasons))


def _render_report(observed, checks, reasons):
    rows = "".join(
        f"<tr><td>{escape(stage)}</td><td>{status}</td>"
        f"<td>{escape(reasons[stage])}</td></tr>"
        for stage, status in checks.items()
    )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        "<title>Mexico production chain analysis</title><body>"
        "<h1>Mexico production chain analysis</h1><h2>Summary</h2>"
        f"<p>Source vintage: {escape(observed.vintage)}. "
        "Historical production is normalized; economic viability is not established.</p>"
        "<h2>Revision history</h2><table><tr><th>Revision</th><th>Date</th><th>Basis</th></tr>"
        f"<tr><td>Initial</td><td>{date.today().isoformat()}</td>"
        "<td>Readiness from supplied workbook observations.</td></tr></table>"
        "<p>Table 1. Report issue and basis.</p>"
        "<h2>Criteria and results</h2><table><tr><th>Stage</th><th>Result</th>"
        f"<th>Criterion or missing evidence</th></tr>{rows}</table>"
        "<p>Table 2. A stage passes only its stated input criterion.</p>"
        "<h2>Method and provenance</h2><p>Monthly volume = average daily rate "
        "× unit multiplier × calendar days. Oil excludes condensate; gas excludes nitrogen. "
        "Water is unavailable unless explicitly supplied.</p>"
        f"<p>Workbook SHA-256: <code>{escape(observed.sha256)}</code>.</p>"
        f'<p><a href="{LISTING_URL}">SENER field-production source</a>.</p>'
        "<p>Way forward: obtain the missing inputs and qualify source freshness "
        "before economic or concept-screening use.</p></body></html>"
    )
    return html
