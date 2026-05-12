#!/usr/bin/env python3
"""Generate the hurricane mooring risk-avoidance infographic artifacts.

The generator intentionally treats the marine-safety CSVs as pathway evidence, not
as a hurricane-only incident sample. It writes a self-contained HTML artifact and
an auditable JSON sidecar with matched incident IDs for every headline bucket.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "modules" / "marine_safety" / "input"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "reports" / "modules" / "marketing"
DEFAULT_DOCX_PATH = Path("/home/vamsee/Downloads/Hurricane Planning and Mooring R0-4revisions.docx")

OUTPUT_HTML_NAME = "hurricane_mooring_risk_avoidance_infographic.html"
OUTPUT_STATS_NAME = "hurricane_mooring_risk_avoidance_infographic_stats.json"

PRIOR_HTML_NAME = "hurricane_mooring_safety_infographic.html"
PRIOR_STATS_NAME = "hurricane_mooring_safety_infographic_stats.json"
REFERENCE_HTML_NAME = "reference_hurricane_mooring_safety_infographic_prior_draft.html"
REFERENCE_STATS_NAME = "reference_hurricane_mooring_safety_infographic_prior_draft_stats.json"

CAVEAT = (
    "These marine-safety records show incident pathways relevant to hurricane mooring readiness. "
    "They are not a hurricane-only or hurricane-caused incident sample."
)

WEATHER_WATER_KEYWORDS = {
    "exposure": ["rough seas", "heavy seas", "heavy weather", "severe weather", "rough weather"],
    "storm": ["storm", "typhoon", "rogue wave", "weather"],
    "water_ingress": ["water ingress", "flooding", "sank", "capsized", "foundered", "founder"],
    "overboard": ["overboard", "drowned", "drowning"],
}
CONTROL_TERMS = [
    "successfully",
    "successful",
    "verified secure",
    "avoid severe storm",
    "without incident",
    "no safety incidents",
    "all safety checks passed",
]


def _rel(path: Path) -> str:
    """Return repo-relative POSIX path when possible."""

    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def _read_csv(path: Path, dataset: str) -> list[dict[str, Any]]:
    """Read source CSV rows and tag each row with provenance fields."""

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["dataset"] = dataset
        row["source_file"] = path.name
        row["source_path"] = _rel(path)
        if "fatalities" in row:
            row["fatalities"] = int(row.get("fatalities") or 0)
    return rows


def load_incident_sources(input_dir: Path = DEFAULT_INPUT_DIR) -> dict[str, list[dict[str, Any]]]:
    """Load the three marine-safety source CSVs used by the infographic."""

    input_dir = Path(input_dir)
    return {
        "fatality": _read_csv(input_dir / "fatality_incidents.csv", "fatality"),
        "foundering": _read_csv(input_dir / "foundering_incidents.csv", "foundering"),
        "hatch": _read_csv(input_dir / "hatch_incidents.csv", "hatch"),
    }


def _matches_weather_or_water(row: dict[str, Any]) -> tuple[bool, str | None]:
    """Classify direct weather/water exposure while excluding controls."""

    text = " ".join(
        str(row.get(field, ""))
        for field in ("description", "cause_of_death", "severity")
    ).lower()
    if str(row.get("severity", "")).lower() == "none":
        return False, "control"
    if any(term in text for term in CONTROL_TERMS):
        return False, "control"
    for group, terms in WEATHER_WATER_KEYWORDS.items():
        if any(term in text for term in terms):
            return True, group
    return False, None


def _evidence_rows(rows: list[dict[str, Any]], ids: list[str]) -> list[dict[str, str | int]]:
    """Build compact source-row evidence for HTML details and JSON auditability."""

    lookup = {row["incident_id"]: row for row in rows}
    evidence: list[dict[str, str | int]] = []
    for incident_id in ids:
        row = lookup[incident_id]
        evidence.append(
            {
                "incident_id": row["incident_id"],
                "dataset": row["dataset"],
                "vessel_name": row["vessel_name"],
                "description": row["description"],
                "source_file": row["source_file"],
                "fatalities": row.get("fatalities", ""),
                "severity": row.get("severity", ""),
            }
        )
    return evidence


def build_stats(input_dir: Path = DEFAULT_INPUT_DIR, docx_path: Path = DEFAULT_DOCX_PATH) -> dict[str, Any]:
    """Recompute all infographic statistics from source CSVs."""

    sources = load_incident_sources(Path(input_dir))
    fatality_rows = sources["fatality"]
    foundering_rows = sources["foundering"]
    hatch_rows = sources["hatch"]
    all_rows = fatality_rows + foundering_rows + hatch_rows

    hatch_controls = [row for row in hatch_rows if str(row.get("severity", "")).lower() == "none"]
    hatch_events = [row for row in hatch_rows if row not in hatch_controls]
    critical_high_hatch_events = [row for row in hatch_events if row.get("severity") in {"Critical", "High"}]

    weather_rows: list[dict[str, Any]] = []
    keyword_groups: dict[str, list[str]] = {group: [] for group in WEATHER_WATER_KEYWORDS}
    preventive_or_control_rows: list[str] = []
    for row in fatality_rows + foundering_rows + hatch_events + hatch_controls:
        matches, group = _matches_weather_or_water(row)
        if matches and group:
            weather_rows.append(row)
            keyword_groups[group].append(row["incident_id"])
        elif group == "control":
            preventive_or_control_rows.append(row["incident_id"])

    weather_fatalities = sum(int(row.get("fatalities") or 0) for row in weather_rows)
    source_paths = [
        Path(input_dir) / "fatality_incidents.csv",
        Path(input_dir) / "foundering_incidents.csv",
        Path(input_dir) / "hatch_incidents.csv",
    ]

    generated_utc = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    stats: dict[str, Any] = {
        "generated_utc": generated_utc,
        "issue": "https://github.com/vamseeachanta/worldenergydata/issues/403",
        "source_files": [_rel(path) for path in source_paths],
        "document_provenance": {
            "filename": Path(docx_path).name,
            "path_role": "external user-provided DOCX; filename cited, original document not committed",
            "themes": [
                "hurricane preparation planning",
                "mooring analysis with dock geometry, bollards, bulkheads, and fenders",
                "storm surge plus changing wind, wave, and current directions",
                "port/refuge decision trees by storm severity and track proximity",
                "crew readiness and pre-season survivability checks",
            ],
        },
        "caveat": CAVEAT,
        "dataset_total_records": len(all_rows),
        "dataset_total_fatalities": sum(int(row.get("fatalities") or 0) for row in fatality_rows + foundering_rows),
        "source_row_counts": {
            "fatality_incidents.csv": len(fatality_rows),
            "foundering_incidents.csv": len(foundering_rows),
            "hatch_incidents.csv": len(hatch_rows),
        },
        "source_fatality_sums": {
            "fatality_incidents.csv": sum(int(row.get("fatalities") or 0) for row in fatality_rows),
            "foundering_incidents.csv": sum(int(row.get("fatalities") or 0) for row in foundering_rows),
        },
        "foundering_pathway_records": len(foundering_rows),
        "foundering_pathway_fatalities": sum(int(row.get("fatalities") or 0) for row in foundering_rows),
        "hatch_watertight_event_records": len(hatch_events),
        "hatch_control_records": len(hatch_controls),
        "critical_high_hatch_events": len(critical_high_hatch_events),
        "critical_high_hatch_event_pct": round(len(critical_high_hatch_events) / len(hatch_events) * 100, 1),
        "critical_high_hatch_all_hatch_pct": round(len(critical_high_hatch_events) / len(hatch_rows) * 100, 1),
        "direct_weather_or_water_exposure_events": len(weather_rows),
        "direct_weather_or_water_exposure_fatalities": weather_fatalities,
        "direct_weather_or_water_exposure_pct_of_event_records": round(
            len(weather_rows) / (len(fatality_rows) + len(foundering_rows) + len(hatch_events)) * 100,
            1,
        ),
        "hatch_severity_counts": dict(Counter(row["severity"] for row in hatch_rows)),
        "matched_incident_ids": {
            "foundering_pathway": [row["incident_id"] for row in foundering_rows],
            "hatch_watertight_events": [row["incident_id"] for row in hatch_events],
            "critical_high_hatch_events": [row["incident_id"] for row in critical_high_hatch_events],
            "direct_weather_or_water_exposure_events": [row["incident_id"] for row in weather_rows],
        },
        "excluded_incident_ids": {
            "hatch_controls": [row["incident_id"] for row in hatch_controls],
            "preventive_or_control_rows": sorted(set(preventive_or_control_rows)),
        },
        "keyword_group_matches": keyword_groups,
        "denominators": {
            "critical_high_hatch_event_pct": "12 critical/high hatch events / 20 hatch event rows excluding severity=None controls",
            "critical_high_hatch_all_hatch_pct": "12 critical/high hatch events / 30 all hatch CSV records including controls",
            "direct_weather_or_water_exposure_pct_of_event_records": (
                f"{len(weather_rows)} direct weather/water exposure events / "
                f"{len(fatality_rows) + len(foundering_rows) + len(hatch_events)} incident/event rows excluding hatch controls"
            ),
        },
        "evidence_rows": {
            "direct_weather_or_water_exposure_events": _evidence_rows(all_rows, [row["incident_id"] for row in weather_rows]),
            "critical_high_hatch_events": _evidence_rows(all_rows, [row["incident_id"] for row in critical_high_hatch_events]),
            "foundering_pathway": _evidence_rows(all_rows, [row["incident_id"] for row in foundering_rows]),
        },
    }
    return stats


def _repo_relative_from_absolute_text(value: str) -> str:
    """Sanitize known absolute workspace paths from prior draft metadata."""

    marker = "/worldenergydata/"
    if marker in value:
        return value.split(marker, 1)[1]
    return value


def _sanitize_reference_stats(reference_stats: Path) -> None:
    """Remove local absolute paths from preserved prior-draft stats JSON."""

    if not reference_stats.exists():
        return
    try:
        payload = json.loads(reference_stats.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    changed = False
    if isinstance(payload.get("output"), str):
        sanitized = _repo_relative_from_absolute_text(payload["output"])
        changed = changed or sanitized != payload["output"]
        payload["output"] = sanitized
    if isinstance(payload.get("source_files"), list):
        source_files = []
        for source in payload["source_files"]:
            sanitized = _repo_relative_from_absolute_text(str(source))
            changed = changed or sanitized != source
            source_files.append(sanitized)
        payload["source_files"] = source_files
    if changed:
        payload["reference_note"] = (
            "Prior draft stats preserved for comparison; local absolute paths were sanitized to repo-relative paths."
        )
        reference_stats.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def preserve_prior_draft(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, str | None]:
    """Move prior HTML/JSON drafts to reference names, idempotently.

    PNG/PDF exports are intentionally not copied or renamed here. They are binary
    artifacts and remain policy-gated for explicit approval. Prior-draft JSON is
    sanitized if it contains local absolute paths.
    """

    output_dir = Path(output_dir)
    prior_html = output_dir / PRIOR_HTML_NAME
    prior_stats = output_dir / PRIOR_STATS_NAME
    reference_html = output_dir / REFERENCE_HTML_NAME
    reference_stats = output_dir / REFERENCE_STATS_NAME

    if not reference_html.exists() and prior_html.exists():
        prior_html.rename(reference_html)
    if not reference_stats.exists() and prior_stats.exists():
        prior_stats.rename(reference_stats)
    _sanitize_reference_stats(reference_stats)

    return {
        "preserved_html": str(reference_html) if reference_html.exists() else None,
        "preserved_stats": str(reference_stats) if reference_stats.exists() else None,
        "binary_exports": "skipped",
    }


def _stat_tile(value: str | int | float, label: str, sublabel: str) -> str:
    return f"""
      <article class=\"stat-card\">
        <div class=\"stat-value\">{escape(str(value))}</div>
        <div class=\"stat-label\">{escape(label)}</div>
        <p>{escape(sublabel)}</p>
      </article>
    """


def _evidence_details(title: str, rows: list[dict[str, Any]]) -> str:
    items = []
    for row in rows:
        tail = []
        if row.get("fatalities") != "":
            tail.append(f"fatalities={row['fatalities']}")
        if row.get("severity"):
            tail.append(f"severity={row['severity']}")
        items.append(
            "<li>"
            f"<strong>{escape(str(row['incident_id']))}</strong> — "
            f"{escape(str(row['vessel_name']))}: {escape(str(row['description']))} "
            f"<span>({escape(str(row['source_file']))}; {escape(', '.join(tail))})</span>"
            "</li>"
        )
    return f"""
      <details class=\"evidence\">
        <summary>{escape(title)} ({len(rows)} rows)</summary>
        <ul>{''.join(items)}</ul>
      </details>
    """


def render_html(stats: dict[str, Any]) -> str:
    """Render a self-contained stakeholder-facing HTML infographic."""

    severity = stats["hatch_severity_counts"]
    source_list = "".join(f"<li>{escape(path)}</li>" for path in stats["source_files"])
    controls = ", ".join(stats["excluded_incident_ids"]["hatch_controls"])
    keyword_groups = "".join(
        f"<li><strong>{escape(group.replace('_', ' ').title())}</strong>: {escape(', '.join(ids) or 'none')}</li>"
        for group, ids in stats["keyword_group_matches"].items()
    )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Hurricane Mooring Risk Avoidance Infographic</title>
  <style>
    :root {{ --navy:#081827; --blue:#1e88e5; --cyan:#67e8f9; --amber:#f59e0b; --red:#ef4444; --ink:#e5edf5; --muted:#9fb2c6; --panel:#10263b; --line:#28445e; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family: Inter, Segoe UI, Roboto, Arial, sans-serif; color:var(--ink); background: radial-gradient(circle at top left, #123a5a 0, var(--navy) 42%, #050b12 100%); }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 40px 24px 56px; }}
    .hero {{ border:1px solid var(--line); border-radius:28px; padding:36px; background:linear-gradient(135deg, rgba(30,136,229,.22), rgba(8,24,39,.9)); box-shadow:0 24px 80px rgba(0,0,0,.35); }}
    h1 {{ margin:0; max-width:920px; font-size: clamp(34px, 5vw, 68px); line-height:.95; letter-spacing:-.05em; }}
    h2 {{ margin:0 0 12px; font-size:30px; letter-spacing:-.03em; }}
    h3 {{ margin:0 0 8px; font-size:18px; }}
    p {{ color:var(--muted); line-height:1.55; }}
    .kicker {{ color:var(--cyan); text-transform:uppercase; letter-spacing:.18em; font-size:13px; font-weight:800; }}
    .caveat {{ margin-top:24px; border-left:5px solid var(--amber); padding:14px 18px; background:rgba(245,158,11,.11); color:#ffe3a7; border-radius:10px; }}
    .grid {{ display:grid; gap:18px; }}
    .stats {{ grid-template-columns: repeat(4, minmax(0, 1fr)); margin:24px 0; }}
    .stat-card, section {{ background:rgba(16,38,59,.82); border:1px solid var(--line); border-radius:22px; padding:22px; }}
    .stat-value {{ font-size:44px; line-height:1; font-weight:900; color:white; }}
    .stat-label {{ margin-top:8px; font-weight:800; color:var(--cyan); }}
    .two {{ grid-template-columns: 1.1fr .9fr; }}
    .bar {{ margin:12px 0 18px; }}
    .bar-label {{ display:flex; justify-content:space-between; color:#cfe4f9; font-weight:700; }}
    .track {{ height:15px; background:#07131f; border-radius:999px; overflow:hidden; border:1px solid var(--line); }}
    .fill {{ height:100%; background:linear-gradient(90deg, var(--blue), var(--cyan)); border-radius:999px; }}
    .decision {{ display:grid; grid-template-columns: repeat(3, 1fr); gap:14px; }}
    .node {{ border:1px solid var(--line); border-radius:18px; padding:16px; background:#0b1d2d; }}
    .node strong {{ display:block; color:#fff; margin-bottom:6px; }}
    .node.warn {{ border-color:rgba(239,68,68,.55); }}
    .node.go {{ border-color:rgba(103,232,249,.55); }}
    details {{ margin-top:14px; border:1px solid var(--line); border-radius:16px; padding:14px 16px; background:#0a1724; }}
    summary {{ cursor:pointer; color:var(--cyan); font-weight:800; }}
    li {{ margin:7px 0; color:#c9d8e8; }}
    footer {{ margin-top:24px; color:var(--muted); font-size:13px; }}
    code {{ color:#dbeafe; }}
    @media (max-width: 900px) {{ .stats, .two, .decision {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <div class=\"hero\">
    <div class=\"kicker\">Marine safety incident pathways → hurricane readiness controls</div>
    <h1>Hurricane mooring analysis turns marine incident pathways into avoidable planning decisions.</h1>
    <p>The source document calls for hurricane preparation before the storm: mooring analysis, dock-side geometry, bollard and fender capacity, surge exposure, changing wind/wave/current directions, crew readiness, and a port/refuge decision tree. The incident data below quantifies pathways that the planning process is designed to avoid.</p>
    <div class=\"caveat\"><strong>Dataset caveat:</strong> {escape(stats['caveat'])}</div>
  </div>

  <div class=\"grid stats\">
    {_stat_tile(stats['dataset_total_records'], 'source CSV records', '20 fatality rows + 15 foundering rows + 30 hatch/watertight rows')}
    {_stat_tile(stats['dataset_total_fatalities'], 'fatalities represented', 'From fatality and foundering CSV fatality fields')}
    {_stat_tile(stats['foundering_pathway_records'], 'foundering pathway records', f"{stats['foundering_pathway_fatalities']} fatalities in loss-of-vessel pathway rows")}
    {_stat_tile(stats['critical_high_hatch_events'], 'critical/high hatch events', stats['denominators']['critical_high_hatch_event_pct'])}
  </div>

  <div class=\"grid two\">
    <section>
      <h2>Statistics that support the risk story</h2>
      <div class=\"bar\"><div class=\"bar-label\"><span>Direct weather/water exposure events</span><span>{stats['direct_weather_or_water_exposure_events']} / 55 event rows</span></div><div class=\"track\"><div class=\"fill\" style=\"width:{stats['direct_weather_or_water_exposure_pct_of_event_records']}%\"></div></div><p>{escape(stats['denominators']['direct_weather_or_water_exposure_pct_of_event_records'])}; {stats['direct_weather_or_water_exposure_fatalities']} fatalities in matched rows.</p></div>
      <div class=\"bar\"><div class=\"bar-label\"><span>Critical/high hatch integrity events</span><span>{stats['critical_high_hatch_event_pct']}%</span></div><div class=\"track\"><div class=\"fill\" style=\"width:{stats['critical_high_hatch_event_pct']}%\"></div></div><p>{escape(stats['denominators']['critical_high_hatch_event_pct'])}; {escape(stats['denominators']['critical_high_hatch_all_hatch_pct'])}.</p></div>
      <p><strong>Severity counts:</strong> Critical {severity.get('Critical', 0)}, High {severity.get('High', 0)}, Medium {severity.get('Medium', 0)}, Low {severity.get('Low', 0)}, None/control {severity.get('None', 0)}.</p>
    </section>

    <section>
      <h2>Avoidable failure modes → planning controls</h2>
      <ul>
        <li><strong>Foundering / capsizing / sinking:</strong> verify storm-category survivability before choosing stay/relocate/refuge.</li>
        <li><strong>Flooding and water ingress:</strong> close hatch, door, ventilator, and access-cover weak points before surge and wave exposure.</li>
        <li><strong>Severe-weather exposure:</strong> use track proximity and forecast category thresholds to leave early enough.</li>
        <li><strong>Mooring operation exposure:</strong> reduce last-minute deck work through pre-planned line layout and crew readiness.</li>
      </ul>
      <p>Control rows excluded from incident counts include {escape(controls)}. NI010 is a positive/control row: weather routing helped avoid severe storm; it is not counted as a loss event.</p>
    </section>
  </div>

  <section style=\"margin-top:18px\">
    <h2>Port / refuge decision tree</h2>
    <p>This is the decision lever from the DOCX: convert site and vessel constraints into a category-by-category action rule before the hurricane season.</p>
    <div class=\"decision\">
      <div class=\"node go\"><strong>1. Pre-season engineering check</strong> Bollard, fender, and mooring-line capacity checks; bulkhead geometry; vessel particulars; survivability by storm category.</div>
      <div class=\"node\"><strong>2. Forecast trigger</strong> Track proximity, surge window, changing wind/current directions, port closure timing, and crew availability.</div>
      <div class=\"node warn\"><strong>3. Action before lock-in</strong> Stay with engineered mooring plan, shift berth, move to refuge, or evacuate before conditions make movement unsafe.</div>
    </div>
  </section>

  <section style=\"margin-top:18px\">
    <h2>Interactive evidence panels</h2>
    <p>Open each panel to audit the matched source rows behind the headline counts.</p>
    {_evidence_details('Direct weather/water exposure matched IDs', stats['evidence_rows']['direct_weather_or_water_exposure_events'])}
    {_evidence_details('Critical/high hatch and watertight integrity IDs', stats['evidence_rows']['critical_high_hatch_events'])}
    {_evidence_details('Foundering/loss-of-vessel pathway IDs', stats['evidence_rows']['foundering_pathway'])}
    <details class=\"evidence\"><summary>Keyword groups used for direct weather/water exposure</summary><ul>{keyword_groups}</ul></details>
  </section>

  <section style=\"margin-top:18px\">
    <h2>Provenance</h2>
    <p><strong>Generated UTC:</strong> {escape(stats['generated_utc'])}</p>
    <p><strong>DOCX reviewed:</strong> {escape(stats['document_provenance']['filename'])}</p>
    <p><strong>CSV sources:</strong></p>
    <ul>{source_list}</ul>
    <p><strong>Issue:</strong> <a style=\"color:var(--cyan)\" href=\"{escape(stats['issue'])}\">{escape(stats['issue'])}</a></p>
  </section>
  <footer>Default deliverables are HTML + JSON only. PNG/PDF exports are intentionally policy-gated to avoid duplicate binary artifact growth.</footer>
</main>
</body>
</html>
"""


def generate_artifacts(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    input_dir: Path = DEFAULT_INPUT_DIR,
    docx_path: Path = DEFAULT_DOCX_PATH,
) -> dict[str, Any]:
    """Generate stats JSON and self-contained HTML into *output_dir*."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    preservation = preserve_prior_draft(output_dir)
    stats = build_stats(Path(input_dir), Path(docx_path))
    html = render_html(stats)

    stats_path = output_dir / OUTPUT_STATS_NAME
    html_path = output_dir / OUTPUT_HTML_NAME
    stats_path.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")

    return {
        "html_path": html_path,
        "stats_path": stats_path,
        "binary_exports": preservation["binary_exports"],
        "preservation": preservation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--docx-path", type=Path, default=DEFAULT_DOCX_PATH)
    args = parser.parse_args()

    result = generate_artifacts(output_dir=args.output_dir, input_dir=args.input_dir, docx_path=args.docx_path)
    print(json.dumps({key: str(value) for key, value in result.items() if key.endswith("_path")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
