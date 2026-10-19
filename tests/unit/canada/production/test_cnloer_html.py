"""Offline synthetic modal tests; no regulator production volumes are retained."""

from sys import float_info

import pandas as pd
import pytest

from worldenergydata.canada.production import cnloer_loader as loader_module
from worldenergydata.canada.production.cnloer_loader import (
    E3M3_TO_MCF,
    M3_TO_BBL,
    WATER_M3_TO_BBL,
    CnloerParseError,
    CnloerProductionLoader,
    parse_cnloer_production_text,
)

MONTHS = (
    "January February March April May June July August September October November December"
).split()
PDF_TEXT = "December 2001 1 999 2 3 4 777\nJanuary 2002 1 998 2 3 4 776\n"


def synthetic_html():
    """Synthetic values in served pshf structure, including th closed with td."""
    tables = ['<div id="gg97"><table><tr><td>Unrelated</td></tr></table></div>']
    for year in range(1997, 2002):
        first = "Year" if year < 2000 else "Year/Month"
        second = "Month" if year < 2000 else "Reservoir"
        if year == 2000:
            second += "<sup>**</sup>"
        rows = [
            f'<tr><th rowspan="3">{first}</td><th rowspan="3">{second}</td>'
            '<th colspan="3">Production</td><th rowspan="3">Amendment Date*</td></tr>',
            "<tr><td>Oil</td><td>Gas</td><td>Water</td></tr>",
            "<tr><td>m<sup>3</sup></td><td>10<sup>3</sup>m<sup>3</sup></td>"
            "<td>m<sup>3</sup></td></tr>",
            '<tr><th colspan="6">Monthly Details</td></tr>',
        ]
        for index, month in enumerate(MONTHS):
            if year < 2000:
                prefix = f'<th rowspan="12">{year}</td>' if index == 0 else ""
                rows.append(
                    f"<tr>{prefix}<td>{month}</td><td><strong>100</strong></td>"
                    "<td>10</td><td>50</td><td></td></tr>"
                )
            else:
                rows.extend(
                    [
                        f'<tr><th rowspan="3">{month}</td><td>Hibernia</td>'
                        "<td>100</td><td>10</td><td>50</td><td></td></tr>",
                        "<tr><td>Avalon</td><td>20</td><td>2</td><td>5</td><td></td></tr>",
                        '<tr class="active"><td>Total</td><td>120</td>'
                        "<td>12</td><td>55</td><td></td></tr>",
                    ]
                )
        rows.append(
            f'<tr><th colspan="2">Cumulative – {year}</th><td>9 999</td>'
            "<td>9 999</td><td>9 999</td><td></td></tr>"
        )
        tables.append(
            f'<div class="modal fade" id="pshf{year % 100:02d}">'
            '<div class="modal-dialog"><div class="modal-content">'
            f"<h4>{year} Production Field Well Summary</h4>"
            '<div class="modal-body"><table>'
            + "".join(rows)
            + "</table></div></div></div></div>"
        )
    return "<!-- SYNTHETIC offline fixture -->" + "".join(tables)


def parse(html):
    return loader_module.parse_cnloer_production_html(html, field_name="Hibernia")


def test_parser_normalizes_five_modal_tables_and_annual_total():
    frame = parse(synthetic_html())
    assert list(frame.columns) == list(
        parse_cnloer_production_text(PDF_TEXT, field_name="Hibernia").columns
    )
    assert len(frame) == 60
    assert frame[["year", "month"]].values.tolist() == [
        [year, month] for year in range(1997, 2002) for month in range(1, 13)
    ]
    assert frame.iloc[0]["oil_bbl"] == pytest.approx(100 * M3_TO_BBL)
    assert frame.iloc[0]["gas_mcf"] == pytest.approx(10 * E3M3_TO_MCF)
    assert frame.iloc[0]["water_bbl"] == pytest.approx(50 * WATER_M3_TO_BBL)
    assert frame[frame.year == 2000].oil_bbl.sum() == pytest.approx(
        12 * 120 * M3_TO_BBL
    )
    assert frame.iloc[-1]["water_bbl"] == pytest.approx(55 * WATER_M3_TO_BBL)
    assert frame.field_name.eq("Hibernia").all()


