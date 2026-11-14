"""Contract tests for the canonical field-identity registry (issue #755).

Guards ``config/fields.yml`` + ``worldenergydata.common.fields_registry`` as the
single source of truth for field identity in this repo (epic #754). Mirrors the
shape of ``tests/unit/lower_tertiary/test_portfolio_roster.py``.

Each duplicate-detection test documents its *mutation check* in the docstring:
it feeds the loader a deliberately corrupted registry and asserts it fails
closed, proving the guard is live (not vacuously green).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from tests.test_markers import unit
from worldenergydata.common.fields_registry import (
    AREA_BLOCK_RE,
    LEASE_RE,
    load_fields,
    normalize_name,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIELDS_YML = PROJECT_ROOT / "config" / "fields.yml"
REGISTRY_YML = PROJECT_ROOT / "config" / "ong_field_development" / "fields_registry.yml"
BENCHMARK_CSV = (
    PROJECT_ROOT
    / "reports"
    / "lower_tertiary"
    / "lt_well_benchmark_lower_tertiary_2010_latest.csv"
)
V_BASELINES = [
    PROJECT_ROOT / "config" / "analysis" / "lower_tertiary" / "golden_baseline_v30.yml",
    PROJECT_ROOT / "config" / "analysis" / "lower_tertiary" / "golden_baseline_v50.yml",
    PROJECT_ROOT / "config" / "analysis" / "lower_tertiary" / "latest_baseline.yml",
]

# The 7 distinct free-text field names the benchmark CSV carries (r1-enumerated).
# kaskida / north_platte / tiber have no benchmark rows. "Cascade Chinook" and
# "Jack St Malo" are the two whose spelling diverges from the display_name.
BENCHMARK_FIELD_NAMES = [
    "Anchor",
    "Big Foot",
    "Cascade Chinook",
    "Jack St Malo",
    "Julia",
    "Shenandoah",
    "Stones",
]

# fdp_slug values that intentionally diverge from slug(display_name).
FDP_SLUG_OVERRIDES = {"cascade_chinook", "north_platte"}


def _display_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


@pytest.fixture(scope="module")
def reg():
    return load_fields(FIELDS_YML)


@unit
class TestRoster:
    def test_at_least_ten_unique_ids(self, reg):
        ids = reg.all_ids()
        assert len(ids) >= 10
        assert len(set(ids)) == len(ids), "canonical_id values must be unique"

    def test_buckskin_present_as_kc_recovered(self, reg):
        """Buckskin (the crosswalk gap that motivated the D&C reconcile) is here."""
        bk = reg.by_id("buckskin")
        assert bk is not None
        assert bk.tier == "kc_recovered"

    def test_all_ids_in_file_order(self, reg):
        assert reg.all_ids()[0] == "big_foot"
        assert "buckskin" in reg.all_ids()


@unit
class TestStructuredForms:
    def test_leases_match_canonical_form(self, reg):
        for f in reg.fields:
            assert f.leases, f"{f.canonical_id} has no leases"
            for lease in f.leases:
                assert LEASE_RE.match(lease), f"{f.canonical_id}: bad lease {lease!r}"

    def test_area_blocks_match_canonical_form(self, reg):
        for f in reg.fields:
            assert f.area_blocks, f"{f.canonical_id} has no area_blocks"
            for blk in f.area_blocks:
                assert AREA_BLOCK_RE.match(blk), f"{f.canonical_id}: bad block {blk!r}"

    def test_fdp_slug_unique(self, reg):
        slugs = [f.fdp_slug for f in reg.fields]
        assert all(slugs), "every field needs an fdp_slug"
        assert len(set(slugs)) == len(slugs), "fdp_slug values must be unique"

    def test_fdp_slug_hyphen_rule(self, reg):
        """fdp_slug == hyphen-rule(display_name) unless an explicit override."""
        for f in reg.fields:
            assert re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", f.fdp_slug)
            if f.canonical_id not in FDP_SLUG_OVERRIDES:
                assert f.fdp_slug == _display_slug(f.display_name), (
                    f"{f.canonical_id}: fdp_slug {f.fdp_slug!r} != "
                    f"slug(display_name) {_display_slug(f.display_name)!r}"
                )

    def test_surfaces_schema(self, reg):
        for f in reg.fields:
            assert set(f.surfaces) == {
                "lifecycle_poster",
                "economics_page",
                "fdp_page",
            }
            assert all(isinstance(v, bool) for v in f.surfaces.values())


@unit
class TestResolution:
    def test_resolve_display_name(self, reg):
        assert reg.resolve("Jack/St. Malo") == "jack_st_malo"

    def test_resolve_is_case_and_punctuation_insensitive(self, reg):
        assert reg.resolve("jack st malo") == "jack_st_malo"
        assert reg.resolve("CASCADE/CHINOOK") == "cascade_chinook"
        assert reg.resolve("north platte (sparta)") == "north_platte"

    def test_resolve_unknown_returns_none(self, reg):
        assert reg.resolve("Mars-Ursa") is None
        assert reg.resolve(None) is None

    def test_by_id(self, reg):
        assert reg.by_id("stones").display_name == "Stones"
        assert reg.by_id("nope") is None

    def test_fdp_slug_lookup(self, reg):
        assert reg.fdp_slug("cascade_chinook") == "chinook"
        assert reg.fdp_slug("nope") is None

    def test_by_lease_resolves_all_input_variants(self, reg):
        """The 3 lease spellings that occur in source data all resolve (r1 F1/F2)."""
        for variant in ("G25806", "g25806", "OCS-G 25806", "G 25806"):
            assert reg.by_lease(variant) == "buckskin", variant
        # a lowercase-in-source lease (kaskida g25792) resolves too
        assert reg.by_lease("g25792") == "kaskida"
        assert reg.by_lease("G99999") is None
        assert reg.by_lease(None) is None


@unit
class TestAliasRoundTrip:
    def test_benchmark_field_names_all_resolve(self, reg):
        """Every distinct benchmark-CSV field name resolves to a canonical id."""
        for name in BENCHMARK_FIELD_NAMES:
            assert reg.resolve(name) is not None, f"benchmark name {name!r} unresolved"

    def test_benchmark_divergent_names_map_correctly(self, reg):
        assert reg.resolve("Cascade Chinook") == "cascade_chinook"
        assert reg.resolve("Jack St Malo") == "jack_st_malo"


@unit
class TestCrossConfigCoherence:
    """fields.yml must not drift from the auto-generated economics registry."""

    def test_ids_and_leases_subset_of_fields_registry(self, reg):
        src = yaml.safe_load(REGISTRY_YML.read_text())["fields"]
        for f in reg.fields:
            if f.tier == "kc_recovered":
                continue  # not present in the auto-generated economics registry
            assert (
                f.canonical_id in src
            ), f"{f.canonical_id} missing from fields_registry.yml"
            src_leases = {
                ln.upper() for ln in (src[f.canonical_id].get("leases") or [])
            }
            for lease in f.leases:
                assert lease.upper() in src_leases, (
                    f"{f.canonical_id}: lease {lease} not in fields_registry.yml "
                    f"{sorted(src_leases)}"
                )

    def test_v30_v50_baseline_projects_all_resolve(self, reg):
        """AUDIT: every field the V30/V50/latest gold-standard scripts name resolves."""
        for path in V_BASELINES:
            projects = yaml.safe_load(path.read_text()).get("projects", {})
            for pid, pv in projects.items():
                assert reg.by_id(pid) is not None, f"{path.name}: id {pid} unresolved"
                dn = pv.get("display_name")
                if dn:
                    assert (
                        reg.resolve(dn) == pid
                    ), f"{path.name}: display {dn!r} did not resolve to {pid}"


@unit
class TestFailClosed:
    """Duplicate/collision guards must raise at load (mutation checks)."""

    def _write(self, tmp_path, fields):
        p = tmp_path / "f.yml"
        p.write_text(yaml.safe_dump({"fields": fields}))
        return p

    def _base_field(self, cid="alpha", **over):
        f = {
            "canonical_id": cid,
            "display_name": cid.title(),
            "aliases": [],
            "region": "r",
            "play": "p",
            "bsee": {"area_blocks": ["WR001"], "leases": ["G00001"]},
            "bsee_block_note": "note",
            "fdp_slug": cid,
            "surfaces": {
                "lifecycle_poster": False,
                "economics_page": False,
                "fdp_page": False,
            },
        }
        f.update(over)
        return f

    def test_duplicate_canonical_id_raises(self, tmp_path):
        """MUTATION: two entries share canonical_id 'alpha' -> ValueError."""
        p = self._write(
            tmp_path,
            [self._base_field("alpha"), self._base_field("alpha", fdp_slug="a2")],
        )
        with pytest.raises(ValueError, match="Duplicate canonical_id"):
            load_fields(p)

    def test_cross_field_alias_collision_raises(self, tmp_path):
        """MUTATION: alias 'Shared' on two different ids -> ValueError."""
        p = self._write(
            tmp_path,
            [
                self._base_field("alpha", aliases=["Shared"]),
                self._base_field("beta", fdp_slug="beta", aliases=["Shared"]),
            ],
        )
        with pytest.raises(ValueError, match="Alias collision"):
            load_fields(p)

    def test_cross_field_lease_collision_raises(self, tmp_path):
        """MUTATION: lease G00001 on two different ids -> ValueError."""
        beta = self._base_field("beta", fdp_slug="beta")
        beta["bsee"]["leases"] = ["G00001"]  # same lease as alpha
        p = self._write(tmp_path, [self._base_field("alpha"), beta])
        with pytest.raises(ValueError, match="Lease collision"):
            load_fields(p)

    def test_same_field_alias_matching_display_is_ok(self, tmp_path):
        """A punctuation variant of the same field's own name is NOT a collision."""
        p = self._write(
            tmp_path,
            [self._base_field("cascade_chinook", aliases=["Cascade Chinook"])],
        )
        reg = load_fields(p)  # must not raise
        assert reg.resolve("Cascade Chinook") == "cascade_chinook"


