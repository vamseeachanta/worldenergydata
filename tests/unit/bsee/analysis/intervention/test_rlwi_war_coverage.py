# ABOUTME: Unit tests for rlwi_war_coverage -- does the dedicated-intervention/RLWI fleet appear in BSEE WAR at all (#628).
# ABOUTME: CI-safe synthetic name-match + banding + verdict tests, a roster-merge test, plus a skip-if-missing real-data smoke test.

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.rlwi_war_coverage import (
    DEFAULT_MAX_TOKEN_DF,
    build_coverage,
    build_token_df,
    load_intervention_vessels,
    match_war_names,
    probe,
    probe_vessel,
)

_REAL_WAR = Path("/mnt/ace/worldenergydata/data/modules/bsee/bin/war/mv_war_main.bin")

# A synthetic WAR rig-name vocabulary where DEEP/SEA are common (df > 2) but
# HARVEY/EVOLUTION/PERFORMER/VENTURE are rare, exercising the distinctiveness
# guard. Used with max_df=2 in the matcher tests.
_UNIQUES = [
    "ISLAND PERFORMER",
    "ISLAND INTERVENTION",
    "OLYMPIC INTERVENTION IV",
    "HELIX Q4000",
    "CALDIVE Q4000",
    "DISCOVERER DEEP SEA",
    "DEEP SEAS",
    "OCEAN DEEP SEA EXPLORER",
    "HARVEY DEEP SEA",
    "OCEAN EVOLUTION",
    "OCEANEERING MSV OCEAN EVOLUTION",
]


def _token_df():
    return build_token_df(_UNIQUES)


def _match(*needles, max_df=2):
    return match_war_names(needles, _UNIQUES, _token_df(), max_df=max_df)


# --- name matching ----------------------------------------------------------
def test_exact_canonical_match():
    assert _match("Island Performer") == ["ISLAND PERFORMER"]


def test_hull_token_contains_match():
    # "Q4000" carries a digit -> contains-matches every operator-prefixed spelling.
    assert _match("Q4000") == ["CALDIVE Q4000", "HELIX Q4000"]


def test_multitoken_distinctive_contains_match():
    # "Ocean Evolution": OCEAN is common, EVOLUTION rare -> still distinctive,
    # matches the bare + operator-prefixed WAR spellings.
    assert _match("Ocean Evolution") == [
        "OCEAN EVOLUTION",
        "OCEANEERING MSV OCEAN EVOLUTION",
    ]


def test_generic_two_word_alias_rejected_for_contains():
    # "Deep Sea": both tokens common (df>2) -> NOT distinctive; with no exact
    # WAR name "DEEP SEA" present, it must not absorb "DISCOVERER DEEP SEA".
    assert _match("Deep Sea") == []


def test_distinctive_two_word_alias_matches():
    # "Harvey Deep Sea": HARVEY is rare -> distinctive -> matches that one rig.
    assert _match("Harvey Deep Sea") == ["HARVEY DEEP SEA"]


def test_bare_single_generic_token_is_exact_only():
    # "Intervention" is a single alpha token -> exact only; it must NOT grab
    # "ISLAND INTERVENTION" or "OLYMPIC INTERVENTION IV".
    assert _match("Intervention") == []
    # The full multi-token name still matches its own rig (and only that one).
    assert _match("Island Intervention") == ["ISLAND INTERVENTION"]


# --- probe_vessel banding + verdicts ----------------------------------------
def _war_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "WATER_DEPTH": [6000.0, 4000.0, None, None, 300.0, 9999.0],
            "RIG_NAME": [
                "HELIX Q4000",  # band_5000_10000
                "CALDIVE Q4000",  # band_3000_5000
                "ISLAND PERFORMER",  # depth null
                "ISLAND PERFORMER",  # depth null
                "OLYMPIC INTERVENTION IV",  # unrelated, shelf
                "DISCOVERER DEEP SEA",  # unrelated, deepwater
            ],
            "WAR_START_DT": [
                "3/5/2018",
                "7/8/2020",
                "1/2/2019",
                "4/9/2021",
                "5/5/2017",
                "6/6/2022",
            ],
        }
    )


