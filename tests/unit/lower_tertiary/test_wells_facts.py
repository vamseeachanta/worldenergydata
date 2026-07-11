"""Contract tests for the generated _wells.json (issue #948).

The pre-#948 hand-curated Big Foot records are pinned as a golden reference:
the benchmark+V30 join (with the 1-dp cum rule + int rig-days) must reproduce
them exactly, so the rollout to 56 wells cannot silently regress the 5 live
Big Foot pages.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

_spec = importlib.util.spec_from_file_location(
    "build_wells_facts_ut", REPO / "scripts/lower_tertiary/build_wells_facts.py"
)
bwf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bwf)

# Golden Big Foot records (the hand-curated values live on the deployed pages).
GOLDEN_BIG_FOOT = {
    "608124006001": {
        "slot": "A004",
        "spud_date": "2019-03-10",
        "td_date": "2019-03-25",
        "drilling_rig_days": 15,
        "completion_rig_days": 156,
        "max_tvd_ft": 22253,
        "mud_weight_ppg": 16.4,
        "first_oil": "2019-06-01",
        "workovers": [{"date": "2020-08-30", "type": "Workover"}],
        "cum_oil_mmbbl": 32.2,
        "uptime_pct": 93.7,
        "status": "producing",
    },
    "608124006603": {
        "slot": "A006",
        "spud_date": "2020-02-12",
        "td_date": "2020-03-01",
        "drilling_rig_days": 18,
        "completion_rig_days": 224,
        "max_tvd_ft": 21395,
        "mud_weight_ppg": 16.4,
        "first_oil": "2020-09-01",
        "workovers": [{"date": "2022-03-16", "type": "Workover"}],
        "cum_oil_mmbbl": 21.3,
        "uptime_pct": 92.2,
        "status": "producing",
    },
    "608124006200": {
        "slot": "A001",
        "spud_date": "2012-04-03",
        "td_date": "2012-08-07",
        "drilling_rig_days": 126,
        "completion_rig_days": 265,
        "max_tvd_ft": 23187,
        "mud_weight_ppg": 16.4,
        "first_oil": "2018-11-01",
        "workovers": [{"date": "2021-07-15", "type": "Workover"}],
        "cum_oil_mmbbl": 14.9,
        "uptime_pct": 94.6,
        "status": "producing",
    },
    "608124006800": {
        "slot": "A008",
        "spud_date": "2013-01-22",
        "td_date": "2021-12-02",
        "drilling_rig_days": 118,
        "completion_rig_days": 164,
        "max_tvd_ft": 21801,
        "mud_weight_ppg": 17,
        "first_oil": "2022-07-01",
        "workovers": [{"date": "2025-10-03", "type": "Workover"}],
        "cum_oil_mmbbl": 4.7,
        "uptime_pct": 92.4,
        "status": "producing",
    },
    "608124006302": {
        "slot": "A002",
        "spud_date": "2024-07-11",
        "td_date": "2024-07-24",
        "drilling_rig_days": 13,
        "completion_rig_days": 168,
        "max_tvd_ft": 21830,
        "mud_weight_ppg": 14,
        "first_oil": "2025-01-01",
        "workovers": [],
        "cum_oil_mmbbl": 1.5,
        "uptime_pct": 96.3,
        "status": "producing",
    },
}
GOLDEN_BIG_FOOT_BLOCK = {
    "display_name": "Big Foot",
    "operator": "Chevron",
    "host": "Extended Tension-Leg Platform (eTLP)",
    "lease": "G16942",
    "block": "Walker Ridge 29",
    "play": "Wilcox / Lower Tertiary",
}


def _built():
    return bwf.build()


def test_big_foot_identity_guard():
    feed = _built()
    by_api = {w["api"]: w for w in feed["wells"]}
    for api, golden in GOLDEN_BIG_FOOT.items():
        got = by_api[api]
        for k, v in golden.items():
            assert got[k] == v, f"{api}.{k}: {got.get(k)!r} != {v!r}"
    assert feed["fields"]["big_foot"] == GOLDEN_BIG_FOOT_BLOCK


def test_no_nan_or_infinity_tokens():
    text = json.dumps(_built())
    assert not re.search(r"\bNaN\b|\bInfinity\b", text)


def test_join_counts():
    feed = _built()
    assert len(feed["wells"]) == 56
    by_field = {}
    for w in feed["wells"]:
        by_field[w["field_id"]] = by_field.get(w["field_id"], 0) + 1
    assert by_field == {
        "jack_st_malo": 24,
        "stones": 10,
        "big_foot": 8,
        "julia": 4,
        "shenandoah": 4,
        "cascade_chinook": 3,
        "anchor": 3,
    }


def test_slot_and_filename_uniqueness():
    feed = _built()
    keys = [(w["field_id"], w["slot"]) for w in feed["wells"]]
    assert len(keys) == len(set(keys))
    files = [f"{w['field_id']}_{w['slot']}_well.html" for w in feed["wells"]]
    assert len(files) == len(set(files))
    assert all(re.fullmatch(r"[A-Za-z0-9_-]+_well\.html", f) for f in files)


def test_unmatched_well_is_thin_and_honest():
    # Anchor 608114076101 is a sidetrack absent from the V30 extract: it has a
    # w<last4> slot and null construction data (never calendar-days-as-rig-days).
    feed = _built()
    thin = next(w for w in feed["wells"] if w["api"] == "608114076101")
    assert thin["slot"] == "w6101"
    assert thin["spud_date"] is None and thin["max_tvd_ft"] is None
    assert thin["drilling_rig_days"] is None
    assert thin["first_oil"] is not None  # production is known


def test_every_producing_field_block_non_empty():
    feed = _built()
    for fid in {w["field_id"] for w in feed["wells"]}:
        blk = feed["fields"][fid]
        assert blk.get("display_name") and blk.get("block"), fid
