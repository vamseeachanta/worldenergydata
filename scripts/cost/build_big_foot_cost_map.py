#!/usr/bin/env python3
"""Build the deterministic, fail-closed Big Foot cost-map evidence pack."""

from __future__ import annotations

import csv
import json
import os
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from openpyxl import __version__ as OPENPYXL_VERSION

from worldenergydata.cost.timeseries.cost_map import (
    BIG_FOOT_JOINT_SCENARIOS,
    largest_remainder_allocate,
)
from worldenergydata.cost.timeseries.evidence_pack import (
    BUILDER_REL as EVIDENCE_BUILDER_REL,
)
from worldenergydata.cost.timeseries.evidence_pack import (
    CSV_FIELDS,
    CSV_REL,
    HTML_REL,
)
from worldenergydata.cost.timeseries.evidence_pack import (
    INPUT_PATHS as EVIDENCE_INPUT_PATHS,
)
from worldenergydata.cost.timeseries.evidence_pack import (
    MANIFEST_REL,
    REQUIREMENT_IDS,
    build_context,
    c_locale,
    csv_row,
    digest,
    money_basis,
    publish_transactionally,
)
from worldenergydata.cost.timeseries.evidence_pack import safe_url as validate_url
from worldenergydata.cost.timeseries.evidence_pack import (
    snapshot,
    target_money,
    validate_producer,
)
from worldenergydata.cost.timeseries.evidence_pack_render import (
    canonical_manifest,
    fdas_gap_row,
    fixed_fields,
    manifest_payload,
    render_html,
    select_fields,
)

safe_url = validate_url
BUILDER_REL = EVIDENCE_BUILDER_REL
INPUT_PATHS = EVIDENCE_INPUT_PATHS


_row = csv_row


OBSERVED = fixed_fields(
    "direction=project_to_asset row_kind=observed_component value_basis=point mapping_status=mapped"
)
AGGREGATE = fixed_fields(
    "direction=project_to_asset row_kind=aggregate_reconciliation additive=false unallocated_mm=0 unreconciled_variance_mm=0 counting_disposition=aggregate"
)
SCENARIO = fixed_fields(
    "direction=project_to_asset row_kind=scenario_allocation additive=true value_basis=point evidence_derivation=allocated source_provenance=assumed confidence=low counting_disposition=included mapping_status=mapped unallocated_mm=0 unreconciled_variance_mm=0 scenario_status=proposed reuse_allowed=false rounding_policy=largest_remainder_0.01_USD_MM"
)
INVERSE = fixed_fields(
    "direction=asset_to_project row_kind=implied_project_total additive=false currency=USD price_basis=nominal ownership_basis=gross scope_basis=project capex_basis=project_capex value_basis=range evidence_derivation=allocated source_provenance=assumed confidence=low counting_disposition=overlap mapping_status=mapped scenario_status=proposed reuse_allowed=false rounding_policy=outward_0.01_USD_MM"
)
FDAS_COMMON = fixed_fields(
    "direction=project_to_asset value_basis=point comparison_eligibility=ineligible rounding_policy=native_USD_divided_by_1000000"
)
TRACE_COMMON = fixed_fields(
    "accounting_view=trace direction=project_to_asset row_kind=trace_event additive=false counting_disposition=trace_only"
)


def _award_rows(context: dict) -> list[dict[str, str]]:
    targets, awards = context["targets"], context["awards"]
    rows = []
    for event_id, target in targets.items():
        money = target_money(context, event_id)
        view = f"bottom_up:{event_id}"
        for award in awards:
            included = award["COUNTING_DISPOSITION"] == "included"
            rows.append(
                _row(
                    **OBSERVED,
                    **select_fields(
                        award,
                        "project_id:PROJECT_ID requirement_id:REQUIREMENT_IDS award_id:AWARD_ID basis_year:BASIS_YEAR evidence_derivation:EVIDENCE_DERIVATION source_provenance:SOURCE_PROVENANCE confidence:CONFIDENCE counting_disposition:COUNTING_DISPOSITION source_identity:AWARD_ID source_locator:SOURCE_LOCATOR",
                    ),
                    accounting_view=view,
                    additive=str(included).lower(),
                    total_event_id=event_id,
                    value_low_mm=award["VALUE_MM"],
                    value_high_mm=award["VALUE_MM"],
                    currency="USD",
                    price_basis="nominal",
                    ownership_basis="gross" if included else "third_party",
                    scope_basis="component" if included else "midstream",
                    capex_basis="component_capex" if included else "non_capex",
                )
            )
        rows.append(_aggregate_row(view, event_id, target, money, awards))
    return rows


