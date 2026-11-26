"""Lease cohorts and snapshot ownership from the BOEM/BSEE public layouts."""

from __future__ import annotations

import csv
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

LEASE_SCHEMA = "data/modules/bsee/leases/source_schema.json"
OWNER_SCHEMA = "data/modules/bsee/boem_lease_history_layout.json"
STATUS_DICTIONARY = "docs/knowledge-base/bsee/data-dictionaries/leasing/lease-fields.md"
GULF_PLANNING_AREAS = ("CGM", "EGM", "WGM")


def _native_lease_records(archive, reference, layout):
    """Call the owning checkout's strict decoder without writing bytecode there."""
    package_dirs = [
        str(reference / "packages" / name / "src")
        for name in ("worldenergydata-bsee", "worldenergydata-core")
    ]
    original_path = sys.path.copy()
    original_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        sys.path[:0] = package_dirs
        from worldenergydata.bsee import lease_ingest

        expected = Path(package_dirs[0]) / "worldenergydata/bsee/lease_ingest.py"
        if Path(lease_ingest.__file__).resolve() != expected.resolve():
            raise ValueError("Lease loader came from a different checkout")
        return lease_ingest.load_table(archive, layout)
    finally:
        sys.path[:] = original_path
        sys.dont_write_bytecode = original_bytecode


def _status_labels(reference):
    """Use exact-code dictionary matches only, retaining every unlisted tape code."""
    dictionary = (reference / STATUS_DICTIONARY).read_text(encoding="utf-8")
    section = dictionary.split("## Lease Status Codes\n", 1)[1].split("\n## ", 1)[0]
    labels = {}
    for line in section.splitlines():
        if line.startswith("|"):
            code, name, *_ = [s.strip() for s in line.strip("|").split("|")]
            if code.isupper():
                labels[code] = name
    # The conceptual SOP label describes a suspension. LSETAPE separately
    # records a suspension type. The conceptual label does not resolve its type.
    if "SOP" in labels:
        labels["SOP"] = "Suspension"
    return labels


def _apply_filters(frame, reasons):
    """Make consecutive exclusion masks mutually exclusive, retaining source counts."""
    kept = pd.Series(True, index=frame.index)
    drops = {}
    for reason, excluded in reasons:
        drops[reason] = int((kept & excluded).sum())
        kept &= ~excluded
    return frame.loc[kept].copy(), drops


