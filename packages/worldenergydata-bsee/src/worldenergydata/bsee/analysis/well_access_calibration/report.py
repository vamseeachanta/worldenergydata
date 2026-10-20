"""Self-contained calibration evidence, without external scripts or assets."""

from html import escape

import yaml


def _display(value):
    """Round report evidence only; machine-readable YAML retains precision."""
    if isinstance(value, float):
        return format(value, ".4g")
    if isinstance(value, dict):
        return {key: _display(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_display(item) for item in value]
    return value


def render_html(result):
    """Render verdicts, rate tables and a rounded evidence echo offline."""
    rows = "".join(
        f'<tr><td>{escape(kind)}</td><td>{escape(spec["status"])}</td>'
        f'<td>{spec["event_count"]}</td></tr>'
        for kind, spec in result["diagnostics"].items()
        if isinstance(spec, dict)
    )
    evidence = escape(yaml.safe_dump(_display(result), sort_keys=True))
    rate_rows = "".join(
        f"<tr><td>{escape(kind)}</td><td>{band['age_min_yr']:.1f}</td>"
        f"<td>{band['age_max_yr']:.1f}</td>"
        f"<td>{band['rate_per_well_year']:.4g}</td>"
        f"<td>{spec['duration_days']:.1f}</td></tr>"
        for kind, spec in result["base_rates"].items()
        for band in spec["age_curve"]
    )
    availability = result["uptime"]["facility_availability_suggested"]
    # Percent is the defining conversion of a dimensionless fraction.
    availability_text = (
        f"{availability:.1%}" if availability is not None else "NOT_EVALUATED"
    )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        "<title>Well-access calibration analysis</title>"
        "<style>body{font:1rem sans-serif;max-width:70rem;margin:auto;padding:2rem}"
        "td,th{padding:.5rem;text-align:left}pre{white-space:pre-wrap}</style>"
        "<h1>Well-access calibration analysis</h1><h2>Summary</h2>"
        "<p>Observed intervention rates and production availability proxy. "
        "Missing evidence remains NOT_EVALUATED. Review coverage and analog "
        "selection before using the result for demand forecasts.</p>"
        "<h2>Revision history</h2><table><tr><th>Revision</th><th>Date</th>"
        "<th>Change and reason</th></tr><tr><td>Initial</td><td>2026-10-19</td>"
        "<td>Initial report format for the stated evidence.</td></tr></table>"
        "<h2>Screening results</h2><table><tr><th>Type</th><th>Status</th>"
        f"<th>Events</th></tr>{rows}</table><h2>Rates and durations</h2>"
        "<p>Rate = event starts / observed well-years in the age band. "
        "Duration = median complete event report-days.</p>"
        "<table><tr><th>Type</th><th>Age from (years)</th><th>Age to (years)</th>"
        f"<th>Events per well-year</th><th>Duration (days)</th></tr>{rate_rows}</table>"
        f"<h2>Production availability proxy</h2><p>{availability_text}; "
        f"missing well-months: {result['uptime']['missing_well_months']}. "
        "Missing months are unknown; the scalar describes observed months only.</p>"
        "<h2>Inputs, method and answer</h2>"
        "<p>Display values use compact precision; the calibration YAML retains "
        "full computational precision.</p>"
        f"<pre>{evidence}</pre></html>\n"
    )
