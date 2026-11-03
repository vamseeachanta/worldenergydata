"""Offline worked example: source evidence -> issue gate -> qualified answer.

From the repository root, print the qualified answers:
    PYTHONPATH=src python examples/eu_tail_source_assessment.py

Rebuild the accompanying research note:
    PYTHONPATH=src python examples/eu_tail_source_assessment.py \
        --output-html docs/data/eu-tail-source-assessment.html

Inputs are the dated observations in docs/data/eu-tail-source-assessment.json.
No production values are downloaded, converted, or supplied to FDAS.
"""

import argparse
import json
from dataclasses import asdict
from html import escape
from pathlib import Path

from worldenergydata.source_assessment import SourceCapabilities, assess_source


def summarize(evidence_path: Path) -> dict:
    """Return one assessment per selected source, preserving independent rights."""
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    return {
        source["key"]: asdict(
            assess_source(SourceCapabilities(**source["capabilities"]))
        )
        for source in evidence["sources"]
    }


def _source_section(source: dict, result: dict) -> str:
    rows = "".join(
        f"<dt>{escape(label)}</dt><dd>{escape(str(source[key]))}</dd>"
        for key, label in (
            ("granularity", "Granularity"),
            ("access", "Access and format inspection"),
            ("temporal_coverage", "Temporal coverage"),
            ("spatial_coverage", "Spatial coverage"),
            ("update_frequency", "Update frequency and vintage"),
            ("licence", "Reuse terms"),
            ("source_units", "Units and qualification"),
            ("previous_decision", "Earlier decision"),
            ("comparison", "Comparison with earlier research"),
            ("next_step", "Next step"),
        )
    )
    limitations = "".join(f"<li>{escape(item)}</li>" for item in source["limitations"])
    observations = "".join(
        f'<li><a href="{escape(item["url"], quote=True)}">Publisher evidence</a>: '
        f'{escape(item["method"])}; HTTP {item["http_status"]}; '
        f'{escape(item["observed_at"])}; {escape(item["digest_scope"])}; '
        f'<code>sha256:{escape(item["sha256"])}</code>.</li>'
        for item in source["observations"]
    )
    historical = source.get("historical_evidence_url")
    if historical:
        observations += (
            f'<li><a href="{escape(historical, quote=True)}">Earlier issue research</a> '
            "supports the historical structure claim; it is not current payload validation.</li>"
        )
    return (
        f'<section id="{escape(source["key"], quote=True)}">'
        f'<h3>{escape(source["country"])} — {escape(source["publisher"])}</h3>'
        f'<p>{escape(source["title"])}</p>'
        f'<p>Data types: {escape(", ".join(source["data_types"]))}. '
        f'Formats: {escape(", ".join(source["formats"]))}.</p>'
        f'<p><strong>{escape(result["decision"])}</strong>: {escape(result["reason"])}</p>'
        f"<dl>{rows}</dl><h4>Limitations</h4><ul>{limitations}</ul>"
        f"<h4>Observation receipts</h4><ul>{observations}</ul></section>"
    )


def render_report(evidence_path: Path) -> str:
    """Render the evidence and gate results together, with escaped source text."""
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    results = summarize(evidence_path)
    table = "".join(
        f'<tr><th scope="row">{escape(source["country"])} / '
        f'{escape(source["publisher"])}</th>'
        + "".join(
            f"<td>{escape(results[source['key']][column])}</td>"
            for column in (
                "decision",
                "fdas_production",
                "field_concept",
                "raw_redistribution",
            )
        )
        + "</tr>"
        for source in evidence["sources"]
    )
    sections = "".join(
        _source_section(source, results[source["key"]])
        for source in evidence["sources"]
    )
    worked = escape(json.dumps(results, indent=2))
    return _report_frame(evidence, table, sections, worked)


