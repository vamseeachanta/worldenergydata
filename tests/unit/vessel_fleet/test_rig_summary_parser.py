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


# Transocean deepwater.com "RigSpecs" layout (Deepwater Titan) — compound
# Dimensions/Drafts lines, metric in parentheses, loads in short tons.
TITAN_TEXT = """\
Design / Generation                Jurong Espadon JE3T Ultra Deepwater Drillship
Year Entered Service / Significant Upgrades                                2023
Flag                                                           Marshall Islands
Dimensions              817 ft. (249 m) x 139.4 ft. (42.5 m) x 64 ft. (19.5 m) Depth
Drafts               Maximum Operating 38.05 ft. (11.6 m) / Transit 26.3 ft. (8 m)
Displacement                                     103,066 st (93,500 mt) (Loadline)
Maximum Water Depth 12,000 ft (3,657.6 m) designed / 8,000 ft (2,438 m) outfitted
Maximum Drilling Depth                                         40,000 ft (12,192 m)
Gross Hook Loads     (Main) 1,700 st. (1,542 mt) capacity
Moonpool              92ft (28m) length x 29.5ft (9m) width
"""

# Transocean semi variant (Spitsbergen): worded Dimensions, "m." with dot,
# no third dimension.
SPITSBERGEN_TEXT = """\
  Design / Generation                                    Aker H-6e Semi-submersible
  Dimensions                    295 ft. (90 m) long x 230 ft. (70 m) wide (main deck)
  Drafts                                 75 ft. (24 m) operating / 31 ft. (9.5 m) Transit
  Hookload Capacity (Main) 1,000 st (908 mt) capacity
  Moonpool             34 ft. (10.3 m) x 75 ft. (23 m.) Outfitted with skid rails.
"""


class TestTransoceanLayout:
    def setup_method(self):
        self.spec = parse_rig_summary_text(TITAN_TEXT)

    def test_dimensions_metric(self):
        assert self.spec["LOA_M"] == 249.0
        assert self.spec["BEAM_M"] == 42.5
        assert self.spec["DEPTH_M"] == 19.5

    def test_drafts_and_displacement(self):
        assert self.spec["DRAFT_M"] == 11.6
        assert self.spec["RAW_DRAFT_TRANSIT_FT"] == 26.3
        assert self.spec["DISPLACEMENT_TONNES"] == 93500.0

    def test_moonpool_and_hook(self):
        assert self.spec["MOONPOOL_LENGTH_M"] == 28.0
        assert self.spec["MOONPOOL_WIDTH_M"] == 9.0
        assert self.spec["HOOKLOAD_RATING_KIPS"] == 3400  # 1,700 st

    def test_general(self):
        assert self.spec["YEAR_BUILT"] == 2023
        assert self.spec["FLAG_STATE"] == "Marshall Islands"
        assert self.spec["WATER_DEPTH_RATING_FT"] == 12000.0

    def test_semi_variant(self):
        spec = parse_rig_summary_text(SPITSBERGEN_TEXT)
        assert spec["LOA_M"] == 90.0  # worded "long x ... wide", 2 dims only
        assert spec["BEAM_M"] == 70.0
        assert "DEPTH_M" not in spec
        assert spec["MOONPOOL_WIDTH_M"] == 23.0  # "(23 m.)" with dot
        assert spec["HOOKLOAD_RATING_KIPS"] == 2000  # Hookload Capacity variant


# Valaris sidebar layout — label on its own line, value 1-2 lines below AT THE
# SAME COLUMN (body text interleaves); jackup loads in lbs.
VALARIS_JACKUP_TEXT = """\
  VALARIS 120
                                       Keppel FELS, Ultra-Enhanced Super 'A' Class • Year in Service: 2013

   CAPACITIES                                                            PRIMARY RIG
      Rotary Load:                       Potable Water:
                                                                           CHARACTERISTICS
      2,500,000 lbs                      3,500 bbl                         Max. Deployed Leg Length:
      Setback Load:                      Drill Water:                      471ft
      1,450,000 lbs                      25,179 bbl
                                                                           Leg Length:
                                                                           540ft

                                                                           Hull Length:
                                                                           246ft

                                                                           Hull Width:
                                                                           250ft
                                                                           Maximum Drilling Depth:
      Woolslayer 160ft x 32ft x 35ft     Varco TDS-8SA, 750t
                                                                           40,000ft
                                                                           Hook Load:
                                                                           2,500,000 lbs
                                                                           Cantilever Skid Out:
                                                                           80ft
"""


