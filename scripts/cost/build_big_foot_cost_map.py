#!/usr/bin/env python3
"""Build the deterministic, fail-closed Big Foot cost-map evidence pack."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from hashlib import sha256
from html import escape
import io
import json
import locale
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from typing import Callable
from urllib.parse import urlsplit

from openpyxl import __version__ as OPENPYXL_VERSION, load_workbook

from worldenergydata.cost.timeseries.cost_map import (
    BIG_FOOT_JOINT_SCENARIOS,
    allocate_big_foot_bands,
    largest_remainder_allocate,
    reconcile_big_foot_targets,
)
from worldenergydata.cost.timeseries.project_trace import build_big_foot_trace


HTML_REL = Path("reports/cost/big_foot_cost_map.html")
CSV_REL = Path("reports/cost/big_foot_cost_map_reconciliation.csv")
MANIFEST_REL = Path("data/modules/cost/curated/cost_map_contract_manifest.v1.json")
CURATED = "data/modules/cost/curated/"
BUILDER_REL = "scripts/cost/build_big_foot_cost_map.py"
# fmt: off
INPUT_PATHS = (BUILDER_REL, "config/analysis/lower_tertiary/fields/big_foot.yml", CURATED+"award_asset_links.csv",
    CURATED+"contract_awards.csv", CURATED+"cost_award_identity.csv", CURATED+"cost_event_identity.csv",
    CURATED+"cost_project_identity.csv", CURATED+"cost_requirement_identity.csv", CURATED+"cost_revision_trails.csv",
    CURATED+"fdas_project_cost_crosswalk.csv", CURATED+"project_asset_requirements.csv", CURATED+"sanctioned_projects.csv",
    "docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx", "docs/modules/bsee/analysis/production/FDAS_V30/financial_project_summary.xlsx",
    "docs/modules/bsee/analysis/production/FDAS_V30/lease_assumptions.xlsx", "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map.py",
    "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map_schema.py", "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/project_trace.py")
CSV_FIELDS = ("accounting_view", "direction", "row_kind", "additive", "project_id", "requirement_id",
    "award_id", "total_event_id", "scenario_id", "value_low_mm", "value_high_mm", "total_mm",
    "eligible_mm", "excluded_mm", "overlap_mm", "currency", "price_basis", "basis_year",
    "ownership_basis", "scope_basis", "capex_basis", "value_basis", "evidence_derivation",
    "source_provenance", "confidence", "counting_disposition", "mapping_status", "residual_mm",
    "unallocated_mm", "unreconciled_variance_mm", "value_coverage", "eligible_requirement_coverage",
    "linked_requirement_coverage", "source_identity", "source_locator", "scenario_status",
    "reuse_allowed", "rounding_policy", "assumption_vintage", "comparison_eligibility")
# fmt: on
# fmt: off

def escape_text(value: object) -> str:
    return escape(str(value), quote=True)

def safe_url(value: str) -> str | None:
    if not value or value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        return None
    try:
        parsed = urlsplit(value)
        _ = parsed.hostname, parsed.port
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None:
        return None
    return value

def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()

def _csv(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))

def _one(rows: list[dict[str, str]], **fields: str) -> dict[str, str]:
    found = [row for row in rows if all(row.get(key) == value for key, value in fields.items())]
    if len(found) != 1:
        raise ValueError(f"expected one row for {fields}, found {len(found)}")
    return found[0]

def _snapshot(root: Path) -> dict[str, bytes]:
    return {path: (root / path).read_bytes() for path in INPUT_PATHS}

def _validate_producer(root: Path, commit: str, snapshot: dict[str, bytes]) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("producer commit must be full 40-hex")
    try:
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=root,
            check=True,
            capture_output=True,
        )
        blob = subprocess.run(
            ["git", "show", f"{commit}:{BUILDER_REL}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as error:
        raise ValueError("producer commit must exist and contain builder") from error
    if _digest(blob) != _digest(snapshot[BUILDER_REL]):
        raise ValueError("producer builder blob does not match current builder")

def _frozen_curated(snapshot: dict[str, bytes]) -> TemporaryDirectory:
    frozen = TemporaryDirectory()
    root = Path(frozen.name)
    for path, data in snapshot.items():
        if path.startswith(CURATED):
            target = root / Path(path).name
            target.write_bytes(data)
    return frozen

def _awards(snapshot: dict[str, bytes]) -> list[dict[str, str]]:
    links, sources = (
        _csv(snapshot[CURATED + "award_asset_links.csv"]),
        _csv(snapshot[CURATED + "contract_awards.csv"]),
    )
    resolved = []
    for link in links:
        locator = link["SOURCE_LOCATOR"].split(":", 1)[1]
        predicates = dict(part.split("=", 1) for part in locator.split("|"))
        source = _one(sources, **predicates)
        if link["SOURCE_URL"] != source["SOURCE_URL"]:
            raise ValueError("award source URL mismatch")
        if safe_url(link["SOURCE_URL"]) is None:
            raise ValueError("unsafe award URL")
        low, high = Decimal(source["VALUE_LOW_MM"]), Decimal(source["VALUE_HIGH_MM"])
        if low != high:
            raise ValueError("pilot awards must be disclosed point values")
        resolved.append(
            {
                **link,
                "VALUE_MM": str(low),
                "BASIS_YEAR": source["AWARD_YEAR"],
                "CONTRACTOR": source["CONTRACTOR"],
            }
        )
    return resolved

def _fdas(
    snapshot: dict[str, bytes],
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str]]:
    rows = _csv(snapshot[CURATED + "fdas_project_cost_crosswalk.csv"])
    workbook_prefix = "docs/modules/bsee/analysis/production/FDAS_V30/"
    frozen = {}
    for row in rows:
        prior = frozen.setdefault(row["WORKBOOK_FILE"], row["WORKBOOK_SHA256"])
        if prior != row["WORKBOOK_SHA256"] or _digest(snapshot[workbook_prefix + row["WORKBOOK_FILE"]]) != prior:
            raise ValueError("workbook fingerprint mismatch")
    for filename in {row["WORKBOOK_FILE"] for row in rows}:
        workbook = load_workbook(
            io.BytesIO(snapshot[workbook_prefix + filename]),
            read_only=True,
            data_only=True,
        )
        for row in [item for item in rows if item["WORKBOOK_FILE"] == filename and item["WORKBOOK_VALUE"] and "!" not in item["WORKBOOK_CELL"]]:
            if Decimal(str(workbook[row["WORKBOOK_SHEET"]][row["WORKBOOK_CELL"]].value)) != Decimal(row["WORKBOOK_VALUE"]):
                raise ValueError("crosswalk value does not match workbook cell")
        workbook.close()
    additive = [row for row in rows if row["WORKBOOK_ROLE"] == "project_summary_total" and row["COUNTING_DISPOSITION"] == "included"]
    opex = [row for row in rows if row["WORKBOOK_ROLE"] == "project_summary_opex"]
    if {row["WORKBOOK_CATEGORY"] for row in additive} != {
        "facilities total",
        "drilling",
        "completion",
    } or len(opex) != 2:
        raise ValueError("FDAS additive/OPEX contract drift")
    stale = re.findall(
        r"(?m)^\s*total_mm_usd:\s*([0-9.]+)\s*$",
        snapshot["config/analysis/lower_tertiary/fields/big_foot.yml"].decode(),
    )
    if len(stale) != 1:
        raise ValueError("stale config estimate must resolve uniquely")
    return (
        additive,
        opex,
        {"value": stale[0], "classification": "stale configuration estimate"},
    )

def _row(**values: object) -> dict[str, str]:
    row = {field: "" for field in CSV_FIELDS}
    row.update({key: str(value) for key, value in values.items()})
    return row

def _award_rows(targets: dict, awards: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for event_id, target in targets.items():
        view = f"bottom_up:{event_id}"
        for award in awards:
            included = award["COUNTING_DISPOSITION"] == "included"
            rows.append(_row(accounting_view=view, direction="project_to_asset", row_kind="observed_component",
                additive=str(included).lower(), project_id=award["PROJECT_ID"], requirement_id=award["REQUIREMENT_IDS"],
                award_id=award["AWARD_ID"], total_event_id=event_id, value_low_mm=award["VALUE_MM"],
                value_high_mm=award["VALUE_MM"], currency="USD", price_basis="nominal", basis_year=award["BASIS_YEAR"],
                ownership_basis="gross" if included else "third_party", scope_basis="component" if included else "midstream",
                capex_basis="component_capex" if included else "non_capex", value_basis="point",
                evidence_derivation=award["EVIDENCE_DERIVATION"], source_provenance=award["SOURCE_PROVENANCE"],
                confidence=award["CONFIDENCE"], counting_disposition=award["COUNTING_DISPOSITION"], mapping_status="mapped",
                source_identity=award["AWARD_ID"], source_locator=award["SOURCE_LOCATOR"]))
        eligible_ids = {r for award in awards if award["COUNTING_DISPOSITION"] == "included" for r in award["REQUIREMENT_IDS"].split("|")}
        linked_ids = {r for award in awards for r in award["REQUIREMENT_IDS"].split("|")}
        rows.append(_row(accounting_view=view, direction="project_to_asset", row_kind="aggregate_reconciliation", additive="false",
            project_id="prj-000001", total_event_id=event_id, total_mm=target.target,
            eligible_mm=target.accounting.eligible.low, excluded_mm=target.accounting.excluded.low,
            overlap_mm=target.accounting.overlap.low, residual_mm=target.accounting.residual.low,
            unallocated_mm="0", unreconciled_variance_mm="0", currency=target.currency,
            value_coverage=target.accounting.eligible.low/target.target,
            eligible_requirement_coverage=f"{len(eligible_ids)}/8", linked_requirement_coverage=f"{len(linked_ids)}/8",
            source_identity=event_id, evidence_derivation="reconciled", source_provenance=target.provenance,
            confidence=target.confidence, counting_disposition="aggregate"))
    return rows

def _scenario_rows(targets: dict) -> list[dict[str, str]]:
    rows = []
    for event_id, target in targets.items():
        for scenario_id, scenario in BIG_FOOT_JOINT_SCENARIOS.items():
            view = f"scenario:{event_id}:{scenario_id}"
            for requirement, value in largest_remainder_allocate(target.target, scenario.shares).items():
                rows.append(_row(accounting_view=view, direction="project_to_asset", row_kind="scenario_allocation", additive="true",
                    project_id="prj-000001", requirement_id=requirement, total_event_id=event_id, scenario_id=scenario_id,
                    value_low_mm=value, value_high_mm=value, currency=target.currency, price_basis="nominal", basis_year=target.target_vintage,
                    ownership_basis="gross", scope_basis="project", capex_basis="project_capex", value_basis="point",
                    evidence_derivation="allocated", source_provenance="assumed", confidence="low", counting_disposition="included",
                    mapping_status="mapped", residual_mm=target.accounting.residual.low, unallocated_mm="0", unreconciled_variance_mm="0",
                    source_identity=event_id, scenario_status="proposed", reuse_allowed="false", rounding_policy="largest_remainder_0.01_USD_MM"))
    return rows

def _reverse_rows(awards: list[dict[str, str]]) -> list[dict[str, str]]:
    included = [award for award in awards if award["COUNTING_DISPOSITION"] == "included"]
    if len(included) != 1 or len(included[0]["REQUIREMENT_IDS"].split("|")) != 1:
        raise ValueError("inverse requires one singly-linked included award")
    award, quantum = included[0], Decimal("0.01")
    requirement = award["REQUIREMENT_IDS"]
    rows = []
    for scenario_id, scenario in BIG_FOOT_JOINT_SCENARIOS.items():
        implied = Decimal(award["VALUE_MM"]) / scenario.shares[requirement]
        rows.append(_row(accounting_view=f"inverse:{scenario_id}", direction="asset_to_project", row_kind="implied_project_total",
            additive="false", project_id=award["PROJECT_ID"], requirement_id=requirement, award_id=award["AWARD_ID"], scenario_id=scenario_id,
            value_low_mm=implied.quantize(quantum, rounding=ROUND_FLOOR), value_high_mm=implied.quantize(quantum, rounding=ROUND_CEILING),
            currency="USD", price_basis="nominal", basis_year=award["BASIS_YEAR"], ownership_basis="gross", scope_basis="project",
            capex_basis="project_capex", value_basis="range", evidence_derivation="allocated", source_provenance="assumed", confidence="low",
            counting_disposition="overlap", mapping_status="mapped", source_identity=award["AWARD_ID"], source_locator=award["SOURCE_LOCATOR"],
            scenario_status="proposed", reuse_allowed="false", rounding_policy="outward_0.01_USD_MM"))
    return rows

def _fdas_rows(additive: list[dict[str, str]], opex: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for source in additive + opex:
        value = Decimal(source["WORKBOOK_VALUE"]) / Decimal("1000000")
        rows.append(_row(accounting_view="fdas_development_capex" if source in additive else "fdas_opex",
            direction="project_to_asset", row_kind="fdas_assumption" if source in additive else "fdas_opex",
            additive=str(source in additive).lower(), project_id=source["PROJECT_ID"], requirement_id=source["REQUIREMENT_IDS"],
            value_low_mm=value, value_high_mm=value, currency=source["CURRENCY"], price_basis=source["PRICE_BASIS"],
            ownership_basis=source["OWNERSHIP_BASIS"], scope_basis=source["SCOPE_BASIS"], capex_basis=source["CAPEX_BASIS"],
            value_basis="point", evidence_derivation=source["EVIDENCE_DERIVATION"], source_provenance=source["SOURCE_PROVENANCE"],
            counting_disposition=source["COUNTING_DISPOSITION"], mapping_status=source["MAPPING_STATUS"],
            source_identity=f"FDAS_V30:{source['WORKBOOK_CATEGORY']}", source_locator=f"{source['WORKBOOK_SHEET']}!{source['WORKBOOK_CELL']}",
            rounding_policy="native_USD_divided_by_1000000", assumption_vintage=source["ASSUMPTION_VINTAGE"], comparison_eligibility="ineligible"))
    total = sum((Decimal(row["value_low_mm"]) for row in rows if row["accounting_view"] == "fdas_development_capex"), Decimal())
    rows.append(_row(accounting_view="fdas_development_capex", direction="project_to_asset", row_kind="fdas_total", additive="false",
        project_id="prj-000001", total_mm=total, currency="USD", capex_basis="project_capex", evidence_derivation="assumed",
        source_provenance="workbook_assumption", counting_disposition="aggregate", source_identity="FDAS_V30",
        assumption_vintage="FDAS_V30", comparison_eligibility="ineligible", rounding_policy="native_USD_divided_by_1000000"))
    return rows

def _trace_rows(trace: tuple) -> list[dict[str, str]]:
    rows = []
    for event in trace:
        money = event.money
        rows.append(_row(accounting_view="trace", direction="project_to_asset", row_kind="trace_event", additive="false",
            project_id=event.project_id, requirement_id=event.requirement_id or "", award_id=event.award_id or "", total_event_id=event.event_id,
            value_low_mm="" if money is None else money.low_value, value_high_mm="" if money is None else money.high_value,
            currency="" if money is None else money.currency, price_basis="" if money is None else money.price_basis,
            basis_year="" if money is None else money.basis_year, ownership_basis="" if money is None else money.ownership_basis,
            scope_basis="" if money is None else money.scope_basis, capex_basis="" if money is None else money.capex_basis,
            value_basis="not_public" if money is None else money.value_basis, evidence_derivation=event.evidence.derivation,
            source_provenance=event.evidence.source_provenance, confidence=event.evidence.confidence,
            counting_disposition="trace_only", mapping_status="unmapped" if money is None else "mapped",
            source_identity=event.event_id, source_locator=event.evidence.source_locator))
    return rows

def _html(context: dict) -> str:
    requirements, awards, targets = (
        context["requirements"],
        context["awards"],
        context["targets"],
    )
    req = "".join(f"<tr><td>{escape_text(r['REQUIREMENT_ID'])}</td><td>{escape_text(r['WORK_PACKAGE'])}</td><td>{escape_text(r['ASSET_TYPE'])}</td><td>{escape_text(r['QUANTITY'])} {escape_text(r['QUANTITY_UNIT'])}</td></tr>" for r in requirements)
    links = "".join(f'<li class="observed">{escape_text(a["AWARD_ID"])} {escape_text(a["CONTRACTOR"])} — <a href="{escape_text(a["SOURCE_URL"])}">{escape_text(a["COUNTING_DISPOSITION"])}</a> once; {escape_text(a["COUNTING_REASON"] or "component floor")}; {escape_text(a["VALUE_MM"])} USD MM</li>' for a in awards)
    ledger = "".join(f"<tr><td>{escape_text(e)}</td><td>{t.target}</td><td>{t.accounting.eligible.low}</td><td>{t.accounting.excluded.low}</td><td>{t.accounting.overlap.low}</td><td>{t.accounting.residual.low}</td><td>{t.accounting.eligible.low / t.target}</td><td>1/8</td><td>2/8</td></tr>" for e, t in targets.items())
    scenarios = "".join(
        f'<li class="allocated">{escape_text(e)}/{escape_text(sid)}: {escape_text(" ".join(f"{rid}={value}" for rid, value in largest_remainder_allocate(t.target, s.shares).items()))} — allocated; assumed; proposed; low confidence; reuse_allowed=false</li>'
        for e, t in targets.items()
        for sid, s in BIG_FOOT_JOINT_SCENARIOS.items()
    )
    trace = "".join(
        f"<tr><td>{escape_text(e.effective_date.label)}</td><td>{escape_text(e.event_id)}</td><td>{escape_text(e.lane)}</td><td>{escape_text(e.event_type)}</td><td>{escape_text('not_public' if e.money is None else str(e.money.low_value) + ' ' + e.money.currency + ' MM')}</td><td>{escape_text(e.evidence.source_locator)}</td></tr>"
        for e in context["trace"]
    )
    add, opex, stale = context["fdas_additive"], context["fdas_opex"], context["stale"]
    values = [Decimal(r["WORKBOOK_VALUE"]) / Decimal("1000000") for r in add]
    bridge = " + ".join(f"{v:,.1f}" for v in values) + f" = {sum(values):,.1f} USD MM"
    opex_text = "; ".join(f"{r['WORKBOOK_CATEGORY']} {Decimal(r['WORKBOOK_VALUE']):,.0f} {r['CURRENCY']} ({r['WORKBOOK_SHEET']}!{r['WORKBOOK_CELL']})" for r in opex)
    sources = "".join(f'<li>{escape_text(a["AWARD_ID"])}: <a href="{escape_text(a["SOURCE_URL"])}">{escape_text(a["SOURCE_LOCATOR"])}</a></li>' for a in awards)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Big Foot cost map</title><style>body{{font:15px system-ui;margin:2rem;max-width:1200px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #bbb;padding:.35rem}}.observed{{border-left:5px solid #176b3a}}.allocated{{border-left:5px solid #9a6700}}</style></head><body>
<h1>Big Foot bidirectional cost map</h1><p><b>Legend:</b> <span class="observed">observed/disclosed</span>; <span class="allocated">allocated/assumed/proposed/low confidence</span>; unknown, unmapped, not_public.</p>
<h2>Required assets</h2><table><tr><th>ID</th><th>Lane</th><th>Asset</th><th>Quantity</th></tr>{req}</table><h2>Awards</h2><ul>{links}</ul>
<h2>Bottom-up ledgers</h2><table><tr><th>Event</th><th>Total</th><th>eligible</th><th>excluded</th><th>overlap</th><th>residual</th><th>value coverage</th><th>eligible requirement coverage</th><th>linked requirement coverage</th></tr>{ledger}</table><p>residual, unallocated, and unreconciled variance remain distinct.</p>
<h2>Joint scenarios</h2><ul>{scenarios}</ul><p>Component envelopes are non-additive: {escape_text(str({e: {r: (str(b.low), str(b.high)) for r, b in allocate_big_foot_bands(t.target).items()} for e, t in targets.items()}))}</p><h2>Dated trace</h2><p>Five events; no interpolation.</p><table><tr><th>Date</th><th>Event</th><th>Lane</th><th>Type</th><th>Value</th><th>Source identity</th></tr>{trace}</table>
<h2>FDAS assumption bridge</h2><p class="allocated">{escape_text(bridge)}. Native workbook USD divided by 1,000,000 to USD MM; assumed/workbook_assumption; FDAS_V30; comparison ineligible; not a disclosure.</p><p><b>OPEX — excluded from development CAPEX:</b> {escape_text(opex_text)}.</p><p><b>installation/hookup:</b> req-000007 unmapped. {Decimal(stale["value"]):,.0f} USD MM is a {escape_text(stale["classification"])}, not workbook truth.</p>
<h2>Sources and gaps</h2><ul>{sources}</ul><p>Unknown/not_public/unmapped findings remain visible.</p><ul><li>taxonomy — pending</li><li>accounting — pending</li><li>scenarios — pending</li><li>portfolio reuse — pending; reuse_allowed=false</li><li>external send — pending owner authorization; email not sent</li></ul></body></html>"""