def _report_frame(evidence: dict, table: str, sections: str, worked: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EU source granularity assessment</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 76rem; margin: auto; padding: 2rem;
 color: #172033; background: #fff; line-height: 1.6; }}
table {{ border-collapse: collapse; display: block; overflow-x: auto; }}
th, td {{ border: 1px solid #ccd3df; padding: .5rem; text-align: left; }}
caption {{ caption-side: bottom; text-align: left; }}
dt {{ font-weight: bold; }} dd {{ margin-bottom: .8rem; }}
code {{ overflow-wrap: anywhere; }} pre {{ overflow-x: auto; background: #f3f5f8; padding: 1rem; }}
section {{ border-top: 1px solid #ccd3df; margin-top: 2rem; }} a {{ color: #174c91; }}
</style></head><body><main>
<h1>EU source granularity assessment</h1>
<p>Assessment date: {escape(evidence['as_of'])}.
<a href="{escape(evidence['issue_url'], quote=True)}">Issue 753</a>.</p>
<h2>Summary</h2>
<p>The ISPRA indicator and the inspected DGEG pages remain coverage sources.
The Italian upstream CSV warrants concession-aware investigation, with field mapping
unresolved. CORES still publishes the production-workbook links, but the current
internal structure is not established by the HEAD-only check. Its existing chain is
retained; reproduction requires permission covering the intended use.</p>
<h2>Revision history</h2>
<table><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr>
<tr><td>{escape(evidence['revision'])}</td><td>{escape(evidence['as_of'])}</td>
<td>Publisher availability and terms are checked; structure evidence, concession mapping
and reuse are separated to prevent unsupported chain-readiness claims.</td></tr>
<caption>Table 1. Initial assessment issue.</caption></table>
<h2>Method</h2>
<p>{escape(evidence['criteria'])}</p>
<p>The Boolean gate is: verified field/well production OR verified usable field metadata.
A concession satisfies the production branch only with a verified field mapping.
Monthly FDAS fit additionally requires verified monthly resolution. These are logical
criteria from the linked issue, not engineering equations; no physical constants,
volume conversions, economic assumptions or numeric acceptance limits are introduced.</p>
<p>A PROMOTE disposition identifies a capability candidate. Adapter conformance,
full-data completeness, freshness, units and lawful intended use remain prerequisites.
NOT_EVALUATED exposes missing evidence; it does not mean a true zero or a country-wide
absence of production. ATTRIBUTION_REQUIRED describes the stated licence condition,
not a completed reuse-compliance check. No automated enrolment is performed.</p>
<table><thead><tr><th>Selected source</th><th>Chain decision</th><th>Monthly FDAS input</th>
<th>FieldConcept input</th><th>Raw redistribution</th></tr></thead><tbody>{table}</tbody>
<caption>Table 2. Dispositions for the inspected sources only.</caption></table>
<h2>Source characterization and evidence</h2>{sections}
<h2>Worked example: inputs, method and answer</h2>
<p>Input: <a href="eu-tail-source-assessment.json">the versioned capability flags and
publisher observations</a>. Method: SourceCapabilities is evaluated by assess_source;
rights are reported independently. Italy has verified monthly concession columns and
no verified field mapping, so the answer is REVIEW_MAPPING / REQUIRES_MAPPING.
Spain has only current HEAD evidence, so its current series is NOT_EVALUATED and its
raw reproduction remains PERMISSION_REQUIRED. ISPRA and DGEG evaluate to COVERAGE_ONLY.</p>
<p>Run from the repository root:</p>
<pre>PYTHONPATH=src python examples/eu_tail_source_assessment.py
PYTHONPATH=src python examples/eu_tail_source_assessment.py \\
    --output-html docs/data/eu-tail-source-assessment.html</pre>
<pre>{worked}</pre>
<h2>Retention and remaining work</h2>
<p>{escape(evidence['evidence_retention'])}</p>
<p>{escape(evidence['catalog_status'])}</p>
<p>Spain already has workbook discovery, parsers, a unified production adapter and a
reference chain. This assessment does not duplicate or alter those modules. Further
work consists of Italian full-CSV validation and title-to-field mapping, authorized
current CORES workbook inspection and intended-use permission, and Portuguese structured
map-layer inspection if field metadata is pursued. Pre-2004 Italian records and the
Portuguese price list are not evaluated. Independent review remains a prerequisite
before merge.</p>
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-html", type=Path)
    args = parser.parse_args()
    source_path = (
        Path(__file__).resolve().parents[1] / "docs/data/eu-tail-source-assessment.json"
    )
    if args.output_html:
        args.output_html.write_text(render_report(source_path), encoding="utf-8")
    else:
        print(json.dumps(summarize(source_path), indent=2))


if __name__ == "__main__":
    main()
