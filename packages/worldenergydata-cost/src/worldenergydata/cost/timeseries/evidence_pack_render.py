"""Render deterministic HTML and manifest content for cost evidence packs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from html import escape
from pathlib import Path

from worldenergydata.cost.timeseries.cost_map import (
    BIG_FOOT_JOINT_SCENARIOS,
    allocate_big_foot_bands,
    largest_remainder_allocate,
)
from worldenergydata.cost.timeseries.evidence_pack import (
    AWARD_IDS,
    BUILDER_REL,
    CSV_REL,
    EVENT_IDS,
    HTML_REL,
    INPUT_PATHS,
    PROJECT_IDS,
    REQUIREMENT_IDS,
    csv_row,
    digest,
)


def select_fields(source: dict, spec: str) -> dict:
    pairs = (item.split(":", 1) for item in spec.split())
    return {target: source[origin] for target, origin in pairs}


def fixed_fields(spec: str) -> dict:
    return dict(item.split("=", 1) for item in spec.split())


def fdas_gap_row(source: dict[str, str]) -> dict[str, str]:
    fields = {
        target: source[origin]
        for target, origin in (
            item.split(":", 1)
            for item in "project_id:PROJECT_ID requirement_id:REQUIREMENT_IDS currency:CURRENCY price_basis:PRICE_BASIS ownership_basis:OWNERSHIP_BASIS scope_basis:SCOPE_BASIS capex_basis:CAPEX_BASIS evidence_derivation:EVIDENCE_DERIVATION source_provenance:SOURCE_PROVENANCE counting_disposition:COUNTING_DISPOSITION mapping_status:MAPPING_STATUS assumption_vintage:ASSUMPTION_VINTAGE comparison_eligibility:COMPARISON_ELIGIBILITY".split()
        )
    }
    return csv_row(
        **fields,
        accounting_view="fdas_development_capex",
        direction="project_to_asset",
        row_kind="fdas_gap",
        additive="false",
        value_basis="not_public",
        source_identity=f"FDAS_V30:{source['WORKBOOK_CATEGORY']}",
        source_locator=f"{source['WORKBOOK_FILE']}:{source['WORKBOOK_SHEET']}",
    )


def _esc(value: object) -> str:
    return escape(str(value), quote=True)


def _html_sections(context: dict) -> dict[str, str]:
    requirements, awards, targets = (
        context["requirements"],
        context["awards"],
        context["targets"],
    )
    required = "".join(
        f"<tr><td>{_esc(r['REQUIREMENT_ID'])}</td><td>{_esc(r['WORK_PACKAGE'])}</td><td>{_esc(r['ASSET_TYPE'])}</td><td>{_esc(r['QUANTITY'])} {_esc(r['QUANTITY_UNIT'])}</td></tr>"
        for r in requirements
    )
    links = "".join(
        f'<li class="observed">{_esc(a["AWARD_ID"])} {_esc(a["CONTRACTOR"])} — <a href="{_esc(a["SOURCE_URL"])}">{_esc(a["COUNTING_DISPOSITION"])}</a> once; {_esc(a["COUNTING_REASON"] or "component floor")}; {_esc(a["VALUE_MM"])} USD MM</li>'
        for a in awards
    )
    eligible = {
        rid
        for a in awards
        if a["COUNTING_DISPOSITION"] == "included"
        for rid in a["REQUIREMENT_IDS"].split("|")
    }
    linked = {rid for a in awards for rid in a["REQUIREMENT_IDS"].split("|")}
    ledger = "".join(
        f"<tr><td>{_esc(e)}</td><td>{t.target}</td><td>{t.accounting.eligible.low}</td><td>{t.accounting.excluded.low}</td><td>{t.accounting.overlap.low}</td><td>{t.accounting.residual.low}</td><td>{t.accounting.eligible.low / t.target}</td><td>{len(eligible)}/{len(REQUIREMENT_IDS)}</td><td>{len(linked)}/{len(REQUIREMENT_IDS)}</td></tr>"
        for e, t in targets.items()
    )
    scenarios = "".join(
        f'<li class="allocated">{_esc(e)}/{_esc(sid)}: {_esc(" ".join(f"{rid}={value}" for rid, value in largest_remainder_allocate(t.target, s.shares).items()))} — allocated; assumed; proposed; low confidence; reuse_allowed=false</li>'
        for e, t in targets.items()
        for sid, s in BIG_FOOT_JOINT_SCENARIOS.items()
    )
    trace = "".join(
        f"<tr><td>{_esc(e.effective_date.label)}</td><td>{_esc(e.event_id)}</td><td>{_esc(e.lane)}</td><td>{_esc(e.event_type)}</td><td>{_esc('not_public' if e.money is None else str(e.money.low_value) + ' ' + e.money.currency + ' MM')}</td><td>{_esc(e.evidence.source_locator)}</td></tr>"
        for e in context["trace"]
    )
    return {
        "required": required,
        "links": links,
        "ledger": ledger,
        "scenarios": scenarios,
        "trace": trace,
    }


def _fdas_sections(context: dict) -> tuple[str, str, str]:
    add, opex = context["fdas_additive"], context["fdas_opex"]
    values = [Decimal(row["WORKBOOK_VALUE"]) / Decimal("1000000") for row in add]
    bridge = (
        " + ".join(f"{value:,.1f}" for value in values)
        + f" = {sum(values):,.1f} USD MM"
    )
    opex_text = "; ".join(
        f"{row['WORKBOOK_CATEGORY']} {Decimal(row['WORKBOOK_VALUE']):,.0f} {row['CURRENCY']} ({row['WORKBOOK_SHEET']}!{row['WORKBOOK_CELL']})"
        for row in opex
    )
    sources = "".join(
        f'<li>{_esc(a["AWARD_ID"])}: <a href="{_esc(a["SOURCE_URL"])}">{_esc(a["SOURCE_LOCATOR"])}</a></li>'
        for a in context["awards"]
    )
    return bridge, opex_text, sources


def render_html(context: dict) -> str:
    sections = _html_sections(context)
    bridge, opex, sources = _fdas_sections(context)
    envelopes = {
        event: {
            rid: (str(band.low), str(band.high))
            for rid, band in allocate_big_foot_bands(target.target).items()
        }
        for event, target in context["targets"].items()
    }
    stale = context["stale"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Big Foot cost map</title><style>body{{font:15px system-ui;margin:2rem;max-width:1200px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #bbb;padding:.35rem}}.observed{{border-left:5px solid #176b3a}}.allocated{{border-left:5px solid #9a6700}}</style></head><body>
<h1>Big Foot bidirectional cost map</h1><p><b>Legend:</b> <span class="observed">observed/disclosed</span>; <span class="allocated">allocated/assumed/proposed/low confidence</span>; unknown, unmapped, not_public.</p>
<h2>Required assets</h2><table><tr><th>ID</th><th>Lane</th><th>Asset</th><th>Quantity</th></tr>{sections["required"]}</table><h2>Awards</h2><ul>{sections["links"]}</ul>
<h2>Bottom-up ledgers</h2><table><tr><th>Event</th><th>Total</th><th>eligible</th><th>excluded</th><th>overlap</th><th>residual</th><th>value coverage</th><th>eligible requirement coverage</th><th>linked requirement coverage</th></tr>{sections["ledger"]}</table><p>residual, unallocated, and unreconciled variance remain distinct.</p>
<h2>Joint scenarios</h2><ul>{sections["scenarios"]}</ul><p>Component envelopes are non-additive: {_esc(envelopes)}</p><h2>Dated trace</h2><p>{len(context["trace"])} events; no interpolation.</p><table><tr><th>Date</th><th>Event</th><th>Lane</th><th>Type</th><th>Value</th><th>Source identity</th></tr>{sections["trace"]}</table>
<h2>FDAS assumption bridge</h2><p class="allocated">{_esc(bridge)}. Native workbook USD divided by 1,000,000 to USD MM; assumed/workbook_assumption; FDAS_V30; comparison ineligible; not a disclosure.</p><p><b>OPEX — excluded from development CAPEX:</b> {_esc(opex)}.</p><p><b>installation/hookup:</b> req-000007 unmapped. {Decimal(stale["value"]):,.0f} USD MM is a {_esc(stale["classification"])}, not workbook truth.</p>
<h2>Sources and gaps</h2><ul>{sources}</ul><p>Unknown/not_public/unmapped findings remain visible.</p><ul><li>taxonomy — pending</li><li>accounting — pending</li><li>scenarios — pending</li><li>portfolio reuse — pending; reuse_allowed=false</li><li>external send — pending owner authorization; email not sent</li></ul></body></html>"""


