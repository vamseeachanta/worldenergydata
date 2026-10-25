"""Synthetic schema examples, not measured emissions.

Schema: Climate TRACE Inventory September 2026, v5.11.0, Data Licensing,
Schema, and Citation Guide, emissions_sources.csv metadata. Tests use no
emission factors, GWP coefficients, or regulatory acceptance limits.
"""

import hashlib

import pytest

from worldenergydata.esg_carbon import read_climate_trace_csv

HEADER = (
    "source_id,source_name,iso3_country,sector,subsector,start_time,end_time,"
    "gas,emissions_quantity,temporal_granularity\n"
)
ROW = (
    "synthetic-1,Synthetic source,USA,fossil-fuel-operations,"
    "oil-and-gas-production-and-transport,2024-01-01 00:00:00,"
    "2024-12-31 23:59:59,co2,12.5,annual\n"
)


def write_inventory(tmp_path, text=HEADER + ROW):
    path = tmp_path / "emissions.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_read_preserves_mass_identity_and_provenance(tmp_path):
    """The supplied synthetic mass is 12.5 tonnes; no conversion is applied."""
    path = write_inventory(tmp_path)
    inventory = read_climate_trace_csv(path, edition="v5.11.0")
    row = inventory.records[0]
    assert row.emissions_quantity == 12.5
    assert row.units == "tonnes"
    assert row.source_id == "synthetic-1"
    assert row.iso3_country == "USA"
    assert row.start_time.isoformat() == "2024-01-01T00:00:00+00:00"
    assert inventory.edition == "v5.11.0"
    assert inventory.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert inventory.source_url == "https://climatetrace.org/data"


@pytest.mark.parametrize("value", ["", "null", "N-A", "N/A"])
def test_missing_mass_remains_unknown(tmp_path, value):
    """Guide emissions_quantity: empty/null/N-A means unavailable, not zero."""
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + ROW.replace(",12.5,", f",{value},")),
        edition="v5.11.0",
    )
    assert inventory.records[0].emissions_quantity is None


def test_reported_zero_is_preserved(tmp_path):
    """Guide emissions_quantity: zero means that gas is not emitted."""
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + ROW.replace(",12.5,", ",0,")),
        edition="v5.11.0",
    )
    assert inventory.records[0].emissions_quantity == 0


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "-1", "unknown"])
def test_invalid_mass_is_rejected(tmp_path, value):
    """This importer covers nonnegative emissions, excluding removal records."""
    with pytest.raises(ValueError, match="row 2.*emissions_quantity"):
        read_climate_trace_csv(
            write_inventory(tmp_path, HEADER + ROW.replace(",12.5,", f",{value},")),
            edition="v5.11.0",
        )


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("USA", "US", "iso3_country"),
        ("synthetic-1", "", "source_id"),
        ("annual", "", "temporal_granularity"),
        (",co2,", ",mystery,", "gas"),
        ("2024-01-01 00:00:00", "not-a-date", "start_time"),
        ("2024-12-31 23:59:59", "2023-01-01 00:00:00", "end_time"),
    ],
)
def test_invalid_metadata_is_rejected(tmp_path, old, new, message):
    with pytest.raises(ValueError, match=message):
        read_climate_trace_csv(
            write_inventory(tmp_path, HEADER + ROW.replace(old, new)),
            edition="v5.11.0",
        )


@pytest.mark.parametrize(
    "text",
    [
        "",
        HEADER.replace("gas,", "unknown,"),
        HEADER.replace("gas,", "gas,gas,"),
        HEADER + ROW.rstrip() + ",extra\n",
        HEADER + ",".join(ROW.split(",")[:-1]) + "\n",
        HEADER + ROW + ROW,
    ],
)
def test_bad_structure_and_duplicate_observations_are_rejected(tmp_path, text):
    with pytest.raises(ValueError):
        read_climate_trace_csv(write_inventory(tmp_path, text), edition="v5.11.0")


