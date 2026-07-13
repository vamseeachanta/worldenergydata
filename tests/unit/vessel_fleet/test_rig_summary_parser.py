"""Tests for the Noble rig-summary text parser.

Fixtures are verbatim excerpts of pdftotext/pdfplumber output from the
committed spec PDFs (_data/raw/spec_pdfs/noble/), including their real
extraction quirks — do not "fix" the fixture strings.
"""

from worldenergydata.vessel_fleet.parsers.rig_summary import (
    _clean_number,
    parse_rig_summary_text,
)

# Noble Valiant (text PDF, 2026-03 sheet) — decimal commas + fused "ftx".
VALIANT_TEXT = """\
Noble Valiant                                        Rig Summary
General.
Rig Type :            Drillship
Rig Design :          Ship shaped, Samsu ng 96 K
Builder :             SHI, Korea
Year Built /          2013
Upgraded :
Flag :                Marshall Islands
Ratings & Dimensions
Water Depth :         12,000 ft
Drilling Depth :      40,000 ft
Length :              748 ft
Breadth :             137 ,8 ft
Depth :               62,3 ft
Draft ( Operating /   39.4 ft / 27.9 ft
Transit ) :
Moonpool :            84 ftx 41 ft
Variable Deck         44,092 kips
Load :
Hook Load :           2,500 kips on main hoist; 1,500
                      kips on auxiliaryhoist
Setback Capacity :    2,645 kips
Quarters              230
"""

# Noble Stanley Lafosse — space-before-comma quirk, extended moonpool,
# rounded drafts.
LAFOSSE_TEXT = """\
Year Built /          2014
Water Depth:          12 ,000 ft
Drilling Depth :      40,000 ft
Length:               748 ft
Breadth:              137 ft
Depth:                62 ft
Draft ( Operating /   39 ft / 28 ft
Moonpool:             115 ftx 41 ft
"""

# Noble Voyager — loads quoted in short tons, not kips.
VOYAGER_TEXT = """\
Moonpool:             84 ft x 41 ft
Variable Deck         44,092 kips
Load:
Hook Load:            1,250 sT on main hoist
"""


class TestCleanNumber:
    def test_thousands_comma(self):
        assert _clean_number("44,092") == 44092.0
        assert _clean_number("12,000") == 12000.0

    def test_decimal_comma(self):
        assert _clean_number("137,8") == 137.8
        assert _clean_number("62,3") == 62.3

    def test_plain(self):
        assert _clean_number("748") == 748.0
        assert _clean_number("39.4") == 39.4

    def test_garbage(self):
        assert _clean_number("") is None
        assert _clean_number("n/a") is None


class TestValiant:
    def setup_method(self):
        self.spec = parse_rig_summary_text(VALIANT_TEXT)

    def test_moonpool(self):
        assert self.spec["MOONPOOL_LENGTH_M"] == 25.6  # 84 ft
        assert self.spec["MOONPOOL_WIDTH_M"] == 12.5  # 41 ft

    def test_principal_dimensions(self):
        assert self.spec["LOA_M"] == 228.0  # 748 ft
        assert self.spec["BEAM_M"] == 42.0  # 137.8 ft (decimal comma)
        assert self.spec["DEPTH_M"] == 19.0  # 62.3 ft
        assert self.spec["DRAFT_M"] == 12.0  # 39.4 ft operating

    def test_depth_not_confused_with_water_depth(self):
        assert self.spec["WATER_DEPTH_RATING_FT"] == 12000.0
        assert self.spec["DRILLING_DEPTH_RATING_FT"] == 40000.0
        assert self.spec["RAW_DEPTH_FT"] == 62.3

    def test_loads(self):
        assert self.spec["VARIABLE_DECK_LOAD_ST"] == 22046  # 44,092 kips
        assert self.spec["HOOKLOAD_RATING_KIPS"] == 2500
        assert self.spec["SETBACK_CAPACITY_KIPS"] == 2645.0

    def test_general(self):
        assert self.spec["YEAR_BUILT"] == 2013
        assert self.spec["FLAG_STATE"] == "Marshall Islands"

    def test_raw_provenance(self):
        assert self.spec["RAW_MOONPOOL_FT"] == "84 x 41"
        assert self.spec["RAW_DRAFT_TRANSIT_FT"] == 27.9


class TestLafosse:
    def setup_method(self):
        self.spec = parse_rig_summary_text(LAFOSSE_TEXT)

    def test_extended_moonpool(self):
        # NSL's moonpool is longer than her sisters' — must come from her
        # own sheet, never assumed class-identical.
        assert self.spec["MOONPOOL_LENGTH_M"] == 35.1  # 115 ft
        assert self.spec["MOONPOOL_WIDTH_M"] == 12.5

    def test_space_before_comma_quirk(self):
        assert self.spec["WATER_DEPTH_RATING_FT"] == 12000.0

    def test_rounded_drafts(self):
        assert self.spec["DRAFT_M"] == 11.9  # 39 ft
        assert self.spec["RAW_DRAFT_TRANSIT_FT"] == 28.0


