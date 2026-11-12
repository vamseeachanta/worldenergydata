"""Restate held nominal project costs using traceable, provisional 2026 indices.

Run ``python -m worldenergydata.cost.escalation --help`` from the repository root.
Method, assumptions and source limitations: ``docs/modules/cost/ESCALATION.md``.
No network access, FX conversion or changes to nominal source records occur.
"""

from __future__ import annotations

import argparse
from bisect import bisect_left
import csv
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Sequence

from worldenergydata.cost.timeseries.dataset import (
    read_sanctioned_csv,
    read_timeseries_csv,
)
from worldenergydata.cost.timeseries.normalization import MAX_INTERPOLATION_SPAN
from worldenergydata.cost.timeseries.schema import CostObservation


TARGET_YEAR = 2026
METHOD = "contiguous_ucci_endpoint_ppi_v1"
_UCCI = "index_ucci"
_MACHINERY = "index_ppi_machinery"
_DRILLING = "index_ppi_drilling"
_CPI = "index_cpi"
_COMPONENTS = {_UCCI, _MACHINERY, _DRILLING, _CPI}
_COST_COLUMNS = ("SANCTIONED_CAPEX_USD_MM", "ACTUAL_COST_USD_MM")
_CURATED = Path("data/modules/cost/curated")
_DERIVED_COLUMNS = (
    "NOMINAL_COST_COLUMN",
    "CAPEX_USD_MM_2026",
    "INDEX_USED",
    "INDEX_BASE_YEAR",
    "ESCALATION_FACTOR",
    "ESCALATION_NOTE",
    "INDEX_TRACE",
    "ESCALATION_METHOD",
    "PROJECTS_SHA256",
    "TIMESERIES_SHA256",
    "STATEMENT_YEARS_SHA256",
    "INPUT_DIGEST_BASIS",
)


