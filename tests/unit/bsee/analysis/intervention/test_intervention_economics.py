# ABOUTME: Unit tests for indicative intervention COST by band x scope (worldenergydata #629).
# ABOUTME: Synthetic dayrate/duration inputs + arithmetic checks + confidence-label/not_public-flag assertions. CI-safe.

"""Unit tests for worldenergydata.bsee.analysis.intervention.intervention_economics."""

import pytest

from worldenergydata.bsee.analysis.intervention.intervention_economics import (
    ASSET_DAYRATE_MAP,
    BAND_MOBILIZATION_DAYS,
    CONF_INDICATIVE,
    CONF_JACKUP_NA,
    CONF_PROXY_MODU,
    CONF_PROXY_MPSV,
    CONF_UNKNOWN,
    CONFIDENCE_LABELS,
    DEFAULT_CAMPAIGN_DURATION_DAYS,
    NULL_COST_CONFIDENCE,
    build_economics_matrix,
    build_intervention_economics,
    intervention_cost,
)
from worldenergydata.bsee.analysis.intervention.serviceability_matrix import SCOPES
from worldenergydata.bsee.analysis.intervention.well_inventory_by_band import (
    BAND_LABELS,
)

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

# Synthetic per-band mobilization adder (mirrors the shipped default shape).
SYNTH_MOBILIZATION = {
    "shelf_lt_500": {"low": 0, "median": 0, "high": 0},
    "band_500_3000": {"low": 2, "median": 3, "high": 5},
    "band_3000_5000": {"low": 4, "median": 6, "high": 9},
    "band_5000_10000": {"low": 7, "median": 10, "high": 14},
    "band_gt_10000": {"low": 10, "median": 14, "high": 20},
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
                if cell["confidence"] in NULL_COST_CONFIDENCE:
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
            mobilization_table=SYNTH_MOBILIZATION,
        )
        cell = result["economics"]["band_5000_10000"]["heavy_dead_well"]
        # base median 50 + band_5000_10000 mobilization +10 = 60 days
        assert cell["duration_days"]["median"] == 60
        # 400000 x 60 = 24,000,000 -> "$24.0M"
        assert cell["cost_usd"]["median"] == 400000 * 60
        assert "$24.0M" in result["headline"]

    def test_default_duration_table_shapes(self):
        for scope in SCOPES:
            dur = DEFAULT_CAMPAIGN_DURATION_DAYS[scope]
            assert dur["low"] < dur["median"] < dur["high"]

    def test_asset_map_defaults(self):
        assert ASSET_DAYRATE_MAP["modu"] == "modu_drillship"
        assert ASSET_DAYRATE_MAP["mpsv"] == "mpsv_osv"


class TestBandMobilization:
    def test_mobilization_added_to_base_duration(self):
        rec = intervention_cost(
            ["modu"],
            "heavy_dead_well",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
            band="band_5000_10000",
            mobilization_table=SYNTH_MOBILIZATION,
        )
        assert rec["base_duration_days"]["median"] == 50
        assert rec["mobilization_days"]["median"] == 10
        # effective = base + mobilization
        assert rec["duration_days"]["median"] == 60
        assert rec["cost_usd"]["median"] == 400000 * 60

    def test_no_band_means_no_mobilization(self):
        rec = intervention_cost(
            ["modu"],
            "heavy_dead_well",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
        )
        assert rec["mobilization_days"] == {"low": 0, "median": 0, "high": 0}
        assert rec["duration_days"]["median"] == 50

    def test_cost_increases_with_depth_band(self):
        result = build_intervention_economics(
            dayrate_bands=SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
            mobilization_table=SYNTH_MOBILIZATION,
        )
        econ = result["economics"]
        shallow = econ["band_500_3000"]["heavy_dead_well"]["cost_usd"]["median"]
        mid = econ["band_3000_5000"]["heavy_dead_well"]["cost_usd"]["median"]
        deep = econ["band_5000_10000"]["heavy_dead_well"]["cost_usd"]["median"]
        deepest = econ["band_gt_10000"]["heavy_dead_well"]["cost_usd"]["median"]
        # The whole point of the #629 fix: deeper water costs more.
        assert shallow < mid < deep < deepest

    def test_mobilization_table_overridable_to_zero(self):
        zero = {b: {"low": 0, "median": 0, "high": 0} for b in BAND_LABELS}
        rec = intervention_cost(
            ["modu"],
            "heavy_dead_well",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
            band="band_5000_10000",
            mobilization_table=zero,
        )
        assert rec["duration_days"]["median"] == 50

    def test_default_mobilization_median_matches_issue_spec(self):
        assert BAND_MOBILIZATION_DAYS["shelf_lt_500"]["median"] == 0
        assert BAND_MOBILIZATION_DAYS["band_500_3000"]["median"] == 3
        assert BAND_MOBILIZATION_DAYS["band_3000_5000"]["median"] == 6
        assert BAND_MOBILIZATION_DAYS["band_5000_10000"]["median"] == 10
        assert BAND_MOBILIZATION_DAYS["band_gt_10000"]["median"] == 14


class TestShelfJackup:
    def test_shelf_heavy_is_jackup_na(self):
        rec = intervention_cost(
            ["modu", "heavy_intervention_semi"],
            "heavy_dead_well",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
            band="shelf_lt_500",
            mobilization_table=SYNTH_MOBILIZATION,
        )
        assert rec["confidence"] == CONF_JACKUP_NA
        assert rec["cost_usd"] == {"low": None, "median": None, "high": None}
        assert rec["representative_asset"] == "jackup"
        assert "jackup" in rec["flag"].lower()

    def test_shelf_ct_is_jackup_na(self):
        rec = intervention_cost(
            ["heavy_intervention_semi", "modu"],
            "through_tubing_ct",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
            band="shelf_lt_500",
            mobilization_table=SYNTH_MOBILIZATION,
        )
        assert rec["confidence"] == CONF_JACKUP_NA

    def test_shelf_light_still_priced(self):
        # Light riserless wireline on the shelf is NOT jackup work -> still priced.
        rec = intervention_cost(
            ["rlwi_monohull", "mpsv"],
            "light_live_well",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
            band="shelf_lt_500",
            mobilization_table=SYNTH_MOBILIZATION,
        )
        assert rec["confidence"] == CONF_PROXY_MPSV
        assert rec["cost_usd"]["median"] is not None

    def test_deepwater_heavy_is_not_jackup_na(self):
        rec = intervention_cost(
            ["modu", "heavy_intervention_semi"],
            "heavy_dead_well",
            SYNTH_BANDS,
            duration_table=SYNTH_DURATIONS,
            band="band_5000_10000",
            mobilization_table=SYNTH_MOBILIZATION,
        )
        assert rec["confidence"] == CONF_INDICATIVE
        assert rec["cost_usd"]["median"] is not None


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