def workbook_manifest(context: dict, version: str) -> list[dict]:
    rows, result = context["fdas_all"], []
    for filename in sorted({row["WORKBOOK_FILE"] for row in rows}):
        selected = [row for row in rows if row["WORKBOOK_FILE"] == filename]
        cells = sorted(
            {
                cell if "!" in cell else f"{row['WORKBOOK_SHEET']}!{cell}"
                for row in selected
                if (cell := row["WORKBOOK_CELL"])
            }
        )
        result.append(
            {
                "file": filename,
                "sha256": selected[0]["WORKBOOK_SHA256"],
                "allowlisted_cells": cells,
                "extraction": {
                    "library": "openpyxl",
                    "version": version,
                    "mode": "read_only,data_only",
                },
            }
        )
    return result


def manifest_payload(
    context: dict,
    frozen: dict[str, bytes],
    output: Path,
    epoch: int,
    commit: str,
    openpyxl_version: str,
) -> dict:
    payload = _manifest_provenance(frozen, epoch, commit)
    scenarios = [
        {
            "scenario_id": key,
            "shares": {rid: str(value) for rid, value in scenario.shares.items()},
            "derivation": "assumed",
            "status": "proposed",
            "confidence": "low",
            "reuse_allowed": False,
        }
        for key, scenario in BIG_FOOT_JOINT_SCENARIOS.items()
    ]
    payload.update(
        {
            "scenarios": scenarios,
            "workbooks": workbook_manifest(context, openpyxl_version),
            "outputs": [
                {"path": str(path), "sha256": digest((output / path).read_bytes())}
                for path in (HTML_REL, CSV_REL)
            ],
            "policies": {
                "email": "not_sent",
                "external_send": "pending_owner_authorization",
                "workbooks": "read_only",
                "reuse_allowed": False,
            },
            "owner_decision": {
                "status": "pending",
                "items": ["taxonomy", "accounting", "scenarios", "portfolio reuse"],
            },
        }
    )
    return payload


