"""Tests for vessel fleet scrape parser."""

from worldenergydata.vessel_fleet.collectors.scrape_parser import (
    _extract_noble_pdf_links,
    _extract_seadrill_tech_sheet_links,
    _match_pdf_link,
    _normalize_noble_name,
    _normalize_seadrill_rig_type,
    _strip_owner_prefix,
    classify_rig_type_by_water_depth,
    parse_water_depth_string,
)


class TestClassifyRigTypeByWaterDepth:
    def test_jackup(self):
        assert classify_rig_type_by_water_depth(300) == "jack_up"

    def test_jackup_boundary(self):
        assert classify_rig_type_by_water_depth(500) == "jack_up"

    def test_semi_submersible(self):
        assert classify_rig_type_by_water_depth(5000) == "semi_submersible"

    def test_semi_submersible_low(self):
        assert classify_rig_type_by_water_depth(501) == "semi_submersible"

    def test_drillship(self):
        assert classify_rig_type_by_water_depth(12000) == "drillship"

    def test_drillship_boundary(self):
        assert classify_rig_type_by_water_depth(10000) == "drillship"

    def test_zero(self):
        assert classify_rig_type_by_water_depth(0) == "jack_up"


class TestParseWaterDepthString:
    def test_simple_number(self):
        assert parse_water_depth_string("12000") == 12000.0

    def test_with_commas(self):
        assert parse_water_depth_string("12,000") == 12000.0

    def test_with_ft_suffix(self):
        assert parse_water_depth_string("12,000 ft") == 12000.0

    def test_with_ft_dot_suffix(self):
        assert parse_water_depth_string("12000 ft.") == 12000.0

    def test_with_feet_suffix(self):
        assert parse_water_depth_string("500 feet") == 500.0

    def test_whitespace(self):
        assert parse_water_depth_string("  12000  ") == 12000.0

    def test_none(self):
        assert parse_water_depth_string(None) is None

    def test_empty(self):
        assert parse_water_depth_string("") is None

    def test_whitespace_only(self):
        assert parse_water_depth_string("   ") is None

    def test_invalid(self):
        assert parse_water_depth_string("abc") is None

    def test_just_ft(self):
        assert parse_water_depth_string("ft") is None


class TestNormalizeNobleName:
    def test_normal(self):
        assert _normalize_noble_name("Noble Resolve") == "Noble Resolve"

    def test_trailing_space(self):
        assert _normalize_noble_name("Noble Resolve ") == "Noble Resolve"

    def test_leading_space(self):
        assert _normalize_noble_name(" Noble Resolve") == "Noble Resolve"


class TestStripOwnerPrefix:
    def test_noble_prefix(self):
        assert _strip_owner_prefix("Noble Resolve") == "Resolve"

    def test_ocean_prefix(self):
        assert _strip_owner_prefix("Ocean Apex") == "Apex"

    def test_maersk_prefix(self):
        assert _strip_owner_prefix("Maersk Developer") == "Developer"

    def test_no_prefix(self):
        assert _strip_owner_prefix("Deepwater Titan") == "Deepwater Titan"

    def test_case_insensitive(self):
        assert _strip_owner_prefix("NOBLE Resolve") == "Resolve"

    def test_whitespace_stripped_then_no_prefix(self):
        # Input without owner prefix but with whitespace
        assert _strip_owner_prefix("  Deepwater Titan  ") == "Deepwater Titan"


class TestMatchPdfLink:
    def test_direct_match(self):
        pdf_links = {"Noble Resolve": "http://example.com/resolve.pdf"}
        assert _match_pdf_link("Noble Resolve", pdf_links) == "http://example.com/resolve.pdf"

    def test_case_insensitive(self):
        pdf_links = {"noble resolve": "http://example.com/resolve.pdf"}
        assert _match_pdf_link("Noble Resolve", pdf_links) == "http://example.com/resolve.pdf"

    def test_owner_prefix_mismatch(self):
        pdf_links = {"Ocean Apex": "http://example.com/apex.pdf"}
        assert _match_pdf_link("Noble Apex", pdf_links) == "http://example.com/apex.pdf"

    def test_partial_match(self):
        pdf_links = {"Noble Resolve X": "http://example.com/resolve.pdf"}
        assert _match_pdf_link("Noble Resolve", pdf_links) == "http://example.com/resolve.pdf"

    def test_no_match(self):
        pdf_links = {"Something Else": "http://example.com/other.pdf"}
        assert _match_pdf_link("Noble Resolve", pdf_links) is None

    def test_empty_links(self):
        assert _match_pdf_link("Noble Resolve", {}) is None


