# ABOUTME: Unit tests for the UDW intervention access-gap synthesis (worldenergydata #638, capstone of #626).
# ABOUTME: Synthetic demand/supply/gap arithmetic + parameter overrides + depth-eligibility + a real-YAML smoke check; CI-safe, no /mnt/ace dep.

"""Unit tests for worldenergydata.bsee.analysis.intervention.access_gap."""

from worldenergydata.bsee.analysis.intervention.access_gap import (
    CONF_FORWARD_RISK,
    DAYS_PER_YEAR,
    DEFAULT_INTERVENTION_FREQUENCY,
    DEFAULT_UTILIZATION,
    HEAVY_DEEPWATER_CLASSES,
    build_access_gap,
    demand_rig_days,
    eligible_global_fleet,
    eligible_gom_resident,
    exposure_usd,
    gap_metrics,
    supply_rig_days,
)

FREQ = {"low": 0.1, "central": 0.2, "high": 0.4}
UTIL = {"low": 0.5, "central": 0.5, "high": 0.5}


class TestDemandArithmetic:
    def test_demand_rig_days_pairs_freq_with_duration(self):
        # wells=100; central interventions = 100*0.2 = 20; duration median 50.
        out = demand_rig_days(100, FREQ, {"low": 30, "median": 50, "high": 60})
        assert out["interventions_per_yr"]["central"] == 20.0
        assert out["rig_days_per_yr"]["central"] == 20.0 * 50
        # low pairs freq.low with dur.low; high pairs freq.high with dur.high.
        assert out["rig_days_per_yr"]["low"] == (100 * 0.1) * 30
        assert out["rig_days_per_yr"]["high"] == (100 * 0.4) * 60

    def test_zero_wells_zero_demand(self):
        out = demand_rig_days(0, FREQ, {"low": 30, "median": 50, "high": 60})
        assert out["rig_days_per_yr"]["central"] == 0


class TestSupplyArithmetic:
    def test_supply_rig_days(self):
        # 4 units x 0.5 utilization x 365 = 730 rig-days.
        out = supply_rig_days(4, UTIL)
        assert out["central"] == 4 * 0.5 * DAYS_PER_YEAR
        assert out["low"] == 4 * 0.5 * 365


class TestGapMetrics:
    def test_gap_and_ratio_central(self):
        demand = {"low": 100, "central": 1000, "high": 2000}
        supply = {"low": 200, "central": 500, "high": 800}
        m = gap_metrics(demand, supply)
        assert m["gap_rig_days_per_yr"]["central"] == 1000 - 500
        assert m["utilization_ratio"]["central"] == round(1000 / 500, 3)
        # conservative = high demand vs low supply (worst case).
        assert m["gap_rig_days_per_yr"]["conservative"] == 2000 - 200
        assert m["utilization_ratio"]["conservative"] == round(2000 / 200, 3)

    def test_ratio_none_when_supply_zero(self):
        demand = {"low": 1, "central": 1, "high": 1}
        supply = {"low": 0, "central": 0, "high": 0}
        m = gap_metrics(demand, supply)
        assert m["utilization_ratio"]["central"] is None


class TestExposure:
    def test_exposure_uses_band_cost(self):
        interventions = {"low": 5, "central": 10, "high": 20}
        cost = {"low": 1_000_000, "median": 2_000_000, "high": 3_000_000}
        out = exposure_usd(interventions, cost)
        assert out["central"] == 10 * 2_000_000

    def test_exposure_none_when_cost_unpriced(self):
        interventions = {"low": 5, "central": 10, "high": 20}
        assert exposure_usd(interventions, None) is None
        assert (
            exposure_usd(interventions, {"low": None, "median": None, "high": None})
            is None
        )


