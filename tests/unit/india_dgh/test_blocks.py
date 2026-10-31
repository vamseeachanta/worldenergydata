"""Block-table parsing and the shipped awarded-block table.

Table layouts mirror the DGH award lists (https://www.dghindia.gov.in, OALP
bid rounds I-IX): rounds I-III print block and H1 bidder only; rounds IV and
VIII print a 'Type / Basin / State' description and area in sq. km, with cells
wrapped over several text rows. Synthetic rows below copy those layouts.
"""

import math

import pandas as pd
import pytest

from worldenergydata.india_dgh import load_awarded_blocks, load_basins
from worldenergydata.india_dgh.blocks import (
    CODE_BASIN,
    acreage_from_code,
    basin_category,
    normalize_block_code,
    parse_area,
    table_records,
)

# Blocks awarded per round, counted in each round's DGH award list.
ROUND_COUNTS = {
    "OALP-I": 55,
    "OALP-II": 14,
    "OALP-III": 18,
    "OALP-IV": 7,
    "OALP-V": 11,
    "OALP-VI": 21,
    "OALP-VII": 8,
    "OALP-VIII": 10,
    "OALP-IX": 28,
}


@pytest.mark.parametrize(
    "text, expected",
    [
        ("RJ-ONHP-2017/1", "RJ-ONHP-2017/1"),
        ("RJ/ONHP/2017/8", "RJ-ONHP-2017/8"),
        ("RJ-ONHP-\n2019/1", "RJ-ONHP-2019/1"),
        ("SR-ONHP(CBM)-2022/4", "SR-ONHP(CBM)-2022/4"),
        ("Total", None),
    ],
)
def test_block_code_normalization(text, expected):
    assert normalize_block_code(text) == expected


@pytest.mark.parametrize(
    "code, acreage",
    [
        ("CB-ONHP-2022/1", "onland"),
        ("MB-OSHP-2022/1", "shallow_water"),
        ("GS-DWHP-2022/1", "deep_water"),
        ("KG-UDWHP-2022/1", "ultra_deep_water"),
    ],
)
def test_acreage_from_help_code(code, acreage):
    assert acreage_from_code(code) == acreage


@pytest.mark.parametrize("value, expected", [("Cat-I", "I"), ("Category- II", "II"), ("III", "III"), ("", None), ("5", None)])
def test_basin_category(value, expected):
    assert basin_category(value) == expected


def test_area_parsing_keeps_blank_unknown_and_rejects_garbage():
    assert parse_area("2,118.83") == 2118.83
    assert math.isnan(parse_area(""))
    with pytest.raises(ValueError):
        parse_area("6717.56 34364")  # area cell merged with a total row
    with pytest.raises(ValueError):
        parse_area("0")


def test_wrapped_cells_join_to_their_block_and_total_row_is_excluded():
    """Round VIII layout: description and awardee wrap; a total row follows."""
    table = [
        ["", "Blocks Awarded", "", "Description\n(Type / Basin /\nState)", "", "Area of"],
        [None, None, None, None, "Name of", None],
        ["SN.", None, "Category", None, None, "Award"],
        [None, None, None, None, "Awardee", None],
        ["", None, "", None, None, "(Sq. Km.)"],
        ["", "KG-UDWHP-2022/1", "", "Ultra Deep\nWater/KG\nOffshore/Eastern\nOffshore", "", ""],
        ["3", None, "I", None, "RIL-BP", "1199.64"],
        [None, None, None, None, "(Consortium)", None],
        ["", "GK-OSHP-2022/1", "", "Shallow\nWater/Kutch", "", ""],
        ["4", None, "II", None, "Sun\nPetrochemic", "765.54"],
        [None, None, None, None, "als Pvt Ltd.", None],
        ["Total: ONGC - 7 blocks", None, None, None, None, ""],
        [None, None, None, None, None, "34364"],
    ]
    records, _ = table_records(table)
    assert [r["block_name"] for r in records] == ["KG-UDWHP-2022/1", "GK-OSHP-2022/1"]
    assert records[0]["awardee"] == "RIL-BP (Consortium)"
    assert records[1]["awardee"] == "Sun Petrochemicals Pvt Ltd."
    assert records[1]["area_km2"] == "765.54"  # total-row 34364 not appended


def test_merged_company_cell_carries_to_following_blocks():
    """Round IV layout: one company cell spans all seven blocks."""
    table = [
        ["Company", "Blocks\nAwarded", "Category", "Description (Type / Basin /\nState)", "Area of Award (Sq.\nKms)"],
        ["Oil and Natural\nGas Corporation\nLimited\n(All 7 Blocks)", "RJ-ONHP-\n2019/1", "Category-\nI", "Onland / Rajasthan / Rajasthan", "2,118.83"],
        [None, "VN-ONHP-\n2019/1", "Category-", "Onland / Vindhayan / Madhya\nPradesh", "2,730.73"],
        [None, None, "II", None, None],
    ]
    records, _ = table_records(table)
    assert records[1]["awardee"] == "Oil and Natural Gas Corporation Limited"
    assert records[1]["basin_category"] == "Category- II"


def test_header_less_table_without_previous_header_fails_closed():
    with pytest.raises(ValueError):
        table_records([["1", "RJ-ONHP-2017/1", "VEDANTA"]])


# --- shipped table -----------------------------------------------------------


@pytest.fixture(scope="module")
def blocks():
    return load_awarded_blocks()


def test_round_counts_match_award_lists(blocks):
    oalp = blocks[blocks.round_family == "OALP"]
    assert oalp.groupby("round").size().to_dict() == ROUND_COUNTS
    assert len(oalp) == 172  # nine OALP rounds, per the DGH award lists


def test_block_identity_is_unique_and_complete(blocks):
    assert not blocks.block_name.duplicated().any()
    assert blocks.block_name.notna().all() and blocks.awardee.notna().all()
    assert blocks.source_id.notna().all() and (blocks.source_page >= 1).all()


def test_acreage_agrees_with_block_code_where_source_states_it(blocks):
    stated = blocks[blocks.acreage_type_basis == "source_table"]
    assert len(stated) > 0
    assert (stated.block_name.map(acreage_from_code) == stated.acreage_type).all()


def test_basin_names_resolve_to_dgh_basin_list(blocks):
    names = set(load_basins().basin)
    assert set(CODE_BASIN.values()) <= names
    assert set(blocks.basin.dropna()) <= names


def test_published_basin_is_consistent_with_code_basin(blocks):
    """Every published basin name shares a word with the code-derived basin."""
    aliases = {"KG": "krishna", "AN": "andaman", "GV": "ganga", "VN": "vindh"}
    for row in blocks.dropna(subset=["basin_published"]).itertuples():
        published = row.basin_published.lower().replace("-", " ")
        stem = aliases.get(row.block_name[:2], row.basin.lower().replace("-", " ").split()[0])
        assert stem[:5] in published or "kg" in published, (row.block_name, row.basin_published)


def test_area_unknown_is_missing_not_zero(blocks):
    assert (blocks.area_km2.dropna() > 0).all()
    assert blocks[blocks["round"] == "OALP-I"].area_km2.isna().all()
    assert set(blocks.area_basis.dropna()) <= {"award_list", "offer_list"}


def test_contract_signed_is_date_or_missing(blocks):
    assert pd.api.types.is_datetime64_any_dtype(blocks.contract_signed)