def read_leases(zip_path, reference):
    """Return one row per Gulf lease effective in 2005 to 2026, counts and source notes."""
    reference = Path(reference)
    schema = json.loads((reference / LEASE_SCHEMA).read_bytes())
    raw = pd.DataFrame(
        _native_lease_records(Path(zip_path), reference, schema["tables"]["lease"])
    )
    fields = {
        "Lease Number": "lease_id",
        "MMS Planning Area Code": "planning_area",
        "Serial Type Code": "serial_type",
        "Sale Number": "sale_number",
        "Lease Effective Date": "effective_date",
        "Primary Term": "primary_term_years",
        "Lease Status Code": "status_code",
        "Lease Status Effective Date": "status_date",
        "Block Max Water Depth": "block_max_depth_ft",
        "Block Low Water Depth": "block_min_depth_ft",
        "Suspension Effective Date": "suspension_start",
        "Suspension Expiration Date": "suspension_end",
        "Suspension Type Code": "suspension_type",
        "First Production Date": "lease_first_production_date",
    }
    frame = raw.loc[:, fields.keys()].rename(columns=fields)
    frame["effective_date"] = pd.to_datetime(
        frame.effective_date, format="%Y-%m-%d", errors="raise"
    )
    years = frame.effective_date.dt.year
    # The Gulf identifier is G + digits. The historical tape also contains
    # unprefixed leases; the planning area keeps Gulf legacy entries eligible.
    gulf_number = frame.lease_id.str.fullmatch(r"G\d{5,6}", na=False)
    gulf_legacy = frame.lease_id.str.fullmatch(
        r"\d{5,6}", na=False
    ) & frame.planning_area.isin(GULF_PLANNING_AREAS)
    selected, drops = _apply_filters(
        frame,
        [
            ("missing_effective_date", frame.effective_date.isna()),
            ("effective_year_outside_2005_2026", ~years.between(2005, 2026)),
            ("outside_gulf", ~(gulf_number | gulf_legacy)),
        ],
    )
    if selected.lease_id.duplicated().any() or selected.lease_id.isna().any():
        raise ValueError(
            "Missing or duplicated lease identifier in the effective cohort"
        )
    if (~selected.planning_area.isin(GULF_PLANNING_AREAS)).any():
        raise ValueError("Gulf identifier and planning-area classifications disagree")
    selected["issue_year"] = selected.effective_date.dt.year.astype(int)
    for column in (
        "status_date",
        "suspension_start",
        "suspension_end",
        "lease_first_production_date",
    ):
        selected[column] = pd.to_datetime(
            selected[column], format="%Y-%m-%d", errors="raise"
        )
    for column in ("block_max_depth_ft", "block_min_depth_ft", "primary_term_years"):
        selected[column] = pd.to_numeric(selected[column], errors="raise")
    labels = _status_labels(reference)
    selected["status_code"] = selected.status_code.fillna("(blank)")
    selected["status_label"] = selected.status_code.map(labels).fillna(
        selected.status_code
    )
    low = selected.block_min_depth_ft
    high = selected.block_max_depth_ft
    missing = low.isna() | high.isna()
    invalid = ~missing & ((low < 0) | (high <= 0) | (low > high))
    crosses = pd.Series(False, index=selected.index)
    for boundary in (100, 500, 1500):
        crosses |= (low * 0.3048 < boundary) & (high * 0.3048 >= boundary)
    selected["block_range_valid"] = ~(missing | invalid)
    selected["block_range_crosses_band"] = crosses & selected.block_range_valid
    selected["lease_depth_m"] = (high * 0.3048).where(selected.block_range_valid)
    complete_suspension = (
        selected.suspension_start.notna() & selected.suspension_end.notna()
    )
    dated = selected.loc[complete_suspension]
    audit = [
        {
            "stage": "LSETAPE effective Gulf lease cohort",
            "read": len(raw),
            "kept": len(selected),
            "drops": drops,
        }
    ]
    counts = selected.status_code.value_counts()
    meta = {
        "first_effective_date": selected.effective_date.min().date().isoformat(),
        "last_effective_date": selected.effective_date.max().date().isoformat(),
        "straddling_ranges": int(selected.block_range_crosses_band.sum()),
        "missing_ranges": int(missing.sum()),
        "invalid_ranges": int(invalid.sum()),
        "no_sale_number": int(selected.sale_number.isna().sum()),
        "planning_area_counts": selected.planning_area.value_counts().to_dict(),
        "serial_type_counts": selected.serial_type.value_counts(dropna=False).to_dict(),
        "suspension_start_present": int(selected.suspension_start.notna().sum()),
        "suspension_end_present": int(selected.suspension_end.notna().sum()),
        "suspension_type_present": int(selected.suspension_type.notna().sum()),
        "suspensions_with_both_dates": int(complete_suspension.sum()),
        "suspensions_with_ordered_dates": int(
            (dated.suspension_end >= dated.suspension_start).sum()
        ),
        "tape_first_production_date_present": int(
            selected.lease_first_production_date.notna().sum()
        ),
        "primary_term_missing_or_nonpositive": int(
            (selected.primary_term_years.fillna(0) <= 0).sum()
        ),
        "status_counts": counts.to_dict(),
        "status_labels": {
            code: label for code, label in labels.items() if code in counts
        },
        "undocumented_status_codes": sorted(set(counts.index) - set(labels)),
        "undated_tape_status_counts": frame.loc[
            frame.effective_date.isna(), "status_code"
        ]
        .value_counts()
        .to_dict(),
    }
    return selected.reset_index(drop=True), audit, meta


def read_owners(zip_path, leases, reference):
    """Read snapshot IDs and coverage; assignment history is incomplete."""
    reference = Path(reference)
    layout = json.loads((reference / OWNER_SCHEMA).read_bytes())
    spec = next(
        m for m in layout["members"] if m["name"].startswith("LeaseOwnerRawData/")
    )
    roles = spec["field_roles"]
    with zipfile.ZipFile(zip_path) as archive, archive.open(spec["name"]) as raw:
        expected_header = next(csv.reader([spec["header"].strip()]))
        frame = pd.read_csv(
            raw, encoding=spec["encoding"]["decoding"], dtype=str, keep_default_na=False
        )
        if frame.columns.tolist() != expected_header:
            raise ValueError("Lease owner header differs from BOEM's saved layout")
    frame = frame.apply(lambda column: column.str.strip())
    owners = frame.loc[
        :, [roles["lease_number"], roles["owner"], "ASGN_STATUS_CODE"]
    ].copy()
    owners.columns = ["lease_id", "company_id", "assignment_status"]
    selected, drops = _apply_filters(
        owners,
        [
            ("assignment_status_other_than_current", owners.assignment_status.ne("C")),
            ("lease_outside_effective_cohort", ~owners.lease_id.isin(leases.lease_id)),
            ("blank_company_id", owners.company_id.eq("")),
        ],
    )
    audit = [
        {
            "stage": "LeaseOwnerRawData current assignments on cohort leases",
            "read": len(frame),
            "kept": len(selected),
            "drops": drops,
        }
    ]
    meta = {
        "source_status_counts": frame.ASGN_STATUS_CODE.value_counts().to_dict(),
        "termination_dates_present": int(frame[roles["termination_date"]].ne("").sum()),
        "missing_assignment_effective_dates": int(
            frame[roles["effective_date"]].eq("").sum()
        ),
        "cohort_current_leases": int(selected.lease_id.nunique()),
        "cohort_current_companies": int(selected.company_id.nunique()),
        "cohort_current_assignment_rows": len(selected),
    }
    return selected.reset_index(drop=True), audit, meta