@pytest.mark.parametrize("token", ["1 200", "1\u00a0200", "1,200", "1200.0"])
def test_parser_reads_grouped_numeric_cells(token):
    html = synthetic_html().replace("<strong>100</strong>", token, 1)
    assert parse(html).iloc[0].oil_bbl == pytest.approx(1200 * M3_TO_BBL)


@pytest.mark.parametrize(
    "old,new",
    [
        ('id="pshf97"', 'id="missing"'),
        ("<strong>100</strong>", "missing"),
        ("<strong>100</strong>", "-100"),
        ("<strong>100</strong>", "NaN"),
        ("<td>January</td>", "<td>Unknown</td>"),
        ("<td>Oil</td>", "<td>Water</td>"),
        ("10<sup>3</sup>m<sup>3</sup>", "MMscf"),
        ("<td>Total</td>", "<td>Other</td>"),
        ("<td>February</td>", "<td>January</td>"),
        ('rowspan="12">1997', 'rowspan="12">1998'),
        ("<td>10</td><td>50</td>", "<td>10</td>"),
    ],
)
def test_malformed_modal_raises_existing_parse_error(old, new):
    with pytest.raises(CnloerParseError):
        CnloerProductionLoader(
            field_name="Hibernia", raw_html=synthetic_html().replace(old, new, 1)
        ).load()


def test_missing_html_tables_raise_existing_parse_error():
    with pytest.raises(CnloerParseError):
        CnloerProductionLoader(field_name="Hibernia", raw_html="<html></html>").load()


def test_combined_loader_preserves_pdf_overlap_and_continuous_junction():
    expected = parse_cnloer_production_text(PDF_TEXT, field_name="Hibernia")
    frame = CnloerProductionLoader(
        field_name="Hibernia", raw_text=PDF_TEXT, raw_html=synthetic_html()
    ).load()
    assert len(frame) == 61
    assert not frame.duplicated(["year", "month"]).any()
    pd.testing.assert_frame_equal(frame.tail(2).reset_index(drop=True), expected)
    assert frame.tail(3)[["year", "month"]].values.tolist() == [
        [2001, 11],
        [2001, 12],
        [2002, 1],
    ]


def test_loader_accepts_html_only():
    pd.testing.assert_frame_equal(
        CnloerProductionLoader(field_name="Hibernia", raw_html=synthetic_html()).load(),
        parse(synthetic_html()),
    )


def test_html_parser_rejects_other_fields():
    with pytest.raises(CnloerParseError):
        loader_module.parse_cnloer_production_html(
            synthetic_html(), field_name="Hebron"
        )


def test_pdf_only_regression_pin():
    """Regression pin: the original supplied-PDF transform stays unchanged."""
    pd.testing.assert_frame_equal(
        CnloerProductionLoader(field_name="Hibernia", raw_text=PDF_TEXT).load(),
        parse_cnloer_production_text(PDF_TEXT, field_name="Hibernia"),
    )


def test_parser_excludes_numeric_superscript_annotations():
    html = synthetic_html().replace(
        "<strong>100</strong>", "<strong><em>100</em><sup>1</sup></strong>", 1
    )
    frame = parse(html)
    assert frame.iloc[0].oil_bbl == pytest.approx(100 * M3_TO_BBL)
    assert frame.iloc[0].gas_mcf == pytest.approx(10 * E3M3_TO_MCF)


# Layout source: C-NLOER Statistical Information, pshf97–pshf01,
# https://www.cnloer.ca/information/statistics/ (opened 2026-10-19).
# The observed group header is Production; the section is Monthly Details.
@pytest.mark.parametrize(
    "old,new",
    [
        ('<th colspan="3">Production</td>', '<th colspan="3">Injection</td>'),
        ('<th colspan="3">Production</td>', ""),
        ('<th rowspan="3">Amendment Date*</td>', ""),
        (
            '<th colspan="6">Monthly Details</td>',
            '<th colspan="6">Annual Details</td>',
        ),
    ],
)
def test_parser_rejects_changed_production_header(old, new):
    with pytest.raises(CnloerParseError, match="production.*header"):
        parse(synthetic_html().replace(old, new, 1))