@pytest.fixture
def global_registry_fields():
    """Synthetic regions with benign repetitions within a canonical identity.

    Lease tokens follow TestFailClosed._base_field's G00001 example; G00002
    is hand-selected to differ in the last digit, not an engineering value.
    """
    return [
        {
            "canonical_id": "alpha",
            "display_name": "Alpha",
            "aliases": [
                "AL.PHA",
                "Shared Field",
                "SHARED-FIELD",
                "shared_field",
                "Shared Field",
            ],
            "region": "region_east",
            "bsee": {
                "leases": [
                    "G00001",
                    "g00001",
                    "OCS-G00001",
                    "OCS-G 00001",
                    "G 00001",
                    "G00001",
                ]
            },
        },
        {
            "canonical_id": "beta",
            "display_name": "Beta",
            "aliases": ["Other Field"],
            "region": "region_west",
            "bsee": {"leases": ["G00002"]},
        },
    ]


@unit
@pytest.mark.parametrize("reverse_fields", [False, True], ids=["forward", "reverse"])
@pytest.mark.parametrize("swap_regions", [False, True], ids=["east-west", "west-east"])
@pytest.mark.parametrize(
    "identity, variants, message",
    [
        pytest.param(
            "aliases",
            ("Shared Field", "sHaReD / fIeLd"),
            "Alias collision",
            id="alias-case-punctuation",
        ),
        pytest.param(
            "leases",
            ("G00001", "OCS-G 00001"),
            "Lease collision",
            id="lease-ocs-spaced",
        ),
        pytest.param(
            "leases",
            ("G00001", "G 00001"),
            "Lease collision",
            id="lease-spaced",
        ),
    ],
)
def test_global_normalized_collisions_are_order_independent(
    tmp_path,
    global_registry_fields,
    reverse_fields,
    swap_regions,
    identity,
    variants,
    message,
):
    """MUTATION: normalized aliases/leases cannot identify distinct regional ids.

    Names ignore case and punctuation; leases ignore case, OCS- and spaces.
    Only the selected identity collides, so the other guard cannot mask it.
    """
    alpha, beta = global_registry_fields
    if swap_regions:
        alpha["region"], beta["region"] = beta["region"], alpha["region"]
    for field, variant in zip(global_registry_fields, variants):
        if identity == "aliases":
            field["aliases"] = [variant]
        else:
            field["bsee"]["leases"] = [variant]
    if reverse_fields:
        global_registry_fields.reverse()
    path = tmp_path / "global-fields.yml"
    path.write_text(yaml.safe_dump({"fields": global_registry_fields}))
    with pytest.raises(ValueError, match=message):
        load_fields(path)


