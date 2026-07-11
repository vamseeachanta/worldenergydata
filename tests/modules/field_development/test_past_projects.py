# ABOUTME: Tests for the past-projects registry catalog + query API (issue #931).
# ABOUTME: Offline only — loader, filters, provenance completeness, null handling.
"""Tests for ``worldenergydata.field_development.past_projects``."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from worldenergydata.field_development.past_projects import (
    PAST_PROJECTS_PATH,
    REQUIRED_PROJECT_FIELDS,
    VALID_STATUSES,
    WATER_DEPTH_CLASSES,
    classify_water_depth,
    load_past_projects,
    past_project_operators,
    past_project_regions,
    past_projects,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIELDS_YML = REPO_ROOT / "config" / "fields.yml"
ATTR_REGISTRY_YML = (
    REPO_ROOT / "config" / "ong_field_development" / "fields_registry.yml"
)


def _raw_catalog() -> dict:
    return yaml.safe_load(PAST_PROJECTS_PATH.read_text(encoding="utf-8"))


def _write(tmp_path: Path, catalog: dict) -> Path:
    p = tmp_path / "catalog.yml"
    p.write_text(yaml.safe_dump(catalog), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Catalog contract
# ---------------------------------------------------------------------------


class TestCatalog:
    def test_catalog_ships_next_to_module(self):
        assert PAST_PROJECTS_PATH.is_file()

    def test_loads_and_is_nonempty(self):
        projects = load_past_projects()
        assert projects, "catalog must not be empty"

    def test_every_entry_carries_required_fields(self):
        for region in _raw_catalog()["regions"].values():
            for raw in region.get("projects") or []:
                assert REQUIRED_PROJECT_FIELDS.issubset(raw), raw.get("project_id")

    def test_gom_region_present_and_populated(self):
        gom = past_projects(region="gulf_of_mexico")
        assert len(gom) >= 10
        assert {p.project_id for p in gom} == {
            p.project_id for p in load_past_projects()
        }, "GoM is currently the only populated region"

    def test_worldwide_region_structured_but_empty(self):
        regions = past_project_regions()
        assert "worldwide" in regions, "worldwide slice must be structured for later"
        assert past_projects(region="worldwide") == []


# ---------------------------------------------------------------------------
# Provenance discipline
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_every_entry_has_at_least_one_source(self):
        for p in load_past_projects():
            assert p.sources, f"{p.project_id} has no provenance sources"

    def test_every_source_path_exists_in_repo(self):
        for p in load_past_projects():
            for source in p.sources:
                assert (REPO_ROOT / source).is_file(), (
                    f"{p.project_id} cites a source that does not exist in the "
                    f"repo: {source}"
                )

    def test_every_project_resolves_in_canonical_fields_yml(self):
        """project_id == canonical_id in fields.yml — no parallel identities."""
        canonical = {
            f["canonical_id"]: f
            for f in yaml.safe_load(FIELDS_YML.read_text(encoding="utf-8"))["fields"]
        }
        for p in load_past_projects():
            assert (
                p.project_id in canonical
            ), f"{p.project_id} is not a canonical_id in config/fields.yml"
            field = canonical[p.project_id]
            assert p.display_name == field["display_name"], p.project_id
            assert set(p.bsee_area_blocks) == set(
                field["bsee"]["area_blocks"]
            ), p.project_id
            assert p.play == field["play"], p.project_id

    def test_attributes_cohere_with_upstream_registry(self):
        """Where an entry cites fields_registry.yml, its attributes match it."""
        upstream = yaml.safe_load(ATTR_REGISTRY_YML.read_text(encoding="utf-8"))[
            "fields"
        ]
        checked = 0
        for p in load_past_projects():
            if "config/ong_field_development/fields_registry.yml" not in p.sources:
                continue
            src = upstream[p.project_id]
            assert p.water_depth_ft == src["water_depth_ft"], p.project_id
            assert p.status == src.get("status"), p.project_id
            assert p.operator == src.get("public_metadata", {}).get(
                "operator"
            ), p.project_id
            first_oil = src.get("first_oil")
            expected_year = int(str(first_oil)[:4]) if first_oil else None
            assert p.first_oil_year == expected_year, p.project_id
            assert p.development_system == src.get("dev_system"), p.project_id
            checked += 1
        assert checked >= 10, "expected the whole GoM slice to be cross-checked"

    def test_null_attributes_carry_an_explanatory_note(self):
        nullable = (
            "operator",
            "facility",
            "status",
            "first_oil_year",
            "development_system",
        )
        for p in load_past_projects():
            if any(getattr(p, attr) is None for attr in nullable):
                assert (
                    p.notes
                ), f"{p.project_id} has null attributes but no provenance note"


# ---------------------------------------------------------------------------
# Water-depth classification
# ---------------------------------------------------------------------------


class TestWaterDepthClass:
    def test_boem_thresholds(self):
        assert classify_water_depth(400) == "shallow"
        assert classify_water_depth(999) == "shallow"
        assert classify_water_depth(1000) == "deepwater"
        assert classify_water_depth(4999) == "deepwater"
        assert classify_water_depth(5000) == "ultra_deepwater"
        assert classify_water_depth(9525) == "ultra_deepwater"

    def test_none_depth_is_never_classified(self):
        assert classify_water_depth(None) is None

    def test_every_class_is_in_the_declared_vocabulary(self):
        for p in load_past_projects():
            assert p.water_depth_class in WATER_DEPTH_CLASSES or (
                p.water_depth_class is None and p.water_depth_ft is None
            )


# ---------------------------------------------------------------------------
# Query API / filters
# ---------------------------------------------------------------------------


class TestFilters:
    def test_no_filters_returns_everything(self):
        assert len(past_projects()) == len(load_past_projects())

    def test_region_accepts_key_and_display_name(self):
        by_key = past_projects(region="gulf_of_mexico")
        by_name = past_projects(region="US Gulf of Mexico")
        by_case = past_projects(region="Gulf_Of_Mexico")
        assert by_key and by_key == by_name == by_case

    def test_unknown_region_fails_closed(self):
        assert past_projects(region="atlantis_basin") == []

    def test_operator_filter_case_insensitive(self):
        chevron = past_projects(operator="chevron")
        assert {p.project_id for p in chevron} == {
            "anchor",
            "jack_st_malo",
            "big_foot",
        }

    def test_operator_filter_never_matches_null_operators(self):
        assert past_projects(operator="Chevron") == [
            p for p in past_projects(operator="Chevron") if p.operator is not None
        ]
        assert past_projects(operator="Unknown Operator LLC") == []

    def test_water_depth_class_filter(self):
        deep = past_projects(water_depth_class="deepwater")
        ultra = past_projects(water_depth_class="ultra_deepwater")
        assert {p.project_id for p in deep} == {"tiber"}
        assert all(p.water_depth_ft >= 5000 for p in ultra)
        assert past_projects(water_depth_class="shallow") == []

    def test_invalid_water_depth_class_raises(self):
        with pytest.raises(ValueError, match="water_depth_class"):
            past_projects(water_depth_class="abyssal")

    def test_status_filter_case_insensitive_and_validated(self):
        producing = past_projects(status="producing")
        assert {p.project_id for p in past_projects(status="pre-fid")} == {
            "kaskida",
            "tiber",
        }
        assert all(p.status == "producing" for p in producing)
        with pytest.raises(ValueError, match="status"):
            past_projects(status="abandoned-maybe")

    def test_filters_compose(self):
        rows = past_projects(
            region="gulf_of_mexico",
            operator="Chevron",
            water_depth_class="ultra_deepwater",
            status="producing",
        )
        assert {p.project_id for p in rows} == {"anchor", "jack_st_malo", "big_foot"}

    def test_operator_selectable_list(self):
        operators = past_project_operators(region="gulf_of_mexico")
        assert operators == sorted(operators)
        assert "Chevron" in operators
        assert None not in operators


# ---------------------------------------------------------------------------
# Loader validation (malformed catalogs are rejected loudly)
# ---------------------------------------------------------------------------


class TestValidation:
    def test_missing_required_field_rejected(self, tmp_path: Path):
        catalog = copy.deepcopy(_raw_catalog())
        gom = catalog["regions"]["gulf_of_mexico"]["projects"]
        del gom[0]["water_depth_ft"]
        with pytest.raises(ValueError, match="missing required fields"):
            load_past_projects(_write(tmp_path, catalog))

    def test_empty_sources_rejected(self, tmp_path: Path):
        catalog = copy.deepcopy(_raw_catalog())
        catalog["regions"]["gulf_of_mexico"]["projects"][0]["sources"] = []
        with pytest.raises(ValueError, match="no sources"):
            load_past_projects(_write(tmp_path, catalog))

    def test_invalid_status_rejected(self, tmp_path: Path):
        catalog = copy.deepcopy(_raw_catalog())
        catalog["regions"]["gulf_of_mexico"]["projects"][0]["status"] = "maybe"
        with pytest.raises(ValueError, match="invalid status"):
            load_past_projects(_write(tmp_path, catalog))
        assert "maybe" not in VALID_STATUSES

    def test_duplicate_project_id_rejected(self, tmp_path: Path):
        catalog = copy.deepcopy(_raw_catalog())
        gom = catalog["regions"]["gulf_of_mexico"]["projects"]
        gom.append(copy.deepcopy(gom[0]))
        with pytest.raises(ValueError, match="Duplicate project_id"):
            load_past_projects(_write(tmp_path, catalog))

    def test_negative_water_depth_rejected(self, tmp_path: Path):
        catalog = copy.deepcopy(_raw_catalog())
        catalog["regions"]["gulf_of_mexico"]["projects"][0]["water_depth_ft"] = -10
        with pytest.raises(ValueError, match="water_depth_ft"):
            load_past_projects(_write(tmp_path, catalog))

    def test_missing_regions_mapping_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="regions"):
            load_past_projects(_write(tmp_path, {"projects": []}))

    def test_null_handling_round_trips(self):
        by_id = {p.project_id: p for p in load_past_projects()}
        kaskida = by_id["kaskida"]
        assert kaskida.operator is None
        assert kaskida.first_oil_year is None
        assert kaskida.water_depth_class == "ultra_deepwater"
        buckskin = by_id["buckskin"]
        assert buckskin.status is None
        assert buckskin.development_system is None
        assert buckskin.first_oil_year == 2019