class TestValarisLayout:
    def setup_method(self):
        self.spec = parse_rig_summary_text(VALARIS_JACKUP_TEXT)

    def test_column_aware_value_matching(self):
        # 40,000ft sits two lines under its label with derrick dims
        # ("160ft x 32ft x 35ft") interleaved at a different column.
        assert self.spec["DRILLING_DEPTH_RATING_FT"] == 40000.0

    def test_jackup_fields(self):
        assert self.spec["LEG_LENGTH_FT"] == 540.0  # not Max. Deployed 471
        assert self.spec["CANTILEVER_REACH_FT"] == 80.0
        assert self.spec["LOA_M"] == 75.0  # Hull Length 246 ft
        assert self.spec["BEAM_M"] == 76.2  # Hull Width 250 ft

    def test_lbs_loads_to_kips(self):
        assert self.spec["HOOKLOAD_RATING_KIPS"] == 2500
        assert self.spec["SETBACK_CAPACITY_KIPS"] == 1450

    def test_subtitle_year_and_design(self):
        assert self.spec["YEAR_BUILT"] == 2013
        assert "Keppel FELS" in self.spec["RIG_DESIGN"]


# Seadrill same-line table layout (West Elara jackup) — wide-gap label/value
# pairs, loads in short tons, jackup legs/spud cans/cantilever.
SEADRILL_TEXT = """\
GENERAL (U.S.)                                                     DRILLING PACKAGE

Built                             2011 Jurong Shipyard, Singapore  Derrick             1,100 st

Design                            Gusto MSC CJ70-X150              Cantilever Envelope             100 ft x 65 ft

Flag/Class                        Norway / DNV                     Top Drive           SENSE 1,000 st

Dimensions                        290 ft x 320 ft x 39 ft          Drawworks           SENSE 5,600 hp 935 st

Draft                             24 ft (loadline)                 Rotary Table        49.5 in

Displacement                      43,000 st (at loadline)          Tubular Handling    HMH RNX

Variable Load                     4,400 st transit / 11,000 st drilling

Legs                              3 x 673 ft / 581 ft usable

Spud Cans                         75 ft
"""


class TestSeadrillLayout:
    def setup_method(self):
        self.spec = parse_rig_summary_text(SEADRILL_TEXT)

    def test_general(self):
        assert self.spec["YEAR_BUILT"] == 2011
        assert self.spec["FLAG_STATE"] == "Norway"
        assert self.spec["RIG_DESIGN"] == "Gusto MSC CJ70-X150"  # column-clean

    def test_three_part_dimensions(self):
        assert self.spec["LOA_M"] == 88.4  # 290 ft
        assert self.spec["BEAM_M"] == 97.5  # 320 ft
        assert self.spec["DEPTH_M"] == 11.9  # 39 ft

    def test_loadline_draft_and_st_displacement(self):
        assert self.spec["DRAFT_M"] == 7.3  # 24 ft (loadline)
        assert self.spec["DISPLACEMENT_TONNES"] == 39009  # 43,000 st

    def test_vdl_drilling_value(self):
        assert self.spec["VARIABLE_DECK_LOAD_ST"] == 11000  # drilling, not transit

    def test_jackup_fields(self):
        assert self.spec["LEG_LENGTH_FT"] == 673.0  # "3 x 673 ft" -> per-leg
        assert self.spec["SPUD_CAN_DIAMETER_FT"] == 75.0
        assert self.spec["CANTILEVER_REACH_FT"] == 100.0


# Borr Drilling dotted-leader jackup layout (Thor) — dotted/ellipsis leaders,
# kips-quoted displacement and deck loads.
BORR_TEXT = """\
Design / Generation ..................................... Keppel FELS Super B Class, Bigfoot
Delivery ............................................................................................................ 2019
Flag ................................................................................................................ Liberia
Overall Dimensions ....................................... 247 ft long x 230 ft wide x 27 ft deep
Legs .......................................................................... 3x 517 ft long, triangular truss
Drafts .......................................................................................... 19 ft load line draft
Load Line Displacement ................................................................. 41,625.45 kips
Variable Deck ...................................... 9,700 kips elevated / 5,500 kips field transit
Operating Water Depth .................................................................................. 400 ft
Maximum Drilling Depth ........................................................................... 35,000 ft
Cantilever/ Drill floor               75 ft / 15 ft Port & 15 ft Stbd
"""

# Newbuild variant (Forseti) — unicode-ellipsis leaders, MT-quoted loads,
# transit-only draft, "(3) 554.7 ft." legs.
BORR_NEWBUILD_TEXT = """\
Design / Generation …………………………………………Friede & Goldman JU3000N
Year Entered Service / Significant Upgrades …………………………………….. 2013
Flag ………………………………………………………………...……...………….. Liberia
Overall Dimensions .................................... ………231 ft long x 277 ft wide x 31 ft deep
Legs …………………………………………...……………… (3) 554.7 ft. long, Triangular
Drafts …………………………………………………………………………….. 19 ft transit
Displacement…………………………………………………………………. 26,109.65 MT
Variable Deck ........................ ………………………………………... 5,433 MT operating
Operating Water Depth ............................................. 400 ft. designed / 400 ft. outfitted
Maximum Drilling Depth .................................................................................. 35,000 ft
"""


