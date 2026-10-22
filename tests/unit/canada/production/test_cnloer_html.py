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


@pytest.mark.parametrize("missing", ["table", "row", "cell", "modal"])
def test_parser_rejects_incomplete_production_markup(missing):
    """Complete monthly values cannot establish a complete source table.

    Structural basis: C-NLOER Statistical Information, pshf97–pshf01,
    https://www.cnloer.ca/information/statistics/ (opened 2026-10-19).
    Each modal encloses a table of explicitly terminated rows and cells;
    the source's mismatched th/td endings remain supported.
    """
    html = synthetic_html()
    if missing == "table":
        html = html.rsplit("</table>", 1)[0]
    elif missing == "row":
        html = html.replace("Amendment Date*</td></tr>", "Amendment Date*</td>", 1)
    elif missing == "cell":
        html = html.replace("100</strong></td>", "100</strong>", 1)
    else:
        html = html.rsplit("</div>", 1)[0]
    with pytest.raises(CnloerParseError, match="incomplete production"):
        parse(html)


def test_parser_ignores_incomplete_unrelated_page_markup():
    """Only the source production modals establish the backfill schema."""
    expected = parse(synthetic_html())
    pd.testing.assert_frame_equal(
        parse(synthetic_html() + "<div><table><tr><td>Unrelated"), expected
    )


@pytest.mark.parametrize(
    "old,new",
    [
        (">Production</td>", ">Injection</td>"),
        (">Monthly Details</td>", ">Annual Details</td>"),
        (">Amendment Date*</td>", ">Unknown</td>"),
    ],
)
def test_parser_rejects_wrong_table_section(old, new):
    """Header oracle: C-NLOER statistics pshf97–pshf01, opened 2026-10-19.

    The production grouping, monthly section and amendment header establish
    the meaning of the otherwise valid numeric cells; changing one invalidates
    that schema. No production volume or conversion coefficient is used.
    """
    html = synthetic_html().replace(old, new, 1)
    with pytest.raises(CnloerParseError, match="unexpected production.*header"):
        parse(html)


def test_parser_accepts_whitespace_in_section_headers():
    html = synthetic_html().replace(
        ">Monthly Details</td>", ">  Monthly\nDetails  </td>"
    )
    pd.testing.assert_frame_equal(parse(html), parse(synthetic_html()))


@pytest.mark.parametrize("overflow", ["input", "conversion"])
@pytest.mark.parametrize("old", ["<strong>100</strong>", "<td>10</td>", "<td>50</td>"])
def test_parser_rejects_nonfinite_monthly_volumes(overflow, old):
    """Hand calculation: max_float times a factor greater than one overflows.

    Python's sys.float_info supplies the runtime floating-point bound; appending
    a decimal zero multiplies it by ten, overflowing on input instead.
    The existing units_catalog.md Oil, Gas and Water volume tables specify
    factors greater than one. No engineering acceptance threshold is added.
    """
    value = format(float_info.max, "f")
    if overflow == "input":
        value = value.split(".")[0] + "0"
    replacement = value if old.startswith("<strong>") else f"<td>{value}</td>"
    with pytest.raises(CnloerParseError, match="nonfinite.*production"):
        parse(synthetic_html().replace(old, replacement, 1))


def test_parser_preserves_zero_month_and_independent_conversions():
    """Independent hand calculation using common/units_catalog.md tables.

    Oil: 100 m3 * 6.2898 = 628.98 bbl; water: 50 * 6.2898 = 314.49 bbl.
    Gas: 10 thousand m3 * 35.3147 scf/m3 = 353.147 Mcf, since the
    two factors of one thousand cancel. These are the catalog's Oil, Water
    and Gas volume factors, not imports from the parser under test.
    Synthetic zero January plus eleven positive months must retain January;
    five complete calendar years contain 5 * 12 = 60 unique periods.
    """
    html = synthetic_html().replace(
        "<strong>100</strong></td><td>10</td><td>50</td>",
        "0</td><td>0</td><td>0</td>",
        1,
    )
    frame = parse(html)
    volumes = ["oil_bbl", "gas_mcf", "water_bbl"]
    assert len(frame) == 60
    assert not frame.duplicated(["year", "month"]).any()
    assert frame.iloc[0][volumes].tolist() == [0.0, 0.0, 0.0]
    assert frame.iloc[1][volumes].tolist() == pytest.approx([628.98, 353.147, 314.49])
