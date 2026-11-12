"""Deterministic, escaped HTML and machine-readable native-unit outputs."""

import csv
import hashlib
import io
import json
from decimal import Decimal
from html import escape


def _json(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _text(value):
    return escape("NOT_EVALUATED" if value is None else str(value), quote=True)


def _money(value):
    # Presentation only: issue 1044 uses native USD. Rounded display is to one
    # decimal; exact Decimal values remain in JSON/CSV for reproduction.
    if value is None:
        return "NOT_EVALUATED"
    number = Decimal(value)
    if number and abs(number) < Decimal("0.1"):
        return "<0.1 (negative)" if number < 0 else "<0.1 (positive)"
    return f"{number:,.1f}"


def _table(headers, rows):
    return (
        "<table><thead><tr>"
        + "".join(f"<th>{_text(h)}</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{_text(v)}</td>" for v in row) + "</tr>"
            for row in rows
        )
        + "</tbody></table>"
    )


def _range(value):
    return (
        "NOT_EVALUATED"
        if value is None
        else f"[{_money(value['low'])}, {_money(value['high'])}]"
    )


def render_report(result):
    projects = result["projects"]
    parts = [
        """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FDAS workbook reconciliation and integrated cost-map analysis</title>
<style>body{font:16px system-ui;max-width:1200px;margin:2rem auto;padding:1rem;color:#172b3a}
table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{padding:.5rem;border:1px solid #ccd5dd;text-align:left}
th{background:#eaf0f4}details{margin:1rem 0}summary{cursor:pointer;font-weight:bold}
.limit{padding:1rem;border-left:5px solid #b77b15;background:#fff6e5}code{overflow-wrap:anywhere}</style>
<h1>FDAS workbook reconciliation and integrated cost-map analysis</h1><h2>Summary</h2>""",
        f"<p>{len(projects)} workbook projects are inventoried. Values retain their FDAS_V30 assumption provenance. "
        "External cost equivalence is NOT_EVALUATED until project/component/time and economic bases are evidenced.</p>",
        "<h2>Revision history</h2>",
        _table(
            ["Revision", "Date", "Change and reason"],
            [
                (
                    "Initial",
                    "2026-10-19",
                    "Read-only frozen workbook comparison; missing evidence remains explicit.",
                )
            ],
        ),
        '<p class="limit">Stakeholder circulation remains maintainer-gated under '
        '<a href="https://github.com/vamseeachanta/worldenergydata/issues/1017">issue 1017</a>. '
        "Workbook assumptions are not disclosures. No workbook is overwritten. "
        "After-tax/NOL behavior is outside this comparison.</p>",
        "<h2>Portfolio summary</h2>",
        _table(
            ["Project", "System", "Window", "Workbook CAPEX (USD)", "Comparison"],
            [
                (
                    p["project"],
                    p["system"],
                    p["time_basis"],
                    _money(p["total_capex_usd"]),
                    p["comparison_status"],
                )
                for p in projects
            ],
        ),
        "<h2>Asset-to-total index</h2>",
        "<p>Component rows lead back to each workbook project total. Totals are repeated for navigation; "
        "they are not additive across rows or across projects with different economic bases.</p>",
        _table(
            [
                "Category",
                "Project",
                "Cell",
                "Requirement IDs",
                "Workbook component (USD)",
                "Project CAPEX (USD)",
            ],
            sorted(
                (
                    r["category"],
                    p["project"],
                    r["cell"],
                    " | ".join(r["requirement_ids"]) or "unmapped",
                    _money(r["value"]),
                    _money(p["total_capex_usd"]),
                )
                for p in projects
                for r in p["crosswalk"]
                if r["disposition"] == "included"
            ),
        ),
        "<h2>Project drill-down</h2>",
    ]
    for p in projects:
        parts.extend(
            [
                f"<details><summary>{_text(p['project'])}</summary>",
                f"<p>{_text(p['comparison_reason'])}</p>",
                "<h3>Asset-to-total / Total-to-asset</h3>",
                "<p>Included components plus the separately cited injection facility form the workbook CAPEX. "
                "Subtotals are not counted again. OPEX remains outside CAPEX. "
                "Installation is not separately available in the workbook; no allocation is inferred.</p>",
                _table(
                    [
                        "Cell",
                        "Parameter",
                        "Category",
                        "Disposition",
                        "Workbook (USD)",
                        "Disclosed (USD)",
                        "Mapped (USD)",
                        "Modeled (USD)",
                        "Variance (USD)",
                    ],
                    [
                        (
                            r["cell"],
                            r["parameter"],
                            r["category"],
                            r["disposition"],
                            _money(r["value"]),
                            _money(r["disclosed"]),
                            _money(r["mapped"]),
                            _money(r["modeled"]),
                            _money(r["variance"]),
                        )
                        for r in p["crosswalk"]
                    ],
                ),
                f"<p>Injection facility (USD): {_money(p['water_injection_facility_usd'])}; "
                f"source: {_text(p['injection_source'])}. Facilities bridge variance (USD): "
                f"{_money(p['component_bridge_variance_usd'])}. D&amp;C bridge variance (USD): "
                f"{_money(p['dnc_bridge_variance_usd'])}.</p>",
                "<h3>Time traces and monthly/component sums</h3>",
                _table(
                    [
                        "Category",
                        "Monthly sum (USD)",
                        "Monthly minus summary (USD)",
                        "Status",
                    ],
                    [
                        (
                            category,
                            _money(check["monthly_sum_usd"]),
                            _money(check["variance_usd"]),
                            check["status"],
                        )
                        for category, check in sorted(p["monthly_checks"].items())
                    ],
                ),
                "<details><summary>Monthly workbook cost trace</summary>",
                _table(
                    [
                        "Month",
                        "Facilities (USD)",
                        "Drilling (USD)",
                        "Completion (USD)",
                        "Variable OPEX (USD)",
                        "Fixed OPEX (USD)",
                    ],
                    [
                        (
                            m["period"],
                            *(
                                _money(m[k])
                                for k in (
                                    "facilities",
                                    "drilling",
                                    "completion",
                                    "variable_opex",
                                    "fixed_opex",
                                )
                            ),
                        )
                        for m in p["months"]
                    ],
                ),
                "</details></details>",
            ]
        )
    parts.extend(
        [
            "<h2>Workbook reconciliation</h2>",
            f"<p>{_text(result['v30_status'])}</p>",
            "<p>V50: "
            + _text(result["v50_status"])
            + ' — <a href="https://github.com/vamseeachanta/worldenergydata/issues/899">assumption change log</a>.</p>',
            "<p>Variance = [workbook low − comparison high, workbook high − comparison low]. "
            "A materiality threshold is a required input, with its evidence. Currency, units, price year, ownership, "
            "scope, CAPEX/OPEX, time period and assumption vintage must match before subtraction. "
            "Classification alone does not resolve missing evidence.</p>",
        ]
    )
    if result["comparisons"]:
        parts.append(
            _table(
                [
                    "Project",
                    "Component",
                    "Variance low",
                    "Variance high",
                    "Materiality",
                    "Status",
                ],
                [
                    (
                        r["project"],
                        r["component"],
                        r["variance_low"],
                        r["variance_high"],
                        r["materiality"],
                        r["status"],
                    )
                    for r in result["comparisons"]
                ],
            )
        )
    parts.extend(
        [
            "<h2>Required assets and award evidence</h2>",
            "<p>Upstream rows retain source provenance and are not automatically comparable to workbook values.</p>",
            _table(
                ["Surface", "Status", "Coverage / reason"],
                [
                    (k, v["status"], v["reason"])
                    for k, v in sorted(result["upstream"].items())
                ],
            ),
            "<h2>Estimator backtests</h2><p>NOT_EVALUATED: the correlated-estimator manifest and "
            "project-level holdout results are required. The existing calibration predictor is not substituted.</p>",
            "<h2>Provenance legend</h2>",
            _table(
                ["Label", "Meaning"],
                [
                    (
                        "workbook_assumption",
                        "Frozen FDAS_V30 input or result; not independent disclosure",
                    ),
                    ("disclosed", "Independently sourced public cost"),
                    ("mapped", "Evidence crosswalk; not a new disclosure"),
                    (
                        "allocated / modeled",
                        "Inference retaining its own vintage and uncertainty",
                    ),
                    (
                        "NOT_EVALUATED",
                        "Missing evidence or incompatible basis; never zero",
                    ),
                ],
            ),
            "<h2>Frozen inventory</h2>",
            _table(
                ["Workbook", "SHA-256", "Sheets"],
                [
                    (name, spec["sha256"], ", ".join(spec["sheets"]))
                    for name, spec in sorted(result["inventory"]["workbooks"].items())
                ],
            ),
            "<p>Machine-readable JSON also carries system parameters, native-unit notes, cell crosswalks, "
            "monthly arrays and unresolved findings. Exact arithmetic is retained there; display values are rounded.</p>",
            "</html>",
        ]
    )
    if "asset_evidence" in result:
        evidence = result["asset_evidence"]
        tables = [
            f"<h2>Existing evidence: {_text(evidence['project_id'])}</h2>",
            "<p>Native USD MM. Bundled links are non-additive; top-down allocation remains NOT_EVALUATED.</p>",
            _table(
                ["Requirement", "Award references"],
                [
                    (
                        r["requirement_id"],
                        ", ".join(a["award_id"] for a in r["awards"]) or "not_public",
                    )
                    for r in evidence["requirements"]
                ],
            ),
            _table(
                [
                    "Event",
                    "Disclosed total (USD MM)",
                    "Eligible (USD MM)",
                    "Residual (USD MM)",
                    "Source",
                ],
                [
                    (
                        t["event_id"],
                        _money(t["value"]),
                        _range(t["eligible"]),
                        _range(t["residual"]),
                        t["source_url"],
                    )
                    for t in evidence["targets"]
                ],
            ),
            _table(
                ["Date", "Event", "Type", "Lane", "Currency", "Amount (USD MM)"],
                [
                    (
                        e["date"],
                        e["event_id"],
                        e["type"],
                        e["lane"],
                        e["currency"],
                        _range(e["amount"]),
                    )
                    for e in evidence["events"]
                ],
            ),
        ]
        parts[-1:-1] = tables
    return "\n".join(parts) + "\n"


