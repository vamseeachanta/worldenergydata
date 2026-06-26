# ABOUTME: Unit tests for the generated Chuck-facing intervention stats brief (worldenergydata #588).
# ABOUTME: Synthetic-fixture tests prove numbers are pulled from the YAMLs (not hard-coded), plus one real-YAML smoke check for the 114/209/270 band counts and the GoM-resident fleet section.

"""Unit tests for worldenergydata.bsee.analysis.intervention.brief_generator."""

import textwrap

import pytest

from worldenergydata.bsee.analysis.intervention.brief_generator import (
    generate_brief,
    load_fleet_catalog,
    load_well_inventory,
)

# ---------------------------------------------------------------------------
# Tiny synthetic fixtures — deliberately use marker numbers that do NOT appear
# in the real committed YAMLs, so a passing assertion proves the value flowed
# from the fixture rather than from a hard-coded constant.
# ---------------------------------------------------------------------------
_INVENTORY_YML = """\
bands:
  band_500_3000:
    label: 500-3,000 ft
    subsea_wells_on_record: 41
    total_wells_in_band: 999
    subsea_share: 0.0411
    modu_servicing: true
  band_5000_10000:
    label: 5,000-10,000 ft
    subsea_wells_on_record: 77
    total_wells_in_band: 123
    subsea_share: 0.6260
    modu_servicing: true
subsea_total: 118
subsea_depth_stats:
  count: 118
  min_ft: 1001.0
  max_ft: 8888.0
  median_ft: 4321.0
well_population_total: 12321
"""

_SERVICEABILITY_YML = """\
matrix:
  band_5000_10000:
    light_live_well:
      band: band_5000_10000
      scope: light_live_well
      eligible_asset_classes:
      - rlwi_monohull
      - mpsv
      riser_required: false
      availability_constrained: true
    heavy_dead_well:
      band: band_5000_10000
      scope: heavy_dead_well
      eligible_asset_classes:
      - modu
      riser_required: true
      availability_constrained: false
scopes:
  light_live_well: Light live-well (riserless wireline)
  heavy_dead_well: Heavy dead-well (tubing pull / recompletion / P&A)
bands:
  band_5000_10000: 5,000-10,000 ft
asset_classes:
  rlwi_monohull: Riserless light well intervention monohull
  modu: Mobile offshore drilling unit
rules:
  riser_rule: Depth does not pick the asset; riser-need picks the asset.
  hxt_modifier: HXT tubing pull forces a riser-based asset.
  availability_constraint: Light riserless work in deep water is supply-thin.
"""

_PLANNED_YML = """\
on_record_projects:
  - name: AlphaFPS
    operator: OpCo
    wells: 9
    first_oil_year: 2025
    water_depth_band: band_5000_10000
    confidence: on_record
  - name: BetaTieback
    operator: OpCo
    wells: 4
    first_oil_year: 2026
    water_depth_band: band_3000_5000
    confidence: on_record
analyst_rate:
  metric: new GoM subsea trees per year
  trees_per_year_low: 11
  trees_per_year_high: 19
  central: 15
  uncertainty_pct: 17
  confidence: projected
  horizon: through 2031
  sources:
    - Synthetic Tracker
"""

_FLEET_YML = """\
by_asset_class:
  modu_jackup:
    count: 4242
    water_depth_capability_ft:
      min: 300.0
      max: 492.0
  rlwi_monohull:
    count: 5
    water_depth_capability_ft:
      min: 6561.0
      max: 6561.0
gom_resident_dedicated_intervention:
  count: 6
  confidence: soft
  units:
  - name: Synthetic Q9000
    intervention_class: heavy
    asset_class: heavy_intervention_semi
    water_depth_rating_m: 3000.0
reconciliation_to_research:
  global_rlwi_fleet:
    figure: 15-25
    confidence: soft
    note: global riserless light well-intervention fleet
  rigs_rated_20k_psi_worldwide:
    figure: '2'
    confidence: on_record
    note: only two rigs worldwide rated to 20,000 psi
"""


@pytest.fixture
def synthetic_yamls(tmp_path):
    """Write the four synthetic source YAMLs to a tmp dir; return their paths."""
    paths = {}
    for name, body in (
        ("inventory", _INVENTORY_YML),
        ("serviceability", _SERVICEABILITY_YML),
        ("planned", _PLANNED_YML),
        ("fleet", _FLEET_YML),
    ):
        p = tmp_path / f"{name}.yml"
        p.write_text(textwrap.dedent(body))
        paths[name] = p
    return paths


