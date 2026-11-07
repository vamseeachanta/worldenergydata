"""PPAC production-table parsing.

Layouts follow the PPAC "PT_Crude oil production" sheets (https://ppac.gov.in):
title rows, a unit line "(Million Metric Tonnes)", a period header row, then
ONGC, OIL, PSU total, JVC/Private, Total crude oil and Condensate rows. The
numbers below are synthetic; expected sums are hand calculations.
"""

import math

import pandas as pd
import pytest

from worldenergydata.india_dgh import load_production
from worldenergydata.india_dgh.production import parse_ppac_sheet

N = None


def monthly_sheet(ongc=1.5, oil=0.25, private=0.5, total=2.25, title="2022-23 (P)"):
    """April populated; May blank components with a printed zero total."""
    months = [
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
        "January",
        "February",
        "March",
    ]
    rows = [
        [N, "Petroleum Planning & Analysis Cell"] + [N] * 12,
        [title, N, "(Million Metric Tonnes)"] + [N] * 11,
        ["Indigenous crude oil production"] + [N] * 13,
        [N] + months + ["Cumulative"],
        ["PSU companies"] + [N] * 13,
        ["ONGC", ongc] + [N] * 11 + [ongc],
        ["OIL", oil] + [N] * 11 + [oil],
        ["PSU total (Crude Oil)", ongc + oil] + [N] * 11 + [ongc + oil],
        ["JVC/ Private", private] + [N] * 11 + [private],
        ["Total crude oil", total, 0] + [0] * 10 + [total],
        ["Condensate", 0.1] + [N] * 11 + [0.1],
    ]
    return pd.DataFrame(rows)


def test_month_columns_map_to_calendar_months_of_the_fiscal_year():
    frame = parse_ppac_sheet(monthly_sheet(), "crude_oil", "s")
    assert set(frame.period) == {"2022-04"}  # May-March not yet published
    crude = frame[frame["product"] == "crude_oil"].set_index("company_group").value
    assert crude.to_dict() == {"ONGC": 1.5, "OIL": 0.25, "JVC/Private": 0.5}
    assert frame.provisional.all() and (frame.unit == "million_tonnes").all()
    assert "TOTAL" not in set(frame.company_group)  # totals checked, not stored


def test_january_belongs_to_the_later_calendar_year():
    sheet = monthly_sheet()
    sheet.iloc[5:11, 10] = sheet.iloc[5:11, 1]  # Complete January period
    frame = parse_ppac_sheet(sheet, "crude_oil", "s")
    assert "2023-01" in set(frame.period)


def test_components_that_do_not_add_up_fail_closed():
    with pytest.raises(ValueError, match="total"):
        parse_ppac_sheet(monthly_sheet(total=3.0), "crude_oil", "s")


def test_unit_change_fails_closed():
    sheet = monthly_sheet()
    sheet.iloc[1, 2] = "(MMSCM)"
    with pytest.raises(ValueError, match="unit"):
        parse_ppac_sheet(sheet, "crude_oil", "s")


@pytest.mark.parametrize("bad", [-1.0, "n.a.", float("inf")])
def test_invalid_values_fail_closed(bad):
    sheet = monthly_sheet()
    sheet.iloc[5, 1] = bad
    with pytest.raises(ValueError):
        parse_ppac_sheet(sheet, "crude_oil", "s")


