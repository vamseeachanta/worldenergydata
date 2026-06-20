# ABOUTME: Tests for the read-only well-operations source-readiness probe (#451).
# ABOUTME: Covers AVAILABLE (present+fresh), MISSING (absent), STALE (old mtime / 0-byte stub).
"""Deterministic, network-free tests for the readiness probe.

The probe module is imported *directly from its file* so the heavy
``worldenergydata`` root ``__init__`` is never triggered (per #407). Tests use
``tmp_path`` plus controlled ``os.utime`` mtimes and byte sizes so freshness and
stub detection are deterministic.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

# --- Import the probe module by path, bypassing the package __init__. -------
# Register in sys.modules before exec so dataclass field-resolution can look up
# the defining module (needed for @dataclass with default_factory).
_PROBE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "worldenergydata"
    / "flywheel"
    / "readiness_probe.py"
)
_MOD_NAME = "readiness_probe_under_test"
_spec = importlib.util.spec_from_file_location(_MOD_NAME, _PROBE_PATH)
probe = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_MOD_NAME] = probe
_spec.loader.exec_module(probe)


# --- Helpers ----------------------------------------------------------------

NOW = 1_700_000_000.0  # fixed clock for determinism


def _write(path: Path, content: bytes, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    os.utime(path, (mtime, mtime))


def _req(repo: Path, **over):
    base = dict(
        module_id="bsee",
        data_location="data/modules/bsee/current/operations",
        required_paths=("well_activity_summary.csv",),
        ttl_days=30.0,
        well_operation_entities=("well", "lease", "operator"),
    )
    base.update(over)
    return probe.RequiredSource(**base)


# --- AVAILABLE --------------------------------------------------------------

def test_available_present_and_fresh(tmp_path: Path):
    f = tmp_path / "data/modules/bsee/current/operations/well_activity_summary.csv"
    _write(f, b"api,well\n1,A\n", mtime=NOW - 5 * 86400)  # 5 days old, ttl 30

    rep = probe.probe_readiness([_req(tmp_path)], tmp_path, now=NOW)

    assert rep.overall_go is True
    src = rep.sources[0]
    assert src.state == "available"
    assert src.freshness_status == "fresh"
    assert src.completeness_status == "full"
    assert src.is_go is True
    # entity mapping only includes go sources
    assert "well" in rep.well_operation_entities
    assert rep.well_operation_entities["well"] == ["bsee"]
    assert rep.blocking_sources == []


# --- MISSING ----------------------------------------------------------------

def test_missing_absent_file(tmp_path: Path):
    # Directory may exist but the required file does not.
    (tmp_path / "data/modules/bsee/current/operations").mkdir(parents=True)

    rep = probe.probe_readiness([_req(tmp_path)], tmp_path, now=NOW)

    assert rep.overall_go is False
    src = rep.sources[0]
    assert src.state == "missing"
    assert src.freshness_status == "missing"
    assert src.completeness_status == "missing"
    assert src.is_go is False
    assert "well_activity_summary.csv" in src.missing_paths
    # missing source contributes nothing to the entity map
    assert rep.well_operation_entities == {}
    assert rep.blocking_sources == ["bsee"]


# --- STALE: old mtime -------------------------------------------------------

def test_stale_old_mtime(tmp_path: Path):
    f = tmp_path / "data/modules/bsee/current/operations/well_activity_summary.csv"
    _write(f, b"api,well\n1,A\n", mtime=NOW - 90 * 86400)  # 90 days old, ttl 30

    rep = probe.probe_readiness([_req(tmp_path)], tmp_path, now=NOW)

    assert rep.overall_go is False
    src = rep.sources[0]
    assert src.state == "stale"
    assert src.freshness_status == "stale"
    assert src.is_go is False
    assert src.age_days is not None and src.age_days > 30


# --- STALE: 0-byte stub -----------------------------------------------------

def test_stale_zero_byte_stub_is_empty(tmp_path: Path):
    f = tmp_path / "data/modules/bsee/current/operations/well_activity_summary.csv"
    _write(f, b"", mtime=NOW - 1 * 86400)  # fresh mtime but 0 bytes -> stub

    rep = probe.probe_readiness([_req(tmp_path)], tmp_path, now=NOW)

    assert rep.overall_go is False
    src = rep.sources[0]
    assert src.state == "missing"  # no real data
    assert src.completeness_status == "empty"
    assert "well_activity_summary.csv" in src.stub_paths
    assert src.is_go is False


# --- BLOCKER overrides files on disk ----------------------------------------

def test_blocker_forces_no_go(tmp_path: Path):
    f = tmp_path / "data/modules/bsee/current/operations/well_activity_summary.csv"
    _write(f, b"api,well\n1,A\n", mtime=NOW)  # present + fresh...

    rep = probe.probe_readiness(
        [_req(tmp_path, blocker_issue="#267")], tmp_path, now=NOW
    )

    src = rep.sources[0]
    assert src.state == "blocked"
    assert src.freshness_status == "blocked"
    assert src.completeness_status == "blocked"
    assert src.is_go is False
    assert src.blocker_issue == "#267"
    assert rep.overall_go is False


# --- Overall go/no-go aggregation across sources ----------------------------

def test_overall_go_requires_all_sources(tmp_path: Path):
    fresh = tmp_path / "data/modules/bsee/current/operations/well_activity_summary.csv"
    _write(fresh, b"x\n", mtime=NOW - 1 * 86400)
    # second source missing entirely
    reqs = [
        _req(tmp_path, module_id="bsee"),
        _req(
            tmp_path,
            module_id="fdas",
            data_location="data/modules/fdas/enhanced/wells",
            required_paths=("well_data_enhanced.csv",),
            ttl_days=60.0,
            well_operation_entities=("well", "production_interval"),
        ),
    ]
    rep = probe.probe_readiness(reqs, tmp_path, now=NOW)

    assert rep.overall_go is False
    states = {s.module_id: s.state for s in rep.sources}
    assert states["bsee"] == "available"
    assert states["fdas"] == "missing"
    assert rep.blocking_sources == ["fdas"]


# --- Contract enum validation -----------------------------------------------

def test_emitted_statuses_are_in_462_contract(tmp_path: Path):
    """Every status the probe emits must be a real #462 contract enum value.

    Uses the real repo contract file (read-only) when present.
    """
    repo_root = Path(__file__).resolve().parents[2]
    contract = repo_root / probe.DEFAULT_CONTRACT_RELPATH
    fresh_vals, comp_vals = probe.load_contract_enums(
        contract if contract.is_file() else None
    )

    f = tmp_path / "data/modules/bsee/current/operations/well_activity_summary.csv"
    _write(f, b"x\n", mtime=NOW - 1 * 86400)
    rep = probe.probe_readiness([_req(tmp_path)], tmp_path, now=NOW)
    for s in rep.sources:
        assert s.freshness_status in fresh_vals
        assert s.completeness_status in comp_vals


# --- Manifest fragment shape (#450 light dependency) ------------------------

def test_manifest_fragment_shape(tmp_path: Path):
    f = tmp_path / "data/modules/bsee/current/operations/well_activity_summary.csv"
    _write(f, b"x\n", mtime=NOW - 1 * 86400)
    rep = probe.probe_readiness([_req(tmp_path)], tmp_path, now=NOW)
    frag = rep.to_manifest_fragment()
    assert "source_readiness" in frag
    sr = frag["source_readiness"]
    assert sr["overall_go"] is True
    assert sr["sources"][0]["module_id"] == "bsee"
    assert "well_operation_entities" in sr


# --- Default well-ops requirement set is well-formed ------------------------

def test_default_well_operations_sources():
    reqs = probe.default_well_operations_sources()
    ids = {r.module_id for r in reqs}
    assert ids == {"bsee", "fdas"}
    for r in reqs:
        assert r.well_operation_entities  # entity mapping populated
        assert r.required_paths
