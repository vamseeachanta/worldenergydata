"""Synthetic annual-layout cases; no regulator production values are retained.

Layout source: C-NLOER Statistical Information, 2026 annual field reports,
Monthly Details and imperial unit headers, opened 2026-10-19:
https://www.cnloer.ca/information/statistics/

Hand calculation: each synthetic reservoir has oil=1001 bbl, gas=2 MMscf,
water=3003 bbl. Two reservoirs give 2002 bbl, 4000 Mcf, 6006 bbl.
Three give 3003 bbl, 6000 Mcf, 9009 bbl. Explicit totals deliberately differ
from these sums to demonstrate source-total selection rather than addition.
MMscf/Mcf = million/thousand = 1000: EIA Glossary, Mcf/MMcf entries,
opened 2026-10-19, https://www.eia.gov/tools/glossary/index.php?id=M .
All other numbers are synthetic test inputs or calendar labels.
"""

import calendar
import importlib

import pytest

from worldenergydata.canada.production import cnloer_annual
from worldenergydata.canada.production.cnloer_annual import (
    parse_cnloer_annual_text,
)
from worldenergydata.canada.production.cnloer_loader import (
    CnloerParseError,
    CnloerProductionLoader,
)

RESERVOIRS = {
    "Hibernia": ["Hibernia", "Avalon", "Catalina", "Total"],
    "Hebron": ["Ben Nevis", "Hibernia", "Jeanne d'Arc", "Total"],
    "North Amethyst": ["Ben Nevis/Avalon", "Hibernia"],
    "Terra Nova": ["Jeanne d'Arc"],
    "White Rose": ["Ben Nevis/Avalon"],
}
VALUES = "10  1 001  20  2  30  3 003"
TOTAL = "40  4 001  50  5  60  6 003"


def annual_text(field="Hibernia", populated=2):
    """Construct twelve synthetic month blocks in the observed report layout."""
    lines = [
        f"{field} Field Monthly Production - 2026",
        "Year  Month  Reservoir  Oil  Gas  Water  Amendment Date",
        "m³  bbls  10³ m³  MMscf  m³  bbls",
        "Monthly Details",
    ]
    for month, name in enumerate(list(calendar.month_name)[1:], start=1):
        for index, reservoir in enumerate(RESERVOIRS[field]):
            prefix = "2026  " if month == 1 and index == 0 else ""
            if "Total" not in RESERVOIRS[field] and index == 0:
                prefix += name + "  "
            if reservoir == "Total":
                values = TOTAL
            else:
                values = VALUES
            suffix = f"  {values}" if month <= populated else ""
            lines.append(prefix + reservoir + suffix)
            # Merged month cells are centred between reservoir rows.
            if "Total" in RESERVOIRS[field] and index == 1:
                lines.append(name)
    lines.append("Total - 2026  999  999  999  999  999  999")
    return "\n".join(lines)


@pytest.mark.parametrize("field", RESERVOIRS)
def test_grouped_values_and_reservoir_selection(field):
    """Expect source Total or the independent sums in the module docstring."""
    out = parse_cnloer_annual_text(annual_text(field), field_name=field, year=2026)
    multiplier = len(RESERVOIRS[field])
    expected = (1001 * multiplier, 2000 * multiplier, 3003 * multiplier)
    if "Total" in RESERVOIRS[field]:
        expected = (4001, 5000, 6003)
    assert out["month"].tolist() == [1, 2]
    assert out["year"].tolist() == [2026, 2026]
    assert out["field_name"].tolist() == [field, field]
    assert out[["oil_bbl", "gas_mcf", "water_bbl"]].values.tolist() == [
        list(expected),
        list(expected),
    ]


def test_loader_selects_annual_parser_only_with_explicit_report_year():
    loader = CnloerProductionLoader(
        field_name="Hibernia", raw_text=annual_text(), report_year=2026
    )
    assert loader.load()["oil_bbl"].tolist() == [4001, 4001]


