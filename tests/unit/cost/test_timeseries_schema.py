"""
ABOUTME: Tests the cost-basis time-series row contract (issue #844).
ABOUTME: The anti-fabrication rules are the point — a TODO row must never be able to carry a number.

Boundary: this covers `worldenergydata.cost.timeseries.schema` only. The
provenance vocabulary (confidence / source priority) is owned by the #337
disclosure ingest contract and is re-exported, not redefined — the test at the
bottom pins that.
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from worldenergydata.cost.timeseries.schema import (
    CostComponent,
    CostObservation,
    DevelopmentSystemBand,
    DisclosureConfidence,
    PriceBasis,
    Provenance,
    SourcePriority,
    csv_header,
    to_csv_row,
)


def _sourced_kwargs(**overrides) -> dict:
    base = dict(
        year=2014,
        component=CostComponent.RIG_DAY_RATE_DRILLSHIP,
        band=DevelopmentSystemBand.NOT_APPLICABLE,
        value=550_000.0,
        unit="usd_per_day",
        provenance=Provenance.SOURCED,
        source_title="Transocean Q3 2014 Fleet Status Report",
        source_url="https://www.deepwater.com/fleet-status",
        page_reference="p. 2, ultra-deepwater fleet table",
        quoted_text="Discoverer Clear Leader — dayrate $553,000",
        accessed_date=date(2026, 7, 14),
        confidence=DisclosureConfidence.HIGH,
        source_priority=SourcePriority.SEC_FILING,
    )
    base.update(overrides)
    return base


def test_sourced_row_round_trips() -> None:
    obs = CostObservation(**_sourced_kwargs())
    assert obs.value == 550_000.0
    assert obs.price_basis is PriceBasis.NOMINAL
    assert obs.currency == "USD"


def test_sourced_row_requires_full_provenance() -> None:
    with pytest.raises(ValidationError, match="must carry full provenance"):
        CostObservation(**_sourced_kwargs(source_url=None))


def test_sourced_row_requires_a_value() -> None:
    with pytest.raises(ValidationError, match="must carry a value"):
        CostObservation(**_sourced_kwargs(value=None))


def test_sourced_row_rejects_relative_source_url() -> None:
    with pytest.raises(ValidationError, match="absolute http"):
        CostObservation(**_sourced_kwargs(source_url="www.deepwater.com/fleet"))


def test_todo_row_must_not_carry_a_value() -> None:
    """The core anti-fabrication rule of issue #844.

    A TODO row with a number in it is a guess wearing a disguise. The schema
    must make that unrepresentable.
    """
    with pytest.raises(ValidationError, match="fabrication"):
        CostObservation(
            year=2003,
            component=CostComponent.SURF_COST,
            value=1234.0,
            unit="usd_mm",
            provenance=Provenance.TODO,
        )


def test_todo_row_with_no_value_is_the_correct_way_to_record_a_gap() -> None:
    obs = CostObservation(
        year=2003,
        component=CostComponent.SURF_COST,
        band=DevelopmentSystemBand.SUBSEA_15,
        value=None,
        unit="usd_mm",
        provenance=Provenance.TODO,
        notes="No public SURF cost disclosure sourced for 2003.",
    )
    assert obs.value is None
    assert obs.provenance is Provenance.TODO


def test_real_row_must_declare_its_basis_year() -> None:
    with pytest.raises(ValidationError, match="must declare basis_year"):
        CostObservation(
            year=2014,
            component=CostComponent.RIG_DAY_RATE_DRILLSHIP,
            value=550_000.0,
            unit="usd_per_day",
            price_basis=PriceBasis.REAL,
            basis_year=None,
            provenance=Provenance.FITTED,
            notes="deflated",
        )


def test_fitted_row_must_explain_its_method() -> None:
    """A bare fitted number with no stated method is not auditable."""
    with pytest.raises(ValidationError, match="must explain its method"):
        CostObservation(
            year=2011,
            component=CostComponent.RIG_DAY_RATE_SEMI,
            value=400_000.0,
            unit="usd_per_day",
            provenance=Provenance.FITTED,
            notes=None,
        )


def test_allocated_and_assumed_rows_also_require_a_method_note() -> None:
    for provenance in (Provenance.ALLOCATED, Provenance.ASSUMED):
        with pytest.raises(ValidationError, match="must explain its method"):
            CostObservation(
                year=2020,
                component=CostComponent.HOST_CAPEX,
                value=900.0,
                unit="usd_mm",
                provenance=provenance,
            )


def test_extra_fields_are_forbidden() -> None:
    with pytest.raises(ValidationError):
        CostObservation(**_sourced_kwargs(some_new_column="oops"))


def test_csv_header_is_upper_snake_and_row_aligns() -> None:
    header = csv_header()
    assert header[0] == "YEAR"
    assert "SOURCE_URL" in header
    assert "QUOTED_TEXT" in header
    row = to_csv_row(CostObservation(**_sourced_kwargs()))
    assert len(row) == len(header)
    assert row[header.index("PROVENANCE")] == "sourced"


def test_todo_row_serialises_its_gap_as_blank_not_zero() -> None:
    """A blank cell reads as 'unknown'. A zero reads as 'free'. They differ."""
    obs = CostObservation(
        year=2003,
        component=CostComponent.SURF_COST,
        value=None,
        unit="usd_mm",
        provenance=Provenance.TODO,
        notes="gap",
    )
    row = to_csv_row(obs)
    assert row[csv_header().index("VALUE")] == ""


def test_provenance_vocabulary_is_reused_from_the_337_contract() -> None:
    """We must not fork a parallel confidence/priority vocabulary."""
    from worldenergydata.cost.data_collection import disclosure_ingest_contract as dic

    assert DisclosureConfidence is dic.DisclosureConfidence
    assert SourcePriority is dic.SourcePriority