class TestExtractNoblePdfLinks:
    def test_basic(self):
        links = [
            {"href": "http://noble.com/fleet-details/2024/Ocean-Apex/default.aspx", "text": "Rig Summary"},
            {"href": "http://noble.com/apex.pdf", "text": "Download Summary PDF"},
        ]
        result = _extract_noble_pdf_links(links)
        assert "Ocean Apex" in result
        assert result["Ocean Apex"] == "http://noble.com/apex.pdf"

    def test_no_rig_summary(self):
        links = [
            {"href": "http://noble.com/page", "text": "Other Link"},
        ]
        result = _extract_noble_pdf_links(links)
        assert result == {}

    def test_multiple_rigs(self):
        links = [
            {"href": "http://noble.com/fleet-details/2024/Ocean-Apex/default.aspx", "text": "Rig Summary"},
            {"href": "http://noble.com/apex.pdf", "text": "Download Summary PDF"},
            {"href": "http://noble.com/fleet-details/2024/Noble-Resolve/default.aspx", "text": "Rig Summary"},
            {"href": "http://noble.com/resolve.pdf", "text": "Download Summary PDF"},
        ]
        result = _extract_noble_pdf_links(links)
        assert len(result) == 2
        assert "Ocean Apex" in result
        assert "Noble Resolve" in result

    def test_rig_summary_without_pdf(self):
        links = [
            {"href": "http://noble.com/fleet-details/2024/Ocean-Apex/default.aspx", "text": "Rig Summary"},
            {"href": "http://noble.com/other", "text": "Other"},
        ]
        result = _extract_noble_pdf_links(links)
        assert result == {}


class TestExtractSeadrillTechSheetLinks:
    def test_basic(self):
        links = [
            {"href": "http://seadrill.com/rig.pdf", "text": "Technical Sheet"},
        ]
        result = _extract_seadrill_tech_sheet_links(links)
        assert result == ["http://seadrill.com/rig.pdf"]

    def test_non_pdf_filtered(self):
        links = [
            {"href": "http://seadrill.com/rig.html", "text": "Technical Sheet"},
        ]
        result = _extract_seadrill_tech_sheet_links(links)
        assert result == []

    def test_non_tech_sheet_filtered(self):
        links = [
            {"href": "http://seadrill.com/rig.pdf", "text": "Other"},
        ]
        result = _extract_seadrill_tech_sheet_links(links)
        assert result == []

    def test_multiple(self):
        links = [
            {"href": "http://seadrill.com/rig1.pdf", "text": "Technical Sheet"},
            {"href": "http://seadrill.com/other.html", "text": "Info"},
            {"href": "http://seadrill.com/rig2.pdf", "text": "Technical Sheet"},
        ]
        result = _extract_seadrill_tech_sheet_links(links)
        assert len(result) == 2

    def test_empty(self):
        assert _extract_seadrill_tech_sheet_links([]) == []


class TestNormalizeSeadrillRigType:
    def test_drillship(self):
        assert _normalize_seadrill_rig_type("Drillship") == "drillship"

    def test_semi_submersible(self):
        assert _normalize_seadrill_rig_type("Semi-submersible") == "semi_submersible"

    def test_jack_up(self):
        assert _normalize_seadrill_rig_type("Jack-up") == "jack_up"

    def test_trailing_space(self):
        assert _normalize_seadrill_rig_type("Drillship ") == "drillship"

    def test_unknown_type(self):
        assert _normalize_seadrill_rig_type("Tender-assist") == "tender_assist"

    def test_case_insensitive(self):
        assert _normalize_seadrill_rig_type("DRILLSHIP") == "drillship"