def _probe_one(vessel, max_df=2):
    war = _war_frame()
    from worldenergydata.vessel_fleet.identity_resolver import canonicalize_name

    war_canon = war["RIG_NAME"].astype(str).map(canonicalize_name)
    uniques = sorted({c for c in war_canon.unique() if c})
    return probe_vessel(
        vessel, war, war_canon, uniques, build_token_df(uniques), max_df
    )


def test_probe_vessel_present_deepwater():
    q = {
        "name": "Q4000",
        "aka": ["Helix Q4000"],
        "vessel_types": ["heavy_intervention_semi"],
    }
    r = _probe_one(q)
    assert r["war_records"] == 2
    assert r["records_with_water_depth"] == 2
    assert r["bands_depth_stamped"]["band_5000_10000"] == 1
    assert r["bands_depth_stamped"]["band_3000_5000"] == 1
    assert r["deepwater_records"] == 2
    assert r["review_band_records"] == 1
    assert r["verdict"] == "present_deepwater"
    assert r["date_range"] == {"first_year": 2018, "last_year": 2020}
    assert r["is_light_intervention"] is False
    assert r["is_floor"] is True


def test_probe_vessel_in_war_depth_unknown_for_rlwi():
    # Island Performer (light RLWI) is in WAR but its rows have no depth stamp.
    v = {"name": "Island Performer", "aka": [], "vessel_types": ["rlwi_monohull"]}
    r = _probe_one(v)
    assert r["war_records"] == 2
    assert r["records_with_water_depth"] == 0
    assert r["deepwater_records"] == 0
    assert r["review_band_records"] == 0
    assert r["verdict"] == "in_war_depth_unknown"
    assert r["is_light_intervention"] is True


def test_probe_vessel_not_in_war():
    v = {"name": "AKOFS Seafarer", "aka": ["Skandi Aker"], "vessel_types": ["mpsv"]}
    r = _probe_one(v)
    assert r["war_records"] == 0
    assert r["verdict"] == "not_in_war"
    assert r["matched_war_rig_names"] == []


def test_rlwi_vessel_does_not_absorb_unrelated_deepwater_rig():
    # An RLWI unit named "Intervention" must NOT pick up OLYMPIC INTERVENTION IV
    # or DISCOVERER DEEP SEA, so it cannot be falsely scored deepwater.
    v = {"name": "Intervention", "aka": [], "vessel_types": ["rlwi_monohull"]}
    r = _probe_one(v)
    assert r["war_records"] == 0
    assert r["verdict"] == "not_in_war"


# --- overall probe ----------------------------------------------------------
def test_probe_overall_verdict_confirms_review():
    war = _war_frame()
    vessels = [
        {"name": "Island Performer", "aka": [], "vessel_types": ["rlwi_monohull"]},
        {
            "name": "Q4000",
            "aka": ["Helix Q4000"],
            "vessel_types": ["heavy_intervention_semi"],
        },
    ]
    result = probe(war, vessels, max_df=2)
    ov = result["overall_verdict"]
    assert ov["light_intervention_vessels_total"] == 1
    assert ov["light_in_review_band"] == 0
    assert ov["review_claim_confirmed"] is True
    assert "CONFIRMED" in ov["headline"]
    assert result["depth_coverage"]["war_records_total"] == 6
    assert any("FLOOR" in c for c in result["caveats"])
    assert result["provenance"]["issue"].startswith("worldenergydata#628")