def test_fiscal_year_layout():
    rows = [
        ["Period : Since 1998 -99", N, N, "(Million Metric Tonnes)"],
        [N, "1998-99", "1999-00", "2000-01"],
        ["ONGC", 26.45, 24.7, 25.07],
        ["OIL", 3.28, 3.28, 3.29],
        ["PSU total", 29.73, 27.98, 28.36],
        ["JVC/ Private", 3.03, 4.02, 4.09],
        ["Total crude oil", 32.76, 32.0, 32.45],
    ]
    frame = parse_ppac_sheet(pd.DataFrame(rows), "crude_oil", "s")
    assert len(frame) == 9 and set(frame.period_type) == {"fiscal_year"}
    ongc = frame[
        (frame.company_group == "ONGC") & (frame.period == "1999-00")
    ].value.iloc[0]
    assert math.isclose(ongc, 24.7)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2021-2022", None),
        ("2022-06-26", None),
        ("2021-22-26", None),
        ("2021-23", None),
        ("1999-00", "1999-00"),
        ("2021 - 22 (P)", "2021-22"),
        ("Updated 2022-06-26; FY 2021-22", "2021-22"),
    ],
)
def test_fiscal_year_requires_a_complete_consecutive_year_pair(text, expected):
    from worldenergydata.india_dgh.production import _fiscal_year

    assert _fiscal_year(text) == expected


def test_update_date_before_fiscal_year_does_not_shift_months():
    from worldenergydata.india_dgh.production import parse_ppac_gas_sheet

    title = "Updated 2022-06-26; fiscal year 2021-22"
    crude = parse_ppac_sheet(monthly_sheet(title=title), "crude_oil", "s")
    gas = parse_ppac_gas_sheet(gas_sheet(title=title), "s")
    assert set(crude.period) == set(gas.period) == {"2021-04"}
    assert set(crude.fiscal_year) == set(gas.fiscal_year) == {"2021-22"}


def test_shipped_production_is_traceable_and_non_negative():
    frame = load_production()
    assert len(frame) > 0
    assert (frame.value >= 0).all()
    assert set(frame.unit) <= {"million_tonnes", "million_scm"}
    assert not frame.duplicated(
        ["period", "product", "measure", "company_group", "location", "state"]
    ).any()


def gas_sheet(
    cbm=10.0,
    offshore=100.0,
    total=None,
    title="State-wise Natural Gas Production in India, 2018-19 (Month-wise)",
):
    """PPAC NG month-wise layout; CBM sits outside Onshore Total (A)."""
    months = [
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
        "January",
        "February",
        "March",
    ]
    onshore = 30.0 + 20.0
    total = onshore + offshore + cbm if total is None else total
    rows = [
        [title] + [N] * 13,
        [N] * 13 + ["In MMSCM"],
        ["State"] + months + ["Total"],
        ["Gross Production :"] + [N] * 13,
        ["A) Onshore:"] + [N] * 13,
        ["   (i) Assam / Arunachal Pradesh", 30.0] + [N] * 12,
        ["   (ii) Gujarat", 20.0] + [N] * 12,
        ["   (vii) West Bengal, MP, Jharkhand (CBM) ", cbm] + [N] * 12,
        ["Onshore Total (A)", onshore] + [N] * 12,
        ["    B) Offshore:", offshore] + [N] * 12,
        ["Total (A+B)", total] + [N] * 12,
        ["Net Production1", total - 5] + [N] * 12,
    ]
    return pd.DataFrame(rows)


def test_gas_onshore_offshore_and_cbm_locations():
    from worldenergydata.india_dgh.production import parse_ppac_gas_sheet

    frame = parse_ppac_gas_sheet(gas_sheet(), "s")
    gross = frame[frame.measure == "gross_production"]
    by_location = gross.groupby("location").value.sum().to_dict()
    assert by_location == {"onshore": 50.0, "onshore_cbm": 10.0, "offshore": 100.0}
    assert set(gross.period) == {"2018-04"}
    assert frame[frame.measure == "net_production"].value.iloc[0] == 155.0
    assert (frame.unit == "million_scm").all() and not frame.provisional.any()


def test_gas_total_mismatch_fails_closed():
    from worldenergydata.india_dgh.production import parse_ppac_gas_sheet

    with pytest.raises(ValueError, match="Total"):
        parse_ppac_gas_sheet(gas_sheet(total=999.0), "s")


