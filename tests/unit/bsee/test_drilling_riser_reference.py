"""Consistency checks on data/modules/bsee/drilling_riser_reference (no network)."""

import csv
import re
from pathlib import Path

import pytest

_DIR = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "modules"
    / "bsee"
    / "drilling_riser_reference"
)


def _rows(name):
    with open(_DIR / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_row_counts():
    assert len(_rows("sources.csv")) == 22
    assert len(_rows("drilling_riser_configurations.csv")) == 8
    assert len(_rows("drilling_riser_joint_data.csv")) == 8


def test_every_cited_source_is_listed():
    ids = {r["source_id"] for r in _rows("sources.csv")}
    assert len(ids) == 22
    for r in _rows("drilling_riser_joint_data.csv"):
        assert r["source_id"] in ids
    cited = set()
    for r in _rows("drilling_riser_configurations.csv"):
        cited.update(re.findall(r"S\d\d", r["sources_with_pages"]))
    assert cited == {i for i in ids if i.startswith("S")}


# Hand calculations, wall = (OD - ID) / 2 / 0.0254 m per in:
#   P05: (0.5334 - 0.489) / 2 = 0.0222 m  -> 0.874 in
#   P06: (0.5588 - 0.5080) / 2 = 0.0254 m -> 1.000 in
#   P08: (0.533 - 0.492) / 2 = 0.0205 m   -> 0.807 in
#   P07: 15.875 mm / 25.4 = 0.625 in
@pytest.mark.parametrize(
    "source_id, expected_wall_in",
    [("P05", 0.874), ("P06", 1.000), ("P08", 0.807), ("P07", 0.625)],
)
def test_wall_matches_hand_calculation(source_id, expected_wall_in):
    row = next(
        r for r in _rows("drilling_riser_joint_data.csv") if r["source_id"] == source_id
    )
    assert float(row["wall_in"]) == pytest.approx(expected_wall_in, abs=0.0005)
    if row["main_tube_id_as_stated"]:
        od = float(row["main_tube_od_as_stated"].split()[0])
        inner = float(row["main_tube_id_as_stated"].split()[0])
        assert (od - inner) / 2 / 0.0254 == pytest.approx(expected_wall_in, abs=0.001)


def test_no_local_paths_or_hosts_in_public_text():
    for name in (
        "README.md",
        "sources.csv",
        "drilling_riser_configurations.csv",
        "drilling_riser_joint_data.csv",
    ):
        text = (_DIR / name).read_text(encoding="utf-8")
        assert "/mnt/" not in text
        assert ":\\" not in text


def test_vendor_incident_and_paper_tables():
    vendor = _rows("vendor_riser_joint_data.csv")
    incidents = _rows("drilling_riser_incidents.csv")
    papers = _rows("drilling_riser_failure_papers.csv")
    assert len(vendor) == 26 and len({r["row_id"] for r in vendor}) == 26
    assert len(incidents) == 22 and len({r["row_id"] for r in incidents}) == 22
    assert len(papers) == 30 and len({r["row_id"] for r in papers}) == 30
    for r in vendor + incidents:
        assert r["source_title"] and r["url"].startswith("http")
    classes = [r["event_class"] for r in incidents]
    assert classes.count("riser parting, separation or drop") == 12
    assert classes.count("unplanned LMRP disconnect or separation") == 5
    assert classes.count("riser handling") == 5


def test_incident_table_states_no_cause():
    incidents = _rows("drilling_riser_incidents.csv")
    assert not any("cause" in key.lower() for key in incidents[0])
    text = (_DIR / "drilling_riser_incidents.csv").read_text(encoding="utf-8").lower()
    assert "cause" not in text


# Hand calculation, Oil States Merlin flysheet (V16, V17): OD = ID + 2 x wall
#   19.25 + 2 x 1.0 = 21.25 in; 19.25 + 2 x 1.125 = 21.5 in
@pytest.mark.parametrize(
    "row_id, wall_in, od_in", [("V16", 1.0, 21.25), ("V17", 1.125, 21.5)]
)
def test_vendor_wall_and_od_by_arithmetic(row_id, wall_in, od_in):
    row = next(r for r in _rows("vendor_riser_joint_data.csv") if r["row_id"] == row_id)
    assert float(row["wall_thickness_in"].rstrip('"')) == wall_in
    assert "19.25" in row["product"]
    assert 19.25 + 2 * wall_in == pytest.approx(od_in)
    assert f"{od_in}" in row["note"]


def test_new_tables_have_no_local_paths():
    for name in (
        "vendor_riser_joint_data.csv",
        "drilling_riser_incidents.csv",
        "drilling_riser_failure_papers.csv",
    ):
        text = (_DIR / name).read_text(encoding="utf-8")
        assert "/mnt/" not in text
        assert ":\\" not in text
        assert "\u2014" not in text
