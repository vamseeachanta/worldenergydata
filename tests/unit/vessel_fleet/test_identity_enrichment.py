# ABOUTME: Tests for public IMO/aka identity enrichment (#619) of the named
# ABOUTME: dedicated-intervention roster + seed YAMLs (loader-agnostic).
"""Tests for the identity-enrichment fields added in #619.

CI-safe: loads the two package-data YAMLs directly with PyYAML and asserts the
identity contract (imo well-formedness + per-IMO provenance). No /mnt/ace or
main-checkout dependency.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_DATA_DIR = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "worldenergydata-vessel_fleet"
    / "src"
    / "worldenergydata"
    / "vessel_fleet"
    / "data"
)
_ROSTER_PATH = _DATA_DIR / "intervention_osv_roster.yml"
_SEED_PATH = _DATA_DIR / "intervention_vessels_seed.yml"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _entries() -> list[dict]:
    rows: list[dict] = []
    for path in (_ROSTER_PATH, _SEED_PATH):
        doc = _load(path)
        assert isinstance(doc, dict), f"{path.name} did not parse to a mapping"
        assert isinstance(doc.get("vessels"), list), f"{path.name} has no vessels list"
        rows.extend(doc["vessels"])
    return rows


def test_both_yamls_parse():
    assert _load(_ROSTER_PATH)["vessels"], "roster vessels empty"
    assert _load(_SEED_PATH)["vessels"], "seed vessels empty"


def test_imo_values_are_seven_digits_where_present():
    for entry in _entries():
        imo = entry.get("imo")
        if imo is None:
            continue
        name = entry.get("vessel_name") or entry.get("name")
        s = str(imo)
        assert s.isdigit(), f"{name}: imo {imo!r} is not numeric"
        assert len(s) == 7, f"{name}: imo {imo!r} is not 7 digits"


def test_every_imo_has_identity_source():
    for entry in _entries():
        if entry.get("imo") is None:
            continue
        name = entry.get("vessel_name") or entry.get("name")
        assert entry.get(
            "identity_source"
        ), f"{name}: imo present but no identity_source"


def test_aka_is_a_list_where_present():
    for entry in _entries():
        aka = entry.get("aka")
        if aka is None:
            continue
        name = entry.get("vessel_name") or entry.get("name")
        assert isinstance(aka, list), f"{name}: aka must be a list, got {type(aka)}"


def test_at_least_one_imo_enriched():
    assert any(e.get("imo") is not None for e in _entries()), "no imo enrichment found"