@unit
def test_global_registry_same_field_variants_roundtrip(
    tmp_path, global_registry_fields
):
    """Hand-enumerated identities document the existing normalization contract.

    Name keys ignore case/non-alphanumerics; lease keys ignore case, OCS-
    and spaces. Expected identities are read from the synthetic fixture,
    without calling normalization helpers. G99999 follows TestResolution's
    unknown-lease example and is absent from this fixture.
    """
    path = tmp_path / "global-fields.yml"
    path.write_text(yaml.safe_dump({"fields": global_registry_fields}))
    reg = load_fields(path)
    assert reg.all_ids() == ["alpha", "beta"]
    expected_aliases = {
        "alpha": "alpha",
        "Alpha": "alpha",
        "AL.PHA": "alpha",
        "a l p h a": "alpha",
        "Shared Field": "alpha",
        "SHARED-FIELD": "alpha",
        "shared_field": "alpha",
        "shared / field": "alpha",
        "beta": "beta",
        "Beta": "beta",
        "Other Field": "beta",
        "OTHER-FIELD": "beta",
        "Unregistered Field": None,
        "": None,
        None: None,
    }
    for alias, expected in expected_aliases.items():
        assert reg.resolve(alias) == expected, alias
    expected_leases = {
        "G00001": "alpha",
        "g00001": "alpha",
        "OCS-G00001": "alpha",
        "OCS-G 00001": "alpha",
        "G 00001": "alpha",
        "ocs-g 00001": "alpha",
        "G00002": "beta",
        "ocs-g 00002": "beta",
        "G99999": None,
        "OCS-G 99999": None,
        "": None,
        None: None,
    }
    for lease, expected in expected_leases.items():
        assert reg.by_lease(lease) == expected, lease


@unit
def test_normalize_name_collapses_punctuation():
    assert normalize_name("Cascade/Chinook") == normalize_name("Cascade Chinook")
    assert normalize_name("Jack/St. Malo") == "jackstmalo"