def _manifest_provenance(frozen: dict[str, bytes], epoch: int, commit: str) -> dict:
    schema = "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map_schema.py"
    return {
        "contract_version": "1.0.0",
        "schema": {"path": schema, "sha256": digest(frozen[schema])},
        "inputs": [
            {"path": path, "sha256": digest(frozen[path])}
            for path in sorted(INPUT_PATHS)
        ],
        "producer": {
            "commit": commit,
            "commit_policy": "exact_builder_containing_commit",
            "builder_path": BUILDER_REL,
            "builder_sha256": digest(frozen[BUILDER_REL]),
            "tool_version": "1.2.0",
        },
        "generated_at": {
            "policy": "SOURCE_DATE_EPOCH",
            "epoch": epoch,
            "utc": datetime.fromtimestamp(epoch, timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "locale": "C",
        },
        "decimal_policy": {
            "arithmetic": "Decimal",
            "source_scale": "native",
            "output_quantum": "0.01 USD MM",
            "allocation_rounding": "largest_remainder",
            "inverse_rounding": "outward",
            "rounding_boundary": "output_only",
        },
        "controlled_ids": {
            "projects": list(PROJECT_IDS),
            "awards": list(AWARD_IDS),
            "requirements": list(REQUIREMENT_IDS),
            "events": list(EVENT_IDS),
        },
    }


def canonical_manifest(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"
