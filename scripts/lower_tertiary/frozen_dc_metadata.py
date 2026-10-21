"""Load digest-bound historical D&C labels without rewriting the source.

Schema and rule: docs/data-sources/bsee/analysis/rig_days/frozen_dc_provenance.md.
This records an archived algorithm, not verified reproduction of a source run.
"""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path

import pandas as pd

# Schema edition 1, documented in frozen_dc_provenance.md, "Metadata contract".
SCHEMA_VERSION = 1
BASIS = "legacy_calendar_or_war_union_post_td_remarks"
STATUS = "historical_coverage_unknown"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate frozen metadata key")
        result[key] = value
    return result


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _validate(metadata):
    required = {
        "schema_version",
        "workbook_sha256",
        "sheet",
        "basis",
        "rule",
        "sources",
        "limitations",
        "pnd_days",
        "days_status",
        "reproduction_status",
    }
    if not isinstance(metadata, dict) or set(metadata) != required:
        raise ValueError("missing or unsupported frozen metadata fields")
    if (
        type(metadata["schema_version"]) is not int
        or metadata["schema_version"] != SCHEMA_VERSION
        or metadata["sheet"] != "Sheet1"
        or metadata["basis"] != BASIS
        or metadata["pnd_days"] is not None
        or metadata["days_status"] != STATUS
        or metadata["reproduction_status"] != "NOT_EVALUATED"
    ):
        raise ValueError("unsupported frozen metadata policy")
    digest = metadata["workbook_sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != hashlib.sha256().digest_size * 2
        or any(c not in "0123456789abcdef" for c in digest)
    ):
        raise ValueError("invalid frozen metadata digest")
    rule = metadata["rule"]
    if (
        not isinstance(rule, dict)
        or set(rule) != {"drilling", "completion", "missing_values", "pnd", "coverage"}
        or not all(_text(value) for value in rule.values())
    ):
        raise ValueError("missing frozen metadata rule")
    for field in ("sources", "limitations"):
        values = metadata[field]
        if not isinstance(values, list) or not values or not all(map(_text, values)):
            raise ValueError(f"missing frozen metadata {field}")


def load_frozen(workbook: Path, metadata_path: Path | None = None) -> pd.DataFrame:
    """Validate metadata and label an in-memory copy of the exact hashed bytes.

    PND and coverage were not recorded; neither missing dates nor historical
    zero counts are used to infer them. Schema edition 1 only supports this
    archival rule and explicitly unevaluated reproduction.
    """
    workbook = Path(workbook)
    sidecar = (
        Path(metadata_path)
        if metadata_path
        else workbook.with_suffix(".provenance.json")
    )
    try:
        metadata = json.loads(
            sidecar.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
        )
    except (OSError, ValueError) as error:
        raise ValueError("cannot read frozen metadata") from error
    _validate(metadata)
    payload = workbook.read_bytes()
    if hashlib.sha256(payload).hexdigest() != metadata["workbook_sha256"]:
        raise ValueError("frozen metadata digest mismatch")
    frame = pd.read_excel(BytesIO(payload), sheet_name=metadata["sheet"])
    if any(column in frame for column in ("BASIS", "PND_DAYS", "DAYS_STATUS")):
        raise ValueError("frozen metadata conflicts with workbook labels")
    # The JSON contract explicitly preserves unknowns instead of inferring zero.
    return frame.assign(
        BASIS=metadata["basis"],
        PND_DAYS=pd.Series(pd.NA, index=frame.index, dtype="Int64"),
        DAYS_STATUS=metadata["days_status"],
    )