def test_hindi_crude_labels_parse():
    rows = [
        ["अवधि : 1998 -99 से", N, N, "( मिलियन मीट्रिक टन)"],
        [N, "2019-20", "2020-21", "2021-22 (P)"],
        ["ओ.एन.जी. सी.", 19.0, 19.0, 18.5],
        ["ओ. आई. एल.", 3.0, 3.0, 3.0],
        ["पी. एस. यू. _कुल ", 22.0, 22.0, 21.5],
        ["जे.वी.सी. / प्राईवेट", 8.0, 7.0, 7.0],
        ["कुल कच्चा तेल ", 30.0, 29.0, 28.5],
    ]
    frame = parse_ppac_sheet(pd.DataFrame(rows), "crude_oil", "s")
    assert len(frame) == 9
    assert frame[frame.period == "2021-22"].provisional.all()
    assert not frame[frame.period == "2019-20"].provisional.any()


def test_shipped_production_coverage():
    frame = load_production()
    gas = frame[
        (frame["product"] == "natural_gas") & (frame.measure == "gross_production")
    ]
    assert gas.period.nunique() == 96  # FY2012-13 to 2018-19 and FY2021-22, monthly
    assert set(gas.location) == {"onshore", "onshore_cbm", "offshore"}
    crude = frame[
        (frame["product"] == "crude_oil") & (frame.period_type == "fiscal_year")
    ]
    assert crude.period.min() == "1998-99" and crude.period.max() == "2021-22"
    assert set(crude.company_group) == {"ONGC", "OIL", "JVC/Private"}


def test_condensate_is_a_product_with_no_company_split():
    frame = parse_ppac_sheet(monthly_sheet(), "crude_oil", "s")
    condensate = frame[frame["product"] == "condensate"]
    assert condensate.company_group.tolist() == ["all"]
    assert condensate.value.tolist() == [0.1]
    # The crude total excludes condensate, so reconciliation still passes.
    assert frame.loc[frame["product"] == "crude_oil", "value"].sum() == 2.25


def test_shipped_condensate_coverage_and_company_group():
    frame = load_production()
    condensate = frame[frame["product"] == "condensate"]
    assert len(condensate) == 18
    assert set(condensate.company_group) == {"all"}
    annual = condensate[condensate.period_type == "fiscal_year"]
    assert set(annual.period) == {
        f"{year}-{(year + 1) % 100:02d}" for year in range(2006, 2022)
    }
    assert set(condensate.loc[condensate.period_type == "month", "period"]) == {
        "2022-04",
        "2022-05",
    }


def test_later_source_supersedes_whole_period_product_group():
    from worldenergydata.india_dgh.production import combine

    old = parse_ppac_sheet(monthly_sheet(), "crude_oil", "old")
    new = old[old.company_group != "OIL"].assign(source_id="new")
    result = combine([old, new])
    assert set(result.source_id) == {"new"}
    assert "OIL" not in set(result.company_group)


def test_later_crude_source_without_condensate_drops_old_condensate():
    from worldenergydata.india_dgh.production import combine, parse_ppac_gas_sheet

    old = parse_ppac_sheet(monthly_sheet(), "crude_oil", "old")
    earlier = old.assign(period="2022-03")
    sheet = monthly_sheet()
    sheet.iloc[10, 1] = None
    new = parse_ppac_sheet(sheet, "crude_oil", "new")
    gas = parse_ppac_gas_sheet(gas_sheet(title="2022-23"), "gas")
    result = combine([earlier, old, gas, new])
    april = result[result.period == "2022-04"]
    assert "condensate" not in set(april["product"])
    assert set(april.loc[april["product"] == "crude_oil", "source_id"]) == {"new"}
    pd.testing.assert_frame_equal(
        result[result["product"] == "natural_gas"].reset_index(drop=True),
        combine([gas]),
    )
    assert len(result[result.period == "2022-03"]) == len(earlier)


