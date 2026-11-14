"""MSIV ingestion contract tests using synthetic, dimensioned input.

All numbers below are fixture inputs, not specifications for a real vessel.
Expected particulars are identity mappings in the stated units: 120 m ->
120 m, 2,400 square metres -> 2400 square metres, and 900 tonnes -> 900 tonnes.
No engineering coefficient or acceptance tolerance is used. The seven-digit
identifier exercises BaseVesselSchema's format rule, not registry verification.
"""

from __future__ import annotations

import pytest

from worldenergydata.vessel_fleet.collectors import acma_msiv_collector as collector


def matrix(**overrides):
    """Build one synthetic source row; each key states its source unit."""
    row = {
        "Vessel Name": "Fixture A",
        "Type": "MSIV",
        "LOA (m)": "120",
        "Beam (m)": "24",
        "Draft (m)": "6",
        "Main Crane (MT)": "900",
        "IMO Number": "1234567",
        "Deck Area (m2)": "2,400",
        "Deck Load Capacity (MT)": "1,500",
        "Source URL": "https://example.org/brochure.pdf",
    }
    row.update(overrides)
    return "\n".join(
        (
            "| " + " | ".join(row) + " |",
            "| " + " | ".join("---" for _ in row) + " |",
            "| " + " | ".join(row.values()) + " |",
        )
    )


def test_maps_identity_deck_and_source():
    """Identity mapping: 2,400 -> 2400 m2; 1,500 -> 1500 t."""
    (record,) = collector.parse_msiv_matrix(matrix())
    assert record["IMO_NUMBER"] == "1234567"
    assert record["DECK_AREA_M2"] == 2400.0
    assert record["DECK_LOAD_CAPACITY_T"] == 1500.0
    assert record["DATA_SOURCE_URL"] == "https://example.org/brochure.pdf"
    assert record["VESSEL_CATEGORY"] == "construction"


def test_ignores_table_with_only_substring_header_matches():
    """A budget heading contains spec words but is not a particulars column."""
    decoy = matrix().replace("LOA (m)", "LOA budget")
    records = collector.parse_msiv_matrix(decoy + "\n\n" + matrix())
    assert len(records) == 1
    assert records[0]["LOA_M"] == 120.0


def test_requires_markdown_separator():
    lines = matrix().splitlines()
    assert collector.parse_msiv_matrix("\n".join((lines[0], lines[2]))) == []


def test_stops_at_adjacent_table_header():
    """The next header is metadata, not a second vessel record."""
    assert len(collector.parse_msiv_matrix(matrix() + "\n" + matrix())) == 1


def test_duplicate_columns_are_not_silently_overwritten():
    text = matrix().replace("IMO Number", "Vessel Name")
    assert collector.parse_msiv_matrix(text) == []


def test_header_whitespace_and_superscript_area():
    text = matrix().replace("Deck Area (m2)", " Deck   Area (m²) ")
    (record,) = collector.parse_msiv_matrix(text)
    assert record["DECK_AREA_M2"] == 2400.0


@pytest.mark.parametrize("value", ["", "-", "N/A"])
def test_missing_optional_identity_stays_unknown(value):
    (record,) = collector.parse_msiv_matrix(matrix(**{"IMO Number": value}))
    assert record["IMO_NUMBER"] is None


def test_explicit_source_directory_wins_over_environment(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "vessel-specifications-matrix.md").write_text(matrix(), encoding="utf-8")
    monkeypatch.setenv(collector.ACMA_ENV_VAR, str(tmp_path / "unused"))
    (record,) = collector.collect_msiv_vessels(source)
    assert record["DECK_AREA_M2"] == 2400.0


@pytest.mark.parametrize(
    "field,value",
    [
        ("IMO Number", "not-an-identifier"),
        ("LOA (m)", "-120"),
        ("Beam (m)", "NaN"),
        ("Draft (m)", "infinity"),
        ("Main Crane (MT)", "unreadable"),
        ("Deck Area (m2)", "-2400"),
        ("Deck Load Capacity (MT)", "nan"),
        ("Accommodation", "12.5"),
        ("Accommodation", "-12"),
        ("DP Class", "DP 2.5"),
        ("DP Class", "DP-2"),
        ("Vessel Name", "''"),
    ],
)
def test_invalid_row_rejected_without_losing_next_row(field, value, caplog):
    """Reject syntax/non-finite values and violations of schema sign rules.

    The negative values negate the fixture inputs; 12.5 is not an integer
    headcount. No engineering limit is inferred from these invalid examples.
    """
    valid = (
        matrix(**{field: ""}) if field in {"Accommodation", "DP Class"} else matrix()
    )
    text = matrix(**{field: value}) + "\n" + valid.splitlines()[-1]
    (record,) = collector.parse_msiv_matrix(text)
    assert record["VESSEL_NAME"] == "Fixture A"
    assert "invalid MSIV particulars" in caplog.text
    assert value not in caplog.text


