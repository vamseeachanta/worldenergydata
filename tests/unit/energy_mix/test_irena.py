"""Offline validation using invented, explicitly synthetic observations."""

import csv
import io
import socket
import sys
from pathlib import Path
from urllib import request

import pytest

from worldenergydata.energy_mix.irena import (
    AccessRefused,
    emit_manifest,
    fetch_irena,
    generation_gwh_to_mwh,
    load_export,
    write_table,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "energy_mix"
CSV = FIXTURES / "irena_offshore_synthetic.csv"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network transport is forbidden in tests")

    monkeypatch.setattr(request, "urlopen", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def changed(column, value):
    rows = list(csv.DictReader(io.StringIO(CSV.read_text())))
    rows[0][column] = value
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def test_load_and_round_trip():
    records = load_export(CSV.read_bytes())
    assert records[0]["capacity_mw"] == 10.5
    assert records[0]["generation_gwh"] == 20.25
    assert records[1]["capacity_mw"] == 0
    assert records[1]["generation_gwh"] is None
    assert records[2]["capacity_mw"] is None
    assert records[0]["iso_code"] == ""
    assert load_export(write_table(records)) == records


def test_loaded_generation_in_mwh():
    """Hand calculation using the synthetic fixture's authored 20.25 GWh.

    NIST SP 330 (2019), section 3, table 7 gives G = 10**9 and M = 10**6:
    20.25 GWh = 20.25 * (10**9 / 10**6) MWh = 20250 MWh, exactly.
    https://www.nist.gov/pml/special-publication-330/sp-330-section-3
    """
    records = load_export(CSV.read_bytes())
    assert generation_gwh_to_mwh(records[0]["generation_gwh"]) == 20250.0
    assert records[0]["generation_gwh"] == 20.25
    # Input contract: docs/data/irena_offshore_wind.md, "Input contract".
    assert generation_gwh_to_mwh(records[1]["generation_gwh"]) is None


@pytest.mark.parametrize("generation,expected", [(0.125, 125.0), (0.0, 0.0)])
def test_generation_conversion(generation, expected):
    """Hand calculation: 0.125 * (10**9 / 10**6) = 125; 0 * ratio = 0.

    NIST SP 330 (2019), section 3, table 7 (SI prefixes):
    https://www.nist.gov/pml/special-publication-330/sp-330-section-3
    Zero is valid under the repository input contract, not missing data.
    """
    assert generation_gwh_to_mwh(generation) == expected


def test_generation_conversion_missing():
    """Blank stays unavailable per the repository's documented input contract."""
    # docs/data/irena_offshore_wind.md, "Input contract": blank != reported zero.
    assert generation_gwh_to_mwh(None) is None


@pytest.mark.parametrize(
    "generation", [-1.0, float("nan"), float("inf"), -float("inf")]
)
def test_generation_conversion_rejects_invalid_measurements(generation):
    """Reject violations of the repository's finite, nonnegative input contract."""
    # docs/data/irena_offshore_wind.md, "Input contract"; -1 is authored input.
    with pytest.raises(ValueError, match="finite and nonnegative"):
        generation_gwh_to_mwh(generation)


def test_generation_conversion_rejects_overflow():
    """The largest finite float times the SI prefix ratio exceeds float range.

    NIST SP 330 (2019), section 3, table 7 defines a ratio greater than unity;
    Python's sys.float_info.max supplies the runtime's finite upper bound.
    This is a representation check, not an engineering acceptance limit.
    """
    with pytest.raises(ValueError, match="Converted generation must be finite"):
        generation_gwh_to_mwh(sys.float_info.max)


@pytest.mark.parametrize(
    "column,value",
    [
        ("country", ""),
        ("country", " Synthetic Alpha"),
        ("iso_code", "12"),
        ("year", "1959"),
        ("year", "2100"),
        ("year", "2023.5"),
        ("technology", "onshore wind"),
        ("capacity_mw", "-1"),
        ("generation_gwh", "NaN"),
        ("capacity_mw", "inf"),
        ("source_url", ""),
        ("source_url", "file:///synthetic"),
        ("citation", ""),
    ],
)
def test_invalid_values(column, value):
    with pytest.raises(ValueError):
        load_export(changed(column, value))


@pytest.mark.parametrize("header", ["capacity_kw", "Capacity (MW)", ""])
def test_changed_header(header):
    with pytest.raises(ValueError, match="header"):
        load_export(CSV.read_bytes().replace(b"capacity_mw", header.encode(), 1))


def test_duplicate_country_year():
    raw = CSV.read_bytes()
    with pytest.raises(ValueError, match="Duplicate"):
        load_export(raw + raw.splitlines(keepends=True)[1])


def test_country_key_consistency():
    with pytest.raises(ValueError, match="country key"):
        load_export(changed("iso_code", "AAA"))


@pytest.mark.parametrize("raw", [b"", CSV.read_bytes().splitlines()[0] + b"\n"])
def test_empty_table(raw):
    with pytest.raises(ValueError):
        load_export(raw)


def test_extra_cell():
    with pytest.raises(ValueError):
        load_export(CSV.read_bytes().replace(b"10.5,20.25", b"10.5,20.25,extra"))


def test_missing_measurements():
    raw = changed("capacity_mw", "").replace(b",20.25,", b",,")
    with pytest.raises(ValueError, match="measurement"):
        load_export(raw)


def test_manifest_reproduction():
    actual = emit_manifest(CSV.read_bytes(), synthetic=True)
    assert actual == (FIXTURES / "irena_offshore_synthetic.manifest.json").read_bytes()
    assert b'"synthetic": true' in actual


def test_manifest_requires_synthetic_or_provenance():
    with pytest.raises(ValueError, match="provenance"):
        emit_manifest(CSV.read_bytes())


def test_fetch_refuses_without_network():
    with pytest.raises(AccessRefused, match="403"):
        fetch_irena()


def test_iso_code_collision():
    raw = CSV.read_bytes().replace(b"Synthetic Alpha,,", b"Synthetic Alpha,AAA,")
    raw = raw.replace(b"Synthetic Beta,,", b"Synthetic Beta,AAA,")
    with pytest.raises(ValueError, match="country key"):
        load_export(raw)


def test_manifest_real_provenance():
    import hashlib
    import json

    manifest = json.loads(
        emit_manifest(
            CSV.read_bytes(),
            retrieved_at_utc="2026-01-01T00:00:00Z",
            terms_quote="not stated by the source",
            terms_url="https://example.invalid/terms",
        )
    )
    assert manifest["sha256"] == hashlib.sha256(CSV.read_bytes()).hexdigest()
    assert manifest["size_bytes"] == CSV.stat().st_size
    assert manifest["retrieved_at_utc"] == "2026-01-01T00:00:00Z"
    assert manifest["terms"]["quote"] == "not stated by the source"
    assert manifest["retrieval_state"] == "caller supplied"


@pytest.mark.parametrize(
    "time", ["2026-01-01", "2026-01-01T00:00:00+01:00", "9999-01-01T00:00:00Z"]
)
def test_manifest_rejects_non_utc_or_future(time):
    with pytest.raises(ValueError):
        emit_manifest(
            CSV.read_bytes(),
            retrieved_at_utc=time,
            terms_quote="synthetic provenance test",
            terms_url="https://example.invalid/terms",
        )


def test_cli_manifest_and_input_preservation(tmp_path, monkeypatch):
    import sys

    from worldenergydata.energy_mix.__main__ import main

    manifest = tmp_path / "manifest.json"
    output = tmp_path / "tidy.csv"
    before = CSV.read_bytes()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "energy_mix",
            "load",
            "--input",
            str(CSV),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--synthetic",
        ],
    )
    main()
    assert manifest.read_bytes() == emit_manifest(before, synthetic=True)
    assert load_export(output.read_bytes()) == load_export(before)
    assert CSV.read_bytes() == before
    with pytest.raises(FileExistsError):
        main()
    assert manifest.read_bytes() == emit_manifest(before, synthetic=True)


