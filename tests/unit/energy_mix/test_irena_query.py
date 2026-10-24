"""Query examples use authored synthetic observations, never source data."""

import csv
import io
import socket
import sys
from decimal import localcontext
from pathlib import Path
from urllib import request

import pytest

from worldenergydata.energy_mix.__main__ import main
from worldenergydata.energy_mix.irena import COLUMNS
from worldenergydata.energy_mix.query import query_export

CSV = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "energy_mix"
    / "irena_offshore_synthetic.csv"
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network transport is forbidden in tests")

    monkeypatch.setattr(request, "urlopen", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def rows(raw):
    return list(csv.DictReader(io.StringIO(raw.decode())))


def test_default_query_preserves_all_observations():
    """Independent expectation: retain all three literal fixture rows in order."""
    assert rows(query_export(CSV.read_bytes())) == rows(CSV.read_bytes())


def test_country_and_inclusive_year_selection():
    """Fixture: Alpha has 2023 and 2024; only its 2024 row meets both bounds."""
    selected = rows(
        query_export(
            CSV.read_bytes(),
            countries=["synthetic alpha"],
            start_year=2024,
            end_year=2024,
        )
    )
    assert selected == [rows(CSV.read_bytes())[1]]


def test_multiple_countries_do_not_duplicate_observations():
    """Set selection retains the original rows once, in their supplied order."""
    selected = rows(
        query_export(
            CSV.read_bytes(),
            countries=["Synthetic Beta", "Synthetic Alpha", "synthetic alpha"],
            end_year=2023,
        )
    )
    assert selected == [rows(CSV.read_bytes())[0]]


@pytest.mark.parametrize(
    "filters",
    [
        {"countries": []},
        {"countries": ["Unknown area"]},
        {"start_year": 2025},
        {"end_year": 2022},
    ],
)
def test_empty_selection_retains_header(filters):
    """No matching literal row means a header and no invented observations."""
    raw = query_export(CSV.read_bytes(), **filters)
    assert raw.decode() == ",".join(COLUMNS) + "\n"


def test_generation_conversion_and_provenance():
    """Hand calculation, BIPM SI Brochure 9th ed. (2019), v4.01 (2026),
    section 3, table 7: giga = 10**9 and mega = 10**6. Thus
    20.25 GWh * (10**9 / 10**6) = 20250 MWh; 1 GWh = 1000 MWh.
    The middle row's absent generation remains blank; its zero MW remains zero.
    No capacity-to-energy equation is applied.
    """
    original = rows(CSV.read_bytes())
    selected = rows(query_export(CSV.read_bytes(), generation_unit="MWh"))
    assert [row["generation_mwh"] for row in selected] == ["20250", "", "1000"]
    assert [row["capacity_mw"] for row in selected] == ["10.5", "0", ""]
    for before, after in zip(original, selected):
        for key in COLUMNS:
            if key != "generation_gwh":
                assert after[key] == before[key]
        assert "generation_gwh" not in after


def test_reported_zero_generation_is_not_missing():
    """Hand calculation: a reported 0 GWh times the SI ratio is 0 MWh."""
    raw = CSV.read_bytes().replace(b",20.25,", b",0,")
    assert rows(query_export(raw, generation_unit="MWh"))[0]["generation_mwh"] == "0"


@pytest.mark.parametrize(
    "filters",
    [
        {"start_year": 2024, "end_year": 2023},
        {"start_year": 2023.5},
        {"end_year": True},
        {"countries": "Synthetic Alpha"},
        {"countries": [""]},
        {"countries": [" Synthetic Alpha"]},
        {"countries": [None]},
        {"generation_unit": "kWh"},
    ],
)
def test_invalid_query_parameters(filters):
    with pytest.raises(ValueError):
        query_export(CSV.read_bytes(), **filters)


def test_query_validates_unselected_rows():
    raw = CSV.read_bytes().replace(b",20.25,", b",NaN,")
    with pytest.raises(ValueError, match="finite"):
        query_export(raw, countries=["Unknown area"])


def test_conversion_above_binary64_range_remains_exact():
    """Hand calculation: 1e308 GWh * 1000 = 1e311 MWh (SI table 7 above).
    Decimal CSV output need not fit binary64; it must never become infinity.
    """
    raw = CSV.read_bytes().replace(b",20.25,", b",1e308,")
    assert rows(query_export(raw, generation_unit="MWh"))[0]["generation_mwh"] == (
        "1.000E+311"
    )


def test_conversion_retains_supplied_decimal_precision():
    """Hand calculation: shifting the decimal point three places gives
    1.234567890123456789012345678901 GWh = 1234.567890123456789012345678901 MWh.
    The scale follows SI table 7 above, independent of binary64 rounding.
    """
    raw = CSV.read_bytes().replace(b",20.25,", b",1.234567890123456789012345678901,")
    assert rows(query_export(raw, generation_unit="MWh"))[0]["generation_mwh"] == (
        "1234.567890123456789012345678901"
    )


def test_conversion_is_independent_of_ambient_decimal_context():
    """Hand result remains 20250 MWh with a caller precision of one digit."""
    with localcontext() as context:
        context.prec = 1
        context.Emax = 1
        assert (
            rows(query_export(CSV.read_bytes(), generation_unit="MWh"))[0][
                "generation_mwh"
            ]
            == "20250"
        )


def test_small_exponent_stays_compact_and_nonzero():
    """Hand calculation: 1e-1000000 GWh * 1000 = 1e-999997 MWh.
    This invented stress case must not expand a million zeroes or underflow.
    """
    raw = CSV.read_bytes().replace(b",20.25,", b",1e-1000000,")
    assert rows(query_export(raw, generation_unit="MWh"))[0]["generation_mwh"] == (
        "1.000E-999997"
    )


def test_cli_query_stdout(tmp_path, monkeypatch, capsys):
    """CLI expectation: select the literal Beta row and convert 1 GWh to 1000 MWh."""
    source = tmp_path / "input.csv"
    before = CSV.read_bytes()
    source.write_bytes(before)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "energy_mix",
            "query",
            "--input",
            str(source),
            "--country",
            "Synthetic Alpha",
            "--country",
            "Synthetic Beta",
            "--start-year",
            "2024",
            "--end-year",
            "2024",
            "--generation-unit",
            "MWh",
        ],
    )
    main()
    selected = rows(capsys.readouterr().out.encode())
    assert [row["country"] for row in selected] == ["Synthetic Alpha", "Synthetic Beta"]
    assert [row["generation_mwh"] for row in selected] == ["", "1000"]
    assert source.read_bytes() == before


def test_cli_query_file_and_overwrite_protection(tmp_path, monkeypatch):
    output = tmp_path / "query.csv"
    monkeypatch.setattr(
        sys,
        "argv",
        ["energy_mix", "query", "--input", str(CSV), "--output", str(output)],
    )
    main()
    assert rows(output.read_bytes()) == rows(CSV.read_bytes())
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        main()
    assert output.read_bytes() == before


@pytest.mark.parametrize(
    "arguments",
    [
        ["query"],
        ["query", "--input", str(CSV), "--output", str(CSV)],
        ["query", "--input", str(CSV), "--manifest", "unused.json"],
        ["query", "--input", str(CSV), "--synthetic"],
        ["load", "--input", str(CSV), "--country", "Synthetic Alpha"],
        ["load", "--input", str(CSV), "--generation-unit", "MWh"],
    ],
)
def test_cli_rejects_incompatible_options(arguments, monkeypatch):
    before = CSV.read_bytes()
    monkeypatch.setattr(sys, "argv", ["energy_mix", *arguments])
    with pytest.raises(SystemExit):
        main()
    assert CSV.read_bytes() == before
