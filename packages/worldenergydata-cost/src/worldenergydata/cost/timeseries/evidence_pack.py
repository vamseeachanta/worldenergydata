"""Fail-closed primitives for deterministic cost evidence-pack publication."""

from __future__ import annotations

import csv
import io
import locale
import re
import shutil
import subprocess
from contextlib import contextmanager
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator
from urllib.parse import urlsplit

from openpyxl import load_workbook

from worldenergydata.cost.timeseries.cost_map import (
    reconcile_big_foot_targets,
)
from worldenergydata.cost.timeseries.project_trace import build_big_foot_trace

HTML_REL = Path("reports/cost/big_foot_cost_map.html")
CSV_REL = Path("reports/cost/big_foot_cost_map_reconciliation.csv")
MANIFEST_REL = Path("data/modules/cost/curated/cost_map_contract_manifest.v1.json")
CURATED = "data/modules/cost/curated/"
BUILDER_REL = "scripts/cost/build_big_foot_cost_map.py"
HELPER_REL = (
    "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/evidence_pack.py"
)
RENDER_REL = (
    "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/"
    "evidence_pack_render.py"
)
INPUT_PATHS = (
    BUILDER_REL,
    HELPER_REL,
    RENDER_REL,
    "config/analysis/lower_tertiary/fields/big_foot.yml",
    *(
        CURATED + name
        for name in "award_asset_links.csv contract_awards.csv cost_award_identity.csv cost_event_identity.csv cost_project_identity.csv cost_requirement_identity.csv cost_revision_trails.csv fdas_project_cost_crosswalk.csv project_asset_requirements.csv sanctioned_projects.csv".split()
    ),
    *(
        "docs/modules/bsee/analysis/production/FDAS_V30/" + name
        for name in "drilling_and_completion_days.xlsx financial_project_summary.xlsx lease_assumptions.xlsx".split()
    ),
    *(
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/" + name
        for name in "cost_map.py cost_map_schema.py project_trace.py".split()
    ),
)
CSV_FIELDS = tuple(
    "accounting_view direction row_kind additive project_id requirement_id award_id total_event_id scenario_id lane effective_date date_precision value_low_mm value_high_mm total_mm eligible_mm excluded_mm overlap_mm currency price_basis basis_year ownership_basis scope_basis capex_basis value_basis evidence_derivation source_provenance confidence counting_disposition mapping_status residual_mm unallocated_mm unreconciled_variance_mm value_coverage eligible_requirement_coverage linked_requirement_coverage source_identity source_locator scenario_status reuse_allowed rounding_policy assumption_vintage comparison_eligibility".split()
)
PROJECT_IDS = ("prj-000001",)
AWARD_IDS = ("awd-000001", "awd-000002")
REQUIREMENT_IDS = tuple(f"req-{number:06d}" for number in range(1, 9))
EVENT_IDS = tuple(f"evt-{number:06d}" for number in range(1, 6))
TARGET_EVENT_IDS = ("evt-000003", "evt-000004")
NUMERIC_FIELDS = {
    "value_low_mm",
    "value_high_mm",
    "total_mm",
    "eligible_mm",
    "excluded_mm",
    "overlap_mm",
    "residual_mm",
    "unallocated_mm",
    "unreconciled_variance_mm",
    "value_coverage",
}


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def csv_rows(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))


def one(rows: list[dict[str, str]], **fields: str) -> dict[str, str]:
    found = [
        row
        for row in rows
        if all(row.get(key) == value for key, value in fields.items())
    ]
    if len(found) != 1:
        raise ValueError(f"expected one row for {fields}, found {len(found)}")
    return found[0]


def safe_url(value: str) -> str | None:
    if not value or any(character.isspace() for character in value):
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    try:
        parsed = urlsplit(value)
        _ = parsed.hostname, parsed.port
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    return value


def snapshot(root: Path) -> dict[str, bytes]:
    return {path: (root / path).read_bytes() for path in INPUT_PATHS}


