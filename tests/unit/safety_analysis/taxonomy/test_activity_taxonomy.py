"""Tests for HSE activity taxonomy."""

from worldenergydata.safety_analysis.taxonomy.activity_taxonomy import (
    Activity,
    ActivityTaxonomy,
    Subactivity,
)


class TestSubactivity:
    def test_frozen(self):
        s = Subactivity(code="test", name="Test", description="A test")
        assert s.code == "test"
        assert s.name == "Test"

    def test_keywords_default_empty(self):
        s = Subactivity(code="t", name="T", description="D")
        assert s.keywords == ()

    def test_with_keywords(self):
        s = Subactivity(code="t", name="T", description="D", keywords=("a", "b"))
        assert len(s.keywords) == 2


class TestActivity:
    def test_minimal(self):
        a = Activity(code="TEST", name="Test", description="Test activity")
        assert a.code == "TEST"
        assert a.subactivities == ()
        assert a.naics_codes == ()

    def test_get_subactivity_found(self):
        sub = Subactivity(code="sub1", name="Sub1", description="D")
        a = Activity(
            code="A",
            name="Activity",
            description="D",
            subactivities=(sub,),
        )
        assert a.get_subactivity("sub1") is sub

    def test_get_subactivity_not_found(self):
        sub = Subactivity(code="sub1", name="Sub1", description="D")
        a = Activity(
            code="A",
            name="Activity",
            description="D",
            subactivities=(sub,),
        )
        assert a.get_subactivity("missing") is None

    def test_list_subactivity_codes(self):
        subs = (
            Subactivity(code="s1", name="S1", description="D"),
            Subactivity(code="s2", name="S2", description="D"),
        )
        a = Activity(code="A", name="A", description="D", subactivities=subs)
        assert a.list_subactivity_codes() == ["s1", "s2"]

    def test_list_subactivity_codes_empty(self):
        a = Activity(code="A", name="A", description="D")
        assert a.list_subactivity_codes() == []


