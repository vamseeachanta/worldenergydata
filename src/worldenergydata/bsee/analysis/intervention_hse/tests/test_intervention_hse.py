"""TDD tests for the intervention-HSE Phase-2 reusable package (#418).

Deterministic and network-free. The heavy root ``worldenergydata.__init__`` /
``bsee.__init__`` block a normal package import (the #407/#451 pattern), so these
tests load the package submodules by file path — the same discipline the #416/#426
exploration scripts used. The classifier itself is the repo-canonical
``IncidentClassifier`` reached via ``classifier.get_incident_classifier()``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PKG_DIR = Path(__file__).resolve().parents[1]  # .../intervention_hse


def _load(modname: str, filename: str):
    spec = importlib.util.spec_from_file_location(modname, _PKG_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


classifier_mod = _load("ih_classifier", "classifier.py")
loaders_mod = _load("ih_loaders", "loaders.py")
patterns_mod = _load("ih_patterns", "patterns.py")


# ---------------------------------------------------------------------------
# classifier bridge
# ---------------------------------------------------------------------------
def test_classifier_categorizes_known_bsee_incidents():
    clf = classifier_mod.get_incident_classifier()
    cases = {
        "Blowout": "DRILL",
        "Fire": "PSAFE",
        "Crane": "CRANE",
        "Pollution": "ENV",
        "Explosion": "PSAFE",
    }
    for accident_type, expected_activity in cases.items():
        res = clf.classify({"ACCIDENT_TYPE": accident_type}, source="bsee")
        assert (
            res.activity == expected_activity
        ), f"{accident_type} -> {res.activity}, expected {expected_activity}"
        # direct ACCIDENT_TYPE mapping is high confidence
        assert res.confidence >= 0.90
        assert res.match_method == "bsee_accident_type"


def test_classifier_unknown_defaults_low_confidence():
    clf = classifier_mod.get_incident_classifier()
    res = clf.classify({"ACCIDENT_TYPE": "Zzz No Such Type"}, source="bsee")
    assert res.activity == "OTHER"
    assert res.confidence < 0.5
    assert res.match_method == "default"


# ---------------------------------------------------------------------------
# loaders
# ---------------------------------------------------------------------------
def test_loader_parses_synthetic_incinv(tmp_path):
    csv_path = tmp_path / "mv_acc_investigations.txt"
    csv_path.write_text(
        "ACCIDENT_TYPE,DATE_OCCURRED,AREA_BLOCK,LEASE_NUMBER\n"
        " Blowout , 3/4/2015 , GC 123 , G01234 \n"
        "Fire,7/8/2016,MC 045,G05678\n",
        encoding="latin-1",
    )
    rows = loaders_mod.load_incinv_file(csv_path)
    assert len(rows) == 2
    # keys and string values stripped
    assert rows[0]["ACCIDENT_TYPE"] == "Blowout"
    assert rows[0]["LEASE_NUMBER"] == "G01234"
    assert rows[1]["ACCIDENT_TYPE"] == "Fire"


def test_resolve_incinv_source_raises_when_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        loaders_mod.resolve_incinv_source([tmp_path / "nope.txt"])


def test_resolve_incinv_source_skips_empty(tmp_path):
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    good = tmp_path / "good.txt"
    good.write_text("ACCIDENT_TYPE\nFire\n")
    resolved = loaders_mod.resolve_incinv_source([empty, good])
    assert resolved == good


# ---------------------------------------------------------------------------
# patterns: severity proxy + year (behavior-preserving helpers)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "accident_type,expected",
    [
        ("Fatality", "fatality"),
        ("Blowout", "major"),
        ("Explosion", "major"),
        ("Injury LTA", "injury_lost_time"),
        ("Fire", "serious"),
        ("Pollution", "serious"),
        ("Evacuation", "evacuation_muster"),
        ("Crane", "other"),
        ("", "other"),
    ],
)
def test_severity_proxy(accident_type, expected):
    assert patterns_mod.severity_proxy(accident_type) == expected


@pytest.mark.parametrize(
    "date_str,expected",
    [("3/4/2015", 2015), ("12/31/1999", 1999), ("garbage", None), ("", None)],
)
def test_parse_year(date_str, expected):
    assert patterns_mod.parse_year(date_str) == expected


# ---------------------------------------------------------------------------
# patterns: classify + compute on a tiny synthetic dataset
# ---------------------------------------------------------------------------
def _synthetic_rows():
    return [
        {
            "ACCIDENT_TYPE": "Blowout",
            "DATE_OCCURRED": "1/1/2015",
            "AREA_BLOCK": "GC 123",
            "LEASE_NUMBER": "G01",
        },
        {
            "ACCIDENT_TYPE": "Blowout",
            "DATE_OCCURRED": "1/1/2016",
            "AREA_BLOCK": "GC 124",
            "LEASE_NUMBER": "G02",
        },
        {
            "ACCIDENT_TYPE": "Fire",
            "DATE_OCCURRED": "1/1/2017",
            "AREA_BLOCK": "MC 045",
            "LEASE_NUMBER": "G03",
        },
        {
            "ACCIDENT_TYPE": "Crane",
            "DATE_OCCURRED": "1/1/2018",
            "AREA_BLOCK": "MC 046",
            "LEASE_NUMBER": "G04",
        },
    ]


def test_classify_records_distribution():
    clf = classifier_mod.get_incident_classifier()
    rows = _synthetic_rows()
    activity_dist, pairs = patterns_mod.classify_records(clf, rows)
    assert len(pairs) == 4
    # two Blowouts -> DRILL
    assert activity_dist["DRILL"] == 2
    assert activity_dist["PSAFE"] == 1  # Fire
    assert activity_dist["CRANE"] == 1


def test_compute_patterns_drill_cut():
    clf = classifier_mod.get_incident_classifier()
    rows = _synthetic_rows()
    _, pairs = patterns_mod.classify_records(clf, rows)
    drill = patterns_mod.compute_patterns(pairs, "DRILL", total_records=len(rows))
    assert drill["total"] == 2
    assert drill["pct_of_records"] == 50.0
    assert drill["severity_proxy"] == {"major": 2}
    assert drill["subactivity_distribution"] == {"well_control": 2}
    assert drill["by_year"] == {2015: 1, 2016: 1}
    assert drill["year_range"] == [2015, 2016]
    assert drill["distinct_leases"] == 2
    assert drill["top_areas"] == {"GC": 2}
    assert drill["confidence_buckets"] == {"direct_code(>=0.90)": 2}


def test_compute_patterns_empty_cut_no_div_zero():
    clf = classifier_mod.get_incident_classifier()
    _, pairs = patterns_mod.classify_records(clf, _synthetic_rows())
    # MARINE activity not present in the synthetic set
    res = patterns_mod.compute_patterns(pairs, "MARINE", total_records=4)
    assert res["total"] == 0
    assert res["pct_of_records"] == 0.0
    assert res["year_range"] is None
    assert res["distinct_leases"] == 0