def test_empty_edition_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="edition"):
        read_climate_trace_csv(write_inventory(tmp_path), edition=" ")


def test_bom_extra_columns_and_utc_offsets_are_supported(tmp_path):
    text = "\ufeff" + HEADER.rstrip() + ",extra\n"
    text += (
        ROW.rstrip().replace("2024-01-01 00:00:00", "2024-01-01T01:00:00+01:00")
        + ",ignored\n"
    )
    inventory = read_climate_trace_csv(write_inventory(tmp_path, text), edition="x")
    assert inventory.records[0].start_time.isoformat() == "2024-01-01T00:00:00+00:00"


def test_header_only_is_an_empty_inventory(tmp_path):
    inventory = read_climate_trace_csv(write_inventory(tmp_path, HEADER), edition="x")
    assert inventory.records == ()


@pytest.mark.parametrize("gas", ["co2", "ch4", "n2o", "co2e_100gwp", "co2e_20gwp"])
def test_supported_gases_preserve_reported_mass(tmp_path, gas):
    """Guide v5.11.0 gas/confidence metadata: these are separate mass labels."""
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + ROW.replace(",co2,", f",{gas},")),
        edition="x",
    )
    assert inventory.records[0].gas == gas
    assert inventory.records[0].emissions_quantity == 12.5


def test_timezone_equivalent_duplicate_is_rejected(tmp_path):
    rows = ROW + ROW.replace("2024-01-01 00:00:00", "2024-01-01T01:00:00+01:00")
    with pytest.raises(ValueError, match="duplicate"):
        read_climate_trace_csv(write_inventory(tmp_path, HEADER + rows), edition="x")


@pytest.mark.parametrize("time", ["2024-01-01", "2024-12-31 23:59:59"])
def test_date_only_and_zero_duration_are_rejected(tmp_path, time):
    with pytest.raises(ValueError):
        read_climate_trace_csv(
            write_inventory(
                tmp_path, HEADER + ROW.replace("2024-01-01 00:00:00", time)
            ),
            edition="x",
        )


def test_quoted_name_and_utc_suffix_are_supported(tmp_path):
    text = HEADER + ROW.replace("Synthetic source", '"Synthetic, source"').replace(
        "2024-01-01 00:00:00", "2024-01-01T00:00:00Z"
    )
    row = read_climate_trace_csv(write_inventory(tmp_path, text), edition="x").records[
        0
    ]
    assert row.source_name == "Synthetic, source"


def test_conflicting_explicit_units_are_rejected(tmp_path):
    """A future or modified schema cannot silently replace tonnes with kg."""
    text = HEADER.rstrip() + ",emissions_quantity_units\n" + ROW.rstrip() + ",kg\n"
    with pytest.raises(ValueError, match="units"):
        read_climate_trace_csv(write_inventory(tmp_path, text), edition="x")


@pytest.mark.parametrize(
    ("label", "canonical"),
    [("co2e_100yr", "co2e_100gwp"), ("co2e_20yr", "co2e_20gwp")],
)
def test_co2e_aliases_use_the_same_basis_without_converting_mass(
    tmp_path, label, canonical
):
    rows = ROW.replace(",co2,", f",{label},")
    rows += ROW.replace("synthetic-1", "synthetic-2").replace(",co2,", f",{canonical},")
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + rows), edition="x"
    )
    assert {row.gas for row in inventory.records} == {canonical}
    assert inventory.summarize(gas=canonical).total_tonnes == 25.0


@pytest.mark.parametrize("horizon", ["100", "20"])
def test_aliases_cannot_hide_duplicate_observations(tmp_path, horizon):
    rows = ROW.replace(",co2,", f",co2e_{horizon}yr,")
    rows += ROW.replace(",co2,", f",co2e_{horizon}gwp,")
    with pytest.raises(ValueError, match="row 3.*duplicate"):
        read_climate_trace_csv(write_inventory(tmp_path, HEADER + rows), edition="x")