class TestFleetEligibility:
    BY_CLASS = {
        "modu_drillship": {
            "count": 10,
            "water_depth_capability_ft": {"min": 4900, "max": 12000},
        },
        "modu_semisub": {
            "count": 5,
            "water_depth_capability_ft": {"min": 1500, "max": 12500},
        },
        "heavy_intervention_semi": {
            "count": 3,
            "water_depth_capability_ft": {"min": 1200, "max": 10000},
        },
        "rlwi_monohull": {
            "count": 4,
            "water_depth_capability_ft": {"min": 6561, "max": 6561},
        },
    }

    def test_all_heavy_classes_eligible_in_mid_band(self):
        out = eligible_global_fleet(self.BY_CLASS, 5000.0)
        assert out["count"] == 10 + 5 + 3
        assert "rlwi_monohull" not in out["by_class"]  # light excluded from heavy

    def test_depth_excludes_shallow_capability_in_ultra_deep_band(self):
        # Above the heavy semi's 10,000 ft rating it can no longer serve the band.
        out = eligible_global_fleet(self.BY_CLASS, 10001.0)
        assert "heavy_intervention_semi" not in out["by_class"]
        assert out["count"] == 10 + 5  # only the two MODU classes reach deeper

    def test_gom_resident_excludes_light_and_shallow(self):
        units = [
            {
                "name": "Helix Q4000",
                "intervention_class": "heavy",
                "asset_class": "heavy_intervention_semi",
                "water_depth_rating_m": 3048.0,
            },
            {
                "name": "Island Performer",
                "intervention_class": "light",
                "asset_class": "rlwi_monohull",
                "water_depth_rating_m": 2000.0,
            },
        ]
        out = eligible_gom_resident(units, 5000.0)
        assert out["count"] == 1  # only the heavy Helix qualifies
        assert out["units"] == ["Helix Q4000"]


# ---------------------------------------------------------------------------
# End-to-end build on synthetic inputs
# ---------------------------------------------------------------------------
SYNTH_INVENTORY = {
    "bands": {
        "band_5000_10000": {"subsea_wells_on_record": 200},
        "band_3000_5000": {"subsea_wells_on_record": 100},
    }
}

SYNTH_ECONOMICS = {
    "economics": {
        "band_5000_10000": {
            "heavy_dead_well": {
                "duration_days": {"low": 37, "median": 55, "high": 74},
                "cost_usd": {
                    "low": 11_100_000,
                    "median": 25_135_000,
                    "high": 39_220_000,
                },
            }
        },
        "band_3000_5000": {
            "heavy_dead_well": {
                "duration_days": {"low": 34, "median": 51, "high": 69},
                "cost_usd": {
                    "low": 10_200_000,
                    "median": 23_307_000,
                    "high": 36_570_000,
                },
            }
        },
    },
    "campaign_duration_days": {
        "heavy_dead_well": {"low": 30, "median": 45, "high": 60}
    },
}

SYNTH_DEMAND = {
    "bands": {
        "band_5000_10000": {"interventions_per_well": 6.434},
        "band_3000_5000": {"interventions_per_well": 7.534},
    }
}

SYNTH_FLEET = {
    "by_asset_class": {
        "modu_drillship": {
            "count": 161,
            "water_depth_capability_ft": {"min": 4900, "max": 12000},
        },
        "heavy_intervention_semi": {
            "count": 5,
            "water_depth_capability_ft": {"min": 1200, "max": 10000},
        },
    },
    "gom_resident_dedicated_intervention": {
        "count": 3,
        "units": [
            {
                "name": "Helix Q4000",
                "intervention_class": "heavy",
                "asset_class": "heavy_intervention_semi",
                "water_depth_rating_m": 3048.0,
            },
            {
                "name": "Helix Q5000",
                "intervention_class": "heavy",
                "asset_class": "heavy_intervention_semi",
                "water_depth_rating_m": 3048.0,
            },
            {
                "name": "Island Performer",
                "intervention_class": "light",
                "asset_class": "rlwi_monohull",
                "water_depth_rating_m": 2000.0,
            },
        ],
    },
}


def _build(**kw):
    return build_access_gap(
        inventory=SYNTH_INVENTORY,
        economics=SYNTH_ECONOMICS,
        demand=SYNTH_DEMAND,
        fleet=SYNTH_FLEET,
        **kw,
    )


