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
    months = ["April", "May", "June", "July", "August", "September", "October",
              "November", "December", "January", "February", "March"]
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
    sheet.iloc[5, 10] = 1.0  # ONGC, January column
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
    ongc = frame[(frame.company_group == "ONGC") & (frame.period == "1999-00")].value.iloc[0]
    assert math.isclose(ongc, 24.7)


def test_shipped_production_is_traceable_and_non_negative():
    frame = load_production()
    assert len(frame) > 0
    assert (frame.value >= 0).all()
    assert set(frame.unit) <= {"million_tonnes", "million_scm"}
    assert not frame.duplicated(["period", "product", "measure", "company_group", "location", "state"]).any()


def gas_sheet(cbm=10.0, offshore=100.0, total=None, title="State-wise Natural Gas Production in India, 2018-19 (Month-wise)"):
    """PPAC NG month-wise layout; CBM sits outside Onshore Total (A)."""
    months = ["April", "May", "June", "July", "August", "September", "October",
              "November", "December", "January", "February", "March"]
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
    gas = frame[(frame["product"] == "natural_gas") & (frame.measure == "gross_production")]
    assert gas.period.nunique() == 96  # FY2012-13 to 2018-19 and FY2021-22, monthly
    assert set(gas.location) == {"onshore", "onshore_cbm", "offshore"}
    crude = frame[(frame["product"] == "crude_oil") & (frame.period_type == "fiscal_year")]
    assert crude.period.min() == "1998-99" and crude.period.max() == "2021-22"
    assert set(crude.company_group) == {"ONGC", "OIL", "JVC/Private"}