class TestVoyagerUnits:
    def test_short_ton_hook_load_converted_to_kips(self):
        spec = parse_rig_summary_text(VOYAGER_TEXT)
        assert spec["HOOKLOAD_RATING_KIPS"] == 2500  # 1,250 sT

    def test_absent_fields_omitted(self):
        spec = parse_rig_summary_text(VOYAGER_TEXT)
        assert "LOA_M" not in spec
        assert "YEAR_BUILT" not in spec


# Ex-Diamond Offshore "specification sheet" layout (Noble BlackHawk et al.) —
# no colon separators, metric equivalents in parentheses, loads in MT.
BLACKHAWK_TEXT = """\
 OCEAN BLACKHAWK
                         GENERAL DESCRIPTION
Design                   Gusto P10,000 DW
Year Entered Service     2015
Main Deck                757ft (230.73m) Long x 118ft (35.96m) Wide
Draft                    36ft (11.0m) Operating
Displacement             70,459 MT Operating
Variable Deck Load       22,045 MT Operating
Water Depth              12,000ft (3,658m) - designed
Drilling Depth           40,000ft (12,192m)
Moonpool                 73 ft x 32ft (22.25m x 9.75m)
"""

# Noble Patriot — moonpool without the metric parenthetical, VDL in MT with
# no space before the unit.
PATRIOT_TEXT = """\
Main Deck                246ft (75m) Long x 206.6ft (63m) Wide
Draft                    77ft (23.5m) Drilling, 36ft (10m) Transit
Variable Deck Load       3,500MT Drilling / 3500MT Transit
Moonpool                  20 ft. x 72 ft
"""

# DSS21 semis (Noble Deliverer) — Rig Summary layout but labels are indented.
DELIVERER_TEXT = """\
 Length :             384 ft
 Breadth :            256 ft
 Draft (Operating /   67.3 ft / 31.8 ft
 Moonpool:            108.3 ft x 29.5 ft
 Variable Deck        22,960 kips
"""


class TestSpecSheetLayout:
    def setup_method(self):
        self.spec = parse_rig_summary_text(BLACKHAWK_TEXT)

    def test_metric_taken_from_parentheses(self):
        assert self.spec["LOA_M"] == 230.7
        assert self.spec["BEAM_M"] == 36.0
        assert self.spec["DRAFT_M"] == 11.0
        assert self.spec["MOONPOOL_LENGTH_M"] == 22.2  # 22.25m printed
        assert self.spec["MOONPOOL_WIDTH_M"] == 9.8

    def test_year_and_displacement(self):
        assert self.spec["YEAR_BUILT"] == 2015
        assert self.spec["DISPLACEMENT_TONNES"] == 70459.0

    def test_vdl_metric_tons_to_short_tons(self):
        assert self.spec["VARIABLE_DECK_LOAD_ST"] == 24300  # 22,045 MT

    def test_depth_ratings(self):
        assert self.spec["WATER_DEPTH_RATING_FT"] == 12000.0
        assert self.spec["DRILLING_DEPTH_RATING_FT"] == 40000.0


class TestPatriotVariants:
    def test_moonpool_without_metric_parenthetical(self):
        spec = parse_rig_summary_text(PATRIOT_TEXT)
        assert spec["MOONPOOL_LENGTH_M"] == 6.1  # 20 ft, converted
        assert spec["MOONPOOL_WIDTH_M"] == 21.9  # 72 ft

    def test_vdl_no_space_before_unit(self):
        spec = parse_rig_summary_text(PATRIOT_TEXT)
        assert spec["VARIABLE_DECK_LOAD_ST"] == 3858  # 3,500 MT

    def test_drilling_draft_variant(self):
        spec = parse_rig_summary_text(PATRIOT_TEXT)
        assert spec["DRAFT_M"] == 23.5


class TestIndentedLabels:
    def test_dss21_indented_dimensions(self):
        spec = parse_rig_summary_text(DELIVERER_TEXT)
        assert spec["LOA_M"] == 117.0  # 384 ft
        assert spec["BEAM_M"] == 78.0  # 256 ft
        assert spec["DRAFT_M"] == 20.5  # 67.3 ft operating
        assert spec["MOONPOOL_LENGTH_M"] == 33.0  # 108.3 ft
        assert spec["MOONPOOL_WIDTH_M"] == 9.0  # 29.5 ft
        assert spec["VARIABLE_DECK_LOAD_ST"] == 11480  # 22,960 kips
