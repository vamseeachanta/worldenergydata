"""Offline checks on the producer and its checked-in article tables."""

import re
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
R12 = ROOT.parent / "issue2_public_data_r12" / "data"
sys.path.insert(0, str(ROOT.parent))
from issue2_public_data_r15 import derive_r15 as derive


def read(stem, **kwargs):
    return pd.read_csv(DATA / (stem + ".csv"), **kwargs)


def test_readme_source_dates_link_to_committed_receipts():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    source_dates = readme.split("## Source dates\n", 1)[1].split("\n## ", 1)[0]
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", source_dates)
    assert set(links) == {"source-pins.json", "data/sources.csv"}
    assert all((ROOT / path).is_file() for path in links)


def test_all_published_table_names_and_columns_are_present():
    baseline = {path.name for path in R12.glob("*.csv")}
    assert baseline, "Expected the published r12 CSVs"
    added = {
        "record-counts.csv": {"source", "disposition", "reason", "records"},
        "r12-vs-r15.csv": {"table", "group", "metric", "difference_unit", "r12", "r15", "difference"},
    }
    assert {path.name for path in DATA.glob("*.csv")} == baseline | added.keys()
    for name in baseline | added.keys():
        if name in added:
            expected = added[name]
        else:
            expected = set(pd.read_csv(R12 / name, nrows=0).columns)
            if name == "sources.csv":
                expected.add("http_last_modified")
        assert set(pd.read_csv(DATA / name, nrows=0).columns) == expected, name


@pytest.mark.parametrize("name", ["map-wells.csv", "map-wells-by-year.csv"])
def test_mapped_wells_match_r12_by_api(name):
    def by_api(directory):
        # Compare the published coordinate precision and preserve leading zeros in IDs.
        frame = pd.read_csv(directory / name, dtype=str)
        assert frame.api_well_number.notna().all()
        return frame.set_index("api_well_number", verify_integrity=True).sort_index(axis="columns")

    old, new = by_api(R12), by_api(DATA)
    added = new.index.difference(old.index)
    removed = old.index.difference(new.index)
    common = old.index.intersection(new.index)
    # Show both values for every changed field, even when annual counts agree.
    changed = old.loc[common].compare(new.loc[common], result_names=("r12", "r15"))
    assert added.empty and removed.empty and changed.empty, (
        f"{name}: added {added.tolist()}, removed {removed.tolist()}\n"
        f"Changed wells:\n{changed.to_string()}"
    )


def test_annual_counts_conserve_wells_and_permits():
    wells = read("map-wells-by-year", dtype={"api_well_number": str})
    assert wells.api_well_number.is_unique
    counts = read("new-wells-by-year").set_index("year")
    assert counts.index.tolist() == list(range(2005, 2026))
    by_band = pd.crosstab(wells.spud_year, wells.band)
    assert set(by_band.columns) == set(counts.columns) - {"total"}
    assert counts.total.sum() == len(wells)
    for band in counts.drop(columns="total"):
        assert counts[band].to_dict() == by_band[band].to_dict()
    assert counts.total.equals(counts.drop(columns="total").sum(axis=1))

    rig = read("fig-p1-new-well-permits-by-rig-type").set_index("year")
    depth = read("new-well-permits-by-water-depth").set_index("year")
    assert rig.index.tolist() == list(range(2005, 2027))
    assert rig.total.equals(rig.drop(columns="total").sum(axis=1))
    assert depth.permits.equals(depth.drop(columns=["permits", "median_m"]).sum(axis=1))
    assert rig.total.equals(depth.permits)


def test_map_windows_agree_with_annual_counts_and_historical_periods():
    counts = read("new-wells-by-year").set_index("year")
    windows = read("map-windows").set_index(["start", "end"])
    assert windows.index.tolist() == [(y, y + 4) for y in range(2005, 2022)]
    for (start, end), row in windows.iterrows():
        assert row.to_dict() == counts.loc[start:end].sum().to_dict()
    legacy = read("map-summary").set_index("period")
    assert legacy.index.tolist() == ["2005 to 2009", "2021 to 2025"]
    for start, end in [(2005, 2009), (2021, 2025)]:
        assert legacy.loc[f"{start} to {end}"].to_dict() == windows.loc[start, end].to_dict()
    annual = read("map-wells-by-year", dtype={"api_well_number": str})
    period_map = read("map-wells", dtype={"api_well_number": str})
    selected = annual[annual.spud_year.le(2009) | annual.spud_year.ge(2021)]
    pd.testing.assert_frame_equal(selected.set_index("api_well_number").sort_index(),
                                  period_map.drop(columns="period").set_index("api_well_number").sort_index())


def test_exclusive_reasons_reconcile_raw_rows_to_outputs():
    # Independently counted with csv.DictReader on the three pinned main members.
    raw = {"APD": 20273, "Borehole": 57520, "APM": 102177}
    audit = read("record-counts")
    assert set(audit.source) == set(raw)
    assert not audit.duplicated(["source", "disposition", "reason"]).any()
    assert audit.reason.notna().all() and audit.records.ge(0).all()
    days = read("days-summary")
    drilling = days.activity.eq("Spud to total depth")
    kept = {
        "APD": read("fig-p1-new-well-permits-by-rig-type").total.sum(),
        "Borehole": len(read("map-wells-by-year")),
        "APM": days.loc[~drilling, "n"].sum(),
    }
    assert days.loc[drilling, "records"].sum() == kept["Borehole"] == read("new-wells-by-year").total.sum()
    assert days.records.equals(days.n + days.missing_invalid_days + days.nonpositive_days)
    for source, rows in audit.groupby("source"):
        totals = rows.groupby("disposition").records.sum().to_dict()
        assert totals["read"] == raw[source]
        assert totals["kept"] == kept[source]
        assert totals["read"] == totals["kept"] + totals["excluded"]


def test_fresh_derivation_matches_every_delivered_csv(tmp_path):
    """Supply the three pinned archives locally to exercise the full producer."""
    import os

    directory = os.environ.get("BSEE_R15_DATA_DIR")
    if not directory:
        pytest.skip("set BSEE_R15_DATA_DIR to the directory holding the pinned BSEE files")
    regenerated = tmp_path / "data"
    derive.derive(Path(directory), regenerated)
    assert {p.name for p in regenerated.iterdir()} == {p.name for p in DATA.glob("*.csv")}
    for path in regenerated.iterdir():
        assert path.read_bytes() == (DATA / path.name).read_bytes(), path.name