def validate_producer(root: Path, commit: str, frozen: dict[str, bytes]) -> None:
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
    if digest(blob) != digest(frozen[BUILDER_REL]):
        raise ValueError("producer builder blob does not match current builder")


def _exact_ids(
    rows: list[dict[str, str]], field: str, expected: tuple[str, ...], label: str
) -> None:
    values = [row[field] for row in rows]
    if len(values) != len(set(values)) or set(values) != set(expected):
        raise ValueError(f"controlled {label} IDs must be exact and unique")


def validate_controlled_ids(frozen: dict[str, bytes]) -> None:
    for path, data in frozen.items():
        if path.startswith(CURATED) and path.endswith(".csv"):
            for row in csv_rows(data):
                if any(
                    key != "NOTES" and value.startswith(("=", "+", "-", "@"))
                    for key, value in row.items()
                ):
                    raise ValueError("CSV formula prefix rejected in curated input")
    requirements = csv_rows(frozen[CURATED + "project_asset_requirements.csv"])
    _exact_ids(requirements, "REQUIREMENT_ID", REQUIREMENT_IDS, "requirement")
    if {row["PROJECT_ID"] for row in requirements} != set(PROJECT_IDS):
        raise ValueError("controlled project IDs must be exact")
    links = csv_rows(frozen[CURATED + "award_asset_links.csv"])
    _exact_ids(links, "AWARD_ID", AWARD_IDS, "award")
    identities = csv_rows(frozen[CURATED + "cost_event_identity.csv"])
    _exact_ids(identities, "OPAQUE_ID", EVENT_IDS, "event")


def _frozen_curated(frozen: dict[str, bytes]) -> TemporaryDirectory[str]:
    directory = TemporaryDirectory()
    root = Path(directory.name)
    for path, data in frozen.items():
        if path.startswith(CURATED):
            (root / Path(path).name).write_bytes(data)
    return directory


def awards(frozen: dict[str, bytes]) -> list[dict[str, str]]:
    links = csv_rows(frozen[CURATED + "award_asset_links.csv"])
    sources = csv_rows(frozen[CURATED + "contract_awards.csv"])
    resolved = []
    for link in links:
        locator = link["SOURCE_LOCATOR"].split(":", 1)[1]
        predicates = dict(part.split("=", 1) for part in locator.split("|"))
        source = one(sources, **predicates)
        if link["SOURCE_URL"] != source["SOURCE_URL"]:
            raise ValueError("award source URL mismatch")
        if safe_url(link["SOURCE_URL"]) is None:
            raise ValueError("unsafe award URL")
        low = Decimal(source["VALUE_LOW_MM"])
        if low != Decimal(source["VALUE_HIGH_MM"]):
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


def fdas(
    frozen: dict[str, bytes],
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str]]:
    rows = csv_rows(frozen[CURATED + "fdas_project_cost_crosswalk.csv"])
    prefix = "docs/modules/bsee/analysis/production/FDAS_V30/"
    hashes: dict[str, str] = {}
    for row in rows:
        prior = hashes.setdefault(row["WORKBOOK_FILE"], row["WORKBOOK_SHA256"])
        if (
            prior != row["WORKBOOK_SHA256"]
            or digest(frozen[prefix + row["WORKBOOK_FILE"]]) != prior
        ):
            raise ValueError("workbook fingerprint mismatch")
    _verify_workbook_cells(rows, frozen, prefix)
    additive = [
        row
        for row in rows
        if row["WORKBOOK_ROLE"] == "project_summary_total"
        and row["COUNTING_DISPOSITION"] == "included"
    ]
    opex = [row for row in rows if row["WORKBOOK_ROLE"] == "project_summary_opex"]
    if {row["WORKBOOK_CATEGORY"] for row in additive} != {
        "facilities total",
        "drilling",
        "completion",
    } or len(opex) != 2:
        raise ValueError("FDAS additive/OPEX contract drift")
    values = re.findall(
        r"(?m)^\s*total_mm_usd:\s*([0-9.]+)\s*$",
        frozen["config/analysis/lower_tertiary/fields/big_foot.yml"].decode(),
    )
    if len(values) != 1:
        raise ValueError("stale config estimate must resolve uniquely")
    return (
        additive,
        opex,
        {
            "value": values[0],
            "classification": "stale configuration estimate",
        },
    )


