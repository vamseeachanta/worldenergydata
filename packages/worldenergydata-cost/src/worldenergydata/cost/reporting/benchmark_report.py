"""Deterministic descriptive cost report; no normalization policy is inferred."""

import json
from dataclasses import asdict
from datetime import date
from hashlib import sha256
from html import escape
from math import isfinite
from pathlib import Path
from statistics import median, quantiles
from string import Template
from urllib.parse import urlsplit

from worldenergydata.fdas.api import DisclosureAnalyticsQuery

SEED_BADGE = "Illustrative seed — not yet ingested"
METHOD_SOURCE = "https://www.itl.nist.gov/div898/handbook/eda/section3/boxplot.htm"


def _operator_rows(records):
    records = [r for r in records if r.scope == "operator"]
    if any(type(r.fiscal_year) is not int for r in records):
        raise ValueError("Fiscal year must be an integer")
    records.sort(key=lambda r: (r.operator, r.fiscal_year))
    seen = set()
    for record in records:
        key = (record.operator, record.fiscal_year)
        if key in seen:
            raise ValueError("Duplicate operator fiscal year; resolve source lineage")
        seen.add(key)
        if record.currency != "USD":
            raise ValueError("USD input required; currency normalization is pending")
        if (
            not isfinite(record.reported_capex_usd_mm)
            or record.reported_capex_usd_mm < 0
        ):
            raise ValueError("CAPEX must be finite and nonnegative")
        for field in ("source", "retrieval_date", "fiscal_basis"):
            if not record.provenance.get(field):
                raise ValueError(f"Missing disclosure provenance: {field}")
        date.fromisoformat(record.provenance["retrieval_date"])
    result, prior = [], {}
    for record, view in zip(
        records, DisclosureAnalyticsQuery().operator_capex(records)
    ):
        row = asdict(view)
        previous = prior.get(record.operator)
        consecutive = (
            previous is not None and record.fiscal_year == previous.fiscal_year + 1
        )
        if not consecutive:
            row["yoy_delta_usd_mm"] = row["yoy_delta_pct"] = None
        comparable = (
            consecutive
            and record.comparability_status == "comparable"
            and previous.comparability_status == "comparable"
            and record.comparability_basis
            and record.comparability_basis == previous.comparability_basis
            and record.provenance["fiscal_basis"] == previous.provenance["fiscal_basis"]
        )
        row["normalized_yoy_pct"] = row["yoy_delta_pct"] if comparable else None
        row["comparability"] = "comparable" if comparable else "ungated — #336 pending"
        row["restatement"] = "NOT_EVALUATED — pending #344"
        row["opex_usd_mm"] = None
        row["opex_status"] = "NOT_EVALUATED — OPEX not supplied"
        result.append(row)
        prior[record.operator] = record
    return result


def _value(value):
    return str(getattr(value, "value", value))


def _group_cost_points(cost_points):
    groups = {}
    for index, point in enumerate(cost_points, start=1):
        if not isfinite(point.cost_usd_mm) or point.cost_usd_mm <= 0:
            raise ValueError("Cohort costs must be finite and positive")
        key = tuple(
            _value(getattr(point, k))
            for k in ("region", "water_depth_band", "cost_type", "activity_type")
        )
        raw = (
            point.model_dump(mode="json")
            if hasattr(point, "model_dump")
            else vars(point)
        )
        identity = {
            "source_record_index": index,
            "source_record_sha256": sha256(
                json.dumps(raw, sort_keys=True).encode()
            ).hexdigest(),
            "operator": point.operator,
        }
        groups.setdefault(key, []).append(
            (point.year_sanction, point.cost_usd_mm, identity)
        )
    return groups


_COHORT_FIELDS = ("region", "water_depth_band", "cost_type", "activity_type")


def _cohort_summary(key, observations):
    values = sorted(amount for _, amount, _ in observations)
    cohort = dict(zip(_COHORT_FIELDS, key))
    cohort.update(
        count=len(values),
        median_usd_mm=median(values),
        year_min=min(year for year, _, _ in observations),
        year_max=max(year for year, _, _ in observations),
        outlier_status="NOT_EVALUATED",
    )
    # Report coverage policy: four observations before quartile flags;
    # this is not evidence of statistical significance.
    if len(values) >= 4:
        # NIST/SEMATECH e-Handbook section 1.3.3.7, web edition retrieved
        # 2026-10-20: inner fences Q1 - 1.5*IQR and Q3 + 1.5*IQR.
        # Inclusive quartiles interpolate over endpoints (Python statistics).
        q1, _, q3 = quantiles(values, n=4, method="inclusive")
        cohort.update(
            q1_usd_mm=q1,
            q3_usd_mm=q3,
            lower_fence_usd_mm=q1 - 1.5 * (q3 - q1),
            upper_fence_usd_mm=q3 + 1.5 * (q3 - q1),
            outlier_status="descriptive_only",
        )
    return cohort


