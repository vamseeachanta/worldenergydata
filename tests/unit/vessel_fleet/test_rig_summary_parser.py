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