class TestBuildEndToEnd:
    def test_demand_supply_gap_chain(self):
        res = _build()
        cell = res["bands"]["band_5000_10000"]
        wells = cell["subsea_wells"]
        assert wells == 200
        # GoM-resident heavy eligible = 2 Helix (Island Performer is light).
        assert cell["supply"]["gom_resident_eligible_count"] == 2
        # global heavy eligible = drillship 161 + heavy semi 5 = 166.
        assert cell["supply"]["global_eligible_fleet_count"] == 166
        # demand central = 200 * 0.15 * 55 (default freq central, duration median).
        exp_demand = 200 * DEFAULT_INTERVENTION_FREQUENCY["central"] * 55
        assert cell["demand"]["rig_days_per_yr"]["central"] == round(exp_demand, 1)
        # supply gom central = 2 * 0.7 * 365.
        exp_supply = 2 * DEFAULT_UTILIZATION["central"] * 365
        assert cell["supply"]["rig_days_per_yr_gom_resident"]["central"] == round(
            exp_supply, 1
        )
        ratio = cell["gap_vs_gom_resident"]["utilization_ratio"]["central"]
        assert ratio == round(exp_demand / exp_supply, 3)
        assert ratio > 1  # forward demand outstrips resident supply

    def test_empirical_xcheck_carried(self):
        res = _build()
        cell = res["bands"]["band_5000_10000"]
        assert cell["demand"]["empirical_interventions_per_well_xcheck"] == 6.434

    def test_exposure_uses_band_economics(self):
        res = _build()
        cell = res["bands"]["band_5000_10000"]
        interventions_central = 200 * DEFAULT_INTERVENTION_FREQUENCY["central"]
        assert cell["exposure_usd_per_yr"]["central"] == round(
            interventions_central * 25_135_000
        )

    def test_gom_resident_view_is_tighter_than_global(self):
        res = _build()
        cell = res["bands"]["band_5000_10000"]
        glob = cell["gap_vs_global"]["utilization_ratio"]["central"]
        gom = cell["gap_vs_gom_resident"]["utilization_ratio"]["central"]
        assert gom > glob  # resident fleet is the binding constraint

    def test_every_band_confidence_labelled(self):
        res = _build()
        for cell in res["bands"].values():
            assert cell["confidence"] == CONF_FORWARD_RISK

    def test_parameters_and_caveats_present(self):
        res = _build()
        params = res["parameters"]
        assert params["intervention_frequency_per_well_per_yr"]
        assert "engineering-assumption" in params["intervention_frequency_source"]
        assert "engineering-assumption" in params["fleet_utilization_source"]
        assert params["heavy_deepwater_classes"] == list(HEAVY_DEEPWATER_CLASSES)
        # Verifier caveats must travel with the synthesis.
        joined = " ".join(res["caveats"])
        assert "FORWARD-LOOKING" in joined
        assert "GEOGRAPHY" in joined
        assert "6%" in joined
        assert "44.5%" in joined

    def test_framing_is_access_risk_not_crossover(self):
        res = _build()
        assert "FORWARD-LOOKING ACCESS RISK" in res["framing"]
        assert "not a measured" in res["framing"].lower()
        assert "NOT a measured crossover" in res["headline"]


class TestParameterOverrides:
    def test_frequency_override_scales_demand(self):
        base = _build()
        doubled = _build(frequency={"low": 0.2, "central": 0.3, "high": 0.4})
        b = base["bands"]["band_5000_10000"]["demand"]["rig_days_per_yr"]["central"]
        d = doubled["bands"]["band_5000_10000"]["demand"]["rig_days_per_yr"]["central"]
        # central freq 0.15 -> 0.30 doubles demand.
        assert d == round(b * 2, 1)

    def test_utilization_override_scales_supply(self):
        base = _build()
        hi = _build(utilization={"low": 0.6, "central": 1.0, "high": 0.8})
        b = base["bands"]["band_5000_10000"]["supply"]["rig_days_per_yr_gom_resident"][
            "central"
        ]
        h = hi["bands"]["band_5000_10000"]["supply"]["rig_days_per_yr_gom_resident"][
            "central"
        ]
        assert h > b


class TestRealCommittedYamls:
    """End-to-end against the real committed YAMLs (no /mnt/ace dependency)."""

    def test_real_build_headline_and_bands(self):
        res = build_access_gap()
        assert "band_5000_10000" in res["bands"]
        cell = res["bands"]["band_5000_10000"]
        # 270 subsea wells on record in the deepest band (#583).
        assert cell["subsea_wells"] == 270
        # The binding GoM-resident view shows demand outstripping resident supply.
        ratio = cell["gap_vs_gom_resident"]["utilization_ratio"]["central"]
        assert ratio is not None and ratio > 1
        assert "access-RISK" in res["headline"]
