"""Tests for worldenergydata.common.units — global unit conversion registry.

TDD: Tests written before implementation (WRK-259).
"""

from __future__ import annotations

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# OilUnits
# ---------------------------------------------------------------------------


class TestOilUnits:
    """Tests for OilUnits class constants."""

    def test_sm3_to_bbl_value(self):
        from worldenergydata.common.units import OilUnits

        assert OilUnits.SM3_TO_BBL == pytest.approx(6.2898, rel=1e-4)

    def test_tonne_to_bbl_value(self):
        from worldenergydata.common.units import OilUnits

        assert OilUnits.TONNE_TO_BBL == pytest.approx(7.33, rel=1e-4)

    def test_bbl_to_sm3_is_inverse_of_sm3_to_bbl(self):
        from worldenergydata.common.units import OilUnits

        assert OilUnits.BBL_TO_SM3 == pytest.approx(1.0 / OilUnits.SM3_TO_BBL, rel=1e-4)

    def test_bbl_to_tonne_is_inverse_of_tonne_to_bbl(self):
        from worldenergydata.common.units import OilUnits

        assert OilUnits.BBL_TO_TONNE == pytest.approx(
            1.0 / OilUnits.TONNE_TO_BBL, rel=1e-4
        )

    def test_m3_to_bbl_equals_sm3_to_bbl(self):
        from worldenergydata.common.units import OilUnits

        assert OilUnits.M3_TO_BBL == OilUnits.SM3_TO_BBL


# ---------------------------------------------------------------------------
# GasUnits
# ---------------------------------------------------------------------------


class TestGasUnits:
    """Tests for GasUnits class constants."""

    def test_sm3_to_scf_value(self):
        from worldenergydata.common.units import GasUnits

        assert GasUnits.SM3_TO_SCF == pytest.approx(35.3147, rel=1e-4)

    def test_sm3_to_mmscf_is_sm3_to_scf_times_1e_minus6(self):
        from worldenergydata.common.units import GasUnits

        assert GasUnits.SM3_TO_MMSCF == pytest.approx(
            GasUnits.SM3_TO_SCF * 1e-6, rel=1e-6
        )

    def test_msm3_to_bcf_value(self):
        from worldenergydata.common.units import GasUnits

        assert GasUnits.MSM3_TO_BCF == pytest.approx(0.0353147, rel=1e-4)

    def test_msm3_to_mmscf_value(self):
        from worldenergydata.common.units import GasUnits

        assert GasUnits.MSM3_TO_MMSCF == pytest.approx(35.3147, rel=1e-4)

    def test_mmscf_to_mcf_is_1000(self):
        from worldenergydata.common.units import GasUnits

        assert GasUnits.MMSCF_TO_MCF == 1000.0

    def test_mcf_to_mmscf_is_inverse_of_mmscf_to_mcf(self):
        from worldenergydata.common.units import GasUnits

        assert GasUnits.MCF_TO_MMSCF == pytest.approx(
            1.0 / GasUnits.MMSCF_TO_MCF, rel=1e-6
        )

    def test_bcf_to_tcf_is_0_001(self):
        from worldenergydata.common.units import GasUnits

        assert GasUnits.BCF_TO_TCF == 0.001


# ---------------------------------------------------------------------------
# WaterUnits
# ---------------------------------------------------------------------------


class TestWaterUnits:
    """Tests for WaterUnits class constants."""

    def test_m3_to_bbl_value(self):
        from worldenergydata.common.units import WaterUnits

        assert WaterUnits.M3_TO_BBL == pytest.approx(6.2898, rel=1e-4)

    def test_tonne_to_bbl_value(self):
        from worldenergydata.common.units import WaterUnits

        assert WaterUnits.TONNE_TO_BBL == pytest.approx(6.2898, rel=1e-4)


# ---------------------------------------------------------------------------
# PressureUnits
# ---------------------------------------------------------------------------


class TestPressureUnits:
    """Tests for PressureUnits class constants."""

    def test_psi_to_bar_value(self):
        from worldenergydata.common.units import PressureUnits

        assert PressureUnits.PSI_TO_BAR == pytest.approx(0.0689476, rel=1e-4)

    def test_bar_to_psi_is_inverse(self):
        from worldenergydata.common.units import PressureUnits

        assert PressureUnits.BAR_TO_PSI == pytest.approx(
            1.0 / PressureUnits.PSI_TO_BAR, rel=1e-4
        )

    def test_kpa_to_psi_value(self):
        from worldenergydata.common.units import PressureUnits

        assert PressureUnits.KPA_TO_PSI == pytest.approx(0.145038, rel=1e-4)