def _cohorts(cost_points):
    cohorts, outliers = [], []
    for key, observations in sorted(_group_cost_points(cost_points).items()):
        cohort = _cohort_summary(key, observations)
        cohorts.append(cohort)
        if cohort["outlier_status"] == "NOT_EVALUATED":
            continue
        for year, amount, identity in sorted(
            observations, key=lambda r: (r[0], r[1], r[2]["source_record_sha256"])
        ):
            if (
                amount < cohort["lower_fence_usd_mm"]
                or amount > cohort["upper_fence_usd_mm"]
            ):
                outliers.append(
                    {
                        **dict(zip(_COHORT_FIELDS, key)),
                        "year_sanction": year,
                        "cost_usd_mm": amount,
                        **identity,
                    }
                )
    return cohorts, outliers


def build_report_facts(records, cost_points, report_date: str) -> dict:
    """Build pure facts via FDAS, keeping nominal cohorts separate from totals.

    Report date is a caller-supplied edition date, not a freshness guarantee.
    Provenance is copied through FDAS. Empty inputs produce empty views.
    """
    date.fromisoformat(report_date)
    operator_rows = _operator_rows(records)
    cohorts, outliers = _cohorts(cost_points)
    return {
        "report_date": report_date,
        "operators_covered": len({r["operator"] for r in operator_rows}),
        "operator_rows": operator_rows,
        "cohorts": cohorts,
        "outliers": outliers,
        "method_source": METHOD_SOURCE,
        "cohort_basis": "Nominal as-reported USD million; no inflation or currency qualification",
        "field_type_basis": "Water-depth band is a proxy, not reservoir or onshore classification",
        "cohort_source": "cost/data_collection/public_dataset.py; curated inputs, not reverified filings",
        "pending": {
            "334": "Canonical annual dataset; seed supplied here",
            "336": "Currency normalization and comparability policy",
            "343": "Source registry and coverage tracking",
            "344": "Restatement lineage",
            "361": "Calculation citation sidecars",
        },
    }