def _brief(paths):
    return generate_brief(
        inventory_path=paths["inventory"],
        serviceability_path=paths["serviceability"],
        planned_path=paths["planned"],
        fleet_path=paths["fleet"],
    )


class TestSectionsPresent:
    def test_all_sections_render(self, synthetic_yamls):
        md = _brief(synthetic_yamls)
        assert "# Subsea well intervention" in md
        assert "## Takeaway" in md
        assert "## Existing subsea wells by water-depth band" in md
        assert "## Serviceability" in md
        assert "## Intervention-asset fleet" in md
        assert "## Planned / projected new subsea wells" in md
        assert "## Sources" in md

    def test_auto_generated_header_present(self, synthetic_yamls):
        md = _brief(synthetic_yamls)
        assert "AUTO-GENERATED" in md
        assert "brief_generator" in md


class TestNumbersComeFromYaml:
    def test_band_counts_pulled_from_fixture(self, synthetic_yamls):
        md = _brief(synthetic_yamls)
        # Marker counts unique to the fixture.
        assert "41" in md
        assert "77" in md
        assert "118" in md  # subsea_total

    def test_planned_floor_summed_from_fixture(self, synthetic_yamls):
        md = _brief(synthetic_yamls)
        # 9 + 4 = 13 new wells across 2 projects.
        assert "2 announced" in md
        assert "13 new subsea wells" in md

    def test_global_roster_count_from_fixture(self, synthetic_yamls):
        md = _brief(synthetic_yamls)
        assert "4,242" in md  # synthetic global jackup count

    def test_gom_resident_count_from_fixture(self, synthetic_yamls):
        md = _brief(synthetic_yamls)
        assert "~6 GoM-resident dedicated intervention units" in md

    def test_changing_a_fixture_value_changes_the_brief(
        self, synthetic_yamls, tmp_path
    ):
        before = _brief(synthetic_yamls)
        assert "118" in before
        # Mutate the subsea_total and regenerate.
        new_inventory = _INVENTORY_YML.replace("subsea_total: 118", "subsea_total: 543")
        (tmp_path / "inventory2.yml").write_text(textwrap.dedent(new_inventory))
        after = generate_brief(
            inventory_path=tmp_path / "inventory2.yml",
            serviceability_path=synthetic_yamls["serviceability"],
            planned_path=synthetic_yamls["planned"],
            fleet_path=synthetic_yamls["fleet"],
        )
        assert "543" in after


class TestConfidenceLabels:
    def test_confidence_tags_render(self, synthetic_yamls):
        md = _brief(synthetic_yamls)
        assert "[on record]" in md
        assert "[soft]" in md
        assert "[projected]" in md
        assert "[engineering judgement]" in md

    def test_global_roster_labelled_not_gom_supply(self, synthetic_yamls):
        md = _brief(synthetic_yamls)
        assert "NOT GoM supply" in md
        # The binding GoM figure leads the fleet section.
        gom_idx = md.index("binding supply")
        roster_idx = md.index("CONTEXT ONLY")
        assert gom_idx < roster_idx


class TestWriteOut:
    def test_writes_file_when_out_path_given(self, synthetic_yamls, tmp_path):
        out = tmp_path / "sub" / "brief.generated.md"
        md = generate_brief(
            out_path=out,
            inventory_path=synthetic_yamls["inventory"],
            serviceability_path=synthetic_yamls["serviceability"],
            planned_path=synthetic_yamls["planned"],
            fleet_path=synthetic_yamls["fleet"],
        )
        assert out.exists()
        assert out.read_text() == md


class TestRealCommittedYamls:
    """One end-to-end check against the real committed YAMLs (no /mnt/ace dep)."""

    def test_real_band_counts_and_gom_fleet_section(self):
        # Sanity: the committed inventory really carries the headline counts.
        inv = load_well_inventory()
        bands = inv["bands"]
        assert bands["band_500_3000"]["subsea_wells_on_record"] == 114
        assert bands["band_3000_5000"]["subsea_wells_on_record"] == 209
        assert bands["band_5000_10000"]["subsea_wells_on_record"] == 270

        fleet = load_fleet_catalog()
        assert fleet["gom_resident_dedicated_intervention"]["count"] == 3

        md = generate_brief()
        assert "114" in md
        assert "209" in md
        assert "270" in md
        assert "GoM-resident dedicated intervention units (the binding supply)" in md
        assert "NOT GoM supply" in md
