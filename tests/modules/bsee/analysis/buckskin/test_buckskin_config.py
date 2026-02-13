"""Tests for BuckskinConfig — field metadata and lease resolution."""

from __future__ import annotations

import pytest


class TestBuckskinConfig:
    """Verify BuckskinConfig fields and methods."""

    def test_field_name(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        assert BUCKSKIN.field_name == "Buckskin"

    def test_area_code(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        assert BUCKSKIN.area_code == "KC"

    def test_blocks_count(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        assert len(BUCKSKIN.blocks) == 6
        assert set(BUCKSKIN.blocks) == {785, 828, 829, 830, 871, 872}

    def test_boem_leases_count(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        assert len(BUCKSKIN.boem_leases) == 5
        assert "OCS-G 25806" in BUCKSKIN.boem_leases
        assert "OCS-G 25823" in BUCKSKIN.boem_leases

    def test_lease_numbers(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        assert "G25806" in BUCKSKIN.lease_numbers
        assert "G25823" in BUCKSKIN.lease_numbers
        assert len(BUCKSKIN.lease_numbers) == 5

    def test_all_lease_numbers(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        assert len(BUCKSKIN.all_lease_numbers) == 8
        # Primary leases are a subset
        for ln in BUCKSKIN.lease_numbers:
            assert ln in BUCKSKIN.all_lease_numbers

    def test_block_set_contains_int_and_str(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        bs = BUCKSKIN.block_set()
        assert 785 in bs
        assert "785" in bs
        assert 872 in bs
        assert "872" in bs

    def test_lease_set_contains_variants(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        ls = BUCKSKIN.lease_set()
        assert "G25806" in ls
        assert "G 25806" in ls  # spaced variant
        assert "G25823" in ls
        assert "G 25823" in ls

    def test_operator_history_chronological(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        years = [entry[1] for entry in BUCKSKIN.operator_history]
        assert years == sorted(years)

    def test_expected_benchmarks(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        assert BUCKSKIN.expected_first_oil_year == 2019
        assert BUCKSKIN.expected_peak_rate_bopd == 30_000

    def test_frozen_dataclass(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        with pytest.raises(AttributeError):
            BUCKSKIN.field_name = "Other"  # type: ignore[misc]

    def test_geological_era(self):
        from worldenergydata.bsee.analysis.buckskin.buckskin_config import BUCKSKIN

        assert "Wilcox" in BUCKSKIN.geological_era
        assert "Lower Tertiary" in BUCKSKIN.geological_era