def test_cli_rejects_input_overwrite(monkeypatch):
    import sys

    from worldenergydata.energy_mix.__main__ import main

    before = CSV.read_bytes()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "energy_mix",
            "load",
            "--input",
            str(CSV),
            "--manifest",
            str(CSV),
            "--synthetic",
        ],
    )
    with pytest.raises(SystemExit):
        main()
    assert CSV.read_bytes() == before


def test_country_key_case_consistency():
    raw = CSV.read_bytes().replace(
        b"Synthetic Alpha,,2023", b"synthetic alpha,AAA,2023"
    )
    with pytest.raises(ValueError, match="country key"):
        load_export(raw)


@pytest.mark.parametrize(
    "quote,url",
    [
        (" ", "https://example.invalid/terms"),
        ("fixture terms", "https:"),
        ("fixture terms", "https://user:pass@example.invalid/terms"),
    ],
)
def test_manifest_rejects_unusable_terms(quote, url):
    with pytest.raises(ValueError, match="provenance"):
        emit_manifest(
            CSV.read_bytes(),
            retrieved_at_utc="2026-01-01T00:00:00Z",
            terms_quote=quote,
            terms_url=url,
        )


def test_cli_existing_manifest_creates_no_output(tmp_path, monkeypatch):
    import sys

    from worldenergydata.energy_mix.__main__ import main

    manifest = tmp_path / "existing.json"
    output = tmp_path / "new.csv"
    manifest.write_bytes(b"preserved")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "energy_mix",
            "load",
            "--input",
            str(CSV),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--synthetic",
        ],
    )
    with pytest.raises(FileExistsError):
        main()
    assert manifest.read_bytes() == b"preserved"
    assert not output.exists()
