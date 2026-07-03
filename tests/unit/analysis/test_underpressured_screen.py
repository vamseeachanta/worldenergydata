"""Unit tests for the under-pressured screen (#710)."""

import math

import numpy as np
import pandas as pd
import pytest

from worldenergydata.analysis.underpressured_screen.screen import (
    TIER_MILD,
    TIER_NORMAL,
    TIER_SEVERE,
    apply_field_tier,
    build_screen_summary,
    classify_tiers,
    earliest_per_well,
    estimate_bhp,
    rank_fields,
    run_screen,
    run_participation_gate,
    run_validation_gate,
)

BHP_SETTINGS = {"gas_sg": 0.65, "z_avg": 0.95, "t_avg_rankine": 520.0}
TIERS = {
    "hydrostatic_normal_min": 0.433,
    "mild_underpressure_min": 0.35,
    "near_vacuum_whp_psia": 50.0,
}


def make_observations(rows):
    defaults = {
        "state": "KS",
        "pressure_kind": "WHP_shut_in",
        "era": "depleted",
        "field": "HUGOTON GAS AREA",
        "source_name": "kansas_kgs_proration",
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


class TestEstimateBhp:
    def test_whp_gets_static_column_correction(self):
        obs = make_observations(
            [
                {
                    "well_key": "w1",
                    "test_year": 1997,
                    "pressure_psia": 100.0,
                    "reference_depth_ft": 2800.0,
                }
            ]
        )
        result = estimate_bhp(obs, BHP_SETTINGS)
        expected = 100.0 * math.exp(0.01875 * 0.65 * 2800.0 / (0.95 * 520.0))
        assert result["bhp_psia_est"].iloc[0] == pytest.approx(expected)
        assert result["bhp_method"].iloc[0] == "static_gas_column_avg_zt"

    def test_flowing_tubing_whp_gets_static_column_screening_correction(self):
        obs = make_observations(
            [
                {
                    "well_key": "w1",
                    "test_year": 2024,
                    "pressure_psia": 100.0,
                    "reference_depth_ft": 2800.0,
                    "pressure_kind": "WHP_flowing_tubing",
                }
            ]
        )
        result = estimate_bhp(obs, BHP_SETTINGS)
        expected = 100.0 * math.exp(0.01875 * 0.65 * 2800.0 / (0.95 * 520.0))
        assert result["bhp_psia_est"].iloc[0] == pytest.approx(expected)
        assert result["bhp_method"].iloc[0] == "static_gas_column_avg_zt"

    def test_measured_bhp_passes_through(self):
        obs = make_observations(
            [
                {
                    "well_key": "w1",
                    "test_year": 1997,
                    "pressure_psia": 1200.0,
                    "reference_depth_ft": 5000.0,
                    "pressure_kind": "BHP_measured",
                }
            ]
        )
        result = estimate_bhp(obs, BHP_SETTINGS)
        assert result["bhp_psia_est"].iloc[0] == pytest.approx(1200.0)
        assert result["bhp_method"].iloc[0] == "as_reported"

    def test_no_gradient_without_depth(self):
        obs = make_observations(
            [
                {
                    "well_key": "w1",
                    "test_year": 1997,
                    "pressure_psia": 100.0,
                    "reference_depth_ft": 0.0,
                }
            ]
        )
        result = estimate_bhp(obs, BHP_SETTINGS)
        assert np.isnan(result["bhp_gradient_psi_ft"].iloc[0])


class TestClassifyTiers:
    @pytest.mark.parametrize(
        "gradient,expected",
        [
            (0.5, TIER_NORMAL),
            (0.433, TIER_NORMAL),
            (0.40, TIER_MILD),
            (0.35, TIER_MILD),
            (0.02, TIER_SEVERE),
        ],
    )
    def test_tier_boundaries(self, gradient, expected):
        frame = pd.DataFrame(
            {
                "bhp_gradient_psi_ft": [gradient],
                "pressure_kind": ["WHP_shut_in"],
                "pressure_psia": [500.0],
            }
        )
        assert classify_tiers(frame, TIERS)["pressure_tier"].iloc[0] == expected

    def test_near_vacuum_flag(self):
        frame = pd.DataFrame(
            {
                "bhp_gradient_psi_ft": [0.02, 0.02],
                "pressure_kind": ["WHP_shut_in", "BHP_measured"],
                "pressure_psia": [30.0, 30.0],
            }
        )
        result = classify_tiers(frame, TIERS)
        # only wellhead readings can assert the vacuum-operations regime
        assert bool(result["near_vacuum"].iloc[0])
        assert not bool(result["near_vacuum"].iloc[1])


class TestEarliestAndRanking:
    def _screened(self):
        obs = make_observations(
            [
                {
                    "well_key": "w1",
                    "test_year": 1999,
                    "pressure_psia": 80.0,
                    "reference_depth_ft": 2800.0,
                },
                {
                    "well_key": "w1",
                    "test_year": 1997,
                    "pressure_psia": 100.0,
                    "reference_depth_ft": 2800.0,
                },
                {
                    "well_key": "w2",
                    "test_year": 1996,
                    "pressure_psia": 90.0,
                    "reference_depth_ft": 2700.0,
                },
                {
                    "well_key": "w3",
                    "test_year": 1996,
                    "pressure_psia": 40.0,
                    "reference_depth_ft": 2750.0,
                },
                {
                    "well_key": "w4",
                    "test_year": 1998,
                    "pressure_psia": 95.0,
                    "reference_depth_ft": 2600.0,
                },
                {
                    "well_key": "w5",
                    "test_year": 1998,
                    "pressure_psia": 85.0,
                    "reference_depth_ft": 2650.0,
                },
                # a normal-pressured deep well in another field, below min_wells cutoff
                {
                    "well_key": "w6",
                    "test_year": 2000,
                    "pressure_psia": 4500.0,
                    "reference_depth_ft": 9000.0,
                    "field": "DEEP NORMAL",
                },
            ]
        )
        return classify_tiers(estimate_bhp(obs, BHP_SETTINGS), TIERS)

    def test_earliest_observation_selected(self):
        wells = earliest_per_well(self._screened())
        w1 = wells[wells["well_key"] == "w1"]
        assert int(w1["test_year"].iloc[0]) == 1997

    def test_field_ranking_and_tier(self):
        wells = earliest_per_well(self._screened())
        ranking = apply_field_tier(
            rank_fields(wells, {"min_wells_per_field": 5}), TIERS
        )
        assert list(ranking["field"]) == ["HUGOTON GAS AREA"]
        row = ranking.iloc[0]
        assert row["well_count"] == 5
        assert row["field_tier"] == TIER_SEVERE
        assert row["near_vacuum_wells"] == 1  # w3 at 40 psia

    def test_min_wells_cutoff_drops_small_fields(self):
        wells = earliest_per_well(self._screened())
        ranking = rank_fields(wells, {"min_wells_per_field": 5})
        assert "DEEP NORMAL" not in set(ranking["field"])

    def test_earliest_per_well_uses_texas_api14_well_key(self):
        obs = make_observations(
            [
                {
                    "well_key": "42127373050000",
                    "state": "TX",
                    "test_year": 2018,
                    "pressure_psia": 1000.0,
                    "reference_depth_ft": 7000.0,
                    "source_name": "texas_rrc_completion_packets",
                },
                {
                    "well_key": "42127373050000",
                    "state": "TX",
                    "test_year": 2017,
                    "pressure_psia": 900.0,
                    "reference_depth_ft": 7000.0,
                    "source_name": "texas_rrc_completion_packets",
                },
            ]
        )
        wells = earliest_per_well(
            classify_tiers(estimate_bhp(obs, BHP_SETTINGS), TIERS)
        )
        assert len(wells) == 1
        assert int(wells.loc[0, "test_year"]) == 2017

    def test_earliest_per_well_uses_source_priority_for_same_year_ties(self):
        obs = make_observations(
            [
                {
                    "well_key": "42127373050000",
                    "state": "TX",
                    "test_year": 2017,
                    "pressure_psia": 1046.7,
                    "reference_depth_ft": 15150.5,
                    "screen_observation_priority": 1,
                },
                {
                    "well_key": "42127373050000",
                    "state": "TX",
                    "test_year": 2017,
                    "pressure_psia": 1046.7,
                    "reference_depth_ft": 7394.0,
                    "screen_observation_priority": 0,
                },
            ]
        )

        wells = earliest_per_well(
            classify_tiers(estimate_bhp(obs, BHP_SETTINGS), TIERS)
        )

        assert len(wells) == 1
        assert wells.loc[0, "reference_depth_ft"] == 7394.0


class TestValidationGate:
    def _ranking(self, tier):
        return pd.DataFrame(
            {
                "field": ["HUGOTON GAS AREA", "PANOMA GAS AREA", "OTHER"],
                "well_count": [100, 50, 10],
                "field_tier": [tier, tier, TIER_NORMAL],
            }
        )

    def test_gate_passes_on_analog_recovery(self):
        gate = run_validation_gate(
            self._ranking(TIER_SEVERE),
            {
                "required_fields_in_top10": ["HUGOTON GAS AREA", "PANOMA GAS AREA"],
                "required_tier": TIER_SEVERE,
            },
        )
        assert gate["passed"]

    def test_gate_fails_on_wrong_tier(self):
        gate = run_validation_gate(
            self._ranking(TIER_NORMAL),
            {
                "required_fields_in_top10": ["HUGOTON GAS AREA", "PANOMA GAS AREA"],
                "required_tier": TIER_SEVERE,
            },
        )
        assert not gate["passed"]

    def test_gate_fails_on_missing_field(self):
        ranking = self._ranking(TIER_SEVERE)
        ranking = ranking[ranking["field"] != "PANOMA GAS AREA"]
        gate = run_validation_gate(
            ranking,
            {
                "required_fields_in_top10": ["HUGOTON GAS AREA", "PANOMA GAS AREA"],
                "required_tier": TIER_SEVERE,
            },
        )
        assert not gate["passed"]


class TestSummaryAndParticipationGate:
    def test_summary_reports_state_source_and_era_counts(self):
        wells = pd.DataFrame(
            {
                "well_key": ["ks-1", "tx-1", "ok-1"],
                "state": ["KS", "TX", "OK"],
                "source_name": [
                    "kansas_kgs_proration",
                    "texas_rrc_completion_packets",
                    "oklahoma_occ_completions",
                ],
                "era": [
                    "depleted",
                    "completion_packet_screening",
                    "completion_test_2010_present",
                ],
                "pressure_tier": [TIER_SEVERE, TIER_MILD, TIER_MILD],
                "near_vacuum": [False, False, False],
                "bhp_gradient_psi_ft": [0.03, 0.40, 0.39],
            }
        )
        ranking = pd.DataFrame({"field": ["HUGOTON GAS AREA", "BRISCOE RANCH"]})

        summary = build_screen_summary(
            wells,
            ranking,
            {"passed": True},
            {"passed": True},
            {
                "input_row_counts": {
                    "kansas_kgs_proration": 2,
                    "texas_rrc_completion_packets": 3,
                    "oklahoma_occ_completions": 4,
                },
                "loaded_row_counts": {
                    "kansas_kgs_proration": 1,
                    "texas_rrc_completion_packets": 1,
                    "oklahoma_occ_completions": 1,
                },
                "source_warnings": {"texas_rrc_completion_packets": ["warning"]},
            },
        )

        assert summary["state_counts"] == {"KS": 1, "TX": 1, "OK": 1}
        assert summary["source_counts"] == {
            "kansas_kgs_proration": 1,
            "texas_rrc_completion_packets": 1,
            "oklahoma_occ_completions": 1,
        }
        assert summary["era_note"] == [
            "completion_packet_screening",
            "completion_test_2010_present",
            "depleted",
        ]
        assert summary["source_warnings"] == {
            "texas_rrc_completion_packets": ["warning"]
        }

    def test_participation_gate_requires_state_well_count(self):
        wells = pd.DataFrame(
            {
                "well_key": ["ks-1", "tx-1"],
                "state": ["KS", "TX"],
            }
        )

        gate = run_participation_gate(
            wells,
            {"required_states": {"TX": {"min_wells": 1}}},
        )

        assert gate["passed"]
        assert gate["states"]["TX"]["well_count"] == 1

    def test_participation_gate_fails_when_state_missing(self):
        wells = pd.DataFrame({"well_key": ["ks-1"], "state": ["KS"]})

        gate = run_participation_gate(
            wells,
            {"required_states": {"TX": {"min_wells": 1}}},
        )

        assert not gate["passed"]
        assert gate["states"]["TX"]["well_count"] == 0

    def test_screen_outputs_are_parquet_safe_with_mixed_optional_metadata(
        self, tmp_path
    ):
        first = make_observations(
            [
                {
                    "well_key": "ks-1",
                    "test_year": 2020,
                    "pressure_psia": 100.0,
                    "reference_depth_ft": 2800.0,
                    "test_date": pd.Timestamp("2020-01-01"),
                }
            ]
        )
        second = make_observations(
            [
                {
                    "well_key": "ok-1",
                    "state": "OK",
                    "test_year": 2021,
                    "pressure_psia": 120.0,
                    "reference_depth_ft": 3200.0,
                    "test_date": "2021-01-01",
                    "source_name": "oklahoma_occ_completions",
                    "era": "completion_test_2010_present",
                }
            ]
        )
        first_path = tmp_path / "first.parquet"
        second_path = tmp_path / "second.parquet"
        first.to_parquet(first_path)
        second.to_parquet(second_path)
        config_path = tmp_path / "screen.yml"
        output_dir = tmp_path / "out"
        config_path.write_text(
            f"""
inputs:
  - name: kansas_kgs_proration
    path: {first_path}
    schema: screen_v1
    era: depleted
  - name: oklahoma_occ_completions
    path: {second_path}
    schema: screen_v1
    era: completion_test_2010_present
bhp_estimate:
  gas_sg: 0.65
  z_avg: 0.95
  t_avg_rankine: 520.0
tiers:
  hydrostatic_normal_min: 0.433
  mild_underpressure_min: 0.35
  near_vacuum_whp_psia: 50.0
field_ranking:
  min_wells_per_field: 1
validation_gate:
  required_fields_in_top10: []
  required_tier: severely_underpressured
participation_gate:
  required_states:
    KS:
      min_wells: 1
    OK:
      min_wells: 1
output:
  base_dir: {output_dir}
""",
            encoding="utf-8",
        )

        summary = run_screen(config_path)

        assert summary["state_counts"] == {"KS": 1, "OK": 1}
        assert (
            pd.read_parquet(output_dir / "well_screen_earliest.parquet").shape[0] == 2
        )