def _workbooks(context: dict) -> list[dict]:
    rows = context["fdas_all"]
    result = []
    for filename in sorted({row["WORKBOOK_FILE"] for row in rows}):
        selected = [row for row in rows if row["WORKBOOK_FILE"] == filename]
        cells = sorted({cell if "!" in cell else f"{row['WORKBOOK_SHEET']}!{cell}" for row in selected if (cell := row["WORKBOOK_CELL"])})
        result.append({"file":filename,"sha256":selected[0]["WORKBOOK_SHA256"],"allowlisted_cells":cells,
            "extraction":{"library":"openpyxl","version":OPENPYXL_VERSION,"mode":"read_only,data_only"}})
    return result

def _manifest(context: dict, snapshot: dict[str, bytes], output: Path, epoch: int, commit: str) -> dict:
    scenarios=[{"scenario_id":key,"shares":{rid:str(value) for rid,value in s.shares.items()},"derivation":"assumed",
        "status":"proposed","confidence":"low","reuse_allowed":False} for key,s in BIG_FOOT_JOINT_SCENARIOS.items()]
    schema = "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map_schema.py"
    return {"contract_version":"1.0.0","schema":{"path":schema,"sha256":_digest(snapshot[schema])},
        "inputs":[{"path":p,"sha256":_digest(snapshot[p])} for p in sorted(INPUT_PATHS)],
        "producer":{"commit":commit,"commit_policy":"exact_builder_containing_commit","builder_path":BUILDER_REL,
                    "builder_sha256":_digest(snapshot[BUILDER_REL]),"tool_version":"1.1.0"},
        "generated_at":{"policy":"SOURCE_DATE_EPOCH","epoch":epoch,
                        "utc":datetime.fromtimestamp(epoch,timezone.utc).isoformat().replace("+00:00","Z"),"locale":"C"},
        "decimal_policy":{"arithmetic":"Decimal","source_scale":"native","output_quantum":"0.01 USD MM",
                          "allocation_rounding":"largest_remainder","inverse_rounding":"outward","rounding_boundary":"output_only"},
        "controlled_ids":{"projects":["prj-000001"],"awards":[a["AWARD_ID"] for a in context["awards"]],
                          "requirements":[r["REQUIREMENT_ID"] for r in context["requirements"]],"events":[e.event_id for e in context["trace"]]},
        "scenarios":scenarios,"workbooks":_workbooks(context),
        "outputs":[{"path":str(p),"sha256":_digest((output/p).read_bytes())} for p in (HTML_REL,CSV_REL)],
        "policies":{"email":"not_sent","external_send":"pending_owner_authorization","workbooks":"read_only","reuse_allowed":False},
        "owner_decision":{"status":"pending","items":["taxonomy","accounting","scenarios","portfolio reuse"]}}