# Python 3 Library Reference, sys.float_info table, max / DBL_MAX:
# https://docs.python.org/3/library/sys.html#sys.float_info (opened 2026-10-19).
@pytest.mark.parametrize(
    "value",
    [str(int(float_info.max)) + "0", str(int(float_info.max))],
    ids=["source-overflow", "conversion-overflow"],
)
@pytest.mark.parametrize(
    "cell",
    ["<strong>100</strong>", "<td>10</td>", "<td>50</td>"],
    ids=["oil", "gas", "water"],
)
def test_parser_rejects_nonfinite_volumes(value, cell):
    """Independent overflow construction from the runtime's largest float.

    Appending a decimal zero multiplies that positive integer by ten, so it
    exceeds the largest finite float before conversion. Without that zero,
    it remains finite but the barrel and cubic-foot factors (both greater
    than one, common/units.py) overflow when applied to a selected volume.
    """
    replacement = value if cell.startswith("<strong>") else f"<td>{value}</td>"
    html = synthetic_html().replace(cell, replacement, 1)
    with pytest.raises(CnloerParseError, match="nonfinite.*production"):
        parse(html)


def test_parser_rejects_nonfinite_reservoir_subrow():
    """The same max-float times ten construction must fail even in a subrow
    that is excluded in favour of the published field total.
    """
    value = str(int(float_info.max)) + "0"
    html = synthetic_html().replace("<td>20</td>", f"<td>{value}</td>", 1)
    with pytest.raises(CnloerParseError, match="nonfinite.*production"):
        parse(html)


def test_parser_conversions_have_independent_hand_calculated_expectations():
    """Hand calculation for synthetic cells; no expected value uses parser code.

    Factors: common/units.py, OilUnits.SM3_TO_BBL, GasUnits.SM3_TO_SCF,
    WaterUnits.M3_TO_BBL (repository conversion contract). Source table units:
    C-NLOER Statistical Information, pshf97–pshf01 (opened 2026-10-19).
    Oil = 100 m3 * 6.2898 = 628.98 bbl.
    Gas = 10 thousand m3 * 35.3147 = 353.147 Mcf.
    Water = 50 m3 * 6.2898 = 314.49 bbl.
    Reservoir total oil = (100 + 20) * 6.2898 = 754.776 bbl per month;
    annual oil = 12 * 754.776 = 9057.312 bbl. The published Total row is
    selected once; the two reservoir rows are not added to that Total.
    """
    frame = parse(synthetic_html())
    assert frame.iloc[0].oil_bbl == pytest.approx(628.98)
    assert frame.iloc[0].gas_mcf == pytest.approx(353.147)
    assert frame.iloc[0].water_bbl == pytest.approx(314.49)
    assert frame.loc[frame.year == 2000, "oil_bbl"].sum() == pytest.approx(9057.312)


def test_loader_pdf_overlap_has_independent_expected_values():
    """Hand calculation: PDF_TEXT supplies oil 999 bbl, gas 3 MMscf,
    water 777 bbl for December; 3 MMscf * 1000 = 3000 Mcf, using the
    repository common/units.py GasUnits.MMSCF_TO_MCF contract. January's
    PDF oil/water are 998/776 bbl. Five calendar years give 5 * 12 = 60
    HTML periods; the overlapping December adds none, January adds one.
    """
    frame = CnloerProductionLoader(
        field_name=loader_module.FIELD_CODES["h"],
        raw_text=PDF_TEXT,
        raw_html=synthetic_html(),
    ).load()
    assert len(frame) == 61
    assert frame.tail(2)[["oil_bbl", "gas_mcf", "water_bbl"]].values.tolist() == [
        [999.0, 3000.0, 777.0],
        [998.0, 3000.0, 776.0],
    ]
