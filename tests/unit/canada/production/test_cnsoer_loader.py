"""Offline tests with invented volumes, never copied regulator observations.

Layout basis: CNSOER monthly reports, archived January 2025, total-production
table headings and date columns (see SOURCE_URLS in the loader). Expected
values below are identity hand calculations: parsing changes punctuation and
types only; 1,234.50 becomes 1234.5 and 6.25 remains 6.25, with no conversion.
"""

import hashlib
import subprocess

import pandas as pd
import pytest

from worldenergydata.canada.production.cnsoer_loader import (
    CnsoerParseError,
    CnsoerProductionLoader,
    parse_cnsoer_production_text,
)


def table(rows="Dec-99 1,234.50 6.25", title="TOTAL PRODUCTION"):
    """Synthetic text with the published column/unit headings only."""
    return (
        f"{title}\n\n"
        "Date Gas Equivalent Volume Water Volume\n"
        "(10³M³/Month) (M³/Month)\n"
        f"{rows}\n"
    )


def test_total_selection_does_not_add_field_or_well_rows():
    text = "\f".join(
        [
            table(),
            table("Dec-99 900.00 4.00", "THEBAUD TOTAL PRODUCTION"),
            table("Dec-99 200.00 1.00 12.00", "THEBAUD 1: T1"),
        ]
    )
    result = parse_cnsoer_production_text(text, report="sable")
    assert result.to_dict("records") == [
        {
            "field_name": "Sable",
            "year": 1999,
            "month": 12,
            "gas_equivalent_e3m3": 1234.5,
            "water_m3": 6.25,
            "source": "cnsoer",
        }
    ]
    assert result.attrs["revenue_status"] == "NOT_EVALUATED"
    assert result.attrs["readiness_status"] == "unverified"
    assert result.attrs["history_complete"] is False
    assert "gas_mcf" not in result
    assert "oil_bbl" not in result
    assert "condensate_bbl" not in result


def test_field_section_is_explicit_and_not_added_to_report_total():
    result = parse_cnsoer_production_text(
        table() + "\f" + table("Dec-99 7.50 2.00", "ALMA TOTAL PRODUCTION"),
        report="sable",
        section="ALMA TOTAL PRODUCTION",
    )
    assert result["field_name"].tolist() == ["Alma"]
    assert result["gas_equivalent_e3m3"].tolist() == [7.5]
    assert result.attrs["section"] == "ALMA TOTAL PRODUCTION"


def test_century_rollover_sorting_and_explicit_zero_are_preserved():
    result = parse_cnsoer_production_text(
        table("Jan-00 0.00 0.00\nDec-99 1.00 2.00"), report="sable"
    )
    assert result["year"].tolist() == [1999, 2000]
    assert result["month"].tolist() == [12, 1]
    assert result["gas_equivalent_e3m3"].tolist() == [1.0, 0.0]
    assert result["water_m3"].tolist() == [2.0, 0.0]


def test_documented_trailing_annotation_preserves_numeric_values():
    """Identity hand calculation: invented 10.00 and 3.00 remain 10 and 3.

    Layout source: January 2025 archived total table, November 2014 row,
    which carries a stray backtick after the water column.
    """
    result = parse_cnsoer_production_text(table("Nov-14 10.00 3.00 `"), report="sable")
    assert result["gas_equivalent_e3m3"].tolist() == [10.0]
    assert result["water_m3"].tolist() == [3.0]


def test_deep_panuke_uses_same_native_units_without_summing_wells():
    result = parse_cnsoer_production_text(
        table("Aug-13 10.00 3.00") + "\f" + table("Aug-13 8 2 10", "Well"),
        report="deep_panuke",
    )
    assert result["field_name"].tolist() == ["Deep Panuke"]
    assert result["gas_equivalent_e3m3"].tolist() == [10.0]
    assert result["water_m3"].tolist() == [3.0]


