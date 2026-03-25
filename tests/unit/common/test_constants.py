"""
Tests for worldenergydata.common.constants module.

Tests cover:
- EnergyUnits enum has all units
- UNIT_CONVERSIONS dictionary is complete
- convert_units() works correctly
- Helper functions (bbl_to_boe, mcf_to_boe, etc.)
"""

import pytest


class TestEnergyUnits:
    """Tests for EnergyUnits enum."""

    def test_energy_units_exist(self):
        """Test all energy units are defined."""
        from worldenergydata.common.constants import EnergyUnits

        energy_units = [
            EnergyUnits.BTU,
            EnergyUnits.MMBTU,
            EnergyUnits.THERM,
            EnergyUnits.GJ,
            EnergyUnits.MWH,
            EnergyUnits.KWH,
            EnergyUnits.TOE,
            EnergyUnits.BOE,
        ]

        for unit in energy_units:
            assert unit is not None

    def test_oil_volume_units_exist(self):
        """Test all oil volume units are defined."""
        from worldenergydata.common.constants import EnergyUnits

        oil_units = [
            EnergyUnits.BARREL,
            EnergyUnits.BARREL_OIL,
            EnergyUnits.GALLON,
            EnergyUnits.LITER,
            EnergyUnits.CUBIC_METER,
        ]

        for unit in oil_units:
            assert unit is not None

    def test_gas_volume_units_exist(self):
        """Test all gas volume units are defined."""
        from worldenergydata.common.constants import EnergyUnits

        gas_units = [
            EnergyUnits.MCF,
            EnergyUnits.MMCF,
            EnergyUnits.BCF,
            EnergyUnits.TCF,
            EnergyUnits.SCF,
        ]

        for unit in gas_units:
            assert unit is not None

    def test_mass_units_exist(self):
        """Test all mass units are defined."""
        from worldenergydata.common.constants import EnergyUnits

        mass_units = [
            EnergyUnits.TONNE,
            EnergyUnits.SHORT_TON,
            EnergyUnits.LONG_TON,
            EnergyUnits.KILOGRAM,
            EnergyUnits.POUND,
        ]

        for unit in mass_units:
            assert unit is not None

    def test_enum_values_are_strings(self):
        """Test EnergyUnits values are strings."""
        from worldenergydata.common.constants import EnergyUnits

        for unit in EnergyUnits:
            assert isinstance(unit.value, str)

    def test_enum_inherits_from_str(self):
        """Test EnergyUnits inherits from str for easy string usage."""
        from worldenergydata.common.constants import EnergyUnits

        assert isinstance(EnergyUnits.BTU, str)
        assert EnergyUnits.BTU == "BTU"


