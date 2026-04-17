"""Tests for Visualization class init, colors, and layout."""

import pytest

from worldenergydata.common.legacy.visualization import Visualization

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestVisualizationInit:
    def test_default_init(self):
        v = Visualization()
        assert v.plot_data == {"data": [], "layout": {}}
        assert v.current_color_index == 0
        assert v.cfg is None

    def test_with_cfg(self):
        cfg = {"x": [1], "y": [2]}
        v = Visualization(cfg=cfg)
        assert v.cfg == cfg
        assert v.default_cfg["type"] == "scatter"
        assert v.default_cfg["mode"] == "lines"

    def test_default_layout(self):
        v = Visualization()
        assert v.default_layout["title"] == "Title"
        assert v.default_layout["xaxis"]["title"] == "X Label"
        assert v.default_layout["yaxis"]["title"] == "Y Label"


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------


class TestColors:
    def test_colors_populated(self):
        v = Visualization()
        assert len(v.colors) == 20

    def test_colors_are_hex(self):
        v = Visualization()
        for color in v.colors:
            assert color.startswith("#")
            assert len(color) == 7

    def test_first_color(self):
        v = Visualization()
        assert v.colors[0] == "#1f77b4"


# ---------------------------------------------------------------------------
# Default config structure
# ---------------------------------------------------------------------------


class TestDefaultCfg:
    def test_cfg_keys(self):
        v = Visualization(cfg={"test": True})
        assert "data_source" in v.default_cfg
        assert "type" in v.default_cfg
        assert "mode" in v.default_cfg
        assert "name" in v.default_cfg
        assert "x" in v.default_cfg
        assert "y" in v.default_cfg
        assert "line" in v.default_cfg

    def test_default_cfg_none_without_cfg(self):
        v = Visualization()
        assert v.default_cfg == {}