class TestActivityTaxonomy:
    def test_has_14_activities(self):
        t = ActivityTaxonomy()
        assert len(t.activities) == 14

    def test_get_activity_by_code(self):
        t = ActivityTaxonomy()
        drill = t.get_activity("DRILL")
        assert drill is not None
        assert drill.name == "Drilling"

    def test_get_activity_missing(self):
        t = ActivityTaxonomy()
        assert t.get_activity("NONEXISTENT") is None

    def test_get_activity_codes(self):
        t = ActivityTaxonomy()
        codes = t.get_activity_codes()
        assert "DRILL" in codes
        assert "PROD" in codes
        assert "MARINE" in codes
        assert "ENV" in codes
        assert "PSAFE" in codes
        assert "PERS" in codes
        assert "OTHER" in codes
        assert len(codes) == 14

    def test_all_expected_codes(self):
        t = ActivityTaxonomy()
        expected = {
            "DRILL",
            "PROD",
            "CONST",
            "MARINE",
            "PIPE",
            "DIVE",
            "CRANE",
            "MAINT",
            "ENV",
            "ELEC",
            "PSAFE",
            "PERS",
            "HELI",
            "OTHER",
        }
        assert set(t.get_activity_codes()) == expected

    def test_drilling_has_subactivities(self):
        t = ActivityTaxonomy()
        drill = t.get_activity("DRILL")
        assert len(drill.subactivities) > 0
        codes = drill.list_subactivity_codes()
        assert "drilling_operations" in codes
        assert "well_control" in codes

    def test_find_by_bsee_type_blowout(self):
        t = ActivityTaxonomy()
        result = t.find_by_bsee_type("Blowout")
        assert result is not None
        assert result.code == "DRILL"

    def test_find_by_bsee_type_fire(self):
        t = ActivityTaxonomy()
        result = t.find_by_bsee_type("Fire")
        assert result is not None
        assert result.code == "PSAFE"

    def test_find_by_bsee_type_collision(self):
        t = ActivityTaxonomy()
        result = t.find_by_bsee_type("Collision")
        assert result is not None
        assert result.code == "MARINE"

    def test_find_by_bsee_type_crane(self):
        t = ActivityTaxonomy()
        result = t.find_by_bsee_type("Crane")
        assert result is not None
        assert result.code == "CRANE"

    def test_find_by_bsee_type_pollution(self):
        t = ActivityTaxonomy()
        result = t.find_by_bsee_type("Pollution")
        assert result is not None
        assert result.code == "ENV"

    def test_find_by_bsee_type_injury(self):
        t = ActivityTaxonomy()
        result = t.find_by_bsee_type("Injury")
        assert result is not None
        assert result.code == "PERS"

    def test_find_by_bsee_type_not_found(self):
        t = ActivityTaxonomy()
        assert t.find_by_bsee_type("CompletelyUnknownType") is None

    def test_find_by_bsee_type_composite(self):
        t = ActivityTaxonomy()
        result = t.find_by_bsee_type("Fire - Pollution")
        assert result is not None
        # Fire segment matches first -> PSAFE
        assert result.code == "PSAFE"

    def test_find_by_bsee_type_case_insensitive(self):
        t = ActivityTaxonomy()
        result = t.find_by_bsee_type("BLOWOUT")
        assert result is not None
        assert result.code == "DRILL"

    def test_find_by_marine_type_collision(self):
        t = ActivityTaxonomy()
        result = t.find_by_marine_type("COLLISION")
        assert result is not None
        assert result.code == "MARINE"

    def test_find_by_marine_type_fire(self):
        t = ActivityTaxonomy()
        result = t.find_by_marine_type("FIRE")
        assert result is not None
        assert result.code == "PSAFE"

    def test_find_by_marine_type_pollution(self):
        t = ActivityTaxonomy()
        result = t.find_by_marine_type("POLLUTION")
        assert result is not None
        assert result.code == "ENV"

    def test_find_by_marine_type_not_found(self):
        t = ActivityTaxonomy()
        assert t.find_by_marine_type("UNKNOWN_TYPE") is None

    def test_find_by_marine_type_case_normalized(self):
        t = ActivityTaxonomy()
        result = t.find_by_marine_type("collision")
        assert result is not None

    def test_find_by_phmsa_cause_corrosion(self):
        t = ActivityTaxonomy()
        result = t.find_by_phmsa_cause("CORROSION")
        assert result is not None
        assert result.code == "PIPE"

    def test_find_by_phmsa_cause_excavation(self):
        t = ActivityTaxonomy()
        result = t.find_by_phmsa_cause("EXCAVATION DAMAGE")
        assert result is not None
        # EXCAVATION DAMAGE is indexed under PIPE (pipeline operations)
        assert result.code == "PIPE"

    def test_find_by_phmsa_cause_all_other(self):
        t = ActivityTaxonomy()
        result = t.find_by_phmsa_cause("ALL OTHER CAUSES")
        assert result is not None
        assert result.code == "OTHER"

    def test_find_by_phmsa_cause_not_found(self):
        t = ActivityTaxonomy()
        assert t.find_by_phmsa_cause("UNKNOWN_CAUSE") is None

    def test_find_by_sic_code_drilling(self):
        t = ActivityTaxonomy()
        result = t.find_by_sic_code("1311")
        assert result is not None
        # Multiple activities may use same prefix; verify it matches one

    def test_find_by_sic_code_not_found(self):
        t = ActivityTaxonomy()
        assert t.find_by_sic_code("9999") is None

    def test_find_by_naics_code_drilling(self):
        t = ActivityTaxonomy()
        result = t.find_by_naics_code("211120")
        assert result is not None

    def test_find_by_naics_code_prefix_match(self):
        t = ActivityTaxonomy()
        result = t.find_by_naics_code("2111200001")
        assert result is not None

    def test_find_by_naics_code_not_found(self):
        t = ActivityTaxonomy()
        assert t.find_by_naics_code("999999") is None

    def test_summary(self):
        t = ActivityTaxonomy()
        s = t.summary()
        assert isinstance(s, dict)
        assert "DRILL" in s
        assert s["DRILL"] > 0
        assert len(s) == 14

    def test_all_activities_have_descriptions(self):
        t = ActivityTaxonomy()
        for a in t.activities:
            assert a.description, f"{a.code} missing description"

    def test_all_activities_have_names(self):
        t = ActivityTaxonomy()
        for a in t.activities:
            assert a.name, f"{a.code} missing name"
