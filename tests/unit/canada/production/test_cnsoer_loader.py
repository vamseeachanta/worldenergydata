"""SYNTHETIC CNSOER layouts; no regulator production values are reproduced.

Layout sources: CNSOER SOEP Monthly Production Report (2019), project and
field-total tables; Deep Panuke Monthly Production Report (2018), page 1.
All expected volumes below are direct readings of invented input tokens;
no physical conversion or engineering acceptance threshold is applied.
"""

import hashlib

import pytest

from worldenergydata.canada.production.cnsoer_loader import (
    CnsoerParseError,
    CnsoerProductionLoader,
    parse_cnsoer_production_text,
)


def section(title, rows, units="(10³M³/Month) (M³/Month)"):
    return f"{title}\nDate Gas Equivalent Volume Water Volume\n{units}\n{rows}\n"


def test_project_total_is_selected_without_adding_fields_or_wells():
    """Hand reading: 1,234.50 -> 1234.5; field 900 and well 800 are excluded."""
    text = section("TOTAL PRODUCTION", "Dec-99 1,234.50 12.50\nJan-00 0.00 0.00")
    text += "\f" + section("THEBAUD TOTAL PRODUCTION", "Dec-99 900 10")
    text += "\f" + section("THEBAUD 1: T1", "Dec-99 800 9")
    frame = parse_cnsoer_production_text(text, field_name="Sable")
    assert frame["year"].tolist() == [1999, 2000]
    assert frame["month"].tolist() == [12, 1]
    assert frame["gas_equivalent_e3m3"].tolist() == [1234.5, 0.0]
    assert frame["water_m3"].tolist() == [12.5, 0.0]
    assert frame["field_name"].tolist() == ["Sable", "Sable"]
    assert "gas_mcf" not in frame  # Equivalent volume is not sales gas.
    assert "oil_bbl" not in frame


@pytest.mark.parametrize(
    "field", ["Thebaud", "Venture", "North Triumph", "Alma", "South Venture"]
)
def test_sable_field_total_selection(field):
    """Hand reading: selected field = 25 gas, 4 water; project 50 excluded."""
    text = section("TOTAL PRODUCTION", "Jan-00 50 8")
    text += "\f" + section(f"{field.upper()} TOTAL PRODUCTION", "Jan-00 25 4")
    frame = parse_cnsoer_production_text(text, field_name=field)
    assert frame["gas_equivalent_e3m3"].tolist() == [25.0]
    assert frame["water_m3"].tolist() == [4.0]


def test_deep_panuke_uses_total_and_sorts_periods():
    """Hand reading: Aug=20, Sep=30; well-level 999 is excluded."""
    text = section("TOTAL PRODUCTION", "Sep-13 30 3\nAug-13 20 2")
    text += "\f" + section("WELL A", "Aug-13 999 999 100")
    frame = parse_cnsoer_production_text(text, field_name="Deep Panuke")
    assert frame["month"].tolist() == [8, 9]
    assert frame["gas_equivalent_e3m3"].tolist() == [20.0, 30.0]


@pytest.mark.parametrize(
    "field", ["Sable", "Thebaud", "Venture", "North Triumph", "Alma", "South Venture"]
)
def test_sable_standalone_trailing_backtick_annotation(field):
    """SOEP (2019), all aggregate Nov-14 rows have a trailing backtick.

    Synthetic hand reading: 25 gas and 4 water; the annotation is not a value.
    """
    frame = parse_cnsoer_production_text(
        section(
            (
                "TOTAL PRODUCTION"
                if field == "Sable"
                else f"{field.upper()} TOTAL PRODUCTION"
            ),
            "Nov-14 25 4 `",
        ),
        field_name=field,
    )
    assert frame["gas_equivalent_e3m3"].tolist() == [25.0]
    assert frame["water_m3"].tolist() == [4.0]


@pytest.mark.parametrize(
    "rows",
    [
        "Jan-00 1 2\nJan-00 1 2",
        "Jan-00 1",
        "Jan-00 -1 2",
        "Jan-00 nan 2",
        "Jan-00 inf 2",
        "Jan-00 1,23 2",
        "Jan-00 1 2 3",
        "Foo-00 1 2",
        "Jan-000 1 2",
        "Jan-00 1e309 2",
    ],
)
def test_malformed_or_duplicate_months_fail_closed(rows):
    with pytest.raises(CnsoerParseError):
        parse_cnsoer_production_text(
            section("TOTAL PRODUCTION", rows), field_name="Sable"
        )


@pytest.mark.parametrize("field", ["unknown", "", "sable"])
def test_unknown_field_rejected(field):
    with pytest.raises(CnsoerParseError, match="field"):
        parse_cnsoer_production_text("", field_name=field)


@pytest.mark.parametrize(
    "text",
    [
        "",
        section("TOTAL PRODUCTION", ""),
        section("THEBAUD 1: T1", "Jan-00 1 2"),
        section("TOTAL PRODUCTION", "Jan-00 1 2", units="(MMcf/Month) (bbl/Month)"),
        section("TOTAL PRODUCTION", "Jan-00 1 2") * 2,
        section("TOTAL PRODUCTION", "Jan-00 1 2")
        + "\f"
        + section("TOTAL PRODUCTION", "Feb-00 3 4"),
    ],
)
def test_missing_ambiguous_or_unsupported_section_rejected(text):
    with pytest.raises(CnsoerParseError):
        parse_cnsoer_production_text(text, field_name="Sable")


def test_loader_exposes_readback_provenance_and_no_automatic_fetch():
    """Hand reading: 10 gas, 2 water; digest covers the exact injected text."""
    text = section("TOTAL PRODUCTION", "Aug-13 10 2")
    loader = CnsoerProductionLoader(raw_text=text, project="Deep Panuke")
    frame = loader.load_field_production("Deep Panuke")
    assert frame["gas_equivalent_e3m3"].tolist() == [10.0]
    assert frame["source"].tolist() == ["canada-cnsoer"]
    metadata = loader.metadata()
    assert metadata["text_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert metadata["source_id"] == "canada-cnsoer"
    assert metadata["publication_status"] == "NOT_EVALUATED"
    assert metadata["revenue_status"] == "NOT_EVALUATED"
    assert "non-commercial" in metadata["LICENCE_NOTE"]
    assert metadata["source_url"].endswith("dp_monthly_production_report_0.pdf")
    assert metadata["gas_unit"] == "10^3 m3/month (gas equivalent)"
    # A caller cannot mutate retained source data through a returned frame.
    frame.loc[0, "gas_equivalent_e3m3"] = 99
    assert loader.load_field_production("Deep Panuke")["gas_equivalent_e3m3"][0] == 10


def test_loader_rejects_cross_project_field():
    loader = CnsoerProductionLoader(
        raw_text=section("TOTAL PRODUCTION", "Jan-00 10 2"), project="Sable"
    )
    with pytest.raises(CnsoerParseError, match="project"):
        loader.load_field_production("Deep Panuke")
    with pytest.raises(CnsoerParseError, match="project"):
        CnsoerProductionLoader(raw_text="", project="unknown")
