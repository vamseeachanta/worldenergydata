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