class TestUnitConversions:
    """Tests for UNIT_CONVERSIONS dictionary."""

    def test_btu_conversions_exist(self):
        """Test BTU has conversions to other energy units."""
        from worldenergydata.common.constants import UNIT_CONVERSIONS, EnergyUnits

        assert EnergyUnits.BTU in UNIT_CONVERSIONS
        btu_conversions = UNIT_CONVERSIONS[EnergyUnits.BTU]

        assert EnergyUnits.MMBTU in btu_conversions
        assert EnergyUnits.THERM in btu_conversions
        assert EnergyUnits.GJ in btu_conversions
        assert EnergyUnits.MWH in btu_conversions

    def test_identity_conversions(self):
        """Test each unit converts to itself with factor 1.0."""
        from worldenergydata.common.constants import UNIT_CONVERSIONS

        for unit, conversions in UNIT_CONVERSIONS.items():
            if unit in conversions:
                assert conversions[unit] == 1.0

    def test_mmbtu_conversions(self):
        """Test MMBTU conversions are correct."""
        from worldenergydata.common.constants import UNIT_CONVERSIONS, EnergyUnits

        mmbtu = UNIT_CONVERSIONS[EnergyUnits.MMBTU]

        assert mmbtu[EnergyUnits.BTU] == 1e6
        assert mmbtu[EnergyUnits.THERM] == 10.0

    def test_barrel_conversions(self):
        """Test barrel conversions are correct."""
        from worldenergydata.common.constants import UNIT_CONVERSIONS, EnergyUnits

        barrel = UNIT_CONVERSIONS[EnergyUnits.BARREL]

        assert barrel[EnergyUnits.GALLON] == 42.0  # 42 gallons per barrel
        assert barrel[EnergyUnits.LITER] == pytest.approx(158.987, rel=0.01)

    def test_mcf_conversions(self):
        """Test MCF conversions are correct."""
        from worldenergydata.common.constants import UNIT_CONVERSIONS, EnergyUnits

        mcf = UNIT_CONVERSIONS[EnergyUnits.MCF]

        assert mcf[EnergyUnits.SCF] == 1000.0
        assert mcf[EnergyUnits.MMCF] == 0.001
        assert mcf[EnergyUnits.MMBTU] == pytest.approx(1.028, rel=0.01)

    def test_boe_conversions(self):
        """Test BOE conversions are correct."""
        from worldenergydata.common.constants import UNIT_CONVERSIONS, EnergyUnits

        boe = UNIT_CONVERSIONS[EnergyUnits.BOE]

        assert boe[EnergyUnits.BARREL_OIL] == 1.0
        assert boe[EnergyUnits.MCF] == pytest.approx(5.64, rel=0.01)
        assert boe[EnergyUnits.MMBTU] == pytest.approx(5.8, rel=0.01)

    def test_mass_conversions(self):
        """Test mass conversions are correct."""
        from worldenergydata.common.constants import UNIT_CONVERSIONS, EnergyUnits

        tonne = UNIT_CONVERSIONS[EnergyUnits.TONNE]

        assert tonne[EnergyUnits.KILOGRAM] == 1000.0
        assert tonne[EnergyUnits.POUND] == pytest.approx(2204.62, rel=0.01)


class TestConvertUnits:
    """Tests for convert_units() function."""

    def test_same_unit_returns_value(self):
        """Test converting to same unit returns original value."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        result = convert_units(100.0, EnergyUnits.BTU, EnergyUnits.BTU)

        assert result == 100.0

    def test_btu_to_mmbtu(self):
        """Test BTU to MMBTU conversion."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        result = convert_units(1_000_000, EnergyUnits.BTU, EnergyUnits.MMBTU)

        assert result == 1.0

    def test_mmbtu_to_btu(self):
        """Test MMBTU to BTU conversion."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        result = convert_units(1.0, EnergyUnits.MMBTU, EnergyUnits.BTU)

        assert result == 1_000_000

    def test_barrel_to_gallon(self):
        """Test barrel to gallon conversion."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        result = convert_units(1.0, EnergyUnits.BARREL, EnergyUnits.GALLON)

        assert result == 42.0

    def test_mcf_to_scf(self):
        """Test MCF to SCF conversion."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        result = convert_units(1.0, EnergyUnits.MCF, EnergyUnits.SCF)

        assert result == 1000.0

    def test_boe_to_mcf(self):
        """Test BOE to MCF conversion."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        result = convert_units(1.0, EnergyUnits.BOE, EnergyUnits.MCF)

        assert result == pytest.approx(5.64, rel=0.01)

    def test_string_input_units(self):
        """Test convert_units accepts string unit names."""
        from worldenergydata.common.constants import convert_units

        result = convert_units(1.0, "MMBTU", "BTU")

        assert result == 1_000_000

    def test_reverse_conversion_calculated(self):
        """Test reverse conversion is calculated when direct not available."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        # GALLON -> BARREL (reverse of BARREL -> GALLON)
        result = convert_units(42.0, EnergyUnits.GALLON, EnergyUnits.BARREL)

        assert result == pytest.approx(1.0, rel=0.01)

    def test_invalid_conversion_raises(self):
        """Test invalid conversion raises ValueError."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        with pytest.raises(ValueError) as exc_info:
            # POUND to MWH has no conversion path
            convert_units(1.0, EnergyUnits.POUND, EnergyUnits.MWH)

        assert "No conversion available" in str(exc_info.value)

    def test_invalid_string_unit_raises(self):
        """Test invalid string unit raises ValueError."""
        from worldenergydata.common.constants import convert_units

        with pytest.raises(ValueError):
            convert_units(1.0, "INVALID_UNIT", "BTU")


