# ABOUTME: Unit tests for the vessel identity resolver + dedup (#599).
# ABOUTME: Covers canonicalize_name, resolve_identities clustering, dedupe_catalog.

from pathlib import Path

import pytest

from worldenergydata.vessel_fleet.identity_crosswalk import (
    _DEFAULT_CURATED_DIR,
    load_corpus_records,
)
from worldenergydata.vessel_fleet.identity_resolver import (
    canonicalize_name,
    dedupe_catalog,
    operators_compatible,
    resolve_identities,
)

# ---------------------------------------------------------------------------
# canonicalize_name
# ---------------------------------------------------------------------------


class TestCanonicalizeName:
    def test_strips_trailing_operator_parenthetical(self):
        assert canonicalize_name("Skandi Constructor (DOF)") == "SKANDI CONSTRUCTOR"

    def test_strips_mv_prefix(self):
        assert canonicalize_name("M/V Island Performer") == "ISLAND PERFORMER"
        assert canonicalize_name("MV Island Performer") == "ISLAND PERFORMER"

    def test_strips_msv_and_sv_prefix(self):
        assert canonicalize_name("MSV Q4000") == "Q4000"
        assert canonicalize_name("SV Q4000") == "Q4000"

    def test_reglues_hull_number_hyphen_variant(self):
        assert canonicalize_name("HELIX Q-4000") == "HELIX Q4000"
        assert canonicalize_name("Q-4000") == "Q4000"

    def test_strips_punctuation_and_collapses_whitespace(self):
        assert canonicalize_name("  Deep   Blue!! ") == "DEEP BLUE"
        assert canonicalize_name("Caldive's Q4000") == "CALDIVE S Q4000"

    def test_empty_and_none(self):
        assert canonicalize_name(None) == ""
        assert canonicalize_name("") == ""


# ---------------------------------------------------------------------------
# operators_compatible
# ---------------------------------------------------------------------------


class TestOperatorsCompatible:
    def test_missing_operator_is_compatible(self):
        assert operators_compatible({"operator": None}, {"operator": "Helix"})

    def test_shared_token_is_compatible(self):
        a = {"operator": "Helix Energy Solutions"}
        b = {"operator": "Helix Well Ops"}
        assert operators_compatible(a, b)

    def test_disjoint_operators_conflict(self):
        a = {"operator": "Maersk Drilling"}
        b = {"operator": "Transocean"}
        assert not operators_compatible(a, b)


# ---------------------------------------------------------------------------
# resolve_identities
# ---------------------------------------------------------------------------


class TestResolveIdentities:
    def test_imo_match_high_confidence(self):
        recs = [
            {"name": "Deep Blue", "imo": "9181135", "source": "a"},
            {"name": "Deepblue", "imo": "9181135", "source": "b"},
        ]
        clusters = resolve_identities(recs)
        assert len(clusters) == 1
        assert clusters[0]["confidence"] == "high"
        assert "imo" in clusters[0]["match_basis"]
        assert clusters[0]["member_count"] == 2

    def test_name_plus_operator_match_medium(self):
        recs = [
            {"name": "Q4000", "operator": "Helix", "source": "a"},
            {"name": "Q4000", "operator": "Helix Energy", "source": "b"},
        ]
        clusters = resolve_identities(recs)
        assert len(clusters) == 1
        assert clusters[0]["confidence"] == "medium"
        assert "canonical_name+operator" in clusters[0]["match_basis"]

    def test_aka_match_merges(self):
        recs = [
            {"name": "Q4000", "operator": "Helix", "aka": ["MSV Q4000"], "source": "a"},
            {"name": "MSV Q4000", "operator": None, "source": "b"},
        ]
        clusters = resolve_identities(recs)
        assert len(clusters) == 1
        assert "aka" in clusters[0]["match_basis"]

    def test_name_match_but_operator_conflict_not_merged(self):
        recs = [
            {"name": "Discoverer", "operator": "Maersk", "source": "a"},
            {"name": "Discoverer", "operator": "Transocean", "source": "b"},
        ]
        clusters = resolve_identities(recs)
        # Same name, conflicting operator -> two distinct vessels.
        assert len(clusters) == 2

    def test_singleton_records_stay_separate(self):
        recs = [
            {"name": "Alpha", "source": "a"},
            {"name": "Beta", "source": "b"},
        ]
        clusters = resolve_identities(recs)
        assert len(clusters) == 2
        assert all(c["confidence"] == "singleton" for c in clusters)


# ---------------------------------------------------------------------------
# dedupe_catalog
# ---------------------------------------------------------------------------


class TestDedupeCatalog:
    def test_count_reduction_and_report(self):
        recs = [
            {
                "name": "Q4000",
                "operator": "Helix",
                "class": "heavy_intervention_semi",
                "aka": ["MSV Q4000", "HELIX Q4000"],
                "source": "seed",
            },
            {"name": "MSV Q4000", "class": "heavy_intervention_semi", "source": "war"},
            {
                "name": "HELIX Q4000",
                "class": "heavy_intervention_semi",
                "source": "war",
            },
            {"name": "Island Performer", "class": "rlwi_monohull", "source": "roster"},
        ]
        deduped, report = dedupe_catalog(recs)
        assert report["records_in"] == 4
        assert report["distinct_vessels_out"] == 2
        assert report["duplicates_collapsed"] == 2
        # The Q4000 cluster collapses 3 rows to 1 and unions the aka names.
        q = next(d for d in deduped if d["CANONICAL_NAME"] == "Q4000")
        assert q["member_count"] == 3
        assert "MSV Q4000" in q["ALTERNATE_NAMES"]
        delta = report["per_class_delta"]["heavy_intervention_semi"]
        assert delta["before"] == 3
        assert delta["after"] == 1

    def test_canonical_name_and_alternate_names_populated(self):
        recs = [
            {"name": "Skandi Constructor (DOF)", "operator": "DOF", "source": "a"},
            {"name": "Skandi Constructor", "operator": "DOF Subsea", "source": "b"},
        ]
        deduped, _ = dedupe_catalog(recs)
        assert len(deduped) == 1
        assert deduped[0]["CANONICAL_NAME"] == "SKANDI CONSTRUCTOR"
        assert deduped[0]["ALTERNATE_NAMES"]


# ---------------------------------------------------------------------------
# Real-corpus smoke test (skip if curated CSVs not mounted)
# ---------------------------------------------------------------------------


class TestRealCorpusSmoke:
    def test_distinct_less_than_total(self):
        if not (Path(_DEFAULT_CURATED_DIR) / "drilling_rigs.csv").is_file():
            pytest.skip("curated CSVs not mounted")
        records = load_corpus_records()
        assert len(records) > 2000  # full corpus present
        deduped, report = dedupe_catalog(records)
        assert report["distinct_vessels_out"] < report["records_in"]
        assert report["duplicates_collapsed"] > 0
        # The Helix Q-series double-count is collapsed to <=3 heavy semis hulls.
        hsemi = report["per_class_delta"]["heavy_intervention_semi"]
        assert hsemi["after"] < hsemi["before"]
