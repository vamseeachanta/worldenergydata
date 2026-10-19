# ABOUTME: Ingestion report generator for Baker Hughes data (WRK-1190).
# ABOUTME: Creates YAML-serializable dict with date range, record counts, and metadata.

"""Baker Hughes ingestion report generator."""

import hashlib
from pathlib import Path
from typing import Any, Dict, Union

import pandas as pd


def generate_workbook_evidence(path: Union[str, Path]) -> Dict[str, Any]:
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


def generate_report(df: pd.DataFrame, source: str) -> Dict[str, Any]:
    """Generate an ingestion report dict from a loaded DataFrame.

    Args:
        df: Loaded Baker Hughes DataFrame (pivot or summary).
        source: Label for the data source ('pivot' or 'summary').

    Returns:
        Dict suitable for YAML serialization with record counts,
        date range, and available dimensions.
    """
    report: Dict[str, Any] = {
        "source": source,
        "record_count": len(df),
    }

    if "date" in df.columns and len(df) > 0:
        report["date_range"] = {
            "min": str(df["date"].min().date()),
            "max": str(df["date"].max().date()),
        }

    if "basin" in df.columns:
        report["basins"] = sorted(df["basin"].dropna().unique().tolist())

    if "state" in df.columns:
        report["states"] = sorted(df["state"].dropna().unique().tolist())

    if "country" in df.columns:
        report["countries"] = sorted(df["country"].dropna().unique().tolist())

    return report