def test_zero_is_reported_production_and_future_blanks_are_omitted():
    text = annual_text("White Rose", populated=1).replace(VALUES, "0  0  0  0  0  0")
    out = parse_cnloer_annual_text(text, field_name="White Rose", year=2026)
    assert out["month"].tolist() == [1]
    assert out[["oil_bbl", "gas_mcf", "water_bbl"]].values.tolist() == [[0, 0, 0]]


def test_source_months_do_not_depend_on_the_process_calendar_locale(monkeypatch):
    """English report tokens retain January=1 even under another calendar locale."""
    text = annual_text()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(calendar, "month_name", [""] + ["other"] * 12)
            importlib.reload(cnloer_annual)
            out = cnloer_annual.parse_cnloer_annual_text(
                text, field_name="Hibernia", year=2026
            )
            assert out["month"].tolist() == [1, 2]
    finally:
        importlib.reload(cnloer_annual)


def test_amendment_dates_are_not_volume_columns():
    text = annual_text().replace(TOTAL, TOTAL + "  7/9/2026")
    out = parse_cnloer_annual_text(text, field_name="Hibernia", year=2026)
    assert out["water_bbl"].tolist() == [6003, 6003]


def test_annual_summary_label_can_follow_its_first_reservoir():
    """North Amethyst centres the annual label on its second summary row."""
    text = annual_text("North Amethyst").replace(
        "Total - 2026  999  999  999  999  999  999",
        f"Ben Nevis/Avalon  {VALUES}\nTotal - 2026  Hibernia  {VALUES}\n"
        f"Total  {TOTAL}",
    )
    out = parse_cnloer_annual_text(text, field_name="North Amethyst", year=2026)
    assert out["month"].tolist() == [1, 2]
    assert out["oil_bbl"].tolist() == [2002, 2002]


@pytest.mark.parametrize(
    "old,new",
    [
        ("MMscf", "Mcf"),
        ("10³ m³", "m³"),
        ("Oil  Gas  Water", "Water  Gas  Oil"),
        ("1 001", "1 01"),
        ("1 001", "-1"),
        ("1 001", "NaN"),
        ("1 001", "1,001"),
        ("Avalon", "Unknown"),
        ("January", "February"),
        ("January", "Januarx"),
        ("December", "November"),
        ("Total - 2026", "Total - 2025"),
        ("Total - 2026", "Unrecognised footer"),
        ("2026  Hibernia", "2025  Hibernia"),
        ("  " + TOTAL, ""),
        ("Monthly Details", ""),
    ],
)
def test_malformed_or_incomplete_layout_is_rejected(old, new):
    text = annual_text().replace(old, new)
    with pytest.raises(CnloerParseError):
        parse_cnloer_annual_text(text, field_name="Hibernia", year=2026)


def test_no_partial_results_when_a_reservoir_row_is_missing():
    text = annual_text().replace("Avalon  " + VALUES + "\n", "", 1)
    with pytest.raises(CnloerParseError):
        parse_cnloer_annual_text(text, field_name="Hibernia", year=2026)


def test_no_populated_month_after_a_blank_month():
    text = annual_text("White Rose").replace(
        "January  Ben Nevis/Avalon  " + VALUES, "January  Ben Nevis/Avalon"
    )
    with pytest.raises(CnloerParseError):
        parse_cnloer_annual_text(text, field_name="White Rose", year=2026)


@pytest.mark.parametrize("year", [True, "2026", 2025, 0, -1])
def test_requested_year_must_match_the_report_title(year):
    with pytest.raises(CnloerParseError):
        parse_cnloer_annual_text(annual_text(), field_name="Hibernia", year=year)


@pytest.mark.parametrize("field", ["mpro", "off_prod", "Unknown"])
def test_only_known_individual_fields_are_supported(field):
    with pytest.raises(CnloerParseError):
        parse_cnloer_annual_text(annual_text(), field_name=field, year=2026)


def test_entirely_blank_report_cannot_establish_production():
    with pytest.raises(CnloerParseError):
        parse_cnloer_annual_text(
            annual_text(populated=0), field_name="Hibernia", year=2026
        )