def test_build_omits_fully_superseded_annual_source():
    import runpy
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    script = runpy.run_path(str(root / "scripts/india_dgh/build_tables.py"))
    assert script["CRUDE"] == [
        "ppac_crude_annual_hindi_2022",
        "ppac_crude_current_2022",
    ]


@pytest.mark.parametrize("row", [5, 6, 7, 8, 9])
def test_partial_crude_period_rejected(row):
    sheet = monthly_sheet()
    sheet.iloc[row, 1] = None
    with pytest.raises(ValueError, match="2022-04.*incomplete"):
        parse_ppac_sheet(sheet, "crude_oil", "s")


def test_crude_total_without_components_is_not_unpublished():
    sheet = monthly_sheet()
    sheet.iloc[5:9, 1] = None
    with pytest.raises(ValueError, match="2022-04.*incomplete"):
        parse_ppac_sheet(sheet, "crude_oil", "s")


@pytest.mark.parametrize("row", [5, 6, 7, 8, 9, 10])
def test_partial_gas_period_rejected(row):
    from worldenergydata.india_dgh.production import parse_ppac_gas_sheet

    sheet = gas_sheet()
    sheet.iloc[row, 1] = None
    with pytest.raises(ValueError, match="2018-04.*incomplete"):
        parse_ppac_gas_sheet(sheet, "s")


def test_gas_wholly_unpublished_month_with_zero_totals_is_omitted():
    from worldenergydata.india_dgh.production import parse_ppac_gas_sheet

    sheet = gas_sheet()
    sheet.iloc[[8, 10, 11], 2] = 0.0
    frame = parse_ppac_gas_sheet(sheet, "s")
    assert set(frame.period) == {"2018-04"}


def test_gas_total_without_components_is_not_unpublished():
    from worldenergydata.india_dgh.production import parse_ppac_gas_sheet

    sheet = gas_sheet()
    sheet.iloc[5:10, 1] = None
    with pytest.raises(ValueError, match="2018-04.*incomplete"):
        parse_ppac_gas_sheet(sheet, "s")


def test_stored_crude_values_reject_a_1900_tonne_total_change():
    from pathlib import Path

    from worldenergydata.india_dgh.production import read_sheets

    root = Path(__file__).resolve().parents[3]
    sheet = read_sheets(
        root
        / "data/modules/india_dgh/raw/PT_Crude_oil_production_Current_wb20220626.xls"
    )[0]
    total_row = sheet.iloc[:, 0].eq("Total crude oil")
    sheet.loc[total_row, 1] += 0.0019  # 1,900 tonnes in million tonnes
    with pytest.raises(ValueError, match="2022-04.*total"):
        parse_ppac_sheet(sheet, "crude_oil", "s")


@pytest.mark.parametrize("scale", [1.0, 4096.0])
@pytest.mark.parametrize("steps, accepted", [(3, True), (4, False)])
def test_reconciliation_bound_follows_binary_precision(scale, steps, accepted):
    """Three operands at scale sum to 3*scale: bound is 3.5 ulps of total."""
    total = 3 * scale + steps * math.ulp(3 * scale)
    sheet = monthly_sheet(ongc=scale, oil=scale, private=scale, total=total)
    if accepted:
        assert len(parse_ppac_sheet(sheet, "crude_oil", "s")) == 4
    else:
        with pytest.raises(ValueError, match="total"):
            parse_ppac_sheet(sheet, "crude_oil", "s")


@pytest.mark.parametrize("steps, accepted", [(3, True), (4, False)])
def test_gas_onshore_reconciliation_precision_boundary(steps, accepted):
    from worldenergydata.india_dgh.production import parse_ppac_gas_sheet

    sheet = gas_sheet()
    delta = steps * math.ulp(50.0)
    sheet.iloc[8, 1] += delta
    if accepted:
        assert len(parse_ppac_gas_sheet(sheet, "s")) == 5
    else:
        with pytest.raises(ValueError, match="Onshore Total"):
            parse_ppac_gas_sheet(sheet, "s")
