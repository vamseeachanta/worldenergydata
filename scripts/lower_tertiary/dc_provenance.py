"""Additive provenance labels for D&C publishing builders.

The presence of a BASIS, basis, basis_v30 or basis_wed column activates labels.
Existing day arithmetic remains in each builder. Nullable arithmetic applies
only to the added pnd_days column. Aggregate days_status may be mixed.
"""

from collections.abc import Iterable, Mapping
from html import escape

LABELS = ("basis", "basis_v30", "basis_wed", "pnd_days", "days_status")
DESCRIPTION = (
    "Days status preserves source coverage labels; aggregate statuses may be mixed."
)


def carries_basis(columns: Iterable[str]) -> bool:
    """Activate provenance only when an input has an explicit basis column."""
    return bool(set(columns) & {"BASIS", "basis", "basis_v30", "basis_wed"})


def _basis_value(raw: object, allow_mixed: bool = False) -> str | None:
    """Distinguish recorded rules from absent sides and aggregate labels."""
    if raw is None or str(raw) in ("", "<NA>"):
        return None
    if not isinstance(raw, str) or not raw.strip() or raw in ("nan", "unavailable"):
        raise ValueError("invalid recorded basis provenance")
    if raw == "mixed" and not allow_mixed:
        raise ValueError("recorded basis provenance requires a full rule")
    return raw


def nullable_days(raw: object) -> int | None:
    """Read the new PND label; an empty cell remains null."""
    if raw is None or str(raw).strip() in ("", "nan", "<NA>"):
        return None
    value = float(str(raw))
    if not value.is_integer() or value < 0:
        raise ValueError("day count must be a nonnegative integer or null")
    return int(value)


def provenance(row: Mapping) -> dict:
    """Validate labelled inputs; legacy rows acquire no new fields."""
    if not carries_basis(row):
        return {}
    required = ("BASIS", "PND_DAYS", "DAYS_STATUS")
    if any(key not in row for key in required):
        raise ValueError("missing provenance columns; regenerate extractor output")
    for key in ("BASIS", "DAYS_STATUS"):
        value = row[key]
        if not isinstance(value, str) or not value.strip() or value in ("nan", "<NA>"):
            raise ValueError("empty provenance; regenerate extractor output")
    if _basis_value(row["BASIS"]) is None:
        raise ValueError("empty provenance; regenerate extractor output")
    return {
        "basis": row["BASIS"],
        "pnd_days": nullable_days(row["PND_DAYS"]),
        "days_status": row["DAYS_STATUS"],
    }


def sum_days(values: Iterable[int | None]) -> int | None:
    """Sum only the added nullable PND label, preserving unknown contributors."""
    items = list(values)
    return None if not items or any(v is None for v in items) else sum(items)


def aggregate_basis(rows: Iterable[Mapping]) -> str:
    bases = {_basis_value(row["basis"], allow_mixed=True) for row in rows}
    if not bases or any(not isinstance(b, str) or not b.strip() for b in bases):
        raise ValueError("aggregate requires recorded basis")
    return next(iter(bases)) if len(bases) == 1 else "mixed"


def aggregate_provenance(rows: Iterable[Mapping]) -> dict:
    members = list(rows)
    if not members or not any("basis" in row for row in members):
        return {}
    if any("basis" not in row for row in members):
        raise ValueError("missing aggregate provenance")
    return {
        "basis": aggregate_basis(members),
        "pnd_days": sum_days(row["pnd_days"] for row in members),
        "days_status": aggregate_basis(
            {"basis": row["days_status"]} for row in members
        ),
    }


def validate_day_schema(columns: Iterable[str]) -> None:
    """Validate day-count output in a flow activated by basis-bearing input."""
    names = set(columns)
    if any(
        n in ("drill", "compl")
        or "days" in n
        or n.startswith(("drill_", "compl_", "d_"))
        for n in names
    ):
        if "basis" not in names:
            raise ValueError("day-count schema requires basis")


def require_publication_provenance(rows: Iterable[Mapping]) -> None:
    """Reject unlabelled rows before a publishing command writes any output.

    Issue #1076, Acceptance (2026), requires a basis beside published days.
    Historical loaders remain usable for inspection; publication requires all
    three labels, including nullable PND and the original coverage vocabulary.
    Aggregates may explicitly record ``mixed`` as their basis.
    """
    for row in rows:
        if any(key not in row for key in ("basis", "pnd_days", "days_status")):
            raise ValueError("missing publication provenance; regenerate labelled inputs")
        basis = row["basis"]
        if not isinstance(basis, str) or _basis_value(basis.strip(), allow_mixed=True) is None:
            raise ValueError("missing publication provenance basis")
        status = row["days_status"]
        # Coverage vocabulary from bsee.analysis.war_rig_days, plus aggregates.
        if not isinstance(status, str) or status not in (
            "war_covered",
            "no_war_activity",
            "war_covered_no_activity_code",
            "mixed",
        ):
            raise ValueError("invalid publication provenance status")
        nullable_days(row["pnd_days"])
        # An overall label cannot supply the missing rule for one vintage's
        # day counts. Outer-join-only rows genuinely have no opposite side.
        vintage = False
        for side, absent_category in (("v30", "wed_only"), ("wed", "v30_only")):
            if any(f"{phase}_{side}" in row for phase in ("drill", "compl")):
                vintage = True
                if (
                    row.get("category") != absent_category
                    and _basis_value(row.get(f"basis_{side}")) is None
                ):
                    raise ValueError("missing publication provenance for vintage side")
        if vintage:
            validate_vintage_row(row)