def test_alias_horizons_remain_separate(tmp_path):
    rows = ROW.replace(",co2,", ",co2e_100yr,")
    rows += ROW.replace(",co2,", ",co2e_20yr,")
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + rows), edition="x"
    )
    with pytest.raises(ValueError, match="mixed emissions basis"):
        inventory.summarize()


@pytest.mark.parametrize("units", ["", "   ", "tonnes"])
def test_optional_units_accept_blank_or_tonnes(tmp_path, units):
    text = HEADER.rstrip() + ",emissions_quantity_units\n"
    text += ROW.rstrip() + f",{units}\n"
    inventory = read_climate_trace_csv(write_inventory(tmp_path, text), edition="x")
    assert inventory.records[0].units == "tonnes"
    assert inventory.records[0].emissions_quantity == 12.5


@pytest.mark.parametrize(
    ("text", "line"),
    [
        ('"source_id,source_name', 1),
        (HEADER + ROW.replace("Synthetic source", '"Synthetic source'), 2),
        (HEADER + ROW.replace("Synthetic source", '"Synthetic\nsource'), 3),
    ],
)
def test_malformed_csv_has_line_context(tmp_path, text, line):
    with pytest.raises(ValueError, match=rf"^CSV row {line}: malformed CSV$"):
        read_climate_trace_csv(write_inventory(tmp_path, text), edition="x")


@pytest.mark.parametrize(
    ("text", "line", "message"),
    [
        (HEADER + "\n" + ROW.replace(",12.5,", ",-1,"), 3, "nonnegative"),
        (HEADER + "\n" + ROW + ROW, 4, "duplicate"),
        (
            HEADER + ROW.replace("Synthetic source", '"Synthetic\nsource"') + ROW,
            4,
            "duplicate",
        ),
        (
            HEADER
            + ROW.replace("Synthetic source", '"Synthetic\nsource"')
            + ROW.replace(",12.5,", ",-1,"),
            4,
            "nonnegative",
        ),
    ],
)
def test_validation_errors_use_physical_line_context(tmp_path, text, line, message):
    with pytest.raises(ValueError, match=rf"CSV row {line}:.*{message}"):
        read_climate_trace_csv(write_inventory(tmp_path, text), edition="x")


@pytest.mark.parametrize(
    "granularity", ["month", "day", "hour", "week", "annual", "other"]
)
def test_supported_temporal_granularities_preserve_basis(tmp_path, granularity):
    """Climate TRACE Data Schema, revision 61dbefb8, lists six resolutions."""
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + ROW.replace("annual", granularity)),
        edition="v5.11.0",
    )
    assert inventory.records[0].temporal_granularity == granularity
    summary = inventory.summarize()
    assert summary.basis.temporal_granularity == granularity
    assert summary.status == "COMPLETE"
    assert summary.total_tonnes == 12.5


@pytest.mark.parametrize(
    "granularity",
    ["annuall", "monthly", "daily", "yearly", "Annual", "ANNUAL", "unknown", "0"],
)
def test_unsupported_temporal_granularity_is_rejected(tmp_path, granularity):
    with pytest.raises(
        ValueError, match=r"^CSV row 2: temporal_granularity must be supported$"
    ):
        read_climate_trace_csv(
            write_inventory(tmp_path, HEADER + ROW.replace("annual", granularity)),
            edition="v5.11.0",
        )


def test_invalid_later_granularity_aborts_import_with_row_context(tmp_path):
    rows = ROW + ROW.replace("synthetic-1", "synthetic-2").replace("annual", "annuall")
    with pytest.raises(
        ValueError, match=r"^CSV row 3: temporal_granularity must be supported$"
    ):
        read_climate_trace_csv(
            write_inventory(tmp_path, HEADER + rows), edition="v5.11.0"
        )
