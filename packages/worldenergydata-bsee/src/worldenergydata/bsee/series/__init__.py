"""Shared annual observations, water-depth bands and figures for the BSEE well series."""

from .annual import BAND_COLORS, BANDS, depth_band, with_trends
from .charts import (
    assign_scales,
    interactive,
    make_figure,
    render,
    write_figures,
    write_manifest,
)

__all__ = [
    "BANDS",
    "BAND_COLORS",
    "assign_scales",
    "depth_band",
    "interactive",
    "make_figure",
    "render",
    "with_trends",
    "write_figures",
    "write_manifest",
]