def validate_vintage_row(row: Mapping) -> None:
    """Validate labelled vintage schemas; absent vintage-side labels stay null."""
    if not carries_basis(row):
        return
    if any(key not in row for key in LABELS):
        raise ValueError("missing vintage provenance; regenerate vintage diff")
    known = {_basis_value(row[c]) for c in ("basis_v30", "basis_wed")}
    known.discard(None)
    expected = next(iter(known)) if len(known) == 1 else ("mixed" if known else None)
    if _basis_value(row["basis"], allow_mixed=True) != expected:
        raise ValueError("inconsistent vintage provenance basis")


def vintage_labels(frozen, candidate, apis: Iterable[str]) -> list[dict]:
    """Label existing vintage rows without changing comparisons or categories."""
    sources = []
    for frame in (frozen, candidate):
        labels = {}
        if carries_basis(frame.columns):
            for row in frame.dropna(subset=["API_WELL_NUMBER"]).to_dict("records"):
                api = str(row["API_WELL_NUMBER"]).strip().removesuffix(".0")
                labels[api] = provenance(row)
        sources.append(labels)
    result = []
    for api in apis:
        before, after = (source.get(api, {}) for source in sources)
        known = [row for row in (before, after) if row]
        meta = after or before
        result.append(
            {
                "basis": aggregate_basis(known) if known else None,
                "basis_v30": before.get("basis"),
                "basis_wed": after.get("basis"),
                "pnd_days": meta.get("pnd_days"),
                "days_status": meta.get("days_status"),
            }
        )
    return result


def _label_cells(row: Mapping, columns: Iterable[str]) -> str:
    cells = []
    for column in columns:
        raw = row.get(column)
        text = "—" if raw is None or str(raw) == "<NA>" else str(raw)
        cells.append(
            escape(text).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")
        )
    return " | ".join(cells)


def markdown_labels(lines: list[str], devs: Mapping, vintage: Mapping) -> list[str]:
    """Append metadata columns while retaining every original Markdown cell."""
    bores = {b["api12"]: b for rows in devs.values() for b in rows}
    vintages = {r["api12"]: r for rows in vintage.values() for r in rows}
    summaries = {
        f"[{dev}](#{dev.lower().replace(' ', '-')})": aggregate_provenance(rows)
        for dev, rows in devs.items()
    }
    summaries["**Total**"] = aggregate_provenance(bores.values())
    result, table, columns = [], {}, ()
    for line in lines:
        if line.startswith("| Development |"):
            table = summaries
        elif line.startswith("| API12 | Bore |"):
            table = bores
        elif line.startswith("| API12 | Development |"):
            table = vintages
        elif not line.startswith("|"):
            table = {}
        if line.startswith(("| Development |", "| API12 |")):
            columns = tuple(c for c in LABELS if any(c in r for r in table.values()))
            names = {
                "basis": "Basis",
                "basis_v30": "V30 basis",
                "basis_wed": "Candidate basis",
                "pnd_days": "PND (days)",
                "days_status": "Days status",
            }
            if columns:
                line += " " + " | ".join(names[c] for c in columns) + " |"
        elif table and columns and line.startswith("|---"):
            line += "---|" * len(columns)
        elif table and columns and line.startswith("|"):
            key = line.split("|", 2)[1].strip()
            if key in table:
                line += " " + _label_cells(table[key], columns) + " |"
        result.append(line)
    if any(carries_basis(row) for row in [*bores.values(), *vintages.values()]):
        result.extend([DESCRIPTION, ""])
    return result


def html_labels(payload: Mapping) -> str:
    """Render an additional label table without altering the existing explorer."""
    rows = []
    for surface, identifier in (("bores", "api"), ("fields", "name"), ("blocks", "id")):
        for row in payload[surface]:
            if carries_basis(row):
                rows.append({"record": f"{surface}: {row[identifier]}", **row})
    if not rows:
        return ""
    columns = tuple(c for c in LABELS if any(c in row for row in rows))
    names = {
        "basis": "Basis",
        "basis_v30": "V30 basis",
        "basis_wed": "Candidate basis",
        "pnd_days": "PND days",
        "days_status": "Days status",
    }
    head = "<th>Record</th>" + "".join(f"<th>{names[c]}</th>" for c in columns)
    body = "".join(
        "<tr><td>"
        + escape(row["record"])
        + "</td>"
        + "".join(
            "<td>" + escape("—" if row.get(c) is None else str(row[c])) + "</td>"
            for c in columns
        )
        + "</tr>"
        for row in rows
    )
    return (
        '<section class="panel"><h2>Recorded provenance</h2><p>'
        + DESCRIPTION
        + "</p><table><thead><tr>"
        + head
        + "</tr></thead><tbody>"
        + body
        + "</tbody></table></section>"
    )