def facts_digest(facts):
    """Digest the reproducible facts payload independently of presentation."""
    return sha256(
        json.dumps(facts, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def _table(headers, rows, caption):
    def cell(value):
        if value == SEED_BADGE:
            return f'<span class="badge-seed">{SEED_BADGE}</span>'
        return escape(str(value))

    body = "".join(
        "<tr>" + "".join(f"<td>{cell(v)}</td>" for v in row) + "</tr>" for row in rows
    )
    head = "".join(f'<th scope="col">{escape(h)}</th>' for h in headers)
    return (
        f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
        f'<tbody>{body}</tbody></table><p class="caption">{escape(caption)}</p></div>'
    )


def _number(value):
    return "NOT_EVALUATED" if value is None else f"{value:,.1f}"


def _bars(rows):
    maximum = max((r["reported_capex_usd_mm"] for r in rows), default=0) or 1
    bars = []
    # SVG dimensions are presentation coordinates, not engineering constants.
    for i, row in enumerate(rows):
        y, width = 30 + i * 38, 350 * row["reported_capex_usd_mm"] / maximum
        bars.append(
            f'<text x="0" y="{y + 15}">{escape(str(row["fiscal_year"]))}</text>'
            f'<rect x="55" y="{y}" width="{width:.1f}" height="22"/>'
            f'<text x="{65 + width:.1f}" y="{y + 15}">'
            f'{_number(row["reported_capex_usd_mm"])}</text>'
        )
    return (
        f'<svg viewBox="0 0 540 {50 + len(rows) * 38}" role="img" '
        'aria-label="Annual reported CAPEX in nominal USD million">'
        + "".join(bars)
        + "</svg>"
    )


def _operator_section(operator, rows, index):
    seed = any(r["provenance"].get("data_tier") == "seed" for r in rows)
    badge = f'<p class="badge-seed">{SEED_BADGE}</p>' if seed else ""
    table = _table(
        [
            "Fiscal year",
            "CAPEX (USD million)",
            "Arithmetic change (USD million)",
            "Arithmetic YoY (%)",
            "Qualified YoY (%)",
            "Comparability",
            "Restatement",
            "Data tier",
        ],
        [
            (
                r["fiscal_year"],
                _number(r["reported_capex_usd_mm"]),
                _number(r["yoy_delta_usd_mm"]),
                _number(
                    None if r["yoy_delta_pct"] is None else r["yoy_delta_pct"] * 100
                ),
                _number(
                    None
                    if r["normalized_yoy_pct"] is None
                    else r["normalized_yoy_pct"] * 100
                ),
                r["comparability"],
                r["restatement"],
                (
                    SEED_BADGE
                    if r["provenance"].get("data_tier") == "seed"
                    else "supplied"
                ),
            )
            for r in rows
        ],
        "Annual CAPEX and unqualified arithmetic changes. OPEX: NOT_EVALUATED; not supplied.",
    )
    return (
        f'<section class="operator" id="operator-{index}"><h2>{escape(operator)}</h2>'
        + badge
        + _bars(rows)
        + table
        + "</section>"
    )


def _cohorts_table(facts):
    return _table(
        [
            "Region",
            "Water-depth proxy",
            "Cost type",
            "Activity",
            "Years",
            "Count",
            "Median (USD million)",
            "Outlier evaluation",
        ],
        [
            (
                c["region"],
                c["water_depth_band"],
                c["cost_type"],
                c["activity_type"],
                f"{c['year_min']}–{c['year_max']}",
                c["count"],
                _number(c["median_usd_mm"]),
                c["outlier_status"],
            )
            for c in facts["cohorts"]
        ],
        "Descriptive sanction-cost cohorts; different cost types and activities remain separate.",
    )


def _outliers_table(facts):
    return _table(
        [
            "Operator",
            "Source row",
            "Region",
            "Water-depth proxy",
            "Cost type",
            "Activity",
            "Sanction year",
            "Cost (USD million)",
        ],
        [
            (
                r["operator"],
                r["source_record_index"],
                r["region"],
                r["water_depth_band"],
                r["cost_type"],
                r["activity_type"],
                r["year_sanction"],
                _number(r["cost_usd_mm"]),
            )
            for r in facts["outliers"]
        ],
        "Observations outside inner IQR fences are descriptive flags, not operator rankings.",
    )


def _citations_table(facts):
    return _table(
        [
            "Operator",
            "Fiscal year",
            "Source",
            "publisher",
            "retrieval_date",
            "revision",
            "page_ref",
            "fiscal_basis",
            "retrieval_note",
            "source_sha256",
            "Data tier",
        ],
        [
            (
                r["operator"],
                r["fiscal_year"],
                *(
                    r["provenance"].get(k, "NOT_EVALUATED")
                    for k in (
                        "source",
                        "publisher",
                        "retrieval_date",
                        "revision",
                        "page_ref",
                        "fiscal_basis",
                        "retrieval_note",
                        "source_sha256",
                    )
                ),
                (
                    SEED_BADGE
                    if r["provenance"].get("data_tier") == "seed"
                    else "supplied"
                ),
            )
            for r in facts["operator_rows"]
        ],
        "Per-row evidence; retrieval date is not the fiscal year or a guarantee of current coverage.",
    )


def _source_links(facts):
    links = set()
    for row in facts["operator_rows"]:
        url = row["provenance"].get("source_url", "")
        if urlsplit(url).scheme in {"http", "https"}:
            links.add((url, row["provenance"]["source"]))
    return "".join(
        (
            f'<li><a href="{escape(url, quote=True)}">{escape(title)}</a></li>'
            for url, title in sorted(links)
        )
    )


_REPORT_TEMPLATE = Template("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Operator cost benchmarking analysis</title><style>
body{font:16px system-ui,sans-serif;background:#f4f7fa;color:#183044;margin:0 auto;padding:2rem;max-width:1200px}
section,header{background:white;border:1px solid #d6e0e8;border-radius:8px;margin:1rem 0;padding:1.4rem}
h1,h2{color:#123f59}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem}
.kpis p{background:#eaf2f7;padding:1rem}.badge-seed{background:#fdf3e0;color:#8a5a12;border:1px solid #f0dcae;padding:.2rem .4rem}
.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:.65rem;border-bottom:1px solid #d6e0e8}
th{background:#eaf2f7}td{overflow-wrap:anywhere}.caption{font-size:.85rem;color:#456}svg{max-width:600px;width:100%}
rect{fill:#267a99}select{font:inherit;padding:.5rem}a{color:#145d83}[hidden]{display:none}
</style></head><body>
<header><h1>Operator cost benchmarking analysis</h1>
<p>Historical cited seed disclosures and derived descriptive statistics are separated from
unestablished normalization, comparability and restatement assumptions. No operator ranking is established.</p>
<p>Data as of / generated for: ${slot0}; source vintages are listed per row.</p>
<div class="kpis"><p>Operators: ${slot1}</p><p>Operator-year rows: ${slot2}</p>
<p>Cohorts: ${slot3}</p><p>OPEX: NOT_EVALUATED</p></div></header>
<section><h2>Revision history</h2><table><thead><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr></thead>
<tbody><tr><td>Initial</td><td>${slot4}</td><td>Cited historical seed and descriptive cohorts expose the disclosure analytics.</td></tr></tbody></table>
<p class="caption">Report edition history.</p></section>
<label for="operator-selector">Operator</label> <select id="operator-selector">${slot5}</select>
${slot6}
<section><h2>Regional and field-type proxy comparisons</h2><p>${slot7}.</p>
<p>${slot8}. No onshore or reservoir-play comparison is established.</p>${slot9}
<h3>Outlier observations</h3>${slot10}<p>IQR = Q3 − Q1; fences = Q1 − 1.5 IQR, Q3 + 1.5 IQR.
Inclusive quartiles; at least four observations per cohort (report coverage policy).</p>
<p>Method: <a href="${slot11}">NIST/SEMATECH e-Handbook, section 1.3.3.7, Box Plot</a>,
web edition retrieved 2026-10-20. ${slot12}.</p></section>
<section><h2>Citations and freshness</h2>${slot13}<ul>${slot14}</ul></section>
<section><h2>Known limits and pending dependencies</h2><ul>${slot15}</ul>
<p>Arithmetic YoY = (current − previous) / previous for consecutive years only;
a zero prior amount has no percentage change. These raw changes do not establish a comparable cost trend.
The equation is the relative change definition used by cost/disclosure_analytics.py (2026).</p>
<p>Facts SHA-256: ${slot16}</p></section>
<script>
const selector = document.getElementById('operator-selector');
function selectOperator() {
  document.querySelectorAll('.operator').forEach(section => {
    section.hidden = section.id !== selector.value;
  });
}
selector.addEventListener('change', selectOperator);
selectOperator();
</script></body></html>
""")


def render_html(facts: dict) -> str:
    "Render escaped HTML with inline CSS, SVG and a native operator selector."
    operators = sorted({r["operator"] for r in facts["operator_rows"]})
    options, sections = ([], [])
    for index, operator in enumerate(operators):
        options.append(f'<option value="operator-{index}">{escape(operator)}</option>')
        rows = [r for r in facts["operator_rows"] if r["operator"] == operator]
        sections.append(_operator_section(operator, rows, index))
    cohorts = _cohorts_table(facts)
    outliers = _outliers_table(facts)
    citations = _citations_table(facts)
    sources = _source_links(facts)
    pending = "".join(
        f'<li><a href="https://github.com/vamseeachanta/worldenergydata/issues/{key}">'
        f"#{key}</a>: {escape(value)}</li>"
        for key, value in sorted(facts["pending"].items())
    )
    return _REPORT_TEMPLATE.substitute(
        slot0=escape(facts["report_date"]),
        slot1=facts["operators_covered"],
        slot2=len(facts["operator_rows"]),
        slot3=len(facts["cohorts"]),
        slot4=escape(facts["report_date"]),
        slot5="".join(options),
        slot6="".join(sections),
        slot7=escape(facts["cohort_basis"]),
        slot8=escape(facts["field_type_basis"]),
        slot9=cohorts,
        slot10=outliers,
        slot11=METHOD_SOURCE,
        slot12=escape(facts["cohort_source"]),
        slot13=citations,
        slot14=sources,
        slot15=pending,
        slot16=facts_digest(facts),
    )


def write_report(out_dir: Path, report_date: str) -> dict[str, Path]:
    """Write self-contained HTML and a sorted, lossless JSON facts companion."""
    from worldenergydata.cost.data_collection.disclosure_seed_dataset import (
        load_seed_disclosure_records,
    )
    from worldenergydata.cost.data_collection.public_dataset import load_public_dataset

    facts = build_report_facts(
        load_seed_disclosure_records(), load_public_dataset(), report_date
    )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "html": out_dir / "operator_cost_benchmarking.html",
        "facts": out_dir / "operator_cost_benchmarking_facts.json",
    }
    outputs["html"].write_text(render_html(facts), encoding="utf-8")
    outputs["facts"].write_text(
        json.dumps(facts, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return outputs
