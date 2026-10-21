# ABOUTME: Ingestion report generator for Baker Hughes data (WRK-1190).
# ABOUTME: Creates YAML-serializable dict with date range, record counts, and metadata.

"""Baker Hughes ingestion report generator."""

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd


def generate_workbook_evidence(path: str | Path) -> dict[str, Any]:
    """Fingerprint supplied bytes and expose unqualified source-evidence gaps.

    This does not parse Excel, bind bytes to a loaded DataFrame, authenticate a
    publisher, or verify QA signatures. Even an empty or invalid workbook is
    unqualified. File access errors propagate without producing an evidence
    record. No local filename or path is included in the returned dictionary.
    """
    # SHA-256: FIPS 180-4 (2015), section 6.2, SHA-256 Hash Computation.
    # https://csrc.nist.gov/pubs/fips/180-4/upd1/final
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    # Evidence requirements: module knowledge pack, sections 3, 5 and 10;
    # independent-evidence follow-up: repository issue 1336. A computed digest
    # supplies byte identity only; no requirement below can be inferred from it.
    requirements = {
        "source_revision": "Permitted publisher workbook revision is not established.",
        "depth_units": "Source well-depth and water-depth units are not established.",
        "independent_counts": "Independent expected counts and their source are absent.",
        "signed_qa": "Signed QA evidence bound to this fingerprint is absent.",
    }
    return {
        "status": "NOT_EVALUATED",
        "fingerprint": {"algorithm": "sha256", "digest": digest},
        "checks": {
            name: {"status": "NOT_EVALUATED", "reason": reason}
            for name, reason in requirements.items()
        },
    }


def generate_report(df: pd.DataFrame, source: str) -> dict[str, Any]:
    """Generate an ingestion report dict from a loaded DataFrame.

    Args:
        df: Loaded Baker Hughes DataFrame (pivot or summary).
        source: Label for the data source ('pivot' or 'summary').

    Returns:
        Dict suitable for YAML serialization with record counts,
        observed date bounds, and available dimensions. The additive
        completeness.date_range entry describes date coverage only, not
        workbook/schema or dimension completeness. Empty input, an absent
        date column, and missing date values are explicitly incomplete.
        Bounds are omitted when no dates are observed; partial bounds are
        retained with an incomplete status. Dates must already be parsed,
        as returned by the loaders.
    """
    report: dict[str, Any] = {
        "source": source,
        "record_count": len(df),
    }

    # Issue #1335, F13/F19; knowledge pack section 11 (2026-10-19):
    # complete date coverage requires nonempty input and no missing dates.
    # Counts are direct enumeration, with no engineering acceptance limit.
    missing_count = None
    if "date" in df.columns:
        missing_count = int(df["date"].isna().sum())

    if df.index.empty:
        reason = "empty_input"
    elif "date" not in df.columns:
        reason = "missing_date_column"
    elif df["date"].isna().all():
        reason = "all_dates_missing"
    elif df["date"].isna().any():
        reason = "missing_dates"
    else:
        reason = None

    report["completeness"] = {
        "date_range": {
            "status": "incomplete" if reason else "complete",
            "reason": reason,
            "missing_count": missing_count,
        }
    }

    if "date" in df.columns and df["date"].notna().any():
        observed_dates = df["date"].dropna()
        report["date_range"] = {
            "min": str(observed_dates.min().date()),
            "max": str(observed_dates.max().date()),
        }

    if "basin" in df.columns:
        report["basins"] = sorted(df["basin"].dropna().unique().tolist())

    if "state" in df.columns:
        report["states"] = sorted(df["state"].dropna().unique().tolist())

    if "country" in df.columns:
        report["countries"] = sorted(df["country"].dropna().unique().tolist())

    return report