def _json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _year(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("year must be an integer between 1970 and 2040")
    try:
        year = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("year must be an integer between 1970 and 2040") from exc
    if not 1970 <= year <= 2040:
        raise ValueError("year must be an integer between 1970 and 2040")
    return year


@dataclass(frozen=True)
class EscalationFactor:
    """Derived ratio and the actual index path, with source-resolvable anchors."""

    factor: float
    index_used: str
    note: str
    trace: tuple[dict, ...]


class CostEscalator:
    """Validated sourced USD index anchors; duplicate yearly prints are averaged.

    Only UCCI requires contiguous coverage of a segment. The PPI blend is an
    endpoint ratio, not a reconstructed annual chain. Its 50:50 weights are a
    declared method assumption, not an empirical project-component allocation.
    """

    def __init__(self, observations: Sequence[CostObservation]):
        buckets: dict[str, dict[int, list[CostObservation]]] = {}
        units: dict[str, set[str]] = {}
        regions: dict[str, set[str]] = {}
        for row in observations:
            component = row.component.value
            if component not in _COMPONENTS or row.value is None:
                continue
            if not math.isfinite(row.value) or row.value <= 0:
                raise ValueError(
                    f"{component}: index anchors must be finite and positive"
                )
            if not (row.unit == "index" or row.unit.startswith("index_")):
                raise ValueError(f"{component}: index unit required")
            if (
                row.currency != "USD"
                or row.price_basis.value != "nominal"
                or row.provenance.value != "sourced"
                or row.figure_type is None
                or row.figure_type.value != "index"
                or row.band.value != "n/a"
            ):
                raise ValueError(
                    f"{component}: expected sourced nominal global/US USD index anchors"
                )
            expected_region = "global" if component == _UCCI else "US"
            if row.region != expected_region:
                raise ValueError(f"{component}: region must be {expected_region}")
            buckets.setdefault(component, {}).setdefault(row.year, []).append(row)
            units.setdefault(component, set()).add(row.unit)
            regions.setdefault(component, set()).add(row.region)
        if any(len(values) != 1 for values in units.values()):
            raise ValueError("incompatible index units within a component")
        if any(len(values) != 1 for values in regions.values()):
            raise ValueError("incompatible index regions within a component")
        self._anchors: dict[str, dict[int, dict]] = {}
        for component, years in buckets.items():
            self._anchors[component] = {}
            for year, rows in years.items():
                # Sorting makes annual means and source order independent of CSV order.
                ordered = sorted(
                    rows, key=lambda row: _json(row.model_dump(mode="json"))
                )
                sources = []
                for row in ordered:
                    source = row.model_dump(mode="json")
                    sources.append(
                        {
                            key: source[key]
                            for key in (
                                "source_title",
                                "source_url",
                                "accessed_date",
                                "notes",
                                "confidence",
                                "provenance",
                            )
                        }
                    )
                self._anchors[component][year] = dict(
                    year=year,
                    value=sum(row.value / len(rows) for row in ordered),
                    unit=ordered[0].unit,
                    sources=sources,
                )

    def _point(self, component: str, year: int, extrapolate: bool = False) -> dict:
        anchors = self._anchors.get(component, {})
        years = sorted(anchors)
        if year in anchors:
            return dict(
                component=component,
                year=year,
                value=anchors[year]["value"],
                method="held_print_mean",
                anchors=[anchors[year]],
            )
        if len(years) < 2:
            raise LookupError("insufficient index coverage")
        position = bisect_left(years, year)
        if 0 < position < len(years):
            left, right = years[position - 1 : position + 1]
            if right - left - 1 > MAX_INTERPOLATION_SPAN:
                raise LookupError("unbridged index gap")
            method = "interpolated"
        elif extrapolate:
            left, right = years[:2] if position == 0 else years[-2:]
            distance = years[0] - year if position == 0 else year - years[-1]
            if distance > 1:
                raise LookupError("index extrapolation exceeds one year")
            method = "extrapolated"
        else:
            raise LookupError("index year outside held coverage")
        low, high = anchors[left]["value"], anchors[right]["value"]
        value = low + (high - low) * (year - left) / (right - left)
        if not math.isfinite(value) or value <= 0:
            raise LookupError("derived index must be finite and positive")
        return dict(
            component=component,
            year=year,
            value=value,
            method=method,
            anchors=[anchors[left], anchors[right]],
        )

    def _segment(
        self, component: str, base: int, target: int, extrapolate: bool = False
    ) -> tuple[float, str, list[dict]]:
        start = self._point(component, base, extrapolate)
        end = self._point(component, target, extrapolate)
        if component == _UCCI:
            interior = [
                self._point(component, year)
                for year in range(min(base, target), max(base, target) + 1)
            ]
            start["interpolated_coverage_years"] = [
                point["year"] for point in interior if point["method"] == "interpolated"
            ]
        return (
            end["value"] / start["value"],
            f"{component}[{base}:{target}]",
            [start, end],
        )

    def _ppi(self, base: int, target: int, extrapolate: bool = False):
        machinery, machinery_name, machinery_trace = self._segment(
            _MACHINERY, base, target, extrapolate
        )
        drilling, drilling_name, drilling_trace = self._segment(
            _DRILLING, base, target, extrapolate
        )
        return (
            0.5 * machinery + 0.5 * drilling,
            f"(0.5*{machinery_name}+0.5*{drilling_name})",
            machinery_trace + drilling_trace,
        )

    @staticmethod
    def _result(
        factor: float, name: str, trace: list[dict], note: str
    ) -> EscalationFactor:
        if not math.isfinite(factor) or factor <= 0:
            raise ValueError("escalation factor must be finite and positive")
        details = [
            note,
            "Derived path; differing index paths across rows limit comparability.",
        ]
        for step in trace:
            if step["method"] in {"interpolated", "extrapolated"}:
                details.append(f"{step['component']} {step['year']}: {step['method']}")
            coverage = step.get("interpolated_coverage_years", [])
            if coverage:
                details.append(f"UCCI interpolated coverage years={coverage}")
            for anchor in step["anchors"]:
                for source in anchor["sources"]:
                    if source["notes"]:
                        details.append(
                            f"{step['component']} {anchor['year']}: {source['notes']}"
                        )
        if any("PARTIAL YEAR" in item for item in details):
            details.append(
                "Provisional partial-year means; seasonal/timing bias against annual means is unquantified."
            )
        return EscalationFactor(
            factor, name, " ".join(dict.fromkeys(details)), tuple(trace)
        )

    def factor(
        self, base_year: int, target_year: int = TARGET_YEAR
    ) -> EscalationFactor:
        """Select one contiguous UCCI block then PPI, or PPI then last-resort CPI.

        Covered CPI precedes extrapolated PPI. UCCI is never extrapolated;
        other components may extrapolate one year only, with an explicit flag.
        """
        base, target = _year(base_year), _year(target_year)
        try:
            return self._result(
                *self._segment(_UCCI, base, target),
                "UCCI contiguous coverage; held period prints averaged within year.",
            )
        except LookupError:
            pass
        if base < target:
            try:
                self._point(_UCCI, base)
                join = base
                for year in range(base + 1, min(target, max(self._anchors[_UCCI])) + 1):
                    try:
                        self._point(_UCCI, year)
                    except LookupError:
                        break
                    join = year
                if base < join < target:
                    ucci, ucci_name, ucci_trace = self._segment(_UCCI, base, join)
                    ppi, ppi_name, ppi_trace = self._ppi(join, target)
                    return self._result(
                        ucci * ppi,
                        f"{ucci_name}*{ppi_name}",
                        ucci_trace + ppi_trace,
                        f"UCCI contiguous block ends at {join}; assumed 50:50 endpoint-ratio PPI blend thereafter; no UCCI re-entry. Global UCCI/US PPI splice.",
                    )
            except LookupError:
                pass
        for extrapolate in (False, True):
            try:
                return self._result(
                    *self._ppi(base, target, extrapolate),
                    "Assumed 50:50 machinery/drilling endpoint-ratio PPI blend; no eligible UCCI segment.",
                )
            except LookupError:
                pass
            try:
                return self._result(
                    *self._segment(_CPI, base, target, extrapolate),
                    "CPI last resort: both PPI components required and no eligible UCCI segment.",
                )
            except LookupError:
                pass
        raise ValueError(
            f"no usable index coverage for {base}:{target}; no unflagged extrapolation permitted"
        )


def _digest(path: Path) -> str:
    """SHA-256 of UTF-8 text with universal newlines normalized to LF."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def _records(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(set(reader.fieldnames)) != len(
            reader.fieldnames
        ):
            raise ValueError("CSV requires unique headers")
        rows = list(reader)
        if any(
            None in row or any(value is None for value in row.values()) for row in rows
        ):
            raise ValueError("CSV row width does not match header")
        return rows


def _statement_years(path: Path | None, projects: list[dict]) -> dict:
    if path is None:
        return {}
    lookup = {(row["PROJECT"], row["SOURCE_URL"]): row for row in projects}
    if len(lookup) != len(projects):
        raise ValueError(
            "statement-year sidecar requires unambiguous project/source identities"
        )
    decisions = {}
    for record in _records(path):
        required = {
            "PROJECT",
            "SOURCE_URL",
            "COST_COLUMN",
            "COST_STATEMENT_YEAR",
            "EVIDENCE",
            "RATIONALE",
        }
        if not required.issubset(record):
            raise ValueError("statement-year sidecar missing required columns")
        project_key = record["PROJECT"], record["SOURCE_URL"]
        cost_column = record["COST_COLUMN"]
        key = (*project_key, cost_column)
        year = _year(record["COST_STATEMENT_YEAR"])
        evidence = record["EVIDENCE"].strip()
        source = lookup.get(project_key)
        if (
            source is None
            or key in decisions
            or cost_column not in _COST_COLUMNS
            or not source.get(cost_column, "").strip()
            or not evidence
            or str(year) not in evidence
            or not record.get("RATIONALE", "").strip()
            or not any(
                evidence in source[field]
                for field in ("CAPEX_BASIS", "SOURCE_TITLE", "NOTES")
            )
        ):
            raise ValueError(
                "statement-year sidecar has unmatched, duplicate or unsupported evidence"
            )
        decisions[key] = (year, evidence, record["RATIONALE"])
    return decisions


def build_projects(
    projects_path: Path, indices_path: Path, statement_years_path: Path | None = None
) -> list[dict[str, str]]:
    """Build derived rows while retaining every original nominal field verbatim.

    A primary sanctioned row is retained for every project, plus one row for
    each held actual/revised amount. Explicit COST_STATEMENT_YEAR applies to
    sanctioned costs; ACTUAL_COST_STATEMENT_YEAR applies independently to actuals.
    """
    projects_path, indices_path = Path(projects_path), Path(indices_path)
    statement_years_path = (
        Path(statement_years_path) if statement_years_path is not None else None
    )
    paths = [projects_path, indices_path] + (
        [statement_years_path] if statement_years_path else []
    )
    before = {path: _digest(path) for path in paths}
    read_sanctioned_csv(projects_path)  # Existing project/basis/schema validation.
    projects = _records(projects_path)
    if not projects:
        raise ValueError("project input must contain rows")
    if set(projects[0]) & set(_DERIVED_COLUMNS):
        raise ValueError("input already contains derived escalation columns")
    decisions = _statement_years(statement_years_path, projects)
    calculator = CostEscalator(read_timeseries_csv(indices_path))
    output = []
    for source in projects:
        for cost_column in _COST_COLUMNS:
            nominal = source[cost_column].strip()
            if cost_column == "ACTUAL_COST_USD_MM" and not nominal:
                continue
            row = dict(source)
            row.update({key: "" for key in _DERIVED_COLUMNS})
            row.update(
                NOMINAL_COST_COLUMN=cost_column,
                ESCALATION_METHOD=METHOD,
                PROJECTS_SHA256=before[projects_path],
                TIMESERIES_SHA256=before[indices_path],
                STATEMENT_YEARS_SHA256=before.get(statement_years_path, ""),
                INPUT_DIGEST_BASIS="sha256_utf8_lf",
            )
            if nominal:
                amount = float(nominal)
                if not math.isfinite(amount) or amount < 0:
                    raise ValueError("nominal cost must be finite and nonnegative")
                if (
                    source.get("CURRENCY", "USD").strip().upper() != "USD"
                    or source.get("PRICE_BASIS", "nominal").strip().lower() != "nominal"
                ):
                    raise ValueError(
                        "project escalation requires nominal USD; no FX or implicit rebasing"
                    )
                if (
                    not source["CAPEX_BASIS"].strip()
                    or not all(
                        source[key].strip()
                        for key in (
                            "SOURCE_TITLE",
                            "SOURCE_URL",
                            "QUOTED_TEXT",
                            "ACCESSED_DATE",
                        )
                    )
                    or not source["SOURCE_URL"].startswith(("http://", "https://"))
                ):
                    raise ValueError(
                        "valued project cost requires basis and source provenance"
                    )
                year_field = (
                    "COST_STATEMENT_YEAR"
                    if cost_column == _COST_COLUMNS[0]
                    else "ACTUAL_COST_STATEMENT_YEAR"
                )
                explicit = source.get(year_field, "").strip()
                decision = decisions.get(
                    (source["PROJECT"], source["SOURCE_URL"], cost_column)
                )
                if explicit:
                    base = _year(explicit)
                    if decision is not None and base != decision[0]:
                        raise ValueError(
                            "explicit statement year conflicts with reviewed sidecar decision"
                        )
                    basis_note = f"Explicit statement year from {year_field}."
                    if decision is not None:
                        basis_note += (
                            f" Agrees with held evidence: {decision[1]}; {decision[2]}."
                        )
                elif decision:
                    base, evidence, rationale = decision
                    basis_note = (
                        f"Held statement year decision: {evidence}; {rationale}."
                    )
                else:
                    base = _year(source["FID_YEAR"].strip())
                    basis_note = "FID year fallback: cost statement year unestablished."
                    if cost_column == _COST_COLUMNS[1]:
                        basis_note += " Actual/revised cost can postdate FID. Bias direction is unknown and path-dependent; the fallback may overstate or understate escalation. Its magnitude cannot be established until the statement year is known."
                        earlier_statement = decisions.get(
                            (source["PROJECT"], source["SOURCE_URL"], _COST_COLUMNS[0])
                        )
                        if earlier_statement and earlier_statement[0] > base:
                            basis_note += f" Chronology inversion: the final/revised disclosure follows the held {earlier_statement[0]} statement, but its exact year is unestablished; the issue-prescribed FID fallback is {base}, not a claim of an earlier actual-cost price vintage. Comparisons remain approximate until a dated source is obtained."
                result = calculator.factor(base)
                escalated = amount * result.factor
                if not math.isfinite(escalated):
                    raise ValueError("escalated cost must be finite")
                context = (
                    "Preserved historical source context (populated nominal label takes precedence over stale null notes; historical wording is not a current finding): "
                    + source["CAPEX_BASIS"]
                    + " | "
                    + source["NOTES"]
                )
                row.update(
                    CAPEX_USD_MM_2026=str(escalated),
                    INDEX_USED=result.index_used,
                    INDEX_BASE_YEAR=str(base),
                    ESCALATION_FACTOR=str(result.factor),
                    ESCALATION_NOTE=f"{basis_note} {result.note} {context}",
                    INDEX_TRACE=_json(result.trace),
                )
            else:
                row["ESCALATION_NOTE"] = (
                    "No disclosed nominal USD sanctioned CAPEX; derived amount remains blank."
                )
            output.append(row)
    if any(_digest(path) != digest for path, digest in before.items()):
        raise ValueError("input changed during escalation; discard derived results")
    return output


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: explicit inputs, deterministic UTF-8/LF derived CSV, no live fetches."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects", type=Path, default=_CURATED / "sanctioned_projects.csv"
    )
    parser.add_argument(
        "--indices", type=Path, default=_CURATED / "cost_component_timeseries.csv"
    )
    parser.add_argument(
        "--statement-years",
        type=Path,
        help="optional year sidecar; auto-selects an existing sidecar beside sanctioned_projects.csv",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    sidecar = args.statement_years
    if sidecar is None and args.projects.name == "sanctioned_projects.csv":
        adjacent = args.projects.resolve().with_name(
            "sanctioned_project_cost_years.csv"
        )
        if adjacent.exists():
            sidecar = adjacent
    for path in (args.projects, args.indices, sidecar):
        if path is not None and (
            args.output.resolve() == path.resolve()
            or (args.output.exists() and args.output.samefile(path))
        ):
            raise ValueError("output must not overwrite an input")
    rows = build_projects(args.projects, args.indices, sidecar)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=args.output.parent,
            prefix=f".{args.output.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(
                handle, fieldnames=list(rows[0]), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, args.output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(
        f"Projects: {sum(row['NOMINAL_COST_COLUMN'] == _COST_COLUMNS[0] for row in rows)}; "
        f"derived nominal costs: {sum(bool(row['CAPEX_USD_MM_2026']) for row in rows)}; rows: {len(rows)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        print(f"escalation: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
