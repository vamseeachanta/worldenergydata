# ABOUTME: Tests for the analogs query layer over the past-projects registry (#932).
# ABOUTME: Offline only — filters, boundaries, ranking determinism, nulls, weights.
"""Tests for ``worldenergydata.field_development.analogs``.

Registry snapshot the hand-anchored expectations below rely on (from
``past_projects.yml``, issue #931 — 11 GoM projects):

    project_id       depth_ft  class          dev_system  status
    stones           9525      ultra_deep     subsea15    producing
    cascade_chinook  8200      ultra_deep     subsea15    producing
    jack_st_malo     7240      ultra_deep     subsea15    producing
    julia            7335      ultra_deep     tieback15   producing
    big_foot         5190      ultra_deep     dry         producing
    anchor           5080      ultra_deep     subsea20    producing
    shenandoah       5800      ultra_deep     subsea20    producing
    buckskin         6800      ultra_deep     null        null
    kaskida          5860      ultra_deep     subsea20    pre-FID
    tiber            4130      deepwater      subsea20    pre-FID
    north_platte     5840      ultra_deep     subsea20    non_producing
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from worldenergydata.field_development.analogs import (
    ANALOG_WEIGHTS_PATH,
    CRITERIA,
    FT_PER_M,
    AnalogMatch,
    find_analogs,
    load_analog_weights,
    to_records,
)

#: Exact metric equivalents of the BOEM class-boundary depths (ft * 0.3048).
M_999_FT = 999 * 0.3048
M_1000_FT = 1000 * 0.3048
M_4999_FT = 4999 * 0.3048
M_5000_FT = 5000 * 0.3048


def _ids(matches: list[AnalogMatch]) -> list[str]:
    return [m.project.project_id for m in matches]


def _rationale_by_criterion(match: AnalogMatch) -> dict[str, str]:
    return {a.criterion: a.status for a in match.rationale}


# ---------------------------------------------------------------------------
# Exact-filter behaviour
# ---------------------------------------------------------------------------


class TestFilters:
    def test_region_accepts_key_and_display_name_case_insensitive(self):
        by_key = _ids(find_analogs(region="gulf_of_mexico"))
        by_name = _ids(find_analogs(region="US Gulf of Mexico"))
        by_case = _ids(find_analogs(region="Gulf_Of_Mexico"))
        assert by_key and by_key == by_name == by_case
        # Region-only query, everything matches -> tie on score, stable by id.
        assert by_key == sorted(by_key)

    def test_unmatched_region_fails_closed(self):
        # 'worldwide' exists in the catalog but has no projects; a region-only
        # query where every project misses returns nothing (nothing invented).
        assert find_analogs(region="worldwide") == []
        assert find_analogs(region="atlantis_basin") == []

    def test_development_system_exact_near_and_excluded(self):
        matches = find_analogs(development_system="subsea15")
        # Hand-anchored: subsea15 matches (score 1.0, tie -> id order):
        #   cascade_chinook, jack_st_malo, stones
        # subsea20 = same 'subsea' family -> near-miss (credit 0.5):
        #   anchor, kaskida, north_platte, shenandoah, tiber
        # julia (tieback15) and big_foot (dry) miss -> EXCLUDED
        # buckskin (dev_system null) -> unknown, kept last at score 0.0
        assert _ids(matches) == [
            "cascade_chinook",
            "jack_st_malo",
            "stones",
            "anchor",
            "kaskida",
            "north_platte",
            "shenandoah",
            "tiber",
            "buckskin",
        ]
        assert matches[0].score == 1.0
        assert matches[3].score == 0.5
        assert matches[-1].score == 0.0

    def test_status_filter_validated_and_null_never_matches(self):
        matches = find_analogs(status="producing")
        producing = {
            "stones",
            "cascade_chinook",
            "jack_st_malo",
            "julia",
            "big_foot",
            "anchor",
            "shenandoah",
        }
        # pre-FID / non_producing projects MISS and are excluded; buckskin
        # (status null) is unknown -> kept at score 0.0, never a match.
        assert set(_ids(matches)) == producing | {"buckskin"}
        assert _ids(matches)[-1] == "buckskin"
        assert matches[-1].score == 0.0
        with pytest.raises(ValueError, match="status"):
            find_analogs(status="abandoned-maybe")

    def test_water_depth_class_param_filters_by_class(self):
        matches = find_analogs(water_depth_class="deepwater")
        # tiber is the only deepwater project (matched); all ultra projects
        # are adjacent-class near-misses; no distances (no query depth).
        assert _ids(matches)[0] == "tiber"
        assert matches[0].score == 1.0
        assert all(m.score == 0.5 for m in matches[1:])
        assert all(m.water_depth_distance_ft is None for m in matches)

    def test_invalid_water_depth_class_raises(self):
        with pytest.raises(ValueError, match="water_depth_class"):
            find_analogs(water_depth_class="abyssal")


# ---------------------------------------------------------------------------
# Depth-class boundaries (BOEM: 999/1000 ft and 4999/5000 ft, queried in m)
# ---------------------------------------------------------------------------


class TestDepthClassBoundaries:
    def test_999_ft_is_shallow(self):
        # shallow: no shallow projects; tiber (deepwater) is adjacent ->
        # the ONLY candidate; ultra projects are two classes away -> excluded.
        matches = find_analogs(water_depth_m=M_999_FT)
        assert _ids(matches) == ["tiber"]
        assert matches[0].rationale[0].status == "near_miss"

    def test_1000_ft_is_deepwater(self):
        matches = find_analogs(water_depth_m=M_1000_FT)
        assert _ids(matches)[0] == "tiber"
        assert matches[0].score == 1.0  # tiber matched
        assert all(m.score == 0.5 for m in matches[1:])  # ultra = adjacent

    def test_4999_ft_is_still_deepwater(self):
        matches = find_analogs(water_depth_m=M_4999_FT)
        assert _ids(matches)[0] == "tiber"
        assert matches[0].score == 1.0

    def test_5000_ft_is_ultra_deepwater(self):
        matches = find_analogs(water_depth_m=M_5000_FT)
        # Now the ultra projects match and tiber is the near-miss; nearest
        # ultra depth to 5000 ft is anchor (5080 ft).
        assert _ids(matches)[0] == "anchor"
        assert matches[0].score == 1.0
        tiber = next(m for m in matches if m.project.project_id == "tiber")
        assert tiber.score == 0.5
        assert tiber.rationale[0].status == "near_miss"

    def test_non_positive_depth_rejected(self):
        with pytest.raises(ValueError, match="water_depth_m"):
            find_analogs(water_depth_m=0)
        with pytest.raises(ValueError, match="water_depth_m"):
            find_analogs(water_depth_m=-100)


# ---------------------------------------------------------------------------
# Ranking determinism
# ---------------------------------------------------------------------------


class TestRanking:
    def test_depth_distance_ranks_within_equal_scores(self):
        # 5,850 ft (queried in m). Every project has a known depth; all ultra
        # projects match (1.0) and rank by |depth - 5850| ft:
        #   kaskida 10, north_platte 10, shenandoah 50, big_foot 660,
        #   anchor 770, buckskin 950, jack_st_malo 1390, julia 1485,
        #   cascade_chinook 2350, stones 3675; then tiber (near-miss, 0.5).
        # kaskida/north_platte tie at 10 ft -> broken by project_id.
        matches = find_analogs(water_depth_m=5850 * 0.3048)
        assert _ids(matches) == [
            "kaskida",
            "north_platte",
            "shenandoah",
            "big_foot",
            "anchor",
            "buckskin",
            "jack_st_malo",
            "julia",
            "cascade_chinook",
            "stones",
            "tiber",
        ]
        assert matches[0].water_depth_distance_ft == pytest.approx(10.0)
        assert matches[1].water_depth_distance_ft == pytest.approx(10.0)

    def test_composite_query_hand_anchored_ranking(self):
        # region GoM + 1,580 m (= 5,183.727 ft, ultra) + subsea20 + producing.
        # Weights: region .30, water_depth .35, development_system .25,
        # status .10; near-miss credit 0.5 on depth-class and dev-family.
        #   anchor       1.0    (all matched), dist 103.7 ft
        #   shenandoah   1.0    (all matched), dist 616.3 ft
        #   north_platte 0.90   (status non_producing missed), dist 656.3
        #   kaskida      0.90   (status pre-FID missed), dist 676.3
        #   jack_st_malo 0.875  (subsea15 = family near-miss), dist 2056.3
        #   cascade      0.875  dist 3016.3
        #   stones       0.875  dist 4341.3
        #   big_foot     0.75   (dry missed dev), dist 6.3
        #   julia        0.75   (tieback family missed dev), dist 2151.3
        #   tiber        0.725  (deepwater adjacent .175 + dev 1.0*.25 ...)
        #   buckskin     0.65   (dev + status unknown -> zero credit)
        matches = find_analogs(
            region="gulf_of_mexico",
            water_depth_m=1580.0,
            development_system="subsea20",
            status="producing",
        )
        assert _ids(matches) == [
            "anchor",
            "shenandoah",
            "north_platte",
            "kaskida",
            "jack_st_malo",
            "cascade_chinook",
            "stones",
            "big_foot",
            "julia",
            "tiber",
            "buckskin",
        ]
        by_id = {m.project.project_id: m for m in matches}
        assert by_id["anchor"].score == 1.0
        assert by_id["north_platte"].score == pytest.approx(0.90)
        assert by_id["jack_st_malo"].score == pytest.approx(0.875)
        assert by_id["buckskin"].score == pytest.approx(0.65)

    def test_ranking_is_deterministic_across_calls(self):
        kwargs = dict(water_depth_m=1580.0, development_system="subsea20")
        first = find_analogs(**kwargs)
        second = find_analogs(**kwargs)
        assert _ids(first) == _ids(second)
        assert [m.score for m in first] == [m.score for m in second]

    def test_limit_truncates_after_ranking(self):
        top3 = find_analogs(
            region="gulf_of_mexico",
            water_depth_m=1580.0,
            development_system="subsea20",
            status="producing",
            limit=3,
        )
        assert _ids(top3) == ["anchor", "shenandoah", "north_platte"]
        with pytest.raises(ValueError, match="limit"):
            find_analogs(region="gulf_of_mexico", limit=0)


# ---------------------------------------------------------------------------
# Null handling — unknowns surface in the rationale, never silent matches
# ---------------------------------------------------------------------------


class TestNullHandling:
    def test_null_attribute_is_unknown_not_matched(self):
        matches = find_analogs(development_system="subsea15")
        buckskin = next(m for m in matches if m.project.project_id == "buckskin")
        assert _rationale_by_criterion(buckskin) == {"development_system": "unknown"}
        assert buckskin.score == 0.0

    def test_all_unknown_candidate_is_kept_not_dropped(self):
        # buckskin has null dev_system AND null status: with both criteria
        # supplied it earns nothing but misses nothing -> kept, ranked last.
        matches = find_analogs(development_system="subsea20", status="producing")
        assert "buckskin" in _ids(matches)
        buckskin = next(m for m in matches if m.project.project_id == "buckskin")
        assert set(_rationale_by_criterion(buckskin).values()) == {"unknown"}

    def test_miss_plus_unknown_is_excluded(self):
        # buckskin misses the (empty) 'worldwide' region and is unknown on
        # dev_system: a hard miss with zero earned credit -> excluded, unlike
        # the all-unknown case above. (Everything else also misses region and
        # earns nothing on a tieback15 query except julia, which matches it.)
        matches = find_analogs(region="worldwide", development_system="tieback15")
        assert "buckskin" not in _ids(matches)
        assert _ids(matches) == ["julia"]

    def test_partial_match_beats_exclusion(self):
        # julia misses a subsea20 query on dev-system but still matches
        # status=producing -> partial score, ranked below full matches but
        # NOT excluded (only projects that earn nothing and miss are dropped).
        matches = find_analogs(development_system="subsea20", status="producing")
        ids = _ids(matches)
        assert "julia" in ids
        assert ids.index("julia") > ids.index("anchor")

    def test_every_rationale_status_is_in_vocabulary(self):
        for m in find_analogs(
            region="gulf_of_mexico", water_depth_m=1580.0, status="producing"
        ):
            for a in m.rationale:
                assert a.status in {"matched", "near_miss", "missed", "unknown"}
                assert 0.0 <= a.credit <= 1.0


# ---------------------------------------------------------------------------
# Screening-run consumability (JSON-serialisable records)
# ---------------------------------------------------------------------------


class TestRecords:
    def test_records_round_trip_through_json(self):
        matches = find_analogs(
            region="gulf_of_mexico", water_depth_m=1580.0, status="producing"
        )
        records = to_records(matches)
        assert json.loads(json.dumps(records)) == records

    def test_records_carry_score_rationale_and_plain_types(self):
        def only_plain(value) -> bool:
            if isinstance(value, dict):
                return all(
                    isinstance(k, str) and only_plain(v) for k, v in value.items()
                )
            if isinstance(value, list):
                return all(only_plain(v) for v in value)
            return value is None or isinstance(value, (str, int, float, bool))

        records = to_records(find_analogs(development_system="subsea20"))
        assert records
        for record in records:
            assert only_plain(record), record["project_id"]
            assert {"project_id", "score", "rationale", "water_depth_class"} <= set(
                record
            )
            assert isinstance(record["bsee_area_blocks"], list)
            assert isinstance(record["sources"], list)
            for entry in record["rationale"]:
                assert {"criterion", "status", "weight", "credit", "detail"} == set(
                    entry
                )


# ---------------------------------------------------------------------------
# Weights file (externalized scoring — validated loudly)
# ---------------------------------------------------------------------------


def _write_weights(tmp_path: Path, cfg: dict) -> Path:
    p = tmp_path / "weights.yml"
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return p


class TestWeightsFile:
    def test_shipped_weights_load_and_cover_all_criteria(self):
        assert ANALOG_WEIGHTS_PATH.is_file()
        cfg = load_analog_weights()
        assert set(cfg["criteria_weights"]) == set(CRITERIA)
        assert sum(cfg["criteria_weights"].values()) == pytest.approx(1.0)
        for credit in cfg["near_miss_credits"].values():
            assert 0.0 <= credit < 1.0

    def test_missing_criterion_rejected(self, tmp_path: Path):
        cfg = copy.deepcopy(yaml.safe_load(ANALOG_WEIGHTS_PATH.read_text()))
        del cfg["criteria_weights"]["status"]
        with pytest.raises(ValueError, match="criteria_weights"):
            load_analog_weights(_write_weights(tmp_path, cfg))

    def test_weights_must_sum_to_one(self, tmp_path: Path):
        cfg = copy.deepcopy(yaml.safe_load(ANALOG_WEIGHTS_PATH.read_text()))
        cfg["criteria_weights"]["region"] = 0.9
        with pytest.raises(ValueError, match="sum to 1.0"):
            load_analog_weights(_write_weights(tmp_path, cfg))

    def test_non_positive_weight_rejected(self, tmp_path: Path):
        cfg = copy.deepcopy(yaml.safe_load(ANALOG_WEIGHTS_PATH.read_text()))
        cfg["criteria_weights"]["region"] = 0
        with pytest.raises(ValueError, match="positive"):
            load_analog_weights(_write_weights(tmp_path, cfg))

    def test_near_miss_credit_must_stay_below_full_match(self, tmp_path: Path):
        cfg = copy.deepcopy(yaml.safe_load(ANALOG_WEIGHTS_PATH.read_text()))
        cfg["near_miss_credits"]["water_depth_adjacent_class"] = 1.0
        with pytest.raises(ValueError, match="near-miss credit"):
            load_analog_weights(_write_weights(tmp_path, cfg))

    def test_unknown_near_miss_key_rejected(self, tmp_path: Path):
        cfg = copy.deepcopy(yaml.safe_load(ANALOG_WEIGHTS_PATH.read_text()))
        cfg["near_miss_credits"]["bonus_for_vibes"] = 0.2
        with pytest.raises(ValueError, match="near_miss_credits"):
            load_analog_weights(_write_weights(tmp_path, cfg))

    def test_alternate_weights_change_scores(self, tmp_path: Path):
        cfg = copy.deepcopy(yaml.safe_load(ANALOG_WEIGHTS_PATH.read_text()))
        cfg["criteria_weights"] = {
            "region": 0.7,
            "water_depth": 0.1,
            "development_system": 0.1,
            "status": 0.1,
        }
        weights = _write_weights(tmp_path, cfg)
        default = find_analogs(region="gulf_of_mexico", status="pre-FID")
        reweighted = find_analogs(
            region="gulf_of_mexico", status="pre-FID", weights_path=weights
        )
        # region .7 / (.7+.1) = .875 vs default .30/.40 = .75 for a
        # region-match + status-miss project (e.g. anchor).
        d = {m.project.project_id: m.score for m in default}
        r = {m.project.project_id: m.score for m in reweighted}
        assert d["anchor"] == pytest.approx(0.75)
        assert r["anchor"] == pytest.approx(0.875)


# ---------------------------------------------------------------------------
# Query validation
# ---------------------------------------------------------------------------


class TestQueryValidation:
    def test_at_least_one_criterion_required(self):
        with pytest.raises(ValueError, match="at least one criterion"):
            find_analogs()

    def test_depth_m_and_class_are_mutually_exclusive(self):
        with pytest.raises(ValueError, match="not both"):
            find_analogs(water_depth_m=1500.0, water_depth_class="ultra_deepwater")

    def test_metric_conversion_constant_is_exact(self):
        assert FT_PER_M == pytest.approx(1 / 0.3048)
