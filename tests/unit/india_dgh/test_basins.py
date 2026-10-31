"""Basin list parser and shipped table.

Source: DGH "Basins and Categories" page (pageId=66), last updated 27/01/2023:
26 basins; Category-I 7, Category-II 5, Category-III 14. The fixture below
copies the three listing sentences of that page verbatim in structure.
"""

import pytest

from worldenergydata.india_dgh import load_basins
from worldenergydata.india_dgh.basins import EXPECTED_COUNTS, parse_basin_page

PAGE = """<p>Based on conventional resource potential, 7 basins are grouped under
Category-I covering 30% of total basinal area. These 7 basins are namely
Krishna-Godavari (KG), Mumbai Offshore, Assam Shelf, Rajasthan, Cauvery,
Assam-Arakan Fold Belt and Cambay. These basins are fairly appraised.</p>
<p>Similarly, Category-II basins cover 23% of total basinal area. Five basins
fall in this category and those are namely Saurashtra, Kutch, Vindhyan,
Mahanadi and Andaman. These basins are moderately appraised.</p>
<p>Further, Category-III basins cover 47% of total basinal area. Fourteen
basins fall in this category and those are namely Kerala-Konkan, Bengal-Purnea,
Ganga-Punjab, Pranhita-Godavari(PG), Satpura-South Rewa-Damodar, Himalyan
Foreland, Chattisgarh, Narmada, Spiti-Zanskar, Deccan Syneclise, Cuddapah,
Karewa, Bhima-Kaladgi, and Bastar. These basins are appraised.</p>"""


def test_page_parses_to_26_basins_by_category():
    frame = parse_basin_page(PAGE)
    assert len(frame) == 26
    assert frame.groupby("category").size().to_dict() == EXPECTED_COUNTS
    row = frame.set_index("basin").loc["Himalayan Foreland"]
    assert row.basin_published == "Himalyan Foreland"  # published spelling kept
    assert row.category == "III"


def test_changed_listing_fails_closed():
    with pytest.raises(ValueError, match="Category-II"):
        parse_basin_page(PAGE.replace("Mahanadi and Andaman", "Mahanadi"))


def test_shipped_basins_match_parser_contract():
    frame = load_basins()
    assert len(frame) == 26
    assert frame.groupby("category").size().to_dict() == EXPECTED_COUNTS
    assert not frame.basin.duplicated().any()
    assert (frame.category_as_of == "2023-01-27").all()
    # Category-I is "reserves and already producing": seven producing basins.
    assert set(frame[frame.category == "I"].basin) == {
        "Krishna-Godavari", "Mumbai", "Assam Shelf", "Rajasthan",
        "Cauvery", "Assam-Arakan Fold Belt", "Cambay",
    }