def _context(snapshot: dict[str, bytes]) -> dict:
    frozen = _frozen_curated(snapshot)
    try:
        targets = reconcile_big_foot_targets(Path(frozen.name))
        trace = build_big_foot_trace(Path(frozen.name))
    finally:
        frozen.cleanup()
    additive, opex, stale = _fdas(snapshot)
    return {"targets":targets,"trace":trace,"awards":_awards(snapshot),
        "requirements":_csv(snapshot[CURATED+"project_asset_requirements.csv"]),
        "fdas_all":_csv(snapshot[CURATED+"fdas_project_cost_crosswalk.csv"]),
        "fdas_additive":additive,"fdas_opex":opex,"stale":stale}

def build_outputs(*, repo_root: Path, output_root: Path, source_date_epoch: int, producer_commit: str,
                  before_final_hash: Callable[[], None] | None = None) -> None:
    if locale.setlocale(locale.LC_ALL, "C") != "C" or source_date_epoch < 0:
        raise ValueError("locale C and nonnegative SOURCE_DATE_EPOCH are required")
    snapshot = _snapshot(repo_root)
    _validate_producer(repo_root, producer_commit, snapshot)
    context = _context(snapshot)
    rows = _award_rows(context["targets"], context["awards"]) + _scenario_rows(context["targets"]) + _reverse_rows(context["awards"]) + _fdas_rows(context["fdas_additive"], context["fdas_opex"]) + _trace_rows(context["trace"])
    html_path, csv_path = output_root / HTML_REL, output_root / CSV_REL
    html_path.parent.mkdir(parents=True,exist_ok=True)
    html_path.write_text(_html(context),encoding="utf-8",newline="\n")
    csv_path.parent.mkdir(parents=True,exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=CSV_FIELDS,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest_path = output_root / MANIFEST_REL
    manifest_path.parent.mkdir(parents=True,exist_ok=True)
    manifest_path.write_text(json.dumps(_manifest(context,snapshot,output_root,source_date_epoch,producer_commit),sort_keys=True,indent=2)+"\n",encoding="utf-8",newline="\n")
    if before_final_hash:
        before_final_hash()
    if _snapshot(repo_root) != snapshot:
        raise RuntimeError("input changed during build")

def main() -> None:
    epoch, commit = (
        os.environ.get("SOURCE_DATE_EPOCH"),
        os.environ.get("PRODUCER_COMMIT"),
    )
    if epoch is None or commit is None:
        raise SystemExit("SOURCE_DATE_EPOCH and PRODUCER_COMMIT are required")
    root = Path(__file__).resolve().parents[2]
    build_outputs(
        repo_root=root,
        output_root=root,
        source_date_epoch=int(epoch),
        producer_commit=commit,
    )


if __name__ == "__main__":
    main()
