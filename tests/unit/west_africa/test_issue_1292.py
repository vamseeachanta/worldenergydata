"""Regression examples for issue #1292 (2026), SF1–SF7.

All dates, volumes, rates and cash flows are synthetic inputs, not source data.
Expected arithmetic is written out below; fiscal applicability is not tested.
"""

from unittest.mock import MagicMock

import pytest
from worldenergydata.west_africa.analysis import field_economics as fiscal
from worldenergydata.west_africa.eiti import eiti_api as eiti
from worldenergydata.west_africa.nigeria import blend_production as blends
from worldenergydata.west_africa.nigeria import nuprc_client as nuprc


def pdf_fixture(monkeypatch, pages):
    """Supply extracted tables and report text without generating PDF bytes."""
    pdf = MagicMock()
    pdf.pages = []
    for text, tables in pages:
        page = MagicMock()
        page.extract_text.return_value = text
        page.extract_tables.return_value = tables
        pdf.pages.append(page)
    backend = MagicMock()
    backend.open.return_value.__enter__.return_value = pdf
    monkeypatch.setattr(nuprc, "pdfplumber", backend)


def test_total_and_repeated_tables_are_not_production(monkeypatch):
    """Hand sum: ALPHA 8 + BETA 2 = 10 kbd, once, excluding total 10."""
    table = [
        ["Blend", "Production (kbd)"],
        ["ALPHA", "8"],
        ["BETA", "2"],
        ["TOTAL CRUDE", "10"],
        ["Grand Total", "10"],
        ["SUB-TOTAL", "10"],
    ]
    pdf_fixture(monkeypatch, [("March 2024", [table]), ("March 2024", [table])])
    rows = nuprc.parse_blend_table_from_pdf(b"synthetic")
    assert [(r["blend"], r["volume_kbd"]) for r in rows] == [
        ("ALPHA", 8.0),
        ("BETA", 2.0),
    ]
    assert all((r["year"], r["month"]) == (2024, 3) for r in rows)


def test_conflicting_duplicate_is_an_error(monkeypatch):
    """Two values for the same blend and period have no unique answer."""
    tables = [
        [["Blend", "kbd"], ["ALPHA", "8"]],
        [["Blend", "kbd"], ["ALPHA", "9"]],
    ]
    pdf_fixture(monkeypatch, [("March 2024", tables)])
    with pytest.raises(nuprc.NuprcAPIError, match="Conflicting"):
        nuprc.parse_blend_table_from_pdf(b"synthetic")


def test_loader_rejects_report_period_mismatch(monkeypatch):
    """A March report cannot answer a February request."""
    loader = blends.BlendProductionLoader()
    monkeypatch.setattr(loader._client, "download_pdf", lambda _: b"synthetic")
    monkeypatch.setattr(
        blends,
        "parse_blend_table_from_pdf",
        lambda _: [{"blend": "ALPHA", "volume_kbd": 8, "month": 3, "year": 2024}],
    )
    with pytest.raises(nuprc.NuprcAPIError, match="period"):
        loader.load(2024, 2, pdf_url="https://example.org/report.pdf")


def test_loader_rejects_unestablished_period(monkeypatch):
    """Request arguments alone are not evidence of a report's period."""
    loader = blends.BlendProductionLoader()
    monkeypatch.setattr(loader._client, "download_pdf", lambda _: b"synthetic")
    monkeypatch.setattr(
        blends,
        "parse_blend_table_from_pdf",
        lambda _: [{"blend": "ALPHA", "volume_kbd": 8, "month": None, "year": None}],
    )
    with pytest.raises(nuprc.NuprcAPIError, match="period"):
        loader.load(2024, 3)


# Synthetic invalid Gregorian month indices; valid indices are calendar.month_name
# (Python Library Reference, calendar, 2025), not an engineering acceptance limit.
@pytest.mark.parametrize("month", [0, -1, 13, 1.5, True])
def test_invalid_month_rejected_before_download(monkeypatch, month):
    loader = blends.BlendProductionLoader()
    download = MagicMock()
    monkeypatch.setattr(loader._client, "download_pdf", download)
    with pytest.raises(ValueError, match="month"):
        loader.load(2024, month, pdf_url="https://example.org/report.pdf")
    download.assert_not_called()


def test_all_candidate_urls_use_matching_months():
    """Calendar order, independently enumerated; URLs remain candidates."""
    names = "january february march april may june july august september october november december"
    loader = blends.BlendProductionLoader()
    for month, name in enumerate(names.split(), start=1):
        assert loader._build_pdf_url(2024, month).endswith(f"{name}-2024.pdf")


