"""Trace EXP r3 spud-count markers to annual source totals and distinct leases."""

import csv
import json
import os
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
import pytest

from worldenergydata.bsee.series import BANDS
from worldenergydata.bsee.series.charts import scale

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "examples/bsee/exploration_leasing"
OUTPUT = EXAMPLE / "output"
YEARLY = OUTPUT / "yearly"
YEARS = range(2005, 2021)


def published_counts():
    # Each annual CSV row already counts leases for one band. The file also
    # contains pooled margins, which must not be added to the four-band grid.
    with (OUTPUT / "exploration.csv").open(encoding="utf-8", newline="") as source:
        counts = {}
        for row in csv.DictReader(source):
            if row["issue_year"] == "All years" or row["depth_band"] not in BANDS:
                continue
            key = int(row["issue_year"]), row["depth_band"]
            assert key not in counts
            counts[key] = int(row["explored_within_five_years"])
    assert counts.keys() == {(year, band) for year in YEARS for band in BANDS}
    return counts


def markers(group):
    result = {}
    for dot in group.findall("{*}circle"):
        year = int(dot.attrib["data-year"])
        assert year not in result
        title = dot.findtext("{*}title")
        result[year] = int(
            re.search(r"Annual value ([\d,]+)\.", title)[1].replace(",", "")
        )
    return result


def test_main_figures_match_published_spud_counts():
    counts = published_counts()
    figures = {
        f["figure_number"]: f
        for f in json.loads((YEARLY / "figures.json").read_bytes())
    }
    figure = figures["2"]
    assert figure["role"] == "main" and figure["layout"] == "overlay"
    assert figure["series_by"] == "depth_band" and figure["labels"] == list(BANDS)
    peak = max(counts.values())
    assert (figure["y_scale"]["max"], figure["y_scale"]["step"]) == scale(peak)
    svg = (YEARLY / figure["svg"]).read_text(encoding="utf-8")
    assert svg.strip() in (YEARLY / figure["interactive"]).read_text(encoding="utf-8")
    series = ET.fromstring(svg).findall(".//{*}g[@data-series]")
    assert [g.attrib["data-label"] for g in series] == list(BANDS)
    for band, group in zip(BANDS, series):
        assert markers(group) == {year: counts[year, band] for year in YEARS}

    # A later cohort cannot contribute a point to the fixed-window series.
    opening = ET.parse(YEARLY / figures["1A"]["svg"]).findall(".//{*}g[@data-series]")
    issued, spuds = opening
    assert issued.find("{*}path[@class='annual']").get("stroke-dasharray") is None
    assert spuds.find("{*}path[@class='annual']").get("stroke-dasharray")
    assert markers(spuds) == {
        year: sum(counts[year, band] for band in BANDS) for year in YEARS
    }


def test_annual_counts_match_distinct_bottom_leases(monkeypatch, tmp_path):
    directory = os.getenv("BSEE_EXP_DATA_DIR")
    if not directory:
        pytest.skip("set BSEE_EXP_DATA_DIR for the independent lease-level recount")
    monkeypatch.syspath_prepend(str(EXAMPLE))
    from bound_check import read_bore_file
    from lease_basis import read_leases
    from source_inputs import BORE, TAPE, verified_inputs

    inputs = tmp_path / "inputs"
    pins = verified_inputs(Path(directory), inputs, (BORE, TAPE))
    leases, _, _ = read_leases(inputs / TAPE, ROOT)
    leases = leases.loc[leases.issue_year.isin(YEARS)]
    cutoff = pd.Timestamp(pins[BORE]["collection_end_utc"]).tz_localize(None)
    _, bores = read_bore_file(inputs / BORE, cutoff)
    dated = bores.dropna(subset=["spud"])
    first = dated.loc[dated.spud.eq(dated.groupby("api10").spud.transform("min"))]
    # Collapse only ties agreeing on bottom lease and well type. A later
    # exploratory sidetrack does not change an original development spud.
    original = first[["api10", "spud", "bottom", "type_code"]].drop_duplicates()
    wells = original.loc[
        ~original.api10.duplicated(keep=False) & original.type_code.eq("E")
    ]
    joined = wells.merge(
        leases, left_on="bottom", right_on="lease_id", validate="many_to_one"
    )
    qualified = joined.loc[
        joined.spud.between(
            joined.effective_date, joined.effective_date + pd.DateOffset(years=5)
        )
    ].drop_duplicates("lease_id")
    bands = pd.cut(
        qualified.lease_depth_m,
        [0, 100, 500, 1500, float("inf")],
        labels=BANDS,
        right=False,
    )
    assert bands.notna().all()
    tally = qualified.groupby([qualified.issue_year, bands], observed=True).size()
    expected = published_counts()
    assert {key: int(tally.get(key, 0)) for key in expected} == expected
    assert sum(expected.values()) == len(qualified)
