"""
ABOUTME: Reads/writes the curated cost-basis CSVs and the sanctioned-project table (issue #844).
ABOUTME: The CSVs are the primary artifact — the code exists to keep them honest, not the reverse.

Layout under ``data/modules/cost/curated/``:

* ``cost_component_timeseries.csv`` — every ``CostObservation``: rig and vessel
  day rates, indices, reference series. One row per (year, component, band,
  source). This is the "year x cost-component x band" table #844 asks for.
* ``sanctioned_projects.csv``      — the top-down anchor table (scope addition #2).

Both carry UPPER_SNAKE headers per the house convention for curated datasets.
Both carry full provenance on every row. A row without a source is a TODO row
with a blank value — never a number.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

from worldenergydata.cost.timeseries.schema import (
    CostComponent,
    CostObservation,
    DevelopmentSystemBand,
    DisclosureConfidence,
    FigureType,
    PriceBasis,
    Provenance,
    SourcePriority,
    csv_header,
    to_csv_row,
)

__all__ = [
    "TIMESERIES_CSV",
    "SANCTIONED_CSV",
    "SanctionedProject",
    "SANCTIONED_CSV_COLUMNS",
    "write_timeseries_csv",
    "read_timeseries_csv",
    "write_sanctioned_csv",
    "read_sanctioned_csv",
    "curated_dir",
]

TIMESERIES_CSV = "cost_component_timeseries.csv"
SANCTIONED_CSV = "sanctioned_projects.csv"


def curated_dir(project_root: Path) -> Path:
    return project_root / "data" / "modules" / "cost" / "curated"


# ---------------------------------------------------------------------------
# Component time-series
# ---------------------------------------------------------------------------


def write_timeseries_csv(rows: Iterable[CostObservation], path: Path) -> int:
    """Write the component time-series. Returns the row count written.

    Rows are sorted (component, year, region, source) so the file is stable
    across refreshes and a `git diff` shows only what actually changed.
    """
    ordered = sorted(
        rows,
        key=lambda o: (
            o.component.value,
            o.year,
            o.band.value,
            o.region,
            o.source_title or "",
        ),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(csv_header())
        for obs in ordered:
            writer.writerow(to_csv_row(obs))
    return len(ordered)


def _blank_to_none(value: str) -> Optional[str]:
    value = (value or "").strip()
    return value or None


def read_timeseries_csv(path: Path) -> list[CostObservation]:
    """Read the component time-series back into validated models.

    Re-validating on read is deliberate: the CSV is hand-editable (that is a
    feature — a researcher can add a sourced row in a spreadsheet), so the
    schema's honesty rules must be re-applied on the way back in. A hand-added
    row with a value but no citation will fail here, loudly.
    """
    out: list[CostObservation] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            raw_value = _blank_to_none(record["VALUE"])
            raw_basis_year = _blank_to_none(record["BASIS_YEAR"])
            raw_accessed = _blank_to_none(record["ACCESSED_DATE"])
            raw_figure = _blank_to_none(record["FIGURE_TYPE"])
            raw_conf = _blank_to_none(record["CONFIDENCE"])
            raw_priority = _blank_to_none(record["SOURCE_PRIORITY"])

            out.append(
                CostObservation(
                    year=int(record["YEAR"]),
                    component=CostComponent(record["COMPONENT"]),
                    band=DevelopmentSystemBand(record["BAND"]),
                    value=float(raw_value) if raw_value else None,
                    unit=record["UNIT"],
                    currency=record["CURRENCY"] or "USD",
                    price_basis=PriceBasis(record["PRICE_BASIS"]),
                    basis_year=int(raw_basis_year) if raw_basis_year else None,
                    figure_type=FigureType(raw_figure) if raw_figure else None,
                    segment=_blank_to_none(record["SEGMENT"]),
                    region=record["REGION"] or "global",
                    provenance=Provenance(record["PROVENANCE"]),
                    source_title=_blank_to_none(record["SOURCE_TITLE"]),
                    source_url=_blank_to_none(record["SOURCE_URL"]),
                    page_reference=_blank_to_none(record["PAGE_REFERENCE"]),
                    quoted_text=_blank_to_none(record["QUOTED_TEXT"]),
                    accessed_date=date.fromisoformat(raw_accessed) if raw_accessed else None,
                    confidence=DisclosureConfidence(raw_conf) if raw_conf else None,
                    source_priority=SourcePriority(raw_priority) if raw_priority else None,
                    notes=_blank_to_none(record["NOTES"]),
                )
            )
    return out


# ---------------------------------------------------------------------------
# Sanctioned projects (scope addition #2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SanctionedProject:
    """A deepwater project's disclosed cost and scope — the top-down anchor.

    ``capex_basis`` is not optional decoration. A CAPEX figure without its basis
    ("gross project cost at FID" vs "operator net share" vs "phase 1 only") is
    unusable, and mixing the two silently is the single easiest way to corrupt a
    benchmark table. It is required on every row that carries a CAPEX.
    """

    project: str
    operator: str
    region: str
    country: str
    water_depth_m: Optional[float]
    fid_year: Optional[int]
    first_oil_year: Optional[int]
    sanctioned_capex_usd_mm: Optional[float]
    actual_cost_usd_mm: Optional[float]
    capex_basis: Optional[str]
    well_count: Optional[int]
    development_type: str
    host_type: Optional[str]
    surf_km: Optional[float]
    peak_production_boepd: Optional[float]
    recoverable_resource_mmboe: Optional[float]
    usd_per_boe: Optional[float]
    # provenance
    source_title: str
    source_url: str
    page_reference: str
    quoted_text: str
    accessed_date: date
    confidence: DisclosureConfidence
    source_priority: SourcePriority
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.sanctioned_capex_usd_mm is not None and not self.capex_basis:
            raise ValueError(
                f"{self.project}: a CAPEX figure without a stated capex_basis is "
                "unusable — is it gross, net, or phase-only?"
            )

    @property
    def derived_usd_per_boe(self) -> Optional[float]:
        """$/boe from CAPEX and recoverable resource, when both are disclosed."""
        if (
            self.sanctioned_capex_usd_mm
            and self.recoverable_resource_mmboe
            and self.recoverable_resource_mmboe > 0
        ):
            return self.sanctioned_capex_usd_mm / self.recoverable_resource_mmboe
        return None


SANCTIONED_CSV_COLUMNS: tuple[str, ...] = (
    "project",
    "operator",
    "region",
    "country",
    "water_depth_m",
    "fid_year",
    "first_oil_year",
    "sanctioned_capex_usd_mm",
    "actual_cost_usd_mm",
    "capex_basis",
    "well_count",
    "development_type",
    "host_type",
    "surf_km",
    "peak_production_boepd",
    "recoverable_resource_mmboe",
    "usd_per_boe",
    "source_title",
    "source_url",
    "page_reference",
    "quoted_text",
    "accessed_date",
    "confidence",
    "source_priority",
    "notes",
)


def write_sanctioned_csv(projects: Iterable[SanctionedProject], path: Path) -> int:
    ordered = sorted(projects, key=lambda p: (p.fid_year or 9999, p.project))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([name.upper() for name in SANCTIONED_CSV_COLUMNS])
        for project in ordered:
            row: list[str] = []
            for name in SANCTIONED_CSV_COLUMNS:
                value = getattr(project, name)
                if name == "usd_per_boe" and value is None:
                    # Derive it when the inputs are there; leave blank otherwise.
                    value = project.derived_usd_per_boe
                    if value is not None:
                        value = round(value, 2)
                if value is None:
                    row.append("")
                elif isinstance(value, date):
                    row.append(value.isoformat())
                elif hasattr(value, "value"):  # Enum
                    row.append(value.value)
                else:
                    row.append(str(value))
            writer.writerow(row)
    return len(ordered)


def _opt_float(value: str) -> Optional[float]:
    value = (value or "").strip()
    return float(value) if value else None


def _opt_int(value: str) -> Optional[int]:
    value = (value or "").strip()
    return int(float(value)) if value else None


def read_sanctioned_csv(path: Path) -> list[SanctionedProject]:
    out: list[SanctionedProject] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            out.append(
                SanctionedProject(
                    project=record["PROJECT"],
                    operator=record["OPERATOR"],
                    region=record["REGION"],
                    country=record["COUNTRY"],
                    water_depth_m=_opt_float(record["WATER_DEPTH_M"]),
                    fid_year=_opt_int(record["FID_YEAR"]),
                    first_oil_year=_opt_int(record["FIRST_OIL_YEAR"]),
                    sanctioned_capex_usd_mm=_opt_float(record["SANCTIONED_CAPEX_USD_MM"]),
                    actual_cost_usd_mm=_opt_float(record["ACTUAL_COST_USD_MM"]),
                    capex_basis=_blank_to_none(record["CAPEX_BASIS"]),
                    well_count=_opt_int(record["WELL_COUNT"]),
                    development_type=record["DEVELOPMENT_TYPE"],
                    host_type=_blank_to_none(record["HOST_TYPE"]),
                    surf_km=_opt_float(record["SURF_KM"]),
                    peak_production_boepd=_opt_float(record["PEAK_PRODUCTION_BOEPD"]),
                    recoverable_resource_mmboe=_opt_float(record["RECOVERABLE_RESOURCE_MMBOE"]),
                    usd_per_boe=_opt_float(record["USD_PER_BOE"]),
                    source_title=record["SOURCE_TITLE"],
                    source_url=record["SOURCE_URL"],
                    page_reference=record["PAGE_REFERENCE"],
                    quoted_text=record["QUOTED_TEXT"],
                    accessed_date=date.fromisoformat(record["ACCESSED_DATE"]),
                    confidence=DisclosureConfidence(record["CONFIDENCE"]),
                    source_priority=SourcePriority(record["SOURCE_PRIORITY"]),
                    notes=_blank_to_none(record["NOTES"]),
                )
            )
    return out
