"""
ABOUTME: Row contract for the living cost-basis time-series (issue #844).
ABOUTME: Every cost figure carries provenance; unsourced figures are TODO rows, never guesses.

Design notes
------------
The provenance block deliberately mirrors ``DisclosureCitation`` from
``worldenergydata.cost.data_collection.disclosure_ingest_contract`` (the #361
calc-citation-contract as it landed for the #334 disclosure layer): the same
``source_title / source_url / page_reference / quoted_text / confidence /
source_priority`` fields, so a cost-basis row and a disclosure row can be
reconciled field-for-field.

On top of that, a *time-series* row needs four things a point-in-time
disclosure row does not:

* ``accessed_date``  — when we pulled it (sources mutate / vanish)
* ``basis_year``     — the year the money is denominated in
* ``currency``       — ISO code; we only accept USD today but the column exists
* ``price_basis``    — NOMINAL vs REAL, the flag that makes issue #844's
  inflation-normalization requirement (scope addition #1) checkable

``Provenance`` is the honesty column that the HTML report colour-codes on.
A row is SOURCED (we read the number on a citable page), FITTED (a curve
produced it — see ``trend_fit``), ASSUMED (an engineering assumption we own
and state), or TODO (we know we need this cell and have not sourced it).
A TODO row carries ``value=None``. That is the whole anti-fabrication
mechanism: the schema makes "I don't know" representable, so there is never a
reason to invent a number.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Re-exported so callers building cost rows use the *same* confidence /
# priority vocabulary as the disclosure ingest contract rather than a parallel
# one that drifts.
from worldenergydata.cost.data_collection.disclosure_ingest_contract import (
    DisclosureConfidence,
    SourcePriority,
)

__all__ = [
    "CostComponent",
    "Provenance",
    "PriceBasis",
    "FigureType",
    "DevelopmentSystemBand",
    "CostObservation",
    "DisclosureConfidence",
    "SourcePriority",
]


class CostComponent(str, Enum):
    """The cost components issue #844 tracks through time.

    Kept flat (not nested) because the CSV is the primary artifact and a flat
    enum is what a spreadsheet user can filter on.
    """

    # Drilling / completion
    RIG_DAY_RATE_DRILLSHIP = "rig_day_rate_drillship"
    RIG_DAY_RATE_SEMI = "rig_day_rate_semi"
    RIG_DAY_RATE_JACKUP = "rig_day_rate_jackup"
    WELL_COST_DRILL = "well_cost_drill"
    WELL_COST_COMPLETE = "well_cost_complete"

    # Installation / construction spread
    VESSEL_DAY_RATE_HEAVY_LIFT = "vessel_day_rate_heavy_lift"
    VESSEL_DAY_RATE_PIPELAY = "vessel_day_rate_pipelay"
    VESSEL_DAY_RATE_MSV = "vessel_day_rate_msv"
    VESSEL_DAY_RATE_OSV_PSV = "vessel_day_rate_osv_psv"
    VESSEL_DAY_RATE_AHTS = "vessel_day_rate_ahts"
    VESSEL_DAY_RATE_WELL_INTERVENTION = "vessel_day_rate_well_intervention"

    # Facilities / SURF
    SURF_COST = "surf_cost"
    HOST_CAPEX = "host_capex"
    INSTALL_HOOKUP_COST = "install_hookup_cost"

    # Operating
    OPEX_VARIABLE = "opex_variable"
    OPEX_FIXED = "opex_fixed"

    # Reference / deflator series (not a field cost — the yardsticks)
    INDEX_UCCI = "index_ucci"
    INDEX_UOCI = "index_uoci"
    INDEX_CPI = "index_cpi"
    INDEX_PPI_DRILLING = "index_ppi_drilling"
    INDEX_PPI_SUPPORT = "index_ppi_support"
    INDEX_PPI_MACHINERY = "index_ppi_machinery"
    OIL_PRICE_BRENT = "oil_price_brent"
    OIL_PRICE_WTI = "oil_price_wti"


class Provenance(str, Enum):
    """How this cell came to hold the number it holds.

    This is the column the report colour-codes. It is the difference between a
    dataset you can defend to Frontier / Roy Shilling / Chuck White and one you
    cannot.
    """

    SOURCED = "sourced"  # read off a citable page; citation block is mandatory
    FITTED = "fitted"  # produced by a trend curve (trend_fit.py)
    ALLOCATED = "allocated"  # back-allocated from a sanctioned project total
    ASSUMED = "assumed"  # our engineering assumption, stated and owned
    TODO = "todo"  # known gap. value MUST be None. NEVER a guess.


class PriceBasis(str, Enum):
    """Nominal (money-of-the-day) vs real (deflated to a basis year)."""

    NOMINAL = "nominal"
    REAL = "real"


class FigureType(str, Enum):
    """What kind of number this is — an average is not a fixture."""

    MARKET_AVERAGE = "market_average"
    FLEET_AVERAGE = "fleet_average"
    INDEX = "index"
    SPOT_RATE = "spot_rate"
    SINGLE_FIXTURE = "single_fixture"
    RANGE_LOW = "range_low"
    RANGE_HIGH = "range_high"
    LUMP_SUM_CONTRACT = "lump_sum_contract"
    DISCLOSED_TOTAL = "disclosed_total"


class DevelopmentSystemBand(str, Enum):
    """Water-depth / development-system band.

    Issue #844 asks for segmentation "by water-depth / development-system band
    where the cost basis differs (subsea15/subsea20/tieback/dry)" — those four
    names come from the FDAS ``lease_assumptions.xlsx`` deck this dataset is
    meant to supersede, so they are reproduced verbatim rather than renamed.
    ``NOT_APPLICABLE`` is for rows (rig day rates, indices) whose cost basis is
    a market-wide rate and genuinely does not vary by band.
    """

    SUBSEA_15 = "subsea15"  # subsea tieback/development, ~15 kpsi class
    SUBSEA_20 = "subsea20"  # subsea, 20 kpsi class (Anchor/Whale-era HPHT)
    TIEBACK = "tieback"  # tieback to an existing host
    DRY = "dry"  # dry-tree host (spar/TLP)
    NOT_APPLICABLE = "n/a"  # market-wide rate; no band dependence


class CostObservation(BaseModel):
    """One cell of the living cost-basis time-series.

    The unit of the dataset. One year, one component, one band, one number —
    plus everything a reader needs to decide whether to believe it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # ---- what / when -----------------------------------------------------
    year: int = Field(..., ge=1970, le=2040)
    component: CostComponent
    band: DevelopmentSystemBand = DevelopmentSystemBand.NOT_APPLICABLE

    # ---- the number ------------------------------------------------------
    # Optional because a TODO row is a legitimate, *required* representation of
    # a gap. See the module docstring: this is the anti-fabrication mechanism.
    value: Optional[float] = Field(default=None)
    unit: str = Field(..., min_length=1, description="e.g. usd_per_day, usd_mm, index")

    # ---- money semantics (scope addition #1) -----------------------------
    currency: str = Field(default="USD", min_length=3, max_length=3)
    price_basis: PriceBasis = PriceBasis.NOMINAL
    basis_year: Optional[int] = Field(
        default=None,
        ge=1970,
        le=2040,
        description="Year the money is denominated in. Required when price_basis=REAL.",
    )

    # ---- interpretation --------------------------------------------------
    figure_type: Optional[FigureType] = None
    segment: Optional[str] = Field(
        default=None, description="e.g. ultra_deepwater, harsh_environment"
    )
    region: str = Field(default="global", min_length=1)

    # ---- honesty ---------------------------------------------------------
    provenance: Provenance

    # ---- provenance block (mirrors DisclosureCitation) -------------------
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    page_reference: Optional[str] = None
    quoted_text: Optional[str] = None
    accessed_date: Optional[date] = None
    confidence: Optional[DisclosureConfidence] = None
    source_priority: Optional[SourcePriority] = None

    notes: Optional[str] = None

    @field_validator("source_url")
    @classmethod
    def _require_absolute_http(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("source_url must be an absolute http(s) URL")
        return value

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def _enforce_provenance_contract(self) -> "CostObservation":
        """The rule that makes this dataset defensible.

        SOURCED  => must carry a real citation AND a value.
        TODO     => must NOT carry a value (a TODO with a number is a guess
                    wearing a disguise, which is exactly what #844 forbids).
        REAL     => must declare the basis_year it was deflated to, else the
                    number is meaningless.
        FITTED / ALLOCATED / ASSUMED => must carry a value and say *why* in
                    notes, so no bare number ever floats free of its method.
        """
        if self.provenance is Provenance.SOURCED:
            if self.value is None:
                raise ValueError("a SOURCED row must carry a value")
            missing = [
                name
                for name in ("source_title", "source_url", "quoted_text", "accessed_date")
                if getattr(self, name) in (None, "")
            ]
            if missing:
                raise ValueError(
                    "a SOURCED row must carry full provenance; missing: "
                    + ", ".join(missing)
                )

        if self.provenance is Provenance.TODO and self.value is not None:
            raise ValueError(
                "a TODO row must have value=None — an unsourced number is a "
                "fabrication, not a datum (issue #844 quality rule)"
            )

        if self.price_basis is PriceBasis.REAL and self.basis_year is None:
            raise ValueError("a REAL row must declare basis_year")

        if (
            self.provenance
            in (Provenance.FITTED, Provenance.ALLOCATED, Provenance.ASSUMED)
        ):
            if self.value is None:
                raise ValueError(f"a {self.provenance.value} row must carry a value")
            if not (self.notes and self.notes.strip()):
                raise ValueError(
                    f"a {self.provenance.value} row must explain its method in notes"
                )

        return self


# Column order for the on-disk CSVs. Explicit so the artifact is stable and
# diffable across refreshes rather than dependent on dict ordering.
#
# Field names here are the model's (snake_case); the curated CSVs under
# data/modules/cost/curated/ are written with UPPER_SNAKE headers to match the
# house convention for curated datasets (cf. offshore_assets/curated/*.csv).
# `csv_header()` is the single place that mapping happens.
CSV_COLUMNS: tuple[str, ...] = (
    "year",
    "component",
    "band",
    "value",
    "unit",
    "currency",
    "price_basis",
    "basis_year",
    "figure_type",
    "segment",
    "region",
    "provenance",
    "source_title",
    "source_url",
    "page_reference",
    "quoted_text",
    "accessed_date",
    "confidence",
    "source_priority",
    "notes",
)


def csv_header() -> list[str]:
    """The curated-CSV header row: UPPER_SNAKE projection of ``CSV_COLUMNS``."""
    return [name.upper() for name in CSV_COLUMNS]


def to_csv_row(obs: "CostObservation") -> list[str]:
    """Flatten one observation to a CSV row aligned with :func:`csv_header`.

    ``None`` becomes the empty string — notably for the ``value`` of a TODO
    row, which is exactly how a gap should read in a spreadsheet: blank, not
    zero. A zero would be a number, and we do not have a number.
    """
    out: list[str] = []
    for name in CSV_COLUMNS:
        value = getattr(obs, name)
        if value is None:
            out.append("")
        elif isinstance(value, Enum):
            out.append(value.value)
        elif isinstance(value, date):
            out.append(value.isoformat())
        else:
            out.append(str(value))
    return out
