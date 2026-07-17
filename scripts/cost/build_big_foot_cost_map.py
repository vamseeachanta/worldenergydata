#!/usr/bin/env python3
"""Build the deterministic Big Foot cost-map evidence pack."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from openpyxl import __version__ as OPENPYXL_VERSION

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
CURATED_REL = Path("data/modules/cost/curated")
# fmt: off
INPUT_PATHS = (
    "config/analysis/lower_tertiary/fields/big_foot.yml", "data/modules/cost/curated/award_asset_links.csv", "data/modules/cost/curated/contract_awards.csv", "data/modules/cost/curated/cost_award_identity.csv",
    "data/modules/cost/curated/cost_event_identity.csv", "data/modules/cost/curated/cost_project_identity.csv", "data/modules/cost/curated/cost_requirement_identity.csv", "data/modules/cost/curated/cost_revision_trails.csv",
    "data/modules/cost/curated/fdas_project_cost_crosswalk.csv", "data/modules/cost/curated/project_asset_requirements.csv", "data/modules/cost/curated/sanctioned_projects.csv", "docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx", "docs/modules/bsee/analysis/production/FDAS_V30/financial_project_summary.xlsx",
    "docs/modules/bsee/analysis/production/FDAS_V30/lease_assumptions.xlsx",
    "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map.py", "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/project_trace.py",
)
# fmt: on
# fmt: off
CSV_FIELDS = (
    "direction", "row_kind", "additive", "project_id", "requirement_id", "award_id", "total_event_id",
    "scenario_id", "value_low_mm", "value_high_mm", "currency", "price_basis", "basis_year",
    "ownership_basis", "scope_basis", "capex_basis", "value_basis", "evidence_derivation",
    "source_provenance", "confidence", "counting_disposition", "mapping_status", "residual_mm",
    "unallocated_mm", "unreconciled_variance_mm", "source_identity", "scenario_status", "reuse_allowed", "rounding_policy",
)
# fmt: on


def escape_text(value: object) -> str:
    """Escape untrusted content for HTML text or quoted attributes."""
    return escape(str(value), quote=True)


def safe_url(value: str) -> str | None:
    """Return a publishable HTTP(S) URL, rejecting ambiguous authority data."""
    if not value or any(ord(char) < 32 for char in value):
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _money(value: Decimal) -> str:
    return f"{value:,.1f}"


def _link(label: str, url: str) -> str:
    safe = safe_url(url)
    if safe is None:
        return escape_text(label)
    return f'<a href="{escape_text(safe)}">{escape_text(label)}</a>'


def _empty_row(**values: object) -> dict[str, str]:
    row = {field: "" for field in CSV_FIELDS}
    row.update({key: str(value) for key, value in values.items()})
    return row


def _scenario_rows(targets: dict) -> list[dict[str, str]]:
    # fmt: off
    rows = []
    for event_id, target in targets.items():
        for scenario_id, scenario in BIG_FOOT_JOINT_SCENARIOS.items():
            allocations = largest_remainder_allocate(target.target, scenario.shares)
            for requirement_id, value in allocations.items():
                rows.append(_empty_row(
                    direction="project_to_asset", row_kind="scenario_allocation", additive="true",
                    project_id="prj-000001", requirement_id=requirement_id, total_event_id=event_id,
                    scenario_id=scenario_id, value_low_mm=value, value_high_mm=value, currency="USD",
                    price_basis="nominal", basis_year=target.target_vintage, ownership_basis="gross",
                    scope_basis="project", capex_basis="project_capex", value_basis="point",
                    evidence_derivation="allocated", source_provenance="assumed", confidence="low",
                    counting_disposition="included", mapping_status="mapped",
                    residual_mm=target.accounting.residual.low, unallocated_mm="0",
                    unreconciled_variance_mm="0", source_identity=event_id, scenario_status="proposed",
                    reuse_allowed="false", rounding_policy="largest_remainder_0.01_USD_MM",
                ))
    # fmt: on
    return rows


def _observed_rows(targets: dict) -> list[dict[str, str]]:
    # fmt: off
    rows = []
    awards = (
        ("awd-000001", "req-000005", "45", "included", "component_capex"),
        ("awd-000002", "req-000006", "200", "excluded", "non_capex"),
    )
    for event_id, target in targets.items():
        for award_id, requirement_id, value, disposition, capex in awards:
            rows.append(_empty_row(
                direction="project_to_asset", row_kind="observed_component",
                additive=str(disposition == "included").lower(), project_id="prj-000001",
                requirement_id=requirement_id, award_id=award_id, total_event_id=event_id,
                value_low_mm=value, value_high_mm=value, currency="USD", price_basis="nominal",
                basis_year="2011" if award_id.endswith("1") else "2009",
                ownership_basis="gross" if disposition == "included" else "third_party",
                scope_basis="component" if disposition == "included" else "midstream",
                capex_basis=capex, value_basis="point", evidence_derivation="disclosed",
                source_provenance="operator", confidence="high", counting_disposition=disposition,
                mapping_status="mapped", residual_mm=target.accounting.residual.low,
                source_identity=award_id,
            ))
    # fmt: on
    return rows


def _reverse_rows() -> list[dict[str, str]]:
    # fmt: off
    rows = []
    component = Decimal("45")
    quantum = Decimal("0.01")
    for scenario_id, scenario in BIG_FOOT_JOINT_SCENARIOS.items():
        implied = component / scenario.shares["req-000005"]
        low = implied.quantize(quantum, rounding=ROUND_FLOOR)
        high = implied.quantize(quantum, rounding=ROUND_CEILING)
        rows.append(_empty_row(
            direction="asset_to_project", row_kind="implied_project_total", additive="false",
            project_id="prj-000001", requirement_id="req-000005", award_id="awd-000001",
            scenario_id=scenario_id, value_low_mm=low, value_high_mm=high, currency="USD",
            price_basis="nominal", basis_year="2011", ownership_basis="gross",
            scope_basis="project", capex_basis="project_capex", value_basis="range",
            evidence_derivation="allocated", source_provenance="assumed", confidence="low",
            counting_disposition="overlap", mapping_status="mapped", source_identity="awd-000001",
            scenario_status="proposed", reuse_allowed="false", rounding_policy="outward_0.01_USD_MM",
        ))
    # fmt: on
    return rows


def _fdas_rows() -> list[dict[str, str]]:
    # fmt: off
    values = (("req-000001|req-000002|req-000003|req-000005|req-000008", "2730", "facilities"),
              ("req-000004", "965.6", "drilling"), ("req-000004", "821.7", "completion"))
    return [_empty_row(
        direction="project_to_asset", row_kind="fdas_assumption", additive="true",
        project_id="prj-000001", requirement_id=requirements, value_low_mm=value,
        value_high_mm=value, currency="USD", price_basis="nominal", ownership_basis="gross",
        scope_basis="project", capex_basis="project_capex", value_basis="point",
        evidence_derivation="assumed", source_provenance="workbook_assumption", confidence="low",
        counting_disposition="included", mapping_status="mapped", source_identity=f"fdas:{category}",
        reuse_allowed="false", rounding_policy="native_USD_divided_by_1000000",
    ) for requirements, value, category in values]
    # fmt: on


def _gap_rows() -> list[dict[str, str]]:
    # fmt: off
    return [
        _empty_row(direction="project_to_asset", row_kind="trace_gap", additive="false",
                   project_id="prj-000001", total_event_id="evt-000005", value_basis="not_public",
                   evidence_derivation="todo", source_provenance="secondary_operator_confirmed",
                   confidence="low", counting_disposition="excluded", mapping_status="unmapped",
                   source_identity="evt-000005"),
        _empty_row(direction="project_to_asset", row_kind="fdas_gap", additive="false",
                   project_id="prj-000001", requirement_id="req-000007", value_basis="not_public",
                   evidence_derivation="assumed", source_provenance="workbook_assumption",
                   confidence="low", counting_disposition="excluded", mapping_status="unmapped",
                   source_identity="fdas:installation/hookup"),
    ]
    # fmt: on


def _write_reconciliation(path: Path, targets: dict) -> None:
    rows = (
        _observed_rows(targets)
        + _scenario_rows(targets)
        + _reverse_rows()
        + _fdas_rows()
        + _gap_rows()
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _requirements_html(requirements: list[dict[str, str]]) -> str:
    return "".join(
        f"<tr><td>{escape_text(row['REQUIREMENT_ID'])}</td>"
        f"<td>{escape_text(row['WORK_PACKAGE'])}</td>"
        f"<td>{escape_text(row['ASSET_TYPE'])}</td>"
        f"<td>{escape_text(row['QUANTITY'])} {escape_text(row['QUANTITY_UNIT'])}</td>"
        f"<td>{escape_text(row['EVIDENCE_DERIVATION'])}</td></tr>"
        for row in requirements
    )


def _scenarios_html(targets: dict) -> str:
    blocks = []
    for event_id, target in targets.items():
        bands = allocate_big_foot_bands(target.target)
        for scenario_id, scenario in BIG_FOOT_JOINT_SCENARIOS.items():
            values = largest_remainder_allocate(target.target, scenario.shares)
            cells = " ".join(f"{key}={_money(value)}" for key, value in values.items())
            blocks.append(
                f'<li class="allocated"><b>{escape_text(event_id)} / '
                f"{escape_text(scenario_id)}</b>: {escape_text(cells)} — allocated; "
                "assumed; proposed; low confidence; reuse_allowed=false</li>"
            )
        envelope = " ".join(
            f"{key}={_money(value.low)}–{_money(value.high)}"
            for key, value in bands.items()
        )
        blocks.append(
            f'<li class="allocated">non-additive component envelope: '
            f"{escape_text(envelope)}</li>"
        )
    return "".join(blocks)


def _trace_html(trace: tuple) -> str:
    rows = []
    for event in trace:
        value = (
            "not_public"
            if event.money is None
            else f"{_money(event.money.low_value)} {event.money.currency} MM"
        )
        rows.append(
            f"<tr><td>{escape_text(event.effective_date.label)}</td>"
            f"<td>{escape_text(event.event_id)}</td><td>{escape_text(event.lane)}</td>"
            f"<td>{escape_text(event.event_type)}</td><td>{escape_text(value)}</td>"
            f"<td>{escape_text(event.evidence.confidence)}</td></tr>"
        )
    return "".join(rows)


def _report_html(root: Path, targets: dict) -> str:
    curated = root / CURATED_REL
    requirements = _read_csv(curated / "project_asset_requirements.csv")
    links = _read_csv(curated / "award_asset_links.csv")
    trace = build_big_foot_trace(curated)
    award_html = "".join(
        f'<li class="observed">{escape_text(row["AWARD_ID"])} — '
        f"{_link(row['COUNTING_DISPOSITION'], row['SOURCE_URL'])} once; "
        f"{escape_text(row['COUNTING_REASON'] or 'component floor')}</li>"
        for row in links
    )
    ledger = "".join(
        f"<tr><td>{escape_text(event_id)}</td><td>{_money(target.target)}</td>"
        f"<td>{_money(target.accounting.eligible.low)}</td>"
        f"<td>{_money(target.accounting.excluded.low)}</td>"
        f"<td>{_money(target.accounting.overlap.low)}</td>"
        f"<td>{_money(target.accounting.residual.low)}</td><td>1/8 value; 2/8 linked</td></tr>"
        for event_id, target in targets.items()
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Big Foot cost map</title>
<style>body{{font:15px system-ui;margin:2rem;max-width:1200px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #bbb;padding:.35rem}}.observed{{border-left:5px solid #176b3a;padding-left:.5rem}}.allocated{{border-left:5px solid #9a6700;padding-left:.5rem}}.gap{{background:#fff3cd}}</style></head>
<body><h1>Big Foot bidirectional cost map</h1>
<p><b>Evidence legend:</b> <span class="observed">observed/disclosed</span>; <span class="allocated">allocated/assumed/proposed/low confidence</span>; <span class="gap">unknown, unmapped, or not_public finding</span>.</p>
<h2>Required assets and work packages</h2><table><tr><th>ID</th><th>Lane</th><th>Asset</th><th>Quantity</th><th>Evidence</th></tr>{_requirements_html(requirements)}</table>
<h2>Award links</h2><ul>{award_html}</ul><p>GE is included once. Enbridge is excluded from Chevron project CAPEX as third-party midstream scope.</p>
<h2>Bottom-up ledgers</h2><table><tr><th>Total event</th><th>Total USD MM</th><th>eligible</th><th>excluded</th><th>overlap</th><th>residual</th><th>coverage</th></tr>{ledger}</table><p>Value coverage and requirement coverage are separate. residual, unallocated, and variance are not synonyms.</p>
<h2>Joint top-down scenarios</h2><ul>{_scenarios_html(targets)}</ul>
<h2>Dated cost trace</h2><p>Five source events only; no interpolation.</p><table><tr><th>Date</th><th>Event</th><th>Lane</th><th>Type</th><th>Value</th><th>Confidence</th></tr>{_trace_html(trace)}</table>
<h2>FDAS assumption bridge</h2><p class="allocated">2,730.0 + 965.6 + 821.7 = 4,517.3 USD MM development CAPEX. Native workbook USD values are divided by 1,000,000 to USD MM. This is an assumption bridge, not a disclosure and not comparison-eligible.</p>
<p><b>OPEX — excluded from development CAPEX:</b> variable 267,482,624 USD; fixed 790,000,000 USD.</p><p class="gap"><b>installation/hookup:</b> req-000007 is explicitly unmapped in FDAS. The 5,200 USD MM value is a stale configuration estimate, not workbook truth or disclosure.</p>
<h2>Sources, gaps, and decision gate</h2><p>Unknown quantities and not_public/unmapped rows are deliverables. No workbook metadata is published.</p>
<ul><li>taxonomy — pending</li><li>accounting — pending</li><li>scenarios — pending</li><li>portfolio reuse — pending; reuse_allowed=false</li><li>external send — pending owner authorization; email not sent</li></ul>
</body></html>
"""


