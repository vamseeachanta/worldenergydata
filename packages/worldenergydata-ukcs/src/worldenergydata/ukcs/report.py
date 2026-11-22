"""Self-contained UKCS reference-chain report; economics are pre-tax plumbing."""

from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[5]


def _json_safe(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _aware_timestamp(value):
    try:
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is not None
        )
    except (AttributeError, TypeError, ValueError):
        return False


def build_report_facts(
    chain_result,
    *,
    provenance="fixture",
    source_url,
    licence,
    refreshed_at=None,
    input_echo,
) -> dict:
    """Flatten chain objects without I/O; only the verified live loader may opt in.

    The router verifies cache-file evidence before passing ``nsta_live`` and its
    mtime. A missing timestamp, empty series or non-NSTA tag fails closed here.
    Missing/non-finite measurements remain null, never invented zero values.
    """
    frame = chain_result["unified_production"].sort_values(["year", "month"])
    live = (
        provenance == "nsta_live"
        and _aware_timestamp(refreshed_at)
        and not frame.empty
        and "source" in frame
        and frame["source"].eq("nsta").fillna(False).all()
    )
    history = [
        {
            "period": f"{int(row.year):04d}-{int(row.month):02d}",
            **{
                name: float(getattr(row, name))
                for name in ("oil_bbl", "gas_mcf", "water_bbl")
            },
        }
        for row in frame.itertuples(index=False)
    ]
    ranked = []
    for candidate in chain_result["ranked_concepts"]:
        parts = [candidate.concept_type, candidate.tree_type, candidate.topology]
        ranked.append(
            {
                "name": " / ".join(
                    str(_json_safe(part)) for part in parts if part is not None
                ),
                "total_score": float(candidate.total_score),
                "rationale": candidate.rationale,
                "warnings": candidate.warnings,
            }
        )
    concept = chain_result["field_concept"]
    facts = {
        "field_name": chain_result["field_name"],
        "field_concept": concept.model_dump(mode="json"),
        "production_history": history,
        "coverage": {
            "row_count": len(history),
            "first_period": history[0]["period"] if history else None,
            "last_period": history[-1]["period"] if history else None,
        },
        "ranked_concepts": ranked,
        "economics_label": chain_result["economics_label"],
        "cashflow_basis": chain_result.get("cashflow_basis"),
        "pre_tax_metrics": {
            key: float(value) for key, value in chain_result["pre_tax_metrics"].items()
        },
        "provenance": "nsta_live" if live else "fixture",
        "source": {
            "source_id": "uk-nsta-opendata",
            "url": source_url,
            "licence": licence,
            "refreshed_at": refreshed_at if live else None,
            "raw_bytes_retained_in_repository": False if live else None,
        },
        "units": {
            "oil_bbl": "bbl",
            "gas_mcf": "Mcf",
            "water_bbl": "bbl",
            "pre_tax_metrics": "USD except months",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_echo": input_echo,
    }
    return _json_safe(facts)


def _escape(value):
    return html.escape(str(value), quote=True)


def _display(value):
    return "Not established" if value is None else _escape(value)


def _table(headers, rows):
    return (
        "<table><thead><tr>"
        + "".join(f"<th>{_escape(h)}</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{_display(v)}</td>" for v in row) + "</tr>"
            for row in rows
        )
        + "</tbody></table>"
    )


def _production_svg(history):
    """Draw separate unit-labelled panels; unknown measurements break the line."""
    if not history:
        return "<p>No production observations are available.</p>"
    months = [int(row["period"][:4]) * 12 + int(row["period"][5:7]) for row in history]
    span = max(1, months[-1] - months[0])
    charts = []
    for key, title in (
        ("oil_bbl", "Oil (bbl)"),
        ("gas_mcf", "Gas (Mcf)"),
        ("water_bbl", "Water (bbl)"),
    ):
        values = [row[key] for row in history if row[key] is not None]
        maximum = max([0, *values]) or 1
        minimum = min([0, *values])
        paths, command = [], "M"
        for month, row in zip(months, history):
            if row[key] is None:
                command = "M"
                continue
            x = 70 + 610 * (month - months[0]) / span
            y = 120 - 90 * (row[key] - minimum) / (maximum - minimum)
            paths.append(f"{command}{x:.2f},{y:.2f}")
            command = "L"
        charts.append(
            '<svg viewBox="0 0 720 160" role="img" xmlns="http://www.w3.org/2000/svg">'
            f"<title>{_escape(title)} monthly production</title>"
            '<path d="M70,25 V120 H680" fill="none" stroke="#a9b6bd"/>'
            f'<text x="70" y="16">{_escape(title)}; axis range {_escape(minimum)}–{_escape(maximum)}</text>'
            f'<path d="{" ".join(paths)}" fill="none" stroke="#176a75" stroke-width="3"/>'
            f'<text x="70" y="145">{_escape(history[0]["period"])}</text>'
            f'<text x="680" y="145" text-anchor="end">{_escape(history[-1]["period"])}</text></svg>'
        )
    return "".join(charts)