class TestGetConversionFactor:
    """Tests for get_conversion_factor() function."""

    def test_returns_conversion_factor(self):
        """Test get_conversion_factor returns correct factor."""
        from worldenergydata.common.constants import get_conversion_factor, EnergyUnits

        factor = get_conversion_factor(EnergyUnits.MMBTU, EnergyUnits.BTU)

        assert factor == 1_000_000

    def test_same_unit_returns_one(self):
        """Test conversion factor for same unit is 1.0."""
        from worldenergydata.common.constants import get_conversion_factor, EnergyUnits

        factor = get_conversion_factor(EnergyUnits.BTU, EnergyUnits.BTU)

        assert factor == 1.0

    def test_string_units(self):
        """Test get_conversion_factor accepts string units."""
        from worldenergydata.common.constants import get_conversion_factor

        factor = get_conversion_factor("MCF", "SCF")

        assert factor == 1000.0


class TestDataConstants:
    """Tests for DataConstants class."""

    def test_api_patterns(self):
        """Test API number patterns are valid regex."""
        import re
        from worldenergydata.common.constants import DataConstants

        assert re.match(DataConstants.API_10_PATTERN, "1234567890")
        assert re.match(DataConstants.API_12_PATTERN, "123456789012")
        assert re.match(DataConstants.API_14_PATTERN, "12345678901234")

        assert not re.match(DataConstants.API_10_PATTERN, "12345")
        assert not re.match(DataConstants.API_12_PATTERN, "1234567890")

    def test_date_formats(self):
        """Test date format strings are valid."""
        from datetime import datetime
        from worldenergydata.common.constants import DataConstants

        assert datetime.strptime("202312", DataConstants.DATE_FORMAT_YYYYMM)
        assert datetime.strptime("20231215", DataConstants.DATE_FORMAT_YYYYMMDD)
        assert datetime.strptime("2023-12-15", DataConstants.DATE_FORMAT_ISO)
        assert datetime.strptime("12/15/2023", DataConstants.DATE_FORMAT_US)

    def test_coordinate_systems(self):
        """Test coordinate system EPSG codes are defined."""
        from worldenergydata.common.constants import DataConstants

        assert DataConstants.NAD27_EPSG == 4267
        assert DataConstants.NAD83_EPSG == 4269
        assert DataConstants.WGS84_EPSG == 4326

    def test_ocs_areas(self):
        """Test OCS area codes are defined."""
        from worldenergydata.common.constants import DataConstants

        assert "GOM" in DataConstants.OCS_AREAS
        assert "PAC" in DataConstants.OCS_AREAS
        assert DataConstants.OCS_AREAS["GOM"] == "Gulf of Mexico"

    def test_well_status_codes(self):
        """Test well status code lists are defined."""
        from worldenergydata.common.constants import DataConstants

        assert "ACTIVE" in DataConstants.WELL_STATUS_ACTIVE
        assert "PRODUCING" in DataConstants.WELL_STATUS_ACTIVE
        assert "SHUT-IN" in DataConstants.WELL_STATUS_INACTIVE
        assert "PLUGGED" in DataConstants.WELL_STATUS_PLUGGED
        assert "ABANDONED" in DataConstants.WELL_STATUS_ABANDONED

    def test_production_thresholds(self):
        """Test production thresholds are reasonable."""
        from worldenergydata.common.constants import DataConstants

        assert DataConstants.MAX_REASONABLE_OIL_BBL_DAY == 100000
        assert DataConstants.MAX_REASONABLE_GAS_MCF_DAY == 500000
        assert DataConstants.MAX_REASONABLE_WATER_BBL_DAY == 500000

    def test_financial_constants(self):
        """Test financial constants are defined."""
        from worldenergydata.common.constants import DataConstants

        assert DataConstants.DEFAULT_DISCOUNT_RATE == 0.10
        assert DataConstants.DEFAULT_ROYALTY_RATE == 0.125
        assert DataConstants.DEFAULT_SEVERANCE_TAX == 0.05


