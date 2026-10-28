"""Read existing cost-map evidence without promoting it to portfolio parity."""

import csv
from decimal import Decimal

from worldenergydata.cost.timeseries.cost_map import (
    load_big_foot_evidence,
    reconcile_big_foot_targets,
)
from worldenergydata.cost.timeseries.project_trace import build_big_foot_trace

from .workbook_reader import digest


def _interval(value):
    return None if value is None else {"low": str(value.low), "high": str(value.high)}


def _attach_crosswalk(result, curated):
    with (curated / "cost_project_identity.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        identities = {
            r["OPAQUE_ID"]: r["DISPLAY_LABEL"]
            for r in csv.DictReader(stream)
            if r["ACTIVE"] == "true" and r["STATE"] == "active"
        }
    with (curated / "fdas_project_cost_crosswalk.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        records = list(csv.DictReader(stream))
    known = result["inventory"]["workbooks"]
    seen = set()
    for record in records:
        name = record["WORKBOOK_FILE"]
        if name not in known:
            continue  # D&C row references require a separate frozen inventory.
        if record["WORKBOOK_SHA256"] != known[name]["sha256"]:
            raise ValueError("crosswalk workbook digest mismatch")
        if (
            name != "financial_project_summary.xlsx"
            or record["WORKBOOK_SHEET"] != "Project_Summary"
        ):
            continue
        cell = record["WORKBOOK_CELL"]
        if not cell:
            continue
        if cell in seen:
            raise ValueError("duplicate workbook cell crosswalk")
        seen.add(cell)
        matches = [
            (project, row)
            for project in result["projects"]
            for row in project["crosswalk"]
            if row["cell"] == f"Project_Summary!{cell}"
        ]
        if len(matches) != 1:
            raise ValueError("unresolved workbook cell crosswalk")
        project, row = matches[0]
        if identities.get(record["PROJECT_ID"]) != project["project"]:
            raise ValueError("workbook project identity mismatch")
        if row["value"] is None or Decimal(record["WORKBOOK_VALUE"]) != Decimal(
            row["value"]
        ):
            raise ValueError("crosswalk workbook value mismatch")
        if (
            record["VALUE_UNIT"] != row["unit"]
            or record["ASSUMPTION_VINTAGE"] != project["vintage"]
        ):
            raise ValueError("crosswalk workbook basis mismatch")
        project["project_id"] = record["PROJECT_ID"]
        project["identity_status"] = (
            "controlled project identity; economic/time equivalence not established"
        )
        row["requirement_ids"] = list(
            filter(None, record["REQUIREMENT_IDS"].split("|"))
        )
        row["mapping_status"] = record["MAPPING_STATUS"]


def attach_existing_evidence(result, repository):
    """Use existing single-project evidence; never run a replacement estimator.

    Sources: controlled cost_project_identity.csv and award_asset_links.csv;
    existing cost_map / project_trace accounting contracts. Native units are
    USD MM, as stated by the source CSVs; no cross-lane addition is performed.
    """
    curated = repository / "data/modules/cost/curated"
    files = sorted(curated.glob("*.csv"))
    before = {str(p.relative_to(repository)): digest(p.read_bytes()) for p in files}
    _attach_crosswalk(result, curated)
    evidence = load_big_foot_evidence(curated)
    targets = reconcile_big_foot_targets(curated)
    events = build_big_foot_trace(curated)
    result["asset_evidence"] = {
        "project_id": "prj-000001",
        "unit": "USD MM",
        "requirements": [
            {
                "requirement_id": rid,
                "awards": [
                    {"award_id": a.award_id, "additive": a.additive}
                    for a in evidence.award_references_by_requirement.get(rid, ())
                ],
            }
            for rid in evidence.requirement_ids
        ],
        "contributions": [
            {
                "award_id": c.award_id,
                "requirements": list(c.requirement_ids),
                "amount": _interval(c.amount),
                "disposition": c.counting_disposition,
                "value_basis": c.value_basis,
            }
            for c in evidence.contributions
        ],
        "targets": [
            {
                "event_id": t.event_id,
                "value": str(t.target),
                "currency": t.currency,
                "basis": t.target_basis,
                "vintage": t.target_vintage,
                "source_url": t.source_url,
                "provenance": t.provenance,
                "eligible": _interval(t.accounting.eligible),
                "excluded": _interval(t.accounting.excluded),
                "overlap": _interval(t.accounting.overlap),
                "residual": _interval(t.accounting.residual),
            }
            for _, t in sorted(targets.items())
        ],
        "events": [
            {
                "event_id": e.event_id,
                "type": e.event_type,
                "lane": e.lane,
                "date": e.effective_date.label,
                "currency": e.money.currency if e.money else None,
                "basis": (
                    e.money.model_dump(mode="json", exclude={"low_value", "high_value"})
                    if e.money
                    else None
                ),
                "provenance": e.evidence.source_provenance,
                "derivation": e.evidence.derivation,
                "source_url": e.evidence.source_url,
                "amount": (
                    {
                        "low": (
                            str(e.money.low_value)
                            if e.money.low_value is not None
                            else None
                        ),
                        "high": (
                            str(e.money.high_value)
                            if e.money.high_value is not None
                            else None
                        ),
                    }
                    if e.money
                    else None
                ),
            }
            for e in events
        ],
    }
    after = {str(p.relative_to(repository)): digest(p.read_bytes()) for p in files}
    if before != after:
        raise ValueError("cost evidence changed during ingestion")
    result["evidence_input_hashes"] = before
    result["upstream"] = {
        "cost_map": {
            "status": "PARTIAL",
            "reason": "Existing single-project requirements/awards and targets only; portfolio synthesis manifest not consumed.",
        },
        "time_traces": {
            "status": "PARTIAL",
            "reason": "Existing single-project event trace only; portfolio trace-contract manifest not consumed.",
        },
        "estimator": {
            "status": "NOT_EVALUATED",
            "reason": "Correlated-estimator manifest and project-level backtests unavailable; no substitute prediction.",
        },
    }
