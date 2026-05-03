"""Roster completeness tests for the LT portfolio (#374).

Asserts that every field declared in `LT_FIELDS_2026` has a corresponding
yaml config and is loadable. Catches the silent-drop pattern where the
loader returns a dict missing one or more fields without raising.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tests.test_markers import unit  # noqa: E402
from worldenergydata.lower_tertiary.npv import (  # noqa: E402
    load_field_inputs,
    load_lease_mapping,
)
from worldenergydata.lower_tertiary.portfolio import (  # noqa: E402
    LT_FIELDS_2026,
    expected_field_yaml_paths,
    fields_config_dir,
)


@unit
class TestLowerTertiaryRoster:
    """The 2026 portfolio must have all 10 fields backed by yaml configs."""

    def test_roster_size_is_ten(self):
        assert len(LT_FIELDS_2026) == 10
        assert len(set(LT_FIELDS_2026)) == 10, "Roster has duplicates"

    @pytest.mark.parametrize("field_id", LT_FIELDS_2026)
    def test_each_field_has_yaml(self, field_id):
        path = fields_config_dir() / f"{field_id}.yml"
        assert path.is_file(), (
            f"LT_FIELDS_2026 lists {field_id!r} but {path} is missing. "
            f"Either add the yaml or remove the field from the roster."
        )

    def test_loader_finds_all_roster_fields(self):
        """load_field_inputs must surface every field in the roster.

        This is the regression-guard against silent drops: if the loader
        ever filters out a field for a non-status reason, this test fails.
        """
        lease_mapping_path = (
            PROJECT_ROOT / "config/analysis/lower_tertiary/lease_mapping_fdas.yml"
        )
        lease_mapping = load_lease_mapping(lease_mapping_path)

        # No status filter — we want every roster field surfaced.
        loaded = load_field_inputs(fields_config_dir(), lease_mapping)
        missing = [fid for fid in LT_FIELDS_2026 if fid not in loaded]
        assert not missing, (
            f"Loader did not surface roster fields: {missing}. "
            f"Loader returned: {sorted(loaded.keys())}."
        )

    def test_expected_field_yaml_paths_resolves_to_real_files(self):
        for path in expected_field_yaml_paths():
            assert path.is_file(), f"Roster path missing: {path}"

    def test_no_extra_yamls_outside_roster(self):
        """If a yaml exists that the roster doesn't list, surface the drift.

        Prevents the inverse silent-drop: someone adds a yaml without
        updating the roster, and the report misses it.
        """
        on_disk = {p.stem for p in fields_config_dir().glob("*.yml")}
        extras = on_disk - set(LT_FIELDS_2026)
        assert not extras, (
            f"Yamls exist that are not in LT_FIELDS_2026: {sorted(extras)}. "
            f"Either add them to the roster or remove the yamls."
        )
