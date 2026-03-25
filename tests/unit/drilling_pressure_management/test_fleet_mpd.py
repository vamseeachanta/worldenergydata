"""Tests for fleet MPD capability flags — fleet_mpd module."""

import pytest
import pandas as pd

from worldenergydata.drilling_pressure_management.fleet_mpd import (
    FLEET_MPD_DATA,
    RigMPDCapability,
    fleet_mpd_summary,
    get_contractor_fleet,
    get_mpd_capable_rigs,
)


class TestFleetMPDData:
    def test_fleet_has_at_least_nine_rigs(self):
        assert len(FLEET_MPD_DATA) >= 9

    def test_all_entries_are_rig_mpd_capability_instances(self):
        for rig in FLEET_MPD_DATA:
            assert isinstance(rig, RigMPDCapability)

    def test_valaris_ds12_is_mpd_capable(self):
        names = {r.rig_name: r for r in FLEET_MPD_DATA}
        assert "VALARIS DS-12" in names
        assert names["VALARIS DS-12"].mpd_capable is True

    def test_valaris_ds12_has_safekick_system(self):
        names = {r.rig_name: r for r in FLEET_MPD_DATA}
        assert names["VALARIS DS-12"].mpd_system == "safekick_mpd"

    def test_three_contractors_represented(self):
        contractors = {r.contractor for r in FLEET_MPD_DATA}
        assert "Valaris" in contractors
        assert "Transocean" in contractors
        assert "Noble" in contractors

    def test_non_mpd_rigs_have_null_system(self):
        for rig in FLEET_MPD_DATA:
            if not rig.mpd_capable:
                assert rig.mpd_system is None, (
                    f"{rig.rig_name} is not MPD capable but has mpd_system={rig.mpd_system!r}"
                )

    def test_non_mpd_rigs_have_null_manufacturer(self):
        for rig in FLEET_MPD_DATA:
            if not rig.mpd_capable:
                assert rig.mpd_manufacturer is None, (
                    f"{rig.rig_name} is not MPD capable but has mpd_manufacturer set"
                )

    def test_mpd_capable_rigs_have_system_set(self):
        for rig in FLEET_MPD_DATA:
            if rig.mpd_capable:
                assert rig.mpd_system is not None, (
                    f"{rig.rig_name} is MPD capable but mpd_system is None"
                )

    def test_mpd_capable_rigs_have_manufacturer_set(self):
        for rig in FLEET_MPD_DATA:
            if rig.mpd_capable:
                assert rig.mpd_manufacturer is not None, (
                    f"{rig.rig_name} is MPD capable but mpd_manufacturer is None"
                )

    def test_rig_names_are_unique(self):
        names = [r.rig_name for r in FLEET_MPD_DATA]
        assert len(names) == len(set(names)), "Duplicate rig_name values found"

    def test_all_rig_types_are_valid(self):
        valid_types = {"drillship", "semisubmersible", "jackup"}
        for rig in FLEET_MPD_DATA:
            assert rig.rig_type in valid_types, (
                f"{rig.rig_name} has unknown rig_type={rig.rig_type!r}"
            )


class TestGetMPDCapableRigs:
    def test_returns_only_mpd_capable(self):
        capable = get_mpd_capable_rigs()
        for rig in capable:
            assert rig.mpd_capable is True

    def test_returns_non_empty_list(self):
        assert len(get_mpd_capable_rigs()) >= 1

    def test_does_not_include_non_mpd_rigs(self):
        capable_names = {r.rig_name for r in get_mpd_capable_rigs()}
        for rig in FLEET_MPD_DATA:
            if not rig.mpd_capable:
                assert rig.rig_name not in capable_names


class TestGetContractorFleet:
    def test_valaris_fleet_returns_only_valaris(self):
        fleet = get_contractor_fleet("Valaris")
        for rig in fleet:
            assert rig.contractor == "Valaris"

    def test_transocean_fleet_returns_only_transocean(self):
        fleet = get_contractor_fleet("Transocean")
        for rig in fleet:
            assert rig.contractor == "Transocean"

    def test_noble_fleet_returns_only_noble(self):
        fleet = get_contractor_fleet("Noble")
        for rig in fleet:
            assert rig.contractor == "Noble"

    def test_each_contractor_has_at_least_three_rigs(self):
        for contractor in ("Valaris", "Transocean", "Noble"):
            fleet = get_contractor_fleet(contractor)
            assert len(fleet) >= 3, (
                f"{contractor} fleet has only {len(fleet)} rigs (need >= 3)"
            )

    def test_unknown_contractor_returns_empty_list(self):
        assert get_contractor_fleet("Nonexistent Corp") == []


class TestFleetMPDSummary:
    def test_returns_dataframe(self):
        df = fleet_mpd_summary()
        assert isinstance(df, pd.DataFrame)

    def test_has_contractor_column(self):
        df = fleet_mpd_summary()
        assert "contractor" in df.columns

    def test_has_total_rigs_column(self):
        df = fleet_mpd_summary()
        assert "total_rigs" in df.columns

    def test_has_mpd_capable_count_column(self):
        df = fleet_mpd_summary()
        assert "mpd_capable_count" in df.columns

    def test_all_three_contractors_in_summary(self):
        df = fleet_mpd_summary()
        contractors = set(df["contractor"].tolist())
        assert "Valaris" in contractors
        assert "Transocean" in contractors
        assert "Noble" in contractors

    def test_total_rigs_sum_matches_fleet(self):
        df = fleet_mpd_summary()
        assert df["total_rigs"].sum() == len(FLEET_MPD_DATA)

    def test_mpd_capable_count_never_exceeds_total(self):
        df = fleet_mpd_summary()
        assert (df["mpd_capable_count"] <= df["total_rigs"]).all()

    def test_mpd_capable_count_sum_matches_capable_rigs(self):
        df = fleet_mpd_summary()
        assert df["mpd_capable_count"].sum() == len(get_mpd_capable_rigs())
