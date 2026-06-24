# ABOUTME: Renders an HSE grounding as a self-contained HTML card for client-facing demos.
# ABOUTME: Pairs an engineering analysis result with real-world precedent incidents + vintage.

"""Grounding card renderer.

Turns a :class:`~worldenergydata.hse.grounding.Grounding` plus a short engineering
analysis summary into one self-contained HTML card — the client-facing artifact
of the grounded-analysis demo stream (epic #486): an engineering result, then the
real-world incidents that ground it, then a data-vintage trust stamp.

Per HTML_REPORTING_STANDARDS the card carries an interactive Plotly timeline of
the precedent incidents (hover = description/location/severity). The card is
pure: no network, no session state; it takes the grounding dict
(``Grounding.to_dict()``) and an :class:`AnalysisSummary`.

Operator Aggregation Contract (#423): the grounding cites lease blocks + dates,
never operator names — enforced upstream in ``grounding.py`` and tested here.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


@dataclass
class AnalysisSummary:
    """The engineering result the grounding is attached to.

    Values are populated from a real digitalmodel run when wired; for the demo
    they come from the mooring_fatigue workflow (parametric pilot dm#796) and
    are labelled accordingly via ``basis``.
    """

    title: str
    headline: str  # one-line result, e.g. "Min fatigue life 18.4 yr at fairlead"
    metrics: list[tuple[str, str]] = field(default_factory=list)  # (label, value)
    method: str = ""
    basis: str = ""  # provenance/attribution for the analysis numbers


_SEVERITY_COLOR = {
    "fatality": "#7f1d1d",
    "catastrophic": "#b91c1c",
    "lost_time": "#c2410c",
    "environmental": "#a16207",
    "injury": "#b45309",
    "property_>$25k": "#1d4ed8",
    "minor": "#475569",
}


def _esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def _incident_li(i: dict) -> str:
    color = _SEVERITY_COLOR.get(i["severity"], "#475569")
    return (
        '<li class="incident">'
        f'<span class="date">{_esc(i["date"])}</span>'
        f'<span class="badge" style="background:{color}">{_esc(i["severity"])}</span>'
        f'<span class="loc">{_esc(i["location"])}</span>'
        f'<span class="desc">{_esc(i["description"])}</span>'
        f'<span class="src">{_esc(i["source"])}</span>'
        "</li>"
    )


def _timeline_traces(grounding: dict) -> str:
    """Build the Plotly data array (JSON) for the incident timeline."""

    def pts(items, name, symbol):
        return {
            "x": [i["date"] for i in items],
            "y": [i["severity_rank"] for i in items],
            "text": [
                f"{i['date']} · {i['location']}<br>{i['description']}<br>"
                f"<b>{i['severity']}</b> ({i['source']})"
                for i in items
            ],
            "mode": "markers",
            "name": name,
            "type": "scatter",
            "marker": {
                "size": 16,
                "symbol": symbol,
                "color": [_SEVERITY_COLOR.get(i["severity"], "#475569") for i in items],
                "line": {"width": 1.5, "color": "#1e293b"},
            },
            "hovertemplate": "%{text}<extra></extra>",
        }

    data = [
        pts(grounding["latest_2"], "Latest on record", "circle"),
        pts(grounding["most_severe_2"], "Highest-consequence", "diamond"),
    ]
    return json.dumps(data)


def render_html(
    grounding: dict,
    analysis: AnalysisSummary,
    generated_on: str,
    *,
    data_source: str = "BSEE incident investigations (data.bsee.gov), public record",
) -> str:
    """Render the grounding + analysis as one self-contained HTML document."""
    latest = "".join(_incident_li(i) for i in grounding["latest_2"])
    severe = "".join(_incident_li(i) for i in grounding["most_severe_2"])
    metrics = "".join(
        f'<div class="metric"><div class="m-val">{_esc(v)}</div>'
        f'<div class="m-lab">{_esc(k)}</div></div>'
        for k, v in analysis.metrics
    )
    vintage = grounding.get("vintage_note", "")
    traces = _timeline_traces(grounding)
    sep = " · " if analysis.method and analysis.basis else ""
    basis_line = f"{_esc(analysis.method)}{sep}{_esc(analysis.basis)}"

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(analysis.title)} — Grounded Analysis</title>
<script src="{PLOTLY_CDN}"></script>
<style>
  :root {{ --ink:#0f172a; --muted:#475569; --line:#e2e8f0; --accent:#0b5394; }}
  * {{ box-sizing:border-box; }}
  body {{ font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); margin:0; background:#f8fafc; }}
  .card {{ max-width:880px; margin:24px auto; background:#fff; border:1px solid var(--line);
          border-radius:12px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,.06); }}
  header {{ padding:20px 24px; background:var(--accent); color:#fff; }}
  header h1 {{ margin:0; font-size:20px; }}
  header p {{ margin:4px 0 0; opacity:.9; font-size:13px; }}
  section {{ padding:18px 24px; border-top:1px solid var(--line); }}
  section h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.04em;
               color:var(--muted); margin:0 0 12px; }}
  .headline {{ font-size:17px; font-weight:600; margin:0 0 12px; }}
  .metrics {{ display:flex; gap:18px; flex-wrap:wrap; }}
  .metric {{ background:#f1f5f9; border-radius:8px; padding:10px 14px; min-width:120px; }}
  .m-val {{ font-size:18px; font-weight:700; color:var(--accent); }}
  .m-lab {{ font-size:12px; color:var(--muted); }}
  .basis {{ font-size:12px; color:var(--muted); margin-top:10px; }}
  ul.incidents {{ list-style:none; margin:0; padding:0; }}
  li.incident {{ display:grid; grid-template-columns:92px 110px 1fr; gap:6px 12px;
                align-items:baseline; padding:10px 0; border-bottom:1px dashed var(--line); }}
  li.incident:last-child {{ border-bottom:none; }}
  .date {{ font-variant-numeric:tabular-nums; font-weight:600; }}
  .badge {{ color:#fff; font-size:11px; padding:2px 8px; border-radius:10px; text-align:center;
           justify-self:start; }}
  .loc {{ grid-column:3; font-weight:600; }}
  .desc {{ grid-column:3; color:var(--ink); }}
  .src {{ grid-column:3; font-size:12px; color:var(--muted); }}
  #timeline {{ width:100%; height:300px; }}
  footer {{ padding:14px 24px; background:#f1f5f9; font-size:12px; color:var(--muted); }}
  footer .vintage {{ font-weight:600; color:var(--ink); }}
</style></head>
<body><div class="card">
  <header>
    <h1>{_esc(analysis.title)}</h1>
    <p>Engineering analysis, grounded in real-world precedent</p>
  </header>

  <section>
    <h2>Engineering result</h2>
    <p class="headline">{_esc(analysis.headline)}</p>
    <div class="metrics">{metrics}</div>
    <p class="basis">{basis_line}</p>
  </section>

  <section>
    <h2>Real-world precedent — {_esc(grounding["failure_mode"])}</h2>
    <div id="timeline"></div>
    <p style="font-size:13px;color:var(--muted);margin:.5em 0 0">
      Latest on record (circles) and highest-consequence on record (diamonds). Hover for detail.</p>
  </section>

  <section>
    <h2>Latest on record</h2>
    <ul class="incidents">{latest}</ul>
  </section>

  <section>
    <h2>Highest-consequence on record</h2>
    <ul class="incidents">{severe}</ul>
  </section>

  <footer>
    <div class="vintage">Data vintage: {_esc(vintage)}.</div>
    Source: {_esc(data_source)}. Incidents are cited by area block + lease and date only —
    no operator names (aggregation policy). Generated {_esc(generated_on)}.
  </footer>
</div>
<script>
  Plotly.newPlot("timeline", {traces}, {{
    margin:{{t:10,r:10,b:36,l:44}},
    xaxis:{{title:"Incident date", type:"date"}},
    yaxis:{{title:"Severity rank", range:[0,105]}},
    legend:{{orientation:"h", y:1.15}},
    hoverlabel:{{align:"left"}},
    plot_bgcolor:"#fff", paper_bgcolor:"#fff"
  }}, {{displaylogo:false, responsive:true}});
</script>
</body></html>"""