@pytest.mark.parametrize(
    "field,value",
    [
        ("Deck Load Capacity (MT)", "1500 kips"),
        ("Deck Load Capacity (MT)", "1,5,00"),
        ("Deck Load Capacity (MT)", "1500 m"),
        ("Deck Area (m2)", "2400 m"),
        ("Deck Area (m2)", "2400 t"),
        ("Deck Area (m2)", "2,4,00"),
        ("Accommodation", "12 m"),
        ("Accommodation", "12 t"),
        ("Accommodation", "1,2"),
        ("LOA (m)", "120 ft"),
        ("Beam (m)", "2,4"),
        ("Main Crane (MT)", "2x900 kips"),
        ("Draft (m)", "6 ft/12"),
        ("Draft (m)", "6/12 ft"),
        ("Draft (m)", "6/unreadable"),
    ],
)
def test_rejects_incompatible_units_and_malformed_numbers(field, value, caplog):
    """Reject whole cells before unit stripping or comma removal can hide errors."""
    valid = matrix(**{field: ""}) if field == "Accommodation" else matrix()
    text = matrix(**{field: value}) + "\n" + valid.splitlines()[-1]
    (record,) = collector.parse_msiv_matrix(text)
    assert record["VESSEL_NAME"] == "Fixture A"
    assert "invalid MSIV particulars" in caplog.text
    assert value not in caplog.text


@pytest.mark.parametrize(
    "field,value,key,expected",
    [
        ("LOA (m)", "120 m", "LOA_M", 120.0),
        ("Beam (m)", "24 metres", "BEAM_M", 24.0),
        ("Deck Area (m2)", "2,400 m2", "DECK_AREA_M2", 2400.0),
        ("Deck Area (m2)", "2400 m²", "DECK_AREA_M2", 2400.0),
        ("Deck Load Capacity (MT)", "1,500 MT", "DECK_LOAD_CAPACITY_T", 1500.0),
        ("Deck Load Capacity (MT)", "1500 tonnes", "DECK_LOAD_CAPACITY_T", 1500.0),
        ("Accommodation", "12.0", "QUARTERS_CAPACITY", 12),
        ("Accommodation", "0", "QUARTERS_CAPACITY", 0),
        ("Main Crane (MT)", "2×900 t", "MAIN_CRANE_CAPACITY_T", 900.0),
        ("Main Crane (MT)", "2x900 MT", "MAIN_CRANE_CAPACITY_T", 900.0),
        ("Draft (m)", "6/12", "DRAFT_M", 6.0),
        ("Draft (m)", "6 m / 12 m", "DRAFT_M", 6.0),
    ],
)
def test_accepts_compatible_units_and_source_conventions(field, value, key, expected):
    """Unit suffixes are identity mappings; multiplicity and paired draft remain."""
    (record,) = collector.parse_msiv_matrix(matrix(**{field: value}))
    assert record[key] == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "-",
        "--",
        "---",
        "n/a",
        "na",
        "nil",
        "none",
        "tbd",
        "tba",
        "unknown",
        "varies",
        " NoNe ",
    ],
)
def test_missing_optional_crane_preserves_row(value):
    """Shared numeric absence markers leave the optional value unknown."""
    (record,) = collector.parse_msiv_matrix(matrix(**{"Aux Crane (MT)": value}))
    assert record["AUX_CRANE_CAPACITY_T"] is None
    assert record["MAIN_CRANE_CAPACITY_T"] == 900.0


@pytest.mark.parametrize(
    "value",
    [
        "brochure.pdf",
        "file:///private/brochure.pdf",
        "https://example.org/brochure.pdf?token=private-marker",
        "[brochure](https://example.org/brochure.pdf)",
    ],
)
def test_only_plain_public_source_urls_accepted(value, caplog):
    """Source URLs must not publish local file references or query values."""
    assert collector.parse_msiv_matrix(matrix(**{"Source URL": value})) == []
    assert value not in caplog.text


def test_blank_name_and_ragged_rows_are_reported(caplog):
    text = matrix(**{"Vessel Name": ""}) + "\n| incomplete |"
    assert collector.parse_msiv_matrix(text) == []
    assert "invalid MSIV particulars" in caplog.text
    assert "column count" in caplog.text


def test_private_columns_are_never_mapped():
    text = matrix(Cost="private-marker", Recommendation="private-marker")
    (record,) = collector.parse_msiv_matrix(text)
    assert "private-marker" not in repr(record)
    assert "Cost" not in record


def test_related_markdown_loader_uses_the_same_table_header(tmp_path):
    """The shared table reader must not pair valid rows with decoy headings."""
    from worldenergydata.vessel_fleet.loaders.mnt_ace_fleet_loader import (
        parse_msiv_markdown,
    )

    decoy = matrix().replace("LOA (m)", "LOA budget")
    source = tmp_path / "matrix.md"
    source.write_text(decoy + "\n\n" + matrix(), encoding="utf-8")
    (record,) = parse_msiv_markdown(source)
    assert record["LOA_M"] == 120.0


