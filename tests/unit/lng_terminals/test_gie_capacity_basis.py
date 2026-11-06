"""Reject storage inventory as an annual-throughput capacity basis."""

import pytest

from worldenergydata.lng_terminals.collectors.gie_collector import GIECollector


@pytest.fixture
def basis():
    """Synthetic inputs, not a gas-property recommendation; see hand calculation."""
    from worldenergydata.lng_terminals.collectors.gie_collector import GIECapacityBasis

    return GIECapacityBasis(
        days_per_year=360,
        tonnes_per_mcm=700,
        tonnes_per_gwh=70,
        reference="Synthetic hand calculation in test_explicit_capacity_units",
    )


@pytest.mark.parametrize("unit,rate", [("mcm/d", "10"), ("GWh/d", 100)])
def test_explicit_capacity_units(basis, unit, rate):
    """Independent dimensional calculation with deliberately synthetic inputs.

    Volume: 10 mcm/d * 700 t/mcm * 360 d/year = 2,520,000 t/year.
    Energy: 100 GWh/d * 70 t/GWh * 360 d/year = 2,520,000 t/year.
    Both give 2.52 million t/year. Million = 10**6: NIST SP 811 (2008),
    section 4, table 5. No production gas property or annual basis is assumed.
    """
    record = {
        "name": "Synthetic Terminal",
        "country": "GB",
        "maxCapacity": rate,
        "maxCapacityUnit": unit,
    }
    with GIECollector(capacity_basis=basis) as collector:
        terminal = collector.parse_records([record])[0]
    assert terminal.capacity_mtpa == pytest.approx(2.52)
    assert "capacity_mtpa" in terminal.sources[0].fields_sourced
    assert terminal.sources[1].source_name == basis.reference


@pytest.mark.parametrize("unit", [None, "", "MW", "bcm/yr", 12])
def test_unknown_or_missing_unit_retains_identity(basis, unit, caplog):
    """An unknown dimension cannot be converted; no numerical answer is valid."""
    with GIECollector(capacity_basis=basis) as collector:
        terminal = collector.parse_records(
            [
                {
                    "name": "Synthetic Terminal",
                    "country": "GB",
                    "maxCapacity": "10",
                    "maxCapacityUnit": unit,
                }
            ]
        )[0]
    assert terminal.capacity_mtpa is None
    assert terminal.terminal_name == "Synthetic Terminal"
    assert "capacity_mtpa" not in terminal.sources[0].fields_sourced
    assert "NOT_EVALUATED" in caplog.text


@pytest.mark.parametrize("value", ["bad", "NaN", "inf", "-inf", -1, 0, True])
def test_invalid_rate_retains_identity(basis, value, caplog):
    """A throughput rate must be finite and positive (dimensional domain)."""
    with GIECollector(capacity_basis=basis) as collector:
        terminal = collector.parse_records(
            [
                {
                    "name": "Synthetic Terminal",
                    "country": "GB",
                    "maxCapacity": value,
                    "maxCapacityUnit": "mcm/d",
                }
            ]
        )[0]
    assert terminal.capacity_mtpa is None
    assert "NOT_EVALUATED" in caplog.text


@pytest.mark.parametrize("unit", ["mcm/d", "GWh/d"])
def test_conversion_requires_basis(unit, caplog):
    """There is no universal gas-to-LNG mass conversion; omit without inputs."""
    with GIECollector() as collector:
        terminal = collector.parse_records(
            [
                {
                    "name": "Synthetic Terminal",
                    "country": "GB",
                    "maxCapacity": "10",
                    "maxCapacityUnit": unit,
                }
            ]
        )[0]
    assert terminal.capacity_mtpa is None
    assert "NOT_EVALUATED" in caplog.text


def test_documented_dtrs_energy_capacity(basis):
    """GIE manual v007 (2022), section 2.4: dtrs is GWh/d, dtmi is volume.

    Synthetic 100 * 70 * 360 / 1,000,000 = 2.52 MTPA; dtmi must not enter it.
    """
    with GIECollector(capacity_basis=basis) as collector:
        terminal = collector.parse_records(
            [
                {
                    "name": "Synthetic Terminal",
                    "country": "GB",
                    "dtrs": "100",
                    "dtmi": "267.84",
                }
            ]
        )[0]
    assert terminal.capacity_mtpa == pytest.approx(2.52)


def test_invalid_explicit_unit_does_not_fall_back_to_dtrs(basis, caplog):
    """Reject ambiguous explicit capacity rather than silently selecting a field."""
    with GIECollector(capacity_basis=basis) as collector:
        terminal = collector.parse_records(
            [
                {
                    "name": "Synthetic Terminal",
                    "country": "GB",
                    "maxCapacity": "10",
                    "maxCapacityUnit": "unknown",
                    "dtrs": "100",
                }
            ]
        )[0]
    assert terminal.capacity_mtpa is None
    assert "NOT_EVALUATED" in caplog.text


@pytest.mark.parametrize(
    "field,value",
    [
        ("days_per_year", 0),
        ("days_per_year", float("nan")),
        ("tonnes_per_mcm", -1),
        ("tonnes_per_gwh", float("inf")),
        ("reference", ""),
        ("reference", "  "),
    ],
)
def test_invalid_basis_rejected(field, value):
    """Conversion factors must be finite, positive and accompanied by a reference."""
    from worldenergydata.lng_terminals.collectors.gie_collector import GIECapacityBasis

    values = {"days_per_year": 360, "reference": "Synthetic test input"}
    values[field] = value
    with pytest.raises(ValueError):
        GIECapacityBasis(**values)


def test_missing_factor_retains_identity(caplog):
    """An energy factor cannot substitute for the missing volume factor."""
    from worldenergydata.lng_terminals.collectors.gie_collector import GIECapacityBasis

    basis = GIECapacityBasis(
        days_per_year=360, tonnes_per_gwh=70, reference="Synthetic test input"
    )
    with GIECollector(capacity_basis=basis) as collector:
        terminal = collector.parse_records(
            [
                {
                    "name": "Synthetic Terminal",
                    "country": "GB",
                    "maxCapacity": "10",
                    "maxCapacityUnit": "mcm/d",
                }
            ]
        )[0]
    assert terminal.capacity_mtpa is None
    assert "NOT_EVALUATED" in caplog.text


@pytest.mark.parametrize("inventory", ["267.84", 267.84, None])
def test_storage_inventory_is_not_throughput_capacity(inventory):
    """GIE API User Manual v007 (4 October 2022), section 2.4, page 8.

    https://www.gie.eu/transparency-platform/GIE_API_documentation_v007.pdf

    The published dtmi example is 267.84 in thousand cubic metres of LNG.
    Dimensional check: a volume cannot determine mass/time without density and
    a time basis, neither of which is supplied. Expected capacity_mtpa is None.
    String and numeric encodings must give the same missing-throughput result;
    absent inventory is the control. Terminal identity must still be retained.
    """
    record = {"name": "Synthetic Terminal", "country": "GBR"}
    if inventory is not None:
        record["dtmi"] = inventory
    with GIECollector() as collector:
        terminals = collector.parse_records([record])
    assert [terminal.terminal_name for terminal in terminals] == ["Synthetic Terminal"]
    assert terminals[0].capacity_mtpa is None
