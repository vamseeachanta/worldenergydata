"""Sedimentary basins of India and their DGH category.

Source: DGH, "Basins and Categories" (Indian Geology), page last updated
27/01/2023, https://www.dghindia.gov.in/index.php/page?pageId=66 (read from the
Internet Archive capture of 27 Jan 2023; the live page returned the same text
structure at survey). The page states 26 basins in three categories based on
maturity of conventional resources:

* Category-I - basins which have reserves and are already producing (7);
* Category-II - contingent resources pending commercial production (5);
* Category-III - prospective resources awaiting discovery (14).

DGH notes the grouping is dynamic and differs for unconventional resources;
the category is therefore stamped with the page date (``category_as_of``).
"""

from __future__ import annotations

import html
import re

import pandas as pd

from .sources import data_path

CATEGORY_AS_OF = "2023-01-27"
CATEGORY_DEFINITION = {
    "I": "reserves and already producing",
    "II": "contingent resources pending commercial production",
    "III": "prospective resources awaiting discovery",
}
EXPECTED_COUNTS = {"I": 7, "II": 5, "III": 14}
# Published spelling -> name used across this module (block-code basin names).
NAME_FIXES = {
    "Krishna-Godavari (KG)": "Krishna-Godavari",
    "Mumbai Offshore": "Mumbai",
    "Andaman": "Andaman-Nicobar",
    "Pranhita-Godavari(PG)": "Pranhita-Godavari",
    "Himalyan Foreland": "Himalayan Foreland",
    "Chattisgarh": "Chhattisgarh",
}
_SENTENCE = re.compile(r"Category-(I{1,3}) basins.*?namely (.+?)\.\s", re.S)
_CAT1 = re.compile(r"7 basins are grouped under Category-I.*?namely (.+?)\.\s", re.S)


def _names(listing: str) -> list[str]:
    listing = listing.replace(", and ", ", ").replace(" and ", ", ")
    return [part.strip() for part in listing.split(",") if part.strip()]


def parse_basin_page(page: str | bytes) -> pd.DataFrame:
    """Parse the DGH 'Basins and Categories' page into one row per basin."""
    if isinstance(page, bytes):
        page = page.decode("utf-8", errors="replace")
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    text = re.sub(r"\s+", " ", text)
    found: dict[str, list[str]] = {}
    first = _CAT1.search(text)
    if first:
        found["I"] = _names(first.group(1))
    for category, listing in _SENTENCE.findall(text):
        found.setdefault(category, _names(listing))
    rows = []
    for category, expected in EXPECTED_COUNTS.items():
        names = found.get(category, [])
        if len(names) != expected:
            raise ValueError(f"Category-{category}: expected {expected} basins, found {len(names)}")
        for name in names:
            rows.append(
                {
                    "basin": NAME_FIXES.get(name, name),
                    "basin_published": name,
                    "category": category,
                    "category_definition": CATEGORY_DEFINITION[category],
                    "category_as_of": CATEGORY_AS_OF,
                    "source_id": "dgh_basins_and_categories",
                }
            )
    frame = pd.DataFrame(rows)
    if frame.basin.duplicated().any():
        raise ValueError("duplicate basin name")
    return frame


def load_basins() -> pd.DataFrame:
    """The 26 basins shipped with the package (built by scripts/india_dgh/build_tables.py)."""
    return pd.read_csv(data_path("basins.csv"), dtype={"category": "string"})