def _cashflow_basis_html(basis):
    if not basis:
        return "<p>Cashflow basis not established.</p>"
    window, costs = basis["cashflow_window"], basis["applied_costs_usd"]
    rows = [
        ["Development system", basis["development_system"]],
        ["Development-system basis", basis["development_system_basis"]],
        ["Assumptions source", basis["assumptions_source"]],
        ["Oil price scenario (pre-tax USD/bbl)", basis["oil_price_usd_bbl"]],
        ["Variable opex (pre-tax USD/bbl)", basis["variable_opex_usd_per_bbl"]],
        ["Assumed first oil", basis["assumed_first_oil"]],
        ["First-oil basis", basis["first_oil_basis"]],
        ["Cashflow first period", window["first_period"]],
        ["Cashflow last period", window["last_period"]],
        ["Cashflow monthly rows", window["row_count"]],
        ["Default HOST_CAPEX_MM (million USD)", basis["host_capex_assumption_mm_usd"]],
        ["Host capital applied (pre-tax USD)", costs["host_capex"]],
    ]
    rows.extend(
        [name.replace("_", " ") + " applied (pre-tax USD)", value]
        for name, value in costs.items()
        if name != "host_capex"
    )
    capital = (
        "A default host capital is applied by the existing chain. Known scale defect: "
        "HOST_CAPEX_MM is passed as USD without the million-to-USD conversion; "
        "the applied amount above is not a valid development cost estimate. "
        "The default schedule includes assumed first oil and the preceding 23 months."
        if costs["host_capex"]
        else "No host capital is applied."
    )
    return (
        _table(["Cashflow basis / pre-tax cost", "Value"], rows) + f"<p>{capital}</p>"
    )


