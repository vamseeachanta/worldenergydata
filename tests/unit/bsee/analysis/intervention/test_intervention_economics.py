# ABOUTME: Unit tests for indicative intervention COST by band x scope (worldenergydata #629).
# ABOUTME: Synthetic dayrate/duration inputs + arithmetic checks + confidence-label/not_public-flag assertions. CI-safe.

"""Unit tests for worldenergydata.bsee.analysis.intervention.intervention_economics."""

import pytest

from worldenergydata.bsee.analysis.intervention.intervention_economics import (
    ASSET_DAYRATE_MAP,
    CONF_INDICATIVE,
    CONF_PROXY_MODU,
    CONF_PROXY_MPSV,
    CONF_UNKNOWN,
    CONFIDENCE_LABELS,
    DEFAULT_CAMPAIGN_DURATION_DAYS,
    build_economics_matrix,
    build_intervention_economics,
    intervention_cost,
)
from worldenergydata.bsee.analysis.intervention.well_inventory_by_band import (
    BAND_LABELS,
)
from worldenergydata.bsee.analysis.intervention.serviceability_matrix import SCOPES

# --- Synthetic day-rate bands keyed by the snapshot taxonomy (#596) ----------
SYNTH_BANDS = {
    "modu_drillship": {
        "rate_disclosed": True,
        "median_usd_per_day": 400000,
        "band_low_usd_per_day": 300000,
        "band_high_usd_per_day": 500000,
        "confidence_labels": ["on_record"],
    },
    "mpsv_osv": {
        "rate_disclosed": True,
        "median_usd_per_day": 30000,
        "band_low_usd_per_day": 20000,
        "band_high_usd_per_day": 80000,
        "confidence_labels": ["reported"],
    },
    "heavy_intervention_semi": {
        "rate_disclosed": False,
        "median_usd_per_day": None,
        "band_low_usd_per_day": None,
        "band_high_usd_per_day": None,
        "confidence_labels": ["not_public"],
    },
    "rlwi_monohull": {
        "rate_disclosed": False,
        "median_usd_per_day": None,
        "band_low_usd_per_day": None,
        "band_high_usd_per_day": None,
        "confidence_labels": ["not_public"],
    },
}

SYNTH_DURATIONS = {
    "light_live_well": {"low": 5, "median": 10, "high": 15},
    "through_tubing_ct": {"low": 15, "median": 20, "high": 30},
    "heavy_dead_well": {"low": 30, "median": 50, "high": 60},
}


class TestArithmetic:
    def test_heavy_dead_well_modu_arithmetic(self):
        # modu is representative + public -> indicative, direct arithmetic.
        rec = intervention_cost(
            ["modu", "heavy_intervention_semi"],
            "heavy_dead_well",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
        )
        assert rec["confidence"] == CONF_INDICATIVE
        assert rec["representative_dayrate_public"] is True
        # low = band_low x dur_low; median = median x dur_median; high = high x dur_high
        assert rec["cost_usd"]["low"] == 300000 * 30
        assert rec["cost_usd"]["median"] == 400000 * 50
        assert rec["cost_usd"]["high"] == 500000 * 60

    def test_light_live_well_uses_mpsv_proxy_arithmetic(self):
        # rlwi_monohull (rep) is not public; mpsv is the eligible public proxy.
        rec = intervention_cost(
            ["rlwi_monohull", "mpsv"],
            "light_live_well",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
        )
        assert rec["confidence"] == CONF_PROXY_MPSV
        assert rec["representative_dayrate_public"] is False
        assert rec["dayrate_basis_asset"] == "mpsv"
        assert rec["cost_usd"]["low"] == 20000 * 5
        assert rec["cost_usd"]["median"] == 30000 * 10
        assert rec["cost_usd"]["high"] == 80000 * 15

    def test_through_tubing_ct_uses_modu_proxy(self):
        # heavy_intervention_semi (rep) not public; modu is the eligible proxy.
        rec = intervention_cost(
            ["heavy_intervention_semi", "modu"],
            "through_tubing_ct",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
        )
        assert rec["confidence"] == CONF_PROXY_MODU
        assert rec["dayrate_basis_asset"] == "modu"
        assert rec["cost_usd"]["median"] == 400000 * 20


