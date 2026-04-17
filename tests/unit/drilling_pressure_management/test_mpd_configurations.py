"""Tests for MPD configuration taxonomy and pressure window calculations."""

import pytest

from worldenergydata.drilling_pressure_management.mpd_configurations import (
    MPD_CONFIGURATIONS,
    MPDConfiguration,
    PressureWindow,
    PressureWindowAnalyzer,
    get_configuration,
    list_config_types,
)


class TestMPDConfigurationDataclass:
    def test_cbhp_config_exists(self):
        cfg = get_configuration("CBHP")
        assert cfg.config_type == "CBHP"

    def test_pmcd_config_exists(self):
        cfg = get_configuration("PMCD")
        assert cfg.config_type == "PMCD"

    def test_dual_gradient_config_exists(self):
        cfg = get_configuration("dual_gradient")
        assert cfg.config_type == "dual_gradient"

    def test_rfc_config_exists(self):
        cfg = get_configuration("RFC")
        assert cfg.config_type == "RFC"

    def test_all_configs_have_full_name(self):
        for cfg in MPD_CONFIGURATIONS:
            assert cfg.full_name and isinstance(cfg.full_name, str)

    def test_all_configs_have_description(self):
        for cfg in MPD_CONFIGURATIONS:
            assert cfg.description and isinstance(cfg.description, str)

    def test_all_configs_have_pressure_control(self):
        for cfg in MPD_CONFIGURATIONS:
            assert cfg.pressure_control and isinstance(cfg.pressure_control, str)

    def test_all_configs_have_typical_applications(self):
        for cfg in MPD_CONFIGURATIONS:
            assert (
                cfg.typical_applications
            ), f"{cfg.config_type} has empty typical_applications"

    def test_all_configs_have_key_equipment(self):
        for cfg in MPD_CONFIGURATIONS:
            assert cfg.key_equipment, f"{cfg.config_type} has empty key_equipment"

    def test_all_configs_have_advantages(self):
        for cfg in MPD_CONFIGURATIONS:
            assert cfg.advantages, f"{cfg.config_type} has empty advantages"

    def test_all_configs_have_limitations(self):
        for cfg in MPD_CONFIGURATIONS:
            assert cfg.limitations, f"{cfg.config_type} has empty limitations"

    def test_config_is_mpd_configuration_instance(self):
        cfg = get_configuration("CBHP")
        assert isinstance(cfg, MPDConfiguration)

    def test_unknown_config_type_raises_key_error(self):
        with pytest.raises(KeyError):
            get_configuration("INVALID_TYPE")

    def test_list_config_types_returns_all_known(self):
        types = list_config_types()
        assert "CBHP" in types
        assert "PMCD" in types
        assert "dual_gradient" in types
        assert "RFC" in types


class TestPressureWindowAnalyzer:
    def setup_method(self):
        self.analyzer = PressureWindowAnalyzer()

    def test_analyze_returns_pressure_window_instance(self):
        result = self.analyzer.analyze(
            depth_m=3000.0,
            pore_pressure_psi=5000.0,
            fracture_gradient_psi=5400.0,
            mud_weight_ppg=10.5,
            flow_rate_gpm=800.0,
        )
        assert isinstance(result, PressureWindow)

    def test_pressure_window_equals_fracture_minus_pore(self):
        result = self.analyzer.analyze(
            depth_m=2500.0,
            pore_pressure_psi=4000.0,
            fracture_gradient_psi=4500.0,
            mud_weight_ppg=10.0,
            flow_rate_gpm=600.0,
        )
        assert result.pressure_window_psi == pytest.approx(500.0)

    def test_mpd_required_true_when_window_below_200(self):
        result = self.analyzer.analyze(
            depth_m=3000.0,
            pore_pressure_psi=5000.0,
            fracture_gradient_psi=5150.0,  # window = 150 psi < 200
            mud_weight_ppg=10.5,
            flow_rate_gpm=800.0,
        )
        assert result.mpd_required is True

    def test_mpd_required_false_when_window_above_500(self):
        result = self.analyzer.analyze(
            depth_m=1000.0,
            pore_pressure_psi=2000.0,
            fracture_gradient_psi=3000.0,  # window = 1000 psi >> 500
            mud_weight_ppg=9.0,
            flow_rate_gpm=400.0,
        )
        assert result.mpd_required is False

    def test_ecd_pressure_returns_positive_float(self):
        ecd = self.analyzer.ecd_pressure(
            mud_weight_ppg=10.0,
            depth_m=2000.0,
            annular_pressure_drop_psi=150.0,
        )
        assert isinstance(ecd, float)
        assert ecd > 0.0

    def test_ecd_psi_in_result_exceeds_pore_pressure(self):
        result = self.analyzer.analyze(
            depth_m=3000.0,
            pore_pressure_psi=4000.0,
            fracture_gradient_psi=5000.0,
            mud_weight_ppg=10.0,
            flow_rate_gpm=700.0,
            annular_pressure_drop_psi=300.0,
        )
        assert result.ecd_psi > result.pore_pressure_psi

    def test_ecd_pressure_increases_with_depth(self):
        shallow = self.analyzer.ecd_pressure(10.0, 1000.0, 100.0)
        deep = self.analyzer.ecd_pressure(10.0, 3000.0, 100.0)
        assert deep > shallow

    def test_ecd_pressure_increases_with_mud_weight(self):
        light = self.analyzer.ecd_pressure(9.0, 2000.0, 100.0)
        heavy = self.analyzer.ecd_pressure(14.0, 2000.0, 100.0)
        assert heavy > light

    def test_analyze_preserves_depth_in_result(self):
        result = self.analyzer.analyze(
            depth_m=1500.0,
            pore_pressure_psi=3000.0,
            fracture_gradient_psi=3600.0,
            mud_weight_ppg=9.5,
            flow_rate_gpm=500.0,
        )
        assert result.depth_m == pytest.approx(1500.0)

    def test_mpd_required_helper_boundary_at_200(self):
        assert self.analyzer.mpd_required(199.9) is True
        assert self.analyzer.mpd_required(200.1) is False

    def test_mpd_required_helper_custom_threshold(self):
        assert self.analyzer.mpd_required(300.0, threshold_psi=500.0) is True
        assert self.analyzer.mpd_required(600.0, threshold_psi=500.0) is False