def render_report_html(facts) -> str:
    """Render escaped facts using inline CSS/SVG only; no external assets."""
    source = facts["source"]
    live = facts.get("provenance") == "nsta_live" and _aware_timestamp(
        source.get("refreshed_at")
    )
    badge, badge_class = (
        ("real: NSTA live", "live") if live else ("fixture/seed", "fixture")
    )
    coverage = _table(["Observation", "Value"], facts["coverage"].items())
    production = _table(
        ["Period", "Oil (bbl)", "Gas (Mcf)", "Water (bbl)"],
        [
            [r["period"], r["oil_bbl"], r["gas_mcf"], r["water_bbl"]]
            for r in facts["production_history"]
        ],
    )
    concepts = _table(
        ["Concept", "Relative screening score", "Rationale", "Warnings"],
        [
            [
                r["name"],
                r["total_score"],
                "; ".join(r["rationale"]),
                "; ".join(r["warnings"]),
            ]
            for r in facts["ranked_concepts"]
        ],
    )
    metrics = _table(
        ["Pre-tax metric", "Value"],
        [
            [key.replace("_usd", " (pre-tax USD)").replace("_", " "), value]
            for key, value in facts["pre_tax_metrics"].items()
        ],
    )
    url = str(source["url"])
    citation = _escape(url)
    if urlsplit(url).scheme in {"http", "https"}:
        citation = f'<a href="{_escape(url)}">NSTA production source</a>'
    timestamp = (
        _display(source.get("refreshed_at")) if live else "Fixture; no live refresh"
    )
    echo = _escape(json.dumps(facts["input_echo"], indent=2, allow_nan=False))
    evidence_note = (
        "Source bytes are not retained in the repository; the live numbers "
        "cannot be re-derived from the digest alone. A re-fetch may return different bytes."
        if live
        else "Bundled synthetic fixture; no live retrieval."
    )
    refresh_mode = _display(source.get("force_refresh"))
    if type(source.get("force_refresh")) is bool:
        refresh_mode = str(source["force_refresh"]).lower()
    refresh_note = (
        f"<p>Force refresh requested: {refresh_mode}. False permits cache reuse; "
        "the timestamp identifies cache retrieval, not source publication or proof of freshness.</p>"
        if live
        else ""
    )
    scope = _escape(
        source.get(
            "coverage_note",
            "Selected-field observations only; absent months are not imputed.",
        )
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(facts['field_name'])} — UKCS reference chain</title>
<style>
:root{{font-family:system-ui,sans-serif;color:#20313b;background:#f3f5f4}}
body{{max-width:1080px;margin:auto;padding:2rem}}h1{{font-size:2.2rem}}h2{{margin-top:2rem}}
section,header,footer{{background:white;padding:1.4rem;margin-bottom:1rem;border:1px solid #dce3df}}
.badge{{display:inline-block;padding:.3rem .7rem;border-radius:1rem;font-weight:700}}
.live{{background:#dcf0df;color:#155927}}.fixture{{background:#fff0cc;color:#684500}}
.banner{{border-left:5px solid #be8120;background:#fff5df;padding:1rem}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{text-align:left;padding:.6rem;border-bottom:1px solid #dce3df}}
svg{{display:block;width:100%;height:auto}}svg text{{font-size:12px;fill:#20313b}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}
a{{color:#176a75}}.table-wrap{{overflow-x:auto}}
</style></head><body>
<header><p>UK Continental Shelf · reference-chain evidence</p><h1>{_escape(facts['field_name'])}</h1>
<span class="badge {badge_class}" data-provenance="{'nsta_live' if live else 'fixture'}">{badge}</span>
<p class="banner">Economics shown are pre-tax chain plumbing (<code>{_escape(facts['economics_label'])}</code>) —
NOT a UK investment NPV. After-tax UK fiscal treatment is deferred to
<a href="https://github.com/vamseeachanta/worldenergydata/issues/736">#736</a>.</p></header>
<section><h2>Source coverage</h2><p>{scope}</p>{coverage}</section>
<section><h2>Production history</h2>{_production_svg(facts['production_history'])}<div class="table-wrap">{production}</div>
<p>Missing measurements are not established; a true zero remains zero.</p></section>
<section><h2>Concept screening</h2><p>Sparse metadata; relative screening is a chain-wiring demonstration, not a field-development recommendation.
Water depth (m): {_display(facts['field_concept'].get('water_depth_m'))}.</p><div class="table-wrap">{concepts}</div></section>
<section><h2>Pre-tax metrics</h2>{metrics}<p>The assumed oil price is an input scenario, not a fetched market quote.
Explicit drilling and development capital inputs are not supplied. These cashflows cannot establish project value.</p>
{_cashflow_basis_html(facts.get('cashflow_basis'))}</section>
<section><details><summary>Input echo</summary><pre>{echo}</pre></details></section>
<footer><p>{citation} · {_escape(source['licence'])}</p><p>Refresh timestamp: {timestamp}</p>
<p>{evidence_note}</p>{refresh_note}
<p>Generated (UTC): {_escape(facts['generated_at'])}</p></footer></body></html>"""


def generate_report(output_dir=None) -> dict:
    """Regenerate the committed fixture report, offline, into the selected directory."""
    import yaml

    from worldenergydata.ukcs.ukcs import Ukcs

    example = _REPO_ROOT / "examples/workflows/ukcs-reference-report"
    cfg = yaml.safe_load((example / "input.yml").read_text(encoding="utf-8"))
    facts = Ukcs().build_facts(cfg, input_root=example)
    output = (
        Path(output_dir)
        if output_dir is not None
        else _REPO_ROOT / "reports/ukcs_reference"
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(render_report_html(facts), encoding="utf-8")
    (output / "_facts.json").write_text(
        json.dumps(facts, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return facts


if __name__ == "__main__":
    generate_report()