@pytest.fixture
def ingestion_script():
    """Load the existing command without executing its command-line entrypoint."""
    import importlib.util
    from pathlib import Path

    script = (
        Path(__file__).resolve().parents[3]
        / "scripts/vessel_fleet/ingest_offrepo_construction_vessels.py"
    )
    spec = importlib.util.spec_from_file_location("msiv_ingestion_command", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_ingestion_inputs(tmp_path):
    """Two existing rows plus three incoming rows give three unique identities.

    Hand calculation: Fixture A matches by normalized name, Fixture B matches
    by IMO despite its changed name, and Fixture C is new: 2 + 3 - 2 = 3.
    The incoming deck area is 2400 m2; the curated crane capacity remains
    1000 t because 'manual' has higher priority than the brochure source in
    dedup/deduplicator.py. All numbers are synthetic fixture inputs.
    """
    data = tmp_path / "data"
    curated = data / "curated"
    curated.mkdir(parents=True)
    csv_path = curated / "construction_vessels.csv"
    csv_path.write_text(
        "VESSEL_NAME,IMO_NUMBER,DATA_SOURCE,MAIN_CRANE_CAPACITY_T\n"
        "FIXTURE A,7654321,manual,1000\n"
        "Fixture B,2345678,manual,\n",
        encoding="utf-8",
    )
    source = tmp_path / "source"
    source.mkdir()
    rows = [
        matrix(),
        matrix(**{"Vessel Name": "Fixture Renamed", "IMO Number": "2345678"}),
        matrix(**{"Vessel Name": "Fixture C", "IMO Number": "3456789"}),
    ]
    text = rows[0] + "\n" + "\n".join(row.splitlines()[-1] for row in rows[1:])
    (source / "vessel-specifications-matrix.md").write_text(text, encoding="utf-8")
    return data, source


def test_command_fuses_and_round_trips_curated_outputs(
    ingestion_script, tmp_path, monkeypatch
):
    """Exercise the hand-calculated merge in write_ingestion_inputs end to end."""
    import pandas as pd

    data, source = write_ingestion_inputs(tmp_path)
    monkeypatch.delenv("FRONTIER_VESSEL_FLEET_DIR", raising=False)
    monkeypatch.setenv(collector.ACMA_ENV_VAR, str(tmp_path / "unused"))
    monkeypatch.setattr(
        "sys.argv", ["ingest", "--data-dir", str(data), "--msiv-dir", str(source)]
    )
    assert ingestion_script.main() == 0
    parquet_path = data / "curated/construction_vessels.parquet"
    csv_path = data / "curated/construction_vessels.csv"
    parquet = pd.read_parquet(parquet_path)
    csv = pd.read_csv(csv_path, dtype={"IMO_NUMBER": str})
    assert len(parquet) == len(csv) == 3
    for table in (parquet, csv):
        indexed = table.set_index("IMO_NUMBER")
        assert indexed.loc["7654321", "MAIN_CRANE_CAPACITY_T"] == 1000.0
        assert indexed.loc["7654321", "DECK_AREA_M2"] == 2400.0
        assert indexed.loc["3456789", "DATA_SOURCE"] == collector.DATA_SOURCE_MSIV
        assert (
            indexed.loc["3456789", "DATA_SOURCE_URL"]
            == "https://example.org/brochure.pdf"
        )
        assert set(table["VESSEL_CATEGORY"]) == {"construction"}
    first = csv_path.read_bytes()
    assert ingestion_script.main() == 0
    assert csv_path.read_bytes() == first


def test_command_dry_run_preserves_existing_outputs(
    ingestion_script, tmp_path, monkeypatch
):
    data, source = write_ingestion_inputs(tmp_path)
    csv_path = data / "curated/construction_vessels.csv"
    original = csv_path.read_bytes()
    monkeypatch.delenv("FRONTIER_VESSEL_FLEET_DIR", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["ingest", "--data-dir", str(data), "--msiv-dir", str(source), "--dry-run"],
    )
    assert ingestion_script.main() == 0
    assert csv_path.read_bytes() == original
    assert not (data / "curated/construction_vessels.parquet").exists()


def test_default_output_uses_packaged_curated_data(ingestion_script, monkeypatch):
    """No writes: capture the default CSV path before any source is loaded."""
    from pathlib import Path

    def capture(path):
        expected = Path(collector.__file__).resolve().parent.parent / "_data/curated"
        assert path == expected / "construction_vessels.csv"
        raise RuntimeError("default path captured")

    monkeypatch.setattr(ingestion_script, "_load_curated_csv", capture)
    monkeypatch.setattr("sys.argv", ["ingest", "--dry-run"])
    with pytest.raises(RuntimeError, match="default path captured"):
        ingestion_script.main()
