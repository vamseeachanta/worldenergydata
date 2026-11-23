"""Tests for unit conversion utilities."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from worldenergydata.bsee.pipeline.adapters.units import (
    BBL_TO_M3,
    BCF_TO_M3,
    LB_PER_FT_TO_KG_PER_M,
    MCF_TO_BOE,
    MCF_TO_M3,
    PSI_TO_PA,
    SM3_TO_BBL,
    barrels_to_m3,
    bcf_to_m3,
    billion_sm3_to_m3,
    convert_column,
    feet_to_metres,
    gas_mcf_to_boe,
    inches_to_metres,
    inches_to_mm,
    lb_per_ft_to_kg_per_m,
    m3_to_barrels,
    mcf_to_m3,
    metres_to_feet,
    mmbbl_to_m3,
    pa_to_psi,
    psi_to_pa,
)


class TestLength:
    def test_feet_to_metres_known(self):
        assert feet_to_metres(1.0) == pytest.approx(0.3048)

    def test_feet_to_metres_zero(self):
        assert feet_to_metres(0.0) == 0.0

    def test_metres_to_feet_roundtrip(self):
        original = 100.0
        assert metres_to_feet(feet_to_metres(original)) == pytest.approx(original)

    def test_inches_to_metres(self):
        assert inches_to_metres(12.0) == pytest.approx(0.3048)

    def test_inches_to_mm(self):
        assert inches_to_mm(1.0) == pytest.approx(25.4)

    def test_water_depth_conversion(self):
        """1000 ft water depth -> 304.8 m."""
        assert feet_to_metres(1000.0) == pytest.approx(304.8)


class TestOilVolume:
    def test_barrels_to_m3(self):
        assert barrels_to_m3(1.0) == pytest.approx(BBL_TO_M3)

    def test_m3_to_barrels_roundtrip(self):
        original = 500.0
        assert m3_to_barrels(barrels_to_m3(original)) == pytest.approx(original)

    def test_mmbbl_to_m3(self):
        result = mmbbl_to_m3(1.0)
        assert result == pytest.approx(1e6 * BBL_TO_M3)

    def test_sm3_to_bbl_constant(self):
        assert SM3_TO_BBL == pytest.approx(6.29, abs=0.01)


class TestGasVolume:
    def test_mcf_to_m3(self):
        assert mcf_to_m3(1.0) == pytest.approx(MCF_TO_M3)

    def test_bcf_to_m3(self):
        assert bcf_to_m3(1.0) == pytest.approx(BCF_TO_M3)

    def test_billion_sm3_to_m3(self):
        assert billion_sm3_to_m3(1.0) == pytest.approx(1e9)


class TestPressure:
    def test_psi_to_pa(self):
        assert psi_to_pa(1.0) == pytest.approx(PSI_TO_PA)

    def test_pa_to_psi_roundtrip(self):
        original = 5000.0
        assert pa_to_psi(psi_to_pa(original)) == pytest.approx(original)


class TestMass:
    def test_lb_per_ft_to_kg_per_m(self):
        assert lb_per_ft_to_kg_per_m(1.0) == pytest.approx(LB_PER_FT_TO_KG_PER_M)


class TestBOE:
    def test_gas_mcf_to_boe(self):
        assert gas_mcf_to_boe(5.8) == pytest.approx(1.0)


class TestConvertColumn:
    def test_converts_existing_column(self):
        df = pd.DataFrame({"depth_ft": [100.0, 200.0, 300.0]})
        convert_column(df, "depth_ft", feet_to_metres, "depth_m")
        assert list(df["depth_m"]) == pytest.approx([30.48, 60.96, 91.44])
        # Original column preserved
        assert "depth_ft" in df.columns

    def test_overwrites_when_no_target(self):
        df = pd.DataFrame({"depth": [100.0]})
        convert_column(df, "depth", feet_to_metres)
        assert df["depth"].iloc[0] == pytest.approx(30.48)

    def test_missing_column_is_noop(self):
        df = pd.DataFrame({"other": [1.0]})
        convert_column(df, "depth_ft", feet_to_metres, "depth_m")
        assert "depth_m" not in df.columns

    def test_handles_none_values(self):
        df = pd.DataFrame({"depth_ft": [100.0, None, 300.0]})
        convert_column(df, "depth_ft", feet_to_metres, "depth_m")
        assert df["depth_m"].iloc[0] == pytest.approx(30.48)
        assert math.isnan(df["depth_m"].iloc[1])  # pandas coerces None -> NaN
        assert df["depth_m"].iloc[2] == pytest.approx(91.44)

    def test_handles_nan_values(self):
        df = pd.DataFrame({"depth_ft": [100.0, float("nan"), 300.0]})
        convert_column(df, "depth_ft", feet_to_metres, "depth_m")
        assert df["depth_m"].iloc[0] == pytest.approx(30.48)
        assert math.isnan(df["depth_m"].iloc[1])
        assert df["depth_m"].iloc[2] == pytest.approx(91.44)