class TestHelperFunctions:
    """Tests for helper conversion functions."""

    def test_bbl_to_boe(self):
        """Test bbl_to_boe returns 1:1 for oil barrels."""
        from worldenergydata.common.constants import bbl_to_boe

        result = bbl_to_boe(100.0)

        assert result == 100.0

    def test_mcf_to_boe(self):
        """Test mcf_to_boe conversion."""
        from worldenergydata.common.constants import mcf_to_boe

        # 5.64 MCF = 1 BOE, so 564 MCF = 100 BOE
        result = mcf_to_boe(5.64)

        assert result == pytest.approx(1.0, rel=0.01)

    def test_mcf_to_boe_large_value(self):
        """Test mcf_to_boe with larger value."""
        from worldenergydata.common.constants import mcf_to_boe

        result = mcf_to_boe(1000.0)

        # 1000 MCF / 5.64 MCF per BOE = ~177 BOE
        assert result == pytest.approx(177.0, rel=0.01)

    def test_boe_to_mcf(self):
        """Test boe_to_mcf conversion."""
        from worldenergydata.common.constants import boe_to_mcf

        result = boe_to_mcf(1.0)

        assert result == pytest.approx(5.64, rel=0.01)

    def test_boe_to_mcf_large_value(self):
        """Test boe_to_mcf with larger value."""
        from worldenergydata.common.constants import boe_to_mcf

        result = boe_to_mcf(100.0)

        assert result == pytest.approx(564.0, rel=0.01)

    def test_boe_to_mmbtu(self):
        """Test boe_to_mmbtu conversion."""
        from worldenergydata.common.constants import boe_to_mmbtu

        result = boe_to_mmbtu(1.0)

        assert result == pytest.approx(5.8, rel=0.01)

    def test_boe_to_mmbtu_large_value(self):
        """Test boe_to_mmbtu with larger value."""
        from worldenergydata.common.constants import boe_to_mmbtu

        result = boe_to_mmbtu(100.0)

        assert result == pytest.approx(580.0, rel=0.01)


class TestConversionConsistency:
    """Tests for conversion consistency and round-trip accuracy."""

    def test_round_trip_btu_mmbtu(self):
        """Test BTU -> MMBTU -> BTU round trip."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        original = 5_000_000
        mmbtu = convert_units(original, EnergyUnits.BTU, EnergyUnits.MMBTU)
        back = convert_units(mmbtu, EnergyUnits.MMBTU, EnergyUnits.BTU)

        assert back == pytest.approx(original, rel=0.001)

    def test_round_trip_barrel_gallon(self):
        """Test BARREL -> GALLON -> BARREL round trip."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        original = 10.0
        gallon = convert_units(original, EnergyUnits.BARREL, EnergyUnits.GALLON)
        back = convert_units(gallon, EnergyUnits.GALLON, EnergyUnits.BARREL)

        assert back == pytest.approx(original, rel=0.01)

    def test_round_trip_mcf_scf(self):
        """Test MCF -> SCF -> MCF round trip."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        original = 50.0
        scf = convert_units(original, EnergyUnits.MCF, EnergyUnits.SCF)
        back = convert_units(scf, EnergyUnits.SCF, EnergyUnits.MCF)

        assert back == pytest.approx(original, rel=0.001)

    def test_chain_conversion_consistency(self):
        """Test chained conversions maintain consistency."""
        from worldenergydata.common.constants import convert_units, EnergyUnits

        # BOE -> MCF -> BOE should be consistent
        original_boe = 10.0
        mcf = convert_units(original_boe, EnergyUnits.BOE, EnergyUnits.MCF)
        back_boe = convert_units(mcf, EnergyUnits.MCF, EnergyUnits.BOE)

        assert back_boe == pytest.approx(original_boe, rel=0.01)
