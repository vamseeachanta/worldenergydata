"""Read-only BSEE/FDAS CSV readiness evidence for well-operations runs.

Contract: https://github.com/vamseeachanta/worldenergydata/issues/451
This bounded slice inspects explicitly selected catalog entries, never refreshes
or deserializes binary inputs, and makes no publication or engineering-validity
claim. Metadata (vintage, sample scope, locality, pending ingest) is supplied by
the catalog consumer; file modification time is not a source-vintage proxy.

Example::

    evidence = probe_source(
        dataset, data_root, source="bsee", as_of=observation_time,
        data_as_of=source_vintage, max_age=freshness_criterion,
        required_columns=("API_WELL_NUMBER", "LEASE_NUMBER"),
        entity_columns={"well": ("API_WELL_NUMBER",),
                        "lease": ("LEASE_NUMBER",)},
        sampled=False, local_only=False,
    )

Freshness is elapsed time <= the caller's maximum age, with future vintages
rejected. No standard prescribes a default age here; the intended-use criterion
is a required input. Entity mappings are explicit caller assertions about column
semantics, confirmed only for columns with observed nonblank values. For FDAS
column names see fdas/adapters/bsee_adapter.py (WellDataAdapter and
ProductionDataAdapter); other source schemas require their own mappings.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path

from worldenergydata.common.catalog import DatasetEntry

# Entity vocabulary from issue 451, acceptance criteria (not inferred joins).
_ENTITIES = {
    "well",
    "borehole",
    "lease",
    "field",
    "operator",
    "completion",
    "production_interval",
    "activity",
    "operation",
}


def _inspect_csv(path, required_columns, entity_columns):
    """Stream CSV records; return observed structure without retaining payloads."""
    count = 0
    observed = set()
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            # Git LFS pointer specification v1, 'The version' section:
            # https://github.com/git-lfs/git-lfs/blob/main/docs/spec.md
            if (
                stream.readline().strip()
                == "version https://git-lfs.github.com/spec/v1"
            ):
                return "lfs_stub", 0, {}, [], []
            stream.seek(0)
            reader = csv.reader(stream, strict=True)
            header = next(reader, [])
            if not header:
                return "empty", 0, {}, [], []
            if any(not name.strip() for name in header) or len(set(header)) != len(
                header
            ):
                return "invalid", 0, {}, [], []
            for row in reader:
                if not row:
                    continue
                if len(row) != len(header):
                    return "invalid", count, {}, [], []
                if any(value.strip() for value in row):
                    count += 1
                    observed.update(
                        name for name, value in zip(header, row) if value.strip()
                    )
    except FileNotFoundError:
        return "missing", 0, {}, [], []
    except (UnicodeError, csv.Error):
        return "invalid", 0, {}, [], []
    except OSError:
        return "unreadable", 0, {}, [], []
    entities = {
        entity: [column for column in columns if column in observed]
        for entity, columns in entity_columns.items()
        if any(column in observed for column in columns)
    }
    missing = sorted(set(required_columns) - set(header))
    unpopulated = sorted((set(required_columns) & set(header)) - observed)
    return "available" if count else "empty", count, entities, missing, unpopulated


def probe_source(
    dataset: DatasetEntry,
    data_root: Path,
    *,
    source: str,
    as_of: datetime,
    data_as_of: datetime | None,
    max_age: timedelta,
    required_columns: tuple[str, ...],
    entity_columns: Mapping[str, tuple[str, ...]],
    sampled: bool,
    local_only: bool,
    allow_local: bool = False,
    blocked_by: tuple[str, ...] = (),
) -> dict:
    """Return JSON-compatible, path-free evidence for one selected catalog entry.

    ``usable`` denotes CSV structure/freshness/scope eligibility only. It does
    not qualify units, provenance, field values, script imports or publication.
    ``blocked_by`` contains unresolved ingest issue references supplied by the
    caller; unrelated open issues must not automatically block all datasets.
    Absolute paths, parent traversal and symlink escapes from the explicitly
    supplied data root are rejected. External roots require ``local_only=True``
    from the caller and ``allow_local=True`` for consumption eligibility.
    """
    if source not in {"bsee", "fdas"}:
        raise ValueError("source must be bsee or fdas")
    if any(type(flag) is not bool for flag in (sampled, local_only, allow_local)):
        raise ValueError("scope flags must be explicit booleans")
    if max_age < timedelta(0):
        raise ValueError("max_age must be nonnegative")
    if not required_columns or any(not column.strip() for column in required_columns):
        raise ValueError("required_columns must contain named columns")
    if set(entity_columns) - _ENTITIES:
        raise ValueError("unknown entity mapping")
    for columns in (required_columns, *entity_columns.values()):
        if (
            isinstance(columns, str)
            or not columns
            or any(
                not isinstance(column, str) or not column.strip() for column in columns
            )
        ):
            raise ValueError("column mappings must contain named columns")
    for instant in (as_of, data_as_of):
        if instant is not None and instant.utcoffset() is None:
            raise ValueError("timestamps must include timezone information")
    root = Path(data_root).resolve()
    relative = Path(dataset.path)
    path = (root / relative).resolve()
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not path.is_relative_to(root)
    ):
        raise ValueError("dataset path must remain within the explicit data root")
    if dataset.format.lower() != "csv":
        availability, rows, entities, missing, unpopulated = (
            "unsupported",
            0,
            {},
            [],
            [],
        )
    else:
        availability, rows, entities, missing, unpopulated = _inspect_csv(
            path, required_columns, entity_columns
        )
    freshness = "not_evaluated"
    if data_as_of is not None:
        age = as_of - data_as_of
        freshness = (
            "future"
            if age < timedelta(0)
            else ("current" if age <= max_age else "stale")
        )
    reasons = []
    if availability != "available":
        reasons.append(availability)
    if freshness != "current":
        reasons.append(freshness)
    if missing:
        reasons.append("missing_columns")
    if unpopulated:
        reasons.append("unpopulated_columns")
    if sampled:
        reasons.append("sampled")
    if local_only and not allow_local:
        reasons.append("external_root_requires_opt_in")
    if blocked_by:
        reasons.append("pending_ingest")
    return {
        "dataset": dataset.name,
        "source": source,
        "as_of": as_of.isoformat(),
        "data_as_of": data_as_of.isoformat() if data_as_of is not None else None,
        "max_age_seconds": max_age.total_seconds(),
        "availability": availability,
        "freshness": freshness,
        "row_count": rows,
        "entities": entities,
        "missing_columns": missing,
        "unpopulated_columns": unpopulated,
        "sampled": sampled,
        "local_only": local_only,
        "blocked_by": list(blocked_by),
        "reasons": reasons,
        "usable": not reasons,
        "publication_eligibility": "not_evaluated",
        "limitations": [
            "Caller-supplied metadata and entity semantics are not independently verified.",
            "CSV structure is inspected; units, values and source rights are not qualified.",
            "No script execution or workflow-manifest integration is established.",
        ],
    }