def _workbook_records(root: Path) -> list[dict]:
    rows = _read_csv(root / CURATED_REL / "fdas_project_cost_crosswalk.csv")
    by_file: dict[str, dict] = {}
    for row in rows:
        record = by_file.setdefault(
            row["WORKBOOK_FILE"],
            {
                "file": row["WORKBOOK_FILE"],
                "sha256": row["WORKBOOK_SHA256"],
                "allowlisted_cells": [],
                "extraction": {
                    "library": "openpyxl",
                    "version": OPENPYXL_VERSION,
                    "mode": "read_only,data_only",
                },
            },
        )
        if row["WORKBOOK_CELL"]:
            record["allowlisted_cells"].append(row["WORKBOOK_CELL"])
    for record in by_file.values():
        record["allowlisted_cells"] = sorted(set(record["allowlisted_cells"]))
    return [by_file[key] for key in sorted(by_file)]


def _manifest(root: Path, output: Path, epoch: int, producer_commit: str) -> dict:
    # fmt: off
    schema_path = "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map_schema.py"
    scenarios = [{
        "scenario_id": key, "shares": {rid: str(value) for rid, value in scenario.shares.items()},
        "derivation": "assumed", "status": "proposed", "confidence": "low",
        "reuse_allowed": False,
    } for key, scenario in BIG_FOOT_JOINT_SCENARIOS.items()]
    return {
        "contract_version": "1.0.0",
        "schema": {"path": schema_path, "sha256": _digest(root / schema_path)},
        "inputs": [{"path": path, "sha256": _digest(root / path)} for path in sorted(INPUT_PATHS)],
        "producer": {"commit": producer_commit, "commit_policy": "injected_source_revision",
                     "tool": "build_big_foot_cost_map.py", "version": "1.0.0"},
        "generated_at": {"policy": "SOURCE_DATE_EPOCH", "epoch": epoch,
                         "utc": datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")},
        "decimal_policy": {"arithmetic": "Decimal", "source_scale": "native",
                           "output_quantum": "0.01 USD MM", "allocation_rounding": "largest_remainder",
                           "inverse_rounding": "outward", "rounding_boundary": "output_only"},
        "controlled_ids": {"projects": ["prj-000001"], "awards": ["awd-000001", "awd-000002"],
                           "requirements": [f"req-{n:06d}" for n in range(1, 9)],
                           "events": [f"evt-{n:06d}" for n in range(1, 6)]},
        "scenarios": scenarios,
        "workbooks": _workbook_records(root),
        "outputs": [{"path": str(path), "sha256": _digest(output / path)} for path in (HTML_REL, CSV_REL)],
        "policies": {"email": "not_sent", "external_send": "pending_owner_authorization",
                     "workbooks": "read_only"},
        "owner_decision": {"status": "pending",
                           "items": ["taxonomy", "accounting", "scenarios", "portfolio reuse"]},
    }
    # fmt: on


def build_outputs(
    *, repo_root: Path, output_root: Path, source_date_epoch: int, producer_commit: str
) -> None:
    if source_date_epoch < 0 or not producer_commit.strip():
        raise ValueError("SOURCE_DATE_EPOCH and producer commit are required")
    targets = reconcile_big_foot_targets(repo_root / CURATED_REL)
    html_path, csv_path = output_root / HTML_REL, output_root / CSV_REL
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(
        _report_html(repo_root, targets), encoding="utf-8", newline="\n"
    )
    _write_reconciliation(csv_path, targets)
    manifest_path = output_root / MANIFEST_REL
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            _manifest(repo_root, output_root, source_date_epoch, producer_commit),
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    epoch_text = os.environ.get("SOURCE_DATE_EPOCH")
    producer_commit = os.environ.get("PRODUCER_COMMIT")
    if epoch_text is None or producer_commit is None:
        raise SystemExit("SOURCE_DATE_EPOCH and PRODUCER_COMMIT are required")
    build_outputs(
        repo_root=root,
        output_root=root,
        source_date_epoch=int(epoch_text),
        producer_commit=producer_commit,
    )


if __name__ == "__main__":
    main()