def test_kbd_input_selects_bopd_tier(monkeypatch):
    """Hand calculation: 30 kbd = 30,000 bopd, so synthetic second tier.

    With profit oil 8 USD, government 1/2 gets 4 USD, contractor gets 4 USD.
    Unit source: BIPM SI Brochure, 9th ed. (2019), section 3, Table 7, kilo.
    """
    # Synthetic tier inputs, not statutory coefficients.
    monkeypatch.setattr(fiscal, "PROFIT_OIL_TIERS", [(20_000, 0.25), (40_000, 0.5)])
    result = fiscal.calculate_profit_oil_split(8, production_rate_kbd=30)
    assert result == {"nnpc": 4, "contractor": 4}
    assert result == fiscal.calculate_profit_oil_split(8, production_rate_bopd=30_000)
    with pytest.raises(ValueError, match="one"):
        fiscal.calculate_profit_oil_split(8, 30_000, production_rate_kbd=30)


def test_rate_beyond_configured_tiers_is_not_defaulted(monkeypatch):
    """A finite table without a matching ceiling supplies no share."""
    monkeypatch.setattr(fiscal, "PROFIT_OIL_TIERS", [(20_000, 0.25)])
    with pytest.raises(ValueError, match="tier"):
        fiscal.calculate_profit_oil_split(8, 30_000)


def test_fiscal_allocation_conserves_gross(monkeypatch):
    """Independent synthetic cash ledger, all USD.

    Gross 128, royalty 0, costs 32 => profit 96. Government share 1/2
    => 48; contractor share 48. Tax 1/4 => 12; gross levy 1/8 => 16.
    Contractor cash = 48 - 12 - 16 = 20. Government = 48 + 12 + 16 = 76.
    Cost recovery + contractor cash + government = 32 + 20 + 76 = 128.
    """
    monkeypatch.setattr(fiscal, "PPT_RATE_PSC", 0.25)
    monkeypatch.setattr(fiscal, "CITA_RATE", 0.0)
    monkeypatch.setattr(fiscal, "NDDC_LEVY_RATE", 0.125)
    monkeypatch.setattr(fiscal, "PROFIT_OIL_TIERS", [(float("inf"), 0.5)])
    result = fiscal.NigeriaDeepwaterPSC().calculate(128, 16, 16, production_rate_kbd=30)
    assert result.cost_oil == 32
    assert result.contractor_net_income == 20
    assert result.total_government_take == 76
    assert (
        result.cost_oil + result.contractor_net_income + result.total_government_take
        == 128
    )


def test_levy_obligation_is_not_hidden_by_zero_floor(monkeypatch):
    """Gross 8; cost recovery 8; no profit/tax; levy 1 => contractor -1.

    Recovery 8 + government 1 + contractor -1 = 8. A cash obligation may
    exceed contractor profit; flooring it invents revenue.
    """
    monkeypatch.setattr(fiscal, "NDDC_LEVY_RATE", 0.125)
    result = fiscal.NigeriaDeepwaterPSC(cost_oil_ceiling=1).calculate(8, 8, 0, 0)
    assert result.contractor_net_income == -1
    assert (
        result.cost_oil + result.total_government_take + result.contractor_net_income
        == 8
    )


# Payload examples from the local client contract; [] is explicitly empty,
# whereas null, a missing data key, or a scalar supplies no record collection.
@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"error": "unavailable"},
        {"data": None},
        {"data": {}},
        {"data": [1]},
        "invalid",
    ],
)
@pytest.mark.parametrize(
    "method", ["get_countries", "get_production_data", "get_payment_data"]
)
def test_eiti_schema_failure_is_not_empty_or_cached(monkeypatch, payload, method):
    response = MagicMock(status_code=200)
    response.json.return_value = payload
    transport = MagicMock()
    transport.get.return_value = response
    monkeypatch.setattr(eiti, "requests", transport)
    client = eiti.EitiApiClient()
    with pytest.raises(eiti.EitiApiError, match="record"):
        getattr(client, method)()
    assert not client._cache
    response.json.return_value = {"data": []}
    assert getattr(client, method)() == []
    assert transport.get.call_count == 2


def test_report_discovery_failure_is_not_empty(monkeypatch):
    transport = MagicMock()
    transport.get.side_effect = RuntimeError("offline")
    monkeypatch.setattr(nuprc, "requests", transport)
    with pytest.raises(nuprc.NuprcAPIError):
        nuprc.list_report_urls()