class TestBorrLayout:
    def setup_method(self):
        self.spec = parse_rig_summary_text(BORR_TEXT)

    def test_dotted_leaders(self):
        assert self.spec["YEAR_BUILT"] == 2019
        assert self.spec["FLAG_STATE"] == "Liberia"
        assert self.spec["RIG_DESIGN"] == "Keppel FELS Super B Class, Bigfoot"

    def test_worded_dimensions(self):
        assert self.spec["LOA_M"] == 75.3  # 247 ft
        assert self.spec["BEAM_M"] == 70.1  # 230 ft
        assert self.spec["DEPTH_M"] == 8.2  # 27 ft

    def test_kips_conversions(self):
        assert self.spec["DISPLACEMENT_TONNES"] == 18881  # 41,625.45 kips
        assert self.spec["VARIABLE_DECK_LOAD_ST"] == 4850  # 9,700 kips elevated

    def test_jackup_fields(self):
        assert self.spec["LEG_LENGTH_FT"] == 517.0
        assert self.spec["CANTILEVER_REACH_FT"] == 75.0
        assert self.spec["WATER_DEPTH_RATING_FT"] == 400.0
        assert self.spec["DRILLING_DEPTH_RATING_FT"] == 35000.0

    def test_load_line_draft(self):
        assert self.spec["DRAFT_M"] == 5.8  # 19 ft load line


class TestBorrNewbuildVariant:
    def setup_method(self):
        self.spec = parse_rig_summary_text(BORR_NEWBUILD_TEXT)

    def test_ellipsis_leaders_and_mt_loads(self):
        assert self.spec["YEAR_BUILT"] == 2013  # via Year Entered Service
        assert self.spec["DISPLACEMENT_TONNES"] == 26109.65  # vendor MT, as printed
        assert self.spec["VARIABLE_DECK_LOAD_ST"] == 5989  # 5,433 MT

    def test_parenthesized_legs(self):
        assert self.spec["LEG_LENGTH_FT"] == 554.7  # "(3) 554.7 ft."

    def test_transit_only_draft(self):
        assert "DRAFT_M" not in self.spec
        assert self.spec["RAW_DRAFT_TRANSIT_FT"] == 19.0


# Equipment-capability extraction (#1006) — verbatim excerpts from committed
# PDFs across layouts.
EQUIPMENT_TEXT = """\
Quarters              230
MPD & HPHT             Equipped for MPD and HPHT operations
Derrick                Dual dynamic derrick 210 ft (64 m) clear internal working
Cranes               Three (3) 110st (100mt) knuckle boom cranes at 65.6 ft. (20m)
Gantry Crane with two (2) x 330st (300mt) main hoist and two
Tree Handling         One (1) 1102st (1000mt) Combined Xmas Tree Trolley and
Riser Tensioner /      (16) NOV DWRT-225-50; 225 kips/ea crane wire
"""

EQUIPMENT_ACCOMMODATION_TEXT = """\
Accommodation                                                            220 persons
Station Keeping      Kongsberg DP3
"""


class TestEquipmentExtraction:
    def setup_method(self):
        self.spec = parse_rig_summary_text(EQUIPMENT_TEXT)

    def test_quarters(self):
        assert self.spec["QUARTERS_CAPACITY"] == 230

    def test_mpd_positive_mention_only(self):
        assert self.spec["MPD_CAPABLE"] is True
        no_mpd = parse_rig_summary_text(EQUIPMENT_ACCOMMODATION_TEXT)
        assert "MPD_CAPABLE" not in no_mpd  # unknown != false

    def test_dual_activity(self):
        # "Dual dynamic derrick" does not qualify; needs dual-activity/derrick
        spec = parse_rig_summary_text("Derrick   Dual Activity NOV bottleneck")
        assert spec["DUAL_ACTIVITY"] is True

    def test_crane_max_excludes_trolley_and_tensioner(self):
        # The 330 st / (300 mt) gantry beats the 110 st deck cranes — the
        # vendor's own metric value (300 mt) wins over the st conversion.
        # The 1102 st Xmas-tree trolley and the tensioner "crane wire" line
        # are excluded.
        assert self.spec["CRANE_MAIN_CAPACITY_T"] == 300.0

    def test_accommodation_variant(self):
        spec = parse_rig_summary_text(EQUIPMENT_ACCOMMODATION_TEXT)
        assert spec["QUARTERS_CAPACITY"] == 220


