"""Self-contained UKCS reference-chain reports with explicit data qualification."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from worldenergydata.ukcs.production.nsta_client import DEFAULT_BASE_URL

LICENCE = "NSTA Open User Licence"
LICENCE_URL = "https://www.nstauthority.co.uk/"
BANNER = (
    "Economics shown are pre-tax chain plumbing (chain_plumbing_pre_tax) — "
    "NOT a UK investment NPV. After-tax UK fiscal treatment is deferred to #736."
)
LIMITATIONS = [
    "Concept scores are sparse-metadata wiring checks, not field recommendations.",
    (
        "Inherited cost and screening assumptions are assumed, based on previous experience; "
        "their engineering applicability is NOT_EVALUATED."
    ),
    (
        "Drilling CAPEX is absent; gas revenue and after-tax investment economics are "
        "NOT_EVALUATED. Net cashflow is an incomplete pre-tax plumbing result."
    ),
    (
        "The inherited nonzero host CAPEX path passes millions into USD fields; "
        "a separate unit correction is pending before cost use."
    ),
    "Oil mass conversion uses a generic density approximation, not a measured field density.",
    "A bounded extract does not establish complete field or UKCS coverage.",
    (
        "For live extracts, the source licence is identified as NSTA Open User Licence; "
        "current licence terms were not independently verified. "
        "The committed example contains synthetic inputs only."
    ),
]


def _plain(value):
    """Convert scalars and nonfinite missing values into strict JSON types."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if hasattr(value, "item"):
        return _plain(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _verified_live(provenance, refreshed_at, evidence):
    try:
        stamp = datetime.fromisoformat(str(refreshed_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    return (
        stamp.tzinfo is not None
        and provenance == "nsta_live"
        and bool(refreshed_at)
        and evidence.get("cache_verified") is True
        and re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("sha256", ""))) is not None
    )


def build_report_facts(
    chain_result,
    *,
    provenance="fixture",
    source_url=DEFAULT_BASE_URL,
    licence=LICENCE,
    refreshed_at=None,
    input_echo=None,
    source_evidence=None,
):
    """Flatten a chain result; source tags alone never establish live provenance.

    Monthly totals are sums of reporting-unit rows (not averages). This is an
    arithmetic aggregation, with no new empirical coefficient. Existing unit
    conversions remain in production.field_production and common.units.
    """
    frame = chain_result["unified_production"].copy()
    evidence = dict(source_evidence or {})
    live = _verified_live(provenance, refreshed_at, evidence) and (
        not frame.empty and set(frame["source"]) == {"nsta"}
    )
    frame["period"] = [
        f"{int(y):04d}-{int(m):02d}" for y, m in zip(frame.year, frame.month)
    ]
    history = []
    for period, rows in frame.groupby("period", sort=True):
        history.append(
            {
                "period": period,
                **{
                    unit: rows[unit].sum(min_count=1)
                    for unit in ("oil_bbl", "gas_mcf", "water_bbl")
                },
            }
        )
    observed_month_count = len(history)
    if history:
        observed = {row["period"]: row for row in history}
        first_year, first_month = map(int, history[0]["period"].split("-"))
        last_year, last_month = map(int, history[-1]["period"].split("-"))
        history = []
        for ordinal in range(
            first_year * 12 + first_month - 1, last_year * 12 + last_month
        ):
            year, month = divmod(ordinal, 12)
            period = f"{year:04d}-{month + 1:02d}"
            history.append(
                observed.get(
                    period,
                    {
                        "period": period,
                        "oil_bbl": None,
                        "gas_mcf": None,
                        "water_bbl": None,
                    },
                )
            )
        missing_periods = [
            row["period"] for row in history if row["period"] not in observed
        ]
    else:
        missing_periods = []
    concepts = []
    for scored in chain_result["ranked_concepts"]:
        parts = [scored.concept_type, scored.tree_type, scored.topology]
        name = " / ".join(str(getattr(p, "value", p)) for p in parts if p is not None)
        concepts.append(
            {
                "name": name,
                "score": scored.total_score,
                "rationale": scored.rationale,
                "warnings": scored.warnings,
            }
        )
    return _plain(
        {
            "field_name": chain_result["field_name"],
            "coverage": {
                "row_count": len(frame),
                "month_count": observed_month_count,
                "span_month_count": len(history),
                "missing_month_count": len(missing_periods),
                "missing_periods": missing_periods,
                "first_period": history[0]["period"] if history else None,
                "last_period": history[-1]["period"] if history else None,
            },
            "production_history": history,
            "ranked_concepts": concepts,
            "economics_label": chain_result["economics_label"],
            "pre_tax_metrics": chain_result["pre_tax_metrics"],
            "provenance": "nsta_live" if live else "fixture",
            "source": {
                "kind": "production_source" if live else "schema_reference",
                "url": source_url if live else DEFAULT_BASE_URL,
                "licence": licence if live else None,
                "licence_url": LICENCE_URL if live else None,
                "refreshed_at": refreshed_at if live else None,
                "evidence": evidence,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "input_echo": input_echo or {},
            "limitations": LIMITATIONS,
            "method": {
                "production": (
                    "Monthly sum of reporting-unit rows after "
                    "UKCSFieldProductionLoader normalization."
                ),
                "conversions": (
                    "common.units registry at revision d867ba1e; generic oil-density approximation."
                ),
                "economics": (
                    "Existing reference_chain and FDAS cashflow; "
                    "no new fiscal or cost coefficients."
                ),
                "readiness": "NOT_EVALUATED for engineering decisions",
            },
            "revision_history": [
                {
                    "revision": "initial",
                    "date": "2026-10-20",
                    "change": "Reference-chain report with explicit source qualification.",
                },
                {
                    "revision": "2",
                    "date": "2026-10-22",
                    "change": (
                        "Clarify synthetic provenance, require depth and expose "
                        "calendar gaps and score differences."
                    ),
                },
            ],
        }
    )


def _text(value):
    return escape(str(value)) if value is not None else "Not available"


def _number(value):
    return "Not available" if value is None else f"{float(value):,.1f}"


def _table(headers, rows):
    head = "".join(f"<th>{_text(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_text(c)}</td>" for c in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _chart(history):
    """Draw separate, unit-labelled sparklines; dimensions are presentation only."""
    if not history:
        return "<p>No production records.</p>"
    plots = []
    for key, label in (
        ("oil_bbl", "Oil (bbl/month)"),
        ("gas_mcf", "Gas (Mcf/month)"),
        ("water_bbl", "Water (bbl/month)"),
    ):
        values = [row[key] for row in history]
        maximum = max((v for v in values if v is not None), default=0) or 1
        # Each segment stops at a missing value; missing measurements are not zeros.
        segments, current = [], []
        for i, value in enumerate(values):
            if value is None:
                if current:
                    segments.append(current)
                current = []
            else:
                current.append(
                    f"{20 + 660 * i / max(len(values) - 1, 1):.1f},"
                    f"{110 - 90 * value / maximum:.1f}"
                )
        if current:
            segments.append(current)
        lines = "".join(f'<polyline points="{" ".join(s)}"/>' for s in segments)
        points = "".join(
            f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="3"/>'
            for s in segments
            for p in s
        )
        plots.append(
            f"<h3>{label}</h3><p>Scale maximum: {_number(maximum)}</p>"
            f'<svg viewBox="0 0 700 130" role="img" aria-label="{label}">'
            f"<title>{label}</title>{lines}{points}</svg>"
        )
    return "".join(plots)


def _source_link(url, title):
    # Never emit data-supplied javascript/file URLs, including in input echo.
    return (
        f'<a href="{escape(url, quote=True)}">{_text(title)}</a>'
        if str(url).startswith("https://")
        else _text(title)
    )


def render_report_html(facts):
    """Render escaped facts without scripts, remote fonts or external styles."""
    source = facts["source"]
    live = _verified_live(
        facts["provenance"], source["refreshed_at"], source["evidence"]
    )
    badge = "real: NSTA live" if live else "SYNTHETIC: invented inputs, not NSTA data"
    coverage = _table(["Coverage", "Value"], facts["coverage"].items())
    production = _table(
        ["Period", "Oil (bbl)", "Gas (Mcf)", "Water (bbl)"],
        [
            (r["period"], *(_number(r[k]) for k in ("oil_bbl", "gas_mcf", "water_bbl")))
            for r in facts["production_history"]
        ],
    )
    concepts = _table(
        ["Concept", "Score", "Rationale", "Warnings"],
        [
            (
                r["name"],
                f'{100 * r["score"]:.1f}%',
                "; ".join(r["rationale"]),
                "; ".join(r["warnings"]),
            )
            for r in facts["ranked_concepts"]
        ],
    )
    metrics = _table(
        ["Pre-tax metric (USD unless months)", "Value"],
        [
            (k, str(int(v)) if k == "months" and v is not None else _number(v))
            for k, v in facts["pre_tax_metrics"].items()
        ],
    )
    revisions = _table(
        ["Revision", "Date", "Change and reason"],
        [(r["revision"], r["date"], r["change"]) for r in facts["revision_history"]],
    )
    limits = "".join(f"<li>{_text(line)}</li>" for line in facts["limitations"])
    source_title = (
        "NSTA PPRS production source" if live else "NSTA PPRS schema reference"
    )
    source_licence = (
        _source_link(source["licence_url"], source["licence"])
        if live
        else "Synthetic inputs; no production-source licence asserted."
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>UKCS reference-chain analysis</title><style>
body {{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;
padding:0 1rem;color:#172b3a}}
table {{border-collapse:collapse;width:100%;margin:1rem 0}}
th,td {{border:1px solid #bdcbd3;padding:.5rem;text-align:left}}
.banner,.badge {{padding:1rem;background:#fff0bd}}.live {{background:#cdebd9}}
svg {{width:100%;background:#f3f7fa}}
polyline {{stroke:#147189;stroke-width:2;fill:none}}circle {{fill:#147189}}
pre {{white-space:pre-wrap;overflow-wrap:anywhere}}h2 {{margin-top:2rem}}
</style></head><body><h1>UKCS reference-chain analysis</h1>
<h2>Summary</h2><p>Selected field: {_text(facts['field_name'])}.</p>
<p class="badge {'live' if live else ''}">{badge}</p><p class="banner">{BANNER}</p>
<h2>Revision history</h2>{revisions}
<h2>Source coverage</h2>{coverage}
<pre>{_text(json.dumps(source['evidence'], indent=2))}</pre>
<h2>Production history</h2>{_chart(facts['production_history'])}{production}
<p>Table 1. Monthly totals for the selected field; missing calendar months and measurements
remain unavailable and break chart lines.</p>
<h2>Concept screening</h2>{concepts}
<p>Table 2. Inherited heuristic scores; applicability is NOT_EVALUATED.</p>
<h2>Pre-tax plumbing metrics</h2>{metrics}
<p>Table 3. Incomplete pre-tax cashflow, without investment qualification.</p>
<h2>Method and qualification</h2><pre>{_text(json.dumps(facts["method"], indent=2))}</pre>
<h2>Known limits</h2><ul>{limits}</ul>
<details><summary>Inputs</summary>
<pre>{_text(json.dumps(facts['input_echo'], indent=2))}</pre></details>
<footer><h2>Sources</h2><p>{_source_link(source['url'], source_title)} ·
{source_licence}</p>
<p>Cache refresh timestamp: {_text(source['refreshed_at'])};
fixture inputs have no live refresh.</p>
<p>Generated UTC: {_text(facts['generated_at'])}.</p></footer></body></html>
"""


def generate_report(output_dir=None):
    """Regenerate the committed fixture analysis; live use requires explicit config."""
    from worldenergydata.ukcs.ukcs import Ukcs

    root = next(
        p
        for p in Path(__file__).resolve().parents
        if (p / "docs/registry/workflows.yaml").is_file()
    )
    import yaml

    example = root / "examples/workflows/ukcs-reference-report"
    cfg = yaml.safe_load((example / "input.yml").read_text(encoding="utf-8"))
    cfg["Analysis"] = {
        "analysis_root_folder": str(example),
        "result_folder": str(output_dir or root / "reports/ukcs_reference"),
    }
    facts = Ukcs().run(cfg)
    destination = Path(cfg["Analysis"]["result_folder"])
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "index.html").write_text(
        render_report_html(facts), encoding="utf-8", newline="\n"
    )
    (destination / "_facts.json").write_text(
        json.dumps(facts, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return facts


if __name__ == "__main__":
    generate_report()