class TestConfidenceLabelsAndFlags:
    def test_not_public_representative_is_never_invented(self):
        rec = intervention_cost(
            ["rlwi_monohull", "mpsv"],
            "light_live_well",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
        )
        # The representative asset's own rate stays not-public...
        assert rec["representative_dayrate_public"] is False
        # ...the priced band comes from the proxy, not the representative.
        assert rec["dayrate_band"]["asset_class"] == "mpsv_osv"
        assert "not public" in rec["flag"]

    def test_unknown_when_no_eligible_public_rate(self):
        # Both eligible assets have no public day-rate -> unknown, null cost.
        rec = intervention_cost(
            ["rlwi_monohull", "heavy_intervention_semi"],
            "light_live_well",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
        )
        assert rec["confidence"] == CONF_UNKNOWN
        assert rec["cost_usd"] == {"low": None, "median": None, "high": None}
        assert rec["dayrate_band"] is None
        assert rec["flag"] == "dayrate not public — use MODU proxy or mark unknown"

    def test_every_cell_has_a_known_confidence_label(self):
        matrix = build_economics_matrix(
            _synthetic_serviceability(),
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
        )
        for band, row in matrix.items():
            for scope, cell in row.items():
                assert cell["confidence"] in CONFIDENCE_LABELS, (band, scope)

    def test_unknown_confidence_implies_null_cost_and_vice_versa(self):
        matrix = build_economics_matrix(
            _synthetic_serviceability(),
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
        )
        for row in matrix.values():
            for cell in row.values():
                if cell["confidence"] == CONF_UNKNOWN:
                    assert cell["cost_usd"]["median"] is None
                else:
                    assert cell["cost_usd"]["median"] is not None


class TestInputValidation:
    def test_unknown_scope_raises(self):
        with pytest.raises(KeyError):
            intervention_cost(["modu"], "nope", SYNTH_BANDS)

    def test_empty_eligible_raises(self):
        with pytest.raises(ValueError):
            intervention_cost([], "heavy_dead_well", SYNTH_BANDS)

    def test_duration_table_is_overridable(self):
        custom = dict(SYNTH_DURATIONS)
        custom["heavy_dead_well"] = {"low": 1, "median": 2, "high": 3}
        rec = intervention_cost(
            ["modu"], "heavy_dead_well", SYNTH_BANDS, duration_table=custom
        )
        assert rec["duration_days"] == {"low": 1, "median": 2, "high": 3}
        assert rec["cost_usd"]["median"] == 400000 * 2


class TestBuildFull:
    def test_build_with_injected_bands_covers_all_cells(self):
        result = build_intervention_economics(
            dayrate_bands=SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
        )
        econ = result["economics"]
        for band in BAND_LABELS:
            assert band in econ
            for scope in SCOPES:
                assert scope in econ[band]
        assert "Heavy dead-well" in result["headline"]
        assert result["provenance"]["issue"].startswith("worldenergydata#629")

    def test_headline_uses_5k_10k_heavy_dead_well(self):
        result = build_intervention_economics(
            dayrate_bands=SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
        )
        cell = result["economics"]["band_5000_10000"]["heavy_dead_well"]
        # 400000 x 50 = 20,000,000 -> "$20.0M"
        assert cell["cost_usd"]["median"] == 400000 * 50
        assert "$20.0M" in result["headline"]

    def test_default_duration_table_shapes(self):
        for scope in SCOPES:
            dur = DEFAULT_CAMPAIGN_DURATION_DAYS[scope]
            assert dur["low"] < dur["median"] < dur["high"]

    def test_asset_map_defaults(self):
        assert ASSET_DAYRATE_MAP["modu"] == "modu_drillship"
        assert ASSET_DAYRATE_MAP["mpsv"] == "mpsv_osv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _synthetic_serviceability() -> dict:
    """A minimal serviceability matrix covering all bands x scopes.

    Includes one band where both eligible assets are not-public to exercise the
    ``unknown`` path.
    """
    matrix: dict = {}
    for band in BAND_LABELS:
        matrix[band] = {
            "light_live_well": {
                "eligible_asset_classes": ["rlwi_monohull", "mpsv"],
                "riser_required": False,
            },
            "through_tubing_ct": {
                "eligible_asset_classes": ["heavy_intervention_semi", "modu"],
                "riser_required": True,
            },
            "heavy_dead_well": {
                "eligible_asset_classes": ["modu", "heavy_intervention_semi"],
                "riser_required": True,
            },
        }
    # Force one unknown cell: both eligible assets not-public.
    matrix["shelf_lt_500"]["light_live_well"]["eligible_asset_classes"] = [
        "rlwi_monohull",
        "heavy_intervention_semi",
    ]
    return matrix