# Stena Drilling dotted-leader layout (Carron class) — UPPERCASE labels,
# metric-first with imperial parentheses; Don semi variant differences.
STENA_TEXT = """\
RIG TYPE / DESIGN.................... Dynamically Positioned, Harsh Environment DP3 Drillship
YEAR ENTERED SERVICE / ........
SIGNIFICANT UPGRADES........... August 2008 / N/A
FLAG......................................... United Kingdom (UK)
DIMENSIONS ............................ 228 m (Long) x 42m (Wide) x 19m (moulded depth)
DRAFTS..................................... 12m (39.4 ft) operating / 8.5m (27.9 ft) transit
ACCOMODATION...................... 180, upgradeable to 220
VARIABLE DECK (OPERATING)... 20,000Mt @12m
MAXIMUM WATER DEPTH ....... 3,000m designed / 3,000m outfitted
                            10,000 ft designed / 10,000 ft outfitted
MAXIMUM DRILLING DEPTH .... 10,700m / 35,104 ft
MAST........................................ NOV Dual Hoisting and Drilling Tower
HOOKLOAD CAPACITY .............. [MAIN] 1000st static hookload (2,000,000 lbs)
MOONPOOL ............................. 84ft x 41ft (25.60m x 12.48m)
with full Managed Pressure Drilling (MPD) capabilities
"""

STENA_DON_TEXT = """\
RIG TYPE / DESIGN.................... Harsh Environment POSMOOR ATAR Twin Pontoon, 6 columns CS30 Semi-
YEAR ENTERED SERVICE /
SIGNIFICANT UPGRADES........... 2001 / 2015 - Mid Life Upgrade
FLAG.......................................... United Kingdom (UK)                             Systems
DIMENSIONS............................. 95.5 m (Long) x 81.0m (Wide)
DRAFTS...................................... 21.5m operating / 11.5-12m transit
MAXIMUM WATER DEPTH ....... 650m / 2132ft
HOOKLOAD CAPACITY .............. 750 short ton (680 metric ton)
MOONPOOL ................            70ft x 23ft (21.50 m x 7.00m)
"""


class TestStenaLayout:
    def setup_method(self):
        self.spec = parse_rig_summary_text(STENA_TEXT)

    def test_metric_first_dimensions(self):
        assert self.spec["LOA_M"] == 228.0
        assert self.spec["BEAM_M"] == 42.0
        assert self.spec["DEPTH_M"] == 19.0

    def test_drafts_with_imperial_parens(self):
        assert self.spec["DRAFT_M"] == 12.0
        assert self.spec["RAW_DRAFT_OPERATING_FT"] == 39.4
        assert self.spec["RAW_DRAFT_TRANSIT_FT"] == 27.9

    def test_water_depth_from_ft_continuation_line(self):
        assert self.spec["WATER_DEPTH_RATING_FT"] == 10000.0

    def test_year_from_upgrades_line(self):
        assert self.spec["YEAR_BUILT"] == 2008

    def test_loads_and_moonpool(self):
        assert self.spec["HOOKLOAD_RATING_KIPS"] == 2000  # 1000 st main
        assert self.spec["VARIABLE_DECK_LOAD_ST"] == 22046  # 20,000 Mt
        assert self.spec["MOONPOOL_LENGTH_M"] == 25.6  # metric parenthetical
        assert self.spec["MOONPOOL_WIDTH_M"] == 12.5

    def test_equipment_flags(self):
        assert self.spec["MPD_CAPABLE"] is True
        assert self.spec["DUAL_ACTIVITY"] is True  # Dual Hoisting tower
        assert self.spec["QUARTERS_CAPACITY"] == 180  # lower bound

    def test_don_semi_variant(self):
        spec = parse_rig_summary_text(STENA_DON_TEXT)
        assert spec["LOA_M"] == 95.5  # two-part dimensions, no depth
        assert "DEPTH_M" not in spec
        assert spec["WATER_DEPTH_RATING_FT"] == 2132.0  # same-line m/ft form
        assert spec["HOOKLOAD_RATING_KIPS"] == 1500  # 750 short ton
        assert spec["FLAG_STATE"] == "United Kingdom (UK)"  # column bleed cut
        assert spec["YEAR_BUILT"] == 2001


class TestIndentedLabels:
    def test_dss21_indented_dimensions(self):
        spec = parse_rig_summary_text(DELIVERER_TEXT)
        assert spec["LOA_M"] == 117.0  # 384 ft
        assert spec["BEAM_M"] == 78.0  # 256 ft
        assert spec["DRAFT_M"] == 20.5  # 67.3 ft operating
        assert spec["MOONPOOL_LENGTH_M"] == 33.0  # 108.3 ft
        assert spec["MOONPOOL_WIDTH_M"] == 9.0  # 29.5 ft
        assert spec["VARIABLE_DECK_LOAD_ST"] == 11480  # 22,960 kips