def _verify_workbook_cells(
    rows: list[dict[str, str]], frozen: dict[str, bytes], prefix: str
) -> None:
    for filename in {row["WORKBOOK_FILE"] for row in rows}:
        workbook = load_workbook(
            io.BytesIO(frozen[prefix + filename]), read_only=True, data_only=True
        )
        selected = [
            row
            for row in rows
            if row["WORKBOOK_FILE"] == filename
            and row["WORKBOOK_VALUE"]
            and "!" not in row["WORKBOOK_CELL"]
        ]
        try:
            for row in selected:
                actual = workbook[row["WORKBOOK_SHEET"]][row["WORKBOOK_CELL"]].value
                if Decimal(str(actual)) != Decimal(row["WORKBOOK_VALUE"]):
                    raise ValueError("crosswalk value does not match workbook cell")
        finally:
            workbook.close()


def build_context(frozen: dict[str, bytes]) -> dict:
    validate_controlled_ids(frozen)
    directory = _frozen_curated(frozen)
    try:
        targets = reconcile_big_foot_targets(Path(directory.name))
        trace = build_big_foot_trace(Path(directory.name))
    finally:
        directory.cleanup()
    if tuple(sorted(targets)) != TARGET_EVENT_IDS:
        raise ValueError("controlled target event IDs must be exact")
    if tuple(sorted(event.event_id for event in trace)) != EVENT_IDS:
        raise ValueError("controlled trace event IDs must be exact")
    additive, opex, stale = fdas(frozen)
    return {
        "targets": targets,
        "trace": trace,
        "awards": awards(frozen),
        "requirements": csv_rows(frozen[CURATED + "project_asset_requirements.csv"]),
        "fdas_all": csv_rows(frozen[CURATED + "fdas_project_cost_crosswalk.csv"]),
        "fdas_additive": additive,
        "fdas_opex": opex,
        "stale": stale,
    }


def csv_row(**values: object) -> dict[str, str]:
    unknown = set(values) - set(CSV_FIELDS)
    if unknown:
        raise ValueError(f"unknown CSV fields: {sorted(unknown)}")
    row = {field: "" for field in CSV_FIELDS}
    row.update({key: str(value) for key, value in values.items()})
    for field, value in row.items():
        if field not in NUMERIC_FIELDS and value.startswith(("=", "+", "-", "@")):
            raise ValueError(f"CSV formula prefix rejected in {field}")
    return row


def money_basis(money) -> dict:
    return {
        "currency": money.currency,
        "price_basis": money.price_basis.value,
        "basis_year": money.basis_year,
        "ownership_basis": money.ownership_basis,
        "scope_basis": money.scope_basis,
        "capex_basis": money.capex_basis,
    }


def target_money(context: dict, event_id: str):
    matches = [event.money for event in context["trace"] if event.event_id == event_id]
    if len(matches) != 1 or matches[0] is None:
        raise ValueError(f"target trace money missing for {event_id}")
    return matches[0]


@contextmanager
def c_locale() -> Iterator[None]:
    previous = locale.setlocale(locale.LC_ALL)
    try:
        if locale.setlocale(locale.LC_ALL, "C") != "C":
            raise ValueError("locale C is required")
        yield
    finally:
        locale.setlocale(locale.LC_ALL, previous)


def publish_transactionally(stage: Path, output: Path) -> None:
    paths = (HTML_REL, CSV_REL, MANIFEST_REL)
    previous = {
        relative: (output / relative).read_bytes()
        for relative in paths
        if (output / relative).exists()
    }
    published: list[Path] = []
    try:
        for relative in paths:
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(stage / relative, target)
            published.append(relative)
    except Exception:
        for relative in published:
            target = output / relative
            if relative in previous:
                target.write_bytes(previous[relative])
            else:
                target.unlink(missing_ok=True)
        raise