# ---------------------------------------------------------------------------
# EnergyUnits
# ---------------------------------------------------------------------------


class TestEnergyUnits:
    """Tests for EnergyUnits class constants."""

    def test_bbl_to_boe_is_1(self):
        from worldenergydata.common.units import EnergyUnits

        assert EnergyUnits.BBL_TO_BOE == 1.0

    def test_mcf_to_boe_value(self):
        from worldenergydata.common.units import EnergyUnits

        # ~6 MCF per BOE rule of thumb → ~0.178 BOE per MCF
        assert EnergyUnits.MCF_TO_BOE == pytest.approx(0.178, rel=0.02)

    def test_mwh_to_boe_value(self):
        from worldenergydata.common.units import EnergyUnits

        assert EnergyUnits.MWH_TO_BOE == pytest.approx(0.5883, rel=0.01)


# ---------------------------------------------------------------------------
# UNIT_REGISTRY
# ---------------------------------------------------------------------------


class TestUnitRegistry:
    """Tests for the flat UNIT_REGISTRY dict."""

    def test_registry_is_dict(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        assert isinstance(UNIT_REGISTRY, dict)

    def test_registry_has_sm3_to_bbl(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        assert ("sm3", "bbl") in UNIT_REGISTRY

    def test_registry_has_bbl_to_sm3(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        assert ("bbl", "sm3") in UNIT_REGISTRY

    def test_registry_has_tonne_oil_to_bbl(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        assert ("tonne_oil", "bbl") in UNIT_REGISTRY

    def test_registry_has_msm3_to_bcf(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        assert ("msm3", "bcf") in UNIT_REGISTRY

    def test_registry_has_msm3_to_mmscf(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        assert ("msm3", "mmscf") in UNIT_REGISTRY

    def test_registry_has_mmscf_to_mcf(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        assert ("mmscf", "mcf") in UNIT_REGISTRY

    def test_registry_has_sm3_gas_to_scf(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        assert ("sm3_gas", "scf") in UNIT_REGISTRY

    def test_registry_has_psi_to_bar(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        assert ("psi", "bar") in UNIT_REGISTRY

    def test_registry_has_bar_to_psi(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        assert ("bar", "psi") in UNIT_REGISTRY

    def test_registry_has_mcf_to_boe(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        assert ("mcf", "boe") in UNIT_REGISTRY

    def test_registry_sm3_to_bbl_factor_correct(self):
        from worldenergydata.common.units import UNIT_REGISTRY, OilUnits

        assert UNIT_REGISTRY[("sm3", "bbl")] == OilUnits.SM3_TO_BBL

    def test_registry_bbl_to_sm3_factor_correct(self):
        from worldenergydata.common.units import UNIT_REGISTRY, OilUnits

        assert UNIT_REGISTRY[("bbl", "sm3")] == OilUnits.BBL_TO_SM3

    def test_registry_all_values_are_positive_floats(self):
        from worldenergydata.common.units import UNIT_REGISTRY

        for key, val in UNIT_REGISTRY.items():
            assert isinstance(val, float), f"Factor for {key} is not a float"
            assert val > 0, f"Factor for {key} must be positive"


# ---------------------------------------------------------------------------
# convert() function
# ---------------------------------------------------------------------------


class TestConvertScalar:
    """Tests for convert(value, from_unit, to_unit)."""

    def test_sm3_to_bbl_scalar(self):
        from worldenergydata.common.units import convert

        result = convert(1.0, "sm3", "bbl")
        assert result == pytest.approx(6.2898, rel=1e-4)

    def test_bbl_to_sm3_scalar(self):
        from worldenergydata.common.units import convert

        result = convert(1.0, "bbl", "sm3")
        assert result == pytest.approx(0.158987, rel=1e-4)

    def test_psi_to_bar_scalar(self):
        from worldenergydata.common.units import convert

        result = convert(1.0, "psi", "bar")
        assert result == pytest.approx(0.0689476, rel=1e-4)

    def test_mcf_to_boe_scalar(self):
        from worldenergydata.common.units import convert

        result = convert(6.0, "mcf", "boe")
        assert result == pytest.approx(6.0 * 0.178, rel=0.02)

    def test_msm3_to_mmscf_scalar(self):
        from worldenergydata.common.units import convert

        result = convert(1.0, "msm3", "mmscf")
        assert result == pytest.approx(35.3147, rel=1e-4)

    def test_unknown_from_unit_raises_key_error(self):
        from worldenergydata.common.units import convert

        with pytest.raises(KeyError, match="no conversion registered"):
            convert(1.0, "frobnitz", "bbl")

    def test_unknown_to_unit_raises_key_error(self):
        from worldenergydata.common.units import convert

        with pytest.raises(KeyError, match="no conversion registered"):
            convert(1.0, "sm3", "frobnitz")

    def test_zero_value_converts_to_zero(self):
        from worldenergydata.common.units import convert

        assert convert(0.0, "sm3", "bbl") == 0.0

    def test_large_value_converts_linearly(self):
        from worldenergydata.common.units import OilUnits, convert

        value = 1_000_000.0
        result = convert(value, "sm3", "bbl")
        assert result == pytest.approx(value * OilUnits.SM3_TO_BBL, rel=1e-6)


# ---------------------------------------------------------------------------
# Round-trip accuracy
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Tests for round-trip accuracy between unit pairs."""

    def test_sm3_bbl_round_trip(self):
        from worldenergydata.common.units import convert

        original = 12345.0
        converted = convert(original, "sm3", "bbl")
        back = convert(converted, "bbl", "sm3")
        assert back == pytest.approx(original, rel=1e-5)

    def test_psi_bar_round_trip(self):
        from worldenergydata.common.units import convert

        original = 3000.0
        converted = convert(original, "psi", "bar")
        back = convert(converted, "bar", "psi")
        assert back == pytest.approx(original, rel=1e-5)

    def test_msm3_mmscf_round_trip(self):
        from worldenergydata.common.units import convert

        original = 50.0
        converted = convert(original, "msm3", "mmscf")
        # There is no mmscf→msm3 in the registry by default; skip reverse
        # but verify forward is non-zero and sensible
        assert converted > 0

    def test_mmscf_mcf_round_trip(self):
        from worldenergydata.common.units import convert

        original = 5.0
        converted = convert(original, "mmscf", "mcf")
        back = convert(converted, "mcf", "mmscf")
        assert back == pytest.approx(original, rel=1e-6)


# ---------------------------------------------------------------------------
# convert_series() function
# ---------------------------------------------------------------------------


class TestConvertSeries:
    """Tests for convert_series(pd.Series, from_unit, to_unit)."""

    def test_series_sm3_to_bbl(self):
        from worldenergydata.common.units import OilUnits, convert_series

        data = pd.Series([0.0, 1.0, 100.0, 1_000_000.0])
        result = convert_series(data, "sm3", "bbl")
        expected = data * OilUnits.SM3_TO_BBL
        pd.testing.assert_series_equal(result, expected)

    def test_series_psi_to_bar(self):
        from worldenergydata.common.units import PressureUnits, convert_series

        data = pd.Series([14.696, 3000.0, 6000.0])
        result = convert_series(data, "psi", "bar")
        expected = data * PressureUnits.PSI_TO_BAR
        pd.testing.assert_series_equal(result, expected)

    def test_series_result_is_pandas_series(self):
        from worldenergydata.common.units import convert_series

        data = pd.Series([1.0, 2.0, 3.0])
        result = convert_series(data, "sm3", "bbl")
        assert isinstance(result, pd.Series)

    def test_series_unknown_unit_raises(self):
        from worldenergydata.common.units import convert_series

        data = pd.Series([1.0, 2.0])
        with pytest.raises(KeyError, match="no conversion registered"):
            convert_series(data, "frobnitz", "bbl")

    def test_empty_series_converts_to_empty(self):
        from worldenergydata.common.units import convert_series

        data = pd.Series([], dtype=float)
        result = convert_series(data, "sm3", "bbl")
        assert len(result) == 0
        assert isinstance(result, pd.Series)

    def test_series_preserves_index(self):
        from worldenergydata.common.units import convert_series

        data = pd.Series([1.0, 2.0, 3.0], index=[10, 20, 30])
        result = convert_series(data, "sm3", "bbl")
        assert list(result.index) == [10, 20, 30]

    def test_series_msm3_to_mmscf(self):
        from worldenergydata.common.units import GasUnits, convert_series

        data = pd.Series([1.0, 2.0, 5.0])
        result = convert_series(data, "msm3", "mmscf")
        expected = data * GasUnits.MSM3_TO_MMSCF
        pd.testing.assert_series_equal(result, expected)