def _aggregate_row(view: str, event_id: str, target, money, awards: list[dict]):
    eligible = {
        rid
        for row in awards
        if row["COUNTING_DISPOSITION"] == "included"
        for rid in row["REQUIREMENT_IDS"].split("|")
    }
    linked = {rid for row in awards for rid in row["REQUIREMENT_IDS"].split("|")}
    return _row(
        **AGGREGATE,
        **money_basis(money),
        accounting_view=view,
        project_id="prj-000001",
        total_event_id=event_id,
        total_mm=target.target,
        eligible_mm=target.accounting.eligible.low,
        excluded_mm=target.accounting.excluded.low,
        overlap_mm=target.accounting.overlap.low,
        residual_mm=target.accounting.residual.low,
        value_coverage=target.accounting.eligible.low / target.target,
        eligible_requirement_coverage=f"{len(eligible)}/{len(REQUIREMENT_IDS)}",
        linked_requirement_coverage=f"{len(linked)}/{len(REQUIREMENT_IDS)}",
        source_identity=event_id,
        source_locator=target.source_url,
        evidence_derivation="reconciled",
        source_provenance=target.provenance,
        confidence=target.confidence,
    )


def _scenario_rows(context: dict) -> list[dict[str, str]]:
    targets = context["targets"]
    rows = []
    for event_id, target in targets.items():
        money = target_money(context, event_id)
        for scenario_id, scenario in BIG_FOOT_JOINT_SCENARIOS.items():
            view = f"scenario:{event_id}:{scenario_id}"
            for requirement, value in largest_remainder_allocate(
                target.target, scenario.shares
            ).items():
                rows.append(
                    _row(
                        **SCENARIO,
                        **money_basis(money),
                        accounting_view=view,
                        project_id="prj-000001",
                        requirement_id=requirement,
                        total_event_id=event_id,
                        scenario_id=scenario_id,
                        value_low_mm=value,
                        value_high_mm=value,
                        residual_mm=target.accounting.residual.low,
                        source_identity=event_id,
                        source_locator=target.source_url,
                    )
                )
    return rows


def _reverse_rows(awards: list[dict[str, str]]) -> list[dict[str, str]]:
    included = [
        award for award in awards if award["COUNTING_DISPOSITION"] == "included"
    ]
    if len(included) != 1 or len(included[0]["REQUIREMENT_IDS"].split("|")) != 1:
        raise ValueError("inverse requires one singly-linked included award")
    award, quantum = included[0], Decimal("0.01")
    requirement = award["REQUIREMENT_IDS"]
    rows = []
    for scenario_id, scenario in BIG_FOOT_JOINT_SCENARIOS.items():
        implied = Decimal(award["VALUE_MM"]) / scenario.shares[requirement]
        rows.append(
            _row(
                **INVERSE,
                **select_fields(
                    award,
                    "project_id:PROJECT_ID award_id:AWARD_ID basis_year:BASIS_YEAR source_identity:AWARD_ID source_locator:SOURCE_LOCATOR",
                ),
                accounting_view=f"inverse:{scenario_id}",
                requirement_id=requirement,
                scenario_id=scenario_id,
                value_low_mm=implied.quantize(quantum, rounding=ROUND_FLOOR),
                value_high_mm=implied.quantize(quantum, rounding=ROUND_CEILING),
            )
        )
    return rows


def _fdas_rows(context: dict) -> list[dict[str, str]]:
    additive, opex = context["fdas_additive"], context["fdas_opex"]
    rows = []
    for source in additive + opex:
        value = Decimal(source["WORKBOOK_VALUE"]) / Decimal("1000000")
        rows.append(
            _row(
                **FDAS_COMMON,
                **select_fields(
                    source,
                    "project_id:PROJECT_ID requirement_id:REQUIREMENT_IDS currency:CURRENCY price_basis:PRICE_BASIS ownership_basis:OWNERSHIP_BASIS scope_basis:SCOPE_BASIS capex_basis:CAPEX_BASIS evidence_derivation:EVIDENCE_DERIVATION source_provenance:SOURCE_PROVENANCE counting_disposition:COUNTING_DISPOSITION mapping_status:MAPPING_STATUS assumption_vintage:ASSUMPTION_VINTAGE",
                ),
                accounting_view=(
                    "fdas_development_capex" if source in additive else "fdas_opex"
                ),
                row_kind="fdas_assumption" if source in additive else "fdas_opex",
                additive=str(source in additive).lower(),
                value_low_mm=value,
                value_high_mm=value,
                source_identity=f"FDAS_V30:{source['WORKBOOK_CATEGORY']}",
                source_locator=f"{source['WORKBOOK_SHEET']}!{source['WORKBOOK_CELL']}",
            )
        )
    gaps = [
        row for row in context["fdas_all"] if row["WORKBOOK_ROLE"] == "coverage_gap"
    ]
    if len(gaps) != 1:
        raise ValueError("FDAS coverage gap must resolve uniquely")
    return rows + [_fdas_total(rows), fdas_gap_row(gaps[0])]


