"""Tests for the C-NLOER offshore production loader (#719).

Covers the pure ``parse_cnloer_production_text`` transform (reservoir summing,
imperial-vs-metric column preference, mpro rejection, blank/header drop,
condensate absent) + the committed labeled-synthetic fixture loader. Fully
self-contained (no PDFs / poppler / network).
"""

import pytest

from worldenergydata.canada.production.cnloer_loader import (
    E3M3_TO_MCF,
    M3_TO_BBL,
    CnloerFixtureLoader,
    CnloerParseError,
    CnloerProductionLoader,
    parse_cnloer_production_text,
)

# Synthetic pdftotext-style text: Month Year oil_m3 oil_bbl gas_e3m3 gas_MMscf
# water_m3 water_bbl. Header + a blank future month are interleaved and dropped.
_HIBERNIA_TEXT = """
Hibernia Monthly Production
Month Year Oil(m3) Oil(bbl) Gas(e3m3) Gas(MMscf) Water(m3) Water(bbl)
January 2024 10000 62898 5000 176.6 8000 50318
February 2024 9500 59753 4800 169.5 8200 51576
March 2024
"""

# North Amethyst has NO per-month Total row — two reservoir subrows per month
# must be summed to the field monthly total.
_NORTH_AMETHYST_TEXT = """
Month Year Oil(m3) Oil(bbl) Gas(e3m3) Gas(MMscf) Water(m3) Water(bbl)
January 2023 1000 6290 500 17.7 400 2516
January 2023 2000 12580 500 17.7 600 3774
"""

# Metric-only row (no imperial columns) → converted via factors.
_METRIC_ONLY_TEXT = """
Month Year Oil(m3) Gas(e3m3) Water(m3)
January 2022 100 10 50
"""


def test_parse_prefers_imperial_columns_and_drops_header_and_blank_month():
    out = parse_cnloer_production_text(_HIBERNIA_TEXT, field_name="Hibernia")

    assert list(out.columns) == [
        "field_name",
        "year",
        "month",
        "oil_bbl",
        "gas_mcf",
        "water_bbl",
    ]
    # header ("Month Year …") + blank "March 2024" row dropped
    assert set(out["month"]) == {1, 2}
    jan = out[out["month"] == 1].iloc[0]
    assert jan["oil_bbl"] == pytest.approx(62898.0)  # imperial bbl column
    assert jan["gas_mcf"] == pytest.approx(176.6 * 1000)  # MMscf × 1000
    assert jan["water_bbl"] == pytest.approx(50318.0)
    # condensate intentionally absent (C-NLOER has no condensate column)
    assert "condensate_bbl" not in out.columns


def test_parse_sums_reservoir_subrows_per_month():
    out = parse_cnloer_production_text(
        _NORTH_AMETHYST_TEXT, field_name="North Amethyst"
    )
    assert len(out) == 1
    row = out.iloc[0]
    assert row["oil_bbl"] == pytest.approx(6290.0 + 12580.0)
    assert row["water_bbl"] == pytest.approx(2516.0 + 3774.0)


def test_parse_falls_back_to_metric_columns():
    out = parse_cnloer_production_text(_METRIC_ONLY_TEXT, field_name="Hibernia")
    row = out.iloc[0]
    assert row["oil_bbl"] == pytest.approx(100 * M3_TO_BBL)
    assert row["gas_mcf"] == pytest.approx(10 * E3M3_TO_MCF)


def test_parse_rejects_all_field_totals_report():
    with pytest.raises(CnloerParseError, match="totals"):
        parse_cnloer_production_text(_HIBERNIA_TEXT, field_name="mpro")


def test_parse_raises_when_no_rows():
    with pytest.raises(CnloerParseError, match="no monthly"):
        parse_cnloer_production_text("just a header line\n", field_name="Hibernia")


def test_production_loader_uses_injected_raw_text():
    loader = CnloerProductionLoader(field_name="Hibernia", raw_text=_HIBERNIA_TEXT)
    out = loader.load()
    assert set(out["field_name"]) == {"Hibernia"}
    assert out["oil_bbl"].gt(0).all()


def test_fixture_loader_is_labeled_synthetic_with_licence_provenance():
    loader = CnloerFixtureLoader()

    metadata = loader.metadata()
    frame = loader.load_field_production("Hibernia")

    assert "LICENCE_NOTE" in metadata
    assert "SYNTHETIC" in metadata["fixture_nature"].upper()
    assert metadata["statistics_page"].startswith("https://www.cnloer.ca")
    assert set(frame["field_name"]) == {"Hibernia"}
    assert (frame["source"] == "cnloer_fixture_synthetic").all()
    assert frame["oil_bbl"].gt(0).any()
