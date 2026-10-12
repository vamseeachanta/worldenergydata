"""Provenance and null-preserving arithmetic for D&C publishing builders.

``basis`` preserves the extractor's complete rule string. ``days_status``
preserves its WAR coverage vocabulary; it does not certify each activity's
measurement. ``pnd_days`` counts the opaque PND code separately.
"""

from collections.abc import Iterable, Mapping


def nullable_days(raw: object) -> int | None:
    """Read integral day counts; an empty cell is unknown, never zero."""
    if raw is None or str(raw).strip() in ("", "nan", "<NA>"):
        return None
    value = float(str(raw))
    if not value.is_integer() or value < 0:
        raise ValueError("day count must be a nonnegative integer or null")
    return int(value)


def provenance(row: Mapping) -> dict:
    """Require metadata from the extractor rather than infer legacy rules."""
    required = ("BASIS", "PND_DAYS", "DAYS_STATUS")
    if any(key not in row for key in required):
        raise ValueError("missing provenance columns; regenerate extractor output")
    if not str(row["BASIS"] or "").strip() or not str(row["DAYS_STATUS"] or "").strip():
        raise ValueError("empty provenance; regenerate extractor output")
    return {
        "basis": row["BASIS"],
        "pnd_days": nullable_days(row["PND_DAYS"]),
        "days_status": row["DAYS_STATUS"],
    }


def sum_days(values: Iterable[int | None]) -> int | None:
    """A total is unknown if any contributor is unknown (or none exist)."""
    items = list(values)
    return (
        None
        if not items or any(v is None for v in items)
        else sum(v for v in items if v is not None)
    )


def add_days(left: int | None, right: int | None) -> int | None:
    return sum_days((left, right))


def aggregate_basis(rows: Iterable[Mapping]) -> str:
    bases = {row["basis"] for row in rows}
    if not bases or any(not str(basis).strip() for basis in bases):
        raise ValueError("aggregate requires recorded basis")
    return next(iter(bases)) if len(bases) == 1 else "mixed"


def validate_day_schema(columns: Iterable[str]) -> None:
    """Every publishing table containing day values must expose its basis."""
    names = set(columns)
    if any(
        "days" in name or name.startswith(("drill_", "compl_", "d_")) for name in names
    ):
        if "basis" not in names:
            raise ValueError("day-count schema requires basis")


def validate_vintage_row(row: Mapping) -> None:
    """Vintage values must identify each source rule, not just an overall label."""
    required = ("basis", "basis_v30", "basis_wed", "pnd_days", "days_status")
    if any(key not in row for key in required):
        raise ValueError("missing vintage provenance; regenerate vintage diff")
    for column in ("basis", "basis_v30", "basis_wed"):
        value = row[column]
        if not isinstance(value, str) or not value.strip() or value in ("nan", "<NA>"):
            raise ValueError("empty vintage provenance; regenerate vintage diff")