def _fdas_total(rows: list[dict[str, str]]) -> dict[str, str]:
    total = sum(
        (
            Decimal(row["value_low_mm"])
            for row in rows
            if row["accounting_view"] == "fdas_development_capex"
        ),
        Decimal(),
    )
    return _row(
        accounting_view="fdas_development_capex",
        direction="project_to_asset",
        row_kind="fdas_total",
        additive="false",
        project_id="prj-000001",
        total_mm=total,
        currency="USD",
        capex_basis="project_capex",
        evidence_derivation="assumed",
        source_provenance="workbook_assumption",
        counting_disposition="aggregate",
        source_identity="FDAS_V30",
        assumption_vintage="FDAS_V30",
        comparison_eligibility="ineligible",
        rounding_policy="native_USD_divided_by_1000000",
    )


def _trace_rows(trace: tuple) -> list[dict[str, str]]:
    rows = []
    for event in trace:
        money = event.money
        money_fields = {} if money is None else money_basis(money)
        rows.append(
            _row(
                **TRACE_COMMON,
                **money_fields,
                project_id=event.project_id,
                requirement_id=event.requirement_id or "",
                award_id=event.award_id or "",
                total_event_id=event.event_id,
                lane=event.lane,
                effective_date=event.effective_date.label,
                date_precision=event.effective_date.precision,
                value_low_mm="" if money is None else money.low_value,
                value_high_mm="" if money is None else money.high_value,
                value_basis="not_public" if money is None else money.value_basis,
                evidence_derivation=event.evidence.derivation,
                source_provenance=event.evidence.source_provenance,
                confidence=event.evidence.confidence,
                mapping_status="unmapped" if money is None else "mapped",
                source_identity=event.event_id,
                source_locator=event.evidence.source_locator,
            )
        )
    return rows


def _rows(context: dict) -> list[dict[str, str]]:
    return (
        _award_rows(context)
        + _scenario_rows(context)
        + _reverse_rows(context["awards"])
        + _fdas_rows(context)
        + _trace_rows(context["trace"])
    )


def _render(
    stage: Path,
    context: dict,
    frozen: dict[str, bytes],
    rows: list[dict[str, str]],
    epoch: int,
    commit: str,
) -> None:
    html_path, csv_path = stage / HTML_REL, stage / CSV_REL
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render_html(context), encoding="utf-8", newline="\n")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest_path = stage / MANIFEST_REL
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest_payload(context, frozen, stage, epoch, commit, OPENPYXL_VERSION)
    manifest_path.write_text(
        canonical_manifest(payload),
        encoding="utf-8",
        newline="\n",
    )


def _validate_rendered(stage: Path, expected_rows: list[dict[str, str]]) -> None:
    html = (stage / HTML_REL).read_text(encoding="utf-8")
    with (stage / CSV_REL).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        actual_rows = list(reader)
        if tuple(reader.fieldnames or ()) != CSV_FIELDS:
            raise RuntimeError("staged CSV schema mismatch")
    manifest = json.loads((stage / MANIFEST_REL).read_text(encoding="utf-8"))
    if not html.startswith("<!doctype html>") or actual_rows != expected_rows:
        raise RuntimeError("staged output semantic validation failed")
    if manifest["owner_decision"]["status"] != "pending":
        raise RuntimeError("staged manifest owner gate drift")


def build_outputs(
    *,
    repo_root: Path,
    output_root: Path,
    source_date_epoch: int,
    producer_commit: str,
    before_final_hash: Callable[[], None] | None = None,
    before_publish: Callable[[Path], None] | None = None,
) -> None:
    if source_date_epoch < 0:
        raise ValueError("nonnegative SOURCE_DATE_EPOCH is required")
    with c_locale():
        frozen = snapshot(repo_root)
        validate_producer(repo_root, producer_commit, frozen)
        context = build_context(frozen)
        rows = _rows(context)
        with TemporaryDirectory() as directory:
            stage = Path(directory)
            _render(stage, context, frozen, rows, source_date_epoch, producer_commit)
            _validate_rendered(stage, rows)
            expected = {
                relative: digest((stage / relative).read_bytes())
                for relative in (HTML_REL, CSV_REL, MANIFEST_REL)
            }
            if before_final_hash:
                before_final_hash()
            if before_publish:
                before_publish(stage)
            if snapshot(repo_root) != frozen:
                raise RuntimeError("input changed during build")
            actual = {
                relative: digest((stage / relative).read_bytes())
                for relative in expected
            }
            if actual != expected:
                raise RuntimeError("staged output changed before publication")
            publish_transactionally(stage, output_root)


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