def write_outputs(result, output):
    """Write deterministic outputs outside source directories; read back digests."""
    output.mkdir(parents=True, exist_ok=True)
    stream = io.StringIO(newline="")
    fields = [
        "project",
        "vintage",
        "provenance",
        "cell",
        "parameter",
        "category",
        "disposition",
        "value",
        "unit",
        "disclosed",
        "mapped",
        "modeled",
        "variance",
        "comparison_status",
        "requirement_ids",
        "mapping_status",
    ]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for p in result["projects"]:
        for row in p["crosswalk"]:
            writer.writerow(
                {**{k: p[k] for k in ("project", "vintage", "provenance")}, **row}
            )
    contents = {
        "fdas_reconciliation.json": _json(result),
        "fdas_reconciliation.csv": stream.getvalue(),
        "fdas_reconciliation.html": render_report(result),
    }
    if any(
        (output / name).exists()
        for name in (*contents, "fdas_reconciliation_manifest.json")
    ):
        raise FileExistsError("output already exists; use a fresh output directory")
    outputs = {}
    for name, text in sorted(contents.items()):
        path = output / name
        if path.exists():
            raise FileExistsError("output already exists; use a fresh output directory")
        data = text.encode("utf-8")
        with path.open("xb") as handle:
            handle.write(data)
        if path.read_bytes() != data:
            raise OSError("output readback mismatch")
        outputs[name] = hashlib.sha256(data).hexdigest()
    manifest = {
        "contract_version": "1",
        "generated_at_policy": "omitted for determinism",
        "arithmetic": "Decimal(str(native workbook value)); no FX or deflation",
        "display_policy": "one decimal USD; exact JSON/CSV",
        "outputs": outputs,
        "inputs": result["inventory"],
        "upstream": result["upstream"],
        "evidence_input_hashes": result.get("evidence_input_hashes", {}),
        "producer_hashes": result.get("producer_hashes", {}),
    }
    with (output / "fdas_reconciliation_manifest.json").open(
        "x", encoding="utf-8"
    ) as handle:
        handle.write(_json(manifest))
    if (
        json.loads((output / "fdas_reconciliation_manifest.json").read_text())
        != manifest
    ):
        raise OSError("manifest readback mismatch")
