# ABOUTME: Unit tests for the depth-band x scope serviceability matrix (worldenergydata #586).
# ABOUTME: Pure-function rule checks — riser-need picks the asset, HXT modifier, 5k-10k availability flag. CI-safe.

"""Unit tests for worldenergydata.bsee.analysis.intervention.serviceability_matrix."""

from pathlib import Path

import pytest

from worldenergydata.bsee.analysis.intervention.serviceability_matrix import (
    SCOPES,
    build_matrix,
    build_serviceability,
    serviceable_assets,
)
from worldenergydata.bsee.analysis.intervention.well_inventory_by_band import (
    BAND_LABELS,
    MODU_SERVICING_BANDS,
)


class TestServiceableAssets:
    def test_light_live_well_is_riserless_and_uses_light_units(self):
        cell = serviceable_assets("band_500_3000", "light_live_well")
        assert cell["riser_required"] is False
        assert "rlwi_monohull" in cell["eligible_asset_classes"]
        assert "mpsv" in cell["eligible_asset_classes"]
        assert "modu" not in cell["eligible_asset_classes"]

    def test_heavy_dead_well_always_riser_required(self):
        for band in BAND_LABELS:
            cell = serviceable_assets(band, "heavy_dead_well")
            assert cell["riser_required"] is True, band
            assert "modu" in cell["eligible_asset_classes"]
            assert "heavy_intervention_semi" in cell["eligible_asset_classes"]

    def test_through_tubing_ct_requires_riser(self):
        cell = serviceable_assets("band_3000_5000", "through_tubing_ct")
        assert cell["riser_required"] is True
        assert "rlwi_monohull" not in cell["eligible_asset_classes"]

    def test_depth_does_not_change_eligible_for_same_scope(self):
        # The whole rule: riser-need (scope) picks the asset, not the band.
        a = serviceable_assets("band_500_3000", "light_live_well")
        b = serviceable_assets("band_3000_5000", "light_live_well")
        assert a["eligible_asset_classes"] == b["eligible_asset_classes"]
        assert a["riser_required"] == b["riser_required"]
        assert "riser-need" in a["riser_rule"]

    def test_shelf_band_not_modu_servicing(self):
        cell = serviceable_assets("shelf_lt_500", "light_live_well")
        assert cell["modu_servicing_band"] is False
        assert "shelf_lt_500" not in MODU_SERVICING_BANDS
        # deepwater band is MODU-servicing
        assert (
            serviceable_assets("band_3000_5000", "heavy_dead_well")[
                "modu_servicing_band"
            ]
            is True
        )

    def test_availability_constrained_only_for_light_in_5k_10k(self):
        light = serviceable_assets("band_5000_10000", "light_live_well")
        assert light["availability_constrained"] is True
        # capability is unchanged — still riserless light units
        assert light["riser_required"] is False
        assert "rlwi_monohull" in light["eligible_asset_classes"]
        # heavy scope in the same band is NOT availability_constrained
        heavy = serviceable_assets("band_5000_10000", "heavy_dead_well")
        assert heavy["availability_constrained"] is False
        # light work in a shallower band is not flagged
        assert (
            serviceable_assets("band_500_3000", "light_live_well")[
                "availability_constrained"
            ]
            is False
        )

    def test_hxt_modifier_forces_riser_for_light_scope(self):
        vxt = serviceable_assets(
            "band_500_3000", "light_live_well", horizontal_tree=False
        )
        hxt = serviceable_assets(
            "band_500_3000", "light_live_well", horizontal_tree=True
        )
        assert vxt["riser_required"] is False
        assert hxt["riser_required"] is True
        assert hxt["hxt_modifier_applied"] is True
        assert hxt["eligible_asset_classes"] == ["modu", "heavy_intervention_semi"]
        # HXT does not change an already riser-based scope
        heavy = serviceable_assets(
            "band_500_3000", "heavy_dead_well", horizontal_tree=True
        )
        assert heavy["hxt_modifier_applied"] is False

    def test_hxt_overrides_availability_flag(self):
        # Once forced riser-based, the light-work availability flag no longer applies.
        cell = serviceable_assets(
            "band_5000_10000", "light_live_well", horizontal_tree=True
        )
        assert cell["availability_constrained"] is False
        assert cell["riser_required"] is True

    def test_unknown_band_or_scope_raises(self):
        with pytest.raises(KeyError):
            serviceable_assets("not_a_band", "light_live_well")
        with pytest.raises(KeyError):
            serviceable_assets("band_500_3000", "not_a_scope")


class TestBuildMatrix:
    def test_shape_is_band_by_scope(self):
        m = build_matrix()
        assert list(m.keys()) == list(BAND_LABELS.keys())
        for band, row in m.items():
            assert list(row.keys()) == list(SCOPES)
            for scope, cell in row.items():
                assert cell["band"] == band
                assert cell["scope"] == scope

    def test_horizontal_variant_differs_only_on_light_scope(self):
        vxt = build_matrix(horizontal_tree=False)
        hxt = build_matrix(horizontal_tree=True)
        for band in BAND_LABELS:
            assert hxt[band]["light_live_well"]["riser_required"] is True
            # heavy/CT scopes are identical between the two variants
            assert (
                vxt[band]["heavy_dead_well"]["eligible_asset_classes"]
                == hxt[band]["heavy_dead_well"]["eligible_asset_classes"]
            )


class TestBuildServiceability:
    def test_result_has_provenance_and_confidence(self):
        result = build_serviceability()
        assert "matrix" in result
        assert "horizontal_tree_variant" in result
        assert result["provenance"]["issue"] == "worldenergydata#586 (epic #582)"
        assert "confidence" in result and result["confidence"]
        assert "riser_rule" in result["rules"]

    def test_writes_yaml(self, tmp_path):
        import yaml

        out = tmp_path / "serviceability_matrix.yml"
        build_serviceability(out_path=out)
        assert out.exists()
        loaded = yaml.safe_load(out.read_text())
        assert (
            loaded["matrix"]["band_5000_10000"]["light_live_well"][
                "availability_constrained"
            ]
            is True
        )
        assert (
            loaded["matrix"]["shelf_lt_500"]["light_live_well"]["modu_servicing_band"]
            is False
        )
