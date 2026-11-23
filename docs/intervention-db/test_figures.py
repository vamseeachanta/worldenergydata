# ABOUTME: Tests for the intervention-brief figure functions + render wiring.
# ABOUTME: Asserts each SVG is valid and carries the headline numbers from the YAMLs.
"""CI-safe tests: every figure reads committed YAMLs and embeds the expected
headline numbers; a smoke test confirms the rendered brief HTML embeds the
inline SVGs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import figures  # noqa: E402
import figures_plots as P  # noqa: E402
import figures_schematics as S  # noqa: E402
import figures_svg as FS  # noqa: E402
import render_brief  # noqa: E402


def _valid_svg(markup: str) -> bool:
    return (
        markup.lstrip().startswith("<svg")
        and markup.rstrip().endswith("</svg>")
        and 'role="img"' in markup
        and markup.count("<svg") == markup.count("</svg>")
    )


# --- per-figure: valid SVG + headline number pulled from the YAML ----------
def test_wells_plot_has_deepest_band_count_and_share():
    inv = FS.load_yaml("well_inventory")["bands"]["band_5000_10000"]
    svg = P.fig_wells()
    assert _valid_svg(svg)
    assert str(inv["subsea_wells_on_record"]) in svg  # 270
    assert f"{round(inv['subsea_share'] * 100, 1):g}%" in svg  # 55.7%


def test_access_ratio_has_44x():
    ag = FS.load_yaml("access_gap")["bands"]["band_5000_10000"]
    ratio = round(ag["gap_vs_gom_resident"]["utilization_ratio"]["central"], 1)
    svg = P.fig_access_ratio()
    assert _valid_svg(svg)
    assert ratio == 4.4
    assert "4.4x" in svg
    assert "1.0x" in svg  # reference line


def test_demand_supply_has_resident_supply():
    ag = FS.load_yaml("access_gap")["bands"]["band_5000_10000"]
    supply = round(ag["supply"]["rig_days_per_yr_gom_resident"]["central"])
    svg = P.fig_demand_supply()
    assert _valid_svg(svg)
    assert f"{supply:,}" in svg  # 511


def test_exposure_has_band_values():
    bands = FS.load_yaml("access_gap")["bands"]
    svg = P.fig_exposure()
    assert _valid_svg(svg)
    assert "$375M" in svg  # band_500_3000 central
    assert "$1.0B" in svg  # band_5000_10000 central
    assert bands["band_3000_5000"]["exposure_usd_per_yr"]["central"] == 730674450


def test_fleet_plot_has_class_counts():
    bac = FS.load_yaml("fleet")["by_asset_class"]
    svg = P.fig_fleet()
    assert _valid_svg(svg)
    assert f"{bac['modu_jackup']['count']:,}" in svg  # 1,018
    assert str(bac["heavy_intervention_semi"]["count"]) in svg  # 5
    assert str(bac["rlwi_monohull"]["count"]) in svg  # 4


def test_dayrate_plot_has_drillship_band():
    dd = FS.load_yaml("fleet")["by_asset_class"]["modu_drillship"]["indicative_dayrate"]
    svg = P.fig_dayrate()
    assert _valid_svg(svg)
    assert f"med ${dd['median_usd_per_day'] / 1e3:.0f}k" in svg  # med $457k
    assert "not public" in svg


def test_planned_plot_has_2025_total():
    data = FS.load_yaml("planned")
    total_2025 = sum(
        p["wells"] for p in data["on_record_projects"] if p["first_oil_year"] == 2025
    )
    svg = P.fig_planned()
    assert _valid_svg(svg)
    assert total_2025 == 32
    assert "32" in svg
    assert "2030" in svg


def test_serviceability_schematic_valid_and_annotated():
    svg = S.fig_serviceability_schematic()
    assert _valid_svg(svg)
    assert "270 subsea wells" in svg  # deepest band count
    assert "riserless" in svg.lower()
    assert "riser" in svg.lower()
    assert "GoM-resident" in svg


def test_riser_concept_schematic_valid():
    svg = S.fig_riser_concept()
    assert _valid_svg(svg)
    assert "workover riser" in svg
    assert "subsea BOP" in svg
    assert "live well" in svg.lower()
    assert "dead well" in svg.lower()


# --- registry --------------------------------------------------------------
def test_registry_builds_nine_valid_figures():
    svgs = figures.build_all()
    assert len(svgs) == 9
    assert len(figures.FIGURES) == 9
    for key, svg in svgs.items():
        assert _valid_svg(svg), key


def test_every_figure_has_caption_and_source():
    for meta in figures.FIGURES:
        assert meta["caption"].strip()
        assert meta["source"].strip()
        assert meta["section"].strip()


# --- regenerate smoke test -------------------------------------------------
def test_render_brief_embeds_inline_svgs():
    md = (HERE / "intervention-stats-brief.generated.md").read_text(encoding="utf-8")
    html = render_brief.render_html(md, "2026-01-01")
    assert "<svg" in html
    # one inline SVG per registered figure
    assert html.count("<svg") == len(figures.FIGURES)
    # self-contained: no external resource references
    for bad in ("<img", "<script", "<link", "src=", 'href="http'):
        assert bad not in html
    # figures appear with their caption/source wrapper
    assert html.count("brief-fig") >= len(figures.FIGURES)


def test_render_html_places_figures_in_anchor_sections():
    md = (HERE / "intervention-stats-brief.generated.md").read_text(encoding="utf-8")
    html = render_brief.render_html(md, "2026-01-01")
    # the access-gap section heading must precede its four figures' source tags
    gap_idx = html.find("Access gap")
    ratio_idx = html.find("access_gap.yml (#638)")
    assert gap_idx != -1 and ratio_idx != -1 and ratio_idx > gap_idx


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
