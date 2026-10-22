"""Compact self-contained vector report; no external runtime or assets."""

from __future__ import annotations

import base64
import html
import json
from datetime import datetime, timezone
from importlib import metadata

import numpy as np


def _svg_image(svg, label):
    encoded = base64.b64encode(svg.encode()).decode()
    return f'<img alt="{html.escape(label, quote=True)}" src="data:image/svg+xml;base64,{encoded}">'


def _fan_chart(frame):
    # Coordinates are presentation dimensions, not engineering coefficients.
    width, height, margin = 800, 300, 35
    scale = max(frame.p90.max(), 1)
    x = np.linspace(margin, width - margin, len(frame))

    def points(values):
        return " ".join(
            f"{a:.1f},{height-margin-v/scale*(height-2*margin):.1f}"
            for a, v in zip(x, values)
        )

    lower = points(frame.p10)
    upper = " ".join(reversed(points(frame.p90).split()))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">'
        f'<polygon points="{lower} {upper}" fill="lightblue"/>'
        f'<polyline points="{points(frame.p50)}" fill="none" stroke="navy"/>'
        f'<text x="{margin}" y="20">Month-end rate (bbl/month); upper scale {scale:.1f}</text>'
        f'<text x="{margin}" y="{height-5}">Month 1</text>'
        f'<text x="{width-100}" y="{height-5}">Month {len(frame)}</text></svg>'
    )
    return _svg_image(svg, "Production fan: p10 to p90 shaded, p50 line")


def _tornado(ranks):
    rows = sorted(ranks.items(), key=lambda pair: abs(pair[1] or 0), reverse=True)
    height = max(70, 35 * len(rows) + 40)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 {height}">',
        f'<path d="M400 0 V{height}" stroke="black"/>',
    ]
    for i, (name, rho) in enumerate(rows):
        y = 30 + i * 35
        length = abs(rho or 0) * 250
        x = 400 if (rho or 0) >= 0 else 400 - length
        svg.append(
            f'<rect x="{x:.1f}" y="{y-15}" width="{length:.1f}" height="20" fill="steelblue"/>'
        )
        value = "undefined (constant)" if rho is None else f"{rho:.1f}"
        svg.append(f'<text x="5" y="{y}">{html.escape(name)}: {value}</text>')
    return _svg_image("".join(svg) + "</svg>", "NPV sensitivity: signed Spearman rho")


def _histogram(values):
    # NumPy histogram bins='auto' is a plotting choice, not a screening limit.
    counts, edges = np.histogram(values, bins="auto")
    peak = max(counts.max(), 1)
    width = 700 / len(counts)
    bars = "".join(
        f'<rect x="{50+i*width:.1f}" y="{250-count/peak*200:.1f}" '
        f'width="{width:.1f}" height="{count/peak*200:.1f}" fill="steelblue"/>'
        for i, count in enumerate(counts)
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 300">{bars}'
        f'<text x="50" y="20">Samples per bin; upper scale {peak}</text>'
        f'<text x="50" y="285">NPV (USD): {edges[0]:,.1f} to {edges[-1]:,.1f}</text></svg>'
    )
    return _svg_image(svg, "NPV histogram")


def build_report_html(result):
    """Render the result and input echo without paths or external resources."""
    try:
        package_version = metadata.version("worldenergydata-production")
    except metadata.PackageNotFoundError:
        package_version = "source tree (metadata unavailable)"

    summary = result.summary
    now = datetime.now(timezone.utc).date().isoformat()
    scalars = "".join(
        f"<tr><th>{name}</th>"
        + "".join(
            f"<td>{summary[name][key]:,.1f}</td>" for key in ("p10", "p50", "p90")
        )
        + "</tr>"
        for name in ("eur_bbl", "npv_usd")
    )
    echo = html.escape(json.dumps(result.config_echo, indent=2))
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>Probabilistic production analysis</title>
<style>body{{font:16px sans-serif;max-width:960px;margin:2em auto;padding:1em}}
img{{width:100%}}td,th{{padding:.5em;border:1px solid gray}}pre{{white-space:pre-wrap}}</style>
<h1>Probabilistic production analysis — {html.escape(summary['field'])}</h1>
<p>Data basis: {html.escape(summary['data_basis'])}; screening: {summary['screening_status']}.
Criterion: {html.escape(summary['screening_rule'])}. EUR is future recovery to the rate limit,
not booked reserves. NPV covers the configured horizon only.</p>
<h2>Revision history</h2><table><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr>
<tr><td>1</td><td>{now}</td><td>Initial configured uncertainty example.</td></tr></table>
<h2>Production fan</h2>{_fan_chart(result.fan)}
<p>Figure 1. Month-end rates (bbl/month); p10–p90 band and p50 line.</p>
<p>Non-exceedance convention: p10 is the 10th percentile (low), p90 the 90th (high).
These labels are reversed relative to petroleum exceedance probabilities.
Pointwise bands do not form a single realizable production trajectory.</p>
<table><tr><th>Quantity</th><th>p10</th><th>p50</th><th>p90</th></tr>{scalars}</table>
<p>Table 1. Future recovery (bbl) and horizon NPV (USD), linear empirical percentiles.</p>
<h2>NPV distribution</h2>{_histogram(result.run_matrix.npv_usd)}
<p>Figure 2. Horizon NPV histogram (USD); counts reflect configured samples.</p>
<h2>NPV sensitivity</h2>{_tornado(summary['spearman'])}
<p>Figure 3. Spearman rho, sorted by absolute value; association is not causation.
Undefined ranks identify constant inputs or outputs.</p>
<h2>Inputs and provenance</h2><pre>{echo}</pre>
<p>Input SHA-256: {summary['input_sha256']}; backend: {result.sampler_used};
package version: {html.escape(package_version)}; generated: {now} (UTC).
Methods: ArpsDeclineCurve.simulate, ProbabilisticForecast.run and EconomicsQuery.npv.</p>
<h2>Method and sources</h2>
<p>Arps rate and cumulative equations: <a href="https://resinsight.org/plot-window/declinecurveanalysis/">ResInsight Decline Curve Analysis</a> (accessed 2026).
Exact monthly volumes are integrated to the rate limit, including partial months.
Time-zero CAPEX and month-end net operating cash are discounted through FDAS;
<a href="https://github.com/numpy/numpy-financial/blob/v1.0.0/numpy_financial/_financial.py#L712-L789">numpy-financial 1.0.0, npv function and Notes</a>.
Percentiles use <a href="https://numpy.org/doc/2.2/reference/generated/numpy.percentile.html">NumPy 2.2 linear percentiles</a>;
ranks use <a href="https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.stats.spearmanr.html">SciPy 1.15.2 Spearman correlation</a>.</p>
<h2>Limits and way forward</h2><p>Independent priors; empirical decline with no pressure,
facility constraints, tax, royalties, fixed operating costs or terminal value.
Synthetic inputs do not establish public-field reserve distributions. Calibrated public
production data, documented priors and a governing acceptance criterion are required
before field screening. No reserve classification is established. Charts are static vectors.</p></html>"""