# --- roster loading / merge -------------------------------------------------
def test_load_intervention_vessels_merges_by_imo(tmp_path):
    roster = tmp_path / "intervention_osv_roster.yml"
    seed = tmp_path / "intervention_vessels_seed.yml"
    roster.write_text(
        "vessels:\n"
        "  - vessel_name: Q4000\n"
        "    imo: 8767123\n"
        "    aka: []\n"
        "    vessel_type: heavy_intervention_semi\n"
        "    gom_resident: true\n"
        "  - vessel_name: Island Performer\n"
        "    imo: 9682045\n"
        "    aka: []\n"
        "    vessel_type: mpsv\n"
        "    gom_resident: true\n"
    )
    seed.write_text(
        "vessels:\n"
        "  - name: Helix Q4000\n"
        "    imo: 8767123\n"
        "    aka: []\n"
        "    vessel_type: heavy_intervention_semi\n"
        "    intervention_class: heavy\n"
        "  - name: Island Performer\n"
        "    imo: 9682045\n"
        "    aka: []\n"
        "    vessel_type: rlwi_monohull\n"
        "    intervention_class: light\n"
    )
    vessels = load_intervention_vessels(roster_path=roster, seed_path=seed)
    assert len(vessels) == 2  # merged by IMO, not 4
    by_imo = {v["imo"]: v for v in vessels}
    q = by_imo["8767123"]
    assert "Helix Q4000" in q["aka"] and "Q4000" in q["aka"]
    assert len(q["source_files"]) == 2
    perf = by_imo["9682045"]
    # The seed contributes the rlwi_monohull type + light class -> is_light.
    assert "rlwi_monohull" in perf["vessel_types"]
    assert "light" in perf["intervention_classes"]


def test_build_coverage_writes_yaml(tmp_path):
    import pickle

    import yaml

    war_path = tmp_path / "mv_war_main.bin"
    with open(war_path, "wb") as fh:
        pickle.dump(_war_frame(), fh)
    roster = tmp_path / "intervention_osv_roster.yml"
    seed = tmp_path / "intervention_vessels_seed.yml"
    roster.write_text(
        "vessels:\n"
        "  - vessel_name: Island Performer\n"
        "    imo: 9682045\n"
        "    aka: []\n"
        "    vessel_type: rlwi_monohull\n"
        "    gom_resident: true\n"
    )
    seed.write_text(
        "vessels:\n"
        "  - name: Q4000\n"
        "    imo: 8767123\n"
        "    aka: [Helix Q4000]\n"
        "    vessel_type: heavy_intervention_semi\n"
        "    intervention_class: heavy\n"
    )
    out_path = tmp_path / "out" / "rlwi_war_coverage.yml"
    result = build_coverage(
        war_path=war_path,
        roster_path=roster,
        seed_path=seed,
        out_path=out_path,
        max_df=2,
    )
    assert out_path.exists()
    loaded = yaml.safe_load(out_path.read_text())
    assert loaded["overall_verdict"]["vessels_total"] == 2
    names = {v["vessel_name"] for v in loaded["vessels"]}
    assert names == {"Island Performer", "Q4000"}
    assert result["depth_coverage"]["war_records_total"] == 6


# --- real-data smoke test ---------------------------------------------------
@pytest.mark.skipif(
    not _REAL_WAR.exists(), reason="real BSEE WAR bin not present (/mnt/ace)"
)
def test_real_data_confirms_no_light_intervention_in_deepwater():
    result = build_coverage(war_path=_REAL_WAR, max_df=DEFAULT_MAX_TOKEN_DF)
    cov = result["depth_coverage"]
    assert cov["war_records_total"] > 100_000
    # Defining property: depth coverage is sparse (FLOOR regime, ~6%).
    assert 0.0 < cov["depth_coverage_fraction"] < 0.2

    ov = result["overall_verdict"]
    assert ov["light_intervention_vessels_total"] > 0
    # The review finding: no light-intervention/RLWI vessel in the 5-10k band.
    assert ov["light_in_review_band"] == 0
    assert ov["review_claim_confirmed"] is True

    # At least one heavy intervention semi (e.g. Q4000) IS confirmed deepwater.
    deep = [v for v in result["vessels"] if v["verdict"] == "present_deepwater"]
    assert any("Q4000" in v["vessel_name"] for v in deep)
    # Some light units are present-but-depth-unknown (a coverage gap, not absence).
    light = [v for v in result["vessels"] if v["is_light_intervention"]]
    assert any(v["verdict"] == "in_war_depth_unknown" for v in light)
