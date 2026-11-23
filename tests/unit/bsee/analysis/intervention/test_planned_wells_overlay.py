# ABOUTME: Unit tests for the planned/projected GoM subsea-wells overlay (worldenergydata #587).
# ABOUTME: Pure aggregation + triangulation on a small synthetic register plus a sanity load of the committed YAML.

"""Unit tests for worldenergydata.bsee.analysis.intervention.planned_wells_overlay."""

from worldenergydata.bsee.analysis.intervention.planned_wells_overlay import (
    UNKNOWN_BAND,
    build_overlay,
    load_register,
    project_band,
    projection_pxx,
    total_on_record_wells,
    wells_by_band,
    wells_by_year,
)

# Small synthetic register exercised by the pure-function tests so they do not
# depend on the exact contents of the committed YAML.
_SYNTH = {
    "on_record_projects": [
        {
            "name": "AlphaFPS",
            "operator": "OpCo",
            "wells": 5,
            "first_oil_year": 2025,
            "water_depth_ft": 6000,  # -> band_5000_10000
        },
        {
            "name": "BetaTieback",
            "operator": "OpCo",
            "wells": 3,
            "first_oil_year": 2025,
            "water_depth_ft": 4000,  # -> band_3000_5000
        },
        {
            "name": "GammaDeep",
            "operator": "OpCo",
            "wells": 2,
            "first_oil_year": 2027,
            "water_depth_ft": None,  # -> deepwater_unknown
        },
    ],
    "analyst_rate": {
        "trees_per_year_low": 12,
        "trees_per_year_high": 20,
        "central": 16,
        "uncertainty_pct": 15,
        "sources": ["Westwood Subsea Tree Tracker", "Rystad"],
    },
}


class TestBandPlacement:
    def test_explicit_band_wins(self):
        assert project_band({"water_depth_band": "band_3000_5000"}) == "band_3000_5000"

    def test_derived_from_depth(self):
        assert project_band({"water_depth_ft": 6000}) == "band_5000_10000"

    def test_unknown_depth_buckets_to_unknown(self):
        assert project_band({"water_depth_ft": None}) == UNKNOWN_BAND
        assert project_band({}) == UNKNOWN_BAND


class TestAggregations:
    def test_wells_by_year(self):
        by_year = wells_by_year(_SYNTH)
        assert by_year == {2025: 8, 2027: 2}
        # ascending order preserved
        assert list(by_year.keys()) == [2025, 2027]

    def test_wells_by_band(self):
        by_band = wells_by_band(_SYNTH)
        assert by_band["band_5000_10000"] == 5
        assert by_band["band_3000_5000"] == 3
        assert by_band[UNKNOWN_BAND] == 2
        assert by_band["shelf_lt_500"] == 0  # zero bands still present

    def test_total(self):
        assert total_on_record_wells(_SYNTH) == 10


class TestProjection:
    def test_ordering_holds_every_year(self):
        proj = projection_pxx(_SYNTH)
        for year, vals in proj.items():
            assert vals["p10"] <= vals["p50"] <= vals["p90"], year

    def test_p50_is_floor(self):
        proj = projection_pxx(_SYNTH)
        assert proj[2025]["p50"] == 8  # 5 + 3 on-record wells in 2025
        assert proj[2027]["p50"] == 2

    def test_analyst_bracket_widens_low_floor(self):
        # central 16, +/-15% -> low ~13.6, high ~18.4. A year whose floor (2)
        # is below the analyst band gets p90 lifted to the analyst high.
        proj = projection_pxx(_SYNTH)
        assert proj[2027]["p10"] == 2  # min(2, 13.6) -> 2
        assert proj[2027]["p90"] == 18  # round(18.4)

    def test_forced_horizon(self):
        proj = projection_pxx(_SYNTH, years=[2030])
        # no on-record wells in 2030 -> floor 0, bracketed up to analyst high
        assert proj[2030]["p50"] == 0
        assert proj[2030]["p10"] == 0
        assert proj[2030]["p90"] >= proj[2030]["p50"]


class TestCommittedRegister:
    """Sanity-check the YAML that ships in the repo (authored in this worktree)."""

    def test_loads_and_totals_in_expected_range(self):
        register = load_register()
        total = total_on_record_wells(register)
        assert 70 <= total <= 80, total

    def test_known_project_band_placement(self):
        register = load_register()
        projects = {p["name"]: p for p in register["on_record_projects"]}
        assert "Whale" in projects
        # Whale (Shell, Alaminos Canyon, ~8,600 ft) sits in the 5,000-10,000 band.
        assert project_band(projects["Whale"]) == "band_5000_10000"

    def test_excludes_trion(self):
        register = load_register()
        names = {p["name"] for p in register["on_record_projects"]}
        assert not any("Trion" in n for n in names)

    def test_build_overlay_shape_and_ordering(self):
        overlay = build_overlay()
        assert overlay["totals"]["on_record_wells"] == total_on_record_wells(
            load_register()
        )
        for year, vals in overlay["projection_per_year"].items():
            assert vals["p10"] <= vals["p50"] <= vals["p90"], year
        # every project is [on_record]; analyst rate is [projected]
        assert overlay["analyst_rate"]["confidence"] == "projected"