def test_repeated_page_headers_allow_continuation_not_duplicate_periods():
    result = parse_cnsoer_production_text(
        table() + "\f" + table("Jan-00 4 5"), report="sable"
    )
    assert result["gas_equivalent_e3m3"].tolist() == [1234.5, 4.0]
    with pytest.raises(CnsoerParseError, match="duplicate"):
        parse_cnsoer_production_text(table() + "\f" + table(), report="sable")


@pytest.mark.parametrize(
    "row",
    [
        "Dec-99 -1 2",
        "Dec-99 NaN 2",
        "Dec-99 inf 2",
        "Dec-99 1 -2",
        "Dec-99 1",
        "Dec-99",
        "Dec-99 1 2 3",
        "Dec-99 1,23.00 2",
        "Dec-99 -- 2",
        "Foo-99 1 2",
        "Dec-98 1 2",
        "Jan-19 1 2",
        "Nov-99 1 2",
    ],
)
def test_malformed_or_out_of_range_rows_fail_closed(row):
    with pytest.raises(CnsoerParseError):
        parse_cnsoer_production_text(table(row), report="sable")


@pytest.mark.parametrize(
    "text",
    [
        "unrelated report",
        table(""),
        table().replace("Equivalent", "Sales"),
        table().replace("10³M³", "MMscf"),
        table().replace("(M³/Month)", "(bbl/Month)"),
    ],
)
def test_missing_section_data_or_wrong_units_fail_closed(text):
    with pytest.raises(CnsoerParseError):
        parse_cnsoer_production_text(text, report="sable")


def test_unknown_report_or_unsupported_field_section_is_rejected():
    with pytest.raises(CnsoerParseError, match="report"):
        parse_cnsoer_production_text(table(), report="other")
    with pytest.raises(CnsoerParseError, match="section"):
        parse_cnsoer_production_text(table(), report="deep_panuke", section="ALMA")


def test_complete_history_flag_is_based_on_all_expected_periods():
    # Source date-column bounds: archived total table August 2013 to May 2018.
    # All invented volumes are zero; one row per calendar month is generated.
    periods = pd.period_range("2013-08", "2018-05", freq="M")
    rows = "\n".join(f"{period.strftime('%b-%y')} 0 0" for period in periods)
    result = parse_cnsoer_production_text(table(rows), report="deep_panuke")
    assert len(result) == len(periods)
    assert result.attrs["history_complete"] is True
    incomplete = parse_cnsoer_production_text(
        table("Aug-13 0 0\nMay-18 0 0"), report="deep_panuke"
    )
    assert incomplete.attrs["history_complete"] is False


def test_text_loader_records_digest_without_claiming_pdf_identity():
    text = table()
    result = CnsoerProductionLoader(report="sable", raw_text=text).load()
    assert result.attrs["input_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert result.attrs["input_kind"] == "extracted_text"


def test_pdf_loader_hashes_the_exact_bytes_sent_to_extractor(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.pdf"
    payload = b"synthetic placeholder, not a regulator PDF"
    path.write_bytes(payload)

    def extract(args, **kwargs):
        assert args == ["pdftotext", "-layout", "-", "-"]
        assert kwargs == {"input": payload}
        return table("Aug-13 10 3").encode()

    monkeypatch.setattr(subprocess, "check_output", extract)
    result = CnsoerProductionLoader(report="deep_panuke", path=path).load()
    assert result.attrs["input_sha256"] == hashlib.sha256(payload).hexdigest()
    assert result.attrs["input_kind"] == "pdf"
    assert result["gas_equivalent_e3m3"].tolist() == [10.0]


def test_loader_requires_exactly_one_input(tmp_path):
    for kwargs in [{}, {"path": tmp_path / "input.pdf", "raw_text": table()}]:
        with pytest.raises(CnsoerParseError, match="exactly one"):
            CnsoerProductionLoader(report="sable", **kwargs).load()