def test_report_discovery_resolves_relative_and_query_urls(monkeypatch):
    """RFC 3986 (2005), section 5: resolve relative references to base URI."""
    transport = MagicMock()
    transport.get.return_value = MagicMock(
        status_code=200,
        text="""
        <a href="reports/a.pdf?download=1">a</a>
        <a href="reports/a.pdf?download=1">a</a>
        <a href="//example.org/b.PDF">b</a>
    """,
    )
    monkeypatch.setattr(nuprc, "requests", transport)
    assert nuprc.list_report_urls("https://example.org/index/") == [
        "https://example.org/index/reports/a.pdf?download=1",
        "https://example.org/b.PDF",
    ]


@pytest.mark.parametrize("text", ["", "March 2024 April 2024"])
def test_pdf_period_must_be_established(monkeypatch, text):
    """Zero or two distinct periods do not identify one report period."""
    pdf_fixture(monkeypatch, [(text, [[["Blend", "kbd"], ["ALPHA", "8"]]])])
    with pytest.raises(nuprc.NuprcAPIError, match="period"):
        nuprc.parse_blend_table_from_pdf(b"synthetic")


@pytest.mark.parametrize("value", ["NaN", "inf", "-1", "unreadable"])
def test_invalid_pdf_value_is_not_partial_success(monkeypatch, value):
    """Synthetic invalid values after a valid row must reject the report."""
    table = [["Blend", "kbd"], ["ALPHA", "8"], ["BETA", value]]
    pdf_fixture(monkeypatch, [("March 2024", [table])])
    with pytest.raises(nuprc.NuprcAPIError):
        nuprc.parse_blend_table_from_pdf(b"synthetic")


def test_pdf_units_are_not_assumed(monkeypatch):
    """A monthly barrel total is not already a daily rate in kbd."""
    table = [["Blend", "Volume (barrels)"], ["ALPHA", "8000"]]
    pdf_fixture(monkeypatch, [("March 2024", [table])])
    with pytest.raises(nuprc.NuprcAPIError, match="units"):
        nuprc.parse_blend_table_from_pdf(b"synthetic")


def test_zero_and_distinct_periods_are_preserved(monkeypatch):
    """Zero is observed production; the same blend in two months is distinct."""
    table = [["Blend", "kbd"], ["ALPHA", 0]]
    pdf_fixture(monkeypatch, [("March 2024", [table]), ("April 2024", [table])])
    rows = nuprc.parse_blend_table_from_pdf(b"synthetic")
    assert [(row["month"], row["volume_kbd"]) for row in rows] == [(3, 0), (4, 0)]


def test_pdf_exception_does_not_return_earlier_pages(monkeypatch):
    """A failing second page invalidates the otherwise valid first page."""
    table = [["Blend", "kbd"], ["ALPHA", "8"]]
    pdf_fixture(monkeypatch, [("March 2024", [table]), ("March 2024", [table])])
    pdf = nuprc.pdfplumber.open.return_value.__enter__.return_value
    pdf.pages[1].extract_tables.side_effect = RuntimeError("extraction failed")
    with pytest.raises(nuprc.NuprcAPIError, match="parsing"):
        nuprc.parse_blend_table_from_pdf(b"synthetic")


# Synthetic counterexamples to finite, nonnegative physical inputs; unity is
# the upper bound of a fraction by definition, not a fiscal acceptance limit.
@pytest.mark.parametrize(
    "name,value",
    [
        ("gross_revenue", -1),
        ("opex", float("nan")),
        ("capex", float("inf")),
        ("production_rate_kbd", -1),
        ("production_rate_kbd", float("inf")),
        ("production_rate_kbd", True),
        ("production_rate_kbd", "30"),
    ],
)
def test_fiscal_input_domain(name, value):
    inputs = {"gross_revenue": 128, "opex": 16, "capex": 16, "production_rate_kbd": 30}
    inputs[name] = value
    with pytest.raises(ValueError):
        fiscal.NigeriaDeepwaterPSC().calculate(**inputs)


@pytest.mark.parametrize("ceiling", [-1, 2, float("nan")])
def test_recovery_fraction_domain(ceiling):
    with pytest.raises(ValueError, match="cost_oil_ceiling"):
        fiscal.NigeriaDeepwaterPSC(cost_oil_ceiling=ceiling).calculate(8, 8, 0, 0)


@pytest.mark.parametrize("status,text", [(503, "unavailable"), (200, "<html></html>")])
def test_report_discovery_http_and_layout_failures(monkeypatch, status, text):
    transport = MagicMock()
    transport.get.return_value = MagicMock(status_code=status, text=text)
    monkeypatch.setattr(nuprc, "requests", transport)
    with pytest.raises(nuprc.NuprcAPIError):
        nuprc.list_report_urls()


def test_report_discovery_missing_dependency(monkeypatch):
    monkeypatch.setattr(nuprc, "BeautifulSoup", None)
    with pytest.raises(nuprc.NuprcAPIError, match="installed"):
        nuprc.list_report_urls()
